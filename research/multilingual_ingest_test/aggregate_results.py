#!/usr/bin/env python3
"""Aggregate KB-RAG eval + pairwise judge → acceptance-criteria outcome.

Per handoffs/active/internal-kb-rag.md § "Multilingual Ingest Quality-Gap"
acceptance criteria table. Reads thresholds from config.yaml. Emits a markdown
decision report.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as f:
        return yaml.safe_load(f)


def load_judge(judge_dir: Path) -> list[dict]:
    summary = judge_dir / "_summary.json"
    if summary.exists():
        return json.loads(summary.read_text())["results"]
    return [json.loads(f.read_text()) for f in sorted(judge_dir.glob("*.json"))
            if f.name != "_summary.json"]


def win_rate_by_stratum(results: list[dict], target_pipeline: str,
                        vs_pipeline: str) -> dict[str, dict]:
    """For each stratum, compute target_pipeline's win rate vs vs_pipeline."""
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "n": 0})
    for r in results:
        pa, pb = r["pa"], r["pb"]
        if {pa, pb} != {target_pipeline, vs_pipeline}:
            continue
        stratum = r.get("stratum") or "unknown"
        verdict = r.get("verdict_actual_winner")
        if verdict == target_pipeline:
            buckets[stratum]["wins"] += 1
        elif verdict == vs_pipeline:
            buckets[stratum]["losses"] += 1
        elif verdict == "TIE":
            buckets[stratum]["ties"] += 1
        buckets[stratum]["n"] += 1
    # Compute win-rate (excluding TIEs and unparseables from denominator)
    out: dict[str, dict] = {}
    for stratum, b in buckets.items():
        decisive = b["wins"] + b["losses"]
        rate = b["wins"] / decisive if decisive > 0 else 0.0
        out[stratum] = {**b, "win_rate_excl_ties": rate}
    return out


def apply_acceptance_criteria(kb_rag: dict, judge: list[dict], cfg: dict) -> dict:
    """Map results → outcome label per the handoff's acceptance criteria table."""
    th = cfg["thresholds"]
    pairwise_th = float(th["pairwise_win_rate_for_h1"])
    ndcg_th = float(th["ndcg5_lift_for_h1"])
    spec_margin = float(th["specialist_vs_decomposition_margin"])
    cn_en_floor = float(th["cn_en_regression_floor"])

    # Pairwise win rates per stratum
    b_vs_a = win_rate_by_stratum(judge, "B", "A")
    b_vs_c = win_rate_by_stratum(judge, "B", "C")
    c_vs_a = win_rate_by_stratum(judge, "C", "A")

    # NDCG lifts (aggregate, not per-stratum yet — TODO if relevance map is per-stratum)
    lifts = kb_rag.get("_lifts", {})
    b_minus_a_ndcg = lifts.get("B_minus_A_ndcg")
    b_minus_c_ndcg = lifts.get("B_minus_C_ndcg")

    # Identify strata where B wins decisively
    cn_en_b_winrate = b_vs_a.get("chinese_english_control", {}).get("win_rate_excl_ties")
    non_cn_en_strata_b_wins = [
        s for s, m in b_vs_a.items()
        if s != "chinese_english_control" and m.get("win_rate_excl_ties", 0.0) >= pairwise_th
    ]

    # Check if any non-CN-EN stratum has BOTH pairwise win AND NDCG lift
    # (the NDCG lift here is aggregate; if per-stratum NDCG is available, refine)
    h1_pairwise = bool(non_cn_en_strata_b_wins)
    h1_ndcg = bool(b_minus_a_ndcg is not None and b_minus_a_ndcg >= ndcg_th)

    # Specialist vs decomposition
    b_beats_c_pairwise = (
        sum(m["wins"] for m in b_vs_c.values())
        > sum(m["losses"] for m in b_vs_c.values()) + sum(m["n"] for m in b_vs_c.values()) * spec_margin
    ) if b_vs_c else False
    b_beats_c_ndcg = bool(b_minus_c_ndcg is not None and b_minus_c_ndcg >= spec_margin)

    # CN/EN regression check
    cn_en_regression = (
        cn_en_b_winrate is not None and (cn_en_b_winrate - 0.5) < cn_en_floor
    )

    # Map to outcome
    if cn_en_regression:
        label = "MIXED_OR_REGRESSION"
        action = "Escalate to user — B regresses on CN/EN strong-coverage stratum"
    elif h1_pairwise and h1_ndcg and (b_beats_c_pairwise or b_beats_c_ndcg):
        label = "H1_CONFIRMED_SPECIALIST"
        action = ("Adopt Hy-MT2-1.8B-1.25bit as optional pre-encode tool, gated by detected "
                  "language. Upgrade intake-586 verdict to adopt_component.")
    elif h1_pairwise and h1_ndcg and not (b_beats_c_pairwise or b_beats_c_ndcg):
        label = "H1_CONFIRMED_DECOMPOSITION_ONLY"
        action = ("Switch ingest_long_context to 2-step (translate→summarize) prompt for affected "
                  "strata. Do NOT adopt Hy-MT2. Mark intake-586 not_applicable.")
    elif not h1_pairwise and not h1_ndcg:
        label = "H0_CONFIRMED"
        action = ("Downgrade intake-586 to not_applicable. Close MT translation sub-track on "
                  "angelslim-techniques-evaluation. Sherry/SpecExit/Tequila/DAQ remain independent.")
    else:
        label = "MIXED_OR_REGRESSION"
        action = ("Mixed signal: only one of pairwise/NDCG criteria met. Escalate to user for "
                  "stratum-level review.")

    return {
        "label": label,
        "action": action,
        "evidence": {
            "h1_pairwise_strata": non_cn_en_strata_b_wins,
            "h1_pairwise_threshold": pairwise_th,
            "h1_ndcg_lift_b_minus_a": b_minus_a_ndcg,
            "h1_ndcg_threshold": ndcg_th,
            "specialist_margin_threshold": spec_margin,
            "b_beats_c_pairwise": b_beats_c_pairwise,
            "b_beats_c_ndcg_lift": b_minus_c_ndcg,
            "cn_en_b_winrate": cn_en_b_winrate,
            "cn_en_regression_floor": cn_en_floor,
            "cn_en_regression_triggered": cn_en_regression,
        },
        "per_stratum_b_vs_a": b_vs_a,
        "per_stratum_b_vs_c": b_vs_c,
        "per_stratum_c_vs_a": c_vs_a,
    }


def emit_markdown(outcome: dict, kb_rag: dict) -> str:
    lines = ["# Multilingual Ingest Quality-Gap — Decision Report", ""]
    lines.append(f"**Outcome**: `{outcome['label']}`")
    lines.append("")
    lines.append(f"**Action**: {outcome['action']}")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for k, v in outcome["evidence"].items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Per-Stratum Pairwise (B vs A)")
    lines.append("")
    lines.append("| Stratum | n | wins | losses | ties | win-rate (excl ties) |")
    lines.append("|---|---|---|---|---|---|")
    for s, m in outcome["per_stratum_b_vs_a"].items():
        lines.append(f"| {s} | {m['n']} | {m['wins']} | {m['losses']} | {m['ties']} | {m['win_rate_excl_ties']:.3f} |")
    lines.append("")
    lines.append("## KB-RAG NDCG Aggregate")
    lines.append("")
    for pn in ("A", "B", "C"):
        agg = kb_rag.get(pn, {}).get("aggregate", {})
        lines.append(f"- Pipeline {pn}: NDCG@K = {agg.get('mean_ndcg_at_k')}, MRR = {agg.get('mean_mrr')}, n_scored = {agg.get('n_scored')}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kb-rag", required=True, type=Path, help="Output of kb_rag_eval.py")
    p.add_argument("--judge", required=True, type=Path, help="Directory output of judge_pairwise.py")
    p.add_argument("--output", required=True, type=Path, help="Decision markdown path")
    args = p.parse_args()

    repo_root = Path(__file__).resolve().parent
    cfg = load_config(repo_root)

    kb_path = args.kb_rag if args.kb_rag.is_absolute() else repo_root / args.kb_rag
    judge_dir = args.judge if args.judge.is_absolute() else repo_root / args.judge
    out_path = args.output if args.output.is_absolute() else repo_root / args.output

    if not kb_path.exists():
        print(f"[aggregate] kb-rag results missing: {kb_path}", file=sys.stderr)
        return 2
    if not judge_dir.exists():
        print(f"[aggregate] judge directory missing: {judge_dir}", file=sys.stderr)
        return 2

    kb_rag = json.loads(kb_path.read_text())
    judge = load_judge(judge_dir)

    outcome = apply_acceptance_criteria(kb_rag, judge, cfg)
    md = emit_markdown(outcome, kb_rag)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    # Also emit the structured outcome as JSON next to it
    out_path.with_suffix(".json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2))
    print(f"[aggregate] decision: {outcome['label']}")
    print(f"[aggregate] report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
