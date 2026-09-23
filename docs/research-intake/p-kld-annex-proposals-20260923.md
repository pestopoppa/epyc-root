# P-KLD annex — drafted wording proposals from research intake jev-exl3 (2026-09-23)

**Status: PROPOSALS ONLY — not the constitution, not the staged annex.** The staged annex
(`artifacts/operator/staged/p-kld-annex-20260915.md`, sha256 `094c6c19…5136f`) is untouched. Adoption is the
operator's call through the OP-38 ratify package (`autokernel-rebuild-program.md` → R23-47); a session may only prepare.

**What this is.** Nine dived sources bear on the annex. Each proposal below is keyed to an annex section, carries the
intake entry and ledger row it came from, and states the reason. Every source is `dive-verified` in
`research/intake_index.yaml`; per-claim anchors and second-reader results live on the entries.

| Intake | Source | Relation to the annex |
|---|---|---|
| intake-1507 | malaiwah/quant-fidelity-suite (QFS) @cf36287c | Sibling implementation of the same rtx6kpro protocol — **not independent corroboration** |
| intake-1508 | HF discussion brandonmusic/GLM-5.3-Flash-tr3-4bpw #1 | Worked example of a KV-cache treatment reported as a weight format |
| intake-1510 | arXiv 2606.19558 "Displacement Is Not Direction" | Corroborates V6/V8 (KLD gates damage, cannot rank near-baseline quality); authors' own quants in the cohort |
| intake-1511 | rtx6kpro `models/kimi-k3/distribution-fidelity-1024x2048.md` @2960b922 | Upstream of the V2 `body` estimand; tooling gaps vs V1/V7 |
| intake-1519 | arXiv 2407.09141 "Accuracy is Not All You Need" | Flips definition and flip floor; its MT-Bench headline is a pairing error (overturned) |
| intake-1520 | arXiv 2608.11212 (route flips in quantized MoE) | Upstream of V4 wording (rtx6kpro cites it) — **not independent corroboration** |
| intake-1524 | arXiv 2606.05688 (VSRAQ) | Only published weight-domain route-set agreement measurement (occurrence only) |

No proposal conflicts with the staged annex; all are refinements or clarifications. Grouped by annex section:

- **V1** — 1507.D2 (teacher provenance, `dequantized_from_quant`); 1510.D1 (name the floored top-k form as refused).
- **V2** — 1507.D5 (DSA/SWA scope limit); 1507.D6 (head-only degenerate case; GGUF output.weight); 1511.D1 (replay qualification against a pre-declared tolerance; head output dtype).
- **V3** — 1510.D1 (a task-stratified suite does not make KLD a quality proxy).
- **V4** — 1520.D1 (R×Q is an interchange intervention); 1520.D2 (margin is occurrence-only; per-layer flip rates at every MoE layer); 1520.D3 (every-position route replay; top-k normalization flag in the trace identity); 1511.D3 (route-control status line on every MoE receipt); 1524.D2 (route-set disagreement = per-layer mean top-k Jaccard beside its R×R floor); 1510.D1 ("codec ranking" → "fidelity ranking").
- **V5/V6** — 1507.D1 (bit-identical R×R repeat is a reproduction, not a floor); 1507.D4 (no cross-plane floor subtraction); 1511.D2 (floor LEVEL vs capture VARIABILITY); 1510.D1 (fidelity ordering ≠ quality ordering); 1519.D1 (task evidence = paired per-item flips vs an R-vs-R flip floor).
- **V8** — 1510.D1 (no secondary statistic converts a fidelity ranking into a quality ranking).
- **V9** — 1507.D3 + 1508.D2 (mandatory treatment field separating weight codec, KV type and activation scheme, with the v44 KV-as-weight mislabel as the worked example); 1510.D1 (refused "lower KLD ⇒ better" example).
- **Provenance** — 1511.D4 (2026-09-23 re-check: rtx6kpro `kld/README.md` @2960b922 differs from @44e817b by one results row only).

## Proposals verbatim (as drafted in the dives)

### Proposal 1507.D1
Draft named annex edit (V5/V6): an R×R repeat with bit-identical captures is a reproduction (exact 0), not a floor; δ must rest on a non-degenerate floor or declared instrument resolution (QFS SC-1/SC-2).
Reason: Real gap: V6 'δ > floor' is vacuous on deterministic planes; operator trust boundary, so a package edit only.

### Proposal 1507.D2
Draft named annex edit (V1): teacher-provenance. A BF16-stored reference of an FP8/FP4-native release is reference_kind=dequantized_from_quant unless audited; name it in the claim.
Reason: INF-77 DeepSeek-V4.1-Flash is FP8/FP4-native; the current dtype test passes an upcast.

### Proposal 1507.D3
Draft named annex edit (V9): a mandatory treatment / Q-identity field that separates weight codec, KV-cache type and activation scheme.
Reason: The intake-1508 mislabel is exactly a KV treatment reported as a weight format.

### Proposal 1507.D4
Draft named annex edit (V5): an unquantized-control or comparison floor from another stack/instrument/plane (CPU, IQK, GPU) is never subtracted and never a δ basis (BIAS-006 analog).
Reason: We run three compute planes; the annex is silent on cross-plane floors.

### Proposal 1507.D5
Draft named annex edit (V2 scope): a context below the DSA index_topk / SWA window cannot certify sparse-selection fidelity; declare it.
Reason: QFS issue #7 §4; applies to DSA (DeepSeek/GLM) and SWA models in our lineup.

### Proposal 1507.D6
Draft named annex note (V2 body): the head-only-quant degenerate case, and GGUF output.weight is usually quantized.
Reason: Small clarification that prevents a false 0.

### Proposal 1508.D2
Include the v44 mislabel as a worked example in the annex V9 treatment-field proposal (see intake-1507 D3).
Reason: Concrete motivating case for the operator package; prepare only.

### Proposal 1510.D1
Stage-3 drafted wording for the OP-38 P-KLD annex package, a PREPARE-only proposal (operator trust boundary). V6: add "A KLD, PPL or top-1 ordering among candidates that all satisfy the non-inferiority rule is a fidelity ordering, never a quality ordering. Selecting among them requires Annex Q evidence." V4: "For codec ranking, R×Q is the headline" becomes "For fidelity ranking of codecs, R×Q is the headline". V8: add "No secondary statistic (PPL ratio, Delta-log-PPL, top-1) converts a fidelity ranking into a quality ranking." V9: add the refused example "❌ `Q_a is better than Q_b (lower KLD)` — a fidelity ordering quoted as quality (§V6)". V3: add "A task-stratified KLD suite improves fidelity coverage; it does not make KLD a task-quality proxy." V1: name the floored top-k form (missing-token log-prob set to a constant) as a refused top-k variant. Corroboration check: annex lines 17-19, 43, 257-263 and 340-341 already require Annex Q task evidence. These edits are clarifications, not new requirements.
Reason: R23-47/OP-38 is the pending annex. The wording is a proposal for the operator's ratify package; a session may only prepare it.

### Proposal 1511.D1
OP-38 annex V2, `body` row, drafted wording (PREPARE-only). Add: "Before first use, a hidden-state replay path is qualified against live logits on a frozen subset. Report the mean/max/p99.9 replay KL and top-1 agreement against a tolerance DECLARED in advance. State whether the candidate's served head is the shared head. State the head matmul OUTPUT dtype (e.g. BF16-rounded logits) in addition to the log-softmax precision." V2 already demands "dtype and matmul precision"; S2 shows that a well-built protocol document can still omit them, so V2 should state them as a receipt field.
Reason: R23-47/OP-38 pending annex; operator trust boundary, so the dive only proposes wording.

### Proposal 1511.D2
OP-38 annex V5/V6, drafted wording. Distinguish (a) the floor LEVEL, the pairwise R×R repeat KL with its cluster CI, from (b) CAPTURE VARIABILITY, the spread of a candidate's mean KL across fresh captures. Operationalize "a difference comparable to the floor is inconclusive" (V6 L269) as: (i) for "no effect beyond floor", a paired excess-over-repeat on the same sentinel clusters (S2 route-reduction receipt pattern); (ii) for candidate-vs-candidate differences, at least 2 captures per arm, or the result is labelled single-capture. Also qualify "δ strictly greater than the R×R repeat floor" (V6 L265-L267): δ is a margin on a mean difference, and the floor level is not its noise.
Reason: The current V6 wording compares a mean-difference margin with a divergence level. The source's own flagship result shows the ambiguity in practice.

### Proposal 1511.D3
OP-38 annex V4, drafted wording. Add "Every MoE receipt carries an explicit route-control status line (e.g. `route-controlled decomposition: unsupported (Q×Q only)`)" and "A matched-control tensor overlay (same experts, different non-expert storage) isolates a tensor set, not the route; it is still Q×Q." Also V5: when a macro estimate is reported, the cluster bootstrap is stratified by allocation with fixed stratum weights.
Reason: S2 is a worked instance of THE RULE. Its status-line disclosure is the pattern to copy.

### Proposal 1511.D4
OP-38 annex provenance paragraph (L21-L25), drafted wording: record the 2026-09-23 re-check that kld/README.md @HEAD 2960b922 differs from @44e817b only by one results row, and name models/kimi-k3/distribution-fidelity-1024x2048.md as the lab's worked `body`-estimand reference.
Reason: Keeps the annex's provenance current without changing any rule.

### Proposal 1519.D1
Proposal to the operator (annex is PREPARE-ONLY): in the staged P-KLD annex §V6, extend the bullet "practical task evidence (Annex Q)" to read "paired per-item flips against R (C->I and I->C counted separately), measured greedily or read against an R-vs-R flip floor, never an aggregate accuracy delta". Evidence: S1 camera-ready Table 24, where two sampled 16-bit runs differ by 23.53% flips.
Reason: R23-47 owns the staged annex. The change sharpens what "task evidence" means in the V6 decision rule and adds the flip-floor requirement S1 itself demonstrates.

### Proposal 1520.D1
Proposal to the operator (staged annex, PREPARE-ONLY): in §V4's four-cell table, change the R×Q interpretation from "Candidate compute error, conditional on the reference path" to "Candidate compute error, conditional on the reference path. This is an interchange intervention: reference routes are read against candidate hidden states, so it is off-distribution and is not the natural compute-only effect." Evidence: 2608.11212 sec 3 estimand semantics.
Reason: R23-47 owns the staged annex. The source the V4 design descends from states this caveat explicitly, and the annex drops it.

### Proposal 1520.D2
Proposal: in §V4 "Also report", qualify "router-margin summaries" as "(flip-occurrence diagnostics only: margin predicts that a route flips, not whether the flip raises or lowers loss)". Qualify "per-layer flip rates" as "at every MoE layer: most route-mediated damage originates in upstream-layer flips, not the scored layer".
Reason: Margin->harm AUC 0.490 and the 45/55 jump/nonlocal split directly refine what these secondary statistics may be used for.

### Proposal 1520.D3
Proposal: in §V4 "Exact pinning versus ID pinning", add "Routes are replayed at EVERY context and scored position. A prefix-only route reference is a different estimand and is reported separately." Also name the model's top-k weight-normalization convention (e.g. norm_topk_prob) in the route-trace identity.
Reason: Prefix-only vs full-decode pinning moved Qwen3 recovery from 0.021 to 0.408. The normalization flag changes damage magnitude x7-10, so it is a load-bearing trace field.

### Proposal 1524.D2
Proposal to the operator (staged annex, PREPARE-ONLY; fold with intake-1520 D2): in §V4 "Also report", define route-set disagreement as "per-layer mean top-k Jaccard between R's and Q's selected expert sets on the scored positions, reported beside its R×R repeat floor".
Reason: R23-47 owns the staged annex. The current wording names the statistic but gives no definition, so two runs could report incomparable "flip rates". The Jaccard definition matches the only published weight-domain measurement of it.
