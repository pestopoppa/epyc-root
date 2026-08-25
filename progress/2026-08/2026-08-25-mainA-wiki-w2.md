# 2026-08-25 — mainA wiki compile w2 (eval/safety/research)

## Task

Research subagent preparation for the wrap-up wiki sweep: compile drifted sources into prepared
updates for `wiki/benchmark-methodology.md`, `wiki/safety.md`, `wiki/autonomous-research.md`.
PREPARE only — no wiki edits, no commits (main thread applies). Output: `/tmp/wiki-w2.md`.

## What was done

1. Read all three pages fully (structure: header block → newest Compiled Updates → Summary/Key
   Findings → Source References).
2. Read the drifted sources and identified what actually changed since the 2026-08-23-evening sweep
   (git-log-verified per file):
   - **tool-use-eval-contract.md** (2026-08-25): TU-DTAP-1 DONE — 18-case Apache-2.0 DTAP subset +
     disposable stdlib-only runner (typed 8-set outcomes, immutable SHA-256 trace replay, Wilson CIs,
     target-disjoint attack payloads, 66/66 tests, zero inference); TU-DTAP-2 filed (live-model,
     inference-gated).
   - **repo-readiness-scorer.md** (2026-08-25): root L5.self_optimizing_loop closed via vidya-loop
     detector (queue 13→6, guardrail test-pinned); PII-gate failure surfaced (candidate_eval_gate.sh
     red since ~2026-08-03, AKIAIOSFODNN7EXAMPLE allowlist drift).
   - **frontier-f1** (COMPLETE 10/10, 2026-08-23), **frontier-f6** (part-one post on llama.cpp #27442
     went out; part two G1-blocked), **frontier-f4** (EVL-26 restic backend + operator target
     rejection; W2/W3 unchecked; T0 now 8.21 GiB).
   - Reviewer-plane handoffs (2026-08-25): already compiled in benchmark-methodology.md bottom
     section (commit a9b02275) — excluded to avoid duplication.
   - Deep-dives + remaining active/completed handoffs: only EVL-32 citation-redirect / status-hygiene
     commits since the last sweep — no new findings.

3. Wrote prepared markdown to `/tmp/wiki-w2.md`:
   - benchmark-methodology.md: 1 new section (TU-DTAP-1 + EVL-38 L5 closeout/PII gate), header line
     update. 4 source references.
   - safety.md: 1 new Key Findings subsection (2 bullets: DTAP fixture + PII drift), 1 Open Question
     bullet, 2 Source Reference entries, header update. Sources 8→10.
   - autonomous-research.md: 1 new section (vidya L5 closeout + F1 complete + F6 post + F4 backup
     attempt), header line update. 5 source references.
   - Deliberate exclusions listed with reasons (reviewer-plane duplication, knowledge-management /
     agent-architecture boundary, redirect-only sources, 2026-08-23-operator.md scope).

## Boundaries honored

- No wiki file edited; no commits; no handoff/index edits; agent-architecture.md and
  knowledge-management.md untouched (other session's in-flight MM state).
- Only writes: /tmp/wiki-w2.md, this progress file, agent audit log.

## Next action (main thread)

Apply the prepared sections per /tmp/wiki-w2.md, update the three headers, run project-wiki lint +
`--check-manifest`, then commit.
