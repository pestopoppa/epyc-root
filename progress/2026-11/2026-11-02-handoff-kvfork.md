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
