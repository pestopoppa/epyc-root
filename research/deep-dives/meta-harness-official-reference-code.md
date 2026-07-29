# Deep Dive: Meta-Harness — Official Reference Code (stanford-iris-lab/meta-harness)

**Date**: 2026-04-24
**Intake**: intake-451 (github.com/stanford-iris-lab/meta-harness)
**Paper**: intake-244 (arxiv:2603.28052 — Lee, Nair, Zhang, Lee, Khattab, Finn)
**Question**: Now that the official companion code is public, does our re-derived Tier-1/Tier-2 implementation still reflect the paper's intent, and what does the actual code expose that the paper underspecified?

## Executive Summary

**Adopt patterns, not components.** The repo is exactly what the authors say on the tin — "a cleaned up version of the code we used for the paper… not tested beyond verifying that it runs." It is a **reference implementation, not a framework**: two self-contained example directories (`text_classification/`, `terminal_bench_2/`), each with its own `meta_harness.py` outer loop, `claude_wrapper.py`, and `.claude/skills/…/SKILL.md` proposer prior. There is no shared framework package to import.

The useful material is qualitative: (a) the `ONBOARDING.md` conversation flow + `domain_spec.md` template for onboarding a new optimization domain, (b) the `SKILL.md` proposer-prior template that replaces our ad-hoc code-mutation system prompt, (c) the filesystem layout — `evolution_summary.jsonl` + `frontier_val.json` + `agents/<name>.py` + `pending_eval.json` — which is concrete enough to port, (d) the decision to **not select parents algorithmically** and instead give the proposer read access to the full frontier and let it choose. That last one is genuinely different from our current PromptForge, which picks a parent via strategy-store retrieval before the mutation call.

The "tbench2-artifact" repo is a sibling — the final 76.4% scaffold as a product, extending Terminus-KIRA. It is not a search log. Its one portable insight is **environment bootstrapping**: inject a one-shot workspace snapshot into the initial prompt so the agent does not burn turns on orientation — directly relevant to `repl-turn-efficiency.md` S5 Gap-1 (`workspace_scan`).

**Refined verdict**: `adopt_patterns`, not `adopt_component`. The "cleaned up but not tested" caveat is load-bearing — there is no shared package to pip-install, each reference example is a separate tree, and copying either wholesale means owning the upstream bugs. Novelty stays low (design already captured in intake-244), relevance stays high (concrete code for directly open questions in three active handoffs).

## Technique Analysis

### Repo structure

```
meta-harness/
├── ONBOARDING.md                    ← conversation template for new domains
├── README.md                        ← quickstart + caveat
├── assets/                          ← figures only
└── reference_examples/
    ├── text_classification/         ← memory-system search
    │   ├── meta_harness.py          ← sequential outer loop
    │   ├── inner_loop.py            ← per-candidate eval
    │   ├── benchmark.py             ← sweep/orchestration layer
    │   ├── memory_system.py         ← the artifact under search
    │   ├── llm.py
    │   ├── claude_wrapper.py
    │   ├── config.yaml              ← datasets, models, active memory systems
    │   ├── agents/                  ← baselines + generated candidates live here
    │   └── .claude/skills/meta-harness/SKILL.md   ← proposer prior
    └── terminal_bench_2/            ← scaffold evolution
        ├── meta_harness.py          ← same loop shape, TB2-specific
        ├── claude_wrapper.py
        ├── agents/
        │   └── baseline_kira.py     ← ~900 LoC, AgentHarness(Terminus2)
        ├── prompt-templates/
        │   └── terminus-kira.txt
        ├── scripts/run_eval.sh      ← invokes harbor runloop
        └── .claude/skills/meta-harness-terminal-bench-2/SKILL.md
```

No `src/meta_harness/` package. No shared dataclasses across examples. Each example is a **self-contained loop** that happens to share a design.

### ONBOARDING.md + domain_spec.md — worth adopting?

Yes, selectively. The ONBOARDING flow is a 6-step scripted conversation:

1. Ask user for a one-paragraph target-domain description.
2. Initialize running summary with what's already known.
3. Identify the biggest gap.
4. Ask **one focused question** about that gap (hard cap 1–2/turn).
5. Iterate until every required field is filled or marked `unknown`.
6. Verify, then write `domain_spec.md`.

`domain_spec.md` has 6 required sections: **problem framing** (unit of eval, what's fixed, base model, budget) · **harness definition** (interface, Python API shape, scope boundaries) · **evaluation** (search/held-out metrics, noise, runtime, leakage risks) · **baselines** · **offline experience** (traces + reference docs) · **online experience** (logging, storage, debugging artifacts).

**Reuse target**: autopilot's new-role onboarding and new-benchmark onboarding. Today, adding a new orchestrator role means a human edits `orchestrator_stack.py`, `model_registry.yaml`, `seeder.py`, and `program.md` by hand. The ONBOARDING flow is directly reusable as a `scripts/autopilot/onboard_role.md` skill that walks the operator through the same 6 sections, emits `role_spec.md`, and that spec becomes the input to auto-generated wiring. It also fits `agent-world-env-synthesis.md`'s AW-1 entry point — env-synth needs exactly this "new domain" ceremony.

The **enforcement rule** ("Do NOT write `domain_spec.md` until every required field is either filled or marked `unknown`") matters. It prevents the common failure mode of the assistant guessing at missing pieces and silently baking them in.

### text_classification reference (memory-system search)

Search space: Python modules under `agents/` implementing a memory system (init, store, retrieve). Proposer reads `frontier_val.json` + `evolution_summary.jsonl` + existing `agents/*.py`, writes new `agents/<name>.py` + a `pending_eval.json` entry.

Scoring: `inner_loop.py` evaluates each candidate on the datasets listed in `config.yaml`, returns `avg_val` across datasets. `evolution_summary.jsonl` gets one row per candidate with `{iteration, name, avg_val, axis, hypothesis, delta_from_best}`. `frontier_val.json` holds a `_pareto` list ordering survivors by validation accuracy.

No explicit parent selection — the proposer reads the full frontier via `Read`/`Grep` tools and decides autonomously. This is a design choice, not an omission: the authors are trusting the proposer's judgment over any parent-selection heuristic a text-optimizer would bake in.

### terminal_bench_2 reference (scaffold evolution) — closest analog to our code-mutation search space

This is the one that maps onto PromptForge's Tier-2 code-mutation path. Worth walking through in detail.

**Baseline**: `agents/baseline_kira.py`, ~900 LoC. Class `AgentHarness(Terminus2)`, three tools (`execute_commands`, `task_complete`, `image_read`), main loop = `LLM(tools=…) → parse → execute → record → repeat until done or max_episodes`. Uses `anthropic_caching`, tenacity retries, asciinema recording, marker-based polling for early command completion. It is a fully-formed production agent, not a toy.

**What "scaffold evolution" means in the code**: the proposer is told (via SKILL.md) that "the search space is arbitrary Python code … anything expressible in Python is fair game. Agents can override any method, use external libraries, modify LLM calls, intercept observations, add tools." The only structural constraint is that the class must be named `AgentHarness`, must subclass `Terminus2`, and must live in `agents/<name>.py` for harbor compatibility.

So a candidate scaffold is not a patch — it's a whole new `agents/<name>.py` file, typically subclassing `baseline_kira` or another high-frontier ancestor and overriding specific methods. Mutation targets observed in the SKILL prior: tool set changes, LLM-call interception (summarization before context overflow, retry wrappers), observation post-processing, prompt-template swaps in `prompt-templates/`, adding new tools, replacing the main-loop policy.

**Evaluation**: `scripts/run_eval.sh <import_path> <task_set> <n_trials> <n_concurrent>` invokes harbor runloop; 89 tasks × N trials; each trial produces `result.json`; aggregated to a flat `pass_rate = total_passes / total_trials` plus per-task rates and token/turn/$ metrics. Default config: 2 trials/task, Opus 4.6, concurrency 50, ~$500 and 4–6 hours per iteration.

**SKILL.md proposer prior — the most useful artifact here**. Key constraints:
- "Produce **1 new agent variant every iteration**" (never "frontier is optimal, abort").
- **One mechanism per candidate** (one hypothesis per trial — directly parallel to our AP-29 / `_validate_single_variable()` constraint).
- **No task-specific hints, never mention task names** in code or prompts (anti-overfitting — enforced as "would this help a human engineer working on MANY unfamiliar tasks?").
- Read order: frontier state files → `jobs/`+`logs/` trajectories (both failed and successful) → current `agents/*.py`.
- **Predict expected token/turn impact** alongside pass-rate gain. This is a small but concrete pattern we do not have in PromptForge — mutations currently predict quality but not cost.

**Mapping to our code-mutation search space** (`epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` + `CODE_MUTATION_ALLOWLIST`): our allowlist is 4 files (`resolver.py`, `escalation.py`, `escalation_helpers.py`, `tool_policy.py`), mutations are AST-validated textual edits, one file at a time. Meta-harness mutates a **whole new class file** per iteration. Concrete gap: we do not support "add a new strategy file alongside existing ones" — only "edit one of these four." A `new_file` mutation type that writes `src/escalation_strategies/<name>.py` inheriting from a base class would give us the same shape, with the allowlist enforced on the **base class / directory**, not individual filenames.

### claude_wrapper.py — proposer interface

Minimal (one file, ~200 LoC from the shape): `subprocess → claude -p --output-format stream-json`, parses streaming JSON into a `SessionResult` dataclass with `text`, `tool_calls`, `files_read`, `files_written`, `token_usage`, `exit_code`, `duration_seconds`, `cost_usd`, `raw_events`. Logs each session to `<log_dir>/<timestamp>_<slug>/` with `meta.json`, `response.md`, `events.jsonl`, `artifacts/`, `tools/` (per-tool-call summary). Tool allowlist configurable per-call: default `[Read, Glob, Grep, Agent, Write, Edit, Bash]`. Skill injection via `--system-prompt "Follow these skill instructions:\n\n{skill_text}"`.

This **is** our `claude_debugger.py` / PromptForge Popen pattern, but with a richer receipt. We already log mutation proposals + accepts/rejects into `experiment_journal.{tsv,jsonl}`; what we do not log is the granular tool-call trace (files read, edits applied, Bash invocations) inside the proposer session. Meta-harness's per-session `tools/` directory is a cheap win for PromptForge auditability and would compose with our existing journal rather than replacing it.

### tbench2-artifact — the production scaffold

Sibling repo `stanford-iris-lab/meta-harness-tbench2-artifact` ships the final 76.4% scaffold as a polished product. Extends Terminus-KIRA + Harbor's Terminus-2. Files: `agent.py`, `anthropic_caching.py`, `prompt-templates/`, `pyproject.toml`. Not a search log — a product of the search.

One portable insight: **environment bootstrapping**. Before the agent loop starts, the scaffold gathers a snapshot (cwd, file listing, available languages/tools, package managers, memory) and injects it into the initial prompt. This eliminates early exploratory turns — which is exactly the claim in `repl-turn-efficiency.md` Gap-1 (`workspace_scan`). Validates that direction; the EPYC equivalent is `_CombinedOpsMixin.workspace_scan(query)` returning `list_dir(".") + frecency.top_k(10) + code_search(query, k=5)` in one TOON-encoded block, injected at REPL turn 0.

## Mapping to EPYC Active Work

### meta-harness-optimization.md — overlap + gaps

The code confirms our Tier-1/Tier-2 design. One paper-underspecified detail the code reveals:

- **Proposer reads trajectories of both failed AND successful runs** (per SKILL.md read order: "Read failed AND successful trajectories from `jobs/` and `logs/`"). Our B3 implementation feeds `inference_tap.log` tail-50 lines — this is mostly recent activity, not curated successful+failed pairs. The meta-harness prior explicitly pairs the two; pairing gives the proposer contrast, not just recent history. Cheap upgrade to `capture_recent_traces()`: pass `k_success` + `k_failure` and merge.
- **"Predict expected token/turn impact"** in every mutation proposal. PromptForge mutations predict quality delta but not cost delta. Adding a mandatory `expected_cost_delta` field to the mutation schema is ~30 LoC in `prompt_forge.py` and hooks into safety-gate simplicity checks.
- **"One mechanism per candidate"** is already enforced in our tree by `_validate_single_variable()` (AP-29). Convergent validation — confirms the constraint is not an EPYC over-reach.
- **No algorithmic parent selection**. Our PromptForge picks a parent via strategy-store `retrieve()` before calling the proposer. Meta-harness does the opposite: exposes the full frontier, lets the proposer read whatever it wants. The honest test is whether proposer judgment beats retrieval heuristics on parent choice — an A/B experiment inside AR-3.

### autopilot-continuous-optimization.md — onboarding pattern reuse

`ONBOARDING.md` + `domain_spec.md` → `scripts/autopilot/onboard_role.md` skill + `role_spec.md` template. Replaces today's ad-hoc manual wiring when a new role or benchmark is introduced. Directly unblocks `agent-world-env-synthesis.md` AW-1 (new env needs this ceremony) and `minddr-deep-research-mode.md` MD-1 (three-agent pipeline role specs).

### repl-turn-efficiency.md — scaffold evolution as skill-crystallization backend

Validates S5 Gap-1 (`workspace_scan` = environment bootstrapping) empirically — meta-harness's final TB2 scaffold arrived at the same pattern. Separately, **scaffold evolution itself is a candidate Tier-3 skill-crystallization backend**: once Tier-1/2 REPL efficiency stabilizes, apply meta-harness-style search over REPL tool templates and combined-op definitions instead of hand-tuning. That is a genuine Tier-3 direction for this handoff, not a near-term action.

## Refined Assessment

**Downgrade `adopt_component` → `adopt_patterns`.** The "cleaned up but not tested" disclaimer is real and load-bearing:

1. No shared framework package exists — each reference example is a self-contained tree. "Adopting the component" means copying one of them wholesale, which buys code that the authors themselves do not claim works.
2. Our Tier-1/Tier-2 is already re-derived and integrated end-to-end (`B3` trace feedback, `code_mutation` action type, allowlist, safety gates, git revert commits, deep validation). Importing meta-harness's sequential outer loop would replace a working, instrumented system with an un-instrumented reference.
3. The reuse value is in **patterns**: ONBOARDING flow (directly portable), SKILL.md proposer prior (template to adopt), filesystem layout (`evolution_summary.jsonl` + `frontier_val.json` + `pending_eval.json` — convergent with our journal + Pareto archive; minor cross-check only), session receipt format (`tools/` directory per proposer call — worth adding), "predict cost impact" constraint on mutations, "one mechanism per candidate" (already enforced), read-both-failed-and-successful (we do recent-only).

Novelty: **low** (confirmed — no new numbers, no new algorithm). Relevance: **high** (confirmed — it is the official code for a handoff we are actively executing).

## Concrete Next Actions

Target: `meta-harness-optimization.md` Tier-2b (upgraded search + telemetry) and Tier-3 (outer-loop rebuild).

1. **MH-6 (Tier-2b): Adopt the SKILL.md proposer-prior template for PromptForge code-mutation system prompt.** Rewrite the current ad-hoc system prompt in `prompt_forge.py::_build_code_mutation_prompt()` against the terminal_bench_2 SKILL.md structure: explicit read order, "one mechanism per candidate" (already enforced — make the constraint visible to the proposer too), "no task-specific hints / never mention suite names" anti-overfitting clause, mandatory `expected_cost_delta` + `expected_quality_delta` prediction fields. ~100 LoC + prompt rewrite. Falsifiable against AR-3 acceptance-rate + per-mutation cost variance.
2. **MH-7 (Tier-2b): Trace feedback upgrade — paired success+failure.** Extend `eval_tower.capture_recent_traces()` to `capture_contrastive_traces(k_success, k_failure)` and feed both sets to PromptForge. Mirrors the meta-harness SKILL's "Read failed AND successful trajectories" instruction. ~40 LoC. Expected gain: closes the "recent-activity-is-not-contrast" gap in B3.
3. **MH-8 (Tier-2b): Per-proposer-session tool-trace receipt.** Mirror meta-harness's `<log_dir>/<timestamp>_<slug>/tools/` directory for every PromptForge invocation. Each tool call Claude makes during mutation gets one human-readable file. Composes with existing TSV/JSONL journal; purely additive. ~60 LoC in `claude_debugger.py` reuse layer. Audit win, no cost.
4. **MH-9 (Tier-2b): `new_file` mutation type with directory-scoped allowlist.** Currently mutations are edits to 4 specific files. Add a `new_file` action that writes a new module under a directory allowlist (e.g. `src/escalation_strategies/`) inheriting from a registered base class. Matches meta-harness's whole-new-candidate-class pattern. ~80 LoC + 3 tests. Enables the "add a strategy" shape, not just "edit a strategy."
5. **MH-10 (Tier-3 seed): ONBOARDING skill for new-role scaffolding.** Port `ONBOARDING.md` to `scripts/autopilot/skills/onboard_role.md` emitting `role_spec.md` with 6 required sections. Unblocks AW-1 (`agent-world-env-synthesis.md`) and MD-1 (`minddr-deep-research-mode.md`) without committing to the full Tier-3 rebuild. ~1 day design + skill authoring. Treat `role_spec.md` as input to a later autogenerated-wiring pass.

## Sources

- Primary repo: https://github.com/stanford-iris-lab/meta-harness
- Sibling artifact repo: https://github.com/stanford-iris-lab/meta-harness-tbench2-artifact
- Paper: https://arxiv.org/abs/2603.28052 (intake-244)
- Fetched files: `README.md`, `ONBOARDING.md`, `reference_examples/text_classification/` directory listing, `reference_examples/terminal_bench_2/` directory listing, `terminal_bench_2/claude_wrapper.py`, `terminal_bench_2/meta_harness.py`, `terminal_bench_2/.claude/skills/meta-harness-terminal-bench-2/SKILL.md`, `terminal_bench_2/agents/baseline_kira.py` (top 50 lines + summary)
- Related EPYC handoffs: `meta-harness-optimization.md`, `autopilot-continuous-optimization.md`, `repl-turn-efficiency.md`, `agent-world-env-synthesis.md`, `minddr-deep-research-mode.md`, `hermes-agent-index.md`
- Related intakes: intake-244 (paper), intake-327 (GEPA), intake-345 (GEPA Full Program Adapter), intake-450 (Venice Skills SKILL.md rubric), intake-454 (hermes-agent orchestrator subagents)
