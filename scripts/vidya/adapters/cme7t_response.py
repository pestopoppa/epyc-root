"""Strict projection of sealed CME-7T native response and hand records.

This is a projection only. The v2 collection is explicitly diagnostic; its tuples carry that
scope and the empty protocol id, so the existing ClaimTuple grader remains the only grader.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.cme7t_response/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "cme7t-response"
METRIC = "cme7t_diagnostic_hand_profit"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_KINDS = ("baseline", "run")


class CaptureError(ValueError):
    pass


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CaptureError(f"unreadable JSON {path.name}: {exc}") from exc


def _load_pinned(path: Path, name: str, digest: str):
    if not path.is_file() or _sha(path) != digest:
        raise CaptureError(f"pinned native validator mismatch: {name}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CaptureError(f"cannot load native validator: {name}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _verify_bundle(root: Path) -> tuple[dict, dict[str, str]]:
    rec = _json(root / "RUN_RECORD.json")
    if rec.get("schema") != "epyc.cme7t.native_run.draft.v1":
        raise CaptureError("unexpected RUN_RECORD schema")
    expected = rec.get("artifacts_sha256")
    if not isinstance(expected, dict) or not expected:
        raise CaptureError("RUN_RECORD lacks closed artifact map")
    actual: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if rel == "RUN_RECORD.json" or rel.startswith("cache/"):
            continue
        if p.is_symlink():
            raise CaptureError(f"symlink in sealed tree: {rel}")
        if p.is_file():
            actual[rel] = _sha(p)
    if actual != expected:
        diffs = sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
        raise CaptureError(f"closed artifact map mismatch: {diffs[:8]}")
    manifest = root / "source-files.sha256"
    manifest_digest = actual.get("source-files.sha256")
    if not manifest_digest or rec.get("source_manifest_sha256") != manifest_digest:
        raise CaptureError("source manifest digest does not bind to RUN_RECORD")
    pins = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        parts = line.split("  ", 1)
        if len(parts) == 2 and _SHA.fullmatch(parts[0]):
            pins[parts[1]] = parts[0]
    base = root.parent.resolve()
    for rel in ("account.py", "artifact_seal.py"):
        p = base / rel
        pin = pins.get(str(p))
        if not pin:
            raise CaptureError(f"source manifest has no pin for {rel}")
        _load_pinned(p, f"_cme7t_{rel.replace('.', '_')}_{pin[:8]}", pin)
    seal = _load_pinned(base / "artifact_seal.py", f"_cme7t_seal_{manifest_digest[:8]}", pins[str(base / "artifact_seal.py")])
    try:
        sealed_rec = seal.verify(root)
    except Exception as exc:
        raise CaptureError(f"native seal refused: {exc}") from exc
    account = _load_pinned(base / "account.py", f"_cme7t_account_{manifest_digest[:8]}", pins[str(base / "account.py")])
    derived = account.account(root / "worker-records", root / "tmp/raw_replies.jsonl")
    reported = _json(root / "response-accounting.json")
    if derived != reported:
        raise CaptureError("response-accounting differs from native journal re-derivation")
    if sealed_rec != rec:
        raise CaptureError("seal verifier returned a different run record")
    return rec, derived


def _rows_from_verified(root: Path, rec: dict, accounting: dict) -> tuple[dict, ...]:
    if accounting.get("schema") != "epyc.cme7t.v2.accounting.v1":
        raise CaptureError("unexpected accounting schema")
    rows = []
    for kind in _KINDS:
        count = 3 if kind == "run" else 5
        for i in range(count):
            label = f"{kind}-{i:04d}"
            worker = _json(root / "worker-records" / f"{label}.json")
            trace = worker.get("trace")
            if not isinstance(trace, dict) or trace.get("status") != worker.get("status"):
                raise CaptureError(f"{label}: worker/trace status mismatch")
            outcomes = trace.get("result", {}).get("instance_outcomes")
            if not isinstance(outcomes, list):
                outcomes = []
            scheduled = [i] if kind == "baseline" else list(range(5))
            hand_states = accounting["cohorts"][label]["hands"]
            if worker.get("status") == "completed" and len(outcomes) != len(scheduled):
                raise CaptureError(f"{label}: outcome denominator differs from scheduled hands")
            events_path = root / "worker-records" / f"{label}.events.jsonl"
            hand_ids = {}
            for line in events_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("event") == "hand_completed":
                    hi = event.get("hand_index")
                    hid = event.get("hand_id")
                    if type(hi) is not int or hi in hand_ids or not isinstance(hid, str):
                        raise CaptureError(f"{label}: duplicate/malformed native hand join")
                    hand_ids[hi] = hid
            if not set(hand_ids).issubset(set(scheduled)):
                raise CaptureError(f"{label}: completed hand IDs escape the scheduled denominator")
            for hand in scheduled:
                if hand_states.get(str(hand)) == "completed" and hand not in hand_ids:
                    raise CaptureError(f"{label}: accounting says completed without a terminal hand ID")
            prev = 0
            by_hand = {}
            for out in sorted(outcomes, key=lambda item: item.get("instance_index", -1)):
                hand = out.get("instance_index")
                if type(hand) is not int or hand not in scheduled or hand in by_hand or not isinstance(out.get("metadata"), dict):
                    raise CaptureError(f"{label}: outcome identity/index/metadata mismatch")
                if hand in hand_ids and out.get("instance_id") != hand_ids[hand]:
                    raise CaptureError(f"{label}: native outcome/hand journal ID mismatch")
                total = out["metadata"].get("total_profit")
                if type(total) not in (int, float):
                    raise CaptureError(f"{label}: native chip result missing")
                delta = total - prev
                prev = total
                by_hand[hand] = (delta, total)
            if set(by_hand) != set(scheduled):
                if worker.get("status") == "completed":
                    raise CaptureError(f"{label}: outcome hand set differs from scheduled denominator")
            for hand in scheduled:
                result = by_hand.get(hand)
                status = hand_states.get(str(hand), "unknown")
                if status == "completed" and result is None:
                    raise CaptureError(f"{label}: completed hand has no native outcome")
                rows.append({"root": str(root), "run": rec, "accounting": accounting,
                             "cohort": label, "kind": kind, "worker": i, "hand": hand,
                             "hand_status": status, "hand_id": hand_ids.get(hand),
                             "worker_status": worker["status"],
                             "profit": result[0] if result is not None else None,
                             "total_profit": result[1] if result is not None else None,
                             "response_ids": accounting["cohorts"][label]["responses"],
                             "run_record_sha256": _sha(root / "RUN_RECORD.json"),
                             "raw_sha256": _sha(root / "tmp/raw_replies.jsonl"),
                             "accounting_sha256": _sha(root / "response-accounting.json")})
    return tuple(rows)


def native_rows(path: str | Path) -> tuple[dict, ...]:
    root = Path(path)
    if not root.is_dir():
        return ()
    rec, accounting = _verify_bundle(root)
    return _rows_from_verified(root, rec, accounting)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("run"), dict):
        raise ProjectionError("CME-7T native row missing")
    root = Path(native.get("root", ""))
    rec, acc = _verify_bundle(root)
    cohort = native.get("cohort")
    rows = [r for r in _rows_from_verified(root, rec, acc)
            if r["cohort"] == cohort and r["hand"] == native.get("hand")]
    if len(rows) != 1 or rows[0].get("hand_status") != "completed":
        raise ProjectionError("CME-7T hand is absent, incomplete, or ambiguous")
    row = rows[0]
    if native != row:
        raise ProjectionError("CME-7T supplied row differs from sealed native projection")
    run_id = rec.get("run_id", "")
    if not run_id or not isinstance(row["profit"], (int, float)):
        raise ProjectionError("CME-7T run identity or native outcome missing")
    # The tuple records a diagnostic hand observation; no historical comparison, efficacy,
    # threshold, or adoption claim is made. The unratified protocol id keeps the existing ladder.
    claim = (f"diagnostic native chip profit {row['profit']} chips for {cohort}, hand {row['hand']}; "
             "not an efficacy or promotion result")
    argv = rec.get("recipe", {}).get("argv", [])
    try:
        model_file = Path(argv[argv.index("-m") + 1]).name
    except (ValueError, IndexError, TypeError):
        raise ProjectionError("CME-7T recipe lacks model path")
    return ClaimTuple(
        measurement_id=f"{run_id}:{cohort}:hand-{row['hand']}", metric=METRIC,
        value=row["profit"], date=rec.get("started_utc", "")[:10],
        category="BASELINE" if row["kind"] == "baseline" else "CANDIDATE", claim=claim,
        metric_direction="higher_better", protocol_id="", reps=1, reps_basis="scored",
        unit="chips/hand", attestation_path=str(root / "response-accounting.json"),
        attestation_sha256=row["accounting_sha256"], attestation_present=True,
        attestation_verified=True, source_kind=SOURCE_KIND,
        attestation_locator=f"{run_id}|{cohort}|raw={row['raw_sha256']}|accounting={row['accounting_sha256']}",
        extra={"diagnostic_only": True, "native_complete": acc["native_complete"],
               "accounting_complete": acc["accounting_complete"],
               "expected_hands": acc["expected_hands"], "counts": acc["counts"],
               "cohort": cohort, "hand_index": row["hand"], "worker_status": row["worker_status"],
               "response_ids": row["response_ids"], "raw_sha256": row["raw_sha256"],
               "source_manifest_sha256": rec["source_manifest_sha256"],
               "recipe": rec.get("recipe"), "model_sha256": rec.get("model_sha256"),
               "prompt_sha256": rec.get("prompt_sha256")},
        applicability={"model_file": model_file,
                       "backend": "gpu", "device": "mi210_0",
                       "model_sha256": rec.get("model_sha256")},
        observation={"outcome_native": "native diagnostic hand result",
                     "outcome_reason": "diagnostic only; not an efficacy or promotion result",
                     "retrofit": True},
    )
