"""VB-CLBENCH-CACHE-WIRE: CL-Bench prefix-cache hit report -> measurement OBSERVATIONS.

Source: the ``cache_hit_report.json`` (schema ``epyc.clbench_cache_hit.v1``) that research
``scripts/benchmark/clbench_epyc_local/cache_hit_report.py --out`` writes. Rows per run (the report is one run):

* ``clbench_cache_hit_ratio_prompt_prefix`` (basis ``prompt_prefix``, the gated basis since research ``08ace05fd``) =
  prompt_prefix_cached_tokens / prompt_prefix_tokens, higher_better;
* ``clbench_cache_hit_ratio_reusable`` (basis ``cme5``: reusable counts the previous call's OUTPUT) =
  cached_tokens / reusable_tokens, higher_better. The two bases are DIFFERENT claims (generated tokens are not
  reusable on a hybrid/recurrent model, so the cme5 ratio cannot reach 0.95 there);
* the three ``missed_split`` buckets as separate token-count rows (``generated_tokens_unreusable``,
  ``history_rewind``, ``prompt_prefix_lost``), lower_better.

The strict reader re-derives every value from the counts recorded in each row (ratios within the report's 4-decimal
rounding; reusable - cached == sum of the split; reusable - prompt_prefix_tokens == generated_tokens_unreusable;
prompt_prefix_tokens - prompt_prefix_cached_tokens == history_rewind + prompt_prefix_lost) and re-hashes the report.

Doctrine: PROJECTION ONLY, ``claim_tuple.grade()`` decides. ``protocol_id`` is always empty (no CME protocol is
codified under ``measurement/protocols/``), so the ladder caps these tuples. A report written before research
``08ace05fd`` has no ``basis`` / ``missed_split``: the writer raises CaptureError and nothing is back-filled. An
INVALID report (``problems`` non-empty / verdict INVALID) yields no row.
"""

from __future__ import annotations

import argparse
import dataclasses
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

REPORT_SCHEMA = "epyc.clbench_cache_hit.v1"
CAPTURE_SCHEMA = "epyc.vidya.clbench_cache_hit.v1"
SIDECAR_NAME = "clbench_cache_hit.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.clbench_cache_hit/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "clbench-cache-hit"
BASES = ("prompt_prefix", "cme5")
BUCKETS = ("generated_tokens_unreusable", "history_rewind", "prompt_prefix_lost")
M_PP = "clbench_cache_hit_ratio_prompt_prefix"
M_RU = "clbench_cache_hit_ratio_reusable"
M_SPLIT = {b: f"clbench_cache_miss_{b}_tokens" for b in BUCKETS}
METRICS = frozenset({M_PP, M_RU, *M_SPLIT.values()})
ROUND_TOL = 5e-5 + 1e-9  # the report rounds ratios to 4 decimals
COUNT_KEYS = ("reusable_tokens", "cached_tokens", "prompt_prefix_tokens", "prompt_prefix_cached_tokens")
IDENTITY_TEXT = ("served_model", "recipe", "kernel_build")
IDENTITY_INT = ("np", "ctx", "slots")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _int(x: Any) -> bool:
    return ns.nonneg_int(x)


def counts_problems(c: Any) -> list[str]:
    """The report's own arithmetic. Shared by the writer (on the report) and the reader (on each row)."""
    if not isinstance(c, dict):
        return ["counts must be an object"]
    p: list[str] = []
    if not all(_int(c.get(k)) for k in COUNT_KEYS):
        return ["counts must carry non-negative integer " + "/".join(COUNT_KEYS)]
    ms = c.get("missed_split")
    if not isinstance(ms, dict) or set(ms) != set(BUCKETS) or not all(_int(ms[b]) for b in BUCKETS):
        return ["missed_split must carry exactly " + "/".join(BUCKETS) + " as non-negative integers"]
    ru, ca, pp, pc = (c[k] for k in COUNT_KEYS)
    if not (ca <= pp <= ru and pc <= pp and pc <= ca):
        p.append("counts must satisfy cached <= prompt_prefix_tokens <= reusable and prompt_prefix_cached <= cached")
    if ru - ca != sum(ms.values()):
        p.append("reusable - cached must equal the sum of the missed_split buckets")
    if ru - pp != ms["generated_tokens_unreusable"]:
        p.append("reusable - prompt_prefix_tokens must equal generated_tokens_unreusable")
    if pp - pc != ms["history_rewind"] + ms["prompt_prefix_lost"]:
        p.append("prompt_prefix_tokens - prompt_prefix_cached_tokens must equal history_rewind + prompt_prefix_lost")
    return p


def _ratio_problems(counts: Mapping[str, Any], pp_val: Any, ru_val: Any) -> list[str]:
    p: list[str] = []
    for name, got, num, den in (("hit_ratio_prompt_prefix", pp_val, counts["prompt_prefix_cached_tokens"],
                                 counts["prompt_prefix_tokens"]),
                                ("hit_ratio_reusable", ru_val, counts["cached_tokens"], counts["reusable_tokens"])):
        if den <= 0:
            p.append(f"{name}: zero denominator has no ratio")
        elif not ns.finite(got) or abs(got - num / den) > ROUND_TOL:
            p.append(f"{name} must re-derive from its counts within the report's 4-decimal rounding")
    return p


def _identity_problems(ident: Any) -> list[str]:
    if not isinstance(ident, dict):
        return ["identity must be an object"]
    p = [f"identity.{k} must be a non-empty string" for k in IDENTITY_TEXT if not ns.text(ident.get(k))]
    p += [f"identity.{k} must be a positive integer" for k in IDENTITY_INT
          if type(ident.get(k)) is not int or ident[k] <= 0]
    if not _SHA40.match(str(ident.get("research_sha", ""))):
        p.append("identity.research_sha must be the 40-hex git SHA of the producing research checkout")
    if ident.get("basis") not in BASES:
        p.append(f"identity.basis must be one of {BASES}")
    return p


def row_problems(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: no CME protocol is codified")
    if row.get("metric") not in METRICS:
        return p + [f"metric must be one of {sorted(METRICS)}"] + ns.self_hash_problems(row)
    p += _identity_problems(e.get("identity"))
    counts = e.get("counts")
    cp = counts_problems(counts)
    p += cp
    if not ns.text(e.get("report_verdict")) or e.get("report_verdict") == "INVALID":
        p.append("extra.report_verdict must be the report's own non-INVALID word")
    if not cp and isinstance(e.get("identity"), dict):
        m = row["metric"]
        if m == M_PP:
            exp_basis, num, den = "prompt_prefix", counts["prompt_prefix_cached_tokens"], counts["prompt_prefix_tokens"]
        elif m == M_RU:
            exp_basis, num, den = "cme5", counts["cached_tokens"], counts["reusable_tokens"]
        else:
            exp_basis = None
        if exp_basis is not None:
            if e.get("metric_basis") != exp_basis:
                p.append(f"extra.metric_basis must be {exp_basis!r} for {m}")
            if den <= 0 or not ns.finite(row.get("value")) or abs(row["value"] - num / den) > ROUND_TOL:
                p.append("value must re-derive from the recorded counts within the report's 4-decimal rounding")
            if row.get("metric_direction") != "higher_better":
                p.append("ratio rows are higher_better")
        else:
            b = next(k for k, v in M_SPLIT.items() if v == m)
            if e.get("metric_basis") != b:
                p.append(f"extra.metric_basis must be {b!r} for {m}")
            if row.get("value") != counts["missed_split"][b]:
                p.append("value must equal the recorded missed_split bucket")
            if row.get("metric_direction") != "lower_better":
                p.append("split rows are lower_better")
        if not (isinstance(e.get("per_run"), list) and e["per_run"] and row.get("reps") == len(e["per_run"])):
            p.append("reps must equal the number of recorded per-run entries")
        if e.get("gated_basis") not in BASES:
            p.append("extra.gated_basis must be the report's basis")
        elif e["gated_basis"] != e["identity"].get("basis"):
            p.append("extra.identity.basis must restate the report's basis")
        if not p:
            p += ns.check_identity(row, {"run_id": row["run_id"], "metric": row["metric"],
                                         "results": row["results_sha256"]}, "clbenchcache")
    return p + ns.self_hash_problems(row)


validate_row = row_problems


def _load_report(path: Path) -> dict:
    try:
        rep = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"cache_hit_report unreadable: {exc}") from exc
    if not isinstance(rep, dict) or rep.get("schema") != REPORT_SCHEMA:
        raise CaptureError(f"report schema must be {REPORT_SCHEMA!r}")
    if rep.get("basis") not in BASES or "missed_split" not in rep:
        raise CaptureError("report lacks basis / missed_split (written before research 08ace05fd): "
                           "a pre-fix record is never back-filled")
    if rep.get("problems") or rep.get("verdict") not in ("PASS", "MISS"):
        raise CaptureError(f"report is not a complete measurement (verdict={rep.get('verdict')!r}, "
                           f"problems={rep.get('problems')!r})")
    counts = {k: rep.get(k) for k in COUNT_KEYS}
    counts["missed_split"] = rep.get("missed_split")
    bad = counts_problems(counts) + (_ratio_problems(counts, rep.get("hit_ratio_prompt_prefix"),
                                                     rep.get("hit_ratio_reusable"))
                                     if not counts_problems(counts) else [])
    if bad:
        raise CaptureError("report is internally inconsistent: " + "; ".join(bad))
    runs = rep.get("per_run")
    if not (isinstance(runs, list) and runs and all(isinstance(r, dict) for r in runs)):
        raise CaptureError("report must carry per_run entries")
    return rep


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str, report_path: str | Path,
                              identity: Mapping[str, Any], emitted_at: str | None = None) -> Path:
    """``identity``: served_model, recipe, np, ctx, slots, kernel_build, research_sha, basis (must restate the report's)."""
    raw = Path(report_path)
    rep = _load_report(raw)
    ident = dict(identity or {})
    bad = _identity_problems(ident)
    if bad:
        raise CaptureError("; ".join(bad))
    if ident["basis"] != rep["basis"]:
        raise CaptureError(f"identity.basis {ident['basis']!r} disagrees with the report's {rep['basis']!r}")
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    counts = {k: rep[k] for k in COUNT_KEYS}
    counts["missed_split"] = dict(rep["missed_split"])
    who = (f"{ident['served_model']} recipe={ident['recipe']} np={ident['np']} ctx={ident['ctx']} "
           f"slots={ident['slots']} kernel={ident['kernel_build']}")
    specs = [
        (M_PP, "prompt_prefix", rep["hit_ratio_prompt_prefix"], "fraction of previous-call input tokens served from cache",
         "higher_better",
         f"CL-Bench prefix-cache hit, prompt_prefix basis: {rep['hit_ratio_prompt_prefix']:.4f} "
         f"({counts['prompt_prefix_cached_tokens']}/{counts['prompt_prefix_tokens']} tokens) on {who}"),
        (M_RU, "cme5", rep["hit_ratio_reusable"], "fraction of CME-5 reusable tokens (prev input + prev output) served from cache",
         "higher_better",
         f"CL-Bench prefix-cache hit, cme5 basis (generated tokens counted reusable): {rep['hit_ratio_reusable']:.4f} "
         f"({counts['cached_tokens']}/{counts['reusable_tokens']} tokens) on {who}; a different claim from the "
         f"prompt_prefix ratio"),
    ]
    for b in BUCKETS:
        n = counts["missed_split"][b]
        specs.append((M_SPLIT[b], b, n, "tokens", "lower_better",
                      f"CL-Bench missed cache tokens, bucket {b}: {n} of {counts['reusable_tokens'] - counts['cached_tokens']} "
                      f"missed reusable tokens on {who}"))
    rows = []
    for metric, mbasis, value, unit, direction, claim in specs:
        row = {"schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when, "date": when[:10],
               "metric": metric, "value": value, "unit": unit, "metric_direction": direction, "category": "BASELINE",
               "claim": claim, "protocol_id": "", "reps": len(rep["per_run"]),
               "reps_basis": "CL-Bench runs (trace files) pooled in the report", "results_path": str(raw),
               "results_sha256": digest,
               "extra": {"identity": ident, "metric_basis": mbasis, "gated_basis": rep["basis"], "counts": counts,
                         "report_verdict": rep["verdict"], "min_hit": rep.get("min_hit"), "per_run": rep["per_run"],
                         "raw_cached_over_input": rep.get("raw_cached_over_input")}}
        row["measurement_id"] = "clbenchcache_" + ns.content_hash(
            {"run_id": run_id, "metric": metric, "results": digest})[:24]
        ns.seal(row)
        problems = row_problems(row)
        if problems:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(problems))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, row_problems)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("CL-Bench cache-hit native row must retain the producer row")
    row = native["row"]
    problems = row_problems(row)
    if problems:
        raise ProjectionError("CL-Bench cache-hit row is not a producer-authored capture: " + "; ".join(problems))
    e, ident = row["extra"], row["extra"]["identity"]
    locator = f"clbench-cache-hit:{row['run_id']}:{row['metric']}:{row['results_path']}"
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator, sidecar_path=native.get("sidecar_path", ""))
    return dataclasses.replace(
        tup, observation={"outcome_native": str(e["report_verdict"])[:120]},
        applicability={"scope_basis": "native", "model_file": ident["served_model"], "recipe": ident["recipe"],
                       "np": ident["np"], "context_tokens": ident["ctx"], "kernel": ident["kernel_build"],
                       "knob_family": "prefix_cache", "knobs": {"slots": ident["slots"]}})


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="write the CL-Bench cache-hit belief sidecar from cache_hit_report.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("--report", required=True)
    w.add_argument("--out-dir", required=True)
    w.add_argument("--run-id", required=True)
    w.add_argument("--identity-json", required=True, help="JSON object: served_model, recipe, np, ctx, slots, "
                   "kernel_build, research_sha, basis")
    w.add_argument("--producer", default="cache_hit_report.py")
    a = ap.parse_args(argv)
    try:
        path = write_belief_measurements(a.out_dir, run_id=a.run_id, producer=a.producer, report_path=a.report,
                                         identity=json.loads(a.identity_json))
    except (CaptureError, ValueError) as exc:
        print(f"belief sidecar NOT written: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"sidecar": str(path), "rows": len(native_rows(path))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
