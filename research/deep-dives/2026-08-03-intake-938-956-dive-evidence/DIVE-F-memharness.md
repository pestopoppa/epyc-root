# DIVE-F — intake-938 MemHarness -> **dive-OVERTURNED**

## HEADLINE: adoptable without RL? **NO** — and the reason is stronger than my brief assumed.
I told the agent to expect "the gradient-free win is ALFWorld-only." That UNDERSTATES it.
**The correct control is `w/o memory`, NOT `RL + Raw Memory`** — both use the SAME MemHarness-trained
actor, differing only in the reconstructor:
| arm (identical trained actor)        | ALFWorld | WebShop |
| MemHarness (trained reconstructor)   | 85.2     | 75.6    |
| **w/o memory (CORRECT control)**     | **83.0** | **73.6**|
| generic LLM reconstruction (untrained)| 77.7 (**-5.3**) | 71.8 (**-1.8**) |
**An untrained reconstructor is WORSE THAN HAVING NO MEMORY AT ALL, on BOTH benchmarks.
There is no gradient-free win anywhere in the paper.**

## THE COLD-START ROW EXISTS — AND IS CATASTROPHIC
Table 2 row `Cold Start Model`: **ALFWorld 7.6, WebShop 17.6** — BELOW the un-fine-tuned base model on
ALFWorld (14.5). Both SFT-only checkpoints ARE downloadable (cold_start/alfworld/, cold_start/webshop/).
They are worthless as instruments: format-aligned shells, not policies.
Stage 1 declared this datum unavailable. It was in Table 2 all along, in two rows our entry omitted
(`Base Model 14.5/7.8` and `Cold Start Model 7.6/17.6`).

## ONLY ~25% OF THE HEADLINE IS THE PORTABLE PART
ALFWorld: +8.8 over GRPO = **+6.6 TRAINING effect** (83.0 vs 76.4, both memory-free at test)
                          **+2.2 TEST-TIME memory** (85.2 vs 83.0)
WebShop:  +9.5 = +7.5 training + 2.0 test-time
=> a gradient-free port of the test-time apparatus targets a **~2pp effect**.
And on ALFWorld's largest category (Pick) the full system is **13.0pp WORSE** than memory-free
(87.0 vs 100.0).

## NUMBERS OUR ENTRY GOT WRONG
- **WebShop Score/SR INVERTED.** Table 1 header is `Avg. SR | Score | SR`. Correct: **SR 75.6,
  Score 87.4** — we filed "Score 75.6 (SR 87.4%)". Confirmed 3 ways: Score>SR in every row; Sec 4.2
  says "success rates of 85.2% on AlfWorld and **75.6% on WebShop**"; the +9.5/+39.7 deltas only close
  using 75.6 as SR.
- **The OOD `w/o memory 83.0` row is NOT an OOD measurement.** It is BYTE-IDENTICAL to Table 2 across
  all six categories AND the average, while every other row differs. ALFWorld ID=140 games, OOD=134 —
  different denominators make identical percentages essentially impossible (Look 68.4 = 13/19 exactly).
  Plain reading: CARRIED OVER, not re-run.
  => **RETRACT "raw memory falls 6.7pp BELOW memory-free under distribution shift"** — it compares an
  OOD number (76.3) against an IN-DISTRIBUTION one. A gate-scope category error, the exact class our
  own entry warns about.
- Claim "naive memory injection is actively harmful" **REVERSES SIGN WITHIN THE PAPER**:
  `RL + Raw Memory` is **+6.5 ABOVE** RL-only on WebShop (72.6 vs 66.1) while -6.3 below on ALFWorld.
- techniques: retrieval top-k=3 but **only top-1 is RECONSTRUCTED** (mem_adaptor.retrieval_top_k=1),
  and the adaptor output REPLACES the whole memory block => exactly ONE short principle (or nothing)
  is injected. Also reconstruction fires **only on retrieval steps** (schedule: on_memory_only),
  1-5 times per EPISODE, not per action — my brief's "before EVERY action" premise was WRONG.
- Paper says tensor_model_parallel_size=1 (A.2); both training scripts set **2**.
- Compute FOUND in repo: 8 GPUs x 1 node, 200 steps, 128 parallel envs. Wall-clock still absent.
- Licence SPLIT: GitHub LICENSE = Apache-2.0; README badge AND HF card say **MIT**. Both permissive.
- Undisclosed reward term: use_invalid_action_penalty=True, coef 0.1 — absent from the paper.

## CREDIBILITY 3 -> 2: THE CORROBORATION POINT WAS UNEARNED
Stage 1 awarded +1 for "independent corroboration of the MECHANISM (reproduced by intake-899 and
intake-935)". Verified against both entries:
- **intake-899's mechanism is the CONSOLIDATION/REWRITING SCHEDULE** — and its own claim 4 states raw
  episodic injection is FINE ("raw episodic trajectories match or beat abstracted memories").
- **intake-935's is heuristic curation x weak executor**, with MemP ABOVE control in 7 of 12 cells.
Neither reproduces MemHarness's finding. Four distinct mechanisms, not one replicated finding.
COMPOUNDING: the `RL + Raw Memory` baseline IS EvolveR (arXiv 2510.16079), **first author Rong Wu —
the SAME first author as MemHarness**, self-reproduced. The central negative-transfer baseline is not
independent.

## THE SkillOS "CONTRADICTION" DOES NOT EXIST — baseline-mismatch artifact
- MemHarness gradient-free arm vs ITS correct control (w/o memory): LOSES ON BOTH.
- SkillOS-base vs no-memory: WINS ON BOTH (ALFWorld 53.1 vs 47.9, 63.6 vs 61.2; WebShop 38.6 vs 33.3,
  43.4 vs 41.5).
The ALFWorld/WebShop flip in intake-935 is **SkillOS-base vs ReasoningBank** — an entirely different
comparison. Like-for-like against a no-memory control, BOTH PAPERS POINT THE SAME WAY.
=> DELETE contradicting_evidence item 2 and recommended_action #4. I reported this contradiction to the
operator as a real finding; it is not.

## THE REAL POLARITY (genuine, well-evidenced, and it favours us)
Driver is **whether stored memory carries transplantable-but-wrong CONCRETE ENTITIES**:
| signal                          | ALFWorld | WebShop |
| raw memory vs RL-only           | **-6.3** | **+6.5**|
| reject rate, correct source     | 8.7%     | 56.0%   |
| reject rate on APPLICABLE memory| 0.6%     | 72.1%   |
ALFWorld memories are ENTITY-BEARING procedures — Fig 12's retrieved memory drags "credit card" and
"coffee table" into a cup/sidetable task; verbatim replay would emit an INVALID ACTION, and
reconstruction re-grounds the entities. WebShop memories are ENTITY-FREE heuristics ("cross-reference
attributes before clicking") — harmless when replayed, rarely actionable.
**Our autopilot/trace memory is heavily entity-bearing — file paths, config keys, flag values, model
names, PIDs, commit SHAs. That places us squarely on the ALFWorld side**, where verbatim replay is
actively harmful and re-grounding has the most headroom. Strongest reason to test the pattern at all —
and it is a hypothesis about OUR data, not an imported ranking.

## COST: MY BRIEF'S PREMISE WAS BACKWARDS
Reconstruct-before-inject is **net CHEAPER on the agent's context than raw injection**: the adaptor
output REPLACES the <memory> block, and on <EMPTY> the block is DELETED entirely. Three retrieved raw
memories become one short sentence, or nothing. On a bandwidth-bound CPU decode path that is FAVOURABLE.
Agent's own estimate (labelled as theirs): decode overhead ~4% ALFWorld / ~5.5% WebShop;
worst case ~13% at the 256-token cap every event.
**THE REAL COST IS KV-CACHE PREFIX THRASH, which the paper cannot tell us.** The reconstruction call is
a SEPARATE PROMPT WITH A DIFFERENT PREFIX from the agent's rolling context. Interleaving them on one
llama-server slot forces a cold ~270-880-token prefill each event and EVICTS the agent's cached prefix.
Mitigation is architectural and the repo already supports it (use_actor_rollout_wg=false + a dedicated
mem_adaptor.model.path). **Any port must decide slot topology UP FRONT; the naive single-slot
implementation will look like a regression for CACHE reasons, not memory-quality reasons.**

## THE PROMPTS — RECOVERED VERBATIM (Appendix C Figs 7-8 + repo ppo_trainer.yaml)
System: "You adapt a retrieved memory principle into a concise reusable guidance for the CURRENT
situation and initial task, or output exactly `<EMPTY>` if the principle does not apply. Do not write
chain-of-thought, first-person reasoning, or a step-by-step action plan."
Fallback on <EMPTY>: "No validated memory principle applies; rely on observation and reasoning."
Sampling: max_new_tokens 256, temperature 1, top_p 1.0, empty markers ["<EMPTY>","<empty>"].
**CRITICAL: there is NO critique step and NO <EMPTY> CRITERION.** The paper's five-stage narrative
("memory critique assesses its applicability and identifies state mismatches") collapses in the
implementation to a single subordinate clause. The portable artifact is FAR THINNER than our entry
implies — and that is also why it fails zero-shot: the prompt carries no criterion, so all the
discrimination has to live in the weights.
Also OVERTURNED: our entry said prompts were "not fully reproduced in the paper body." Appendix C
reproduces all of them.

## THE `<EMPTY>`-IS-SHALLOW INFERENCE IS OVERTURNED
Invariance holds only for source REMOVAL (8.7->7.8). CORRUPTING the source moves rejection sharply
(8.7->13.3, 56.0->63.3) and the paper's own reading is "the policy actively compares historical and
current states." Rejection is state-comparison-dependent — LEARNED, not shallow.
SURVIVING justification for porting <EMPTY> first is different and stronger: it strictly REDUCES
injected tokens and is FAIL-CLOSED.

## LEDGER
1 reconstruct-before-inject as a 2nd arm -> **KEEP, re-scoped as EPYC-ORIGINAL** (UTM-M11), with a
  MANDATORY no-memory control, the ~2pp ceiling stated, and slot topology decided first
2 port <EMPTY> first -> **KEEP, rationale REPLACED** (token reduction + fail-closed, not shallowness)
3 "third independent data point" -> **DECLINE, premise false.** Redundant anyway: UTM-M9 (no-memory
  control for every memory A/B) already exists and is open. Append a note recording MemHarness as a
  FOURTH, DISTINCT mechanism.
4 domain-conditionality contradiction vs 935 -> **DECLINE, contradiction does not exist.** UTM-M10
  already carries the correct nuance. Replace with the entity-bearing polarity note.
5 latent guidance -> **DECLINE as adoptable; record as observation.** Real in-distribution but
  (a) confounded — the paper never states the GRPO baseline got the same cold-start SFT, (b) its OOD
  support is a copied row, (c) needs 8-GPU GRPO. Transferable corollary is a GATE not a project:
  75-79% of the gain is a training effect, so gradient-free effort is chasing ~2pp.
6 correct intake-938 in place -> DO (12 corrections, verification dive-overturned, credibility 3->2)

## DIVE-SURFACED SOURCES
- github.com/KnowledgeXLab/MemHarness — **the missing Table-2 cell (untrained policy WITH
  memory+reconstruction) is ONE CONFIG AWAY**: use_actor_rollout_wg=false + rollout.name=openai_api +
  trainer.val_only, and our llama-server exposes an OpenAI-compatible endpoint. The only way to
  actually measure the gradient-free ceiling.
- huggingface.co/KnowledgeXLab/MemHarness — checkpoints confirmed. **Recommend NOT downloading**:
  cold-start scores 7.6/17.6, below base model.
- arXiv 2510.16079 EvolveR — the 70.1 baseline, self-reproduced by the same first author.
- arXiv 2607.21273 "The Dark Room in the Reward Channel: Dense Prediction Rewards Collapse GRPO-Trained
  LLM Agents" — same benchmark + algorithm; tests whether ALFWorld/GRPO results of this shape are stable.
- arXiv 2605.29463 "Honest Lying: Understanding Memory Confabulation in Reflexive Agents" — candidate
  GENUINE corroboration, in place of the unearned intake-899/935 credit.
- arXiv 2601.02553 (SimpleMem) / 2601.03192 (MemRL) — whether injected blob SIZE explains the collapse
  would separate genuine negative transfer from intake-936's context-budget competition.
ADVERSARIAL: no independent replication or criticism exists. 4 days old; HF downloads 0, likes 0;
GitHub 14 stars. Every headline number is a single unreplicated run. All figures are OBSERVATION-grade.
