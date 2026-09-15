<!-- Annex V of MEASUREMENT.md. Same trust boundary and amendment rules as the core file.
     Protocol family: distribution divergence (KLD, perplexity, top-1 agreement).
     This file is installed byte-identically by
     artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh, which pins its SHA-256.
     The operator identity and the apply timestamp are recorded in
     artifacts/operator/ratify_p_kld_divergence_protocol_20260915.json, not here.
     A copy of this text anywhere other than measurement/protocols/divergence.md is a staged
     draft, not the constitution. -->

# Annex V — Distribution-divergence protocols (KLD, perplexity, top-1 agreement)

This annex has one protocol, `P-KLD-1`. It answers one question: *how far does a candidate `Q` move
the next-token distribution away from a named reference `R`, on exactly aligned teacher-forced
tokens?* It governs every KL-divergence, perplexity and top-1-agreement number used to compare two
artifacts, kernels, routes or configurations of the same model.

**KLD measures distribution fidelity and nothing else.** It does not measure correctness,
capability, generation stability or preference. A divergence number never replaces a quality
protocol (Annex Q) or a coherence gate, and neither of those replaces it (§V8).

Provenance. This text is distilled from the Local Inference Lab protocol `kld/README.md` at
`local-inference-lab/rtx6kpro` commit `44e817b`, adopted through research intake
`docs/research-intake/rtx6kpro-20260907.md` item 4.5. It was then adapted to our instrument:
`llama-perplexity` in the frozen `production-consolidated-v9` tree, re-read at `0db32c06e` for this
annex. Every clause marked **(ours)** is an adaptation that the source does not contain.

## P-KLD-1 — Teacher-forced next-token distribution divergence

**Scope.** Any claim that candidate `Q` changes the next-token distribution of reference `R`. The
factor under test may be:

- a weight quantization or codec;
- a per-tensor precision swap (PLE, router, head, shared expert);
- a kernel or route change;
- a KV-cache type;
- a graph change;
- a speculative path, but only when that path is the declared treatment.

The protocol does **not** cover:

- two different models;
- two tokenizers or vocabularies. A vocabulary mismatch is refused, not reported (§V7).
- capability or task quality, which is Annex Q.
- bit-identity. A claim that two distributions are *identical* is an Annex D verdict, not a
  P-KLD-1 number.

**Primary metric.** Forward `KL(R‖Q)` in nats: the arithmetic mean of `KL_t` over all scored
positions. **Lower is better.** The secondary metrics are in §V5. None of them replaces the forward
KLD.

```text
p_t    = softmax(z_t^R)                 # reference logits
q_t    = softmax(z_t^Q)                 # candidate logits
KL_t   = Σ_{v ∈ V} p_t[v] · (log p_t[v] − log q_t[v])
```

### V1. Full vocabulary, fp64 sums, direction, alignment

- **Full vocabulary only.** Every entry of `V` is compared. Top-k log-probabilities are
  insufficient. A KLD derived from a server's `n_probs` / `logprobs` top-k output is **not** a
  P-KLD-1 number. Exact streaming is allowed: a comparator may process the vocabulary in chunks and
  keep only sufficient statistics, provided it computes the same full-vocabulary `logsumexp` and
  weighted sum as the dense formula. A top-k approximation is not exact streaming.
- **Precision.** Compute `log_softmax` / `logsumexp` in at least FP32. Accumulate every summary
  sum in **FP64**: `Σ KL_t`, `Σ KL_t²`, the per-cluster sums, and the NLL sums.
- **Direction.** `KL(R‖Q)` is asymmetric. Name `R` and `Q` explicitly and preserve their order.
  Label the reference `BF16` only when both the checkpoint and the measured compute actually are
  BF16. A result against a Q8_0 or IQ4_XS reference is `KL(Q8_0‖Q)` or `KL(IQ4_XS‖Q)`, and it must
  never be quoted as `KL(BF16‖Q)`. **(ours)** If `R` and `Q` come from different checkpoint
  lineages (different source weights, a different imatrix, a different converter), the result
  mixes quantization error with checkpoint change. It must say so.
- **Alignment.** Both operands consume identical stored token IDs at identical positions. Load
  stored token IDs directly and never re-tokenize the source text. Record the vocabulary identity
  (size plus tokenizer hash). A shape, vocabulary or token-ID mismatch is a refusal (§V7).
- **Negative values.** A per-token `KL_t` below zero by more than the declared numerical tolerance
  is an **error**. Count it and report it. Never clamp it.
- **(ours) The `llama-perplexity --kl-divergence` instrument is NOT exact full-vocabulary.**
  Verified in `tools/perplexity/perplexity.cpp` at `0db32c06e`:
  1. **The reference is stored lossy.** At `:79-106` the base file keeps each position's
     log-probabilities as `uint16` over a window `[max_logit − 16, max_logit]`. Each step is at
     most `16/65535 ≈ 2.44e-4` nats. Every logit more than 16 below the maximum is floored.
  2. **The sum is truncated.** At `:221-231` the comparator skips every reference entry with
     `log p ≤ −16`, so reference mass below that floor never enters the sum. The tool neither
     reports that dropped mass nor bounds its contribution. The worst case is `|V|·e^−16` of
     probability mass, which is about 0.017 for `|V| = 151,936`.
  3. **Precision meets the floor above.** Per-token terms are computed in `float` and
     accumulated in `double`.
  4. **Only the second half of each chunk is scored.** Positions run from `n_ctx/2` to
     `n_ctx − 2` (`:1758-1760`, `:1792`).

  The tool is admissible under P-KLD-1 only as the declared instrument
  `instrument=llama-perplexity-u16w16`. Three conditions apply:
  - its scored-position rule is stated;
  - its resolution is characterized by an `R`-versus-`R` self-comparison (§V5, repeat floor);
  - it is **not** used to resolve a difference comparable to its quantization step or its
    truncation.

  Such differences need an exact comparator (`instrument=exact-fullvocab`).
- **(ours) The `±` that `llama-perplexity` prints is not an interval under this protocol.** At
  `:1769-1776` it is a per-token standard error, `sqrt(var/(count−1))` over token positions, and it
  treats every position as independent. So are the printed `±` on PPL, on the log-PPL ratio and on
  "same top p", and every `Nσ` computed from them. See §V5.

### V2. Declared estimand, before capture

A result is interpretable only when the report states, **before capture**, which difference it
estimates. A divergence number without a declared estimand is an **observation**.

| `estimand=` | Required comparison | What it contains |
|---|---|---|
| `end-to-end` | Natural `R` versus natural `Q` | Checkpoint, quantized tensors, kernels, router changes and every other unfrozen runtime difference |
| `body` | One shared canonical LM head over both operands' final hidden states | Everything upstream of the head. Excludes candidate head error. The shared head's identity, hash, dtype and matmul precision must be named |
| `fixed-route` | Reference routes and consumed route weights replayed through candidate compute (`R×Q`) | Candidate compute error, conditional on the reference routing path |
| `four-cell` | All four route × compute cells (§V4) | Separates route changes from compute changes and exposes their interaction |

**Freeze every non-treatment variable.** Those are:

- source checkpoint lineage, tokenizer and chat template;
- KV-cache dtype. **(ours)** Default is `-ctk f16 -ctv f16`, per Annex D's quantized-KV confound.
- context length and scored-position rule;
- `n_batch`, `n_ubatch`, `n_seq` and thread count. **(ours)** Batch invariance is not a property
  of any of our three compute planes (Annex D, P-PARITY-1), so these are numerics, not tuning.
- flash-attention mode, `GGML_IQK` state, backend, route-logging environment and graph mode;
- build commit and binary digest. **(ours)** For a GPU operand, add proven residency
  (`verify_ggml_linkage.sh`, VRAM sampled during the run), because invoking a HIP build is not
  evidence of a HIP run.
- MTP and every other speculative path: **disabled** unless it is the declared treatment. Capture
  only the target model's canonical output, never a draft head.

A variable that cannot be frozen is named **as part of the treatment**. The result is then not
attributed to the codec alone.

### V3. Evaluation data — document clusters, partitions, contamination

Three datasets have different roles and must never be conflated:

1. **Quantizer calibration corpus.** **(ours)** For GGUF this includes the imatrix text. It
   estimates scales and clipping when the candidate is built.
2. **KLD analysis partition.** Used for debugging, codec tuning and choosing the acceptance rule.
3. **KLD qualification partition.** Read **once**, and only after the candidate configuration and
   the decision rule are frozen (§V6).

There is no universal calibration corpus and no universal KLD corpus. The KLD suite is a frozen,
stratified sample of intended use: prose, technical text, dialogue and instructions, code, formal
reasoning, the supported languages, and structured or tool-shaped text, in declared proportions.

Each context records:

- source dataset and immutable revision;
- **source document or repository cluster id**;
- extraction rule and deterministic offset;
- exact token IDs, tokenizer revision, token hash and content hash;
- allocation stratum and partition.

- **Source-document clusters are the independent sampling units.** Contexts cut from one document or
  one repository are correlated. They stay in the same partition and are resampled together.
- **(ours)** `llama-perplexity` on a single concatenated text file (e.g. WikiText-2 `wiki.test.raw`)
  cuts chunks at fixed token offsets. **A chunk is not a document, and a chunk index is not a
  cluster id.** Such a run supports a cluster interval only after a declared chunk → source-article
  mapping. Without one it is a single-source suite with no admissible interval.
- **Contamination checks** run at more than one granularity: exact-content hashes, token or
  character n-gram overlap, and an approximate shingle method such as MinHash. They cover the
  calibration corpus, both KLD partitions and the capability benchmarks. If the calibration corpus
  is unknown (the case for most third-party GGUFs), record it as `unknown`. Never assert
  independence.

### V4. MoE route control — before attributing KLD to the codec

Hard top-k routing is discontinuous. A small upstream numerical difference can flip an expert
selection, and every later hidden state and route then follows a different trajectory.
Natural-route KLD on a MoE therefore mixes routing flips with compute error. Two codecs can show
similar deployed-path divergence while their error on the *same* expert path differs substantially.

**Four-cell design.** The left symbol names the source of expert IDs and consumed route weights.
The right symbol names the compute precision. With a real BF16 reference, write `B` for `R`.

| Cell | Expert IDs and consumed weights | Compute | Interpretation |
|---|---|---|---|
| `R×R` | Natural reference routes | Reference | Reference and runtime-repeat floor |
| `R×Q` | Reference routes replayed verbatim | Candidate | Candidate compute error, conditional on the reference path |
| `Q×R` | Natural candidate routes transplanted verbatim | Reference | Diagnostic: the candidate's routing schedule under reference compute |
| `Q×Q` | Natural candidate routes | Candidate | Deployed-path divergence |

- **THE RULE.** On a MoE model, **no KLD may be attributed to the codec, quantization, precision
  swap or kernel unless a route-pinned `R×Q` cell was measured.** A natural-route `Q×Q` number is
  reportable **only** as `estimand=end-to-end`. It may not be quoted as "the codec's damage".
- For codec ranking, `R×Q` is the headline. Report `Q×Q` beside it as the deployed-path divergence,
  and `Q×R` as a routing diagnostic when it is available.
- **Exact pinning versus ID pinning.** An exact pinned-route run captures and replays five things:
  - logical expert IDs, before any load-balancing remap;
  - the exact post-selection route weights the expert kernel consumed, including normalization
    and bias-correction semantics;
  - `(context_id, position, layer, route_slot)` identity;
  - top-k width, expert count, route order, dtype, shape and hashes;
  - the originating checkpoint and run.

  A run that replays IDs but recomputes the weights is `route=id-pinned`, not exact `R×Q`, and is
  reported separately. Three things invalidate the intervention: reordering or renormalizing the
  weights, substituting physical indices, or accepting a missing token or layer entry. The runner
  fails closed on any of them (§V7).
- **No additive decomposition.** `Q×Q` is not the sum of compute damage and routing damage: the
  factors interact and KLD is nonlinear. A statement such as "X% of the divergence is routing"
  needs a declared causal estimand, a denominator and a cluster-bootstrap interval.
- **Also report**, where available: route-set disagreement, per-layer flip rates, expert
  replacements and router-margin summaries.
- **(ours) Our stack today.** No route capture/replay path is qualified on our stack. The v9 graph
  builder accepts an externally supplied selected-experts tensor (`src/llama-graph.cpp:1892`,
  `:1982`), but that is an internal hook, not a qualified replay. An `R×Q` cell requires an
  implementation on an experimental branch, qualified before first use. Qualification means: replay
  the natural `R×R` routes through reference compute and reproduce the natural `R×R` logits
  bit-identically, or within a declared tolerance, on a frozen subset.
- **Dense models** declare `route=n/a-dense`, and this section does not apply.

### V5. Required statistics

Publish at least:

- per-token `KL_t`: micro mean, median, p95, p99, p99.9 and maximum;
- macro mean over the frozen strata, and estimates by stratum and by context-depth bucket;
- secondary metrics: Jensen–Shannon divergence, top-1 agreement (↑), and the paired
  `ln(PPL(Q)/PPL(R))` (§V8);
- the highest-KLD and most top-1-discordant contexts, with their source identities;
- **(ours)** the count of negative `KL_t` beyond tolerance. For a truncated instrument, the
  reference mass it dropped, or the statement that it could not be measured.
- the runtime repeat floor (below);
- for a MoE, all measured cells from §V4.

**Uncertainty is a source-cluster bootstrap. Never a per-token standard error.**

- Resample source clusters, not token positions. Millions of positions are not millions of
  independent samples.
- Candidate-versus-candidate and candidate-versus-reference *differences* use **paired**
  resampling: the same clusters and the same positions on both sides.
- Report the 95% interval, the resampling count `B` and the seed. **(ours)** An interval with
  `B < 1000`, or with fewer than 20 source clusters in the resampled partition, is not a P-KLD-1
  interval.
- **(ours)** A per-token SE, or an `Nσ` multiple built from one, may be printed for debugging. It
  is **not decision-grade** and must never appear in a claim.

**Runtime repeat floor.** Repeat a stratified sentinel subset in fresh processes for `R` (and for
`Q` when it is quoted alone). The `R×R` repeat distribution is the floor any difference is read
against. **(ours)** Because batch invariance is not held here, the floor is measured at the frozen
`n_batch` / `n_ubatch` / thread count and is not transferable to another setting.

### V6. No universal bands — the decision rule

**No model-independent KLD, PPL or top-1 band is supported.** Examples of refused bands:

- "below 0.01 nats is near-lossless";
- "same-top-1 above 99% is fine";
- "ΔPPL under 1% is free";
- "PPL 5.0 is healthy".

None of these may gate a decision. Where one appears in a handoff or gate definition, it is an
observation until a model-specific rule replaces it.

An acceptance rule is set **per model and per artifact**, and **frozen before the qualification
partition is read**. It is based on:

- the runtime repeat floor;
- the paired cluster-bootstrap uncertainty;
- practical task evidence (Annex Q);
- the smallest difference the study is designed to resolve.

**(ours) Decision rule form.** Pre-register a non-inferiority margin `δ` in nats on the declared
estimand, with `δ` strictly greater than the `R×R` repeat floor. The candidate is non-inferior when
the **upper** 95% cluster-bootstrap bound of the paired mean difference is below `δ`.

- A difference comparable to the repeat floor is **inconclusive**.
- A null result states its power and its fired-knob control under BOUNDED-NULL-1. For a precision
  swap, the control is proof that the swapped tensor was actually loaded at the new type.

### V7. Fail-closed runner and receipts

**The runner fails closed.** It exits non-zero and writes **no** metrics file when any of these
occurs:

- vocabulary size or tokenizer hash mismatch between operands;
- token-ID or position misalignment, a shape mismatch, or any missing `(context, position)`
  capture;
- NaN or Inf in any logit or any `KL_t`;
- a negative `KL_t` beyond the declared tolerance;
- a route-trace entry that is missing, reordered, renormalized or hash-mismatched (§V4);
- a build commit, binary digest, `GGML_IQK` state or residency proof that does not match the
  declared runtime record;
- a reference capture whose hash differs from the one recorded when it was produced;
- a qualification-partition read without a hashed freeze manifest committed first.

A partial result is never reported as a result.

**Minimum receipt** (equivalent layouts are acceptable if the same identities and checks are
present):

```text
suite-manifest.json        corpus, strata, partitions, token identities, freeze-manifest hash
source-registry.json       source revisions and cluster identities
tokens/                    exact per-context token IDs
reference-runtime.json     checkpoint + hashes, build commit + binary digest, env, launch args, host
candidate-runtime.json     same fields for the candidate
reference-capture/         logits, hidden states, or the u16w16 base file (or hash + provenance)
candidate-capture/         same
routes/{reference,candidate}/   logical IDs + consumed weights, when route-controlled
comparison.json            all §V5 statistics, numerical settings, instrument id, input hashes
paired-comparison.json     paired cluster-bootstrap estimates (B, seed)
validation/                repeat floor, replay qualification, overlap and structural checks
SHA256SUMS
```

**(ours)** Receipts backing any decision live under `epyc-inference-research/data/<campaign>/`, per
the §5 durability clause. Captures too large to keep (multi-GiB base-logit files) are recorded
hash-and-provenance-only, and the citation says so. **A deleted reference capture cannot be
re-bootstrapped.** A decision that may need re-derivation therefore retains its per-token `KL_t`
vector and the cluster mapping, which are small, even when the capture itself is reclaimed.

### V8. How perplexity, top-1 agreement and coherence relate to KLD

- **Perplexity is not a fidelity metric.** `PPL = exp(mean NLL)` of the *observed corpus token*. It
  measures fit to the text, not agreement with `R`.
  - The paired `ln(PPL(Q)/PPL(R))` is the mean of a **signed** per-position difference, so errors
    in opposite directions cancel.
  - `KL_t ≥ 0` at every position, and it weights every vocabulary entry by `R`'s own probability.
  - Hence PPL can be unchanged, or even improve, while the distribution moves substantially.

  Consequences:
  - ΔPPL is a **secondary** P-KLD-1 statistic. It is reported beside the KLD and never substitutes
    for it in a fidelity claim.
  - A "PPL null" is not a fidelity null.
  - A PPL number follows the same corpus, cluster-bootstrap and grammar rules as a KLD number.
  - A **single-arm** absolute PPL with no reference ("PPL 5.02, healthy") is an observation about
    fit to one corpus. It is not a divergence claim.
- **Top-1 agreement** ("same top p") is secondary. It sees only the argmax and is blind to
  everything below it. Its interval is a cluster bootstrap, never the per-token binomial `±`.
- **Coherence** is a verdict on free-running generation at production length. Teacher-forced KLD at
  one context length does not measure error accumulation during free generation. **Neither
  substitutes for the other:**
  - a low KLD does not clear a coherence gate;
  - a coherence pass does not bound divergence;
  - a coherence classifier label such as "23 COHERENT" is not a divergence number.

  A deployment-fidelity argument needs the declared P-KLD-1 estimand **and** the coherence gate
  **and** the role's quality protocol.
- **(ours) Speculative acceptance `α`** measures agreement between draft and target. It is neither
  a fidelity metric of the target nor a coherence verdict, and it may not be quoted as either.
- **Identity.** A claim that two configurations produce identical logits or tokens is an Annex D
  verdict (`P-PARITY-1` / `P-NONDET-1`). A bit-identical PPL across arms is supporting evidence for
  such a verdict. It is not a P-KLD-1 measurement.

### V9. Claim grammar for divergence numbers

A divergence claim carries these fields, in addition to §3 of the core file (`category`,
`instrument_class`):

```text
<statistic> <value> nats KL(<R>‖<Q>)
  model=<model>  estimand=<end-to-end|body|fixed-route|four-cell>
  route=<natural|exact-pinned|id-pinned|n/a-dense>
  instrument=<exact-fullvocab|llama-perplexity-u16w16|…>
  corpus=<suite-id>@<revision>/<analysis|qualification>  clusters=<n>  positions=<n>
  CI95=[<lo>, <hi>] (source-cluster bootstrap, paired=<yes|no>, B=<n>, seed=<s>)
  floor=<R×R repeat value>
  [P-KLD-1, n=<clusters>, <date>, attest <receipt path>]
```

- `instrument_class` for a teacher-forced capture is `bench`. A divergence number is never an
  absolute serving headline (INSTRUMENT-CLASS-1).
- The `n=` field of the claim tuple counts **source clusters**, not token positions and not chunks.
- A secondary statistic uses the same fields and names itself, e.g.
  `ln(PPL(Q)/PPL(R)) <value>` or `top1_agree <value>%`.
- ❌ `Mean KLD 0.0649 ± 0.0017, t = 37.9σ` — no reference named, no estimand, a per-token SE and a σ
  multiple built from it, no cluster count, and on a MoE with no route cell.
- ❌ `quality identical: PPL null (MDE 1.04%)` — a PPL null is not a fidelity null. Its MDE is
  derived from a per-token SE, and it states no cluster count.
- ❌ `r16 is near-lossless (KLD < 0.01)` — a universal band (§V6).
- ❌ `α 0.8209 → 0.8249 — coherence identical` — acceptance is not coherence (§V8).
- ✅ template:
  `mean KL(<R>‖<Q>) <v> nats, model=<m>, estimand=fixed-route, route=exact-pinned, instrument=exact-fullvocab, corpus=<suite>@<rev>/qualification, clusters=<n>, positions=<n>, CI95=[<lo>,<hi>] (paired cluster bootstrap, B=10000, seed=<s>), floor=<f>, category=CANDIDATE, instrument_class=bench [P-KLD-1, n=<n>, <date>, attest epyc-inference-research/data/<campaign>/comparison.json]`

### V10. Numbers recorded before this annex

The core file's §6 verbs apply. **(ours)** A divergence, PPL or top-1 number recorded before this
annex was ratified is `demote-to-prior` unless all of these hold:

- its receipt establishes every §V9 field;
- it used an exact or declared instrument;
- it has a cluster-bootstrap interval;
- on a MoE, it has an `R×Q` cell.

A demoted number may shape hypotheses and ordering. It may not gate a keep, revert, deploy,
promote, delete or close decision. **Deterministic replay comes first (§5):** where the per-token
`KL_t` values and a cluster mapping survive, re-derive the interval by cluster bootstrap *without
new inference*, and retro-certify only the fields the surviving receipt actually proves. The primary
records are never edited.
