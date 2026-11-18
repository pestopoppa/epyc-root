"""Replay the two original thinking-budget diagnostics to the AutoKernel prompt boundary."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

SOURCE = "thinking-budget-semantics"
VIDYA = Path(__file__).resolve().parents[1]
ROOT = VIDYA.parents[1]
sys.path.insert(0, str(VIDYA))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def ingest(path, ledger):
    run = subprocess.run(
        [sys.executable, "-IB", str(VIDYA / "cli.py"), "--ledger", str(ledger), "--json",
         "ingest", SOURCE, "--path", str(path), "--only-new",
         "--as-of", datetime.now(timezone.utc).isoformat()],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=24,
    )
    return json.loads(run.stdout)


def native_rows(results, out):
    from adapters import thinking_budget_semantics as native

    ledger = out / "ledger.jsonl"
    rows = {}
    for path in results:
        report = ingest(path, ledger)
        require((report["rows_projected"], report["frames_emitted"], report["refused"]) == (3, 9, []),
                f"registered native intake refused {path}: {report}")
        for row in native.native_rows(path):
            data = row["row"]
            require(data["emitted_at"] is None and data["extra"]["time_basis"] == "registered-row-day",
                    "original report was assigned an unrecorded emission time")
            rows["clm_" + data["measurement_id"]] = data
    require(len(rows) == 6, "native claims collided")

    controls = {}
    original = json.loads(results[0].read_bytes())
    for name, change, expected in (
        ("smoke", {"smoke": True}, "smoke capture"),
        ("partial", {"status": "UNKNOWN", "error": "control transport failure"}, "control transport failure"),
        ("unregistered-controls", {"planned": original["planned"][1:]}, "incomplete native controls"),
    ):
        path = out / f"{name}.json"
        path.write_text(json.dumps({**original, **change}))
        refused = ingest(path, out / f"{name}.jsonl")
        require(refused["rows_projected"] == refused["frames_emitted"] == 0
                and len(refused["refused"]) == 1 and expected in refused["refused"][0]["reason"],
                f"{name} did not refuse before publishing a tuple")
        controls[name] = expected
    digest_original = native.file_sha256
    response = Path(original["window"]) / "attempt-01/RESPONSE.json"

    def mismatched_digest(path):
        return "0" * 64 if path == response else digest_original(path)

    with patch.object(native, "file_sha256", mismatched_digest):
        try:
            native.native_rows(results[0])
        except native.ProjectionError as exc:
            require("artifact mismatch: attempt-01/RESPONSE.json" in str(exc), str(exc))
            controls["response-digest"] = "raw response digest mismatch"
        else:
            raise ValueError("native response digest mismatch projected")
    return rows, controls


def replay(results, research, out):
    rows, refusals = native_rows(results, out)
    weights, = {row["extra"]["inputs"]["model_sha256"] for row in rows.values()}
    model, = {row["extra"]["inputs"]["model_path"] for row in rows.values()}
    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]
    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    source_path = research / "scripts/kernel_rnd/autokernel/loop"
    require(Path(actors.__file__).resolve() == source_path / "actors.py"
            and Path(belief_context.__file__).resolve() == source_path / "belief_context.py",
            "wrong Research consumer checkout")
    index, alarm, ledger = (out / name for name in ("index.yaml", "alarm.yaml", "ledger.jsonl"))
    index.write_text("[]\n")
    alarm.write_text(f"backend: file\nfile:\n  path: {json.dumps(str(out / 'alarms.jsonl'))}\n")
    config = belief_context.BeliefConfig(root=ROOT, ledger=ledger, index=index, alarm_config=alarm,
                                        known_good=out / "known-good.json", alarm_state=out / "alarm-state.json")

    def run_child(argv, **kwargs):
        # The row verifies the source snapshot hash before the replay. This override is local to
        # the sealed copy and does not alter the live consumer's checkout policy.
        require(Path(argv[1]) == VIDYA / "loop_beliefs.py" and argv[2] == "prepare",
                "unexpected planner reader invocation")
        env = {**os.environ, "VIDYA_READ_LOG": str(out / "reads.jsonl"),
               "ALARM_BACKEND": "file", "ALARM_FILE_PATH": str(out / "alarms.jsonl")}
        return subprocess.run([argv[0], "-IB", *argv[1:], "--allow-stale-reader"], env=env, **kwargs)

    seen = {}

    def before_backend(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        seen[context["label"]] = (belief, prompt)
        return actors.Abstain(reason="thinking-budget diagnostic canary"), sorted(rows)

    contexts = (("exact", "cpu", weights), ("wrong-cpu-weights", "cpu", "0" * 64),
                ("wrong-backend", "gpu", weights), ("missing-weights", "cpu", None))
    with (patch.object(actors.AgentPlanner, "_proposal_from_agent", before_backend),
          patch.object(actors, "_run_agent", side_effect=RuntimeError("actor backend reached"))):
        for label, backend, digest in contexts:
            target_model = {"path": model}
            if digest is not None:
                target_model["sha256"] = digest
            context = {"label": label, "current_regime": {"model": target_model, "backend": backend, "quant": "Q8_0"}}
            context_root = out / label
            workspace = context_root / "lane"
            workspace.mkdir(parents=True)
            planner = actors.AgentPlanner(workspace=workspace,
                                          belief=replace(config, known_good=context_root / "known-good.json"),
                                          belief_runner=run_child)
            require(isinstance(planner.propose(context), actors.Abstain), "planner did not stop at prompt boundary")

    ids = set(rows)
    require(set(seen) == {label for label, _, _ in contexts}, "missing planning controls")
    ready, prompt = seen["exact"]
    evidence = ready.evidence
    require(ready.ledger_state["ledger_path"] == str(ledger)
            and ready.ledger_state["frame_count"] == len(ids) * 3
            and ready.section in prompt and ready.answer["reader_checkout_check"] is False,
            "wrong pinned isolated read or prompt")
    require(set(evidence["claim_ids"]) == ids and all(
        claim["tier"] == "target" and claim["grade"] == "Judged/Located"
        and claim["claim_id"] in ready.section for claim in evidence["claims"]),
        "exact CPU/weight planning evidence absent or wrong grade")
    require(evidence["tried_index_count"] == len(ids) and "UNKNOWN" in ready.section
            and all(arm in ready.section for arm in ("budget-omitted", "budget-8", "thinking-disabled")),
            "planner lacks do-not-repeat history, arms or censoring")

    reliance = {}
    receipt_bindings = {}
    for label, _, _ in contexts:
        answer, prompt = seen[label]
        if label != "exact":
            require(not (answer.section or answer.evidence["claims"] or answer.evidence["tried_index"]),
                    f"unrelated context {label} received native claims")
        context_root = out / label
        receipt_path = context_root / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
        receipt_bytes = receipt_path.read_bytes()
        line, = receipt_bytes.splitlines()
        receipt = json.loads(line)
        require(receipt["call"]["workspace"] == str(context_root / "lane")
                and receipt["call"]["prompt_sha256"] == sha256(prompt.encode()).hexdigest()
                and receipt["target"] == answer.target
                and receipt["ledger_state_digest"] == answer.ledger_state_digest,
                f"planner receipt custody drift for {label}")
        rely = receipt["reliance"]
        expected = belief_context.reliance(sorted(ids), sorted(ids) if label == "exact" else [], [])
        require(rely == expected, f"proposal reliance drift for {label}")
        reliance[label] = rely
        receipt_bindings[label] = {
            "receipt_id": receipt["receipt_id"], "sha256": sha256(receipt_bytes).hexdigest(),
        }

    excerpt = out / "planner-context.txt"
    excerpt.write_text(ready.section + "\n")
    return {
        "consumer": config.consumer, "native_rows": len(ids), "native_report_count": len(results),
        "visible_count": len(evidence["claims"]), "history_count": evidence["tried_index_count"],
        "refusal_control_count": len(refusals), "exclusion_count": len(contexts) - 1,
        "refusal_count": 0, "reader_checkout_check": False, "model_sha256": weights,
        "native_time_basis": "registered-row-day",
        "refusals": refusals, "reliance": reliance, "receipt_bindings": receipt_bindings,
        "actor_backend_called": False,
        "excerpt_sha256": sha256(excerpt.read_bytes()).hexdigest(),
    }
