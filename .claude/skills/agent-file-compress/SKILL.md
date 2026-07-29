---
name: agent-file-compress
description: Compress the prose of project agent files (`agents/*.md`, `agents/shared/*.md`, `CLAUDE.md`) at authoring time using a strict project rider that preserves directive polarity (RFC 2119), procedural ordering, and structural blocks. Use when generating compressed variants of an agent file (mild / medium / aggressive levels) for per-model deployment.
---

# Agent File Compress

Use this skill for static compression of agent-file prose. Compression is run once per file, the diff is human-reviewed, the result is committed. Per-model deployment of compressed variants is governed by `agent_file_compression_operating_point` in the model registry; this skill produces the artifacts that flag is keyed against.

Use when:

- Generating mild / medium / aggressive variants of a role overlay (`agents/<role>.md`).
- Generating mild / medium / aggressive variants of a shared policy file (`agents/shared/*.md`).
- Generating mild / medium / aggressive variants of `CLAUDE.md` after the per-model probe has cleared smaller files first.
- Refreshing compressed artifacts after the verbose source is edited.

Do not use when:

- Compressing live tool-call output streams — that is `repl-turn-efficiency.md`'s slot, with different persistence-clause caveats.
- Compressing structured payloads (TOON / JSON tool results) — that is `tool-output-compression.md`'s slot.
- Editing the source agent file. Source edits go through `agent-file-architecture` first.

## Workflow

1. Read the source file and count directive markers via the polarity-grep below. Record `directive_count_orig`.
2. Generate the requested level (mild / medium / aggressive) by applying the Drop list with the level-specific stringency from "Levels" below.
3. Apply the Preserve-verbatim list — these blocks pass through untouched regardless of level.
4. Re-count directive markers in the compressed artifact. `directive_count_compressed` MUST equal `directive_count_orig`. If not, revert and tighten the rider.
5. Run the agent-file architecture validator suite: `python3 .claude/skills/agent-file-architecture/scripts/validate_agents.py`. If the compressed file is at `agents/<role>.compressed-*.md`, the structure validator may not pick it up by glob — that is acceptable for shared/ overlays. For top-level `agents/*.md` role files, the validator MUST pass on the compressed artifact.
6. Human diff review per artifact. Only commit after a human reads the unified diff.

## Boundaries

- One file at a time. Do not batch-compress; each file's directive structure has its own polarity profile.
- Three levels per file: mild (~20% reduction), medium (~40%), aggressive (~60%). Do not invent a fourth level.
- Output filenames: `<original>.compressed-mild.md`, `<original>.compressed-medium.md`, `<original>.compressed-aggressive.md`.
- Never overwrite the source file. The source is canonical; compressed artifacts are derived.

## Drop list

The compressor MUST drop the following classes of tokens at every level (stringency increases with level):

- **Articles**: `a` / `an` / `the` when removal does not change meaning. Aggressive level drops them in nearly all cases; mild keeps them in lead sentences.
- **Filler words**: `just` / `really` / `basically` / `actually` / `simply` / `essentially` / `quite` / `rather` / `very`. Drop unconditionally at all levels.
- **Pleasantries**: `sure` / `certainly` / `of course` / `happy to` / `feel free to` / `please`. Drop unconditionally.
- **Hedging on non-directive content**: "you might want to consider" → "consider", "it could be useful to" → "" or "do". Drop only on non-directive prose — directive hedging is the Preserve list's job.
- **Redundant restatements**: "for example, X, Y, or Z" where X already conveys the rule. Keep one example, drop the parade.
- **Parenthetical asides** that do not add directive content. Keep parentheticals that carry hard constraints, file paths, line numbers, or RFC citations.

## Preserve verbatim (overrides the Drop list)

These MUST pass through unchanged. If a Drop-list rule and a Preserve rule conflict, Preserve wins.

- **Directive markers (RFC 2119)**: `must` / `must not` / `MUST` / `MUST NOT` / `shall` / `should` / `SHOULD` / `should not` / `SHOULD NOT` / `may` / `MAY` / `never` / `always` / `do` / `do not` / `don't` — and their original casing. These carry directive polarity; dropping or downcasing one is a compliance bug.
- **Section headers**: any line starting with `#` / `##` / `###` / `####`. Keep verbatim including trailing whitespace.
- **YAML frontmatter**: lines between leading `---` markers. Keep verbatim.
- **Code blocks**: any line inside fenced ` ``` ` blocks or 4-space-indented blocks. Keep verbatim.
- **Inline code**: anything between backticks. Keep verbatim.
- **Numbered / ordered lists**: list items and their numbering. Keep ordering AND content; only compress the prose inside each item per the Drop list.
- **File-path references**: `agents/shared/X.md`, `scripts/hooks/Y.sh`, `src/foo/bar.py:42`. Keep verbatim including the line-number suffix.
- **Worked examples and example dialogues**: any block-level example marked by `**Example**:` / `**Anti-pattern**:` / `**Required pattern**:` / similar. Block-level preserve.
- **RFC / external standard citations**: `RFC 2119`, `arxiv:NNNN.NNNNN`, `intake-NNN`, etc. Keep verbatim.
- **Procedural ordering in prose**: when the source describes a workflow as "first X, then Y, then Z" without using a numbered list, keep the ordering words ("first / then / finally / before / after"). Procedural-ordering loss is a compliance bug at the same severity as polarity loss.

## Disabled clauses (vs vanilla `/caveman`)

- **No persistence clause**. This is one-shot static-text compression, not a runtime style mode. The compressor runs once at authoring time; the persistence clause that vanilla `/caveman` uses to keep the style across a streaming session does not apply.
- **No auto-clarity exception**. The Preserve-verbatim block-level rules above explicitly cover the cases where clarity must win. There is no "the model decides at runtime" escape hatch.

## Levels

Three discrete levels. Each defines target reduction range and Drop-list stringency.

- **mild**: ~20% reduction. Drop pleasantries + filler unconditionally. Drop articles only inside list items, never in lead sentences. Drop redundant restatements when ≥3 alternatives are listed. Hedging removal limited to most overt cases ("you might want to" → "").
- **medium**: ~40% reduction. Drop articles in most positions. Compress hedging more aggressively. Allow paragraph reflow that merges adjacent same-topic sentences when no directive marker spans them.
- **aggressive**: ~60% reduction. Drop articles unless they carry meaning (e.g. "the orchestrator registry" vs "an orchestrator registry"). Compress narrative prose into bullet form where the source uses paragraphs of explanation.

## Verification Gates

### Step 1 — Polarity Preservation
- Evidence: directive marker occurrence count equal between original and compressed, computed via:
  ```bash
  grep -oiE '\b(must|must not|shall|should|may|never|always|do not|don.t)\b' <file> | wc -l
  ```
- Use `-o` (occurrences) not `-c` (matching lines). When compression merges multiple directive sentences onto one line, line-counting under-reports — occurrence-counting is correct.
- Gate: counts match exactly. Any decrease = revert this artifact. Adding markers (over-strengthening directive force) is also a failure — counts must be exactly equal.

### Step 2 — Procedural-Ordering Preservation
- Evidence: ordering words (`first`, `then`, `finally`, `before`, `after`, `next`) count is non-decreasing in compressed vs original for prose-described workflows.
- Gate: count >= original. Numbered lists are out of scope (their order is structural).

### Step 3 — Structure Validator
- Evidence: `python3 .claude/skills/agent-file-architecture/scripts/validate_agents.py` returns 0 (only applicable to top-level `agents/*.md` role files; shared/ files use Step 1+2 gates only).
- Gate: exit 0 for role files. N/A for shared/ overlays.

### Step 4 — Token Reduction Range
- Evidence: `wc -w <original> <compressed>` shows reduction within ±5 percentage points of the level's target.
- Gate: mild 15-25%, medium 35-45%, aggressive 55-65%. Outside the band → re-run with adjusted stringency.

### Step 5 — Human Diff Review
- Evidence: a human reads `diff -u <original> <compressed>` and approves.
- Gate: explicit approval before commit. No auto-commit on this skill.

## Anti-Rationalization

| Excuse | Rebuttal |
|--------|----------|
| "The hedging in 'you might want to consider X' is just filler — drop it." | Only true on non-directive prose. If the surrounding sentence carries a directive (`must` / `should` / `never`), the hedge attaches to the directive and must stay. Polarity Step 1 catches the egregious cases; you must catch the subtle ones. |
| "The compressed file reads cleaner without the procedural ordering words." | Procedural ordering is directive content. "First do X" before "then do Y" is not equivalent to two unordered bullets when X must complete before Y. Preserve. |
| "The validator passed, so the compression is fine." | The structure validator only checks 6 required headers. It does not check polarity, ordering, or token reduction. All 5 verification gates must pass. |
| "I should regenerate at all three levels in one pass." | One file, one level, per skill invocation. Three levels = three invocations + three diff reviews. Polarity profile differs across files. |
| "The source got edited, the compressed artifacts are stale, but they are close enough." | Stale compressed artifacts ARE the failure mode. Either regenerate immediately, or remove the stale artifact and let the model fall back to the source. Stamping git SHA in the compressed-file frontmatter is the canonical drift-management answer. |
| "RFC 2119 lowercase `must` is a verb, not a directive." | RFC 2119 explicitly assigns directive force to lowercase `must` in normative documents. Treat all listed RFC 2119 keywords as directive at all casings. |
