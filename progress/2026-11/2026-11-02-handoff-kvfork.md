# 2026-11-02 — handoff kvfork

## 09:46Z — KPF-17a shared-trunk exactness harness

Corrected the exactness comparator to parse the actual hs=hsk/hsv listing and verify dump hashes; three offline fixtures passed. Added an unbuilt masked-cell sensitivity control to the draft. KPF-17a remains open: CPU needs an independently bound baseline, and masked-value perturbation controls plus keeper qualification and CPU/ROCm execution remain required. No row was published.

## 09:50Z — KPF-17a shared-trunk masked-value controls

Added globally invisible K/V perturbation and visible-V sensitivity controls to shared cases; these are unexecuted. Published kvfork17a-cpu-20261102 and kvfork17a-gpu-20261102 for keeper qualification, with source-bound identities and per-case raw evidence. CPU compares pinned pre-skip and champion builds; GPU compares skip off/on with during-run residency. Qualification and scientific gates remain open.

## 09:52Z — KPF-17a shared-trunk masked-value controls

Published CPU and GPU KPF-17a rows; qualification and scientific verdict remain pending. The preceding preparation commit is included in this lane merge.

## 09:52Z — KPF-17a shared-trunk masked-value controls

Published CPU and GPU KPF-17a rows; qualification and scientific verdict remain pending. The preceding preparation commit is included in this lane merge.

## 09:55Z — Prepare remaining KPF-17a GPU validation and KPF-17.4d image-specific controls

KPF-17a CPU row kvfork17a-cpu-20261102 is published and needs keeper dry run. GPU harness preparation is delegated; KPF-17.4d(b) needs the historical-image layout witness and a runnable reviewed control. KPF-LB2.1 still has no real V2 rows in the inspected snapshots. P3 worktree discovery and impact preparation continue; completion files are registered under the session awaiting directory.

## 09:57Z — Repair KPF-17a GPU qualification and prepare remaining controls

KPF-17a GPU qualification failed: five result units were produced but sampled VRAM peaked at 13,131,776 bytes; the failure also reported orphan PIDs 1279599 and 1279600. Launcher diagnosis and repair are delegated, as are P3 index preparation and KPF-17.4d(b) control preparation; their completion files are registered. No GPU result is accepted. CPU row kvfork17a-cpu-20261102 still needs qualification.

## 09:59Z — Prepare KPF-17a GPU residency qualification repair

The KPF-17a GPU qualification failure is being repaired by placing an existing supported large case first and exposing its real live allocation to the keeper residency sample; the original failure remains unqualified. The two reported orphan PIDs no longer exist. P3 experimental worktree is at c72ec82f5417bb2937310326120f149b665e8400; its index is absent and a keeper build-role preparation is in progress. KPF-17.4d(b) control preparation continues. Completion reports are registered for the dispatcher.

## 10:01Z — Repair and republish KPF-17a GPU residency qualification

Republished kvfork17a-gpu-20261102 after the failed VRAM residency sample: first supported case 83 retains its actual computed allocation for a 12-second observation on arm 0, followed by shared case 86 and all remaining cases. The prior failed dry-run output is preserved in out-failed-20261102; Python compilation, launcher shell syntax and bound-input verification passed. This is not a GPU result or qualification pass; keeper dry run remains pending. P3 worktree exists at c72ec82f5417bb2937310326120f149b665e8400 but remains unindexed.

## 10:03Z — Complete KPF-40 hybrid slice pre-check and port plan

KPF-40 completed: checked the v11 FA audit, C5 hybrid split and upstream #29510 head b3ad117508ebddf430106005515e9aec4be67444 (open, not draft); recorded slice eligibility, fallback constraints and a gated port plan in the handoff. The independent GPU-X source audit found no measured attention-only KV bytes/token in retained P0 timing outputs, so no crossover verdict is claimed.

## 10:15Z — Land KPF-40 pre-check and resolve lane merge

Preserved the completed KPF-40 pre-check across the origin/main update and resolved the generated index conflict. KPF-04 waits for KPF-18; KPF-17.4 CPU evidence already exists and its outstanding work is GPU adjudication. The LB2.1 real-row check awaits a migrated V2 session.

## 10:18Z — Record delegate-wave trunk-first disposition

Closed KPF-21 using its explicit record-as-not-wired disposition: orchestrator origin/main 488b31c96c6c148768508b3dcaefcb6c4c297664 has the scout path but delegate waves still call llm_call without the trunk-prefill/checkpoint_at hook. No live behavior claimed. KPF-17a and KPF-31 await keeper dry runs; KPF-17.4d(a) was already filed and (b) needs image-specific controls.

## 10:21Z — Complete KPF-21 trunk-first disposition

KPF-21 source evidence and its completed checkbox were retained after the initial index freshness check failed; refresh the generated index before landing. KPF-18-S1 follow-up depends on group-3 localization, and KPF-26.1h awaits actual KEEP_ON-window traffic. Corrected the belief source table to match the 52 WORKING-ALLOWED manual classifications.

## 10:31Z — Complete KPF-27e interface mapping

Closed KPF-27e on its existing 2026-11-01 source audit: orchestrator 6d631212d181565d69236ee7d04d5928487e4382 maps the listed P1 interface fields and sends checkpoint_at in gated trunk-first dispatch. Live shadow metrics remain KPF-27d; no runtime result claimed.

## 10:35Z — Complete KPF-27e interface mapping

KPF-27e's existing source audit establishes the specified P1 field mapping and gated checkpoint_at dispatch. Shadow-window metrics remain KPF-27d. Initial wrap-up required a generated-index refresh after the checkbox change.

## 10:39Z — Land KPF-27e interface mapping

KPF-27e field mapping and checkpoint_at dispatch are complete per existing source evidence. The generated handoff index conflict against current main was resolved and regenerated in merge commit 92096dcd8. KPF-27d still owns live shadow measurements.

## 10:56Z — Prepare KPF-20 and KPF-17.4d rows

Prepared KPF-20 v3 with a pinned isolated scratch source and committed-source member-call scan, and KPF-17.4d build v2 with source provenance, content binding and cooperative build stop. Neither has a smoke PASS. All four CPU quarters were held by filler-inf70-cls-rect-live-20261101, so current smokes could not acquire a quarter; retry only once an appropriate quarter is available. KPF-31's two smoke attempts failed on the q0 region lock, and a partial source scan does not establish a GitNexus impact. GPU KPF-17a smoke was refused because the GPU was busy.

## 11:01Z — Repair and preserve KPF row preparations

KPF-20 v3 isolates and hash-binds its retained checkout and rejects untracked files. KPF-17.4d build v2 now validates exact host compiler provenance, CMake option equality and cooperative process stopping; six tests pass. Neither row has a smoke PASS: all four CPU quarters were held by the INF-70 workload at inspection. The earlier commit was stopped by a non-collectable test, now fixed.

## 11:11Z — Detect omitted KPF-64 family bursts

The retained F replay attempted 267 of 442 frozen manifest requests: eight children (175 requests) never ran because their parent retained only 16 turns while their parent_turn indices are 94–110. F DONE is insufficient evidence of complete sample coverage; no complete F-FB verdict is claimed. A fail-closed replay preflight and local source recovery investigation are underway. All CPU quarters and GPU were busy when publisher admission was checked; no new smoke PASS.

## 11:24Z — Publish KPF-17a CPU successor

Filed kvfork17a-cpu-20261102 inconclusive (rc 75 disk floor, 68 original cases recorded). Published kvfork17a-cpu-successor: four-CPU smoke PASS with eight fresh cases and 68 validated imports; no complete CPU or shared-trunk verdict. KPF-20 reached three failed smokes and remains parked under the lineage rule. KPF-64.3 preflight patch fails closed on eight missing bursts; local snapshot recovers the original parent but the missing prompts exceed the frozen cap. Build-v3 is a reviewed preparation, not yet published; its repeated source verification needs reconciliation with the no in-grant preparation rule.

## 11:27Z — Publish KPF-17.4d instrumented build row and file KPF-17a successor

Filed kvfork17a-cpu-successor inconclusive (rc 1, 86 original case receipts retained, no extended case receipt or COMPLETE). Published kvfork174d-build-20261102 with four-CPU smoke PASS compiling one real unit. KPF-64.3 replay guard prepared; the revised experiment awaits the operator decision.

## 11:32Z — Prepare paired KPF-17a CPU successor

Diagnosed the CPU successor cross-run preservation failure: its original and extended outputs were produced at different thread counts. Prepared kvfork17a-cpu-paired to compare each original and extended case under identical grant and thread count, retaining earlier receipts separately; publication smoke started but its outcome was not yet observed. No new exactness verdict is claimed.

## 11:33Z — Prepare paired KPF-17a CPU successor

Diagnosed the CPU successor cross-run preservation failure: its original and extended outputs were produced at different thread counts. Prepared kvfork17a-cpu-paired to compare each original and extended case under identical grant and thread count, retaining earlier receipts separately; publication smoke started but its outcome was not yet observed. No new exactness verdict is claimed.

## 11:34Z — Prepare paired KPF-17a CPU successor

Diagnosed the CPU successor cross-run preservation failure: its original and extended outputs were produced at different thread counts. Prepared kvfork17a-cpu-paired to compare each original and extended case under identical grant and thread count, retaining earlier receipts separately; publication smoke started but its outcome was not yet observed. No new exactness verdict is claimed.

## 11:37Z — Qualify paired CPU shared-trunk exactness and queue GPU smoke

kvfork17a-cpu-paired publication smoke PASS with two case receipts; row grantable. The paired comparison runs the original and extended harness under the same grant and thread count; no full CPU verdict yet. Fixed preparation to copy the checked-in job, create required directories and refuse existing scratch; isolated fixture and Python AST equivalence checks passed. For kvfork17a-gpu-20261102, set smoke_timeout_s=1500 and invoked the publisher; GPU busy, smoke queued, no PASS or new qualification failure yet. Prior staged handoff findings and row artifacts are preserved in this commit.
