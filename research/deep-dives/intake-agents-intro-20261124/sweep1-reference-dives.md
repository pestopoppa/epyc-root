# Sweep 1 — Stage 1 report and the reference dives (intake-2907..2917)

Session intake-agents-intro-20261124. Date 2026-11-24. Lane head b61af8f2a4b5.

## Stage 1 report

### Processed entries

| ID | Title | Type | Novelty | Relevance | Cred | Verdict | Verification after Stage 2 |
|---|---|---|---|---|---|---|---|
| intake-2907 | The Little Book of Agent Engineering (local PDF) | blog | low | medium | 1 | adopt_patterns | stage1-unverified (PDF, no anchor mark possible) |
| intake-2908 | Effective harnesses for long-running agents (Anthropic) | blog | medium | high | 2 | worth_investigating | dive-verified |
| intake-2909 | Effective context engineering for AI agents (Anthropic) | blog | medium | high | 2 | worth_investigating | dive-verified |
| intake-2910 | Demystifying evals for AI agents (Anthropic) | blog | medium | high | 2 | worth_investigating | dive-verified |
| intake-2911 | Writing effective tools for agents (Anthropic) | blog | medium | medium | 2 | worth_investigating | dive-verified |
| intake-2912 | Introducing Contextual Retrieval (Anthropic) | blog | medium | medium | 2 | worth_investigating | dive-verified |
| intake-2913 | Defeating Prompt Injections by Design (CaMeL), arXiv:2503.18813v2 | paper | medium | medium | 3 | worth_investigating | dive-verified |
| intake-2914 | LLMs Cannot Self-Correct Reasoning Yet, arXiv:2310.01798v2 | paper | low | medium | 4 | worth_investigating | dive-verified |
| intake-2915 | Holistic Agent Leaderboard (HAL), arXiv:2510.11977v1 | paper | medium | medium | 4 | worth_investigating | dive-verified |
| intake-2916 | Don't Build Multi-Agents (Cognition) | blog | medium | medium | 1 | worth_investigating | dive-verified |
| intake-2917 | CooperBench, arXiv:2601.13295v2 | paper | medium | medium | 3 | worth_investigating | dive-verified |

### Dedup

The source is a local PDF with no URL, so it has a `locator_note` and is not a collision. The 87-entry
bibliography (pp.187-195) was deduplicated against all 2,859 entries without truncation. Of its 51
arXiv ids, 18 are already in the index: intake-007, 014, 018, 026, 028, 030, 240, 369, 819, 858, 927,
1110, 1117, 1120, 2302, 2530, 2533 and 2685. Several cited blogs are also indexed: intake-273 Context
Rot, intake-846 Building effective agents, intake-1113 multi-agent research system, intake-2226 Agent
Skills, intake-2276 Manus, intake-2616 Managed Agents, intake-2679 code execution with MCP, intake-274
Complexity Trap, intake-153 Recursive Language Models and intake-1107 Science of Scaling Agent Systems.
Redirects were followed: the anthropic.com /engineering/ paths redirect to /research/, and cognition.ai
serves the page via cognition.com. Every resolved URL was absent from the index.

### Literature expansion

There were 10 additions, all by reference chasing, which reaches the cap. The refused candidates are
recorded in `.research-session.json` under `expansion.expansion_refused`. In priority order they are:
How we contain Claude, the lethal trifecta, AgentDojo, METR time horizon, Agentless, SWE-agent, RULER,
CRITIC, OpenTelemetry GenAI semconv and the CS329Z lecture notes. Textbook classics with low current
relevance were not expanded.

### Cheap contradiction pass (provisional)

- intake-2916 is contested by intake-1113 (parallel research subagents help).
- intake-2915 is contested by arXiv:2611.04399, which reports silent instrument errors in HAL. This
  was dived in wave 1.

### Recommended dives (all were run under the operator's pre-authorisation)

All ten expansion entries were dived. The book itself was read in full by the integrator.

### Preliminary actionables [hypotheses at Stage 1]

| ID | Hypothesis | Final mapping (see stage3-plan) |
|---|---|---|
| S1-1 | Truncated or declined generations may be returned as answers | P1 |
| S1-2 | Prompt prefixes may not be byte-stable, so prefix and KV cache hits are lost | covered by PREFIX-CACHE-LAYOUT-AB |
| S1-3 | Tool failures and truncation may not reach the model as instructive observations | P1 |
| S1-4 | Old tool results may not be elided in long runs | covered by CF-AKV-0 and the TOC compaction A/B |
| S1-5 | A review step without new evidence may hurt | P3 |
| S1-6 | Eval statistics: pass^k, oracle task QA, rerun noise | P2 |
| S1-7 | kb-search contextual or hybrid retrieval | P5 |
| S1-8 | Untrusted content plus external communication in one role | P4 |
| S1-9 | Goal list with verified pass status for long-running sessions | K2 |

### Explicit declines

None among entries with relevance at medium or above. Every such entry was dived.

## The book (intake-2907) — integrator read, all 203 pages

The book is a textbook with no experiments of its own. It is organised around an "agent map" with
seven parts: policy, loop, actions, context builder, store, gate and evaluator. Its citations were
checked against the dives below:

| Book statement | Source | Dive verdict |
|---|---|---|
| Long-running harness: goal list, one verified increment per session, startup check; passing only after verification "prevents premature victory" (p.110-111) | intake-2908 | NARROWED: one harness with two first prompts; verification mitigates and does not prevent, and only with explicit end-to-end prompting |
| Smallest high-signal context; just-in-time references (pp.73-81) | intake-2909 | CONFIRMED; the book omits the source's stated cost of just-in-time retrieval and its hybrid recommendation |
| Eval task = instruction + environment + verifier; 20-50 real tasks; pass@k vs pass^k (pp.152-160) | intake-2910 | task count and pass^k CONFIRMED; the vocabulary is the book's own framing (reattributed) |
| Tools: meaningful identifiers, descriptions are prompts, bounded output (pp.55-58) | intake-2911 | CONFIRMED with narrowing |
| Contextual chunk prefix reduces retrieval failures (p.92) | intake-2912 | CONFIRMED for dense and BM25; not tested on late interaction |
| Plan-then-execute / CaMeL: untrusted data changes content but not which actions (pp.144-145) | intake-2913 | NARROWED: that describes the unprotected dual-LLM state; CaMeL adds capability policies because data can still steer arguments |
| Self-review without new evidence made models worse (p.106) | intake-2914 | CONFIRMED |
| A leaderboard found no relation between accuracy rank and reliability rank (p.160) | intake-2915 | NOT FOUND in HAL. The reliability dimensions come from arXiv:2602.16666 (intake-2922), which also has no rank statement |
| Single agent with full context is often more reliable for code (p.126) | intake-2916 | PARTIAL: the post is broader, and its author later revised it (intake-2918) |
| One agent beat two coordinating agents on paired coding tasks; three failure kinds (p.127) | intake-2917 | PARTIAL: direction holds on tasks built to conflict; the cited title does not match arXiv v1 or v2 |

Many of the book's incidents rest on unpublished CS329Z lecture notes [79]. Examples are the agent
that deleted mail after compaction and the 1,000+ sandboxed agents that coordinated against a scorer.
They remain uncited.

## Reference dives — findings and derived-actionables ledger

Each row gives the dive's derived actionable and its proposed disposition. Final terminal mappings are
in the stage3-plan complete recommendation mapping.

### intake-2908 — Effective harnesses for long-running agents (dive A, FULL)
- The initializer writes init.sh, a progress file, a first commit and a JSON feature list of 200+ items.
  Each later session reads the git log and progress file, runs a basic end-to-end test, and works on
  one feature.
- The JSON format was chosen because the model is less likely to overwrite JSON than Markdown.
- No completion rates are reported. The author's later revision is intake-2228.
- Ledger: i2908-A1 add a premature-pass check to the agent loop protocol. i2908-A2 A/B JSON versus
  Markdown for model-mutated state.
- Surfaced sources: none.

### intake-2909 — Effective context engineering (dive A, FULL)
- Compaction keeps architectural decisions, unresolved bugs and implementation details. It discards
  redundant tool output and keeps the five most recent files.
- Sub-agent summaries are often 1,000-2,000 tokens.
- The source has no measured effect sizes.
- Ledger: i2909-A1 add a tool-result-clearing arm to the compaction A/B. i2909-A2 hybrid retrieval
  policy for REPL agents.
- Surfaced sources: none.

### intake-2910 — Demystifying evals (dive B, FULL)
- Grade outcome over path.
- A 0% pass rate across many trials usually means the task is broken.
- Isolate trials.
- Capability suites graduate into regression suites.
- The CORE-Bench 42% to 95% figure is a vendor self-report.
- Ledger: i2910-A1 reference-solution check and a 0%-over-N audit rule. i2910-A2 report pass@1 and
  pass^k. i2910-A3 grade outcome first, plus capability/regression tags. i2910-A4 calibrate judges
  against human labels.

### intake-2911 — Writing effective tools (dive C, FULL)
- Claude Code caps tool responses at 25,000 tokens.
- Concise responses use about one third of the detailed tokens (72 vs 206).
- Namespacing choice matters and depends on the model.
- Ledger: i2911-A1 tool-eval harness. i2911-A2 response_format, plus a truncation message that names
  the narrowing parameters. i2911-A3 namespacing A/B on local models.

### intake-2912 — Contextual Retrieval (dive C, FULL)
- Failure rate is 1 minus recall@20 (lower is better). Baseline 5.7%.
- Contextual embeddings: 3.7%. Adding contextual BM25: 2.9%. Adding reranking: 1.9%.
- Context generation costs $1.02 per million document tokens with prompt caching.
- Late interaction was not tested.
- Ledger: i2912-A1 contextual prefix on kb-search. i2912-A2 BM25 leg plus fusion. i2912-A3 sweep k
  for local models.
- Surfaced sources (dived in wave 1): arXiv:2504.19754, 2505.24782, 2409.04701.

### intake-2913 — CaMeL (dive D, PARTIAL)
- On o3-High, utility is 84.5% native vs 77.3% CaMeL.
- Successful attacks out of 949 fall sharply (for example Gemini 2.5 Pro 163 to 0).
- Median token overhead is about 2.7-2.8x.
- Benign tasks trigger a policy confirmation 34% of the time under NORMAL policies and 53% under
  STRICT.
- Text-to-text attacks and side channels are out of scope.
- Ledger: i2913-A1 provenance tags plus a policy check on one tool class. i2913-A2 measure the token
  multiplier first. i2913-A3 run the quarantined LLM on a small local model. i2913-A4 never claim
  provable security without the interpreter.
- Surfaced sources (wave 1): arXiv:2505.22852, 2510.05244, 2610.05640.

### intake-2914 — Cannot self-correct (dive D, PARTIAL)
- Under intrinsic self-correction, GPT-4 on GSM8K goes 95.5 to 91.5 to 89.0, and Llama-2-70B goes
  62.0 to 43.5 to 36.5.
- Debate loses to self-consistency at an equal response count.
- Most cells use 100-200 question samples.
- Ledger: i2914-A1 a no-evidence review step is advisory unless an A/B wins. i2914-A2 change matrix.
  i2914-A3 route escalation to evidence-bearing checks. i2914-A4 one bounded probe on our reviewer.
- Surfaced sources (wave 1): arXiv:2406.01297, 2409.12917.

### intake-2915 — HAL (dive B, PARTIAL)
- 21,730 rollouts cost about $40,000.
- Higher reasoning effort gave equal or lower accuracy in 21 of 36 cells, from single runs.
- The most costly run is on the Pareto frontier in 1 of 9 benchmarks.
- The rank-relation claim is absent.
- Ledger: i2915-A1 use the reasoning-effort result as a prior and test it with 3 or more trials.
  i2915-A2 report cost axes. i2915-A3 LLM-aided log inspection. i2915-A4 dive the two surfaced
  sources (discharged in wave 1). i2915-A5 record weights hash and quant per eval row.
- Surfaced sources (wave 1): arXiv:2611.04399, 2602.16666.

### intake-2916 — Don't Build Multi-Agents (dive A, FULL)
- Principles: share full traces; actions carry implicit decisions.
- For long tasks, use a dedicated history-compression model.
- Ledger: i2916-A1 single-writer delegation rule. i2916-A2 small summariser model as a compaction
  reference.
- Surfaced sources (wave 1): cognition.ai/blog/multi-agents-working.

### intake-2917 — CooperBench (dive C, PARTIAL)
- 652 tasks. GPT-5 and Claude reach 25% when cooperating, about half of the Solo baseline. Pooled
  retention is 0.59.
- Communication cuts merge conflicts but does not change success.
- A first-turn plan cuts conflicts from 51.5% to 29.4%.
- The abstract's 30% is never derived in the paper.
- Ledger: i2917-A1 evidence on bus completion claims. i2917-A2 first-turn plan on cross-session
  handoffs. i2917-A3 a shared record of semantic decisions. i2917-A4 a solo-first prior in fan-out
  rules.
- Surfaced sources (wave 1): arXiv:2511.02687, 2502.06994.

## EPYC grounding scan (read-only, orchestrator @ 1cc2043, research @ 3ab8362, root @ b61af8f)

| Question | Current behaviour (pinned) | Gap |
|---|---|---|
| Stop reasons | The backend maps finish_reason to completion_reason (src/backends/llama_server.py:596-612, 1102-1111). The REPL retries on length only behind a default-off flag (src/graph/helpers.py:1951-2027). | The /chat response has no finish_reason or truncated field (src/api/models/responses.py), so a length-cut chat answer returns as final |
| Prefix stability | The stable layout flags exist but are off (src/features.py:935-956, src/prompt_builders/types.py:130-149). cache_prompt is on. | Covered by PREFIX-CACHE-LAYOUT-AB |
| Tool execution | Unknown tool, argument and permission errors reach the model as observations. The REPL spill tells the model how to narrow. | src/llm_primitives/primitives.py:1267, 1409, 1529 truncate with no narrowing hint. The SideEffect enum does not gate by default |
| Context growth | Spill-to-file. session_compaction is on. Old tool-result stubbing exists only on the /v1 fold and is off. | Covered by CF-AKV-0, UTM-B2-RECOVERY-POINTERS and the TOC A/B |
| Self-review | The architect review gets condensed output only. Workers are told not to self-correct. A1 is the self-review arm: FA 45.8%, FR 41.7%, AUC 0.463 (reviewer-control-plane RM-2). | No fix/break reporting and no matched-compute baseline |
| Eval statistics | pass^k exists in scripts/analysis/reviewer_calibration_report.py:304-345. Oracle checks exist for debugbench and livecodebench. MEASUREMENT.md:170-184 sets the replay rules. | Tower has no graded-fraction gate and no drops manifest; MONITOR on Pass^k |
| Retrieval | ColBERT MaxSim over chunk text. The heading breadcrumb is metadata only and not encoded (src/retrieval/kb_rag.py:663, 808). The FTS5 lexical leg is off (no uplift found in K11). K7 recall@3/5/10. | No document-situating text in the encoded chunk |
| Trifecta | The frontdoor role's web category holds both web_search and http_post. http_post has no destination guard (orchestration/tools/web.py:51-81). | TOOLPERM-DENY-DEFAULT is open in engineering-hygiene-backlog. http_post guard is missing |
| Long-running sessions | Autopilot verifies its startup authority and recovers an in-flight trial. Handoff boxes carry a done_when check. | No per-item verified-pass goal list in autopilot (holds apply) |
