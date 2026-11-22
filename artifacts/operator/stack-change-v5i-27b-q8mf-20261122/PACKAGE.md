# Stack change V5I-27B-Q8MF: V5I matrix-core Q8 path on the 27B DFlash2 role only

Status: PREPARED, NOT APPLIED. Nothing here has touched a running process or production.

## 0 Intent

```yaml
topology:
  architect_critic:      # MI210 :8083, Qwen3.8-27B Q8_0 + DFlash2-Q8_0 drafter
    env:                 # aliases coder_escalation + ingest_long_context share this process
      GGML_HIP_Q8_MF: "6"
      GGML_HIP_Q8_MF_MIN: "1"
      GGML_HIP_Q8_MF_INPLACE: "1"
      GGML_HIP_Q8_MF_SLC: "1"
      GGML_HIP_Q8_WVSK_MAX: "16"
exclude: [frontdoor and every other role]   # A3B-MTP loses at 0.988x
```

## 1 Evidence (epyc-root handoffs/active/speculative-decoding.md)

- V5I-SERVED-27B (2026-11-21): served 27B DFlash2 path, np1 V/X **1.0995x, 95% CI [1.078, 1.121]**, np2 **1.161x**; 27B-anchored KLD gate passed. Env exactly as above.
- DTREE-0-Q8MF-V5: kernel-level win, correct 215/215. DTREE-0-Q8MF-V6: NO_GAIN, so V6 is not used.
- A3B-MTP served V5I/X **0.988x [0.983, 0.992]** (FUTILITY_BELOW_BASELINE), so A3B is excluded.
- The env names were checked against kernel source (C18 fold `74c18e2d8`, `mmq-q8-mf.cu:127-132,1052`, `mmq-q8-wvsk.cu:73`) and `strings` of the fork build that was measured.

## 2 BLOCKER: production v10 does not contain V5I

- `kernels/production/gpu` is `kernels/builds/gpu-20260921-ffc1bac82`. `strings libggml-hip.so` finds **0** `GGML_HIP_Q8_MF*` and **0** `GGML_HIP_Q8_WVSK*` strings.
- V5I commit `a8cb3a839` (DTREE-0-Q8MF-V5) is not an ancestor of `ffc1bac82`. It **is** in the C18 champion fold (`llama.cpp-experimental-c18-20261122` @ `74c18e2d8`), together with the packed consumers `d3afcd6e5`, `d7fabe949` and `519c40774`.
- In C18 every knob defaults OFF (`MF=0`, `SLC=0`, `INPLACE=0`, `WVSK_MAX=11`), so this env is required after a promotion.
- Applying the package on v10 does nothing. Promotion is operator-only.

**Recommendation: bundle this package with the next promotion (C18 to v11). Do not stage it now.** The project removed `GGML_NUMA_REPACK_INTERLEAVE` on 2026-09-26 because a knob the binary never reads is misleading provenance, and staging this env on v10 would repeat that mistake. Bundling also means the v11 serving gate measures the 27B with V5I on, the way it will actually serve.

## 3 Surfaces (DERIVATION.md walk)

| Surface | Change | Why |
|---|---|---|
| orchestrator `scripts/server/stack_env.py` `_ROLE_ENV_BLOCKS` | add `architect_critic` block | the per-role launch-env layer; aliases resolve to it through `arch_aliases` |
| orchestrator `tests/unit/test_stack_env.py` | scope test | 27B and both aliases get the env; frontdoor, worker_*, architect_general, vision and toolrunner get none |
| research `model_registry.yaml` | none | `server_mode.architect_critic` has no `recipe` block. Adding `recipe.env` would invent a recipe identity, and the override layer is the documented place for this |
| stack_topology / launch_manifest / templates / derived files | none | env is not a topology fact, and nothing derived changes |
| `kernels/production/gpu` | none | frozen; see section 2 |

Patch: `patches/orchestrator-01-stack-env-v5i-architect-critic.patch` (orchestrator commit `8fd386d0` on `origin/lane/sc-v5i-27b-q8mf-20261122`).
Test result: all 17 tests in `test_stack_env.py` pass, run in the orchestrator venv without conftest because the venv has no pytest or fastapi.
Preflight: `stack_change_pipeline.py check` was not run. No derived output changes and no role, model or capacity moves, so there was nothing for it to find. The promotion's own phase-3 preflight covers the bundled run.

### Process incident during preparation

The lane worktree tracked `origin/main`, so `serialized_push.py` published `8fd386d0` to orchestrator **main** for about one minute. It was reverted on main by `f8c313fb` (PUSH VERIFIED). No process was reloaded during that window, and the knobs are inert on v10 anyway. Orchestrator main is now byte-identical to before.

## 4 Apply (after signature, within the promotion's phase 7-8)

1. `git -C /mnt/raid0/llm/epyc-orchestrator cherry-pick 8fd386d0` (or `git revert f8c313fb`) on main.
2. Promote the C18 champion to production v11 (kernel-promotion skill).
3. Reload only the :8083 process. Then gather serving proof: `/proc/<pid>/environ` carries the 5 knobs, the frontdoor PID carries none, `strings` on the mapped libggml-hip.so finds `GGML_HIP_Q8_MF_SLC`, and a real completion returns content.

## 5 Rollback

`git revert 8fd386d0` in the orchestrator, then reload :8083. No symlinks change.

## 6 Risks

- Inert on v10, so a pre-promotion apply shows no gain and claims a tuning that does not happen.
- The evidence comes from the fork `1778cda76`, not from C18 or v11. Re-confirm at the promotion gate.
- The 27B DFlash2 run is nondeterministic (see `docs/design/spec-decode-run-nondeterminism-20261122.md`), so do not expect byte identity.
- The aliases coder_escalation and ingest_long_context inherit the env, as intended, because they share one process.
- `MF_INPLACE` repacks weights in place, which can change VRAM. Check headroom at the gate.

## Sign

`bash artifacts/operator/stack-change-v5i-27b-q8mf-20261122/ratify_v5i_27b_q8mf_20261122.sh --attest RATIFY-V5I-27B-Q8MF-20261122`
