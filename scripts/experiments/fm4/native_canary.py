#!/usr/bin/env python3
"""Check FM-4 selected-gate or native Codex dispatch observations in Vidya."""

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts" / "vidya"), str(ROOT)]

import ingest_sources  # noqa: E402
import loop_beliefs  # noqa: E402
from adapters import fm4_gate_acceptance as adapter  # noqa: E402
from ledger import Ledger  # noqa: E402
from scripts.coordination import alarm_channel, session_oracle  # noqa: E402


def _sha256(path):
    if not path.is_file():
        raise ValueError(f"expected a regular transcript file: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _accepted_assessment(child, parent, task_id, native):
    record = native["acceptance"]
    row = session_oracle.assess(child, parent_path=parent, task_id=task_id,
                                acceptance_paths=[Path(native["path"])])
    signals = row["signals"]
    signal = signals.get("task_acceptance", {})
    disposition = signal.get("disposition", "missing")
    if disposition != "applied":
        raise ValueError(f"oracle did not apply the prospective acceptance: {disposition}")

    result = signals.get("parent_result", {})
    identity = {"parent_session_id": result.get("session_id"),
                "dispatch_tool_use_id": result.get("tool_use_id"),
                "child_agent_id": result.get("agent_id"), "task_id": task_id}
    if (row.get("harness") != "claude" or row.get("path") != str(child)
            or row.get("session_id") != identity["parent_session_id"]
            or signals.get("parent_join") != "matched" or result.get("path") != str(parent)
            or signal.get("caller_task_id") != task_id or signal.get("identity") != identity
            or any(record[key] != value for key, value in identity.items())):
        raise ValueError("oracle acceptance did not bind the matched dispatch and independent task ID")

    expected_source = {"path": native["path"], "sha256": native["sha256"],
                       "disposition": "verified", "record": record}
    if signal.get("sources") != [expected_source]:
        raise ValueError("oracle acceptance did not verify the supplied record and digest")
    verdict = "success" if record["gate_result"] == "pass" else "failure"
    if row.get("verdict") != verdict:
        raise ValueError("oracle verdict disagrees with the verified gate result")
    return identity, verdict


def _ingest(state_dir, path, count):
    ledger = Ledger(state_dir / "ledger.jsonl")
    index = state_dir / "intake_index.yaml"
    index.write_text("[]\n", encoding="utf-8")
    stamp = datetime.now(timezone.utc).isoformat()
    with ledger.write_lock():
        report = ingest_sources.ingest(ledger, adapter.SOURCE_KIND, [path], as_of=stamp)
    if report["refused"] or report["rows_projected"] != count or report["frames_emitted"] != 3 * count:
        raise ValueError(f"Vidya rejected the FM-4 bundle: {report['refused'] or report}")
    return ledger.path, index


def _planning_context(state_dir, ledger, index, consumer):
    # Keep alarm delivery file-only even when the caller's environment configures paging.
    alarm_api = SimpleNamespace(
        load_config=lambda _: {"backend": "file", "file": {"path": str(state_dir / "alarms.jsonl")}},
        raise_alarm=alarm_channel.raise_alarm, clear_alarm=alarm_channel.clear_alarm,
    )
    target = {"scope": "lineup", "stack_regime": "fm4"}
    known_good = "known-good.json" if consumer == adapter.PLANNER_CONSUMER else f"{consumer}.known-good.json"
    answer = loop_beliefs.prepare(
        consumer, target, ledger=ledger, index_path=index,
        known_good=state_dir / known_good, read_log=state_dir / "reads.jsonl",
        alarm_state=state_dir / "alarm-state.json", alarm_config=state_dir / "alarms.jsonl",
        alarm_api=alarm_api,
    )
    if answer["status"] != "ready":
        raise ValueError(f"Vidya planning context refused: {answer['reason']} {answer['detail']}")
    return answer


def _selected_claim(state_dir, native):
    ledger, index = _ingest(state_dir, Path(native["path"]), 1)
    answer = _planning_context(state_dir, ledger, index, adapter.PLANNER_CONSUMER)
    evidence = answer["evidence"]
    claims = [row for row in evidence["claims"] if row.get("source_kind") == adapter.SOURCE_KIND]
    digest = native["sha256"]
    claim_id = f"clm_{adapter.SOURCE_KIND}:{digest}"
    locator = f"{native['path']}#sha256={digest}"
    expected = {"claim_id": claim_id, "locator": locator, "tier": "harness", "not_evidence": True,
                "value": int(native["acceptance"]["gate_result"] == "pass"),
                "unit": "gate_pass_indicator"}
    if (len(claims) != 1 or any(claims[0].get(key) != value for key, value in expected.items())
            or claim_id not in evidence["section"] or claim_id in evidence["claim_ids"]):
        raise ValueError("Vidya planning context did not select the exact gate observation")
    return claims[0], answer["ledger_state"], answer["ledger_state_digest"]


def run(child, parent, task_id, acceptance, state_dir):
    parameters = inspect.signature(session_oracle.assess).parameters
    if not {"task_id", "acceptance_paths"} <= parameters.keys():
        raise ValueError("the D9 oracle acceptance API is required; see proposed/fm4-acceptance-consumption/README.md")

    child, parent = child.resolve(strict=True), parent.resolve(strict=True)
    if child.samefile(parent):
        raise ValueError("child and parent must be distinct transcript files")
    state_dir = state_dir.absolute()
    if state_dir.exists() or state_dir.is_symlink():
        raise ValueError(f"state directory must be new: {state_dir}")
    inputs = {label: {"path": str(path), "sha256": _sha256(path)}
              for label, path in (("child", child), ("parent", parent))}
    (native,) = adapter.native_rows(acceptance)
    identity, verdict = _accepted_assessment(child, parent, task_id, native)
    if any(_sha256(Path(item["path"])) != item["sha256"] for item in inputs.values()):
        raise ValueError("a transcript changed during oracle assessment")

    state_dir.mkdir(mode=0o700)
    claim, ledger_state, state_digest = _selected_claim(state_dir.resolve(), native)
    if adapter.native_rows(acceptance) != (native,):
        raise ValueError("the acceptance bundle changed during Vidya ingest or retrieval")
    if any(_sha256(Path(item["path"])) != item["sha256"] for item in inputs.values()):
        raise ValueError("a transcript changed during Vidya ingest or retrieval")
    inputs["acceptance"] = {"path": native["path"], "sha256": native["sha256"],
                            "execution_sha256": native["acceptance"]["evidence"]["sha256"]}
    return {"schema": "fm4.native_canary.v1", "inputs": inputs, "identity": identity,
            "gate_result": native["acceptance"]["gate_result"], "oracle_verdict": verdict,
            "oracle_disposition": "applied", "consumer": adapter.PLANNER_CONSUMER,
            "selected_claim": claim, "ledger_state": ledger_state, "ledger_state_digest": state_digest}


def run_codex_dispatch(replay, state_dir):
    """Replay a completed census selection through the real coordination planner reader."""
    natives = adapter.native_rows(replay)
    if not natives or any("receipt" not in row for row in natives):
        raise ValueError("a native Codex dispatch replay bundle is required")
    state_dir = state_dir.absolute()
    state_dir.mkdir(mode=0o700)
    ledger, index = _ingest(state_dir, replay, len(natives))
    frames = [record.frame for record in Ledger(ledger).read_all()]
    gate_claim_count = sum(frame["assertion"].get("metric") == "fm4_selected_gate_pass" for frame in frames)
    if gate_claim_count or any(frame["pubinfo"]["authority_scope"] != adapter.DISPATCH_AUTHORITY
                               for frame in frames):
        raise ValueError("Vidya did not preserve native dispatch authority in the canary ledger")
    answer = _planning_context(state_dir, ledger, index, adapter.PLANNER_CONSUMER)
    evidence = answer["evidence"]
    claims = {row["claim_id"]: row for row in evidence["claims"]}
    selected = []
    for row in natives:
        receipt = row["receipt"]
        pair = receipt["pair_id"]
        digest = row["sha256"]
        claim_id = f"clm_{adapter.SOURCE_KIND}:{digest}:{pair}"
        expected = {"source_kind": adapter.SOURCE_KIND, "tier": "harness", "grade": "Judged/Located",
                    "locator": f"{row['result_path']}#sha256={digest}&pair_id={pair}",
                    "not_evidence": True, "value": 1, "unit": adapter.DISPATCH_UNIT}
        claim = claims.get(claim_id, {})
        if (any(claim.get(key) != value for key, value in expected.items())
                or claim_id not in evidence["section"] or claim_id in evidence["claim_ids"]
                or receipt["task_outcome"] is not None):
            raise ValueError(f"Vidya planning context did not select the exact dispatch observation for {pair}")
        selected.append({"receipt": receipt, "claim": claim})
    if len(evidence["claims"]) != len(selected) or adapter.DISPATCH_LIMITATION not in evidence["section"]:
        raise ValueError("Vidya planning context included extra claims or lost the task-outcome limitation")
    other = _planning_context(state_dir, ledger, index, "autokernel.planner")
    if other["evidence"]["claims"] or other["ledger_state_digest"] != answer["ledger_state_digest"]:
        raise ValueError("Vidya planning context leaked dispatch observations to an unrelated consumer")
    if any(read.get("read_log_error") or read.get("known_good_error") for read in (answer, other)):
        raise ValueError("Vidya planning context did not retain its read or freshness record")
    if adapter.native_rows(replay) != natives:
        raise ValueError("the dispatch replay bundle changed during Vidya ingest or retrieval")
    return {"schema": "fm4.codex_dispatch.canary.v1", "consumer": adapter.PLANNER_CONSUMER,
            "census": {"path": natives[0]["result_path"], "sha256": natives[0]["sha256"]},
            "selected": selected, "task_outcome": None, "task_gate_claim_count": gate_claim_count,
            "excluded_consumer": other["consumer"],
            "ledger_state": answer["ledger_state"], "ledger_state_digest": answer["ledger_state_digest"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--child", type=Path)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--task-id", help="task identity obtained from the dispatch")
    parser.add_argument("--acceptance", type=Path, help="record emitted by run_gate.py")
    parser.add_argument("--dispatch-replay", type=Path, help="read-only native Codex census replay bundle")
    parser.add_argument("--state-dir", type=Path, required=True, help="new directory for isolated Vidya state")
    args = parser.parse_args(argv)
    gate_args = (args.child, args.parent, args.task_id, args.acceptance)
    if args.dispatch_replay:
        if any(arg is not None for arg in gate_args):
            parser.error("--dispatch-replay is exclusive with the selected-gate arguments")
    elif any(arg is None for arg in gate_args):
        parser.error("use --dispatch-replay or supply --child, --parent, --task-id and --acceptance")
    try:
        receipt = (run_codex_dispatch(args.dispatch_replay, args.state_dir) if args.dispatch_replay
                   else run(*gate_args, args.state_dir))
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"FM-4 canary refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
