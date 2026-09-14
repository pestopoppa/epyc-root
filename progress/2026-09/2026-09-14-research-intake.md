# 2026-09-14 — Research intake: ripwire / pd-bridge / 2609.09153 / 2609.05364 / SoL-Pi / GPT-OSS-20B harness search

Session ran in the SHARED CLONE (operator-spawned `/research-intake`, no lane worktree).

## Stages
- **Stage 1** — 6 operator sources (5 URLs + 1 pasted write-up) + 10 expansions → intake-1346…1361 (`stage1-unverified`). No duplicates.
- **Stage 2** — operator selected 12 dives (1346, 1348, 1350–1353, 1355–1360). All `dive-verified`; many claims narrowed. intake-1204 "sibling forks" wording corrected (earendil-works/pi is the renamed badlogic/pi-mono).
- **Stage 2b** — operator selected 5 dive-surfaced sources → intake-1362 (Niklaus results bucket), 1363 (Muse-Glimmer TB2.1 harness grid), 1364 (LARGER), 1365 (SWEzze), 1366 (ContextBench), born dive-verified; 15 others declined and recorded.
- **Stage 3** — plan approved (`/home/node/.claude/plans/sharded-discovering-mist.md`); operator chose "file + fix".
- **Stage 4** — applied.

## Key findings
- ripwire's GitNexus head-to-head (27W/7L/14T) is single-judge and not reproducible from committed artifacts; its LocBench "held-out" slice was partly tuned on. CLAUDE.md GitNexus rule unchanged (human-only path).
- GPT-OSS-20B harness-search post (4.8% → 14.8% held-out TB2.1) is primary-anchored, but the author's own August campaign shows per-patch effects are noise-sized and confounded by a provider rate-limit regime change.
- Harness rank tracks model class (Spearman −0.05 GLM-5.2↔Gemma-4; +0.76 Gemma-4↔Muse-Glimmer-30B).
- ContextBench chosen as the primary zero-decode instrument for DCP discovery; Loc-Bench secondary.

## Handoffs updated (25 new tasks, 6 ticked on merge, 19 open)
- delegation-context-preassembly.md — DCP-10/10a✅/10b/10c/11/12/13, DCP-2 correction, DCP-7 priors, stale P22→RTG-10 pointer
- tool-output-compression.md — TOC-SP-1✅, TOC-SP-2, TOC-SP-3, TOC-RD-1✅, standing no-LLM-summary-of-code rule, anchor fixes, P4e sink absent
- context-folding-progressive.md — CF-PB-1, CF-RX-1✅, :84/:124 corrections, CF-3c re-fetch co-metric
- harness-selection-and-integration.md — HS-14, HS-1f source-level score + HS-1f.1, pi lineage + star-count fixes
- tool-use-eval-contract.md — TU-TC-1✅, TU-GR-1, TU-TM-1, TU-LED-1
- multi-file-coding-completion-capability.md — MF-FIN-1✅, MF-VBS-1, MF-NDG-1, MF-RR-1
- autopilot-continuous-optimization.md — AP-55, AP-56, AP-53 measurement note

## epyc-orchestrator defect fixes (merged to local main `35b05fde`, NOT pushed; main is ahead of origin by 12)
- C1 `1e2a6315` spill footer peek/grep keyword args (+ `suggestions.py` hint templates)
- C2 `b32f683c` malformed tool-call JSON repaired or visibly refused, never `{}`
- C3 `090c63d9` `_REPL_OUTPUT_RE` built from real TOOL_OUTPUT delimiters
- C4 `2bffb45b` dead `fetch_report` advertisement removed
- C5 `57ceb7d5` full specialist report on user-facing delegation returns
- C6 `a2af42ad` skip `worker_summarize` on rescued reports
- C7 `982ca87c` task-root search covers C/C++/Go/Rust/Java
- C8 `118b65e5` MCP compressor redacts; PEM rule covers truncated keys
- C9 `0b261dde` `FINAL('done')` accepted only where the turn's prompt sanctioned it
- Combined branch `intake/20260914-dive-defects` built on origin/main `826008df` (3 --no-ff merges); 1,856 passed / 52 skipped on the merged tree; shared clone main fast-forwarded.

## Residuals / operator items
- Orchestrator main pushed at wrap-up (see Wrap-up below).
- Root `pii_precommit.sh` PEM pattern misses `OPENSSH`/`ED25519` headers and blocks any edit to `tests/unit/test_credential_redaction.py` (pre-existing fake credentials) — filed as **TOC-RD-1a** (operator decision: widen pattern + reviewed fixture allow-list together).
- Handle text still says "Use fetch_report(...)" → **DCP-13a**; delegation-cache hits still return the handle+summary form → **DCP-13b**; refusal echo could count as loop-guard progress → **TU-TC-1a**.
- Worktrees kept (not removed): `/mnt/raid0/llm/worktrees/intake-20260914-{deleg,repl,guard,merge}`.
- Derived-actionables gate: 4 residual tasks filed (DCP-13a, DCP-13b, TU-TC-1a, TOC-RD-1a); all other dive "could/should" items were filed or explicitly declined in the approved plan (Tier D).

## Validation
`validate_intake.sh` exit 0 (1,362 entries) · `index_state.py --check` exit 0 · `vidya cite-check` exit 0 on all touched handoffs.

## Wrap-up (operator-invoked /wrap-up, 2026-09-14)
- Ran from an isolated promotion worktree at root `origin/main` (the shared clone is 277 commits behind and carries peers' uncommitted work); this session's files were copied in after verifying each had an unchanged base on origin.
- **epyc-orchestrator** main pushed via `serialized_push.py --push`: `826008df..35b05fde` (12 commits).
- Index rows refreshed: RTG-10 → DCP-10, RTG-21 → MF-VBS-1, EVL-46 → TU-GR-1. Pruning screen: 0 candidates.
- Wiki compile sweep (11 sources): autonomous-research, benchmark-methodology, context-management, tool-implementation, search-retrieval, agent-architecture + INDEX; `lint_wiki.py` exit 0; cite-check exit 0; manifest advanced with `--touch`.
- Checkbox flips this session: 6 (DCP-10a, TOC-SP-1, TOC-RD-1, CF-RX-1, TU-TC-1, MF-FIN-1); new open tasks: 23 (19 plan tasks + DCP-13a/13b, TU-TC-1a, TOC-RD-1a).
- Agent logging was not active for this operator-spawned session.
