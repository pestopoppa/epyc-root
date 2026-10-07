# Research intake — memory and embedding sources — Stage2 —2026-10-07

Stage 2 reviewed 14 retained primary sources across three waves (5 + 8 + 1): intake-1963#record–1967, intake-1968#record–1975, and intake-1976#record. Four secondary leads await operator selection; none is declined. Stage 3 has not begun.

For memory, Cognition’s current article describes Git-backed linked memory, source/date metadata examples, separate owner repositories, a periodic “Dreaming” capability, and an illustrative swarm workspace. Behavior and benefits remain publisher assertions, not independent evidence. The AgentMemoryRepo companion repo is pinned at `8798cb26c817d451a5ed6cba0ad8d9eca8d5ec3e`: the spec uses a compact linked `MEMORY.md`, optional open metadata with source/date recommended, and root-relative `[[path]]` links. Its local trial uses same-machine persistent storage and explicitly omits automatic startup and scheduled Dreaming; no installation or execution occurred.

The current project-wiki consumer has content-hash source-change detection and explicit review/compilation. Task-context, episodic-memory, and multi-agent paths also have existing contracts. Consumer evidence is pinned to orchestrator `2b0a727e490b1e4a01f1d2d720dcc7d0349d630e` and the selected root/wiki and handoff snapshots in intake-1963#record/1965. This supports a bounded conclusion: change detection/review exists; semantic supersession and exception coverage is unproven by hashes alone. The proposal-only semantic maintenance assessment remains unresolved for Stage-3 review; no automatic worker is adopted. Do not record the no-worker proposal as proof that semantic maintenance coverage is closed. Per-owner memory composition and swarm-finding discoverability are separate outcomes. The latter is partly represented by the session bus; no live need for isolated owner stores was grounded.

For model sources, the Google card/config, developer guide, GGUF card, and conversion log were read at pinned revisions. The publisher card lists 8,192 context while config/GGUF advertises 262,144; neither value establishes an effective tested maximum. The GGUF collection has text main-model BF16 and Q8_0 artifacts plus distinct multimodal projector files; this does not make the text main files themselves multimodal. Wave 2 pinned the conversion recipe, upstream llama.cpp PR, current Transformers docs/release, and Sentence-Transformers release. Native Transformers support appears in v5.19.0; model docs recommend Sentence-Transformers >=6.1.0 and document a Transformers AutoModel path. Sentence-Transformers v6.1.0 metadata allows Transformers >=5,<6 and Torch >=2.2. MTEB #5588 is open/unmerged with a CHANGES_REQUESTED review; the submitter withheld exact evaluation setup and a maintainer says current submitted scores cannot be accepted. Results PR #745 is an open/unmerged submission; review inspected representative files including CodeSearchNetRetrieval, not all 246 score files. No score was independently replayed or treated as accepted/model-quality evidence.

Frozen production source `ffc1bac82` maps `gemma-embedding`, not `gemma-embedding2`; this is source compatibility evidence, not an executed load failure. Upstream PR #30054 merged at `4fbc76dec51d0add466f0210855c0596589b60d4` and current upstream has a dedicated converter/graph path, but generic architecture tests skip it because results are inconsistent. This proves neither failure nor parity. The conversion recipe does not pin its external llama.cpp converter revision. No model load, inference, score rerun, installation, kernel build, or runtime parity experiment was performed.

The arXiv v1 VibeMemBench paper is bounded to 111 oracle/reference-selected repository tasks and its paired executable-test protocol. All five frozen-transfer target-bootstrap 95% intervals cross zero; among 12 system/solver pairings, 11 point estimates are at or below matched memory-off and no system interval lies above zero. Low judge agreement constrains detailed failure attribution. The paper does not test EPYC’s curated source-linked diagnostic context. The linked companion subtree was checked at current `main` HEAD `188835d4f9948563a6b9c8ac50cd0f3ae4021ed6` (local clone and remote `HEAD`/`main` agree); `VibeMemBench/` contains only a 100-byte README ending “Coming.” This is release-status evidence, not reproduction, and not a claim that the parent DAMO-ConvAI repository is empty.

The intake-1968#record entry’s independent-reader anchors for the fixed condition list, executable-test primary metric, and excluded resource measures were added to the scratch reviewed proposal because its attached span omitted those components. Model-wave review removed unsupported dtype-policy, release-API, model-specific reproduction, and accepted-score propositions from canonical-claim recommendations; they remain corrections/audit questions, not purported prior claims. The 1976 second-reader check passed. Wave 1 claims were independently reviewed and GGUF corrections applied in scratch. A 2 MiB BF16 GGUF range was fetched briefly during the earlier metadata check and then deleted; no full model artifact was fetched, no range bytes remain in scratch, and no inference occurred.

Intake records/checkpoint/progress are updated; no code/lockfile/handoff/wiki/production changes. Existing handoffs remain untouched; checkbox flips: 0. Publication receipts are outside this source review. No broad wiki sweep is included; per-task wrap-up is root-owned. No Stage-3 plan has begun. Proposed follow-through remains for Stage-3 review; this report does not approve any action, memory maintenance closure, model change, or new substrate.

## Retained primary-source register

| Entry | Reviewed source |
|---|---|
| intake-1963#record | [Cognition Agent Memory Repo](https://cognition.com/agent-memory-repo) |
| intake-1964#record | [EmbeddingGemma 2 model card](https://huggingface.co/google/embeddinggemma-2) |
| intake-1965#record | [AgentMemoryRepo specification and trial](https://github.com/AgentMemoryRepo/agentmemoryrepo) |
| intake-1966#record | [EmbeddingGemma 2 developer guide](https://developers.googleblog.com/en/embeddinggemma-2-the-developer-guide/) |
| intake-1967#record | [EmbeddingGemma 2 GGUF collection](https://huggingface.co/ggml-org/embeddinggemma-2-GGUF) |
| intake-1968#record | [VibeMemBench paper, arXiv v1](https://arxiv.org/abs/2609.23570) |
| intake-1969#record | [llama.cpp PR #30054](https://github.com/ggml-org/llama.cpp/pull/30054) |
| intake-1970#record | [Pinned conversion recipe commit](https://github.com/ggml-org/convert/commit/aa5d5d997139d86298edb6e17fe2e5ade4d1aa90) |
| intake-1971#record | [Transformers EmbeddingGemma2 docs](https://huggingface.co/docs/transformers/model_doc/embedding_gemma2) |
| intake-1972#record | [Transformers v5.19.0 release](https://github.com/huggingface/transformers/releases/tag/v5.19.0) |
| intake-1973#record | [Sentence-Transformers v6.1.0 release](https://github.com/huggingface/sentence-transformers/releases/tag/v6.1.0) |
| intake-1974#record | [MTEB implementation PR #5588](https://github.com/embeddings-benchmark/mteb/pull/5588) |
| intake-1975#record | [MTEB results PR #745](https://github.com/embeddings-benchmark/results/pull/745) |
| intake-1976#record | [VibeMemBench linked repository subtree](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/VibeMemBench) |

## Four secondary leads awaiting selection

- [S5 Labs EmbeddingGemma 2 commentary](https://s5labs.io/resources/insights/google-embeddinggemma-2-multimodal-embeddings/)
- [MTEB leaderboard](https://leaderboard.mteb.org/models)
- [LocalLLaMA Reddit discussion](https://www.reddit.com/r/LocalLLaMA/comments/1wz5va3/googleembeddinggemma2_hugging_face/)
- [CodeSota MTEB benchmark page](https://www.codesota.com/benchmarks/mteb)

These four are pending operator selection, not dismissed or declined.

## Validation

Index entry cardinality 1,972 and maximum allocated ID 1,976 are distinct values. Required gate results follow.

Native intake validation exited 0 (1,972 surviving entries), README freshness exited 0, handoff index-state check exited 0, report cite-check exited 0, and whitespace checks exited 0. Native projection used only this reviewed 14-entry subset and an isolated shadow ledger; source reading supplies no Witnessed measurement or human attestation. Existing index-state advisory warnings are unrelated to this intake. Publication and remote containment are recorded in the retained Stage-2 publication receipt.
