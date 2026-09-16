# 2026-09-16 — sub-tooling (harness + KB tooling subagent, zero-inference)

Worktrees: root `/mnt/raid0/llm/worktrees/sub-tooling-root` (branch `sub/tooling-root-20260916`),
orchestrator `/mnt/raid0/llm/worktrees/sub-tooling-orch` (branch `sub/tooling-orch-20260916`).
Nothing merged or pushed.

## Task 1 — OP-34 scoped `--touch` (PROPOSAL branch)

Commit `7cfc4846` on `sub/tooling-root-20260916`.
`.claude/skills/project-wiki/scripts/compile_sources.py`: new `parse_touch_scope()` and
`refresh_tracked_manifest_scoped()`. `--touch` is now `nargs="?"` + `action="append"`:

- bare `--touch` (no `--type`) → unchanged: whole-manifest regeneration + `.last_compile` advance.
- `--touch SCOPE` (repeatable or comma-separated; a configured source type, a file, a directory
  prefix, or an fnmatch glob) and `--type T --touch` → only in-scope entries advance
  (adds, changes and removals). Out-of-scope entries are carried over unchanged, so uncompiled
  deltas stay visible. `.last_compile` and the manifest's `last_compile` are NOT advanced. The
  applied scope and the added/changed/removed counts are recorded under `last_touch`. A scope
  token that matches no saved or current source exits 1, and so does a path outside the project.

Tests: `tests/skills/test_project_wiki_compile_sources.py`, 7 new tests, 21/21 pass.
GitNexus: `gitnexus impact refresh_tracked_manifest --repo epyc-root` returns "not found"
(`.claude/skills` scripts are not in the graph), so risk is UNKNOWN from the tool. Callers were
derived structurally instead: `main()` in the same file, `agents/commands/wrap-up.md` Step 7
(bare `--touch`, unchanged) and `project-wiki/SKILL.md` Step 5. The blast radius is LOW.

### OP-34 decision package

**Decision:** how should a *partial* wiki compile advance the shared watermark?

| Option | What it does | Tradeoffs |
|---|---|---|
| A. Adopt the scoped touch (this branch) | Partial compiles advance only what they compiled. Bare `--touch` is unchanged. | + Removes the incentive to defer partial compiles, which made the deferral look like a backlog.<br>+ Two lanes compiling disjoint scopes no longer clobber each other.<br>− `--type T --touch` changes meaning: it used to ignore `--type` and touch everything.<br>− `.last_compile` now lags after scoped-only compiles. It is display-only, because selection is by content hash. |
| B. Accept all-or-nothing | Keep today's `--touch`. Document that only a full-delta compile may touch. | + Zero change.<br>− The structural gap stays open, and partial compiles keep being deferred. |
| C. Scoped touch, but explicit scope only | Same as A, except `--type` never scopes `--touch`. | + No change to the meaning of any existing flag combination.<br>− Keeps a footgun: `--type research --touch` silently touches the whole fleet. |

**Recommendation: A.** The old `--type T --touch` behaviour is the exact failure OP-34 names, and
no caller in the repo uses that combination (the wrap-up uses bare `--touch`). If A is adopted:

1. Merge `sub/tooling-root-20260916`.
2. Amend `agents/commands/wrap-up.md` Step 7 so a partial compile runs `--touch <scope>`.
3. Lift BLOCKER 2 in `docs/design/inf70-close-out-20260908/WIKI-DRAFT.md`.

## Task 2 — TOC-SP-2 exact recall for spilled output

Commit `af89c864` on epyc-orchestrator branch `sub/tooling-orch-20260916`. Files: `src/graph/file_artifacts.py`,
`src/repl_environment/file_exploration.py`, `environment.py` (Protocol stub signature only) and
`tests/unit/test_output_spill.py`.

- `peek` now takes `offset` and reads with `newline=""`.
- The spill excerpt is head + tail. The marker between them is an executable exact-span `peek(...)` call.
- Spill names are content-hashed and never overwritten.
- A test proves a verbatim legacy `peek(99999, file_path="..._t3.txt")` pointer still resolves.
- Test results: 50/50 across `test_output_spill`, `test_repl_file_exploration` and `test_repl_spill_output`. A wider
  `-k "spill or peek or exploration ..."` run gave 163 passed and 9 skipped.
- Handoff box ticked with evidence.
- Follow-up for the owner: `src/prompts/root_lm_system.txt` still documents `peek(n=500)` only. I left it alone
  because a prompt edit touches prompt determinism.

## Task 3 — KB-RAG H2 + C7, PREFIX-1 verification

The code lives in **epyc-orchestrator** (`src/retrieval/`, `src/repl_environment/code_search.py`).

- **H2**, `32336445` (orchestrator branch):
  - `colbert_encoder.count_tokens()` tokenizes on a private copy with no truncation and no padding. The
    shared tokenizer is untouched.
  - `kb_rag.query()` appends one untruncated count per query to `data/kb_rag/telemetry/query_lengths.jsonl`.
    `KB_RAG_QUERY_LENGTH_LOG` redirects it, and `off` disables it. The query text is never logged.
  - New `src/retrieval/kb_rag_query_telemetry.py` and `scripts/kb_rag/query_length_report.py`, which reports
    p50, p95, max and the over-cap rate per (encoder, cap, convention) group. An empty log reads "UNKNOWN,
    not 0 %".
  - `tests/conftest.py` pins the log off for the whole suite.
  - Tests: 15 new, all pass. Retrieval suites: 62 passed.
  - Caveat: the existing test `test_prefixes_are_single_trained_tokens_in_the_real_tokenizer` ran inside
    that selection, and it calls `ensure_loaded()`, which creates an ONNX session. That is a model load, not
    an encode. I deselected the tests that call `encode()` on the real model.
- **Belief kernel:** the write-side rows are in the report as `belief_measurements`. The root adapter is
  `039a4f3b`, `scripts/vidya/adapters/kb_rag_query_length.py`: 12 tests pass and 1 skips (the live-producer
  guard, which passes when run against the branch). Also added the README row and VB-KBRAG-QLEN in the vidya
  program. `cli.py ingest` is not wired yet (VB-KBRAG-QLEN-R).
- **C7**, `51b30f5e` (orchestrator branch): the :8089 docstring now names GTE-ModernColBERT-v1, matching
  `launch_manifest.yaml`. The same stale name was also fixed in both `scripts/nextplaid` scripts.
  `test_code_search`: 30/30.
- **PREFIX-1** verified and ticked in `colbert-reranker-web-research.md`:
  - `fe55b228` and `f876d989` are both on orchestrator `main`.
  - The live `index-qd-v1` catalog, opened read-only, is stamped `qd-v1` and holds 29,611 chunks. Its
    stamp time is 2026-08-12T21:32:15Z.

## Task 4 — security-review skill: GATE-0, refutation, dedup

- Root commit `affa8f9d` (`.claude/skills/security-review/SKILL.md`, `.claude/commands/security-review.md`).
- New stage order:
  1. Discovery. Each candidate now records a path, a line range, `cwes[]` and a category.
  2. Dedup, before any validation. The key is a normalised path, overlapping line ranges and CWE relatedness
     (identical or parent/child, ten pillars excluded). Merges follow a stable order and are listed.
  3. GATE-0 production reachability. An unreachable candidate stops here, with evidence and no severity.
  4. Exploit gates 1–8.
  5. Mandatory refutation, checked against the code, before CONFIRMED.
- The finding schema gains Class, Reachability and Refutation lines.
- All three handoff boxes are ticked with evidence.
- GitNexus: the skill is markdown, so impact analysis does not apply (there are no code symbols).
- **Overlap for the main session:** the handoff's RA-9 items (dual-gold schema and gold-sanity gate) are
  already built once, in `reviewer-typed-artifacts.md` RA-9, on orchestrator `sub/reviewer-artifacts-20260916`
  @ `e242a156`. RA-12's envelope is on the same branch. I did not build a second schema; `SKILL.md` points at
  RA-9's `gold_annotation.schema.json` and `gold_sanity.run_gate`, which only resolve once that branch merges.
- The dedup is written as reviewer prose, not a coded matcher. benchmrk's five-tier scored matcher was not
  ported.

## Branches (nothing merged or pushed)

- root `sub/tooling-root-20260916`: `7cfc4846` (OP-34 PROPOSAL), `039a4f3b` (vidya adapter), `affa8f9d` (security-review)
- orchestrator `sub/tooling-orch-20260916`: `af89c864` (TOC-SP-2), `32336445` (H2), `51b30f5e` (C7)
- Uncommitted /workspace docs for the main session to commit:
  - `handoffs/active/tool-output-compression.md` (SP-2)
  - `internal-kb-rag.md` (H2, C7)
  - `colbert-reranker-web-research.md` (PREFIX-1)
  - `security-review-skill.md` (3 boxes)
  - `vidya-belief-substrate-program.md` (VB-KBRAG-QLEN)
  - `scripts/vidya/adapters/README.md` (one row)
  - this progress file
