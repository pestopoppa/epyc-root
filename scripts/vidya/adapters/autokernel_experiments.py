"""AutoKernel `experiments.db` rows -> loop beliefs (belief-kernel redesign, Phase 1 lane C).

One experiments row is one producer-recorded outcome of one mechanism attempt: a measured A/B
(improved / null / regressed), a refusal by a deterministic correctness check, a serving-gate
divergence, or an anchor/runtime baseline reading. This adapter PROJECTS those into
`ClaimTuple`s; `claim_tuple.grade()` grades them, never this module (DESIGN §4.2, §5.1).

READ SIDE (`native_rows`). `<store>/experiments.db` is opened `mode=ro` + `query_only`. Rows come
back in rowid order, incrementally (`since_rowid`, strictly greater). The DS41 store is 4.3 GB with
payloads up to about 6 MB, so `payload` is selected ONLY for the statuses this adapter can project;
every other row costs its small columns, which is what lets a planning-step call advance a
high-water mark cheaply. A full read is a backfill operation, never a planning-step one.

PROJECTION (`project`). Three classes and one refusal rule (DESIGN §4.1, §4.4, §5.1):

    kept / keep_candidate / measured_null / regression / measured_serving_gate
                                          -> measurement, CANDIDATE, outcome improved|null|regressed
    gate_refused (CORRECTNESS gate) / integrity_refused / measured_divergence
                                          -> VERIFIER class (a check, not a measurement); the
                                             decided proposition is the gate's own output line and
                                             no binding is recorded, so SC56 grades it Judged
    anchor_verified / runtime_observed    -> measurement, BASELINE, outcome anchor
    everything else                       -> None: scope/rule gates (patch_rejected, op_scope,
                                             oracle_unavailable, compile...), critic rejections,
                                             authoring failures and transients describe the
                                             author's diff or an LLM judgment, not the target.

Nothing here fills `protocol_id`, so every projection grades `Judged/Located` by the existing
ladder: an observation. A negative result is a first-class VERIFIED observation whose
`observation.outcome` is negative; it is never encoded as a refuted claim (DESIGN §4.3).

IDENTITY. `measurement_id = ak-exp:v1:<store-digest16>:<attempt_id>` is a pure function of the
store identity and the attempt id, never of the ledger, the clock or the row's position. A row
without an attempt id is never projected (no identity, no claim).

SCOPE. `applicability.scope_basis` says where the model/backend scope came from: `native` when the
row's own `research_scope` names the model, else `store_manifest` (the producer contract pins the
whole store's scope; see `build_store_manifest`). Never mixed, never inferred from a path or a date.

DEDUP JOIN. A row whose comparison carries a serving `belief_capture` has a serving claim
`legacy-serving-v2:<capture_id>` (lane B). The join key is `comparison.belief_capture.capture_id`;
`belief_receipt_id` on these rows is the planner-evidence receipt, a different object (it appears
on refusal rows that never measured anything), so it is carried for provenance only. The
experiment claim keeps statement, falsifier and outcome and links the serving claim by id in
`extra["serving_claim_id"]` and a short claim-text pointer. It does NOT drop its own numbers: the
projection must be a pure function of the row, because a projection that depended on what the
ledger already holds would emit different frames for the same attempt on re-run.

RETROFIT. `observation.retrofit` is True for every row with no top-level `belief_capture` in its
payload, i.e. every row written before the producer hook (Phase 2) exists.

Stdlib + ROOT `scripts/vidya` only. No research-repo import; no grading rule here.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping

from claim_tuple import ClaimTuple, ProjectionError

ADAPTER_ID = "vidya.adapters.autokernel_experiments/v1"
SOURCE_KIND = "autokernel-experiment"
ID_PREFIX = "ak-exp:v1"
REPORT_SCHEMA = "epyc.vidya.autokernel_experiments_report.v1"
SERVING_V2_PREFIX = "legacy-serving-v2:"

# --- the status vocabulary (DESIGN §3.1, §4.4, §5.1) ---------------------------------------
MEASUREMENT_STATUSES = frozenset({"kept", "keep_candidate", "measured_null", "regression",
                                  "measured_serving_gate"})
VERIFIER_STATUSES = frozenset({"gate_refused", "integrity_refused", "measured_divergence"})
BASELINE_STATUSES = frozenset({"anchor_verified", "runtime_observed"})
PROJECTED_STATUSES = MEASUREMENT_STATUSES | VERIFIER_STATUSES | BASELINE_STATUSES

#: status -> observation.outcome for the statuses whose outcome is fixed by the status alone.
#: `measured_serving_gate` is decided by the sign of its effect (see `_outcome`).
OUTCOME_BY_STATUS = {
    "kept": "improved", "keep_candidate": "improved",
    "measured_null": "null", "regression": "regressed",
    "measured_divergence": "divergence", "integrity_refused": "refused_correctness",
    "anchor_verified": "anchor", "runtime_observed": "anchor",
}

#: A `gate_refused` row is a CORRECTNESS refusal only when the refusing gate is one of these
#: (loop/gates.py: `Verdict("correctness", ...)`, `Verdict("reference_comparison", ...)`).
#: compile/configure, op_scope, oracle_unavailable and cpu_fa_perf_screen are harness or scope
#: verdicts about the author's diff, never about the target.
CORRECTNESS_GATES = frozenset({"correctness", "reference_comparison"})

#: Why a status is not projected. Reported by `classify` and counted by the dry run.
NOT_PROJECTED = {
    "patch_rejected": "critic_or_scope_rejection", "hypothesis_rejected": "critic_rejection",
    "authoring_failed": "authoring_failure", "hypothesis_retired": "authoring_failure",
    "patch_rounds_exhausted": "authoring_failure", "scope_blocked": "scope_gate",
    "refused_at_formation": "scope_gate", "refused_duplicate": "duplicate_dispatch",
    "anchor_guard_excursion": "instrument_session_health", "anchor_mismatch": "instrument_abort",
    "measurement_invalid": "invalid_measurement", "bench_failed": "instrument_failure",
    "planner_transient": "noise", "abstained": "noise", "stopped_mid_formation": "noise",
    "lane_error": "noise", "resume_rejected": "noise", "superseded": "noise",
}

_COLUMNS = ("attempt_id", "recorded_at", "campaign_id", "deployment", "epoch_sha256",
            "hypothesis_id", "mechanism_id", "target_surface", "target_symbol", "statement",
            "falsifier", "status", "effect_fraction", "exact_effect", "target_effect",
            "refusal_reason", "result_sha256", "spawn_parent", "branch_id", "width", "depth")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_ATTEMPT = re.compile(r"[^\s\x00-\x1f\x7f]{1,200}\Z")
_OP_FAILED = re.compile(r"^([A-Z][A-Z0-9_]{2,})\s+failed\b")
_SERVING_SURFACE = re.compile(r"^serving:(?P<recipe>\S+)$")

STATEMENT_MAX = 240
REASON_MAX = 300
PROPOSITION_MAX = 1000


# ============================================================================== carrier seam
#
# THE ONE PLACE a ClaimTuple is constructed. Lane A adds `ClaimTuple.observation` and the new
# applicability keys (DESIGN §4.1/§4.2) on a separate branch. Until that lands this module still
# runs: the observation rides in `extra["observation"]` and the keys the old validator rejects
# ride in `extra["applicability_full"]`. After the integration rebase `CARRIER_READY` is True and
# the fallback branch below is dead code to delete; nothing else in this file changes.


def _carrier_ready() -> bool:
    if "observation" not in {f.name for f in dataclasses.fields(ClaimTuple)}:
        return False
    try:
        ClaimTuple(measurement_id="probe", metric="m", value=0, date="", category="CANDIDATE",
                   claim="probe", applicability={"scope_basis": "native", "np": 1})
    except ProjectionError:
        return False
    return True


CARRIER_READY = _carrier_ready()
_LEGACY_APPLICABILITY = frozenset({"model_file", "quant", "backend", "device", "context_tokens",
                                   "kernel", "run_id", "run_expected_keys"})


def _make_tuple(fields: dict, applicability: dict, observation: dict) -> ClaimTuple:
    """Build the ClaimTuple. `fields` are ClaimTuple constructor kwargs except the two below."""
    if CARRIER_READY:
        return ClaimTuple(**fields, applicability=applicability, observation=observation)
    extra = dict(fields.get("extra") or {})
    extra["observation"] = observation
    extra["applicability_full"] = dict(applicability)
    legacy = {key: value for key, value in applicability.items() if key in _LEGACY_APPLICABILITY}
    return ClaimTuple(**{**fields, "extra": extra}, applicability=legacy)


def observation_of(tup: ClaimTuple) -> dict:
    """The observation of a projected tuple, on either side of the carrier integration."""
    return dict(getattr(tup, "observation", None) or tup.extra.get("observation") or {})


def applicability_of(tup: ClaimTuple) -> dict:
    """The full applicability of a projected tuple, on either side of the carrier integration."""
    return dict(tup.extra.get("applicability_full") or tup.applicability)


# ============================================================================== small helpers


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _round(value: float | None) -> float | None:
    """12 significant digits: a stable decimal image of a float that came out of JSON."""
    return None if value is None else float(f"{value:.12g}")


def _median(values: Any) -> float | None:
    if not isinstance(values, list):
        return None
    numbers = [_num(v) for v in values]
    if not numbers or any(v is None for v in numbers):
        return None
    return float(median(numbers))


def _text(value: Any, limit: int | None = None) -> str:
    text = value.strip() if isinstance(value, str) else ""
    return text[:limit] if limit else text


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


# ============================================================================== read side


def _db_path(store_dir: Path) -> Path:
    return Path(store_dir) / "experiments.db"


def _connect(store_dir: Path) -> sqlite3.Connection:
    path = _db_path(store_dir)
    if not path.is_file():
        raise ProjectionError(f"no experiments.db under {store_dir}")
    # `mode=ro` is the file-level guarantee; `query_only` is the connection-level one.
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=30)
    conn.execute("PRAGMA query_only = ON")
    return conn


def native_rows(store_dir: Path, since_rowid: int | None = None) -> list[dict]:
    """Rows of `<store>/experiments.db` with rowid > `since_rowid`, in rowid order.

    Each dict carries `rowid`, every column the store has (None for a column an older store
    lacks), and for the statuses this adapter can project: `payload` (parsed JSON object, or None
    with `payload_error` set when it is not one) and `payload_sha256` (over the raw stored text).
    Other statuses carry `payload=None` and no payload is read from disk for them.
    """
    if since_rowid is not None and (type(since_rowid) is not int or since_rowid < 0):
        raise ProjectionError("since_rowid must be a non-negative integer or None")
    conn = _connect(Path(store_dir))
    try:
        present = {row[1] for row in conn.execute("PRAGMA table_info(experiments)")}
        if "attempt_id" not in present or "status" not in present or "payload" not in present:
            raise ProjectionError("experiments table lacks attempt_id/status/payload")
        select = ", ".join(c if c in present else f"NULL AS {c}" for c in _COLUMNS)
        marks = ",".join("?" for _ in PROJECTED_STATUSES)
        sql = (f"SELECT rowid, {select}, "
               f"CASE WHEN status IN ({marks}) THEN payload END AS payload "
               "FROM experiments WHERE rowid > ? ORDER BY rowid")
        cursor = conn.execute(sql, (*sorted(PROJECTED_STATUSES), -1 if since_rowid is None
                                    else since_rowid))
        names = ["rowid", *_COLUMNS, "payload"]
        rows = []
        for values in cursor:
            row = dict(zip(names, values))
            raw = row["payload"]
            row["payload"], row["payload_sha256"], row["payload_error"] = None, None, None
            if raw is not None:
                blob = raw if isinstance(raw, bytes) else str(raw).encode()
                row["payload_sha256"] = hashlib.sha256(blob).hexdigest()
                try:
                    parsed = json.loads(blob)
                except ValueError as exc:
                    row["payload_error"] = f"payload is not JSON: {exc}"[:200]
                else:
                    if isinstance(parsed, dict):
                        row["payload"] = parsed
                    else:
                        row["payload_error"] = "payload is not a JSON object"
            rows.append(row)
        return rows
    finally:
        conn.close()


# ============================================================================== store manifest


def _store_digest16(store_manifest: Mapping[str, Any]) -> str:
    digest = store_manifest.get("store_digest")
    if isinstance(digest, str) and _HEX64.fullmatch(digest):
        return digest[:16]
    path = store_manifest.get("store_path")
    if isinstance(path, str) and path.strip():
        return hashlib.sha256(path.encode()).hexdigest()[:16]
    raise ProjectionError("store_manifest needs store_digest (64 hex) or store_path")


def _native_scope(payload: Mapping[str, Any], comparison: Mapping[str, Any]) -> dict:
    """The row's own `research_scope`, as applicability keys; {} when it names no model."""
    scope = payload.get("research_scope")
    if not isinstance(scope, Mapping):
        return {}
    model = scope.get("model")
    path = model.get("path") if isinstance(model, Mapping) else model
    if not _text(path):
        return {}
    out = {"model_file": _text(path)}
    sha = model.get("sha256") if isinstance(model, Mapping) else None
    if isinstance(sha, str) and _HEX64.fullmatch(sha.lower()):
        out["model_sha256"] = sha.lower()
    for key in ("quant", "backend"):
        if _text(scope.get(key)):
            out[key] = _text(scope[key])
    match = _SERVING_SURFACE.match(_text(scope.get("measurement_surface")))
    if match:
        out["recipe"] = match.group("recipe")
    return out


def _manifest_scope(store_manifest: Mapping[str, Any]) -> dict:
    if not _text(store_manifest.get("model_file")):
        return {}
    out = {}
    for key in ("model_file", "model_sha256", "quant", "backend", "device", "recipe"):
        if _text(store_manifest.get(key)):
            out[key] = _text(store_manifest[key])
    if type(store_manifest.get("np")) is int and store_manifest["np"] > 0:
        out["np"] = store_manifest["np"]
    return out


def build_store_manifest(store_dir: Path, *, label: str | None = None,
                         overrides: Mapping[str, Any] | None = None) -> dict:
    """The store identity plus, when the store pins one, its scope.

    `store_path` (resolved) names the store; its sha256 is the `store-digest16` of every id.
    The scope is the ONE native `research_scope` shared by every measured row that has one
    (bounded read: a few payloads). A store whose measured rows disagree, or carry none, gets NO
    manifest scope: unscoped is honest, a guessed scope is not. `overrides` (e.g. a reviewed
    campaign-manifest extract) wins key by key.
    """
    store = Path(store_dir)
    manifest: dict[str, Any] = {"store_path": str(store.resolve()), "scope_derivation": "none"}
    scopes: set[str] = set()
    conn = _connect(store)
    try:
        marks = ",".join("?" for _ in ("kept", "keep_candidate", "measured_null", "regression"))
        cursor = conn.execute(
            f"SELECT payload FROM experiments WHERE status IN ({marks}) "
            "AND payload LIKE '%\"research_scope\"%' ORDER BY rowid LIMIT 8",
            ("kept", "keep_candidate", "measured_null", "regression"))
        for (raw,) in cursor:
            try:
                payload = json.loads(raw)
            except ValueError:
                continue
            scope = _native_scope(payload, {}) if isinstance(payload, dict) else {}
            if scope:
                scopes.add(json.dumps(scope, sort_keys=True))
    finally:
        conn.close()
    if len(scopes) == 1:
        manifest.update(json.loads(next(iter(scopes))))
        manifest["scope_derivation"] = "uniform native research_scope of the store's measured rows"
    elif len(scopes) > 1:
        manifest["scope_derivation"] = "none: the store's measured rows name different scopes"
    if label:
        manifest["label"] = label
    manifest.update({k: v for k, v in (overrides or {}).items() if v not in (None, "")})
    return manifest


# ============================================================================== classification


def _refusal_gate(payload: Mapping[str, Any]) -> str:
    gate = _text(payload.get("refusal_gate"))
    if gate:
        return gate
    gates = payload.get("gates")
    if isinstance(gates, list):
        for item in reversed(gates):
            if isinstance(item, Mapping) and item.get("passed") is False and _text(item.get("gate")):
                return _text(item["gate"])
    return ""


def classify(row: Mapping[str, Any]) -> tuple[str | None, str]:
    """(disposition, reason): disposition is measurement | verifier | baseline | None.

    The reason names why a row is NOT projected, so a dry run can count dead ends by cause
    instead of reporting one opaque total.
    """
    attempt = row.get("attempt_id")
    if not isinstance(attempt, str) or not _ATTEMPT.fullmatch(attempt):
        return None, "no_attempt_id"
    status = _text(row.get("status"))
    if status in NOT_PROJECTED:
        return None, NOT_PROJECTED[status]
    if status not in PROJECTED_STATUSES:
        return None, "unlisted_status"
    payload = row.get("payload")
    if not isinstance(payload, Mapping):
        return None, "payload_unreadable"
    if status in VERIFIER_STATUSES:
        if status == "gate_refused" and _refusal_gate(payload) not in CORRECTNESS_GATES:
            return None, "scope_gate"
        if not _proposition(row, payload):
            return None, "no_decided_proposition"
        return "verifier", status
    comparison = _comparison(row, payload)
    if _numbers(row, comparison)["value"] is None:
        return None, "no_numbers"
    return ("baseline" if status in BASELINE_STATUSES else "measurement"), status


# ============================================================================== extraction


def _comparison(row: Mapping[str, Any], payload: Mapping[str, Any]) -> dict:
    comparison = payload.get("comparison")
    if isinstance(comparison, Mapping):
        return dict(comparison)
    guard = payload.get("anchor_guard")
    if isinstance(guard, Mapping):
        inner = guard.get("comparison")
        return dict(inner) if isinstance(inner, Mapping) else dict(guard)
    serving = payload.get("serving")
    return dict(serving) if isinstance(serving, Mapping) else {}


def _numbers(row: Mapping[str, Any], comparison: Mapping[str, Any]) -> dict:
    """value / anchor / effect / floor / decisive / pairs, from the producer's own fields only."""
    anchor = _num(comparison.get("anchor_tok_s"))
    if anchor is None:
        anchor = _median(comparison.get("anchor_samples"))
    candidate = _num(comparison.get("candidate_tok_s"))
    if candidate is None:
        candidate = _median(comparison.get("candidate_samples"))
    effect = _num(row.get("effect_fraction"))
    if effect is None:
        effect = _num(comparison.get("effect"))
    if effect is None and _num(comparison.get("effect_pct")) is not None:
        effect = _num(comparison["effect_pct"]) / 100.0
    floor = _num(comparison.get("noise_floor_pct"))
    if floor is None:
        floor = _num(comparison.get("floor_pct"))
    pairs = comparison.get("pairs")
    status = _text(row.get("status"))
    # BASELINE readings are the anchor's own rate; a measurement is the candidate's.
    primary = (anchor if status in BASELINE_STATUSES else candidate)
    metric = _text(comparison.get("metric")) or _text(comparison.get("surface")) or "aggregate_tok_s"
    unit = "t/s"
    if primary is None and effect is not None and status not in BASELINE_STATUSES:
        metric, primary, unit = "effect_fraction", effect, "fraction"
    return {"value": primary, "unit": unit, "metric": metric, "anchor": anchor,
            "candidate": candidate, "effect": effect, "floor_pct": floor,
            "decisive": comparison.get("decisive") if isinstance(comparison.get("decisive"), bool)
            else None,
            "pairs": pairs if type(pairs) is int and pairs >= 1 else None}


def _proposition(row: Mapping[str, Any], payload: Mapping[str, Any]) -> str:
    """The gate's own output line (DESIGN §4.4), verbatim."""
    status = _text(row.get("status"))
    if status == "measured_divergence":
        text = _text(payload.get("hypothesis")) or _text(row.get("refusal_reason"))
    else:
        text = _text(row.get("refusal_reason")) or _text(payload.get("reason"))
    if not text and isinstance(payload.get("gates"), list):
        for gate in payload["gates"]:
            if isinstance(gate, Mapping) and gate.get("passed") is False:
                detail = _text(gate.get("detail")) or _text(gate.get("reason"))
                text = next((line.strip() for line in detail.splitlines() if line.strip()), "")
                if text:
                    break
    return text[:PROPOSITION_MAX]


def _outcome(row: Mapping[str, Any], numbers: Mapping[str, Any]) -> str:
    status = _text(row.get("status"))
    if status == "gate_refused":
        return "refused_correctness"
    if status == "measured_serving_gate":
        effect = numbers["effect"]
        if effect is not None and effect > 0:
            return "improved"
        if effect is not None and effect < 0 and numbers["decisive"]:
            return "regressed"
        return "null"
    return OUTCOME_BY_STATUS[status]


def serving_claim_id(payload: Mapping[str, Any]) -> str | None:
    """`legacy-serving-v2:<capture_id>` when this row's comparison carries a serving capture."""
    comparison = payload.get("comparison")
    capture = comparison.get("belief_capture") if isinstance(comparison, Mapping) else None
    ident = capture.get("capture_id") if isinstance(capture, Mapping) else None
    return f"{SERVING_V2_PREFIX}{ident}" if isinstance(ident, str) and _HEX64.fullmatch(ident) else None


def _is_retrofit(payload: Mapping[str, Any]) -> bool:
    capture = payload.get("belief_capture")
    return not (isinstance(capture, Mapping) and bool(capture))


def _applicability(row: Mapping[str, Any], payload: Mapping[str, Any],
                   comparison: Mapping[str, Any], store_manifest: Mapping[str, Any],
                   op: str) -> dict:
    native = _native_scope(payload, comparison)
    if native:
        scope, basis = native, "native"
    else:
        scope = _manifest_scope(store_manifest)
        basis = "store_manifest" if scope else None
    out = dict(scope)
    if basis:
        out["scope_basis"] = basis
    if type(comparison.get("np")) is int and comparison["np"] > 0:
        out["np"] = comparison["np"]
    elif "np" not in out and type(payload.get("np")) is int and payload["np"] > 0:
        out["np"] = payload["np"]
    build = _text(row.get("spawn_parent")) or _text(payload.get("champion_head"))
    for key, value in (("build_sha", build), ("epoch", _text(row.get("epoch_sha256"))),
                       ("surface", _text(row.get("target_surface"))),
                       ("symbol", _text(row.get("target_symbol"))), ("op", op)):
        if value:
            out[key] = value
    return out


def _label(store_manifest: Mapping[str, Any], applicability: Mapping[str, Any]) -> str:
    # The manifest's label names the manifest's model: never put it on a row whose own scope says
    # something else.
    label = (_text(store_manifest.get("label"))
             if applicability.get("scope_basis") == "store_manifest" else "")
    if not label and applicability.get("model_file"):
        label = Path(applicability["model_file"]).name.removesuffix(".gguf")
    backend = _text(applicability.get("backend"))
    recipe = _text(applicability.get("recipe"))
    return " ".join(part for part in (label, backend) if part) + (f" [{recipe}]" if recipe else "")


def _row_digest(row: Mapping[str, Any]) -> str:
    columns = {name: row.get(name) for name in _COLUMNS}
    payload_sha = row.get("payload_sha256") or hashlib.sha256(_canon(row.get("payload"))).hexdigest()
    return hashlib.sha256(_canon({"columns": columns, "payload_sha256": payload_sha})).hexdigest()


def measurement_id(row: Mapping[str, Any], store_manifest: Mapping[str, Any]) -> str:
    attempt = row.get("attempt_id")
    if not isinstance(attempt, str) or not _ATTEMPT.fullmatch(attempt):
        raise ProjectionError("experiments row has no usable attempt_id")
    return f"{ID_PREFIX}:{_store_digest16(store_manifest)}:{attempt}"


# ============================================================================== projection


def project(row: dict, *, store_manifest: dict) -> ClaimTuple | None:
    """One experiments row -> one ClaimTuple, or None when the row is not a loop belief.

    None is the answer for rows with no attempt id, scope/rule gates, critic and authoring
    outcomes, transients and rows whose payload or numbers are unusable (see `classify`, which
    names the reason). Raises ProjectionError only when the STORE identity is unusable.
    """
    disposition, _ = classify(row)
    if disposition is None:
        return None
    ident = measurement_id(row, store_manifest)
    status = _text(row.get("status"))
    payload = row["payload"]
    comparison = _comparison(row, payload)
    numbers = _numbers(row, comparison)
    outcome = _outcome(row, numbers)
    reason = (_text(row.get("refusal_reason")) or _text(payload.get("reason")))[:REASON_MAX]
    mechanism_id = _text(row.get("mechanism_id")) or _text(payload.get("mechanism_id"))
    statement = _text(row.get("statement")) or _text(payload.get("statement"))
    falsifier = _text(row.get("falsifier")) or _text(payload.get("falsifier"))
    serving = serving_claim_id(payload)

    op = ""
    proposition = ""
    metric, value, unit = numbers["metric"], numbers["value"], numbers["unit"]
    if disposition == "verifier":
        proposition = _proposition(row, payload)
        value, unit = 0, ""
        if status == "gate_refused":
            match = _OP_FAILED.match(proposition)
            op = match.group(1) if match else ""
            metric = f"correctness:{op}" if op else "correctness"
        elif status == "integrity_refused":
            screen = payload.get("integrity_screen")
            klass = _text(screen.get("refusal_class")) if isinstance(screen, Mapping) else ""
            metric = f"integrity:{klass}" if klass else "integrity"
        else:
            metric = "serving_gate:diverged"

    applicability = _applicability(row, payload, comparison, store_manifest, op)
    label = _label(store_manifest, applicability)
    where = f" on {row['target_symbol']}" if _text(row.get("target_symbol")) else ""
    what = mechanism_id or f"attempt {row['attempt_id'][:12]}"
    effect = numbers["effect"]
    if disposition == "verifier":
        verdict = ("refused by the correctness gate" if status == "gate_refused" else
                   "refused by the integrity screen" if status == "integrity_refused" else
                   "serving gate diverged from the bench")
        claim = f"{label}: {what}{where}: {verdict}: {proposition[:160]}"
    else:
        if disposition == "baseline":
            measured = ("anchor reading" if effect is None
                        else f"anchor reading, A/A {effect * 100:+.2f}%")
        else:
            measured = ("no effect recorded" if effect is None
                        else f"{effect * 100:+.2f}% vs anchor")
        detail = [part for part in (
            None if numbers["floor_pct"] is None else f"floor {numbers['floor_pct']:.2f}%",
            None if numbers["pairs"] is None else f"{numbers['pairs']} pairs") if part]
        claim = f"{label}: {what}{where}: {measured}" + (f" ({', '.join(detail)})" if detail else "")
    claim = f"{claim} — producer verdict {status.upper()}"
    if serving:
        claim += f" [serving claim {serving.removeprefix(SERVING_V2_PREFIX)[:16]}]"

    observation: dict[str, Any] = {"outcome": outcome, "outcome_native": status,
                                   "retrofit": _is_retrofit(payload)}
    for key, source in (("anchor_value", numbers["anchor"]), ("effect_rel", effect),
                        ("noise_floor_rel", None if numbers["floor_pct"] is None
                         else numbers["floor_pct"] / 100.0)):
        if source is not None:
            observation[key] = _round(source)
    if numbers["decisive"] is not None:
        observation["decisive"] = numbers["decisive"]
    if numbers["pairs"] is not None:
        observation["n_pairs"] = numbers["pairs"]
    if reason:
        observation["outcome_reason"] = reason
    if mechanism_id:
        observation["mechanism"] = {"id": mechanism_id, **(
            {"statement": statement[:STATEMENT_MAX]} if statement else {}), **(
            {"falsifier": falsifier[:STATEMENT_MAX]} if falsifier else {})}

    plan = comparison.get("measurement_plan")
    matched = isinstance(plan, Mapping) and plan.get("instrument") == "matched_process_v2"
    fields: dict[str, Any] = dict(
        measurement_id=ident, metric=metric, value=value if disposition == "verifier" else _round(value),
        unit=unit, metric_direction="higher_better",
        category="BASELINE" if disposition == "baseline" else "CANDIDATE", claim=claim,
        date=_text(row.get("recorded_at")), protocol_id="",
        reps=None if disposition == "verifier" else numbers["pairs"],
        reps_basis="" if disposition == "verifier" or numbers["pairs"] is None else (
            "scored:matched process pairs" if matched else "scored:paired A/B pairs"),
        source_kind=SOURCE_KIND,
        attestation_locator=(f"autokernel-experiments:{store_manifest.get('store_path', '')}"
                             f"/experiments.db#attempt={row['attempt_id']}"),
        attestation_sha256=_row_digest(row), attestation_present=True,
        extra={"attempt_id": row["attempt_id"], "store_digest16": _store_digest16(store_manifest),
               "status": status, "campaign_id": row.get("campaign_id"),
               "serving_claim_id": serving,
               "belief_receipt_id": _text(payload.get("belief_receipt_id")) or None,
               "candidate_diff_sha256": _text(payload.get("candidate_diff_sha256")) or None,
               "result_sha256": row.get("result_sha256")})
    if disposition == "verifier":
        fields.update(source_class="verifier", decided_proposition=proposition, binding_kind="")
    return _make_tuple(fields, applicability, observation)


# ============================================================================== ingest (CLI)


def _canonical_paths() -> set[str]:
    from ledger_home import DEFAULT_STATE_DIR, canonical_ledger_path  # noqa: PLC0415

    return {os.path.realpath(canonical_ledger_path()),
            os.path.realpath(DEFAULT_STATE_DIR / "ledger.jsonl")}


def check_ledger_target(path: str | os.PathLike, *, i_own_canonical: bool) -> Path:
    """The write target: refuses the canonical ledger unless the owning session says so."""
    target = Path(path)
    if os.path.realpath(target) in _canonical_paths() and not i_own_canonical:
        raise ProjectionError(
            f"{target} is the canonical ledger; pass --i-own-the-canonical-ledger from the owning "
            "session, or write to a copy (no lane writes the canonical ledger)")
    return target


def ingest(stores: Iterable[Path], *, as_of: str | None = None,
           ledger_path: Path | None = None, since_rowid: int | None = None,
           store_manifests: Mapping[str, Mapping[str, Any]] | None = None) -> dict:
    """Project every projectable row of each store. Writes only when `ledger_path` is given.

    Dry run (no ledger): reads, projects and counts; touches no ledger, not even to read it.
    """
    from claim_tuple import to_frames  # noqa: PLC0415

    started = time.monotonic()
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA, "dry_run": ledger_path is None, "stores": [], "rows_read": 0,
        "by_status": {}, "projected": 0, "by_disposition": {}, "not_projected": {},
        "by_scope_basis": {}, "by_outcome": {}, "retrofit": 0, "projection_errors": [],
        "frames": 0, "carrier_ready": CARRIER_READY}
    incoming: list[dict] = []

    def bump(table: dict, key: str) -> None:
        table[key] = table.get(key, 0) + 1

    for store in (Path(s) for s in stores):
        manifest = dict((store_manifests or {}).get(str(store)) or build_store_manifest(store))
        rows = native_rows(store, since_rowid)
        report["stores"].append({"store": str(store), "store_digest16": _store_digest16(manifest),
                                 "rows": len(rows),
                                 "max_rowid": rows[-1]["rowid"] if rows else since_rowid,
                                 "scope_derivation": manifest.get("scope_derivation")})
        for row in rows:
            report["rows_read"] += 1
            bump(report["by_status"], str(row.get("status")))
            disposition, why = classify(row)
            if disposition is None:
                bump(report["not_projected"], why)
                continue
            try:
                tup = project(row, store_manifest=manifest)
            except ProjectionError as exc:
                report["projection_errors"].append(f"{row.get('attempt_id')}: {exc}"[:200])
                continue
            if tup is None:
                bump(report["not_projected"], "project_returned_none")
                continue
            report["projected"] += 1
            bump(report["by_disposition"], disposition)
            observation = observation_of(tup)
            bump(report["by_outcome"], observation["outcome"])
            bump(report["by_scope_basis"], applicability_of(tup).get("scope_basis", "unscoped"))
            report["retrofit"] += bool(observation.get("retrofit"))
            if ledger_path is not None:
                incoming.extend(to_frames(tup, as_of=as_of, adapter_id=ADAPTER_ID))
            else:
                report["frames"] += 3
    report["projection_errors"] = report["projection_errors"][:20]
    if ledger_path is not None:
        from ledger import Ledger  # noqa: PLC0415
        from scoped_ingest import append_scoped  # noqa: PLC0415

        result = append_scoped(Ledger(Path(ledger_path)), incoming, as_of=as_of or "")
        report["ledger"] = str(ledger_path)
        report["frames"] = result["frames"]
        report["only_new"] = {k: result[k] for k in ("new_claims", "rescoped", "already_present")
                              if k in result}
    report["seconds"] = round(time.monotonic() - started, 3)
    return report


__all__ = ["ADAPTER_ID", "CARRIER_READY", "applicability_of", "build_store_manifest",
           "check_ledger_target", "classify", "ingest", "measurement_id", "native_rows",
           "observation_of", "project", "serving_claim_id"]
