# Dive — memmgmt — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2505.16067v2", retrieved: "2026-11-24", sha256: "f527b3676cf7"}

authors: Xiong, Lin, Xie, He, Liu, Tang, Lakkaraju, Xiang; arXiv v2 (Oct 2025), ACL 2026 long

## 1. Stage-1 fields
- title: How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior. arXiv 2505.16067 (v1 May 2025; v2 Oct 2025 read). Found by web search; abs title matches; intake index count 0 (unbounded grep) so new.
- categories: memory_augmented, agent_architecture, knowledge_management. novelty medium. relevance high for lesson-store demotion.
- credibility_score: 2 (peer-reviewed ACL 2026 +2; >12 months 0; no lab bonus; web summary and the autoresearch bibliography are restatements). verdict: adopt_patterns.

## 2. Key claims
0. Experience-following (similar input -> similar output as the retrieved record) - CONFIRMED (anchor 0). Whether it copies BAD experience: yes via error propagation (claim 1).
1. Error propagation and misaligned experience replay; later evaluations are free quality labels - CONFIRMED (anchors 1, 2).
2. Retrieval-count (periodic) deletion shrinks memory with small, mixed accuracy change - CONFIRMED, with signs: Table 2 strict rows RegAgents 70.95->67.65, EHRAgents 38.67->38.59, AgentDriver 51.00->50.94, CIC-IoT 85.40->80.80; memory down 60-77% (anchor 3).
3. Utility-gated deletion improves real agents with a strict evaluator but is evaluator-dependent - CONFIRMED (anchors 4, 5). Strict: EHR +3.39, AgentDriver +0.81, CIC +4.2, RegAgents -1.15.
4. "10% average absolute gain": NOT-FOUND-IN-SOURCE (v2 page has no such figure). Out-of-scope operations: merging, summarisation, reflection (anchor 6).

## 3. Reported results
Table 2 as in the draft; agents: synthetic RegAgent (4000 test pairs), EHRAgent (MIMIC-III, 2,392 tasks), AgentDriver (nuScenes, 2,000 cases), CIC-IoT. Evaluators: strict, coarse C1-C3, GPT-4o-mini/GPT-4.1-mini, fine-tuned evaluator. No seeds/CIs seen.

## 4. Performance-principles table (mechanism)
| Principle | MI210 | Zen 5 | Reason |
|---|---|---|---|
| Unused-in-window deletion (alpha=0) | YES | YES | pure bookkeeping on the journal, device independent |
| Utility-gated deletion after >=n retrievals | YES | YES | AK has a strict evaluator: each attempt carries a keep/discard receipt, so utility after retrieval is observable without an LLM judge |
| Fixed-capacity memory with least-utility eviction | YES | YES | bounded planner bundle; paper reports convergence to unbounded performance as capacity grows (strict evaluator, AgentDriver) |

## 5. In-house state
Lesson store: controller/experiments.py:recall() (epoch-scoped, stale_epoch marking, limit=40), seeds/negatives.json, controller/do_not_repeat.py (refuses a mechanism answered 3x in an epoch) - epyc-inference-research, read-only; per the autoresearch dive section 5. AK negatives are mechanism-keyed guards (what NOT to retry) rather than demonstrations to be copied, so experience-following acts through the planner re-proposing from a retrieved success/failure narrative; the mapping is not measured here.

## 6. Derived-actionables ledger
1. refines autoresearch row 1: Draft: "In the offline journal replay, compare THREE demote rules for rendered prose lessons: unused-5 (no citation in 5 turns), the paper's periodic rule at alpha=0 over a window, and a utility-gated rule (retrieved >= n times and mean downstream keep-rate below beta, using AK keep/discard receipts as the strict evaluator); for each count (a) bundle chars saved, (b) later same-epoch re-proposals of a demoted mechanism, (c) keep-rate of proposals made while a demoted lesson was absent vs present." Owner: autokernel-loop.md (not frozen). Code/doc-only, zero inference. Decision rule: adopt a rule only if false-demotion re-proposals are 0 and the utility-gated arm saves at least as many chars as unused-5; gate-backed negatives never demoted. Question: does demoting by retrieval utility beat demoting by non-use for our store? Stop-on-answer when the replay emits all three arms.
2. Decline: merging/summarising lessons on this paper's authority; reason: not studied (Limitations), and autoresearch E.3.1 shows merging drops applicability conditions.

## 7. Dive-surfaced sources
- GitHub yuplin2333/agent_memory_manage (code and dataset): would not change row 1 (we have no LLM evaluator). Decline.
- arXiv 2607.10113 (Li, survey): see skillsurvey; declined.

## 8. Contradiction / adversarial pass
RegAgent (strong experience-following, large capacity) degrades under every deletion rule; coarse-evaluator history deletion hurt AgentDriver (36.92->34.00); a GPT-4o-mini evaluator helped one agent and hurt another; no variance reported in Table 2; demonstrations bank, not negative lessons.

9. read_depth: PARTIAL. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.
10. artifact audit: clean (7 anchors verified).
