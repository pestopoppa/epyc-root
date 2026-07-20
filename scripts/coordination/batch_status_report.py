#!/usr/bin/env python3
"""B9 — inference-batch status report + operator-bundle formatter.

Reads the compiled manifest (``manifest.yaml``, from B1/W0a) and the append-only
execution ledger (``ledger.jsonl``) and renders an operator-facing markdown
status report:

  * per-phase counts by ledger status,
  * blocked / held breakdown (with reasons),
  * next-eligible entries (deps satisfied, not terminal/held/running),
  * the accumulated operator-bundle rows harvested from held ledger rows.

Also exposes :func:`format_op_bundle_row`, which renders the tri-role
Gate / Evidence / Options block appended to
``coordination/inference-batch/op-bundle.md``.

The rendering functions are pure and operate on already-parsed dicts, so they
are testable without any file I/O or yaml dependency. Only :func:`load_manifest`
needs yaml, and only for ``.yaml``/``.yml`` inputs (imported lazily).

Modeled on epyc-orchestrator/scripts/lab/readiness_report.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Any

# Reuse the single authoritative ledger-status vocabulary + groupings.
try:  # when imported as part of a package / with coordination dir on path
    from entry_verdict import (  # type: ignore
        BLOCKED_PRECONDITION,
        BLOCKED_STATUSES,
        HELD_STATUSES,
        INFRA_BLOCKED,
        LEDGER_STATUSES,
        READY,
        TERMINAL_SUCCESS,
    )
    from batch_ledger import canonical_hash, is_retry_pickable  # type: ignore
except ImportError:  # pragma: no cover - fallback when run from elsewhere
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from entry_verdict import (  # type: ignore
        BLOCKED_PRECONDITION,
        BLOCKED_STATUSES,
        HELD_STATUSES,
        INFRA_BLOCKED,
        LEDGER_STATUSES,
        READY,
        TERMINAL_SUCCESS,
    )
    from batch_ledger import canonical_hash, is_retry_pickable  # type: ignore


class StatusReportError(RuntimeError):
    """Operator-facing status-report failure."""


UNSTARTED = "UNSTARTED"  # report-only bucket: entry present in manifest, absent from ledger
# Statuses that can be next-eligible without an entry-level retry policy.
_ELIGIBLE_FROM = frozenset({UNSTARTED, READY})
_GATE_ROW_RE = re.compile(r"^\s*-\s+\[(?P<mark>[ xX])\]\s+\*\*(?P<label>[^*]+)\*\*")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ── loaders ────────────────────────────────────────────────────────────────
def load_manifest(path: str | Path) -> dict[str, Any]:
    """Load a compiled manifest. ``.yaml``/``.yml`` via pyyaml (lazy import);
    ``.json`` via stdlib json."""
    p = Path(path)
    try:
        text = p.read_text()
    except FileNotFoundError as exc:
        raise StatusReportError(f"manifest not found: {p}") from exc
    if p.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise StatusReportError(
                "pyyaml required to load a .yaml manifest; run with the "
                "epyc-orchestrator venv python, or pass a .json manifest"
            ) from exc
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text or "{}")
    if not isinstance(data, dict):
        raise StatusReportError(f"manifest must be a mapping: {p}")
    return data


def load_ledger(path: str | Path) -> list[dict[str, Any]]:
    """Load the append-only ledger.jsonl.

    The status reporter is normally called with an explicit ledger path. Treat a
    missing file as an operator-visible error so a typo cannot make blocked rows
    disappear from the report.
    """
    p = Path(path)
    if not p.exists():
        raise StatusReportError(f"ledger not found: {p}")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(p.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StatusReportError(f"{p}:{lineno}: invalid JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise StatusReportError(f"{p}:{lineno}: ledger row must be an object")
        rows.append(row)
    return rows


def load_operator_gate_registry(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse op-bundle checkbox rows into gate-id -> status metadata.

    Gate ids are the bold label prefix before " — ". A checked row grants a
    gate unless its line explicitly says DENIED.
    """
    p = Path(path)
    if not p.exists():
        return {}
    registry: dict[str, dict[str, Any]] = {}
    for lineno, line in enumerate(p.read_text().splitlines(), start=1):
        match = _GATE_ROW_RE.match(line)
        if not match:
            continue
        label = match.group("label").strip()
        gate_id = label.split(" — ", 1)[0].strip()
        checked = match.group("mark").lower() == "x"
        denied = "DENIED" in line.upper()
        registry[gate_id] = {
            "gate_id": gate_id,
            "label": label,
            "checked": checked,
            "granted": checked and not denied,
            "line": lineno,
            "text": line.strip(),
        }
    return registry


def load_load_report(path: str | Path) -> dict[str, Any]:
    """Load one JSON snapshot from inference_load_check.py --json."""
    p = Path(path)
    try:
        data = json.loads(p.read_text())
    except FileNotFoundError as exc:
        raise StatusReportError(f"load report not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise StatusReportError(f"load report is not valid JSON: {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise StatusReportError(f"load report must be a JSON object: {p}")
    return data


# ── ledger folding ─────────────────────────────────────────────────────────
def _row_task_id(row: dict[str, Any]) -> str:
    return str(row.get("task_id") or row.get("id") or row.get("entry_id") or "")


def latest_by_task(ledger_rows: list[dict[str, Any]]) -> "OrderedDict[str, dict[str, Any]]":
    """Fold the append-only ledger to the latest row per task (latest-row-wins,
    by file/append order)."""
    latest: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for row in ledger_rows:
        tid = _row_task_id(row)
        if not tid:
            continue
        latest[tid] = row  # later append overwrites; preserves first-seen order key
    return latest


def _entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("entries")
    if entries is None:
        entries = manifest.get("tasks", [])
    return [e for e in (entries or []) if isinstance(e, dict)]


def _entry_id(entry: dict[str, Any]) -> str:
    return str(entry.get("task_id") or entry.get("id") or "")


def _entry_phase(entry: dict[str, Any]) -> int:
    try:
        return int(entry.get("phase", 0))
    except (TypeError, ValueError):
        return 0


def _entry_priority(entry: dict[str, Any]) -> str:
    return str(entry.get("priority") or "P4")


def _depends_on(entry: dict[str, Any]) -> list[str]:
    pre = entry.get("preconditions") or {}
    return [str(d) for d in (pre.get("depends_on") or [])]


def _status_of(entry_id: str, latest: dict[str, dict[str, Any]]) -> str:
    row = latest.get(entry_id)
    if not row:
        return UNSTARTED
    status = str(row.get("status") or "").strip()
    return status if status in LEDGER_STATUSES else (status or UNSTARTED)


def _deps_satisfied(entry: dict[str, Any], latest: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    unmet = [
        dep
        for dep in _depends_on(entry)
        if _status_of(dep, latest) not in TERMINAL_SUCCESS
    ]
    return (not unmet), unmet


def _operator_gates(entry: dict[str, Any]) -> list[str]:
    pre = entry.get("preconditions") or {}
    return [str(gate) for gate in (pre.get("operator_gates") or [])]


def _operator_gate_blockers(
    entry: dict[str, Any],
    operator_gate_registry: dict[str, dict[str, Any]] | None,
) -> list[dict[str, str]]:
    if operator_gate_registry is None:
        return []
    blockers: list[dict[str, str]] = []
    for gate in _operator_gates(entry):
        row = operator_gate_registry.get(gate)
        if row is None:
            blockers.append({"gate": gate, "reason": "missing_from_op_bundle"})
        elif not row.get("granted"):
            blockers.append({"gate": gate, "reason": "not_granted"})
    return blockers


def is_structurally_eligible(entry: dict[str, Any], latest: dict[str, dict[str, Any]]) -> bool:
    entry_id = _entry_id(entry)
    status = _status_of(entry_id, latest)
    if status not in _ELIGIBLE_FROM and not is_retry_pickable(entry, latest.get(entry_id)):
        return False
    ok, _ = _deps_satisfied(entry, latest)
    return ok


def is_eligible(
    entry: dict[str, Any],
    latest: dict[str, dict[str, Any]],
    operator_gate_registry: dict[str, dict[str, Any]] | None = None,
) -> bool:
    if not is_structurally_eligible(entry, latest):
        return False
    return not _operator_gate_blockers(entry, operator_gate_registry)


def _current_entry_hash(entry: dict[str, Any]) -> str:
    if entry.get("entry_hash"):
        return str(entry["entry_hash"])
    clean = {k: v for k, v in entry.items() if k != "entry_hash"}
    return canonical_hash(clean)


def _entry_hash_drift(entry: dict[str, Any], latest_row: dict[str, Any] | None) -> dict[str, str] | None:
    if not latest_row:
        return None
    ledger_hash = latest_row.get("entry_hash")
    if not ledger_hash:
        return None
    current_hash = _current_entry_hash(entry)
    if str(ledger_hash) == current_hash:
        return None
    return {
        "ledger_entry_hash": str(ledger_hash),
        "current_entry_hash": current_hash,
    }


def _entry_execution(entry: dict[str, Any]) -> dict[str, Any]:
    execution = entry.get("execution") or {}
    return execution if isinstance(execution, dict) else {}


def _serial_noninference(entry: dict[str, Any]) -> bool:
    return str(_entry_execution(entry).get("concurrency_mode") or "") == "serial_noninference"


def _load_summary(load_report: dict[str, Any] | None) -> dict[str, Any] | None:
    if load_report is None:
        return None
    return {
        "ts": load_report.get("ts"),
        "state": load_report.get("state"),
        "quiet": bool(load_report.get("quiet")),
        "quiet_blockers": list(load_report.get("quiet_blockers") or []),
        "busy_reasons": list(load_report.get("busy_reasons") or []),
    }


def _busy_llama_ports(load_report: dict[str, Any]) -> set[int]:
    signals = load_report.get("signals") if isinstance(load_report, dict) else {}
    llama = signals.get("llama") if isinstance(signals, dict) else {}
    slots = llama.get("slots_busy_by_port") if isinstance(llama, dict) else {}
    busy: set[int] = set()
    if not isinstance(slots, dict):
        return busy
    for raw_port, raw_count in slots.items():
        try:
            port = int(raw_port)
            count = int(raw_count)
        except (TypeError, ValueError):
            continue
        if count > 0:
            busy.add(port)
    return busy


def _load_blockers(
    entry: dict[str, Any],
    load_report: dict[str, Any] | None,
    *,
    allow_gpu_parallel: bool = False,
    allowed_active_ports: set[int] | None = None,
) -> list[str]:
    """Return reasons this entry is not runnable under the supplied load snapshot.

    The loop protocol permits serial_noninference entries outside a quiet window;
    every entry that can touch model/runtime compute needs the quiet predicate.
    """
    if load_report is None or _serial_noninference(entry):
        return []
    if bool(load_report.get("quiet")):
        return []
    reasons = list(load_report.get("quiet_blockers") or [])
    if not reasons:
        reasons = list(load_report.get("busy_reasons") or [])
    if allow_gpu_parallel and reasons:
        allowed_ports = allowed_active_ports or set()
        busy_ports = _busy_llama_ports(load_report)
        filtered: list[Any] = []
        for reason in reasons:
            text = str(reason)
            if text == "MI210 occupied":
                continue
            if text in {"llama-server actively decoding", "llama-server decode active"}:
                if busy_ports and busy_ports.issubset(allowed_ports):
                    continue
            filtered.append(reason)
        reasons = filtered
    if not reasons:
        if allow_gpu_parallel:
            return []
        state = str(load_report.get("state") or "unknown")
        reasons = [f"load_state={state}; quiet=false"]
    return [str(reason) for reason in reasons]


# ── report model ───────────────────────────────────────────────────────────
def build_report(
    manifest: dict[str, Any],
    ledger_rows: list[dict[str, Any]],
    operator_gate_registry: dict[str, dict[str, Any]] | None = None,
    load_report: dict[str, Any] | None = None,
    allow_gpu_parallel: bool = False,
    allowed_active_ports: set[int] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the structured status report (pure; no I/O)."""
    entries = _entries(manifest)
    latest = latest_by_task(ledger_rows)

    per_phase: "OrderedDict[int, dict[str, int]]" = OrderedDict()
    status_totals: dict[str, int] = defaultdict(int)
    blocked: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    runnable: list[dict[str, Any]] = []
    load_blocked: list[dict[str, Any]] = []
    structurally_eligible: list[dict[str, Any]] = []
    operator_gate_blocked: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for entry in sorted(entries, key=lambda e: (_entry_phase(e), _entry_priority(e), _entry_id(e))):
        eid = _entry_id(entry)
        phase = _entry_phase(entry)
        status = _status_of(eid, latest)
        per_phase.setdefault(phase, defaultdict(int))
        per_phase[phase][status] += 1
        status_totals[status] += 1

        row = latest.get(eid) or {}
        reasons = row.get("reasons") or []
        if status in BLOCKED_STATUSES:
            ok, unmet = _deps_satisfied(entry, latest)
            blocked.append(
                {
                    "task_id": eid,
                    "title": entry.get("title"),
                    "phase": phase,
                    "status": status,
                    "reasons": reasons,
                    "unmet_deps": unmet,
                }
            )
        if status in HELD_STATUSES:
            held.append(
                {
                    "task_id": eid,
                    "title": entry.get("title"),
                    "phase": phase,
                    "status": status,
                    "reasons": reasons,
                    "op_bundle_row": row.get("op_bundle_row"),
                }
            )
        if is_structurally_eligible(entry, latest):
            structural_row = {
                "task_id": eid,
                "title": entry.get("title"),
                "phase": phase,
                "priority": _entry_priority(entry),
                "status": status,
                "driver": (entry.get("execution") or {}).get("driver"),
            }
            drift = _entry_hash_drift(entry, row)
            if drift:
                structural_row["entry_hash_drift"] = True
                structural_row.update(drift)
                warnings.append(
                    {
                        "task_id": eid,
                        "type": "entry_hash_drift",
                        "message": (
                            "latest ledger row was recorded against a different "
                            "entry_hash than the current manifest entry"
                        ),
                        **drift,
                    }
                )
            structurally_eligible.append(structural_row)
            gate_blockers = _operator_gate_blockers(entry, operator_gate_registry)
            if gate_blockers:
                operator_gate_blocked.append(
                    {
                        **structural_row,
                        "operator_gate_blockers": gate_blockers,
                    }
                )
            else:
                eligible.append(structural_row)
                blockers = _load_blockers(
                    entry,
                    load_report,
                    allow_gpu_parallel=allow_gpu_parallel,
                    allowed_active_ports=allowed_active_ports,
                )
                if load_report is not None:
                    if blockers:
                        load_blocked.append(
                            {
                                **structural_row,
                                "load_blockers": blockers,
                            }
                        )
                    else:
                        runnable.append(structural_row)

    # Accumulated op-bundle rows: every held ledger row that carries one.
    op_bundle_rows: list[dict[str, Any]] = []
    for eid, row in latest.items():
        obr = row.get("op_bundle_row")
        if obr:
            op_bundle_rows.append(obr)

    return {
        "schema_version": "inference_batch_status_report.v1",
        "generated_at": generated_at or utc_now(),
        "load_policy": {
            "allow_gpu_parallel": bool(allow_gpu_parallel),
            "allowed_active_ports": sorted(allowed_active_ports or []),
        },
        "summary": {
            "entries_total": len(entries),
            "ledger_rows": len(ledger_rows),
            "tracked_tasks": len(latest),
            "by_status": dict(sorted(status_totals.items())),
            "eligible_now": len(eligible),
            "runnable_now": len(runnable) if load_report is not None else None,
            "load_blocked": len(load_blocked),
            "structurally_eligible": len(structurally_eligible),
            "operator_gate_blocked": len(operator_gate_blocked),
            "blocked": len(blocked),
            "held": len(held),
            "op_bundle_rows": len(op_bundle_rows),
            "done_pass": status_totals.get("DONE_PASS", 0),
            "done_marginal_obs": status_totals.get("DONE_MARGINAL_OBS", 0),
            "failed_reverted": status_totals.get("FAILED_REVERTED", 0),
            "warnings": len(warnings),
        },
        "per_phase": {ph: dict(sorted(c.items())) for ph, c in per_phase.items()},
        "current_load": _load_summary(load_report),
        "warnings": warnings,
        "runnable": runnable,
        "load_blocked": load_blocked,
        "eligible": eligible,
        "structurally_eligible": structurally_eligible,
        "operator_gate_blocked": operator_gate_blocked,
        "blocked_breakdown": blocked,
        "held_breakdown": held,
        "op_bundle_rows": op_bundle_rows,
    }


# ── markdown rendering ─────────────────────────────────────────────────────
def _render_counts_table(by_status: dict[str, int]) -> list[str]:
    if not by_status:
        return ["_(no entries)_", ""]
    lines = ["| Status | Count |", "| --- | --- |"]
    for status, count in sorted(by_status.items()):
        lines.append(f"| {status} | {count} |")
    lines.append("")
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    out: list[str] = []
    out.append("# Inference-Batch Status Report")
    out.append("")
    out.append(f"_Generated {report['generated_at']}_")
    out.append("")
    if report.get("current_load") is not None:
        out.append(
            f"**{s['entries_total']}** entries | "
            f"**{s['runnable_now']}** runnable under current load | "
            f"**{s['eligible_now']}** operator-eligible | "
            f"**{s['load_blocked']}** load-blocked | "
            f"**{s['operator_gate_blocked']}** operator-gate blocked | "
            f"**{s['blocked']}** blocked | "
            f"**{s['held']}** held | "
            f"**{s['op_bundle_rows']}** op-bundle rows"
        )
    else:
        out.append(
            f"**{s['entries_total']}** entries | "
            f"**{s['eligible_now']}** operator-eligible (load not checked) | "
            f"**{s['operator_gate_blocked']}** operator-gate blocked | "
            f"**{s['blocked']}** blocked | "
            f"**{s['held']}** held | "
            f"**{s['op_bundle_rows']}** op-bundle rows"
        )
    out.append("")
    out.append(
        f"Done(pass): {s['done_pass']} · Done(marginal-obs): {s['done_marginal_obs']} "
        f"· Failed(reverted): {s['failed_reverted']}"
    )
    out.append("")

    if report.get("current_load") is not None:
        load = report["current_load"]
        policy = report.get("load_policy") or {}
        blockers = ", ".join(load.get("quiet_blockers") or []) or "-"
        busy = ", ".join(load.get("busy_reasons") or []) or "-"
        allowed_ports = ",".join(str(p) for p in policy.get("allowed_active_ports") or []) or "-"
        out.append("## Current load")
        out.append("")
        out.append(
            f"- state={load.get('state') or 'unknown'} · quiet={load.get('quiet')} "
            f"· quiet_blockers={blockers} · busy_reasons={busy}"
        )
        if policy.get("allow_gpu_parallel"):
            out.append(
                f"- load policy: allow GPU-only parallel work; allowed active ports={allowed_ports}"
            )
        out.append("")

    if report.get("warnings"):
        out.append("## Warnings")
        out.append("")
        for warning in report["warnings"]:
            out.append(
                f"- **{warning['task_id']}** {warning['type']}: {warning['message']} "
                f"(ledger={warning.get('ledger_entry_hash')}, current={warning.get('current_entry_hash')})"
            )
        out.append("")

    out.append("## Counts by status")
    out.append("")
    out.extend(_render_counts_table(s["by_status"]))

    out.append("## Per-phase breakdown")
    out.append("")
    per_phase = report["per_phase"]
    if not per_phase:
        out.append("_(no phases)_")
        out.append("")
    else:
        for phase in sorted(per_phase.keys()):
            counts = per_phase[phase]
            inline = ", ".join(f"{st}={ct}" for st, ct in sorted(counts.items()))
            out.append(f"- **Phase {phase}**: {inline}")
        out.append("")

    if report.get("current_load") is not None:
        out.append("## Runnable under current load")
        table_rows = report["runnable"]
        empty = "_None runnable under the supplied load snapshot._"
    else:
        out.append("## Operator-eligible entries")
        table_rows = report["eligible"]
        empty = "_None operator-eligible — every entry is blocked, gate-held, running, or done._"
    out.append("")
    if not table_rows:
        out.append(empty)
        out.append("")
    else:
        out.append("| task_id | phase | prio | driver | from-status |")
        out.append("| --- | --- | --- | --- | --- |")
        for e in table_rows:
            out.append(
                f"| {e['task_id']} | {e['phase']} | {e['priority']} | "
                f"{e.get('driver') or '-'} | {e['status']} |"
            )
        out.append("")

    if report.get("current_load") is not None:
        out.append("## Operator-eligible but load-blocked")
        out.append("")
        if not report["load_blocked"]:
            out.append("_None._")
            out.append("")
        else:
            out.append("| task_id | phase | prio | load blockers |")
            out.append("| --- | --- | --- | --- |")
            for e in report["load_blocked"]:
                blockers = ", ".join(e.get("load_blockers") or [])
                out.append(f"| {e['task_id']} | {e['phase']} | {e['priority']} | {blockers} |")
            out.append("")

    out.append("## Structurally eligible but operator-gated")
    out.append("")
    if not report.get("operator_gate_blocked"):
        out.append("_None._")
        out.append("")
    else:
        out.append("| task_id | phase | prio | missing/ungranted gates |")
        out.append("| --- | --- | --- | --- |")
        for e in report["operator_gate_blocked"]:
            gates = ", ".join(
                f"{b['gate']} ({b['reason']})" for b in e.get("operator_gate_blockers", [])
            )
            out.append(f"| {e['task_id']} | {e['phase']} | {e['priority']} | {gates} |")
        out.append("")

    out.append("## Blocked / held")
    out.append("")
    if not report["blocked_breakdown"] and not report["held_breakdown"]:
        out.append("_None._")
        out.append("")
    else:
        for b in report["blocked_breakdown"]:
            deps = f" unmet deps: {', '.join(b['unmet_deps'])}" if b["unmet_deps"] else ""
            reason = f" — {'; '.join(b['reasons'])}" if b["reasons"] else ""
            out.append(f"- [BLOCKED:{b['status']}] **{b['task_id']}** (phase {b['phase']}){reason}{deps}")
        for h in report["held_breakdown"]:
            reason = f" — {'; '.join(h['reasons'])}" if h["reasons"] else ""
            out.append(f"- [HELD:{h['status']}] **{h['task_id']}** (phase {h['phase']}){reason}")
        out.append("")

    out.append("## Accumulated operator-bundle rows")
    out.append("")
    if not report["op_bundle_rows"]:
        out.append("_None accumulated._")
        out.append("")
    else:
        for obr in report["op_bundle_rows"]:
            out.append(
                format_op_bundle_row(
                    obr.get("task_id") or obr.get("entry_id") or "<unknown>",
                    obr.get("gate", ""),
                    obr.get("evidence", ""),
                    obr.get("options", []),
                    title=obr.get("title"),
                )
            )
            out.append("")
    return "\n".join(out).rstrip() + "\n"


# ── op-bundle row formatter (tri-role Gate / Evidence / Options) ───────────
def format_op_bundle_row(
    entry: dict[str, Any] | str,
    gate: str,
    evidence: str,
    options: list[str] | None,
    title: str | None = None,
) -> str:
    """Render one tri-role Gate/Evidence/Options block for op-bundle.md.

    ``entry`` may be a manifest entry dict (uses task_id/title) or a task_id
    string. This is the block appended to
    ``coordination/inference-batch/op-bundle.md`` for each held decision.
    """
    if isinstance(entry, dict):
        task_id = str(entry.get("task_id") or entry.get("id") or "<unknown>")
        entry_title = title or entry.get("title") or task_id
    else:
        task_id = str(entry)
        entry_title = title or task_id

    lines = [f"### {task_id} — {entry_title}", ""]
    lines.append(f"- **Gate**: {gate or '(unspecified)'}")
    lines.append(f"- **Evidence**: {evidence or '(none recorded)'}")
    lines.append("- **Options**:")
    opts = list(options or [])
    if not opts:
        lines.append("  1. (no pre-formed options — operator to adjudicate)")
    else:
        for i, opt in enumerate(opts, start=1):
            lines.append(f"  {i}. {opt}")
    return "\n".join(lines)


def append_op_bundle_row(
    op_bundle_path: str | Path,
    entry: dict[str, Any] | str,
    gate: str,
    evidence: str,
    options: list[str] | None,
    title: str | None = None,
    dry_run: bool = True,
) -> str:
    """Format and (unless dry_run) append a tri-role block to op-bundle.md.

    Returns the rendered block. dry_run defaults True (nothing is written).
    """
    block = format_op_bundle_row(entry, gate, evidence, options, title=title)
    if not dry_run:
        p = Path(op_bundle_path)
        prefix = "\n" if (p.exists() and p.read_text().strip()) else ""
        with p.open("a") as fh:
            fh.write(prefix + block + "\n")
    return block


# ── CLI ────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="manifest.yaml or .json")
    parser.add_argument("--ledger", required=True, help="ledger.jsonl")
    parser.add_argument(
        "--op-bundle",
        default=None,
        help=(
            "operator gate registry markdown; defaults to op-bundle.md beside "
            "the manifest when present"
        ),
    )
    parser.add_argument(
        "--ignore-operator-gates",
        action="store_true",
        help="report structural eligibility only; do not filter by op-bundle grants",
    )
    parser.add_argument(
        "--load-report",
        default=None,
        help=(
            "JSON emitted by inference_load_check.py --json; when supplied, "
            "separates operator-eligible entries from entries runnable under "
            "the current quiet-window/load snapshot"
        ),
    )
    parser.add_argument(
        "--allow-gpu-parallel",
        action="store_true",
        help=(
            "current-load report only: ignore MI210 occupancy and llama decode "
            "on explicitly allowed active ports, for CPU-domain batch planning"
        ),
    )
    parser.add_argument(
        "--allow-active-port",
        action="append",
        type=int,
        default=[],
        help=(
            "port whose active llama-server decode is known GPU-only and may be "
            "ignored when --allow-gpu-parallel is set; repeatable"
        ),
    )
    parser.add_argument("--json", action="store_true", help="emit structured JSON instead of markdown")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        ledger = load_ledger(args.ledger)
        gate_registry = None
        if not args.ignore_operator_gates:
            op_bundle = Path(args.op_bundle) if args.op_bundle else Path(args.manifest).parent / "op-bundle.md"
            gate_registry = load_operator_gate_registry(op_bundle)
        load_report = load_load_report(args.load_report) if args.load_report else None
        report = build_report(
            manifest,
            ledger,
            operator_gate_registry=gate_registry,
            load_report=load_report,
            allow_gpu_parallel=bool(args.allow_gpu_parallel),
            allowed_active_ports=set(args.allow_active_port or []),
        )
    except StatusReportError as exc:
        print(f"batch_status_report: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, sort_keys=True, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
