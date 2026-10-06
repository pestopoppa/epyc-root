# Intake re-verification: past dives at risk from the WebFetch-digest read-depth gap

**Scratch**: `/mnt/raid0/llm/tmp/intake-reverify/` · worktrees: `/mnt/raid0/llm/worktrees/intake-reverify-*`

**Status**: active (draft, awaiting owning-session apply)
**Created**: 2026-10-06 (operator-approved with the read-depth fix, commit 4563f8d8e)
**Categories**: knowledge_management, benchmark_methodology

**Why this file exists**: a Stage-2 dive that fetched through WebFetch read a model-summarised digest, not the source, yet was stamped `dive-verified`. The skill is now fixed going forward; this handoff audits the past.

## Background

Root cause, from [`artifacts/intake-depth-audit-20261006/AUDIT.md`](../../artifacts/intake-depth-audit-20261006/AUDIT.md) (2026-10-06):

> SKILL.md:314 "Verify, don't summarise. Read the actual source/code. Quote file:line or the exact passage." is the ONLY read-depth rule. "Primary source" is never defined; no FULL-read requirement. ... Nothing says WebFetch summarises, nothing says curl the PDF + Read pages, nothing says clone repos. ... anchors are "required" in prose, "optional" in schema, unenforced in code, so a run that uses WebFetch drifts to digests silently.

> So a digest-based dive with no anchors passes every gate. The 10-06 entries (1900,1906,1907,1911,1918,1919,1922...) honestly self-report "WebFetch digest ... quotes are digest relays and carry no quote_sha256 anchors; re-pull the PDF before any load-bearing citation" yet are stamped dive-verified.

Incident: 2026-10-06, 9 of 9 dives that day were unanchored WebFetch digests (the 10-03 run was 64/65 anchored). The 10-06 batch was redone against full primary sources (commit 1c5183df9). Fix landed in 4563f8d8e: Stage-2 read-depth contract, `read_depth: FULL|PARTIAL|DIGEST`, anchors required and validator-enforced for entries ingested 2026-10-07 or later. Legacy entries are grandfathered by the validator, so nothing past is re-checked automatically. That is this handoff's job.

Counts (AUDIT): 889 dived, 689 anchored, about 200 unanchored. Depth rose sharply Aug-Sep (anchor rate 11% before intake-913, about 97% after intake-1251), so the risk concentrates in intake-913..1250 and in unanchored entries generally.

## Scope

At risk = `dive-verified` or `dive-overturned` AND any of: (A) empty `claim_anchors`; (B) dive notes mention WebFetch, digest or abs page; (C) no recorded full-read evidence (`read_depth` not FULL/PARTIAL and no read-depth keyword such as PDF, pages, Table, section, line, clone, html, sha in the dive text). Keywords are noisy and used as corroboration only.

Script: `scripts/handoffs/` is not modified; run from the repo root:

```bash
python3 .claude/skills/research-intake/scripts/at_risk_list.py research/intake_index.yaml > /mnt/raid0/llm/tmp/intake-reverify/at_risk.tsv
```

It prints TSV `id, ingested, verification, verdict, flags(A/B/C)` and a summary on stderr. On the 2026-10-06 index (1918 entries) it yields **352 at risk of 889 dived** (A=191, B=100, C=109). Re-run on the current index; the count is the authority, not this line.

## Triage rubric

Score each at-risk entry, then assign one class.

| Signal | Weight |
|---|---|
| Cited as rationale: `python3 scripts/vidya/cli.py cite-check --as-of <ts>` hits, plus `grep -rn "intake-NNN" handoffs wiki docs` | high |
| Gates a live decision or an open handoff task (a `- [ ]` row or decision depends on it) | high |
| Verdict risk: digest-era CONFIRMED / `dive-verified` with a headline number is riskiest; `dive-overturned` is lower (a digest rarely overturns by accident) | high / medium |
| Flags B (explicit digest self-report) | raises to at least medium |
| Source is a repo or paper whose full read is cheap (HTML on arXiv, small repo) | tie-break toward RE-DIVE |
| Not cited, gates nothing, low relevance | low |

Output classes (record reason per entry in the triage table):
- **RE-DIVE**: cited or gating AND (flag B, or A with CONFIRMED verdict). Dive anew under the fixed skill.
- **DEMOTE to stage1-unverified**: uncited, gates nothing, flagged B or A, and not worth a dive. Demotion is an index write (verification field) and goes through the stage machine; never silent.
- **KEEP (with reason)**: full-read evidence exists in notes (pinned SHA, line anchors, sha256 of fetched artifact) even though anchors are absent; or overturned and independently corroborated. Examples seen in the AUDIT sample: intake-1020 and intake-1175 were full reads without anchors.

## Procedure

1. Follow the fixed skill (`.claude/skills/research-intake/SKILL.md`, Stage-2 read-depth contract): curl PDF or HTML to `/mnt/raid0/llm/tmp/intake-reverify/dive-<id>/` one download at a time, `Read` with `pages`, `git clone --depth 1` for repos, record `read_depth`, anchors with `quote_sha256`, and `source_revision`. WebFetch is Stage-1 discovery only.
2. Batches of at most 10 entries per wave; fan out cheap subagents per entry, main reviews.
3. Every finding goes through the research-intake stage machine. **Stage 3 plan approval comes before any handoff edits**; a changed verdict on a cited entry names every citing handoff in the plan.
4. CPU-touching steps (none expected) use `region-lock run --cpu-list 0-95`. No inference, no benchmarks.

## Tasks

- [ ] **IRV-1 — Generate the at-risk list.** Run the script above on current `research/intake_index.yaml`; save TSV and counts to the scratch dir.
- [ ] **IRV-2 — Run cite-check and citation grep.** `cite-check --as-of <ts>` plus `grep` for `intake-NNN` across handoffs, wiki and docs; join onto the TSV as `cited_by`.
- [ ] **IRV-3 — Triage.** Apply the rubric; emit RE-DIVE / DEMOTE / KEEP with a one-line reason each.
- [ ] **IRV-4 — Stage-3 plan for the re-dives.** Plan-mode audit of the RE-DIVE set, operator approval before any handoff edits.
- [ ] **IRV-5 — Re-dive batches.** Waves of at most 10 under the fixed skill; record verdict changes and `dive_corrections`.
- [ ] **IRV-6 — Demotions.** Apply approved DEMOTE rows to the index; run `validate_intake.py` (exit 0) and `cite-check`.
- [ ] **IRV-7 — Final report.** Counts by class, verdict changes, affected handoffs; move this handoff to `completed/` and delete its index row.

## Cost guidance

Cheapest capable model per step (`agents/shared/OPERATING_CONSTRAINTS.md` token-efficiency rules): haiku for IRV-1 and IRV-2 (mechanical); sonnet for dives in IRV-5 and for triage judgment in IRV-3; main reviews and owns the Stage-3 plan. No Fable.
