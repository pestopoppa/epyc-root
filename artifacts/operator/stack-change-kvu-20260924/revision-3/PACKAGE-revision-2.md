# GPU-residency change set: one package for signature

**Date**: 2026-09-24, revision 2 (operator direction ~18:10Z) · **Skill**: stack-change phases 0–5 · **Status**: READY FOR SIGNATURE, with one parameter open (whisper cores, N-B)
**Scratch**: `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/v2/`. The research registry is at `v2/reg`; the orchestrator clone is at `v2/full-orch` (base `ff67bbec`).
**Supersedes** the -kvu-only package, now `patches/v1/PACKAGE-v1.md`.

**Safety of preparation**: no real tree, live service or `~/.config/opencode` file was modified. I started, stopped or signalled nothing.
Live reads were read-only: `/proc/<pid>/cmdline`, KFD `vram_57300`, `rocm-smi`, `GET /props`.
The scratch pipeline's `runtime_attestation` step probes live PIDs with signal 0, which is an existence check that delivers nothing.

**Lock check**: no `push-*.json` is held and no stack-change or promotion is running. A `wrapup-*` lease is held; it is not a region or push lock.

---

## 0. Intent

```yaml
topology:
  architect_general:              # :8083 Qwen3.8-27B Q8_0, MI210; aliases ingest_long_context, coder_escalation
    slots: 4                      # was 2
    n_ctx: 196608                 # unchanged; ONE unified pool
    kv_unified: true              # NEW, emitted explicitly as --kv-unified
    draft_max: 4                  # was 8 (--spec-draft-n-max)
    ubatch: 2048                  # K4, already committed (-ub 2048)
    cache_ram: 65536              # NEW --cache-ram
  frontdoor:        {cache_ram: 32768}   # :8070 (+ :8080/:8180 halves, role-level)
  architect_critic: {cache_ram: 32768}   # :8074 (operator range 16384-32768; upper end)
aux:
  whisper:                        # :9000 -> CPU
    argv: [-ng, -t <THREADS>]
    env: {HIP_VISIBLE_DEVICES: "-1"}
    cpuset: <CPUSET>              # PARAMETER, filled from the option-C result (N-B)
```

## 1. Resulting argv (built from the scratch priors, `v2/expected-argv.txt`)

```
:8083  …/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m …/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 8083
       -np 4 -c 196608 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all
       --cache-ram 65536 --chat-template-file …/epyc-qwen3x-v1-terse.jinja --spec-type draft-mtp --spec-draft-n-max 4
       --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_general
:8070  … -np 4 -c 262144 -t 96 … --cache-ram 32768 …        (the :8080/:8180 halves are identical except -np 1 -t 48)
:8074  … -np 1 -c 262144 -t 96 … --cache-ram 32768 …
:9000  taskset -c <CPUSET> /mnt/raid0/llm/whisper.cpp/build/bin/whisper-server -m …/ggml-large-v3-turbo.bin --host 127.0.0.1
       --port 9000 --inference-path /v1/audio/transcriptions -t <THREADS> -ng
       env HIP_VISIBLE_DEVICES=-1, LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin:/opt/rocm/lib (replace mode, linkage check kept)
```

Two differences from the operator's argv:
- **No `-ctkd q8_0 -ctvd q8_0`.** See N-A.
- **No `--device-draft ROCm0`.** The committed priors already dropped it, and it is inert without `-md`.

Checked read-only against the live :8083 restarted at 18:19:57Z (PID 1887789). The new attestation reports exactly the four intended changes:
- `slots expected 4; live 2`
- `kv_unified expected True; live False`
- `spec.draft_max expected 4; live 8`
- `cache_ram expected 65536; live no --cache-ram`

## 2. Patch set (`patches/v2/`)

| File | Repo | Content |
|---|---|---|
| `research-gpu-residency.patch` | research `model_registry.yaml` | Declares `serving_shape.kv_unified: true` and corrects the false "KV IS UNIFIED" banner (root cause below). `slots 2→4` on architect_general and the ingest compat scalar. `draft_max 8→4` in all 5 restatements (server_mode ×2, roles ×2, and `k:` alias). `cache_ram` on architect_general 65536, frontdoor 32768, architect_critic 32768. `vram_non_kv_gib 27.33 → 32.80` as a load-time figure, UNVALIDATED until bring-up. `voice_server` → `device: cpu`, `vram_gib 0`, latency 2 s. The O-2 declaration is deliberately absent, with the reason recorded in place. np=1 recipe note on `qwen38_27b_q8_local` |
| `orchestrator-gpu-residency.TEMPLATE.patch` | orchestrator | **kv_unified**: compiled by `stack_priors`, emitted by the launcher in both directions, attested by `_live_kv_unified()`, which resolves the flag the way the server does. **draft KV types** (`-ctkd/-ctvd`): plumbing only, inert unless declared. **`AuxService.cpuset`**: honoured verbatim; the bench guard may refuse it but never re-pin it; malformed values fail only that service at launch. **whisper CPU entry**. **Template `spec_overrides.draft_max 8→4`**. 30 new tests; 232 pass across the 5 affected suites |
| `fill-whisper-layout.sh` + `whisper-measured-safe-layouts.txt` | helper | Writes the concrete `orchestrator-gpu-residency.patch` from the template. It **refuses** any (threads, cpuset) pair not marked `CORUN-OK`. No pair is `CORUN-OK` yet (N-B). An unfilled template placeholder also fails safe: whisper refuses to launch, and since it is `optional` nothing else is affected |
| `opencode-OPERATOR-ACK-limit.patch` | `~/.config/opencode/opencode.jsonc` | `limit: {context: 196608, output: 32768}` on `qwen-gpu/qwen3.8-27b`. The file is outside containment, so the operator applies it; restart opencode afterwards |
| `PREVIEW-derived-after-update.diff` | — | What `update` produced in scratch. Never apply it; phase 7 regenerates it |

Surfaces not touched:
- `stack_topology.yaml`, `stack_numa.py`, `launch_manifest` port and role blocks, `models.py`, `roles.py`: no placement, port or role change, and no cpuset change for any llama-server.
- `kernels/production/*`: unchanged. The same frozen binaries are used, with whisper running its binary in CPU mode.
- `slots` is **not** duplicated into `serving_shape`, because it is already the `-np` declaration.

## 3. Root cause of the old kv_unified mismatch (unchanged from v1, verified)

- The server defaults `n_parallel` to −1 (`common/arg.cpp:1216`). Only auto becomes `np=4` **and** `kv_unified=true` (`tools/server/server.cpp:145-150`); otherwise it defaults to false (`common/common.h:580`).
- The orchestrator always passes `-np`, so production was never unified.
- The registry's claim came from bench launches: some omitted `-np`, and the 2026-08-20 run passed `--kv-unified` by hand.
- The MTP draft context inherits the flag (`common/speculative.cpp:2808` → `:2867` → `common/common.cpp:1692`).

## 4. Capacity report

### GPU leg (MI210, 65,520 MiB usable)

| Source | Scope | MiB |
|---|---|---:|
| **measured** load-only (`q38_27b_q8_loadonly`) | current np2/split/d8 | 39,018 |
| **measured** load-only | np4/196k/kvu/**q8 draft**/d4 | 40,522 |
| **derived** (see N-A) | np4/196k/kvu/**F16 draft**/d4, i.e. this package | **40,114** |

The derived row reproduces the load-only table to within 29 MiB. The np2→np4 step is exactly 2 × 5 × 149.6 MiB of GDN state, and the 196k→262k step is exactly 3,336 MiB.

| Resident (after the change) | MiB | basis |
|---|---:|---|
| :8083 27B np4 kvu d4, at load | 40,114 | derived from measured |
| + first-execution growth | +567 | measured on the live split process (KFD 39,585 vs its load-only twin 39,018) |
| :8086 VL-30B | 22,869 | KFD, fresh load 18:21Z |
| driver/other | ~45 | measured |
| whisper :9000 | **0** | moves to CPU (was 2,127–2,230) |
| **projected free** | **≈ 1,925 (1.88 GiB)** | with O-2 instead: ≈ 1,517 (1.48 GiB), matching the operator's +1.5 |

TTS (:9002, 2.62 GiB) remains declared-not-running and still cannot fit on the GPU. This is pre-existing, and the change set does not make it worse.

**Declared gate** (`stack_manifest.validate_serving_shape_capacity`, 64.00 capacity − 2.00 first-execution headroom = 62.00):

| Configuration | Gate result |
|---|---|
| This package | architect 39.17 + VL 22.45 = **61.62 → PASS** (0.38 margin) |
| With O-2 | 62.02 → **FAIL** by 0.02 (load-time basis); 62.57 if first-execution growth is counted |

**The gate runs at import of `stack_manifest`, so a failing lineup takes the launcher and the pipeline down with it.** This happened in scratch: the lean compile could not recompile its way out.

Host leg: 232.97 / 1069.42 GiB, PASS. `--cache-ram` is not in the host model. The worst-case total is +64 (:8083) +96 (frontdoor ×3) +32 (:8074) = 192 GiB of on-demand prompt cache, against about 840 GiB available.

### Shared pool and consequences
- 4 slots share one 196,608-token pool. Admission checks only `slot.n_ctx` (196,608) (`server-context.cpp:3303-3310`).
- When concurrent requests exhaust the pool, the server purges idle slots, halves the batch, and finally fails **all** in-flight requests with `decode() failed: Context size has been exceeded.` (`:3759-3801`, `:2949-2951`). The study's poolfull arms reproduced this: unified np2 c4096 gave 1 error in each of 3 runs.
- The caller-side handling is **the overflow work landing separately**; this package does not duplicate it.
- Under kvu, idle slots are saved to the RAM prompt cache and **cleared** from VRAM on each new task (`:2469-2482`). That is why `--cache-ram 65536` matters: it is where warm prefixes of the 4 slots now live.

## 5. Preflight: ONE classified list

This is the scratch pipeline `update` run on the v2 clone (`v2/pipeline-update.txt`). Results:
- green: `lean_registry`, `descriptors`, `stack_priors`, `procedure_enums`, `summary`, `guard`, `guard_strict`, `stack_manifest_registry`, `q_scorer_priors`
- warnings only: `guard_all_surfaces`
- `runtime_attestation`: 14 "unmanaged listener" lines. **This is a scratch artifact**: `STATE_FILE` resolves to the clone's own nonexistent `logs/`. The attestation that matters was run directly against the live :8083; see §1.

`topology_check.py`: PASS, since the topology is unchanged. The N-6 pre-existing blockers from v1 are **resolved upstream** (`ff67bbec`, promotion gate strict green).

- **fixable-by-transform: 0.**
- **needs-measurement (at bring-up, post-sign):**
  - **M-1**: :8083 buffers and VRAM. Read the `-lv 4` buffer lines and KFD at load and **during** a >98k request, then replace the UNVALIDATED `vram_non_kv_gib` line. Predicted: load ≈ 40,114 MiB, draft compute without FA scratch, card free ≥ 1.5 GiB.
  - **M-2**: whisper on CPU. Check `rocm-smi --showpids` shows 0 VRAM, the log says `no GPU found`, `taskset -cp` matches the cpuset, and one transcription meets RTF < 0.3.
  - **M-3**: draft depth 4 on **production traffic**. Acceptance and t/s vs the olympiad-study numbers (0.63–0.66 acceptance). Draft depth 8 remains a one-line revert.
  - **M-4**: kvu aggregate decode at np4. Per-request medians are equal or better under kvu, but aggregate decode in the single-run cells was 8–16% lower at np4 with L ≥ 8k (94.0 vs 102.0, 85.0 vs 100.8; `q38_27b_q8_h`). Watch aggregate t/s under concurrent load.
- **needs-operator (new only):**
  - **N-A — O-2 is dropped from the argv.** `-ctkd/-ctvd q8_0` is speed-neutral, but it is **not** a VRAM saving: it costs about **+0.40 GiB**, derived above.
    - Why: KV falls by 360 MiB, but a q8_0 draft KV forces the flash-attention F16 conversion scratch into the draft graph (+768 MiB; `ggml-cuda/fattn-common.cuh:68-71`, reserved via `ggml-cuda.cu:917-918`).
    - At np 4 that is exactly what makes the capacity gate fail, and the gate failure blocks import.
    - Recommendation: accept the drop.
    - To keep O-2 anyway: add `draft_kv_quant: {k: q8_0, v: q8_0}` to the serving_shape (the launcher already supports it), set `vram_non_kv_gib` to 33.20, **and** lower the headroom via `ORCHESTRATOR_VRAM_HEADROOM_GIB=1.9` (default 2.0, `src/scheduling/device_model.py:97`). That is a policy change.
  - **N-B — whisper cores (the parameter).** Nothing measured to date is safe for production:
    - every physical-core layout in 0-95 collapses when a frontdoor generation co-runs (STT RTF 0.8–2.9, frontdoor down to 0.3–7.4 tok/s);
    - the only candidate is option C (SMT siblings, e.g. `16@96-111`, 3/3 healthy with the frontdoor idle).

    Once option C passes the frontdoor co-run test:
    1. add its pair as `CORUN-OK` in `whisper-measured-safe-layouts.txt` with evidence;
    2. run `fill-whisper-layout.sh <threads> <cpuset>`;
    3. apply the resulting patch.

    **If option C fails, whisper stays on the GPU and :8083 cannot go to `-np 4`.** Projected free would be ≈ −0.3 GiB and the gate fails. In that case sign the np-2 variant instead (same patches with `slots: 2` and `vram_non_kv_gib` 31.34: 38,618 MiB at load minus 6.375 GiB of KV); I can prepare it on request.
  - Consequence to acknowledge, not a new decision: CPU STT latency is about **2 s per utterance** vs 0.12 s on the GPU, because of whisper's 30 s window padding.

## 6. Bring-up (phases 7–8, after the signature and N-B)

The whole change set lands at one boundary:
- :8083 is not mid-planner call for DS41;
- the bench guard is clear. Do not pass `--allow-during-bench`: the CPU reloads mlock the 35B and the Flash-Next and perturb CPU measurements.

The stack was restarted at 18:19–18:21Z on the old config, so this is a reload of the running services.
```bash
# phase 7 (pathspec commits only)
cd /mnt/raid0/llm/epyc-inference-research && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/v2/research-gpu-residency.patch
bash /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/v2/fill-whisper-layout.sh <THREADS> <CPUSET>
cd /mnt/raid0/llm/epyc-orchestrator && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/v2/orchestrator-gpu-residency.patch
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
.venv/bin/python -m pytest -q tests/unit/test_aux_service_env.py tests/unit/test_build_server_command_helpers.py tests/unit/test_stack_priors_compiler.py tests/unit/test_orchestrator_stack_reload.py
.venv/bin/python scripts/registry/stack_change_pipeline.py check --numa-mode both --run-promotion-gate
# phase 8, SEQUENTIAL: free the GPU first, then grow :8083, then the CPU cache-ram reloads
cd /mnt/raid0/llm/epyc-orchestrator
.venv/bin/python scripts/server/orchestrator_stack.py reload whisper                     # -> CPU; confirm 0 VRAM before continuing
LLAMA_ARG_LOG_VERBOSITY=4 .venv/bin/python scripts/server/orchestrator_stack.py reload architect_general
.venv/bin/python scripts/server/orchestrator_stack.py reload frontdoor server_8080 server_8180
.venv/bin/python scripts/server/orchestrator_stack.py reload architect_critic
```
Apply N-3 (opencode) in the same window and restart opencode.

## 7. Serving proof (report what each returned)

1. **:8083 binary and argv**:
   - `readlink -f /proc/$PID/exe` resolves under `kernels/production/gpu`;
   - the argv contains `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 --cache-ram 65536`;
   - `/proc/$PID/maps` shows `libggml-hip.so` from the same build.
2. **:8083 log**:
   - `kv_unified = 'true'`, `n_ctx_slot = 196608`, `n_slots = 4`;
   - `llama_memory_recurrent … 4 seqs 4 rs_seq` (RS ≈ 2,992 MiB);
   - draft KV `(f16)` 768 MiB;
   - all six buffer lines, recorded against M-1.
3. **/props and /slots**: `n_ctx` 196608 for all 4 slots.
4. **VRAM** (M-1): KFD for the :8083 PID at load ≈ 42.06e9 B. `rocm-smi` free ≥ 1.5 GiB after the first completion, and still during proof 6.
5. **Real completion** with `max_tokens: 4096`: non-empty content, `finish_reason: stop`, draft acceptance logged (M-3).
6. **>98k request with the other slots idle**: about 120k tokens with `max_tokens` 2048. Expect `prompt_tokens > 98304`, `finish_reason: stop`, and no `failed to find free space`. Run it before DS41 resumes planning.
7. **whisper** (M-2):
   - `rocm-smi --showpids` has no whisper entry, or shows 0 VRAM;
   - the log says `no GPU found`;
   - `taskset -cp $WPID` equals the cpuset;
   - one `POST /v1/audio/transcriptions` of `jfk.wav` comes back verbatim with RTF < 0.3, **also with a frontdoor generation running**.
8. **CPU roles**: `--cache-ram 32768` is in the :8070, :8080, :8180 and :8074 argv. `orchestrator_stack.py status` shows no attestation warnings.

**Rollback triggers**: any HIP OOM; free < 0.5 GiB; whisper hang or RTF > 1 under co-run; empty completions; acceptance < 0.4 or t/s −5% vs the study at matching np/L.

## 8. Rollback

- **Fast, config only**, in the master registry:
  - :8083: `slots: 2`, `draft_max: 8` (all 5 places), `kv_unified: false`. `false` emits `--no-kv-unified`, which is today's behaviour.
  - whisper: restore the aux entry (drop `-ng`, `cpuset`, `env`).
  - Then `update` and reload in reverse order: architect_general **before** whisper, so the GPU has room when whisper returns.
- **Full**: `git revert` both pathspec commits, then `update`, then the same reload order.
- **opencode**: restore `opencode/opencode.jsonc.orig` (sha256 `d25a2430…c8f1`) and restart opencode.
- `kernels/` does not change.

## 9. Evidence

- **Study**: `epyc-inference-research/artifacts/np_context_kvu_study_20260924/`:
  - `q38_27b_q8_h/summary.tsv`: kvu vs split, O-2, poolfull;
  - `q38_27b_q8_depth/`: depth 4/6;
  - `q38_27b_q8_loadonly/loadonly.txt`;
  - `q36_35b_a3b_q8_h/`;
  - results page https://claude.ai/artifact/Lr4Xd1jBwUW3ToDCQJCEjm
- **Speech on CPU**: `epyc-inference-research/artifacts/speech_cpu_realtime_20260924/README.md` and `raw/whisper_bench_encoder_matrix.txt`.
- **SSU-F3**: `/workspace/artifacts/operator/vram-gap-27b-20260923.md`.
- **v1 package and patches**: `patches/v1/`.

## 10. Follow-ups (owning sessions; not in this package)

- **Capacity validation at import is a trap.** A lineup that fails the gate makes `stack_manifest` un-importable, which also blocks the pipeline that would recompile a fix. In scratch I had to restore the derived lean registry before `update` could run. Move the check to the pipeline or launch path.
- The gate still cannot see per-slot GDN state, draft KV, or the FA conversion scratch (SSU-F3 structural fix). The `vram_non_kv_gib` scalar is valid at one shape only.
- `routing_decision.py:195-207` routes long context by a 20,000-character threshold; `compaction.py:50-61` falls back to 32768 tokens.
- The stack-change `scratch.sh` source list omits `stack_priors.py`, `stack_commands.py`, `orchestrator_stack.py` and `stack_manifest.py`. `preflight.sh`, `capacity.sh` and `topology_check.py` hardcode the real ORCH path.
- whisper's threadpool is layout-sensitive. A persistent, pinned threadpool build would remove the measured-layout constraint.
