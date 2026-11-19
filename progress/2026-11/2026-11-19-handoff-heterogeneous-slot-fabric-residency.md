# 2026-11-19 — handoff heterogeneous-slot-fabric-residency

## 02:59Z — Consume already-filed byte-alignment R2 run-end and resolve stale resume conflict

Run-end event `kpf623-byte-align-r2-20261105` was already consumed: file_result.py returned NOOP because its FILED receipt exists, with verdict pass. Current origin/main already records the R2 full result under KPF-62.3.BYTE-ALIGN; the apparent R2 open checkbox existed only in stale local edits. No new result or checkbox is claimed. Existing result SHA-256 `e6a945c6dfa94ae5fe07919752b247493fc95eab5346c88d5db56c1028f6f34f`, path `docs/reports/kv-cache/kpf623-byte-align-r2-result-20261105/RESULT.json`. No tokenizer or quality conclusion.

Resolved the stale resume conflict in favor of current upstream handoff text; all old tracked edits remain in stash `hs-resume-preserve-20261119`, and loose files are preserved at `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/resume-preserved-20261119/`. No stale evidence copies or binaries landed. Next task: qualify GPU deficit row `kpf41-backend-gpu-qualification-20261105`.

## 03:02Z — Consume duplicate trace-analyzer run-end; existing matching PASS receipt makes re-filing a no-op.

Duplicate run-end for `kvu19b-trace-analyzer-qual-20261105`: file_result.py returned already FILED. Existing verdict (2026-11-05T02:19:20Z) is PASS, rc0, two synthetic tests and 14 mutation cases; native result SHA-256 `a70243f5c4ec8fe5b5ee331089783680cf47e8122dc3d701c9fb88b775bfcffe` matches. No new result or checkbox completion claimed. Supplied clock bounds remain synthetic assumptions; KVU-19b-gap stays open. The priority GPU row `kpf41-backend-gpu-qualification-20261105` is STOP-held with repeated failures; no retry or hold removal performed. [no-belief: duplicate event acknowledgement; original scoped verdict already retained]

## 03:04Z — Acknowledge duplicate prefix integration run-end; existing PASS receipt and completed box require no new filing.

Duplicate event `kpf174-prefix-request-integration-20261105`: file_result.py returned already FILED. Its retained verdict dated 2026-11-05T02:46:00Z records rc0, one positive compare and five pre-judge refusals, matching seals and worker cleanup; native result SHA-256 `81e8bf0f063093b555306dd1a459c38fa05a4728bdc3333eca4b659510506bf7`. KPF-17.4D-PREFIX-INTEGRATION-QUAL is already complete; no new result or tick claimed. No native tracing, historical replay or equivalence follows. Checkpoint correction: `kpf131-native-binding-impact-a1f0-r5-20261105` routes by manifest to KPF-17.4D-NATIVE-IMPACT-RETRY, is owned by operator-adhoc-takeover-20261105 and is STOP-held; no modification or retry performed. [no-belief: duplicate event acknowledgement]

## 03:06Z — Consume already-filed output-supervision run-end; no new result-bearing task in this duplicate event.

Duplicate event `kpf18-g3-output-supervision-qual-r2-20261105`: existing PASS verdict dated 2026-11-05T03:33:24Z and completed KPF-18-G3-OUTPUT-SUPERVISION-QUAL box already retain the six isolated controls. Native result SHA-256 from the existing receipt: `869486c3da026e9987bd7004b87f509e648ac035d96165ec5ff276ed9bf1cec9`. No new result or checkbox completion. Existing scope excludes integrated candidate, native lifecycle, GPU and unsampled peak. [no-belief: duplicate event acknowledgement]

## 03:07Z — Acknowledge replayed later-slot qualification run-end; preserve the existing filed PASS and completed box.

### KPF-18-G3-LATER-SLOTS-QUAL — replayed run-end acknowledged

Row `kpf18-g3-later-slots-qual-20261105` ended rc0. Applied the decision rule to the existing native result: PASS, all 12 synthetic real-socket controls present across queries 2 and 3; target stalls took 0.180150–0.180189 s and STOP took 0.020251–0.020377 s, with joined peers. Query-2 timeouts were swallowed before the fixture terminal Deadline propagated; query-3 timeouts propagated directly. This is scoped software qualification, with no native lifecycle or GPU claim. Existing agent verdict already records PASS with matching result SHA-256 `9155b36b15b7707fc4383086fa2de0e198a69e7739da79495e87a84a77952a35`; the handoff box is already checked. Refreshed the FILED receipt without overwriting the verdict or reticking the box. Evidence: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-later-slots-qual-20261105/out/full-attempt/RESULT.json` (SHA-256 above), and `/mnt/raid0/llm/tmp/compute-flags/filing-done/kpf18-g3-later-slots-qual-20261105.verdict.json`. [no-belief: duplicate receipt for scoped model-free software qualification]

Next: inspect the deficit GPU lane row `kpf41-backend-gpu-qualification-20261105`, resolve its routed box and current qualification failure, and advance only if unheld and within the lineage retry limit.

## 03:09Z — Acknowledge replayed allocator ELF run-end and preserve the existing filed PASS.

### KPF-13.1-ALLOCATOR-ELF — replayed run-end acknowledged

Row `kpf131-old-allocator-elf-20261105` ended rc0. Result `ALLOCATOR_ELF_CAPTURED` records one pinned libllama image and five rc0 tool outputs, including find_slot, apply_ubatch and apply_ubatch part.0 bodies. The existing agent filing records pinned tool/image checks before and after and owned-child cleanup. Its result digest matches the retained result SHA-256 `1adbacefd71ec14ef049d31bc315fd65e5787315912507ca00698f46e7249e1d`. The handoff box and PASS verdict were already completed on 2026-11-05; refreshed the FILED receipt without overwriting the verdict or reticking the box. Scope remains machine-code custody; ABI/layout, historical control and task-binding qualification are not established. Evidence: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-old-allocator-elf-20261105/out/RESULT.json` (SHA-256 above) and `/mnt/raid0/llm/tmp/compute-flags/filing-done/kpf131-old-allocator-elf-20261105.verdict.json`. [no-belief: duplicate acknowledgement of an existing filed result]

Next: inspect deficit GPU row `kpf41-backend-gpu-qualification-20261105`, resolve its routed box and qualification failure, and advance only if unheld and within the lineage retry limit.

## 03:11Z — Acknowledge replayed RAM helper qualification run-end and preserve its existing filed PASS.

### KPF-18-G3-RAM-ADMISSION-QUAL — replayed run-end acknowledged

Row `kpf18-g3-ram-admission-qual-20261105` ended rc0. Applied the decision rule to the retained result: PASS, all 28 original/corrected synthetic comparisons matched, source seals recorded, direct-child cleanup verified. The original accepted the future-only own grant; the corrected helper refused it with `own grant not active yet`. The existing agent PASS filing matches result SHA-256 `8efa02523664d8126af93ab761cfb560b18dc28d22cf8875eeeb497d86e57bec` and the handoff box was already completed on 2026-11-05. Refreshed FILED without overwriting the verdict or reticking the box. Scope remains a model-free helper contract; no whole-candidate, live-host or GPU admission claim. Evidence: `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-ram-admission-qual-20261105/out/full-attempt/RESULT.json` (SHA-256 above) and `/mnt/raid0/llm/tmp/compute-flags/filing-done/kpf18-g3-ram-admission-qual-20261105.verdict.json`. [no-belief: duplicate acknowledgement of scoped software qualification]

Next: inspect deficit GPU row `kpf41-backend-gpu-qualification-20261105`, resolve its routed box and qualification failure, and advance only if unheld and within the lineage retry limit.

## 03:13Z — Acknowledge replayed integrated-cell qualification run-end without duplicating its existing PASS filing.

### KPF-18 group 3 — replayed integrated-cell result acknowledged

Dispatched row `kpf18-g3-integrated-cell-qual-20261105` ended rc0 and its retained result passes the declared four-control rule: STOP refusal, latched STOP across finalizer failure, deadline/refusal-ledger failure, and ordinary diagnostic error. Existing agent PASS filing binds the same result SHA-256 `b611f20de15fd424521f35bed0e19835e8e9be9df332c592e165d029ab4cc7fd`; the handoff already records that full-attempt verdict. Refreshed the existing FILED receipt without replacing the verdict or ticking the broader group-3 localisation box. Scope remains the extracted copied draft cell under fakes; no full-driver, native construction, lifecycle, GPU or layout conclusion. Result: `/mnt/raid0/llm/tmp/kvfork/g3-integrated-cell-qual-20261105/out/full-attempt/RESULT.json`; filing: `compute-flags/filing-done/kpf18-g3-integrated-cell-qual-20261105.verdict.json`. [no-belief: duplicate acknowledgement of scoped software qualification]

Deficit GPU follow-up cannot be restarted: `kpf41-backend-gpu-qualification-20261105` is stopped, with 137 retained launch-failure records (latest precondition refusal), exceeding the stated three-failure retry limit. Its earlier publisher smoke PASS is not a full backend-corpus verdict. `kvu19b-native-custody-r3-20261105` also has a STOP marker. Neither STOP was removed and no successor was published. Next inspect the highest-priority listed CPU qualification, `kpf131-native-binding-impact-a1f0-r5-20261105`, its routed box, STOP/retry posture and latest failure before making any successor ready.

## 03:14Z — Acknowledge replayed observer-build run-end, preserving the existing build-only PASS.

### KPF-60.GPU-X — observer-build replay acknowledged

Row `kpf60-gpux-observer-build-20261105-r3` ended rc0. Its result records BUILT for source `8952a0f693fb923918157eb25117641b74766230`, the selection/observer diff seal, linked binaries, own-ggml linkage and model-free chunk-store test logs. The existing agent filing records PASS including child cleanup and binds result SHA-256 `25aae556e42f22b24b279613497f277a676f308dd96c8ef6a9a547594b35ed19`. The handoff already records this build-only result. Refreshed the existing FILED receipt; no replacement verdict, new measurement or checkbox completion was warranted. The crossover box stays open; writer equivalence, native byte count, GPU and crossover remain outside this build result. The separately recorded HIGH native-fixture impact remains a source-edit stop. Evidence: `/mnt/raid0/llm/tmp/kvfork/kpf60-observer-build-r3-20261105/out/RESULT.json` (SHA-256 above), existing filing `compute-flags/filing-done/kpf60-gpux-observer-build-20261105-r3.verdict.json`, and `docs/reports/kv-cache/kpf60-observer-build-r3-result-20261105/RESULT.json`. [no-belief: duplicate acknowledgement of build-only qualification]

Next: inspect the highest-priority listed CPU qualification `kpf131-native-binding-impact-a1f0-r5-20261105`, its routed box, STOP/retry posture and latest failure before making a successor ready. The two listed GPU rows were already found stopped in the preceding turn; do not remove their STOP markers or repeat that inspection without a new event.

## 03:16Z — Close the source-bound KPF-30 phase impact box using the existing filed six-symbol PASS.

### KPF-30.PHASE-IMPACT — PASS, six source-bound impacts

Filed row `kpf30-impact-8952-20261104-r9-sq3` ended rc0 at exact detached source `8952a0f693fb923918157eb25117641b74766230`. Applied its decision rule: all six native upstream impacts are LOW, pagination verified, and final scan_complete has partial=false. Affected-node counts: handle_last_sampled_token 1; pre_decode 0; decode 2; sample_and_accept_dspark_serial 1; spec_exact_bonus 1; set_input_kq_mask 0. The retained graph status binds the indexed and current commit; coverage records native_analyze_complete=true and verbose_skip_coverage_verified=true, 25 native large-file skips and one Python scope skip. No HIGH/CRITICAL occurred. The prior operator-takeover PASS filing matches the result digest; preserved it and refreshed FILED. Closed the still-open phase-impact capture box in this boundary, reconciling it with the already completed rerun box. This establishes static impact capture only; skipped/ignored files remain outside edit-safety claims and there is no runtime or inference conclusion. [belief: cc]

Evidence: `/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104-r9-sq3/out/results.jsonl` SHA-256 `00b41f3b1adb641928f6218de67a70497031f21bcc006e3609fe87684cd8c563`; `/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104-r9-sq3/out/coverage.json` SHA-256 `09e63772944f8c7328147f1d1e6af59e43d570bfcaa859a920030987b17e0c60`; existing filing `compute-flags/filing-done/kpf30-impact-8952-20261104-r9-sq3.verdict.json`. No source, log or binary copies were added. Next: inspect CPU row `kpf131-native-binding-impact-a1f0-r5-20261105` and its routed box, STOP/retry posture and latest qualification failure before publishing any successor.

## 03:18Z — Consume duplicate typed-decoder run-end event; existing verdict and receipt already satisfy filing.

Duplicate run-end event for `kpf131-typed-decoder-qual-20261105`: its KPF-13.1-TYPED-DECODER-QUAL box is already complete and its PASS verdict plus FILED receipt were recorded on 2026-11-05. Existing verdict records 8/8 synthetic controls, child exit 0 and cleanup; native ABI, layout and historical binding remain UNKNOWN. Existing result SHA-256: `9b6ba0c7e0caf687a8e5eb4fc844e2dd6c95303e6d4d38e65f65f697a911824a` at `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-typed-decoder-qual-20261105/out/RESULT.json`. No new result or checkbox completion claimed. Next turn: inspect GPU-deficit row kpf41-backend-gpu-qualification-20261105 and its routed box/qualification failure before choosing an unheld result-bearing action.

## 03:20Z — Consume duplicate rebuild-diagnostic event already covered by completed box and existing FILED receipt.

Duplicate event `kvu11c-rebuild-diagnostic-20261105`: KVU-11c-REBUILD-DIAGNOSTIC is already complete with an existing verdict and FILED receipt. Existing result is BUILT, prior_build_match=false (four of five artifact digests differ); this supplies no original-crash, GPU-execution or promotion conclusion. Evidence: `/mnt/raid0/llm/tmp/kvfork/kvu11c-rebuild-diagnostic-20261105/out/RESULT.json` SHA-256 `01a8f0ff7d2b7423b69b8db7cde214587aafc3f9ded4b5a85dbacffee649862b`. No new completion claimed. Next: inspect the highest-priority GPU qualification row and exact routed box, without replaying this completed build.

## 03:22Z — Consume duplicate q8 HIP build event already covered by the existing filing.

Duplicate event `kpf41-q8-hip-build-20261105`: existing PASS verdict and FILED receipt date from 2026-11-05, and KPF-41 already records the completed linked build. Scratch RESULT.json is absent; no evidence recreated and no new completion claimed. Durable receipt: `docs/reports/kv-cache/kpf41-q8-hip-build-result-20261105/RESULT.json` git blob `5111e952277ccb3087a0b939b33069684262bfa5`. GPU execution and correctness are separate from this build-only verdict. Next action remains qualifying the pending backend GPU row, subject to its current failure and lineage limits.

## 03:23Z — Consume already-filed correlation event; reject retries of failed or held GPU rows.

Duplicate event `kpf18-g3-residency-correlation-qual-20261105`: completed box, PASS verdict and FILED receipt already exist (18 expected synthetic outcomes; standalone helper scope only). Durable result `docs/reports/kv-cache/kpf18-g3-qualification-results-20261105/residency-correlation.json`, git blob `9147ddd969178470cd46c74553ef033ceab3b73d`. No new filing or completion claimed. GPU-deficit follow-up inspected: `kpf41-backend-gpu-qualification-20261105` has smoke PASS dated 2026-11-05 03:30:23Z but later FAIL-137 is a launch admission/precondition refusal, not corpus evidence. No retry performed under the stated lineage failure limit. `kvu19b-native-custody-r3-20261105` is explicitly held with STOP by its handoff because of separate-lineage use; not republished. Next: inspect the CPU native-binding impact row exact routed box and hold/successor history before acting.

## 03:26Z — Resolve replayed HSF-1 run-end and checkpointed historical-impact row; no new result possible from either event.

Replayed event `hsf1-impact-326f-20261105` already has its INCONCLUSIVE verdict and FILED receipt (rc1; source references only, native result SHA-256 `3122c59ffb8fbb41f71451cdc3c664018322f9edba1d6aefd0094743523c99cd`). No duplicate filing or parent completion claimed. Checkpoint row `kpf131-native-binding-impact-a1f0-r5-20261105` maps to KPF-17.4D-NATIVE-IMPACT-RETRY, not KPF-13.1. Its declared quarter successor and later q3-sq3 successor are already recorded in the handoff (git object `674f9b55e997df5235bdcd1beb88754f472f5a93:handoffs/active/kv-cache-program.md`); q3-sq3 has a filed PASS, native result SHA-256 `7e373e3c8905acd5e833d25b458e5dd7720726f397eb5749050c0751aba939d3`. Attempt to file the original as SUPERSEDED using file_result.py --no-reclaim was refused with `SKIP:no manifest or end record` (manifest exists, no qualifying end record). No receipt was fabricated, no manifest changed, and no compute launched. No new result-bearing task completed in this turn. Next turn: inspect the deficit-GPU qualification row instead of replaying either historical event.

## 03:29Z — Resolve already-filed startup event and determine whether the deficit GPU qualification can proceed.

Run-end `kvu11c-startup-cleanup-control-r1-20261105` is a replay: PASS verdict, FILED receipt and completed KVU-11c-STARTUP-CLEANUP box already exist. Native result SHA-256 `f5bc45e44d137e9c4207d55060d0b758a3959ab4d40d0fa034b27cab523a12b9`; no duplicate filing or new completion. Advanced inspection to deficit GPU task KPF-41.BACKEND-GPU-QUALIFICATION: retained publisher PASS is dated 2026-11-05T03:30:23Z, while all 137 FAIL memos are kind=launch (admission/precondition refusals), not failed corpus or publisher qualifications. Correction to earlier checkpoints: those memos alone do not establish three failed qualifications. Row remains STOP-held, with neither full result nor grant end. Read-only `job.py --check` verified artifact hashes before failing because expected detached source `/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-tests-build-20261105/source` is absent; runtime manifest digest still matches launcher pin `9d08a5dafc4566c29c207e793e76ffa7caf20fdecc0a45dcc5e0fa05b0b601cf`. No source reconstruction, STOP removal or retry performed. One inventory inspection found STOP markers on all 21 listed needs-qualification rows; the next CPU component-impact row also has a completed PASS successor already recorded in the handoff. No unblocked result-bearing task identified and no new result claimed. Next resolve KPF-41 STOP provenance and source-custody recovery rather than replay completed events or republish obsolete impact rows.

## 03:34Z — Repair source custody and publish same-lineage backend GPU qualification successor; smoke queued because GPU busy.

Duplicate D64 parity event was already filed PASS with FILED receipt; no duplicate completion. Located keeper source reclamation at 2026-11-05T03:30:25Z immediately before launch refusals. Park notice permits fix/republish; 137 failures are launch refusals, not qualification trials. Prepared same-lineage kpf41-backend-gpu-qualification-r2-20261119 with its own detached exact source, unchanged five build digests and corpus decision rule, and FILLER_ID preservation. Post-repair custody/loader check rc0. Publisher final response GPU busy: smoke queued; no PASS or checkbox claimed. Evidence and packet seals: docs/reports/kv-cache/kpf41-backend-gpu-custody-recovery-20261119.md. Next inspect dispatcher-delivered publisher verdict; do not wait or replay completed rows.

## 03:35Z — Consume replay of already-filed KPF-17 oracle-impact r2; no new result-bearing task from this event.

Dispatched kpf17-oracle-impact-8952-20261105-r2 is already filed INCONCLUSIVE by operator-adhoc-takeover-20261105 at 2026-11-05T09:59:04Z, with FILED receipt present. Operator STOP interrupted analyze before native impact; retained native result SHA-256 fe102201d8561a2bbe81c37947555cb70d24a4d02492456fe6f5317603a65104. The KPF-17 handoff already records the later r2-q2-sq3b successor PASS. No verdict overwrite, recomputation or checkbox completion. No new result-bearing task is supplied by this replay. Preserve the prior checkpoint: kpf41-backend-gpu-qualification-r2-20261119 publisher smoke is queued, without a PASS claim; consume its dispatcher-delivered verdict next.

## 03:36Z — Consume already-filed zero-skip qualification event; no new result possible from replay.

Replay hsf1-coverage-zero-skip-qual-20261105 already has PASS verdict, FILED receipt and completed HSF-1.COVERAGE-ZERO-QUAL box dated 2026-11-05. Existing filing records 16 matched synthetic outcomes; result SHA-256 1cffbf1f78caaf8034c5fd2d9038a985fefc94c9cd3dc576d17f10f6b694b565. No native-impact or actual nonzero-skip clearance, new filing, rerun or completion claimed. No new result-bearing task is supplied by this replay. Prior checkpoint remains the queued publisher smoke for kpf41-backend-gpu-qualification-r2-20261119; consume its delivered verdict rather than polling or republishing.

## 03:37Z — Consume duplicate census event; existing verdict and receipt already satisfy filing.

Dispatcher replay kpf623-census-r2-20261105 is already filed: the 2026-11-05 verdict records rc0 CENSUS_COMPLETE with two inventories of 151936 sequential pieces each; FILED receipt exists and KPF-62.3.NATIVE-CENSUS-R2 is already completed. Native result SHA-256 71010a039d2349a6a821e6119a60c67a5aaeaaaee195f2889706c077f8d9b128. Existing custody limitations and UNKNOWN alignment remain unchanged. No new filing, tick, compatibility or quality claim. No result-bearing task is available from this duplicate event. The checkpointed kpf41-backend-gpu-qualification-r2-20261119 publisher smoke remains queued without a delivered PASS/FAIL; do not rerun or republish it.

## 03:38Z — Consume duplicate own-child memory event; existing verdict and receipt already satisfy filing.

Dispatcher replay kpf50-own-child-memory-read-20261105 was already filed on 2026-11-05 by handoff-kvu: rc0 PASS for all 3 controls (fixture equality, private mutation detection, invalid-address EFAULT), bracketed identities and mapped files, all children exited 0. FILED receipt exists and KPF-50.OWN-CHILD-MEMORY-QUAL is completed. Native result SHA-256 342b81bf4b3524141ccb4b068b396d147c615f55f64398ff4ea5cc403f7e7648. Scope remains own-child CPU virtual memory only, with no physical-page, GPU, map_files, native-target or whole-custody conclusion. No new filing, tick or rerun. No result-bearing task is supplied by this duplicate event; retain checkpoint to consume the delivered publisher verdict for kpf41-backend-gpu-qualification-r2-20261119.

## 03:40Z — Consume duplicate memfd control event; existing verdict and receipt already satisfy filing.

Dispatcher replay kpf17-memfd-seal-control-20261105 was already filed on 2026-11-05 by handoff-kvu: rc0 PASS for 4/4 controls (unsealed mapped-write visibility, sealed alias overwrite refusal, truncation refusal and seal-change refusal). FILED receipt exists and KPF-17.MEMFD-SEAL-QUAL is completed. Native result SHA-256 43f5d531aaf5297d00d00e8787f3f3724230b07d5307013a6e82dce3f5dc5027. Scope remains private non-ELF same-process memfd only; no native-loader, build-identity, cross-process or whole-custody conclusion. No new filing, tick or rerun. No result-bearing task is supplied by this duplicate event; retain checkpoint to consume the delivered publisher verdict for kpf41-backend-gpu-qualification-r2-20261119.

## 03:41Z — Consume duplicate serving histogram event; existing verdict and receipt already satisfy filing.

Dispatcher replay hsf4-serving-histogram-20261105 was already filed on 2026-11-05 by handoff-kvu: rc0 CENSUS_COMPLETE, 195 serving and 290 dispatch records yielded 168 unique valid joins (all direct) and 27 invalid/unmatched records. FILED receipt exists and HSF-4.SERVING-HISTOGRAM is completed. Native result SHA-256 4813fefcbce9e79f1d58b5d2db967254c89480a27af56cda0299372c85593fa8. Historical rho remains illustrative; no inference, fleet-representativeness or HSF-4 completion claim. No new filing, tick or rerun. No result-bearing task is supplied by this duplicate event; retain checkpoint to consume the delivered publisher verdict for kpf41-backend-gpu-qualification-r2-20261119.

## 03:42Z — Consume duplicate native-grid run-end event; result already filed and handoff box already complete.

Duplicate run-end delivery for `kvu-kpf131-native-grid-20261105`: no new result-bearing task. Existing verdict and `.FILED` receipt were created 2026-11-05; KPF-13.1-NATIVE-GRID is already checked. Existing result SHA-256 `0e08b05a23fc6402a1857cb1d730bb7dd5e49708157633a72ee9b42d07e0ef94` records two grids per arm, empty initial grids, honest second cells 0,1 at positions 0,1, empty skip-apply second grid, both rc=0, stable executable and five DSOs. Existing PASS remains fixture-only; no new measurement, tick, or qualification replay. Preserve pending GPU publisher event as next action.

## 03:43Z — Consume duplicate supervisor qualification run-end; existing PASS and FILED receipt already acknowledge this result.

Duplicate dispatcher delivery for `kpf41-r4-supervisor-qual-20261105`; no new result to file. Existing verdict and `.FILED` receipt date to 2026-11-05T03:11Z. The filed PASS cites native result SHA-256 `32f660abc3b79b1a3e0f2dac8ea4bf2e738b0d7213e90ec1ddd52604c515a25d` and covers source-bound synthetic owned-grandchild pidfd cleanup plus four exact marker controls including wrong-type and suffix rejection. No rerun, new finding or parent KPF-41 completion; GPU/backend qualification remains separate. Next action remains consuming the pending r2 publisher smoke event.

## 03:44Z — Consume duplicate grid-binding run-end; existing PASS, receipt and completed box already record the result.

Duplicate dispatcher event `kvu-kpf131-grid-binding-20261105`: no new result-bearing task. Verdict and `.FILED` receipt already date to 2026-11-05T02:50Z, and KPF-13.1-GRID-BINDING is checked. Existing PASS references native result SHA-256 `9570c743d43798ee4da403a8b0d794b70b23865fcee63f21e7439efdf324f028`: two entries per case, one grid per entry, honest second cells 0,1 at positions 0,1, empty mutant second grid, zero child exits, cleanup and stable executable/five DSOs. This is fixture ordering only. No re-filing, new tick, rerun or live task-binding claim. Pending backend GPU publisher event remains the next action.

## 03:46Z — Consume duplicate retained-result comparator event; result already filed and box completed.

Duplicate dispatcher event `kvu11c-retained-result-reconcile-r1-20261105`. Existing PASS filing and `.FILED` receipt date to 2026-11-05T02:56Z, and KVU-11c-COMPLETION-COMPARATOR is checked; no new result-bearing task. Filed native result SHA-256 `798cb3953db6c1a0a6fb82208e5ed890c3111f42e66b11ced3d0109a2c7ff583` records `reconciled_inconclusive`: retained completion predicates and original rc75 receipt match. Historical outer environment and independent execution custody remain unknown, and the original verdict remains inconclusive. No replay, promotion, new tick or finding. Preserve pending backend GPU publisher event as next action.

## 03:47Z — Consume duplicate backend test build event; PASS, receipt and completed box already exist.

Duplicate dispatcher event `kpf41-backend-tests-build-20261105`: existing PASS and `.FILED` receipt date to 2026-11-05T02:53Z; KPF-41.BACKEND-TESTS-BUILD is already checked. Filed native result SHA-256 `4b08e349541a0b6eb3ceedd61ec7c16be34858a065dbb8a81441d43bb736423c` is build-only for source `15caecbbf4cb27452dbd87fa1a68a0e75098388e`, linked gfx90a HIP executable and four library digests with own linkage. No new result, tick, build, GPU execution or parity claim. Pending backend GPU publisher event remains next.

## 03:48Z — Consume duplicate allocator displacement census run-end; existing verdict and receipt already complete

Duplicate run-end event for kpf131-allocator-displacement-census-20261105; no new result or checkbox claimed. Existing verdict is PASS (rc=0), three bodies with 6/494/1100 instruction lines, syntactic operand census only. Existing FILED receipt consumes the event. Evidence: native RESULT.json SHA-256 a959c9213ce17f12f21a38b1711c0ea4fd63b725ed734866205a75bfa385e8ec; handoffs/active/kv-cache-program.md at git 2af27b498 already records the completed KPF-13.1-ALLOCATOR-DISPLACEMENTS box. Preserve the previous checkpoint: consume dispatcher-delivered publisher PASS/FAIL for kpf41-backend-gpu-qualification-r2-20261119; do not replay completed rows or republish queued smoke without a failure event.

## 03:51Z — Consume duplicate stat-fixture run-end; verdict, receipt and box already complete

Duplicate run-end for kpf50-model-stat-fixture-20261105; no new result claimed or checkbox ticked. Existing PASS verdict and FILED receipt already consume the event: rc=0, all six synthetic outcomes matched, including expected acceptance of a same-size mutation with restored mtime. This remains a stat-only limitation, with no model immutability, integration or profiling claim. Existing native-result SHA-256 in the filed verdict: 8fa7de048351e35e690da7cd2ab263071855c3c505c24ffc814d55b65f33d210. Completed box: handoffs/active/kv-cache-program.md at git 44677ed95. Preserve the pending GPU publisher checkpoint; do not replay completed work.

## 03:52Z — Consume duplicate prospective g1 witness run-end; existing SMOKE_ONLY verdict already filed

Duplicate event kvu-kpf174-witness-g1-20261105 already has a PASS filing for its declared prospective SMOKE_ONLY mode and an existing FILED receipt. No new result or tick claimed. Existing finding: g1-S2-B fork/control physical layouts matched, own-PID VRAM sampled during both requests, R5 source/DSO checks and cleanup verified. Historical verdicts and the open parent KPF-17.4d remain unchanged; do not rerun the exposed cell. Evidence: docs/reports/kv-cache/kpf174-witness-g1-result-20261105/ and handoffs/active/kv-cache-program.md at git b0ad2afc4c40bf2e25c447f98beda1015b71175f; existing filed native-result SHA-256 eeb731de83fc42e202b6c24796b380a15c8e8c021b1217830605c4f5ee7bc677. Preserve the pending GPU publisher checkpoint.

## 03:53Z — Consume duplicate observer-impact stop event; partial HIGH stop already filed

Duplicate run-end kpf-rs1-observer-impact-20261105 already has an inconclusive verdict and FILED receipt. Existing completed KPF-RS-1.OBS-IMPACT-HIGH box records rc=3, nine of twelve impacts (eight LOW, one HIGH), stopped on llama_synchronize; owner review is required before changes to that symbol. Parent KPF-RS-1.OBS-IMPACT remains open; no complete scan or skipped-file edit-safety claim. No new result or tick claimed. Evidence: handoffs/active/kv-cache-program.md and docs/reports/kv-cache/kpf-rs1-observer-impact-result-20261105/results.jsonl plus OWNER_WARNING at git 64f64da6b. Preserve the pending GPU publisher checkpoint.
