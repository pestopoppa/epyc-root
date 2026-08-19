# 2026-08-19 — research-intake — LLM-as-a-Verifier re-ingest (stages 1–4)

**Session**: operator-invoked `/research-intake https://llm-as-a-verifier.com/ https://github.com/llm-as-a-verifier/llm-as-a-verifier#self-verification-terminal-bench-21`
**Outcome**: 6 Stage-1 entries + 5 Stage-2b entries = `intake-1161..1171`; 5 existing entries promoted
to `dive-verified`; 5 handoffs amended; **no new handoff, no new index row** (deliberate — see below).
Ten dives total. Started and completed 2026-08-19.

## Problem

Both submitted URLs were **already in the index** — the repo as `intake-363` (exact URL collision) and
the paper as `intake-804` (found via the README, exact `arxiv_id` collision). The value of the
re-encounter was not new material; it was that **the existing entries were stale in a way that
inverted their conclusion**.

`intake-362/363` (ingested 2026-04-14) carried one blocking rationale — *"Key limitation: Gemini API
dependency. Would need to adapt for local models"* — and that rationale is **false** at the current
upstream commit. It is why this source sat unused for four months.

## What the dives established

| Finding | Status |
|---|---|
| The Gemini-dependency blocker | **OVERTURNED.** At `115de305f23e` (v0.2.0, 2026-08-14, MIT) `fine_grained_reward.py:126-128` builds a client for any OpenAI-compatible server returning token-level logprobs |
| Can our own stack serve it? | **YES, verified empirically** on `production-consolidated-v9`: no `top_logprobs` cap (20/40/64 all honored), OAI response shape, **pre-sampler** head (temp 0 ≡ temp 1 byte-identical), 19/20 A–T letters present |
| `intake-804` filing | **MIS-FILED** — re-graded `duplicate`→`medium`, `already_integrated`→`worth_investigating`, cred 3→4; `round_robin_tournament_ranking` was the *baseline*, not the contribution |
| Open-weight verifier | **CONFIRMED and load-bearing** — Qwen 3.6 35B over SGLang produces the 87.4% RoboRewardBench headline (§5.3), not just an appendix |
| Probabilistic Pivot Tournament | **DOES NOT beat round-robin** — 67.13% @ 9,630 pairs vs **67.42% @ 13,111**; and its O(Nk) is not an advance over V1's earlier O(N)-scale adaptive schedule |
| `intake-875` reconciliation (never done before) | **VERDICT (2) BOUNDS.** The LiveCodeBench best-of-N arm is **training-free**, so selection-only is *not* a safe harbour — but the quantity that inflates is the judge's own score, and true pass still rises 0.27→0.29 |
| Ensembling as a hacking mitigation | **STRUCTURALLY EXCLUDED** — Proposition 2 covers every monotone rule; three-family min-vote still accepts ~65% (three-seed mean; our index carried 55%, the seed-0 figure) |
| G=20 granularity | **API-cap-shaped, not optimal** — Gemini caps at 20 top logprobs; SNR gains +0.002 from G=16→20 |
| Our own parked selector result | **RECOMPUTES WORSE** — 9.1% recovery, not the ~25% a Stage-1 note estimated |
| Best-of-3/5 overoptimization risk | **NOT our risk** — 35–60× below the turn in n. The binding condition is a **verifier competence floor** |
| The cheap route | **May need no logprobs at all** — V1 gets the same graded tie-free signal from text ratings + margin weighting, ~20 lines |

## Corrections issued against this session's own earlier output

Three, all recorded in-index rather than silently repaired:

1. **`92/120` → `42/48`.** I "verified" the win-count verbatim against **ar5iv, which silently serves
   v1** for `2503.03064`, and on that basis overrode a sub-agent that had correctly reported the v2
   figure. Byte-level confirmation: v1 and ar5iv contain `92 out of 120` ×3 and `42 out of 48` ×0;
   `arxiv.org/html/…v2` is the exact inverse. Verifying that a string exists in *a* source is not
   verifying it against the *current* source.
2. **The V1-is-non-monotonic claim I wrote into `intake-804` was mis-attributed** and is withdrawn.
   V1 publishes only 1×/2×/3× budgets and claims *monotonic* scaling; the 5N/7N points are
   `intake-804`'s own extrapolation 2.3× beyond V1's envelope at untuned parameters. The corrected
   objection is stronger: it benchmarked its baseline out of envelope and then reported beating it.
3. **Granularity evidence was mislabelled** — the figures recorded were Table 5's *tie-subset* column,
   not the expectation's accuracy. Corrected to Table 6. Same conclusion, right evidence.

Also corrected: the `intake-875` de-anchoring figure was **misattributed across judges** (0.588→0.637
is the *same* judge getting **worse**; 0.227 belongs to a 4.7× larger one), and the ensemble figure
quoted the most conservative seed.

## Changes made

| File / repo | Change |
|---|---|
| `research/intake_index.yaml` | 11 new entries; 5 promoted to `dive-verified` with `dive_corrections`, `claim_corrections`, `claim_anchors`, `depends_on`; `handoffs_updated` written back on 10 entries |
| `handoffs/active/eval-tower-verification.md` | Corrected the stale "Logprob Truncation" section (cited `L1755`; actual v9 location is **`server-common.cpp:1256`**, and the full-vocab claim is now *conditional*); added the **EV-15a–f** instrument cluster; amended the de-anchoring rule with a capability gate; bounded the retrospective judge-scored-gain check; added an operator-review candidate to **split the cross-family claim** |
| `handoffs/active/reviewer-model-ablations.md` | **RM-11a** (cross-family vs same-family verifier gain) and **RM-11b** (reviewer solve-accuracy — the Corollary 1 anchoring test, never run) + dep-graph edge + the AUC premise correction |
| `handoffs/active/reviewer-calibration-accounting.md` | **RC-10** — first runnable entry point for a cross-link that had been prose-only since 2026-07-29 |
| `handoffs/active/vidya-belief-substrate-program.md` | **SC43** — write side filed *before* the first run; keys on the run, not the score |
| `scripts/vidya/adapters/README.md` | matching source-table row |
| `handoffs/active/gpu-cot-scaffold-sidecar.md` | reopen condition sharpened into recovery-rate terms and made falsifiable |

## Results

- `validate_intake.sh` **exit 0** (1,167 entries) · `index_state.py --check` **exit 0, 0 problems**
- **14 new `- [ ]`, 1 new `- [x] ✅ 2026-08-19`**
- Rollup moved research-evaluation open 341→348 / blocked 10→11, reviewer-control-plane 30→34 —
  reconciles exactly. The +1 blocked is the new cross-family candidate, correctly classified
  non-dispatchable by `backlog_row_check` ("the ROW DECLARES ITS OWNER … and it is not you")

## Deliberate non-actions

**No new handoff, and no new index row.** A `local-pairwise-verifier.md` stub was considered and
rejected: `gpu-cot-scaffold-sidecar.md:202` already parked this exact lever as MARGINAL with a reopen
condition our recomputed 9.1% recovery does not clear, and the build is gated on a measurement that may
kill it. A stub for a contingent build is the row that appears in two consecutive wrap-ups with an
unchanged blocker.

**One sub-agent recommendation declined**: dropping `intake-804` to `novelty: low`. Our rubric defines
`low` as well-covered-in-chapters and `medium` as related-work-exists-plus-new-results; a paper
contributing four benchmarks and a full ablation suite meets `medium` regardless of mechanism priority.
The priority finding lives in `dive_corrections`, where it stays legible.

## Deferred — with named blockers

- **RM-11a/RM-11b require operator bench windows** (the standing gate on all inference-heavy runs in
  `reviewer-model-ablations.md`). Blocker: operator window allocation. Not agent-actionable.
- **The five operator-review candidates in `eval-tower-verification.md`** (including the two amended and
  one added today) are behind the human-amendment-only eval trust boundary. Blocker: operator decision.
- **Non-selected Stage-2b sources** recorded as NOT-SELECTED on their bearing entries. Strongest
  remaining: `2401.01879` (Beirami et al., which shows the `log n − (n−1)/n` expression is an **upper
  bound**, not the equality `intake-1167`'s x-axis assumes) and `2404.17140` (the capability-floor
  question `intake-1168` explicitly hands off). Blocker: operator selection for a further Stage-2b round.

## Defect found and not fixed

**13 pre-existing index entries carry a malformed list item** where an unquoted colon-space turned a
claim or technique string into a single-key mapping — `intake-218/239/350/991/994/995/996` (`key_claims`),
`intake-498` (`reported_results`), `intake-502/505/506/688/779` (`techniques`). Example:
`intake-218.key_claims[0]` parses as `{'Feature absorption': '…'}`. `validate_intake.py` does not catch
it and `yaml.safe_load` accepts it, so any consumer iterating claims as strings gets a dict. Found by
hitting the same bug in my own edit and sweeping for it. **Not repaired** — it is other sessions' claim
text and rewriting it risks changing meaning.
