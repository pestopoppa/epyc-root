# 2026-09-16 — sub-vidya-wire (belief-kernel ingest wiring)

Zero-inference subagent. Worktree `/mnt/raid0/llm/worktrees/sub-vidya-wire`, branch
`sub/vidya-wire-20260916`, based on origin/main `c57b0b6c`. Not merged or pushed.

## Commits

- `843cac41`: ports the AP-55 `infra_fingerprint`/`comparability` change (autopilot_journal.py) and
  the RTG-35 foreign-process gate (contention_matrix.py), with their tests. Before this they existed
  only uncommitted in /workspace; both producers are on orchestrator main. 23 tests pass, 1 skipped.
- `295b0cb1`: `scripts/vidya/ingest_sources.py` and 15 new `cli.py ingest` names. KB-RAG query
  length and SC75 come first; the other 13 are every file-shaped adapter that had no ingest name.
  `tests/vidya/test_ingest_sources.py`: 22 pass (end to end through the CLI; ledger grade ==
  `claim_tuple.grade()`).
- `af232216`: handoff VB-WIRE section with the status table, the SC76 collision fix
  (VGPR -> SC84, reviewer -> SC83), README source rows plus a new section, and the refreshed
  master rollup.

Full `tests/vidya`: 1197 passed. The remaining failures are pre-existing and unrelated: 1 failure
plus 12 errors in `test_autokernel_serving_feedback.py`, from `KeyError: EPYC_RESEARCH_ROOT`; the
same happens on a pristine tree. GitNexus index is at `d372c95` (the /workspace HEAD, 388 commits
behind origin/main). The impact checks on `cmd_ingest`, `validate_block` and `as_record` were all LOW.

Real-corpus dry runs:
- contention-gate: 382 rows.
- fanout-outcome: 5 rows.
- sealed-manifest: 6 rows; 8 manifests are unsealed and declined.
- contention-matrix: 6 runs, all pre-hook and declined.
- inf70-arms: 0 sidecars. The harness1 arm scripts do not call the capture yet (VB-WIRE-2).
- autopilot-journal: 0 measured rows.

## SC id collision

On origin/main SC76 was already allocated twice: S3-VID-02 (claim_anchor re-verifier) and
VB-VGPR-STATIC. Today's reviewer FA-rate filing in /workspace made a third. S3-VID-02 keeps SC76.
VB-VGPR-STATIC becomes **SC84** and the reviewer filing becomes **SC83**. SC82 is taken on
`sub/misc-fixes-root-20260916`.

Still stale, for the owners to fix:
- /workspace `vidya-belief-substrate-program.md` and adapters/README still say SC76 for the
  reviewer filing.
- `research/intake_index.yaml` (intake-1398 handoffs_updated) still says "SC76" for VGPR. This is
  an intake entry, so it can only be prepared here.
- progress/2026-09-15-vgpr-compiler-ab.md is historical and was left alone.

## MHS-5 verdict — prepared (NOT applied) amendment to research/intake_index.yaml, entry intake-1323

The owning session applies this: under ruling (b), a subagent may prepare an intake-entry edit but
may not apply it. Apply it after orchestrator `sub/autopilot-safety-20260916` (commit 4f28e6c3)
merges, so that the evidence commit is reachable from main.

### Why the refutation does not attach to key_claims[4]

intake-1323 has 5 key_claims (00-04), and claim 04 is the Section 3.1 "same-batch, transductive
objective" scope boundary. The MHS-5 corpus does not touch it. MHS-4 in
promptforge-mutation-safety-contract.md cites the anti-override prior as `intake-1323#04`, which is a
mis-anchor. The statement that MHS-5 refutes is not a key claim. It is MHS-4's generalization of
dive_corrections item (6): "the two rewrite_action WebShop patches are exactly the -68 / -71
catastrophes." Item (6) itself still holds for WebShop. Recording `effect: overturned` on claim 04
would therefore refute a true, anchored claim.

The same handoff also cites `#07` and `#09`, and eval-tower-verification.md cites `#06`. All three
are out of range for a 5-claim entry, so their numbering does not follow the index.
autopilot-continuous-optimization.md cites `#03`, which is in range. SC80 exists to make out-of-range indices `dangling` instead of `unknown`.

### 1. Append to `dive_corrections` (the correction_recorded channel; the correction queue adjudicates it)

 (13) 2026-09-16 LOCAL EVIDENCE (orchestrator 4f28e6c3, `orchestration/datasets/harness_r1_heldout_effect_corpus.json`, sha256 09ae7365febc11e0627a26dccfeb500a712c498e9de55a9034578cb301efbc71, derived from upstream examples/heldout_generalization @411bb5489ada, results sha256 cf4ce8c0...): item (6) NARROWED. The two rewrite_action patches are the worst WebShop regressions, but the single worst valid patch over all 23 is a hint-only CONSTRAIN patch (deepseek-v4-pro, ALFWorld, seed 20260721, -83/490 = -16.9 pp). The generalization "every catastrophic held-out regression came from an override patch" (MHS-4 rationale) is REFUTED on this corpus. The ordering survives: REPLACE is 4/4 negative, mean -8.4 pp, rescue:regression 0.21; CONSTRAIN is n=19, mean +3.9 pp, 1.65, with 4 negative.

### 2. Add to `claim_corrections`

  - claim_index: 4
    effect: unaffected
    note: '2026-09-16 MHS-5 (orchestrator 4f28e6c3): the refuted anti-override generalization is not this claim. MHS-4 cited it as #04 by mis-anchor. The transductive-scope claim is untouched.'

Claims 0-3 are also unaffected by item (13). The correction queue records them, as in step 3.

### 3. After the merge and the index edit, run

    python3 scripts/vidya/cli.py ingest intake --as-of <UTC now>
    python3 scripts/vidya/cli.py corrections --as-of <UTC now>                 # item (13) appears
    python3 scripts/vidya/correction_queue.py worksheet --as-of <UTC now> --out <ws.yaml>
    #   set claims 00-04 of intake-1323 to `unaffected` in <ws.yaml>, then:
    python3 scripts/vidya/correction_queue.py emit --worksheet <ws.yaml> --at <UTC now>
    python3 scripts/vidya/cli.py cite-check --as-of <UTC now>

### 4. Handoff fix (owner: the promptforge-mutation-safety-contract session)

MHS-4 should cite `intake-1323#record` plus orchestrator 4f28e6c3. Its text should read "the
REPLACE-before-CONSTRAIN ordering holds on the 23-patch corpus; the worst single patch is CONSTRAIN
(-16.9 pp), so the prior ranks risk and does not certify safety."

### cite-check (2026-09-16T10:45Z, live ledger /workspace/.vidya/ledger.jsonl, last written 2026-08-28)

intake-1323 has never been ingested (it was ingested into the index on 2026-09-07), so every
citation of it resolves `unknown` today and none flags:
- autopilot-continuous-optimization.md: `intake-1323` (bare), `#03`
- eval-tower-verification.md: `#06`
- promptforge-mutation-safety-contract.md: `#00 #01 #02 #04 #07 #09`, `#record`
- harness-selection-and-integration.md, wiki/agent-architecture.md: `#record` (never graded)
- wiki/benchmark-methodology.md: `intake-1323` (bare)

If claim 04 were wrongly marked overturned, the bare `intake-1323` citations (autopilot-continuous-
optimization.md, wiki/benchmark-methodology.md) and promptforge `#04` would flag `overturned`. With
the prepared amendment (no overturned effect), nothing flags. Item (13) only raises `review` on the
entry's claims until the queue adjudicates it.

## Review fixes (Fable MERGE-AFTER-FIX)

- `c99f5ade` merges origin/main `8abf6984` and resolves three conflicts:
  - the master rollup was regenerated;
  - the handoff keeps SC84, SC83 and origin's SC82, and only S3-VID-02 still holds SC76;
  - the README keeps origin's rows and adds the ingest prefixes.
- `e04c44a2`:
  - `autopilot_journal.py` now carries AP-54 `eval_fence`, and its test is ported.
  - `kb_rag_query_length.py` declares `AUTHORITY` explicitly, and the dispatcher refuses an adapter
    that declares none.
  - `ingest autopilot-journal --path <shard>` now works, and a foreign file is declined.
  - `--limit` is now a global row limit.
- Checks:
  - `tests/vidya`: 1201 passed, 80 skipped.
  - `index_state.py --check`: 0 problems.
  - cite-check over the three edited docs flags 3 `overturned` citations (intake-896, intake-896#03,
    intake-1245), all in adapters/README.md. The origin/main README flags the same 3, so none come
    from this branch.
