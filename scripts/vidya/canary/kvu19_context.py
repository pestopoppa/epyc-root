"""Replay a complete KVU19a2 native run through AutoKernel planning in scratch."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
VIDYA = ROOT / "scripts/vidya"
SCRATCH_ROOT = Path("/mnt/raid0/llm/tmp")
SIDECAR = "kvu19a2_native.beliefs.jsonl"
SOURCE = "kvu19a2-native"
SCOPE = {"backend": "gpu", "device": "gfx90a"}
MODEL = "Qwen3.8-27B-Q8_0.gguf"
CPU_MODEL = "Qwen3.6-35B-A3B-Q4_K_M.gguf"
LIMITS = ("scoped by device only, no model", "not about this model",
          "not evidence for a proposal")
MATRIX = tuple((case, arm, repeat) for case in (78, 80) for repeat in range(1, 6)
               for arm in (("base", "candidate") if repeat % 2 else ("candidate", "base")))


def require(condition, detail):
    if not condition:
        raise ValueError(detail)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def objects(records):
    rows = [json.loads(record) for record in records if record.strip()]
    require(all(isinstance(row, dict) for row in rows), "expected JSON objects")
    return rows


def completed_capture(sidecar):
    """Check completion external to the sealed sidecar before attempting ingestion."""
    require(sidecar.name == SIDECAR, f"--native must name {SIDECAR}")
    result_path = sidecar.with_name("result.json")
    native_path = sidecar.with_name("kvu19a2-native.json")
    require(not sidecar.with_name("partial-result.json").exists(), "partial KVU19a2 run")
    require(result_path.is_file(), "completed KVU19a2 result.json is required")
    result, = objects([result_path.read_text()])
    require(result.get("schema") == "kvu19a2.repeat-diagnostic.v1"
            and result.get("smoke") is False and result.get("measurement") is False,
            "expected a non-smoke KVU19a2 model-free diagnostic")
    runs = result.get("runs")
    require(isinstance(runs, list) and len(runs) == len(MATRIX), "expected 20 completed launches")
    native, = objects([native_path.read_text()])
    observations = native.get("observations")
    rows = objects(sidecar.read_text().splitlines())
    run_id = result.get("run_id")
    require(isinstance(run_id, str) and bool(run_id) and native.get("run_id") == run_id
            and native.get("schema") == "kvu19a2.native-run.v1"
            and isinstance(observations, list) and len(observations) == len(MATRIX)
            and len(rows) == len(MATRIX), "completion record must bind 20 native observations and rows")
    native_digest = sha(native_path)
    for i, ((case, arm, repeat), run, obs, row) in enumerate(zip(MATRIX, runs, observations, rows)):
        require(isinstance(run, dict) and isinstance(obs, dict) and isinstance(row.get("extra"), dict),
                f"malformed launch {i}")
        label = f"FA_CASE={case},repeat={repeat}"
        require((run.get("case"), run.get("arm"), run.get("repeat")) == (case, arm, repeat)
                and (obs.get("case"), obs.get("arm")) == (label, arm),
                f"launch matrix differs at {label} / {arm}")
        require(run.get("rc") == obs.get("rc") == 0 and obs.get("observed") is True
                and obs.get("cleanup_verified") is True and run.get("output_sha256")
                and run["output_sha256"] == obs.get("raw_sha256")
                and obs.get("applicability") == SCOPE and obs.get("mapping_sample_present") is True
                and all(run.get(key) == obs.get(key) for key in (
                    "pid", "birth_ticks", "started_at", "ended_at", "samples", "input_hashes", "log_sha256")),
                f"incomplete or unscoped capture at {label} / {arm}")
        require(row.get("run_id") == run_id and row.get("results_path") == str(native_path)
                and row.get("results_sha256") == native_digest and row["extra"].get("index") == i,
                f"sidecar does not bind the original launch at {label} / {arm}")
    return rows, (sidecar, native_path, result_path)


def ingest(sidecar, ledger):
    done = subprocess.run(
        [sys.executable, "-B", str(VIDYA / "cli.py"), "--ledger", str(ledger), "--json", "ingest",
         SOURCE, "--path", str(sidecar), "--as-of", datetime.now(timezone.utc).isoformat(), "--only-new"],
        cwd=ROOT, check=True, capture_output=True, text=True, timeout=120,
    )
    report = json.loads(done.stdout)
    count = len(MATRIX)
    require(report["rows_projected"] == count and report["frames_emitted"] == count * 3
            and report["units_projected"] == 1 and not (report["refused"] or report["declined"] or report["missing"]),
            f"incomplete or refused native ingest: {report}")
    return {"rows": count, "frames": count * 3, "refused": 0}


def replay(research, out, ledger):
    sys.path[:0] = [str(research), str(research / "scripts/kernel_rnd")]
    from scripts.kernel_rnd.autokernel.loop import actors, belief_context

    consumer = research / "scripts/kernel_rnd/autokernel/loop"
    sources = (Path(actors.__file__).resolve(), Path(belief_context.__file__).resolve())
    require(sources == (consumer / "actors.py", consumer / "belief_context.py"),
            "AutoKernel consumer came from a different checkout")
    index = out / "index.yaml"
    index.write_text("[]\n")
    alarm = out / "alarm.yaml"
    alarm.write_text(f"backend: file\nfile:\n  path: {json.dumps(str(out / 'alarms.jsonl'))}\n")
    config = belief_context.BeliefConfig(root=ROOT, ledger=ledger, index=index,
                                         known_good=out / "gpu-known-good.json", alarm_config=alarm,
                                         alarm_state=out / "alarm-state.json")
    captured = {}
    child_reads = []

    def run_child(argv, **kwargs):
        if argv[1:3] == [str(VIDYA / "loop_beliefs.py"), "prepare"]:
            child_reads.append(argv[3:])
        env = {**os.environ, "VIDYA_READ_LOG": str(out / "reads.jsonl")}
        return subprocess.run([argv[0], "-B", *argv[1:]], env=env, **kwargs)

    def stop_before_agent(self, prompt, backend, env, context, *, belief):
        belief_context.require_ready(belief)
        target = context["current_regime"]["backend"]
        captured[target] = (belief, prompt)
        ids = captured["gpu"][0].evidence["not_evidence_claim_ids"]
        return actors.Abstain(reason="KVU19 planning-context canary"), ids

    with (patch.object(actors.AgentPlanner, "_proposal_from_agent", stop_before_agent),
          patch.object(actors, "_run_agent", side_effect=RuntimeError("canary reached the actor backend"))):
        for backend, model, quant in (("gpu", MODEL, "Q8_0"), ("cpu", CPU_MODEL, "Q4_K_M")):
            context = {"current_regime": {"model": {"path": model}, "quant": quant, "backend": backend}}
            target_config = replace(config, known_good=out / f"{backend}-known-good.json")
            planner = actors.AgentPlanner(workspace=out / backend, belief=target_config, belief_runner=run_child)
            require(isinstance(planner.propose(context), actors.Abstain), f"planner did not stop for {backend}")
    require(len(child_reads) == 2 and set(captured) == {"gpu", "cpu"}, "expected two real prepare child reads")
    receipts = out / actors.ACTOR_REPLY_DIR / belief_context.RECEIPT_LOG
    return config.consumer, captured, objects(receipts.read_text().splitlines()), sources


def check_reads(captured, receipts, rows, ledger):
    gpu, gpu_prompt = captured["gpu"]
    cpu, _ = captured["cpu"]
    state = gpu.ledger_state
    require(state["ledger_path"] == str(ledger) and state["frame_count"] == len(MATRIX) * 3
            and cpu.ledger_state["ledger_path"] == str(ledger)
            and cpu.ledger_state["head_hash"] == state["head_hash"], "reader used an unexpected ledger state")
    for ready, expected in ((gpu, (MODEL, "Q8_0", "gpu", "gfx90a")),
                            (cpu, (CPU_MODEL, "Q4_K_M", "cpu", "epyc-9655"))):
        target, = ready.answer["targets"]
        require(tuple(target[k] for k in ("model_file", "quant", "backend", "device")) == expected,
                f"reader did not use the requested {expected[2]} target")
    evidence = gpu.evidence
    claims = evidence["claims"]
    ids = evidence["not_evidence_claim_ids"]
    native_by_id = {f"clm_{row['measurement_id']}": row for row in rows}
    require(claims and set(ids) == {claim["claim_id"] for claim in claims}
            and evidence["tiers"]["host"] == len(MATRIX)
            and not (evidence["claim_ids"] or evidence["nonempty_target"] or evidence["tried_index"]
                     or any(evidence["flagged"].values())),
            "expected host-tier context without proposal evidence")
    for claim in claims:
        row = native_by_id[claim["claim_id"]]
        require((claim["source_kind"], claim["grade"], claim["tier"], claim["status"], claim["reps"])
                == (SOURCE, "Judged/Located", "host", "verified", 1)
                and claim["not_evidence"] and not claim["model_file"] and row["claim"] in gpu.section,
                f"unexpected planner claim {claim['claim_id']}")
    require(gpu.section in gpu_prompt and all(wording in gpu.section for wording in LIMITS),
            "device-only limitations missing from the planner prompt")
    require(not (cpu.section or cpu.evidence["claims"] or cpu.evidence["claim_ids"])
            and cpu.evidence["reasons"] == ["no_applicable_claims"], "CPU target admitted a GPU diagnostic")
    gpu_receipt, cpu_receipt = receipts
    for receipt, reason in ((gpu_receipt, "host_tier"), (cpu_receipt, "not_presented")):
        require(receipt["reliance"] == {"declared": ids, "accepted": [], "rejected": [
            {"claim_id": claim_id, "reason": reason} for claim_id in ids]},
            f"planner did not reject attempted reliance as {reason}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, required=True, help=f"producer's {SIDECAR}")
    parser.add_argument("--research", type=Path, required=True, help="epyc-inference-research checkout")
    parser.add_argument("--scratch", type=Path, required=True, help="parent directory for a private canary run")
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    if SCRATCH_ROOT not in scratch.parents:
        parser.error(f"--scratch must be a subdirectory of {SCRATCH_ROOT}")
    sidecar = args.native.resolve()
    try:
        rows, inputs = completed_capture(sidecar)
        input_digests = {str(path): sha(path) for path in inputs}
    except (OSError, ValueError) as exc:
        parser.error(f"--native: {exc}")
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="kvu19-context-", dir=scratch))
    ledger = out / "ledger.jsonl"
    report = ingest(sidecar, ledger)
    before = sha(ledger)
    consumer, captured, receipts, sources = replay(args.research.resolve(), out, ledger)
    check_reads(captured, receipts, rows, ledger)
    require(input_digests == {str(path): sha(path) for path in inputs} and sha(ledger) == before,
            "native input or scratch ledger changed during replay")

    gpu, _ = captured["gpu"]
    cpu, _ = captured["cpu"]
    excerpt = out / "planner-context.txt"
    excerpt.write_text(gpu.section + "\n")
    receipt = {
        "schema": "epyc.vidya.kvu19a2_planning_canary.v1", "status": "passed",
        "native_inputs_sha256": input_digests, "ingest": report, "consumer": consumer,
        "entry_point": "AgentPlanner.propose -> belief_context.prepare -> loop_beliefs.py prepare",
        "stop_boundary": "AgentPlanner._proposal_from_agent intercepted before the backend call",
        "ledger": gpu.ledger_state, "ledger_sha256": before,
        "reader_checkout": gpu.answer.get("reader_checkout"),
        "sources_sha256": {str(p): sha(p) for p in (*sources, VIDYA / "loop_beliefs.py",
                                                   VIDYA / "adapters/kvu19a2_native.py")},
        "gpu_target": gpu.answer["targets"], "claims_shown": gpu.evidence["claims"],
        "cpu_target": cpu.answer["targets"], "cpu_exclusion": cpu.evidence["reasons"],
        "actor_receipts": [{"receipt_id": row["receipt_id"], "reliance": row["reliance"]} for row in receipts],
        "rendered_excerpt": excerpt.name, "rendered_excerpt_sha256": sha(excerpt),
        "scope": "Model-free GPU diagnostics. Scratch ledger, no inference, model transfer or promotion.",
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
