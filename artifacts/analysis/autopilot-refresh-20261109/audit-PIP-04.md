# Audit PIP-04 (knowledge-pipelines.md), 2026-11-09, read-only

Handoff last edited 2026-11-07 20:03Z (888355f48). Everything below happened after or was never recorded.

## Box table (13 open boxes; line numbers are hints, text is identity)

| # | Line | Box | Class | Evidence / what is wrong or missing |
|---|---|---|---|---|
| 1 | 702 | KB-GS-1 four-arm retrieval A/B | STILL-VALID, UNDERSPECIFIED, DOABLE-DURING-HOLD | Premise got stronger: the "ColBERT as deployed" arm is currently broken and index is stale (see finding 1); the staleness arm now has a live data point. Needs: which index (qd-v2 rebuild) is arm A, how the 200-commit drift is dated, who builds ground truth. Backlog tool already tags it [cpu]. No Autopilot dependency. |
| 2 | 1699 | G14 re-export Reason-mxbai-colbert-v0-32m | ALREADY-DONE (export) + STILL-VALID (install) | Row pip04-g14-reason32m-reexport-r2-20261107 ran, rc0 20:52Z 11-07, filed PASS 11-08 (filing-done/*.verdict.json): onnx_config.json written, embedding_dim=128, candidate sha 3e5657a2. Verdict itself says box stays open for the reviewed install into /mnt/raid0/llm/models/reason-mxbai-colbert-v0-32m-onnx-int8 (that dir still has no onnx_config.json, checked). Box text still says "compute-gated / Python 3.10-3.12 venv must exist" = stale. Value is weakened: operator "Keep GTE" 11-07 and seed "Keep web_research_rerank disabled" (operator_seed_strategies.yaml:~629). DOABLE-DURING-HOLD (file copy + parity check, no inference). |
| 3 | 1931 | PIP02-PHASEC-ENGLISH-RUN (755 pages) | STALE-PREMISE | R36 rebuild decision (line 1934) fixed scope: 690 pages PROTECTED_SCOPE_UNKNOWN permanent, never redrawn; only 65 candidate pages eligible. R36 ran: out/results.jsonl final record 2026-11-08T16:51:02Z, pages_done 65/65, paired 65, labelled "operational/diagnostic observation, not a Phase D gate verdict": ODL table TEDS 0.265 (struct 0.417), Paddle 0.910 (0.971), n tables 52. Grant pip02-r36-english-run-20261107b rc0; first grant ...-20261107 ended rc1 22:22Z 11-07. Box still says 755 pages, n=665. Not recorded in handoff. |
| 4 | 1932 | PIP02-PHASEC-CUSTODY-20261101 safe legacy cutover | STALE-PREMISE | "Legacy custody stack RETIRED in favour of v3 keeper custody" (line 1934, e783b4e09). Legacy writer drain / shard lock steps describe the retired stack. Close as superseded with pointer to the keeper rebuild. |
| 5 | 1955 | Decide the table path (ODL / ODL+Paddle / Paddle wholesale) | UNDERSPECIFIED | Gate is "English-only table TEDS" at 755 pages; achievable evidence is now n=65 pages / 52 GT tables. Needs an operator-ratified rule for a reduced-n result (P-DOCPARSE-1 covers LiteParse vs ODL, not this). Operator decision package, not agent work. Everything else about the evidence is present. |
| 6 | 2513 | Parser-quality comparison (LightOnOCR vs docling etc., 200 PDFs) | STALE-PREMISE / partly ALREADY-DONE | Arms narrowed: pdftotext, legacy_router, ODL, LiteParse already run on the 200 PDFs (r2, below). docling, marker, LightOnOCR, ODL hybrid arms were never in r2. Text should be rewritten to the remaining arms. Needs inference (GPU/CPU model arms) via normal grants, not Autopilot. |
| 7 | 2518 | Make ODL-013 decision-capable | ALREADY-DONE (execution) / STALE text | r2 ran (grants ...complete 20:59Z 11-07), filed 11-08: 200 docs, 0 failed, LiteParse-ODL diff +0.0385 CI [0.0176,0.0614] but LiteParse median 676.9 ms > ODL 237.2 ms so ADOPT latency clause fails: NO_DECISION_DEFAULT_UNCHANGED. P-DOCPARSE-1 was ratified 2026-11-08 (artifacts/operator/ratify_p_docparse_1_20261108.json, commit 4c6565a27; MEASUREMENT.md:82,358; measurement/protocols/quality-eval.md:289) with effect "ODL-013 r2 is a formal NO DECISION; routing default unchanged". Box and index row still say "ratification pending". Remaining real step: copy durable hashes/raw outputs in-repo (filing said not closed). Also: legacy_router == pdftotext, 43 docs flagged needs_ocr, so the OCR leg was not exercised. |
| 8 | 2535 | Route complex/dense-table/scanned away from LiteParse | UNDERSPECIFIED | Carries its own "[too-big...]" tag; a routing policy with no done criterion. Given the NO_DECISION and unchanged default it has no trigger. Re-file after a real routing change (same stance as the declined ODL-011 rows). |
| 9 | 2543 | P2 Unlimited-OCR single-pass arm (preserve full-MHA, Q5_K_M+, lm_head>=Q8_0, no R-SWA PR #24975 in prod kernel) | UNDERSPECIFIED | A guard list, not a doable step. R-SWA clause is policy-consistent with v10 freeze (CLAUDE.md). Merge into 2545/2547 as acceptance constraints and tick or delete. |
| 10 | 2545 | Canonical Unlimited-OCR profile fresh matched A/B | ALREADY-DONE (run) / needs adjudication | Row pip04-unlimited-ocr18-paired-r2-20261107 ran 20:33Z 11-07, filed PASS 11-08: 2 profiles x 18 pages = 36 records, 0 unknown, 0 scorer fallbacks. Original scorer text edit 0.359 / TEDS 0.0120 / RO 0.238; canonical 0.297 / 0.0114 / 0.173. Filing deliberately did not tick: digest, linkage/residency, latency, cleanup receipts and A/B adjudication unverified. Scratch dir is gone from /mnt/raid0/llm/tmp (no vault archive found for this id, only g14, r36-revival), so the "data are in run/" evidence needs locating. Handoff_task anchor in the filing is :2540 (rot). |
| 11 | 2547 | Run and score the 18-page OmniDocBench demo | ALREADY-DONE (same run) | Same row covers it per box text. Stale text "only after an inference grant". |
| 12 | 2794 | SX-6 swap default | STALE-PREMISE (framing) / STILL-VALID (measurement) | Code default already ON: src/tools/web/search.py:31 (`ORCHESTRATOR_SEARXNG_DEFAULT` default "1"). Box title "swap default" is done; the open item is the sentinel measurement, which needs the stack to bring up SearXNG (:8888 not served). Trigger is stack lifecycle, not Autopilot. Draft spec exists /mnt/raid0/llm/tmp/pip04-rows/pip04-sx6-searxng-sentinel.spec.json but its driver script is unwritten (writing it is DOABLE-DURING-HOLD). Text still says "Gated on AR-3 warmup trial quality data / Post-AR-3": that gate is the Autopilot HOLD only in name; the measurement does not need Autopilot. Retitle to "SX-6 sentinel measurement". |
| 13 | 3017 | SLIDERS 0.4 gate decision | STILL-VALID, DOABLE-DURING-HOLD | Operator answered "evaluate now, low-priority filler" 11-07. data/sliders_validation/ does not exist in root or orchestrator; scratch clone exists at /mnt/raid0/llm/scratch/sliders (cloned 11-02), so 0.1 may be partly done but nothing is recorded. Final CPU Coder-30B filler row is a normal grant; 0.1-0.3 are non-inference. |

Counts (primary class, "ALREADY-DONE (x)/needs y" counted as ALREADY-DONE): STILL-VALID 3 (1, 2 install part, 13), STALE-PREMISE 4 (3, 4, 6, 12), ALREADY-DONE 4 (7, 10, 11, plus 2 export part, counted STILL-VALID above), UNDERSPECIFIED 3 (5, 8, 9), NEEDS-AUTOPILOT-RUN 0. Strict tally by first label: STILL-VALID 2 (1,13), STALE-PREMISE 4 (3,4,6,12), ALREADY-DONE 4 (2,7,10,11), UNDERSPECIFIED 3 (5,8,9). That is 13.

## Next action (index row) check

"Fix PIP02-R36-DEVNULL-FENCE, republish R36; file ODL-013/G14/OCR r2 rows; operator ratifies P-DOCPARSE-1 annex"

- Fix fence: done 11-07 (8b3706f3b, ticked [x] at line 1936).
- Republish R36: done; ran 11-08, 65 pages.
- File ODL-013/G14/OCR r2 rows: all three filed 11-08 10:37Z (filing-done/*.FILED).
- Ratify P-DOCPARSE-1: ratified 11-08 (4c6565a27).
The whole next-action is ALREADY-DONE. The real next action is: (1) repair the KB index (finding 1), (2) tick/close boxes 7, 10, 11, 2, (3) rescope 3/4/5, (4) install G14 candidate.

## Findings

1. CRITICAL: the KB RAG index is both stale and write/query-broken. colbert_encoder.PREFIX_CONVENTION was bumped "qd-v1" to "qd-v2" in orchestrator 7d92b1a8 (2026-10-31, "qd-v1 stores must be rebuilt in a fresh path"). Live store data/kb_rag/index-qd-v1/catalog.sqlite index_meta still says prefix_convention=qd-v1 (stamped 2026-08-12). kb_rag._roles_for_convention raises ValueError for it (kb_rag.py:327-337), called at :590 (build), :756 (update_files), :949 (query). So `kb_rag.query` and every post-commit update fail. logs/kb_rag_update.log has 2,156 such ValueErrors (first near line 79237) plus sqlite "database is locked" from kb_catalog_dependency.py:137; the hook swallows them ("non-fatal"). Newest chunk mtime in the index is 2026-10-31T08:30Z, 9 days ago. The handoff never mentions qd-v2 (grep: 0 hits); line 1642-1644 asserts qd-v1 as the live state.
2. Coverage did not survive folding. Index holds 29,274 chunks / 1,600 files. 26 of 38 current handoffs/active/*.md are absent, including knowledge-pipelines.md itself and every domain-program file created by the 11-02/03 fold. 7 indexed paths no longer exist on disk (e.g. handoffs/active/v7-promotion.md, routing-truth-restoration.md). 550 handoff .md files are newer than the index. Wiki is fine (31 of 32). The catalog_dependency row (remove_files, 2026-11-09T12:35Z) shows an update did land a removal path today with stored_identity prefix_convention qd-v1 and loaded_identity null, so the index never passes its own identity check. Inference: kb-search skill text still claims "~53 active handoffs / 24 wiki articles".
3. Three overnight rows ran and were filed with no handoff update (boxes 2, 7, 10, 11) and R36 produced results with no handoff update (box 3). The index row, "next action", and a session reading only the handoff will redo finished work.
4. Scope drift in Phase C: boxes 3/4/5 are written for 755 pages/legacy custody; reality is 65 pages/keeper custody. The 65-page result (Paddle TEDS 0.910 vs ODL 0.265) is the first table evidence and is labelled observation, not a Phase D verdict. Box 5's decision gate needs an operator-ratified reduced-n rule.
5. Anchor rot: BACKLOG-handoff-sliders-local-validation.md (generated by the keeper) cites "sliders-local-validation L702" (the KB-GS-1 box, now in the folded file) and still routes by the old handoff name; filing handoff_task for OCR points to :2540 which is now the "Model-backed parser arms" header area, not the box (box is 2545/2547). Task text must be the identity.

## Autopilot / KB RAG links

- scripts/lab/run_job.py:35,53,414-437 (frontier lab jobs) consumes kb_rag via `context_modes: kb_rag`, `kb_top_k: 6` in orchestration/lab_jobs.yaml:46,133 using kb_rag.DEFAULT_INDEX_DIR. These jobs inherit the qd-v1/qd-v2 failure (run_job.py:425 wraps in a broad except, so it degrades silently to "kb_rag" excerpt reason entries, not a hard failure; I did not run it).
- scripts/autopilot/operator_seed_strategies.yaml:~66-72 seeds a "retrieval-weight sweep for NumericSwarm" with bind_identifiers kb_rag_retrieval, bind_status future, source_handoff internal-kb-rag (file renamed 11-02). Grep of src/ scripts/ orchestration/ finds NO code that defines a kb_rag_retrieval knob: the identifier appears only in that yaml. So the seed is unbound and the source_handoff name is dangling. No Autopilot evaluation path measures KB retrieval quality; K7 certification pool (70 cases) lives in data/kb_rag/eval.
- seed at ~622-640: web_research_rerank no-go ("0 percent irrelevant pages vs 20 percent threshold") is why G14 (mxbai re-export for the reranker) has low consumer value; handoff G14 text does not mention it.
- No other Autopilot dependency. Nothing in this handoff truly waits on the Autopilot HOLD.

## Duplicates / overlaps between folded tracks

- Box 6 (2513) overlaps boxes 7 (2518): both are ODL-vs-others comparisons on the same 200 PDFs; r2 satisfied the shared arms.
- Boxes 10 and 11 are the same run (box text says so).
- Box 9 is a constraint set for 10/11.
- Box 3 and box 5 chain (run feeds decision); box 4 is a precondition of box 3 and is retired.
- Moved-out note at 2541 points to model-evaluation-queue.md "Track: meq-carve-opendataloader-pipeline-integration"; I did not confirm that heading exists (grep for "meq-carve" there lists only gpu-serving and gpu-acceleration tracks). Possible dangling pointer.

## Unmentioned drift

- qd-v2 contract (finding 1); kb-search SKILL.md and the K-status block (line ~5) assert a working index.
- v10 kernel store: Unlimited-OCR box cites v10 production CPU kernel; this is consistent. No "llama.cpp/build/bin" hardcodes checked in scripts for these rows (not audited).
- ik_llama: no PIP-04 box depends on it (not exhaustively searched).
- KB hook split: .claude/hooks/post_commit_kb_rag_update.sh header still cites "handoffs/active/internal-kb-rag.md K5" (file renamed). scripts/hooks/posttool_kb_rag_update.sh is the live dispatcher (settings.json:20).

## DOABLE-DURING-HOLD

1, 2 (install part), 3-5 (rescope/close: text work, plus decision package for 5), 6 (rewrite), 7 (durable evidence copy and tick), 10/11 (receipt adjudication, locating run/ data), 12 (driver script only; measurement waits on stack bringup, not Autopilot), 13.
## NEEDS-AUTOPILOT-RUN: none.

## Could not verify

- Whether the qd-v2 mismatch also blocks a live `cli.py query` (I read code paths and index_meta; I did not run a query or touch the index).
- Receipts for the Unlimited-OCR run (scratch dir missing; no vault tarball matched).
- Whether run_job.py:425 swallow covers the query call (only read grep lines).
- Exact current content of wiki 31/32 gap, and whether ratify flow requires further operator steps for the P-DOCPARSE-1 "annex draft" file still being named draft.
