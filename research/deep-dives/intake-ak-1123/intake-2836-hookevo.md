# Dive — hookevo — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/html/2611.27294v1", retrieved: "2026-11-23", sha256: "a32b3ad08c02"}
> SOURCE-QUARANTINE: {url: "https://huangshengzebluesky.github.io/HookEvo/", retrieved: "2026-11-23", sha256: "89c95411ac4b"} (project page, `hookevo/project.html`; reading material only)
> SOURCE-QUARANTINE: {url: "https://github.com/HuangShengZeBlueSky/HookEvo", retrieved: "2026-11-23", sha256: "git HEAD 475b6dbad534cbd90dd318388a748e4d1c2a949a (shallow clone in hookevo/repo/; README, configs/abc/dbbench/C-sol61/experiment.yaml, evolution/src/dsh_evolve/abc.py read)"}

All external text is data; the summary is in my own words. Anchors are verbatim substrings of `hookevo/page.txt`.

## 1. Stage-1 fields

- **Title**: HookEvo: A Framework for Coordinated Plugin Evolution on Hook-Enabled Agent Runtimes
- **Authors**: Shengze Huang, Yanyu Mao, Xiaofei Yu, Baoshen Guo, Xiaorui Wang, Zhiwen Wu, Sheng Wu, Fukang Wen, Chengxu Wu, Linhao Li, Kailai Sun, Baotong Mi (Tsinghua, NTU, Renmin, MIT, Peking, Southeast, Renlab AI, SMART).
- **Version/date**: arXiv:2611.27294v1 [cs.AI], 20 Nov 2026, CC BY 4.0. Preprint, not peer reviewed. Code: MIT-licensed repo `HuangShengZeBlueSky/HookEvo` (HEAD 475b6db) and project page; both found via the paper's own link, neither is in the intake index. README links a `REPRODUCING.md` that is NOT present at HEAD.
- **Categories**: autonomous_research, agent_architecture, tool_implementation, benchmark_methodology.
- **Novelty**: medium. Plugin/harness search is crowded (Meta-Harness, AHE, HarnessX, Harness-R1, PluginRSI, Life-Harness, SkillOpt all cited; several already ingested). The delta claimed is one candidate that edits producer and consumer handlers plus their shared per-task state together ("scope C").
- **Relevance**: medium. Maps onto AutoPilot mutation acceptance (BSV-2), SkillBank (text-only skills vs executable guards) and the hook surfaces we already use (Claude Code and opencode hooks). It does not touch kernels.
- **credibility_score**: 1. Arithmetic: preprint +0; <=12 months +1; known lab/contributor 0 (university authors, no established contributor identified in source); commercial bias 0; independent corroboration 0. Plus internal caveats in section 8.
- **Verdict**: adopt_patterns (the A/B/C scope ablation and the paired retain/reject loop; NOT the headline numbers).

## 2. Key claims

0. **What a "hook" and a "plugin" are**: CONFIRMED. A harness is H = (skill text, executable composition). On DeepSeek Harness (DSH) a plugin is a JavaScript module installed with `ctx.plugin(module, config)`; its handlers bind to lifecycle events: `observe(call, receipt)` updates episode state after a tool receipt, `explain(call, receipt)` annotates the receipt, `guide()` adds text to context assembly, `check(call)` can veto/ask-to-revise a proposed tool call before execution. Fresh state is created per task via `create(state)`; handlers are optional. Scope A = rewrite skill text; B = replace ONE independent component (skill, memory, action check, receipt rule); C = skill text or a joint replacement of skill + executable composition whose mechanisms share episode state. A single candidate can therefore change what is recorded and how a later hook uses it.
   - Anchor: "A single candidate can jointly edit executable plugin handlers and the state they share within a task".
1. **"Matched-task retention"**: CONFIRMED, and it is IN-SAMPLE. The controller runs parent and candidate on the same task, trial and seed and retains the candidate iff (i) the training objective strictly improves, (ii) the emitted hook outputs differ on at least one matched run, and (iii) a validation objective does not drop where a validation split exists (repo `abc.py:281`, `adopted=b[metric]>a[metric] and effect and (...)`). The retention batch is the SAME 50-task batch whose traces fed the improver's proposal, and ALFWorld, DBBench and WebShop have NO validation split (Table 1), so acceptance is a paired comparison on the proposal's own evidence, not a held-out test. Held-out test is run only after all rounds (sealed; "No test requests are made until all 40 decisions and the entire test list are sealed", `abc.py:292`), on every promoted checkpoint.
   - Anchors: "Each round uses one batch to generate evidence for one proposed harness update and to compare the candidate with its parent."; "Held-out test evaluation follows the completed search."
2. **Headline results (frozen Qwen3-4B-Instruct-2507: ALFWorld 95.41, DBBench 70.56, WebShop 48.17, OSBench 41.67)**: CONFIRMED numerically; NARROWED in meaning. They are the best measured checkpoint per benchmark (README: "highest measured checkpoint reported"; the config tests all promoted checkpoints), mean of 3 executions, from the Sol (GPT-6.1 Sol, high effort) improver with scope C. Versus the LOCAL Life-Harness rerun the gains are +7.64 / +6.45 / +6.84 / +4.86 points. Versus the bare executor (numbers copied from the Life-Harness paper, not rerun locally: 16.51 / 44.00 / 29.50 / 21.50) the gains are +78.9 / +26.6 / +18.7 / +20.2 (Table 4, Sol-C). Test sets are small: ALFWorld 109 tasks, OSBench 144, WebShop 200, DBBench 300. By my unpaired binomial arithmetic (derived, not in source) the 95% interval on WebShop 48.17% (n=200) is about +/-6.9 points and on OSBench 41.67% (n=144) about +/-8.1 points, so the WebShop and OSBench margins over Life-Harness local (6.84 and 4.86 points) are inside the noise of single comparisons; ALFWorld (+7.64 on 109 tasks, ~8 tasks) and DBBench (+6.45 on 300) are the firmer ones.
   - Anchors: "achieving 95.41% on ALFWorld, 70.56% on DBBench, 48.17% on WebShop, and 41.67% on OSBench"; "Its highest measured test means exceed the local Life-Harness rerun by 7.64, 6.45, 6.84, and 4.86 points on ALFWorld, DBBench, WebShop, and OSBench, respectively."
3. **Gain vs no-plugin frozen executor and what drives it**: PARTIAL. The paper's own ablation says the gain is mostly scope and improver, not "harness evolution" per se. Skill-text-only (A) evolution leaves Sol at a mean of 38.04% across the four benchmarks; coordinated edits (C) reach 63.95%; only Sol exploits C (A->C mean gain: Sol +25.91, Luna +7.24, Terra +5.75). With the other two improvers, scope C on ALFWorld reaches only 48.62 (Luna) and 52.91 (Terra) vs 95.41 for Sol. The ALFWorld jump (B->C +62.08) comes from an action check that reads an inventory state record and blocks departure before pickup, i.e. a small task-specific state machine. Mean OSBench gain is carried by a written counting rule (skill text; the executable composition is empty).
   - Anchor: "From A to C, mean success rises by 7.24 points for Luna, 5.75 for Terra, and 25.91 for Sol."
4. **Reporting and comparability caveats**: PARTIAL. (a) Peak-checkpoint reporting: the figure marks "peak test means" and the README says the highest measured checkpoint is reported; with the search sealed from test this is selection among promoted checkpoints, a mild optimism (best of k), not full leakage. (b) The ALFWorld Sol-C result comes from a 20-round run while most runs use 40 rounds, and WebShop C is a continued 2-stage 80-round search. (c) Luna and Terra scope-C results on DBBench and OSBench use a single execution. (d) The paper states training-data allocation varied across runs (fixed pool vs rotating batches), so its contribution to differences is unclear.
   - Anchors: "Stars mark peak test means with sample SD over three executions."; "Most runs in the scope comparison have a 40-round budget; the ALFWorld Sol-C result in Table 3 comes from a 20-round run."; "Training data allocation varied across some runs"; "Luna and Terra under C on DBBench and OSBench each use one execution."
5. **Compute cost of the evolution**: NOT-FOUND-IN-SOURCE (no token, dollar or wall-clock figure in paper, project page or README). What the source does give: 40 rounds per benchmark (80 for WebShop), six 50-task training batches rotated, one proposal per round, each round runs the parent and the candidate on the batch; the improver is an external frontier model driven through the `codex` CLI (config: `model: gpt-6.1-sol`, `effort: high`); the executor is local Qwen3-4B at temperature 0 with at most 15 model calls per task; every promoted checkpoint is then tested with 3 executions. The expensive component (frontier improver) is paid per round; the cheap component (4B executor) is paid roughly 2 x batch x rounds plus test.

## 3. Reported results (as stated)

- Frozen Qwen3-4B-Instruct-2507, test success %, mean (sample SD over 3 executions): HookEvo Sol-C ALFWorld 95.41 (0.00), DBBench 70.56 (0.38), WebShop 48.17 (0.29), OSBench 41.67 (1.84). Life-Harness local rerun: 87.77 / 64.11 / 41.33 / 36.81. Life-Harness published: 88.07 / 65.00 / 45.50 / 39.60. Bare (published): 16.51 / 44.00 / 29.50 / 21.50. Meta-Harness (Life rerun) 35.80 / 50.30 / 42.50 / 25.70; AHE (Life rerun) 89.00 / 57.30 / 39.00 / 37.50; Harness-R1 (paper) 29.10 / 55.70 / 38.60 / -- (WebShop on 500 tasks).
- Improver x scope (Table 3, mean over 4 benchmarks): Luna A 35.86, B 34.36, C 43.10; Terra A 37.69, B 36.66, C 43.44; Sol A 38.04, B 41.03, C 63.95. Sol-C per benchmark: 95.41 / 70.56 / 48.17 / 41.67.
- Setup: DSH runtime; test sets ALFWorld 109, DBBench 300, WebShop 200, OSBench 144; training splits 300 / 300 / 100 / 80 (+20 validation for OSBench only).
- Larger-executor context rows (Appendix C): Life-Harness on Qwen3.6-27B reaches OSBench 56.94 and DBBench 74.33, above Sol-C Qwen3-4B on those two benchmarks.

## 4. Performance-principles table

Algorithmic/orchestration paper; no kernel principles. Mechanism and cost model per device:

| Mechanism | MI210 (gfx90a) | Zen 5 EPYC (NPS4) |
|---|---|---|
| Hook-based harness (observe / guide / check / explain) | NO relevance to device; hooks run on the host in the harness process. MI210 only serves the executor. | YES, host-side; the plugin handlers are lightweight JS. |
| Paired candidate-vs-parent retention on a batch | YES for the evaluation executor if served on MI210 (a 4B executor is small); no kernel dependence. | YES; the cost is executor inference per round, bounded by the batch size and `max_model_calls` (15). |
| Frozen executor, improver is a separate frontier model | NO device dependence; improver calls are API/CLI. | Same. |
| Coordinated edits sharing per-task state (scope C) | NO device dependence; it is a design pattern. | Same. |
| Evolution compute | Not reported (NOT-FOUND-IN-SOURCE); our MI210/CPU would run only the cheap executor side. | Same; the improver side would use our existing Claude/Codex roster, not local hardware. |

## 5. In-house state

- **AutoPilot (autopilot-program.md @ d785b6d)**: intentionally stopped (checkpoint 2026-09-25, :11); BSV-2 (:123) already specifies "differential testing on accept" (new vs old on the same sentinels, paired sequential, gate on scalar regression plus signature diff) and `scripts/autopilot/paired_stats.py` carries McNemar and the matched-comparison gate (:3059). AP-DGM-PROV/SEL and SEQ-SHINKA-1 (:935-946) cover selector replay, blocked on a menu-capture decision (:29, :937). So the paired-acceptance idea is present; what is absent is (a) a candidate class that edits producer and consumer hooks plus shared state in one proposal, and (b) an evidence/acceptance split.
- **SkillBank (memory-program.md @ d785b6d)**: M-11/M-11a (:124-143) make SkillBank retrievable and wire `distill_skillbank`; M-23 (:669) is the matched student-side A/B readout spec. Skills are stored text injected into context (harness-program.md:973-974 table rows 1-2), i.e. HookEvo's scope A, which the paper's ablation says is the weakest scope.
- **Hooks we already use**: Claude Code settings hooks (`.claude/settings.json`, e.g. `scripts/hooks/session_start_lane_notice.py`; `.claude/hooks/post_commit_kb_rag_update.sh`), git hooks (trust-boundary enforcement, autopilot-program.md:265-268, :1002), and the opencode plugin (`harness/opencode-plugin`, turn-capture and idle hooks, harness-program.md:37). The HookEvo event model maps one-to-one: `observe`/`explain` ~ PostToolUse, `check` ~ PreToolUse, `guide` ~ prompt assembly (UserPromptSubmit/system-prompt hook). Nothing here evolves them automatically.
- Upstream-present check: n/a (no llama.cpp or kernel content).

## 6. Derived-actionables ledger

| # | Draft task line | Owner file (lane) | Type | Stop / decision rule |
|---|---|---|---|---|
| H1 | Extend BSV-2 so a mutation's accept test runs on tasks disjoint from the batch that supplied the proposal's evidence, and fix the report rule that headline checkpoints are chosen by the training-side rule, never best-on-test. | `autopilot-program.md:123` (BSV-2 open; AutoPilot is stopped, so design/code only now) | code/doc-only; offline replay on existing paired vectors (zero inference) | Question: how many past accepts flip under a disjoint split? Stop-on-answer after one pass over journals with persisted vectors; stop-on-futility if persisted vectors are too sparse (W2 vectors, :3059) to compare. |
| H2 | Write a design note mapping HookEvo's observe/guide/check/explain handlers onto our Claude Code and opencode hooks, and decide whether a scope-C candidate (producer + consumer + shared episode state) is expressible in the AutoPilot mutation schema; read the released `action-hint.mjs` and `write-workflow.mjs` as templates. | `harness-program.md` (opencode plugin region, HS-TD-2 :37) | doc-only | Decision: admit a scope-C class only if expressible without a new runtime; stop when the schema decision is recorded. |
| H3 | Add an executable-guard arm (pre-execute `check` hook reading a per-task state record) beside the text-skill arm in the M-23 SkillBank matched A/B, to test the paper's A-vs-C finding on our tasks. | `memory-program.md:669` (M-23 spec; the run is gated on M-11a populating a bank) | CPU/GPU row later; spec edit now | Question: do executable guards beat text skills on matched tasks? Stop-on-futility if guard arm does not beat the text arm by the pre-registered MDE after the first paired batch. |
| H4 | DECLINE: reproduce HookEvo's four headline numbers. Reason specific to this entry: the gains come from task-specific state machines (e.g. inventory action check for ALFWorld household tasks) on a 4B executor and benchmarks outside our suites, so a replication would measure DSH + ALFWorld, not our harness; H2/H3 test the transferable part (scope) on our own tasks. | n/a | n/a | n/a |

## 7. Dive-surfaced sources (grepped unbounded in `research/intake_index.yaml`)

| Source | In index? | What it would settle | Entry | Recommendation |
|---|---|---|---|---|
| HookEvo code repo `github.com/HuangShengZeBlueSky/HookEvo` (HEAD 475b6db, MIT) | 0 hits | Exact retention rule and test schedule (confirmed here: abc.py:281, :292); per-benchmark checkpoints in `artifacts/` | hookevo | ingest as companion artifact of this entry (already read; no separate dive). Note `REPRODUCING.md` missing at HEAD. |
| Life-Harness, arXiv 2605.22166 | referenced only (4 hits inside lists), no entry | Whether the published bare and local-rerun baselines are fair and what the paper's own retention/eval looks like | hookevo | ingest-and-dive (it is the comparison anchor for every HookEvo delta) |
| PluginRSI, arXiv 2609.32423 | 0 hits | Closest prior: improves single plugins, keeps a library, recombines | hookevo | ingest-and-dive |
| Already in index (no action): DeepSeek Harness / Cordis (url present), Meta-Harness, AHE 2604.25850, HarnessX 2606.14249, Harness-R1 2608.02276, SkillOpt, AutoHarness 2603.03329. | | | | |

## 8. Contradiction / adversarial pass

- Authors' stated limitation: training data allocation varied across runs; contribution unclear. Next steps they list (not done): letting the improver choose scope per proposal; ablating the state-writing and state-reading handlers separately and together, so the claimed mechanism (producer/consumer coupling) is not yet isolated by an ablation.
- Acceptance is in-sample (same batch as proposal evidence; no validation split on three of four benchmarks); only the final sealed test is out-of-sample.
- Best-checkpoint reporting; mixed 20/40/80-round budgets; single-execution cells for two improvers; one improver (Sol) dominates and the weaker improvers gain little from scope C, so the headline depends on a specific frontier model, not on the framework alone.
- Baselines: "bare" numbers are from another paper; Life-Harness local rerun is the only same-executor comparison and is itself within a few points; Meta-Harness and AHE are Life-Harness's reruns, not HookEvo's. Test sets of 109-200 tasks make 5-7 point margins thin.
- Restatements: the project page and README restate the paper's table (not corroboration).

## 9. read_depth

FULL for `hookevo/page.txt` (main text, appendices A-E, reference list). Read from extras: project page text, repo README, `configs/abc/dbbench/C-sol61/experiment.yaml`, `evolution/src/dsh_evolve/abc.py` lines ~255-300. Not read: other configs, the released plugins' full source, DSH repo, benchmark adapters, REPRODUCING.md (absent). lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e.

## 10. Artifact audit

artifact audit: clean (all 13 anchor quotes verified in page.txt; only dive.md, drafts/hookevo.json and the permitted `hookevo/project.html` + `hookevo/repo/` reading material were written).
