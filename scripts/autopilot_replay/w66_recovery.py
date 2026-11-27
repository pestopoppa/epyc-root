#!/usr/bin/env python3
"""Replay saved OpenCode traces with the orchestrator detectors. Never run recorded commands."""

from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "06b010e1361768b7d1d65b83cb4428df28a0d1c3"
SOURCE_ARCHIVE = "artifacts/analysis/27b-q38fn-full-tools-repeat-20261127"
RUNTIME_ORIGIN = Path("/mnt/raid0/llm/tmp/ws58-27b-q38fn-repeat-20261127/runtime")
LAYOUT_SHA256 = "11bcc1151a583761818416c62f01bb4850d5daf91f66a50e8ef04ccb68397afd"
QUALITY = "quality-final-closed-01/QUALITY.json"
PAID = "report-data-final-closed-01/PAID-CALLS.json"
WARNING_AUDIT = "tool-warning-v2-owner-acceptance-prep/OWNER-ACCEPTANCE-DRAFT.json"
INSPECTION_LIMITS = {"primary": 80, "longer_inspection_run": 120, "exact_repeat_only": None}
INSPECTION = {"read", "grep", "glob", "list"}
EXECUTION = {"shell", "execute", "bash"}
CHECK = re.compile(r"\bpytest\b|\b(?:py_compile|compileall|unittest|ruff|mypy)\b")
READ_ONLY_SHELL = re.compile(r"^(?:git (?:status|diff|show|log|ls-files)|rg|grep|find|ls|cat|wc|head|tail|nl)\b")
WARNING_TEXT = re.compile(r"Repeated unchanged tool result|Repeated unchanged read", re.I)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


class Evidence:
    def __init__(self, runtime: Path | None):
        self.runtime = runtime
        raw = git(ROOT, "show", f"{SOURCE_COMMIT}:{SOURCE_ARCHIVE}/ARCHIVE-LAYOUT.json.gz")
        layout = gzip.decompress(raw)
        if digest(raw) != LAYOUT_SHA256 and digest(layout) != LAYOUT_SHA256:
            raise ValueError("archive layout digest mismatch")
        inventory = json.loads(layout)
        self.members = {
            str(Path(row["source"]).relative_to(RUNTIME_ORIGIN)): row
            for row in inventory["members"] if Path(row["source"]).is_relative_to(RUNTIME_ORIGIN)
        }
        self.case_paths = {}
        for row in inventory["members"]:
            if row["group"] == "cases" and row["source"].endswith("/case.json"):
                key = f"cases/{row['sha256']}/case.json"
                self.members[key] = row
                self.case_paths[row["sha256"]] = key
        self.shards = {row["archive"]: row["stored_sha256"] for row in inventory["shards"]}
        self.cache: dict[str, bytes] = {}

    def prefetch(self, paths: set[str]) -> None:
        shards: dict[str, dict[str, str]] = {}
        for path in sorted(paths):
            row = self.members[path]
            if path in self.cache or (self.runtime and (self.runtime / path).is_file()):
                continue
            shards.setdefault(row["archive"], {})[row["member"]] = path
        for archive, wanted in shards.items():
            raw = git(ROOT, "show", f"{SOURCE_COMMIT}:{SOURCE_ARCHIVE}/{archive}")
            if digest(raw) != self.shards[archive]:
                raise ValueError(f"archive shard digest mismatch: {archive}")
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r|gz") as stream:
                for member in stream:
                    if member.name not in wanted:
                        continue
                    path = wanted.pop(member.name)
                    source = stream.extractfile(member)
                    if source is None:
                        raise ValueError(f"archive member is not a regular file: {path}")
                    self.cache[path] = source.read()
            if wanted:
                raise ValueError(f"archive members missing: {sorted(wanted.values())}")

    def read(self, path: str, expected_sha: str | None = None) -> bytes:
        self.prefetch({path})
        data = self.cache[path] if path in self.cache else (self.runtime / path).read_bytes()
        actual = digest(data)
        if actual != self.members[path]["sha256"] or (expected_sha and actual != expected_sha):
            raise ValueError(f"source digest mismatch: {path}")
        return data

    def json(self, path: str, expected_sha: str | None = None):
        return json.loads(self.read(path, expected_sha))

    def link(self, path: str) -> dict:
        row = self.members[path]
        return {"path": path, "sha256": row["sha256"], "archive": row["archive"], "member": row["member"]}


def relative(path: str) -> str:
    return str(Path(path).relative_to(RUNTIME_ORIGIN))


def load_detectors(repo: Path):
    path = repo / "src/trace/l2/loop_detectors.py"
    spec = importlib.util.spec_from_file_location("w66_orchestrator_loop_detectors", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, {
        "path": str(path.relative_to(repo)), "sha256": digest(path.read_bytes()),
        "commit": git(repo, "rev-parse", "HEAD").decode().strip(),
    }


@dataclass
class Tool:
    name: str
    args: dict
    result_sha256: str | None
    status: str
    inspected: bool
    check_exit: int | None
    warning: bool


@dataclass
class Turn:
    tools: list[Tool]
    end_ms: int | None
    changes: list[str] | None


def session_turns(session: dict, started_at: float, ended_at: float, editable_paths: set[str]) -> list[Turn]:
    turns = []
    for message in session["messages"]:
        if message["type"] != "assistant" or not started_at * 1000 <= message["time"]["created"] <= ended_at * 1000:
            continue
        tools = []
        for part in message.get("content", []):
            if part["type"] != "tool":
                continue
            state = part["state"]
            args = state.get("input") or {}
            command = args.get("command", "") if isinstance(args, dict) else ""
            is_check = part["name"] in EXECUTION and bool(CHECK.search(command))
            output = state.get("content") or state.get("error")
            status = state["status"]
            observed = output is not None and status in {"completed", "error"}
            result = json.dumps([status, output], sort_keys=True, ensure_ascii=False) if observed else None
            tools.append(Tool(
                part["name"], args, digest(result.encode()) if result else None, status,
                part["name"] in INSPECTION or (
                    part["name"] in EXECUTION and not is_check and bool(READ_ONLY_SHELL.match(command))
                ),
                state.get("metadata", {}).get("exit") if is_check else None,
                bool(result and WARNING_TEXT.search(result)),
            ))
        snapshot = message.get("snapshot")
        files = snapshot.get("files") if isinstance(snapshot, dict) else None
        changes = [path for path in files if path in editable_paths] if files is not None else None
        turns.append(Turn(tools, message["time"].get("completed"), changes))
    return turns


def inspect_recovery_trace(turns: list[Turn], detectors, started_at: float, wall_budget: float) -> dict:
    tools = [tool for turn in turns for tool in turn.tools]
    units = [detectors.CallUnit(tool.name, tool.args) for tool in tools]
    exempt = detectors.test_after_edit_exempt(units)
    repeated = detectors.repeated_calls(units, exempt)
    stream, kept = detectors.action_stream(units, exempt)
    tokens = detectors.regex_tokenize(stream)
    period = detectors.first_period_fire(tokens)
    lines = detectors.first_line_fire(stream)
    # Normalized line detection is available as a separate signal. Multiline argument strings
    # invalidate simple call attribution for line detections, so keep the qualifying line index.
    normalized = detectors.first_line_fire(stream, normalize=True)
    period_call = None
    if period is not None:
        fire_chars = sum(len(token) for token in tokens[:period])
        # action_stream joins call bodies with a newline. Tokenization may span that separator.
        remaining = fire_chars
        for index in kept:
            remaining -= len(units[index].body()) + 1
            if remaining <= 0:
                period_call = index + 1
                break

    stable = deque(maxlen=32)
    changes = []
    checks = []
    advisories = dict.fromkeys(INSPECTION_LIMITS)
    uninterrupted_inspections = 0
    unknown_snapshots = 0
    call = 0
    for turn in turns:
        if turn.changes is None:
            unknown_snapshots += 1
        for tool in turn.tools:
            call += 1
            if tool.check_exit is not None:
                checks.append({"call": call, "exit": tool.check_exit})
            if tool.inspected and tool.result_sha256 and not exempt[call - 1]:
                stable.append((units[call - 1].key, tool.result_sha256))
                uninterrupted_inspections += 1
            else:
                stable.clear()
                uninterrupted_inspections = 0
        if turn.changes:
            changes.append({"after_call": call, "paths": turn.changes, "execution_tool_in_turn": any(
                tool.name in EXECUTION for tool in turn.tools),
                "direct_edit_or_write_in_turn": any(tool.name in {"edit", "write"} for tool in turn.tools),
                "completed_at_ms": turn.end_ms})
        if turn.changes is None or turn.changes:
            stable.clear()
            uninterrupted_inspections = 0
            continue
        max_same = max(Counter(stable).values(), default=0)
        if not turn.tools or turn.end_ms is None:
            continue
        elapsed = turn.end_ms / 1000 - started_at
        remaining = max(0.0, wall_budget - elapsed)
        if remaining < 120:
            continue
        exact_repeat = uninterrupted_inspections >= 20 and max_same >= 4
        for name, limit in INSPECTION_LIMITS.items():
            if advisories[name] is not None or not (exact_repeat or (limit and uninterrupted_inspections >= limit)):
                continue
            advisories[name] = {
                "after_call": call,
                "reason": "same_input_and_result" if exact_repeat else "long_inspection_run",
                "same_input_result_in_last_32": max_same,
                "consecutive_inspection_results": uninterrupted_inspections,
                "elapsed_s": round(elapsed, 3), "remaining_phase_wall_s": round(remaining, 3),
                "remaining_charged_tokens": None,
                "action": "offer_one_focused_next_step_keep_tools_enabled",
                "delivered": None, "acted_on": None, "recovered": None,
            }
    return {
        "tool_calls": len(tools),
        "completed_grep_calls": sum(tool.name == "grep" and tool.status == "completed" for tool in tools),
        "first_completed_edit_or_write": next((i for i, tool in enumerate(tools, 1)
                                               if tool.name in {"edit", "write"} and tool.status == "completed"), None),
        "max_identical_inputs": max(Counter(unit.key for unit in units).values(), default=0),
        "first_repeated_call_exempted_metric": repeated[0] + 1 if repeated else None,
        "repeated_calls_after_exemption": len(repeated), "test_after_edit_exemptions": sum(exempt),
        "first_tools_period_token_regex_proxy": period, "first_tools_period_call_regex_proxy": period_call,
        "first_exact_qualifying_line": lines, "first_normalized_qualifying_line": normalized,
        "observed_artifact_changes": changes, "turns_without_file_snapshot": unknown_snapshots,
        "local_check_exit_codes": checks,
        "exported_warning_markers": sum(tool.warning for tool in tools),
        "counterfactual_advisories": advisories,
    }


def path_for(receipt: dict) -> str:
    return relative(receipt["path"])


def observed_attempt(row: dict, evidence: Evidence, paid_calls: list[dict], warning_audit: dict) -> tuple[dict, dict]:
    receipt_path = path_for(row["worker_receipt"])
    worker = Path(receipt_path).parent
    receipt = evidence.json(receipt_path, row["worker_receipt"]["sha256"])
    plan_path = path_for(row["plan"])
    plan = evidence.json(plan_path, row["plan"]["sha256"])
    before = plan.get("charged_chain_before")
    ceiling = row["condition"]["max_chain_generated"]
    charged = row["charged_toward_ceiling"]
    elapsed = row["worker_elapsed_s"]
    condition = row["condition"]["id"]
    profile = row["condition"].get("profile", "")
    ordinal = row["ordinal"]
    accepted = row["accepted"]
    patch_path = str(worker / "candidate/candidate.patch")
    if accepted:
        outcome = "owner_accepted"
    elif row["owner_rejection"]:
        outcome = "owner_rejected"
    elif row["worker_status"] == "interrupted":
        outcome = "interrupted_partial" if row["changed_paths"] else "interrupted_no_patch"
    else:
        outcome = "candidate_without_owner_acceptance"
    trace_kind = "fresh_with_draft" if "artifact-carryover" in profile or "artifact-fresh" in condition else "fresh"
    if receipt.get("resume"):
        trace_kind = "same_session_resume"
    grade_receipts = []
    for item in row["grades"]:
        path = path_for(item["receipt"])
        grade_receipts.append({"source": evidence.link(path), "rc": item["rc"],
                               "withdrawn": item["withdrawn"], "same_patch": item["same_patch"]})
    warning = {"configured": profile in {"read-warning-only-v1", "repeated-tool-warning-v2"}
               or "toolwarn-v2" in condition,
               "triggered": None, "delivered": None, "acted_on": None}
    if condition == warning_audit["condition_id"]:
        audit = warning_audit["plugin_and_raw_evidence"]
        warning.update({"triggered": bool(audit["warning_markers"]),
                        "delivered": bool(audit["wire_requests_with_warning"]),
                        "acted_on": False if not audit["wire_requests_with_warning"] else None,
                        "audit": evidence.link(WARNING_AUDIT)})
    elif warning["configured"]:
        log_path = str(worker / "sandbox/FORM-SERVER.log")
        if log_path in evidence.members:
            log = evidence.read(log_path).decode()
            if "epyc.repeated-read.loaded.v1" in log:
                warning.update({"triggered": "epyc.repeated-read.warning.v1" in log,
                                "audit": evidence.link(log_path)})
    else:
        warning.update({"triggered": False, "delivered": False, "acted_on": False})
    return {
        "condition": condition, "case": row["condition"]["case_key"], "ordinal": ordinal,
        "group": row["group"], "initial": row["initial"], "trace_kind": trace_kind,
        "outcome": outcome,
        "accepted": accepted, "worker_status": row["worker_status"],
        "attempt_receipt": evidence.link(receipt_path), "plan": evidence.link(plan_path),
        "owner_acceptance": row["owner_acceptance"], "owner_rejection": row["owner_rejection"],
        "patch": evidence.link(patch_path) if patch_path in evidence.members else None,
        "changed_paths": row["changed_paths"], "independent_checks": grade_receipts,
        "incoming_guidance": row["feedback"], "actual_warning": warning,
        "paid_threads": [{k: item.get(k) for k in ("paid_thread_id", "role", "semantic_advisory", "execution", "usage", "accounting")}
                         for item in paid_calls if item["condition"]["id"] == condition and item["native_ordinal"] == ordinal],
        "budget": {"wall_allowance_s": row["wall_budget_s"], "elapsed_s": round(elapsed, 3),
                   "phase_wall_remaining_s": round(max(0, row["wall_budget_s"] - elapsed), 3),
                   "chain_token_ceiling": ceiling, "charged_before": before, "charged_phase": charged,
                   "chain_tokens_remaining": max(0, ceiling - before - charged) if before is not None else None,
                   "generation_observed": row["generated_observed"], "generation_unknown_receipts": row["generation_unknown"]},
    }, receipt


def correction_cases(evidence: Evidence, rows: list[dict]) -> list[dict]:
    cases = [
        ("27b-PFXC-A3-detailed-off-common", 0, "feedback-27b-pfx-off-ci/FEEDBACK.json",
         "Make each of the 41 pinned source events appear exactly once. Remove five duplicate source lines and preserve the blank spacer column."),
        ("q38fn-MM-5-detailed-on-common", 0, "feedback-q38fn-mm-on-ci/FEEDBACK.json",
         "Add tests/unit/test_vl_describe_resize.py from the original brief and run the task-local checks. The existing implementation passed the behavioral check."),
        ("q38fn-TU-GR-1-detailed-off-common", 0, "feedback-q38fn-tu-off-ci/FEEDBACK.json",
         "Add the missing grader-isolation test file and run the original task-local checks. Keep the original assertions and verify the substitution control."),
    ]
    indexed = {(row["condition"], row["ordinal"]): row for row in rows}
    out = []
    for condition, ordinal, path, diagnostic in cases:
        row = indexed[(condition, ordinal)]
        feedback = evidence.json(path)
        if row["patch"]["sha256"] != feedback["candidate_patch_sha256"]:
            raise ValueError(f"correction binds to a different patch: {path}")
        prompt = feedback["prompt"]
        prompt_text = evidence.read(path_for(prompt), prompt["sha256"]).decode().strip()
        followup = indexed[(condition, ordinal + 1)]
        budget = row["budget"]
        can_resume = budget["phase_wall_remaining_s"] >= 120 and (budget["chain_tokens_remaining"] or 0) >= 4096
        out.append({"condition": condition, "ordinal": ordinal, "original_patch": row["patch"],
                    "original_brief_sha256": row["brief_sha256"],
                    "diagnostic": diagnostic, "recorded_feedback": evidence.link(path),
                    "recorded_prompt": prompt_text,
                    "acceptance_evidence": evidence.link(path_for(feedback["acceptance_evidence"])),
                    "actual_next_outcome": followup["outcome"],
                    "actual_next_kind": followup["trace_kind"], "actual_next_budget": followup["budget"],
                    "counterfactual_terminal_decision": "one_correction" if can_resume else "freeze_and_fallback",
                    "counterfactual_recovery": None, "terminal_budget": budget})
    return out


def replay(runtime: Path | None, orchestrator: Path) -> dict:
    evidence = Evidence(runtime)
    detectors, detector_source = load_detectors(orchestrator)
    evidence.prefetch({QUALITY, PAID, WARNING_AUDIT})
    quality = evidence.json(QUALITY)
    paid = evidence.json(PAID)
    audit = evidence.json(WARNING_AUDIT)
    paths = set()
    for row in quality["attempts"]:
        paths.add(evidence.case_paths[row["condition"]["case_spec_sha256"]])
        receipt = path_for(row["worker_receipt"])
        paths.update({receipt, path_for(row["plan"]), str(Path(receipt).with_name("session.json"))})
    evidence.prefetch(paths)
    rows = []
    for row in quality["attempts"]:
        actual, receipt = observed_attempt(row, evidence, paid["calls"], audit)
        session_path = str(Path(actual["attempt_receipt"]["path"]).with_name("session.json"))
        session = evidence.json(session_path)
        elapsed_start, elapsed_end = receipt["started_at"], receipt["ended_at"]
        case_sha = row["condition"]["case_spec_sha256"]
        case_path = evidence.case_paths[case_sha]
        editable_paths = set(evidence.json(case_path, case_sha)["editable_paths"])
        turns = session_turns(session, elapsed_start, elapsed_end, editable_paths)
        actual["case_spec"] = evidence.link(case_path)
        signals = inspect_recovery_trace(turns, detectors, elapsed_start, row["wall_budget_s"])
        warning = actual["actual_warning"]
        if warning["configured"]:
            warning["exported_markers"] = signals["exported_warning_markers"]
            if warning["triggered"] is False and not warning["exported_markers"]:
                warning.update({"delivered": False, "acted_on": False})
        actual["brief_sha256"] = row["condition"]["prompt_sha256"]
        actual["session"] = evidence.link(session_path)
        actual["counterfactual_advisories"] = signals.pop("counterfactual_advisories")
        actual["observed_trace"] = signals
        actual["no_patch_inspection_expiry_proxy"] = (
            actual["outcome"] == "interrupted_no_patch" and not signals["observed_artifact_changes"]
            and signals["tool_calls"] >= 20
            and 10 * sum(tool.inspected for turn in turns for tool in turn.tools) >= 9 * signals["tool_calls"]
        )
        rows.append(actual)
    accepted = [row for row in rows if row["accepted"]]
    loop_proxy = [row for row in rows if row["no_patch_inspection_expiry_proxy"]]
    sensitivity = {}
    for name, limit in INSPECTION_LIMITS.items():
        fired = {(row["condition"], row["ordinal"]) for row in rows if row["counterfactual_advisories"][name]}
        sensitivity[name] = {
            "inspection_run_threshold": limit,
            "advisories_total": len(fired),
            "advisories_on_owner_accepted": sum((row["condition"], row["ordinal"]) in fired for row in accepted),
            "missed_inspection_expiry_proxy_conditions": [row["condition"] for row in loop_proxy
                                                           if (row["condition"], row["ordinal"]) not in fired],
        }

    outcome_counts = Counter(row["outcome"] for row in rows)
    return {
        "schema": "ap-w66-recovery-replay.v1", "source_commit": SOURCE_COMMIT,
        "layout_sha256": LAYOUT_SHA256, "detector_source": detector_source,
        "sources": [evidence.link(item) for item in (QUALITY, PAID, WARNING_AUDIT)],
        "scoring": {
            "attempts": len(rows), "actual_outcomes": dict(outcome_counts),
            "accepted": len(accepted), "inspection_expiry_proxy": len(loop_proxy),
            "sensitivity": sensitivity,
            "first_repeated_call_on_owner_accepted": sum(row["observed_trace"]["first_repeated_call_exempted_metric"]
                                                          is not None for row in accepted),
        },
        "correction_replays": correction_cases(evidence, rows),
        "attempts": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orchestrator", type=Path, default=Path("/workspace/repos/epyc-orchestrator"))
    parser.add_argument("--runtime", type=Path, help="Optional mounted copy of archived runtime receipts")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.runtime, args.orchestrator)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result["scoring"], indent=2))


if __name__ == "__main__":
    main()
