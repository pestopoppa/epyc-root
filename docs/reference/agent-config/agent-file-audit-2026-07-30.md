# Agent-File Stack Audit — 2026-07-30

Operator-requested full audit of the core agent-context files: staleness, verbosity,
modularization. Three parallel fact-checking passes (root entry files; `agents/` role layer;
`agents/shared/` policy layer) verified every checkable claim against repo ground truth, plus a
main-thread audit of `MEASUREMENT.md`. Builds on — does not re-propose — the 2026-07-29 lossless
structural deletion pass (root `400fb4b3`, `f4d2b34a`; AFC-P5.0/P5.2).

**Companion plan**: `handoffs/active/agent-file-prose-compression.md` → §AFC-P6 rider
(checkboxed, prioritized).
**MEASUREMENT.md rewrite draft (NOT ratified)**: `artifacts/operator/measurement-v2-draft/`.

## Headline verdicts

| Surface | Verdict |
|---|---|
| `CLAUDE.md` (151 ln, auto-loads every session) | Factually **sound** — every load-bearing claim verified, incl. v8 commit/build/ratification SHA and iqk IQ1-stub status down to CMake level. Defects are structural: 1 stranded bullet, ~7 duplication sites, ~35–40% compressible via extraction. |
| `AGENTS.md` | **Symlink to CLAUDE.md** (since 2026-05-27, guarded by `check_agent_file_symlink.sh`). Nothing separate to maintain. |
| **OPENING_PROMPT.md** (348 ln) | **Dead + hazardous.** Zero live consumers; frozen 2026-02-26; contradicts ratified policy (hand-typed bench commands vs codified-recipes rule, retired models/roles, pre-era unlabeled claims, `pkill` advice vs process discipline). Archive. |
| `CLAUDE_GUIDE.md` (the file remembered as "CLAUDE-GUIDE.md") | **Content-rotted but governance-live**: referenced by 2 hooks + the CLAUDE_MD_MATRIX, yet describes a CLAUDE.md layout that no longer exists ("~370 lines", sections long deleted). Rewrite or retire-with-matrix-update. |
| `MEASUREMENT.md` (617 ln) | Normatively solid, structurally decayed: stale era-table copy (missing E4-qcore/E6/E7/E8), duplicate P-GPU-1 blocks, resolved-but-open placeholder, phantom validator citation, and two operator-ratified policies living only in the digest. v2 draft rewrites it as core + 3 annexes. |
| `agents/*.md` role layer | Schema-clean (validators pass) but **barely consumed**: no `.claude/agents/` wiring exists; 6 of 9 role files have zero consumers outside `agents/` itself. One hard staleness class (per-run approval, below). `agents/coordinator-agent.md` is the live, healthy exception — its issue is duplication with OPERATING_CONSTRAINTS. |
| `agents/shared/*.md` | The right layer, mostly dense. Defects: one active self-contradiction (approval vs region-lock), one governance inversion (digest outruns constitution), compressed-* artifacts drifted, OPERATING_CONSTRAINTS is 56% session-lifecycle content that belongs elsewhere. |

## Defect register

### D1 — Active policy contradiction (worst finding)
Per-run operator bench approval was retired 2026-07-27 (commit `bc2feb10`; held `region-lock`
claim instead; "concurrency alone is never grounds for a human gate" —
`OPERATING_CONSTRAINTS.md:35-36`). Still mandated by: `agents/shared/MEASUREMENT_POLICY.md:20`,
`agents/shared/WORKFLOWS.md:32`, `agents/benchmark-analyst.md:36` (which never mentions
`region-lock` at all), and `MEASUREMENT.md` P-BENCH-1. An agent reading any of the stale copies
will either block on a nonexistent gate or believe approval substitutes for a region claim.

### D2 — Dangling `CLAUDE.md#repository-map` anchor
The 07-29 dedup consolidated repo tables "to the canonical CLAUDE.md map" — but `400fb4b3`
deleted that section. Now dangling: `agents/AGENT_INSTRUCTIONS.md:7`,
`agents/shared/ENGINEERING_STANDARDS.md:29` (uncommitted), `agents/README.md:63` (prose). The
reference validator can't catch it (only scans 6 governance files; regex requires links ending
`.md`, so `#anchor` links escape).

### D3 — MEASUREMENT digest outruns its constitution
"Deterministic replay" + "Consolidated apply-time ratification" (both operator-ratified
2026-07-27) exist only in `agents/shared/MEASUREMENT_POLICY.md` (L25–75); `MEASUREMENT.md` never absorbed
them, violating its own "constitution wins" rule. Fixed in the v2 draft (ledger L6).

### D4 — Stale pointers & content
- `.claude/dependency-map.json` (linked from `AGENT_INSTRUCTIONS.md:8`): says production =
  **v3**, rebuilt 2026-04-09.
- `agents/README.md:29-35` model routing = Haiku/Sonnet/Opus only; no Codex
  terra/luna, no Fable — contradicts CLAUDE.md §Codex Delegation Policy.
- `agents/research-writer-guide.md`: targets nonexistent research_report.md; `@research-writer`
  invocation machinery (`.claude/agents/`) doesn't exist; near-duplicates
  `docs/guides/agent-workflows/research-writer.md` which it itself calls canonical; zero content
  consumers. Retirement candidate on four grounds.
- `agents/build-engineer.md`: framed around deprecated ik_llama-class builds; missing the single
  most important current constraint (v8 freeze / experimental-branch-only builds).
- `agents/lead-developer.md`: mission + delegation matrix predate and collide with
  coordinator-agent's exclusive cross-main authority.
- `ENGINEERING_STANDARDS.compressed-*.md` (May 27): missing the
  `## Kernel Workflow (Production Immutability)` section added 07-26 — a compressed-variant
  reader gets no kernel-freeze rule from this file.
- `CLAUDE.md:50`: stranded `- handoffs/completed/ — Done` bullet inside the wrong section.
- `MEASUREMENT.md`: stale era table, duplicate P-GPU-1, resolved MI210 placeholder, stale
  "v7 candidate" consequence, phantom `check_claims_grammar.sh` (script exists nowhere).

### D5 — Enforcement-surface skew
- Skill workflow + docs cite `scripts/validate_agents.py` — actual entry points are
  `.claude/skills/agent-file-architecture/scripts/validate_agents.py` and
  `scripts/validate/validate_agents_{structure,references}.py` (all pass).
- Three different exclusion lists: `.claude/skills/agent-file-architecture/references/schema.md` + structure validator exclude
  `agents/research-writer-guide.md`; the PreToolUse hook `agents_schema_guard.sh` does NOT — any future
  edit to that file is hook-blocked.
- `.claude/commands/agent-files.md` says "exactly these headers"; the validator checks presence
  only; most role files carry extra H2s — compliant with one surface, not the other.
- `agents/commands/wrap-up.md` (16.5 KB, live via `.claude/commands` symlink) sits outside every
  validation surface.

### D6 — Duplication (post-07-29 residue)
Root/role layer: checkbox-discipline rule ×5 (3 inside OPERATING_CONSTRAINTS alone); "idle main
with an empty queue is a coordination failure" ×5; heartbeat birth-certificate ×2 (with incident
narrative in both); tmux Ctrl-C block ~20 lines near-verbatim in coordinator-agent + OC;
wrap-up/pre-reboot//clear rules restated in coordinator-agent vs OC (each "points at the other"
then restates); agent-logging stated 3× in CLAUDE.md alone; AGENT_INSTRUCTIONS Non-Negotiables
still duplicate OC/ES point-for-point.
Shared layer: recipes-only rule ×4; reps thresholds ×2; observation-vs-claim rule ×3 phrasings;
WORKFLOWS "Benchmark Update" is an unsanctioned third copy of the measurement digest.

### D7 — Layering violations (content in the wrong file)
- OC L89–196 (56%): session-lifecycle/coordination policy → belongs in a lifecycle doc or
  coordinator-agent overlay.
- OC L55–74: tmux TUI mechanics → tool doc.
- ES L78–115 (28%): model-registry YAML format spec for one epyc-inference-research file →
  that repo.
- WORKFLOWS "Orchestration Stabilization Closure (RLM)": single-campaign checklist → owning
  handoff.
- CLAUDE.md: handoff-index authoring spec (L40–52, authoring-time-only) and Codex delegation +
  long-horizon contract (L115–123, Codex-audience-only; currently canonical here with no shared
  home) → docs/guides + agents/shared respectively.
- coordinator-agent.md L146–184 (~39-line escalation ladder with timer constants) →
  `docs/guides/agent-workflows/` (the extraction target dir exists but has received nothing
  since May 2).

## House style adopted for "negatives" (operator directive 2026-07-30)

Negative/incident-derived rules are load-bearing and stay. What moves is the narrative: every
prohibition keeps its directive + **one line** of origin ("origin: <incident>, <date>"); the
full blow-by-blow (PIDs, timestamps, ordinal storytelling) migrates to one incident log
(`docs/reference/agent-config/INCIDENT_LOG.md`) keyed by ID. Estimated yield: the largest
single-file wins are OC (~35–40%) and coordinator-agent (~30%) with zero polarity loss —
the AFC compression gate (`live_runner.py`, compliance ≥0.95× baseline) remains the check
that nothing behaviorally regressed.

## Target architecture (modularization)

Per-session auto-load (CLAUDE.md, target ≲80 lines): repo purpose + repo map stub (fixes D2) +
working-tree identity invariant; v8 freeze headline + 4-step experimental workflow; handoff
entry point + checkbox one-liner; measurement pointer; bus drain + heartbeat commands +
BUS_PROTOCOL link; decision-package pointer; research-intake + debugging one-liners.
Read-on-role (agents/AGENT_INSTRUCTIONS read-order → agents/shared/* + one role overlay).
Read-on-task (docs/guides/agent-workflows/*, MEASUREMENT annexes, BUS_PROTOCOL, incident log).
Everything else discoverable, not resident.

## Addendum — sub-repo agent files (audited 2026-07-30, same day)

**Inventory**: epyc-orchestrator and epyc-inference-research each have a project `CLAUDE.md`
with `AGENTS.md` symlinked to it (104/89 lines). **epyc-llama has NO project agent layer**: its
CLAUDE.md (1 line) and AGENTS.md (200 lines, not a symlink) are pure upstream ggml-org files.

**D8 — the frozen tree is the least-protected tree (worst sub-repo finding).** A session cwd'd
in `/mnt/raid0/llm/llama.cpp` auto-loads only upstream contribution policy, which (a) points
agents at build docs — inviting builds in the FROZEN tree, (b) mandates `Assisted-by:` and
forbids `Co-authored-by:` (opposite of project rules), (c) says ASCII-only. Writing an overlay
into the tree would dirty the freeze (HEAD is pinned by `verify_llama_cpp.sh` + the ratification
SHA), so mitigation is layered: FROZEN warnings added to both sibling repos'
Related-Repositories blocks; `.claude/commands/agent-governance.md` corrected (it claimed
llama.cpp governance rides `repos/epyc-llama/CLAUDE.md` — a dead channel); a project overlay
gets baked into `llama.cpp-experimental` at the next promotion so v9 ships freeze-aware agent
files (AFC-P6.20). Also noted: the frozen v8 tree carries untracked files (`.gitnexusignore`,
`tools/math-tools/`) — operator hygiene call (AFC-P6.22).

**D9 — orchestrator CLAUDE.md architecture rot (fixed same day).** The architecture diagram was
the most decayed block audited anywhere: `REPLExecutor` (nonexistent; real:
Executor/RestrictedExecutor/StepExecutor), `src/orchestration_graph/` (real: `src/graph/`), "7
node classes" (real: 9 = 6 main + 3 MindDR), `FAISSStore`/`ParallelEmbedder`/`OutcomeTracker`
(defs not found), `make gates` missing its 5th step (`nextplaid-reindex`), dir-table row for the
nonexistent dir. All corrected.

**D10 — research CLAUDE.md pre-constitution benchmarking workflow (fixed same day).** Its
"Benchmarking Workflow" predated MEASUREMENT.md: no canonical recipe, no region-lock, no era
citation. Also stale: "29 research chapters" (10 exist); `scripts/lib/registry_loader.py`
(real: `scripts/lib/registry.py`). Rewritten to route through `bench_canonical.sh` /
`canonical_recipe.py` + region-lock + protocol/era citation; registry-FROZEN note added;
architect constraint flagged as under re-evaluation.

**D11 — matrix accounting fiction.** The CLAUDE-accounting matrix
(`docs/reference/agent-config/claude_md_matrix.json` — NOT `.claude/claude_md_matrix.json`;
that path is itself stale) governs exactly ONE file (root CLAUDE.md) while 6 sub-repo agent
files, 3 `.claude/` dirs, and a nested `scripts/benchmark/.claude` settings scope exist
unaccounted. `validate_claude_md_matrix.py` only asserts the string "CLAUDE.md" appears — it
can detect none of this. The claude-md-accounting skill's stated purpose ("all
repository-relevant CLAUDE.md files") does not match single-row reality (AFC-P6.19).

**D12 — gitnexus bloat artifact.** epyc-orchestrator's `.claude/skills/` contains a nested
duplicate `skills/gitnexus/gitnexus-*` subtree — the exact bare-`gitnexus analyze` accident its
own CLAUDE.md line 85 warns against (AFC-P6.21).

**D13 — reference-guard blind spot (found while writing this doc).** The
`agents_reference_guard.sh` hook validates the file's PRE-edit disk state, not the post-edit
content: an Edit can introduce unresolved references undetected, which then block every
subsequent edit to the file. Fold into the AFC-P6.16 validator-hardening item.

**Duplication resolved same day**: the verbatim Operator-Decision-Requests paragraph in both
sub-repo files → one-line pointers to the canonical contract. Kept deliberately: the
Related-Repositories blocks (a sub-repo CLAUDE.md is the ONLY auto-load for sessions cwd'd in
that tree — it must stay self-sufficient; root's map serves /workspace-rooted sessions).

## MEASUREMENT.md v2 (drafted, awaiting ratification)

`artifacts/operator/measurement-v2-draft/`: core constitution (194 ln) + `protocols/`
bench-cpu / quality-eval / gpu-cross-device annexes (471 ln) + `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md`
enumerating all 13 semantic deltas (4 need operator decisions: split-vs-single-file; GPU banked
wins re-certified?; build-or-strike the phantom validator; current core_id). New §1 Metric
scoping codifies the operator's 2026-07-30 directive: task_rate = autopilot-objective metric,
tok/s = instrument-level metric for individual model/kernel benchmarks; neither demotes the
other outside its scope. Verified invariants: all numeric thresholds identical; every lost MUST
restored after diff-check; grammar/verbs/dump-list carried in full.
