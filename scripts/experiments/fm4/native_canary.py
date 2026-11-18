#!/usr/bin/env python3
"""Check a prospective FM-4 Claude dispatch through the oracle and Vidya planner."""

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


def _selected_claim(state_dir, native):
    ledger = Ledger(state_dir / "ledger.jsonl")
    index = state_dir / "intake_index.yaml"
    index.write_text("[]\n", encoding="utf-8")
    stamp = datetime.now(timezone.utc).isoformat()
    with ledger.write_lock():
        report = ingest_sources.ingest(ledger, adapter.SOURCE_KIND, [Path(native["path"])],
                                       as_of=stamp)
    if report["refused"] or report["rows_projected"] != 1 or report["frames_emitted"] != 3:
        raise ValueError(f"Vidya rejected the acceptance bundle: {report['refused'] or report}")

    # Keep alarm delivery file-only even when the caller's environment configures paging.
    alarm_api = SimpleNamespace(
        load_config=lambda _: {"backend": "file", "file": {"path": str(state_dir / "alarms.jsonl")}},
        raise_alarm=alarm_channel.raise_alarm, clear_alarm=alarm_channel.clear_alarm,
    )
    target = {"scope": "lineup", "stack_regime": "fm4"}
    answer = loop_beliefs.prepare(
        adapter.PLANNER_CONSUMER, target, ledger=ledger.path, index_path=index,
        known_good=state_dir / "known-good.json", read_log=state_dir / "reads.jsonl",
        alarm_state=state_dir / "alarm-state.json", alarm_config=state_dir / "alarms.jsonl",
        alarm_api=alarm_api,
    )
    if answer["status"] != "ready":
        raise ValueError(f"Vidya planning context refused: {answer['reason']} {answer['detail']}")
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--child", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--task-id", required=True, help="task identity obtained from the dispatch")
    parser.add_argument("--acceptance", type=Path, required=True, help="record emitted by run_gate.py")
    parser.add_argument("--state-dir", type=Path, required=True, help="new directory for isolated Vidya state")
    args = parser.parse_args(argv)
    try:
        receipt = run(args.child, args.parent, args.task_id, args.acceptance, args.state_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"FM-4 canary refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
