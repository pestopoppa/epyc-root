# 2026-11-02 — handoff kvfork

## 09:46Z — KPF-17a shared-trunk exactness harness

Corrected the exactness comparator to parse the actual hs=hsk/hsv listing and verify dump hashes; three offline fixtures passed. Added an unbuilt masked-cell sensitivity control to the draft. KPF-17a remains open: CPU needs an independently bound baseline, and masked-value perturbation controls plus keeper qualification and CPU/ROCm execution remain required. No row was published.

## 09:50Z — KPF-17a shared-trunk masked-value controls

Added globally invisible K/V perturbation and visible-V sensitivity controls to shared cases; these are unexecuted. Published kvfork17a-cpu-20261102 and kvfork17a-gpu-20261102 for keeper qualification, with source-bound identities and per-case raw evidence. CPU compares pinned pre-skip and champion builds; GPU compares skip off/on with during-run residency. Qualification and scientific gates remain open.

## 09:52Z — KPF-17a shared-trunk masked-value controls

Published CPU and GPU KPF-17a rows; qualification and scientific verdict remain pending. The preceding preparation commit is included in this lane merge.
