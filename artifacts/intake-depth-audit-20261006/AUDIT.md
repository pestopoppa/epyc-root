# Intake Stage-2 read-depth audit (2026-10-06)

## Root cause (skill)
- SKILL.md:314 "Verify, don't summarise. Read the actual source/code. Quote file:line or the exact passage." is the ONLY read-depth rule. "Primary source" (lines 3, 32, 237) is never defined; no FULL-read requirement.
- SKILL.md:135-159 (added 2026-08-21, 6888208e3) says "ALWAYS PREFER THE arXiv HTML RENDERING OVER THE PDF ... The PDF is the worst of the three routes". Fetching is via WebFetch (since e2bc54215, line 42-44 of the original); WebFetch returns a small-model digest. Nothing says WebFetch summarises, nothing says curl the PDF + Read pages, nothing says clone repos (the word "clone" appears only about lane-worktree hygiene, line 327).
- claim_anchors: SKILL.md:349 says "Record a claim_anchors entry for every claim the dive will let a plan cite", but intake-schema.md:93 says "Anchors are optional". scripts/validate_intake.py has zero references to claim_anchors, read depth, or dive-verified (grep: only awaiting_dive check, line 356, and claim_corrections shape check).
- So a digest-based dive with no anchors passes every gate. The 10-06 entries (1900,1906,1907,1911,1918,1919,1922...) honestly self-report "WebFetch digest ... quotes are digest relays and carry no quote_sha256 anchors; re-pull the PDF before any load-bearing citation" yet are stamped dive-verified.

## Historical counts (origin/main index, 1918 entries)
verification: dive-verified 809, dive-overturned 80, stage1-unverified 167, absent 862. Dived = 889.
Anchored (non-empty claim_anchors): 689/889 (77%).
Note-keyword hits (in notes/dive_corrections/dive_notes/source_*): WebFetch 32, digest 31, abstract 93, "abs page" 66, summary/summar 123; PDF 148, Table 157, Eq 33, "line" 557, clone 51, pages 58 (keywords are noisy; used as corroboration only).

By intake-id bucket (dived n / anchored / digest-ish note / depth-ish note):
- 001-300: 1/0/0/1; 301-700: 8/5/3/7; 701-912: 16/10/8/13
- 913-1067: 148/26/25/106; 1068-1250: 142/95/57/131
- 1251-1500: 198/190/78/162; 1501+: 376/363/62/233
By ingest date, anchored/dived: 2026-07 20/41, 08 143/298, 09 457/467, 10-03 64/65, 10-06 **0/9**.

## Sample of 15 (evenly spaced over the 889)
272 (2026-04) PARTIAL: corrected later from a v2 re-read; no anchors. 952 FULL: code read (load_dotenv trace), 4 anchors. 1020 FULL (code): pinned commit+tree+README sha, no anchors. 1094 FULL: abc.txt:697 / nips.txt:706 line anchors (text extraction on disk), 10 anchors. 1175 FULL (repo): main@SHA and frozen tree read, no anchors. 1256 FULL: GGUF tensor dir parsed by ranged fetch, 5 anchors. 1341 FULL: html route sha256, 13 anchors. 1416 PARTIAL: press article, restatement, 1 anchor. 1489 PARTIAL: README:12@f0baced only. 1562 FULL: exllamav3 file:line anchors (14). 1627 FULL: independent recompute, METHODS.md lines. 1690 FULL: repo README + CI + dependency pins. 1754 FULL: hf_quant_config.json json-pointer. 1836 PARTIAL: heading-and-hash anchors. 1922 (2026-10-06) DIGEST: "arXiv HTML v2 read via WebFetch digest", 0 anchors.
Result: FULL 9, PARTIAL 4, DIGEST 1 of 15 (sample heuristic; 1020/1175 were full reads without anchors).

## Caches
/mnt/raid0/llm/tmp has 157 dive-* dirs (149 created 2026-09, 8 in 2026-10); 72 PDFs under tmp (all 2026-09/10); only 2 dive dirs hold paper.txt (e.g. dive-1367). Clones: ds41-engram-scratch, secondread-1585-source, inf68-baseline-tree. research/sources has 44 entries. No cache predates 2026-09; earlier dives (Jul-Aug) left source SHAs in notes (e.g. 1020, 1175) rather than files.

## Trend
Not "always superficial": depth improved sharply Aug-Sep (anchor rate 11% before 913 -> 18% in 913-1067 -> 67% -> 96% -> 97%), driven by the 2026-08-09 anchor rule (44d52f866) and 2026-08-10 vidya work. The 10-06 run is an outlier: 9/9 unanchored, all WebFetch digest; the 10-03 run (64/65 anchored) was fine.

## Regression in the skill?
No past version required full reads. Original (e2bc54215, 2026-03) already said WebFetch for everything; 6d429b048/1c1c82adb carry the same "Verify, don't summarise" line. 6888208e3 (08-21) HTML-over-PDF is the only direction change, and it never distinguished digest from source. Real regression is behavioural: anchors are "required" in prose, "optional" in schema, unenforced in code, so a run that uses WebFetch drifts to digests silently.

## Fix
skill-fix.patch (not applied; `git apply --check` passes from /workspace): read-depth contract, anchors REQUIRED, read_depth FULL|PARTIAL|DIGEST, validator gate (forward-only from 2026-10-07 or whenever read_depth is declared, so the 889 legacy entries are not broken). Still to do if adopted: update intake-schema.md field table (read_depth) and flip line 93 "optional"; the 9 digest entries from 10-06 should be demoted to stage1-unverified or re-dived.
