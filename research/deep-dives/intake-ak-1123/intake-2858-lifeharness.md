# Dive — lifeharness — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/html/2605.22166v3", retrieved: "2026-11-23", sha256: "169a3030686d"} (the fetch resolves the latest version, v3 of 15 Oct 2026; v1 is from May 2026 per the arXiv id)
> SOURCE-QUARANTINE: {url: "https://raw.githubusercontent.com/Tianshi-Xu/Life-Harness/main/README.md", retrieved: "2026-11-23", sha256: "9c781071f9ca"} (README only; `gh api` metadata: MIT, 229 stars, last push 2026-10-13, 194 MB)

Bearing entry: intake-2836 (HookEvo). That dive said Life-Harness has "no entry of its own", is "the comparison anchor for every HookEvo delta" and asked whether HookEvo's baselines against it are fair and what Life-Harness's own retention and evaluation look like. HookEvo numbers used below are marked cross-source (from `hookevo/page.txt` and `hookevorepo`), never anchors.

## 1. Stage-1 fields

- **Title**: Adapting the Interface, Not the Model: Runtime Harness Adaptation for Deterministic LLM Agents (method name Life-Harness; the intake key "self-harness" in earlier entries refers to this paper).
- **Authors**: Tianshi Xu, Huifeng Wen (equal contribution), Meng Li (Peking University).
- **Version/date**: arXiv:2605.22166v3 [cs.AI], 15 Oct 2026, CC BY 4.0. Preprint. Code `Tianshi-Xu/Life-Harness` (README titled V2, MIT).
- **Categories**: autonomous_research, agent_architecture, tool_implementation, benchmark_methodology.
- **Novelty**: medium. Failure-driven evolution of a four-layer runtime harness (environment contract, procedural skill, action realisation, trajectory regulation) with evolution tokens reported as a first-class cost; the loop itself (propose, validate, paired-accept on a training batch) is the pattern HookEvo later inherits.
- **Relevance**: medium. Its layer taxonomy is a usable failure-annotation schema for the HIL loop, its cost accounting is the metric the harness cluster lacks, and it is the measuring stick for HookEvo.
- **Credibility**: 2 = peer-reviewed 0 (preprint) + within 12 months +1 (first posted May 2026, latest version Oct 2026) + major lab / known contributor 0 + independent corroboration +1 (HookEvo reran Life-Harness locally on the same executor and test-set sizes and got 87.77 / 64.11 / 41.33 / 36.81 against the published 88.07 / 65.00 / 45.50 / 39.60: ALFWorld and DBBench within 1 point, WebShop and OSBench 4.2 and 2.8 points lower; cross-source) + commercial bias 0.
- **Verdict**: adopt_patterns. Adopt the layer taxonomy as an annotation schema, the evolution-token metric and the cheap validity gate; do not adopt the headline margins over Meta-Harness and AHE (claim 1).

## 2. Key claims

**Claim 0 — the loop and its retention rule. CONFIRMED (section 4.4, Appendix A.2).** Each round runs the frozen solver on a batch of training tasks; an evolution LLM reads the trajectories and the current harness and edits mechanisms in the four layers. A candidate first passes interface checks and replay on training traces ("failed checks are returned to the evolution LLM for up to three repair attempts"); a valid candidate is then evaluated against the current harness on the same complete training batch with the benchmark's native scorer and "replaces the current harness only if accuracy improves" (the prompt says "accepts only a strict accuracy improvement"). Otherwise the current harness is kept and the next round uses a new training batch. The retained harness is frozen; "held-out test data are excluded from evolution". There is no validation split and no held-out check inside the loop; acceptance is the same in-sample paired test HookEvo later uses.

**Claim 1 — "exceeds Meta-Harness and AHE by 28.7 and 7.5 points with 8.5% and 68.4% fewer evolution tokens". PARTIAL (arithmetic reproduces; the comparison is weaker than stated).** From Table 1 the unweighted seven-environment Pass@1 means are Life-Harness 64.46 (88.1, 45.5, 39.6, 65.0, 60.0, 63.0, 90.0), Meta-Harness 35.73, AHE 56.94, giving 28.7 and 7.5. Summing the printed token costs (units of 10^7) gives 20.4 (Life), 22.2 (Meta-Harness), 64.4 (AHE), so 8.1% and 68.3% fewer by my sum, within rounding of the stated 8.5% and 68.4%. Qualifications. (a) The baselines were run by the Life-Harness authors for six rounds each "using identical training batches of up to 50 tasks", with "each method's selection rules" retained and, in the README's words, "six rounds do not imply equal token consumption". (b) AHE beats Life-Harness on ALFWorld (89.0 vs 88.1) and Telecom (95.0 vs 90.0). (c) The authors' Meta-Harness reruns fall below the unharnessed solver on Airline (11.7 vs 35.0) and Retail (33.3 vs 48.0), which suggests under-tuned baselines. (d) The tau-bench and tau2-bench test sets are 20, 40 and 40 tasks (Table 5), so per-cell margins there are noise-level; AgentBench cells are single runs ("we evaluate each task once").

**Claim 2 — evaluation protocol and training pool. CONFIRMED (Table 5, Table 6, section 5.1).** Evolution uses a pool of only 100 training tasks per AgentBench environment (ALFWorld raw pool 3,150, DBBench 4,803, OS 1,000, WebShop 9,000), each round a batch of up to 50; test sets are 109 ALFWorld, 300 DBBench, 144 OS, 200 WebShop; temperature 0.0 throughout; solver Qwen3-4B-Instruct, evolution LLM GPT-5.5; the selected harness is frozen and re-used on 17 further open-weight backbones. Optimisation cost is of order 1-4 x 10^7 tokens per environment (Table 1).

**Claim 3 — are HookEvo's baselines against Life-Harness fair? PARTIAL: fair at the test side, unmatched at the search side (cross-source reading).** Test side: HookEvo's Table 1 uses the same test-set sizes as Life-Harness's Table 5 (109, 300, 200, 144), the same frozen Qwen3-4B-Instruct executor and its own three-execution local rerun, so the rerun comparison is like-for-like at evaluation. Search side: Life-Harness evolved for 6 rounds on a 100-task pool with GPT-5.5; HookEvo evolved for 40 rounds (80 on WebShop) with 300 distinct training tasks on ALFWorld and DBBench, and with the GPT-6.1 Sol improver at high effort. HookEvo's own ablation shows that weaker improvers under its best scope reach ALFWorld 48.62 (Luna) and 52.91 (Terra), far below Life-Harness's published 88.07, so the framework alone does not beat Life-Harness; the improver and the round budget carry the gain. HookEvo's text calls its baseline "a same-executor Life-Harness rerun"; whether that re-evaluated the released harness or re-evolved Life-Harness at HookEvo's budget is NOT-FOUND-IN-SOURCE. Against the published Life-Harness numbers HookEvo's headline margins are +7.34 (ALFWorld), +5.56 (DBBench), +2.67 (WebShop), +2.07 (OSBench) (arithmetic on cross-source numbers), and the last two sit inside the roughly +/-7 point single-comparison noise of 200 and 144 test tasks. The Life-Harness repository now ships an evolve-from-scratch runner for Life-Harness, Meta-Harness and AHE (`python -m evolution.reproduce --suite agentbench --method all`), so a matched-budget rerun is possible.

**Claim 4 — transfers to frontier models (+2.8, +4.4, +3.4 points; 18 of 21 settings). PARTIAL.** Table 2 supports the averages as stated, but each cell is one run of 20-300 tasks with temperature 0; several cells move by under 1 point or fall (Gemini 3.1 Pro on OS 50.0 to 48.6, ALFWorld unchanged at 96.3). The finding that a harness helps strong models less than weak ones is consistent with a ceiling effect, not a new mechanism.

**Claim 5 — layer importance is environment-specific. CONFIRMED (Table 4).** Leave-one-layer-out relative drops range from -1.0% to -86.5%: removing the action-realisation layer costs -61.7% on Airline and -59.6% on OS but -1.0% on ALFWorld; removing trajectory regulation costs -86.5% on ALFWorld. There is no universally dominant layer, and each cell is a single run.

## 3. Reported results (as the source states them)

- Table 1 (Qwen3-4B-Instruct, Acc %, Cost = evolution tokens in 10^7; columns without harness / Meta-Harness / AHE / Life-Harness): ALFWorld Pass@1 16.5, 35.8 (3.7), 89.0 (9.6), 88.1 (2.4); WebShop 29.5, 42.5 (3.7), 39.0 (10.4), 45.5 (3.8); OS 21.5, 25.7 (2.7), 37.5 (9.4), 39.6 (2.6); DBBench 44.0, 50.3 (3.3), 57.3 (10.5), 65.0 (1.1); Airline 35.0, 11.7 (5.3), 35.0 (6.4), 60.0 (3.6) with Pass^3 5.0, 0.0, 20.0, 50.0; Retail 48.0, 33.3 (1.4), 45.8 (9.3), 63.0 (2.6); Telecom 25.8, 50.8 (2.1), 95.0 (8.8), 90.0 (4.3). Means: AgentBench Pass@1 27.9, 38.6, 55.7, 59.5; tau suites 36.3, 31.9, 58.6, 71.0.
- Frontier models (Table 2, without / with): GPT 5.5 ALFWorld 93.6 / 95.4, DBBench 67.7 / 75.0; Opus 4.8 WebShop 73.8 / 82.7, Retail 72.5 / 84.2; Gemini 3.1 Pro OS 50.0 / 48.6. AppWorld mean over 18 backbones 25.50 to 30.76, improved on 16 of 18; improvements in 116 of 126 model-environment settings.
- Setup: temperature 0.0; tau benchmarks use DeepSeek-V4-Flash as user simulator and report single-run and Pass^3 over three runs; AgentBench one run per task; solver Qwen3-4B-Instruct, evolution LLM GPT-5.5; six rounds for all three compared methods.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC 9655 |
|---|---|---|
| Frozen solver plus runtime interface layers (contract, skill, action realisation, trajectory regulation) | YES. All four layers run on the host in the agent process; the MI210 only serves the solver. | YES (host-side logic). |
| Validity gate by replay on stored training traces with up to three repair attempts | YES. Zero model inference for the replay; repair attempts are improver calls. | YES. |
| Paired accept on the training batch (same tasks, strict improvement) | YES for a small solver served on the MI210; cost is solver episodes per round. | YES; bandwidth-bound decode for a CPU-hosted solver. |
| Top-1 retrieved skill at task start | YES; text injection, no kernel dependence. | YES. |
| Evolution LLM as an external frontier model, tokens as the cost unit | n/a | n/a; tokens come from our Claude/Codex roster, not local silicon. |

## 5. In-house state

- HIL (harness-improvement-loop) track in `harness-program.md:L1719 @ d785b6d`: HIL-6 (operator-selected architecture) is undecided; HIL-6j lifts the 2026-09-16 "no loop run" deferment for the HIL-6 pilot only, every other loop stays deferred (operator decision 2026-10-22). DPF-1132-L2 (L1981) records AHE evolving and scoring on the same tasks; DPF-1132-L7 records that nothing shows a small local evolver working.
- AutoPilot is intentionally stopped (checkpoint 2026-09-25); BEP-5 (autopilot-program.md:L2214 @ d785b6d) generalises Meta-Harness Tier-2's sandbox-before-disk and granular accept/reject; BSV-2 (L123) carries paired behavioural comparison.
- Existing intake context: `research/intake_index.yaml` entry intake-1323 (Harness-R1) lists arXiv 2605.22166 among its references and reads a vendored `code/life-harness/AgentBench` tree; no entry exists for the Life-Harness paper or `github.com/Tianshi-Xu/Life-Harness` (0 hits for the URL).
- No multi-turn environment suite in the lane (see the agentrl dive); the Life-Harness AgentBench environments run on AgentRL's controller (README: "AgentRL controller and native workers").
- Upstream-present check: n/a.

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane file, status) | Compute | Stop/decision rule and question |
|---|---|---|---|---|
| LH1 | Record Life-Harness's four-layer taxonomy as the failure-annotation schema for HIL traces (environment contract, procedural skill, action realisation, trajectory regulation), map our existing hooks and checks to the layers, and require the HIL pilot to ablate by layer because Table 4 shows no universally dominant layer. | `harness-program.md` (harness-improvement-loop track; HIL-2 checklist append pattern) | doc-only | Done when the checklist names the four layers and a leave-one-layer-out arm; question recorded: do our observed failures concentrate in one layer? |
| LH2 | Make "evolution tokens per accepted gain" a recorded field of every HIL (and, if relaunched, AutoPilot) round, using improver-session token counts, mirroring Life-Harness's Table 1 cost column; refines intake-2836 H1/HR1. | `harness-program.md` (HIL track) with a cross-reference in `autopilot-program.md` (stopped, design only) | code/doc-only | Question: what does one accepted mutation cost in improver tokens on our harness? Done when the round record carries the field; futility if the improver CLI does not expose token usage (then record that gap). |
| LH3 | Add a zero-inference validity gate before any paired evaluation: replay each candidate on recorded training traces and allow up to three repair attempts, as in section 4.4. Refines BEP-5 and intake-2836 HR3. | `autopilot-program.md:L2214` (BEP-5) and `harness-program.md` (HIL-2 checklist) | doc-only now; code later | Decision recorded: validity-by-replay precedes any paid evaluation. Done when BEP-5's text names the replay gate and the repair limit. |
| LH4 | Run the Life-Harness evolve-from-scratch runner with a LOCAL evolution model (a served 27B or Flash-Next) and a small local solver on ALFWorld for 6 rounds, on the AgentRL controller from agentrl G2, and compare against bare 16.5 and the published 88.1. Answers DPF-1132-L7. | `harness-program.md` (HIL track). The 2026-10-22 operator decision permits loop runs only for the HIL-6 pilot, so this row needs one operator choice (extend the pilot allowance) and is conditional on agentrl G2 and hookevorepo HR4; that choice blocks only this row. | GPU/CPU inference rows in a quiet window | Question: can a local improver evolve any measurable harness gain in 6 rounds? Stop on answer after round 6 with adoption count and test success recorded; stop on futility if no candidate is adopted in the first 3 rounds. |
| LH5 | DECLINE: reproduce the 18-backbone, 126-cell Table 10. Reason specific to this entry: most cells are tau-bench and AppWorld tasks with 20-57 test tasks and models we do not serve, so per-cell results are noise-level for any decision of ours; LH4 tests the one question that matters (local improver on a served solver). | n/a | n/a | n/a |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml`)

- `github.com/Tianshi-Xu/Life-Harness` (0 hits): README read; it ships the evolve-from-scratch and comparison runner that LH4 needs. Recommend ingest as the companion artifact of this entry (README read here, runner source not read); it changes LH4 only through what the runner supports.
- arXiv:2604.25850 AHE, Meta-Harness, ALIGN, AgentSquare: AHE and Meta-Harness are already in the index (per intake-2836); ALIGN and AgentSquare are baselines evaluated only on ALFWorld and WebShop. Decline ALIGN and AgentSquare: no ledger row of this run depends on them.
- arXiv:2606.14249 HarnessX and arXiv:2608.02276 Harness-R1: already in the index (intake-1323 covers Harness-R1).

## 8. Contradiction / adversarial pass

- Baselines (Meta-Harness, AHE) are the authors' own six-round reruns under "each method's selection rules"; Meta-Harness falls below the unharnessed solver on two tau tasks; token budgets are not equalised (README caveat).
- Single-run AgentBench cells, 20-40-task tau test sets, no seeds or intervals; frontier-model gains of 0-4 points are within single-cell noise.
- Acceptance is in-sample on the evolution batch; the held-out set is touched only after evolution, which is the right protocol, but one 100-task pool per environment makes the harness environment-specific (the paper's own framing).
- HookEvo reports a local Life-Harness rerun 0.3-4.2 points below the published numbers (cross-source), so the published figures are not exactly reproduced by a third party on the same executor.
- Authors' stated limitation: text and API-based environments only, no visual GUI tasks. No independent replication of the Meta-Harness/AHE comparison was found.
- The paper's AI-assistant statement (Appendix C) was not used for any claim.

## 9. Read depth

read_depth: FULL for sections 1-6, Appendix A.1-A.2 prompts, Appendix B (Tables 5, 6, 10 header and first rows); PARTIAL for A.3 per-layer harness inventory tables and Tables 10-13 beyond the first rows; README read, repo source not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## Anchors (verbatim substrings of page.txt, verified)

- claim 0 | page | Section 4.4 | "It replaces the current harness only if accuracy improves."
- claim 0 | page | Section 4.4 | "failed checks are returned to the evolution LLM for up to three repair attempts"
- claim 0 | page | Section 5.1 Models | "Held-out test data are excluded from evolution."
- claim 0 | page | Appendix A.2 evolution prompt | "The host evaluates the candidate and current harness on the same complete training batch and accepts only a strict accuracy improvement."
- claim 1 | page | Section 5.2 Accuracy and Evolution Efficiency | "exceeds Meta-Harness and AHE by 28.7 and 7.5 percentage points in mean accuracy, respectively"
- claim 1 | page | Section 5.1 Baselines | "Three methods undergo six evolution rounds using identical training batches of up to 50 tasks per round."
- claim 1 | page | Section 5.2 | "AHE performs better on ALFWorld and Telecom"
- claim 1 | page | Table 1 (Airline row) | "Airline Pass@1 35.0 11.7 5.3 35.0 6.4 60.0 3.6"
- claim 1 | page | Table 1 (Retail row) | "Retail Pass@1 48.0 33.3 1.4 45.8 9.3 63.0 2.6"
- claim 2 | page | Section 5.1 Evaluation Parameters | "For AgentBench, we evaluate each task once, following the official implementation."
- claim 2 | page | Appendix A.3 Table 5 | "ALFWorld 3,150 100 109 3,259 DBBench 4,803 100 300 5,103 OS Interaction 1,000 100 144 1,144 WebShop 9,000 100 200 9,200"
- claim 3 | page | Appendix A.3 Table 5 (test-set sizes used for the like-for-like comparison) | "ALFWorld 3,150 100 109 3,259 DBBench 4,803 100 300 5,103 OS Interaction 1,000 100 144 1,144 WebShop 9,000 100 200 9,200"
- claim 4 | page | Section 5.2 Transfer to Frontier Models | "Life-Harness improves accuracy by 2.8, 4.4, and 3.4 pp, respectively, with gains in 18 of 21 model–environment settings."
- claim 5 | page | Table 4 (action row) | "w/o Action -61.7% -15.9% -10.1% -1.0% -6.6% -59.6% -4.6%"
- claim 5 | page | Table 4 (trajectory row) | "w/o Trajectory -3.3% -16.7% -36.2% -86.5%"

Anchors verified: 15 of 15 (python count >= 1 in `lifeharness/page.txt`).

## 10. Artifact audit

artifact audit: clean (only this file and `drafts/lifeharness.json` written; all anchor quotes verified in `lifeharness/page.txt`).
