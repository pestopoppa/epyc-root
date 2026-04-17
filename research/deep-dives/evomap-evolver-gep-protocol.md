# EvoMap / evolver — GEP Protocol Deep Dive

**Intake**: intake-394
**Source**: https://github.com/EvoMap/evolver (GPL-3.0, Node.js, 3.5k stars / 362 forks as of 2026-04-17)
**Hub**: https://evomap.ai
**Investigation date**: 2026-04-17
**Investigator**: deep-dive sub-agent on behalf of PromptForge/autopilot governance

---

## TL;DR

Evolver is a real, actively-released project (v1.67.1 shipped 2026-04-17, multiple contributors, ~40 files in `src/gep/`). The "GEP protocol" is **not** vaporware at the repo level, but it is **much thinner than the marketing suggests**: the on-disk GEP schema is three small JSON/JSONL files, two of which ship empty. Genes are prompt-strategy records with hard-coded validation shell commands; Capsules are empty stubs; EvolutionEvents append-only log is empty. The actual "evolution" is an LLM prompt-builder that emits a protocol-constrained prompt for a host runtime (OpenClaw) to interpret — **Evolver itself does not mutate code or prompts**.

For EPYC/PromptForge: the Gene schema (signals_match, preconditions, strategy, constraints, validation) is a **tidy governance wrapper we should crib** on top of our existing mutation machinery. Nothing else in the project is competitive with what PromptForge + GEPA (intake-240 / intake-327) already offer. Verdict **stays `worth_investigating`** but narrows to "copy the Gene schema concept; ignore the Hub, ignore the runtime, ignore the marketing."

---

## Core Architecture

### What Evolver actually does

Per the README, `src/` layout, and `package.json` (dependencies: only `dotenv`):

1. **Scans memory/logs** → extracts signals (errors, perf, user requests)
2. **Selector** (`src/gep/selector.js`) picks best-matching existing Gene/Capsule by `signals_match`
3. **Prompt assembler** (`src/gep/prompt.js`) embeds the selected Gene + recent EvolutionEvents into a GEP-bound prompt
4. **Emits the prompt to stdout** — the host runtime (OpenClaw) reads stdout directives like `sessions_spawn(...)` and actually performs the edits
5. **Solidify** (`src/gep/solidify.js`) appends an EvolutionEvent after validation passes

**Key realisation**: Evolver is a **prompt-builder CLI**, not an autonomous code editor. Its "safety" comes from the host runtime, not Evolver itself. The `scripts/validate-modules.js ...` entries in Genes are run via the host's whitelisted shell.

### `src/gep/` modules (~40 files)

Concrete modules found: `selector.js`, `mutation.js`, `solidify.js`, `policyCheck.js`, `assetStore.js`, `memoryGraph.js`, `prompt.js`, `signals.js`, `strategy.js`, `candidateEval.js`, `candidates.js`, `skillDistiller.js`, `skillPublisher.js`, `sanitize.js`, `contentHash.js`, `a2a.js` / `a2aProtocol.js`, `mailboxTransport.js`, `hubReview.js`, `hubSearch.js`, `hubVerify.js`, `directoryClient.js`, `idleScheduler.js`, `personality.js`, `narrativeMemory.js`, `reflection.js`, `integrityCheck.js`, `localStateAwareness.js`, `envFingerprint.js`, `deviceId.js`, `crypto.js`, `shield.js`, `taskReceiver.js`, `questionGenerator.js`, `curriculum.js`, `learningSignals.js`, `llmReview.js`, `executionTrace.js`, `explore.js`, `selfPR.js`, `issueReporter.js`, `validationReport.js`, `.integrity`.

Red flags in the layout:
- `javascript-obfuscator` is a **devDependency** — non-trivial signal that parts of shipped code may be obfuscated.
- `.integrity` file next to source and `crypto.js` / `shield.js` / `deviceId.js` / `envFingerprint.js` suggest anti-tamper / telemetry / licensing plumbing rather than pure evolution logic.
- `hubReview.js`, `hubSearch.js`, `hubVerify.js`, `a2a*.js`, `mailboxTransport.js`, `skillPublisher.js` are all Hub-coupled — a large fraction of the codebase is network/commerce plumbing rather than the optimizer.

---

## GEP Schema — Actual Fields, Not Marketing

### `assets/gep/genes.json` (populated, 3 bundled genes)

```json
{
  "version": 2,
  "genes": [
    {
      "type": "Gene",
      "id": "gene_gep_repair_from_errors",
      "category": "repair",                       // repair | optimize | innovate
      "signals_match": ["error", "exception", "failed", "unstable"],
      "preconditions": ["signals contains error-related indicators"],
      "strategy": [ /* 6-step natural-language recipe */ ],
      "constraints": {
        "max_files": 20,
        "forbidden_paths": [".git", "node_modules"]
      },
      "validation": [
        "node scripts/validate-modules.js ./src/evolve ./src/gep/solidify ...",
        "node scripts/validate-suite.js"
      ]
    },
    /* 2 more genes: gene_gep_optimize_prompt_and_assets, gene_gep_innovate_from_opportunity */
  ]
}
```

That's the **entire shipped Gene corpus**: 3 genes, one per category (repair / optimize / innovate). No more. No JSON-schema definition file, no TypeScript types visible in assets. The schema is implied by the three examples.

### `assets/gep/capsules.json` (empty)

```json
{ "version": 1, "capsules": [] }
```

No bundled Capsules. The README says Capsules are "successful task execution paths" but the repo ships zero — users generate them locally, or fetch them from the Hub.

### `assets/gep/events.jsonl` (0 lines / 0 bytes)

Completely empty at HEAD. EvolutionEvent schema is inferred only from in-source `solidify.js` emission, not declared.

### Assessment of protocol concreteness

- **Present**: A clear Gene record shape (7 fields) with validation-command whitelisting and forbidden-path constraints — this is useful.
- **Absent**: A declared JSON Schema; a bundled Capsule example; a documented EvolutionEvent format; version/migration rules; publish/subscribe wire format with the Hub.
- **Verdict**: "Concrete at the Gene-record level, aspirational everywhere else." The GEP name implies an RFC-grade spec; the shipped artifact is a data-shape convention plus three examples. It is **reusable as a design pattern**, not droppable as a protocol.

---

## Project Liveness

| Signal | Finding |
|---|---|
| Last push | 2026-04-17 (same day as investigation) |
| Release cadence | v1.67.1 → v1.67.0 → v1.66.0 within 2 days; automated `evolver-publish` bot |
| Contributors | Multi-author (voidborne-d, blackdogcat, shinjiyu, autogame-17, etc.) — not single-author POC |
| Open issues | 14–22 (API returned 22), substantive: Hub solidify API 500ing "4+ days", SSE reconnection failures, license inconsistency README/package.json, Windows shell incompat, sanitize.js missing Slack/JWT/Azure/Discord redaction |
| Community | 3.5k stars, 362 forks, "top of ClawHub charts, 36k downloads in 3 days" per third-party coverage |
| Hub reality | Real domain (evomap.ai), public blog, **but** Issue #110 is titled "申请 EvoMap 邀请码" ("Apply for EvoMap invite code") — Hub appears invite-gated, which explains why no user-captured telemetry exists in the bundled repo |

**This is a live project with a business behind it, not a POC.** That said, the Hub is currently invite-gated and at least one core Hub API (`solidify`) is broken per its own issue tracker. The commerce layer is real but unreliable.

---

## Third-party reception

- **Capability Evolver Deep Research Report (Mar 2026)** (gist by SQLOPTIMISE): "cautiously favorable." Flags "Mad Dog Mode default" (changes apply immediately without review), repair loops that patch symptoms, unreliable blast-radius in git-less repos. Recommends Phase-1 adoption with strict isolation.
- **EvoMap vs. Nous Research (Hermes Agent) dispute (Apr 2026)**: EvoMap publicly accused Hermes Agent of architectural copying (three-layer memory, closed-loop experience extraction, "10+ similarities"). Nous/Teknium rebutted: Hermes repo predates Evolver by 6 months, Hermes uses **GEPA** (academic, ICLR 2026 Oral) which is unrelated to "GEP", Teknium called the claim "brainless." This matters for EPYC because **Hermes is on this machine** (`/mnt/raid0/llm/hermes-agent`) and we already track Hermes self-evolution in intake-327. The allegation, if taken at face value, would imply EvoMap sees PromptForge-adjacent systems as competitive — but the timeline and GEP-vs-GEPA confusion undercut EvoMap's credibility rather than Hermes'.
- No HN / Reddit substantive technical threads surface. Coverage is mostly Chinese-language crypto/AI news reposting the Hermes dispute.

---

## Comparison vs PromptForge / GEPA / Darwinian Evolver

| Axis | PromptForge (EPYC) | GEPA (intake-240/327) | Darwinian Evolver | EvoMap Evolver |
|---|---|---|---|---|
| Optimization signal | Orchestrator eval tower (T0/T1/T2) scores | Execution traces + LLM-as-judge | Code-level evolutionary search | Log-signal extraction, no closed loop in-repo |
| Mutation driver | Claude CLI with 6 mutation types (targeted_fix, compress, few_shot_evolution, crossover, style_transfer, gepa) | Reflective mutation + Pareto selection | AST-level transforms | LLM emits prompt; host runtime does mutation |
| Audit trail | experiment_journal.py (TSV + JSONL) + git diffs | DSPy run artifacts | Generational fitness logs | `events.jsonl` append-only (empty in repo) |
| Safety gates | safety_gate.py: quality floor, per-suite guard, routing diversity, rollback | 5 constraint gates (tests, size, cache, semantics, human review) | Test-passage gating | `policyCheck.js` + validation shell whitelist |
| Asset reuse | pareto_archive.py (4D non-dominated) | Pareto front over trace-level score | Per-run | Gene library (3 bundled) + optional Hub |
| Empirical results | Internal benchmarks, quality/speed/cost/reliability | Published — 10-35% gains, ICLR 2026 Oral | Published | **None in README** |
| License | Internal | MIT | AGPL-3.0 | GPL-3.0 |
| Language | Python | Python | Python | Node.js |

**Novelty check**: Evolver's algorithmic core (signal extraction → template-matched prompt → validate → append event) is **below** PromptForge's current state and **far below** GEPA integrated into PromptForge (AP-19). What Evolver has that we don't:

1. **Declared Gene record schema** with `signals_match` / `preconditions` / `strategy` / `constraints.forbidden_paths` / `validation` — a clean governance contract per mutation strategy.
2. **"Protected source files" pattern** (constraints.forbidden_paths + `shield.js`) to prevent the optimizer from mutating the optimizer. PromptForge has CODE_MUTATION_ALLOWLIST (whitelist); Evolver adds a forbidden-paths blacklist that travels with the strategy record. Combining both (allowlist on modifiable paths + per-strategy deny-list) is cheap and strictly better.
3. **Strategy-preset intent mixer** (balanced / innovate / harden / repair-only, e.g. 80/15/5 vs 0/20/80 weights). PromptForge's meta_optimizer.py currently rebalances species budgets but not per-category mutation bias within PromptForge.

Nothing else in Evolver is novel vs what EPYC ships today.

---

## What EPYC Could Adopt

Concrete, scoped proposals (none require adopting Evolver itself):

1. **Gene-record schema for PromptForge mutation strategies.** Today `MUTATION_TYPES` in `prompt_forge.py:37` is a flat string list. Replace with a YAML catalog of records shaped like Evolver's Gene:
   ```yaml
   - id: prompt_targeted_fix
     category: repair
     signals_match: [low_quality, wrong_answer, tool_misuse]
     preconditions: [failure_cases provided, per_suite_quality available]
     constraints:
       max_files: 1
       forbidden_paths: [orchestration/prompts/controller/*, orchestration/prompts/frozen/*]
     validation:
       - python -m compileall orchestration/prompts
       - pytest tests/prompts/smoke -q
   ```
   This upgrades PromptForge governance for ~a day of work, fits cleanly with `failure_blacklist.yaml`, and gives the controller a richer selection surface than "pick a string from MUTATION_TYPES."

2. **Per-strategy `forbidden_paths` deny-list** alongside `CODE_MUTATION_ALLOWLIST`. Lets us declare e.g. "the `compress` strategy is never allowed to touch `controller.md`" without changing the global allowlist. Tiny code change in `apply_mutation` / `apply_code_mutation`.

3. **Intent-mix weighting for PromptForge mutation-type selection.** Today the controller picks a mutation type per trial; add a `strategy_preset` (balanced / innovate / harden / repair) that biases the sample distribution. Fits naturally into `program.md` as a tunable.

4. **EvolutionEvent log format** as a shape for `experiment_journal.jsonl`. We already journal mutations; aligning fields (`intent`, `gene_id`, `parent_event_id`, `blast_radius`, `validation_result`) would make future inter-repo interop possible without committing to Evolver's toolchain.

Explicitly **not** adopted: the Hub, A2A protocol, skillPublisher/skillDistiller, mailboxTransport, `.integrity`/`shield.js`/`deviceId.js`/`envFingerprint.js` layer (licensing/telemetry plumbing, not evolution logic), Node.js runtime.

---

## Limitations / Risks

- **Empirical vacuum.** Zero benchmarks in README. No regression results, no A/B vs baseline, no before/after trace analysis. The third-party "Deep Research Report" is anecdotal single-run.
- **Capsule + Event stores ship empty.** The "auditable evolution assets" pitch is structurally present but substantively absent — every user starts from zero, and the Hub (where shared Capsules would live) is invite-gated with a broken `solidify` API at time of writing.
- **Obfuscated code.** `javascript-obfuscator` as devDependency + `.integrity` file + `crypto.js`/`shield.js`/`envFingerprint.js`/`deviceId.js` suggest shipped code is partially obfuscated with tamper detection and device fingerprinting. GPL-3.0 technically, but practically inspecting / extending parts of the runtime may be hostile. **Don't vendor any of it.**
- **Self-promotion dispute.** EvoMap's public accusation against Nous/Hermes (which lives on our own machine and which we use via intake-327) introduces reputational coupling — adopting Evolver wholesale would force us to pick a side. Adopting schema ideas only avoids this.
- **"Evolution" is one LLM call.** The advertised self-evolution is a signal-extraction + prompt-template + host-runtime-eval loop. It has no Pareto selection, no population, no rollout sampling. PromptForge+GEPA is strictly more sophisticated.
- **Hub vaporware risk is medium, not high.** evomap.ai exists and serves real content; but the Hub's core solidify/review/publish endpoints have shipped bugs and invite gating. Treat the Hub as "may disappear within 12 months" and don't depend on it.

---

## Verdict Change from Initial Intake

**Initial (2026-04-17 intake)**: `novelty=medium`, `relevance=medium`, `verdict=worth_investigating`, rationale "adoptable design ideas for PromptForge/autopilot governance."

**After deep-dive**:

- **Verdict: unchanged at `worth_investigating`**, but with tightened scope — the *only* investigation output is cribbing the Gene-record schema, forbidden-paths pattern, and intent-mix preset into PromptForge governance. Not a component adoption candidate.
- **Novelty: downgrade to `low-medium`.** The algorithmic core is below PromptForge+GEPA. Novelty is purely at the governance-schema layer.
- **Relevance: unchanged at `medium`**, constrained to PromptForge governance + `program.md` strategy presets. Not relevant to eval tower, Pareto archive, species budgeting, or Hermes-agent work.
- **Credibility: assign `credibility_score: 2`** (was null). Active project with releases and multi-author contribution, but zero empirical validation, partially obfuscated code, and a public dispute that undermines the org's analytical credibility.

**Action**: Open a small PromptForge enhancement proposal referencing this deep-dive for items (1)–(4) in "What EPYC Could Adopt". Do not open a handoff for Evolver adoption. Do not add evomap.ai to any dependency surface.

---

## Key file locations (for follow-up)

- Intake record: `/mnt/raid0/llm/epyc-root/research/intake_index.yaml` lines 14236–14287 (intake-394)
- Related intake: `intake-240` (GEPA paper), `intake-327` (Hermes Agent self-evolution, DSPy+GEPA), `intake-338` (Agent Lightning)
- PromptForge source: `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py` (813 lines, `MUTATION_TYPES` at line 37, `CODE_MUTATION_ALLOWLIST` at line 29)
- PromptForge GEPA integration: `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/gepa_optimizer.py` (AP-19)
- Handoff context: `/mnt/raid0/llm/epyc-root/handoffs/active/autopilot-continuous-optimization.md`
- Hermes (referenced in dispute): `/mnt/raid0/llm/hermes-agent`

---

## Sources

- [GitHub — EvoMap/evolver](https://github.com/EvoMap/evolver)
- [evolver/assets/gep/genes.json (raw)](https://raw.githubusercontent.com/EvoMap/evolver/main/assets/gep/genes.json)
- [evolver/assets/gep/capsules.json (raw)](https://raw.githubusercontent.com/EvoMap/evolver/main/assets/gep/capsules.json)
- [evolver/package.json (raw)](https://raw.githubusercontent.com/EvoMap/evolver/main/package.json)
- [Capability Evolver Deep Research Report (gist, Mar 2026)](https://gist.github.com/SQLOPTIMISE/2ca9313bb11e37c573aae053b8f0f80d)
- [evomap.ai — What is GEP?](https://evomap.ai/learn/what-is-gep)
- [Phemex coverage of EvoMap vs. Hermes dispute](https://phemex.com/news/article/evomap-accuses-hermes-agent-of-architectural-copying-nous-research-rebuts-73500)
- [Issue #110 — "申请 EvoMap 邀请码" (invite-code gate)](https://github.com/EvoMap/evolver/issues/110)
