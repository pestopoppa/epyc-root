# STACKCHG-DFLASH2-20261003: :8083 Qwen3.8-27B on DFlash2, Qwen3-VL-30B to cold CPU, drafter selection compiled

**Status: PREPARED (phases 0–5). The operator signs next (phase 6).**
Nothing was applied to a real tree. No commit, push or branch switch was made. No process was started, stopped or reloaded. No inference was sent.
Everything below lives in `/mnt/raid0/llm/tmp/stack-change-dflash2-20261003/`.

**Live state changed during preparation.** At 2026-10-03T04:30:01Z the operator fast-path relaunched :8083 as **PID 3737649 on DFlash2**:
- Its flag set is identical to §2's rendered argv. Only the order differs: `--device-draft ROCm0` comes before `--slot-save-path`. Attestation is order-insensitive.
- Threads are on 184-191.
- :8086 was stopped with `orchestrator_stack.py stop`.

**This package is therefore the PERMANENT registry and compiler fix behind an already-live DFlash2.** Without it:
- The stack's own `start` or `reload` renders `--spec-type draft-mtp --spec-draft-n-max 4` again.
- A default `start` relaunches the VL on the MI210. With DFlash2 resident it no longer fits (61.62 + 5.12 GiB).

With it, the stack's own compile, launch and attestation produce the live argv. `check` against the live fleet is **fully green** (§3).

**Signing token:** `RATIFY-STACKCHG-DFLASH2-20261003`. Signing script: `ratify_stackchg_dflash2_20261003.sh`. It is TTY-gated and the **operator runs it** (§9).

## 0. Intent (phase 0: `intent.yaml`)

Operator decisions:
1. **2026-10-01, "ALWAYS use dflash2".** The :8083 Qwen3.8-27B-Q8_0 (host `architect_critic`, with aliases `coder_escalation` and `ingest_long_context`) moves permanently to the DFlash2 drafter:
   - `-md Qwen3.8-27B-DFlash2-Q8_0.gguf --spec-type draft-dflash --spec-draft-n-max 8 -ngld 99`, the canonical recipe `qwen3.8-27b-q8-gpu-dflash2-np4.json`.
   - The production shape is unchanged: np 4, `-c 196608`, q8_0 K/V, kv-unified, flash-attn, same template, same slot path.
2. **2026-10-03, "Vision down, canonical DFlash2", as refined via workspace-89.** Qwen3-VL-30B (:8086; `worker_vision`, with alias `vision_escalation`) leaves the MI210 and goes to a **CPU placement, COLD/on-demand**:
   - It is in the WARM tier, so a default `start` does not launch it.
   - It is **not** retired or deprecated. Its weights stay.
   - The operator reassesses the placement when the 2nd MI210 arrives.
3. **Structural fix, DRAFT-SEL-1:**
   - The master lists every acceptable drafter per model.
   - The orchestrator topology selects exactly one per server.
   - The compiler projects that choice into the lean registry, the priors and the argv. There are no hand-carried `spec_type` copies.
   - The global `production_recipe: draft-mtp` is demoted to the n-gram composition scope.

Bases:
- Orchestrator `main@99e3e5fe`. It moved from 2d97ade2 during preparation, and the patch was re-verified on 99e3e5fe.
- Research `main@7b9bc565`. origin/main is 42f434a5, 17 commits ahead, but **none of them touch `orchestration/`**, and the master is byte-identical on both.
- Root `.claude/skills` file: identical on HEAD and origin/main.

## 1. The patch set (ONE per repo), verified to apply on the current HEADs

| repo | file | size | sha256 |
|---|---|---|---|
| orchestrator | `patches/orchestrator/stackchg-dflash2-20261003.orchestrator.patch` | 21 files, +1120/−83 | `040561a5…91e9` |
| research | `patches/research/stackchg-dflash2-20261003.research.patch` | master registry, +118/−42 | `5996c660…5168` |
| root | `patches/root/stackchg-dflash2-20261003.root.patch` | change-topology `topology_check.py`, +3/−1 | `986dead1…b031` |

**Proof of apply:** `sandbox-pristine/` was built with `git archive HEAD` of orch 99e3e5fe plus the research master at 7b9bc565, using `tools/build_sandbox.sh`. Both patches pass `git apply --check` and apply. Everything in §3–§5 was run on that tree (`tools/verify.sh`).

**Reconciliation of the two 10-01 packages.** The drafter-compile design (topology selection) is the base. From dflash2-27b it keeps the VRAM arithmetic, the fail-closed compile check and the `-ngld` attestation. Additions from this run are marked NEW.

**Research master (`orchestration/model_registry.yaml`):**
- `roles.qwen38_27b_q8_local.drafters`:
  - `mtp`: draft-mtp, self, n-max 4.
  - `dflash2`: draft-dflash, DFlash2-Q8_0, n-max 8, ngld 99, plus the recipe and ruling refs.
- Hand-carried drafter fields are deleted from:
  - `server_mode.architect_critic`: the top-level `draft_model` and the `acceleration`.
  - `roles.architect_critic`.
  - Both `ingest_long_context` rows.
- `challenger_under_evaluation` becomes `SUPERSEDED_BY_drafters.dflash2`.
- **Canonical `speculative_decoding_policy`** (trust boundary, see §8):
  - `production_recipe: draft-mtp` becomes `default_spec_type: draft-mtp`, documentation scoped to n-gram composition.
  - The statement is rewritten.
  - NEW: `exceptions.ingest_long_context` is closed. It was the stale Qwen3-Next row, flagged in three places.
  - NEW: `amended_on` and `amended_by_receipt` are recorded.
- NEW: `server_mode.architect_critic.serving_shape.vram_non_kv_gib` goes 32.80 → **37.92 MEASURED**, with `vram_non_kv_drafter: dflash2`:
  - Source: KFD on live PID 3737649, 44.30 and 44.297 GiB at 04:32:13Z and 04:32:50Z, after at least one served request, minus 6.38 GiB KV.
  - It is a runtime reading, so it is conservative against the gate's load-time convention.
  - The derived estimate of 36.34 was 1.58 GiB low.
- NEW (vision):
  - `server_mode.worker_vision`: `tier: warm`, `device: none`, `memory_gb: 18.3`. The throughput is annotated as the MI210 figure.
  - `roles.worker_vision` and `roles.vision_escalation`: `serving.device: none`, `n_gpu_layers` removed, `memory.residency: warm`.
  - `process_layout`: both move from `hot_resident` to `warm_mmap`.
  - The GPU-only figures (`vram_mb`, `vram_non_kv_gib` 19.26, 112.20 t/s) are **kept** as the restore record for MI210 #2.

**Orchestrator:**
- `orchestration/stack_topology.yaml`:
  - `drafter_selection: {architect_critic: dflash2}`.
  - NEW: `numa_config.worker_vision` becomes `{cpu_shape: NUMA_HALF_A, port: 8086}`, with `numactl_policy: interleave=0,1` and `numa_pre_evict_gib: 40`. `gpu_host_lane` and `membind=3` are removed, and the old values are recorded in a comment.
- NEW: `orchestration/launch_manifest.yaml`: `role_launch_meta.worker_vision.tier: warm`, and both vision roles are removed from `hot_roles`. `port_map` is unchanged (8086).
- NEW: `stack_templates/default.yaml`: worker_vision becomes `tier WARM`, `numa HALF_A`, `threads 48`.
- `src/registry/drafter_selection.py` (new): `resolve`, `project`, `check_lean`.
  - NEW: it refuses a selection that differs from `serving_shape.vram_non_kv_drafter`. Flipping the drafter without re-deriving VRAM is a stale restatement.
- `registry_compiler.py`: the topology is a compile input, and its selection is in the cache key.
- `registry_validator.py`: runs `check_lean`.
- `autokernel_enrollment.py`: compiles against the pinned topology.
- `stack_priors.py`:
  - Spec is enabled for `draft-dflash`, `draft-simple` and `draft-eagle3`.
  - It projects `n_gpu_layers_draft`.
  - NEW: it **fails closed at compile** when an external-drafter type resolves to no drafter, or to the target file itself, which would otherwise launch with no `-md`.
- `orchestrator_stack.py`:
  - Emits `-ngld` beside `-md`.
  - NEW: `start_orchestrator` derives `ORCHESTRATOR_VISION_VL_BACKEND` from the vision tier: `server` when warm, `auto` when hot. An exported value wins. See §6.
- NEW: `stack_commands.py`: `_RUNTIME_FIELD_CHECKS["runtime.flags.spec.n_gpu_layers_draft"]` attests `-ngld`.
  - Without it, every speculating role's new `n_gpu_layers_draft` prior would have been reported "declared but nothing attests it".
- NEW: `scripts/registry/stack_change_pipeline.py`, two defects found by this run and fixed:
  - (a) **Step `serving_shape_capacity`.** `update` reported all-green over a lean that failed the import-time VRAM gate, because the pipeline had imported `stack_manifest` before rewriting the lean. A fresh-interpreter import now re-runs the gate on the lean the run wrote.
    - Measured: with VL still on the card, `update` was green while a fresh import raised `ROCm0 OVERSUBSCRIBED by 3.16 GiB`.
  - (b) **Lean BOOTSTRAP.** `stack_manifest` validates launcher↔lean parity at import, so a field both sides declare (here, the vision `tier`) could never be flipped: the lean that would fix the parity cannot compile, because compiling needs the import.
    - During `update` only, the lean step derives the active set from `launch_manifest.yaml` plus master `shared_with`, mirroring `_build_role_launch_meta`. A test pins equality with `ROLE_LAUNCH_META`.
    - It then compiles, and the later steps re-import against the fresh lean. `check` never takes this path.
- NEW: `orchestration/contention_matrix.yaml`: a **DECLARED WITHDRAWAL** (`tools/withdraw_contention_role.py`, same shape as the ARCHSWAP relabel).
  - worker_vision's 3 measured pairs described the old placement (184-191, -t 8). They were moved to `unknown_pairs` with reason `placement_withdrawn` and kept verbatim as comments.
  - The other stamped roles were asserted to have identical placement in base and candidate. The old stamp was recomputed from the base tree first.
  - `topology_hash` goes `5d772b2c4698b2ae` → `560d489bb6df16b9`. Matrix status is **OK** under the candidate topology.
  - Without this, the whole matrix reads STALE, and contention_gate QUEUEs every background request stack-wide until a re-bench.
- **Tests:**
  - New: `test_drafter_selection.py` (22) and `test_external_drafter_launch.py` (12).
  - New cases in `test_stack_change_pipeline.py` (capacity step ×3, bootstrap equality, step inventory) and `test_orchestrator_stack_reload.py` (VL backend ×3).
  - Re-pinned placement tests. Each says, in its own words, that a re-roster must fail it and move it. They were re-pinned at **the same strength** to the new intent (device `none`, NUMA_HALF_A cpuset, shape class `half`, -t 48, nodes {0,1}, pre-evict 40, warm cost 2.0, vision pairs declared unknown). No test was loosened or deleted.
- **Derived files are NOT in the patch.** Lean, descriptors, priors, procedure enums and summary are regenerated by phase 7 `update` (DERIVATION.md). For review, `evidence/derived-delta.GENERATED.diff` shows exactly what `update` writes.
  - **Only these roles' priors change:** `architect_critic`, `coder_escalation`, `ingest_long_context`, `qwen38_27b_q8_local`, `worker_vision`, `vision_escalation`.
  - Every other role gains only the inert `spec.n_gpu_layers_draft: null`.

**Root:** `.claude/skills/change-topology/scripts/topology_check.py` accepts `device: none` as CPU. `none` is the launcher's own CPU spelling (`_append_device_args`). Without this, the skill's check reports the vision move as a "registry-only device move" although the topology moved with it.

## 2. Rendered :8083 argv (compiled from the patched tree, `evidence/argv_8083.txt`)

```
/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
  --host 127.0.0.1 --port 8083 -np 4 -c 196608 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified
  --no-mmap -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
  -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 8
  --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic --device-draft ROCm0
```

- The unpatched render (`evidence/argv_8083-baseline.txt`) is byte-identical to the pre-change live MTP argv (PID 29330).
- The patched render replaces `--spec-type draft-mtp --spec-draft-n-max 4` with `-md …DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 8`. It has the **same flag set as the live fast-path PID 3737649**; the live process only orders `--device-draft` earlier.
- `kernels/production/gpu` resolves to `builds/gpu-20260921-ffc1bac82/bin`, the v10 store. The drafter GGUF is present (2,056,414,752 B).
- n-max 8 is clamped to 7 at load (DFlash2 `block_size 8`, WARN logged). The GDN ring is sized from the unclamped 8. 8 is kept because it is the measured recipe value.

On-demand :8086 argv (`evidence/argv_8086.txt`; `start` adds the topology prefix: cpuset 0-47,96-143, `numactl --interleave=0,1`, pre-evict 40 GiB/node):

```
/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/llama-server -m …/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf
  --mmproj …/mmproj-Qwen3-VL-30B-A3B-Instruct-F16.gguf --host 127.0.0.1 --port 8086 -np 1 -c 65536 -t 48
  --flash-attn on -ctk q8_0 -ctv q8_0 --device none --image-min-tokens 1024 --cache-ram 0
```

## 3. Preflight report (phase 3)

`stack_change_pipeline.py check` on the scratch (`evidence/pipeline-check.txt`) reports:
- Every compile and guard step `ok`: numa_mode, shared_with_derivations, lean_registry, descriptors, stack_priors, procedure_enums, operator_summary, guard, guard_strict, reasoning_effort_certifications, **serving_shape_capacity (new)**, stack_manifest_registry, q_scorer_priors and declared_env_attestation.
- `guard_all_surfaces`: 13 warnings, identical to the baseline.
- `runtime_attestation`: 4 errors.

The baseline (unpatched HEAD vs the same live fleet) is fully green: "acceptance: no-inference checks passed" (`evidence/pipeline-check-baseline.txt`).

The skill classifier (`tools/preflight_scratch.sh`, the skill's `preflight.sh` repointed at the scratch) puts the 13 remaining unmatched lines into needs-operator, exit 5 (`evidence/preflight-classified.txt`). All 13 are pre-existing warnings. Reclassified per the skill's definitions:

| # | line(s) | class | disposition |
|---|---|---|---|
| 1–4 | (earlier run, vs MTP PID 29330) four `runtime_attestation` drift lines for `-md`, `spec.type`, `draft_max`, `-ngld` | expected pre-relaunch drift | **GONE.** Re-run at 04:3xZ against the live fast-path PID 3737649: `runtime_attestation: ok`, `summary: ok`, `acceptance: no-inference checks passed` (`evidence/pipeline-check.txt`) |
| 5–17 | 13 `hardcoded_surface` warnings (retired-role strings in tests and docs) | pre-existing | Byte-identical in the baseline check; not this change |
| — | fixable-by-transform | **0** | — |

Not visible to the pipeline but required by the skill:
- **needs-measurement** (none blocks apply, all are queued post-bring-up, see §7.4):
  - M-1: DFlash2 has **never been served at the production shape** (np 4 / 196608 / q8_0 KV / kv-unified). The nearest runs were ctx 16384 f16, 65536 f16, and DF2-5 4096×np. Needed: coherence at production prompt length, speed paired with a correctness check, and acceptance rate.
  - M-2: **largely DONE.** 37.92 is MEASURED on live PID 3737649 (two persistent KFD samples, runtime). Still owed: the load-time PEAK, sampled DURING a load. The gate convention is load-time, so 37.92 is conservative.
  - M-3: Qwen3-VL-30B on CPU (NUMA_HALF_A, -t 48) has no throughput or quality evidence. The only CPU runs are K35 2026-07-17 at -t 96. Measure it the first time it is started on demand, in a window that does not overlap a DS41 CPU A/B.
  - M-4: Re-bench worker_vision's contention pairs before it ever becomes a hot role again.
- **needs-operator:** §8 (the trust-boundary items).

Sub-skill assertions on the scratch:
- `change-topology/topology_check.py --intent`: **PASS**, with the root patch applied. Unpatched, it fails only on `device='none'` (see §1, root).
- `change-role/assert_alias_clean.py --all`: **PASS** (9 aliases).
- `change-topology/capacity.sh`: **CAPACITY PASS**.
- `retire-model`: not invoked. Nothing is retired.

## 4. Capacity report: both legs, per instance (`evidence/capacity.txt`, `evidence/capacity_sh.txt`)

| role | port | shape class | leg | n_ctx | KV GiB | non-KV | host weights |
|---|---|---|---|---|---|---|---|
| architect_critic | 8083 | gpu_host_lane | **GPU** | 196608 | 6.38 | **37.92 measured** (was 32.80) | 27 (counted on host too, pre-existing) |
| architect_general | 8074 | full | host | 262144 | 24.00 | — | 90 |
| frontdoor | 8070 / 8080 / 8180 | full / half / half | host | 262144 | 2.66 each | — | 37 each |
| worker_vision | 8086 | **half** (was gpu_host_lane) | **host** | 65536 | 3.19 | 19.26 (kept, unused) | **18.3** (was 0) |

| leg | baseline (live config) | candidate | verdict |
|---|---|---|---|
| **GPU ROCm0** | 61.62 / 62.00 GiB (architect_critic 39.18 + worker_vision 22.45) | **44.30 / 62.00** (architect_critic only) | PASS, 17.70 GiB slack |
| **host RAM** | 232.97 / 1069.42 GiB | **254.46 / 1069.42** (219.30 weights + 35.16 KV) | PASS. The warm vision is counted, conservatively |

- **Live cross-check (read-only KFD):**
  - The MTP 27B, PID 29330, holds 39.15 GiB against the declared 32.80 + 6.38 = 39.18. The old figure is confirmed live.
  - The DFlash2 27B, PID 3737649, holds **44.30 GiB** (04:32Z, two samples). That equals the declared 37.92 + 6.38.
  - :8086 is stopped. The card is 44.31 / 63.98 used.
- **Superseded derived DFlash2 delta** (dflash2-27b PACKAGE §4), which gave 36.34 load-time non-KV:
  - MTP draft context freed: −1.70
  - DFlash2 weights: +1.90
  - Drafter iSWA KV: +0.20
  - Drafter graph @ub 2048 (UNMEASURED): +0.60
  - Hidden-state extraction: +0.20
  - GDN ring at n-max 8 vs 4: +2.34
- That predicted ≈ 43.3–44.5 GiB at runtime; 44.30 was measured. With the VL also on the card it would need 66.75 GiB against a 62.00 budget.

## 5. Tests (phase 3)

Run serially, no xdist, to stay light while DS41 runs. Results are in `evidence/tests.txt` (candidate = HEAD + patches) and `evidence/tests-baseline.txt`.

| set | baseline (HEAD) | candidate |
|---|---|---|
| promotion-gate targets: simulated_fixtures, build_server_command_helpers, 4× seeding | 202 passed | **202 passed** |
| related: pipeline, compiler, priors, validator, orchestrator_stack ×4, stack_manifest, guard, template parity, stack_numa ×3, contention ×5, topology, vision ×3 | 713 passed | **723 passed** (10 new) |
| new: `test_drafter_selection.py` + `test_external_drafter_launch.py` | n/a | **34 passed** |

**gitnexus blast radius** (`gitnexus impact <sym> --direction upstream --repo /mnt/raid0/llm/epyc-orchestrator`). The index is STALE: it was built from the `/workspace/repos` checkout at 3fb01cc. It was **not** re-indexed, because the analyze writes into the real tree and loads the CPU during DS41 A/Bs. Every edited symbol predates the index.

| symbol | risk | impacted | note |
|---|---|---|---|
| `stack_priors._launch_runtime_record` | ⚠ **HIGH** | 6 | Reaches `_serving_record`, `_role_record`, `compile_stack_priors` and the guard's `validate_launch_manifest_serving_alignment`, i.e. every role's launch record. **Mitigation, measured:** the compiled priors change ONLY for the six intended roles (all others gain only `n_gpu_layers_draft: null`); guard and guard_strict are green; 202 + 723 + 34 tests pass. |
| `registry_compiler.compile_lean` / `load_or_compile` / `cache_key` | LOW | 6 / 6 / 5 | process `cmd_start` |
| `registry_validator.validate_all` | LOW | 8 | `cmd_start` |
| `orchestrator_stack._append_runtime_spec_args` | LOW | 4 | `start_server` |
| `orchestrator_stack._append_spec_decode_args` | LOW | 7 | — |
| `stack_change_pipeline.run_stack_change_pipeline` | LOW | 2 | — |
| `start_orchestrator` | LOW | 0 | — |
| `_lean_registry_step`, `_RUNTIME_FIELD_CHECKS` | not in index | — | covered by the pipeline tests |

## 6. Vision routing while :8086 is cold

- Every image request routes to `worker_vision` (`routing_decision.py:277`).
- `chat_vision` tries :8086 as worker_vision, then as the vision_escalation alias, then POSTs `/vision/analyze`.
- `_FALLBACK_MAP[WORKER_VISION] = []`. There is **no infrastructure fallback**: no other served model has vision, and escalation goes to the text-only 27B.
- **Today (`auto`):** `/vision/analyze` silently spawns `llama-mtmd-cli` **per request**. That loads the full 30B plus mmproj on **unpinned** CPU cores at -t 8 with a 120 s timeout. It is an undeclared CPU tenant landing on whatever cores the scheduler picks, the DS41 A/B windows included.
- **With this package:** while worker_vision is not HOT, the API is launched with `ORCHESTRATOR_VISION_VL_BACKEND=server`. Image requests **fail fast** ("All vision paths failed") instead of degrading that way.
  - To serve images, start the cold server: `orchestrator_stack.py start --only worker_vision`.
  - To opt back into the ad-hoc CLI, export `ORCHESTRATOR_VISION_VL_BACKEND=auto` before `reload orchestrator`. This is an operator choice, see A-4.
- `/health` fallback probes no longer list the vision roles (removed from `hot_roles`), so a deliberately stopped :8086 does not alarm.

## 7. Phase 7 (apply) and phase 8 (bring-up)

**Run only after the receipt exists.** Owner: the session that owns :8083 inference. That owner performs every reload at its own boundary. Never run `start --dry-run`.

### 7.1 Apply (phase 7)

```bash
P=/mnt/raid0/llm/tmp/stack-change-dflash2-20261003
test -f /workspace/artifacts/operator/receipts/RATIFY-STACKCHG-DFLASH2-20261003.json || { echo "NOT SIGNED"; exit 1; }
bash $P/ratify_stackchg_dflash2_20261003.sh --validate-only            # re-verifies pins + applicability

# research (local main is 17 behind origin; none touch orchestration/)
cd /mnt/raid0/llm/epyc-inference-research && git fetch origin && git merge --ff-only origin/main
git apply --check $P/patches/research/stackchg-dflash2-20261003.research.patch
git apply         $P/patches/research/stackchg-dflash2-20261003.research.patch
git commit -m "registry(STACKCHG-DFLASH2-20261003): drafters list + DFlash2 VRAM; VL-30B cold CPU; amend speculative_decoding_policy" -- orchestration/model_registry.yaml
RES_C1=$(git rev-parse HEAD)

# orchestrator
cd /mnt/raid0/llm/epyc-orchestrator && git fetch origin && git merge --ff-only origin/main
git apply --check $P/patches/orchestrator/stackchg-dflash2-20261003.orchestrator.patch
git apply         $P/patches/orchestrator/stackchg-dflash2-20261003.orchestrator.patch
git add src/registry/drafter_selection.py tests/unit/test_drafter_selection.py tests/unit/test_external_drafter_launch.py
git commit -m "stack(STACKCHG-DFLASH2-20261003): DRAFT-SEL-1 drafter selection; DFlash2 on :8083; VL-30B cold CPU; capacity step + lean bootstrap; contention withdrawal" -- \
  orchestration/stack_topology.yaml orchestration/launch_manifest.yaml orchestration/contention_matrix.yaml stack_templates/default.yaml \
  src/registry/drafter_selection.py src/registry/registry_compiler.py src/registry/registry_validator.py src/registry/stack_priors.py \
  scripts/registry/stack_change_pipeline.py scripts/server/autokernel_enrollment.py scripts/server/orchestrator_stack.py scripts/server/stack_commands.py \
  tests/unit/test_drafter_selection.py tests/unit/test_external_drafter_launch.py tests/unit/test_build_server_command_helpers.py \
  tests/unit/test_orchestrator_stack_reload.py tests/unit/test_orchestrator_stack_threads.py tests/unit/test_scheduling_contention.py \
  tests/unit/test_stack_change_pipeline.py tests/unit/test_stack_numa_evict.py tests/unit/test_stack_priors_compiler.py
ORCH_C1=$(git rev-parse HEAD)

uv run python scripts/registry/stack_change_pipeline.py update      # EXPECT: lean BOOTSTRAP warn; serving_shape_capacity ok;
                                                                    #   runtime_attestation = ONLY the 4 :8083 drift lines (§3)
uv run python -c "import scripts.server.stack_manifest"             # import-time gates on the new lean: must be silent
uv run pytest -q tests/unit/test_drafter_selection.py tests/unit/test_external_drafter_launch.py \
  tests/unit/test_stack_change_pipeline_simulated_fixtures.py tests/unit/test_build_server_command_helpers.py \
  tests/unit/test_seeding_infra.py tests/unit/test_seeding_infra_additional.py tests/unit/test_seeding_infra_branching.py \
  tests/unit/test_seed_specialist_routing_main_and_retry.py; echo "pytest rc=$?"     # capture rc; do not pipe
git commit -m "derived(STACKCHG-DFLASH2-20261003): regenerate lean, descriptors, stack_priors, summary" -- \
  orchestration/model_registry.yaml orchestration/model_descriptors.yaml orchestration/derived/stack_priors.yaml \
  docs/generated/current_stack_summary.md orchestration/procedures orchestration/procedure.schema.json
ORCH_C2=$(git rev-parse HEAD)

# root
cd /workspace && git apply $P/patches/root/stackchg-dflash2-20261003.root.patch && \
  git commit -m "skills(change-topology): device none is CPU (STACKCHG-DFLASH2-20261003)" -- .claude/skills/change-topology/scripts/topology_check.py
ROOT_C1=$(git rev-parse HEAD)
```

Push each repo with its push lock (`coordination/push-locks`) and pathspec-limited commits. Copy this package directory into `/workspace/artifacts/operator/stack-change-dflash2-20261003/` in the root wrap-up commit.

### 7.2 Bring-up (phase 8)

**Now (04:32Z):**
- :8083 already runs the target argv (PID 3737649).
- :8086 is stopped.
- The stack state file still records the dead MTP PID 29330 for :8083. Runtime attestation resolves the listener by port, so it attests 3737649 as ok.

Required steps after apply:
- **(d)** `reload orchestrator`: picks up the new lean and priors and `VL_BACKEND=server`.
- **(c)** `reload architect_critic`: RECOMMENDED at the owner's next boundary. It brings :8083 back under the stack's own launch, re-registers state, and is the only proof that the STACK (not a fast path) renders this argv. It is not urgent, because the live argv already matches.
- (a) is a no-op unless something listens on :8086 again.

```bash
cd /mnt/raid0/llm/epyc-orchestrator
# (a) :8086 — already DOWN as of 2026-10-03T04:28Z. If anything listens again:
ss -ltnp 'sport = :8086'   &&   uv run python scripts/server/orchestrator_stack.py stop server_8086
# (b) VRAM sampler armed BEFORE the reload (observation window); capture its PID yourself
( while :; do date +%T.%N; cat /sys/class/drm/card2/device/mem_info_vram_used; sleep 0.5; done ) \
    > /mnt/raid0/llm/tmp/stack-change-dflash2-20261003/vram_during_reload.log 2>&1 & SAMPLER=$!
# (c) relaunch ONLY the :8083 llama-server (aliases ride it; do not stop autopilot)
uv run python scripts/server/orchestrator_stack.py reload architect_critic
# (d) API reload so it picks up the new lean/priors and ORCHESTRATOR_VISION_VL_BACKEND=server
uv run python scripts/server/orchestrator_stack.py reload orchestrator
kill $SAMPLER; ps -p $SAMPLER || echo "sampler stopped"
```

### 7.3 Serving-proof checklist (all must hold; `healthy` is not proof)

1. **New process:** `PID=$(ss -ltnp 'sport = :8083' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)`. It must not be 29330. Check `ps -o lstart= -p $PID`.
2. **argv:** `tr '\0' ' ' < /proc/$PID/cmdline` equals §2 byte-for-byte. It must contain `-md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf`, `-ngld 99`, `--spec-type draft-dflash`, `--spec-draft-n-max 8` and `--device-draft ROCm0`. It must not contain `draft-mtp`.
3. **Binary and store:**
   - `readlink /proc/$PID/exe` gives `/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server`.
   - `bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh` passes on it.
   - Thread affinity is 184-191: `grep Cpus_allowed_list /proc/$PID/task/*/status`.
   - Do not check `/proc/$PID/maps` for DFlash2. Under `--no-mmap` the drafter is read, not mapped, so the live PID 3737649 shows 0 maps hits. Use the load log instead (item 4).
4. **Load log** (`logs/llama-server-8083.log`, last block) shows:
   - `adding speculative implementation 'draft-dflash'`
   - `block_size=8 … n_extract=5`
   - the n-max clamp WARN
   - `n_slots = 4, n_ctx_slot = 196608, kv_unified = 'true'`
   - no `failed to load draft model`
5. **`/slots`:** `curl -s localhost:8083/slots` lists 4 slots with n_ctx 196608 and speculative type draft-dflash.
6. **Real completion** through an alias, with a generous budget (thinking bills the same budget):
   `curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"coder_escalation","messages":[{"role":"user","content":"Write a Python function that returns the n-th Fibonacci number iteratively, then explain it in two sentences."}],"max_tokens":4096}'`
   The content must be non-empty and correct. The server log must show `draft acceptance` for it.
7. **VRAM residency:**
   - KFD `/sys/class/kfd/kfd/proc/$PID/vram_*` sum is non-zero, about 41–44 GiB.
   - `vram_during_reload.log` shows the load-time peak, sampled during the load.
   - Card free is at least 2 GiB.
8. **Attestation:** `uv run python scripts/registry/stack_change_pipeline.py check --run-promotion-gate` reports `runtime_attestation: ok`, `serving_shape_capacity: ok`, `promotion_gate: ok`, and acceptance passed.
9. **Vision cold:**
   - Nothing listens on :8086.
   - `tr '\0' '\n' < /proc/<api pid>/environ | grep VL_BACKEND` gives `server`.
   - One image request fails fast and does not spawn `llama-mtmd-cli`. Check with `ps --ppid <api pid>` and the API's own children only.

### 7.4 First window after bring-up (needs-measurement, owner's inference)

- M-1/M-2:
  - Coherence gate at production prompt length.
  - Speed paired with correctness: MTP vs DFlash2 at the production shape.
  - Replace `vram_non_kv_gib` with the measured load-time figure and the derivation.
  - Measure n-max 7 vs 8: 7 saves 0.58 GiB with identical drafting.
- M-3: Only when the operator starts :8086, measure CPU VL decode and MMMU parity in a non-DS41 window.
- Belief-kernel wiring (CLAUDE.md): the DFlash2 production-shape measurement and the VL CPU measurement are new measurement sources. Add an adapter row and task when they are produced.

## 8. Trust-boundary items the operator signs (phase 6)

The receipt `acknowledged` block lists each item:
- **A-1 Canonical block amended.**
  - `speculative_decoding_policy`, master L86-315: `canonical: true, ratified_by: operator, ratified_on: 2026-07-31`. It is the only block in the master carrying those fields.
  - `production_recipe: draft-mtp` becomes `default_spec_type: draft-mtp` (n-gram composition scope).
  - The statement is rewritten.
  - `exceptions.ingest_long_context` is closed.
  - `amended_on` and `amended_by_receipt` are added.
  - No code enforces ratification of this block; it is passed through to the lean only. The receipt is the record.
- **A-2 Reverses the 2026-09-22 ruling** "BOTH GPU ROLES STAY ON THE CARD". It is recorded only in prose, in the master `server_mode.worker_vision` and `server_mode.architect_critic.serving_shape` comments. Vision is off the MI210 until MI210 #2.
- **A-3 Cold-CPU vision cpuset.** When started it runs on cores **0-47 + SMT siblings 96-143** (NPS4 nodes 0,1), -t 48, `numactl --interleave=0,1`, pre-evict 40 GiB/node.
  - It is never started by a default `start`.
  - When started it **overlaps frontdoor :8070 (0-95) and :8080 (half A)**.
  - The DS41 A/B cpuset was not found in the orchestrator declarations. **The operator should confirm it does not overlap 0-47/96-143**, or name another set. NUMA_HALF_B is excluded because it contains the 27B's host lane 184-191.
- **A-4 Vision refuses while cold** (`VL_BACKEND=server` derived from tier) instead of the silent, unpinned per-request `llama-mtmd-cli` 30B fallback. The alternative is `auto`, which keeps degraded image answers but puts an ad-hoc CPU tenant on unpinned cores. Recommended: refuse.
- **A-5 VRAM figure 37.92 GiB is MEASURED at runtime on live PID 3737649**; the load-time peak is not sampled. Speed paired with correctness at the production shape is still owed (M-1). The margin is 17.70 GiB.
- **A-6 Contention matrix declared withdrawal:** 3 vision pairs move to `unknown_pairs`, and the stamp goes 5d772b2c → 560d489b. **This is not a re-measurement.**
- **A-7 Orchestrator code changes:**
  - DRAFT-SEL-1 compiler and launcher.
  - Pipeline capacity step and lean bootstrap.
  - VL-backend derivation.
  - `-ngld` attestation.
  - gitnexus HIGH on `_launch_runtime_record` (§5), with the measured mitigation.
- **A-8** n-max 8 is kept; the kernel clamps it to 7 and logs a WARN.

**Signature mechanism:**
- A TTY-gated ratify script, `ratify_stackchg_dflash2_20261003.sh`, shaped like ARCHSWAP/RI-23a. It differs in that there are no lanes, because this run made no git writes. Instead it re-checks that each patch still `git apply --check`s on the current working trees.
- It pins sha256 values and writes ONE receipt to `/workspace/artifacts/operator/receipts/RATIFY-STACKCHG-DFLASH2-20261003.json`, with a copy in `receipts/` here.
- It applies nothing.
- **The operator runs it in a separate terminal, never chained with `&&` and never under a `!` command:**

```
RATIFY_OPERATOR="<your name>" bash /mnt/raid0/llm/tmp/stack-change-dflash2-20261003/ratify_stackchg_dflash2_20261003.sh --attest RATIFY-STACKCHG-DFLASH2-20261003
```

## 9. Rollback (a `git revert` set; no symlink changes, the kernel store is untouched)

```bash
cd /mnt/raid0/llm/epyc-orchestrator && git revert --no-edit $ORCH_C2 $ORCH_C1      # derived first, then sources+code
cd /mnt/raid0/llm/epyc-inference-research && git revert --no-edit $RES_C1
cd /workspace && git revert --no-edit $ROOT_C1                                     # optional (checker-only)
cd /mnt/raid0/llm/epyc-orchestrator && uv run python scripts/registry/stack_change_pipeline.py update
# the lean BOOTSTRAP covers the reverse tier flip (warm -> hot) too
uv run python -c "import scripts.server.stack_manifest"                            # must import (VL back on GPU: 61.62/62.00)
uv run python scripts/server/orchestrator_stack.py reload architect_critic          # back to draft-mtp n-max 4
uv run python scripts/server/orchestrator_stack.py start --only worker_vision       # VL back on MI210 :8086 (tier hot again)
uv run python scripts/server/orchestrator_stack.py reload orchestrator              # VL_BACKEND back to auto
```

Order matters on rollback. Revert and `update` BEFORE `start --only worker_vision`: the reverted lean puts the VL back on the GPU leg, and with DFlash2 still resident the card would not fit it. The rollback argv for :8083 is `evidence/argv_8083-baseline.txt`, which equals the live PID 29330 argv.

## 10. Files

- `PACKAGE.md` (this file), `intent.yaml` and `ratify_stackchg_dflash2_20261003.sh`.
- `patches/{orchestrator,research,root}/*.patch`.
- `evidence/`:
  - pipeline update and check, baseline and candidate
  - classified preflight
  - capacity for both trees, and the skill's `capacity.sh`
  - argv for :8083 (baseline and candidate) and :8086
  - tests for both trees
  - topology_check and assert_alias_clean
  - gitnexus impact
  - contention withdrawal log
  - live state
  - `derived-delta.GENERATED.diff` (review only; regenerated at apply)
- `tools/`: `build_sandbox.sh`, `vision_transform.py`, `update_test_pins.py`, `withdraw_contention_role.py`, `make_patches.sh`, `verify.sh`, `run_tests.sh`, `capacity_report.py`, `render_argv.py` and `preflight_scratch.sh`.
- `scratch/`: the skill's `scratch.sh` output (`PROVENANCE.json`).
- `sandbox-{base,new,pristine}/`: `git archive` trees, where pristine is current HEAD + patches. They are disposable once signed.

Observed but out of scope, not fixed here:
- `sync_procedure_role_enums._replace_schema_permission_enum_text` corrupts a single-line JSON enum. Only test fixtures use that form.
- The orchestrator gitnexus index is stale (3fb01cc).
- `stack_topology.architect_general.spec_overrides` still describes the pre-ARCHSWAP critic, a second argv writer (drafter-compile DESIGN §7).
