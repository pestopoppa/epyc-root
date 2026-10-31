# 2026-10-31 — YaRN aggregate reanalysis and HIL15b-v2 R7 source readiness

## YaRN aggregate result filing

The accepted offline analysis repair is filed in `artifacts/compute/ni-yarnagg-final-20261031/` and published in root commit `e98555e4c72e`. The registered paired one-sided exact McNemar rule uses alpha 0.05, counts score >= 1.0 as right, and fails if p <= 0.05. The fresh full cohort had 141 pairs, b=7, c=11, p=0.8810577392578125, mean A1−A0=0.03667996453900709, and 18 discordants; the exact prospectively declared original 120 had b=5, c=10, p=0.940765380859375, mean difference=0.051432291666666664, and 15 discordants. Both are NOT-FAIL and meet the 10-new-discordant-pair target. NOT-FAIL means no harm detected at this sample size; it does not establish equivalence, safety, or adoption. Historical extension b=2/c=1 remains separate and excluded. All negative controls reject; missing-pair, hash mismatch, and served-count mismatch remain caught. The original postprocessor failure remains preserved as failed; this is a corrected offline quality verdict, not a rewritten exit status.

The r11 full-120 attempt is superseded by exact identity of all 120 pairs, prompts/input bytes, model/server/template, native outputs, and score source. Do not rerun that duplicate GPU work. Full native A0/A1 streams are preserved compressed with uncompressed SHA-256 values. The expanded 141-item plan was excluded because its tokenizer SHA hex value triggered the repository PII gate; full 141-plan metadata, results, source manifest and native outputs are retained. No frozen model or serving code was changed.

## HIL15b-v2 R7 READY source

The canonical R7 source capsule is `artifacts/compute/ni-hil15b-v2-r7-20261031/`. It preserves the 20-task frozen source, canonical single-process native driver, source pins, one-window 60-attempt READY manifest, and the model-free cutoff control. Its noncohort qualification completed in 236.7s (about 241s): one request returned 391, one step-bearing run joined to one outcome (1/1), L2 writer rc=0, replay rc=0/clean, `content_cache=False`, and captured server PID 1282968 was confirmed dead. This is transport/writer qualification only. No frozen task was run and HIL-15b remains OPEN until the original 20×3 cohort completes. The one-budget cutoff reports rc=75, partial=true, original denominator 60, 0 complete, 1 exposed-incomplete UNKNOWN, and 59 unexposed. No partial quality verdict, redraw, or adoption claim is made. The former per-slot r1 prototype was withdrawn before any frozen attempt and is not included as canonical source.

## Child source status

The C5 counter-gate progress note is copied byte-for-byte at `progress/2026-10/2026-10-31-c5-7-counter-gate.md`; its C57 parent remains OPEN and no hardware/live cohort is claimed. Its `NOT-READY` condition gates only that specific source. No row checkbox was changed in this source-only wrap-up; handoff semantics and existing source-table wiring are owned by the main session after source commit review.

## Verification

Artifact file manifests were regenerated and checked against each staged file. Both YaRN native output streams match the original source manifest after decompression; all 14 source-manifest entries checked. R7 capsule files match its capsule SHA manifest. The PII hook rejected the original expanded 141-item file due to a digit run inside a valid 64-hex tokenizer hash; that file was excluded without bypassing or modifying the hook. Commit-scoped validation also reported existing grep-under-pipefail findings in preserved R7 `job.sh`; this artifact is evidence/source, not an executed code change.

A post-publication audit compared every capsule manifest row to the Git blob, not only the sparse checkout. It found and corrected one stale YaRN README hash/size row; all other files already matched. The final published manifest was regenerated from committed blobs and checked for every file, including decompressed native A0/A1 stream hashes.
