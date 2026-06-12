# Agents' Last Exam (ALE) — Deep-Dive Refinement

| Field | Value |
|-------|-------|
| Date | 2026-06-12 |
| Intake | intake-690 |
| Source | arXiv:2606.05405 · agents-last-exam.org · github.com/rdi-berkeley/agents-last-exam |
| Prior verdict | `not_applicable` (flagged as possible future agentic-eval corpus) |
| **Refined verdict** | **`not_applicable` HOLDS for the dataset/harness.** One narrow, non-dataset transfer is real: adopt the **occupational-taxonomy coverage frame** (O\*NET/SOC) as a Ch07 suite-construction lens. That is a methodology borrow, not a reason to soften the entry's runnability verdict. |
| License | Harness `ale_run/` Apache-2.0; data `tasks/` CC-BY-4.0 (license is a non-blocker for us regardless) |

## TL;DR / Refined recommendation

- **The benchmark IS released and runnable — but not on our substrate.** ALE ships `ale_run` (provisions sandboxes, executes agents, grades), 150 public reference tasks (of a 1,500+ corpus), and two reference agent harnesses. Grading is genuinely deterministic (executable Python graders, hidden references staged only after the agent finishes → leak-resistant, scores in [0,1]). On the two axes that usually kill an intake — *released?* and *verifiable?* — ALE passes.
- **It dies on the third axis: environment.** Tasks require provisioned **cloud VMs running a full Windows/Linux OS with real professional software**, driven by **CUA (computer-use) agents** that screenshot/click/type/scroll via an MCP GUI bridge. This is a GUI-grounded, OS-level, long-horizon agent benchmark — categorically outside our CPU-served `llama.cpp` + REPL/`CALL(...)` text harness. We cannot run ALE tasks against the local stack without standing up a CUA + VM-provisioning layer we do not have and do not plan to build.
- **The 2.6% / sub-1% hardest-tier pass rate does NOT change our autopilot difficulty or targets.** Those numbers measure frontier *computer-use* agents on OS-level workflows; they are not commensurate with our per-suite quality scores on closed-form Q&A. Reading them as a target would be a category error (the same trap memory flags elsewhere: confirm metric semantics before acting).
- **The one genuinely reusable idea is the taxonomy, decoupled from the data:** organizing a benchmark suite by an **occupational coverage map (O\*NET/SOC 2018 → industry clusters → subfields)** is a construction discipline Ch07 currently lacks. Ch07 indexes suites by *capability* (math/coder/agentic/…) and *source benchmark*; it has no notion of *occupational/domain coverage*. That is a worth-noting methodology transfer — but it is a Ch07 authoring lens, not a dataset adoption, so the intake verdict stays `not_applicable`.

## What it is

ALE ("Agents' Last Exam") is a **living agentic benchmark** of 1,000+ (paper) / 1,500+ (repo corpus) long-horizon, real-world professional tasks, co-developed with 250+ industry experts, organized around a task taxonomy of **55 subfields in 13 industry clusters**, with the cluster/subfield decomposition **defined by reference to O\*NET / SOC 2018** (the U.S. federal occupational taxonomy). It targets *non-physical* knowledge-work industries.

- **Public release**: 150 reference tasks (subset of the full corpus), `ale_run` toolkit, two reference agent harnesses, curated task tracks ("near-term / full-spectrum / last-exam" tiers, plus "unlicensed" and "Linux-only" tracks).
- **Task format**: executable `main.py` per task — instruction + input data + **hidden reference answer**; an executable Python grader emits a score in [0,1].
- **Headline finding**: the hardest tier is far from saturated — across mainstream harness × backbone configs, average full-pass rate is **below 1%** (the intake's "2.6% at hardest tier" is in the same regime; the repo/abstract phrase it as sub-1% on the very hardest stratum).
- **Execution substrate**: Google Cloud VMs running full Windows or Linux with actual professional software installed; **CUA agents** mixing CLI + GUI actions (screenshot/click/type/scroll) through an MCP bridge. Multi-turn agent loops on real machines, explicitly *not* simplified text environments.

## Stress-testing `not_applicable`

The user asked to stress-test the verdict rather than rubber-stamp it. Four questions:

### (a) Is ALE released/runnable, license, harness?

**Released and runnable — yes, materially more than the intake's "described only" framing implied.** The repo contains `ale_run` (sandbox provisioning + agent execution + grading), 150 public tasks, two reference harnesses, and an end-to-end documented run. License: Apache-2.0 harness, CC-BY-4.0 data (a non-issue for us per `feedback_license_not_a_blocker`). So the prior characterization ("flagged only as a possible future corpus, just described") **undersold release maturity** — this is a real, executable benchmark, not a paper artifact. *This is the one place the prior verdict's framing was wrong; the conclusion still holds for a different reason (substrate, not maturity).*

### (b) Verifiable outcomes (autopilot-feedable) or human/expert judging?

**Verifiable — and well-designed for it.** Executable Python graders, hidden references staged post-run (leak-resistant), [0,1] scores, "deterministic graders / verifiable outcomes." This is *exactly* the property our Ch07 design principle #1 demands ("every question machine-verifiable, no human judgment"), and it mirrors patterns we already adopted (SkillsBench intake-096 deterministic post-solution verifier; CoEvoSkills opaque-oracle-bit). **So ALE is NOT killed by the grading axis** — if anything its grading philosophy is aligned with ours. The kill is purely the execution environment (next question).

### (c) Is the O\*NET/SOC taxonomy itself reusable for OUR suite (Ch07), independent of the dataset?

**Yes — this is the single transferable nugget.** The idea: structure a benchmark portfolio by an **occupational/industry coverage map** (O\*NET/SOC 2018 → 13 clusters → 55 subfields) so the suite's coverage gaps are legible in *domain* terms, not just *capability* terms.

- Ch07 today indexes by **capability** (thinking/math/coder/vl/agentic/instruction_precision/long_context/…) and by **source benchmark** (MMLU, GSM8K, HumanEval…). There is no axis answering "which *occupational domains / industry workflows* does our suite cover or miss?"
- Ch06 maps suites to **orchestrator roles**, not to occupational domains either.
- An O\*NET/SOC-style coverage frame is **orthogonal** to both and cheap to apply: it is a Ch07 *authoring lens* (a checklist/coverage matrix), requiring **no ALE data, no license entanglement, no new infra**. It complements the existing tier-stratification and the dev/test_normal split discipline already in eval-tower notes.
- **Honest bound**: this is a *soft* methodology borrow. Our suites exist to differentiate models for *orchestrator roles* on CPU, not to certify occupational competence. The taxonomy is useful as a gap-finding overlay (e.g., "we have zero finance/legal/clinical-workflow representation; AA-Omniscience's 6 domains partially cover this"), not as a mandate to mirror all 55 subfields. Treat it as a Ch07 sidebar, not a restructuring.

### (d) Does the 2.6% / sub-1% finding change autopilot difficulty/targets?

**No.** Three reasons:

1. **Non-commensurable metric.** Sub-1% is *full-task pass* for *computer-use agents* on *OS-level multi-step workflows*. Our autopilot optimizes per-suite quality (0/1.5/3-quantized scores at ~2 q/suite) + tool_use sentinels on closed-form text tasks. There is no conversion between the two; importing "2.6%" as a difficulty target would repeat the exact category error memory warns against (confirm metric direction/semantics before acting; do not patch against the wrong baseline).
2. **Our difficulty knob is already principled.** Ch06/Ch07 set difficulty via T1/T2/T3 stratification and the Dec-2025 hardening (no model >90%, distribution spread). That is the right lever for *our* discriminative goal. ALE's saturation level is irrelevant to where we set T3.
3. **What it *does* (weakly) confirm**: long-horizon real-world agentic tasks remain unsaturated frontier-wide — i.e., there is headroom in *agentic* evaluation generally. That is consistent with our existing agentic/tool-use investments (tool-use-eval-contract, AppWorld defer, HALO) but adds no new action.

## Fit to EPYC (if any)

| Asset | Fit | Why |
|-------|-----|-----|
| ALE dataset (150/1500 tasks) | **No** | Requires Windows/Linux VM + GUI/CUA agent; our harness is CPU text REPL/`CALL(...)`. Not runnable without a CUA+provisioning layer we don't have/want. |
| `ale_run` harness | **No** | Built around cloud sandbox provisioning + MCP GUI bridge; nothing maps onto `eval_tower.py`. |
| Deterministic-grader pattern | **Already have it** | Our Ch07 principle #1 + SkillsBench/CoEvoSkills adoption already embody leak-resistant post-solution verification. No new transfer. |
| **O\*NET/SOC coverage frame** | **Weak-yes (methodology only)** | A Ch07 authoring overlay to make occupational/domain coverage legible. No data, no infra, no license cost. |
| Sub-1% saturation finding | **No** | Non-commensurable with our metrics; informational only. |

Net: nothing runs on EPYC; one authoring-lens idea is worth a Ch07 sidebar if/when someone is already editing suite-construction docs.

## Decision gates & next steps

- **Gate 1 — Does EPYC ever acquire a CUA / VM-provisioning eval substrate?** If NO (current state, and no plan to), the dataset/harness stay permanently `not_applicable`. Revisit ONLY if the eval scope explicitly expands to OS-level computer-use agents (it has not; AppWorld — a *simpler* multi-app simulator — was already deferred 2026-04-30 for the same "feasible but no current gap" reason; ALE is strictly heavier).
- **Gate 2 — Is anyone editing Ch07 suite-construction?** If a Ch07 revision is already in flight, add an O\*NET/SOC occupational-coverage sidebar (gap-matrix overlay). Do NOT open standalone work for this; it is a low-priority authoring nicety, not a backlog item.
- **No inference, no new suite, no dataset download** is warranted by this entry.
- **Do NOT** import ALE's sub-1% number into any autopilot target/difficulty setting.

## Risks

- **Scope-creep risk**: ALE's release maturity is seductive (real harness, real deterministic grading) and could tempt a "let's just run a slice" push. The blocker is structural (CUA+VM), not effort-bounded — a slice still needs the full substrate. Resist; this is the AppWorld lesson one tier harder.
- **Taxonomy over-application risk**: mirroring all 55 subfields would bloat the suite away from its role-differentiation purpose. Keep the O\*NET/SOC borrow as a *gap-finding overlay*, not a coverage mandate.
- **Metric-confusion risk**: the headline pass-rate is the kind of cross-context number that gets miscited as a target. Flagged explicitly above.
- **Living-benchmark drift**: ALE is explicitly "living" (grows as workflows onboard) — any future engagement would chase a moving target with no fixed split, weakening reproducibility for our purposes.

## Cross-refs

- **intake-104 (OneMillion-Bench)**, **intake-412 (DeepPlanning)**, **intake-001 / intake-096 (SkillsBench)** — adjacent agentic/skill-eval entries; SkillsBench's deterministic-verifier methodology is *already adopted* (`completed/07-skillsbench-eval-suite.md`) and is the closest precedent for "borrow the grading philosophy, not the suite."
- **intake-516 (AppWorld/HALO)** — the direct precedent: a long-horizon multi-tool agent benchmark **deferred** 2026-04-30 ("feasible hardware, no current eval gap"). ALE is heavier (OS+GUI vs app-simulator) → defer *a fortiori*. See `eval-tower-verification.md` 2026-04-30 update.
- **Ch06 / Ch07** (`epyc-inference-research/docs/chapters/06,07`) — suite framework + construction; the O\*NET/SOC coverage-frame sidebar would land in Ch07.
- **tool-use-eval-contract.md** — our agentic-eval surface; relevant only to note ALE's environment is far beyond our REPL `CALL(...)` contract.
- **CoEvoSkills (intake-628) / SkillsBench (intake-096)** — leak-resistant post-solution verification precedents that ALE's grader design echoes.
