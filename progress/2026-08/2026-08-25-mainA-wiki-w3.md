# 2026-08-25 — mainA (wiki compile w3: document-processing / multimodal / search-retrieval / context-management)

Subagent run: wiki compilation sweep wave W3 — PREPARE only. Prepared exact markdown to
`/tmp/wiki-w3.md`; no wiki files edited, no commits.

## Pages prepared (4, all in /tmp/wiki-w3.md)

1. **wiki/document-processing.md** — new "Compiled Update — 2026-08-25" section (5 source refs):
   - PIP-05 harness hardening closes the three ODL-013 durability gaps (fail-closed extractors,
     engine pins `opendataloader-pdf==2.5.0` / `liteparse==2.12.0`, per-doc latencies + p90,
     score-phase exit 3) — research `run_three_way_bench.py`, 69 passed/1 skipped.
   - Unlimited-OCR record correction closed in place: supersession note on
     `progress/2026-08/2026-08-13-mainD.md`; run dir verified GONE from disk (held_s survives only
     in prose); canonical A/B still operator-gated.
   - document-parser-table-bench instrument: full OmniDocBench 1,651/665 local; PaddleOCR-VL
     three-stage correction (0.0/0.058 TEDS figures void); Phase A landed, llama-cpp-server backend
     verified; MinerU2.5-Pro/GLM-OCR neither single-pass.
   - Did NOT duplicate the already-recorded omnidocbench rename RESOLVED note.
2. **wiki/multimodal.md** — new "Compiled Update — 2026-08-25" section (5 source refs):
   - PaddleOCR-VL 0.0/0.058 figures in the 07-17 finding are void (off-label), instrument now fixed,
     Phases B/C operator-gated; Unlimited-OCR measured 18-page demo (median 5857 ms/page, 392 t/s)
     corrected to demonstrated prompt/profile mismatch — second harness-vs-model instance.
3. **wiki/search-retrieval.md** — new "Compiled Update — 2026-08-25" section (4 source refs):
   - PREFIX-1/PREFIX-2 (encoder never applies trained [Q]/[D]; 1.63e-01 vs 6.60e-03 quantization,
     62.5% top-1; OP-24; re-embed corpus); GrepSeek intake-1239 zero-index challenge (KB-GS-1..4);
     Firecrawl verdict label `not_applicable` → `superseded` + CA-6 engine-waterfall decision.
4. **wiki/context-management.md** — three new "Compiled Update — 2026-08-25" sections
   (5/5/3 source refs):
   - OCC-2 provider image-billing verification (RTG-53): Gemini/OpenAI/Anthropic verified, Kimi
     partial; Anthropic tile-model drift demonstrates the staleness caveat.
   - BEP-6 hashline granularity overturn; BEP-7 aider pairing rule + Cursor line-number tension;
     query_memory↔spill-pointer integer-key mismatch (options a/b/c, a recommended) +
     `_spill_if_truncated` reference correction; markdownfs `/runs/<run-id>/` trajectory-artifact
     shape; pi-agent-core afterToolCall field-replace/throw-isolation; venice drift-detector.
   - UTM-V1..V6 append-only memory-op envelope (shadow-first, no-memory control); intake-1279
     llama-server nine-day log-retention hole (covered window clean incl. 64,019-token prefill).

## Excluded (with reasons)

- KB-WM watermark items → knowledge-management.md (another session's page).
- GLM-OCR MTP note → speculative-decoding page.
- SX-5/6, CA-5/7 unchanged deployment details.
- Duplicate restatement of the omnidocbench rename (already RESOLVED on the page).

## Validation

- All four pages read fully; all 16 drifted sources read (or skimmed where instructed).
- Prepared markdown written to /tmp/wiki-w3.md (only output file; no wiki edits).
