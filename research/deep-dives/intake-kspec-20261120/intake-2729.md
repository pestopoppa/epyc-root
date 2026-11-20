# Forget Freely, Grep Later: Lossless, Index-Free Memory for Long-Horizon LLM Agents

- **Intake**: intake-2729 (`intake-2729#record`)
- **Source**: https://arxiv.org/html/2611.25123v1
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: context-and-token-economy.md, memory-program.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Use the prompt-only numbers for our case. Do not repeat the abstract's lossy-baseline framing without noting that MemGPT-style searchable history matches on KV.

## Key claims (anchored)

0. GrepMem is SUPO summarization plus a lossless append-only history log and an index-free grep tool using case-insensitive regular expressions.
   - s4.1: "GrepMem augments SUPO with a lossless, append-only history log and an index-free grep interface"
   - s3.2: "The tool searches the persistent history log using case-insensitive regular expressions."
1. After RL on Qwen3.5-9B (32K window) GrepMem reaches 97.4% on ContextBench KV Store and 95.3% on Log Triage; a MemGPT-style baseline with searchable history gets 99.9 and 50.0, while the lossy baselines stay low.
   - s5.1: "After RL, GrepMem achieves 97.4% accuracy on KV Store and 95.3% on Log Triage"
   - Table 3 after RL: "MemGPT 39.9 46.4 45.4 99.9 50.0 56.3 GrepMem 46.9 46.3 46.1 97.4 95.3 66.4"
   - s4.2: "All strategies use a 32,768-token context window and the same interaction budgets."
2. Prompt-only (before RL) GrepMem already reaches 93.9 KV and 75.0 Log, against 10.9 and 6.6 for SUPO.
   - Table 3 before RL: "GrepMem 40.9 46.9 45.8 93.9 75.0 60.5"
   - Table 3 before RL: "SUPO 45.2 45.5 41.7 10.9 6.6 30.0"
3. Benefit is task-conditional: on AMA-Bench stream all non-ReAct strategies are within 1.2 points after RL; evaluation is a single model and lexical search has limits.
   - s5.1: "all strategies except ReAct differ in accuracy by at most 1.2 percentage points after RL"
   - Limitations: "Our evaluation focuses on controlled benchmarks and a single model"

## Claim corrections

- claim 0: **narrowed** — Not pure log+grep: compaction (SUPO) is retained.
- claim 1: **narrowed** — The <=21% group is SUPO and Masking only; MemGPT (searchable history) matches on KV. Training data includes 15% ContextBench-style synthetic streams.

## Dive record

2026-11-20 Stage-2 dive (sonnet; full read). Orchestrator @94cd43201: ms.search/ms.expand are FTS5/bm25 over the structured SQLite trace store (src/trace/query.py:L3-L10,L126,L170), feature trace_navigation_tools default OFF (src/features.py:L394); session_log_verbatim (default off) appends turns verbatim to session.verbatim.md (src/graph/session_summary.py:L111); context arms summary_only/summary_pointer/pointer_only/prune_pointer/full_history exist (src/graph/context_arm_ab.py:L19) and the continuation text points the model to peek()/grep() over the full log; the A7 lossless-log arm is specified but not run (context-and-token-economy.md:L187,L255 @e9ee76c). Differences: our default is summary-only; their grep has count-only mode and grouping; they RL-train, we would run prompt-only (the before-RL numbers apply). Name collision: our DCP-10 'ContextBench' (context-and-token-economy.md:L503) is a different benchmark. Adversarial pass not run. lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d) Stage-2 close-out (2026-11-20): arXiv 2608.12888 and 2605.15184 ingested as intake-2737 and intake-2738; arXiv 2609.37725 (ContextBench source) declined (benchmark definition only).
