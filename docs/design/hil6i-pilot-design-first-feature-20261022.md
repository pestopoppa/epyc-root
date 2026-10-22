# HIL-6i: pilot design for the first feature of the sibling loop

**Date**: 2026-10-22. **Owner handoff**: [`harness-improvement-loop.md`](../../handoffs/active/harness-improvement-loop.md)
HIL-6i. **Parent plan**: [`hil6-sibling-loop-implementation.md`](hil6-sibling-loop-implementation.md)
§4, §5 and §7. **Design source**: [`harness-improvement-loop-design-20261006.md`](harness-improvement-loop-design-20261006.md)
(HIL-1 homes, HIL-2 items 1–22, "HIL-6 pilot requirements").

**This is build-only.** No run happens until three things are true:

1. the operator lifts the 2026-09-16 deferment on running a harness-improvement loop;
2. P0.4 acceptance and freeze are complete (HS-5b ordering: no tuning and no efficacy claim before
   it);
3. the protocols that apply to each comparison are in place.

The entrypoint and schedule are HIL-6j, which is blocked on those three. Every number this pilot
produces is an **observation** unless the row cites a human-ratified protocol id
([MEASUREMENT.md](../../MEASUREMENT.md) §2; Annex Q, `measurement/protocols/quality-eval.md`).
The design honours the requirements of P-AB-1 (paired, N ≥ 100 per arm, failures classified by
reason, flag-state attestation) and of P-QUAL-PROMO (fresh stratified draw, n ≥ 200, qids unseen
within 60 days). It does not cite either one as a claim. In code, `protocol_id` stays `None` until
a human cites one.

## Evidence pins

- epyc-root `origin/main` `d019249c5`, read 2026-10-22.
- epyc-orchestrator `origin/main` `df9d2eca`. The `src/harness_loop/` skeleton is unchanged since
  `55465c20`.
- The pilot instance in code landed on orchestrator `main` as `1ae0ad42` (authored on branch
  `hil6i-pilot-20261022` as `657f9da0`), with follow-up `05bfb4de`. The follow-up wires the screen
  to the landed S2 guard and checks the editor-port pin. The files are:
  - `src/harness_loop/pilots/__init__.py`;
  - `src/harness_loop/pilots/first_feature.py`;
  - `tests/unit/test_harness_loop_pilot_first_feature.py`.

  No existing file under `src/harness_loop/` was edited.
- Question pool: epyc-inference-research `benchmarks/prompts/question_pool.jsonl`, 77,823 rows,
  `corpus_version` `corpus-ev19b-20261021`. The pool was read for suite names, scoring methods and
  lengths only. No split was drawn from it.
- Identifiers. Every id below is read from the file named beside it. Zero inference was used;
  nothing was started or stopped.

## 1. Choice of home

HIL-1 gives six homes with a loop-mutable arm (§3.1–§3.6). §3.7 (skills) and §3.8 (not rebuilt)
have no mutable arm, so they are not candidates.

The six homes were compared on five criteria:

- a measurable arm;
- headroom;
- not being memory-accumulating (a §3.1/§3.2/§3.4 home carries the extra item-20 burden);
- a suite and split that exist now;
- how easily the item-12 "treatment fired" signal can be recorded.

| Home | Measurable arm today | Headroom | Item 20 | Suite / split | Item-12 signal |
|---|---|---|---|---|---|
| §3.1 profile memory | Harness-side only. On `/v1`, `x_memory=on` is "Recorded, not acted on, until HS-4 P2" (`src/api/routes/openai_compat.py`, `_apply_request_key_metadata`). | Unknown. HS-PROF-1 is about to measure this same surface: admission schema vs `PREF [category]`, BEAM preference/instruction following, judge `sonnet-5-5-low`. A loop that moved the incumbent now would collide with it. | **Yes** | BEAM via research `scripts/benchmark/run_hs_prof1_beam_arm.sh`. The metric is judge-scored. | Injection is mechanical. "Used it" needs a declared rule. |
| §3.2 agent notes | Only as a conditional leg after §3.1 shows an effect (HIL-2 table). | — | Yes | Reuses §3.1 | — |
| §3.3 session search | The Tulving `retrieved` arm. Its scorer is deterministic F1 (`score_tulving_run.py`), and the pool holds 456 `tulving_episodic` rows. | Unknown for a parameter. The defect the retriever's docstring describes (text searches ordered by `ts_utc DESC`, not bm25) was fixed in code on 2026-09-16 (`src/trace/query.py`, `order="relevance"` is the default). The retriever still asks for every match and re-ranks by bm25 itself, which bypasses the production `limit`, so the suite does not measure the production parameter. | No | Yes | Retrieval is harness-driven, so it "fires" on every item and the signal is trivial. The model-invoked `ms.search` (`src/trace/mcp_tools.py`) has no suite. |
| §3.4 background review | Proposal precision/recall has no named protocol and needs labels (HIL-2). | — | **Yes** | No labelled set | Idle-only background admission |
| **§3.5 delegation** | **Yes.** `orchestration/prompts/architect_investigate.md` is live: `architect_delegation` is a production default (`FeatureSpec("architect_delegation", False, True, …)`, `src/features.py`). It is resolved per request and consumed by exactly one role, `architect_general` (`src/api/routes/chat_pipeline/delegation_stage.py`). | Plausible but unmeasured. The prompt states seven decision rules, and the delegation stats already record mechanical failure reasons (`break_reason`, decision-guard rewrites, parse fallback) that a prompt rule could move. The item-13 count runs at freeze (§9). | No | Yes. The pool has deterministic scorers for every stratum the rules name (§3). | **Easiest.** The phase-A decision mode `direct`/`investigate` is recorded per item in `stats["phases"]` (`src/api/routes/chat_delegation.py`). The arm's bytes are proven by the prompt root (§4). |
| §3.6 compaction | Not live. `session_compaction`, `context_compression` and `session_compaction_llm_index` all default False (`src/features.py`). The index written by `compaction_index.md` reaches no model: per the UFH14-B1 note in `src/graph/compaction.py`, `TaskState.context` is never rendered into a turn prompt. The `/v1` fold is deterministic and needs histories longer than 8 messages (the P0.4 OpenCode suite). | Expected-null for the prompt | No | Needs the P0.4 shell suite, plus item-8 controls | Fold count is mechanical and easy |

**Decision: §3.5, the architect delegation prompt.**

- It is the only home whose mutable prompt is live by default and reaches a model on every
  delegated request.
- It is scored by deterministic pool scorers, with no LLM judge in the metric.
- It is not memory-accumulating.
- Its item-12 signal is a recorded field rather than an inference.
- It can be evaluated through `/chat` without writing the live file.

§3.1 has the richest suite infrastructure. It is second, because the injection is not served on
`/v1`, HS-PROF-1 owns the surface first, and item 20 applies to it. Nothing is dismissed here. Each
excluded home has a stated, source-cited reason, and §3.1 is the natural second pilot once
HS-PROF-1 resolves and HS-4 P2 wires the injection.

## 2. Feature, mutable surface, protected layer

- **Feature id**: `HS4-3.5-architect-investigate-prompt`.
- **Target**: `orchestration/prompts/architect_investigate.md`, kind `prompt`.
  - sha256 at design is `82dcf9d0cdece2e22f621ba9fe181001e6524a11f7dc2bb7e23f7414da902090`
    (orchestrator `df9d2eca`).
  - The freeze re-reads the file and pins those bytes as the unmodified control.
- **Builder**: `build_architect_investigate_prompt` (`src/prompt_builders/review.py`) through
  `resolve_prompt("architect_investigate", …)`.
- **Consumer**: role `architect_general`, model `Qwen3.8-Flash-Next-UD-IQ4_XS`
  (`orchestration/model_registry.yaml` `roles.architect_general`; CPU instance `:8074` in
  `orchestration/stack_topology.yaml`).
- **Delegatees**: the prompt names `worker_general` and `coder_escalation`. They are children of the
  delegation. Their tokens count in the `solver_child` seat (§8).

**Mutable surface.** The wording of the rules that decide between answering directly and
delegating, and the guidance for writing the discovery brief.

**Protected layer.** These parts are policy or a parser contract. `first_feature.protected_layer_reason`
refuses a candidate that changes any of them, always comparing against the unmodified control:

- the template slots `{valid_roles_section}`, `{context_section}` and `{question}` (the count must
  be unchanged, and no placeholder may be added);
- the decision grammar markers `D|` and `I|brief:`;
- the set of `to:<role>` bindings. Role choice is routing policy under HIL-1 §3.5;
- the closing `Decision:` anchor.

`make_candidate_screen` runs this check first and then the MHS-3 leakage check
(`substrate.leakage_reason`: since seam S2, orchestrator `5d646df9`, this is the real fail-closed
MHS-3 guard, and the driver's `original=` / `trace_context=` keywords pass through). The result is a callable
the future entrypoint can pass as the driver's `leakage` seam.

The rest of the protected layer, under item 21:

- the evaluator and the scorers;
- the splits and the split manifest;
- the reference arms;
- the attempt ledger;
- the proposers and their meta-prompt;
- the judge.

**Collision with AutoPilot.** PromptForge's mutable surface is every `*.md` under
`orchestration/prompts` (`scripts/autopilot/species/prompt_forge.py`, `PROMPTS_DIR`,
`rglob("*.md")`), and AutoPilot has mutated files there before. The pilot never writes the file.

- **Run precondition**: PromptForge excludes this target for the length of the pilot.
- If the live sha256 changes mid-run, the driver's `stale_original` screen refuses the candidates,
  and the run stops for a re-freeze.

## 3. Splits

**Source**: the question pool, at the corpus version pinned at freeze.

**Strata.** There are five, one per decision rule the prompt states:

| Stratum | Rule it tests | Scoring method |
|---|---|---|
| `mmlu_pro` | direct multiple-choice answer | `multiple_choice` |
| `simpleqa` | obscure fact: search via `worker_general` | `f1` |
| `math` | compute in the REPL, then `D|` | `exact_match`/`substring` |
| `cruxeval` | code reasoning | `exact_match` |
| `livecodebench` | implementation: delegate to `coder_escalation` | `code_execution` |

The per-item pass/fail comes from `scripts/benchmark/answer_scoring_vendored.score_response`
(orchestrator).

**Strata left out, with reasons.**

- `hotpotqa` and `longbench`: `build_architect_investigate_prompt` slices the question to 2,000
  characters and the evidence to 3,000. 7,365 of 7,405 `hotpotqa` prompts and all 503 `longbench`
  prompts are longer than 2,000 characters. Those items would measure the cap, not the prompt.
- `gpqa_diamond`: only 198 rows. The dataset asks that its items not be published, and the P3
  judge would send validation items to a cloud endpoint. The operator can add it if that egress is
  cleared.

**Sizes.** These are per stratum; totals are in brackets.

| Split | Per stratum | Total |
|---|---|---|
| T1, train (cycle-1 tuning) | 30 | 150 |
| V, validation (selection only) | 84 | 420 |
| T2, cycle-1 arrival (joins tuning in cycle 2) | 30 | 150 |
| T3, cycle-2 arrival | 30 | 150 |
| TEST (touched once) | 48 | 240 |

TEST is at least 200, the P-QUAL-PROMO floor. The splits total 1,110 qids.

**How the splits are frozen.** `first_feature.build_splits` is pure. It does not open the pool;
the freeze step passes the rows in.

1. **Eligibility.**
   - A row is eligible only if it is in one of the five strata, has no `image_path`, has a prompt
     of at most 2,000 characters and context of at most 3,000 characters, and is not in
     `exclude_qids`.
   - `exclude_qids` is computed at freeze. It covers EV-19 gold self-check outcomes `wrong` or
     `scorer_error` (`src/autopilot_core/gold_self_check.py`), `core_v2` members (so the pilot never
     overlaps the P-QUAL-T1 instrument), and qids seen in any evaluation within 60 days.
2. **Order and slices.**
   - The eligible qids of each stratum are ordered by `sha256(seed ‖ qid)`, with seed
     `hil6i-first-feature-v1`.
   - The ordered list is cut into consecutive slices in the order T1, V, T2, T3, TEST, so the splits
     are disjoint by construction.
   - A stratum with too few eligible qids refuses. The draw never shrinks silently.
3. **Manifest.** The freeze writes a manifest of the seed, strata, sizes, caps, exclusion count and
   the qids of every split. Its sha256 tags every `split_id` (`hil6i-T1@<sha12>` and so on) and is
   recorded in the design notes. The test checks that the draw is deterministic and independent of
   row order.
4. **Arrivals.**
   - T2 and T3 are drawn at freeze and stay sealed, with `arrived_at` empty, until the commit of the
     cycle before them.
   - They are emulated arrivals: held-back items from the same distribution, not newer tasks. A true
     arrival would come from a later pool refresh, which this design does not control.
5. **Labels.**
   - Labels never reach a proposer.
   - The proposer sees only the index-style `ProposerView`: trace ids, roles, mechanical event names
     and excerpts, plus a declared selection rule (item 7).
   - The fence is armed and echoed `active` on every arm.
   - The tripwire and the decoy canary run on every proposer context.
   - The splits are frozen when the run is authorized, not now. A draw made today could go stale
     against the 60-day rule before the deferment is lifted.

## 4. Arms

All arms run through `/chat` with `eval_fence=True`, `force_role="architect_general"` and
`real_mode=True`. Every arm is a byte-pinned prompt tree under the orchestrator base
`tmp/gepa_prompt_roots`, passed per request as `x_orchestrator_prompt_root`
(`src/api/routes/chat.py`, `_validated_prompt_dir_override`).

| Arm | Definition |
|---|---|
| Incumbent | Cycle 1: the unmodified bytes. Cycle 2: the harness that lineage committed in cycle 1. |
| Candidates | Two editor lineages, `local_editor` and `reference_editor`. Each starts from the same incumbent. Each proposes at most 2 candidates per cycle over 2 cycles. |
| Matched-rollout baseline (item 1) | The incumbent sampled k = 8 times per validation item. That is the solver rollouts one lineage spends per item: 2 cycles × 2 candidates × 2 runs. The answer is the label-free majority over the extracted answers. It is finalized under its own run_id. `ChatRequest` has no temperature, so if the architect's role sampler is deterministic the 8 samples coincide; that is reported, not hidden. |
| Unmodified control (item 6) | The bytes pinned at freeze. It equals the incumbent in cycle 1 and differs from it in cycle 2 whenever cycle 1 committed. This is stated per run, under its own run_id. |
| Verification arms (items 4 and 17d) | Selection modes over the same validation evaluations: `with` (the scorer outcomes plus the sign-test gate); `none` (the first screened candidate in proposal order, committed without looking); `self_judged` (the local editor picks among its own candidates without labels). The P3 judge matrix is a fourth, cross-model mode. Each mode's choice is reported on the arrival split. Only `with` can commit. |
| Per-role arm set (item 19) | One consuming role and one feature, so n + 2 collapses to all-on (delegation on, arm prompt) and all-off (`allow_delegation=False`). Leave-one-out is the same as all-off. No verdict transfers to another role or model. The mechanism is not a reviewer, so `reviewer_model` is empty. |
| Editor capability (P2) | `local_editor` vs `reference_editor` on the same splits, the same executor and the same dossier rule, with the same ported meta-prompt (§11). Gain is reported with run-to-run noise. No claim of local feasibility is made. In cycle 2 each lineage's dossier comes from its own committed harness. |
| Reference-trajectory diagnosis (M9) | A separate local-editor proposal whose dossier also carries one T1 trajectory that reached a scorer-passing answer. It implies an outcome, so it stays outside selection: never committed, never in the ledger, reported apart. |

**Cycles (P1).**

- **Cycle 1** tunes on T1, selects on V and evaluates the committed arm on T2 with no tuning.
- **Cycle 2** re-tunes on T1+T2 from the cycle-1 harness, selects on V and evaluates on T3.
  - `first_feature_design(cycle=2)` builds that design with `train = T1∪T2` and `arrival = T3`.
  - It runs on the same loop journal, so the attempt ledger resumes and keeps one alpha budget.
- **TEST** is touched once, for the reported claim.

## 5. Editors and judge (P2, P3)

- **Local editor**: `Qwen3.6-35B-A3B-MTP-Q8_0`. This is the 35B-A3B MoE served as `frontdoor`, and
  as `worker_general` by alias (`orchestration/model_registry.yaml`). It is the "30B-A3B class
  served on EPYC".
- **Reference editor**: `gpt-5.6-luna`, OpenAI family, through the codex CLI. It is the `model` of
  the `codex-luna-low` entry in `orchestration/cloud_judges.yaml`, used here as a proposer through
  the HIL-6h reference-editor adapter, not through the judge endpoint.
- **Judge**: `cloud:sonnet-5-5-low`, the exact-version pin for `claude-sonnet-5-5` (`claude_cli`
  transport) in `orchestration/cloud_judges.yaml`.

**Family-correlation caveat.**

- The judge is Anthropic. The local editor and the consumer are Qwen, and the reference editor is
  OpenAI, so the judge shares a family with no proposer.
- An Anthropic reference editor would put the judge in its family; the reference editor is
  OpenAI-family to avoid exactly that.
- `codex-luna-low` (`gpt-5.6-luna`) is the cross-family judge option. It would share the reference
  editor's family, so it is not used. It becomes the judge only if the operator moves the
  reference editor to an Anthropic model.
- The test asserts all of this, including the stronger condition that the judge's family differs
  from the reference editor's, which the validator does not require.

**Further cautions.**

- Both cloud entries are `verified_live: false`.
- Judge calls send V items to Anthropic. Reference-editor calls send T1 dossier excerpts, which
  include question text, to OpenAI. The operator clears egress for the five strata before any run,
  and each call log records its egress.
- The current typed endpoint is `/v1/typed/coherence_judge`, which is not a credibility matrix.
  HIL-6h (orchestrator `43bc90a7`) defines its own schema in
  `src/harness_loop/credibility_judge.py` (`epyc.orchestrator.hil_credibility_judge_*.v1`).
- The incumbent wins ties, and the matrix must have no empty cell and pass the zero-LLM argmax
  check (item 17).

## 6. Runs, CI, MDE and validation power (items 5 and 11; M9)

**Runs and CI.**

- Every arm is evaluated twice (`runs = 2`) on each split it touches, in independent sessions with
  the same pins.
- The item score is the mean over the two runs (0, ½ or 1).
- CI: a paired bootstrap over items, resampling tasks rather than runs, at 95% with 10,000
  resamples. Single-arm pass shares get a Wilson 95% interval.
- The two incumbent runs form an A/A pair, and their discordance measures the run-to-run noise.

**Alpha.**

- 2 lineages × 2 cycles × 2 candidates = 8 planned attempts.
- They draw on one ledger with a budget of α = 0.05, so each attempt gets α = 0.00625. Alpha is
  reserved when an attempt opens; an interrupted attempt still consumes it (item 21).

**Power statement**, declared before the run:

| Quantity | Value | Derivation |
|---|---|---|
| `paired_n` | 420 | V, 84 per stratum × 5 |
| assumed discordance ψ | 0.20 | Replaced before any candidate is evaluated by the measured A/A discordance |
| `expected_discordant` | 84 | 420 × 0.20 |
| critical wins k | 54 | Smallest k with P(X ≥ k \| Bin(84, ½)) ≤ 0.00625; exact one-sided sign test |
| `min_win_share` | 0.643 | 54 / 84 |
| `mde` | 0.075 | Absolute pass-share gain. Power 0.84 at ψ = 0.20, conditional on D = 84 |
| not powered | 0.05 | Power 0.41. A null at a true 5 pp gain is uninformative |
| equivalent `IncumbentWinsTies` margin | 0.0571 | (2k − D) / n. Exact only at D = 84; see gap G3 |

**Near-ceiling statement (M9).**

- If the incumbent's validation pass share p is above 0.9, `expected_discordant` is restated from
  the headroom: at most n(1 − p) wins are possible.
- At p > 0.871 (that is, 1 − 54/420), no candidate can reach 54 wins even with zero losses. The
  run is then labelled underpowered before any candidate is evaluated, and its null is
  uninformative.
- Per-stratum readouts are diagnostic. A stratum whose incumbent pass share is above 0.9 is
  labelled underpowered. `math` is the likeliest.

## 7. Stopping rule

The horizon is fixed: exactly 2 cycles per lineage and at most 8 attempts.

1. **Underpowered check, before any candidate.** Once the A/A gives the discordance, the run is
   labelled underpowered, and no candidate is evaluated, if either:
   - a candidate at the MDE would pass with power below 0.8; or
   - the incumbent pass share exceeds 0.871.

   n is never enlarged mid-run; a larger n means a re-freeze.
2. **Early stop** happens only on `AlphaBudgetExhausted`, or on an infra `NON_COMPARABLE` result on
   the incumbent.
3. **Outcomes.** A cycle-2 KEEP_BASE is an outcome, not a failure, and a one-cycle gain is not
   evidence that the loop compounds (`intake-2143#00`).
4. **Reporting.** The reported state is the committed final state after cycle 2, with the
   per-cycle trajectory. There is no best-of-rounds figure. For a lineage with a candidate pool,
   report committed vs pool-oracle vs all-candidate-oracle; the oracle gold is used for diagnosis
   only (item 9).

## 8. Exclusions, regression readout, token-cost columns

**Exclusions** (item 15, HIL-20 #3), declared now.

- *Before the draw*: the §3 eligibility rules and `exclude_qids`. If the code-execution sandbox is
  unavailable at freeze, `livecodebench` is dropped as a whole stratum before the freeze, never
  mid-run.
- *During the run*: nothing is removed from the primary slice.
  - Infra failures count as failures and are classified by reason, as P-AB-1 requires: backend
    outage, timeout, empty, or genuine.
  - The robust slice drops any item with an infra failure in either arm. It is diagnostic only and
    is reported with per-arm exclusion counts.
  - When exclusions concentrate in one arm, the primary slice is the claim.
  - Ungradable runs are reported both ways: excluded, and counted as failures.

**Regression set** `hil6i-arch-deleg-regress-v1` (item 18):

- the V items the incumbent passed in both runs, with a right-to-wrong count per arm;
- the non-degeneracy readouts in the same run: empty-answer share, decision-line parse-failure
  share, and the shift in the investigate rate.

The five strata hold no labelled unsafe-control items, and none are invented. A capability-flat
result is not a no-regression result.

**Token-cost columns** (items 2 and 16; HIL-20 #1, #2, #4, #5).

- Seats: `proposer`, `judge`, `solver` (the architect, as parent) and `solver_child` (the
  delegatees).
- Per seat, report uncached prefill, decode and cached prefill, plus the cached share.
- Per solved task, report uncached prefill + decode, as parent, child and total, with the
  child-authored share.
- Report slot-occupancy seconds on the CPU claim, in cost-of-pass form, with the independence
  caveat.
- A counter that was not captured, such as a cloud CLI that reports no usage, is `None`. It is
  never zero.
- Headlines are computed over every session started, with failed and cancelled counts beside them.
- The cumulative-solved-by-turn diagnostic uses t_max = 3, the architect's `max_loops`. It is an
  observation.

## 9. Treatment fired and headroom (items 12 and 13)

**Treatment fired.**

- `treatment_fired` is the number of items whose phase-A architect call resolved the arm's prompt
  bytes. The proof is the resolver's provenance under that arm's prompt root.
- Reported beside it, per arm:
  - the `I|` (investigate) decision rate;
  - the share of decisions rewritten by `_apply_decision_guards`;
  - the share answered with no model call.
- If `treatment_fired == 0`, the result is labelled *not exercised*, and its null says nothing about
  content (the M9 zero-adoption rule; a report rule in HIL-6h).

**Headroom**, counted at freeze, before any arm is generated.

- Scan the incumbent's existing `architect_general` delegated-mode traces for:
  - `break_reason` in {`max_loops`, `semantic_dedup`, `role_repetition`, `token_budget`,
    `wall_clock_budget`, `pre_delegation_architect_error`};
  - decision-line parse fallback;
  - decision-guard rewrites;
  - the HIL-12 L2 categories.
- Count the share of baseline failures a prompt rule could prevent.
- If that share × the baseline failure rate is below the MDE (0.075), record an expected-null note
  and generate no arms.

## 10. Writing to the belief kernel

The producer call already exists: `src/harness_loop/finalize.py` (VB-HIL-WRITE, orchestrator
`5195ad53`).

- It runs once per paired comparison, after the raw result file closes.
- Each control arm, including the matched-rollout baseline, is finalized under its own run_id.
- `protocol_id=None` unless a human cites one.

No new source row is needed.

## 11. M9 extras

| M9 extra | In this pilot |
|---|---|
| near-ceiling suite power statement | §6. `notes["m9.near_ceiling_power"]` |
| zero-adoption diagnosis | §9. `notes["m9.zero_adoption"]` |
| reference-trajectory diagnosis arm | §4, a diagnostic arm outside selection. `notes["m9.reference_trajectory_arm"]` |
| offline-then-freeze | Arms are prompt trees passed per request. The live file is never written, and promotion is a separate change a human applies. `notes["m9.offline_then_freeze"]` |
| local-editor port of published prompts | Ported from GEPA 0.0.26 `InstructionProposalSignature.default_prompt_template`, as installed in the orchestrator `.venv`. Template sha256 `7949f860c308b9d99a2091d2cadc2c18824f684ca373260d285eecd3f3e63336`; a test checks it against the installed package. The port does two things. It replaces the inputs/outputs/feedback slot with the outcome-free dossier (item 7). It drops the "include niche factual information" sentence, because that sentence invites eval content into the harness (MHS-3). HIL-6h landed the port: `src/harness_loop/editor.py` `LOCAL_EDITOR_META_PROMPT_SHA256` `107dca4cf2760eb187e2a1aece256dd6abb7795cce50efae4f09918a3edd7d3a` over (system, template); a test checks that the pilot and the editor name the same source. Both editors get the same port. `notes["m9.local_editor_prompt_port"]` |
| planner self-modification | Excluded. The proposer, its meta-prompt, the judge and the evaluator are protected (§2). `notes["m9.planner_self_modification"]` |
| regression-set definition | §8, `hil6i-arch-deleg-regress-v1`. `notes["m9.regression_set"]` |

## 12. Requirements map

`first_feature_design(splits, cycle=1|2)` satisfies `unmet_requirements() == []` for both cycles.
That is tested in `tests/unit/test_harness_loop_pilot_first_feature.py`.

| Requirement | Satisfied by |
|---|---|
| P1: ≥ 2 cycles, arriving split | `cycles=2`; T2 and T3; the cycle-2 design has `train = T1∪T2` and `arrival = T3` (§3, §4) |
| P2: editor-capability arm | `local_editor_model`, `reference_editor_model`, `served_local_models`; `notes["p2.editor_arm"]` (§4, §5) |
| P3: cross-model judge | `judge_model=cloud:sonnet-5-5-low`; `notes["p3.family_caveat"]`, `notes["p3.egress"]` (§5) |
| P4: memory-accumulating | Not applicable: §3.5 is not in `MEMORY_ACCUMULATING_HOMES`, and `stream_positions=()` |
| P5: items 7–22 | Rows 7–22 below |
| 1 matched-rollout baseline | `matched_rollout_baseline=True`; `notes["i1.matched_rollout_baseline"]` (§4) |
| 2 all seats' tokens | `token_seats ⊇ {proposer, judge, solver}`, plus `solver_child` (§8) |
| 3 disjoint splits, validation-only selection, single test touch | `build_splits`; the driver's validation-only selection and `final_test` (§3). See gap G2 |
| 4 with/without verification signal | `verification_arms={with, none, self_judged}`; `notes["i4.verification_arms"]` (§4) |
| 5 ≥ 2 runs, CI, MDE | `runs=2`, `mde=0.075`; bootstrap CI (§6) |
| 6 unmodified control | `unmodified_control=True`; `notes["i6.unmodified_control"]` (§4) |
| 7 isolation | Driver: fence, tripwire, decoy canary, outcome-free view. Sealed arrivals and egress clearance (§3, §5) |
| 8 context-policy contract | Not applicable outside §3.6 (`context_policy_controls=∅`) |
| 9 arrival and commitment | Arrival evaluation with no tuning; `stopping_rule`; committed vs oracle reporting (§7) |
| 10 harness growth | Driver `harness_bytes` per cycle. Rule count reported as the number of rule lines (§7) |
| 11 validation power | `paired_n=420`, `expected_discordant=84`, `min_win_share=0.643`; near-ceiling statement (§6) |
| 12 feature exercised | `treatment_fired` required on every result, with the investigate rate and guard-rewrite share beside it (§9) |
| 13 headroom | `headroom_note` (§9) |
| 14 pinned arm identity | Driver `ARM_PIN_FIELDS`. The final-result selection rule is the architect `D|` answer, else the synthesized answer after ≤ 3 loops (`max_loops=3`, `force_response_on_cap=True`) |
| 15 exclusions | `exclusions_declared=True`; `notes["i15.exclusions"]` (§8) |
| 16 token-cost columns | `ArmResult.tokens` per seat; the HIL-20 columns (§8) |
| 17 judged arms | `IncumbentWinsTies`, `VerdictMatrix.validate`, `choice_is_argmax` (§5) |
| 18 regression readout | `regression_set_id=hil6i-arch-deleg-regress-v1` (§8) |
| 19 per-role arm set | `per_role_arm_set=True`, `reviewer_model=""`; `notes["i19.per_role_arm_set"]` (§4) |
| 20 stream positions | Not applicable (not memory-accumulating) |
| 21 attempt ledger, protected layer | `alpha_budget=0.05`, 8 × 0.00625; `protected_layer_reason` (§2) |
| 22 arm prompt lint | Driver MHS-15 lint per candidate, recorded in the cycle event |

## 13. Gaps in the skeleton

These were recorded in the design notes. G2 and G3 were closed the same day by the seam builder;
G1 and G4 stand, with the workarounds below.

- **G1. One arrival split.** `PilotDesign` has a single `arrival`, and `run_cycle` refuses a tuning
  split that overlaps it. The cycle-2 re-tune on T1+T2 that P1 asks for therefore needs a second
  design (`train=T1∪T2`, `arrival=T3`) on the same journal. `first_feature_design(cycle=2)` is
  that design.
  - The skeleton test `test_two_cycles_with_arriving_split` notes that cycle 2 re-tunes on T1+T2,
    but it runs cycle 2 on T1 only.
  - **Fix**: a per-cycle `arrivals` field.
- **G2. Single-arm test touch.** `SiblingLoopDriver.final_test` evaluates one arm and then refuses.
  A paired test claim needs the committed arm and the unmodified control in the same single touch.
  **Closed 2026-10-22** (orchestrator `c69ba5a1`): `final_test_paired(committed, control)` evaluates
  both in one touch.
- **G3. No paired decision rule.** There is no paired sign-test `DecisionRule`, and no
  `PilotDesign.decision_rule` field. `IncumbentWinsTies(margin=0.0571)` matches the critical count
  only when D equals 84. **Closed 2026-10-22** (orchestrator `c69ba5a1`): `interfaces.PairedWinShare`
  is the exact one-sided sign test, and `pilots.first_feature.DECISION_RULE` pins it at α = 0.00625
  with a minimum win share of 54/84. There is still no `PilotDesign.decision_rule` field; the driver
  takes the rule as an argument.
- **G4. Missing design fields.** `PilotDesign` has no fields for the split-manifest digest, the
  target sha256, the editor meta-prompt pin, the egress clearance, or the per-cycle arrival. They
  are carried in `notes`.

## 14. Defects found while choosing the home

These are recorded for their owners. None of them is in HIL-6i scope.

- `build_architect_investigate_prompt` truncates the question to 2,000 characters and the evidence
  bundle to 3,000. That makes 99.5% of pool `hotpotqa` prompts and all `longbench` prompts reach
  the architect truncated on the delegated path (`src/prompt_builders/review.py`).
- The research `scripts/benchmark/tulving_trace_retriever.py` docstring still says
  `src.trace.query.query` orders text searches by `ts_utc DESC`. That was fixed on 2026-09-16:
  `order="relevance"` (bm25 before `LIMIT`) is now the default when `text` is given
  (`src/trace/query.py`). The docstring is stale, and its "ask for every match" workaround is no
  longer needed.
- The graph compaction index (`compaction_index.md`) reaches no model, as the UFH14-B1 note in
  `src/graph/compaction.py` already says. A loop must not target that file until a renderer
  consumes it.
