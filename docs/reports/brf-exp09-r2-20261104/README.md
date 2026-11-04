# EXP-09 answer-budget replay

The original native run completed 48 unique cells (12 logs × 4 arms), with the unchanged pinned control at orchestrator `3a428cb3`, isolated CPU-kernel linkage, complete raw answer/evidence capture, 48 parsed answers below the 1024-token limit, and 12/12 planted mismatches rejected. Verified-quote mean per-cell composite fact score was 0.8681 versus control 0.8035; the predeclared exploratory decision is EXPAND. Shape-header was 1.000 and pointer-only 0.2638 under the same scorer. These are small-sample descriptive results, not production or enablement evidence; failed-ID references remain capped at 10 and use substring matching.

The original terminal record says `mechanism_fired=false` and `capture_complete=false`. It is preserved unchanged. In `job.py`, `run_cell` emits a complete cell but returns a score-only dictionary; `main` places that score dictionary in `got`, then reads `evidence`, `view` and `answer_raw` from it. The native per-cell records do carry those fields. SUMMARY.json independently checks the exact 48 item-arm keys, item hashes, parsing, token limits, captured fields and each planted rejection. The earlier inconclusive verdict is retained as prior-verdict-inconclusive.json; it was based on the faulty aggregate. This correction is an observation from original captured records, not a replacement terminal record or invented run warrant.

A larger, source-separated evaluation and product implementation remain under TOC-SP-3; do not infer served latency from this standalone greedy CPU run.

On the 12 paired items, verified-quote had 4 higher scores, 6 ties, and 2 lower scores versus control. Eleven quote responses were accepted and one fell back after verification; all 12 planted mismatches were rejected. These observations describe the frozen pilot only.

An additional non-gating audit recomputes exact-string failed-ID recall from the retained answers against the same capped references; see exact-id-audit.json. It does not change the predeclared substring-scored EXPAND verdict.
