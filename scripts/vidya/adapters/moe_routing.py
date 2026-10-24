"""VB-MOE-ROUTING-WIRE: INF-72 RT-1 MoE routing-trace ANALYSES as measurement OBSERVATIONS.

Source: the analysis JSONs of ``epyc-inference-research/scripts/benchmark/moe_routing`` -- ``skew_report.json`` (RT-5),
``residency_curve.json`` (RT-7), ``placement_replay_{same,cross}.json`` (RT-6) and ``locality_report.json`` (RT-8) -- AS
STAMPED by the producer (``trace_io.stamp``): every analysis document carries ``input_traces`` (one record per input shard:
rows / ids sha256, shard path, model file, arch, corpus sha256, chunk size, window accounting, hazard-guard status, verified
and quarantine markers) and a ``content_sha256`` (sha256 of the canonical JSON of the document excluding that key). An
analysis written before that emit has neither and yields NO row; nothing is back-filled (spec section 4.7).

One self-hashed sidecar row per projected statistic (``moe_routing.beliefs.jsonl``):

* ``moe_skew_top{10,25}_share_heldout`` -- per (domain, phase): held-out share of expert selections on the top-10% / top-25%
  experts, mean over layers; the per-layer values, the in-sample share and the uniform-routing null ride in the row.
* ``moe_residency_hit_rate`` -- h(k) per (learned-on domain A, scored domain B, phase, k): share of B's selections a static
  k-experts-per-layer residency learned on A covers; the chance k/E and the in-sample oracle bound ride in the row.
* ``moe_placement_max_over_mean`` -- per (domain, calibration, bins, phase, T, arm): per-step max-bin-load / mean-bin-load with
  its bootstrap CI over windows; rows for the contiguous baseline and the arms the analysis itself selected (best practical /
  idealized-dispatch / bound), the null and the whole arm table riding in the row.
* ``moe_ir_t_mean`` / ``moe_lru_hit_rate`` / ``moe_coactivation_excess_fraction`` -- per (domain, phase[, k]).

Doctrine (README "INF-72 RT-1" and "MoE per-token routing tap" rows): PROJECTION ONLY; ``claim_tuple.grade()`` decides. The
strict reader RE-DERIVES the row's scope (model file, arch, workload corpus sha256, phase, chunk size, calibration source, n
windows / steps) from the row's own recorded ``input_traces`` -- it never opens a trace shard -- and re-derives every value from
the recorded per-layer payload. A shard that is quarantined, unverified (VERIFIED marker or recomputed sha256 missing) or whose
RT-3 hazard guard did not run yields no row; a stride-hazard signature (guard FATAL count, sub-chance adjacent
reuse, perfectly flat expert counts) is REFUSED fail-closed (a non-fatal guard sub-chance count rides in the scope as
``guard_sub_chance_checks``: the real Qwen3.6 code shards carry 1-2 in ~20k checks with the guard passed); domains are never pooled (one evaluated domain per row); an
analysis never mixes models, so a number is a claim about THAT model only and is never projected for another. Every metric here
is a DIAGNOSTIC of the routing distribution: the ``higher_better`` / ``lower_better`` label is carrier-only, and none of these
rows licenses a throughput claim (INF-72 objective). ``protocol_id`` is always empty (no codified protocol), so the ladder caps
the tuples.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import posixpath
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.moe_routing_capture.v1"
SIDECAR_NAME = "moe_routing.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.moe_routing/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "moe-routing-analysis"
PROVENANCE_SCHEMA = "epyc.moe.analysis_provenance.v1"
#: file names the writer scans for in an analysis directory (mirrors research trace_io.ANALYSIS_FILES)
ANALYSIS_FILES = ("skew_report.json", "residency_curve.json", "placement_replay_same.json", "placement_replay_cross.json",
                  "locality_report.json")
KINDS = ("skew_report", "residency_curve", "placement_replay", "locality_report")
REL = 1e-9
HAZARD = "STRIDE-HAZARD"
UNVERIFIED = "UNVERIFIED-INPUT"
SKEW_FRACS = (10, 25)
#: metric -> (analysis kind, unit, direction); the direction is a carrier label, never a performance claim
METRICS = {
    "moe_skew_top10_share_heldout": ("skew_report", "fraction of expert selections on the top-10% experts (held-out, mean over layers)", "higher_better"),
    "moe_skew_top25_share_heldout": ("skew_report", "fraction of expert selections on the top-25% experts (held-out, mean over layers)", "higher_better"),
    "moe_residency_hit_rate": ("residency_curve", "fraction of the scored phase's expert selections covered by a static k-per-layer residency", "higher_better"),
    "moe_placement_max_over_mean": ("placement_replay", "per-step max-bin-load / mean-bin-load, mean over steps and layers (1.0 = perfect balance)", "lower_better"),
    "moe_ir_t_mean": ("locality_report", "mean adjacent-token expert-set overlap IR_t = |E_t n E_(t-1)| / K, mean over layers", "higher_better"),
    "moe_lru_hit_rate": ("locality_report", "within-window fully-associative LRU expert-cache hit rate, mean over the sampled layers", "higher_better"),
    "moe_coactivation_excess_fraction": ("locality_report", "co-activation pair mass above the rescaled-independence null, mean over layers", "higher_better"),
}
M_SKEW = {10: "moe_skew_top10_share_heldout", 25: "moe_skew_top25_share_heldout"}
PHASES = frozenset({"prefill", "decode", "all"})
RULES = frozenset({"all", "odd", "mod4eq3", "first"})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHA_TAIL = re.compile(r"-([0-9a-f]{7,40})$")


# --------------------------------------------------------------------------------------------- small helpers
def canonical_json(obj: Any) -> str:
    """The form ``content_sha256`` is taken over (identical to research ``trace_io.canonical_json``)."""
    return json.dumps(json.loads(json.dumps(obj)), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def content_sha256(doc: dict) -> str:
    """sha256 of the canonical JSON of ``doc`` excluding its ``content_sha256`` key."""
    return hashlib.sha256(canonical_json({k: v for k, v in doc.items() if k != "content_sha256"}).encode("utf-8")).hexdigest()


def _close(a: Any, b: Any) -> bool:
    return ns.finite(a) and ns.finite(b) and math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-9)


def _mean(xs: Iterable[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs)


def _posint(x: Any) -> bool:
    return not isinstance(x, bool) and isinstance(x, int) and x > 0


def _nonneg(x: Any) -> bool:
    return not isinstance(x, bool) and isinstance(x, int) and x >= 0


def _hex(x: Any) -> bool:
    return isinstance(x, str) and bool(_HEX64.match(x))


def _unit_frac(x: Any) -> bool:
    return ns.finite(x) and -1e-9 <= x <= 1 + 1e-9


# --------------------------------------------------------------------------------------------- input traces
_TRACE_KEYS = ("shard", "part", "domain", "arch", "model_path", "llama_build_info", "corpus_sha256", "ids_sha256", "rows_sha256")


def trace_problems(traces: Any) -> list[str]:
    """Verdict on a row's recorded ``input_traces`` ALONE (no shard is opened). ``UNVERIFIED-INPUT`` problems mean the
    inputs were not proven (no row); ``STRIDE-HAZARD`` problems mean the tap's own guard flagged a broken read (refused)."""
    if not isinstance(traces, list) or not traces:
        return ["input_traces must be a non-empty list of shard records"]
    p: list[str] = []
    seen: set = set()
    for i, t in enumerate(traces):
        w = f"input_traces[{i}]"
        if not isinstance(t, dict):
            p.append(f"{w} is not an object")
            continue
        for k in _TRACE_KEYS:
            if not ns.text(t.get(k)):
                p.append(f"{w}.{k} must be a non-empty string")
        for k in ("corpus_sha256", "ids_sha256", "rows_sha256"):
            if ns.text(t.get(k)) and not _hex(t.get(k)):
                p.append(f"{w}.{k} must be a 64-hex digest")
        if t.get("shard") in seen:
            p.append(f"{w}.shard is listed twice")
        seen.add(t.get("shard"))
        for k in ("chunk_size", "layers", "rows"):
            if not _posint(t.get(k)):
                p.append(f"{w}.{k} must be a positive integer")
        for k in ("first_window", "n_windows", "windows_prefill", "windows_decode", "rows_prefill", "rows_decode"):
            if not _nonneg(t.get(k)):
                p.append(f"{w}.{k} must be a non-negative integer")
        for k in ("n_experts", "top_k"):
            v = t.get(k)
            if not (isinstance(v, list) and len(v) == 1 and _posint(v[0])):
                p.append(f"{w}.{k} must be a single-value list (uniform layers)")
        if _nonneg(t.get("rows")) and _nonneg(t.get("rows_prefill")) and _nonneg(t.get("rows_decode")) \
                and t["rows_prefill"] + t["rows_decode"] != t["rows"]:
            p.append(f"{w}: rows_prefill + rows_decode must equal rows")
        # --- proof of the input, in the order the README states it: unverified / quarantined / guard did not run -> no row
        if t.get("hashes_verified") is not True:
            p.append(f"{UNVERIFIED}: {w} rows/ids sha256 were not recomputed equal to the manifest")
        if t.get("verified_marker") is not True:
            p.append(f"{UNVERIFIED}: {w} carries no VERIFIED marker")
        if t.get("quarantined") is not False:
            p.append(f"{UNVERIFIED}: {w} is quarantined")
        g = t.get("hazard_guard")
        if not isinstance(g, dict) or not _posint(g.get("checks")):
            p.append(f"{UNVERIFIED}: {w} hazard guard did not run (no checks recorded)")
        elif not (_nonneg(g.get("sub_chance_checks")) and _nonneg(g.get("fatal"))):
            p.append(f"{UNVERIFIED}: {w} hazard guard counts are malformed")
        elif g["fatal"] > 0:
            # The tap's own RT-3 verdict. A non-fatal sub-chance count (the real Qwen3.6 code shards carry 1-2 in ~20k checks, cv_min
            # 0.67, guard passed, VERIFIED) is NOT a stride read -- that would show in nearly every check at cv ~ 0 -- so it is carried
            # in the scope (guard_sub_chance_checks) instead of refused; the analysis-level signatures below still refuse a flat read.
            p.append(f"{HAZARD}: {w} hazard guard FATAL (fatal={g['fatal']}, sub_chance_checks={g['sub_chance_checks']}): a broken read, "
                     "not a negative result")
    if p:
        return p
    for k in ("model_path", "arch", "llama_build_info", "chunk_size", "layers", "n_experts", "top_k"):
        if len({json.dumps(t[k]) for t in traces}) != 1:
            p.append(f"input_traces mix different {k}: one analysis, one model (a number is a claim about THAT model only)")
    for dom in {t["domain"] for t in traces}:
        if len({t["corpus_sha256"] for t in traces if t["domain"] == dom}) != 1:
            p.append(f"domain {dom!r} lists more than one corpus sha256")
    return p


def _windows(t: dict, phase: str, rule: str, cutoff: int | None) -> int:
    """Windows of one shard that a statistic over (phase, rule) covers, from the shard's recorded accounting alone."""
    count = {"prefill": t["windows_prefill"], "decode": t["windows_decode"],
             "all": max(t["windows_prefill"], t["windows_decode"])}[phase]
    ids = range(t["first_window"], t["first_window"] + count)
    if rule == "all":
        return count
    if rule == "odd":
        return sum(1 for i in ids if i % 2 == 1)
    if rule == "mod4eq3":
        return sum(1 for i in ids if i % 4 == 3)
    return sum(1 for i in ids if cutoff is not None and i < cutoff)


def calibration_source(kind: str, subject: dict, payload: dict) -> str:
    """The calibration source named from the row's own recorded fields (cross-domain sources name their corpus)."""
    if kind == "skew_report":
        return "heldout:even-odd-window-split"
    if kind == "locality_report":
        return "none:descriptive-statistic"
    if kind == "residency_curve":
        a, b, ph = payload["learned_on"], subject["domain"], subject["phase"]
        sha = payload.get("calibration_corpus_sha256")
        if a != b:
            return f"learned-on:{a}:prefill:all-windows:corpus={sha}"
        return "learned-on:" + a + (":prefill:even-windows" if ph == "prefill" else ":prefill:all-windows")
    if kind == "placement_replay":
        calib, ph = payload["calib"], subject["phase"]
        if calib == "same":
            return "same-domain:" + ("prefill-windows>=24" if ph == "decode" else "prefill-windows-mod4!=3")
        return "cross-domain:" + ",".join(subject["calibration_domains"]) + ":prefill"
    return ""


def expected_scope(row: dict) -> tuple[dict | None, list[str]]:
    """Re-derive the row's scope from its recorded ``input_traces`` / ``subject`` / ``payload``. Never from a shard."""
    e = row["extra"]
    subj, payload, traces = e.get("subject"), e.get("payload"), e.get("input_traces")
    if not isinstance(subj, dict) or not isinstance(payload, dict):
        return None, ["extra.subject and extra.payload must be objects"]
    dom, phase, rule = subj.get("domain"), subj.get("phase"), subj.get("window_rule")
    cal = subj.get("calibration_domains")
    if not ns.text(dom) or phase not in PHASES or rule not in RULES or not isinstance(cal, list) \
            or not all(ns.text(c) for c in cal) or len(set(cal)) != len(cal) or dom in cal:
        return None, ["subject must name one evaluated domain, a phase, a window rule and the calibration domains"]
    kind = e.get("kind")
    ev = [t for t in traces if t["domain"] == dom]
    if not ev:
        return None, [f"no input trace belongs to the evaluated domain {dom!r}"]
    if any(t["domain"] not in {dom, *cal} for t in traces):
        return None, ["input_traces contain a domain that is neither evaluated nor a named calibration domain (pooling refused)"]
    if {t["domain"] for t in traces if t["domain"] != dom} != set(cal):
        return None, ["subject.calibration_domains must be exactly the other domains present in input_traces"]
    cutoff = payload.get("lru_windows") if rule == "first" else None
    if rule == "first" and not _posint(cutoff):
        return None, ["window rule 'first' needs payload.lru_windows"]
    if phase == "decode" and any(t["part"] == "bulk" and t["windows_decode"] for t in ev):
        return None, ["a bulk shard records decode windows (decode legs are their own shards)"]
    n_windows = sum(_windows(t, phase, rule, cutoff) for t in ev)
    first = ev[0]
    sc: dict = {"model_file": posixpath.basename(first["model_path"]), "model_path": first["model_path"], "arch": first["arch"],
                "domain": dom, "corpus_sha256": first["corpus_sha256"], "phase": phase, "chunk_size": first["chunk_size"],
                "calibration_source": "", "build_info": first["llama_build_info"], "n_experts": first["n_experts"][0],
                "top_k": first["top_k"][0], "layers": first["layers"], "n_windows": n_windows,
                "guard_checks": max(t["hazard_guard"]["checks"] for t in ev),
                "guard_sub_chance_checks": max(t["hazard_guard"]["sub_chance_checks"] for t in ev)}
    try:
        sc["calibration_source"] = calibration_source(kind, subj, payload)
        if kind == "residency_curve" and payload["learned_on"] != dom:
            a_tr = [t for t in traces if t["domain"] == payload["learned_on"]]
            if payload.get("calibration_corpus_sha256") != (a_tr[0]["corpus_sha256"] if a_tr else None):
                return None, ["payload.calibration_corpus_sha256 does not match the learned-on domain's recorded corpus"]
    except (KeyError, TypeError):
        return None, ["payload does not carry the fields its calibration source is named from"]
    n_unit = {"skew_report": "windows", "locality_report:lru": "windows", "residency_curve": "expert-selections",
              "placement_replay": "steps", "locality_report:ir": "adjacent-token-pairs",
              "locality_report:coact": "tokens"}
    key = kind if kind != "locality_report" else f"locality_report:{e.get('part')}"
    unit = n_unit.get(key)
    try:
        n = {"windows": lambda: n_windows, "expert-selections": lambda: payload.get("selections"),
             "steps": lambda: payload.get("steps"),
             "adjacent-token-pairs": lambda: sum(x["pairs"] for x in payload.get("per_layer", [])),
             "tokens": lambda: payload.get("tokens")}[unit]()
    except (KeyError, TypeError):
        return None, ["payload does not carry the counts n is taken from"]
    if not _posint(n) or not _posint(n_windows):
        return None, ["n and n_windows must be positive integers"]
    sc["n"], sc["n_unit"] = n, unit
    if phase == "decode":
        sc["decode_rows"] = sum(t["rows_decode"] for t in ev)
        caps = {t.get("decode_tokens_per_window") for t in ev if t["windows_decode"]}
        cap = next(iter(caps)) if len(caps) == 1 else None
        sc["decode_cap_per_window"] = cap
        sc["eos_stopped"] = bool(_posint(cap) and sc["decode_rows"] < n_windows * cap) if rule == "all" else None
    return sc, []


# --------------------------------------------------------------------------------------------- per-metric payload
def _layer_list(payload: dict, keys: tuple[str, ...], layers: int | None) -> list[str]:
    pl = payload.get("per_layer")
    if not isinstance(pl, list) or not pl:
        return ["payload.per_layer must be a non-empty list"]
    p: list[str] = []
    for i, x in enumerate(pl):
        if not isinstance(x, dict) or not _nonneg(x.get("layer")) or not all(ns.finite(x.get(k)) for k in keys):
            p.append(f"payload.per_layer[{i}] must carry a layer and finite {list(keys)}")
    if not p and len({x["layer"] for x in pl}) != len(pl):
        p.append("payload.per_layer repeats a layer")
    return p


def metric_problems(row: dict, scope: dict) -> list[str]:
    """Re-derive the value (and the fields it is read with) from the recorded payload."""
    e, m = row["extra"], row["metric"]
    pl, kind = e["payload"], e["kind"]
    p: list[str] = []
    if m in M_SKEW.values():
        frac = 10 if m == M_SKEW[10] else 25
        p += _layer_list(pl, ("n", "in_sample", "heldout", "null", "chance", "gini", "never_selected"), scope["layers"])
        if p:
            return p
        if pl.get("frac") != frac:
            p.append(f"payload.frac must be {frac}")
        if len(pl["per_layer"]) != scope["layers"]:
            p.append("skew rows cover every layer of the model: per_layer length must equal the recorded layer count")
        for k, src in (("in_sample_mean", "in_sample"), ("null_mean", "null"), ("chance_mean", "chance")):
            if not _close(pl.get(k), _mean(x[src] for x in pl["per_layer"])):
                p.append(f"payload.{k} must re-derive from per_layer")
        if not _close(row["value"], _mean(x["heldout"] for x in pl["per_layer"])):
            p.append("value must equal the mean of per_layer.heldout")
        if not (_posint(pl.get("rows")) and _posint(pl.get("selections"))):
            p.append("payload.rows and payload.selections must be positive integers")
        if any(not _unit_frac(x[k]) for x in pl["per_layer"] for k in ("in_sample", "heldout", "null", "chance")):
            p.append("shares must lie in [0, 1]")
        if any(x["gini"] < 1e-9 for x in pl["per_layer"]):
            p.append(f"{HAZARD}: a layer's expert counts are perfectly flat (gini 0): every expert selected equally often is the "
                     "stride-read signature, not a router")
    elif m == "moe_residency_hit_rate":
        for k in ("h", "chance", "oracle_in_sample"):
            if not _unit_frac(pl.get(k)):
                p.append(f"payload.{k} must be a fraction")
        if p:
            return p
        if not (_posint(pl.get("k")) and _posint(pl.get("selections"))):
            return ["payload.k and payload.selections must be positive integers"]
        if not _close(row["value"], pl["h"]):
            p.append("value must equal payload.h")
        if not _close(pl["chance"], pl["k"] / scope["n_experts"]):
            p.append("payload.chance must be k / n_experts")
        a, b, ph = pl.get("learned_on"), scope["domain"], scope["phase"]
        want = a if a != b else (f"{b}_even->{b}_odd(prefill)" if ph == "prefill" else f"{b}(same-domain prefill->decode)")
        if pl.get("learned_on_key") != want or not ns.text(a):
            p.append("payload.learned_on_key does not match (learned_on, scored domain, phase)")
    elif m == "moe_placement_max_over_mean":
        at, arm = pl.get("arms_table"), pl.get("arm")
        if not isinstance(at, dict) or arm not in at or not all(ns.finite(v) and v >= 1 - 1e-9 for v in at.values()):
            return ["payload.arms_table must map every arm to a max/mean >= 1 and contain payload.arm"]
        if not _close(row["value"], at[arm]):
            p.append("value must equal arms_table[arm]")
        ci = pl.get("ci95")
        if ci is not None and not (isinstance(ci, list) and len(ci) == 2 and all(ns.finite(c) for c in ci) and ci[0] <= ci[1]):
            p.append("payload.ci95 must be [lo, hi] with lo <= hi")
        cfg = pl.get("config")
        mm = re.fullmatch(r"B(\d+)/(prefill|decode)/T(\d+)", cfg or "")
        if not mm or (int(mm.group(1)), mm.group(2), int(mm.group(3))) != (pl.get("bins"), scope["phase"], pl.get("T")):
            p.append("payload.config must be B<bins>/<phase>/T<T> and match bins, phase and T")
        dec = pl.get("decision")
        roles = pl.get("roles")
        if not (isinstance(dec, dict) and isinstance(roles, list)):
            p.append("payload.decision and payload.roles must be recorded")
        else:
            want_roles = [r for r in ("best_practical", "best_idealized_dispatch", "best_bound") if dec.get(r) == arm]
            if arm == "contiguous":
                want_roles = ["baseline"] + want_roles
            if roles != want_roles:
                p.append("payload.roles must re-derive from the recorded decision block")
        if pl.get("anchor_arm") not in at:
            p.append("payload.anchor_arm must be an arm of the table")
        if pl.get("calib") not in ("same", "cross"):
            p.append("payload.calib must be 'same' or 'cross'")
        elif (pl["calib"] == "cross") != bool(e["subject"]["calibration_domains"]):
            p.append("a cross-domain calibration names its calibration domains and a same-domain one names none")
        if not (_posint(pl.get("steps")) and _posint(pl.get("bins")) and _posint(pl.get("T"))):
            p.append("payload.steps, bins and T must be positive integers")
    elif m == "moe_ir_t_mean":
        p += _layer_list(pl, ("ir_mean", "chance", "pairs"), scope["layers"])
        if p:
            return p
        if not _close(row["value"], _mean(x["ir_mean"] for x in pl["per_layer"])):
            p.append("value must equal the mean of per_layer.ir_mean")
        if not _close(pl.get("chance_mean"), _mean(x["chance"] for x in pl["per_layer"])):
            p.append("payload.chance_mean must re-derive from per_layer")
        if row["value"] < pl["chance_mean"] - 1e-12:
            p.append(f"{HAZARD}: adjacent-token reuse is below the K/E chance level (sub-chance reuse is a broken read)")
        if any(not _posint(x["pairs"]) for x in pl["per_layer"]):
            p.append("per_layer.pairs must be positive integers")
    elif m == "moe_lru_hit_rate":
        p += _layer_list(pl, ("hit_rate", "uniform_chance", "selections"), scope["layers"])
        if p:
            return p
        if not (_posint(pl.get("k")) and _posint(pl.get("lru_windows"))):
            return ["payload.k and payload.lru_windows must be positive integers"]
        if not _close(row["value"], _mean(x["hit_rate"] for x in pl["per_layer"])):
            p.append("value must equal the mean of per_layer.hit_rate")
        if not _close(pl.get("uniform_chance_mean"), _mean(x["uniform_chance"] for x in pl["per_layer"])):
            p.append("payload.uniform_chance_mean must re-derive from per_layer")
    elif m == "moe_coactivation_excess_fraction":
        p += _layer_list(pl, ("excess_fraction", "noise", "tokens"), scope["layers"])
        if p:
            return p
        if not _close(row["value"], _mean(x["excess_fraction"] for x in pl["per_layer"])):
            p.append("value must equal the mean of per_layer.excess_fraction")
        if not _close(pl.get("noise_mean"), _mean(x["noise"] for x in pl["per_layer"])):
            p.append("payload.noise_mean must re-derive from per_layer")
        if not _posint(pl.get("tokens")) or any(x["tokens"] != pl["tokens"] for x in pl["per_layer"]):
            p.append("payload.tokens must be the one positive token count of every layer")
    return p


def identity_parts(row: dict) -> dict:
    e, pl, sub = row["extra"], row["extra"]["payload"], row["extra"]["subject"]
    return {"analysis": e["analysis"]["content_sha256"], "metric": row["metric"], "domain": sub["domain"], "phase": sub["phase"],
            "calib": pl.get("calib"), "learned_on": pl.get("learned_on_key"), "k": pl.get("k"), "config": pl.get("config"),
            "arm": pl.get("arm")}


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: an observation, no codified protocol")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    kind, unit, direction = METRICS[row["metric"]]
    if e.get("kind") != kind or row.get("unit") != unit or row.get("metric_direction") != direction:
        p.append(f"metric {row['metric']!r} fixes kind/unit/direction to {kind!r}/{unit!r}/{direction!r}")
    an = e.get("analysis")
    if not (isinstance(an, dict) and an.get("kind") == kind and _hex(an.get("content_sha256")) and ns.text(an.get("file"))):
        p.append("extra.analysis must name the analysis kind, file and content_sha256")
    tp = trace_problems(e.get("input_traces"))
    if tp:
        return p + tp + ns.self_hash_problems(row)
    if p or not (isinstance(e.get("subject"), dict) and isinstance(e.get("payload"), dict) and isinstance(e.get("scope"), dict)):
        return p + ["extra.subject, extra.payload and extra.scope must be objects"] + ns.self_hash_problems(row)
    if row["metric"] in ("moe_ir_t_mean", "moe_lru_hit_rate", "moe_coactivation_excess_fraction") \
            and e.get("part") != {"moe_ir_t_mean": "ir", "moe_lru_hit_rate": "lru", "moe_coactivation_excess_fraction": "coact"}[row["metric"]]:
        p.append("extra.part must name the locality statistic")
    scope, why = expected_scope(row)
    if why:
        return p + why + ns.self_hash_problems(row)
    if e["scope"] != scope:
        p.append("extra.scope does not re-derive from the recorded input_traces / subject / payload")
    p += metric_problems(row, scope)
    basis = "steps" if row["metric"] == "moe_placement_max_over_mean" else "windows"
    want_reps = scope["n"] if basis == "steps" else scope["n_windows"]
    if row.get("reps") != want_reps or row.get("reps_basis") != f"scored:{basis}":
        p.append(f"reps/reps_basis must be {want_reps}/'scored:{basis}'")
    if not p:
        p += ns.check_identity(row, identity_parts(row), "moerout")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


# --------------------------------------------------------------------------------------------- writer
def _claim(metric: str, value: float, scope: dict, extra_txt: str) -> str:
    return (f"INF-72 RT-1 {metric} = {value:.6g} on {scope['model_file']} ({scope['arch']}), workload {scope['domain']} "
            f"(corpus {scope['corpus_sha256'][:12]}), {scope['phase']}, chunk {scope['chunk_size']}, {extra_txt}, "
            f"calibration {scope['calibration_source']}, n={scope['n']} {scope['n_unit']} over {scope['n_windows']} windows; "
            "a claim about THIS model only, a routing-distribution diagnostic with no throughput claim; the direction label "
            "is carrier-only")


def _specs(doc: dict) -> list[dict]:
    """Candidate rows of one stamped analysis document: {metric, subject, payload, part?, phase-free text}."""
    kind, out = doc["analysis_kind"], []
    doms = lambda d: sorted({t["domain"] for t in doc["input_traces"]} - {d})
    if kind == "skew_report":
        for dom, phs in doc.get("domains", {}).items():
            for ph, d in phs.items():
                for frac in SKEW_FRACS:
                    key = f"top{frac}"
                    try:
                        pls = [{"layer": r["layer"], "n": r[f"{key}_n"], "in_sample": r[f"{key}_in_sample"],
                                "heldout": r[f"{key}_heldout"], "null": r[f"{key}_null"], "chance": r[f"{key}_chance"],
                                "gini": r["gini"], "never_selected": r["never_selected"]} for r in d["per_layer"]]
                    except KeyError:
                        continue  # no even/odd split in this phase: no held-out number, so no row
                    out.append({"metric": M_SKEW[frac], "subject": {"domain": dom, "phase": ph, "window_rule": "all", "calibration_domains": []},
                                "payload": {"frac": frac, "per_layer": pls, "rows": d["summary"]["rows"], "windows_in_analysis": d["summary"]["windows"],
                                            "selections": sum(r["selections"] for r in d["per_layer"]),
                                            "in_sample_mean": _mean(x["in_sample"] for x in pls), "null_mean": _mean(x["null"] for x in pls),
                                            "chance_mean": _mean(x["chance"] for x in pls)}})
    elif kind == "residency_curve":
        ks = sorted(set(doc.get("ks", [])) | set(doc.get("ks_same_fraction_of_pool", [])))
        for bph, rec in doc.get("curves", {}).items():
            dom, ph = bph.split("/")
            for key, hs in rec["learned_on"].items():
                a = key if key in doc_domains(doc) else key.split("_even->")[0].split("(")[0]
                for k in ks:
                    if str(k) not in hs or str(k) not in rec["chance"] or str(k) not in rec["oracle_in_sample"]:
                        continue
                    sub = {"domain": dom, "phase": ph, "window_rule": "odd" if (a == dom and ph == "prefill") else "all",
                           "calibration_domains": [] if a == dom else [a]}
                    pl = {"k": k, "h": hs[str(k)], "chance": rec["chance"][str(k)], "oracle_in_sample": rec["oracle_in_sample"][str(k)],
                          "selections": rec["selections"], "learned_on": a, "learned_on_key": key}
                    if a != dom:
                        pl["calibration_corpus_sha256"] = next((t["corpus_sha256"] for t in doc["input_traces"] if t["domain"] == a), None)
                    out.append({"metric": "moe_residency_hit_rate", "subject": sub, "payload": pl})
    elif kind == "placement_replay":
        dom, calib = doc["domain"], doc["calib"]
        for cfg, res in doc.get("configs", {}).items():
            arms, dec = res["arms"], res["decision"]
            table = {a: v["max_over_mean"] for a, v in arms.items()}
            picks = ["contiguous", dec["best_practical"], dec["best_idealized_dispatch"], dec["best_bound"]]
            for arm in dict.fromkeys(picks):
                roles = [r for r in ("best_practical", "best_idealized_dispatch", "best_bound") if dec[r] == arm]
                if arm == "contiguous":
                    roles = ["baseline"] + roles
                anchor = "null_random" if arm == "contiguous" else "contiguous"
                sub = {"domain": dom, "phase": res["phase"], "window_rule": "all" if res["phase"] == "decode" else "mod4eq3",
                       "calibration_domains": doms(dom) if calib == "cross" else []}
                out.append({"metric": "moe_placement_max_over_mean", "subject": sub, "payload": {
                    "calib": calib, "config": cfg, "bins": res["bins"], "T": res["T"], "steps": res["steps"],
                    "per_step_arm_steps": res["per_step_arm_steps"], "units_per_step": res["units_per_step"], "redundant_copies_per_layer": res["R1"],
                    "arm": arm, "roles": roles, "ci95": arms[arm].get("ci95"), "anchor_arm": anchor, "arms_table": table, "decision": dec}})
    elif kind == "locality_report":
        lw_cap = None
        for dom, d in doc.get("domains", {}).items():
            lw_cap = d.get("lru_windows")
            for ph in ("prefill", "decode"):
                pls = [{"layer": x["layer"], "ir_mean": x[ph]["ir_mean"], "chance": x["chance"], "pairs": x[ph]["pairs"]} for x in d["ir"] if ph in x]
                if pls:
                    out.append({"metric": "moe_ir_t_mean", "part": "ir", "subject": {"domain": dom, "phase": ph, "window_rule": "all", "calibration_domains": []},
                                "payload": {"per_layer": pls, "chance_mean": _mean(x["chance"] for x in pls),
                                            "ratio_to_chance_mean": _mean(x["ir_mean"] for x in pls) / _mean(x["chance"] for x in pls)}})
                sizes = sorted({int(k) for v in d["lru"].values() if ph in v for k in v[ph]["hit_rate"]})
                for k in sizes:
                    lp = [{"layer": int(l), "hit_rate": v[ph]["hit_rate"][str(k)], "uniform_chance": v[ph]["uniform_chance_hit_rate"][str(k)],
                           "selections": v[ph]["selections"]} for l, v in d["lru"].items() if ph in v]
                    out.append({"metric": "moe_lru_hit_rate", "part": "lru", "subject": {"domain": dom, "phase": ph, "window_rule": "first", "calibration_domains": []},
                                "payload": {"k": k, "per_layer": sorted(lp, key=lambda x: x["layer"]), "lru_windows": d["lru_windows"],
                                            "uniform_chance_mean": _mean(x["uniform_chance"] for x in lp)}})
            if d.get("coact"):
                cp = [{"layer": x["layer"], "excess_fraction": x["excess_fraction"], "noise": x["excess_fraction_noise"], "tokens": x["tokens"]} for x in d["coact"]]
                out.append({"metric": "moe_coactivation_excess_fraction", "part": "coact", "subject": {"domain": dom, "phase": "all", "window_rule": "all", "calibration_domains": []},
                            "payload": {"per_layer": cp, "tokens": cp[0]["tokens"], "noise_mean": _mean(x["noise"] for x in cp)}})
    return out


def doc_domains(doc: dict) -> set:
    return {t["domain"] for t in doc["input_traces"]}


def _traces_for(doc: dict, spec: dict) -> list[dict]:
    keep = {spec["subject"]["domain"], *spec["subject"]["calibration_domains"]}
    return [t for t in doc["input_traces"] if t["domain"] in keep]


def _stamped_docs(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"{path.name}: analysis unreadable: {exc}") from exc
    docs = data if isinstance(data, list) else [data]
    out = []
    for d in docs:
        if not isinstance(d, dict) or "content_sha256" not in d or "input_traces" not in d:
            raise CaptureError(f"{path.name}: no content_sha256 / input_traces (an analysis written before the provenance emit; "
                               "nothing is back-filled, re-run the analysis to produce a row)")
        if d.get("provenance_schema") != PROVENANCE_SCHEMA or d.get("analysis_kind") not in KINDS:
            raise CaptureError(f"{path.name}: not a {PROVENANCE_SCHEMA} analysis of a known kind")
        if d["content_sha256"] != content_sha256(d):
            raise CaptureError(f"{path.name}: content_sha256 does not bind the document (edited after emit)")
        out.append(d)
    if not out:
        raise CaptureError(f"{path.name}: empty analysis")
    return out


def plan_rows(paths: Iterable[Path], *, producer: str | None = None, emitted_at: str | None = None) -> dict:
    """Project every stamped analysis; legacy files are SKIPPED by name, gated domains are skipped or refused. Returns
    {rows, skipped, refused}."""
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict] = []
    skipped: list[dict] = []
    refused: list[dict] = []
    for path in paths:
        try:
            docs = _stamped_docs(path)
        except CaptureError as exc:
            skipped.append({"file": str(path), "reason": str(exc)})
            continue
        digest = ns.file_sha256(path)
        for doc in docs:
            kind = doc["analysis_kind"]
            for spec in _specs(doc):
                traces = _traces_for(doc, spec)
                tp = trace_problems(traces)
                label = f"{path.name}:{spec['subject']['domain']}:{spec['metric']}"
                if any(x.startswith(HAZARD) for x in tp):
                    refused.append({"unit": label, "reason": next(x for x in tp if x.startswith(HAZARD))})
                    continue
                if tp:
                    skipped.append({"file": label, "reason": tp[0]})
                    continue
                unit = METRICS[spec["metric"]]
                row = {"schema": CAPTURE_SCHEMA, "run_id": f"moe-routing:{kind}:{doc['content_sha256'][:16]}",
                       "producer": producer or f"moe_routing/{kind}.py", "emitted_at": when, "date": when,
                       "metric": spec["metric"], "value": None, "unit": unit[1], "metric_direction": unit[2],
                       "category": "BASELINE", "claim": "", "protocol_id": "", "reps": None, "reps_basis": "",
                       "results_path": str(path), "results_sha256": digest,
                       "extra": {"kind": kind, "analysis": {"kind": kind, "content_sha256": doc["content_sha256"], "file": path.name},
                                 "subject": spec["subject"], "payload": spec["payload"], "input_traces": traces, "scope": None,
                                 **({"part": spec["part"]} if "part" in spec else {})}}
                pl = spec["payload"]
                row["value"] = {  # the same derivation the reader re-checks
                    "moe_residency_hit_rate": lambda: pl["h"], "moe_placement_max_over_mean": lambda: pl["arms_table"][pl["arm"]],
                    "moe_ir_t_mean": lambda: _mean(x["ir_mean"] for x in pl["per_layer"]),
                    "moe_lru_hit_rate": lambda: _mean(x["hit_rate"] for x in pl["per_layer"]),
                    "moe_coactivation_excess_fraction": lambda: _mean(x["excess_fraction"] for x in pl["per_layer"]),
                    **{m: (lambda: _mean(x["heldout"] for x in pl["per_layer"])) for m in M_SKEW.values()}}[spec["metric"]]()
                scope, why = expected_scope(row)
                if why:
                    skipped.append({"file": label, "reason": "; ".join(why)})
                    continue
                if kind == "skew_report" and pl["windows_in_analysis"] != scope["n_windows"]:
                    skipped.append({"file": label, "reason": f"analysis windows {pl['windows_in_analysis']} != windows derived from the "
                                                              f"recorded shards {scope['n_windows']}"})
                    continue
                row["extra"]["scope"] = scope
                basis = "steps" if spec["metric"] == "moe_placement_max_over_mean" else "windows"
                row["reps"], row["reps_basis"] = (scope["n"] if basis == "steps" else scope["n_windows"]), f"scored:{basis}"
                extra_txt = {"moe_residency_hit_rate": f"k={pl.get('k')} experts/layer, learned on {pl.get('learned_on')}",
                             "moe_placement_max_over_mean": f"{pl.get('config')} arm {pl.get('arm')} ({','.join(pl.get('roles', []))})",
                             "moe_lru_hit_rate": f"LRU k={pl.get('k')}"}.get(spec["metric"], "descriptive statistic")
                row["claim"] = _claim(spec["metric"], row["value"], scope, extra_txt)
                row["measurement_id"] = "moerout_" + ns.content_hash(identity_parts(row))[:24]
                try:
                    ns.seal(row)
                except CaptureError as exc:  # a non-finite number somewhere in the payload: this statistic has no row
                    skipped.append({"file": label, "reason": str(exc)})
                    continue
                bad = row_problems(row)
                if any(x.startswith(HAZARD) for x in bad):  # e.g. perfectly flat counts / sub-chance reuse found in the numbers
                    refused.append({"unit": label, "reason": next(x for x in bad if x.startswith(HAZARD))})
                    continue
                if bad:
                    raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
                rows.append(row)
    return {"rows": rows, "skipped": skipped, "refused": refused}


def discover_analyses(directory: str | Path) -> list[Path]:
    d = Path(directory)
    return [d / n for n in ANALYSIS_FILES if (d / n).is_file()]


def write_belief_measurements(out_dir: str | Path, *, producer: str | None = None, results_paths: Iterable[str | Path] | None = None,
                              emitted_at: str | None = None) -> Path:
    """Project the stamped analyses in ``out_dir`` (or ``results_paths``) into ``<out_dir>/moe_routing.beliefs.jsonl``.
    Raises CaptureError when nothing projects (all legacy / unverified / refused) or when a stride-hazard was refused."""
    paths = [Path(p) for p in results_paths] if results_paths else discover_analyses(out_dir)
    if not paths:
        raise CaptureError(f"no analysis JSON found in {out_dir}")
    plan = plan_rows(paths, producer=producer, emitted_at=emitted_at)
    for s in plan["skipped"]:
        print(f"moe_routing: skipped {s['file']}: {s['reason'][:200]}", file=sys.stderr)
    if plan["refused"]:
        raise CaptureError("stride-hazard refused fail-closed: " + "; ".join(f"{r['unit']}: {r['reason']}" for r in plan["refused"][:5]))
    if not plan["rows"]:
        raise CaptureError("no row projected: " + ("; ".join(s["reason"][:120] for s in plan["skipped"][:3]) or "empty analyses"))
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, plan["rows"])


# --------------------------------------------------------------------------------------------- reader / projection
def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    """Strict reader. A row carrying a stride-hazard signature is REFUSED by name (fail-closed, ProjectionError); a sidecar
    with any row that does not re-derive, or that rests on unverified / quarantined / guard-less inputs, is void (no rows)."""
    path = Path(sidecar_path)
    if path.is_file():
        try:
            body = path.read_text()
        except OSError:
            body = ""
        for line in body.splitlines():
            try:
                row = json.loads(line) if line.strip() else None
            except ValueError:
                continue
            hz = [x for x in row_problems(row) if x.startswith(HAZARD)] if isinstance(row, dict) else []
            if hz:
                raise ProjectionError("MoE routing row refused fail-closed: " + "; ".join(hz))
    return ns.native_rows(path, row_problems)


def _anchor(row: dict) -> tuple[float, float] | None:
    e, pl = row["extra"], row["extra"]["payload"]
    m = row["metric"]
    if m in M_SKEW.values():
        a = pl["null_mean"]
    elif m == "moe_residency_hit_rate":
        a = pl["chance"]
    elif m == "moe_placement_max_over_mean":
        a = pl["arms_table"][pl["anchor_arm"]]
    elif m == "moe_ir_t_mean":
        a = pl["chance_mean"]
    elif m == "moe_lru_hit_rate":
        a = pl["uniform_chance_mean"]
    else:
        a = pl["noise_mean"]
    return (a, (row["value"] - a) / a) if ns.finite(a) and a > 0 else None


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("MoE routing native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError(("MoE routing row refused fail-closed: " if any(x.startswith(HAZARD) for x in problems)
                               else "MoE routing row is not a producer-authored capture: ") + "; ".join(problems))
    e, sc, pl = row["extra"], row["extra"]["scope"], row["extra"]["payload"]
    locator = f"moe-routing:{e['kind']}:{sc['domain']}:{sc['phase']}:{row['metric']}:{e['analysis']['content_sha256'][:12]}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    obs: dict = {}
    anc = _anchor(row)
    if anc:
        obs["anchor_value"], obs["effect_rel"] = anc
    knobs: dict = {"arch": sc["arch"], "domain": sc["domain"], "corpus_sha256": sc["corpus_sha256"], "phase": sc["phase"],
                   "chunk_size": sc["chunk_size"], "calibration_source": sc["calibration_source"], "n": sc["n"],
                   "n_unit": sc["n_unit"], "n_windows": sc["n_windows"], "guard_checks": sc["guard_checks"],
                   "guard_sub_chance_checks": sc["guard_sub_chance_checks"]}
    for k in ("k", "bins", "T", "arm", "frac", "config"):
        if k in pl:
            knobs[k] = pl[k]
    if sc["phase"] == "decode":
        knobs["decode_rows"] = sc["decode_rows"]
        if _posint(sc.get("decode_cap_per_window")):
            knobs["decode_cap_per_window"] = sc["decode_cap_per_window"]
        if isinstance(sc.get("eos_stopped"), bool):
            knobs["eos_stopped"] = sc["eos_stopped"]
    app = {"scope_basis": "native", "model_file": sc["model_file"], "kernel": f"llama-moe-trace {sc['build_info']}",
           "surface": f"moe-routing:{e['kind']}", "op": row["metric"], "recipe": sc["calibration_source"],
           "shape": f"{sc['layers']}L x {sc['n_experts']}E top-{sc['top_k']}", "knob_family": "moe_routing", "knobs": knobs}
    m = _SHA_TAIL.search(sc["build_info"])
    if m:
        app["build_sha"] = m.group(1)
    return dataclasses.replace(tup, observation=obs, applicability=app)


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the MoE-routing belief sidecar from stamped RT-1 analysis JSONs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--analysis-dir", required=True, help="directory holding skew_report.json, residency_curve.json, "
                   "placement_replay_{same,cross}.json, locality_report.json; the sidecar is written next to them")
    w.add_argument("--results", action="append", help="explicit analysis JSON (repeatable); default = the known names in the dir")
    w.add_argument("--producer", default=None)
    a = ap.parse_args(argv)
    paths = [Path(p) for p in a.results] if a.results else discover_analyses(a.analysis_dir)
    plan = plan_rows(paths, producer=a.producer)
    out: dict = {"skipped": plan["skipped"], "refused": plan["refused"]}
    if plan["rows"] and not plan["refused"]:
        path = ns.write_rows_atomic(Path(a.analysis_dir) / SIDECAR_NAME, plan["rows"])
        out.update(sidecar=str(path), rows=len(native_rows(path)))
    print(json.dumps(out, indent=1))
    return 0 if out.get("rows") and not plan["refused"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
