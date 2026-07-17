#!/usr/bin/env python3
"""B5 — entry verdict wiring for the consolidated inference-batch loop.

Pure decision function. Given an *executed* inference-batch entry (validated
against ``inference_batch.schema.json``) plus the evidence produced by the run,
map that evidence onto exactly one pre-decided fork action from the entry's
``outcomes.gate_table`` and return a :class:`Verdict` *plan*.

This module NEVER touches the world. It:
  * does NOT execute reverts (it only *plans* them),
  * does NOT relaunch servers or mutate runtime flags / registries,
  * does NOT write the ledger, flip checkboxes, or edit files.

The batch loop (caller) consumes the returned :class:`Verdict` and is the sole
executor. What the loop is allowed to do autonomously is fixed by the
**locked autonomy policy** encoded below.

--------------------------------------------------------------------------
LOCKED AUTONOMY POLICY (operator-decided; baked into the fork semantics)
--------------------------------------------------------------------------
  * auto-revert is permitted ONLY for:
        - runtime flags               (reset an env/runtime flag), and
        - relaunch-to-reference-lineup (restart onto the reference stack).
  * file / config edits are NEVER auto-reverted -> they become an
    operator-bundle row (HELD_OP_GATE) with pre-formed options.
  * an ``ambiguous`` verdict (conflicting / missing evidence, or an entry
    gated on an operator sign-off) -> operator-bundle row with pre-formed
    options (HELD_AMBIGUOUS / HELD_OP_GATE). Never auto-actioned.
  * a decisive negative (SafetyGate REJECT or sequential *refuted*) ->
    FAILED_REVERTED, and the reset flag / reference relaunch is planned.
  * ledger rows + artifacts: the loop commits these directly (not our call).
  * checkbox flips: direct, but listed in wrap-up (see flip_checkbox.py).

--------------------------------------------------------------------------
Vocabulary reuse (MIRRORED, not imported)
--------------------------------------------------------------------------
The SafetyGate verdict vocabulary (PASS / WARN / REJECT) is mirrored from
``epyc-orchestrator/src/safety_gate.py`` (``class Verdict(str, Enum)``, L37-40)
and the sequential-verdict states (accumulating / confirmed / refuted) from
``epyc-orchestrator/src/autopilot_core/sequential_verdict.py``
(``STATE_ACCUMULATING`` / ``STATE_CONFIRMED`` / ``STATE_REFUTED``, L17-19).

They are mirrored rather than imported because this file lives in ``epyc-root``
and those symbols live in the ``epyc-orchestrator`` src tree / a different venv;
a hard import would couple the batch loop to that install. Callers may pass the
real enum instances anyway — the normalizers below accept enum members (via
``.value``), ``GateVerdict`` objects (via ``.verdict``), sequential views (via
``.state``), or plain strings, case-insensitively.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


# ── mirrored vocabularies ──────────────────────────────────────────────────
# SafetyGate — epyc-orchestrator/src/safety_gate.py L37-40
SAFETY_PASS = "pass"
SAFETY_WARN = "warn"
SAFETY_REJECT = "reject"

# sequential_verdict — epyc-orchestrator/src/autopilot_core/sequential_verdict.py L17-19
SEQ_ACCUMULATING = "accumulating"
SEQ_CONFIRMED = "confirmed"
SEQ_REFUTED = "refuted"


# ── ledger status vocabulary (W0a execution_manifest.jsonl v2) ─────────────
# Kept here so batch_status_report.py can import one authoritative copy.
READY = "READY"
RUNNING = "RUNNING"
DONE_PASS = "DONE_PASS"
DONE_MARGINAL_OBS = "DONE_MARGINAL_OBS"
FAILED_REVERTED = "FAILED_REVERTED"
INFRA_BLOCKED = "INFRA_BLOCKED"
HELD_AMBIGUOUS = "HELD_AMBIGUOUS"
HELD_OP_GATE = "HELD_OP_GATE"
BLOCKED_PRECONDITION = "BLOCKED_PRECONDITION"
SKIPPED_SUPERSEDED = "SKIPPED_SUPERSEDED"
COORDINATION = "COORDINATION"

LEDGER_STATUSES = frozenset(
    {
        READY,
        RUNNING,
        DONE_PASS,
        DONE_MARGINAL_OBS,
        FAILED_REVERTED,
        INFRA_BLOCKED,
        HELD_AMBIGUOUS,
        HELD_OP_GATE,
        BLOCKED_PRECONDITION,
        SKIPPED_SUPERSEDED,
        COORDINATION,
    }
)

# Semantic groupings used by the reporter and by dependency resolution.
TERMINAL_SUCCESS = frozenset({DONE_PASS, DONE_MARGINAL_OBS})
TERMINAL_FAILURE = frozenset({FAILED_REVERTED})
HELD_STATUSES = frozenset({HELD_AMBIGUOUS, HELD_OP_GATE})
BLOCKED_STATUSES = frozenset({INFRA_BLOCKED, BLOCKED_PRECONDITION})
IN_FLIGHT = frozenset({READY, RUNNING})

# The five fork categories (mirrors the schema's fork_branch / fork_infra /
# fork_ambiguous vocabulary in inference_batch.schema.json).
CAT_PASS = "pass"
CAT_MARGINAL = "marginal"
CAT_FAIL = "fail"
CAT_INFRA = "infra"
CAT_AMBIGUOUS = "ambiguous"

_DEFAULT_STATUS_FOR_CATEGORY = {
    CAT_PASS: DONE_PASS,
    CAT_MARGINAL: DONE_MARGINAL_OBS,
    CAT_FAIL: FAILED_REVERTED,  # may escalate to HELD_OP_GATE (autonomy policy)
    CAT_INFRA: INFRA_BLOCKED,
    CAT_AMBIGUOUS: HELD_AMBIGUOUS,
}

# exec status strings that mean "the run itself did not produce trustworthy
# evidence" -> infra branch.
_INFRA_BAD_STATUS = frozenset(
    {
        "error",
        "timeout",
        "timed_out",
        "crashed",
        "crash",
        "preflight_failed",
        "infra_blocked",
        "oom",
        "aborted",
        "topology_mismatch",
        "quiet_window_lost",
    }
)

# Revert-mechanism classification of a fork branch's action tokens.
# AUTO markers => runtime-flag reset or reference-lineup relaunch (auto-revertible).
_AUTO_FLAG_MARKERS = (
    "reset_flag",
    "reset_flags",
    "unset_flag",
    "revert_runtime_flag",
    "revert_flag",
    "clear_flag",
    "runtime flag",
    "env flag",
)
_AUTO_RELAUNCH_MARKERS = (
    "relaunch_reference_lineup",
    "relaunch reference lineup",
    "relaunch-to-reference",
    "relaunch_to_reference",
    "reference lineup relaunch",
    "restore_reference_lineup",
    "relaunch:",
    "relaunch_lineup",
)
# NON-AUTO markers => touching files / config / registry / source: operator only.
_FILE_EDIT_MARKERS = (
    "edit_file",
    "edit file",
    "revert_file",
    "revert_commit",
    "revert_config",
    "config edit",
    "config_edit",
    "registry",
    "yaml edit",
    "patch",
    "rewrite",
    "source change",
    "code change",
    "git revert",
    "modelfile",
)


# ── result dataclasses ─────────────────────────────────────────────────────
@dataclass
class RevertPlan:
    """A *planned* (never-executed) auto-revert. Only ever runtime-flag resets
    and/or a reference-lineup relaunch — the two operator-permitted auto actions."""

    auto: bool
    kind: str  # "runtime_flags" | "reference_relaunch" | "runtime_flags+reference_relaunch"
    flags_to_reset: list[str] = field(default_factory=list)
    reference_lineup: str | None = None
    steps: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto": self.auto,
            "kind": self.kind,
            "flags_to_reset": list(self.flags_to_reset),
            "reference_lineup": self.reference_lineup,
            "steps": list(self.steps),
            "note": self.note,
        }


@dataclass
class OpBundleRow:
    """A tri-role Gate / Evidence / Options row for the operator bundle. Emitted
    whenever the loop is NOT authorized to act autonomously (ambiguous evidence,
    an operator-gated entry, or a fail whose revert would require a file edit)."""

    task_id: str
    title: str
    gate: str
    evidence: str
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "gate": self.gate,
            "evidence": self.evidence,
            "options": list(self.options),
        }


@dataclass
class Verdict:
    """The fork *plan* for one executed entry. The caller executes it."""

    action: str  # one of the five fork categories
    ledger_status: str  # target ledger status string
    reasons: list[str] = field(default_factory=list)
    revert_plan: RevertPlan | None = None
    op_bundle_row: OpBundleRow | None = None
    # audit extras (not part of the required 5-tuple but useful to the caller):
    next_task: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ledger_status": self.ledger_status,
            "reasons": list(self.reasons),
            "revert_plan": self.revert_plan.to_dict() if self.revert_plan else None,
            "op_bundle_row": self.op_bundle_row.to_dict() if self.op_bundle_row else None,
            "next_task": self.next_task,
            "signals": dict(self.signals),
            "actions": list(self.actions),
        }


# ── signal normalizers ─────────────────────────────────────────────────────
def normalize_safety(value: Any) -> str | None:
    """Coerce a SafetyGate signal to 'pass'/'warn'/'reject'/None.

    Accepts: safety_gate.Verdict members (via .value), GateVerdict objects
    (via .verdict), or plain strings, case-insensitively.
    """
    if value is None:
        return None
    # GateVerdict-like: has a .verdict attribute.
    inner = getattr(value, "verdict", value)
    # Enum member: str(Enum) may be "Verdict.PASS"; prefer .value.
    raw = getattr(inner, "value", inner)
    text = str(raw).strip().lower()
    if not text:
        return None
    if "reject" in text:
        return SAFETY_REJECT
    if "warn" in text:
        return SAFETY_WARN
    if "pass" in text:
        return SAFETY_PASS
    return None


def normalize_sequential(value: Any) -> str | None:
    """Coerce a sequential-verdict signal to
    'confirmed'/'refuted'/'accumulating'/None.

    Accepts: CandidateSequentialView / EProcessState-derived objects exposing a
    ``.state`` attribute, or plain strings, case-insensitively.
    """
    if value is None:
        return None
    inner = getattr(value, "state", value)
    text = str(inner).strip().lower()
    if not text:
        return None
    if SEQ_CONFIRMED in text:
        return SEQ_CONFIRMED
    if SEQ_REFUTED in text:
        return SEQ_REFUTED
    if SEQ_ACCUMULATING in text:
        return SEQ_ACCUMULATING
    return None


# ── infra / execution health ───────────────────────────────────────────────
def _infra_ok(exec_result: Any) -> tuple[bool, str]:
    """Did the run itself complete and produce trustworthy evidence?"""
    if not isinstance(exec_result, dict):
        return False, "no exec_result supplied"
    if exec_result.get("infra_ok") is False:
        why = exec_result.get("error") or exec_result.get("status") or "infra_ok=False"
        return False, f"execution infra unhealthy: {why}"
    status = str(exec_result.get("status", "")).strip().lower()
    if status in _INFRA_BAD_STATUS:
        return False, f"execution status={status}"
    completed = exec_result.get("completed")
    if completed is False and exec_result.get("infra_ok") is not True:
        return False, "execution did not complete"
    return True, "execution infra healthy"


# ── entry helpers ──────────────────────────────────────────────────────────
def _entry_id(entry: dict[str, Any]) -> str:
    return str(entry.get("task_id") or entry.get("id") or "<unknown>")


def _concurrency_mode(entry: dict[str, Any]) -> str:
    return str(((entry.get("execution") or {}).get("concurrency_mode")) or "")


def _requires_sequential(entry: dict[str, Any]) -> bool:
    return _concurrency_mode(entry) == "paired_sequential"


def _gate_rows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ((entry.get("outcomes") or {}).get("gate_table")) or []
    return [r for r in rows if isinstance(r, dict)]


def _preconditions(entry: dict[str, Any]) -> dict[str, Any]:
    return entry.get("preconditions") or {}


# ── the classifier: evidence -> one fork category ──────────────────────────
def classify(
    entry: dict[str, Any],
    exec_result: Any,
    verifier_signals: dict[str, Any] | None,
) -> tuple[str, list[str], dict[str, Any]]:
    """Deterministically map the run evidence to one of the five fork
    categories. Returns ``(category, reasons, normalized_signals)``.
    """
    signals: dict[str, Any] = {}
    reasons: list[str] = []
    verifier_signals = verifier_signals or {}

    infra_ok, infra_reason = _infra_ok(exec_result)
    signals["infra_ok"] = infra_ok
    if not infra_ok:
        return CAT_INFRA, [infra_reason], signals

    mode = _concurrency_mode(entry)
    if mode == "observe_only":
        return (
            CAT_MARGINAL,
            ["observe_only entry: recorded as observation, non-decision-gating"],
            signals,
        )

    safety = normalize_safety(
        verifier_signals.get("safety_gate", verifier_signals.get("safety"))
    )
    seq = normalize_sequential(
        verifier_signals.get("sequential", verifier_signals.get("seq"))
    )
    signals["safety_gate"] = safety
    signals["sequential"] = seq

    forced = verifier_signals.get("category")
    if forced in _DEFAULT_STATUS_FOR_CATEGORY:
        return forced, [f"caller-forced category={forced}"], signals

    if _requires_sequential(entry) and seq is None:
        return (
            CAT_AMBIGUOUS,
            ["paired_sequential entry but no sequential verdict supplied"],
            signals,
        )

    if safety is None and seq is None:
        return CAT_AMBIGUOUS, ["no safety or sequential evidence supplied"], signals

    # ── decisive negatives ────────────────────────────────────────────
    if seq == SEQ_REFUTED:
        reasons.append("sequential verdict REFUTED (statistically not an improvement)")
        return CAT_FAIL, reasons, signals
    if safety == SAFETY_REJECT:
        if seq == SEQ_CONFIRMED:
            reasons.append(
                "conflict: SafetyGate REJECT but sequential CONFIRMED "
                "-> operator adjudication"
            )
            return CAT_AMBIGUOUS, reasons, signals
        reasons.append("SafetyGate REJECT (quality/diversity floor violated)")
        return CAT_FAIL, reasons, signals

    # ── positives / inconclusive (safety in {pass,warn,None}) ─────────
    if safety == SAFETY_PASS and seq == SEQ_CONFIRMED:
        reasons.append("SafetyGate PASS and sequential CONFIRMED")
        return CAT_PASS, reasons, signals
    if safety is None and seq == SEQ_CONFIRMED:
        reasons.append("sequential CONFIRMED (no safety-gate axis on this entry)")
        return CAT_PASS, reasons, signals
    if safety == SAFETY_PASS and seq is None:
        reasons.append("SafetyGate PASS; entry carries no sequential axis")
        return CAT_PASS, reasons, signals
    if safety == SAFETY_WARN and seq == SEQ_CONFIRMED:
        reasons.append(
            "sequential CONFIRMED but SafetyGate WARN (advisory) "
            "-> recorded as marginal observation"
        )
        return CAT_MARGINAL, reasons, signals
    if seq == SEQ_ACCUMULATING:
        reasons.append(
            "sequential ACCUMULATING (inconclusive) -> marginal observation"
        )
        return CAT_MARGINAL, reasons, signals
    if safety == SAFETY_WARN and seq is None:
        reasons.append("SafetyGate WARN, no sequential axis -> marginal observation")
        return CAT_MARGINAL, reasons, signals

    reasons.append(
        f"signals do not resolve cleanly (safety={safety}, sequential={seq})"
    )
    return CAT_AMBIGUOUS, reasons, signals


# ── fork-branch selection from the gate_table ──────────────────────────────
def _select_branch(
    entry: dict[str, Any], category: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    """Return ``(branch, gate_row, missing_notes)`` for the chosen category.

    Iterates gate rows; the first row carrying the category's branch supplies
    the actions / ``next``. If no row declares the branch, degrade gracefully
    (marginal->pass-branch, else generic) and note the fallback.
    """
    notes: list[str] = []
    rows = _gate_rows(entry)
    for row in rows:
        fork = row.get("fork") or {}
        if category in fork and isinstance(fork[category], dict):
            return fork[category], row, notes

    # Degradation: marginal with no explicit branch collapses onto pass actions.
    if category == CAT_MARGINAL:
        for row in rows:
            fork = row.get("fork") or {}
            if CAT_PASS in fork and isinstance(fork[CAT_PASS], dict):
                notes.append("no explicit 'marginal' branch; reused 'pass' actions")
                return fork[CAT_PASS], row, notes
    notes.append(f"gate_table declares no '{category}' branch; using policy default")
    first_row = rows[0] if rows else None
    return None, first_row, notes


def _branch_actions(branch: dict[str, Any] | None) -> list[str]:
    if not branch:
        return []
    actions = branch.get("action") or []
    if isinstance(actions, str):
        return [actions]
    return [str(a) for a in actions]


def _classify_revert_scope(actions: Iterable[str], entry: dict[str, Any]) -> dict[str, Any]:
    """Decide whether a fail-branch revert is auto-revertible under the locked
    autonomy policy (runtime flags / reference relaunch only) or must go to the
    operator bundle (any file/config edit, or an unknown mechanism)."""
    joined = " \n".join(a.lower() for a in actions)
    needs_file_edit = any(m in joined for m in _FILE_EDIT_MARKERS)
    has_flag_action = any(m in joined for m in _AUTO_FLAG_MARKERS)
    has_relaunch_action = any(m in joined for m in _AUTO_RELAUNCH_MARKERS)

    pre = _preconditions(entry)
    flags_required = pre.get("flags_required") or {}
    flags_to_reset = sorted(str(k) for k in flags_required.keys())
    reference_lineup = pre.get("stack_lineup")

    # A runtime-flag revert is available if the branch says so OR the entry
    # asserted flags it set (which we can reset to restore the reference state).
    can_reset_flags = has_flag_action or bool(flags_to_reset)
    # A reference relaunch is available if the branch says so OR the entry named
    # the reference stack lineup to relaunch onto.
    can_relaunch = has_relaunch_action or bool(reference_lineup)

    return {
        "needs_file_edit": needs_file_edit,
        "can_reset_flags": can_reset_flags,
        "can_relaunch": can_relaunch,
        "flags_to_reset": flags_to_reset,
        "reference_lineup": reference_lineup,
    }


def _terminal_or_next(next_value: Any) -> tuple[str | None, str | None]:
    """Split a branch ``next`` into (terminal_ledger_status, next_task_id)."""
    if not next_value:
        return None, None
    text = str(next_value).strip()
    if text in LEDGER_STATUSES:
        return text, None
    return None, text


def _evidence_summary(signals: dict[str, Any], reasons: list[str]) -> str:
    parts = [
        f"safety_gate={signals.get('safety_gate')}",
        f"sequential={signals.get('sequential')}",
        f"infra_ok={signals.get('infra_ok')}",
    ]
    if reasons:
        parts.append("; ".join(reasons))
    return " | ".join(parts)


# ── the public decision function ───────────────────────────────────────────
def decide(
    entry: dict[str, Any],
    exec_result: Any,
    verifier_signals: dict[str, Any] | None = None,
) -> Verdict:
    """Map an executed entry's evidence onto a fork-action *plan*.

    ``entry`` — an inference-batch entry (``inference_batch.schema.json``).
    ``exec_result`` — dict describing whether the run completed & is trustworthy
        (keys: ``infra_ok`` bool, ``status`` str, ``completed`` bool, ``error``).
    ``verifier_signals`` — dict with ``safety_gate`` (PASS/WARN/REJECT) and
        ``sequential`` (confirmed/refuted/accumulating); may also carry an
        explicit ``category`` to force the fork.

    Returns a :class:`Verdict` plan. Does NOT execute reverts or write anything.
    """
    task_id = _entry_id(entry)
    title = str(entry.get("title") or task_id)

    category, reasons, signals = classify(entry, exec_result, verifier_signals)
    branch, gate_row, notes = _select_branch(entry, category)
    reasons = list(reasons) + list(notes)
    actions = _branch_actions(branch)
    gate_text = (gate_row or {}).get("gate") or "inference-batch fork"
    terminal_status, next_task = _terminal_or_next(
        (branch or {}).get("next") if isinstance(branch, dict) else None
    )

    # ── PASS ──────────────────────────────────────────────────────────
    if category == CAT_PASS:
        return Verdict(
            action=CAT_PASS,
            ledger_status=terminal_status or DONE_PASS,
            reasons=reasons,
            next_task=next_task,
            signals=signals,
            actions=actions,
        )

    # ── MARGINAL (observation; never gates, never reverts) ────────────
    if category == CAT_MARGINAL:
        return Verdict(
            action=CAT_MARGINAL,
            ledger_status=terminal_status or DONE_MARGINAL_OBS,
            reasons=reasons,
            next_task=next_task,
            signals=signals,
            actions=actions,
        )

    # ── INFRA (evidence untrustworthy; re-queue, no revert/bundle) ────
    if category == CAT_INFRA:
        classify_note = (branch or {}).get("classify") if isinstance(branch, dict) else None
        if classify_note:
            reasons.append(f"infra classify: {classify_note}")
        return Verdict(
            action=CAT_INFRA,
            ledger_status=INFRA_BLOCKED,
            reasons=reasons,
            next_task=None,  # infra re-queues the same task
            signals=signals,
            actions=actions,
        )

    # ── FAIL (decisive negative) -> autonomy policy on the revert ─────
    if category == CAT_FAIL:
        scope = _classify_revert_scope(actions, entry)
        # Policy: file/config edits are NEVER auto-reverted; and if we cannot
        # positively identify a flag-reset or reference relaunch, we do NOT act.
        auto_ok = (not scope["needs_file_edit"]) and (
            scope["can_reset_flags"] or scope["can_relaunch"]
        )
        if auto_ok:
            kinds = []
            steps: list[str] = []
            if scope["can_reset_flags"]:
                kinds.append("runtime_flags")
                if scope["flags_to_reset"]:
                    steps.append(
                        "reset runtime flags: " + ", ".join(scope["flags_to_reset"])
                    )
                else:
                    steps.append("reset the entry's runtime flags to reference values")
            if scope["can_relaunch"]:
                kinds.append("reference_relaunch")
                lineup = scope["reference_lineup"] or "reference lineup"
                steps.append(f"relaunch onto reference lineup: {lineup}")
            steps.extend(actions)
            revert = RevertPlan(
                auto=True,
                kind="+".join(kinds),
                flags_to_reset=scope["flags_to_reset"],
                reference_lineup=scope["reference_lineup"],
                steps=steps,
                note="auto-revert authorized: runtime flags / reference relaunch only",
            )
            reasons.append(
                "auto-revert planned (flags/reference-relaunch within autonomy policy)"
            )
            return Verdict(
                action=CAT_FAIL,
                ledger_status=FAILED_REVERTED,
                reasons=reasons,
                revert_plan=revert,
                next_task=next_task,
                signals=signals,
                actions=actions,
            )

        # Not auto-revertible -> operator bundle (HELD_OP_GATE).
        why = (
            "revert requires a file/config edit"
            if scope["needs_file_edit"]
            else "no runtime-flag reset or reference relaunch identified"
        )
        reasons.append(f"auto-revert withheld: {why} -> operator bundle")
        options = [
            f"Operator reverts {task_id} manually ({why}); loop marks FAILED_REVERTED after.",
            f"Accept {task_id} despite the negative verdict (operator override).",
            "Escalate: re-run with adjusted preconditions before deciding.",
        ]
        op_row = OpBundleRow(
            task_id=task_id,
            title=title,
            gate=gate_text,
            evidence=_evidence_summary(signals, reasons),
            options=options,
        )
        return Verdict(
            action=CAT_FAIL,
            ledger_status=HELD_OP_GATE,
            reasons=reasons,
            op_bundle_row=op_row,
            next_task=next_task,
            signals=signals,
            actions=actions,
        )

    # ── AMBIGUOUS -> operator bundle with pre-formed options ──────────
    pre = _preconditions(entry)
    op_gated = bool(pre.get("operator_gates"))
    held_status = HELD_OP_GATE if (op_gated or terminal_status == HELD_OP_GATE) else HELD_AMBIGUOUS
    options: list[str] = []
    if actions:
        options.extend(actions)
    if op_gated:
        options.append(
            "Grant/deny operator gate(s): " + ", ".join(str(g) for g in pre["operator_gates"])
        )
    options.extend(
        [
            f"Adjudicate {task_id}: keep (mark DONE_*) or revert (mark FAILED_REVERTED).",
            "Request more evidence: re-run under a cleaner window before deciding.",
        ]
    )
    op_row = OpBundleRow(
        task_id=task_id,
        title=title,
        gate=gate_text,
        evidence=_evidence_summary(signals, reasons),
        options=options,
    )
    return Verdict(
        action=CAT_AMBIGUOUS,
        ledger_status=held_status,
        reasons=reasons,
        op_bundle_row=op_row,
        next_task=next_task if held_status != HELD_OP_GATE else None,
        signals=signals,
        actions=actions,
    )
