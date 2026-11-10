"""VB-CJ7A-INVERSE-MUTATION-WRITE: CJ-7a inverse-edit fixture outcome records (`verifier` class).

Producer (research repo): ``scripts/benchmark/inverse_mutation_v1/scorer.py::score()`` returns one
native outcome record per (fixture, candidate); ``control_proof.py`` persists the deterministic
native controls as ``fixtures/native_control_proof.json`` (schema ``cj7a_native_control_proof.v1``).

This adapter only PROJECTS what the native checker decided:

* ``decided_proposition`` is the producer's own string. The reader RE-DERIVES it from the record's
  normalized hashes and formatter identity and refuses any difference -- it is never composed on read.
* ``value`` is 1 when the native verdict is ``pass`` (normalized candidate hash == pinned inverse
  normalized hash) and 0 when ``fail``; the verdict must agree with the hashes.
* An ``out-of-coverage`` record (formatter absent/mismatched/timeout, no candidate) is UNDECIDED: it is
  refused with its cause and yields no tuple, never a 0.
* Only the two native control kinds are admitted. A record without a control kind is a model
  evaluation, which needs the issued-task / model / runtime binding that does not exist yet; it is
  refused rather than guessed. No model-efficacy, software-engineering or representative-mix claim.
* ``binding_kind`` stays empty: the proposition (a hash equality under one formatter) is not bound to
  any wider claim, so the shared SC56 cap applies. ``protocol_id`` is empty: an OBSERVATION.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.cj7a_inverse_mutation/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "cj7a-inverse-mutation"
DOC_SCHEMA = "cj7a_native_control_proof.v1"
METRIC = "cj7a_inverse_normalized_hash_equal"
CONTROL_KINDS = frozenset({"correct-inverse-control", "mutated-source-negative-control"})
MUTATIONS = frozenset({"operator-swap", "boolean-flip", "off-by-one", "removed-guard"})
_HEX = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED = ("recorded_at_utc", "fixture_id", "instruction", "instruction_sha256", "source_sha256",
             "source_provenance", "mutation", "candidate_raw_sha256", "candidate_normalized_sha256",
             "expected_normalized_sha256", "decided_proposition", "formatter", "verdict", "control_kind")


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _proposition(rec: Mapping[str, Any]) -> str:
    f = rec["formatter"]
    return ("candidate normalized SHA-256 equals the pinned inverse normalized SHA-256 "
            f"under Ruff {f['version']} ({f['configuration']}): "
            f"{rec['candidate_normalized_sha256']} == {rec['expected_normalized_sha256']}")


def _problems(rec: Any) -> list[str]:
    if not isinstance(rec, dict):
        return ["record is not an object"]
    if rec.get("verdict") == "out-of-coverage":
        return [f"undecided (out-of-coverage, cause={rec.get('cause')!r}): no proposition was decided"]
    p = [f"missing {k}" for k in _REQUIRED if rec.get(k) in (None, "")]
    if p:
        return p
    if rec["control_kind"] not in CONTROL_KINDS:
        p.append("not a native control record: a model evaluation needs its issued-task/model binding")
    if rec["verdict"] not in ("pass", "fail"):
        p.append("verdict must be pass or fail")
    if rec["mutation"] not in MUTATIONS:
        p.append("unknown mutation kind")
    for k in ("instruction_sha256", "source_sha256", "candidate_raw_sha256",
              "candidate_normalized_sha256", "expected_normalized_sha256"):
        if not _HEX.match(str(rec[k])):
            p.append(f"{k} must be a 64-hex digest")
    f, prov = rec["formatter"], rec["source_provenance"]
    if not isinstance(f, dict) or any(not f.get(k) for k in ("version", "configuration", "executable_sha256")):
        return p + ["formatter identity (version/configuration/executable_sha256) is incomplete"]
    if not isinstance(prov, dict) or prov.get("source_sha256") != rec["source_sha256"]:
        p.append("source provenance does not bind source_sha256")
    elif not all(prov.get(k) for k in ("repository", "commit", "path", "license")):
        p.append("source provenance lacks repository/commit/path/license pins")
    if hashlib.sha256(str(rec["instruction"]).encode()).hexdigest() != rec["instruction_sha256"]:
        p.append("instruction_sha256 does not hash the recorded instruction")
    if p:
        return p
    equal = rec["candidate_normalized_sha256"] == rec["expected_normalized_sha256"]
    if (rec["verdict"] == "pass") != equal:
        p.append("verdict disagrees with the normalized hashes")
    if rec["decided_proposition"] != _proposition(rec):
        p.append("decided_proposition does not re-derive from the record's hashes and formatter")
    try:
        if datetime.fromisoformat(str(rec["recorded_at_utc"])).utcoffset() is None:
            p.append("recorded_at_utc must carry a UTC offset")
    except ValueError:
        p.append("recorded_at_utc is not a timestamp")
    return p


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Re-open one persisted outcome document; every record is returned with its own problems intact
    (an undecided or malformed record is refused at ``project``, never silently dropped)."""
    p = Path(path)
    if not p.is_file():
        return ()
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"CJ-7a document unreadable: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != DOC_SCHEMA or not isinstance(doc.get("records"), list):
        raise ProjectionError(f"not a {DOC_SCHEMA} document")
    digest = _sha(p)
    return tuple({"record": r, "doc_path": str(p), "doc_sha256": digest} for r in doc["records"])


@register("cj7a_inverse_mutation", source_class="verifier", decided_proposition_field="decided_proposition")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one native outcome. The shared ladder and SC56 cap grade it; nothing is graded here."""
    if not isinstance(native, Mapping) or not isinstance(native.get("record"), Mapping):
        raise ProjectionError("CJ-7a native must retain the producer record")
    rec = dict(native["record"])
    problems = _problems(rec)
    if problems:
        raise ProjectionError("CJ-7a record refused: " + "; ".join(problems))
    doc = Path(native["doc_path"])
    if not doc.is_file() or _sha(doc) != native["doc_sha256"]:
        raise ProjectionError("CJ-7a document no longer carries the hashed bytes")
    held = rec["verdict"] == "pass"
    ident = hashlib.sha256("|".join((rec["fixture_id"], rec["control_kind"], rec["candidate_raw_sha256"],
                                     rec["recorded_at_utc"])).encode()).hexdigest()[:24]
    f = rec["formatter"]
    return ClaimTuple(
        measurement_id=f"cj7a_{ident}", metric=METRIC, value=1 if held else 0, unit="proposition held",
        metric_direction="higher_better", category="BASELINE", date=rec["recorded_at_utc"], protocol_id="",
        claim=(f"CJ-7a {rec['mutation']} fixture {rec['fixture_id']} ({rec['control_kind']}): the formatter-"
               f"normalized candidate hash {'equals' if held else 'does not equal'} the pinned inverse hash "
               "(mechanical edit application only; no model efficacy)"),
        reps=1, reps_basis="scored: one fixture, one candidate",
        attestation_path=str(doc), attestation_sha256=native["doc_sha256"], attestation_present=True,
        attestation_verified=True, attestation_locator=f"cj7a:{doc.name}#{rec['fixture_id']}:{rec['control_kind']}",
        source_kind=SOURCE_KIND, decided_proposition=rec["decided_proposition"], binding_kind="",
        extra={"schema": DOC_SCHEMA, "fixture_id": rec["fixture_id"], "mutation": rec["mutation"],
               "control_kind": rec["control_kind"], "verdict": rec["verdict"],
               "source_sha256": rec["source_sha256"], "source_provenance": rec["source_provenance"],
               "instruction_sha256": rec["instruction_sha256"],
               "candidate_raw_sha256": rec["candidate_raw_sha256"],
               "candidate_normalized_sha256": rec["candidate_normalized_sha256"],
               "expected_normalized_sha256": rec["expected_normalized_sha256"], "formatter": dict(f),
               "control_behaved": held == (rec["control_kind"] == "correct-inverse-control")})


__all__ = ["ADAPTER_ID", "AUTHORITY", "METRIC", "native_rows", "project"]
