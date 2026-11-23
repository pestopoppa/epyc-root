# Dive — hookevorepo — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/HuangShengZeBlueSky/HookEvo/main/README.md", retrieved: "2026-11-23", sha256: "2e2853fdcd8f"}
> SOURCE-QUARANTINE: {url: "https://github.com/HuangShengZeBlueSky/HookEvo (depth-1 clone kept by the bearing dive at hookevo/repo/, reused read-only; HEAD 475b6dbad534cbd90dd318388a748e4d1c2a949a, re-verified with git ls-remote and git rev-parse on 2026-11-23)", retrieved: "2026-11-23", sha256: "n/a (git tree; anchors come from page.txt only)"}
> Extra reading material (not anchors): `evolution/src/dsh_evolve/abc.py` (312 lines, read in full), `evolution/src/astra_evolve/project.py`, `configs/abc/*/C-sol61/experiment.yaml`, `artifacts/*/evaluation.json`, `artifacts/alfworld/plugins/action-hint.mjs`, `evolution/src/dsh_evolve/assets/slot-c.mjs`, `evolution/src/astra_evolve/assets/harness-api.txt`, `evolution/pyproject.toml`.

Bearing entry: intake-2836 (HookEvo paper). That dive read the README, one config and `abc.py:~255-300`. This dive reads the whole controller, every shipped per-round record and the four configs.

## 1. Stage-1 fields

- **Title**: HookEvo (code companion of arXiv:2611.27294): "A Framework for Coordinated Plugin Evolution on Hook-Enabled Agent Runtimes".
- **Authors**: Shengze Huang et al. (12 authors, Tsinghua, NTU, Renmin, MIT, Peking, Southeast, Renlab AI, SMART; per intake-2836).
- **State**: GitHub `HuangShengZeBlueSky/HookEvo`, HEAD `475b6dbad534cbd90dd318388a748e4d1c2a949a` ("Link the published HookEvo preprint and cite its official arXiv record"), MIT, Python 3.10-3.12 plus Node.js 22.19 or later. The README links `REPRODUCING.md`, which is absent at HEAD.
- **Categories**: autonomous_research, agent_architecture, tool_implementation, benchmark_methodology.
- **Novelty**: low. Companion of an ingested paper; the new content is the controller, the shipped per-round records and the released plugins.
- **Relevance**: medium. The controller is the most concrete public acceptance loop in the harness-evolution cluster, and its shipped records quantify how in-sample acceptance behaves (claim 2).
- **Credibility**: 1 = peer-reviewed 0 (preprint companion) + within 12 months +1 + major lab / known contributor 0 + independent corroboration 0 + commercial bias 0. Same score as the paper entry; released per-round records are verifiable but first-party.
- **Verdict**: adopt_patterns. The operational patterns (per-round decision record, effect gate, sealed test schedule, executable-plugin install guard, infra-failure abort) are adoptable; the acceptance statistic itself is not (claim 1).

## 2. Key claims

**Claim 0 — the retention rule is as the paper says. CONFIRMED (abc.py:281).** After scoring the parent and the candidate on the same batch, `adopted = b[metric] > a[metric] and effect and (not val or val[1][metric] >= val[0][metric])`. `metric` is `strict_success` for ALFWorld, DBBench and OSBench and `mean_reward` for WebShop (configs). `effect` is true when the set of hook activations (hook, text, reason, annotation of the `scale-slot` method, excluding the load event) differs from the parent's on at least one matched (task, trial, seed) row (abc.py:204-210, :277). Validation exists only where the task list has a `validation` split (OSBench). Comparison is strict `>`: the config key `min_improvement: 0` is read only by the generic path at `project.py:184`; `abc.py` never reads it, so any one-task difference with a changed hook output is adopted. Test scoring is refused until a `training-seal.json` lists the test targets (abc.py:226-228, :292-295); every promoted checkpoint plus the parent is then tested, with a pass-cubed field added (abc.py:306).

**Claim 1 — "matched-task retention" is an in-sample test, in two ways. CONFIRMED (code).** (i) Evidence overlap: `trace_sample` (abc.py:70-79) draws 8 failing and 4 passing rows, seeded by the version string, from the parent's rows on the round's batch, truncated to 2,900 characters each, and puts them in the improver's prompt; the candidate is then scored on that same batch. (ii) Batch recurrence: `Project.batch` (project.py:74-80) maps round i to batch `((i-1) mod 6) + 1`, so over 40 rounds each 50-task batch supplies evidence and acceptance 6-7 times, and the parent is re-scored on a recurring batch after earlier proposals already saw its failures. The previous measured decision (before/after, repaired, regressed, the proposal's own rationale) is also written to `feedback.json` and fed into the next prompt (abc.py:110, :287).

**Claim 2 — what the shipped per-round records show. NEW, read from `artifacts/*/evaluation.json` (arithmetic mine).** Adoptions: ALFWorld 6 of 40 rounds (rounds 1-6 only; headline v06; no adoption in rounds 7-40), DBBench 18 of 40 (headline v35), WebShop 34 of 80 (two stages; headline v12), OSBench 2 of 40 (rounds 1 and 3; headline v01). Test curves of the promoted checkpoints that were tested: DBBench rises from 48.89 (v01) to 70.56 (v35) over 16 tested checkpoints, so in-sample adoption transferred there; WebShop test is 45.67 at v02, peaks at v12 (47.00 +/- 0.87 in the search run), then sits at 43.00-46.17 for the tested versions v16-v36, so the later tested checkpoints never beat v12 (the `tests` list names versions 7, 9, 12, 16, 17, 18, 24, 25, 27, 32 and 36 that are not adopted rows in `rows`, so for WebShop the two lists do not describe one lineage; the source string is a two-run concatenation, and I do not map test versions to adoption rounds); OSBench test is 41.67 (v01) and 40.05 (v03); ALFWorld has a single tested checkpoint. The WebShop headline 48.17 +/- 0.29 comes from a separate re-evaluation of the same checkpoint inside `competitors-webshop-frozen-20261102/jobs/ours-v12`, 1.17 points above the 47.00 the search run measured for v12. Gate behaviour: positive train delta but rejected happens (DBBench rounds 8 and 33 at +2.0 and +4.0; WebShop six times at +2.0; OSBench round 20 at +1.25), which is the effect gate or, for WebShop, the mean-reward metric; WebShop adopted five rounds with a negative success delta (mean-reward metric). Adopted deltas of one task (2 points on a 50-task batch) occur (DBBench 2 of 18; WebShop several). ALFWorld SD is 0.00 because the three repeats are identical (104/109 each): the executor runs at temperature 0, so the reported "SD over three executions" measures runtime non-determinism, not sampling uncertainty of the test set; OSBench repeats do differ (43.75, 40.97, 40.28 percent).

**Claim 3 — the released configs reproduce the headline runs. OVERTURNED for three of four benchmarks.** `evaluation.json` records the headline run sources: ALFWorld `simple-dsh-l4-fixed40-20261030/.../alfworld/sol61-high` with train scores in whole-percent steps (17, 18, 68, 77, 91), implying a pool of at least 100 tasks per round, whereas the released `configs/abc/alfworld/C-sol61` rotates six 50-task batches (300 distinct tasks); OSBench `.../C-sol61-narrow`, whose config differs from `C-sol61` only by `data: narrow` and a different 80-task `train.jsonl` ("narrow" is not defined in the README or paper); WebShop a two-stage 80-round continuation from `webshop-methods-20r-.../method2-sol61`, while the paper's Table 1 lists 100 WebShop training tasks and the released config rotates 300 distinct task ids. DBBench is the one headline whose source name and 2-point train granularity match the released config. `REPRODUCING.md` is absent, so the intended reproduction path is not shipped.

**Claim 4 — compute and cost signals. PARTIAL (no accounting in code, only structure).** The improver is an external frontier model driven through `codex exec` with `--sandbox read-only`, model `gpt-6.1-sol`, effort high, one JSON-schema reply per round, `timeout=900` s (abc.py:142-146), `optimizer_slots` default 4, and a `quota-hold` file that halts the run when events contain "usage limit" or "quota exhausted" (abc.py:136-150). The executor is local Qwen3-4B-Instruct-2507 at temperature 0, `max_model_calls: 15`, `max_tokens: 4096`, `concurrency: 4`, `timeout_seconds: 1500` per episode, `max_context_tokens: 32768`. Evaluation slots default to 6 concurrent batches and 2 for OSBench (abc.py:233-237). No token, dollar or wall-clock total is recorded by the controller. Derived bounds (mine): per round at most 2 x 50 executor episodes of at most 15 calls (parent plus candidate; parent reuse when the (parent, batch) pair was already scored), one improver call of at most 900 s, hence at most 10 h of improver wall time per 40-round run; test cost is 3 x N episodes per promoted checkpoint (DBBench: 900 episodes per checkpoint, 16 tested).

**Claim 5 — what is safe to copy. CONFIRMED (code).** `install()` (abc.py:158-183) accepts one aspect per proposal, caps the skill at 12,000 characters, requires `export function create(`, rejects modules that mention `import|require|process|fetch|globalThis|eval|Function`, and runs `node --check`; an invalid candidate is recorded as a rejected decision, not an error. `verify_hooks` (abc.py:190-195) aborts the whole search if any tool message carries the known runtime defect string, so an infrastructure fault is never scored as candidate failure. Runs are resumable (a decision file per round, `controller.lock` flock, atomic writes). Slots are flock-based file semaphores.

## 3. Reported results

The README repeats the paper's leaderboard (Qwen3-4B-Instruct-2507 frozen executor, mean held-out success with SD over three executions): HookEvo Sol scope C ALFWorld 95.41 +/- 0.00, DBBench 70.56 +/- 0.38, WebShop 48.17 +/- 0.29, OSBench 41.67 +/- 1.84; Life-Harness local 87.77 / 64.11 / 41.33 / 36.81; Life-Harness published 88.07 / 65.00 / 45.50 / 39.60; Bare published 16.51 / 44.00 / 29.50 / 21.50; Harness-R1 paper 29.10 / 55.70 / 38.60 / none (WebShop on 500 tasks). These restate intake-2836 and are not corroboration. Repo-only additions are the per-round records of claim 2 and the held-out sizes (109, 300, 200, 144 tasks; `test.jsonl` holds each task three times).

## 4. Performance-principles table (mechanism and cost model)

| Mechanism | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Paired candidate-versus-parent evaluation with an effect gate | YES for a 4B executor served on the MI210; no kernel dependence; at temperature 0 the paired diff is mostly deterministic, so the gate separates real behaviour change from scheduling noise. | YES, host side; Node 22.23.4 and Python 3.12.3 are present on this host (observed), executor episodes are the cost. |
| Hook runtime (system-prompt/assemble, tools/pre-execute, observe/explain handlers) | n/a (host process) | YES, lightweight JS; maps to Claude Code PreToolUse/PostToolUse/UserPromptSubmit and opencode plugin hooks. |
| Frontier-model improver via CLI, per-round cost | n/a | n/a; paid on our existing Claude/Codex roster, not local silicon. |
| Executor concurrency 4 with 15-call episodes | PARTIAL. Small-ubatch verify-like batches; throughput is whatever the served 4B model gives; no number in source. | PARTIAL, bandwidth-bound decode on a 4B model. |

## 5. In-house state

- **BSV-2** (autopilot-program.md:L123 @ d785b6d) already specifies paired differential testing with "signature diff severity" and a McNemar-based report (`scripts/autopilot/bsv_paired_report.py`, `paired_stats.py` per :L3059); HookEvo's effect gate is the same idea in a weaker form (set inequality of activations, strict `>`, no McNemar). What BSV-2 lacks: a persisted per-round decision record with `repaired`/`regressed` counts fed to the next proposal, a sealed-test guard, and an evidence/acceptance split. AutoPilot is intentionally stopped; this is design and code only.
- **BEP-5** (autopilot-program.md:L2214 @ d785b6d) generalises Meta-Harness Tier-2's git-commit-before and `ast.parse` validation; `install()`'s regex-plus-`node --check` guard is a second precedent for that row.
- **HIL-2 checklist items 9 (arrival split) and 11 (power)** and DPF-1132-L2 (harness-program.md:L1981 @ d785b6d) already record AHE evolving and scoring on the same 89 tasks as a worked counterexample; the WebShop curve in claim 2 is a second one.
- **Infra-failure doctrine**: `orchestration/repl_memory/q_reward.py` carries the rule that infrastructure failure is "the ABSENCE of a measurement, never a bad one" (comment above `gate_penalty`, ~L165-169 @ 1a10541b); `verify_hooks` is the same rule as a controller abort.
- **Scheduling**: flock slots and the quota-hold file duplicate what rowflow claims and grants already do; nothing to adopt.
- SkillBank is stored text injected into context (harness-program.md:L973-L974), HookEvo's weakest scope A (intake-2836 section 5).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| HR1 | Append the HookEvo per-round statistics (adoption counts, WebShop tested checkpoints never beating v12, WebShop headline re-measurement, SD 0.00 from deterministic repeats) to the HIL-2 pre-first-suite checklist as worked case 2 beside DPF-1132-L2, citing `artifacts/*/evaluation.json` at 475b6db. Refines intake-2836 H1. | `harness-program.md` (harness-improvement-loop track, HIL-9 pattern: append to the HIL-2 checklist, zero inference) | doc-only | Done when items 9 and 11 cite the numbers; the question recorded is whether our first loop run uses an acceptance set disjoint from evidence. |
| HR2 | Add a sealed-test guard to the HIL eval runner and, if AutoPilot is relaunched, to its accept path: refuse any test-split scoring until the decision list is written to a seal file naming the test targets (abc.py:226-228, :292-295 pattern), and record the per-round decision as `{candidate, parent, batch, adopted, before, after, observed_effect, repaired, regressed, proposal}`. Refines intake-2836 H1. | `harness-program.md` (HIL track; `scripts/benchmark/hil_ab_sidecar.py::finalize_hil_run` is the named hook) with a cross-reference row in `autopilot-program.md` BSV-2 (stopped, design only) | code-only, zero inference | Question: can the seal be enforced without touching the measurement trust boundary? Done when a unit test shows test scoring raising before seal; futility if the runner has no per-round decision store (then file that gap and stop). |
| HR3 | Record `install()`'s envelope (single aspect per proposal, 12,000-character skill cap, forbidden-token regex, syntax check, invalid candidate stored as a rejected decision) and `verify_hooks` (known infra-defect string aborts the run) as the safety template for any executable-mutation class in the H2 design note. Refines intake-2836 H2 and cross-references BEP-5. | `harness-program.md` (HS-TD-2 region as in H2) and `autopilot-program.md:L2214` (BEP-5) | doc-only | Decision recorded in H2: admit an executable-handler class only with this envelope; done when the note lists the guards and the abort rule. |
| HR4 | Run the release's no-model smoke (`python -m pip install -e evolution` in a throwaway venv, then `python evolution/scripts/smoke.py ./runs/smoke`; scripted actor, synthetic task, Node 22 present) to confirm the controller and hook runtime start on this host. | `harness-program.md` (next to the H2 note) | CPU, minutes, no model | Question: does the scope A/B/C proposal-select-test loop run locally without a model account? Stop on answer when the smoke prints its final summary; futility if `npm` cannot fetch the runtime packages (record). |
| HR5 | DECLINE: copy `slot()` (flock file semaphore) and the quota-hold file. Reason specific to this entry: rowflow claims and grants already provide the same exclusion on this host, and quota-hold keys on Codex "usage limit" strings in `codex exec` events, which only matters for a Codex-driven improver. | n/a | n/a | n/a |
| HR6 | DECLINE: reproduce the four headline numbers from the released configs. Reason specific to this entry: `REPRODUCING.md` is absent and the released ALFWorld, OSBench and WebShop configs differ from the headline runs recorded in `evaluation.json` (claim 3), so a rerun would not be a reproduction; the transferable parts are covered by HR1-HR4. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `github.com/HuangShengZeBlueSky/HookEvo`: 2 hits (inside intake-2836 notes); read here, this is its entry.
- `github.com/Tianshi-Xu/Life-Harness` and arXiv:2605.22166: 0 URL hits, 4 arXiv-id hits inside other entries; being dived in this wave as `lifeharness` (it changes the fairness reading of HookEvo's baselines, ledger HR1's cited comparison).
- arXiv:2609.32423 PluginRSI: 0 hits; being dived as `pluginrsi` in this wave.
- DeepSeek Harness repository (runtime and plugin API): present in the index per intake-2836; no further source needed.

## 8. Contradiction / adversarial pass

- Acceptance is strict `>` with no tolerance and no significance test; `min_improvement` is unused by `abc.py`. One-task adoptions happen. In-sample at two levels (evidence overlap, batch recurrence).
- Released configs do not match the headline runs for ALFWorld, OSBench and WebShop; Table 1's WebShop train size (100) disagrees with the released 300-task rotation; "narrow" is undefined; the paper says the ALFWorld Sol-C cell of its scope table (Table 3) comes from a 20-round run while the leaderboard history is a 40-round budget, so the two ALFWorld numbers are different runs.
- WebShop later tested checkpoints did not beat v12 (peak at v12); the `tests` and `rows` lists do not describe one lineage; the headline is a re-measurement 1.17 points above the in-run measurement of the same checkpoint.
- Peak-checkpoint reporting among tested promoted checkpoints; SD from temperature-0 repeats is not a confidence interval (ALFWorld 0.00).
- `REPRODUCING.md` linked and absent. No independent replication; the README restates the paper's table.

## 9. Read depth

read_depth: FULL for the README, `abc.py`, the four C-sol61 configs, the four `evaluation.json` files (all rows), `slot-c.mjs`, `harness-api.txt`, `pyproject.toml`, `project.py` lines 60-130 and :184, and one released plugin (`action-hint.mjs` head). PARTIAL: other plugins, adapters, benchmark sources, the DSH runtime. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | README How the search works step 3 | "Retain a candidate when the training objective improves, an emitted hook output changes, and validation performance holds or improves when validation is configured."
- claim 0 | page | README How the search works step 3 | "Compare the candidate and parent on matching tasks, trials, and seeds."
- claim 5 | page | README How the search works step 4 | "Accepted code persists across rounds. Each new episode starts with fresh runtime state."
- claim 2 | page | README Released harnesses | "Each row gives the highest measured checkpoint reported for that benchmark"
- claim 2 | page | README Released harnesses (OSBench row) | "Its executable composition is empty."
- claim 2 | page | README Main leaderboard note | "Local results show mean held-out success (%) ± sample SD over three executions."
- claim 3 | page | README header links | "[Evaluation and search](REPRODUCING.md)"
- claim 3 | page | README Main leaderboard note | "Harness-R1 specifies Qwen3-4B and uses 500 WebShop tasks; our evaluation uses 200."
- claim 5 | page | README How the search works step 2 | "It proposes one replacement and a rationale."

Anchors verified: 9 of 9 (python count >= 1 in `hookevorepo/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/hookevorepo.json` written; the pre-existing clone was only read; all anchor quotes verified in `hookevorepo/page.txt`).
