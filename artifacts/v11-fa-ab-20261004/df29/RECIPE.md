# DF2-9 reproducer kit — recipe, code map, run plan (prepared 2026-10-04, NOT run on GPU)

Everything here was prepared without touching the GPU. Nothing in `/mnt/raid0/llm/llama.cpp`, any git
branch, or any live server was modified. CPU work (compile, tokenize, smoke, mock tests) ran under
`region-lock run --cpu-list 0-95 --role build --tag v11fa -- nice -n 19 taskset -c 0-95`.

## 1. Production `:8083` recipe (Qwen3.8-27B target + DFlash2 drafter)

**Sources (all agree):**
- the stack launch record `/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/launches.jsonl` (last `:8083` row,
  `launched_at 2026-10-04T02:48:09Z`, `argv_sha256 b865820d…`, launcher `orchestrator_stack.py reload architect_critic`);
- the launch banner in `/mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log`;
- `/mnt/raid0/llm/tmp/stack-change-8083-batch-20261004/evidence/argv_8083-live-X0.txt` and `live-state.txt`.

**Live-state caveat.** At 05:14Z `:8083` was **not listening**: its pid 1703677 was gone, and the GPU held
the slot server `gpu-20261004-c7f5ac9ad` on `:18183`, holding 55.5 GB. So the recipe below is the
last-launched argv, not a running process. A pending stack change (STACKCHG-8083BATCH-20261004) would
add `-b 512 -ub 512` and `--no-cache-idle-slots`. It is **unsigned**, so the current recipe still has
`-ub 2048`.

```
numactl --membind=3 -- taskset -c 184-191 \
/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin/llama-server \
  -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf --host 127.0.0.1 --port 8083 \
  -np 4 -c 393216 -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --kv-unified --no-mmap \
  -ngl all --cache-ram 65536 --chat-template-file /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja \
  -md /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 \
  --device ROCm0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/architect_critic --device-draft ROCm0
```

- **No `-b`.** llama.cpp then defaults `n_batch` to 2048. `-b 512 -ub 512` is the pending change.
- **Env.** `scripts/server/stack_env.py:build_launch_env`:
  - the canonical OMP block `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false`;
  - no per-role `GGML_*` vars (`architect_general: {}`);
  - `LD_LIBRARY_PATH=<kernel bin>:/opt/rocm/lib:…`.
- **Registry pin.** `stack_topology.yaml:75` declares `architect_critic: dflash2`.
- **Stale recipe file.** The canonical recipe JSON `epyc-inference-research/artifacts/serving-recipes/qwen3.8-27b-q8-gpu-dflash2-np4.json` is OLDER than the live argv (f16 KV, n-max 8, ctx 16384, no kvu). The live argv wins.
- **Drafter n-max.** The DFlash2 drafter has `block_size=8`, so n-max 8 is clamped to 7, which is block_size−1 (`g2_df25_concurrency_grid.py:61`).

**Models**

| file | bytes | GiB | key metadata |
|---|---|---|---|
| `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf` | 29,047,086,048 | 27.05 | arch qwen35 (hybrid GDN): 64 layers; full attention every 4th layer (il = 3, 7, …, 63 → 16 FA layers); D=256, 24 Q heads, 4 KV heads; n_embd 5120 |
| `/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf` | 2,056,414,752 | 1.92 | `general.architecture=dflash`, 5 blocks, n_embd 5120, head 128 (32q/8kv), non-causal, SWA 2048; `dflash.target_layers=[6,20,34,48,62]`; block_size 8; conv k2/g16; selector rank 256, top-k 16; mask token 248070 |

**VRAM**
- **Production process** (np 4, `-c 393216`, q8_0): about **51.9 GiB**. This is the registry `serving_shape.vram_non_kv_gib: 39.15` plus 12.75 GiB of KV, derived in `epyc-inference-research/orchestration/model_registry.yaml:~1595-1620`; the gate budget is 62 GiB.
- **KV rate.** q8_0 KV is 34,816 B/token: 16 layers × 4 heads × 256 × 2 × 34/32. f16 KV is 65,536 B/token.
- **Reproducer configs** (np 1):
  - weights: 27.05 + 1.92 GiB;
  - compute and FA scratch at `-ub 2048`: about 3–4 GiB;
  - GDN rollback ring: about 1.2 GiB (1 × 8 × 149.6 MiB);
  - KV: 0.27 GiB (prod config, q8_0 at 8192) or 2.0 GiB (orig config, f16 at 32768);
  - total ≈ **33–36 GiB**.
- **Preflight thresholds.** The scripts require **≥ 38 GiB free** for server runs (`DF29_VRAM_NEED_GIB`) and **≥ 32 GiB** for the probe, which loads the target only (`DF29_VRAM_NEED_GIB_PROBE`). They print KFD holders when they refuse.
- **Residency proof.** VRAM is sampled every second during each run. Peak minus baseline should be **≥ ~29 GiB**.

## 2. Where DFlash2 takes its target features (champion `90c12df42`, `src-champion`)

**Registration**
- `common/speculative.cpp:1333-1368` (`common_speculative_impl_draft_dflash` ctor): `target_layer_ids = llama_model_target_layer_ids(model_dft)` gives `[6,20,34,48,62]`, so n_extract is 5 and `n_embd_enc = 5 × 5120 = 25600`.
- `:1415-1425` calls `llama_set_embeddings_layer_inp(ctx_tgt, lid, true)` for each extracted layer.

**Capture**
- `src/models/qwen35.cpp:156`: `res->t_layer_inp[il] = inpL;`. This is the **input of layer il**, which equals `l_out-(il-1)`. The features are therefore the outputs of layers 5, 19, 33, 47 and 61.
- `src/llama-graph.cpp:1313-1318` marks them as graph outputs.
- `src/llama-context.cpp:2545-2570` (`extract_layer_inputs`) copies them to host asynchronously after every target ubatch (`:2285`).

**The non-finite check** (`common/speculative.cpp:1490-1560`, `process()`)
- For each target batch it walks the rows per seq in chunks of `n_ubatch(ctx_dft)` and gathers the 5 layers interleaved.
- Each non-finite value is replaced: NaN becomes 0, ±Inf becomes ±65504.
- If the count exceeds `min(16, max(1, size/100))`, it logs `LOG_ERR "%s: rejecting DFlash batch after %zu/%zu non-finite target features (limit=%zu, cumulative=%llu)"` (`:1542`) and returns false.
- Otherwise it logs `LOG_WRN "sanitized %zu isolated non-finite target features"` (`:1549`).

**What the server does next** (this bounds the server reproducer)
- `tools/server/server-context.cpp:3810-3814`: on that false return the server logs `failed to process speculative batch` and **throws `std::runtime_error`** ("TODO: handle error"). The request fails, and the process may die. `df29_server.sh` therefore restarts the server and resumes.
- **On a failing arm the server dies on every failing prompt.** The throw escapes `update_slots`, because `server-queue.cpp:163` has no try/catch, which ends in `std::terminate`. `df29_server.sh` therefore restarts it (`--restarts 2`, default) and resumes at the next prompt. The arm cap is split evenly between the two configs, and the prod config tests the long ~2k prompts right after the control. On a FAIL arm the server path's k/N is bounded by deaths (the verdict says `note=k-bounded-by-server-deaths`); the **probe** gives the full N, because it never dies on NaN.
- `3020800 / 25600 = 118`. The 2026-08-27 failure was a **118-row** chunk with **every** value of all 5 layers non-finite. That means every row was already NaN at the output of layer 5, which is downstream of the first FA layer (il 3) and of GDN layers 0–2 and 4.

**Upstream master `11fe02151` (arm M) has no such guard.**
- `git grep -n isfinite src-master/common/speculative.cpp` shows only the rate/length checks at `:2469` and `:2482`.
- NaN features flow silently into the drafter, so acceptance collapses and the target's own logits go NaN. That shows up as `!!!!` text, because NaN argmax decodes to token 0, `!`.
- For M the scripts therefore print `guard=absent` and judge on garbage text and acceptance.

**Knobs (env/log)**
- `LLAMA_SPEC_EXACT=off|drop|serial` (`server-context.cpp:61`).
- `LLAMA_SERVER_SLOTS_DEBUG=1`.
- `LLAMA_TRACE` (spec-dec trace).
- `GGML_CUDA_LOG_MMVQ_ROUTE=1` (`ggml-cuda.cu:1827`; this is the MMVQ route, not FA).
- `GGML_CUDA_DISABLE_FUSION`.
- `LLAMA_GRAPH_REUSE_DISABLE`.
- `-lv 4` for verbose server logs.
- There is **no runtime FA-kernel selector or FA route log** in the champion. `GGML_CUDA_FA_MASK_SKIP` and `GGML_CUDA_FA_SEQ_ROWS` exist only on the KVU-19 slot builds. FA routing is set at compile time by `GGML_HIP_ROCWMMA_FATTN` and the shape: `ne[1]` query rows × GQA.

## 3. The original DF2-9 reproducer (found)

**Scripts**
- `/mnt/raid0/llm/tmp/df2_bisect.sh` (flags bisect, A–E all passed on the short prompt).
- `/mnt/raid0/llm/tmp/df2_req_bisect.sh` (request bisect: the long prompt fails, the short one passes).
- `/mnt/raid0/llm/tmp/df2_control.sh` (standalone `2046c64e9` control).
- The grid runner is `epyc-inference-research/scripts/benchmark/g2_df25_concurrency_grid.py`, which calls `v7_quality_gate_runner.py --suites olympiadbench_hard --n 12 --seed 42 --temperature 0.6 --top-p 0.95 --top-k 20 --no-enable-thinking --questions-in /workspace/tmp/questions_mtp_ab.json`.

**Failing command** (champion `5c278648a`, rocWMMA OFF, `/mnt/raid0/llm/tmp/champ2/build-hip`)
```
llama-server -m Qwen3.8-27B-Q8_0.gguf -md Qwen3.8-27B-DFlash2-Q8_0.gguf --spec-type draft-dflash \
  --spec-draft-n-max 8 -np 1 -c 32768 -t 8 -tb 8 -b 2048 -ub 2048 -ctk f16 -ctv f16 --device ROCm0 \
  -ngl 99 -ngld 99 -fa on --host 127.0.0.1 --port 8099 --metrics --slots
```

**Prompts**
- `/workspace/tmp/questions_mtp_ab.json`: 12 olympiadbench_hard prompts of **216–955 chars**, about 60–300 tokens. They are **not 2k tokens.** A snapshot is in `prompts/src/`.
- The control `"Name three prime numbers."` (25 chars) **passed**.
- The failing server log was not preserved: a grep for `3020800` under `artifacts-df25/` and `tmp/` found nothing.

**What the original shape implies**
- With `-ub 2048`, a 60–300-token prompt is **one ubatch of n_q = 60–300 rows** against **n_kv ≈ 256–512** (padded) cells.
- Measured token counts (27B tokenizer, `prompts/token_counts.tsv`): raw prompts **60–341 tokens**, plus about 10–20 tokens of chat markup. The control is 5 tokens raw and about 17 in chat markup.
- On a non-rocWMMA build that is the `> 32-row` D=256 **MFMA-MMA** route (`<256,256,32,2>`, 314 VGPRs spilled per REPORT §0.3).
- The 25-char control is about 20 rows, which goes to TILE/vec.
- So hypothesis (1) fits. Hypothesis (2), fp16 VKQ overflow as n_kv·|V|, needs |V| > ~128–256 at n_kv ≈ 256–512, not ~32. The probe measures `max_v` and `max_v_chansum` (max over channels of |Σ_kv V|) directly, so (2) gets a number instead of an argument.

## 4. The kit (all under this directory)

| file | what |
|---|---|
| `df29_server.sh <arm_dir> <out>` | Server reproducer with two configs per arm. **orig**: the exact 2026-08-27 command, f16 KV, `-ub 2048`, the 25-char control first, then the 12 json prompts, DF2-5 sampling. **prod**: the `:8083` recipe at `-np 1 -c 8192 --cache-ram 0`, control + 12 + 2 synthetic ~2k-token prompts, greedy. Prints one `DF29 arm=… config=… mode=dflash2/target-only guard=present/absent verdict=PASS/FAIL/ERROR/INCOMPLETE k=…` line per config into `<out>/verdicts.txt`. |
| `run_probe.sh <arm_dir> <out>` | Wraps `fa_nan_probe` / `fa_nan_probe_master` (arm M). The default is KV {f16, q8_0} × {json prompt 0 at R=2048 (the 2026-08-27 one-ubatch shape), long2k_a at R ∈ {9, 36, 512, 2048}}, with one model load. Prints `PROBE arm=… verdict=…` into `<out>/verdict.txt`. |
| `fa_nan_probe.cpp` | Source. Built as `fa_nan_probe` (champion headers, links `gpu-20260929-90c12df42/bin`) and `fa_nan_probe_master` (src-master headers, `build-master-11fe02151/bin`). No RUNPATH. |
| `df2_e2e.sh <arm_dir> <out>` | Slot step (c). `llama-batched-bench` has **no draft/DFlash support** (checked in `src-champion/tools/batched-bench` and `common/arg.cpp:3967-3973`: `-md` is scoped to SPECULATIVE/SERVER/CLI). It runs `llama-batched-bench -fa on -ctk q8_0 -ctv q8_0 -kvu -npp 2048 -ntg 128 -npl 1,2,4` (no drafter), then a llama-server DFlash2 `-np 4` run at C = 1/2/4 concurrent, reporting aggregate tok/s and acceptance. |
| `df29_client.py` | stdlib HTTP driver. Attributes server-log lines per request by byte window, detects garbage, resumes after a crash, and has a concurrency mode. |
| `df29_lib.sh` | Shared hygiene, described below. |
| `make_prompts.py`, `prompts/` | Deterministic prompt set. `prompts/token_counts.tsv` holds the token counts from the 27B tokenizer (CPU `llama-tokenize`, vocab-only): probe_long2k_a **2286**, probe_long2k_b **2306**, probe_olymp00 **260**, probe_short 17; server long2k_a/b 2274/2294 raw. |
| `locked_prep.sh`, `mock_tests.sh`, `mock/arm-Z` | CPU-only prep: compile, token count, probe smoke, and mock hygiene tests (fake llama-server, no GPU). |

**`df29_lib.sh` hygiene**
- Owned-PID bookkeeping. Each PID is killed with TERM, then KILL, then verified with `ps -p`.
- A watchdog that can never fire at a recycled PID.
- Port-busy refusal (`ss`).
- VRAM preflight and the sysfs VRAM sampler.
- KFD holder listing.
- `/proc/<pid>/maps` proof of the loaded libraries.
- Per-arm flag mapping. `--no-mmap` on the champion becomes `-lm none` on master, because master replaced `--no-mmap` with `--load-mode`. It also detects DFlash and the non-finite guard.

## 5. Arm M (upstream master `11fe02151`): can it load our DFlash2 drafter?

**Statically, yes.** This was checked against `src-master`; the binary was not executed.

**Metadata keys.** Master `src/models/dflash.cpp` reads every key the GGUF carries:
- `dflash.target_layers` (required; master throws if it is absent);
- `block_size`, `conv_kernel_size`, `conv_group_size`, `selector_rank`, `selector_top_k`;
- `attention.sliding_window` and `sliding_window_pattern`;
- `tokenizer.ggml.mask_token_id`.

**Tensors.** Master creates every tensor the GGUF has:
- `fc`, `enc.output_norm`, `output_norm`;
- `selector_{predecessor,successor,hidden}`, created when `selector_hidden.weight` is present, which it is;
- `blk.*.{attn,ffn}_conv_{base,proj}`, `attn_q/k/v/output`, `attn_q/k_norm`, `attn_norm`, `ffn_norm`, `ffn_gate/up/down`.

**Tensor-set diff.** Master versus champion `dflash.cpp`:
- master no longer *references* `ATTN_GATE` and `ENC_AUX_NORM`; the GGUF has neither;
- master adds optional `D2T`, `TOKEN_EMBD`, `OUTPUT`, `ATTN_POST_NORM`, `FFN_POST_NORM`, `LAYER_OUT_SCALE` and `ROPE_FREQS`;
- the GGUF has no `token_embd`/`output`, so master shares the target's head via `ctx_other`.

**Flags.** Master parses `-md`, `--spec-type draft-dflash`, `--spec-draft-n-max`, `-ngld`, `--device-draft`, `-kvu`, `-fa`, `--jinja`, `--chat-template-file`, `--cache-ram`, `-ngl all`, `--metrics`, `--slots` and `-tb`.

**Mapped flags.**
- `--no-mmap` does not exist on master. Its equivalent is `-lm none`, chosen automatically from the strings in the build's libraries. The binary is never executed to do this, because `--help` on a HIP build would initialise ROCm.
- Master's qwen35 also sets `t_layer_inp` (`src-master/src/models/qwen35.cpp:160`).
- `llama_{set,get}_embeddings_layer_inp` keep the same signatures (`src-master/src/llama-ext.h:125,129`), so the probe's DFlash-path check works on M.

**Fallback.** If the M server fails to come up with the drafter, `df29_server.sh` / `df2_e2e.sh` automatically re-run it **target-only** and print `mode=target-only`. A runtime incompatibility therefore shows up in the verdict instead of aborting the slot.

## 5b. CPU-only validation done here

**Probe smoke** (`smoke/champion/`)
- Run with `fa_nan_probe` on Qwen3.5-0.8B-Q8_0 (qwen35 arch, so the same graph code as the 27B: GDN + FA every 4th layer + `t_layer_inp`).
- Settings: CPU build `cpu-20260925-90c12df42` libs, `--ngl 0`, 24 threads, R ∈ {9, 64} × KV {q8_0, f16}.
- Every run passed, with 174 FA ops at R=9 and 30 at R=64; `MAPS` shows only CPU-build libs, plus `libggml-hip.so: NOT LOADED`.
- The 5-layer feature check covered 798,720 values.
- `max_v` is 8.8 for q8_0 and 37.4 for f16, and `max_v_chansum` is 1785–2060. That last figure is the fp16-VKQ-overflow quantity, already at 3% of 65504 on a 0.8B model at 260 cells.
- `--all-nodes-ubatch` mode also passed.

**Mock hygiene** (`smoke/mock_tests.log`): fake llama-server, no model, no GPU.
- crash per NaN prompt leads to restart and resume, giving FAIL k/N, control=OK, nothing left running;
- clean run gives PASS 13/13 and 15/15;
- NaN without crash (HTTP 500) gives FAIL 12/13;
- a busy port is refused (exit 2);
- the e2e bench plus conc 1/2/4 is parsed;
- a server that never becomes healthy gives ERROR at the per-config deadline, with nothing left running.

**Master probe**
- `fa_nan_probe_master` is compiled against src-master headers and `build-master-11fe02151/bin`.
- Link resolution was checked only. It was not run, because master's `libggml.so` NEEDs `libggml-hip.so` and running it would open `/dev/kfd`.
- Master ggml is 0.25.3, while the champion and arms are 0.16.0. Both name their library `libllama.so.0`, so **never** run the champion-API probe on M or vice versa: the struct layouts differ (`n_outputs_max_per_seq` added and `moe_spec_*` removed on master). `run_probe.sh` picks the right binary from the arm name.

## 6. Per-arm wall time (estimates; the GPU path was not executed)

| step | estimate | cap |
|---|---|---|
| `df29_server.sh` | Two server loads, each about 45–70 s: `--no-mmap` 29 GB from page cache plus upload and init. Orig sends 13 requests and prod 15, each with `max_tokens` 32 at about 1–3 s per request. **≈ 3–4 min** | `--cap 300` (deadline-driven, watchdog at cap+60) |
| `run_probe.sh` | Load with mmap is about 20–40 s. Ten contexts: R=9 over ~2.3k tokens is about 260 ubatches at ~50–80 ms each (callback syncs included) per KV type; the rest take seconds. **≈ 1.5–2.5 min** | `--cap 180`; probe `--time-cap` cap−25 |
| `df2_e2e.sh` | batched-bench, about 14k PP tokens plus 3×128 TG, ≈ 40–70 s including load; server load about 60 s; C=1/2/4 at 128 tokens, about 20 s. **≈ 3–4 min** | `--cap 300` |
| **Total for 5 arms** | A, B, C, D and M with server + probe ≈ 5 × (4 + 2) ≈ **30 min**. With e2e as well ≈ **50 min**. | Can be cut with `--configs orig`, `--n-orig 6`, `--no-long`, `--kv q8_0`, `--R-long 9,36,512`. |

## 7. Suggested slot invocation (GPU window only)

```
D=/mnt/raid0/llm/tmp/v11-fa-ab-20261004/df29; R=$D/runs/$(date -u +%Y%m%dT%H%M%SZ)
for A in /mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-A /mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-B \
         /mnt/raid0/llm/kernels/builds/gpu-20261004-5026470c6-C /mnt/raid0/llm/kernels/builds/gpu-20261004-2e0f9dd06-D \
         /mnt/raid0/llm/tmp/v11-fa-ab-20261004/build-master-11fe02151; do
  n=$(basename $A); bash $D/df29_server.sh $A $R/$n/server --cap 300; bash $D/run_probe.sh $A $R/$n/probe --cap 180
done
grep -h '^DF29 \|^PROBE ' $R/*/server/verdicts.txt $R/*/probe/verdict.txt
```

Arm A (rocWMMA ON) is the positive control and must PASS everywhere. If A fails, the instrument or the environment is suspect, not the kernel. On a FAIL, re-run the probe with `--all-nodes-ubatch <ubatch of first_bad>`, restricted to that prompt/R, to name the first non-finite op.

## 8. Risks and limitations

- **Callback splits.** The eval callback splits the graph at every inspected node (16 FA + 64 `l_out` + 2 per ubatch). That can disable HIP-graph capture and some op fusion on the probed run. Kernel *selection* (TILE/MMA/vec/WMMA) is a function of shape only and is unchanged, but fused-op numerics may differ slightly from the server. The server reproducer is the unperturbed ground truth.
- **Probe prompt text.** The probe tokenizes chat-marked text (`probe_*.txt`) itself. Row counts match the server prompts only approximately; the template system preamble differs.
- **Prod-config differences.** The prod config runs `-np 1 -c 8192`, not np 4 / 393216. The FA shape depends on n_q (rows) and n_kv (used cells, padded to 256), not on `-c`. np 1 vs np 4 changes only the slot count and the GDN RS ring.
- **Master never executed.** The master binaries and `fa_nan_probe_master` were never run here, because the master build is HIP-linked and no CPU-only master build exists. Only compile and link resolution were checked, plus the champion probe smoke on CPU with the same source.
- **Drafter FA not probed.** The drafter's own FA (D=128, non-causal, SWA) is not probed. The DF2-9 message is about *target* features, which are computed before the drafter runs, so the target is where to look.
- **No GPU validation.** No GPU run validated these scripts end to end. Hygiene and verdict logic were exercised on CPU against a mock llama-server (`smoke/mock_tests.log`).
