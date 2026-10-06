# GPU27B_JETLONG_TEST: full Jet-Long long-context test on Qwen3.8-27B Q8_0 (MI210, DFlash2)

Read-only design, 2026-10-06. Nothing was built, started or opened. This replaces the CPU-35B hybrid study (dropped by the operator).
Evidence: GGUF headers read with gguf-py; jetlong worktree `/mnt/raid0/llm/worktrees/llama-jetlong-proto-20261006` @ f06123436; E1 logs in
`/mnt/raid0/llm/tmp/yarn-e1-20261004/results`; `jetlong/DESIGN.md` + `LONGCTX_PLAN.md`; `gpu-backlog-20261006/RUNBOOK_NEXT_SLOT.md`.

## 1. Model facts (Qwen3.8-27B-Q8_0.gguf)
- arch `qwen35` (hybrid, NOT all full attention). `context_length` 262144. `block_count` 65 = 64 layers + 1 nextn/MTP layer (unused with `-md` DFlash2).
- `full_attention_interval` 4 -> **16 full-attention layers**, 48 GDN layers. n_head 24, **n_head_kv 4**, key/value length 256, **n_rot 64**,
  rope sections [11,11,10,0] (IMRoPE, freq_base 1e7). Weights 27.05 GiB; DFlash2 drafter file 1.92 GiB.
- Per cell (all 16 attn layers): KV q8_0 = 34 KiB (matches E1's 8.5 GiB at 262k); Jet-Long side cache f32 = 16 KiB (64x4x4 B x 16).
- GDN recurrent state is small (~0.15 GiB per sequence), constant in context.

## 2. Does the prototype run on HIP as-is? Verdict: nearly. One mandatory change, two verify items.
Hook: `llama_jetlong_attach` (llama-model.cpp:2100) accepts a plain `llama_kv_cache` or the attention half of `llama_memory_hybrid`; qwen35
uses the hybrid wrapper, so it attaches. The rope gate (llama-context.cpp:278) accepts IMROPE with no YaRN. Flag path
common.cpp:1683 -> cparams exists. The DFlash2 drafter's memory is a different type (iswa/shared), so it falls into the "unsupported / shares cells; disabled"
warnings. Confirm in the log that the drafter context does not abort.
Op coverage in `ggml/src/ggml-cuda/ggml-cuda.cu` (this tree): GET_ROWS (q8_0->f32), SET_ROWS (f32->f32/f16, I32/I64 idx), CONCAT, CONT, CPY, SOFT_MAX
(with mask), ROPE (contiguous_2 src; `is_imrope` present in rope.cu so `ggml_rope_multi` works), MUL_MAT (F32/F16/Q8_0 src0, f32 src1) all declared supported.
Ops used by llama-jetlong.cpp: add, mul, cast, concat, cont, get_rows, set_rows, mul_mat (set_prec F32), permute/view/reshape, rope_ext, rope_multi, soft_max_ext. No gap.
1. **MANDATORY change**: `llama_kv_cache::jetlong_init` (llama-kv-cache.cpp:1849-1895) allocates the side cache with `ggml_backend_cpu_buffer_type()`
   ("CPU-first prototype"). On HIP the scheduler would then place set_rows/the s_rot mul_mat on the CPU backend (src buffer is CPU) or copy 8 GiB per step.
   Fix: allocate each `jl_kgrp[ikv]` from the buffer type of `layers[ikv].k->buffer` (same device as that layer's KV), ~10 lines. Do it on a child branch
   `llama.cpp-experimental-jetlong-gpu-20261006`; never commit to production or to the jetlong-proto branch.
2. Verify (cheap, in the build step): `test-backend-ops` for MUL_MAT with q8_0 src0 that is a PERMUTED VIEW with batch dims 4 x 4 (`kp` in jetlong), n_kv up to 524288, f32 prec; and
   ROPE with imrope sections and a per-row 4-component position tensor. The smoke run (section 6) exercises both end to end.
3. Optional patch (reduces VRAM, section 3): side cache type f16 (CTX-3a C1 follow-on). `set_rows` f32->f16 is supported on HIP. It changes numerics slightly, so
   keep the f32 arm as the correctness reference at 300k.
4. Risk, not a blocker: the reserve graph deliberately has no Jet-Long nodes (f06123436), so the first active ubatch grows the compute buffer at runtime on top of the ggml-cuda
   legacy pool that never frees (NO_VMM). Budget headroom; use the stage-300k peak to extrapolate before the 524k stage.

## 3. VRAM budget (GiB, 64 GiB card = 63.9 usable; :8083 parked/stopped, it holds 54.5 now)
Calibration (E1, ub 2048, no drafter): static 37.9 -> peak 52.72 at 262k (+14.8 unexplained); YaRN 524k peak 63.93 (clamped by the card). Production-ub runtime growth
was +7..8 GiB. I assume +5 at tiny ub (UNMEASURED; this is the main uncertainty, the 300k stage measures it).
Transients (n_kv = current depth, not -c): score tensor S = n_kv x ub x 24 x 4 B, ~5 live; V f32 + transposed copy = 2 x n_kv x 4 KiB; epoch-change row rebuild ~4.5 GiB at 524k, shares the V transient.

| item | 300k | 524k | 1M |
|---|---|---|---|
| weights | 27.05 | 27.05 | 27.05 |
| DFlash2 drafter + ctx | 2.2 | 2.2 | 2.2 |
| KV q8_0 (34 KiB/cell) | 9.7 | 17.0 | 34.0 |
| side cache f32 / f16 | 4.6 / 2.3 | 8.0 / 4.0 | 16.0 / 8.0 |
| JL transients at ub 32 (5S + V pair) | 6.9 | 11.5 | 23 |
| base compute + FA scratch | 2 | 3 | 5 |
| runtime growth (assumed) | 5 | 5 | 5 |
| **total, f32 side, ub 32** | **57.5 fits** | **73.8 no** | 111 no |

Offload plan for 524k (needs about -10 GiB; all levers are cheap because the Jet-Long ubatch costs 0.25-0.4 s while a CPU FFN layer adds ~2 ms/ub):
- `-ub 16 -b 16`: -3.75 (transients 7.75). Costs ~25% in the sub-262k fill (weights re-read per ub).
- `-ot "token_embd.weight=CPU"`: -1.26, free (lookup only).
- `-ot "blk\.(<list>)\.ffn_(gate|up|down)\.weight=CPU"`: 0.27 GiB per layer. 24 layers = -6.5 (prefill +<15%, decode ~+35 ms/token). Name check: dense `ffn_*` tensors, see
  tensor dump (blk.3.ffn_gate/up/down.weight Q8_0). Pick layers from the top end so the GDN/attention interleave is untouched.
- Config A (no extra code): ub 16 + embd + 24 FFN layers CPU -> ~62.3. Config B (f16 side patch): ub 16 + embd + 12 FFN layers -> ~61.6. Both are THIN (1.6-2.3 GiB under the card).
  Fallback if the stage-300k peak extrapolates worse: `-ub 8` (-1.9), more FFN layers, and cap the 524k stage at ~480k.
- Rejected: `--no-kv-offload` (puts all 16 layers' KV and attention on the CPU: it is the CPU-bound regime we are escaping); host side cache (the s_rot matmul would run on CPU);
  drafter on CPU (`-ngld 0`, only -2.2 and kills acceptance data).
- 1M does NOT fit one MI210 (KV 34 + side 8-16 + weights 27 = 69-77 before transients). It needs the planned second MI210 (`--split-mode layer`, KV and side cache follow
  their layer) or a fused kernel (no f32 V copy, no score tensors). Out of scope for this test; the 524k result is the gate for it.
- Parked :8083 is not enough: a parked server still holds ~59 GiB (E1 launch_arm.sh note), so :8083 must be STOPPED by the executor.

## 4. Test design (one fill, one question per stage)
Arms: **JON** (jetlong, `--jetlong-window 2048`, native 262144, no YaRN) is the only new run. Baselines are reused from E1 (`results/A1`, static YaRN f2 to 524288: prefill 399/179/106/77 tok/s by
depth band, peak 63.93, needle reports `needle_{128k,240k,400k,500k}.jsonl`) and E1 A0 (native <=262k). E1 needles sit at 10..90% depths of its own stages, so the comparison on
recall is by depth band, not the same needle. A same-prompt Y524 control costs ~71 min (E1 A1 wall 4254 s): run it as a separate window only if JON shows a signal.
The in-window control comes free: stage S0 below is inside 262144, where jetlong builds nothing (bit-identical to stock by design), so it is the native arm on the same server.
- Haystack: reuse `yarn_needle.py` plain-prose segments with the existing user-turn-per-segment chaining so each stage prefills only its new segment (prefix reuse holds with `--cache-ram 0`, `-np 1`).
- Needles (declarative sentences about fictional entities, as in E1), unique answers, at absolute token positions **75k, 150k, 270k, 290k, 400k, 500k**.
- Stages (cumulative tokens), ONE question each that asks for all needles present in context, no per-request deadline (the harness timeout is the window cap):
  - S0 at ~255k: needles 75k, 150k (in-window control; also the native arm).
  - S1 at ~300k: 75k, 150k, 270k, 290k (first above-native stage, G=2; first epoch rebuild at 262144).
  - S2 at ~520k (total incl. answer < 524288, G=2): all six.
  Score per needle (strict + lenient) with the E1/niah_scorer graders; failures and timeouts count in the denominator.
- Decode probe after each stage: 256 forced greedy tokens, record tok/s and DFlash2 accepted/drafted (server log, `--verbosity 4`); E1 reference decode without drafter at depth ~11-12 tok/s.
  Stock FA decode at 300k/524k comes from E1 A1 (depth rows). Expect JON decode well below that (V f32 copy rebuilt every step: ~60 ms/step extra at 524k).
- Persist every call as it completes (calls.jsonl), VRAM sampler `kfd_sampler.py` throughout (peak per stage, plus a tripwire: abort the stage if free VRAM < 1.5 GiB).

Wall-time estimate (E1 rates, ub 2048; JON region modelled by bandwidth, UNMEASURED):
| segment | tokens | rate (tok/s) | seconds |
|---|---|---|---|
| 0-128k | 128k | 399 | 321 |
| 128k-240k | 112k | 179 | 624 |
| 240k-262k | 22k | ~106 | 207 |
| (ub 16 overhead on the stock part, +20%) | | | +230 |
| 262k-300k (JL, ub 16: ~100) | 38k | ~100 | 380 |
| 300k-520k (JL, ub 16: ~85 mean, ub 32: ~112) | 220k | 85 | 2590 |
| questions + 3 decode probes + load + drain | | | ~450 |
Total ~4800 s = **~80 min** (ub 32 variant ~70 min; plausible range 65-110 min, dominated by the unmeasured JL rate). Does not fit the 55 min inner budget.

## 5. Window mechanics
- Needs: schedule entry via `mkentry.py` (holder autokernel, device mi210_0, campaign e.g. `yarn-jonlong-27b`), `--compute-grant` (coordinator-daemon message id; workspace-ec is not a consumer row in
  compute_policy.yaml, so ask the operator for a grant id or token), `gpu_window_executor open --roles architect_critic --ports 8083 --stack-owner-session workspace-ec`; it drains :8083
  (<=10 min), stops it, and refuses on any other KFD process, a stack-change pending marker, or gpu-quiet exclusive held. Then `region-lock run --gpu-quiet exclusive`, run, release, `gpu_window restore`
  (serving proof) AFTER the lock returns. Copy `run_e1mem.sh` structure.
- Length: an entry >3600 s needs `"operator_approved": true`, and the open itself refuses expected_end > now+60m, so a 85-95 min single window requires the operator token. Without it use TWO windows:
  W-A (~30 min): load, fill to 300k, S0 + S1, `slot save` (KV 9.7 GiB + GDN state; side cache is rebuilt on restore because `state_read` invalidates it, which is also a free epoch-rebuild test);
  W-B (~50 min): restore, fill to 520k, S2. Save path `--slot-save-path` scratch dir on RAID0. W-B is tight against the 52 min inner cap; a ub-32 variant is safer on time but needs the memory margin.
- Mandatory 1-minute smoke on the EXACT argv before measuring (inside the window, after the card is free): same binary/flags with `-c 524288` plus `--jetlong-native 1024` so Jet-Long is active
  on a ~3k prompt (G=3). It must show: `Jet-Long ON` for the main context, side cache on a ROCm buffer (log size matches 8.0 GiB or 4.0 GiB, KFD VRAM rises by it), no CPU fallback of set_rows/mul_mat
  (`GGML_SCHED_DEBUG=1`), no drafter-context abort, 8-token answer correct, `verify_ggml_linkage.sh` ok and non-zero VRAM sampled DURING the run. Exit on any failure; restore runs from the EXIT trap.
  The smoke cannot test the memory peak (transients scale with depth), which is why S1's measured peak gates S2.
- Argv (single slot): `llama-server -m Qwen3.8-27B-Q8_0.gguf -c 524288 -np 1 -t 8 -b 16 -ub 16 --flash-attn on --jinja -ctk q8_0 -ctv q8_0 --no-mmap -ngl all --cache-ram 0 --device ROCm0
  -md Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --device-draft ROCm0 --spec-type draft-dflash --spec-draft-n-max 7 --jetlong-window 2048 -ot "token_embd.weight=CPU" -ot "<ffn layers>=CPU"`
  with the production chat template and a scratch slot path; THP/env as production GPU recipe (no `GGML_NOHUGEPAGE`; that shim is CPU-decode-only).

## 6. Build (HIP, production gfx90a flags)
Copy the configure line of `/mnt/raid0/llm/tmp/copy-spec-eval-20261006/width/champ-build/build.sh`:
`cmake -S <worktree> -B /mnt/raid0/llm/tmp/jetlong-gpu-build-20261006/gpu -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DGPU_TARGETS=gfx90a -DGGML_HIP_GRAPHS=ON -DGGML_HIP_NO_VMM=ON
-DGGML_HIP_MMQ_MFMA=ON -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DGGML_OPENMP=ON -DLLAMA_CURL=OFF -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib'
-DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++ -DCMAKE_C_COMPILER=/usr/bin/gcc-15 -DCMAKE_CXX_COMPILER=/usr/bin/g++-15`, targets `llama-server llama-bench test-backend-ops`, built under
`region-lock run --cpu-list` (builds take the CPU region lock; no GPU use, so it can be done before the window and in parallel with other planning).
Source = child branch of f06123436 carrying the section-2 change(s). The jetlong branch is based on v10 `ffc1bac82` so the gfx90a kernels are the production ones. Pre-flight per CLAUDE.md:
`.so` mtime after the branch tip, `strings libllama.so | grep -c jetlong`, `libggml-hip.so` next to the binary, `LD_LIBRARY_PATH` set to that bin dir (three ggml generations), and `ldd` is NOT proof of HIP:
sample VRAM during the smoke.

## 7. Risks, ranked
1. Peak VRAM at 524k (assumed +5 GiB runtime growth, reserve graph without JL nodes): margin 1.6-2.3 GiB on paper. S1 measures it first.
2. JL region speed is a bandwidth model, not a measurement (could be 2x worse: window 110+ min).
3. DFlash2 acceptance with a drafter that sees stock-RoPE target states while the target uses grouped positions above native: unknown, that is a measurement (the design predicts a blip per epoch).
4. Batched permuted q8_0 mul_mat path on gfx90a may fall to a slow dequant path (check in test-backend-ops before the window).
