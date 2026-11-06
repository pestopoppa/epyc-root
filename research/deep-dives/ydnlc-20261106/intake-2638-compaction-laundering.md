# intake-2638 — Compaction Laundering (arXiv 2610.29869v1)

**Dive date**: 2026-11-06 · **Read depth**: FULL (paper + public code + local source read) · **Revision**: v1 (2026-10-21)

## The result

Harnesses that flatten a typed conversation into one role-labelled string before summarisation destroy provenance
**before the summariser runs**. A `[User]:` label embedded in anything the agent reads becomes a genuine user turn
after compaction. Forged approvals launder in **87–100%** of trials across pi, opencode, Cline, Aider and OpenHands;
four role-typed harnesses (Codex, Gemini CLI, Qwen Code, Continue) are **0%** because there is no in-band marker to
forge. Laundering is flat at 100% out to ~908K tokens; executed consequences attenuate to ~20–40%. A pre-compaction
audit catches it every time; compaction erases the audit and promotes the forgery.

Minimal fix: **escape role labels in tool content before flattening**, or keep roles typed. A post-summary
provenance-contrast check catches 77% with 2% collateral.

## Local exposure (must be proven by probe, not assumed)

The dive read both local OpenCode compaction modules: `serialize()` interpolates `[User]:` / `[Tool result]:` with
no escaping, and `to-llm-message` re-injects the whole summary as a **user-role** message. Installed build is
v2.2.5; the paper tested 1.18.15–1.18.21, so version range is not the test — the serializer is.

The orchestrator summary path is structurally safer: it ingests structured `TurnRecord` previews, neutralises
control tokens, and appends the summary to the prompt rather than a user turn. Residual risk is the weaker
provenance-erasure primitive only.

## Actionables

| Action | Owner | Disposition |
|---|---|---|
| Probe the OpenCode build: place a forged `[User]:` approval in a readable file, `/compact`, dump the summary | harness-program.md (UFH-15) | immediate |
| Decide local patch: escape role labels or restore typed array; send upstream advisory | harness-program.md | probe→trigger |
| Regression test that a hostile tool output cannot produce an un-neutralised role boundary in the orchestrator prompt | context-and-token-economy.md | immediate |
| Adopt provenance-contrast demotion as an optional post-summary check | context-and-token-economy.md | knowledge-only |

## Surfaced

`pixee/flat-compaction-attacks-oct-2027@9ce87b7` (disclosure + per-run data); Gemini CLI anti-injection ablation;
Sleeper/Straiker memory-poisoning lineage.
