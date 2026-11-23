# Dive — pluginrsi — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/html/2609.32423v2", retrieved: "2026-11-23", sha256: "e0193b9b9f36"} (fetch resolved v2, 18 Oct 2026; v1 is dated 26 Sep 2026 per the repo news)
> SOURCE-QUARANTINE: {url: "https://github.com/syr-cn/PluginRSI", retrieved: "2026-11-23", sha256: "ae163ec09e7b"} (README, `pluginrsi/repo.txt`; depth-1 clone read as reading material at `pluginrsi/repo_src/`, HEAD bafab39e4c62b7f0aa252f2ffd891886b45c82f8, MIT, 63 stars, last push 2026-10-18; files read: `search/mutation.py`, `search/selection.py`, parts of `search/loop.py`, `configs/swe.yaml`, `configs/qa_transfer.yaml`)

Bearing entry: intake-2836 (HookEvo). That dive called PluginRSI the closest prior ("improves single plugins, keeps a library, recombines") and asked: settle its plugin library and recombination design against HookEvo, and whether it changes ledger rows H1-H3.

## 1. Stage-1 fields

- **Title**: PluginRSI: Recursive Improvement of Agent Harnesses with Reusable Plugins.
- **Authors**: Yaorui Shi, Yuchun Miao, Yuxin Chen, Jiayuan Zhang, Yueqing Sun, Xierui Song, Xiang Wang, An Zhang (USTC, Meituan, Wuhan University, NUS).
- **Version/date**: arXiv:2609.32423v2 [cs.AI], 18 Oct 2026, CC BY-SA 4.0. Preprint. Code MIT.
- **Categories**: autonomous_research, agent_architecture, tool_implementation, benchmark_methodology.
- **Novelty**: medium. A shared plugin library with per-plugin mutation and library-driven recomposition, against Meta-Harness-style whole-program rewriting.
- **Relevance**: medium. Its two-tier acceptance structure and its versioned plugin manifest bear directly on AutoPilot BSV-2 and the candidate-graph work (AP-DGM-PROV).
- **Credibility**: 1 = peer-reviewed 0 (preprint) + within 12 months +1 + major lab / known contributor 0 + independent corroboration 0 + commercial bias 0. No seeds, intervals or repeats are reported (no temperature or seed statement for the solver either), and the held-out set is 100 tasks.
- **Verdict**: adopt_patterns. Adopt the two-tier gate (cheap archive admission, strict incumbent retention on a large set) and the versioned manifest; do not adopt the 6-10 point SWE-bench margins as established.

## 2. Key claims

**Claim 0 — the design. CONFIRMED (section 3, Algorithm 1, repo code).** A harness is H(W, P): a workflow W plus plugins P drawn from a library; a plugin is a versioned Python package `<library>/<kind>/<name>/<version>/` with a `plugin.yaml` manifest (kind, name, version, entrypoint, JSON-Schema `config_schema`, optional provenance with parent references) and a Python class of one of four categories (role `render`, tool `schema/execute`, skill `load`, memory `update/retrieve`). Each iteration has two stages. Plugin mutation: N = 8 parallel branches, each on its own balanced minibatch of b = 20 tasks (10 solved and 10 unsolved by the incumbent), mutate one plugin while "the workflow and the remaining plugins stay fixed" (code enforces it: `validate_local_surface` raises if any workflow file or any other alias reference changes, mutation.py:45-59); a variant joins the library only if it strictly beats the incumbent on that minibatch (`retained = valid and gain > 0`, mutation.py:42). Recomposition: the proposer selects plugin versions from the library and revises the workflow, producing one candidate that is evaluated on all 400 held-in SWE-bench tasks and replaces the incumbent only if strictly better; the returned harness is the best on held-in. The library grows from 75 to 132 plugins over 15 steps.

**Claim 1 — "improves held-out resolve rate over Meta-Harness by 6-10 points on SWE-bench Verified and carries to other solvers". PARTIAL.** Table 1 (held-out, n = 100): GPT-5.6 Terra-optimised PluginRSI 65.00 against Meta-Harness 55.00 and ReAct few-shot 55.00; Kimi-K3-optimised 69.00 against Meta-Harness 63.00. Terminal-Bench-2.1 held-out (30 tasks) 73.3 against 66.7. QA held-out 0.588 against 0.568. Qualifications: single run per cell, no seeds, intervals or repeats; with n = 100 one standard error of a rate near 65% is about 4.8 points, so the 6-point margin is about one standard error; held-in margins are small (58.50 vs 54.50, 66.75 vs 64.25) and in the cross-solver held-in column PluginRSI is below Meta-Harness in two cells (58.00 vs 58.25 for Terra on the Kimi-optimised harness; 59.50 vs 59.75 for GLM-5.2); PluginRSI runs 15 iterations against 25 for baselines, with the x-axis of Figure 3 switched to cumulative solver rollouts "for fair comparison" and token cost per solver rollout +7.5% (input) and +19.8% (output).

**Claim 2 — "mutation and recomposition both matter; a plugin library alone does not". PARTIAL (confounded).** Table 4, Kimi-K3 held-out: PluginRSI 69.00; without plugin mutation 57.00; without harness recomposition 59.00; without initial plugins 67.00; Meta-Harness 63.00, with an added library 64.00. The "without recomposition" arm replaces the full-held-in selection by "the mutation-stage harness with the highest score on its b-task minibatch", so the 10-point drop mixes two changes (no workflow revision and selection on a 20-task minibatch score instead of the 400-task set). It is nevertheless the only quantity in this cluster that bears on how costly minibatch-level selection is.

**Claim 3 — admission is not a clean paired test. CONFIRMED (paper statement plus code).** Table 11 reports the screening of eight selected mutations "using cached outcomes for the original harness": every row starts at 10/20 (one at 10/19) and ends at 12-14. The code confirms it: `branch_feedback` (loop.py:280-288) "projects the incumbent's full evaluation onto a branch minibatch, reusing its rollouts" (`reused_result=True, rollouts_started=0`), and `balanced_batch` (mutation.py:18-25) draws failures and successes from that same cached evaluation. The parent is never re-run on the minibatch. With a stochastic solver, tasks selected for having failed once pass again at some rate, and a balanced 10/10 batch is pulled toward the population pass rate (55-66% for the optimised harnesses in Table 1, above the 50% of the balanced batch), so a child can score above 10/20 with no real improvement (inference from the construction; the magnitude is not measured in the source). Contrast HookEvo, which re-scores the parent on the batch every round.

**Claim 4 — "an evolved library accelerates later optimisation (69% after two steps versus 65%)". PARTIAL.** The reuse setup states that "the subsequent harness optimization runs on the held-out 100 tasks following the held-in protocol", so in that experiment the 100 tasks play the optimisation role; the paper does not separately state an out-of-sample score for it, and the difference is 4 tasks of 100 (my reading; flagged as inference).

**Claim 5 — relation to HookEvo (the steering question). SETTLED by reading both.** PluginRSI's mutation unit is one plugin with the workflow frozen, which is HookEvo's scope B; its recomposition revises the workflow and selects among existing library versions (`allowed_plugin_refs`), so a single PluginRSI candidate does not edit plugin internals and workflow together. The paper states the gap: "plugin mutation evaluates each change with the remaining harness fixed. This can miss mechanisms that require coordinated changes to other plugins or the workflow", which is the problem HookEvo's scope C targets. PluginRSI has a persistent library and versioned provenance; HookEvo has none (accepted code only persists along one lineage). Acceptance differs in scale: PluginRSI retains an incumbent on a 400-task set that is also the feedback pool (`feedback_tasks` and `selection_tasks` are the same file in `configs/swe.yaml`), HookEvo on a recurring 50-task batch; neither is disjoint from its evidence. HookEvo's A-to-C result (coordinated shared-state edits beat independent ones, for the Sol improver only) is not contradicted by PluginRSI's results, which concern a different benchmark and solver and never tested shared-state hooks.

## 3. Reported results (as the source states them)

- SWE-bench Verified: 400 held-in and 100 held-out tasks; proposers and solvers GPT-5.6 Terra and Kimi-K3, evaluation also on GLM-5.2; reasoning effort xhigh for the proposer, none for solvers. Held-out (GPT-5.6 Terra / Kimi-K3 / GLM-5.2 columns) for the Terra-optimised group: PluginRSI 65.00 / 60.00 / 52.00, Meta-Harness 55.00 / 53.00 / 44.00, DGM 50.00 / 51.00 / 43.00, GEPA 51.00 / 44.00 / 48.00; Kimi-optimised: PluginRSI 64.00 / 69.00 / 64.00, Meta-Harness 60.00 / 63.00 / 59.00, DGM 58.00 / 55.00 / 51.00, GEPA 61.00 / 62.00 / 52.00. Additional baselines (Table 7) SkillOPT, A-Evolve, AHE: PluginRSI ahead by 9.00, 12.00 and 6.00 held-out points.
- Terminal-Bench-2.1 (Kimi-K3): held-in 69.5 and held-out 73.3 against Meta-Harness 64.4 and 66.7. QA (Kimi-K3, optimised on 150 tasks from three domains, five held-out domains): held-in 0.820 against 0.753, held-out 0.588 against 0.568, overall 0.675 against 0.638.
- Hyperparameters (Table 5): T = 15 iterations (baselines 25), N = 8 mutations, b = 20, 10 solved : 10 unsolved, 1 recomposition candidate, proposer max 40 turns, solver max 20 turns, timeout 360 s, seed 42; 560 solver rollouts per iteration (400 + 8 x 20); repo cap `max_task_rollouts: 24000`.
- Tokens (Appendix L): total input and output tokens per solver rollout increase by 7.5% and 19.8% against Meta-Harness; solver usage similar, proposer overhead from the mutation stage.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Plugin library and versioned manifests | n/a (host files); solver served on the MI210 only. | YES; plain files and YAML. |
| Balanced-minibatch mutation (8 branches x 20 tasks) plus full-set recomposition (400 tasks) | PARTIAL. 560 solver rollouts per iteration at SWE-bench scale is rollout-bound; with a local solver on the MI210 the cost is whatever the served model gives per episode (no number in source). The 20-task branches are small and parallel, fitting small-ubatch serving. | PARTIAL. Same rollouts on a CPU-hosted solver are bandwidth-bound and slow. |
| Strict improvement on cached-parent minibatch for admission | YES (arithmetic); the bias is statistical, not device-bound. | YES |
| Proposer on a frontier model (xhigh effort) | n/a | n/a (paid on our existing roster) |

## 5. In-house state

- **AP-DGM-PROV / AP-DGM-SEL** (autopilot-program.md:L935-L946 @ d785b6d): a candidate-graph and selector-replay package exists; option A (observe-only `eligible_parents` per journal row) and option C are built default-off; the live parent choice is the deterministic `select_lineage_parent`. PluginRSI's library is an archive of admitted mutation variants with parent references, the kind of record this work freezes; nothing in the journal today versions a mutation as a reusable component.
- **BSV-2** (L123): paired behavioural comparison with McNemar report; no admission-versus-retention tiering. **BEP-5** (L2214): sandbox-before-disk and granular accept/reject.
- SkillBank (memory-program.md:L124-L143, M-23 at L669) stores text skills; the A/B spec is gated on M-11a populating a bank.
- HIL-2 checklist items 9 and 11 (arrival split, power) exist; DPF-1132-L2 is the worked counterexample for same-task evolution and scoring (harness-program.md:L1981 @ d785b6d).
- Upstream-present check: n/a (no kernel content).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| PR1 | Specify BSV-2 acceptance as two tiers: cheap admission of a mutation variant into an archive on an evidence batch against a FRESH re-run of the incumbent (not cached outcomes), and retention of the incumbent only on the full sentinel set; record PluginRSI's admission bias (cached parent plus failure-selected batch) and its "without recomposition" 69-to-59 held-out drop (confounded) as the rationale. Refines intake-2836 H1 and hookevorepo HR1/HR2. | `autopilot-program.md` BSV-2 (L123; AutoPilot stopped, design only), with a pointer in `harness-program.md` HIL-2 checklist | doc-only | Decision: adopt the two-tier structure in the BSV-2 spec; done when the spec names the fresh-parent rule and the retention set. Question recorded: how often does a failure-selected minibatch score above chance with no change? (measurable later by re-running an unchanged incumbent on such a batch; no new compute now). |
| PR2 | Adopt PluginRSI's versioned manifest as the schema for our mutation journal: kind, name, version, entrypoint, config schema, provenance parent references, and the rule that a mutation creates a new version while preserving alias, configuration and interface. Refines intake-2836 H2. | `autopilot-program.md` AP-DGM-PROV (box OPEN; options A and C built default-off) | doc-only | Decision recorded: whether the candidate graph stores mutations as versioned components; done when the AP-DGM-PROV note carries the field list. |
| PR3 | Add a matched-budget rule to the HIL-2 checklist: harness-evolution methods are compared by cumulative solver rollouts or evolution tokens, never by iteration count (PluginRSI used 15 against 25 iterations and re-plotted by rollouts; Life-Harness reports tokens; HookEvo matched neither). Refines hookevorepo HR1 and lifeharness LH2. | `harness-program.md` (HIL track, HIL-2 checklist append) | doc-only | Done when the checklist item states the budget unit and requires it in any comparison table. |
| PR4 | Add the invalid-versus-infra split to the same record: PluginRSI excludes infra-error tasks from matched comparisons and fails a candidate only on candidate errors (`apply_quality_policy`, `min_valid_ratio`), matching the house rule that infrastructure failure is the absence of a measurement. | `autopilot-program.md` BSV-2 and `harness-program.md` HIL-2 | doc-only | Done when the record schema has separate candidate-error and infra-error statuses with a minimum valid ratio. |
| PR5 | DECLINE: reproduce the SWE-bench Verified and Terminal-Bench numbers. Reason specific to this entry: about 8,800 solver rollouts per run with Kimi-K3 or GPT-5.6 solvers and an xhigh proposer, and the 6-10 point margins are about one standard error of a 100-task held-out set, so a reproduction would not settle the question we care about; PR1-PR4 carry the transferable parts. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `github.com/syr-cn/PluginRSI` (0 hits): read here (README plus the admission and selection code), so it is the companion of this entry; it settled the cached-parent question directly. Ingest as the companion artifact; no separate dive.
- arXiv:2609.32423 itself: 0 hits before this entry; `PluginRSI` appears once, in intake-2836's novelty line.
- arXiv:2606.14249 HarnessX and the DeepSeek Harness: already in the index (per intake-2836). arXiv:2604.25850 AHE: in the index. No further source changes a ledger row.
- A-Evolve and SkillOPT (additional baselines, Table 7): decline; no row depends on them.

## 8. Contradiction / adversarial pass

- Admission against cached incumbent outcomes on a failure-balanced minibatch (paper text, Table 11, `branch_feedback`): biased toward admitting.
- Feedback pool and selection pool are the same 400 tasks (`configs/swe.yaml`), so incumbent retention is in-sample at the held-in level; only the 100-task held-out set is out of sample.
- One run per cell, no variance; held-out sets of 100 (SWE-bench), 30 (Terminal-Bench) and 250 (QA, five domains); baselines run 25 iterations with a different cost profile.
- The reuse result (69 vs 65) optimises on the 100 held-out tasks.
- Authors' stated limitations: fixed task sets and limited iterations, transfer depends on domain and solver, and "plugin mutation evaluates each change with the remaining harness fixed".
- The authors note a performance degradation in GPT-series models around the end of August 2026 and re-ran all experiments in September; results depend on API model state at that time.
- No independent replication found.

## 9. Read depth

read_depth: FULL for the paper (main text, Appendices A-L tables read, Figure captions only for figures); repo README, `mutation.py`, `selection.py`, `loop.py` (admit, recomposition, branch_feedback, held-out report), `configs/swe.yaml` and the head of `configs/qa_transfer.yaml` read. NOT read: proposer prompts, plugin source files, evaluation harness, tests. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | Section 3.2.2 / Algorithm 1 | "Each minibatch contains 10 tasks solved by the current harness and 10 unsolved tasks."
- claim 0 | page | Section 3.2.2 | "Plugin variants with empirical improvements are added to"
- claim 0 | page | Appendix E | "The subsequent harness recomposition stage generates one candidate, which is evaluated on all held-in tasks."
- claim 0 | page | Appendix J | "Plugin mutation creates a new version and updates the corresponding reference while preserving the instance alias, configuration, and category interface."
- claim 0 | page | Section 4.5 | "the library grows from 75 to 132 plugins over 15 evolution steps"
- claim 1 | page | Table 1 (Kimi-K3-optimised rows) | "PluginRSI 58.00 66.75 59.50 64.00 69.00 64.00"
- claim 1 | page | Table 4 (Meta-Harness rows) | "Meta-Harness 58.25 64.25 59.75 60.00 63.00 59.00 + Plugin Library 58.25 65.50 55.25 58.00 64.00 56.00"
- claim 1 | page | Appendix E | "We run our method for T = 15 T=15 iterations and the baselines for T = 25 T=25 iterations."
- claim 1 | page | Section 4.1 | "We split SWE-bench Verified into 400 held-in and 100 held-out tasks"
- claim 1 | page | Appendix L | "Total input and output tokens per solver rollout increase by 7.5% and 19.8%, respectively."
- claim 2 | page | Table 4 | "w/o Plugin Mutation 52.25 58.50 46.25 49.00 57.00 50.00 w/o Harness Recomposition 57.25 62.50 59.00 57.00 59.00 60.00"
- claim 2 | page | Section 4.4 | "we adopt the mutation-stage harness with the highest score on its"
- claim 3 | page | Table 11 caption | "using cached outcomes for the original harness"
- claim 4 | page | Section 4.5 | "Reusing the library from the initial harness reaches a held-out resolve rate of 69% after two evolution steps, compared with 65% without reuse."
- claim 5 | page | Appendix D | "Third, plugin mutation evaluates each change with the remaining harness fixed. This can miss mechanisms that require coordinated changes to other plugins or the workflow."

Anchors verified: 15 of 15 (python count >= 1 in `pluginrsi/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/pluginrsi.json` written; the clone under `pluginrsi/repo_src/` is reading material inside the permitted scratch tree; all anchor quotes verified in `pluginrsi/page.txt`).
