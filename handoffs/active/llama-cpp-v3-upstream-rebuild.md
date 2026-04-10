# llama.cpp Upstream Rebuild — production-consolidated-v3

**Status**: CHERRY-PICKS COMPLETE — Smoke tests pending (requires inference window)
**Created**: 2026-04-08
**Priority**: HIGH (blocks all future llama.cpp feature work)
**Workstream**: WS2
**Branch**: `production-consolidated-v3` (to be created from `origin/master` in `llama.cpp-experimental`)
**Blocks**: Any new cherry-picks, feature branches, or upstream syncs
**Blocked by**: Nothing — ready to execute
**Prior art**: [`handoffs/completed/llama-cpp-upstream-rebase.md`](../completed/llama-cpp-upstream-rebase.md) (v1→v2 rebase, 2026-03-03)

## Goal

Rebuild `production-consolidated-v2` onto current upstream master, gaining 517 commits of upstream improvements while preserving all 23 production-critical custom patches. Work exclusively in `llama.cpp-experimental` — production binary remains untouched until validation passes.

## Current State

| Metric | Value |
|--------|-------|
| Fork point | `137435ff` (2026-03-03, kleidiai aarch64 fp16) |
| Upstream HEAD (at rebuild) | `0ec191e1d` (538 commits ahead as of 2026-04-09) |
| Source branch | `production-consolidated-v2` (27 custom commits incl. `860ab737c`) |
| Carry-forward patches | 23 (27 minus 4 drops — see notes) |
| v3 branch | `production-consolidated-v3` — 24 commits (23 patches + 2 fixups, skipped v1 docs) |
| Build flags | `-DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=ON` |
| Experimental worktree | `/mnt/raid0/llm/llama.cpp-experimental` — on `production-consolidated-v3` |
| Remotes | `origin` = ggml-org/llama.cpp, `fork` = pestopoppa/llama.cpp |

---

## Patch Inventory

### Tier 1 — Production-Critical (orchestrator depends on these)

These patches implement features actively used by `orchestrator_stack.py` and `model_registry.yaml`. All must be carried forward.

| # | Commit | Feature | Files | Conflict Risk | Orchestrator Usage |
|---|--------|---------|-------|--------------|-------------------|
| 1 | `bbcca6dea` | `--moe-n-expert` (Hard Mask / REAP) | `common/arg.cpp`, `common/common.h`, model files | LOW | REAP-246B architect_coding depends on expert count override |
| 5 | `ca8cfd1ca` | SWA slot reuse optimization (forward-looking masking) | `src/llama-kv-cache.cpp` | **HIGH** | Implicit — all SWA models benefit |
| 6 | `7b75d212b` | SWA cell reuse correctness fix | `src/llama-kv-cache.cpp` | **HIGH** | Correctness fix for #5 |
| 7 | `39f4949c7` | CPU paged attention for flash attention | `src/llama-kv-cache.cpp`, `src/llama-context.cpp`, `src/llama-graph.cpp` | **CRITICAL** | Models ≥39GB use paged attention (registry `enabled_threshold_gb: 39`) |
| 8 | `4ff8e2c5a` | Dynamic block allocation for paged attention | `src/llama-kv-cache.cpp`, `src/llama-kv-block.h` | **CRITICAL** | Part of paged attention stack |
| 9 | `b217755b3` | Block pool statistics (debug) | `src/llama-kv-cache.cpp` | **CRITICAL** | Part of paged attention stack |
| 10 | `cbb124912` | KV cache memory reduction for paged attention | `src/llama-kv-cache.cpp` | **CRITICAL** | Part of paged attention stack |
| 11 | `6f880097b` | CLI flags for paged attention | `common/arg.cpp`, `common/common.h` | MEDIUM | Orchestrator passes paged attention flags |
| 12 | `7b7f8818a` | Trim verbose comments in llama-kv-block.h | `src/llama-kv-block.h` | LOW | Cleanup, no functional change |
| 13 | `9cf32164f` | Unit tests for block pool and table | `tests/test-kv-block.cpp`, `tests/CMakeLists.txt` | LOW | Test coverage |
| 14 | `45ea13916` | Server slot erase without `--slot-save-path` | `tools/server/server-context.cpp` | MEDIUM | Orchestrator uses dynamic slot management |
| 15 | `505d0c997` | Server error handling for force-erased slots | `tools/server/server-context.cpp`, `tools/server/server-queue.cpp` | MEDIUM | Correctness fix for #14 |
| 19 | `0819d1f20` | `--lookup` (prompt n-gram lookup) | `common/arg.cpp`, `common/common.h` | LOW | worker_explore, coder_escalation use `--lookup` flag |

### Tier 2 — Research/Acceleration (benchmarks, not production-blocking)

These implement features used in completed research. Carry forward for reference and potential future use.

| # | Commit | Feature | Files | Conflict Risk | Notes |
|---|--------|---------|-------|--------------|-------|
| 2 | `e8f21a4c8` | OpenMP tensor repacking | `ggml/src/ggml-cpu/repack.cpp` | MEDIUM | Both sides modified repack.cpp |
| 3 | `c5565e6a8` | Layer skip / early exit for speculative decoding | `src/llama-graph.cpp`, `src/llama-graph.h`, `include/llama.h`, model files | MEDIUM | `--n-layer-exit-draft` used in orchestrator self_speculation path |
| 4 | `eda635d48` | Layer skip for qwen3vl-moe and qwen3next | `src/models/qwen3next.cpp`, `src/models/qwen3vl-moe.cpp` | MEDIUM | Upstream added NVFP4 + control vectors to these files |
| 16 | `6e49ca1ae` | SSM state checkpointing for spec decode on hybrids | `src/llama-memory-recurrent.cpp`, `src/llama-memory-recurrent.h`, `src/llama-memory-hybrid.cpp`, `src/llama-memory-hybrid.h` | MEDIUM | Upstream `f93c09e26` fixed seq_id bounds in same file |
| 20 | `44255f33b` | HSD + freeze-recurrent speculation for hybrid SSM | `common/speculative.cpp`, `common/speculative.h` | LOW | `speculative.cpp/h` are our-only files (no upstream changes) |
| 22 | `7acee0d64` | Tree speculation with DySpec + multi-path verification | `common/speculative.cpp`, `common/speculative.h` | LOW | `--draft-p-split` used by orchestrator for tree mode |

### Tier 3 — Documentation/Tooling (no conflict risk)

| # | Commit | Feature | Notes |
|---|--------|---------|-------|
| 17 | `7c30bc307` | EPYC toolchain chapter | `docs/epyc/` — our-only directory |
| 18 | `bb21af7cf` | Toolchain chapter update for v2 | `docs/epyc/` — our-only directory |
| 24 | `937bd12ec` | MTP acceptance/speculation benchmark tools | `tools/mtp-acceptance/`, `tools/mtp-speculation/` — our-only directories |
| 25 | `f55bf68de` | .gitignore updates | Trivial merge |

### Confirmed DROPS (4 patches)

| # | Commit | Reason |
|---|--------|--------|
| 21 | `64e0a7080` | Merge commit for HSD branch — content carried by commit #20 (`44255f33b`) |
| 23 | `ffb4ad417` | MTP-1 / MoE self-draft / skip-recurrent / clone-cell mega-commit (20 files, +995/-75). **All techniques concluded NOT VIABLE** (inference-acceleration-index: MTP 0.56x, MoE self-draft negative, hybrid self-accel all negative). No production value. Research artifacts preserved in progress logs. |
| 26 | `b51c905ec` | Hadamard KV smoothing (`--kv-hadamard`). **Superseded by upstream PR #21038** (`744c0c731`, 2026-04-01). Upstream auto-enables identical Walsh-Hadamard rotation when `-ctk`/`-ctv` use quantized types. Our `--kv-hadamard` flag, `llama-hadamard.cpp/h` become dead code. Production config gets Hadamard for free on v3. |
| 27 | `860ab737c` | enable_thinking Jinja fix for PEG parser path. **Superseded by upstream refactor** — `common_chat_template_direct_apply_impl` now passes `enable_thinking` to Jinja for all code paths. |

Also skipped: `7c30bc307` (toolchain chapter v1) — superseded by `bb21af7cf` (v2 chapter which was applied instead).

**Net: 27 patches → 23 to carry forward.**

---

## Conflict Hotspot Map

40 files modified by both our patches and upstream. Ranked by conflict severity.

### CRITICAL — Heavy changes both sides, expect multi-hunk conflicts

| File | Our Lines | Upstream Lines | Our Patches | Upstream Changes |
|------|-----------|---------------|-------------|-----------------|
| `src/llama-kv-cache.cpp` | 350 | 275 | Paged attention (#7-10), SWA optimization (#5-6) | iSWA rotation (#21513), Hadamard rotation (#21038), hybrid memory fix (#21224), seq_id bounds fix (#20887), state read fix (#20273), dynamic head_dim (#20301) |
| `tools/server/server-context.cpp` | 683 | 302 | Paged attention server integration, slot erase (#14-15) | Checkpoints (#20288, #20287, #20671, #20726), kill switch (#20277), `--clear-idle` (#20993), mtmd chunks (#21107), timing fix (#21201), pos_min restore (#21510) |
| `src/llama-graph.cpp` | 211 | 229 | Layer skip (#3-4), tree speculation (#22) | Hadamard rotation (#21038), GDN ops (#19504, #20340), lora_mm scale (#20427), iSWA rotation (#21513), graph reuse (#20463, #20927) |
| `src/llama-context.cpp` | 339 | 176 | Paged attention context management | Pooled embedding (#20840), output buffer (#20781), control vector fix (#20381), graph reuse fixes |

### HIGH — Significant changes one or both sides

| File | Our Lines | Upstream Lines | Notes |
|------|-----------|---------------|-------|
| `common/arg.cpp` | 104 | 241 | Our CLI flags vs upstream's new flags (`--clear-idle`, `--reasoning`, `--tools`, etc.) |
| `include/llama.h` | 69 | 78 | Public API additions both sides |
| `src/llama-model.cpp` | 39 | **1,066** | Massive upstream refactor (NVFP4 #19769, new models, GDN). Our changes small (moe-n-expert wiring) but context completely different. |
| Model files: `qwen3.cpp`, `qwen35.cpp`, `qwen3moe.cpp`, `qwen3next.cpp`, `qwen3vl-moe.cpp`, `qwen2.cpp` | ~40 each | varies | Upstream: NVFP4 (#20506), control vectors (#20653), GDN chunking (#20340). Our: layer skip (#3-4), moe-n-expert (#1). |
| `src/llama-memory-hybrid.cpp` | modified | modified | Upstream `e1cb81748` (unified KV in hybrid memory). Our SSM checkpointing (#16). |
| `src/llama-memory-recurrent.cpp` | modified | modified | Upstream `f93c09e26` (seq_id bounds fix). Our SSM checkpointing (#16). |

### MEDIUM — Manageable conflicts

| File | Notes |
|------|-------|
| `ggml/src/ggml-cpu/repack.cpp` | Our OpenMP repacking (#2) vs upstream changes |
| `ggml/src/ggml-cpu/ops.cpp`, `ops.h` | Our Hadamard ops (DROPPED — but repack touches these too) |
| `ggml/include/ggml.h`, `ggml/src/ggml.c` | Our custom types (DROPPED Hadamard) vs upstream Q1_0 (#21273), NVFP4 |
| `src/CMakeLists.txt` | Our new source files vs upstream additions |
| `gguf-py/gguf/constants.py` | Our model constants vs upstream new models |
| `convert_hf_to_gguf.py` | Our patches vs upstream new model support |
| `common/sampling.cpp` | Minor overlap |
| `tools/server/server-task.cpp`, `server-task.h` | Our slot erase vs upstream task changes |

### LOW — Trivial to resolve

`.gitignore`, `AGENTS.md`, `tests/CMakeLists.txt`, `tools/CMakeLists.txt`, `src/llama-cparams.h`, `src/llama-arch.cpp`, `src/models/models.h`, `src/models/llama.cpp`

---

## Key Upstream Changes to Account For

8 upstream features that directly intersect our patches:

| # | Upstream PR/Commit | Feature | Impact on Our Patches |
|---|-------------------|---------|----------------------|
| U1 | `744c0c731` (#21038) | **Hadamard rotation for better quantization** | **Supersedes our #26.** Auto-enables WHT when KV types are quantized. Same algorithm. Controlled by `LLAMA_ATTN_ROT_DISABLE` env var. |
| U2 | `4eb19514d` (#21513) | **iSWA attention rotation for heterogeneous models** | Intersects our SWA patches (#5-6). New rotation logic in KV cache. Must verify our slot reuse optimization is compatible. |
| U3 | `59db9a357` (#20301) | **Dynamic head_dim and n_rot for SWA** | Changes SWA architecture assumptions our patches rely on. SWA patches may need rewrite. |
| U4 | `50e0ad08f` (#20993) | **`--clear-idle` server flag** | New idle slot management — verify no conflict with our slot erase (#14-15). |
| U5 | `e1cb81748` (#21224) | **Unified KV cache in hybrid memory** | Intersects our SSM checkpointing (#16). Verify hybrid memory API compatibility. |
| U6 | `f93c09e26` (#20887) | **seq_id bounds fix in recurrent memory** | Intersects our SSM checkpointing (#16). May partially overlap. |
| U7 | `5eae9cb1d` (#19769) + `d23355afc` (#20506) | **NVFP4 quantization type** | New type wired through all model files we touch. Context changes in model files. |
| U8 | `c5a778891` (#19504) + `d28961d81` (#20340) | **GATED_DELTA_NET op + chunked fused GDN** | New graph builder patterns in `llama-graph.cpp` where our layer skip lives. |

---

## Cherry-Pick Playbook

### Prerequisite Setup

```bash
cd /mnt/raid0/llm/llama.cpp-experimental

# Save current experimental state
git stash

# Fetch latest upstream
git fetch origin

# Create v3 branch from fresh upstream
git checkout -b production-consolidated-v3 origin/master

# Verify clean state
git log --oneline -3  # should show upstream HEAD
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON
cmake --build build -j96  # baseline build must pass
```

### Phase 1 — Low-Risk Standalone Features

Apply these first. Each is self-contained with minimal conflict expected.

| Step | Commit | Feature | Expected Conflicts | Resolution |
|------|--------|---------|-------------------|------------|
| 1 | `bbcca6dea` | `--moe-n-expert` (Hard Mask) | `common/arg.cpp` (context shift from upstream's new flags) | Add our flag block in the same style as upstream's recent additions. Check `common/common.h` for struct field. Wire through model files — `llama-model.cpp` has massive upstream changes, locate MoE expert count usage. |
| 2 | `0819d1f20` | `--lookup` (prompt lookup) | `common/arg.cpp` (same as above) | Standalone flag addition. Verify upstream hasn't renamed the lookup infrastructure. |
| 3 | `f55bf68de` | .gitignore updates | None or trivial | Accept both sides. |
| **BUILD CHECK** | | `cmake --build build -j96` | | Must pass before continuing. |

### Phase 2 — SWA Optimizations

These depend on KV cache internals that upstream has changed (dynamic head_dim #20301, iSWA rotation #21513).

| Step | Commit | Feature | Expected Conflicts | Resolution |
|------|--------|---------|-------------------|------------|
| 4 | `ca8cfd1ca` | SWA slot reuse optimization | `src/llama-kv-cache.cpp` — **HIGH**. Upstream `59db9a357` changed SWA head_dim handling, `4eb19514d` added iSWA rotation, `17193cce3`/`39b27f0da` toggled SWA KV quant. | Locate the SWA cell iteration logic in the new upstream code. Our optimization adds forward-looking masking to avoid unnecessary cache invalidation. The API around `llama_hparams::is_masked_swa()` may have changed — grep for it. May need partial rewrite. |
| 5 | `7b75d212b` | SWA cell reuse correctness fix | Same area as #4 | Apply immediately after #4. This fixes an edge case in the optimization. If #4 was rewritten, this fix may already be incorporated. |
| **BUILD CHECK** | | `cmake --build build -j96` | | Must pass before continuing. |

### Phase 3 — Paged Attention Stack (HIGHEST RISK)

7 commits forming a dependency chain. This is the single hardest part of the rebuild. `llama-kv-cache.cpp` has 275 lines of upstream changes (Hadamard rotation, iSWA, state fixes) since our fork.

**Strategy**: Apply the stack bottom-up. If cherry-pick produces unresolvable conflicts, consider manual re-implementation of the paged attention feature against the new KV cache API.

| Step | Commit | Feature | Expected Conflicts | Resolution |
|------|--------|---------|-------------------|------------|
| 6 | `39f4949c7` | CPU paged attention for flash attention | `src/llama-kv-cache.cpp` — **CRITICAL**. This is the foundation commit adding block-based allocation. Upstream's KV cache constructor now includes Hadamard rotation setup (#21038), iSWA rotation (#21513). | Study the new `llama_kv_cache` constructor carefully. Our block allocation hooks into cache initialization. The Hadamard rotation fields (`attn_rot_k`, `attn_rot_v`, rotation matrices) are new upstream additions — our paged attention must coexist with them. Also check `src/llama-context.cpp` for context init changes. |
| 7 | `4ff8e2c5a` | Dynamic block allocation | `src/llama-kv-cache.cpp`, `src/llama-kv-block.h` | Extends #6. `llama-kv-block.h` is our-only file (no upstream conflict). Focus on `llama-kv-cache.cpp` integration. |
| 8 | `b217755b3` | Block pool statistics | `src/llama-kv-cache.cpp` | Debug instrumentation. Light conflict. |
| 9 | `cbb124912` | KV cache memory reduction | `src/llama-kv-cache.cpp` | Memory optimization layer. Verify against upstream's new cache sizing (Hadamard matrices add memory). |
| 10 | `6f880097b` | CLI flags for paged attention | `common/arg.cpp` | Flag additions — low risk. |
| 11 | `7b7f8818a` | Trim comments in llama-kv-block.h | `src/llama-kv-block.h` | Our-only file. Trivial. |
| 12 | `9cf32164f` | Unit tests for block pool | `tests/test-kv-block.cpp`, `tests/CMakeLists.txt` | Our-only test file. CMakeLists may need adjustment for upstream's new test structure. |
| **BUILD CHECK** | | Full build + run test-kv-block | | Critical gate — paged attention must build and pass unit tests. |

### Phase 4 — Server Patches

Server has ~20 upstream commits (checkpoints, kill switch, `--clear-idle`, timing fixes). Our slot erase patches are small but the surrounding code has shifted.

| Step | Commit | Feature | Expected Conflicts | Resolution |
|------|--------|---------|-------------------|------------|
| 13 | `45ea13916` | Slot erase without `--slot-save-path` | `tools/server/server-context.cpp` — **MEDIUM**. Upstream added checkpoint logic, kill switch, `--clear-idle`. Our change modifies slot release logic. | Read the new server-context.cpp `slot_release` / `slot_save` methods. Our patch adds a path where slots can be erased even without `--slot-save-path`. Verify upstream's `--clear-idle` (#20993) doesn't conflict. |
| 14 | `505d0c997` | Error handling for force-erased slots | `tools/server/server-context.cpp`, `tools/server/server-queue.cpp` | Small fix. Queue file has minimal upstream changes. |
| **BUILD CHECK** | | `cmake --build build -j96` | | |

### Phase 5 — Research/Acceleration Features

| Step | Commit | Feature | Expected Conflicts | Resolution |
|------|--------|---------|-------------------|------------|
| 15 | `e8f21a4c8` | OpenMP tensor repacking | `ggml/src/ggml-cpu/repack.cpp` — MEDIUM | Our parallelization pragma additions vs upstream's repack changes. |
| 16 | `c5565e6a8` | Layer skip / early exit | `src/llama-graph.cpp` — MEDIUM, `include/llama.h`, model files | Graph builder has upstream GDN + Hadamard additions. Find the attention build section and add our layer exit logic. Model files have NVFP4/control vector additions — context shift only. |
| 17 | `eda635d48` | Layer skip for qwen3vl-moe + qwen3next | Model files — MEDIUM | Same context shift issue. Locate the `build_graph` method in each model file. |
| 18 | `6e49ca1ae` | SSM state checkpointing | `src/llama-memory-recurrent.cpp` — MEDIUM | Upstream `f93c09e26` fixed seq_id bounds. Our checkpointing adds save/restore methods. Verify API compatibility. |
| 19 | `44255f33b` | HSD + freeze-recurrent speculation | `common/speculative.cpp/h` — LOW | Our-only files. Should apply cleanly. |
| 20 | `7acee0d64` | Tree speculation (DySpec) | `common/speculative.cpp/h` — LOW | Our-only files. Should apply cleanly. |
| **BUILD CHECK** | | Full build | | |

### Phase 6 — Documentation/Tooling

| Step | Commit | Feature | Expected Conflicts |
|------|--------|---------|-------------------|
| 21 | `7c30bc307` | EPYC toolchain chapter | None — our-only directory |
| 22 | `bb21af7cf` | Toolchain chapter update | None |
| 23 | `937bd12ec` | MTP benchmark tools | None — our-only directories. Update `tools/CMakeLists.txt` if upstream changed it. |
| **FINAL BUILD** | | `cmake --build build -j96` | Must pass clean. |

---

## Build & Smoke Test Protocol

### Build Command

```bash
cd /mnt/raid0/llm/llama.cpp-experimental
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON
cmake --build build -j96
```

### Smoke Tests — Production Models

Every model in the production stack must load and generate. Expected baselines from inference-acceleration-index v2 benchmarks:

| Role | Model | Path | Test Command | Expected t/s |
|------|-------|------|-------------|-------------|
| worker_explore | Qwen3-Coder-30B-A3B Q4KM | `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Coder-30B-A3B-Instruct-GGUF/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` | `./build/bin/llama-cli -m <path> -n 64 -p "Hello" --no-cnv -t 48` | ~39 t/s |
| frontdoor | Qwen3.5-35B-A3B Q4KM | `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-35B-A3B-GGUF/Qwen3.5-35B-A3B-UD-Q4_K_M.gguf` | `./build/bin/llama-cli -m <path> -n 64 -p "Hello" --no-cnv -t 48` | ~12.7 t/s |
| coder_escalation | Qwen2.5-Coder-32B Q4KM | `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen2.5-Coder-32B-Instruct-GGUF/Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf` | `./build/bin/llama-cli -m <path> -n 64 -p "Hello" --no-cnv -t 48` | ~10.8 t/s |
| architect_coding | REAP-246B Q4KM | (verify path in model_registry.yaml) | `./build/bin/llama-cli -m <path> -n 32 -p "Hello" --no-cnv --moe-n-expert <N> -t 96` | ~8.0 t/s |

### Feature-Specific Tests

| Feature | Test | Pass Criteria |
|---------|------|--------------|
| `--moe-n-expert` | Launch REAP-246B with expert override, verify generation | Coherent output at expected speed |
| `--lookup` | Launch worker with `--lookup`, send 3 prompts | No crash, lookup activates (check server log for ngram matches) |
| Paged attention | Launch 70B+ model with paged attention flags, check RSS | RSS lower than non-paged baseline |
| KV quantization (upstream Hadamard) | Launch Coder-32B with `-ctk q4_0 -ctv f16`, check logs | Upstream rotation auto-enabled (no `LLAMA_ATTN_ROT_DISABLE`). PPL should match v2 `--kv-hadamard` measurements (±0.02) |
| Spec decode | Launch with draft model, send prompt | Acceptance rate > 0, generation speed benefit |
| Slot erase | `curl -X DELETE http://localhost:<port>/slots/0` | HTTP 200, slot released |
| Server health | `curl http://localhost:<port>/health` | HTTP 200 |
| NUMA | `taskset -c 0-47 ./build/bin/llama-server -m <30B> -t 48 --port 9999` | Throughput within 5% of v2 baseline |

### Server Integration Test

```bash
# Launch with orchestrator-like config
./build/bin/llama-server \
  -m <frontdoor_model> \
  -t 48 -c 8192 --port 9999 \
  -ctk q4_0 -ctv f16 \
  --moe-n-expert 6

# Test completions
curl http://localhost:9999/completion -d '{"prompt":"Hello","n_predict":64,"temperature":0}'

# Test health
curl http://localhost:9999/health
```

---

## Orchestrator Compatibility Checklist

Every custom CLI flag and feature the orchestrator uses, confirmed present in v3:

| Flag / Feature | Source in Orchestrator | v3 Status |
|---------------|----------------------|-----------|
| `--moe-n-expert <N>` | `orchestrator_stack.py` (REAP models) | Carry forward (patch #1) |
| `--lookup` | `orchestrator_stack.py:878` (workers, coder) | Carry forward (patch #19) |
| `--kv-hadamard` | `orchestrator_stack.py:950` | **REMOVE** — superseded by upstream auto-rotation. Flag will not exist in v3. |
| `-ctk <type> -ctv <type>` | `orchestrator_stack.py:950` | Upstream native — no change needed |
| `--draft-max <N>` | `orchestrator_stack.py:876,971,982` | Upstream native — no change needed |
| `--draft-p-split <N>` | `orchestrator_stack.py:1007-1011` | Carry forward (patch #22, tree speculation) |
| `--n-layer-exit-draft <N>` | `orchestrator_stack.py:989,997` | Carry forward (patch #3, layer skip) |
| `--n-layer-exit-intermediate <N>` | `orchestrator_stack.py:1002` | Carry forward (patch #3, layer skip) |
| Slot erase API | Server slot management | Carry forward (patches #14-15) |
| Paged attention env/flags | Registry `paged_attention.enabled_threshold_gb` | Carry forward (patches #7-13) |

---

## Post-Rebuild: Production Upgrade

Once v3 passes all validation in `llama.cpp-experimental`:

### A. Binary Swap (llama.cpp)

```bash
cd /mnt/raid0/llm/llama.cpp
git checkout production-consolidated-v3  # branch created in experimental worktree
cmake -B build -DGGML_CPU_ALL_VARIANTS=ON -DLLAMA_CURL=ON
cmake --build build -j96
```

### B. Orchestrator Config Updates (epyc-orchestrator)

| File | Line | Change | Reason |
|------|------|--------|--------|
| `scripts/server/orchestrator_stack.py` | 939 | Update comment: reference upstream #21038 instead of commit `b51c905ec` | Provenance |
| `scripts/server/orchestrator_stack.py` | 950 | Remove `"--kv-hadamard"` from `cmd.extend(...)` | Flag no longer exists — upstream auto-enables |
| `orchestration/model_registry.yaml` | 195 | Update "Cherry-picked to production-consolidated" → v3 | Branch reference |
| `orchestration/model_registry.yaml` | 742 | Update commit reference for lookup if hash changed | Commit reference |

### C. Governance Updates (epyc-root)

| File | Change |
|------|--------|
| `scripts/session/verify_llama_cpp.sh:15` | Change `EXPECTED_BRANCH="production-consolidated"` → `"production-consolidated-v3"` (NOTE: currently stale — says v1, not v2) |
| `.claude/dependency-map.json` | Update notes if branch name referenced |
| `handoffs/active/kv-cache-quantization.md` | Note `--kv-hadamard` replaced by upstream automatic rotation (#21038) |
| `handoffs/active/inference-acceleration-index.md` | Update Build Safety Protocol branch name, Key Artifacts section |

### D. Full Stack Verification

1. Launch full orchestrator stack via `orchestrator_stack.py` — all 8 roles must start
2. Health check all ports (8070-8085 + NUMA quarters 8080/8180/8280/8380 etc.)
3. Spot-check: frontdoor, coder, architect each generate coherent output
4. Verify upstream Hadamard is active: check server logs or confirm `LLAMA_ATTN_ROT_DISABLE` is not set

---

## Rollback Plan

If v3 fails validation:

1. **Production is unaffected** — all work is in `llama.cpp-experimental`, production binary remains on v2
2. To stay on v2: no action needed. `production-consolidated-v2` remains checked out in `/mnt/raid0/llm/llama.cpp`
3. v3 branch preserved in experimental worktree for debugging
4. If partially successful: identify which patches failed, document in this handoff, attempt targeted fixes

---

## Closeout Checklist

- [x] `llama.cpp-experimental` cleaned and `production-consolidated-v3` branch created from `origin/master` (2026-04-09)
- [x] Phase 1 patches applied — moe-n-expert, lookup, gitignore (enable_thinking dropped — upstream fixed)
- [x] Phase 2 patches applied — SWA optimization + fix (applied cleanly, HIGH risk was overestimated)
- [x] Phase 3 patches applied — paged attention stack (7 commits + 2 fixups: GGML_OP_COUNT bump, n_kv scope fix)
- [x] Phase 4 patches applied — server slot erase (applied cleanly)
- [x] Phase 5 patches applied — research features (SSM checkpoint + HSD conflicts resolved, tree spec clean)
- [x] Phase 6 patches applied — docs/tooling (skipped v1 chapter, took v2 instead; MTP tools clean)
- [x] Build passes clean (`cmake -DGGML_CPU_ALL_VARIANTS=ON -DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON -DLLAMA_CURL=ON`)
- [x] Unit tests pass (test-kv-block: 19/19)
- [x] Governance files updated — verify_llama_cpp.sh, inference-acceleration-index.md, master-handoff-index.md, this handoff
- [x] All production models smoke-tested — ✅ 2026-04-10. 4/4 PASS: worker 38.6 t/s, frontdoor 14.3 (+13%), coder 21.7 (+101%), REAP 12.0 (+50%). Upstream spec decode improvements.
- [x] Feature: `--moe-n-expert` — PASS
- [x] Feature: server health + completion — PASS
- [ ] Feature: `--lookup` — REMOVED in upstream. Needs orchestrator compat update.
- [ ] Feature: slot erase — Endpoint returns 404 (path changed). Needs orchestrator compat update.
- [ ] Feature: paged attention RSS — DEFERRED (needs manual check)
- [ ] NUMA throughput validated — DEFERRED
- [ ] Upstream Hadamard auto-rotation confirmed (replaces `--kv-hadamard`) — DEFERRED
- [ ] PPL regression test: `-ctk q4_0 -ctv f16` matches v2 measurements — DEFERRED
- [x] Orchestrator config updated — ✅ 2026-04-10. `--kv-hadamard` removed from `orchestrator_stack.py:950` and `server_lifecycle.py:200`. `--lookup` kept (exists in v3 server). Slot erase endpoint unchanged (POST, not DELETE — smoke test was wrong). `verify_llama_cpp.sh` branch updated. Test updated (18/18 pass).
- [ ] Production binary swap (checkout v3 branch in production llama.cpp, rebuild, restart stack)
- [ ] Branch pushed to `fork` remote
- [ ] This handoff moved to `completed/`

### Build Fixups Applied During Cherry-Pick

| Fixup | Commit | Reason |
|-------|--------|--------|
| GGML_OP_COUNT 96→97 | `4eb4776f8` | Paged attention added `GGML_OP_FLASH_ATTN_EXT_PAGED` |
| n_kv scope fix | `8bc9f585d` | Upstream refactored `build_attn_inp_kv_impl`, `n_kv` not in local scope |
| CMake flags | — | Upstream now requires `-DGGML_BACKEND_DL=ON -DBUILD_SHARED_LIBS=ON` with `GGML_CPU_ALL_VARIANTS` |
| SSM checkpoint stub/restore | — | Lookup patch arrived before SSM patch; stubbed in Phase 1, restored in Phase 5 |

## Future: HIP/GPU Build Path

When GPU hardware is acquired, v3 will need a parallel HIP build configuration. See [`gpu-acceleration-path.md`](gpu-acceleration-path.md) for full details. Summary:

- Add `-DGGML_HIP=ON -DAMDGPU_TARGETS=<arch> -DGGML_HIP_ROCWMMA_FATTN=ON` to build flags
- All 24 custom patches must be verified against HIP backend compilation
- Paged attention patches (Tier 1 #7-13) need specific validation with GPU memory management
- 4 community rocWMMA flash attention fixes (intake-306) are candidates for Tier 2 carry-forward patches
- hipBLASLt grouped GEMM (`USE_HIPBLASLT_GROUPED_GEMM=1/2/3`) is runtime config, no patch needed

Research context: intake-303 through intake-311 in `research/intake_index.yaml`.
