# Deep Dive: OpenAI Privacy Filter — Small-MoE PII Preprocessor

**Date**: 2026-04-23
**Intake**: intake-449 (huggingface.co/openai/privacy-filter)
**Release**: 2026-04-22 (one day old at time of writing)
**Question**: Does this model belong in any EPYC pipeline, and are its architectural choices useful as design references even if we never deploy it?

## Executive Summary

**Do not deploy. Do read as a design reference.** The OpenAI Privacy Filter is a very strong PII token-classifier (96–97% F1 on PII-Masking-300k; 94.3% F1 on OpenAI's internal eval vs ~30% for Llama baselines and 13.9% for Piiranha). The problem is that we do not currently have a workload that needs PII masking. Our orchestrator is a research/inference stack, not a user-data-handling product; the KB ingests research papers, not customer conversations.

**What makes this worth more than a one-line note** is the architectural bundle. This is the first publicly-released small-MoE (50M active / 1.5B total, ~3.3% active) bidirectional encoder with 128-expert / top-4 routing, banded attention (band=128, 257-token effective window) at 128k context, and an unusual **autoregressive-pretrain → bidirectional-encoder conversion** recipe. Every one of those choices is a design reference point for any small-model preprocessor we might build — a router classifier, a difficulty estimator, a prompt-injection detector, etc. The economics (50M active params, WebGPU-deployable, Apache-2.0) are exactly what we'd want for an always-on filter in the orchestrator.

## Technique Analysis

### What the model does

Takes a text input (up to 128k tokens), emits per-token BIOES labels over 8 PII span classes plus background, decodes coherent spans with constrained Viterbi. Output categories: `account_number`, `private_address`, `private_email`, `private_person`, `private_phone`, `private_url`, `private_date`, `secret`. Total token-level output: 33 classes (1 `O` + 8 span types × 4 BIOES tags).

### Architecture

| Component | Detail |
|-----------|--------|
| Parameters total | 1.5B |
| Parameters active per token | 50M (**3.3% of total**) |
| Layers | 8 pre-norm transformer blocks |
| d_model | 640 |
| Attention | Grouped-query (14Q / 2KV, group=7), rotary positional embedding |
| Attention pattern | Banded, band=128, **257-token effective window per layer** |
| Feed-forward | Sparse MoE, **128 experts**, **top-4 routing** (3.1% expert-active) |
| Output head | Token classification over 33 BIOES × PII classes |
| Context | 128k tokens, no chunking |
| Pretraining | Autoregressive (GPT-style) |
| Conversion | Fine-tuned as bidirectional encoder + token classifier |
| Formats | BF16 + F32 safetensors; runnable on WebGPU with q4 dtype |
| License | Apache 2.0 |

### Why each of those choices matters

1. **50M active / 1.5B total = 3.3% active.** This is substantially sparser than our production hybrid MoEs (Qwen3.5/3.6-35B-A3B is 3B/35B ≈ 8.6% active). A task-specific preprocessor can push sparsity further because it does not need full linguistic capacity — the model just needs to activate the 4 experts that recognize "email addresses" or "phone numbers" for the current token. Lesson: for future small-MoE classifiers / routers we build, do not assume 8–10% active is the floor; 3% is viable for narrow tasks.

2. **128 experts / top-4 = 3.1% per-token routing.** The ratio of expert count to active count (128:4) gives the router 32-way discrimination before any token touches compute. That granularity matters for multi-class tasks (8 PII classes here; could be many more in a router model). Reference point for any learned-routing classifier we build (see `project_learned_routing_controller` memory — Phase 1 MLP uses dense classification, could be MoE-ified).

3. **Banded attention, band=128, effective 257-token window.** 128k context through local windows only; no global attention at all. This works because PII is a local signal — an email address is self-contained, a name is in a sentence. Over 8 layers with overlapping bands, the effective receptive field grows but stays sub-linear. Reference point for: any EPYC preprocessor whose task is locally-decidable (including CSAM filtering, spam detection, citation-reference matching in the KB). The model demonstrates that you can honestly serve 128k context with purely local attention if the task allows.

4. **Autoregressive-pretrain → bidirectional-encoder conversion.** This is the unusual choice. Typical encoder models (BERT-family) are pretrained with masked-language-modeling on bidirectional attention from the start. OpenAI instead pretrained with causal attention (GPT-style), then during fine-tuning flipped to bidirectional attention + added a token-classification head. Advantages they presumably exploit: (a) AR pretraining has better compute utilization (no [MASK] tokens discarded); (b) the pretrained weights transfer fine despite the attention-mask flip, because the dense-matrix knowledge is mask-independent; (c) reuses existing GPT-style training infrastructure. Reference point for: if we ever fine-tune a task-specific preprocessor from our own Qwen3.5/3.6 checkpoints, this is prior art for the AR→bidirectional conversion, avoiding the need to pretrain an encoder-only model from scratch.

### Reported results

| Benchmark | F1 | Precision | Recall | Source |
|-----------|------|-----------|--------|--------|
| PII-Masking-300k (raw) | 96.00% | 94.04% | 98.04% | OpenAI blog |
| PII-Masking-300k (corrected, dataset annotation fixes) | 97.43% | 96.79% | 98.08% | OpenAI blog + model card |
| OpenAI internal eval (domain-specific) | 94.3% | — | — | OpenAI blog |
| vs Llama-family NER baselines (internal eval) | <30% F1 | — | — | OpenAI blog |
| vs Piiranha (internal eval) | 13.9% F1 | — | — | OpenAI blog |
| Fine-tune on small domain data | 54% → 96% F1 | — | — | OpenAI blog |

The Llama/Piiranha numbers should be read carefully: Piiranha reports **98%+ catch rate** on its own multilingual benchmarks (Protecto review), so the 13.9% on OpenAI's internal eval is a domain-shift artifact, not a fair head-to-head. The honest summary is: on PII-Masking-300k (an independent third-party benchmark), this model achieves 96–97% F1, which is genuinely strong. The internal-eval comparisons are marketing, not evidence.

## Cross-Reference to EPYC Stack

### What this DOESN'T change

- **No current handoff needs PII masking.** The orchestrator does not expose user data externally; the KB does not ingest user-generated content. The `opendataloader-pipeline-integration` handoff has "No prompt injection filtering" as gap #5 — but prompt-injection and PII are different problems. The privacy filter does not close that gap.
- **No inference-speed lesson for our stack.** This is an encoder, not a generator. Its throughput characteristics (single forward pass over the input, no KV-cache, no sequential decode) do not transfer to our generative Qwen3.5/3.6 workloads.
- **No quantization/compression lesson for our stack.** The Apache-2.0 weights are BF16/F32 safetensors, not GGUF. WebGPU q4 is a runtime-quant, not a production path for CPU inference.

### What this DOES change (lightly)

1. **Architectural reference library +3 entries.** The 3.3%-active small-MoE ratio, the 128/top-4 routing granularity, and the AR→bidirectional conversion recipe all become reference points for future small-model preprocessors we might build. Concrete candidates from our active handoffs:
   - **`project_learned_routing_controller`** (Phase 1.5-3 pending): if we upgrade the MLP classifier to MoE, the 128-expert / top-4 sparsity pattern is the strongest demonstrated precedent at this scale.
   - **Meta-harness optimization** (if task difficulty classifier ever gets built): same pattern.
2. **Deployment pattern for task-specific preprocessors.** 50M active + 128k context + WebGPU-runnable + Apache-2.0 is the template for any always-on text classifier in an agent stack. Noted.
3. **Tool bookmarked for three specific future triggers** (any one of which would change the relevance calc):
   - Orchestrator exposes third-party user data → input sanitization.
   - KB begins ingesting user-generated text → ingestion-time scrub.
   - We begin SFT on conversation logs → training-data hygiene.

### What's genuinely NOT portable

- **Encoder-only inference.** Our llama.cpp backend is designed for causal LM; running an encoder-mode bidirectional model through llama.cpp would require a separate code path (if supported at all). Realistically any EPYC deployment would be via Transformers/PyTorch on CPU, not through our existing server stack.
- **128k-context banded attention.** Our existing KV quantization and attention-matching work (production) are causal-attention-specific. Banded bidirectional attention is a separate implementation with no overlap.

## Adoption Posture

| Trigger | Action |
|--------|--------|
| **Now** | Do not deploy. Do not add to any pipeline. Keep as a catalogued design reference. |
| **Small-MoE classifier project kicks off** (routing controller Phase 1.5-3, meta-harness difficulty classifier, etc.) | Re-read this deep-dive; use the 128/top-4 sparsity + AR→bidirectional conversion as precedent citations in the design doc. |
| **User-data-handling use case emerges** | Evaluate head-to-head vs Presidio + Piiranha on our specific data distribution before choosing. The OpenAI model's 96% on PII-Masking-300k does not guarantee 96% on our data. |
| **Someone proposes running this in the orchestrator** | Push back: it does not solve prompt injection (gap #5 in `opendataloader-pipeline-integration`), and we do not have a PII problem. Adding it is infra complexity with no closed-loop benefit. |

## Risks and Caveats

1. **Self-reported benchmarks, one day old.** 97.43% F1 is OpenAI's number; no third-party replication yet. The 96% raw-dataset number is more trustworthy (standard benchmark); the "corrected" 97.43% involved OpenAI fixing annotations in the eval set, which is a methodological red flag even if the fixes were genuine.
2. **English-and-Latin-script bias explicitly acknowledged.** Performance degrades on non-English text, non-Latin scripts, and regional naming conventions. Any deployment needs to specify the expected data distribution.
3. **Failure modes documented by OpenAI itself**: under-detection of uncommon names, over-redaction of public entities (organizations, locations), span-boundary fragmentation in mixed-format text, missed secrets for novel credential formats. These are the "98% recall but not 100%" tails that matter most in high-sensitivity settings.
4. **Commercial bias signal**: the announcement frames this as "open-source tool that scrubs your secrets before ChatGPT ever sees them" (Decrypt headline). The primary use case OpenAI is promoting is **sanitizing user input before sending to ChatGPT API** — i.e., the model exists partly to make OpenAI's API more enterprise-palatable. This is not a problem with the model, but it does mean the incentives for quality claims are not fully aligned with pure research transparency.
5. **Not an anonymization guarantee.** OpenAI is explicit: "not an anonymization tool, a compliance certification, or a substitute for policy review." A real compliance pipeline still needs HIPAA/GDPR-specific review, audit logs, and exhaustive testing on the domain data.

## Open Questions

- Does the AR-pretrain → bidirectional-encoder conversion recipe work as a post-hoc technique on our existing Qwen3.5/3.6 checkpoints? If yes, it's a cheap way to produce task-specific encoders from our own pretrained weights.
- What is the wall-clock throughput on EPYC CPU (no GPU)? OpenAI doesn't disclose. Given 50M active params and 257-token effective attention, we'd expect very fast (hundreds of tok/s easily) on our hardware — but not measured.
- Is the 128-expert top-4 MoE actually better than a dense 50M model at this size, or is the sparsity a deployment optimization rather than a quality win? (Probably the latter — sparse routing at this small scale mostly buys speed, not quality — but worth verifying before citing this as precedent for a MoE router.)
- How does this model compare to [GLiNER](https://github.com/urchade/GLiNER) on PII-Masking-300k? GLiNER's zero-shot flexibility is a different value proposition; a direct F1 comparison on the same benchmark would clarify whether the OpenAI model's quality gain is worth the architectural complexity.

## References

- Primary: https://huggingface.co/openai/privacy-filter
- Repo: https://github.com/openai/privacy-filter
- Model Card PDF: https://cdn.openai.com/pdf/c66281ed-b638-456a-8ce1-97e9f5264a90/OpenAI-Privacy-Filter-Model-Card.pdf
- Announcement (403 on our fetch): https://openai.com/index/introducing-openai-privacy-filter/
- Coverage: Decrypt, Bloomberg Law, BetaNews, Help Net Security, VentureBeat, Phemex (all 2026-04-22/23)
- Third-party review context: [Protecto NER comparison](https://www.protecto.ai/blog/best-ner-models-for-pii-identification/)
- Comparable tools: Microsoft Presidio, Piiranha, GLiNER, AWS Comprehend
- Related EPYC handoffs: `opendataloader-pipeline-integration.md` (adjacent pipeline), `routing-intelligence.md` (architectural analogy for small-MoE classifiers)
- Related memory: `project_learned_routing_controller` (MLP routing classifier, potential MoE upgrade path), `feedback_opensource_only` (Apache-2.0 satisfies constraint), `feedback_dont_dismiss_creative_uses`
