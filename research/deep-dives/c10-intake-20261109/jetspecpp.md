# JetSpec++ (arXiv 2610.19792v2) Stage-2b dive, intake-2668 (wave 2)

- **read_depth:** FULL. v2 text read end to end, including Appendices A-F and all 16 tables. Figures read through captions and body prose only.
- **version:** v2, 15 Oct 2026 (v1 14 Oct). Raw HTML sha256 `dffecf19a787e0b5f64c5d3da90b5404bdcbce3902ca0f7845ce99133ff13498` (`src/paper-2610.19792-v2.html`).
- **Companion code read, never executed:** `hao-ai-lab/JetSpec` at `673267e4faba71a63099c258f0802c2f3aa44f8e` (the checkout from the wave-1 JetSpec dive): `README.md`, `jetspec/methods/jetspec_plus_plus/models/hybrid.py`, `jetspec/engines/jetspec_plus_plus/README.md`, `profiles.py`, `bench/jetspec_plus_plus/reproduce_paper_results.md`. Selective read.
- **lane_head:** ad1e73525f6b86077936d9a1065f4da35c27c9d5.

## Answers to the four questions

1. **What it adds over JetSpec and XPress.** Over JetSpec: it drops tree verification and returns to a chain; it adds a learned hidden-state adapter and a target-layer decoder so drafting can start before verification ends; it retrains the head on token inputs with clean-prefix blocks so it can refine. Over XPress: refinement uses the **whole drafter** rather than a small head, and adds simulated verification (context refresh plus anchor replacement). XPress needs one device; JetSpec++ as evaluated needs two.
2. **Does self-refinement add drafter passes? Yes.** Each J is a full drafter forward (`T_pass`, Eq 3). J3-R3 is 4 drafter passes per round per cached outcome, plus 3 adapter+decoder refreshes, plus the foresight call. This is the opposite of XPress, where the backbone runs once. The paper hides these passes behind verification on a second GPU; it does not make them cheap.
3. **DFlash2 or hybrid-target result?** **DFlash2: none** (0 occurrences in the HTML). **Hybrid: yes**, and it is the first we have on our exact target: Qwen3.8-27B in Table 2 (tau) and Table 3 (serving, GB200, two GPUs). The only 27B baselines are AR and DSpark. Verification is a chain, block 16, temp 0 for serving.
4. **Does it change the proposed gates (tau >= +10% at B<=28; verify cost <= 0.5 ms/node on MI210)?** **Thresholds unchanged, one measurement amendment.** The paper contains no tree verification data, so it cannot move the tau gate. It does supply the only published per-token verify slope on a hybrid target: **0.72-0.75 ms/token on GB200** (derived below), which already exceeds 0.5 ms on a much faster GPU, while dense Qwen3-8B on the same GPU is 0.05 ms. That raises the probability that A2 fails. Amendment: A2 must add a **chain-depth arm** (1..8 tokens, one branch) at both short and long context, because the in-house s≈0-0.65 ms/node came from a 32.7k-context run where fixed cost dominates. See "Gate impact".

## Mechanism

Three parts, per round:

- **Pipelining.** Draft block t+1 while block t verifies. Cache one pre-drafted block per anticipated outcome (k, a). Hit: use it. Miss: draft a fallback in one pass on the critical path (Eq 4).
- **Foresight.** A 12-layer adapter (copies of target layers, trained, 4.47B parameters for 27B, 2.32B for 8B) predicts the target hidden states of the unverified block. A 2-layer training-free decoder (the target's own last two layers plus norm and LM head) turns those into P(k, a). The top B outcomes are cached (B=16 in Tables 1-2, **B=4 in serving**).
- **Self-refinement.** J Jacobi passes of the full drafter. Between passes, up to R context refreshes: re-predict target states for the current draft, find the first position where the decoder disagrees, overwrite it (anchor replacement), and freeze the prefix.

Drafter: 5 layers, causal mask within the block, token inputs (not mask tokens), noise tokens copied from the sequence, forward-KL, clean-prefix schedule Pr[m=0]=0.25. 1.73B trainable for 27B. It reads target layers 5/19/33/47/61 (0-indexed), the same spacing as DFlash2's taps [6,20,34,48,62] at speculative-decoding.md:1611; whether those lists are the same layers depends on indexing conventions I did not reconcile.

Argmax draft with point-mass proposal: accept d_i with p(d_i), else resample from the residual. Lossless at any temperature (App F.3). **Softmax q with an argmax token is not** (App F.3 worked example).

## Claim table

| # | Claim | Status | Locator | Verbatim |
|---|---|---|---|---|
| 0 | Foresight drafting starts the next block before verification ends | CONFIRMED | Abstract, Sec 4.1 | "which begins the next block before the current one is verified" |
| 1 | The drafter refines its own block in parallel, no extra module | PARTIAL. No module beyond foresight's, but it runs the full drafter J+1 times and the decisive gain needs the adapter+decoder | Sec 4.3 | "We instead let the draft model refine its own draft in parallel" |
| 2 | Works on a hybrid target | CONFIRMED for Qwen3.8-27B, chain verification only | Sec 5.3 | "a hybrid model in which 48 of the 64 layers are Gated DeltaNet" |
| 3 | 1.54x over DSpark | PARTIAL. 8B, GSM8K, J1-R1, **2 GPUs vs DSpark's 1**, with DSpark's confidence scheduling disabled. 27B: 1.37x / 1.31x | Table 3, Sec 5.1 | "DSpark runs without its confidence-based scheduling, so every method verifies a block of fixed size." |
| 4 | Jacobi passes raise tau | CONFIRMED vs J0, but **Jacobi alone never reaches DSpark** on any of 7 benchmarks | Table 5 vs Table 1 | "so most of that gain comes from anchor replacement" |
| 5 | Verify time on 27B | CONFIRMED, and load-bearing for the gate | Sec 5.4, Table 3 | "On Qwen3.8-27B, graphed verification takes 27.4 to 27.8 ms" |
| 6 | Training cost | CONFIRMED. 27B drafter 710 + adapter 172 = **882 GB200 GPU-hours** | App E, App A | "Training takes 347 GPU-hours on GB200 GPUs for Qwen3-8B and 710 for Qwen3.8-27B." |
| 7 | Mask-input heads cannot refine | CONFIRMED. JetSpec head 5.86→2.39 and 7.51→2.57 at J1 (Table 12); mask + fully noised 4.34→1.23 (Table 4) | Sec 4.3, App C | "A draft model trained only on masked blocks is never trained to condition on tokens at its inputs." |
| 8 | Point-mass verification is lossless; a softmax q on an argmax token is not | CONFIRMED by reading the proof; the worked example checks (commits 2/3 vs target 0.6) | App F.3 | "because the token is not drawn from that softmax" |
| 9 | Average tau 8.94 and "up to 7.45x" | PARTIAL. 8.94 is **J3-R3, 8B, offline, B=16**. 7.45x is **J1-R1, 8B, serving, B=4, tau 9.41 on MATH-500**. The abstract joins two configurations | Abstract, Tables 1, 3 | see Table 1 and 3 |
| 10 | Most of the gain comes from hiding drafting | CONFIRMED on 8B only; **on 27B tau contributes more than round time** | Sec 5.4, derived | see decomposition |

Arithmetic that held: Table 1 averages (7.50, 6.89, 8.94); Table 3 tok/s ≈ tau/round to within about 1% on the cells I recomputed; Table 16 leads of 0.79 and 0.81.

### Decomposing the headline (Table 3, temp 0, np1, 2 GPUs vs 1, GB200)

| Target, benchmark | Total | Tau ratio | Round-time ratio | Speedup per GPU vs DSpark |
|---|---|---|---|---|
| 8B GSM8K | 1.543 | 1.060 | 1.450 | 0.77 |
| 8B MATH-500 | 1.509 | 1.048 | 1.438 | 0.75 |
| 27B GSM8K | 1.372 | 1.219 | 1.120 | 0.69 |
| 27B MATH-500 | 1.312 | 1.162 | 1.127 | 0.66 |

On our target, tau is the larger part. Pipelining buys about 12% of round time on 27B because verification dominates.

### Tau on 27B (Table 2, block 16, budget 16, mean of 7 benchmarks, offline, B=16)

| | DSpark | J1-R1 | J3-R3 | J1/DS | J3/DS |
|---|---|---|---|---|---|
| Temp 0 | 7.18 | 7.79 | 9.06 | +8.5% | +26.1% |
| Temp 1 | 5.98 | 6.60 | 7.28 | +10.3% | +21.7% |

### What actually produces the gain (Table 5, 8B, budget 16, mean of 7, temp 0; DSpark = 6.89)

| Config | Tau | vs DSpark | Added machinery |
|---|---|---|---|
| J0 | 5.44 | 0.79 | new head only |
| J1 R0 | 6.16 | 0.89 | +1 full drafter pass |
| J3 R0 | 6.48 | 0.94 | +3 full drafter passes |
| J1 R1, no anchor replacement | 6.49 | 0.94 | + adapter refresh |
| J1 R1 | 7.50 | 1.09 | + decoder anchor replacement |
| J3 R3 | 8.94 | 1.30 | all |

**Jacobi alone trails DSpark on all seven benchmarks.** The win over a first-order-conditioned head comes from anchor replacement: 14 layers of target-derived compute guessing what verification will say. "Self-refinement" is a generous name for this. It is closer to a truncated, learned rehearsal of the target. DSpark's Markov head is the closest published proxy for DFlash2's selector, as in the XPress dive, so this is the row that matters for us. DSpark is not DFlash2, so the proxy is an assumption.

## Baselines and fairness

- All heads retrained by the authors on the same 800k set. Good control, but all baselines are the authors' reproductions.
- **DSpark loses its confidence scheduling** (Sec 5.1), the feature that would reduce wasted verify rows.
- **Resource asymmetry:** JetSpec++ and SSD use two GPUs, DSpark and DFlash one. No DSpark-on-a-second-GPU arm exists, so the value of the second GPU is not separated from the method.
- **"JetSpec" in Table 1 is a chain at budget 16/32, not its tree mode.** The paper therefore does not compare against JetSpec trees. Cross-paper only and non-commensurable (different heads): JetSpec tree B256 MATH-500 tau 10.76 (intake-2666 dive) vs J3-R3 chain budget 32 tau 14.55 and budget 16 tau 11.04.
- Serving results are temp 0, batch 1 only. Sec 4.1 states the scope: "JetSpec++ targets per-request latency". **No concurrency data at all.**
- Temp 1 is offline tau only, and hit rate is never reported at temp 1.
- Repetition loops are excluded fairly across all methods (App E).
- Calibration uses 56 held-out prompts per target; small but disjoint.
- Evaluation is 128 prompts per benchmark at 2048 max tokens, on benchmark shapes, not agentic traffic.

## Verify-cost model

Paper model: `round = max(T_verify, T_draft) + T_comm + (1 - p_hit) T_fallback` (Eq 4), with `T_draft = T_pred(1) + R T_pred(|S|) + (J+1) T_pass(|S|) + T_host` (Eq 3). Component times are **not reported**.

Derived from Table 3 (GB200, CUDA graphs): slope = (verify at budget 16 - AR verify) / 15.

| Target | Benchmark | AR verify | Budget 16 verify | ms per added token | % of AR forward per token |
|---|---|---|---|---|---|
| 8B dense | GSM8K, MATH | 5.45, 5.44 | 6.16-6.26 | 0.047-0.055 | 0.9-1.0% |
| 27B hybrid | GSM8K | 16.54 | 27.42 DSpark, 27.76 JS++ | 0.725, 0.748 | 4.4-4.5% |
| 27B hybrid | MATH-500 | 16.83 | 27.57 DSpark, 27.70 JS++ | 0.716, 0.725 | 4.3% |

**Hybrid chain verification costs about 15x more per added token than the dense target in absolute terms, and 4.5x in relative terms.** The reference code's `HybridCache` sets `sequential_verify = True` (hybrid.py:179). That is the torch reference path; the served engine has separate 27B kernels that I did not trace. The GDN recurrence is the plausible cause, but the paper does not state one. This is a mean slope over 15 tokens and assumes linearity.

The draft-to-verify ratio on GB200 for a DSpark round is 4.46/27.42 = 0.163. Our DFlash2 round is 11.1/67.1 = 0.165 (kernel-champion-and-promotion.md:465, Pass L). The ratios match closely, so the shape of the problem transfers even though absolute times do not.

## Drafter training

Required, and heavier than any prior item in this wave.

- 27B: drafter 710 GPU-hours + adapter 172 = **882 GB200 GPU-hours** (Apps E, A), 800k sequences regenerated by the target, 6 + 2 epochs. Qwen3-8B: 347 + 219 = 566.
- Calibration fit on 56 served prompts per target.
- Published checkpoints exist for Qwen3.8-27B (`JetSpec/jetspec-plus-plus-qwen3p8-27b`, README line 37: drafter, adapter, calibration) but at **block 16**, not our block 8.
- MI210 hours are not stated anywhere. Local pipeline does not exist (DF2-FT-1, speculative-decoding.md:1611). A build cost, not a decline reason.
- A port test on the published block-16 checkpoint needs no training. It is an MI210 tau-only experiment, but the drafter is not DFlash2 and requires the adapter/decoder/graph port first.

## Target requirements

A chain: linear verify, single branch. No tree mask, no per-branch state, no change to rollback semantics. It needs:
- target hidden-state taps exported after every verify (5 layers; DFlash2 already reads 5 taps);
- for hybrid, the committed recurrent and convolution states of layer 62 and the K/V of layer 63 sent to the draft process (App B.1);
- a second process or device, with `T_comm` small. The repo's stated requirement: "two GPUs that have peer access" (README line 41). HIP/gfx90a port is a build cost.

## Hybrid-SSM analysis

**Neither kills nor merely prices verification, because verification stays a chain.** Target-side recurrent state follows the existing single-path rollback. `HybridCache` takes per-verify-token snapshots and restores by accepted count; it refuses anything except width-one (hybrid.py:178-198, same refusal found in the wave-1 dive).

The hybrid cost lands in **two other places**:

1. **Draft-side state.** The decoder needs layer 62's committed GDN recurrent and convolution state, re-sent after every verify. Decoder rows are isolated causal rows, so each row carries its own state. The draft side now holds a small recurrent state per anticipated outcome. Size is small (one GDN layer), and it is priced, not fatal.
2. **The adapter's accuracy across GDN layers.** Paper's solution: each adapter layer "takes its MLP from the copied layer and its attention from the nearest full-attention layer at or below it" (App A). So the adapter replaces recurrent layers by attention layers. Tau held on 27B (J3-R3 +26% over DSpark). Table 6's 95-98% state-recovery result is **8B only**, so adapter accuracy on 27B is inferred from Table 2's tau, not directly reported.

No per-branch recurrent verification exists here. This is the paper's practical workaround for the hybrid constraint: it did not solve multi-branch GDN verification, it avoided it. Reading that as the authors conceding that branch verification is uneconomic on hybrid is my inference.

## Estimate for our regime (ESTIMATE, labeled; no measurement)

**Regime:** np1, n-max 7, block 8, temp 0, short M1 prompts, 128 tokens, Qwen3.8-27B Q8_0 + DFlash2 Q8_0, MI210. Reference 78-84 t/s, acceptance 0.62-0.73, tau = 1 + 7a ≈ 5.34-6.11, midpoint 5.76. Busy round 78.2 ms: verify 67.1, drafter 11.1 (kernel-champion-and-promotion.md:465).

**Tau transfer to block 8.** Fit geometric per-position acceptance to Table 2 (15 draft positions, 27B, temp 0): DSpark a=0.878; J1-R1 0.892; J3-R3 0.917. Rejection ratios: J1-R1 0.883, J3-R3 0.678. Apply the ratio to DFlash2's geometric a (0.880-0.921, tau 5.34-6.11) at 7 positions:

- J1-R1: tau +3.1-4.6%, central +3.8%.
- J3-R3: tau +8.9-13.5%, central +10.9%.

Assumes DFlash2 ≈ DSpark in conditioning, geometric acceptance, and that rejection ratio survives the depth cut. Actual J3-R3 gain at block 16 is +26%, so **most of the headline is depth that block 8 does not have**, consistent with DSpine's failure mode.

**Draft-side cost.** Refresh cost two ways: (a) by layer count, 12/64 + 2/64 of verify ≈ 14.7 ms, call 15; (b) by the parameter ratio to the drafter, 4.47/1.73 × 11.1 ≈ 29 ms. Paper ratio check: at GB200 J3-R3 fits inside verify, so its draft side is ≤ 1.0x verify at 27B (Sec 5.4), which on MI210 implies ≤ about 67 ms if ratios hold.

**Case 1: one MI210, drafting on the critical path (our actual hardware).**

| Config | Round (ms) | Tau ratio | Speedup vs DFlash2 n7 |
|---|---|---|---|
| J1 R0 | 67.1 + 22.2 = 89.3 | 0.895 (DSpark-proxy, block 16) | 0.895 x 0.876 = **0.78x** |
| J3 R0 | 67.1 + 44.4 = 111.5 | 0.94 | 0.94 x 0.70 = **0.66x** |
| J1 R1 | 67.1 + 22.2 + 15..29 = 104-118 | 1.038 | **0.69-0.78x** |
| J3 R3 | 67.1 + 44.4 + 45..86 = 157-198, or capped at 134 by paper ratio | 1.109 | **0.44-0.65x** |

Single-device overlap (MI210 queue sharing) is unmeasured and would contend for HBM; I assign no gain. **All single-device configs lose.** The draft-side cost is real and, on one device, it lands on the critical path. **np1 27B single-MI210 estimate: 0.44-0.78x.**

**Case 2: a second accelerator (not present; 2nd MI210 referenced as future, kernel-champion-and-promotion.md:1244).**
Tau multiplier for hit/miss: 0.9 x 0.97 + 0.1 x 0.4 = 0.913 (Table 3 hit 0.89-0.90; Table 6 predicted-state retention 0.95-0.98, measured on 8B; miss/hit tau ratio 0.38-0.42 from Table 3). Range 0.865-0.935.

| Config | Round | Effective tau | Speedup vs DFlash2 n7 |
|---|---|---|---|
| Foresight + J0, pipelining only | 67.1 + 0.75 + 1.1 = 69 | 0.913 | 0.913 x 1.134 = **1.04x** (0.98-1.06) |
| J1 R1 | 69-73 | 1.038 x 0.913 = 0.948 | **1.02-1.07x** |
| J3 R3 if it fits inside verify (paper ratio) | 69 | 1.0125 | **1.15x** |
| J3 R3 if it does not (layer-cost estimate, draft ≈104 ms) | ≈106 | 1.0125 | **0.75x** |

**Case 2 range 0.75-1.15x, for two GPUs at batch 1.** Per-device that is at most 0.57x. It is a latency trade, not an efficiency gain, and it needs the second device.

**Real temp-1 agentic traffic** (acceptance 0.29-0.39, tau 3.0-3.7): applying the Table 2 temp-1 rejection ratios, tau J1-R1 +8.7-10.5%, J3-R3 +18-22%, offline proxy. Low confidence: hit rate at temp 1 is not reported, and the deciding question is distribution mismatch (DF2-FT-1).

**CPU placement of the draft side.** Unmeasured, and blocked today: the drafter-on-CPU control aborts at reserve because the drafter shares the target's ROCm-resident `output.weight` (kernel-champion-and-promotion.md:461). A build cost. CPU decode is bandwidth-bound and a 12-layer adapter is a heavy load, so I would not assume it fits inside a 67 ms window.

**A3B (Qwen3.6-35B-A3B Q8_0):** CPU with MTP today. MTP is causal, so there is nothing for Jacobi to repair, and adapter layers would run on the bandwidth-bound device. **0% today.** GPU-eventual A3B needs a DFlash-family drafter first, then the 27B analysis applies, since A3B is hybrid too.

**MI210 small models at high concurrency:** no data; all serving is batch 1. Sec 4.1 scopes the method to per-request latency. Dense small targets have a far flatter verify slope (0.05 vs 0.72 ms/token on GB200), so pipelining hides a larger share of the round on them: on 8B the round-time ratio was 1.44-1.45x. If a dense small model ever serves on MI210 with a second device, this is where the method pays best. No such lineup row exists.

**Evidence grade:** C+ for the paper's own setup (open code and weights, retrained baselines, serving correctness checks, paired ablations; no independent replication, DSpark handicapped, two-vs-one GPU comparison). **C-** for transfer to our block 8, DFlash2, single MI210.

## Gate impact (proposed from the JetSpec dive, A1-A3)

| Gate | Change? | Why |
|---|---|---|
| tau >= +10% at B<=28 (A1) | **No change** | No tree data here. It remains a DFlash2-lattice question |
| verify cost <= 0.5 ms/node (A2) | **Threshold unchanged, arm added** | Published hybrid chain slope 0.72-0.75 ms/token on GB200 is already above 0.5. Scaling by AR-forward ratio (Pass L plain token 57 ms wall vs 16.5 ms: 3.5x, wall vs busy, indicative only) gives roughly 2.5 ms/token on MI210, near the 3 ms scenario in the JetSpec dive where B=28 is 0.59x. In-house s≈0-0.65 comes from LongHealth 32.7k, where fixed cost dominates. A2 needs a **chain-depth arm** and **both short and long context** |
| A3 tree build | **Lower prior, no new condition required** | A chain-depth slope near 0.7 does not prove tree-breadth cost, since level-synchronous nodes share a depth sweep. It does remove the assumption that per-token cost is small on hybrid |

Decision: A2 must measure MI210 slope in both axes before A3 can open. Tree-build remains conditional on A1 and A2.

## DSpine overlap

**Same bet on one device, different bet on two.** DSpine (CLOSED NOT_OUTPERFORMS, best 0.915x DFlash2 n7, speculative-decoding.md:1598-) paid draft-side time for acceptance at block 16 and lost at the round level. JetSpec++ on one MI210 is the same bet at a higher price (several full drafter passes plus a 12-layer adapter), and the estimate above is worse than DSpine's result. With a second device it is a different bet, because the cost leaves the critical path. It shares DSpine's transfer risk: gains measured at block 16 do not arrive at block 8.

## Adversarial pass (bounded web search, 2026-11-09)

One standard search. Returned the JetSpec paper and restatements (arXiv, Hugging Face papers, a news write-up, sotaverified, catalyzex), xPress and ParallelSpec. **No source mentions JetSpec++, and no independent replication or criticism was found.** Paper is under a month old. Strongest criticism is internal, listed above.

Sources: [arXiv 2606.18394](https://arxiv.org/pdf/2606.18394), [HF papers 2606.18394](https://huggingface.co/papers/2606.18394), [NYU RITS write-up](https://rits.shanghai.nyu.edu/ai/jetspec-causal-parallel-tree-drafting-hits-9-64x-faster-llm-inference/), [sotaverified](https://sotaverified.org/papers/260618394), [HF papers 2608.02438](https://huggingface.co/papers/2608.02438.md).

## Derived-actionables ledger

| ID | Action | Task or decline |
|---|---|---|
| JP-1 | Amend proposed A2: MI210 ms/token **chain-depth arm** 1..8 plus breadth arm 8/16/32/64 nodes, at short (M1) and long (32.7k) context, 27B Q8_0 | **Task** (amendment to the A2 proposal; owning session applies) |
| JP-2 | Port JetSpec++ to a single MI210 with drafting on the critical path | **Decline**: cost-model reason, 0.44-0.78x estimate. Not missing software |
| JP-3 | Jacobi passes on existing DFlash2 weights, zero training | **Decline**: DFlash2 is a mask-input non-causal head; Tables 4 and 12 show this class collapses or loses at J1, and Jacobi alone trails DSpark even with the right training |
| JP-4 | Full JetSpec++ on 27B block 8 with second device (adapter, decoder, refinement, retrain; or block-16 published checkpoint as first port test) | **Trigger, no checkbox**: fires when a second accelerator with peer access is installed AND DF2-FT-1 yields a working pipeline. Estimate 0.75-1.15x; 882 GB200 GPU-hours as stated |
| JP-5 | Add to DF2-FT-1 / DF2-BLOCK16 training arms: token inputs and clean-prefix schedule Pr[m=0]=0.25, alongside the causal-mask arm A4 from the JetSpec dive | **Addendum, conditional on the pipeline existing**. Cheap in that case; Table 13 shows the band 0.125-0.5 is flat |
| JP-6 | DF2-PM | **No new task**. App F.3 independently states the point-mass construction and warns that a softmax q on an argmax token is not lossless; cite as design support (`#record`) |
| JP-7 | SPEC-CONF.1: Table 11's draft-model rule hit rate is .743/.738 at B=4 vs .929/.909 for the decoder-based rule | **Knowledge note**: on 8B, drafter self-confidence is a weaker predictor of accepted length than a target-derived score. Does not change the step-1 AUC protocol |
| JP-8 | CPU or A3B application | **Decline for now**: MTP is causal, bandwidth-bound device. Reopen with a DFlash-family A3B drafter |
| JP-9 | CAFE-3, SL-2, DF2-LB1, DF2-LAT | **No overlap for action**. DF2-LB1 may note the 0.72 ms hybrid slope as corroboration |
| JP-10 | Do not cite 1.54x, 7.45x or 8.94 for planning | **Knowledge note**: 8B, 2 GPUs vs 1; 8.94 and 7.45x are different configs. 27B is 1.31-1.37x |

## Dive-surfaced sources

**Wave cap reached; none listed for dive.** Noticed in the reference list and absent from the index copy: arXiv 2609.27396 (DPara), 2607.22634 (PRESTO), 2608.13524 (DARTree), 2606.04446 (D2SD), 2605.30852 (Speculative Pipeline Decoding), and 2604.12989 (DDTree, already named by the JetSpec dive). DSpark (2607.05147) and SSD (2603.03251) are already indexed.
