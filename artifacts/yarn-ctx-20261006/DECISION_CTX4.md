# YARN-OPTION-D-DECISION (CTX-4): long-context configuration for Qwen3.6-35B-A3B-MTP on :8070

Date 2026-10-06. Owner: `yarn-context-extension-research.md` (`YARN-OPTION-D-DECISION`). Docs only; no repo commits, production v10 untouched.
Inputs: STAGE3_PLAN.md CTX-4 (G1-G3), OPTIONS.md, results/summary.md, CTX2_KSHIFT.md, ctx3a/COST.md + results_20261006T054613Z.csv, jetlong/{DESIGN,TESTS,LONGCTX_PLAN}.md.

## 1. Context
The operator rule is that context extension must not change outputs inside the native 262144-token window. Static YaRN (the current way to go past 262K) does change them. The fork is which design delivers 262K to 1M without breaking that rule. The three gates have now reported, and the choice among D, F and J depends on a security-of-identity trade and a build-cost trade that only the operator can weigh.

## 2. Evidence (claim grammar: n, arm, metric; all CPU, greedy, short prompts unless stated)
| Gate | Result | Consequence |
|---|---|---|
| G1 / CTX-1 (n=20 greedy prompts per arm) | N 20/20 self; Y (static YaRN) 13/20 byte-identical vs N; **YM (YaRN with mscale cancelled) 13/20**. MTP accepted/drafted, short: N 0.704, Y 0.707, YM 0.734. MTP at 34k: N 0.514, Y 0.490, YM 0.468. | **G1 FAIL.** Cancelling the mscale temperature does not restore identity, so the drift is from the frequency interpolation itself. A per-token-`ff` design (F) cannot be made inert by a cheap scale trick; it is inert only by *not applying* YaRN in-window. MTP acceptance at 34k moves by 2.4-4.6 pp (outside the 1 pp rule). Tok/s is not a speed claim in this run. |
| G2 / CTX-2 (unit, standalone ggml, CPU) | K-shift at v10 `ffc1bac82` is unusable: H1 (mscale re-applied per shift, norm 1.0693^n), H2 (pos_div shift sign wrong, max-abs error 4.7 vs 1.7e-6 fixed), H3 confirmed. Three fixes are unit-verified on `llama.cpp-experimental-kshift-probe-20261006`. | **G2 FAIL at v10.** Not model-verified on the fixes. No design below uses K-shift. |
| G3 / CTX-3a cost (n=1 CPU microbench, extrapolated baselines) | **PASS.** Cached correction +2.4 ms/step at 262K and +9.4 ms at 1M (10 attention layers); uncached +13.5 / +46 ms. G = ceil(L/w): G=1 (zero cost) up to 262144, G=2 to 524288, G=4 at 1M. | The cost is small against the extrapolated baseline (about +2% decode above native, an estimate, not an end-to-end measurement). |
| Prototype tests (jetlong, synthetic single-layer harness, not the real model) | T1 in-window identity **max-abs exactly 0**; T2 above-native vs double-precision reference passes (tol 1e-3 rel, f32); T3 epoch crossing cached == uncached passes. | Inert in-window **by construction**: no graph node is built when every sequence has L <= 262144. |

Prototype limits (all must stay in the decision): it is non-fused, plain ggml ops in f32; above native it needs `-ub 32 -b 32`; it keeps a f32 side cache of **about 5 GiB at 1M** (the COST.md f16 C1 figure is 2.7 GB; the prototype is f32); a 300K prefill takes minutes, 524K roughly 1-2 h and 1M several hours; **no end-to-end run on the real model has been done** (no real-model identity, no MTP, no needle recall).

## 3. Option D RAM (computed)
The canonical :8070 recipe is `--no-mmap --mlock`, so a second server holds a private second weights copy (sharing page cache would be a recipe deviation and defeats NUMA interleave).
- Weights: `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` = 37,801,097,504 B = **35.2 GiB** (37.8 GB).
- KV at 1M, q8_0 (1.0625 B/elem): per token per layer = (2 heads x 256 K + 2 x 256 V) x 1.0625 = 1088 B; x 10 attention layers = 10,880 B/token; x 1,048,576 tokens = 11.41 GB = **10.6 GiB** (about 11.7 GiB if the MTP draft layer's own KV is counted at the same length). The 30 GDN layers have O(1) state.
- Compute buffers and GDN state: not measured; I assume 3-5 GiB at the canonical `-ub 2048`. **Estimate, unmeasured.**
- **Total added by D: about 49-52 GiB** (35.2 + 10.6 to 11.7 + 3-5).
- Host (`free -g`, 2026-10-06): total 1133 GiB, used 354, available 778, swap 7 (fully used, 0 free). D consumes about 6.5% of available RAM. **RAM does not reject D** at any headroom above about 60 GiB. D's real costs are CPU-core contention when both servers are busy and a second NUMA-interleaved mlock footprint, both unmeasured here; D also means two models/ports and routing by context length.

## 4. Options
**D: two servers (native :8070 unchanged; extended server with static YaRN for long requests).**
- Entails: second server, router rule by prompt+max_tokens length. In-window exact by construction (the native server is untouched). Above native equals static YaRN.
- Tradeoffs: zero kernel risk, available now, fully reversible; +49-52 GiB RAM and a second set of cores/NUMA when both are busy; a request that crosses native mid-way must be routed up front (same margin/truncate problem as F); MTP on the extended server drifts as in CTX-1.

**F: admission-time per-sequence native vs extended factors (per-token freq factors).**
- Entails: kernel work for per-token `ff` (and Q scale) in the rope path, one process. In-window exact by construction (native factors). Above native equals static YaRN quality. A sequence that crosses native mid-way cannot switch (re-rope is the unsafe K-shift path, G2 FAIL), so it needs a safety margin or a truncate rule at admission.
- Tradeoffs: no second weights copy; medium-low kernel risk, not started; G1 failing removes the "cheap scale" shortcut but not F itself. Cost: cannot serve a sequence that starts short and grows past native without a rule, which is a product limitation.

**J: cached Jet-Long (correction applied on read, base-RoPE K cache, near/distant split with grouped positions).**
- Entails: promote the prototype (`llama.cpp-experimental-jetlong-proto-20261006`, `a2e129fcc`/`b216a5deb`) to a fused kernel and a v11 candidate. In-window exact by construction (T1 = 0). Handles crossing sequences natively (T3). Cost estimated +2% decode above native (CTX-3a: +2.4/+9.4 ms; estimate, not end-to-end).
- Tradeoffs: highest engineering cost; prototype is non-fused and f32 with `-ub 32` above native and about 5 GiB side cache at 1M; above-native *quality vs static YaRN is unmeasured* (the method comes from a paper; needle recall on this model is not run); its MTP behaviour is untested (verify batches that straddle k*w use the larger G, expected small acceptance loss at each boundary only).

**Static YaRN everywhere (rejected baseline).** Simplest and what exists today. Fails the operator's native-window rule: 13/20 byte-identical in CTX-1 (Y), MTP at 34k 0.514 to 0.490. Listed only as the baseline; not recommended.

## 5. Recommendation
Conditional, in order:
1. **Now: adopt D as the interim path** if 1M/above-native service is wanted before J is proven. It is the only option that is exact in-window today with no kernel work; the 49-52 GiB RAM cost is small against 778 GiB available.
2. **Target: J, conditional on `JETLONG-LONGCTX-RUN`.** Promote J (over F) only if **gate A** passes (real-model, 20/20 + 20/20 identical tokens, identical MTP accepted counts, logits max-abs exactly 0 in-window) **and** needle recall at 300K/524K/1M shows J >= static YaRN on lenient recall (the CTX-5 rule). J beats F because it is exact in-window, handles crossing sequences, and needs no admission margin.
3. **Fall back to F** if J's gate A fails or J < YaRN on recall but static YaRN above native is acceptable; F is then built for per-token `ff`. If neither F nor J are funded, stay on D.
4. G2 is a standing no: do not use K-shift for crossing sequences at v10.

## 6. Still unmeasured (do not claim these)
- Real-model in-window identity and MTP acceptance for J (gate A). Only the synthetic single-layer T1 = 0 exists.
- Needle recall for J and for static YaRN at 300K/524K/1M on this model (all 15 cells: 5 needles x 3 seeds per length per depth).
- End-to-end decode tok/s at depth for J (+2% is a CTX-3a extrapolation against an extrapolated baseline).
- Fused-kernel behaviour; the prototype is non-fused and limited to `-ub 32` above native.
- D's CPU contention, compute-buffer size and NUMA effects (RAM total above uses an assumed 3-5 GiB for compute buffers).
- Whether the three K-shift fixes hold on the real model.

## 7. What the operator needs to decide
1. Approve J as the target design **conditional on gate A + recall**, and approve scheduling the CPU window for `JETLONG-LONGCTX-RUN` (the 1M arm takes several hours non-fused; 300K and 524K first is acceptable).
2. Name the headroom for D, and whether D ships as the interim path: this package says about 49-52 GiB of added RAM and that a router rule by context length is required.
3. Accept or reject the crossing-sequence rule for F/D (margin, or truncate at admission) in case J does not pass.

## 8. Default if no choice is made
Status quo: production stays on the native-window :8070 recipe with no above-native service; D and J are not started, `JETLONG-LONGCTX-RUN` stays unscheduled, and no kernel (v11) work begins. Static YaRN is not enabled.
