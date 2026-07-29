# ConceptLM Monitoring

**Status**: STALE (watch-only — no concept-level models available as of 2026-04-11)
**Created**: 2026-03-03
**Priority**: P3 — no action required, monitor for developments
**Effort**: None (monitoring only)
**Source**: [ConceptLM (arxiv.org/pdf/2602.08984)](https://arxiv.org/pdf/2602.08984) | [Substack breakdown](https://arxiviq.substack.com/p/next-concept-prediction-in-discrete)

## Research Review

### ConceptLM: Next Concept Prediction in Discrete Latent Space
**Authors:** Yuliang Liu, Yunchong Song, Yixuan Wang et al.

Instead of next-token prediction, ConceptLM predicts the next *concept* (a discrete latent vector representing k-token spans) then decodes back to tokens. Uses vector quantization to create a semantic codebook. Achieves **37% fewer parameters** and **24% fewer training tokens** for equivalent performance vs GPT-2/Pythia baselines. Improved MMLU, HellaSwag, RACE scores.

**Orchestrator Relevance: LOW-MEDIUM (long-term).** This is a pretraining paradigm shift, not something we can adopt directly with existing inference models. However, the conceptual insight is valuable:
- **"Granularity gap"** — models waste compute on syntactic prediction when reasoning operates at concept level — mirrors our observation that small models write verbose prose that gets truncated by token caps
- **If concept-level models become available**, they could enable more efficient worker models (same quality at lower compute)
- **The lookahead/planning property** aligns with our session log anti-loop detection needs
- **37% fewer parameters for equivalent quality** — if this scales, a concept-level 2B model could match a standard 3B model

### Why Monitor, Not Act
- No concept-level models available for inference today
- Architecture requires training from scratch (not a fine-tuning approach)
- No llama.cpp or GGUF support for concept prediction architectures
- Most relevant as a signal for future model selection

### Trigger Conditions for Action
- A concept-level model is released at 3B+ scale with open weights
- llama.cpp or vLLM adds support for concept prediction inference
- A major lab (Meta, Mistral, Qwen) adopts concept prediction for a production model

## References

- [ConceptLM paper](https://arxiv.org/pdf/2602.08984)
- [Substack breakdown](https://arxiviq.substack.com/p/next-concept-prediction-in-discrete)
- Related architectures: MegaByte, Hourglass Transformers, JEPA (Yann LeCun)
- Our token cap issue: `_repl_turn_token_cap()` in `src/graph/helpers.py` — small models write verbose prose that gets truncated

## Monitoring Checklist

- [ ] Check quarterly: any concept-level models released with open weights?
- [ ] Track: does any inference framework add concept prediction support?
- [ ] Watch: MegaByte / Hourglass follow-up papers
- [ ] If triggered: create new handoff for evaluation and integration
