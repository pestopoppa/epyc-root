# fa4-c5-rwoff-build current audit (2026-11-01)

## Current backlog identity

`/mnt/raid0/llm/tmp/compute-flags/BACKLOG-ni.md` lists `fa4-c5-rwoff-build` as CPU rank 14, `needs-launcher`. Its historical FILLERS row says attempt 1 refused before clone/build due to night HOLD. That is not the latest state of the same build dependency.

## Superseding build evidence

FILLERS contains successor `fa4-c5-rwoff-build-r2`, status COMPLETE, rc=0 at 2026-10-27 03:41:27Z. Its build is the exact requested C5 source commit `c72ec82f5417bb2937310326120f149b665e8400`, with ROCWMMA OFF as the sole project feature delta against the existing C5 control, CPU build role, no promotion or performance claim. `/mnt/raid0/llm/tmp/cal-1026/fa4-c5-rwoff-r2/BUILD_VERIFICATION.json` binds source, builder-source-manifest, ELF/native ELF manifests, recipe/feature comparison, UI input, and captured grant. `/mnt/raid0/llm/tmp/cal-1026/fa4-c5-rwoff-r2/BUILT` records that GPU Stage B remains a separate pending item.

Subsequent downstream evidence used this exact build: `/workspace/progress/2026-10/2026-10-28-fa6a-native-gate.md` records native `v11-fa6a-off-native-20261028` passing 2978/2978 on the OFF build, rc=0/nonpartial, with the executable SHA and build-verification hash. This closes the standalone OFF operator gate (FA6a) but does not close the broader V11-FA-6 parent, FA4 matched-band work, or promotion.

The current handoff `/workspace/handoffs/active/kv-unified-stack-rollout.md` §V11-FA-6 (around lines 1046-1050) records the DF2-9 model probe on the OFF build and the separate FA6a full gate. It explicitly scopes remaining work beyond the build dependency.

## Disposition

The original missing-launcher event is superseded by the completed r2 successor and downstream native use. A fresh engine-v14 build packet would repeat completed source/build work and would not advance the current remaining GPU gates. Do not create another build ID or rerun compilation. The backlog generator should reconcile the stale original row to the existing r2 completion; the remaining V11-FA-6/FA4 tasks retain their own identities and evidence requirements.

No source, READY/FILLERS row, grant, queue, HOLD, production tree, or process was changed. No keeper action was taken. Existing r2 launcher was a legacy-engine launcher, but it is historical execution evidence; no claim of v2 qualification is made for that old build row.
