# WRAP-4: physical core relabel and conclusion audit

Source: `handoffs/active/cpu-decode-roofline-program.md` WRAP-4. This audit changes no raw records, historical scratch reports, timing values, or grading rules.

Checked against ROOT lane `885affd35d1abe721f04753eab5f16d5f3685c5f`. Historical report SHA-256: speed-claim `93e530f284f182991aa1b8e0c11c140b39baaf90911f3dba3179c5d92529619a`; champion-1 `f6be44c0c25f10155ce7278c61b808da08b7403c42fa12d10333d3c96ab5e2d3`; champion-3 `03d04f1fb575a1e6f4a026f0be89c90464b8a76e0339967fd26a281c561162b1`; B12 `1d6cbae20ed10f27a0f224a5bfc757a889e337ab053d51c91e0bd3c18b4273d0`; INSTR-B7 `a21a7f71471f597da82c79d24ae8ba620d1abacbb66dc0425c0528da7863a183`; SYNC-16 `b88aad0f7d0dbf335fbbdb337de01668ae377f0cf5bb7885f9922b78c4518080`; SYNC-17 `b714688ebc4879d85410c9fb24c8991d695ab11a505736ed9bf54ac60abfb855`.

## Sampler

`scripts/inf70/harness1/tools/cpuoverlap.py` is already corrected: it reads `thread_siblings_list` and classifies 184–191 as SMT siblings of 88–95. `python3 .../cpuoverlap.py --selftest` passes all six cases. `scripts/vidya/adapters/inf70_serving_arm_capture.py` refuses legacy `disjoint-from-0-95` and `OVERLAPS-0-95` labels. No sampler source patch is needed. Legacy raw reports remain intact.

## Reopened conclusions

| Source | Old conclusion | Evidence and corrected disposition |
|---|---|---|
| `speed-claim/REPORT.md:42–46, 120–123, 381–383` | 184–191 GPU peer was disjoint/harmless; false contention escalation | False physical premise. CPU lock ownership and GPU identity may still be true, but they do not prove absence of physical contention. The direct `test-backend-ops` A3 overlap remains an additional observed load, not the only one. |
| `speed-claim/REPORT.md:57–110` and root handoff :4319–4321 | 23.16 t/s / 1.876× “claim-grade” ABA | Preserve six arm values, coherence and within-window ratios as historical observations. Exact per-arm sibling load is unquantified from the old binary label, and ABA alternation alone does not prove it common-mode. Withdraw clean-window/claim-grade attribution; do not fabricate a corrected rate or CI. Current champion already supersedes build 10221. |
| `speed-claim/REPORT.md:219–221` | +0.7% KV plain arm is clean; +2.1% is upper bound | Neither arm is demonstrably clean from the old label. Both numbers remain observed. The numeric ordering is real; “clean” and the contention-derived bound are unsupported. Acceptance loss under quantized KV was separately recorded and does not need a new timing claim. |
| `champion1/REPORT.md:117–123` | 184–191 did not share a core, so background was stationary/absorbed | False physical premise. Keep token/placement/correctness evidence, but the timing cleanliness and automatic ABA cancellation need reopening; do not treat 35.407 t/s as an uncontended physical-core anchor. |
| `champion3/REPORT.md:315–339` | Old label wrong, absolutes depressed; paired ratios “survive” | The report already flags the mislabel and an unequal GPU-lane window. Preserve measured ratios as observations, but “paired” does not establish equal sibling load. Its own window-3 plain caveat says CI understates uncertainty. Champion-3 and 1.4993×/1.5149× are separately retired in the 2026-09-08 close-out. |
| `b12/REPORT.md:242` | 184–191 peers disjoint, ~0.6 core only overlap, alternation absorbs it | The two peers are also physical co-tenants. ~0.6 core describes only the three direct-overlap processes, not total physical co-residency. Keep A/B results as historical, with co-tenant load unbalanced/unknown. |
| `instr-b7/REPORT.md:38,87` and root handoff :4198–4213 | `GPU-PEER`/KFD or 184–191 means harmless; incident fully cleared | GPU process identification and CPU lock nonviolation are distinct from contention. Correct the latter only. Later HARNESS-1 sibling-aware sampler supersedes the old verdict; do not retroactively promote old label. |
| `sync16/REPORT.md:13,309–329,371–409` | +4.9% MTP was co-residency; +2.91% plain was binary | Direct 0–191 load and A/A binary control remain evidence for their stated alternatives. The old sampler omitted 96–191 sibling load, so attribution of the full +4.9% solely to measured direct load and any “clean” arm is too strong. NO-GO remains independently supported by same-binary ≤+0.04% and the lever budget; preserve raw rates. |
| `sync17/REPORT.md:368,440` | Co-resident processes only on 0–95; clean window needed for regression size | Correct: the old sampler could omit sibling work. Keep no-go/correctness evidence but do not use old direct-overlap counts as exhaustive; report already limits regression magnitude. |

## Source boundary

The raw historical reports and `runs/` remain unmodified. This is a dated correction to their interpretations, not retrospective measurement warrant. Later corrected HARNESS-1 reports and writer are distinct native runs. The prepared patch updates only the methodology wiki; the owning session handles the WRAP-4 checkbox and handoff paragraph separately. No new performance grade or re-estimated number is asserted.
