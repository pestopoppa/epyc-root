# Research Intake Run — ydnlc-20261106

**Source**: https://arxiv.org/html/2611.05306v1 — "You don't need long context" (Belcak et al., NVIDIA).
**Branch**: `intake/ydnlc-20261106` · **Lane**: `/mnt/raid0/llm/worktrees/intake-ydnlc-20261106`
**Operator instruction** (steering seq 1): accept all recommended deep dives for up to three Stage-2 waves.

## Entries

| ID | Source | Wave | Verification |
|---|---|---|---|
| intake-2628 | You don't need long context (2611.05306v1) | 1 | dive-verified |
| intake-2629 | Compact-Bench (2610.31710v2) | 1 | dive-verified |
| intake-2630 | Benchmarks Are Surprisingly Compaction-Friendly (2610.31778v1) | 1 | dive-verified |
| intake-2631 | ARCBench (2611.03223v1) | 1 | dive-verified |
| intake-2632 | transparent-compact (2610.20116v1) | 1 | dive-verified |
| intake-2636 | Governance Decay (2606.22528v2) | 2 | dive-verified |
| intake-2637 | Lost in Context Compaction (2608.11242v2) | 2 | dive-verified |
| intake-2397 | SWE-chat (2604.20779v2) — deepened existing | 2 | dive-verified, PARTIAL → FULL |
| intake-2527 | Execution instability / TRACE (2608.06503v2) — deepened existing | 2 | dive-verified, PARTIAL → FULL |
| intake-2638 | Compaction Laundering (2610.29869v1) | 3 | dive-verified |
| intake-2639 | Guardrail residue (2608.11392v2) | 3 | dive-verified |
| intake-2640 | From Alignment to Access Control (2609.26682v1) | 3 | dive-verified |
| intake-2633/2634/2635 | source-judged compaction, Bud ContextCompact, later-question compaction | — | stage1-unverified (not selected) |

Duplicate re-encounters recorded, not minted: intake-1071 (ACE), intake-2397 (SWE-chat), intake-2527 (TRACE).

## What the run found

- Compaction is safe for **benchmark accuracy** only where ground truth lives outside the transcript, and only for
  strong models. The source's own Appendix D is the counter-result for local open-weight models.
- The project-relevant risk is **governance**, not task score: retained rules are violated 2.6× more often,
  soft policies decay 8.3× more than hard norms, open-weight compactors retain 6% of side constraints, and a
  text-presence check is not a safety check.
- **Live exposure**: OpenCode's compaction serializer interpolates role labels unescaped and re-injects the summary
  as a user-role message. The paper measures 87-100% laundering across five harnesses; our build (v2.2.5) is
  untested and must be probed, not assumed patched.
- Counterweight: the orchestrator summary path is structurally safer (structured previews, control-token
  neutralisation, summary appended to the prompt) but has no regression test.

## Dives and their artifacts

Wave 1: `intake-2628-*.md`, `intake-2629-*.md`, `intake-2630-*.md`, `intake-2631-*.md`, `intake-2632-*.md`.
Wave 2: `intake-2636-*.md`, `intake-2637-*.md`.
Wave 3: `intake-2638-*.md`, `intake-2639-*.md`, `intake-2640-*.md`.
Plan: `PLAN.md` (Stage 3, awaiting approval). Source HTML/PDF and extracts live under
`/mnt/raid0/llm/tmp/dive-<id>/`.

## Validator status

`bash scripts/validate/validate_intake.sh` exits 1 on `origin/main` **before this intake**: all 5,877 errors are
one pre-existing class, `invalid committed fold mapping: invalid fold destination
handoffs/completed/mi210-serving-program.md`, introduced when `mi210-serving-program` was archived (commit
`bcad0506a`) while `docs/design/backlog-refactor-2026-11/fold-list-{1a,1b}.json` kept `handoffs/completed/...`
destinations. The same error fires on `cross-reference-map` lines this intake never touched. The appended entries
add no other error class, and the Stage-3 proposed-payload check
(`--plan-file ... --session-file ...`) reports **zero plan/session errors**.

The fold-mapping defect is recorded in `.research-session.json` under `pre_existing_validator_failure`; it is not
this lane's artifact to fix silently, but it must be repaired before a green validator gate can be claimed.
