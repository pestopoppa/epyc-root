# Deep Dive: Venice.ai Skills — Cross-Runtime SKILL.md Authoring + OpenAPI Drift Detection

**Date**: 2026-04-24
**Intake**: intake-450 (github.com/veniceai/skills)
**Question**: The Venice API itself is a commercial service we will never consume — but the repo is a production-grade reference for *how to author and ship* SKILL.md bundles across heterogeneous agent runtimes (Claude, Codex, Cursor, OpenCode, Hermes). What is actually portable to our `.claude/skills/` + `scripts/hermes/skills/` corpora, and does the OpenAPI→SKILL.md drift-detection pattern translate to anything we maintain?

## Executive Summary

The Venice API surface is irrelevant to us. What's genuinely useful is the repo's *authoring infrastructure*: a 19-skill canonical corpus built to a strict ≤500-line rubric, a shared template directory, per-runtime plugin manifests (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`) that resolve the same skill content into different install paths, and a CI drift-detector that treats the OpenAPI spec as ground truth and SKILL.md files as derived documentation. Every one of those is a pattern we are currently doing informally or not at all.

Our `scripts/hermes/skills/` corpus is three files (`use/`, `escalation/`, `nocode/`), hand-written, no shared template, no cross-runtime manifest, no drift check against the `x_*` override API it documents. Our `.claude/skills/` corpus is five skills, each with its own scripts/references/agents subtree, authored to no written rubric. Venice demonstrates what "mature" looks like at roughly 4× our current volume, and the shape of the maturity is worth mimicking **before** we grow the corpus further — retrofitting a rubric across 30+ skills is harder than adopting one across 8.

The portable value breaks into three distinct patterns, each of which maps to an existing active handoff: (1) the ≤500-line authoring rubric lands in hermes-outer-shell's skill-authoring remaining work; (2) the OpenAPI→SKILL.md drift detector generalizes to an `x_*` override API → `scripts/hermes/skills/` drift detector, which is infrastructure hermes-outer-shell does not currently have; (3) the cross-runtime plugin-manifest pattern is relevant to intake-454 (hermes-agent v0.11.0 namespaced skill bundles) and gives us a concrete template for packaging our overrides as a bundle rather than a patch-set against a fork.

## Technique Analysis

### What the repo contains

Concrete structure (per WebFetch of the repo root + representative files):

- **`skills/`** — 19 skill folders, each a single `SKILL.md` (no scripts/references/agents subtrees like our `.claude/skills/` use). Surfaces: `venice-api-overview`, `venice-auth`, `venice-chat`, `venice-responses`, `venice-embeddings`, image gen/edit, audio speech/music/transcription, video, models, characters, api-keys, billing, x402, crypto-rpc, augment, errors.
- **`template/`** — starter SKILL.md for new contributors. Provides the canonical section order.
- **`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`** — per-runtime manifests resolving the same skill content into each runtime's install layout. Hermes is explicitly named as a target runtime (`$HERMES_OPTIONAL_SKILLS_DIR` / `~/.hermes/skills/`).
- **`scripts/sync_from_swagger.py`** — drift detector. Pulls `https://api.venice.ai/doc/api/swagger.yaml` (or local file), regex-extracts endpoint references from each SKILL.md, diffs both directions (spec→skills for coverage gaps, skills→spec for stale refs), tracks enum drift via a `TRACKED_ENUMS` config, emits human or JSON output, exit 1 on drift for CI.
- **`.github/workflows/`** — runs the sync script on a schedule plus PR checks.
- **`skills.json`** — catalog index.

Representative skill sizing (from fetched samples):
- `venice-chat/SKILL.md`: ~500 lines (at the rubric cap). Frontmatter (`name`, `description`), "When to use", core request fields table, Venice-extension parameters, multimodal table, error-code table, gotchas. Dense reference, not tutorial.
- `venice-api-overview/SKILL.md`: shorter index/roadmap document linking to the other 15 skills — endpoint map, auth-mode comparison, fast-start checklist. Functions as an entry-point skill.

### Key design patterns worth adopting

1. **≤500-line authoring rubric with fixed section order.** Short lead paragraph → "When to use" → endpoint/parameter tables → curl + one SDK example → gotchas → cross-navigation links. Enforced by convention + CI line-count check. Our `scripts/hermes/skills/` files already approximate this (the `use/`, `escalation/`, `nocode/` SKILL.md files are ~40 lines each with a "Usage" + "API Mapping table" + "Notes" pattern) but we have no written rubric — new skills will drift unless we codify it. **Mapping**: a `scripts/hermes/skills/TEMPLATE.md` + a short rubric section in `handoffs/active/hermes-outer-shell.md` is ~30 minutes of work and converts a de-facto convention into an enforceable one.

2. **Overview/index skill as entry point.** `venice-api-overview` is explicitly a roadmap skill that points at the 15 others. We have no equivalent for `scripts/hermes/skills/` — a new user (or agent) reading our three skills in isolation cannot tell what the override API looks like overall. **Mapping**: add a `scripts/hermes/skills/overview/SKILL.md` that enumerates every `x_*` override parameter, links to the three command-specific skills, and points at the hermes-outer-shell handoff. Pairs naturally with the rubric.

3. **OpenAPI→SKILL.md drift detection, adapted to `x_*` overrides.** Venice's script treats `swagger.yaml` as ground truth; any endpoint in the spec not referenced in any SKILL.md is a coverage gap, any endpoint in a SKILL.md not in the spec is stale. This pattern generalizes cleanly to our situation: our ground truth is `src/api/models/openai.py` (where the `x_*` fields on `OpenAIChatRequest` are defined) and the derived doc is our three `scripts/hermes/skills/*.md`. A small Python script that parses the Pydantic model's `x_*` fields and greps the skills for `x_force_model` / `x_max_escalation` / `x_disable_repl` / `x_orchestrator_role` would catch the exact failure mode we already nearly hit: adding a new override field and forgetting to update the skill, or removing one and leaving stale docs. **Mapping**: `scripts/hermes/skills/check_drift.py` + a hook entry in `scripts/hooks/` so the check runs pre-commit on edits to either `openai.py` or `scripts/hermes/skills/`. ~2 hours of work; strictly additive, no dependency on Venice's script.

4. **Per-runtime plugin manifests for the same skill content.** Venice's `.claude-plugin/` / `.codex-plugin/` / `.cursor-plugin/` pattern — one content tree, per-runtime manifests that resolve into each runtime's install path — is exactly the packaging problem intake-454 (hermes-agent v0.11.0) introduces with namespaced skill bundles. Today we would install our hermes skills by symlinking `scripts/hermes/skills/` into `~/.hermes/skills/`; under v0.11.0 we can ship them as a namespaced bundle. Venice's manifest structure is a concrete template for what that bundle should look like. **Mapping**: deferred until we actually merge hermes-agent v0.11.0, but worth referencing when intake-454's "plugin surface evaluation" task runs — it's the right answer to "how do we package x_* overrides without forking?"

5. **Density, not verbosity, in authoring.** `venice-chat` fits the entire OpenAI-compatible surface plus Venice extensions plus multimodal plus error codes in ~500 lines because every field is a table row, not a paragraph. Our existing skills are already dense; the rubric would codify this as a non-negotiable — no tutorials, no walkthroughs, reference documents only.

### What NOT to adopt

- **The 19-skill API-surface granularity.** Venice has an endpoint-per-skill split (`venice-chat` separate from `venice-embeddings` separate from `venice-models`) because they have dozens of endpoints. Our `x_*` override surface is three parameters; one-skill-per-override is the right granularity and we already have it. Do not proliferate — the right heuristic is "one skill per user-facing command," not "one skill per API field."
- **`skills.json` catalog.** A catalog makes sense at 19+ skills where an LLM needs to select one by name; at 3–8 skills a human or an agent can read the directory listing. Skip until we cross ~15, at which point the drift detector (action 2 below) can be extended to also emit/validate the catalog as a side-product.
- **Flat `SKILL.md`-only skill layout.** Venice's skills have no `scripts/`, `references/`, or `agents/` subtrees — they're single reference documents. Our `.claude/skills/research-intake/` and `.claude/skills/agent-file-architecture/` both use the subtree layout and benefit from it (shared scripts, reference docs, sub-agent definitions). Don't flatten to match Venice; the subtree is correct for process skills. The flat layout is fine for Hermes slash-command skills where there's no companion code to ship.
- **Runtime-specific plugin manifests *today*.** Our only real runtime target is Claude Code + Hermes. Authoring Codex/Cursor/OpenCode manifests with no consumer is complexity without payoff. Revisit only if/when we actually need cross-runtime distribution (intake-454 bundle packaging is the trigger).
- **The Venice API surface itself.** Commercial LLM service, not relevant. No further review needed; the repo is a reference implementation of authoring infrastructure, not a data source.

## Cross-EPYC Applicability

- **hermes-agent-index (intake-117)** — parent index. Phase 2 P2 block includes the three written skills as ✅ done. This deep-dive gives that block a next step: a rubric + overview skill + drift detector. Small additions, all in scope for the "Hermes skill YAML files" work item.
- **hermes-outer-shell** — the rubric + overview skill + drift-detector land here directly. Specifically: the handoff's "Remaining Phase 2 Work" list is currently all inference-dependent; adopting the Venice patterns adds three *inference-independent* tasks that can proceed immediately.
- **intake-454 (hermes-agent v0.11.0)** — namespaced skill bundles + plugin hooks. Venice's `.claude-plugin/` layout is a concrete template for what a Hermes namespaced bundle manifest should look like when we evaluate the new plugin surface. Cross-reference only; do not pre-implement.
- **intake-337 (addyosmani/agent-skills)** — already adopted its anti-rationalization tables pattern in `.claude/skills/research-intake` and `.claude/skills/agent-file-architecture`. Venice adds a complementary pattern: addyosmani is "how to write rigorous process skills", Venice is "how to ship a canonical API-reference skill corpus." The two are stackable — our rubric can mandate both a "Rationalizations" section (addyosmani) and the ≤500-line reference-doc density (Venice).
- **meta-harness-optimization** — minimally relevant. The drift-detection pattern is conceptually similar to meta-harness treating traces as ground truth for prompt/code mutation; different subject, same "derived artifact must match upstream source" pattern. No direct action.
- **repl-turn-efficiency + tool-output-compression** — not directly applicable. These handoffs concern runtime behavior, not skill authoring. Weak cross-ref at best: if we ever write SKILL.md files documenting REPL tool semantics (e.g., `peek_grep` combined op, compressed tool output), the Venice rubric applies.
- **intake-277 (Hermes LLM Wiki skill)** — Venice's overview/index-skill pattern is the right template if we ever author a wiki-entry-point skill. Noted.

## Refined Assessment

**Original**: verdict `adopt_patterns`, novelty low, relevance medium.

**Refined**: verdict `adopt_patterns` **confirmed**; novelty **unchanged** (still low — none of these patterns are novel in isolation, they are competent application of known patterns); relevance **upgraded from medium to medium-high**. The upgrade is justified by two specific observations this deep dive surfaced that the intake entry understated:

1. The OpenAPI→SKILL.md drift detector is not just a "nice pattern to note" — it maps to a concrete gap in our tooling (no CI check that `scripts/hermes/skills/` stays synchronized with `src/api/models/openai.py`) that we've already come close to hitting. This is actionable infrastructure, not a reference point.
2. The rubric + overview-skill patterns become substantially more valuable *before* we grow the skill corpus than *after*. With intake-454's namespaced bundles landing soon, we will likely add skills; retrofitting a rubric across a grown corpus is materially harder than adopting one now. The window for cheap adoption is narrow.

Novelty stays low because the underlying ideas (style guides for docs, CI drift checks, template-based authoring) are well-established practice. The value here is the *combination shipped as a coherent bundle* at the right granularity for agent-runtime skill authoring — a working example, not a new idea.

No change to the "not applicable as API consumer" conclusion. Venice API itself is out of scope and stays out of scope.

## Concrete Next Actions

Priority-ordered, each tied to an existing handoff:

1. **[hermes-outer-shell, new P2 task, ~30 min]** Add `scripts/hermes/skills/TEMPLATE.md` + a rubric subsection to `hermes-outer-shell.md` codifying the ≤500-line / fixed-section-order / tables-not-prose convention our existing three skills already follow. Blocks nothing; cheap to adopt; prevents drift as we add more skills under intake-454.

2. **[hermes-outer-shell, new P2 task, ~2 hr]** Write `scripts/hermes/skills/check_drift.py`: parse the `x_*` fields on `OpenAIChatRequest` in `src/api/models/openai.py` (via `ast` or importing the Pydantic model), regex-scan `scripts/hermes/skills/*.md` for each field name, produce a two-way diff (API fields without skill coverage + skill references to removed fields), exit 1 on mismatch with a human-readable report, exit 0 clean. Add `--json` flag mirroring Venice's script for CI consumption. Wire into `scripts/hooks/` as a pre-commit hook that fires when either `src/api/models/openai.py` or `scripts/hermes/skills/` is touched. The concrete failure mode this closes: Phase 2 added `x_max_escalation` / `x_force_model` / `x_disable_repl` and the skills were written three days later — there is currently nothing preventing the next `x_*` field from shipping without a skill update.

3. **[hermes-outer-shell, new P2 task, ~30 min]** Author `scripts/hermes/skills/overview/SKILL.md` — the entry-point skill that enumerates every `x_*` override, links to `use/`, `escalation/`, `nocode/`, and points at `handoffs/active/hermes-outer-shell.md`. Apply the rubric from action 1 as its first consumer.

4. **[intake-454 evaluation, deferred]** When the hermes-agent v0.11.0 merge task begins (cf. intake-454 "plugin surface evaluation"), reference Venice's `.claude-plugin/` manifest layout as the concrete template for packaging our `x_*` overrides as a namespaced Hermes bundle instead of a fork patch-set. Do not pre-build; just cross-reference.

5. **[hermes-agent-index, bookkeeping]** Add a one-line "Skill-authoring infrastructure" subsection under P2 that lists actions 1–3 as a cluster with a shared rationale (pre-empts growth, closes a concrete drift gap, modeled on intake-450). Keeps the index actionable per the root CLAUDE.md index-document requirements.

## Drift-Detector Sketch (action 2 detail)

Concrete shape of what `scripts/hermes/skills/check_drift.py` should look like, modeled on Venice's `sync_from_swagger.py`:

```
# Ground truth: x_* fields on OpenAIChatRequest
# Parse strategy: import the Pydantic model, enumerate model_fields,
#                 filter keys starting with "x_".
#                 Fallback for CI without deps: ast.parse the file and
#                 collect AnnAssign targets whose name matches ^x_.*.

# Derived artifact: scripts/hermes/skills/**/SKILL.md
# Parse strategy: regex `\bx_[a-z_]+\b` over each file's full text,
#                 per-skill set of referenced field names.

# Diff:
#   missing_coverage = spec_fields - union(skill_refs)   # exit 1
#   stale_refs       = union(skill_refs) - spec_fields   # exit 1
#   per-skill coverage manifest (skill -> [fields it documents]) -> --json

# Enum tracking (optional, phase 2): for x_max_escalation whose values
# are enumerated as A/B1/B2/C in the API model, check that each enum
# value appears in the corresponding skill's API Mapping table.
# This is Venice's TRACKED_ENUMS pattern, directly portable.
```

This is ~80 lines of Python. The enum-tracking phase is strictly additive and would have caught the kind of drift where, e.g., a new `B3` tier is added to the escalation enum but not to `scripts/hermes/skills/escalation/SKILL.md`.

## Open Questions

- Does hermes-agent v0.11.0's namespaced-skill-bundle format specify a manifest schema? If so, Venice's `.claude-plugin/` structure is a reference; if not, we may need to propose one upstream.
- Would the drift-detector run usefully against `.claude/skills/` as well? Those skills don't document an API surface, so probably not — they document processes. The pattern may not generalize beyond the hermes skill corpus.
- Is there value in a `TEMPLATE.md` shared between `.claude/skills/` and `scripts/hermes/skills/`, or do the two corpora need different rubrics (process-skill vs command-skill)? Probably different — the Venice rubric applies cleanly to command skills only.

## Sources

- Primary: https://github.com/veniceai/skills
- Fetched files:
  - https://raw.githubusercontent.com/veniceai/skills/main/skills/venice-chat/SKILL.md
  - https://raw.githubusercontent.com/veniceai/skills/main/skills/venice-api-overview/SKILL.md
  - https://raw.githubusercontent.com/veniceai/skills/main/scripts/sync_from_swagger.py
- Related deep-dives: `research/deep-dives/opengauss-architecture-analysis.md`, `research/deep-dives/context-mode-tool-compression-patterns.md`
- Related handoffs: `handoffs/active/hermes-agent-index.md`, `handoffs/active/hermes-outer-shell.md`
- Related intakes: intake-117 (Hermes Agent), intake-277 (Hermes LLM Wiki skill), intake-327 (Hermes self-evolution), intake-337 (addyosmani/agent-skills rubric), intake-454 (hermes-agent v0.11.0 namespaced skill bundles)
- Local skill corpora: `scripts/hermes/skills/{use,escalation,nocode}/SKILL.md`; `.claude/skills/{research-intake,agent-file-architecture,gitnexus,project-wiki,claude-md-accounting}/`
