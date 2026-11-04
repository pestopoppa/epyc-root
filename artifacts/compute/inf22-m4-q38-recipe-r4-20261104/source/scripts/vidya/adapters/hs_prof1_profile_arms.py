"""VB-HSPROF1-WRITE: the HS-PROF-1 BEAM profile-arm table as a measurement source (writer + reader).

HS-PROF-1 runs the BEAM reader twice under ONE context mode (``profile``) with two different
profile snapshots: ``pref_current`` (today's PREF[category] profile, the baseline) and ``admission``
(the admission-schema profile, the candidate). The SC68 BEAM carrier (``beam_memory_capture``)
cannot express that: its ``--arm`` must equal the rows' recorded context mode, which is ``profile``
for BOTH arms, and its single claim is the ten-column BEAM-fold headline, while HS-PROF-1 judges
two abilities. This module is the dedicated PROJECTION for the table
(``epyc-inference-research:scripts/benchmark/hs_prof1_profile_arms.py table``). It adds NO ladder:
rows project into the existing measurement :class:`ClaimTuple` and ``claim_tuple.grade()`` decides.

Claims written (one self-hashed row each, schema ``epyc.vidya.hs_prof1_profile_arms_capture.v1``):

* **arm mean**, per ability x arm: the judge-scored mean over the question ids BOTH arms scored
  (the table's paired basis), with ``n`` and the arm's own scored count. ``pref_current`` is
  ``BASELINE``, ``admission`` is ``CANDIDATE``. Attests ``scored_<arm>.json``.
* **paired delta**, per ability: mean of (admission - pref_current) over the shared ids, with the
  admission-win / pref-win / tie counts and ``n``. A separate claim (``CANDIDATE``), never folded
  into the arm rows. Attests ``table.json``. Report-only: no threshold or verdict is invented.

Every number is RE-DERIVED, not trusted: rows carry their per-question scores, the validator
recomputes value / n / win-loss-tie from them, and the writer refuses a ``table.json`` that does
not equal the recomputation from the two ``scored_<arm>.json`` files.

**Judge identity is part of the claim.** ``judge_backend`` (``served`` | ``cloud``), ``judge_model``,
``judge_prompt_version`` and ``question_in_judge_prompt`` always; for ``cloud`` also ``cloud_judge``,
``judge_model_id`` and ``judge_response_models`` (non-empty) — digested into
``judge_identity_sha256``, which enters the ``measurement_id`` and the locator, so the same arm
judged by two judges is two claims. ``judge_usage_totals`` (per arm) is recorded alongside, required
for ``cloud`` with ``calls > 0``, but is cost accounting rather than identity, so it is not hashed
into the id. A judged payload that predates the judge-backend fields (research ``02084e30c``) is
REFUSED, never back-filled as ``served``. Both arms must carry the identical judge identity.

**Refusals** (``CaptureError``, nothing written): missing judge identity; mock/fake/stub/dummy
runs (an identity token, a truthy ``mock``/``dry_run`` flag, or a cloud judge that recorded zero
calls or no response model); arm rows not all recorded as ``context_mode=profile`` with
``profile_arm == <arm>`` by the harness; ``checked_against_dataset`` false; reader identity that
differs between arms; per-row reader inference parameters that are not uniform.

**Absent stays absent.** The reader result JSON carries model role / path / config / run id /
timestamp and per-row inference parameters, but NOT the GGUF sha256, server build, recipe or argv;
the BEAM provenance carries split and ``beam_source`` but no dataset revision or parquet digest; the
reader rows do not record the profile-snapshot digest (the snapshot file is hashed at table time and
labelled as such). Caller-supplied ``reader_pins`` are recorded when given; every pin not given is
listed in ``extra.reader_pins_absent`` and never invented.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401
from adapters.beam_memory_capture import BEAM_ABILITIES, MIN_SCORER_VERSION, SPLITS  # noqa: E402

CAPTURE_SCHEMA = "epyc.vidya.hs_prof1_profile_arms_capture.v1"
SIDECAR_NAME = "hs_prof1_profile_arms.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.hs_prof1_profile_arms/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "hs-prof1-profile-arm-measurement"
TABLE_SCHEMA = "epyc.hs_prof1_table.v1"

ARMS = ("pref_current", "admission")
ARM_CATEGORY = {"pref_current": "BASELINE", "admission": "CANDIDATE"}
DELTA_ARM = "admission-minus-pref_current"
CONTEXT_MODE = "profile"
KIND_ARM, KIND_DELTA = "arm_mean", "paired_delta"
METRIC = {KIND_ARM: "hs_prof1_arm_judge_score_mean",
          KIND_DELTA: "hs_prof1_paired_delta_admission_minus_pref_current"}
UNIT = {KIND_ARM: "score", KIND_DELTA: "score_delta"}

JUDGE_BACKENDS = frozenset({"served", "cloud"})
JUDGE_TEXT = ("judge_model", "judge_prompt_version")
CLOUD_ONLY = ("cloud_judge", "judge_model_id", "judge_response_models")
JUDGE_FIELDS = ("judge_backend", *JUDGE_TEXT, "question_in_judge_prompt", *CLOUD_ONLY)
READER_PIN_FIELDS = ("model_sha256", "server_build", "recipe_path", "recipe_sha256", "argv")
_MOCK = re.compile(r"(^|[^a-z])(mock|fake|stub|dummy)([^a-z]|$)", re.IGNORECASE)
_TOL = 1e-9


# --- identity ------------------------------------------------------------------------------------

def judge_identity(source: Mapping[str, Any]) -> dict:
    """The judge identity fields of a judged payload or scored summary; absent fields are None."""
    return {k: source.get(k) for k in JUDGE_FIELDS}


def judge_identity_problems(ident: Any, *, where: str = "extra.judge") -> list[str]:
    if not isinstance(ident, dict) or sorted(ident) != sorted(JUDGE_FIELDS):
        return [f"{where} must carry exactly {sorted(JUDGE_FIELDS)}"]
    p: list[str] = []
    backend = ident["judge_backend"]
    if backend not in JUDGE_BACKENDS:
        p.append(f"{where}.judge_backend must be one of {sorted(JUDGE_BACKENDS)} (a payload that "
                 "predates the judge-backend fields is refused, never back-filled)")
    for key in JUDGE_TEXT:
        if not ns.text(ident[key]):
            p.append(f"{where}.{key} must be recorded")
    if not isinstance(ident["question_in_judge_prompt"], bool):
        p.append(f"{where}.question_in_judge_prompt must be a boolean")
    if backend == "cloud":
        for key in ("cloud_judge", "judge_model_id"):
            if not ns.text(ident[key]):
                p.append(f"{where}.{key} must be recorded for the cloud judge")
        models = ident["judge_response_models"]
        if not (isinstance(models, list) and models and all(ns.text(m) for m in models)
                and models == sorted(set(models))):
            p.append(f"{where}.judge_response_models must be a non-empty sorted list — a cloud "
                     "judge that recorded no answering model is not evidence a judge answered")
    elif backend == "served":
        for key in CLOUD_ONLY:
            if ident[key] is not None:
                p.append(f"{where}.{key} applies to the cloud backend only")
    for key in JUDGE_FIELDS:
        val = ident[key]
        vals = val if isinstance(val, list) else [val]
        if any(isinstance(v, str) and _MOCK.search(v) for v in vals):
            p.append(f"{where}.{key} names a mock/fake judge: {val!r}")
    return p


def usage_problems(usage: Any, *, where: str) -> list[str]:
    if not isinstance(usage, dict):
        return [f"{where} must be the judged payload's judge_usage_totals object"]
    calls = usage.get("calls")
    if not ns.nonneg_int(calls) or calls == 0:
        return [f"{where}.calls must be a positive integer — a cloud judge that made no call "
                "judged nothing"]
    return []


def measurement_identity(*, kind: str, ability: str, arm: str, run_ids: Mapping[str, str],
                         split: str, judge_identity_sha256: str, attested_sha256: str) -> str:
    return "hsp1_" + ns.content_hash({
        "kind": kind, "ability": ability, "arm": arm, "run_ids": dict(run_ids), "split": split,
        "judge": judge_identity_sha256, "attested": attested_sha256})[:24]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _score(v: Any) -> bool:
    return ns.finite(v) and 0.0 <= v <= 1.0


def _arm_basis(n: int, scored_in_arm: int) -> str:
    return ("scored:questions" if n == scored_in_arm
            else f"scored:questions (paired subset of {scored_in_arm} scored)")


# --- row validation (shared by writer and reader) ------------------------------------------------

def _reader_problems(reader: Any, pins: Any, absent: Any) -> list[str]:
    p: list[str] = []
    if not isinstance(reader, dict) or sorted(reader) != sorted(ARMS):
        return ["extra.reader must carry one identity per arm"]
    for arm in ARMS:
        r = reader[arm]
        if not isinstance(r, dict):
            p.append(f"extra.reader.{arm} must be an object")
            continue
        for key in ("run_id", "model_role", "model_path", "result_path"):
            if not ns.text(r.get(key)):
                p.append(f"extra.reader.{arm}.{key} must be recorded")
        if not ns.SHA256.match(str(r.get("result_sha256", ""))):
            p.append(f"extra.reader.{arm}.result_sha256 must be a 64-hex digest")
        if not isinstance(r.get("inference"), dict) or not r.get("inference"):
            p.append(f"extra.reader.{arm}.inference must be the uniform per-row inference block")
        if not ns.nonneg_int(r.get("profile_rows")) or r.get("profile_rows") == 0:
            p.append(f"extra.reader.{arm}.profile_rows must count the rows recorded under the arm")
    if not p:
        for key in ("model_role", "model_path", "config_name", "inference"):
            if reader[ARMS[0]].get(key) != reader[ARMS[1]].get(key):
                p.append(f"extra.reader.*.{key} differs between arms — not a paired profile A/B")
    if not isinstance(pins, dict) or set(pins) - set(READER_PIN_FIELDS):
        p.append(f"extra.reader_pins may only carry {list(READER_PIN_FIELDS)}")
    elif absent != sorted(set(READER_PIN_FIELDS) - set(pins)):
        p.append("extra.reader_pins_absent must list exactly the pins not supplied")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    kind = e.get("kind")
    if kind not in METRIC:
        return p + [f"extra.kind must be one of {sorted(METRIC)}"]
    if row.get("metric") != METRIC[kind] or row.get("unit") != UNIT[kind]:
        p.append(f"metric/unit must be {METRIC[kind]!r}/{UNIT[kind]!r} for kind {kind!r}")
    if row.get("metric_direction") != "higher_better":
        p.append("metric_direction must be higher_better (judge score; admission-minus-baseline)")
    if row.get("protocol_id") != CAPTURE_SCHEMA:
        p.append(f"protocol_id must be {CAPTURE_SCHEMA!r}")
    if e.get("ability") not in BEAM_ABILITIES:
        p.append("extra.ability must be a BEAM ability column")
    if e.get("split") not in SPLITS:
        p.append(f"extra.split must be one of {sorted(SPLITS)}")
    if e.get("context_mode") != CONTEXT_MODE:
        p.append("extra.context_mode must be 'profile' (both arms share it; the arm is the snapshot)")
    if e.get("checked_against_dataset") is not True:
        p.append("extra.checked_against_dataset must be true (score_beam_run --check-dataset)")
    if not ns.nonneg_int(e.get("scorer_version")) or e.get("scorer_version", 0) < MIN_SCORER_VERSION:
        p.append(f"extra.scorer_version must be >= {MIN_SCORER_VERSION}")
    if not ns.text(e.get("beam_source")):
        p.append("extra.beam_source must be the harness-recorded BEAM source")
    p += judge_identity_problems(e.get("judge"))
    if not p and e.get("judge_identity_sha256") != ns.content_hash(e["judge"]):
        p.append("extra.judge_identity_sha256 does not re-derive from extra.judge")
    usage = e.get("judge_usage_totals_by_arm")
    if isinstance(e.get("judge"), dict) and e["judge"].get("judge_backend") == "cloud":
        if not isinstance(usage, dict) or sorted(usage) != sorted(ARMS):
            p.append("extra.judge_usage_totals_by_arm must carry both arms for the cloud judge")
        else:
            for arm in ARMS:
                p += usage_problems(usage[arm], where=f"extra.judge_usage_totals_by_arm.{arm}")
    elif usage is not None:
        p.append("extra.judge_usage_totals_by_arm is recorded by the cloud judge only")
    p += _reader_problems(e.get("reader"), e.get("reader_pins"), e.get("reader_pins_absent"))
    if not isinstance(e.get("inputs"), dict):
        p.append("extra.inputs must bind the input files by digest")

    value, n = row.get("value"), e.get("n")
    if not ns.nonneg_int(n) or n == 0:
        p.append("extra.n must be a positive integer")
    elif row.get("reps") != n:
        p.append("reps must equal extra.n")
    if kind == KIND_ARM:
        arm = e.get("arm")
        if arm not in ARMS:
            p.append(f"extra.arm must be one of {list(ARMS)}")
        elif row.get("category") != ARM_CATEGORY[arm]:
            p.append(f"category must be {ARM_CATEGORY[arm]} for arm {arm}")
        pq = e.get("per_question")
        if not (isinstance(pq, list) and pq and all(
                isinstance(x, list) and len(x) == 2 and ns.text(x[0]) and _score(x[1]) for x in pq)):
            p.append("extra.per_question must list [question_id, score in [0,1]] pairs")
        else:
            if len({x[0] for x in pq}) != len(pq):
                p.append("extra.per_question repeats a question id")
            if n != len(pq):
                p.append("extra.n must equal the per-question count")
            if ns.finite(value) and abs(_mean([x[1] for x in pq]) - value) > _TOL:
                p.append("value does not re-derive as the mean of extra.per_question")
            sia = e.get("scored_in_arm")
            if not ns.nonneg_int(sia) or sia < len(pq):
                p.append("extra.scored_in_arm must be >= n")
            elif row.get("reps_basis") != _arm_basis(len(pq), sia):
                p.append(f"reps_basis must be {_arm_basis(len(pq), sia)!r}")
    else:
        if e.get("arm") != DELTA_ARM:
            p.append(f"extra.arm must be {DELTA_ARM!r} for the paired delta")
        if row.get("category") != "CANDIDATE":
            p.append("category must be CANDIDATE for the paired delta")
        if row.get("reps_basis") != "scored:paired_questions":
            p.append("reps_basis must be 'scored:paired_questions'")
        pr = e.get("paired")
        if not (isinstance(pr, list) and pr and all(
                isinstance(x, list) and len(x) == 3 and ns.text(x[0]) and _score(x[1])
                and _score(x[2]) for x in pr)):
            p.append("extra.paired must list [question_id, pref_current, admission] triples")
        else:
            d = [x[2] - x[1] for x in pr]
            if len({x[0] for x in pr}) != len(pr):
                p.append("extra.paired repeats a question id")
            if n != len(pr):
                p.append("extra.n must equal the paired count")
            if ns.finite(value) and abs(_mean(d) - value) > _TOL:
                p.append("value does not re-derive as the mean paired delta")
            want = {"admission_wins": sum(1 for x in d if x > 0),
                    "pref_wins": sum(1 for x in d if x < 0),
                    "ties": sum(1 for x in d if x == 0)}
            for key, val in want.items():
                if e.get(key) != val:
                    p.append(f"extra.{key} does not re-derive from extra.paired")
            means = e.get("arm_means")
            if not isinstance(means, dict) or sorted(means) != sorted(ARMS) or any(
                    not ns.finite(means[a]) for a in ARMS) or \
                    abs(means["pref_current"] - _mean([x[1] for x in pr])) > _TOL or \
                    abs(means["admission"] - _mean([x[2] for x in pr])) > _TOL:
                p.append("extra.arm_means must re-derive from extra.paired")
    if not p:
        p += ns.check_identity(row, {
            "kind": kind, "ability": e["ability"], "arm": e["arm"],
            "run_ids": {a: e["reader"][a]["run_id"] for a in ARMS}, "split": e["split"],
            "judge": e["judge_identity_sha256"], "attested": row["results_sha256"]}, "hsp1")
    return p + ns.self_hash_problems(row)


# --- writer --------------------------------------------------------------------------------------

def _load(path: Path, what: str) -> Any:
    if not path.is_file():
        raise CaptureError(f"{what} missing: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise CaptureError(f"{what} is not JSON: {path}: {exc}") from exc


def _single(counts: Any) -> str | None:
    if not isinstance(counts, Mapping):
        return None
    present = [k for k, v in counts.items() if ns.nonneg_int(v) and v > 0]
    return present[0] if len(present) == 1 else None


def _flagged_mock(doc: Any) -> bool:
    return isinstance(doc, Mapping) and any(bool(doc.get(k)) for k in ("mock", "dry_run", "fake"))


def _reader_identity(arm: str, result_path: Path, run_id: str) -> dict:
    doc = _load(result_path, f"reader result for arm {arm}")
    if _flagged_mock(doc):
        raise CaptureError(f"arm {arm}: reader result is flagged mock/dry_run — refused")
    rows = (doc.get("results") or {}).get("beam") if isinstance(doc, dict) else None
    if not isinstance(rows, dict) or not rows:
        raise CaptureError(f"arm {arm}: reader result carries no results['beam'] rows")
    bad = [q for q, r in rows.items()
           if (r.get("provenance") or {}).get("context_mode") != CONTEXT_MODE
           or (r.get("provenance") or {}).get("profile_arm") != arm]
    if bad:
        raise CaptureError(f"arm {arm}: {len(bad)} reader row(s) not recorded as "
                           f"context_mode=profile/profile_arm={arm} (e.g. {bad[0]}) — the arm "
                           "is only what the harness recorded, never the file name")
    inference = {ns.canonical_json(r.get("inference") or {}) for r in rows.values()}
    if len(inference) != 1 or inference == {"{}"}:
        raise CaptureError(f"arm {arm}: per-row inference parameters are missing or not uniform")
    sources = {(r.get("provenance") or {}).get("beam_source") for r in rows.values()}
    if len(sources) != 1 or not ns.text(next(iter(sources))):
        raise CaptureError(f"arm {arm}: beam_source is missing or not uniform")
    if doc.get("run_id") != run_id:
        raise CaptureError(f"arm {arm}: reader run_id {doc.get('run_id')!r} != scored run_id "
                           f"{run_id!r}")
    ident = {
        "run_id": run_id, "model_role": doc.get("model_role"), "model_path": doc.get("model_path"),
        "config_name": doc.get("config_name"), "timestamp": doc.get("timestamp"),
        "inference": json.loads(next(iter(inference))), "profile_rows": len(rows),
        "result_path": str(result_path), "result_sha256": ns.file_sha256(result_path),
    }
    for key in ("model_role", "model_path", "run_id"):
        if not ns.text(ident[key]):
            raise CaptureError(f"arm {arm}: reader result does not record {key}")
        if _MOCK.search(ident[key]):
            raise CaptureError(f"arm {arm}: reader {key} names a mock run: {ident[key]!r}")
    ident["_rows"] = rows
    ident["_beam_source"] = next(iter(sources))
    return ident


def recompute_table(per_question: Mapping[str, list]) -> dict:
    """The research ``table()`` arithmetic, re-derived from the scored per-question lists."""
    qa = {r["question_id"]: r for r in per_question[ARMS[0]]}
    qb = {r["question_id"]: r for r in per_question[ARMS[1]]}
    shared = sorted(set(qa) & set(qb))
    out: dict[str, dict] = {}
    for ability in sorted({qa[q]["ability"] for q in shared}):
        ids = [q for q in shared if qa[q]["ability"] == ability]
        if any(qb[q]["ability"] != ability for q in ids):
            raise CaptureError(f"{ability}: a shared question id carries different abilities")
        out[ability] = {"ids": ids, "a": [qa[q]["score"] for q in ids],
                        "b": [qb[q]["score"] for q in ids]}
    return out


def write_belief_measurements(
    out_dir: str | Path, *, table_path: str | Path, producer: str,
    run_id: str | None = None, reader_pins: Mapping[str, Any] | None = None,
    emitted_at: str | None = None, sidecar_path: str | Path | None = None,
) -> Path:
    """Emit ``hs_prof1_profile_arms.beliefs.jsonl`` beside ``table.json`` (call AFTER writing it).

    Reads the HS-PROF-1 ``OUT_DIR`` exactly as ``run_hs_prof1_beam_arm.sh`` leaves it:
    ``arm_<arm>.result.path`` (-> the reader result JSON), ``judged_<arm>.json``,
    ``scored_<arm>.json``, ``snapshots_<arm>.json`` and the table. ``reader_pins`` optionally
    supplies {model_sha256, server_build, recipe_path, recipe_sha256, argv} — only what the caller
    actually captured. Raises :class:`CaptureError`; nothing is written on any refusal.
    """
    out = Path(out_dir)
    table_file = Path(table_path)
    table = _load(table_file, "table.json")
    if not isinstance(table, dict) or table.get("schema") != TABLE_SCHEMA \
            or table.get("arms") != list(ARMS):
        raise CaptureError(f"table must be {TABLE_SCHEMA} over arms {list(ARMS)}")
    pins = dict(reader_pins or {})
    unknown = sorted(set(pins) - set(READER_PIN_FIELDS))
    if unknown:
        raise CaptureError(f"reader_pins has unknown fields {unknown}")
    pins = {k: v for k, v in pins.items() if v not in (None, "", [])}

    scored, judged, reader, inputs, usage = {}, {}, {}, {}, {}
    idents = {}
    for arm in ARMS:
        sp, jp = out / f"scored_{arm}.json", out / f"judged_{arm}.json"
        scored[arm], judged[arm] = _load(sp, f"scored_{arm}.json"), _load(jp, f"judged_{arm}.json")
        summ = scored[arm].get("summary") if isinstance(scored[arm], dict) else None
        if not isinstance(summ, dict) or not isinstance(scored[arm].get("per_question"), list):
            raise CaptureError(f"scored_{arm}.json is not a score_beam_run report")
        if _flagged_mock(judged[arm]) or _flagged_mock(summ):
            raise CaptureError(f"arm {arm}: judged/scored payload is flagged mock — refused")
        if _single(summ.get("context_mode_by_row")) != CONTEXT_MODE or \
                _single(judged[arm].get("context_mode_by_row")) != CONTEXT_MODE:
            raise CaptureError(f"arm {arm}: rows were not all recorded under context_mode=profile")
        ident = judge_identity(judged[arm])
        if judge_identity(summ) != ident:
            raise CaptureError(f"arm {arm}: scored summary judge identity differs from the judged "
                               "payload it folded")
        bad = judge_identity_problems(ident, where=f"judged_{arm}")
        if bad:
            raise CaptureError(f"arm {arm}: judge identity refused: " + "; ".join(bad))
        if ident["judge_backend"] == "cloud":
            bad = usage_problems(judged[arm].get("judge_usage_totals"),
                                 where=f"judged_{arm}.judge_usage_totals")
            if bad:
                raise CaptureError(f"arm {arm}: " + "; ".join(bad))
            usage[arm] = judged[arm]["judge_usage_totals"]
        idents[arm] = ident
        if summ.get("checked_against_dataset") is not True:
            raise CaptureError(f"arm {arm}: scored without --check-dataset")
        rp_file = out / f"arm_{arm}.result.path"
        if not rp_file.is_file():
            raise CaptureError(f"arm {arm}: {rp_file} missing — reader result not recorded")
        result_path = Path(rp_file.read_text().strip())
        rid = summ.get("run_id")
        if not ns.text(rid) or judged[arm].get("run_id") != rid:
            raise CaptureError(f"arm {arm}: run_id missing or judged/scored disagree")
        reader[arm] = _reader_identity(arm, result_path, rid)
        missing = sorted({r["question_id"] for r in scored[arm]["per_question"]}
                         - set(reader[arm]["_rows"]))
        if missing:
            raise CaptureError(f"arm {arm}: scored ids absent from the reader result: {missing[:3]}")
        snap = out / f"snapshots_{arm}.json"
        inputs[arm] = {
            "scored_path": str(sp), "scored_sha256": ns.file_sha256(sp),
            "judged_path": str(jp), "judged_sha256": ns.file_sha256(jp),
            "snapshots_path": str(snap),
            "snapshots_sha256": ns.file_sha256(snap) if snap.is_file() else None,
            "snapshots_basis": ("hashed at table time; the reader rows do not record the "
                                "snapshot digest" if snap.is_file() else "absent at table time"),
        }
    if idents[ARMS[0]] != idents[ARMS[1]]:
        raise CaptureError("the two arms were judged under different judge identities — a paired "
                           "delta across judges is not one measurement")
    s0, s1 = (scored[a]["summary"] for a in ARMS)
    for key in ("split", "scorer_version", "model_role"):
        if s0.get(key) != s1.get(key):
            raise CaptureError(f"summary.{key} differs between arms")
    split = s0.get("split")
    if reader[ARMS[0]]["_beam_source"] != reader[ARMS[1]]["_beam_source"]:
        raise CaptureError("beam_source differs between arms")
    beam_source = reader[ARMS[0]]["_beam_source"]
    reader_pub = {a: {k: v for k, v in reader[a].items() if not k.startswith("_")} for a in ARMS}
    judge = idents[ARMS[0]]
    judge_sha = ns.content_hash(judge)
    run_ids = {a: reader[a]["run_id"] for a in ARMS}
    table_sha = ns.file_sha256(table_file)
    inputs["table"] = {"path": str(table_file), "sha256": table_sha}

    derived = recompute_table({a: scored[a]["per_question"] for a in ARMS})
    tab = table.get("per_ability")
    if not isinstance(tab, dict) or sorted(tab) != sorted(derived):
        raise CaptureError("table.json abilities do not equal the recomputation from scored files")
    for ability, cell in derived.items():
        a, b = cell["a"], cell["b"]
        d = [y - x for x, y in zip(a, b)]
        want = {"n": len(a), "pref_current": _mean(a), "admission": _mean(b),
                "mean_delta": _mean(d), "admission_wins": sum(1 for x in d if x > 0),
                "pref_wins": sum(1 for x in d if x < 0), "ties": sum(1 for x in d if x == 0)}
        got = tab[ability]
        for key, val in want.items():
            g = got.get(key) if isinstance(got, dict) else None
            if not ns.finite(g) or abs(g - val) > _TOL:
                raise CaptureError(f"table.json {ability}.{key}={g!r} does not re-derive ({val!r})")

    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    run_label = run_id or f"hsprof1:{run_ids['pref_current']}+{run_ids['admission']}"
    scored_in_arm = {a: {} for a in ARMS}
    for a in ARMS:
        for r in scored[a]["per_question"]:
            scored_in_arm[a][r["ability"]] = scored_in_arm[a].get(r["ability"], 0) + 1
    common = {
        "split": split, "context_mode": CONTEXT_MODE, "beam_source": beam_source,
        "checked_against_dataset": True, "scorer_version": s0.get("scorer_version"),
        "judge": judge, "judge_identity_sha256": judge_sha,
        "judge_usage_totals_by_arm": usage or None,
        "reader": reader_pub, "reader_pins": pins,
        "reader_pins_absent": sorted(set(READER_PIN_FIELDS) - set(pins)),
        "inputs": inputs, "table_schema": TABLE_SCHEMA,
    }
    judge_tag = (f"{judge['judge_backend']}:{judge['cloud_judge'] or '-'}:"
                 f"{judge['judge_model_id'] or judge['judge_model']}")

    def build(kind: str, ability: str, arm: str, value: float, n: int, category: str,
              basis: str, attested: Path, attested_sha: str, extra: dict, claim: str) -> dict:
        e = {"kind": kind, "ability": ability, "arm": arm, "n": n, **common, **extra}
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_label, "producer": producer,
            "emitted_at": when, "date": when[:10], "metric": METRIC[kind], "value": value,
            "unit": UNIT[kind], "metric_direction": "higher_better", "category": category,
            "claim": claim, "protocol_id": CAPTURE_SCHEMA, "reps": n, "reps_basis": basis,
            "results_path": str(attested), "results_sha256": attested_sha, "extra": e,
            "measurement_id": measurement_identity(
                kind=kind, ability=ability, arm=arm, run_ids=run_ids, split=str(split),
                judge_identity_sha256=judge_sha, attested_sha256=attested_sha),
        }
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid HS-PROF-1 row: " + "; ".join(bad))
        return row

    rows = []
    for ability, cell in derived.items():
        ids = cell["ids"]
        for arm, scores in ((ARMS[0], cell["a"]), (ARMS[1], cell["b"])):
            n, val = len(scores), _mean(scores)
            rows.append(build(
                KIND_ARM, ability, arm, val, n, ARM_CATEGORY[arm],
                _arm_basis(n, scored_in_arm[arm][ability]),
                Path(inputs[arm]["scored_path"]), inputs[arm]["scored_sha256"],
                {"per_question": [[q, s] for q, s in zip(ids, scores)],
                 "scored_in_arm": scored_in_arm[arm][ability]},
                f"HS-PROF-1 BEAM {split} {ability}, profile arm {arm}: judge-scored mean "
                f"{val:.4f} over n={n} paired questions (judge {judge_tag})"))
        d = [y - x for x, y in zip(cell["a"], cell["b"])]
        wins = {"admission_wins": sum(1 for x in d if x > 0),
                "pref_wins": sum(1 for x in d if x < 0), "ties": sum(1 for x in d if x == 0)}
        rows.append(build(
            KIND_DELTA, ability, DELTA_ARM, _mean(d), len(d), "CANDIDATE",
            "scored:paired_questions", table_file, table_sha,
            {"paired": [[q, x, y] for q, x, y in zip(ids, cell["a"], cell["b"])], **wins,
             "arm_means": {"pref_current": _mean(cell["a"]), "admission": _mean(cell["b"])}},
            f"HS-PROF-1 BEAM {split} {ability}: admission minus pref_current paired delta "
            f"{_mean(d):+.4f} over n={len(d)} (wins {wins['admission_wins']}/"
            f"losses {wins['pref_wins']}/ties {wins['ties']}; judge {judge_tag}); report-only, "
            "no threshold"))
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate measurement identity")
    target = Path(sidecar_path) if sidecar_path else table_file.parent / SIDECAR_NAME
    return ns.write_rows_atomic(target, rows)


# --- reader / projection -------------------------------------------------------------------------

def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    """Projection only; revalidates so callers cannot bypass ``native_rows``."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("HS-PROF-1 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("HS-PROF-1 row is not a producer-authored capture: "
                              + "; ".join(problems))
    e, j = row["extra"], row["extra"]["judge"]
    locator = (f"hsprof1:{row['run_id']}:{e['split']}:{e['ability']}:{e['kind']}:arm-{e['arm']}:"
               f"judge-{j['judge_backend']}:{j['cloud_judge'] or '-'}:"
               f"{j['judge_model_id'] or j['judge_model']}:{e['judge_identity_sha256'][:16]}")
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = [
    "CAPTURE_SCHEMA", "SIDECAR_NAME", "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "ARMS",
    "ARM_CATEGORY", "METRIC", "JUDGE_FIELDS", "READER_PIN_FIELDS", "CaptureError",
    "judge_identity", "judge_identity_problems", "measurement_identity", "validate_row",
    "recompute_table", "write_belief_measurements", "native_rows", "rows_for_run", "project",
    "frames_for_sidecar",
]
