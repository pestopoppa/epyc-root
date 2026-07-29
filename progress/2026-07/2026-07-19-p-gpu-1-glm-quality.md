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

## PM update — agent executed the handoff; GLM failed decision-grade; reviewer slate opened

**The deterministic-oracle path worked end-to-end.** The parallel agent executed my
`GC-shadow-repair4b.2c` TODO (13:03) — the mechanical c-CRAB accept-oracle relabel → corpus
went decision-grade (hard-accept n=24) — then ran the matched C-CRAB P-REV-1 (15:22). **GLM-5.2-IQ2
FAILED patch-review admission: FA 41.7% (10/24), FR 25.0% (6/24), parse 0%, AUC 0.509 (≈ random),
ECE/AUC/Brier 0.239/0.509/0.278.** First claim-grade verdict: GLM-5.2 is not a usable patch reviewer.

**OP-2 canonical bench PASSED** (agent ran it 13:16 in a quiet window — my "not reboot-gated,
actionable now" correction was right). `GGML_IQK=1` confirmed, role smokes 6/6, canonical raw CPU
decode 12.44 t/s (regression control — NOT the deployed MTP speed; live role smoke ~35–43). v7
promotion gate now 4/8 green (K5, OP-2, P-GPU-1, upstream-audit); remaining blockers = final
coherence smoke + the two GLM boxes (GLM quality FAILED).

**Reviewer-model slate opened (operator-requested experiments).** Since v7 is coupled to GLM and
GLM failed, the highest-leverage open question is *big-quantized reviewer (GLM) vs efficiently-
harnessed small models*. Added to `reviewer-model-ablations.md`:
- **RM-2.fast** — Qwen3.6-27B dense (Q8) reviewer on the SAME decision-grade C-CRAB slice + runner.
- **RM-2.fast-b** — Qwable standalone (IQ4_XS; the primary harnessed-small candidate — it historically
  dominated the Qwable→beneficiary scaffold 77% vs 73% GPQA) + 27B+Qwable CoT scaffold (the coupling;
  past evidence falsified it on gemma-26B, so confirm-don't-assume).
- **Hard requirement:** all arms MI210-hosted (GPU, grammar on) — a fast slate we can iterate.
- Report matched FA/FR/AUC vs GLM's 41.7/25.0/0.509. If a small/fast arm reviews better → route the
  reviewer role there and **decouple v7 from GLM**. Surfaced at master-index top level (2026-07-19 PM).

**OP-2 number clarification (operator flag):** 12.44 t/s is the canonical raw no-spec CPU decode
(regression control), not the optimized deployed frontdoor speed (native NEXTN-MTP + OMP stack).

## Evening — reviewer slate resolved it; operator DECOUPLED GLM from v7; v7 READY

**Reviewer slate (agent executed all arms on the decision-grade C-CRAB slice, MI210-hosted):**
- GLM-5.2-IQ2 (754B): FA 41.7% / FR 25.0% / **AUC 0.509** — FAILED.
- Qwen3.6-27B dense Q8: 54.2% / 16.7% / **0.503** — over-approves, random.
- Qwable standalone IQ4_XS: 54.2% / 45.8% / **0.438** — worst (below random).
- 27B + Qwable CoT scaffold: 33.3% / 41.7% / **0.659** — best small arm (scaffold *helped* on patch-review,
  contradicting the GPQA prior — validated testing it — but FR too high; not role-ready).
- A0 objective floor: perfect (FA 0/FR 0). A3 122B-IQ2: FR 58.3%. A1 122B-Q4 self-review: 45.8/41.7/0.463.
- External: JudgeBench 22/24, SWE-bench-Verified 22/24 accept-controls — positive but partial (SWE has no hard negatives).
- **Verdict: no local model reviews near-miss patches better than ~chance.** GC-external-1e routed GLM away from production patch-review.

**Native GLM-MTP repaired (agent):** DeepSeek32/GLM-DSA NEXTN row-selection fix → CPU draft-mtp **5.33 t/s
decode** (α 0.933, 376/403 accepted) vs 2.49 no-spec (~2.1×). Still slow, CPU-only (238GB ⇒ no MI210 path).

**Architectural Q&A (operator):** the Architect→Reviewer control-plane design is model-agnostic and
largely VINDICATED — GLM was candidate arm A4, not the design; the calibration layer (P-REV-1) did its
job by catching a bad reviewer before production. Handoffs stay: H1-H4/H-LB/H7/H8 model-agnostic infra;
H5 tournament doing its job; H6 glm52 narrows to diagnostic. Control plane runs on objective-gates +
human-escalation regardless of whether any model reviewer clears.

**OPERATOR DECISION — DECOUPLE GLM from v7 finalization (2026-07-19).** GLM failed as reviewer AND is
slow; v7 promotes on production validation, reviewer tournament runs separately. Flipped `v7-promotion.md`
gate → DECOUPLED; operator-decision box + flag-READY box both ✅. **v7 is now READY FOR OPERATOR PROMOTION**
(all production boxes green: K5, OP-2, P-GPU-1, final cutover smoke PASS, upstream-audit, GLM-MTP repaired).
Validated promotion tip = `6ad45fa3ff`; operator authorizes the cutover (frozen-kernel rule). Relay message
handed to operator for the parallel agent (freeze tip, stop gating v7 on reviewer). Commit `09e1ac3a`.
