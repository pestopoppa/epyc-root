# Stack-change package: unified KV (`--kv-unified`) on :8083

**Date**: 2026-09-24 · **Skill**: stack-change phases 0–5 (+ change-topology capacity) · **Status**: READY FOR OPERATOR SIGNATURE
**Scratch**: `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/` · **Nothing has touched a real tree or the live stack.**
Only read-only calls went to the live :8083: `GET /props`, `GET /slots`, `/proc/3343847/{cmdline,environ}`, KFD `vram_57300`, and `rocm-smi`.
No reload was run, no inference was run, and no process was signalled.

Lock check before starting: `coordination/push-locks/` holds no `push-*.json`. No stack-change scratch dir and no
kernel-promotion activity was present. `gpu_device.mi210_0.lock` is held by the DS41 autokernel loop (PID 3508990).
That lock belongs to the campaign, not to a stack change, so it did not block preparing this package.

---

## 0. Intent

```yaml
topology:
  architect_general:            # :8083, Qwen3.8-27B Q8_0, MI210 ROCm0; aliases ingest_long_context, coder_escalation
    kv_unified: true            # NEW: emit --kv-unified explicitly
    slots: 2                    # unchanged (-np 2); operator may pick another value, see N-2
    n_ctx: 196608               # unchanged
```

## 1. Root cause: it never "flipped". Production was never unified.

| Fact | Where |
|---|---|
| The server's `n_parallel` defaults to **-1 (auto)** | `llama.cpp common/arg.cpp:1216` |
| Auto becomes `n_parallel = 4` **and `kv_unified = true`**. This is the only place the server turns unified on by itself | `tools/server/server.cpp:145-150` |
| Otherwise `kv_unified` defaults to **false** | `common/common.h:580` |
| The help text says the same: "default: enabled if number of slots is auto" | `common/arg.cpp:1548` |
| The unified vs split split of the pool: `n_ctx_seq = n_ctx` when unified, else `n_ctx / n_seq_max` | `src/llama-context.cpp:289-302` |
| The orchestrator **always** passes `-np <slots>`. No orchestrator file mentions kv-unified | `scripts/server/orchestrator_stack.py` `_build_role_command` (`"-np", parallel_slots`, ~l.1503); grep for kvu returns 0 hits |
| Every production :8083 launch logged `kv_unified = 'false'` | `epyc-orchestrator/logs/llama-server-8083.log:8,17565,…,21283,21685`; live `/props` n_ctx 98304 |
| The "unified" evidence in the registry came from **bench launches**: 2026-07-31 and 2026-09-17 had no `-np`, so `n_slots = 4` came from auto; 2026-08-20 passed `--kv-unified` by hand | `workspace/artifacts/typed_decisions/run_20260917/server-27b.log:23`; research `artifacts/architect-bench-gpu-20260814/q38_vram_shape_20260820/server_command.txt:1` |

The registry's "KV IS UNIFIED ON THIS SERVER" (master `model_registry.yaml` ~1330, ~1404) was a bench fact
copied onto a production launcher that could not produce it. The fix therefore declares the fact **and emits it
explicitly in both directions** (`--kv-unified` / `--no-kv-unified`), so it can never again depend on a default.

**The MTP draft context becomes unified as well.** It inherits the flag through `common/speculative.cpp:2808`
(`result = params`) → `:2867` → `common/common.cpp:1692`, so both contexts get `n_ctx_seq = 196608`.

## 2. Multi-repo patch set

All patches are in `patches/`. Every patch was verified with `git apply --check` against the live working trees:
research `21ca61b0`, orchestrator `6b26f3ae` plus another session's uncommitted edits (see P-3). Chains were
verified on pristine copies.

| # | Patch | Repo | Default? | Content |
|---|---|---|---|---|
| 1 | `research-01-kv-unified-declaration.patch` | research | **YES** | `serving_shape.kv_unified: true` with provenance. Corrects the false "KV IS UNIFIED" banner and the four "98304 per slot" restatements (l.~1330, ~1404, ingest (a), `alias_note`, `ctx_max` comment) |
| 2 | `research-02-vram-non-kv-correction.patch` | research | **YES** (requires 1) | `vram_non_kv_gib 27.33 → 33.03`, **UNVALIDATED until bring-up**. 27.33 came from a different artifact at -c 16384. The new value is 32.28 measured non-KV (KFD 38.657 − KV 6.375) + 0.75 derived kvu mask growth. Without this hunk the gate stays blind to about 5.7 GiB |
| 3 | `orchestrator-01-kv-unified-launch-and-attest.patch` | orchestrator | **YES** | `stack_priors.py`: `_runtime_flag_bool_prior` + `runtime.cache.kv_unified`. `orchestrator_stack.py._append_runtime_kv_args` emits `--kv-unified`/`--no-kv-unified` only when declared. `stack_commands.py`: new attestation `_live_kv_unified()` resolves the flag the way the server does (last flag wins, else unified iff `-np` is absent). Adds 18 unit tests |
| 4 | `research-03-OPTIONAL-draft-kv-q8.patch` | research | no, O-2 (requires 2) | `serving_shape.draft_kv_quant: {k: q8_0, v: q8_0}` and `vram_non_kv_gib → 32.68` |
| 5 | `orchestrator-03-OPTIONAL-draft-kv-q8.patch` | orchestrator | no, O-2 (requires 3) | `runtime.cache.draft_kv_type_{k,v}` → `-ctkd/-ctvd`. Attested as token flags. Adds 7 unit tests |
| 6 | `opencode-OPERATOR-ACK-limit.patch` | `~/.config/opencode/opencode.jsonc` (outside containment) | operator applies | `limit: {context: 196608, output: 32768}` on `qwen-gpu/qwen3.8-27b` (see N-3) |
| — | `PREVIEW-derived-after-update-01+02.diff` | orchestrator | **preview only** | What `update` produced in scratch. `kv_unified: true` on the 3 :8083 launch records and `null` on the other 10. Never apply this. Phase 7 regenerates it, and its source paths point at scratch |

**Launch argv the scratch priors produce** (`expected-argv-8083.txt`):
```
…/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 8083
 -np 2 -c 196608 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all
 --chat-template-file …/epyc-qwen3x-v1-terse.jinja --spec-type draft-mtp --spec-draft-n-max 8 --device ROCm0
 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_general
```
With O-2 the argv also carries `-ctkd q8_0 -ctvd q8_0` (`expected-argv-8083-with-O2.txt`).
Besides `--kv-unified`, the reload also deploys two changes that are already committed but not yet live. Both
are inert:
- `-ub 8192 → 2048` (K4). Effective ubatch was already 2048 by clamp.
- `--device-draft ROCm0` is dropped (priors `device_draft: null`). It has no effect without `-md`.

### Surfaces (DERIVATION.md source list)

| Surface | Touched? | Why |
|---|---|---|
| research `model_registry.yaml` | yes | master |
| orchestrator `src/registry/stack_priors.py`, `scripts/server/orchestrator_stack.py`, `scripts/server/stack_commands.py` + 3 test files | yes | a declared boolean had no compile, emit or attest path. **These are not in `scratch.sh`'s source list; the DERIVATION source set is incomplete for new launch flags** (fixable follow-up to the skill) |
| `stack_topology.yaml`, `stack_numa.py`, `launch_manifest.yaml`, `src/config/models.py`, `src/roles.py`, `stack_templates/default.yaml` | no | no placement, port, role or template change. `topology_check.py` PASS (5 roles, 7 instances). No cpuset changed, so **no contention recert** |
| `/mnt/raid0/llm/kernels/production/gpu` | no | already → `builds/gpu-20260921-ffc1bac82/bin`, and the binary supports `-kvu` (`--help`) |
| `src/backends/server_lifecycle.py` (`ServerConfig`) | no | not the production launch path |
| `serving_shape.np` | **deliberately not added** | `server_mode.architect_general.slots` already declares it, and the capacity report reads it (`slots 2`). A second copy would be a RESTATED DERIVATION. What the gate lacks is the per-seq GDN term, which is SSU-F3's structural fix and out of scope |

## 3. Preflight: ONE classified list

Sources: `pipeline-update.txt`, `pipeline-check-scratch.txt`, `pipeline-check-baseline.txt` (pristine HEAD),
`capacity-declared-scratch.txt`, and pytest on scratch.
**This change introduces zero new violations.** Every item below is either caused by kvu (marked **[kvu]**) or
already present at HEAD (marked **[pre-existing]**).

**fixable-by-transform (0 open)**
- None open. Already fixed in the patches: registry assertion, restatements, compile/emit/attest path, derived recompile (scratch).

**needs-measurement (3), all at bring-up**
- **M-1 [kvu]: VRAM at the new shape.** Read the 6 buffer lines from `-lv 4`. Sample KFD per-PID VRAM **during** residency and during the >98k proof.
  - Predicted: `KV 6528 (196608 cells, 2/2 seqs)`, `RS 2693.25`, target compute ≈ **1856**, draft KV 768, draft compute ≈ **1040** MiB. KFD ≈ **40353 MiB (39.41 GiB)**, card free ≈ **0.18 GiB**.
  - Not measured now because the card has 0.93 GiB free, so a scratch 27B server cannot load, and :8083 is DS41's planner.
- **M-2 [kvu]: MTP draft acceptance and decode t/s under unified KV.** No production-shape evidence exists for hybrid + draft-mtp + kvu + np 2.
  - The known hybrid+kvu scar is tree-spec multi-path (`handoffs/completed/tree-speculation-numa-drafting.md` Phase 8), not linear MTP.
  - DF2-5's paired kvu control on DFlash2 was about 7% slower at c4 (`autokernel-champion-aggregate.md:217`).
  - Compare `mean len` and t/s against the live log baseline (`mean len ≈ 3.0–4.6`).
- **M-3 [O-2 only]:** draft acceptance with q8_0 draft KV. Same instrument as M-2.
- [pre-existing, not this change] strict gate: `architect_critic` and `qwen38_flash_next_ud_iq4xs_local` each have 2 known gaps (no quality suite_vector). They sit in the baseline and make `guard_strict` fail. See N-6.

**needs-operator (6)**
- **N-1** Sign the default set (patches 1, 2, 3).
- **N-2 −np / funding choice.** Table in §4.3. My recommendation: **-np 2 + kvu + O-2 (`-ctkd/-ctvd q8_0`)**.
- **N-3** Apply the opencode `limit` diff (outside containment). opencode reads config only at start, so restart it at the same DS41 boundary.
- **N-4 Timing.** Reload only at a DS41 run-8 planner boundary with the bench guard clear.
  - A :8083 reload kills any in-flight planner call, which costs one transient.
  - Recommend **not** passing `--allow-during-bench`: the reload reads 27 GiB `--no-mmap` and perturbs a CPU measurement.
- **N-5 [pre-existing, sharpened by kvu] TTS does not fit.** The `tts` aux service (:9002, 2.62 GiB measured 2026-09-22) is declared but **not running**. It cannot start today (0.93 GiB free), nor after kvu (0.18 / 0.53 GiB).
  - Once INF-41 lands, patch 2 makes the capacity gate FAIL correctly (61.85 + 4.68 aux > 62).
  - Decide: TTS on-demand only, or reclaim VRAM elsewhere (e.g. `--spec-draft-n-max`).
- **N-6 [pre-existing] Phase-7 gate is red regardless of this change.**
  - `guard_strict` fails on the 4 known-gap errors above.
  - 7 unit tests in `LAUNCH_PARITY_TARGET` fail identically on pristine HEAD (retired `worker_general`, K4 ubatch 2048, `architect_critic` KV types).
  - So `check --run-promotion-gate` cannot go green. Decide: apply with these acknowledged, or have their owners fix them first.

## 4. Capacity report

### 4.1 Host leg
Unchanged: `HOST required 232.97 GiB / budget 1069.42 GiB`, PASS (not UNGATED). No host-memory term changes.
**Side effect**: unified mode also doubles the *host* copy of each KQ mask (`ROCm_Host compute` 464 → about 848 MiB ×2 contexts, +0.75 GiB RAM). This is negligible.

### 4.2 GPU leg (MI210, 65520 MiB usable), buffer model from SSU-F3 (read 2026-09-23 via `-lv 4`)

Residents now, from KFD during residency, 2026-09-24:

| Resident | MiB | GiB |
|---|---:|---:|
| :8083 27B (PID 3343847) | 39584.7 | 38.657 |
| :8086 VL-30B | 22814.4 | 22.280 |
| :9000 whisper (gate-invisible, fluctuates about ±130 MiB) | 2126.5 | 2.077 |
| driver/other | 44.7 | 0.044 |
| **free** (rocm-smi) | **949.6** | **0.927** |

Declared-but-absent: TTS :9002, 2.62 GiB.

The KQ mask is `[n_kv, n_ubatch/n_stream, 1, n_stream]` F16 (`src/llama-graph.cpp:30-38`). The graph is reserved
with `n_seqs = n_seq_max` (`src/llama-context.cpp:589`).
- Split KV: `196608/np × 2048` elements. The mask **shrinks** with -np.
- Unified KV: `196608 × 2048` elements = **768 MiB at any -np**.

The FA F16 K/V conversion scratch sits inside the FA tensor's allocation (`ggml-cuda.cu:917-918`,
`fattn-common.cuh:68-71`), so it is reserved at load. Its element count is equal under both modes. The `+0.75 GiB`
is therefore the whole kvu delta at -np 2, and it is fixed at load, not a runtime ratchet.

### 4.3 Table for N-2 (MiB; all rows keep `-c 196608`)

Columns:
- RS = `156,893,184 B × np × (1+draft_max)` (`llama-memory-recurrent.cpp:101`, `llama-model.cpp:2278`)
- tgt/drf comp = the target and draft compute buffers
- HIP ovh = 1064.4 MiB, constant (KFD − logged buffers)
- Δ = change vs the live process

| config | weights | attn KV (pool) | GDN RS | tgt comp | draft KV | draft comp | HIP ovh | **total GiB** | **Δ GiB** | **card free GiB** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| live: np2 split | 26402.7 | 6528 | 2693.3 | 1472.3 | 768 | 656.1 | 1064.4 | 38.66 | 0 | **0.93** |
| **np2 kvu (default patch)** | 26402.7 | 6528 | 2693.3 | 1856.3 | 768 | 1040.1 | 1064.4 | 39.41 | +0.75 | **0.18** |
| **np2 kvu + O-2 (recommended)** | 26402.7 | 6528 | 2693.3 | 1856.3 | 408 | 1040.1 | 1064.4 | 39.06 | +0.40 | **0.53** |
| np4 kvu | 26402.7 | 6528 | 5386.5 | ~1873 | 768 | 1040.1 | 1064.4 | 42.05 | +3.40 | **−2.47 (does not load)** |
| np4 kvu + O-2 + draft 4 | 26402.7 | 6528 | 2992.5 | ~1873 | 408 | 1040.1 | 1064.4 | 39.36 | +0.71 | 0.22 |
| np4 kvu + O-2 + draft 3 | 26402.7 | 6528 | 2394.0 | ~1873 | 408 | 1040.1 | 1064.4 | 38.78 | +0.12 | 0.80 |
| np8 kvu | 26402.7 | 6528 | 10773.0 | ~1907 | 768 | 1040.1 | 1064.4 | 47.35 | +8.69 | **−7.76** |
| np8 kvu + O-2 + draft 2 | 26402.7 | 6528 | 3591.0 | ~1907 | 408 | 1040.1 | 1064.4 | 39.98 | +1.33 | **−0.40** |
| np1 (unified ≡ split) | 26402.7 | 6528 | 1346.6 | ~1848 | 768 | 1040.1 | 1064.4 | 38.08 | −0.57 | 1.50 |

Assumptions:
- `~` marks an estimate of the output-logits term (248320 × 4 B × np·(1+draft)). The GDN per-seq compute term is not modelled. M-1 reads both.
- Per extra slot: GDN costs +1.315 GiB at draft 8. That is independent of kvu, and it is why a higher -np is **not** cheap on this hybrid model.
- Per unit of draft depth at np 2: GDN costs +0.292 GiB. The +0.329 figure in SSU-F3's addendum divided the whole buffer by 8.

Declared gate (`stack_manifest`) at the default: `61.85 / 62.00 GiB`, PASS. With O-2: `61.50`.
It still omits whisper (INF-41), so it is **not** proof of fit. The KFD arithmetic above is.

**Recommendation (N-2): np 2 + kvu + O-2**, which leaves 0.53 GiB free.
- **np2 kvu alone** leaves 0.18 GiB. That is inside whisper's observed ±130 MiB swing and has no room for a VL image burst, so I would not ship it bare. It remains the conservative *code* default, as briefed.
- **np4** fits only by cutting draft depth to 3 or 4. The live acceptance of `mean len` 3.0–4.6 says depth 3 truncates accepted drafts. The cost is unmeasured (likely 10–20% single-stream decode).
- **np4 buys little on the concurrency side.** :8083 is a single-stream planner plus two aliases, and 4 streams sharing one 196608 pool exhaust it sooner.
- **np8** does not fit.
- **np1** frees 0.57 GiB but serializes architect_general, ingest_long_context and coder_escalation.

### 4.4 The shared-pool failure mode (new with kvu)
Per-request admission checks `slot.n_ctx` (now 196608) only (`server-context.cpp:3303-3310` returns 400
`exceed_context_size_error`). It does not check the pool's current occupancy. So two concurrent long requests
(e.g. 120k + 90k) are both admitted. When `llama_decode` finds no free cells, the server escalates in three steps:
1. It purges idle slots (`try_clear_idle_slots`, `:1716-1735`, unified only).
2. It halves `n_batch` down to 1, logging `failed to find free space in the KV cache, retrying with smaller batch size` (`:3797-3801`).
3. Finally it throws **"Context size has been exceeded."** (`:3759-3763`). `abort_all_slots` then fails **every in-flight request** with `decode() failed: …` (`:2949-2951`).

This is not a crash, but both callers lose their request. Under split KV the same load produced a per-slot
`finish_reason: length` instead (DS41 run 8's failure).

**Idle-slot behaviour also changes.** With the default `--cache-idle-slots` and `--cache-ram 8192`, starting any
task already *saves* idle slots to the RAM prompt cache today. Under kvu it also **clears** them (`:2468-2482`,
`TAG_IDLE_SLOT_CLEAR`). A returning conversation on the other slot restores its prefix from RAM rather than
hitting VRAM. That is a warm-prefix latency cost on the shared :8083, not a correctness cost. The DS41 planner's
own slot is not cleared while it is processing.

## 5. Bring-up (phases 7–8, after signature)

**Phase 7 — apply.** Pathspec only. Another session holds uncommitted edits in epyc-orchestrator (`launch_manifest.yaml`,
`orchestrator_stack.py`, `src/models/image.py`, … for the sd_server → Qwen-Image swap), so coordinate and **do not sweep them in**.
```bash
cd /mnt/raid0/llm/epyc-inference-research && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/research-01-kv-unified-declaration.patch && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/research-02-vram-non-kv-correction.patch
#   (O-2) && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/research-03-OPTIONAL-draft-kv-q8.patch
cd /mnt/raid0/llm/epyc-orchestrator && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/orchestrator-01-kv-unified-launch-and-attest.patch
#   (O-2) && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/orchestrator-03-OPTIONAL-draft-kv-q8.patch
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
.venv/bin/python -m pytest -q tests/unit/test_build_server_command_helpers.py tests/unit/test_stack_priors_compiler.py tests/unit/test_orchestrator_stack_reload.py   # expect ONLY the 7 pre-existing failures (N-6)
.venv/bin/python scripts/registry/stack_change_pipeline.py check --numa-mode both --run-promotion-gate                                                              # expect ONLY the 4 pre-existing strict errors (N-6)
```

**Phase 8 — bring up.** This must run at a **DS41 run-8 planner boundary**. A :8083 reload kills an in-flight
planner call, which costs one transient.
```bash
# boundary: both slots idle AND DS41 not inside a planner call (coordinate with the DS41 owner / its loop-status)
curl -s http://127.0.0.1:8083/slots | python3 -c 'import json,sys; print([s["is_processing"] for s in json.load(sys.stdin)])'   # [False, False]
cat /mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/state-run8/loop-status.json
cd /mnt/raid0/llm/epyc-orchestrator && LLAMA_ARG_LOG_VERBOSITY=4 .venv/bin/python scripts/server/orchestrator_stack.py reload architect_general
```
Notes:
- `LLAMA_ARG_LOG_VERBOSITY=4` reaches the child. The live PID's environ carries it from SSU-F3's reload, and it is what makes M-1 a *reading*.
- If the bench guard refuses, wait. Do not add `--allow-during-bench` (N-4).
- Restart opencode after N-3 in the same window.

## 6. Serving proof (report what each returned; `healthy` is not proof)

Capture PID from KFD first, by matching port and not by name: `for p in $(ls /sys/class/kfd/kfd/proc/); do tr '\0' ' ' </proc/$p/cmdline | grep -q -- '--port 8083' && echo $p; done`.

1. **Binary**:
   - `readlink -f /proc/$PID/exe` == `readlink -f /mnt/raid0/llm/kernels/production/gpu`/llama-server (`builds/gpu-20260921-ffc1bac82`).
   - `grep -c builds/gpu-20260921-ffc1bac82/bin/libggml-hip.so /proc/$PID/maps` ≥ 1.
   - argv contains `-np 2 -c 196608 … --kv-unified` (+ `-ctkd q8_0 -ctvd q8_0` if O-2).
2. **Log**: in the new launch block of `logs/llama-server-8083.log`, check for:
   - `kv_unified = 'true'` (srv line)
   - `llama_context: kv_unified = true` ×2 (target and draft)
   - `n_ctx_seq = 196608` ×2
   - `n_ctx_slot = 196608`
   - the six buffer lines, compared against M-1's predictions
3. **/props, /slots**: `default_generation_settings.n_ctx == 196608`; every slot `n_ctx == 196608`.
4. **VRAM during residency**: `cat /sys/class/kfd/kfd/proc/$PID/vram_57300` ≈ 42.31e9 B (O-2: ≈ 41.94e9); `rocm-smi --showmeminfo vram` free ≥ 0.15 GiB.
   - Sample again **during** proof 6, which is the window that exercises a 196608-cell FA pass.
   - Then replace `vram_non_kv_gib`'s UNVALIDATED line with KFD − 6.375.
5. **Real completion, real budget**: `POST /v1/chat/completions` with `max_tokens: 4096`. Thinking is medium, and reasoning bills against max_tokens.
   - Require non-empty `content` and `finish_reason: "stop"`.
   - Log `draft acceptance … mean len` should be within the 3.0–4.6 band (M-2).
6. **>98k request with the other slot idle**: confirm `/slots` shows the other slot not processing.
   - Send a ~120k-token prompt (e.g. concatenated repo text) with `max_tokens: 2048`.
   - Require `usage.prompt_tokens > 98304`, `finish_reason: "stop"`, no `exceed_context_size_error`, and no `failed to find free space` in the log.
   - Run it **before DS41 resumes planning**. A concurrent planner call could exhaust the pool (§4.4).
7. **Attestation**: `.venv/bin/python scripts/server/orchestrator_stack.py status`. There must be no `kv_unified` or `ubatch` warning for :8083.
   - Before the change, the new check flags the live PID: `runtime kv_unified expected True; live cmdline has False`. That was verified read-only against the scratch priors.

**Rollback triggers**: proof 4 free < 0.15 GiB; any HIP OOM; proof 5 empty or garbled; `mean len` below 3.0 on
proof 5 and a repeat; decode t/s down > 5% vs the pre-change log at equal prompt length.

## 7. Rollback

- **Fast (config only)**: set `serving_shape.kv_unified: false` in the master. The launcher then emits `--no-kv-unified`, which is identical to today's behaviour and keeps the new plumbing. Then `stack_change_pipeline.py update --numa-mode both` and `orchestrator_stack.py reload architect_general` at a DS41 boundary.
- **Full**: `git revert <research commit>` and `git revert <orchestrator commit>` (pathspec commits from phase 9), then `update`, then reload at a boundary.
- **opencode**: restore `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/opencode/opencode.jsonc.orig` (sha256 `d25a2430…c8f1`) to `~/.config/opencode/opencode.jsonc`, or set `context: 98304`, then restart opencode.
- No symlinks or kernels change, so there is nothing to restore in `kernels/`.

## 8. opencode (N-3, operator-ack; I did not edit the file)

`patches/opencode-OPERATOR-ACK-limit.patch`:
```diff
-        "qwen3.8-27b": { "name": "Qwen3.8-27B Q8_0 (author)" }
+        "qwen3.8-27b": {
+          "name": "Qwen3.8-27B Q8_0 (author)",
+          // :8083 serves a UNIFIED 196608-token KV pool (-kvu, stack-change-kvu 2026-09-24): …
+          "limit": { "context": 196608, "output": 32768 }
+        }
```
Setting `output: 32768` caps max_tokens (reasoning included) and makes opencode compact before prompt+output
passes 196608. If kvu does not ship, use `context: 98304`. Apply this only together with, or after, the reload.
Advertising 196608 against a split server re-creates DS41's failure.

## 9. Evidence refs
- SSU-F3: `/workspace/artifacts/operator/vram-gap-27b-20260923.md`, specifically §3.5 and the RESOLVED buffer table. Live log lines `llama-server-8083.log:21605-21693`.
- Live reads 2026-09-24: `/proc/3343847/cmdline`; KFD 41,507,569,664 B; rocm-smi used 67,706,933,248 / 68,702,699,520 B; `/props` n_ctx 98304, build b10303-ffc1bac82.
- Bench provenance of the "unified" claim: research `artifacts/architect-bench-gpu-20260814/q38_vram_shape_20260820/`; root `artifacts/typed_decisions/run_20260917/server-27b.log`.
- Scratch outputs in this directory: `pipeline-*.txt`, `capacity-declared-scratch.txt`, `expected-argv-*.txt`, `PROVENANCE.json`. Scratch clones are under `full/` (01+02 checkpoint commit `5916a429` + O-2 working diff) and `pristine/`.
- gitnexus: `_build_role_command` impact LOW (1 direct caller, `start_server`). The index is 718 commits stale for epyc-orchestrator, so the structural blast radius was derived by hand: new code emits only when `kv_unified` or `draft_kv_*` is declared, and only :8083's three launch records declare it.

## 10. Follow-ups (not fixed here; listed for the owning sessions)
- `routing_decision.py:195-207` routes long context on a **20,000-character** threshold, not tokens or live `/props`.
- `src/graph/compaction.py:50-61` falls back to `n_ctx 32768` when the registry lookup fails.
- No caller handles llama-server's 400 `exceed_context_size_error` or the §4.4 `decode() failed: Context size has been exceeded.`
- Ambient `LLAMA_ARG_*` env reaches the server (`LLAMA_ARG_LOG_VERBOSITY` proves it). `-kvu` on argv wins over `LLAMA_ARG_KV_UNIFIED`, but an ambient `LLAMA_ARG_N_PARALLEL` or similar would be invisible to the cmdline attestation.
- The stack-change skill's `scratch.sh`/DERIVATION source list omits `src/registry/stack_priors.py`, `scripts/server/stack_commands.py` and `orchestrator_stack.py`, which any new launch flag needs. `preflight.sh`, `capacity.sh` and `topology_check.py` hardcode the real ORCH path, so they cannot run against a scratch clone.
- SSU-F3 structural capacity model (RS / draft-KV / compute terms); INF-41 aux VRAM in the gate.
- Belief-kernel wiring: the M-1 bring-up reading is a verified measurement. Record it with SSU-F3's prepared claim tuple (row prepared by SSU-F3; owning session applies).
