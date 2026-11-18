"""Orchestrator tool-picker event log -> strict reader -> shared grade (VB-TOOL-SELECTOR-WIRE).

Source: ``logs/tool_selector_events.jsonl`` written by orchestrator
``src/prompt_builders/tool_picker.py`` (``log_event`` prepends ``ts``; row types ``selection``,
``outcome``, ``shadow``). Only an explicitly named file is read.

What is projected, per stratum (role, variant, mode, k_min, k_max, tool-count bucket):

* ``tool_picker_proxy_recall`` -- call-weighted ``1 - sum(called_not_selected) / sum(called)`` over the
  outcome rows joined to a selection row by ``request_id``. It is a PROXY: a tool the model called that
  was neither sent nor already in history. A call the model never made because the tool was missing is
  invisible, so true recall is not measured. Requests with no call carry no recall information and are
  excluded from the denominator (the producer's per-row formula returns a vacuous 1.0 for them);
  ``mode == "full"`` sends every tool so recall there is vacuous and is not emitted.
* ``tool_picker_elapsed_ms_p95`` -- nearest-rank p95 of ``elapsed_ms`` over the selection rows.

Era and config: selection rows written since orchestrator ``a2790c82`` carry ``picker_version``, ``delta``,
``family_cap`` and ``full_list_max``; they are read into the stratum key (a version or config change never
pools). Rows from an older producer lack them and read as ``unknown`` -- never invented. An outcome with no selection row
(role unknown) is counted and excluded; a selection with no outcome is counted and is unknown, never a
miss. Shadow rows are tallied in ``extra`` only (they are logged beside the applied pick, never applied).
The log is unsealed producer output: category CANDIDATE, protocol_id empty, ``ClaimTuple.grade()`` is
the only grader.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = "tool-selector-events"
ADAPTER_ID = "vidya.adapters.tool_selector_events/v1"
AUTHORITY = "measurement"
PLANNER_CONSUMER = "orchestrator.tool_picker"
RECALL = "tool_picker_proxy_recall"
LATENCY = "tool_picker_elapsed_ms_p95"
MAX_BYTES = 64 * 1024 * 1024
_SEL = ("request_id", "conversation", "variant", "role", "mode", "rung", "n_tools_in", "n_tools_out", "k_min",
        "k_max", "k_effective", "selected", "sent", "scores_top16", "elapsed_ms")
_OUT = ("request_id", "conversation", "called", "called_not_selected", "proxy_recall")
_CFG = ("delta", "family_cap", "full_list_max")
_MODES = {"narrow", "full", "core_search"}


def _bad(msg: str) -> None:
    raise ProjectionError("tool-selector-events: " + msg)


def _num(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _strs(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def _bucket(n: int) -> str:
    return "le16" if n <= 16 else "17to40" if n <= 40 else "gt40"


def _pairs(items):
    out: dict = {}
    for k, v in items:
        if k in out:
            _bad("duplicate JSON key " + k)
        out[k] = v
    return out


def _read(path: Path) -> tuple[bytes, list[dict]]:
    if not path.is_file():
        _bad("not a file")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        _bad("file exceeds bounded envelope")
    lines = raw.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    elif lines:
        lines.pop()                       # unterminated final line: a torn concurrent append, never a row
    rows = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_pairs, parse_constant=lambda x: _bad("nonfinite constant"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ProjectionError(f"tool-selector-events: line {i} is not JSON") from exc
        if not isinstance(row, dict) or not _num(row.get("ts")) or not isinstance(row.get("type"), str):
            _bad(f"line {i} lacks ts/type")
        rows.append(row)
    return raw, rows


def _check_selection(r: dict) -> None:
    if any(k not in r for k in _SEL):
        _bad("selection row missing fields")
    if not all(isinstance(r[k], str) and r[k] for k in ("request_id", "role", "variant", "rung")) or r["mode"] not in _MODES:
        _bad("selection identity/mode malformed")
    if not all(type(r[k]) is int and r[k] >= 0 for k in ("n_tools_in", "n_tools_out", "k_min", "k_max", "k_effective")):
        _bad("selection counts malformed")
    if "picker_version" in r and not (isinstance(r["picker_version"], str) and r["picker_version"]):
        _bad("selection picker_version malformed")
    if any(k in r and not (_num(r[k]) and r[k] >= 0) for k in _CFG):
        _bad("selection config fields malformed")
    if not _num(r["elapsed_ms"]) or r["elapsed_ms"] < 0 or not _strs(r["selected"]) or not _strs(r["sent"]):
        _bad("selection latency/sets malformed")
    if not isinstance(r["scores_top16"], list) or not all(
            isinstance(p, list) and len(p) == 2 and isinstance(p[0], str) and _num(p[1]) for p in r["scores_top16"]):
        _bad("selection scores malformed")


def _check_outcome(r: dict) -> None:
    if any(k not in r for k in _OUT) or not isinstance(r["request_id"], str) or not r["request_id"]:
        _bad("outcome row missing fields")
    if not _strs(r["called"]) or not _strs(r["called_not_selected"]) or not _num(r["proxy_recall"]):
        _bad("outcome fields malformed")
    called, cns = set(r["called"]), set(r["called_not_selected"])
    if not cns <= called:
        _bad("called_not_selected is not a subset of called")
    if abs(r["proxy_recall"] - (1.0 - len(cns) / max(1, len(called)))) > 1e-9:
        _bad("proxy_recall disagrees with its own called/called_not_selected")


def _p95(xs: list[float]) -> float:
    s = sorted(xs)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def native_rows(path: str | Path) -> tuple[dict, ...]:
    path = Path(path).resolve()
    raw, rows = _read(path)
    sel: dict[str, dict] = {}
    outs: dict[str, dict] = {}
    shadow = {"rows": 0, "errors": 0, "fallbacks": 0}
    unknown = 0
    for r in rows:
        t = r["type"]
        if t == "selection":
            _check_selection(r)
            if r["request_id"] in sel:
                _bad("duplicate selection for request " + r["request_id"])
            sel[r["request_id"]] = r
        elif t == "outcome":
            _check_outcome(r)
            if r["request_id"] in outs:
                _bad("duplicate outcome for request " + r["request_id"])
            outs[r["request_id"]] = r
        elif t == "shadow":
            shadow["rows"] += 1
            shadow["errors"] += int("error" in r)
            shadow["fallbacks"] += int(bool(r.get("fallback")))
        else:
            unknown += 1
    orphans = sorted(set(outs) - set(sel))
    strata: dict[tuple, dict] = {}
    for rid, s in sel.items():
        key = (s["role"], s["variant"], s["mode"], s["k_min"], s["k_max"], _bucket(s["n_tools_in"]),
               s.get("picker_version", "unknown"), *(s.get(k, "unknown") for k in _CFG))
        st = strata.setdefault(key, {"lat": [], "calls": 0, "cns": 0, "recall_requests": 0, "selections": 0,
                                     "no_outcome": 0, "no_call": 0, "top1": [], "rungs": {}, "ts": [], "rids": []})
        st["selections"] += 1
        st["lat"].append(float(s["elapsed_ms"]))
        st["rungs"][s["rung"]] = st["rungs"].get(s["rung"], 0) + 1
        st["ts"].append(s["ts"])
        st["rids"].append(rid)
        if s["scores_top16"]:
            st["top1"].append(max(float(p[1]) for p in s["scores_top16"]))
        o = outs.get(rid)
        if o is None:
            st["no_outcome"] += 1
        elif not o["called"]:
            st["no_call"] += 1
        else:
            st["calls"] += len(set(o["called"]))
            st["cns"] += len(o["called_not_selected"])
            st["recall_requests"] += 1
            st["ts"].append(o["ts"])
    digest = hashlib.sha256(raw).hexdigest()
    out = []
    for key in sorted(strata):
        st = strata[key]
        role, variant, mode, kmin, kmax, bucket, pver, delta, fcap, flmax = key
        base = {"path": str(path), "sha256": digest,
                "stratum": {"role": role, "variant": variant, "mode": mode, "k_min": kmin, "k_max": kmax,
                            "tool_count_bucket": bucket, "picker_version": pver, "delta": delta,
                            "family_cap": fcap, "full_list_max": flmax},
                "counts": {"selections": st["selections"], "recall_requests": st["recall_requests"],
                           "calls": st["calls"], "called_not_selected": st["cns"],
                           "selections_without_outcome": st["no_outcome"], "outcomes_without_call": st["no_call"],
                           "orphan_outcomes_file": len(orphans), "shadow": dict(shadow), "unknown_row_types": unknown},
                "rungs": dict(sorted(st["rungs"].items())),
                "top1_score_mean": round(sum(st["top1"]) / len(st["top1"]), 4) if st["top1"] else None,
                "first_ts": min(st["ts"]), "last_ts": max(st["ts"]),
                "request_ids_sha256": hashlib.sha256("\n".join(sorted(st["rids"])).encode()).hexdigest()}
        if mode != "full" and st["recall_requests"]:
            out.append({**base, "metric": RECALL, "value": 1.0 - st["cns"] / st["calls"]})
        out.append({**base, "metric": LATENCY, "value": _p95(st["lat"])})
    return tuple(out)


def units(path: Path) -> list[Path]:
    return [path] if Path(path).is_file() else []


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or "path" not in native:
        _bad("native row malformed")
    if native not in native_rows(native["path"]):
        _bad("native row does not rederive from the log")
    s, c, metric, v = native["stratum"], native["counts"], native["metric"], native["value"]
    date = datetime.datetime.fromtimestamp(native["last_ts"], tz=datetime.timezone.utc).date().isoformat()
    scope = (f"role {s['role']}, variant {s['variant']}, mode {s['mode']}, k {s['k_min']}-{s['k_max']}, "
             f"tools-in bucket {s['tool_count_bucket']}, picker {s['picker_version']}, delta {s['delta']}, "
             f"family_cap {s['family_cap']}, full_list_max {s['full_list_max']}")
    if metric == RECALL:
        unit, direction, reps = "ratio", "higher_better", c["recall_requests"]
        basis = "requests with at least one tool call; denominator excludes no-call and unjoined requests"
        text = (f"Tool-picker PROXY recall {v:.4f} ({scope}): {c['called_not_selected']} of {c['calls']} called tools were "
                f"neither sent nor in history, over {reps} requests. Proxy only: a tool never called because it was "
                f"missing is invisible. {c['selections_without_outcome']} selections have no outcome (unknown, not misses).")
    else:
        unit, direction, reps = "ms", "lower_better", c["selections"]
        basis = "selection rows (one per picker invocation)"
        text = (f"Tool-picker selection latency p95 {v:.2f} ms ({scope}) over {reps} selections; "
                f"rungs {native['rungs']}.")
    mid = "tool-selector-events:" + hashlib.sha256(json.dumps(
        [s, metric, native["request_ids_sha256"], c["recall_requests"]], sort_keys=True).encode()).hexdigest()[:32]
    return ClaimTuple(
        measurement_id=mid, metric=metric, value=v, date=date, category="CANDIDATE", claim=text,
        metric_direction=direction, protocol_id="", reps=reps, reps_basis=basis, unit=unit,
        attestation_path=native["path"], attestation_sha256=native["sha256"],
        attestation_locator=f"{native['path']}#{metric}:{s['role']}:{s['variant']}:{s['mode']}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"consumer": PLANNER_CONSUMER, "role": s["role"]},
        observation={"outcome_native": f"{metric}={v:.4f}" if metric == RECALL else f"{metric}={v:.2f}"},
        extra={"adapter": ADAPTER_ID, "stratum": s, "counts": c, "rungs": native["rungs"],
               "top1_score_mean": native["top1_score_mean"], "first_ts": native["first_ts"], "last_ts": native["last_ts"],
               "picker_version": s["picker_version"],
               "unlogged_config": [k for k in _CFG if s[k] == "unknown"],
               "limitation": "unsealed producer log; proxy recall is not true recall; no promotion or default-on warrant"})


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "PLANNER_CONSUMER", "native_rows", "project", "units"]
