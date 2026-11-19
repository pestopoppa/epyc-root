"""Check the Q38 exact-weight scope at AutoKernel's planner entry without inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
TMP = Path("/mnt/raid0/llm/tmp")
SOURCE = "mi210-paired-raw"
METRIC = "native_request_decode_tps"
ORDER = [["p1", "C"], ["p1", "B"], ["p2", "B"], ["p2", "C"]]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fixture(out: Path, kind: str) -> Path:
    from scripts.vidya.producers import mi210_paired_capture as raw

    model = out / "CONTROL-ONLY.gguf"
    model.write_bytes(b"Q38 exact-weight structural fixture; no weights or inference\n")
    capture = out / ("synthetic-q38-" + kind)
    capture.mkdir()
    raw.begin(capture, {
        "source": "Q38P-3a", "mode": "measurement" if kind != "smoke" else "smoke",
        "test_fixture": "synthetic-planner-control-only",
        "model": [{"path": str(model), "sha256": sha(model), "error": None}],
        "builds": None, "grant": None, "order": ORDER,
        "native_producer": {"path": __file__, "sha256": sha(Path(__file__))},
        "recipe": {
            "arm_categories": {"C": "BASELINE", "B": "CANDIDATE"},
            "argv": {arm: ["llama-server", "-m", str(model), "-ngl", "all", "--device", "ROCm0"]
                     for arm in ("C", "B")},
        },
    })
    for launch, (pair, arm) in enumerate(ORDER):
        raw.record(capture, {
            "pair": pair, "arm": arm, "state": "complete",
            "requests": [{"timings": {"predicted_n": 8, "predicted_ms": 100,
                                      "predicted_per_second": 80 + 5 * launch + request}}
                         for request in range(5)],
            "actual_placement": None, "residency_linkage": None, "grant": None,
            "stop": None, "errors": None, "release": None,
        })
        if kind == "partial":
            break
    raw.finish(capture, "partial" if kind == "partial" else "complete")
    return capture


def ingest(reader: Path, capture: Path, ledger: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-B", str(reader / "scripts/vidya/cli.py"),
         "--ledger", str(ledger), "--json", "ingest", SOURCE, "--path", str(capture),
         "--as-of", datetime.now(timezone.utc).isoformat(), "--only-new"],
        cwd=reader, check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def verified_native(deploy: Path) -> Path:
    # Use the exact original deployment completion predicate before opening its capture.
    command = [sys.executable, "-I", "-B", str(deploy / "mi210_native_deploy.py"), "complete"]
    subprocess.run(command, cwd=deploy, check=True, capture_output=True, text=True)
    return Path(json.loads((deploy / "RESULT.json").read_bytes())["capture"])


def run(reader: Path, research: Path, out: Path, deploy: Path | None, baseline: bool) -> dict:
    sys.path.insert(0, str(ROOT))
    from scripts.vidya.adapters import mi210_paired_raw
    from scripts.vidya.producers import mi210_paired_capture as raw

    native = deploy is not None
    capture = verified_native(deploy) if native else fixture(out, "complete")
    captures = {path.name: sha(path) for path in capture.glob("*.json")}
    record = raw.read(capture)
    declaration = record["intent"]["declaration"]
    require(record["state"] == "complete" and declaration["source"] == "Q38P-3a"
            and declaration["mode"] == "measurement" and declaration["order"] == ORDER,
            "Q38 four-launch measurement contract refused")
    require(not native or "test_fixture" not in declaration, "synthetic Q38 input refused as native")
    attempts = record["attempts"]
    require(len(attempts) == 4 and all(len(item["native"]["requests"]) == 5 for item in attempts),
            "Q38 native schedule incomplete")
    model, = declaration["model"]
    expected_scope = {"model_sha256": model["sha256"], "backend": "gpu", "scope_basis": "native"}
    rows = mi210_paired_raw.project(capture)
    require(len(rows) == 20 and all(row.applicability == expected_scope for row in rows),
            "Q38 weight or GPU scope refused")
    expected_ids = {"clm_" + row.measurement_id for row in rows}
    require(len(expected_ids) == 20, "Q38 request identity collision")
    index, alarm, ledger = (out / name for name in ("index.yaml", "alarm.yaml", "ledger.jsonl"))
    index.write_text("[]\n")
    alarm.write_text("backend: file\nfile:\n  path: " + str(out / "alarms.jsonl") + "\n")
    report = ingest(reader, capture, ledger)
    require((report["rows_projected"], report["frames_emitted"], report["refused"]) == (20, 60, []),
            "registered ingest refused a Q38 request")
    frames = [json.loads(line)["frame"] for line in ledger.read_text().splitlines()]
    support = {frame["assertion"]["claim_id"]: frame["assertion"] for frame in frames
               if frame["frame_type"].endswith("evidence_supports_claim/v1")}
    require(set(support) == expected_ids and all(
        (item["metric"], item["metric_direction"], item["unit"], item["protocol_id"],
         item["reps"], item["grade"]) == (
             METRIC, "higher_better", "token/s", "", 1, {"Q": "Judged", "T": "Located"})
        for item in support.values()), "registered ingest grade or request identity drift")

    refusals = {}
    if not native and not baseline:
        for kind in ("smoke", "partial", "tampered"):
            invalid = fixture(out, kind)
            if kind == "tampered":
                (invalid / "attempt-01.json").write_text("{}\n")
            refused = ingest(reader, invalid, out / f"refused-{kind}.jsonl")
            require((refused["rows_projected"], refused["frames_emitted"], len(refused["refused"]))
                    == (0, 0, 1), f"{kind} fixture projected")
            refusals[kind] = refused["refused"][0]["reason"]

    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]
    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    config = belief_context.BeliefConfig(root=reader, ledger=ledger, index=index, alarm_config=alarm,
                                        known_good=out / "known-good.json", alarm_state=out / "alarm-state.json")

    def context(backend, digest=None):
        target = {"path": model["path"]}
        if digest is not None:
            target["sha256"] = digest
        return {"current_regime": {"model": target, "backend": backend}}

    observed = {}

    def before_backend(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        observed.update(belief=belief, prompt=prompt)
        return actors.Abstain(reason="Q38 offline planner canary"), sorted(expected_ids)

    with patch.object(actors.AgentPlanner, "_proposal_from_agent", before_backend):
        actors.AgentPlanner(workspace=out / "lane", belief=config).propose(context("gpu", model["sha256"]))
    ready = observed["belief"]
    require(ready.answer["reader_checkout"]["current"] is True, "planner reader checkout refused")
    evidence = ready.evidence
    shown = evidence["claims"]
    if baseline:
        require(not shown and not ready.section, "base planner unexpectedly retained digest scope")
    else:
        visible = {claim["claim_id"] for claim in shown}
        omitted = {claim["claim_id"] for claim in evidence["omitted"] if claim["reason"] == "bounded"}
        require(shown and not visible & omitted and visible | omitted == expected_ids,
                "planner did not account for every exact-scope Q38 request")
        require(ready.section in observed["prompt"] and all(
            claim["tier"] == "target" and claim["grade"] == "Judged/Located"
            and claim["claim_id"] in ready.section for claim in shown), "Q38 planner scope or grade drift")
    receipt_log = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
    actor = json.loads(receipt_log.read_text().splitlines()[-1])
    expected_reliance = belief_context.reliance(sorted(expected_ids),
                                                belief_context.reliable_claim_ids(evidence),
                                                belief_context.host_claim_ids(evidence))
    require(actor["reliance"] == expected_reliance, "Q38 proposal reliance receipt drift")

    excludes = {}
    if not baseline:
        other_digest = hashlib.sha256(b"different weight bytes").hexdigest()
        for label, target in {"cpu": context("cpu", model["sha256"]),
                              "different-weight": context("gpu", other_digest),
                              "missing-digest": context("gpu"),
                              "invalid-digest": context("gpu", "invalid")}.items():
            control = belief_context.prepare(target, config)
            require(not control.evidence["claims"] and not control.section, f"{label} received Q38 claims")
            excludes[label] = control.evidence["reasons"]
    require(captures == {path.name: sha(path) for path in capture.glob("*.json")},
            "capture changed during replay")
    excerpt = out / "planner-context.txt"
    excerpt.write_text(ready.section + "\n")
    return {
        "schema": "epyc.vidya.mi210_q38_planning_canary.v1", "status": "passed",
        "authority": "verified-native-replay" if native else "software-control-only",
        "baseline": baseline, "capture_files_sha256": captures,
        "capture_terminal_sha256": record["terminal"]["row_sha256"], "capture_run_id": capture.name,
        "rows": 20, "frames": 60, "refused": 0, "visible_count": len(shown),
        "entry_point": "AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        "actor_backend_called": False, "excluded": excludes, "refusal_controls": refusals,
        "reader_checkout": ready.answer["reader_checkout"], "model_scope": expected_scope,
        "actor_receipt_id": actor["receipt_id"], "reliance": actor["reliance"],
        "rendered_excerpt_sha256": sha(excerpt), "scratch_ledger": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("reader", "research", "scratch"):
        parser.add_argument(f"--{field}", required=True, type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--native-deploy", type=Path)
    modes.add_argument("--synthetic", choices=("baseline", "candidate"))
    args = parser.parse_args()
    out = args.scratch.resolve()
    if TMP not in out.parents or out.exists():
        parser.error(f"--scratch must be a new subdirectory of {TMP}")
    out.mkdir(parents=True)
    try:
        report = run(args.reader.resolve(strict=True), args.research.resolve(strict=True), out,
                     args.native_deploy.resolve(strict=True) if args.native_deploy else None,
                     args.synthetic == "baseline")
    except (OSError, AssertionError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError, TypeError) as exc:
        report = {"status": "unknown", "refusal": f"{type(exc).__name__}: {exc}"}
    (out / "receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return int(report["status"] != "passed")


if __name__ == "__main__":
    sys.exit(main())
