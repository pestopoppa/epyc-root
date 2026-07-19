# 2026-07-19 — P-GPU-1 ratification + GLM quality read + deterministic accept-oracle

Continuation of the v7-lever-audit session (advisory + governance). Docs-only from my side;
shared tree with an active parallel inference agent (careful single-file commits throughout).

## P-GPU-1 ratified (operator)
Drafted the strict `P-GPU-1` MEASUREMENT amendment (production-named-kernel-only, retro-cert
strict-allowed, all evidence fields mandatory incl. `rocm-smi` clocks/power/temp before+after);
**operator appended it to `MEASUREMENT.md` and flipped the `:45` DEFERRED header to RATIFIED**
via one-liners this session. Draft reference copy: `docs/reference/p-gpu-1-amendment-draft-2026-07-19.md`.
Consequence recorded: production-kernel-only means v7's Gate-R/banked-GPU rows stay observation
until re-run on `production-consolidated-v7` **after** promotion; ratifying the protocol does not
upgrade experimental numbers. `v7-promotion.md` gate box flipped ✅.

## OP-2 correction (I was wrong twice, now fixed)
OP-2 canonical bench is **NOT reboot-gated**. Live host is bench-eligible (`numa_balancing=0`,
CPU ~3.2 GHz/no severe throttle, 16-day uptime). It needs an operator quiet window + throttle/
affinity preflight — not a reboot. Corrected the over-strict "needs a fresh reboot" note in
`v7-promotion.md` + the OP-2 package doc.

## Model-probe scoreboard + sub-2-bit steering
Created `docs/reference/model-probe-scoreboard.md` (living, glance-able read of every experimental-v7
probe). Key read: production roles all clean (Qwable 91–104 t/s 18/18; frontdoor MTP 119.7; gemma
worker K5 +0.0%; MiniCPM-o vision activated 4/4). The sub-2-bit/exotic breadth (Bonsai/Ternary/
Nemotron) is speed-only + quality-blocked/broken — none role-ready. Steered the agent off grinding
them (scoreboard + `tq3-quantization-evaluation.md`).

## GLM-5.2 quality verdict (survey)
MIXED and mostly UNPROVEN. Exact-answer judging GOOD (FA 0%/FR 16.7%, n=24, well-calibrated).
**Flagship patch-review is weakest — over-approves (FA up to 91.7%, n=24).** Long-context FAILS
>12K (malformed output; DSA `indexer_top_k` cap doesn't scale; 32K needle fails). GC-1/2/3 pass
only as synthetic n=3 repaired smokes. Nothing claim-grade.

## GLM testing directive (surfaced to the agent)
Stop hand-labeling C-CRAB. Test GLM quality on **external ground-truth benchmarks on disk**
(`judgebench`/`reward-bench(-2)`/`llmbar`/`judgelm` for judge; `swe-bench-verified` test-oracle for
patch). Reviewer/judge gate runs NOW at ≤12K (doesn't wait for any kernel fix). Long-context (>12K)
is a separate track gated behind the `indexer_top_k`/sparse-final-attention D2 fix — orthogonal to
reviewer quality. Written into `glm52-reviewer-capability-gates.md` + `llama-cpp-dsa-contribution.md`.

## Deterministic accept-oracle finding (the headline)
Investigated whether the C-CRAB patch-review accept-control gate can be labeled deterministically.
**Finding: the deterministic label already exists and the builder discards it.** c-CRAB's fail→pass
testgen oracle proves the merged (accept) patch PASSES (stage3/stage4 membership), but
`mine_ccrab.py` hardcodes accept rows to `observation`/`executable_oracle=None`. Fix = a metadata
join (attach the latent pass verdict) → rebuild → re-run scorer → `decision_grade=true`. No
inference, no containers, no Claude-as-judge, scorer already supports the tier; ~139 eligible vs 24
needed. **Operator approved the oracle definition** (*testgen-pass-on-merged = hard accept*).
Ownership: handed to the parallel agent (it owns the nearmiss-v1 instrument + runs the eval) —
persisted as TODO **`GC-shadow-repair4b.2c`** in `glm52-reviewer-capability-gates.md`. My executor
subagent was stopped before it touched the shared tree (read-only stage only).

## Deferred / next (operator- or agent-gated)
- OP-2 canonical bench (operator quiet window + preflight — actionable now, no reboot).
- v7 promotion: coupled to GLM quality (operator kept coupled); real blocker is now the GLM
  patch-review verdict, which `GC-shadow-repair4b.2c` unblocks mechanically, then a live GLM run.
- Long-context GLM (>12K): D2 sparse-final-attention / top-k schedule fix.
- P-GPU-1 GPU-number certification: post-promotion on production-consolidated-v7.
