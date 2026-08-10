# Intake merge map — where a removed id went

**Generated. Do not hand-edit** — run
`.claude/skills/research-intake/scripts/resolve_intake_id.py --write-map`.
Source of truth is the `merged_ids` field on each surviving entry.

An intake id is never reused and never renumbered (schema § ID Sequencing), so a merged
id resolves to nothing rather than to the wrong paper. This table is what makes that
recoverable: land on a dead id in an old log, look it up here.

**A reference to a removed id is not automatically wrong.** Historical records naming a
merged id are correct as written, and some name it *because* it was a mis-stamp — the
MI210 speed-campaign handoff cites intake-797 inside a correction saying intake-797 was
the wrong id for KernelBench. Read the context before repointing anything.

| Removed | Resolves to | Title | Merged |
|---|---|---|---|
| `intake-336` | [`intake-315`](intake_index.yaml) | Neural Computer: A New Machine Form Is Emerging (Meta AI) | 2026-08-10 |
| `intake-784` | [`intake-244`](intake_index.yaml) | Meta-Harness: End-to-End Optimization of Model Harnesses | 2026-08-10 |
| `intake-785` | [`intake-772`](intake_index.yaml) | Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents | 2026-08-10 |
| `intake-797` | [`intake-418`](intake_index.yaml) | Externalization in LLM Agents: A Unified Review of Memory, Skills, Pro | 2026-08-10 |
