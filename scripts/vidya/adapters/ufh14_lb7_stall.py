"""UFH14-LB7 cache-idle-slots stall attribution as value-bearing, scoped beliefs (VB-LB7-STALL-WIRE).

Native record: one launcher directory of the UFH14-LB7 run (``agentic-serving-harness-fixes.md`` UFH14-LB7), e.g.
``/mnt/raid0/llm/tmp/f8-launchers-20261023/locals-ufh14-lb7-stall/``:

* ``PREDECLARATION.md``     the decision rule, written before any compute; its sha256 IS the protocol id;
* ``VERDICT.json``          the producer's ``lb7_parse.py aggregate`` output (schema ``epyc.ufh14.lb7.verdict.v1``);
* ``RUN_RECORD.json``       launcher record (build digest, champion, verdict, ``sessions_ok``);
* ``out/<label>.attrib.json``  one per ABBAAB session (s1-ON, s2-OFF, s3-OFF, s4-ON, s5-ON, s6-OFF), schema
                            ``epyc.ufh14.lb7.attrib.v1``: per-turn window partition and the turn-2+ summary;
* ``out/<label>/report.json``  the replay driver's preflight (pid, argv, KFD residency, ``props_build``).

STRICT READER. The producer's own statistics are RE-IMPLEMENTED EXACTLY (``lb7_parse.py`` ``aggregate`` and the
turn-2+ summary of ``attribute_session``; the producer script's sha256 is recorded in ``extra`` when it is beside the
run) and re-derived from the attrib records: each session's turn-2+ means/medians, groups, slot sequence and
alignment counts from its ``per_turn`` rows, then the pair deltas, gates, medians, copy-throughput tag and VERDICT word
from the session summaries. Any difference from ``VERDICT.json`` / ``RUN_RECORD.json`` is REFUSED (``ProjectionError``),
never repaired. The server logs are not re-parsed (the attrib record is the retained evidence; the log-to-attrib step is
the producer's, named in ``extra``).

PROJECTION ONLY. ``claim_tuple.grade()`` decides every grade; this module registers no ladder. Six tuples per run:
the median ON-minus-OFF client gap delta, the four group deltas (``NEIGHBOUR_IDLE_SAVE``, ``OWN_PROMPT_LOAD``,
``OTHER_PROMPT_LOAD``, ``QUEUE_AND_LOOP_BUSY``; seconds, median over valid pairs) and the ON copy-throughput median
(GiB/s, report-only in the rule). ``reps`` = valid ABBAAB pairs (copies for the throughput), ``protocol_id`` =
``ufh14-lb7-predeclaration-sha256:<sha256 of PREDECLARATION.md>``, build sha from the launched binary's build dir and
RUN_RECORD's ``llama_server_sha256``. The run's verdict word rides verbatim in the claim and ``observation.outcome_native``.

Absence: ``INCOMPLETE`` (< 2 valid pairs) and ``INSTRUMENT_FAIL`` runs project NOTHING (declined; ``decline_reason``
names why). A directory whose ``VERDICT.json`` has another schema is declined (``[]``).

Retrofit (DP-1 (a)): the producer has no belief hook, so every projection says ``observation.retrofit``.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import scope_from_argv  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.ufh14_lb7_stall/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ufh14-lb7-stall"
KNOB_FAMILY = "slot_serving"
VERDICT_SCHEMA = "epyc.ufh14.lb7.verdict.v1"
ATTRIB_SCHEMA = "epyc.ufh14.lb7.attrib.v1"
ITEM = "locals-ufh14-lb7-stall"
_MAX_BYTES = 32 << 20

# --- the producer's fixed constants (lb7_parse.py) ---------------------------------------------------------------
COMPONENTS = ["neighbour_save_own_trigger", "neighbour_save_other_trigger", "idle_noop",
              "own_load_victim_save", "own_load_lookup", "own_load_copy", "own_load_bookkeeping",
              "other_load", "dispatch_overhead", "residual_pre_pickup", "residual_post_launch"]
GROUPS = {"NEIGHBOUR_IDLE_SAVE": ["neighbour_save_own_trigger", "neighbour_save_other_trigger"],
          "OWN_PROMPT_LOAD": ["own_load_victim_save", "own_load_lookup", "own_load_copy", "own_load_bookkeeping"],
          "OTHER_PROMPT_LOAD": ["other_load"],
          "QUEUE_AND_LOOP_BUSY": ["idle_noop", "dispatch_overhead", "residual_pre_pickup", "residual_post_launch"]}
ORDER = ["s1-ON", "s2-OFF", "s3-OFF", "s4-ON", "s5-ON", "s6-OFF"]
PAIRS = [("s1-ON", "s2-OFF"), ("s4-ON", "s3-OFF"), ("s5-ON", "s6-OFF")]
MIN_EFFECT_S = 10.0
DECLINED_VERDICTS = ("INCOMPLETE", "INSTRUMENT_FAIL")
_OUTCOME = {"NOT_REPRODUCED": "null"}

# rounding noise: per-turn values are stored at 4 decimals, summary values at 4, so a re-derived mean differs from
# the stated one by at most a few 1e-5; anything beyond ABS_ROUND is a real disagreement.
ABS_ROUND = 3e-4
_REL = 1e-9


def _same(stated: Any, derived: Any, where: str, *, tol: float = 0.0) -> None:
    """Deep, order-insensitive-on-keys comparison; floats within ``tol`` (0 -> producer-exact re-summation)."""
    if isinstance(derived, dict):
        if not isinstance(stated, dict) or set(stated) != set(derived):
            raise ProjectionError(f"{where}: keys differ (stated {sorted(stated) if isinstance(stated, dict) else stated!r}, "
                                  f"re-derived {sorted(derived)})")
        for k in derived:
            _same(stated[k], derived[k], f"{where}.{k}", tol=tol)
    elif isinstance(derived, (list, tuple)):
        if not isinstance(stated, (list, tuple)) or len(stated) != len(derived):
            raise ProjectionError(f"{where}: list differs (stated {stated!r}, re-derived {derived!r})")
        for i, (s, d) in enumerate(zip(stated, derived)):
            _same(s, d, f"{where}[{i}]", tol=tol)
    elif isinstance(derived, bool) or derived is None or isinstance(derived, str):
        if stated != derived or type(stated) is not type(derived):
            raise ProjectionError(f"{where}: stated {stated!r}, re-derived {derived!r}")
    elif isinstance(derived, (int, float)):
        if type(stated) not in (int, float) or type(stated) is bool or not math.isfinite(stated):
            raise ProjectionError(f"{where}: stated {stated!r} is not a number")
        if not math.isclose(float(stated), float(derived), rel_tol=_REL, abs_tol=max(tol, 1e-12)):
            raise ProjectionError(f"{where}: stated {stated!r}, re-derived {derived!r}")
    else:
        raise ProjectionError(f"{where}: unsupported value {derived!r}")


def _read(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ProjectionError(f"{path.name} is not a bounded regular file")
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> tuple[dict, str]:
    raw, digest = _read(path)
    try:
        doc = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"{path.name} is not JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ProjectionError(f"{path.name} is not an object")
    return doc, digest


# --- session re-derivation (lb7_parse.attribute_session, the turn-2+ summary) --------------------------------------
def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.mean(xs), 4) if xs else None


def _med(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 4) if xs else None


def verify_session(s: dict) -> None:
    """Refuse an attrib record whose summary does not follow from its own per-turn rows."""
    label = s.get("label")
    where = f"{label}.attrib"
    turns = s.get("per_turn")
    if not isinstance(turns, list) or not turns or not all(isinstance(t, dict) for t in turns):
        raise ProjectionError(f"{where}: per_turn is missing")
    if s.get("n_turns") != len(turns) or s.get("n_matched") != len(turns) - len(s.get("unmatched") or []):
        raise ProjectionError(f"{where}: n_turns / n_matched disagree with the per-turn rows")
    for t in turns:
        comp = t.get("components_s")
        grp = t.get("groups_s")
        if not isinstance(comp, dict) or not isinstance(grp, dict) or set(comp) != set(COMPONENTS) \
                or set(grp) != set(GROUPS):
            raise ProjectionError(f"{where}: turn {t.get('conv')}/{t.get('turn')} lacks the component partition")
        for g, members in GROUPS.items():
            _same(grp[g], sum(comp[c] for c in members), f"{where}.turn{t.get('conv')}/{t.get('turn')}.{g}",
                  tol=ABS_ROUND)
    later = [p for p in turns if p["turn"] >= 2]
    lags = [p["lag_s"] for p in turns if p.get("lag_s") is not None]
    al = s.get("align") or {}
    _same(al.get("n_lag_below_0_2s"), sum(1 for x in lags if x < 0.2), f"{where}.align.n_lag_below_0_2s")
    _same(al.get("lag_max_s"), max(lags) if lags else None, f"{where}.align.lag_max_s", tol=ABS_ROUND)
    if lags and not (al.get("lag_p95_s") is not None and min(lags) - ABS_ROUND <= al["lag_p95_s"] <= max(lags) + ABS_ROUND):
        raise ProjectionError(f"{where}: lag_p95 lies outside the per-turn lag range")
    derived = {
        "n": len(later),
        "gap_client_mean_s": _mean(p["gap_client_s"] for p in later),
        "gap_client_median_s": _med(p["gap_client_s"] for p in later),
        "pre_hdr_client_mean_s": _mean(p["pre_hdr_client_s"] for p in later),
        "W_mean_s": _mean(p["W_server_s"] for p in later),
        "W_median_s": _med(p["W_server_s"] for p in later),
        "components_mean_s": {c: _mean(p["components_s"][c] for p in later) for c in COMPONENTS},
        "groups_mean_s": {g: _mean(p["groups_s"][g] for p in later) for g in GROUPS},
        "groups_median_s": {g: _med(p["groups_s"][g] for p in later) for g in GROUPS},
        "draft_copy_est_mean_s": _mean(p["draft_copy_est_s"] for p in later),
        "prompt_ms_mean": _mean(p["prompt_ms"] for p in later),
    }
    t2 = s.get("turn2plus")
    if not isinstance(t2, dict):
        raise ProjectionError(f"{where}: turn2plus is missing")
    seq = [[p["conv"], p["turn"], p["slot"], p["sel_how"]] for p in sorted(later, key=lambda p: (p["turn"], p["conv"]))]
    # prompt_ms is stored unrounded (3 decimals) in the rows and the mean is over them: exact to 4 decimals.
    _same({k: t2.get(k) for k in derived}, derived, f"{where}.turn2plus", tol=ABS_ROUND)
    _same(t2.get("slot_sequence"), seq, f"{where}.turn2plus.slot_sequence")
    for c in s.get("copies") or []:
        mib, sec = c.get("mib"), c.get("s")
        if not (type(mib) in (int, float) and type(sec) in (int, float) and sec > 0):
            raise ProjectionError(f"{where}: a copy record lacks mib / s")
        d = mib / 1024 / sec
        if abs(c.get("gib_per_s", math.nan) - d) > 6e-4 + 2e-3 * d:
            raise ProjectionError(f"{where}: copy gib_per_s {c.get('gib_per_s')!r} != mib/1024/s {d!r}")


# --- verdict re-derivation (lb7_parse.aggregate, exact) --------------------------------------------------------------
def rederive_verdict(by_label: dict[str, dict], min_effect_s: float = MIN_EFFECT_S) -> dict:
    res: dict = {"schema": VERDICT_SCHEMA, "rule": "PREDECLARATION.md sections 4-5", "min_effect_s": min_effect_s,
                 "sessions_present": [l for l in ORDER if l in by_label], "pairs": [], "gates": {}}
    valid = []
    for on_l, off_l in PAIRS:
        on, off = by_label.get(on_l), by_label.get(off_l)
        if not on or not off or on.get("status") != "OK" or off.get("status") != "OK":
            res["pairs"].append({"pair": [on_l, off_l], "valid": False, "why": "session missing or not OK"})
            continue
        a, b = on["turn2plus"], off["turn2plus"]
        dG = (a["gap_client_mean_s"] or 0) - (b["gap_client_mean_s"] or 0)
        dW = (a["W_mean_s"] or 0) - (b["W_mean_s"] or 0)
        dgrp = {g: round((a["groups_mean_s"][g] or 0) - (b["groups_mean_s"][g] or 0), 3) for g in GROUPS}
        dcmp = {c: round((a["components_mean_s"][c] or 0) - (b["components_mean_s"][c] or 0), 3) for c in COMPONENTS}
        frac = {g: (round(v / dW, 3) if dW > 0 else None) for g, v in dgrp.items()}
        cover = (a["W_mean_s"] or 0) / a["gap_client_mean_s"] if a.get("gap_client_mean_s") else None
        align_ok = all(s["align"]["lag_p95_s"] <= 0.5 and s["align"]["n_lag_below_0_2s"] >= 3 for s in (on, off))
        match_ok = all(s["n_matched"] >= 0.9 * s["n_turns"] for s in (on, off))
        p = {"pair": [on_l, off_l], "valid": True, "dGap_client_s": round(dG, 3), "dW_server_s": round(dW, 3),
             "gap_on_median_s": a["gap_client_median_s"], "gap_off_median_s": b["gap_client_median_s"],
             "coverage_on": round(cover, 3) if cover else None, "align_ok": align_ok, "match_ok": match_ok,
             "dGroups_s": dgrp, "fraction_of_dW": frac, "dComponents_s": dcmp,
             "draft_copy_est_on_s": a["draft_copy_est_mean_s"],
             "pre_hdr_share_on": round(a["pre_hdr_client_mean_s"] / a["gap_client_mean_s"], 3)
             if a.get("gap_client_mean_s") else None}
        res["pairs"].append(p)
        valid.append(p)
    res["n_valid_pairs"] = len(valid)
    if len(valid) < 2:
        res["verdict"] = "INCOMPLETE"
        return res
    reproduced = statistics.median(p["dGap_client_s"] for p in valid) >= 20.0 \
        and all((p["gap_on_median_s"] or 0) >= 20.0 for p in valid)
    instrument_ok = all(p["align_ok"] and p["match_ok"] and p["coverage_on"] is not None
                        and abs(1 - p["coverage_on"]) <= 0.10 for p in valid)
    res["gates"] = {"reproduced": reproduced, "instrument_ok": instrument_ok,
                    "stall_before_eval": all((p["pre_hdr_share_on"] or 0) >= 0.8 for p in valid)}
    med_frac = {g: statistics.median(p["fraction_of_dW"][g] or 0 for p in valid) for g in GROUPS}
    med_d = {g: statistics.median(p["dGroups_s"][g] for p in valid) for g in GROUPS}
    res["median_fraction_of_dW"] = {g: round(v, 3) for g, v in med_frac.items()}
    res["median_dGroups_s"] = {g: round(v, 3) for g, v in med_d.items()}
    res["median_dComponents_s"] = {c: round(statistics.median(p["dComponents_s"][c] for p in valid), 3)
                                   for c in COMPONENTS}
    res["report_only"] = {"PROMPT_LOAD_ALL_median_fraction_of_dW": round(statistics.median(
        (p["fraction_of_dW"]["OWN_PROMPT_LOAD"] or 0) + (p["fraction_of_dW"]["OTHER_PROMPT_LOAD"] or 0)
        for p in valid), 3),
        "draft_copy_est_on_median_s": round(statistics.median(p["draft_copy_est_on_s"] or 0 for p in valid), 3)}
    if not reproduced:
        res["verdict"] = "NOT_REPRODUCED"
        return res
    if not instrument_ok:
        res["verdict"] = "INSTRUMENT_FAIL"
        return res
    owners = [g for g in GROUPS if all((p["fraction_of_dW"][g] or 0) >= 0.5 for p in valid) and med_d[g] >= min_effect_s]
    if owners:
        res["verdict"] = f"OWNER={owners[0]}"
    else:
        material = sorted((g for g in GROUPS if med_d[g] >= min_effect_s), key=lambda g: -med_d[g])
        if len(material) >= 2 and sum(med_frac[g] for g in material[:2]) >= 0.8:
            res["verdict"] = f"SHARED={material[0]}+{material[1]}"
        else:
            res["verdict"] = "UNATTRIBUTED"
    if "QUEUE_AND_LOOP_BUSY" in res["verdict"]:
        res["follow_up"] = ("residual-dominant: the stall is loop time no -lv 4 line covers; next stage = timing "
                            "probes on an experimental branch (PREDECLARATION.md section 6)")
    gps = [c["gib_per_s"] for s in by_label.values() if s.get("arm") == "ON" and s.get("status") == "OK"
           for c in s.get("copies", [])]
    if gps:
        m = statistics.median(gps)
        res["copy_throughput_median_gib_s"] = round(m, 3)
        res["copy_mechanism_tag"] = ("transfer-count bound (fragmented ranges / per-cell scatter)" if m < 1.0
                                     else "bandwidth bound" if m > 5.0 else "mixed")
    return res


# --- unit reading --------------------------------------------------------------------------------------------------
def _is_unit(unit: Path) -> bool:
    v = unit / "VERDICT.json"
    if not v.is_file():
        return False
    try:
        doc = json.loads(v.read_bytes()[:_MAX_BYTES])
    except (ValueError, RecursionError):
        return False
    return isinstance(doc, dict) and doc.get("schema") == VERDICT_SCHEMA


def _unit_dir(unit_dir: str | Path) -> Path:
    unit = Path(unit_dir)
    if unit.is_file():
        unit = unit.parent
    if unit.name == "out" and not (unit / "VERDICT.json").is_file():
        unit = unit.parent
    return unit


def _load(unit: Path) -> dict:
    """Read + verify everything; the returned context carries the re-derived verdict (any verdict word)."""
    verdict, v_digest = _json(unit / "VERDICT.json")
    run_record, rr_digest = _json(unit / "RUN_RECORD.json")
    if run_record.get("item") != ITEM:
        raise ProjectionError(f"RUN_RECORD.json item {run_record.get('item')!r} is not {ITEM!r}")
    _pre_raw, pre_digest = _read(unit / "PREDECLARATION.md")
    by_label: dict[str, dict] = {}
    attrib_sha: dict[str, str] = {}
    for label in ORDER:
        p = unit / "out" / f"{label}.attrib.json"
        if not p.is_file():
            continue
        doc, d = _json(p)
        if doc.get("schema") != ATTRIB_SCHEMA or doc.get("label") != label \
                or doc.get("arm") != label.rsplit("-", 1)[1]:
            raise ProjectionError(f"{p.name}: schema / label / arm do not match {label}")
        if doc.get("status") == "OK":
            verify_session(doc)
        by_label[label] = doc
        attrib_sha[label] = d
    if sorted(by_label) != sorted(verdict.get("sessions_present") or []):
        raise ProjectionError("VERDICT.json sessions_present differs from the attrib files on disk")
    if verdict.get("min_effect_s") != MIN_EFFECT_S:
        raise ProjectionError(f"VERDICT.json min_effect_s {verdict.get('min_effect_s')!r} is not the predeclared "
                              f"{MIN_EFFECT_S}")
    derived = rederive_verdict(by_label)
    _same(verdict, derived, "VERDICT.json")
    if run_record.get("verdict") != derived["verdict"]:
        raise ProjectionError("RUN_RECORD.json verdict differs from the re-derived verdict")
    ok = sum(1 for s in by_label.values() if s.get("status") == "OK")
    if run_record.get("sessions_ok") != ok:
        raise ProjectionError(f"RUN_RECORD.json sessions_ok {run_record.get('sessions_ok')!r} != {ok} OK attribs")
    return {"unit": unit, "verdict": derived, "verdict_sha256": v_digest, "run_record": run_record,
            "run_record_sha256": rr_digest, "predeclaration_sha256": pre_digest, "by_label": by_label,
            "attrib_sha256": attrib_sha}


def decline_reason(unit_dir: str | Path) -> str | None:
    """Why a verified unit projects nothing (``None`` when it projects, or when it is not an LB7 unit)."""
    unit = _unit_dir(unit_dir)
    if not _is_unit(unit):
        return None
    word = _load(unit)["verdict"]["verdict"]
    if word == "INCOMPLETE":
        return "INCOMPLETE: fewer than 2 valid ABBAAB pairs; no verdict, no grade"
    if word == "INSTRUMENT_FAIL":
        return "INSTRUMENT_FAIL: alignment / match / coverage gate failed; the attribution is not evidence"
    return None


def _scope_inputs(ctx: dict) -> tuple[list | None, str | None, bool]:
    """(argv, binary, readback_ok) from the ON sessions' replay preflight: own pid, KFD VRAM, build."""
    unit, rr = ctx["unit"], ctx["run_record"]
    argv, ok = None, False
    for label in ORDER:
        s = ctx["by_label"].get(label)
        if not s or s.get("status") != "OK" or s.get("arm") != "ON":
            continue
        rp = unit / "out" / label / "report.json"
        if not rp.is_file():
            return None, None, False
        try:
            pre = json.loads(rp.read_bytes()[:_MAX_BYTES]).get("preflight") or {}
        except (ValueError, RecursionError):
            return None, None, False
        a = pre.get("argv")
        kfd = pre.get("kfd") or []
        proven = (isinstance(a, list) and all(isinstance(t, str) for t in a)
                  and any(k.get("pid") == pre.get("pid") and (k.get("vram_gib") or 0) > 0 for k in kfd if isinstance(k, dict))
                  and str(rr.get("champion", "")).split("/")[0] in str(pre.get("props_build", "")))
        if not proven:
            return None, None, False
        if argv is None:
            argv = a
        elif a != argv and [t for t in a if "slot-save-path" not in t and "/slots" not in t] != \
                [t for t in argv if "slot-save-path" not in t and "/slots" not in t]:
            return None, None, False
        ok = True
    if argv is None:
        return None, None, False
    binary = argv[0] if argv and argv[0].endswith("/llama-server") else None
    if binary is not None and binary != rr.get("binary"):
        return argv, binary, False
    return argv, binary, ok


def native_rows(unit_dir: str | Path) -> list[dict]:
    """Six native rows for a verified, gradeable UFH14-LB7 unit; ``[]`` for a foreign dir, INCOMPLETE or INSTRUMENT_FAIL."""
    unit = _unit_dir(unit_dir)
    if not _is_unit(unit):
        return []
    ctx = _load(unit)
    v = ctx["verdict"]
    if v["verdict"] in DECLINED_VERDICTS:
        return []
    if not v.get("median_dGroups_s"):
        raise ProjectionError("a gradeable verdict must state its median group deltas")
    rr = ctx["run_record"]
    argv, binary, readback_ok = _scope_inputs(ctx)
    producer = unit / "lb7_parse.py"
    prod_sha = hashlib.sha256(producer.read_bytes()).hexdigest() if producer.is_file() else None
    valid = [p for p in v["pairs"] if p.get("valid")]
    gap = round(statistics.median(p["dGap_client_s"] for p in valid), 3)
    on_copies = [c for s in ctx["by_label"].values() if s.get("arm") == "ON" and s.get("status") == "OK"
                 for c in s.get("copies", [])]
    base = {"unit_dir": str(unit), "run_name": unit.name, "verdict": v["verdict"], "n_valid_pairs": v["n_valid_pairs"],
            "predeclaration_sha256": ctx["predeclaration_sha256"], "verdict_sha256": ctx["verdict_sha256"],
            "run_record_sha256": ctx["run_record_sha256"], "attrib_sha256": ctx["attrib_sha256"],
            "producer_sha256": prod_sha, "date": rr.get("time"), "gates": v["gates"], "argv": argv, "binary": binary,
            "binary_sha256": rr.get("llama_server_sha256"), "champion": rr.get("champion"), "readback_ok": readback_ok,
            "copy_mechanism_tag": v.get("copy_mechanism_tag"), "median_fraction_of_dW": v["median_fraction_of_dW"],
            "pairs": [p["pair"] for p in valid]}
    rows = [{**base, "metric_key": "client_gap_delta", "value": gap, "reps": v["n_valid_pairs"]}]
    rows += [{**base, "metric_key": f"delta_{g}", "value": v["median_dGroups_s"][g], "group": g,
              "reps": v["n_valid_pairs"]} for g in GROUPS]
    if on_copies and "copy_throughput_median_gib_s" in v:
        rows.append({**base, "metric_key": "copy_throughput", "value": v["copy_throughput_median_gib_s"],
                     "reps": len(on_copies)})
    return rows


# --- projection ----------------------------------------------------------------------------------------------------
_METRICS = {"client_gap_delta": ("ufh14_lb7_client_gap_delta", "s", "lower_better"),
            **{f"delta_{g}": (f"ufh14_lb7_delta_{g.lower()}", "s", "lower_better") for g in GROUPS},
            "copy_throughput": ("ufh14_lb7_on_copy_throughput", "GiB/s", "higher_better")}


def _claim(n: dict, metric: str, unit: str) -> str:
    key = n["metric_key"]
    what = {"client_gap_delta": "median over valid pairs of the ON-minus-OFF mean client gap (TTFT - prompt_ms)",
            "copy_throughput": "median ON-session copy throughput (idle saves and restores)"}.get(
        key, f"median over valid pairs of the ON-minus-OFF mean server-window time in {n.get('group')}")
    return (f"UFH14-LB7 {n['run_name']}: {what} = {n['value']:g} {unit} (n = {n['reps']} "
            f"{'copies' if key == 'copy_throughput' else 'valid ABBAAB pairs'}); Qwen3.8-27B Q8_0 + DFlash2, MI210, "
            f"np 4, --cache-idle-slots ON vs --no-cache-idle-slots, champion {n.get('champion')}; run verdict "
            f"{n['verdict']} (PREDECLARATION.md sha256 {n['predeclaration_sha256'][:16]})")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    key = native.get("metric_key")
    if key not in _METRICS:
        raise ProjectionError(f"UFH14-LB7 metric {key!r} is unknown")
    value = native.get("value")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ProjectionError("UFH14-LB7 value is not a finite number")
    if native.get("verdict") in DECLINED_VERDICTS:
        raise ProjectionError(f"UFH14-LB7 verdict {native.get('verdict')!r} projects nothing")
    reps = native.get("reps")
    if type(reps) is not int or reps < 1:
        raise ProjectionError("UFH14-LB7 reps must be a positive count")
    pre = native.get("predeclaration_sha256")
    digest = native.get("verdict_sha256")
    if not (isinstance(pre, str) and len(pre) == 64 and isinstance(digest, str) and len(digest) == 64):
        raise ProjectionError("UFH14-LB7 native row lost its digests")
    metric, unit, direction = _METRICS[key]
    obs: dict = {"retrofit": True, "outcome_native": str(native["verdict"])[:120]}
    if native["verdict"] in _OUTCOME:
        obs["outcome"] = _OUTCOME[native["verdict"]]
    extra = {k: native.get(k) for k in (
        "verdict", "n_valid_pairs", "pairs", "gates", "median_fraction_of_dW", "copy_mechanism_tag", "group",
        "predeclaration_sha256", "verdict_sha256", "run_record_sha256", "attrib_sha256", "producer_sha256", "champion",
        "binary", "binary_sha256", "unit_dir") if native.get(k) is not None}
    extra.update(schema=VERDICT_SCHEMA, rule="PREDECLARATION.md sections 4-5", min_effect_s=MIN_EFFECT_S,
                 write_side_gap="the producer wrote no belief_measurements.jsonl; retrofit projection",
                 log_to_attrib_step="lb7_parse.py session (server.log -> attrib.json), not re-parsed by this reader")
    scope = scope_from_argv(native.get("argv"), binary=native.get("binary"), binary_sha256=native.get("binary_sha256"),
                            family=KNOB_FAMILY, varied=["cache_idle_slots"], dflash2=True,
                            readback_ok=bool(native.get("readback_ok")))
    if scope:
        sha = str(native.get("champion") or "").split("/")[0]
        if sha and "build_sha" not in scope and f"-{sha}-" in str(native.get("binary") or ""):
            scope["build_sha"] = sha   # the build dir is gpu-<date>-<sha>-<tag>; the shared regex wants no tag
        scope["run_id"] = f"ufh14-lb7:{native['run_name']}"
    return ClaimTuple(
        measurement_id=f"ufh14lb7:v1:{native['run_name']}:{digest[:16]}:{key}",
        metric=metric, value=value, unit=unit, date=str(native.get("date") or ""), category="CANDIDATE",
        claim=_claim(native, metric, unit), metric_direction=direction,
        protocol_id=f"ufh14-lb7-predeclaration-sha256:{pre}", reps=reps,
        reps_basis=("scored:ON copy intervals across the ON sessions" if key == "copy_throughput"
                    else "scored:valid ABBAAB ON/OFF pairs, 15 turns >= 2 per session"),
        attestation_locator=f"ufh14-lb7:{native['run_name']}:VERDICT.json#{key}", attestation_sha256=digest,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra=extra, applicability=scope, observation=obs)


__all__ = ["ADAPTER_ID", "AUTHORITY", "KNOB_FAMILY", "SOURCE_KIND", "decline_reason", "native_rows", "project",
           "rederive_verdict", "verify_session"]
