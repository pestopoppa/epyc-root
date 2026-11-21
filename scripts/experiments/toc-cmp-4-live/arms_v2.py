"""TOC-CMP-4 pre-registration v2 arm registry (amendment 2026-11-21; see the v2 section of
docs/design/toc-cmp-4-preregistration-20261109.md).

`resolve_arms()` is the single gate every analysis/runner entry uses: unknown names and BLOCKED arms are
refused with the reason, so a blocked arm can never be silently scheduled or analysed.
"""
from analysis import ARMS as V1_ARMS

# name -> (status, note). status: "v1" implemented in orchestrator context_arm_ab.ARMS; "new" accepted by the runner
# and analysis, arm implementation owned by the orchestrator side; "blocked" refused until its dependency lands.
REGISTRY = {
    "summary_only": ("v1", "summary-compaction baseline"),
    "pointer_only": ("v1", "pointer to the full log, no summary"),
    "prune_pointer": ("v1", "pruned history plus pointer"),
    "persistence_floor": ("new", "no history, no summary: only the task and the system prompt survive the boundary"),
    "prose_only_frozen_append": ("new", "prose tool output summarised in fixed-size segments as they close; each summary "
                                        "appended after the unchanged prefix, never rewritten; non-prose kept verbatim"),
    "async_compaction_next_k_judge": ("blocked", "needs two sequences sharing the pre-compaction prefix: blocked on "
                                                 "kv-prefix-fork P1"),
}
BOUNDARY_FRACTIONS = (0.25, 0.50, 0.75)  # boundary placement as a fraction of the reference trajectory
IRC_TARGET_CHAR_FRACTION = 0.10          # retention-ratio matching target for the self-built IRC calibration


def resolve_arms(names):
    names = tuple(names)
    if len(set(names)) != len(names) or len(names) < 2:
        raise ValueError("need at least two distinct arms")
    for name in names:
        if name not in REGISTRY:
            raise ValueError(f"unknown arm {name!r}")
        status, note = REGISTRY[name]
        if status == "blocked":
            raise ValueError(f"arm {name!r} is blocked: {note}")
    return names


def prefix_reuse(events, boundary_turn=None):
    """Prefix-cache reuse tally from trajectory turn events (server counts, never estimated).

    reuse = sum(cached_prompt_tokens) / sum(prompt_tokens) over turns where BOTH are observed (non-null).
    Returned for all turns and for post-boundary turns (turn > boundary_turn). `unobserved_turns` counts turns
    skipped for a missing count; a fraction with zero observed turns is None, never 0.
    """
    def tally(turns):
        seen = [t for t in turns if isinstance(t.get("prompt_tokens"), int) and t["prompt_tokens"] > 0
                and isinstance(t.get("cached_prompt_tokens"), int)]
        cached = sum(t["cached_prompt_tokens"] for t in seen)
        prompt = sum(t["prompt_tokens"] for t in seen)
        return {"cached_prompt_tokens": cached, "prompt_tokens": prompt,
                "reuse": (cached / prompt) if prompt else None, "turns_observed": len(seen),
                "unobserved_turns": len(turns) - len(seen)}

    turns = [e for e in events if e.get("event") == "turn"]
    out = {"all_turns": tally(turns)}
    if boundary_turn is not None:
        out["post_boundary"] = tally([t for t in turns if t["turn"] > boundary_turn])
    return out


def prefix_reuse_by_arm(runs):
    """Aggregate per-run `prefix_reuse` dicts into a per-arm token-weighted tally (voided points excluded)."""
    agg = {}
    for r in runs:
        pr = r.get("prefix_reuse")
        if not pr or r.get("void_point"):
            continue
        for scope in ("all_turns", "post_boundary"):
            if scope in pr:
                a = agg.setdefault(r["arm"], {}).setdefault(scope, {"cached_prompt_tokens": 0, "prompt_tokens": 0, "runs": 0})
                a["cached_prompt_tokens"] += pr[scope]["cached_prompt_tokens"]
                a["prompt_tokens"] += pr[scope]["prompt_tokens"]
                a["runs"] += 1
    for arm in agg.values():
        for a in arm.values():
            a["reuse"] = a["cached_prompt_tokens"] / a["prompt_tokens"] if a["prompt_tokens"] else None
    return agg
