# EVL-10 staleness audit (2026-11-09, read-only)

File: /workspace/handoffs/active/memory-program.md (line numbers as of audit). Index row: routing-and-optimization-index.md:20.
Hold semantics: the Autopilot HOLD blocks only autopilot-driven work. Inference windows are a separate (calendar/claim) constraint.
Depth note: claims marked (V) were checked against code/git/disk; others are judged from handoff text only.

## Re-embed finding (details)
- Full re-embed #1: M-10, receipt 20260727T220715Z, 58,281 rows (handoff line 76). DONE.
- Full re-embed #2 (NOT in this handoff, grep for 20260809/08-09 = 0 hits): receipt reseed_episodic_store_20260809T160329Z, state=published, embedded 63,786/63,786, ntotal=id_map=63,786, desync 0 (V: sessions/*.receipt.json). Six earlier same-day attempts (152547Z..160220Z) are stuck in state backups_complete/in-progress, each left 538 MB db + 261 MB faiss + id_map backups (~5-6 GB total, V by ls).
  Documented in routing-program.md:1250 (EPD-3-decision) and progress/2026-08/2026-08-09.md.
- Live store now (V, mode=ro SQLite + file sizes): episodic.db 64,514 rows; embedding_idx 0..64513 distinct, 0 NULL; id_map.npy shape (64514,); embeddings.faiss 264,249,389 B = 64514*4096 + 45 header (consistent with 64,514 vectors x 1024 f32). Last write 2026-10-03T03:48:10 (files mtime identical). 732 rows written after the 08-09 reseed; 0 since 2026-10-03; 0 since the 10-27 EG2 snapshot (matches harness-program.md:2548). memories_appendonly_legacy still holds 680,918 rows (not indexed). Did NOT run the integrity check (needs embedder); alignment above is structural only.
- Is a FULL re-embed outstanding? YES, two of them, both OWNED OUTSIDE EVL-10 and both gated:
  (1) routing-program.md:1235 `EPD-3` (box OPEN, decided 2026-08-12): drop `priority` from `MemoryRecord.embedding_text()` and re-embed the whole store in the SAME change (never code first; 34,938 rows carry `priority:interactive`). Code still emits priority (V: orchestration/repl_memory/memory_record.py:329). Cost measured: 63,786 rows ~15 min at 151.8 rows/s on a 6-process BGE fleet. Needs an inference window (BGE servers), not Autopilot.
  (2) harness-program.md REPL-EMB-2.x EG2 swap: `scripts/migration/reembed_stores_eg2.py run --apply --assume-stopped` on live sessions + strategies dirs, BGE-1024 -> EmbeddingGemma2@256. Bound to the v11 stack change (EG2 arch `gemma-embedding2` absent from production v10). R3 private-copy apply passed; production apply not done. REPL-EMB-R5 threshold recalibration open. If (2) lands first, (1) should be folded into it (one re-embed, one convention) rather than paid twice.
- Triggers: embedder model change (EG2), embed-text recipe change (EPD-3), index/vector corruption (single row -> repair_episodic_vector.py, no full re-embed), serving-binary change (REPL-EMB-2.14 v10 binary parity, flipped, cosine>=0.9999 sample so no re-embed).
- No box in memory-program.md owns either. EVL-10 has NO box for "full re-embed"; EPD-3 is the exact ID for (1). Needs a pointer row/line in EVL-10 or an explicit statement that it lives in EPD-3.

## Box table
Class legend: SV=STILL-VALID, SP=STALE-PREMISE, AD=ALREADY-DONE, UN=UNDERSPECIFIED, NA=NEEDS-AUTOPILOT-RUN, DH=DOABLE-DURING-HOLD.

| # | Box (line) | Class | Evidence / what is wrong or missing |
|---|---|---|---|
| 1 | M-11a first re-distil (140) | SP + UN, DH (teacher run is inference, not autopilot-only) | Readiness probe baseline says 374 / suggested >=2,000; M-25 measured 6,237 post-reseed (5,452 at q>=0.7 = 99.9% success; line 224/M-25) so threshold already met but pool is eval/external-dominated and live writes stopped 2026-10-03 (V). Box premise "let live traffic accumulate" is dead while no traffic flows. Alternative path `seed_skills.py --teacher claude` does not need Autopilot. Missing: decision whether a 99.9%-success pool is acceptable. |
| 2 | M-15 reopen COMP_r (221) | SV, DH | Blocker was the reseed; done 07-27 and 08-09. Pure offline analysis on the store. Must use the 08-09 store (64,514 rows) and note embed-text convention. Not blocked by hold. Missing: statement that the 2 reseeds have happened. |
| 3 | M-12 A/B parent (391) | SP (partial) + NA/inference | Judge re-scoped 2026-11-03 to Qwen3.8-27B-Q8_0 but "recipe to be re-pinned"; B5 GPU window deferred by operator 2026-09-16; eval-tower row is human-only. Needs an inference window, not Autopilot. |
| 4 | M-12b BEAM 128K (493) | UN | Data staged (V: /mnt/raid0/llm/data/eval/beam/data/100K-00000-of-00001.parquet). Judge must be re-pinned, trace arm merged from UTM-B2/B3. Missing: new judge recipe path. Inference. |
| 5 | M-12c checklist (512) | SV, DH | Zero-inference checklist; item (4) judge!=reader must reflect new judge Qwen3.8-27B. Could be ticked as a written checklist now. |
| 6 | M-12f chrono scoring-validity + M-12i (576) | SV, DH | Absorbed M-12i 2026-11-03. Anchor rot: `compute_chronological_awareness_score` is now scripts/benchmark/tulving_episodic_adapter.py:543, not :325 (V). Rescored artifact exists at /mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json (V) but NOT under /workspace/benchmarks (path ambiguity). Write-up only. |
| 7 | M-12k frontdoor A/B (600) | UN | No suite named, no seeds, "memory-off" switch not specified, no flag cited. Needs live frontdoor inference. |
| 8 | VB-SKILLBANK-AB-WRITE (606) | UN, marked too-big | Needs M-23 runner that does not exist; 2026-11-02 correction says writer is called after all arms, not before. Depends on M-11a bank. |
| 9 | M-20 recall()/route_advice() telemetry (630) | SP (anchors) + SV | Anchors rotted: `_recall` is routing.py:93 (not :81), `_route_advice` :339 (not :319) (V). No recall telemetry code exists (grep recall_telemetry/recall_calls = 0). M-22 closed the scope part. Code part DH. |
| 10 | M-19 typed decision record (715) | SV, DH | Spec-only, zero inference. Owner typed-decision-plane.md RTG-56. Not verified deeper. |
| 11 | CFI-1 cache-friendly A/B (738) | SV, inference | Flag exists and is wired (V: reusable_blocks.py, builder.py:36, skill_retriever.py:234). Needs inference window; flag default OFF. |
| 12 | CFI-2 memory-k widening (739) | SV, DH | Decision package, not compute. |
| 13 | M-27 lint/probe extensions (744) | UN | Sub-items (a)-(d) mixed; (d) done 2026-10-27; parent stays open with unclear remaining parts. 11-05 note says s5-stackup-bundle superseded, queue ids stale. |
| 14 | M-27d.1 source label (750) | SP (partial) + SV, DH | MemoryRecord already has `source` field default "unknown" (V: memory_record.py:314) and store carries source classes (seed/eval_or_external/autopilot); box claims cannot separate interactive vs autopilot, but no interactive/cron value written. Premise needs refresh; the code change is DH. |
| 15 | D-c1 measure resume cost (1031) | UN | No carrier named beyond "T3 probe slice"; needs real workload traffic (none since 10-03). |
| 16 | D-f1 verify lease under live 6-worker API (1236) | SP | "once the API is back up": API reload dependency; D-f fence code exists (session lease, protocol.py:589). Needs a live API window; operator reload ownership. |
| 17 | D-f2 fence findings/docs/tags (1239) | SV, DH | Decision plus small code; add_finding/add_tag/add_document still unfenced (V: session/sqlite_store.py, persister.py). |
| 18 | D-g journal uncertain side effects (1267) | SV, DH | No prepared/dispatched/uncertain journal exists (V: grep `uncertain.*reconciled` = 0). Design big; missing owner and tool-surface list. |
| 19 | D-h shape capture (1281) | SV, DH | `variable_lineage` shape gap not rechecked; anchors state.py:450-462 may have drifted. |
| 20 | D-i bound kernel-to-context channels (1291) | SV, DH | Anchors unverified. |
| 21 | D-RI-CONTAIN (1308) | SV, DH | No killable CPython lane exists (V: only exec_sandbox/exec_containment modules). Big code. |
| 22 | D-RI-MONTY-SLICE (1309) | SV, DH | No Monty adapter (V grep: none in src). Code and bench; needs pinned OSS Monty. |
| 23 | D-RI-PREVIEW-1.1 (1314) | SV, inference | 90/90 bad_final; 11-02 audit says old replies not saved, driver has no invalid-cell guard. Driver fix is DH; re-run is a ~5 min CPU filler needing the worker GGUF (Qwen3.6-35B-A3B-MTP-Q8_0, check still the lineup). |
| 24 | UTM-P1a.3 real-data pairing (1474) | SV, DH | Needs non-destructive replay DB; code. |
| 25 | UTM-LB2.2 projector events ingest (1534) | SV, DH | Dev-harness projector -> src/trace. `src/trace` has harness_schema.py but no dev-harness EventSource found (V: partial grep). Check against DHM mining results. |
| 26 | UTM-M9 no-memory control arm in eval tower (1682) | SV, operator-gated | Eval-tower rows are human-amendment-only; needs operator, not Autopilot. |
| 27 | UTM-V1 memory-op envelope (1690) | SV, DH | Design and code, zero inference. |
| 28 | UTM-V2 scoped write proposer (1700) | SV, DH | As above; depends on V1. |
| 29 | UTM-V3 structural vs semantic verification (1708) | SV, DH (structural), inference (semantic judge calibration) | |
| 30 | UTM-V4 answer-time distillation test (1717) | SV, inference | |
| 31 | UTM-V6 full eval matrix (1730) | SV, inference + operator | Merges with M-12/M-9 no-memory arm; overlaps M-12. |
| 32 | UTM-B1 register ms.search/ms.expand (1740) | AD | Registered in src/trace/mcp_tools.py:21,27 via commit 715b49ae (2026-10-07), wired in src/mcp_server.py, test test_trace_mcp_tools.py. Box text still says "no MCP registration". Open question whether "model-facing" means REPL tool vs MCP server only; if MCP is enough, tick. |
| 33 | UTM-V7 profile-write audit (1787) | SP/blocked | Audit run vacuous: no user_profiles.db (V: absent), features().user_modeling off. Waits on a profile store existing. Code and checklist done (09396bbe). |
| 34 | DHM-4 labelling sheet (1831) | SV, operator-labelling | Sheet at /mnt/raid0/llm/private/dev-harness-traces/mining/full-20261022T1310Z/ (not checked). Operator-only. |
| 35 | DHM-5 always-on prefix (1835) | SV, depends on 5.2 | Measured for Claude main/subagent/Codex main; remainder in DHM-5.2. Also note memory index split (KT-5) changes the figure. |
| 36 | DHM-5.2 paired probe (1840) | SV, inference (cloud calls, no local model) | Not blocked by hold. |
| 37 | DHM-8 glob rm guard proposal (1865) | SV, DH | File proposal only; hook edit needs D9 ack. |
| 38 | DHM-9 wholesale_git_add rise (1866) | SV, DH | Analysis; fix needs D9 ack. |
| 39 | DHM-11 hook coverage Codex/opencode (1868) | SV, DH | Absorbs DHM-10. D9 ack for edits. git status shows .opencode/plugins/filesystem-containment.ts and scripts/hooks/tests modified (V), i.e. work is in flight; check before starting. |
| 40 | KT-5 MEMORY.md split (1895) | SV (partial) | Memory split by ws58 (MEMORY.md now has sub-index INDEX-benchmarking.md per context), search half has no owner. Check whether the split half is already done and tick. |

Counts (primary class): STILL-VALID 28, UNDERSPECIFIED 6 (M-12b, M-12k, VB-SKILLBANK-AB-WRITE, M-27, D-c1, M-11a is SP), STALE-PREMISE 5 (M-11a, M-12 parent, M-20, M-27d.1, D-f1), ALREADY-DONE 1 (UTM-B1), blocked on non-hold event 1 (UTM-V7). NEEDS-AUTOPILOT-RUN: 0 truly. No open box actually requires an Autopilot run; M-11a offers an Autopilot path but also a seed_skills.py path.
(Counts are approximate where a box fits two classes; table is authoritative.)

## Index row (next action)
"Run M-12i model-free diagnostic replay after full-CPU bench release under an exclusive claim; keep M-12f metric construction separate" is STALE:
- M-12i was marked declined/merged into M-12f on 2026-11-03 (line 590), so the row names a box that no longer exists and contradicts the "keep M-12f separate" half.
- A model-free offline re-score needs no CPU bench release or exclusive claim; the only compute is pandas/pyarrow over a parquet (M-12j).
- Anchor rot (tulving adapter :325 -> :543); rescored artifact lives in research repo.
- Missing: the full re-embed pointer (EPD-3 / REPL-EMB-2 swap), the 2026-08-09 second reseed, and the fact that live writes stopped 2026-10-03.
Suggested row: next action = "Write the M-12f scoring-validity note (absorbs M-12i), zero inference" plus a separate pointer to EPD-3.

## Drift not mentioned in the handoff
1. 08-09 second full reseed (63,786) not recorded; header still says ntotal=58,749 (stale) and "reseed DONE" is only the 07-27 one.
2. EPD-3 priority-drop re-embed and EG2 re-embed (see above).
3. Embedding convention hardened since: commits 9096a600 (2026-09-14 route all writers through canonical builder), 604c70bf (08-12 self-match gate text), 26c5220c (namespace isolation), 189389cb/9d72b8cc (v10 kernel-store embed binary behind flag; subprocess opt-in) and REPL-EMB-2.13 side= migration.
4. Live write traffic into episodic store stopped 2026-10-03 (Autopilot hold plus no interactive traffic); M-11a, M-12k, D-c1 premises assume flowing traffic.
5. ~25 GB of pre-repair/pre-reseed backups still in sessions/ including six abandoned 08-09 attempts (in-progress receipts never closed); the CLAUDE.md "confirm before deleting" rule applies.
6. Judge/lineup changes: judge now Qwen3.8-27B-Q8_0; the 35B-A3B role binding in D-RI-PREVIEW-1.1 should be rechecked.
7. v10 freeze: any box citing a v9 in-tree llama-embedding binary is stale (REPL-EMB-2.14 flipped to kernel store).
8. Fold artifacts: handoff has duplicated tracks/IDs (two M-17c/M-17d/M-17e entries at lines ~240-330) and header "Related" links point at pre-fold files.

## Not verified
Integrity check/self-match not run (needs embedder; forbidden). Vector alignment not inspected beyond sizes/row counts. D-, UTM-V and DHM box anchors and whether partial code exists were only grep-sampled. M-15, M-19, DHM-4 file existence not checked. FAISS header ntotal not parsed (size arithmetic only; faiss/numpy not available in system python).
