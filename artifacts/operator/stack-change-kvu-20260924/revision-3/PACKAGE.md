# GPU-residency change set: FINAL package for signature

**Date**: 2026-09-24, revision 3 (operator decisions ~18:35Z) · **Skill**: stack-change phases 0–5 · **Status**: READY FOR SIGNATURE
**Scratch**: `/mnt/raid0/llm/tmp/stack-change-kvu-20260924/v2/`. The registry is at `v2/reg`; the orchestrator clone is at `v2/full-orch`.
**Patches**: `patches/v2/`. Earlier revisions are in `patches/v1/` (`PACKAGE-v1.md`, `PACKAGE-v2-rev2.md`).

**Safety of preparation**: no real tree, live service or `~/.config/opencode` file was modified, and no process was started, stopped or signalled.
- Live reads were read-only.
- The shim was compiled and self-tested **in scratch only** (`v2/shim-test/`).
- Both patches pass `git apply --check` against the live trees: orchestrator `8a0c0944`, research `21ca61b0`. Upstream moved during preparation, but none of the moves touch a patched file.

**Locks**: no push lock, no stack-change and no promotion is held.

---

## 1. What changes

| Service | Change |
|---|---|
| **:8083** architect_general, 27B on the MI210 | `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub 2048 --cache-ram 65536`. The draft KV stays F16: O-2 was dropped by operator decision, because a q8_0 draft cache adds a 768 MiB FA conversion buffer |
| **:8070 / :8080 / :8180** frontdoor | `--cache-ram 32768`. The flag is role-level, so the halves get it too |
| **:8074** architect_critic | `--cache-ram 32768` |
| **:9000** whisper STT | CPU: `-t 24 -ng`, `taskset -c 0-23`, `HIP_VISIBLE_DEVICES=-1` |
| **:9002** qwentts TTS | CPU: `taskset -c 24-39`, `GGML_BACKEND=CPU`, `HIP_VISIBLE_DEVICES=-1`, `LD_PRELOAD=/mnt/raid0/llm/cache/shims/nprocs_shim.so`, `SHIM_NPROCS=32` (gives 16 threads) |
| opencode `qwen-gpu/qwen3.8-27b` | `limit: {context: 196608, output: 32768}` |

Exact argvs, generated from the scratch priors, are in `v2/expected-argv.txt`. For :8083:
```
…/builds/gpu-20260921-ffc1bac82/bin/llama-server -m …/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 8083 -np 4 -c 196608 -t 8 -ub 2048
 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap -ngl all --cache-ram 65536 --chat-template-file …/epyc-qwen3x-v1-terse.jinja
 --spec-type draft-mtp --spec-draft-n-max 4 --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_general
```

## 2. Patch set

- **`research-gpu-residency.patch`** (master `model_registry.yaml`):
  - `serving_shape.kv_unified: true`, plus the corrected "KV IS UNIFIED" banner (root cause in §6).
  - `slots 2→4`, including the ingest compat scalar.
  - `draft_max 8→4` in all 5 restatements.
  - `cache_ram` on the 3 roles.
  - `vram_non_kv_gib 27.33 → 32.80`: a load-time figure, **UNVALIDATED until bring-up**.
  - `voice_server` and `tts_server` → `device: cpu`, `vram_gib: 0`, with CPU latency and the caveats.
  - O-2 left undeclared, with the reason recorded in place.
- **`orchestrator-gpu-residency.patch`**:
  - **kv_unified** is compiled by `stack_priors`, emitted in both directions, and attested by `_live_kv_unified()`.
  - **draft-KV plumbing** (`-ctkd/-ctvd`) is inert while undeclared.
  - **`AuxService.cpuset`** is honoured verbatim. The bench guard may refuse it but never re-pin it, and a malformed value fails only that service.
  - **The launcher refuses a missing `LD_PRELOAD`.** glibc would otherwise ignore it silently and the TTS would run 96 threads.
  - Speech entries moved to CPU.
  - **`scripts/voice/nprocs_shim.c` + `build_nprocs_shim.sh`**: an out-of-tree build that is idempotent, hash-stamped, and self-tests interposition before publishing.
  - **`scripts/voice/speech_layouts.yaml` + `check_speech_layout.py`** implement the new acceptance rule: a layout must be measured safe solo or concurrently, frontdoor idle, and the frontdoor-contention caveat is documented. A unit test asserts that the manifest's declared layouts pass.
  - Template `draft_max 8→4`.
  - **35 new tests; 235 pass across the affected suites.** `test_fleet_layer_dispatch.py` and `test_full_slot_demotion.py` fail at collection with `KeyError 'worker_general'` on pristine HEAD too, so those failures predate this change.
- **`opencode-OPERATOR-ACK-limit.patch`**: the operator applies this (the file is outside containment), then restarts opencode.
- **`PREVIEW-derived-after-update.diff`**: preview only. Phase 7 regenerates it.

**Preflight** (scratch `update`): green for lean, descriptors, priors, enums, summary, guard, guard_strict, stack_manifest_registry and q_scorer, with the declared capacity passing.
- **Capacity**: `GPU 61.62 / 62.00 GiB (2.0 GiB headroom kept) PASS`; host 232.97 / 1069 GiB PASS.
- **Topology**: unchanged; `topology_check` PASS.
- **Only non-green item**: `runtime_attestation`, 16 "unmanaged listener" lines. This is a scratch artifact: the clone's `STATE_FILE` does not exist. The real attestation, run against the live :8083 PID 1887789, reports exactly the intended drift (slots, kv_unified, draft_max, cache_ram).

## 3. Capacity (GPU, 65,520 MiB)

| Item | MiB |
|---|---:|
| 27B np4/196k/kvu/d4/F16-draft at load (derived from the measured 40,522 load-only minus 408 for O-2) | 40,114 |
| + measured first-execution growth | 567 |
| VL-30B (KFD, 18:21Z) | 22,869 |
| driver | ~45 |
| whisper | 0 |
| TTS | 0 |
| **projected free** | **≈ 1,925 (1.88 GiB)** |

N-5 is resolved: :9002 is no longer an unfittable GPU service.

On the host, speech uses cores 0-39 and about 4 GB of RAM. The `--cache-ram` caps total up to 192 GiB, allocated on demand, against about 840 GiB available.

## 4. Needs-operator (minimal)

1. **Sign the package.**
2. **Accept the TTS thread shim as the mechanism until a speech kernel v2 exists.** It is an `LD_PRELOAD` interposer on `get_nprocs()` around a frozen binary. It is a hack, but a contained one: the source is tracked, it is built out of every frozen tree, it self-tests, the launcher fails closed if the file is missing, and the serving proof checks the log for `CPU threads: 16`. The durable fix is a thread flag in qwentts.cpp on `experimental`, promoted as the next speech kernel version.
3. **Apply the opencode diff** and restart opencode.

Acknowledged, not new decisions:
- CPU speech latency is about 2 s per STT utterance and TTS RTF about 0.6, against 0.12 s and 0.17 on the GPU.
- **A generating CPU frontdoor collapses both speech servers**, which is why voice turns route reasoning to :8083 (the upcoming voice pipeline).
- Pool overflow handling is landing separately.

## 5. Bring-up (after signature)

Do this at one boundary: DS41 is not mid-planner-call on :8083, and the bench guard is clear. **Do not pass `--allow-during-bench`.** Reloads run sequentially.
```bash
# phase 7: apply + recompile (commit by pathspec only)
cd /mnt/raid0/llm/epyc-inference-research && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/v2/research-gpu-residency.patch
cd /mnt/raid0/llm/epyc-orchestrator && git apply /mnt/raid0/llm/tmp/stack-change-kvu-20260924/patches/v2/orchestrator-gpu-residency.patch
cd /mnt/raid0/llm/epyc-orchestrator && bash scripts/voice/build_nprocs_shim.sh            # -> /mnt/raid0/llm/cache/shims/nprocs_shim.so
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/voice/check_speech_layout.py
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py check --numa-mode both --run-promotion-gate
# phase 8: free the GPU first, then grow :8083, then the CPU cache-ram reloads
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/server/orchestrator_stack.py reload whisper tts
cd /mnt/raid0/llm/epyc-orchestrator && LLAMA_ARG_LOG_VERBOSITY=4 .venv/bin/python scripts/server/orchestrator_stack.py reload architect_general
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/server/orchestrator_stack.py reload frontdoor server_8080 server_8180 architect_critic
```

**Serving proof** (report what each step returns; "healthy" alone is not proof):
1. **:8083 identity**: argv[0] resolves into `kernels/production/gpu`, and `libggml-hip` from that build is in `/proc/<pid>/maps`.
2. **:8083 log**: `kv_unified = 'true'`, `n_slots = 4`, `n_ctx_slot = 196608`, `4 seqs 4 rs_seq`, and all six buffer lines. Replace the UNVALIDATED `vram_non_kv_gib` with the KFD reading at load minus 6.375.
3. **:8083 endpoints**: `/props` and all 4 slots report n_ctx 196608.
4. **GPU memory**: `rocm-smi` free ≥ 1.5 GiB after the first completion.
5. **:8083 completion**: a real completion with `max_tokens` 4096, plus a >98k-token request with the other slots idle.
6. **Speech off the GPU**: `rocm-smi --showpids` shows no whisper and no tts; both logs say no GPU was found; TTS logs `CPU threads: 16`; `taskset -cp` shows 0-23 and 24-39.
7. **Speech working**: a jfk.wav transcription comes back verbatim with RTF < 0.3, and a TTS smoke returns ≥ 1024 bytes with first packet under 150 ms.
8. **CPU roles**: `--cache-ram 32768` in all four argvs, and `orchestrator_stack.py status` shows no attestation warnings.

**Post-bring-up measurements**:
- **M-3**: draft depth 4 on production traffic.
- **M-4**: aggregate decode at np4 under concurrent load. The study showed 8–16% lower in single-run cells.

## 6. Root cause of the old kv_unified mismatch (verified)

llama-server enables unified KV only when `-np` is left on auto (`common/arg.cpp:1216`, `tools/server/server.cpp:145-150`). Otherwise it stays false (`common/common.h:580`). The launcher always passes `-np`, so production was never unified, and the registry claim came from bench launches.

## 7. Rollback

- **Fast, config only**, in the master registry:
  - :8083: `slots: 2`, `draft_max: 8` (all 5 places), `kv_unified: false` (emits `--no-kv-unified`, i.e. today's behaviour);
  - speech: restore both aux entries (drop `-ng`/`cpuset`/`env`, and whisper back to `-t 8`);
  - `cache_ram`: remove the three declarations.
  - Then `update` and reload in **reverse order**: `architect_general` **before** `whisper tts`, so the GPU has room when speech returns, then the CPU roles.
- **Full**: `git revert` both pathspec commits, then `update`, then the same reload order.
- **opencode**: restore `opencode/opencode.jsonc.orig` (sha256 `d25a2430…c8f1`) and restart opencode.
- **Shim**: leaving it in place is harmless, because nothing preloads it once the TTS entry is reverted. Delete `/mnt/raid0/llm/cache/shims/nprocs_shim.so*` only if wanted.
- **Kernels**: no kernel symlink changes.

## 8. Evidence

- **Study**: `epyc-inference-research/artifacts/np_context_kvu_study_20260924/` (`q38_27b_q8_h`, `_depth`, `_loadonly`; `q36_35b_a3b_q8_h`), results page https://claude.ai/artifact/Lr4Xd1jBwUW3ToDCQJCEjm
- **Speech on CPU**: `…/speech_cpu_realtime_20260924/README.md` and `raw/` (encoder matrix, `concurrent_main40.stdout`).
- **SSU-F3**: `/workspace/artifacts/operator/vram-gap-27b-20260923.md`.
- **O-2 cost**: the FA conversion scratch is reserved inside the FA tensor (`ggml-cuda/fattn-common.cuh:68-71`, `ggml-cuda.cu:917-918`). This explains the load-only table to within 29 MiB.

## 9. Follow-ups (other owners)

- The capacity gate runs at import of `stack_manifest`, so a failing lineup makes the launcher and pipeline un-importable (hit in scratch).
- SSU-F3's structural VRAM terms are still not in the gate.
- A qwentts thread flag, in the next speech kernel version.
- The skill's `scratch.sh` source list misses `stack_priors.py`, `stack_commands.py`, `orchestrator_stack.py`, `stack_manifest.py` and `scripts/voice/`.
- Two unit test files still reference the retired `worker_general`.
- Ambient `LD_PRELOAD` and `SHIM_NPROCS` in the launcher's parent env would reach every aux service, because `build_service_env` starts from `os.environ`.
