"""TD-7: replay the recorded routing corpus through the typed-decision shadow.

One recorded routing decision becomes one typed-decision call: the state is
the recorded ``context``, the question is a single ``choice`` over every
distinct routing action in the snapshot, and the typed answer is compared
against the recorded incumbent action. The recorded ``outcome`` is used ONLY
as a calibration label against the typed confidence.

Label provenance (READ THIS BEFORE RE-RUNNING)
----------------------------------------------
The LIVE ``episodic.db`` is **not admissible** as ground truth: the
2026-09-17 leak purge modified it (see ``scripts/analysis/
escalation_prediction_probe.py`` and ``handoffs/active/
learned-routing-controller.md``). This module refuses the live database and
requires a frozen pre-purge snapshot, identified by a DB whose
``max(created_at)`` precedes ``PURGE_DATE`` or by the known 2026-04-15 backup
(``episodic.db.backup-20260415``). Every receipt carries the snapshot path,
its SHA-256, and the admissibility reason, and its labels are read only from
that frozen file.

A snapshot path is either a DIRECTORY containing ``episodic.db`` (and
optionally ``embeddings.faiss``, per the escalation-probe convention — the
replay itself never reconstructs vectors), or a direct path to a frozen
``episodic.db`` file. The live DB path is refused even if passed to a
directory argument.

Native then JSON, per the runner's own dispatch contract
---------------------------------------------------------
``mode="native"`` is attempted first (``cue_style="id_only"``). The native
runner never falls back itself: a question whose candidate labels are
multi-token or whose tokenizer is unavailable fails closed with a typed
``ParseFailure`` and is NOT sent to the model. This module re-asks exactly
those questions in ``mode="json"`` — the correctness fallback the native
contract names — and records the per-row path (``native`` / ``json`` /
``unresolved``) plus both failure lists, so the receipt never lies about how
each answer was produced.

TD-9 code map and incumbent-aware framing
-----------------------------------------
The TD-7 run resolved **0/200** rows natively: every recorded routing action is
a multi-token label (``frontdoor`` = ``front``+``door``), so the native arm
failed the whole question closed and all rows took the JSON fallback. TD-9
maps every distinct action to a deterministic single-token code (``A``..``Z``,
then ``0``..``9``) and exposes the mapping in the question text
(``A = frontdoor``); the native grammar binds the codes, and the chosen code is
mapped back to the action in code. The incumbent action stays among the
candidates, the per-row framing names it and asks for the best role for the
task, and both the chosen code and the incumbent are recorded.

**The frozen label still describes the INCUMBENT action's outcome**, not the
chosen one. For a disagreeing row it is not a label for the chosen action, so
the agreement rate and every confidence-versus-label metric (AUROC, ECE) are
**informative-only** until a counterfactual design labels the counterfactual
outcome of the chosen action; the receipt carries this caveat verbatim.

Measurement contract:
    * ``--dry-run`` reads the snapshot and prints the plan; no model call, no
      receipt.
    * Without ``--live`` and without ``--dry-run`` the CLI refuses (exit 2).
    * A mock primitives object is refused; a receipt NEVER carries fabricated
      numbers.
    * Calibration reuses ``src.llm_primitives/stat_tests.py`` (ECE via
      ``expected_calibration_error`` / ``compute_calibration_metrics``,
      Wilson interval for agreement); the one-line Brier and the reliability
      bins live here because ``stat_tests`` deliberately does not own them.
    * Confidence is the LOCAL typed-decision statistic, not calibrated
      probability; the calibration block is the measurement of how far it
      is from one. The frozen label describes the INCUMBENT action's outcome,
      so for a disagreeing row it is not a label for the chosen action; the
      ``calibration_agreeing_only`` sub-block restricts to rows where the
      chosen action IS the incumbent.

CLI::

    python -m src.typed_decisions.routing_replay --list-snapshots
    python -m src.typed_decisions.routing_replay --dry-run --snapshot <dir> --n 60
    python -m src.typed_decisions.routing_replay --live --snapshot <dir> --n 60 \\
        --role frontdoor --server-url http://127.0.0.1:8199 --receipt <path>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sqlite3
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.llm_primitives.stat_tests import (
    compute_calibration_metrics,
    wilson_interval,
)
from src.typed_decisions.runner import run_typed_decisions
from src.typed_decisions.types import Decision, DecisionResult, Question, QuestionKind

__all__ = [
    "DEFAULT_N",
    "DEFAULT_ROLE",
    "DEFAULT_SEED",
    "DEFAULT_SERVER_URL",
    "DEFAULT_STATE_BUDGET_CHARS",
    "KNOWN_2026_04_15_SNAPSHOT",
    "LIVE_DB_PATH",
    "PURGE_DATE",
    "ReplayError",
    "RoutingCodeMap",
    "RoutingRow",
    "RowOutcome",
    "Snapshot",
    "aggregate",
    "build_code_map",
    "build_question",
    "calibration_stats",
    "check_code_tokens",
    "default_tokenize_fn",
    "discover_snapshots",
    "load_rows",
    "main",
    "prepare_state",
    "require_live_primitives",
    "resolve_snapshot",
    "run_replay",
    "run_row",
    "sample_rows",
]

# ── constants ─────────────────────────────────────────────────────────────

DEFAULT_N = 60
DEFAULT_SEED = 20260918
DEFAULT_ROLE = "frontdoor"
DEFAULT_SERVER_URL = "http://127.0.0.1:8199"
DEFAULT_STATE_BUDGET_CHARS = 4000
DEFAULT_JSON_N_TOKENS = 768
DEFAULT_CUE_STYLE = "id_only"
DEFAULT_ECE_BINS = 10

ENV_SERVER = "TD_ROUTING_REPLAY_SERVER"
ENV_ROLE = "TD_ROUTING_REPLAY_ROLE"

# TD-9: single-token routing codes. A..Z first (matching the handoff's A..E
# obligation), then digits 0..9; a corpus with more than 36 distinct actions is
# refused rather than given a multi-character code.
_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# The acceptance bar TD-9 was written against: the native arm must resolve at
# least this fraction of rows without the JSON fallback.
NATIVE_RESOLUTION_ACCEPTANCE = 0.95

LIVE_DB_PATH = Path(
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db"
)
KNOWN_2026_04_15_SNAPSHOT = Path(
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/"
    "episodic.db.backup-20260415"
)
PURGE_DATE = "2026-09-17"

SNAPSHOT_DB_NAME = "episodic.db"
SNAPSHOT_FAISS_NAME = "embeddings.faiss"

ROUTING_SQL = """
SELECT embedding_idx, action, outcome, context
FROM memories
WHERE action_type='routing' AND outcome IN ('success','failure')
"""

QUESTION_ID = "routing_action"

_ROUTING_QUESTION = (
    "Which recorded routing action should handle the task described in STATE? "
    "Answer with exactly one of the declared action classes."
)

_ROUTING_CODE_QUESTION = "Which routing action is the best role for the task described in STATE?"

_METRIC_DIRECTIONS: dict[str, str] = {
    "agreement.rate": "higher_is_better",
    "agreement.wilson_95_low": "higher_is_better",
    "calibration.ece": "lower_is_better",
    "calibration.brier": "lower_is_better",
    "calibration.mae": "lower_is_better",
    "calibration.auroc": "higher_is_better",
    "calibration.top1_accuracy": "higher_is_better",
    "calibration.bottom1_accuracy": "lower_is_better",
    "calibration.spearman_rho": "higher_is_better",
    "path_split.native_resolution_rate": "higher_is_better",
    "path_split.unresolved": "lower_is_better",
    "wall_ms_total": "lower_is_better",
}


class ReplayError(RuntimeError):
    """The replay cannot produce an admissible measurement.

    Raised for a missing/inadmissible snapshot, a mock primitives object, a
    malformed corpus, or a CLI gate violation. A fabricated receipt is worse
    than no receipt.
    """


# ── snapshot provenance ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Snapshot:
    """A frozen store plus the provenance the receipt must carry.

    ``db_sha256`` is the identity of the exact label source;
    ``admissibility_reason`` names which admission test passed. ``faiss_path``
    is present only when the snapshot is a directory containing
    ``embeddings.faiss``; this replay never opens it (no vectors are needed).
    """

    path: Path
    db_path: Path
    faiss_path: Path | None
    db_sha256: str
    faiss_sha256: str | None
    db_bytes: int
    db_mtime_utc: str
    max_created_at: str | None
    max_updated_at: str | None
    admissible: bool
    admissibility_reason: str

    def provenance(self) -> dict[str, Any]:
        """JSON-safe provenance block for the receipt."""
        return {
            "path": str(self.path),
            "db_path": str(self.db_path),
            "db_sha256": self.db_sha256,
            "db_bytes": self.db_bytes,
            "db_mtime_utc": self.db_mtime_utc,
            "faiss_path": str(self.faiss_path) if self.faiss_path else None,
            "faiss_sha256": self.faiss_sha256,
            "max_created_at": self.max_created_at,
            "max_updated_at": self.max_updated_at,
            "admissible": self.admissible,
            "admissibility_reason": self.admissibility_reason,
        }


def resolve_snapshot(path: str | Path, *, purge_date: str = PURGE_DATE) -> Snapshot:
    """Resolve, hash and admit a frozen snapshot.

    Raises:
        ReplayError: when the path does not exist, would resolve to the live
            database, or fails the pre-purge admission test.
    """
    raw = Path(path)
    if not raw.exists():
        raise ReplayError(f"snapshot path does not exist: {raw}")
    if raw.is_dir():
        db_path = raw / SNAPSHOT_DB_NAME
        faiss_path: Path | None = raw / SNAPSHOT_FAISS_NAME
        if not faiss_path.exists():
            faiss_path = None
    else:
        db_path = raw
        # A direct file argument carries no faiss sibling by provenance: the
        # live sessions/ directory also holds an embeddings.faiss and must
        # never be presented as part of a frozen snapshot.
        faiss_path = None
    if not db_path.exists():
        raise ReplayError(f"snapshot has no {SNAPSHOT_DB_NAME}: {db_path}")
    if db_path.resolve() == LIVE_DB_PATH.resolve():
        raise ReplayError(
            "refusing the LIVE episodic.db: its outcomes were changed by the "
            "2026-09-17 leak purge and are not admissible ground truth"
        )

    max_created_at, max_updated_at = _db_max_timestamps(db_path)
    known_frozen = db_path.resolve() == KNOWN_2026_04_15_SNAPSHOT.resolve()
    if known_frozen:
        admissible, reason = True, "known_2026_04_15_frozen_snapshot"
    elif max_created_at is not None and max_created_at < purge_date:
        admissible, reason = True, "max_created_at_precedes_purge"
    else:
        admissible, reason = False, "max_created_at_not_before_purge"
    if not admissible:
        raise ReplayError(
            "snapshot is not admissible: "
            f"max(created_at)={max_created_at!r} is not before {purge_date} and the "
            f"path is not the known 2026-04-15 frozen snapshot ({KNOWN_2026_04_15_SNAPSHOT})"
        )

    stat = db_path.stat()
    return Snapshot(
        path=raw,
        db_path=db_path,
        faiss_path=faiss_path,
        db_sha256=_sha256_file(db_path),
        faiss_sha256=_sha256_file(faiss_path) if faiss_path is not None else None,
        db_bytes=stat.st_size,
        db_mtime_utc=_utc_from_epoch(stat.st_mtime),
        max_created_at=max_created_at,
        max_updated_at=max_updated_at,
        admissible=admissible,
        admissibility_reason=reason,
    )


def discover_snapshots(
    roots: Sequence[str | Path],
    *,
    max_depth: int = 4,
) -> list[dict[str, Any]]:
    """List directories under ``roots`` holding BOTH snapshot store files."""
    found: dict[str, dict[str, Any]] = {}
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            depth = len(Path(dirpath).relative_to(base).parts)
            if depth >= max_depth:
                dirnames[:] = []
            if SNAPSHOT_DB_NAME in filenames and SNAPSHOT_FAISS_NAME in filenames:
                db = Path(dirpath) / SNAPSHOT_DB_NAME
                faiss = Path(dirpath) / SNAPSHOT_FAISS_NAME
                found[str(db.resolve())] = {
                    "dir": dirpath,
                    "db_bytes": db.stat().st_size,
                    "db_mtime_utc": _utc_from_epoch(db.stat().st_mtime),
                    "faiss_bytes": faiss.stat().st_size,
                    "is_live": db.resolve() == LIVE_DB_PATH.resolve(),
                }
    return sorted(found.values(), key=lambda record: record["dir"])


def _db_max_timestamps(db_path: Path) -> tuple[str | None, str | None]:
    """Return ``(max(created_at), max(updated_at))`` from a read-only DB."""
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise ReplayError(f"cannot open snapshot read-only: {db_path}: {exc}") from exc
    try:
        created = con.execute("SELECT max(created_at) FROM memories").fetchone()[0]
        updated = con.execute("SELECT max(updated_at) FROM memories").fetchone()[0]
    except sqlite3.Error as exc:
        raise ReplayError(f"snapshot {db_path} has no usable memories table: {exc}") from exc
    finally:
        con.close()
    return (
        str(created) if created is not None else None,
        str(updated) if updated is not None else None,
    )


# ── corpus load and deterministic sampling ────────────────────────────────


@dataclass(frozen=True)
class RoutingRow:
    """One recorded routing decision (state, incumbent action, frozen label)."""

    embedding_idx: int | None
    action: str
    outcome: str
    context: str

    @property
    def label(self) -> bool:
        """Ground-truth label from the frozen snapshot: outcome == success."""
        return self.outcome == "success"

    def canonical_key(self) -> tuple[Any, ...]:
        """Total, DB-independent ordering key for deterministic sampling."""
        return (
            self.embedding_idx is None,
            self.embedding_idx if self.embedding_idx is not None else -1,
            self.action,
            self.outcome,
            self.context,
        )


def load_rows(db_path: str | Path, *, sql: str = ROUTING_SQL) -> list[RoutingRow]:
    """Read the recorded routing corpus from a snapshot, read-only."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        raw = con.execute(sql).fetchall()
    except sqlite3.Error as exc:
        raise ReplayError(f"cannot read routing rows from {db_path}: {exc}") from exc
    finally:
        con.close()
    return [
        RoutingRow(
            embedding_idx=row[0] if row[0] is None else int(row[0]),
            action=str(row[1] or ""),
            outcome=str(row[2] or ""),
            context=str(row[3] or ""),
        )
        for row in raw
    ]


def sample_rows(
    rows: Sequence[RoutingRow],
    n: int,
    seed: int,
) -> list[RoutingRow]:
    """Deterministic sample: canonical sort, then seeded ``random.Random``.

    Shuffling the input cannot change the sample; the result is re-sorted by
    the canonical key so the receipt order is also seed-stable. ``n`` greater
    than the frame returns the whole frame.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    frame = sorted(rows, key=RoutingRow.canonical_key)
    if n >= len(frame):
        return frame
    sampled = random.Random(seed).sample(frame, n)
    return sorted(sampled, key=RoutingRow.canonical_key)


def load_options(rows: Sequence[RoutingRow]) -> tuple[str, ...]:
    """Distinct non-empty routing actions, sorted (the choice's option set)."""
    options = sorted({row.action for row in rows if row.action.strip()})
    if len(options) < 2:
        raise ReplayError(
            f"the corpus declares {len(options)} distinct non-empty action(s); "
            "a choice question needs at least 2"
        )
    return tuple(options)


# ── TD-9: deterministic single-token code map ─────────────────────────────


@dataclass(frozen=True)
class RoutingCodeMap:
    """A deterministic routing-action -> single-token-code map (TD-9).

    ``actions`` is the input order (``load_options`` returns sorted distinct
    actions) and ``codes`` is aligned index-for-index. The mapping is total and
    bidirectional: every action gets exactly one code and every code maps to
    exactly one action. Codes are single letters ``A``..``Z`` first, then
    digits ``0``..``9``; more than 36 classes raise ``ReplayError`` rather than
    generating a multi-character code the native grammar could not bind.
    """

    actions: tuple[str, ...]
    codes: tuple[str, ...]

    @property
    def code_to_action(self) -> dict[str, str]:
        return dict(zip(self.codes, self.actions))

    @property
    def action_to_code(self) -> dict[str, str]:
        return dict(zip(self.actions, self.codes))

    def code_for(self, action: str) -> str | None:
        """The code bound to ``action``, or ``None`` when it is not a candidate."""
        return self.action_to_code.get(action)

    def action_for(self, code: str) -> str | None:
        """The action bound to ``code``, or ``None`` when the code is unknown."""
        return self.code_to_action.get(code)

    def legend(self) -> str:
        """The ``"A = frontdoor; B = SELF"`` text exposed to the model."""
        return "; ".join(f"{code} = {action}" for code, action in zip(self.codes, self.actions))

    def to_record(self) -> dict[str, Any]:
        """JSON-safe map block for the receipt/config."""
        return {
            "codes": list(self.codes),
            "actions": list(self.actions),
            "code_to_action": self.code_to_action,
            "action_to_code": self.action_to_code,
        }


def build_code_map(options: Sequence[str]) -> RoutingCodeMap:
    """Bind each distinct routing action to a deterministic single-token code.

    Codes follow the input order, so the sorted ``load_options`` result gives a
    receipt-stable map. A duplicate or empty action is a caller bug and raises
    ``ValueError``; more classes than the alphabet raises ``ReplayError``.
    """
    actions = tuple(str(action) for action in options)
    if len(set(actions)) != len(actions):
        raise ValueError("routing code map requires distinct actions")
    if any(not action.strip() for action in actions):
        raise ValueError("routing code map requires non-empty actions")
    if len(actions) > len(_CODE_ALPHABET):
        raise ReplayError(
            f"{len(actions)} routing actions exceed the {len(_CODE_ALPHABET)} single-token "
            "codes available (A-Z, 0-9); the native grammar cannot bind a longer code"
        )
    return RoutingCodeMap(actions=actions, codes=tuple(_CODE_ALPHABET[: len(actions)]))


def _code_variants(code: str) -> tuple[str, ...]:
    """The code texts the native candidate binder probes (bare and space-prefixed)."""
    return (code, " " + code)


def check_code_tokens(code_map: RoutingCodeMap, tokenize_fn: Any) -> dict[str, Any]:
    """Probe every code (and its space-prefixed variant) for single-token binding.

    The native arm binds the exact token id(s) of a candidate text; a code that
    is not exactly one token (with or without a leading space) excludes the
    whole question, so this check runs BEFORE the model and refuses the run when
    any code would fall back to JSON.

    Returns:
        A JSON-safe record: ``ok`` is True only when every probe resolved to
        exactly one id; ``multi_token`` / ``unavailable`` list the offending
        probe texts; ``probes`` carries the raw id lists.
    """
    probes: dict[str, dict[str, Any]] = {}
    multi_token: list[str] = []
    unavailable: list[str] = []
    seen_ids: dict[int, str] = {}
    collisions: list[str] = []
    for code in code_map.codes:
        code_probes: dict[str, Any] = {}
        for text in _code_variants(code):
            try:
                ids = tokenize_fn(text)
            except Exception:  # noqa: BLE001 - any failure is "no answer"
                ids = None
            if ids is None:
                code_probes[text] = None
                unavailable.append(text)
                continue
            ids = list(ids)
            code_probes[text] = ids
            if len(ids) != 1:
                multi_token.append(text)
                continue
            token_id = ids[0]
            other = seen_ids.get(token_id)
            if other is not None and other != code:
                collisions.append(f"{other!r} and {code!r} both tokenize to id {token_id}")
            seen_ids[token_id] = code
        probes[code] = code_probes
    return {
        "ok": not multi_token and not unavailable and not collisions,
        "multi_token": multi_token,
        "unavailable": unavailable,
        "collisions": collisions,
        "probes": probes,
    }


def default_tokenize_fn(primitives: Any, role: str) -> Any:
    """Resolve the native runner's HTTP ``/tokenize`` seam for one role.

    Lazy import: ``native.py`` imports this module's runner contract (through
    ``runner``), so a module-level import here would close a cycle. Returns the
    resolver's tokenizer object (``None`` when no backend URL could be found);
    callers that receive an ``_HttpTokenizer`` should ``close()`` it.
    """
    from src.typed_decisions.native import _resolve_tokenize_fn

    return _resolve_tokenize_fn(primitives, role)


# ── state and question construction ───────────────────────────────────────


def prepare_state(context: str, budget: int = DEFAULT_STATE_BUDGET_CHARS) -> tuple[str, bool]:
    """Truncate an oversized context to ``budget`` chars. Returns (state, cut)."""
    if budget <= 0:
        raise ValueError(f"state budget must be > 0, got {budget}")
    text = str(context or "")
    if len(text) <= budget:
        return text, False
    return text[:budget] + f"\n[... truncated at {budget} chars]", True


def build_question(
    options: Sequence[str],
    *,
    code_map: RoutingCodeMap | None = None,
    incumbent: str | None = None,
) -> Question:
    """One choice question over the snapshot's action classes.

    Without ``code_map`` this is the TD-7 question: option labels are the raw
    routing action names. With a ``code_map`` (TD-9) the declared options are
    the single-token codes, the question text exposes the ``A = action`` legend,
    and ``incumbent`` (when given) is named as the recorded incumbent action so
    the framing is incumbent-aware while still asking for the best role for the
    task. The incumbent must be one of the declared actions.
    """
    if code_map is None:
        if incumbent is not None:
            raise ValueError("incumbent-aware framing requires a code map")
        return Question(
            id=QUESTION_ID,
            kind=QuestionKind.CHOICE,
            text=_ROUTING_QUESTION,
            options=tuple(options),
            criteria=("Pick one recorded action class; do not answer the request itself.",),
        )

    declared = tuple(str(action) for action in options)
    if declared != code_map.actions:
        raise ValueError(
            "options do not match the code map actions; build both from the same load_options()"
        )
    legend = code_map.legend()
    text = f"{_ROUTING_CODE_QUESTION} Declared codes: {legend}."
    criteria: list[str] = [
        "Pick the code of the best role for the task; do not answer the request itself.",
        f"code map: {legend}",
    ]
    if incumbent is not None:
        incumbent_code = code_map.code_for(incumbent)
        if incumbent_code is None:
            raise ValueError(f"incumbent {incumbent!r} is not one of the declared code map actions")
        text += f" The recorded incumbent action is {incumbent_code} = {incumbent}."
        criteria.append(f"incumbent recorded action: {incumbent_code} = {incumbent}")
    text += " Answer with exactly one of the declared codes."
    return Question(
        id=QUESTION_ID,
        kind=QuestionKind.CHOICE,
        text=text,
        options=code_map.codes,
        criteria=tuple(criteria),
    )


# ── per-row replay ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RowOutcome:
    """One replayed row: what was chosen, by which path, and at what cost."""

    position: int
    incumbent: str
    label: bool
    state_sha256: str
    state_chars: int
    state_truncated: bool
    action: str | None
    confidence: float | None
    probabilities: Mapping[str, float] | None
    path: str
    native_failures: tuple[Mapping[str, str], ...]
    json_failures: tuple[Mapping[str, str], ...]
    prompt_sha256: str | None
    elapsed_ms: float
    chosen_code: str | None = None
    incumbent_code: str | None = None

    def to_record(self) -> dict[str, Any]:
        """JSON-safe row record (probabilities key-sorted for stability)."""
        probabilities: dict[str, float] | None = None
        if self.probabilities is not None:
            probabilities = {
                str(label): float(value)
                for label, value in sorted(
                    self.probabilities.items(), key=lambda item: str(item[0])
                )
            }
        return {
            "position": self.position,
            "incumbent": self.incumbent,
            "label": self.label,
            "state_sha256": self.state_sha256,
            "state_chars": self.state_chars,
            "state_truncated": self.state_truncated,
            "path": self.path,
            "action": self.action,
            "chosen_code": self.chosen_code,
            "incumbent_code": self.incumbent_code,
            "confidence": self.confidence,
            "probabilities": probabilities,
            "native_failures": [dict(failure) for failure in self.native_failures],
            "json_failures": [dict(failure) for failure in self.json_failures],
            "prompt_sha256": self.prompt_sha256,
            "elapsed_ms": self.elapsed_ms,
        }


def run_row(
    primitives: Any,
    row: RoutingRow,
    question: Question,
    *,
    position: int,
    role: str,
    state_budget: int = DEFAULT_STATE_BUDGET_CHARS,
    json_n_tokens: int = DEFAULT_JSON_N_TOKENS,
    cue_style: str = DEFAULT_CUE_STYLE,
    tokenize_fn: Any = None,
    code_map: RoutingCodeMap | None = None,
) -> RowOutcome:
    """Replay one row: native first, JSON only for questions native excluded.

    With a ``code_map`` (TD-9) the question carries single-token codes as
    options; the decision's code and probability keys are mapped back to the
    routing actions here, and both the chosen code and the incumbent's code are
    recorded. An unmappable code is a harness bug, not a model answer: it
    raises ``ReplayError`` rather than fabricating a role.
    """
    started = time.perf_counter()
    state, truncated = prepare_state(row.context, state_budget)
    state_sha256 = _sha256_text(state)

    native = run_typed_decisions(
        primitives,
        state=state,
        questions=(question,),
        role=role,
        mode="native",
        cue_style=cue_style,
        tokenize_fn=tokenize_fn,
    )
    native_failures = _failure_records(native)
    native_decision = _decision_for(native, question.id)
    if native_decision is not None:
        return _outcome(
            position=position,
            row=row,
            state_sha256=state_sha256,
            state_chars=len(state),
            truncated=truncated,
            decision=native_decision,
            path="native",
            native_failures=native_failures,
            json_failures=(),
            prompt_sha256=native.prompt_sha256,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            code_map=code_map,
        )

    json_result = run_typed_decisions(
        primitives,
        state=state,
        questions=(question,),
        role=role,
        mode="json",
        n_tokens=json_n_tokens,
    )
    json_failures = _failure_records(json_result)
    json_decision = _decision_for(json_result, question.id)
    if json_decision is not None:
        return _outcome(
            position=position,
            row=row,
            state_sha256=state_sha256,
            state_chars=len(state),
            truncated=truncated,
            decision=json_decision,
            path="json",
            native_failures=native_failures,
            json_failures=json_failures,
            prompt_sha256=json_result.prompt_sha256,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            code_map=code_map,
        )

    return _outcome(
        position=position,
        row=row,
        state_sha256=state_sha256,
        state_chars=len(state),
        truncated=truncated,
        decision=None,
        path="unresolved",
        native_failures=native_failures,
        json_failures=json_failures,
        prompt_sha256=json_result.prompt_sha256 or native.prompt_sha256,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
        code_map=code_map,
    )


def _outcome(
    *,
    position: int,
    row: RoutingRow,
    state_sha256: str,
    state_chars: int,
    truncated: bool,
    decision: Decision | None,
    path: str,
    native_failures: tuple[Mapping[str, str], ...],
    json_failures: tuple[Mapping[str, str], ...],
    prompt_sha256: str | None,
    elapsed_ms: float,
    code_map: RoutingCodeMap | None = None,
) -> RowOutcome:
    chosen_code: str | None = None
    incumbent_code = code_map.code_for(row.action) if code_map is not None else None
    if decision is None:
        action: str | None = None
        confidence: float | None = None
        probabilities: Mapping[str, float] | None = None
    elif code_map is None:
        action = str(decision.value)
        confidence = float(decision.confidence)
        probabilities = {
            str(label): float(value) for label, value in decision.probabilities.items()
        }
    else:
        chosen_code = str(decision.value)
        action = code_map.action_for(chosen_code)
        if action is None:
            raise ReplayError(
                f"chosen code {chosen_code!r} is not in the routing code map "
                f"{code_map.code_to_action!r}; the question and map disagree"
            )
        confidence = float(decision.confidence)
        probabilities = {}
        for label, value in decision.probabilities.items():
            mapped = code_map.action_for(str(label))
            if mapped is None:
                raise ReplayError(
                    f"probability label {label!r} is not in the routing code map "
                    f"{code_map.code_to_action!r}; the question and map disagree"
                )
            probabilities[mapped] = float(value)
    return RowOutcome(
        position=position,
        incumbent=row.action,
        label=row.label,
        state_sha256=state_sha256,
        state_chars=state_chars,
        state_truncated=truncated,
        action=action,
        confidence=confidence,
        probabilities=probabilities,
        path=path,
        native_failures=native_failures,
        json_failures=json_failures,
        prompt_sha256=prompt_sha256,
        elapsed_ms=elapsed_ms,
        chosen_code=chosen_code,
        incumbent_code=incumbent_code,
    )


def _decision_for(result: DecisionResult, question_id: str) -> Decision | None:
    for decision in result.decisions:
        if str(decision.question_id) == question_id:
            return decision
    return None


def _failure_records(result: DecisionResult) -> tuple[Mapping[str, str], ...]:
    return tuple(
        {"reason": str(failure.reason), "detail": str(failure.detail)}
        for failure in result.failures
    )


# ── aggregation ───────────────────────────────────────────────────────────


def aggregate(outcomes: Sequence[RowOutcome], *, n_bins: int = DEFAULT_ECE_BINS) -> dict[str, Any]:
    """Agreement, path split, failures, calibration and wall-time aggregates."""
    decided = [outcome for outcome in outcomes if outcome.action is not None]
    unresolved = [outcome for outcome in outcomes if outcome.action is None]
    agreeing = [outcome for outcome in decided if outcome.action == outcome.incumbent]

    rate = (len(agreeing) / len(decided)) if decided else None
    by_action: dict[str, dict[str, Any]] = {}
    for outcome in decided:
        bucket = by_action.setdefault(outcome.incumbent, {"n": 0, "agreeing": 0})
        bucket["n"] += 1
        bucket["agreeing"] += 1 if outcome.action == outcome.incumbent else 0
    for bucket in by_action.values():
        bucket["rate"] = bucket["agreeing"] / bucket["n"]

    failure_counts: Counter[str] = Counter()
    for outcome in outcomes:
        for failure in (*outcome.native_failures, *outcome.json_failures):
            failure_counts[str(failure.get("reason", "unknown"))] += 1

    paired = [
        (outcome.confidence, float(outcome.label))
        for outcome in decided
        if outcome.confidence is not None
    ]
    agreeing_paired = [
        (outcome.confidence, float(outcome.label))
        for outcome in agreeing
        if outcome.confidence is not None
    ]
    elapsed = [outcome.elapsed_ms for outcome in outcomes]
    return {
        "n_rows": len(outcomes),
        "n_decided": len(decided),
        "n_unresolved": len(unresolved),
        "agreement": {
            "n_agreeing": len(agreeing),
            "n_disagreeing": len(decided) - len(agreeing),
            "rate": rate,
            "wilson_95": list(wilson_interval(len(agreeing), len(decided))) if decided else None,
            "by_incumbent_action": by_action,
        },
        "path_split": {
            "native": sum(1 for outcome in decided if outcome.path == "native"),
            "json": sum(1 for outcome in decided if outcome.path == "json"),
            "unresolved": len(unresolved),
            "native_resolution_rate": (
                sum(1 for outcome in decided if outcome.path == "native") / len(outcomes)
                if outcomes
                else None
            ),
        },
        "acceptance": {
            "native_resolution_ge_95pct": (
                bool(outcomes)
                and sum(1 for outcome in decided if outcome.path == "native") / len(outcomes)
                >= NATIVE_RESOLUTION_ACCEPTANCE
            ),
            "native_resolution_threshold": NATIVE_RESOLUTION_ACCEPTANCE,
        },
        "failures": {
            "total": int(sum(failure_counts.values())),
            "by_reason": dict(sorted(failure_counts.items())),
        },
        "calibration": calibration_stats(paired, n_bins=n_bins),
        "calibration_agreeing_only": calibration_stats(agreeing_paired, n_bins=n_bins),
        "label_base_rate": (
            sum(1 for outcome in decided if outcome.label) / len(decided) if decided else None
        ),
        "wall_ms_total": float(sum(elapsed)),
        "wall_ms_mean": (float(sum(elapsed)) / len(elapsed)) if elapsed else None,
        "wall_ms_max": max(elapsed) if elapsed else None,
    }


def calibration_stats(
    pairs: Sequence[tuple[float, float]],
    *,
    n_bins: int = DEFAULT_ECE_BINS,
) -> dict[str, Any]:
    """ECE/Brier/AUROC/MAE + reliability bins over (confidence, label) pairs.

    Uses ``stat_tests`` for every metric it owns; Brier is the one-line mean
    squared error ``stat_tests`` documents as deliberately local, and the
    reliability bins are the equal-width bins the stat-tests ECE counts over,
    so the bins explain the reported ECE exactly.
    """
    if not pairs:
        empty = {key: None for key in compute_calibration_metrics([], [])}
        empty.update({"brier": None, "base_rate": None, "reliability_bins": []})
        return empty
    confidences = [float(confidence) for confidence, _ in pairs]
    labels = [float(label) for _, label in pairs]
    metrics = compute_calibration_metrics(confidences, labels)
    brier = sum((c - y) ** 2 for c, y in zip(confidences, labels)) / len(pairs)
    return {
        "n": len(pairs),
        "ece": metrics["ece"],
        "brier": brier,
        "auroc": metrics["auroc"],
        "top1_accuracy": metrics["top1_accuracy"],
        "bottom1_accuracy": metrics["bottom1_accuracy"],
        "spearman_rho": metrics["spearman_rho"],
        "mae": metrics["mae"],
        "base_rate": sum(labels) / len(labels),
        "reliability_bins": reliability_bins(confidences, labels, n_bins=n_bins),
    }


def reliability_bins(
    confidences: Sequence[float],
    labels: Sequence[float],
    *,
    n_bins: int = DEFAULT_ECE_BINS,
) -> list[dict[str, Any]]:
    """Equal-width reliability bins, identical edges to ``stat_tests`` ECE."""
    bins: list[dict[str, Any]] = []
    total = len(confidences)
    for index in range(n_bins):
        lo = index / n_bins
        hi = (index + 1) / n_bins
        if index < n_bins - 1:
            members = [k for k in range(total) if lo <= confidences[k] < hi]
        else:
            members = [k for k in range(total) if lo <= confidences[k] <= hi]
        count = len(members)
        bins.append(
            {
                "bin": index,
                "lo": lo,
                "hi": hi,
                "n": count,
                "mean_confidence": (
                    sum(confidences[k] for k in members) / count if count else None
                ),
                "accuracy": sum(labels[k] for k in members) / count if count else None,
            }
        )
    return bins


# ── top-level replay ──────────────────────────────────────────────────────


def run_replay(
    rows: Sequence[RoutingRow],
    *,
    snapshot_provenance: Mapping[str, Any],
    primitives: Any = None,
    n: int = DEFAULT_N,
    seed: int = DEFAULT_SEED,
    role: str = DEFAULT_ROLE,
    cue_style: str = DEFAULT_CUE_STYLE,
    state_budget: int = DEFAULT_STATE_BUDGET_CHARS,
    json_n_tokens: int = DEFAULT_JSON_N_TOKENS,
    tokenize_fn: Any = None,
    receipt_path: str | Path | None = None,
    artifacts_dir: str | Path | None = None,
    dry_run: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Replay N sampled rows; return the receipt (and write it unless dry-run).

    Every row's question is built from the deterministic TD-9 code map with the
    row's own incumbent named in the framing. When a ``tokenize_fn`` is given,
    every code is probed for single-token binding BEFORE the first model call
    and a non-single-token code aborts the run (``ReplayError``): the native
    arm would otherwise fall back to JSON for every row.
    """
    frame = [row for row in rows if row.action.strip()]
    excluded_empty_action = len(rows) - len(frame)
    options = load_options(frame)
    code_map = build_code_map(options)
    sample = sample_rows(frame, n, seed)
    started_at = timestamp or _utc_now()

    config = {
        "n": int(n),
        "seed": int(seed),
        "role": role,
        "cue_style": cue_style,
        "mode": "native+json_fallback",
        "state_budget_chars": int(state_budget),
        "json_n_tokens": int(json_n_tokens),
        "question_id": QUESTION_ID,
        "framing": "incumbent_aware_code_map",
        "question_text": _ROUTING_CODE_QUESTION,
        "options": list(options),
        "code_map": code_map.to_record(),
    }
    plan = {
        "plan": "td7-routing-replay",
        "dry_run": True,
        "timestamp": started_at,
        "snapshot": dict(snapshot_provenance),
        "config": config,
        "corpus": {
            "routing_rows": len(rows),
            "rows_with_action": len(frame),
            "excluded_empty_action_rows": excluded_empty_action,
            "distinct_actions": len(options),
        },
        "sample": _plan_rows(sample, state_budget),
        "estimated_calls": {
            "native_attempts": len(sample),
            "json_fallbacks_max": len(sample),
        },
    }
    if dry_run:
        return plan

    require_live_primitives(primitives)
    preflight: dict[str, Any] | None = None
    if tokenize_fn is not None:
        preflight = check_code_tokens(code_map, tokenize_fn)
        if not preflight["ok"]:
            raise ReplayError(
                "refusing the replay before any model call: the routing code map is not "
                f"single-token (multi_token={preflight['multi_token']!r}, "
                f"unavailable={preflight['unavailable']!r})"
            )
    outcomes: list[RowOutcome] = []
    replay_started = time.perf_counter()
    for position, row in enumerate(sample):
        question = build_question(options, code_map=code_map, incumbent=row.action)
        outcome = run_row(
            primitives,
            row,
            question,
            position=position,
            role=role,
            state_budget=state_budget,
            json_n_tokens=json_n_tokens,
            cue_style=cue_style,
            tokenize_fn=tokenize_fn,
            code_map=code_map,
        )
        outcomes.append(outcome)
        print(
            f"[{position + 1}/{len(sample)}] {outcome.path:10s} "
            f"code={outcome.chosen_code!r:4s} choice={outcome.action!r:32s} "
            f"incumbent={row.action!r:32s} label={row.label!s:5s} "
            f"conf={outcome.confidence} wall={outcome.elapsed_ms / 1000.0:.2f}s",
            flush=True,
        )
    wall_ms_total = (time.perf_counter() - replay_started) * 1000.0

    receipt: dict[str, Any] = {
        "receipt": "td7-routing-replay",
        "timestamp": started_at,
        "snapshot": dict(snapshot_provenance),
        "config": config,
        "corpus": plan["corpus"],
        "rows": [outcome.to_record() for outcome in outcomes],
        "aggregates": aggregate(outcomes),
        "wall_ms_total": wall_ms_total,
        "metric_directions": dict(_METRIC_DIRECTIONS),
        "code_token_preflight": preflight,
        "label_provenance": {
            "status": "frozen-snapshot",
            "label_definition": "outcome == 'success' from the frozen snapshot above",
            "snapshot_db_sha256": snapshot_provenance.get("db_sha256"),
            "admissibility_reason": snapshot_provenance.get("admissibility_reason"),
            "warning": (
                "The LIVE episodic.db is not admissible ground truth: the "
                "2026-09-17 leak purge changed it. Every label in this receipt "
                "was read from the frozen snapshot, identified by path+SHA-256."
            ),
            "agreement_scope": "vs_incumbent_action",
            "counterfactual_caveat": (
                "The frozen label describes the INCUMBENT action's outcome, not the "
                "chosen action's; for a disagreeing row it is not a label for the "
                "chosen action. Agreement/AUROC/ECE are informative-only until a "
                "counterfactual design labels the counterfactual outcome of the "
                "chosen action."
            ),
        },
    }

    resolved_receipt_path = _resolve_receipt_path(receipt_path, artifacts_dir, started_at)
    if resolved_receipt_path is not None:
        receipt["receipt_path"] = str(resolved_receipt_path)
        _write_receipt(resolved_receipt_path, receipt)
    return receipt


def require_live_primitives(primitives: Any) -> None:
    """Refuse a mock primitives object; a typed replay must be a real call."""
    if primitives is None:
        raise ReplayError("no primitives provided for a live replay")
    if bool(getattr(primitives, "mock_mode", True)):
        raise ReplayError(
            "refusing to replay against MOCK primitives: labels come from a real "
            "frozen corpus and the answers must come from a real model"
        )
    backends = getattr(primitives, "_backends", None)
    if isinstance(backends, Mapping) and not backends:
        raise ReplayError("live primitives expose no backends for the requested role")


def _plan_rows(sample: Sequence[RoutingRow], state_budget: int) -> list[dict[str, Any]]:
    plan_rows: list[dict[str, Any]] = []
    for position, row in enumerate(sample):
        state, truncated = prepare_state(row.context, state_budget)
        plan_rows.append(
            {
                "position": position,
                "embedding_idx": row.embedding_idx,
                "action": row.action,
                "outcome": row.outcome,
                "state_sha256": _sha256_text(state),
                "state_chars": len(state),
                "state_truncated": truncated,
            }
        )
    return plan_rows


def _resolve_receipt_path(
    receipt_path: str | Path | None,
    artifacts_dir: str | Path | None,
    stamp: str,
) -> Path | None:
    if receipt_path is not None:
        return Path(receipt_path)
    if artifacts_dir is None:
        return None
    safe_stamp = "".join(char for char in stamp if char.isalnum())
    return Path(artifacts_dir) / "typed_decisions" / f"routing_replay-{safe_stamp}.json"


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


# ── live primitives ───────────────────────────────────────────────────────


def live_primitives(
    *,
    server_url: str = DEFAULT_SERVER_URL,
    role: str = DEFAULT_ROLE,
    num_slots: int = 4,
) -> Any:
    """Build real ``LLMPrimitives`` bound to one role/server; import lazily.

    ``role`` is served by a single-endpoint ``server_urls`` mapping so the
    replay never depends on the live stack's config for the server under
    test. ``ORCHESTRATOR_USE_CHAT_COMPLETIONS_ROLES`` must be empty (the
    default here is to leave the caller's env untouched) so the role routes
    ``/completion``, which forwards ``grammar`` / ``json_schema``.
    """
    import httpx

    try:
        health = httpx.get(f"{server_url.rstrip('/')}/health", timeout=5.0)
        health.raise_for_status()
        payload = health.json()
    except Exception as exc:  # noqa: BLE001 - any failure is "server not usable"
        raise ReplayError(f"llama-server health check failed at {server_url}: {exc}") from exc
    if str(payload.get("status")) != "ok":
        raise ReplayError(f"llama-server at {server_url} is not ready: {payload!r}")

    from src.llm_primitives import LLMPrimitives

    primitives = LLMPrimitives(
        mock_mode=False,
        server_urls={role: server_url},
        num_slots=num_slots,
    )
    require_live_primitives(primitives)
    return primitives


# ── CLI ───────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.typed_decisions.routing_replay",
        description=(
            "TD-7: replay a frozen routing corpus through the typed-decision shadow. "
            "Real model calls require --live; --dry-run prints the plan only."
        ),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="allow real model calls; without this (or --dry-run) the replay refuses",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the replay plan without calling the model or writing a receipt",
    )
    parser.add_argument(
        "--list-snapshots",
        action="store_true",
        help="list snapshot directories (episodic.db + embeddings.faiss) under the search roots",
    )
    parser.add_argument(
        "--snapshot",
        default=None,
        help=(
            "snapshot directory (episodic.db + optional embeddings.faiss) or a direct "
            f"path to a frozen episodic.db; the known 2026-04-15 backup lives at "
            f"{KNOWN_2026_04_15_SNAPSHOT}"
        ),
    )
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="sample size (default 60)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="sampling seed")
    parser.add_argument(
        "--role",
        default=os.environ.get(ENV_ROLE, DEFAULT_ROLE),
        help="registry role the calls are charged to",
    )
    parser.add_argument(
        "--server-url",
        default=os.environ.get(ENV_SERVER, DEFAULT_SERVER_URL),
        help="llama-server base URL for --live runs",
    )
    parser.add_argument(
        "--state-budget-chars",
        type=int,
        default=DEFAULT_STATE_BUDGET_CHARS,
        help="max STATE characters per row (documented truncation budget)",
    )
    parser.add_argument(
        "--json-n-tokens",
        type=int,
        default=DEFAULT_JSON_N_TOKENS,
        help="output budget for the JSON fallback",
    )
    parser.add_argument("--receipt", default=None, help="exact receipt path")
    parser.add_argument("--artifacts-dir", default=None, help="directory for the default receipt")
    return parser


_SNAPSHOT_SEARCH_ROOTS = (
    "/mnt/raid0/llm/epyc-orchestrator/orchestration",
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/autopilot_checkpoints",
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/backups",
)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns 0 ok, 1 replay error, 2 gate violation."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_snapshots:
        print(json.dumps(discover_snapshots(_SNAPSHOT_SEARCH_ROOTS), indent=2, sort_keys=True))
        return 0

    if not args.live and not args.dry_run:
        print(
            "refusing to run: pass --live for real model calls or --dry-run to print the plan",
            file=sys.stderr,
        )
        return 2
    if args.snapshot is None:
        parser.error("--snapshot is required unless --list-snapshots is given")

    tokenize_fn: Any = None
    try:
        snapshot = resolve_snapshot(args.snapshot)
        rows = load_rows(snapshot.db_path)
        primitives = (
            live_primitives(server_url=args.server_url, role=args.role)
            if (args.live and not args.dry_run)
            else None
        )
        if primitives is not None:
            # One tokenizer for both the pre-model code preflight and the run's
            # candidate binding, so the verified map is the map the run uses.
            tokenize_fn = default_tokenize_fn(primitives, args.role)
            if tokenize_fn is None:
                raise ReplayError(
                    f"could not resolve a /tokenize endpoint for role {args.role!r} at "
                    f"{args.server_url}; refusing a live run that cannot bind codes natively"
                )
        receipt = run_replay(
            rows,
            snapshot_provenance=snapshot.provenance(),
            primitives=primitives,
            n=args.n,
            seed=args.seed,
            role=args.role,
            tokenize_fn=tokenize_fn,
            state_budget=args.state_budget_chars,
            json_n_tokens=args.json_n_tokens,
            receipt_path=args.receipt,
            artifacts_dir=args.artifacts_dir,
            dry_run=args.dry_run,
        )
    except (ReplayError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        close = getattr(tokenize_fn, "close", None)
        if callable(close):
            close()

    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0


# ── small helpers ─────────────────────────────────────────────────────────


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_from_epoch(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
