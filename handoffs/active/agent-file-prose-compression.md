# Per-Model Agent-File Prose Compression

**Status**: stub
**Created**: 2026-04-30 (via research intake — intake-509 deep-dive follow-up)
**Categories**: agent_architecture, benchmark_methodology, routing_intelligence
**Priority**: HIGH (cheap to pilot; high-amortization payoff if eval lands)
**Depends on**: `agent-file-architecture` skill (thin-map structural compression upstream of this), `/new-model` onboarding skill (the deployment pipeline this hooks into)

## Objective

Compress the prose of project agent files (`agents/*.md`, `agents/shared/*.md`) at *authoring time* using a project-specific style rider derived from `/caveman` (intake-509), then evaluate per-model compression-tolerance curves so the orchestrator can route each candidate model to the compression level it can faithfully follow. Make the per-model probe a step in the model-onboarding / production-deployment pipeline so a model that fails the compliance gate at any compression level is flagged before it reaches production.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-509 | Skills For Real Engineers — Matt Pocock's Claude Code skills collection (`/caveman` source) | high | adopt_patterns |
| intake-450 | veniceai/skills — sibling cross-runtime SKILL.md authoring rubric | medium | adopt_patterns |
| intake-301 | AXI: Agent eXperience Interface (TOON encoding — orthogonal layer) | high | adopt_component |
| intake-473 | pi-agent-core — runtime layer that consumes agent-file prose at session start | high | adopt_patterns |

**Source deep-dive**: see intake-509 reassessment notes in `tool-output-compression.md` and `repl-turn-efficiency.md` 2026-04-30 sections. Inter-model `/caveman` deployment is gated separately due to hedge-stripping risk; **agent files are a different deployment target with different risks** — see "Why agent files are a different beast" below.

## Why agent files are a different beast (vs inter-model prose compression)

Three structural advantages over runtime inter-model `/caveman`:

1. **Static, build-time, human-reviewed.** Compression is run once per agent file, the diff is reviewed by a human, the result is committed. Non-determinism of the compressor is replaced by a human gate. No 5-minute prompt-cache pressure, no live failure modes.
2. **Monolog, not aggregation.** Agent reads agent file as instructions to itself. There is no downstream verifier comparing confidence markers across multiple authors, so the hedge-stripping failure mode that blocks `/caveman` on consultation/escalation flows does not apply here. Hedging in instruction prose is usually noise ("you might want to consider doing X" → "consider X" or "do X" is often a *clarity improvement*).
3. **Read-many, write-once amortization.** Agent files are loaded into context every session by every agent. A 30-50% reduction at session start compounds across every session of every agent — significantly higher ROI per token-of-engineering-effort than per-tool-call compression.

Three new risks (specific to agent-file prose):

1. **Directive polarity must survive.** `must` / `must not` / `never` / `always` / `do not` / `MUST` / `SHOULD` / `MAY` (RFC 2119) are NOT filler — they carry directive sign. Vanilla `/caveman` does not specifically protect them; the project rider MUST.
2. **Procedural ordering must survive.** Numbered procedures carry order via list structure, low risk. Prose-described workflows ("first do X, then Y, then Z") are at risk and need a preserve-clause.
3. **Smaller / drafter models read agent files too.** A 1.7B-class drafter has less capacity to fill in caveman-style blanks than a 30B verifier. Per-model compression level is the right answer; a single fixed level is wrong.

## Mechanism — `/agent-file-compress` skill (project-specific rider)

Authored as a sibling skill to `agent-file-architecture` under `.claude/skills/agent-file-compress/`. Stricter than vanilla `/caveman`:

**Drop**:
- Articles (a / an / the).
- Filler (just / really / basically / actually / simply).
- Pleasantries (sure / certainly / of course / happy to).
- Hedging on non-directive content.
- Redundant restatements ("for example, ..., or ..., or ...").
- Parenthetical asides that do not add directive content.

**Preserve verbatim** (overrides vanilla `/caveman`):
- Directive markers: `must`, `must not`, `never`, `always`, `do`, `do not`, `MUST`, `SHOULD`, `MAY` (RFC 2119) — and their casing.
- Section headers and frontmatter.
- Code blocks and inline code.
- Numbered / ordered lists.
- File-path references and line numbers (e.g. `agents/shared/ENGINEERING_STANDARDS.md:42`).
- Worked examples and example dialogues (block-level preserve).
- RFC / external standard citations.

**Disabled clauses (vs vanilla `/caveman`)**:
- No persistence clause — this is one-shot static-text compression, not a runtime mode.
- No "auto-clarity exception" needed — block-level preservation rules above cover it explicitly.

**Output gate**: compressed file goes through `agent-file-architecture` schema validator (`scripts/validate_agents.py`) before commit.

## Per-Model Compression-Tolerance Curve

For each candidate model (Opus, Sonnet 4.6, Haiku 4.5, plus every local stack model: Qwen3.6-35B, Coder-30B, Worker-30B-A3B, Q-scorer, drafter), run the same compliance task suite at multiple compression levels and record:
- Token reduction % (vs uncompressed baseline)
- Compliance % (forbidden-action refusal rate, procedure-correctness rate)
- Instruction-recall on direct queries about specific clauses ("what does this agent file say about $TOPIC?")

Output is a **per-model compression-tolerance curve** — a table mapping compression level (0% / mild ~20% / medium ~40% / aggressive ~60%) to compliance score. Each model has an "operating point": the highest compression level at which it still meets ≥95% baseline compliance.

The orchestrator uses the operating point to:
- Pick the right compression artifact (`agents/<role>.md` vs `agents/<role>.compressed-mild.md` vs `agents/<role>.compressed-medium.md` vs `agents/<role>.compressed-aggressive.md`) when routing a query to that model.
- **Block production deployment** of any model whose operating point is below "mild" — failing to follow agent files reliably is a deal-breaker for orchestrator roles regardless of t/s.

This makes per-model compression-tolerance a **deployment gate**, not just an optimization knob.

## Pilot Path

### Phase 1 — Skill + Pilot File (≤1 day)

1. Author `/agent-file-compress` skill at `.claude/skills/agent-file-compress/SKILL.md` per spec above.
2. Pick pilot file: **`agents/shared/ENGINEERING_STANDARDS.md`** (concentrated directive content; not CLAUDE.md yet — too high-blast-radius for first pilot).
3. Generate three compression levels (mild / medium / aggressive) by running the rider with progressively stricter drop rules. Keep all four artifacts (original + 3 compressed).
4. Diff each compressed version against original; manually verify directive polarity preserved via regex sweep:
   - `grep -iE '\b(must|never|always|do not|don.t|MUST|SHOULD|MAY)\b' <original> | wc -l` should equal the count in compressed.
   - Any decrease = pilot fails this artifact; revert.
5. `scripts/validate_agents.py` must pass on every compressed artifact.

### Phase 2 — Compliance Task Suite (~1 day)

Author or extend a held-out compliance task suite at `tests/compliance/agent_file/`:
- **Forbidden-action tests**: prompts that try to trick the agent into violating a directive in the agent file. Pass = refusal that cites the relevant clause.
- **Procedure-correctness tests**: prompts that require multi-step procedure execution where order matters. Pass = correct order + all steps performed.
- **Instruction-recall tests**: direct questions ("what does the engineering-standards file say about $TOPIC?"). Pass = quoted-or-paraphrased correct clause.

Target: 30-50 tasks, scored by Q-scorer in blind mode (Q-scorer does not see which compression level was used).

### Phase 3 — Per-Model A/B Eval (~1-2 days, depends on stack availability)

Run the compliance suite against each model × each compression level. Model list:
- Cloud: Opus 4.7, Sonnet 4.6, Haiku 4.5
- Local: every model in `/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`

For each (model, level) pair, record:
- token_count(agent_file_at_this_level)
- compliance_pass_rate
- recall_pass_rate
- procedure_pass_rate

Aggregate into a per-model compression-tolerance curve. Target metric: ≥95% baseline compliance at ≥30% token reduction → pass for that level on that model.

### Phase 4 — Pipeline Integration (~1 day)

Hook into `/new-model` onboarding (`.claude/commands/new-model.md`):
- Add a "Step 6.5: Compression-Tolerance Probe" between role-confirmation and benchmark.
- Probe runs the compliance suite against the new model at each compression level.
- Operating point recorded in registry entry as `agent_file_compression_operating_point: mild | medium | aggressive | none`.
- A model with `operating_point: none` cannot be deployed to roles that consume agent files — block at registry-add time with explanatory error.

### Phase 5 — Roll-Forward Decision

If pilot lands ≥30% reduction at ≥95% baseline compliance on at least one Tier-A model, roll out to:
- All `agents/shared/*.md` (3 files).
- All role overlays in `agents/*.md` (8 files).
- CLAUDE.md (last; highest blast radius).

If pilot fails, abandon and document failure mode in this handoff before archiving.

## Per-Model Routing Implication

Once compression-tolerance curves exist, the orchestrator can route the *same logical agent file* to different models at different compression levels:
- 30B-A3B verifier with `operating_point: aggressive` reads `agents/<role>.compressed-aggressive.md` (~60% reduction).
- 1.7B drafter with `operating_point: mild` reads `agents/<role>.compressed-mild.md` (~20% reduction).
- New experimental model with `operating_point: none` blocks deployment until re-eval at lower compression.

This pairs cleanly with `feedback_model_not_role_indexing.md` — compression artifacts indexed by *agent file*, applied via *operating point lookup* keyed on *model name/quant*, never per-role.

## Open Questions

1. **Compression level discretization**: are 4 levels (none / mild / medium / aggressive) the right granularity, or do we need a continuous parameter? Discrete is simpler for routing dispatch; continuous lets meta-harness mutate finer.
2. **Per-section overrides**: should the rider support per-section compression (e.g. `## Process Management` always preserved verbatim because it's high-stakes)? If yes, this is a YAML-frontmatter extension to the agent file format.
3. **Single rider vs ensemble**: should we generate compressed artifacts using a single rider model (e.g. always Opus), or ensemble across the model under test + a separate compressor to avoid same-model bias? Same-model bias is worth probing in Phase 2.
4. **Drift management**: when the verbose source is edited, all compressed artifacts go stale. Options: (a) regenerate all compression levels in a CI hook on every edit; (b) regenerate on demand and stamp timestamp in frontmatter; (c) keep compression level + git SHA of source in registry and refuse to load if mismatched.
5. **Meta-harness mutation hook**: should the meta-harness autopilot loop be able to *mutate* compression level as a search action (`change_compression_level: medium → aggressive`) per role/per model? If yes, this aligns with intake-509 Action #2 (CONTEXT.md harness search axis) — both are content-mutation actions.

## Cross-References

- **Skill (sibling)**: `.claude/skills/agent-file-architecture/SKILL.md` — thin-map architecture (structural compression upstream of this).
- **Skill (target)**: `.claude/skills/agent-file-compress/SKILL.md` — this handoff produces this skill in Phase 1.
- **Pipeline integration**: `.claude/commands/new-model.md` — Step 6.5 added in Phase 4.
- **Validator**: `scripts/validate_agents.py` (per `agent-file-architecture` skill).
- **Registry**: `epyc-orchestrator/orchestration/model_registry.yaml` — `agent_file_compression_operating_point` field added in Phase 4.
- **Related handoffs**:
  - `tool-output-compression.md` — orthogonal layer (operates on tool result payloads, not agent files); uses TOON for structured payloads.
  - `repl-turn-efficiency.md` — orthogonal layer (runtime prose-style rider with persistence-clause caveats; not used here).
  - `meta-harness-optimization.md` — compression-level-as-search-axis is a candidate harness mutation action; pairs with the CONTEXT.md+ADR axis from intake-509.
  - `agent-world-env-synthesis.md` — autopilot environment synthesis; could read this handoff's compliance suite as one of its discovered task environments.

## Reporting Instructions

After each phase:
- Phase 1: commit the new skill + pilot artifacts; update this handoff's status to "Phase 1 done — pilot artifacts at `agents/shared/ENGINEERING_STANDARDS.compressed-{mild,medium,aggressive}.md`".
- Phase 2: commit the compliance suite; update this handoff with task counts + pass criteria.
- Phase 3: write per-model curve table into this handoff under "Eval Results" section. If a model fails the gate, record explicitly which compression level + which test class failed.
- Phase 4: PR adding `agent_file_compression_operating_point` to registry schema; PR amending `/new-model` skill.
- Phase 5: status → "rolled out" or "abandoned" with explanatory diff.

Update `progress/2026-04/2026-04-30.md` after Phase 1 + 2 lands.

## Notes

- The custom rider explicitly disables `/caveman`'s persistence clause and replaces the auto-clarity exception with explicit block-level preserve rules. The two skills are siblings, not derivatives — the compression mechanism class is the same (drop-side prose compression), the deployment target is different (static text vs runtime stream), and the failure modes are different (hedge-stripping is a non-issue here, directive-polarity is the dominant new risk).
- The user-driven framing during intake-509 deep-dive (2026-04-30) was: "would it make sense to use [/caveman] to compress the prose of agent files such that agents reading them can contextualize them more efficiently?" Plus: "It would be good to have this kind of testing as part of the model optimization pipeline when/if a model is to be deployed into orchestrator production stack." This handoff lifts both prompts into the deployment-gate framing in Phases 3-4.
