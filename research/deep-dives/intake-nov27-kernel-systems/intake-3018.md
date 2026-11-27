# MGMem: An Efficient, Deterministic, and Provenance-Preserving Framework for Long-Horizon Agent Memory

[Primary source](https://arxiv.org/abs/2611.33174v1) · intake-3018 · 2026-11-27

English raw episode retrieval. Deterministic spaCy en_core_web_trf mention extraction plus lexical normalization, embedded segmentation, mention co-occurrence/incidence graph, exact→subject-local→global dense bridge, then confidence/IDF ranking; emits top five original episodes. No generative indexing calls/tokens but transformer embeddings and parsing remain; LLM reader/judge remain. LoCoMo four-category (1,540 questions/10 conversations, adversarial separate): reported judge accuracy 75.89±0.10% vs locally matched EMem 73.29±0.10, AnchorMem 71.69±0.36, LightMem 62.42±0.10 and Hybrid 66.62±0.34; MGMem–EMem conversation-bootstrap +0.22 to +5.15 pp and dev-conversation exclusion preserves ranking. Index build on Apple M5 Pro 199.02±43.37 s, slower than BM25 1.67±0.08s or Hybrid 13.53±0.76s, faster than generated-memory matched baselines. Full LongMemEval-S 500 questions: 72.60% vs BM25 74.60% and Hybrid 73.80%; delta vs BM25 interval [-5.40,+1.40] pp, not equivalence. MGMem multi-session accuracy 55.64% vs Hybrid 65.41%, and all-gold temporal coverage 68.42% vs BM25/Hybrid 77.44%. Original single-run ablation removing subject-local bridge costs ~6.1 pp, near removing all bridges (6.0 pp); no replicated evidence of graph indispensability. Raw pointers enable provenance, while the 200-response audit finds 94% evidence support. Parsing and results are English dialogue-specific; history scale and code-mixed logs remain open.

Read §3–§7, Appendices A, F, G, H selected tables and analysis. Remaining appendix prompt text, extended tuning tables and bibliography not read.

## Evidence

- Incidence edges are provenance through co-occurrence, without semantic entailment. [§3.2](https://arxiv.org/html/2611.33174v1)
- No generative calls are compatible with materially higher indexing compute than lexical or hybrid retrieval. [§4.3 Table 3](https://arxiv.org/html/2611.33174v1)
- MGMem leads or ties local single-session categories while overall LongMemEval-S trails BM25 and Hybrid. [§4.3 and Appendix G Table 8](https://arxiv.org/html/2611.33174v1)

## Scope and local transfer

Provenance of source turns is not evidence that the answer is supported. The LongMemEval-S overall result is lower than lexical/hybrid; transfer is mixed and current graph-versus-Hybrid ranking is dataset-dependent. No generative indexing means a CPU/accelerator cost still exists.

EPYC 9655: replay raw fixed-window transcript/artifact episodes against shipped BM25+EmbeddingGemma RRF with all-gold-session recall and cited spans, first compare exact lexical and graph candidates on the same freeze. Query-side project/session conditioning might help without generative rewrite. Consider graph/embedding resource cost with real logs, and compare broad multi-session/temporal queries alongside within-thread. Existing lane harness-program.md:2823–2908 gives hybrid control. MI210: reserve for embedding batches and local fixed-reader concurrency only if measured savings exceed residency/queue contention. No GPU acceleration is implied for episode/graph traversal.

Current externalization and BEAM reader controls permit adding a raw-episode retriever without changing live memory writes. Add a CPU parser and incidence-postings arm returning original episode IDs and text at the same answer budget. Compare with lexical, raw/full-context and incumbent retrieval; include episode provenance, temporal errors and missed evidence.

## Sources surfaced

- https://github.com/junhong-h/MGMem — Available implementation/protocol companion. Verify append-only writes, episode units, raw pointers and cost.
- https://arxiv.org/abs/2604.17377 — AnchorMem comparison with generated anchored facts; audit matched and quoted baseline families separately.
