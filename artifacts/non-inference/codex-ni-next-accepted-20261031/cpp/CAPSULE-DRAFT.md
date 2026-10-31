# Capsule draft — AKX-ALL-11 C++ long-context patch regeneration

- Original queue checkbox citation: `/workspace/handoffs/active/autokernel-all-devices-all-dimensions.md:276` — exact text: `- [ ] C++ follow-up: regenerate \`test-backend-ops-cpu-fa-longctx-v1.patch\`.`
- Current research CODE SHA: `e95a9d2e25c3eeedc7a6f997e608d9bd338cbc31` (`codex-ni/code-20261031`, fetched `origin/main`).
- Source file SHA-256: `ad028c93bccd49e227c2aa78466c7170421cd4e84d632d9d6af38f78591d55bf` (`scripts/kernel_rnd/autokernel/loop/cpu_fa_reference.py`).
- Generated block: `backend_ops_patch_block()`, `cpu_fa_longctx_v1`, 35 cases; source-generated block SHA-256 `04517e1afda4dcf59f7ab031660176bd7590a5971ddeed3dd3ecf0ffd6b1f9ca`.
- Durable artifact target: `/mnt/raid0/llm/tmp/codex-ni-cpp-fa-patch-regen-20261031/test-backend-ops-cpu-fa-longctx-v1.patch`. Patch SHA-256 `395e5bbdd66f585dad4f233dfb2b57c1c0e882487244011d9d6ad39be24e0871`.
- Declared base: kernel commit `4348de400191c0b4c5127047037bf9ad83da19b6`, `tests/test-backend-ops.cpp` blob `46b556039d27a3a6048d87a807d8c99e16d1049d`.
- Reviewed target reference: kernel commit `4e0ebc987e354556fbc44a7df0ba26413ed26d95`, blob `8b2991747a0f37b6b5a859e7a4da4fb879a8ee0f`.
- Artifact verification: `git apply --check` returned 0 against the declared base in the existing scratch file tree (not a registered Git worktree); applying the patch reproduced target blob `8b2991747a0f37b6b5a859e7a4da4fb879a8ee0f`. Independent structural check found 35 added cases, both eval/perf registrations, and the `AUTOKERNEL_CPU_N_THREADS` pin.
- The regenerated patch is byte-identical to archived `/mnt/raid0/llm/tmp/ak-codex-handover-20261007/test-backend-ops-cpu-fa-longctx-v1.patch`; the handoff-named `/mnt/raid0/llm/tmp/ak-cpu-fa-route-20261004/` directory was absent. No evidence supports a claim that the prior patch content was stale; the regenerated copy and provenance manifest are now available in this task scratch. Exact command/return-code/blob evidence: `VERIFICATION.log`.
- Scope/evidence boundary: artifact generation and patch application only; no C++ build/test execution, inference, live mask capture, timing or promotion claim.
- Result tick: `[no-belief: static patch regeneration/application only; no measurement or decision-grade inference result]`.
- GitNexus: status was stale (index at `a0a3df0`, current `e95a9d2`); root wrapper denied by global-region-lock and CPU-admission guards. Current indexed impact/context for `backend_ops_patch_block` showed 0 upstream dependants, LOW, with stale-index caveat.
- Source lane remained clean at `e95a9d2e25c3eeedc7a6f997e608d9bd338cbc31`; no main/root handoff or index row was edited here.
