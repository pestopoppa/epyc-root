"""PB-HOL-1 slot-order head-of-line probe as value-bearing, scoped serving beliefs (loop-belief redesign 12.2, P1-L).

Native record: one run directory of ``scripts/benchmark/pb_hol_1/pb_hol_1.py`` (research repo; schema
``epyc.pbhol1.run.v1``): ``summary.json`` (arm TTFT lists, medians, the predeclared rule and its verdict, the
launched servers' argv readback) beside ``pb_hol_1.jsonl`` (the per-run rows the summary was made from).

PROJECTION ONLY. ``claim_tuple.grade()`` decides every grade; this module holds no ladder and no new rule. One
claim per arm comparison present in the run:

* ``A-off`` vs ``B-off`` (budget off, slot order): the predeclared-rule comparison. ``observation.outcome_native``
  carries the producer's verdict word VERBATIM (``CONFIRMED`` / ``NOT_REPRODUCED`` / ``INCOMPLETE``) and
  ``outcome_reason`` the rule text verbatim; the normalised ``outcome`` is the producer's own mapping of that
  verdict (CONFIRMED -> regressed: the rule's 2x threshold was met; NOT_REPRODUCED -> null), never a threshold of
  ours, and is absent when the verdict is INCOMPLETE.
* ``A-on`` vs ``B-on`` (prefill budget on, feeder decoding) and ``B-on-nodec`` vs ``B-on``: when those arms hold
  samples. The rule is a statement about the OFF arms, so these carry no verdict and no outcome, and the
  summary's own confound sentence (the budget phase also changes -b/-ub) is in the claim text.

value = the contended arm's (B, short slot above the long prefill) median short-TTFT in ms; ``anchor_value`` the
reference arm's median; ``effect_rel`` = B/A - 1; ``n_pairs`` = the smaller arm's rep count. The ratio the producer
states (``B_over_A_off``) is re-derived from the medians and refused if it disagrees. The summary's TTFT lists must
equal the ``short_ttft_ms`` of the jsonl rows (arm by arm, in order): a summary that does not re-derive from its own
rows is refused, never repaired.

Scope is read from the launched server's own argv readback (``_argv_scope``): model, quant, backend, np, -b/-ub,
--kv-unified, DFlash2 (``--spec-type draft-dflash``), kernel. ``knob_family = "slot_serving"`` (stack topology, not
AutoPilot's action space); ``varied`` names what the compared arms change. ``device`` is not declared.

Retrofit (DP-1 (a)): the producer has no belief hook yet, so every projection today says
``observation.retrofit``. The budget-on arms re-run 2026-10-22 into ``runs/on-20261022/``; each run directory is its
own claim set (the measurement id carries the run directory name and the summary's digest).

M4.2 (VB-M4-PBHOL-WIRE): the same harness re-run on the M4 SRPF candidate writes phase dirs ``<launcher>/out/<phase>/``
whose summaries carry phase-suffixed ``arms`` (``A-srpf512`` / ``B-off512`` / ...) and no verdict of their own; the
verdict is the launcher's ``VERDICT.json`` (``verdict.py`` over all phases), bound by ``RUN_RECORD.json`` to
``PREDECLARATION.md``'s sha256 (re-hashed on read, refused on mismatch; ``verdict.py`` / ``pb_hol_1.py`` likewise when
beside it). One claim per phase unit, so a whole-``out`` ingest never double counts:

* ``srpf512`` / ``srpf2048`` (C1) and ``off512`` (C2): B vs A short-TTFT medians over the VALID reps only (the
  predeclared validity rule re-applied to the jsonl and refused unless it is VERDICT.json's partition, medians and
  ratio); ``n`` = valid B reps; the condition word verbatim in ``outcome_native``; invalid runs stay listed in
  ``extra.invalid_runs`` with the verdict's reason and their recorded TTFT. ``srpf2048cap0`` is reported, never gating
  (no condition word). A phase whose ratio the producer could not form (C2 NOT_MEASURED: every B run invalid) is an
  attested row with ``value`` None, no reps and no observation (the carrier binds an observation to a number).
* ``comp-m4off``: C3, the candidate's champion-deterministic completions byte-identical on both passes;
  ``comp-champion``: the champion-determinism control C3 is read against (no condition word). Token-id and text sha256
  are re-hashed per completion and the verdict's per-prompt detail re-derived from both comp phases.

Normalised ``outcome`` only when the run's own overall verdict is PASS/FAIL (``_M4_OUTCOME``); INCOMPLETE carries none.
``protocol_id`` stays empty (a harness-local predeclaration is not a ratified protocol: the OCC-1 / U4-NOISE-1
precedent), so every M4.2 claim grades Judged/Located; the predeclaration sha and the claim class ride in ``extra``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import flag, scope_from_argv, to_int  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

SCHEMA = "epyc.pbhol1.run.v1"
ADAPTER_ID = "vidya.adapters.pb_hol/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "pb-hol-measurement"
KNOB_FAMILY = "slot_serving"
SUMMARY = "summary.json"
ROWS = "pb_hol_1.jsonl"
METRIC = "pbhol_short_ttft_median_ms"
_MAX_BYTES = 16 << 20
_VERDICT_OUTCOME = {"CONFIRMED": "regressed", "NOT_REPRODUCED": "null"}
#: comparison id -> (reference arm, contended arm, server phase, varied)
COMPARISONS = {
    "A-off_vs_B-off": ("A-off", "B-off", "off", ["short_slot_index_order"]),
    "A-on_vs_B-on": ("A-on", "B-on", "on", ["short_slot_index_order"]),
    "B-on-nodec_vs_B-on": ("B-on-nodec", "B-on", "on", ["decode_feeder"]),
}


def _read(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ProjectionError(f"{path.name} is not a bounded regular file")
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def _finite_list(value: Any) -> list[float] | None:
    if (isinstance(value, list) and all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in value)):
        return [float(v) for v in value]
    return None


def _jsonl_arms(rows_raw: bytes) -> dict[str, list[float]]:
    arms: dict[str, list[float]] = {}
    for line in rows_raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{ROWS} has a torn line: {exc}") from exc
        if (isinstance(row, dict) and row.get("kind") == "run" and not row.get("skipped")
                and type(row.get("short_ttft_ms")) in (int, float) and isinstance(row.get("arm"), str)):
            arms.setdefault(row["arm"], []).append(float(row["short_ttft_ms"]))
    return arms


def _arm_lists(summary: dict) -> dict[str, tuple[list[float], Any]]:
    """arm label -> (TTFT list, the summary's stated median)."""
    out = {"A-off": (_finite_list(summary.get("A_off_ttft_ms")), summary.get("A_off_median")),
           "B-off": (_finite_list(summary.get("B_off_ttft_ms")), summary.get("B_off_median"))}
    on = summary.get("budget_on_arms") if isinstance(summary.get("budget_on_arms"), dict) else {}
    for label in ("A-on", "B-on", "B-on-nodec"):
        arm = on.get(label) if isinstance(on.get(label), dict) else {}
        out[label] = (_finite_list(arm.get("ttft_ms")), arm.get("median_ms"))
    return out


def native_rows(run_dir: str | Path) -> list[dict]:
    """One native row per arm comparison with samples on both sides; ``[]`` for any other directory."""
    path = Path(run_dir)
    if path.is_file():
        path = path.parent
    from adapters import _pb_hol_m42b
    paired = _pb_hol_m42b.native_rows(path)
    if paired is not None:
        return paired
    summary_path = path / SUMMARY
    if not summary_path.is_file():
        return []
    raw, digest = _read(summary_path)
    try:
        summary = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"{SUMMARY} is not JSON: {exc}") from exc
    if not isinstance(summary, dict) or summary.get("schema") != SCHEMA:
        return []
    if "A_off_ttft_ms" not in summary and isinstance(summary.get("arms"), dict):
        return _m4_native_rows(path, summary, digest)  # M4.2 phase dir (phase-suffixed arms)
    rows_raw, rows_digest = _read(path / ROWS)
    recorded = _jsonl_arms(rows_raw)
    arms = _arm_lists(summary)
    out = []
    for cid, (ref, contended, _phase, _varied) in COMPARISONS.items():
        (a, a_med), (b, b_med) = arms[ref], arms[contended]
        if not a or not b:
            continue
        for label, values, stated in ((ref, a, a_med), (contended, b, b_med)):
            if recorded.get(label) != values:
                raise ProjectionError(f"{SUMMARY} {label} TTFT list does not re-derive from {ROWS}")
            if stated != statistics.median(values):
                raise ProjectionError(f"{SUMMARY} {label} median does not re-derive from its samples")
        out.append({"comparison": cid, "summary": summary, "summary_sha256": digest,
                    "rows_sha256": rows_digest, "run_dir": str(path)})
    return out


def _server(summary: dict, phase: str) -> dict | None:
    for server in summary.get("servers") or []:
        if isinstance(server, dict) and f"pbhol-{phase}-" in str(server.get("label") or ""):
            return server
    return None


def _scope(summary: dict, phase: str, varied: list[str]) -> dict:
    server = _server(summary, phase)
    readback = (server or {}).get("readback") if isinstance((server or {}).get("readback"), dict) else {}
    argv = readback.get("proc_cmdline")
    ok = readback.get("proc_cmdline_matches_argv") is True and readback.get("exe_matches_binary") is True
    spec = flag(argv, "--spec-type") if isinstance(argv, list) else None
    return scope_from_argv(argv, binary=readback.get("exe"), binary_sha256=summary.get("binary_sha256"),
                           family=KNOB_FAMILY, varied=varied,
                           dflash2=(spec == "draft-dflash") if spec else None, readback_ok=ok)


def _fmt(x: float) -> str:
    return f"{x:g}"


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    from adapters import _pb_hol_m42b
    if native.get("kind") == _pb_hol_m42b.KIND:
        return _pb_hol_m42b.project(native)
    if native.get("kind") == M4_KIND:
        return _m4_project(native)
    cid = native.get("comparison")
    if cid not in COMPARISONS or not isinstance(native.get("summary"), dict):
        raise ProjectionError("PB-HOL native row must retain its summary and name a known comparison")
    summary = native["summary"]
    if summary.get("schema") != SCHEMA:
        raise ProjectionError(f"PB-HOL summary schema is not {SCHEMA}")
    ref, contended, phase, varied = COMPARISONS[cid]
    (a, a_med), (b, b_med) = _arm_lists(summary)[ref], _arm_lists(summary)[contended]
    if not a or not b:
        raise ProjectionError(f"PB-HOL comparison {cid} has no samples on one side")
    a_med, b_med = statistics.median(a), statistics.median(b)
    if a_med <= 0:
        raise ProjectionError("PB-HOL reference median is not positive")
    ratio = round(b_med / a_med, 2)
    if cid == "A-off_vs_B-off" and summary.get("B_over_A_off") not in (None, ratio):
        raise ProjectionError("PB-HOL B_over_A_off does not re-derive from the arm medians")
    obs: dict = {"anchor_value": a_med, "effect_rel": b_med / a_med - 1.0, "n_pairs": min(len(a), len(b)),
                 "retrofit": True}
    verdict = summary.get("verdict")
    status = summary.get("status")
    text = (f"PB-HOL-1 {cid.replace('_vs_', ' vs ')}: short-prompt (128 tok) TTFT median {_fmt(b_med)} ms vs "
            f"{_fmt(a_med)} ms = {ratio}x (n={len(b)} vs {len(a)} reps, one 64k-token prefill in flight, np 3)")
    if cid == "A-off_vs_B-off":
        rule = summary.get("rule")
        if isinstance(verdict, str) and verdict.strip():
            obs["outcome_native"] = verdict[:120]
            if verdict in _VERDICT_OUTCOME:
                obs["outcome"] = _VERDICT_OUTCOME[verdict]
        if isinstance(rule, str) and rule.strip():
            obs["outcome_reason"] = rule[:300]
        text += f"; predeclared rule verdict {verdict}"
        c = summary.get("C_median")
        if type(c) in (int, float):
            text += f"; solo short {_fmt(c)} ms"
    else:
        confound = summary.get("confound")
        text += "; no predeclared rule applies to this comparison"
        if isinstance(confound, str) and confound.strip():
            text += f"; confound: {confound}"
    if isinstance(status, str) and status:
        text += f"; run status {status!r}"
    run_name = Path(native.get("run_dir") or ".").name
    digest = native["summary_sha256"]
    return ClaimTuple(
        measurement_id=f"pbhol:v1:{run_name}:{digest[:16]}:{cid}",
        metric=METRIC, value=b_med, unit="ms", date=str(summary.get("finished") or ""),
        category="CANDIDATE", claim=text, metric_direction="lower_better", protocol_id="",
        reps=len(b), reps_basis="repeated A/B collisions on one server launch",
        attestation_locator=f"pbhol:{run_name}:{SUMMARY}#{cid}", attestation_sha256=digest,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra={"schema": SCHEMA, "comparison": cid, "run_dir": native.get("run_dir", ""),
               "rows_sha256": native.get("rows_sha256"), "ratio": ratio, "status": status,
               "verdict": verdict if cid == "A-off_vs_B-off" else None,
               "solo_median_ms": summary.get("C_median"), "binary_sha256": summary.get("binary_sha256"),
               "budget_args": summary.get("budget_args") if phase == "on" else None},
        applicability=_scope(summary, phase, varied), observation=obs)


# ---------------------------------------------------------------------------------------------------------------------
# M4.2: PB-HOL-1 re-run on the M4 SRPF candidate (launcher dir with PREDECLARATION.md / RUN_RECORD.json / VERDICT.json;
# phase dirs at <launcher>/out/<phase>/). See the module docstring's M4.2 section.

M4_KIND = "pbhol-m4.2"
M4_VERDICT, M4_RUN_RECORD, M4_PREDECL = "VERDICT.json", "RUN_RECORD.json", "PREDECLARATION.md"
#: launcher file -> the RUN_RECORD key that records its sha256 (re-hashed when the file is beside it)
M4_REHASH = {"verdict.py": "verdict_py_sha256", "pb_hol_1.py": "pb_hol_1_py_sha256"}
# PREDECLARATION.md "Conditions": a collision run is VALID only if the short answered (HTTP 200, a first token), the long
# was not finished before the short was answered, and the logged long progress at send was >= 0.40; a ratio needs >= 2
# valid reps of A and of B; a completion counts only with HTTP 200 and exactly 96 tokens.
M4_MIN_COLLIDE_FRAC = 0.40
M4_MIN_VALID = 2
M4_COMP_TOKENS = 96
M4_COMP_CHAMPION, M4_COMP_CANDIDATE = "comp-champion", "comp-m4off"
#: collision phase -> (claim id, VERDICT.json condition key | None = reported, never gating, condition family)
M4_COLLISION = {
    "srpf512": ("C1_srpf512", "C1_srpf512", "C1"),
    "srpf2048": ("C1_srpf2048", "C1_srpf2048", "C1"),
    "off512": ("C2_off_identity_ratio", "C2_off_identity_ratio", "C2"),
    "srpf2048cap0": ("srpf2048cap0_informational", None, None),
}
M4_C1_OVERALL = "C1_srpf_B_over_A_lt_2"
M4_C3_KEY = "C3_off_completions_byte_identical"
M4_C3_CLAIM = M4_C3_KEY
M4_CONTROL_CLAIM = "C3_champion_determinism_control"
M4_METRIC_IDENTICAL = "pbhol_m4_off_identical_completions"
M4_METRIC_DETERMINISTIC = "pbhol_m4_champion_deterministic_completions"
# The normalised outcome is emitted ONLY when the run's own overall verdict is PASS or FAIL (PREDECLARATION.md: anything
# else is INCOMPLETE = "no claim"), and only through the predeclared reading of each condition: C1 is PB-HOL-1's 2x
# head-of-line rule (FAIL = B/A >= 2.0 = the regression PB-HOL-1 mapped to `regressed`; PASS = not reproduced = `null`);
# C2 PASS = the off path kept PB-HOL-1's ratio (`null`), a C2 FAIL is two-sided (below = changed behaviour, above =
# regression) so it keeps only its native word; C3 PASS = byte-identical (`null`), FAIL = a byte mismatch (`divergence`).
_M4_OUTCOME = {"C1": {"PASS": "null", "FAIL": "regressed"}, "C2": {"PASS": "null"},
               "C3": {"PASS": "null", "FAIL": "divergence"}}
_HEX64 = re.compile(r"[0-9a-f]{64}")
_GIT = re.compile(r"[0-9a-f]{7,40}")
_IMAGE_SHA = re.compile(r"-\d{8}-([0-9a-f]{7,40})(?:-|$)")
_CLAIM_CLASS = re.compile(r"^## Claim class\s*\n+([A-Z][A-Z_-]+)\b", re.M)


def _m4_json(path: Path) -> tuple[dict, str]:
    raw, digest = _read(path)
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"M4.2 {path.name} is not JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ProjectionError(f"M4.2 {path.name} is not a JSON object")
    return doc, digest


def _m4_context(root: Path) -> dict | None:
    """The launcher's verdict, run record and predeclaration, every recorded hash re-derived; None when not an M4.2 dir."""
    if not all((root / name).is_file() for name in (M4_VERDICT, M4_RUN_RECORD, M4_PREDECL)):
        return None
    verdict, verdict_sha = _m4_json(root / M4_VERDICT)
    record, record_sha = _m4_json(root / M4_RUN_RECORD)
    predecl_raw, predecl_sha = _read(root / M4_PREDECL)
    stated = record.get("predeclaration_sha256")
    if not (isinstance(stated, str) and _HEX64.fullmatch(stated)):
        raise ProjectionError(f"M4.2 {M4_RUN_RECORD} records no predeclaration_sha256: the rule is unbound")
    if stated != predecl_sha:
        raise ProjectionError(f"M4.2 {M4_PREDECL} sha256 {predecl_sha[:12]} != the {M4_RUN_RECORD} binding {stated[:12]}")
    rehashed, unread = [M4_PREDECL], []
    for name, key in M4_REHASH.items():
        if record.get(key) is None:
            continue
        if not (root / name).is_file():
            unread.append(name)
            continue
        if _read(root / name)[1] != record[key]:
            raise ProjectionError(f"M4.2 {name} sha256 does not match its {M4_RUN_RECORD} binding ({key})")
        rehashed.append(name)
    overall = verdict.get("verdict")
    if not isinstance(overall, str) or overall != record.get("verdict"):
        raise ProjectionError(f"M4.2 {M4_VERDICT} verdict {overall!r} != {M4_RUN_RECORD} verdict {record.get('verdict')!r}")
    if not isinstance(verdict.get("conditions"), dict) or not isinstance(verdict.get("phases"), dict):
        raise ProjectionError(f"M4.2 {M4_VERDICT} carries no conditions/phases")
    window = record.get("window_id")
    if not isinstance(window, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", window):
        raise ProjectionError(f"M4.2 {M4_RUN_RECORD} carries no usable window_id")
    cls = _CLAIM_CLASS.search(predecl_raw.decode("utf-8", "replace"))
    return {"verdict": verdict, "verdict_sha256": verdict_sha, "record": record, "record_sha256": record_sha,
            "predeclaration_sha256": predecl_sha, "claim_class": cls.group(1) if cls else None,
            "rehashed": rehashed, "not_rehashed": unread, "window_id": window, "root": str(root)}


def _m4_rows(path: Path) -> tuple[list[dict], str]:
    raw, digest = _read(path / ROWS)
    rows = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"M4.2 {ROWS} has a torn line: {exc}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows, digest


def _m4_check_summary_arms(summary: dict, rows: list[dict]) -> None:
    """The summary's per-arm TTFT lists and medians must re-derive from the jsonl rows (the harness's own grouping)."""
    by: dict[str, list[float]] = {}
    for r in rows:
        if r.get("kind") == "run" and type(r.get("short_ttft_ms")) in (int, float) and not r.get("skipped"):
            arm = str(r.get("arm"))
            by.setdefault(arm if arm != "C" else f"C-{r.get('phase')}", []).append(float(r["short_ttft_ms"]))
    arms = summary["arms"]
    if set(arms) != set(by):
        raise ProjectionError(f"M4.2 {SUMMARY} arms {sorted(arms)} do not re-derive from {ROWS} ({sorted(by)})")
    for label, values in by.items():
        arm = arms[label] if isinstance(arms[label], dict) else {}
        if _finite_list(arm.get("ttft_ms")) != values:
            raise ProjectionError(f"M4.2 {SUMMARY} {label} TTFT list does not re-derive from {ROWS}")
        if arm.get("median_ms") != statistics.median(values):
            raise ProjectionError(f"M4.2 {SUMMARY} {label} median does not re-derive from its samples")


def _m4_valid(r: dict) -> bool:
    if r.get("skipped") or r.get("short_http") != 200 or r.get("short_error") or r.get("short_ttft_ms") is None:
        return False
    if r.get("long_finished_before_abort"):
        return False
    p = r.get("long_progress_at_send")
    return bool(p) and isinstance(p, list) and len(p) > 1 and type(p[1]) in (int, float) and p[1] >= M4_MIN_COLLIDE_FRAC


def _m4_collision_stats(rows: list[dict], stated: dict) -> dict:
    """Partition the A/B collision runs by the predeclared validity rule; refuse unless it is the verdict's partition."""
    runs = [r for r in rows if r.get("kind") == "run" and str(r.get("arm") or "").split("-")[0] in ("A", "B")]
    a: list[float] = []
    b: list[float] = []
    invalid = []
    for r in runs:
        if _m4_valid(r):
            (a if str(r["arm"]).startswith("A") else b).append(r["short_ttft_ms"])
        else:
            invalid.append(r)
    med_a = statistics.median(a) if a else None
    med_b = statistics.median(b) if b else None
    ratio = (round(med_b / med_a, 3) if med_a and med_b and len(a) >= M4_MIN_VALID and len(b) >= M4_MIN_VALID
             else None)
    stated_invalid = stated.get("invalid")
    if not (isinstance(stated_invalid, list) and all(isinstance(i, dict) for i in stated_invalid)):
        stated_invalid = None
    if (stated.get("attempted") != len(runs) or stated.get("valid") != len(a) + len(b) or stated.get("A") != a
            or stated.get("B") != b or stated_invalid is None
            or [(i.get("arm"), i.get("rep")) for i in stated_invalid]
            != [(r.get("arm"), r.get("rep")) for r in invalid]):
        raise ProjectionError(f"M4.2 {M4_VERDICT} valid/invalid partition does not re-derive from {ROWS}")
    if stated.get("medA") != med_a or stated.get("medB") != med_b or stated.get("ratio") != ratio:
        raise ProjectionError(f"M4.2 {M4_VERDICT} medians/ratio do not re-derive from the valid reps")
    # Invalid runs stay rows: the verdict's reason verbatim beside the run's own recorded TTFT (never a sample).
    inv = [{"arm": r.get("arm"), "rep": r.get("rep"), "why": str(i.get("why") or "")[:200],
            "short_ttft_ms": r.get("short_ttft_ms")} for r, i in zip(invalid, stated_invalid)]
    return {"A": a, "B": b, "medA": med_a, "medB": med_b, "ratio": ratio, "attempted": len(runs), "invalid": inv}


def _m4_completions(rows: list[dict]) -> dict:
    """prompt -> pass -> (tokens sha, text sha) | None, each digest re-hashed from the retained token ids and text."""
    out: dict = {}
    for r in rows:
        if r.get("kind") != "completion":
            continue
        toks, txt = r.get("tokens"), r.get("text")
        if not isinstance(toks, list) or r.get("n_tokens") != len(toks):
            raise ProjectionError(f"M4.2 {ROWS} completion {r.get('prompt')!r} does not retain its token ids")
        if hashlib.sha256(json.dumps(toks).encode()).hexdigest() != r.get("tokens_sha256"):
            raise ProjectionError(f"M4.2 {ROWS} completion {r.get('prompt')!r} tokens_sha256 does not re-hash")
        if (hashlib.sha256(txt.encode()).hexdigest() if isinstance(txt, str) else None) != r.get("text_sha256"):
            raise ProjectionError(f"M4.2 {ROWS} completion {r.get('prompt')!r} text_sha256 does not re-hash")
        ok = r.get("http") == 200 and not r.get("error") and r.get("n_tokens") == M4_COMP_TOKENS and txt is not None
        out.setdefault(str(r.get("prompt")), {})[r.get("pass")] = (r["tokens_sha256"], r["text_sha256"]) if ok else None
    return out


def _m4_comp_detail(out_dir: Path, stated: dict) -> dict:
    """Champion self-agreement and candidate identity per completion; refused unless it is the verdict's detail."""
    tables = {}
    for phase in (M4_COMP_CHAMPION, M4_COMP_CANDIDATE):
        tables[phase] = _m4_completions(_m4_rows(out_dir / phase)[0]) if (out_dir / phase / ROWS).is_file() else {}
    ch, m4 = tables[M4_COMP_CHAMPION], tables[M4_COMP_CANDIDATE]
    if not ch or not m4:
        return {"measured": False, "champion_completions": len(ch)}
    prompts, det, mismatches = {}, [], []
    for n in sorted(set(ch) | set(m4)):
        c1, c2 = ch.get(n, {}).get(1), ch.get(n, {}).get(2)
        deterministic = c1 is not None and c1 == c2
        got = [m4.get(n, {}).get(p) for p in (1, 2)]
        same = deterministic and all(g is not None and g == c1 for g in got)
        prompts[n] = {"champion_deterministic": deterministic, "m4_off_identical": same if deterministic else None,
                      "m4_passes_valid": [g is not None for g in got]}
        if deterministic:
            det.append(n)
            if not same:
                mismatches.append(n)
    if (stated.get("prompts") != prompts or stated.get("deterministic") != det
            or stated.get("mismatches") != mismatches):
        raise ProjectionError(f"M4.2 {M4_VERDICT} completions detail does not re-derive from the comp-* {ROWS}")
    return {"measured": True, "prompts": prompts, "deterministic": det, "mismatches": mismatches,
            "champion_completions": len(ch)}


def _m4_server(summary: dict) -> dict:
    servers = [s for s in summary.get("servers") or [] if isinstance(s, dict)]
    if len(servers) != 1:
        raise ProjectionError(f"M4.2 phase {SUMMARY} has {len(servers)} servers; the predeclaration loads one per phase")
    return servers[0]


def _m4_check_binary(phase: str, server: dict, record: dict) -> None:
    if phase == M4_COMP_CHAMPION:
        image = record.get("champion_image")
        if not (isinstance(image, str) and image and f"/{image}/" in str(server.get("binary") or "")):
            raise ProjectionError(f"M4.2 {phase} server binary is not the recorded champion image {image!r}")
    elif server.get("binary_sha256") != record.get("m4_llama_server_sha256"):
        raise ProjectionError(f"M4.2 {phase} server binary sha256 is not the {M4_RUN_RECORD} m4_llama_server_sha256")


def _m4_native_rows(path: Path, summary: dict, digest: str) -> list[dict]:
    """One native per M4.2 phase dir; the cross-phase C3 claim rides the candidate comp phase only (no double count)."""
    phase = path.name
    if phase not in M4_COLLISION and phase not in (M4_COMP_CHAMPION, M4_COMP_CANDIDATE):
        return []  # an earlier `<phase>.attempt-*` dir or a foreign layout: the verdict reads the latest attempt only
    ctx = _m4_context(path.parent.parent)
    if ctx is None:
        return []
    rows, rows_digest = _m4_rows(path)
    _m4_check_summary_arms(summary, rows)
    server = _m4_server(summary)
    _m4_check_binary(phase, server, ctx["record"])
    native = {"kind": M4_KIND, "phase": phase, "summary": summary, "summary_sha256": digest,
              "rows_sha256": rows_digest, "run_dir": str(path), "ctx": ctx, "server": server}
    if phase in M4_COLLISION:
        stated = ctx["verdict"]["phases"].get(phase)
        if not isinstance(stated, dict):
            raise ProjectionError(f"M4.2 {M4_VERDICT} has no phase {phase!r}")
        native.update(claim_id=M4_COLLISION[phase][0], stats=_m4_collision_stats(rows, stated),
                      stated_phase=stated)
    else:
        stated = ctx["verdict"].get("completions")
        if not isinstance(stated, dict):
            raise ProjectionError(f"M4.2 {M4_VERDICT} carries no completions detail")
        native.update(claim_id=M4_CONTROL_CLAIM if phase == M4_COMP_CHAMPION else M4_C3_CLAIM,
                      comp=_m4_comp_detail(path.parent, stated))
    return [native]


def _m4_scope(native: dict, varied: list[str]) -> dict:
    server, record = native["server"], native["ctx"]["record"]
    readback = server.get("readback") if isinstance(server.get("readback"), dict) else {}
    argv = readback.get("proc_cmdline")
    ok = readback.get("proc_cmdline_matches_argv") is True and readback.get("exe_matches_binary") is True
    spec = flag(argv, "--spec-type") if isinstance(argv, list) else None
    scope = scope_from_argv(argv, binary=readback.get("exe"), binary_sha256=server.get("binary_sha256"),
                            family=KNOB_FAMILY, varied=varied,
                            dflash2=(spec == "draft-dflash") if spec else None, readback_ok=ok)
    if not scope:
        return scope
    knobs = dict(scope.get("knobs") or {})
    order, cap = flag(argv, "--prefill-order"), flag(argv, "--prefill-contend-cap")
    if order:
        knobs["prefill_order"] = order
    if cap is not None:
        knobs["prefill_contend_cap"] = to_int(cap) if to_int(cap) is not None else cap
    if knobs:
        scope["knobs"] = knobs
    if "build_sha" not in scope:
        if native["phase"] == M4_COMP_CHAMPION:
            image = _IMAGE_SHA.search(str(record.get("champion_image") or ""))
            sha = image.group(1) if image else None
        else:  # the M4 binary is bound to the recorded head by its sha256 (_m4_check_binary)
            head = record.get("head")
            sha = head[:9] if isinstance(head, str) and _GIT.fullmatch(head) else None
        if sha:
            scope["build_sha"] = sha
    return scope


def _m4_outcome(obs: dict, ctx: dict, key: str | None, family: str | None) -> str | None:
    """The producer's condition word verbatim; a normalised outcome only from a PASS/FAIL run (see _M4_OUTCOME)."""
    if key is None:
        return None
    conds, overall = ctx["verdict"]["conditions"], ctx["verdict"]["verdict"]
    word = conds.get(key)
    if not isinstance(word, str) or not word.strip():
        raise ProjectionError(f"M4.2 {M4_VERDICT} has no condition {key!r}")
    obs["outcome_native"] = word[:120]
    gating = str(ctx["verdict"].get("gating") or "")
    obs["outcome_reason"] = (f"{key} (PREDECLARATION.md sha256 {ctx['predeclaration_sha256'][:12]}); run verdict "
                             f"{overall}; {gating}")[:300]
    if overall in ("PASS", "FAIL") and family and word in _M4_OUTCOME[family]:
        obs["outcome"] = _M4_OUTCOME[family][word]
    return word


def _m4_project(native: dict) -> ClaimTuple:
    ctx, summary, phase = native.get("ctx"), native.get("summary"), native.get("phase")
    if (not isinstance(ctx, dict) or not isinstance(summary, dict) or summary.get("schema") != SCHEMA
            or not isinstance(native.get("server"), dict)):
        raise ProjectionError("M4.2 native row must retain its summary, server and launcher context")
    overall, window = ctx["verdict"]["verdict"], ctx["window_id"]
    cls = ctx.get("claim_class")
    tail = f"; run verdict {overall}" + (f" ({cls} per PREDECLARATION.md)" if cls else "")
    obs: dict = {"retrofit": True}
    extra: dict = {"schema": SCHEMA, "kind": M4_KIND, "phase": phase, "run_dir": native.get("run_dir", ""),
                   "rows_sha256": native.get("rows_sha256"), "summary_sha256": native.get("summary_sha256"),
                   "run_verdict": overall, "claim_class": cls,
                   "predeclaration_sha256": ctx["predeclaration_sha256"], "verdict_sha256": ctx["verdict_sha256"],
                   "run_record_sha256": ctx["record_sha256"], "rehashed": ctx["rehashed"],
                   "not_rehashed": ctx["not_rehashed"], "window_id": window, "head": ctx["record"].get("head"),
                   "branch": ctx["record"].get("branch"), "champion_image": ctx["record"].get("champion_image"),
                   "binary_sha256": native["server"].get("binary_sha256")}
    vram = native["server"].get("vram") if isinstance(native["server"].get("vram"), dict) else {}
    extra["own_vram_peak_gib"] = vram.get("own_vram_peak_gib")
    cid = native.get("claim_id")
    if phase in M4_COLLISION:
        want, key, family = M4_COLLISION[phase]
        st = native.get("stats")
        if cid != want or not isinstance(st, dict):
            raise ProjectionError(f"M4.2 native for phase {phase} names claim {cid!r}")
        a, b = st["A"], st["B"]
        med_a = statistics.median(a) if a else None
        med_b = statistics.median(b) if b else None
        if med_a != st["medA"] or med_b != st["medB"]:
            raise ProjectionError("M4.2 native medians do not re-derive from its valid reps")
        measured = st["ratio"] is not None
        value = med_b if measured else None
        if med_a is not None:
            obs["anchor_value"] = med_a
        if measured:
            obs["effect_rel"] = med_b / med_a - 1.0
            obs["n_pairs"] = min(len(a), len(b))
        word = _m4_outcome(obs, ctx, key, family)
        argv = (native["server"].get("readback") or {}).get("proc_cmdline") or []
        batch, order = flag(argv, "-b", "--batch-size"), flag(argv, "--prefill-order")
        cap = flag(argv, "--prefill-contend-cap")
        shape = ", ".join(x for x in (f"-b {batch}" if batch else "",
                                      f"--prefill-order {order}" if order else "no prefill flags",
                                      f"--prefill-contend-cap {cap}" if cap is not None else "") if x)
        n_inv = len(st["invalid"])
        head = (f"M4.2 PB-HOL-1 on the M4 SRPF candidate, phase {phase} ({shape}): short-prompt (128 tok) TTFT, "
                f"B (short slot above the 64k-token prefill) vs A")
        if measured:
            text = (f"{head}: median {_fmt(med_b)} ms vs {_fmt(med_a)} ms = {st['ratio']}x (n={len(b)} vs {len(a)} "
                    f"valid reps of {st['attempted']} attempted, {n_inv} invalid, np 3)")
        else:
            text = (f"{head}: B/A NOT MEASURED - {len(b)} valid B and {len(a)} valid A reps of {st['attempted']} "
                    f"attempted ({n_inv} invalid, reasons in the record); a ratio needs >= {M4_MIN_VALID} valid reps "
                    f"of each" + (f"; A median {_fmt(med_a)} ms" if med_a is not None else ""))
        text += (f"; predeclared condition {key} {word}" if key else "; reported, never gating (PREDECLARATION.md)")
        if family == "C1":
            text += f" (C1 overall {ctx['verdict']['conditions'].get(M4_C1_OVERALL)})"
        extra.update(claim=cid, condition=key, condition_word=word, ratio=st["ratio"], attempted=st["attempted"],
                     valid=len(a) + len(b), valid_A=a, valid_B=b, invalid_runs=st["invalid"],
                     solo_short_ms=(native.get("stated_phase") or {}).get("C"),
                     solo_64k_s=(native.get("stated_phase") or {}).get("solo_64k_s"),
                     graphs=(native.get("stated_phase") or {}).get("graphs"))
        metric, unit, reps = METRIC, "ms", (len(b) if measured else None)
        basis = ("valid collision runs of the B arm (PREDECLARATION.md validity rule); invalid runs listed in "
                 "extra.invalid_runs with their reasons")
        direction, varied = "lower_better", ["short_slot_index_order"]
    elif phase in (M4_COMP_CHAMPION, M4_COMP_CANDIDATE):
        comp = native.get("comp")
        want = M4_CONTROL_CLAIM if phase == M4_COMP_CHAMPION else M4_C3_CLAIM
        if cid != want or not isinstance(comp, dict):
            raise ProjectionError(f"M4.2 native for phase {phase} names claim {cid!r}")
        measured = comp.get("measured") is True
        det = comp.get("deterministic") or []
        excluded = sorted(n for n, p in (comp.get("prompts") or {}).items() if not p["champion_deterministic"])
        extra.update(claim=cid, completions=comp.get("prompts"), deterministic=det,
                     excluded_champion_nondeterministic=excluded, mismatches=comp.get("mismatches"))
        unit, direction = "completions", "higher_better"
        if phase == M4_COMP_CHAMPION:
            metric, varied = M4_METRIC_DETERMINISTIC, ["completion_pass"]
            value = len(det) if measured else None
            n = comp.get("champion_completions") or 0
            reps = n if measured and n > 0 else None
            basis = "champion completions compared pass 1 vs pass 2 (token-id and text sha256, re-hashed)"
            text = ("M4.2 champion-determinism control (champion image, no flags, -b 512): "
                    + (f"{len(det)} of {n} completions byte-identical across its two passes (n_predict 96, temp 0, "
                       f"seed 42); excluded from C3: {', '.join(excluded) or 'none'}" if measured
                       else "NOT MEASURED - comp-champion or comp-m4off has no completion rows")
                    + "; the control C3 is read against, no condition of its own")
        else:
            metric, varied = M4_METRIC_IDENTICAL, ["kernel_build"]
            same = [n for n in det if comp["prompts"][n]["m4_off_identical"]]
            value = len(same) if measured else None
            reps = len(det) if measured and det else None
            if measured and det:
                obs["anchor_value"] = len(det)
            word = _m4_outcome(obs, ctx, M4_C3_KEY, "C3")
            basis = "champion-deterministic completions (both candidate passes compared to the champion's)"
            text = ("M4.2 off-identity bytes, M4 candidate with no flags (-b 512) vs the champion image: "
                    + (f"{len(same)} of {len(det)} champion-deterministic completions byte-identical on both candidate "
                       f"passes (token ids + text sha256); mismatches: {', '.join(comp['mismatches']) or 'none'}; "
                       f"excluded (champion disagrees with itself): {', '.join(excluded) or 'none'}" if measured
                       else "NOT MEASURED - comp-champion or comp-m4off has no completion rows")
                    + f"; predeclared condition {M4_C3_KEY} {word}")
            extra.update(condition=M4_C3_KEY, condition_word=word)
    else:
        raise ProjectionError(f"M4.2 native names an unknown phase {phase!r}")
    text += tail
    if value is None:
        # NOT MEASURED stays an attested row (claim text + extra carry the condition word, the A median and every
        # invalid run with its reason), but the carrier binds an observation to a number, so it carries none: no
        # value, no outcome, never a fabricated one.
        extra["observation_withheld"] = {k: v for k, v in obs.items() if k != "retrofit"}
        extra["retrofit"] = True
        obs = {}
    return ClaimTuple(
        measurement_id=f"pbhol-m4:v1:{window}:{phase}:{ctx['verdict_sha256'][:16]}:{cid}",
        metric=metric, value=value, unit=unit, date=str(summary.get("finished") or ""),
        category="CANDIDATE", claim=text, metric_direction=direction, protocol_id="",
        reps=reps, reps_basis=basis,
        attestation_locator=f"pbhol-m4:{window}:{M4_VERDICT}#{cid}", attestation_sha256=ctx["verdict_sha256"],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra=extra, applicability=_m4_scope(native, varied), observation=obs)


__all__ = ["ADAPTER_ID", "AUTHORITY", "COMPARISONS", "KNOB_FAMILY", "M4_KIND", "SOURCE_KIND", "native_rows",
           "project"]


def units(path: Path) -> list[Path]:
    """A paired launcher/window is one unit; preserve historical flat summary units."""
    from adapters import _pb_hol_m42b
    paired = _pb_hol_m42b.units(path)
    if paired is not None:
        return paired
    if not path.is_dir():
        return []
    if (path / SUMMARY).is_file():
        return [path]
    return sorted(p for p in path.iterdir() if p.is_dir() and (p / SUMMARY).is_file())
