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
from adapters._argv_scope import flag, scope_from_argv  # noqa: E402
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


__all__ = ["ADAPTER_ID", "AUTHORITY", "COMPARISONS", "KNOB_FAMILY", "SOURCE_KIND", "native_rows", "project"]
