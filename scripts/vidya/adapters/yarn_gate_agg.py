"""VB-YARN-AGG-1: YaRN gate aggregation / recall / judged arms as a measurement source.

Research producers (``scripts/benchmark/yarn_gate/`` on main): ``agg_scoring.py`` (Oolong real-length
bins, ``net_paired_mcnemar``), ``helmet_judged_cell.py`` (``epyc.yarn_helmet_judged_cell.v1``),
``local_judge.py`` (``JudgePin.claim_fields()``), ``judge_validation_kit.py``
(``epyc.yarn_judge_pin.v1``), ``retokenize.py`` (``label_zone`` / ``bin_label``). No single
"decision record" exists in that code today (only the pieces), so THIS docstring defines the record
the runner must write, ``epyc.yarn_gate_decision.v1``, one JSON object per cell or verdict, in a
file the runner keeps durable (the file's sha256 is the row attestation).

Expected record fields (all REQUIRED unless marked optional; absent -> CaptureError naming the field):

  schema            "epyc.yarn_gate_decision.v1"
  record_kind       "cell" | "verdict"
  mock              bool. True only for fixture/mock-judge cells. The WRITER refuses mock unless called
                    with ``fixture=True`` (tests); a real run with a mock cell is refused.
  comparison        "A0_vs_A1" | "CN_vs_CY2"
  arm_role          cell: "A0" | "A1" | "CN" | "CY2";  verdict: "A1_vs_A0" | "CY2_vs_CN"
  suite             "oolong" | "helmet" | "longbio"
  task              str (oolong counting/user, helmet cell name, longbio variant)
  nominal_length    int, informational ONLY; never a scope axis, never used for the zone
  model_pin         str: served model id (+ GGUF); ``model_file_sha256`` optional 64-hex
  prompt_n          {source, count, min, median, max}: REAL prompt tokens (prompt_n + cache_n);
                    ``source`` in {"served_tokenizer","server_timings","model_tokenizer_json"}
  bin               "lo-hi" from retokenize.bin_label (step 32768): lo < min and max <= hi
  zone              "native" | "boundary" | "beyond-native" from retokenize.label_zone; "mixed" is refused
                    (a cell is one zone); min and max must land in that zone (native 262144, reserve 4096)
  source_pins       per suite: oolong -> {"source_revision": "oolongbench/oolong-synth@<40hex>",
                    "vendored_sha256"}; helmet -> {"helmet_pin": 40hex, "config_file", "config_sha256",
                    "max_test_samples"}; longbio -> {"generator_pin": 40hex}; ruler -> {"ruler_repo", "ruler_pin" (7-40 hex
                    checkout commit), "essay_sha256" (64hex, local Paul Graham essay haystack), "words_source"
                    == "essay_vocab_hyphen_pairs" (hyphenated-pair keys), "deviations" (non-empty list of the
                    local-generation deviations from upstream RULER, research ruler_local.py DEVIATIONS)}.
                    RULER items are locally generated, never comparable to published RULER numbers.
  judged            bool. True -> ``judge_pin`` {model, prompt_version, prompt_sha256 (64hex),
                    temperature, seed, max_tokens} (== JudgePin.claim_fields()) AND
                    ``judge_validation`` {n_compared, accuracy, cohen_kappa (null ok), sheet_sha256}
                    (the 50-item hand-agreement record) are required; False -> both must be absent
  comparable_to_published   must be false

  cell only:        metric in {mean_score, accuracy, attempted_rate, exact_match (higher_better),
                    no_answer_rate (lower_better)}; value finite in [0,1]; n_units int>0; unit
                    "contexts" (oolong, clustered) | "items"; n_unjudged int>=0 (0 if not judged);
                    ci {lo, hi} optional
  verdict only:     verdict in {"PASS","FAIL","INCONCLUSIVE","NOT-FAIL"} stored VERBATIM (INCONCLUSIVE is
                    never folded to PASS; the producer's ``net_paired_mcnemar`` emits FAIL/NOT-FAIL),
                    rule_id str, alpha, b_a0right_a1wrong, c_a0wrong_a1right, n_pairs, p_one_sided,
                    mean_score_diff_a1_minus_a0 (value), a0_record_sha256, a1_record_sha256 (the paired
                    cell record files' digests)

Projection: cell value = ``value``, reps = ``n_units`` (reps_basis names the unit); verdict value =
the mean paired score difference, reps = ``n_pairs`` (basis "pairs"), verdict/b/c/p/alpha ride in
``extra``. Category BASELINE for A0/CN, CANDIDATE for A1/CY2 and for verdicts. Judge pin, zone, bin,
pins ride in ``extra`` and so in the tuple. ``claim_tuple.grade()`` decides; there is no ladder here.
A protocol id is carried only if the caller names one (the pre-declared margin rule applies); else
``observation:none`` -> projected empty (an OBSERVATION).

Mock rows: written only with ``fixture=True``, stamped ``extra.mock/fixture`` true with a ``fixture:``
locator; ``native_rows`` voids any sidecar containing them unless ``allow_fixture=True``.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

DECISION_SCHEMA = "epyc.yarn_gate_decision.v1"
CAPTURE_SCHEMA = "epyc.vidya.yarn_gate_agg_capture.v1"
SIDECAR_NAME = "yarn_gate_agg.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.yarn_gate_agg/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "yarn-gate-agg-measurement"
NO_PROTOCOL = "observation:none"

#: retokenize.py constants (producer-owned; consistency check only, never the labeller).
NATIVE_CTX, RESERVE, BIN_STEP = 262144, 4096, 32768
MEASURED_SOURCES = ("served_tokenizer", "server_timings", "model_tokenizer_json")
ZONES = ("native", "boundary", "beyond-native")
COMPARISONS = {"A0_vs_A1": ("A0", "A1", "A1_vs_A0"), "CN_vs_CY2": ("CN", "CY2", "CY2_vs_CN")}
BASELINE_ROLES, CANDIDATE_ROLES = ("A0", "CN"), ("A1", "CY2")
SUITES = ("oolong", "helmet", "longbio", "ruler")
CELL_METRICS = {"mean_score": "higher_better", "accuracy": "higher_better",
                "attempted_rate": "higher_better", "exact_match": "higher_better",
                "no_answer_rate": "lower_better"}
VERDICTS = ("PASS", "FAIL", "INCONCLUSIVE", "NOT-FAIL")
VERDICT_METRIC = "yarn_net_paired_score_diff_a1_minus_a0"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RULER_PIN = re.compile(r"^[0-9a-f]{7,40}$")
RULER_WORDS_SOURCE = "essay_vocab_hyphen_pairs"
JUDGE_PIN_KEYS = ("model", "prompt_version", "prompt_sha256", "temperature", "seed", "max_tokens")


def _zone(n: int) -> str:
    return "beyond-native" if n > NATIVE_CTX else ("native" if n + RESERVE <= NATIVE_CTX else "boundary")


def record_problems(rec: Any, *, where: str = "record") -> list[str]:
    """Strict check of one decision record (the producer-facing schema above)."""
    if not isinstance(rec, dict):
        return [f"{where}: not an object"]
    p: list[str] = []
    def need(k, ok, msg):
        if k not in rec:
            p.append(f"{where}: field {k!r} absent (producer gap)")
        elif not ok(rec[k]):
            p.append(f"{where}: {k} {msg}")
    need("schema", lambda v: v == DECISION_SCHEMA, f"must be {DECISION_SCHEMA}")
    need("record_kind", lambda v: v in ("cell", "verdict"), "must be cell|verdict")
    need("mock", lambda v: isinstance(v, bool), "must be a boolean")
    need("comparison", lambda v: v in COMPARISONS, f"must be one of {sorted(COMPARISONS)}")
    need("suite", lambda v: v in SUITES, f"must be one of {SUITES}")
    need("task", ns.text, "must be a non-empty string")
    need("nominal_length", ns.nonneg_int, "must be an integer (informational only)")
    need("model_pin", ns.text, "must be a non-empty string")
    need("comparable_to_published", lambda v: v is False, "must be false")
    need("judged", lambda v: isinstance(v, bool), "must be a boolean")
    if p:
        return p
    pair = COMPARISONS[rec["comparison"]]
    kind = rec["record_kind"]
    allowed = pair[:2] if kind == "cell" else (pair[2],)
    need("arm_role", lambda v: v in allowed, f"must be one of {allowed} for a {kind}")
    # real length, bin, zone
    pn = rec.get("prompt_n")
    if not isinstance(pn, dict):
        p.append(f"{where}: prompt_n absent or not an object (REAL measured count required)")
    else:
        if pn.get("source") not in MEASURED_SOURCES:
            p.append(f"{where}: prompt_n.source must be a measured source {MEASURED_SOURCES}")
        vals = [pn.get(k) for k in ("min", "median", "max")]
        if not all(ns.nonneg_int(v) and v > 0 for v in vals) or not ns.nonneg_int(pn.get("count")) \
                or not pn.get("count") or not (vals[0] <= vals[1] <= vals[2]):
            p.append(f"{where}: prompt_n needs positive integer count/min<=median<=max")
        else:
            z = rec.get("zone")
            if z not in ZONES:
                p.append(f"{where}: zone must be one of {ZONES} (mixed/nominal refused)")
            elif _zone(vals[0]) != z or _zone(vals[2]) != z:
                p.append(f"{where}: zone {z!r} inconsistent with measured prompt_n min/max")
            m = re.fullmatch(r"(\d+)-(\d+)", str(rec.get("bin", "")))
            if not m or int(m[2]) - int(m[1]) != BIN_STEP or not (int(m[1]) < vals[0] and vals[2] <= int(m[2])):
                p.append(f"{where}: bin must be a {BIN_STEP}-wide 'lo-hi' containing min..max")
    # source pins
    sp, suite = rec.get("source_pins"), rec["suite"]
    if not isinstance(sp, dict):
        p.append(f"{where}: source_pins absent")
    elif suite == "oolong":
        name, _, rev = str(sp.get("source_revision", "")).partition("@")
        if not name.startswith("oolongbench/") or not HEX40.match(rev) or not ns.SHA256.match(str(sp.get("vendored_sha256", ""))):
            p.append(f"{where}: source_pins needs oolongbench/<set>@<40hex> source_revision and vendored_sha256")
    elif suite == "helmet":
        if not HEX40.match(str(sp.get("helmet_pin", ""))) or not ns.text(sp.get("config_file")) \
                or not ns.SHA256.match(str(sp.get("config_sha256", ""))) or "max_test_samples" not in sp:
            p.append(f"{where}: helmet source_pins needs helmet_pin(40hex), config_file, config_sha256, max_test_samples")
    elif suite == "ruler":
        dev = sp.get("deviations")
        if not ns.text(sp.get("ruler_repo")) or not RULER_PIN.match(str(sp.get("ruler_pin", ""))) \
                or not ns.SHA256.match(str(sp.get("essay_sha256", ""))) \
                or sp.get("words_source") != RULER_WORDS_SOURCE \
                or not isinstance(dev, list) or not dev or not all(ns.text(d) for d in dev):
            p.append(f"{where}: ruler source_pins needs ruler_repo, ruler_pin(7-40hex), essay_sha256, "
                     f"words_source={RULER_WORDS_SOURCE!r} and a non-empty deviations list")
    elif not HEX40.match(str(sp.get("generator_pin", ""))):
        p.append(f"{where}: longbio source_pins needs generator_pin(40hex)")
    # judge
    jp, jv = rec.get("judge_pin"), rec.get("judge_validation")
    if rec["judged"]:
        if not isinstance(jp, dict) or any(k not in jp for k in JUDGE_PIN_KEYS) \
                or not ns.SHA256.match(str(jp.get("prompt_sha256", ""))) or not ns.text(jp.get("model")):
            p.append(f"{where}: judged record needs judge_pin with {JUDGE_PIN_KEYS}")
        if not isinstance(jv, dict) or not ns.nonneg_int(jv.get("n_compared")) or not jv.get("n_compared") \
                or not ns.finite(jv.get("accuracy")) or not ns.SHA256.match(str(jv.get("sheet_sha256", ""))):
            p.append(f"{where}: judged record needs judge_validation (n_compared, accuracy, sheet_sha256)")
    elif jp is not None or jv is not None:
        p.append(f"{where}: judge_pin/judge_validation present on an unjudged record")
    if kind == "cell":
        need("metric", lambda v: v in CELL_METRICS, f"must be one of {sorted(CELL_METRICS)}")
        need("value", lambda v: ns.finite(v) and 0 <= v <= 1, "must be finite in [0,1]")
        need("n_units", lambda v: ns.nonneg_int(v) and v > 0, "must be a positive integer")
        need("unit", lambda v: v in ("contexts", "items"), "must be contexts|items")
        need("n_unjudged", ns.nonneg_int, "must be a non-negative integer")
        if rec.get("n_unjudged") and not rec["judged"]:
            p.append(f"{where}: n_unjudged>0 on an unjudged record")
        if suite == "oolong" and rec.get("unit") != "contexts":
            p.append(f"{where}: oolong cells are context-clustered: unit must be contexts")
    else:
        need("verdict", lambda v: v in VERDICTS, f"must be verbatim one of {VERDICTS}")
        need("rule_id", ns.text, "must be a non-empty string")
        need("alpha", lambda v: ns.finite(v) and 0 < v < 1, "must be in (0,1)")
        need("p_one_sided", lambda v: ns.finite(v) and 0 <= v <= 1, "must be in [0,1]")
        need("mean_score_diff_a1_minus_a0", ns.finite, "must be finite (no pairs -> no verdict row)")
        for k in ("b_a0right_a1wrong", "c_a0wrong_a1right", "n_pairs"):
            need(k, ns.nonneg_int, "must be a non-negative integer")
        for k in ("a0_record_sha256", "a1_record_sha256"):
            need(k, lambda v: bool(ns.SHA256.match(str(v))), "must be a 64-hex digest")
        if not p and (rec["b_a0right_a1wrong"] + rec["c_a0wrong_a1right"] > rec["n_pairs"] or rec["n_pairs"] == 0):
            p.append(f"{where}: discordants exceed pairs or n_pairs is 0")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    rec = e.get("decision")
    p += record_problems(rec, where="extra.decision")
    if isinstance(rec, dict) and not p:
        if rec["mock"] != e.get("mock") or e.get("mock") != e.get("fixture"):
            p.append("extra.mock/fixture must equal decision.mock (fixture rows are explicitly marked)")
        if rec["record_kind"] == "cell":
            want = (rec["metric"], rec["value"], rec["n_units"], f"{rec['unit']}")
            if (row["metric"], row["value"], row["reps"], row["reps_basis"].split(" ")[0]) != want:
                p.append("row metric/value/reps/basis must re-derive from decision")
            if row["metric_direction"] != CELL_METRICS[rec["metric"]]:
                p.append("metric_direction contradicts the metric")
            cat = "BASELINE" if rec["arm_role"] in BASELINE_ROLES else "CANDIDATE"
        else:
            if (row["metric"], row["value"], row["reps"]) != (
                    VERDICT_METRIC, rec["mean_score_diff_a1_minus_a0"], rec["n_pairs"]) \
                    or row["metric_direction"] != "higher_better":
                p.append("verdict row metric/value/reps must re-derive from decision")
            cat = "CANDIDATE"
        if row.get("category") != cat:
            p.append(f"category must be {cat}")
        p += ns.check_identity(row, {"run_id": row["run_id"], "decision": rec,
                                     "results": row["results_sha256"]}, "yga")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, records: Sequence[Mapping[str, Any]],
    protocol_id: str | None = None, emitted_at: str | None = None, fixture: bool = False,
) -> Path:
    """Emit ``yarn_gate_agg.beliefs.jsonl``. ``records``: ``{"record_path": <durable JSON file holding
    the decision record, or a list/obj containing it>, "decision": <decision record dict>}`` per row.

    Call once per aggregation pass in the yarn_gate runner after cells/verdicts are written::

        write_belief_measurements(run_dir, run_id=..., producer="yarn-gate-runner",
            records=[{"record_path": cell_json_path, "decision": cell_dict}, ..., verdict ...])

    ``mock`` decisions are refused unless ``fixture=True`` (tests only); real runs refuse mock.
    """
    if not records:
        raise CaptureError("at least one decision record is required")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for i, item in enumerate(records):
        rec, path = item.get("decision"), Path(str(item.get("record_path", "")))
        bad = record_problems(rec, where=f"records[{i}].decision")
        if bad:
            raise CaptureError("; ".join(bad))
        if rec["mock"] and not fixture:
            raise CaptureError(f"records[{i}] is mock-judged/mock and this is not a fixture call: "
                               "a mock cell has no warrant and is never written as a gradeable row")
        if fixture and not rec["mock"]:
            raise CaptureError(f"records[{i}]: fixture=True is for mock records only")
        if not path.is_file():
            raise CaptureError(f"records[{i}] durable record file missing: {path}")
        digest = ns.file_sha256(path)
        if rec["record_kind"] == "cell":
            metric, value, reps = rec["metric"], rec["value"], rec["n_units"]
            direction = CELL_METRICS[metric]
            basis = f"{rec['unit']} (unjudged {rec['n_unjudged']})" if rec["n_unjudged"] else rec["unit"]
            category = "BASELINE" if rec["arm_role"] in BASELINE_ROLES else "CANDIDATE"
        else:
            metric, value, reps = VERDICT_METRIC, rec["mean_score_diff_a1_minus_a0"], rec["n_pairs"]
            direction, basis, category = "higher_better", "pairs", "CANDIDATE"
        e = {"decision": rec, "mock": rec["mock"], "fixture": bool(fixture)}
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
            "date": when[:10], "metric": metric, "value": value, "unit": "fraction" if rec["record_kind"] == "cell" else "score_diff",
            "metric_direction": direction, "category": category,
            "claim": (f"YaRN gate {run_id}: {rec['comparison']} {rec['arm_role']} {rec['suite']}/{rec['task']} "
                      f"zone={rec['zone']} bin={rec['bin']} {metric}={value}"
                      + (f" verdict={rec['verdict']}" if rec["record_kind"] == "verdict" else "")),
            "protocol_id": protocol_id or NO_PROTOCOL, "reps": reps, "reps_basis": basis,
            "results_path": str(path), "results_sha256": digest, "extra": e,
        }
        row["measurement_id"] = "yga_" + ns.content_hash({
            "run_id": run_id, "decision": rec, "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate decision record")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path, *, allow_fixture: bool = False) -> tuple[dict, ...]:
    out = ns.native_rows(sidecar_path, validate_row)
    if not allow_fixture and any(n["row"]["extra"]["mock"] or n["row"]["extra"]["fixture"] for n in out):
        return ()
    return out


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    import dataclasses
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("YaRN gate native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("YaRN gate row is not a producer-authored capture: " + "; ".join(problems))
    d = row["extra"]["decision"]
    pre = "fixture:" if row["extra"]["fixture"] else ""
    locator = (f"{pre}yarn-gate:{row['run_id']}:{d['comparison']}:{d['arm_role']}:{d['suite']}/{d['task']}:"
               f"{d['zone']}:{d['bin']}:{row['results_path']}")
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                            sidecar_path=native.get("sidecar_path", ""))
    if tup.protocol_id == NO_PROTOCOL:
        tup = dataclasses.replace(tup, protocol_id="")
    return tup


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str, allow_fixture: bool = False) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path, allow_fixture=allow_fixture):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
