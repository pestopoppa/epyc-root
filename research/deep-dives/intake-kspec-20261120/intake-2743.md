# BM25 Wins at Scale: A Scaling Study of Retrieval-Augmented Generation Paradigms

- **Intake**: intake-2743 (`intake-2743#record`)
- **Source**: https://arxiv.org/html/2607.26497v3
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: context-and-token-economy.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Same research group as intake-2737; do not count it as independent corroboration. Evidence is enterprise prose only, with no hybrid arm and no code or log corpus.

## Key claims (anchored)

0. On a nested corpus ladder an LLM file-agent leads only at the smallest tiers; around 10 million corpus tokens BM25 overtakes it and leads at every larger shared tier.
   - Abstract: "Around 10 million corpus tokens, BM25 overtakes it and leads at every larger shared tier"
1. At full scale BM25 retains 50.5 versus 30.7 for the file-system agent and 29.9 for dense RAG.
   - Sec 4.2: "At full scale, BM25 retains 50.5, versus 30.7 for File-System Agent and 29.9 for DenseRAG"
2. Dense retrieval is efficient but less accurate, and graph RAG hits construction walls.
   - Abstract: "Dense retrieval remains efficient but less accurate, whereas graph-based RAG encounters construction walls"
3. Agency helps after globally ranked candidate discovery, not instead of it.
   - Sec 5.1: "Agency therefore helps after globally ranked candidate discovery"
4. The authors attribute the lexical edge to precise lexical anchors and semantically similar wrong traps; all embedding calls use one 0.6B embedder.
   - Sec 6.1: "Enterprise questions contain precise lexical anchors, while traps are semantically similar but factually wrong"
   - Sec 4.1.2: "all main-pipeline embedding calls go through a shared Qwen3-Embedding-0.6B model"

## Dive record

2026-11-20 Stage-2b wave-2 dive (sonnet; full read; surfaced by intake-2737). Not independent of ReFind: shared authors (Benfeng Xu, Licheng Zhang), count the pair as one source. One synthetic enterprise-prose corpus (EnterpriseRAG-Bench, 511,959 docs), one 0.6B embedder, top-5 chunks, Qwen3.6-27B reader; no BM25+dense RRF arm and no code or log corpus. Agent+BM25 (forced-first BM25 then reformulation) lifts the full-scale agent from 36.9 to 69.4 at ~1/9 the tokens (Table 4, 150-question subset). Our trace store already uses FTS5 bm25 with zero model calls (orchestrator src/trace/query.py L8-L10, L171 @94cd4320); REPL-EMB-2.1 kill rule is already lexical-relative (harness-program.md:L2592-L2594 @901b3fe) and our stored texts are short (median 61-126 tokens, L2549). EnterpriseRAG-Bench 2605.05253 and LinearRAG 2510.10114 declined. lane_head 901b3fe44a30
