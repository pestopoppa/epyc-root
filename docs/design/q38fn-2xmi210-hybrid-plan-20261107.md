# Q38FN hybrid / 2x MI210 serving: experiment plan (PARKED)

Status: PARKED. Re-open when a second MI210 is installed. Not a row. There is no spec.json or launch.sh by design.
Seed: AK-ASM-H22 (research `scripts/kernel_rnd/autokernel/loop/seeds/hypotheses/07-mi210-asm-port-open-seeds.md`, commit 272b39a1a).
Scope: INFORMATIONAL. The output informs a future stack decision. It makes no champion claim and is no promotion gate.
Q38FN is CPU-only in production today.
Drafted 2026-11-07 (main-inf22 subagent).

## Question
For Q38FN UD-IQ4_XS, how do decode tok/s (first 256 tokens) and prefill tok/s at 8k and 32k compare with the
CPU-only production recipe on 1-GPU hybrid placements (B, C)? Does a 2x MI210 placement (D) with no CPU experts and
the PLE n-gram table in host RAM beat CPU-only at full 262k context? Higher tok/s is better.

## Model facts (from the GGUF, verified 2026-11-07)
- `/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/` (3 shards, 87.2 GiB). Arch is `qwen4exp`.
  48 layers, n_embd 2560, 512 experts with top-10, full_attention_interval 4 (so 12 attention layers),
  head_count_kv 2, key/value length 256, compress_ratios 4 on the attention layers, and an indexer (4 heads, k 128, top_k 2048).
  The other 36 layers are SSM: inner 6144, state 128, conv 4. There are 4 hyper-connections.
- The PLE table is `per_layer_token_embd.weight`, 26.8 GiB. ple.ngram_size 3, 16 heads of about 20M rows each.
  It is consumed by `ggml_get_rows` (`src/models/qwen4exp.cpp:1352`).
- **Placement fact:** in the champion source (62cb6a6af), `llama-arch.cpp:921` maps `LLM_TENSOR_PER_LAYER_TOKEN_EMBD` to
  `LLM_TENSOR_LAYER_INPUT`, and `dev_input` is always `cpu_dev` (`llama-model.cpp:1384`). The table therefore already
  lands in host RAM with no override. Pass `-ot 'per_layer_token_embd\.weight=CPU'` anyway, as an explicit pin, and verify
  it in the load log (`buffer type overrid` / model buffer sizes).
- Routed experts take 55.4 GiB (about 1.154 GiB per layer). Everything else, excluding the table, is about 5.0 GiB. The total off the table is about 60.4 GiB.
- The MTP draft is `MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, 2.6 GiB.
- Operator caveat: the MI210 kernels are tuned best for 8/16-bit quants, and the IQ4_XS expert MMQ/MMVQ kernels on gfx90a are not
  optimized. All GPU numbers are therefore EXPLORATORY. They are a lower bound on what a tuned kernel would give.

## Kernel stores (champion C7r 62cb6a6af; re-resolve at re-open: "champion always current")
- CPU: `/mnt/raid0/llm/kernels/builds/cpu-20261106-62cb6a6af-c7r`
- GPU: `/mnt/raid0/llm/kernels/builds/gpu-20261106-62cb6a6af-c7r`. Precondition: BUILD-OK `source_sha` == the champion, and
  `libggml-hip.so` sha256 == BUILD-OK. Also check `strings libggml-base.so | grep GGML_SCHED_DEBUG`.
- Each launcher sets its own `LD_LIBRARY_PATH=<store>/bin(:/opt/rocm/lib)`. Run `verify_ggml_linkage.sh` per binary first.

## Arms
All arms use llama-server with the same prompts and greedy decoding (temp 0, top_k 1, seed 0, ignore_eos, cache_prompt false)
and `--reasoning off` (Qwen3.x rule 15). Every arm uses MTP draft-mtp n_max 4, p_min 0.5, because production serves MTP.
Every arm is pinned to `taskset -c 0-95 numactl --interleave=all` with explicit `-t 96 -tb 96 --load-threads 96`.
The CPU env comes from `launch_local_inference.sh cpu_env`: GGML_FA_SPLIT_KV=0, GGML_FUSED_DECODE_OFF=1, GGML_IQK=1,
GGML_NOHUGEPAGE_PROCESS=1, and OMP_* cores/spread/active. All arms use `--no-mmap -b 2048`, and `-ub` is fixed per arm (below).

| Arm | Placement | Key argv |
|---|---|---|
| A | CPU-only production recipe (cpu store) | `--device none -ngl 0 -fa on -ub 512 -ctk f16 -ctv f16 -np 1 -md MTP -ngld 0 --device-draft none --spec-type draft-mtp --spec-draft-n-max 4 --draft-p-min 0.5` |
| B | 1 GPU, current hybrid baseline: all experts on CPU | `-ngl 99 --n-cpu-moe 48 -ot 'per_layer_token_embd\.weight=CPU' -fa on -ub 2048 -ngld 99 --device-draft ROCm0` |
| C | 1 GPU, PLE in RAM + smallest N CPU-expert layers that fits | `-ngl 99 --n-cpu-moe N -ot 'per_layer_token_embd\.weight=CPU' ...` (N from the fit probe, 4..8) |
| D | 2x MI210, layer split, no CPU experts, PLE in RAM | `-ngl 99 -sm layer -ts 1,1 -ot 'per_layer_token_embd\.weight=CPU' -c 262144 ... -ngld 99 --device-draft ROCm0` (no `--n-cpu-moe`) |

The production serving shape is np4 at 262144 total. For timing, use `-np 1`, and set `-c` to 32768 in the 8k/32k cells for A/B/C.
D additionally runs at its target `-c 262144`, and its own 8k/32k cells use that same server.
Also record A at `-c 262144 -np 4` (the exact production argv) as the reference.

## VRAM-fit math (estimates; the fit probe measures)
MI210: 64 GiB nominal, about 63.8 GiB practical. Keep a 2 GiB margin, so the target own-PID peak is at most 61.8 GiB per GPU.
- KV (f16): 12 attention layers x 2 kv-heads x 256 x 2 (K,V) x 2 B = 24 KiB/token. That is 0.19 GiB at 8k,
  0.75 GiB at 32k and 6.0 GiB at 262k, upper bound with compress_ratio 4 ignored. Add the indexer keys, about +0.1x.
  SSM state is about 0.12 GiB per sequence.
- The compute buffer at `-ub 2048` is about 2-4 GiB per GPU (a guess; read it from `compute buffer size`).
- The MTP draft on the GPU is 2.6 GiB weights plus its own small KV.

| Arm | Weights on GPU | + KV@32k | + MTP | + compute | Est. peak/GPU | Verdict |
|---|---|---|---|---|---|---|
| B (N=48) | 5.0 | 0.8 | 2.6 | ~3 | ~11.4 GiB | fits |
| C N=4 | 5.0+44x1.154=55.8 | 0.8 | 2.6 | ~3 | ~62.2 GiB | OVER the 61.8 margin, so probe |
| C N=5 | 54.6 | 0.8 | 2.6 | ~3 | ~61.0 GiB | likely the smallest fit |
| C N=6 | 53.5 | 0.8 | 2.6 | ~3 | ~59.9 GiB | fits |
| C @262k | needs +5.3 GiB KV, so N is about 9-10 | | | | | 1-GPU full context only at N>=9 |
| D (2 GPU) | 60.4/2 = 30.2 | 6.0/2 = 3.0 at 262k | 2.6 on GPU0 | ~3 | GPU0 ~38.8, GPU1 ~36.2 GiB | fits with about 23 GiB headroom per GPU |

D has room at 262k with np4. If D wins, the follow-up option is to move the PLE table onto the GPU: D puts about 75 GiB on 127.6 GiB,
and the table would add 26.8 GiB. That is out of scope here. The operator's rule is that the table stays in host RAM because it is the
justified CPU split.

**Fit probe (first, no timing):** C at N = 8, 7, 6, 5, 4 (descending, stop at the first failure) at `-c 4096`, then at `-c 32768`.
Each probe server answers a 4k-token prompt plus 64 tokens. Record the own-PID KFD VRAM peak, sampled during the request, and the
load-log buffer sizes. Pick the smallest N whose peak is at most 61.8 GiB at c32768. For D, do the same at `-c 262144` with
a 32k prompt, per GPU.

## Measurements (per arm x context)
- Prompts: wikitext (`/mnt/raid0/llm/data/wiki.test.raw`) tokenized to exactly 8192 and 32768 tokens. D also gets one 200k-token prompt
  (the "full context" claim cell).
- Per request: prefill tok/s = `timings.prompt_per_second`; decode tok/s = 256 / `timings.predicted_ms`, with n_predict 256.
  Also record draft_n and draft_n_accepted (MTP acceptance), because acceptance can differ by placement only through numerics.
- 3 interleaved reps per cell, with a Latin-square order per rep: (A,B,C,D), (B,C,D,A), (C,D,A,B). Start a fresh server per arm visit
  (the GPU-LEAK-1 rule: timing keeps HIP graphs ON with a fresh server per session, plus an own-PID VRAM guard at 62 GiB that ends cleanly).
  Page cache: one untimed warm load of the shards before rep 1. That avoids the cold-cache VOID (2026-10-21 Block B ruling).
- Own-PID VRAM peak per GPU (KFD, sampled at 0.5 s during each request), and the device busy %.
- Graph splits: one separate census pass per arm with `GGML_SCHED_DEBUG=2 -v`, parsed live (re-use the c8-zerosplit-census
  `Census` parser; `cause` is compiled out, so the reason is derived from the srcs). Report the splits per graph by n_tokens bucket, every
  CPU-assigned node (op, tensor pattern, reason), and the split input bytes. Census passes are NOT timed, because debug printing perturbs timing.
- Also record `graph splits = N` from the reserve log for every timed server.

## Expected splits and justification (pre-registered)
- **PLE GET_ROWS on CPU: JUSTIFIED and indispensable.** The table is 26.8 GiB of random-access n-gram rows. Its per-ubatch output is
  n_tokens x (16 heads x 160?) floats, a few KB per token, so one small upload per graph. It also takes the `token_embd`
  GET_ROWS on CPU, which is the standard llama.cpp input layer. Together these are 1 crossing per graph and are expected in every arm.
- **B:** about 100 splits per decode token (the 2026-11-06 H13b+c KEEP measurement: "remaining 100 splits are inherent --n-cpu-moe
  boundaries"), with 2 crossings per expert layer. These are structural, not defects.
- **C:** 2 x N expert-layer crossings plus the PLE crossing. With N=5 that is about 11 splits per graph. Each crossing is justified only as
  the fit cost: the layer cannot be in VRAM.
- **D:** the PLE/input crossing, 1 GPU0 to GPU1 layer-boundary crossing (`-sm layer`), and any draft-model crossing. Anything else
  is UNJUSTIFIED and gets listed as a fix item (op, tensor pattern, reason). The 2026-11-06 zero-split policy for the served GPU models is
  the bar.
- Per-split cost estimate: (input bytes / 24 GB/s + 30 us) / n_tokens. This is an estimate and is labelled as one.

## Rules
- Metric direction: tok/s, higher is better. Effect = ln(arm/A) x 100 per rep. The point estimate is the median of 3 reps, and the
  range is reported. With n=3 this is a SCREENING result, with no CI claim. A follow-up row is needed only if D or C is within
  +/-10% of A.
- Pre-registered reading (informational): an arm "beats CPU" at a cell iff all 3 reps exceed A's median. It "loses" iff all 3 are below.
  Otherwise the result is "mixed".
- Stop-on-answer: when every arm x cell has 3 valid reps. A unit is valid iff predicted_n=256 and prompt_n equals the target.
  Futility: stop an arm if 2 of its first visits fail to load or OOM. Record that, and the decision table carries it as "does not fit".
- Correctness side check (not gating): greedy first-64-token identity of B/C/D vs A on one 8k prompt. Report the match length.
  IQ4_XS CPU-vs-HIP numerics differ, so a mismatch is reported, not failed.
- Job-side rules (compute-fillers.md): use the shared job_fence (`fence --gpu`, exec, never vendored), explicit threads,
  `--load-threads`, and own-PID port proof before any workload. The smoke holds own-PID VRAM >= 40 s. Results go to an append-only jsonl.
  The job is resumable per visit (rc 75 on STOP/deadline). SOURCE.sha256 is resealed after any edit, and precond rc must be 0 before publishing.
  Never run `git gc` or prune.
- Grant shape at re-open: class cpu+gpu, `--gpu-quiet exclusive` on BOTH GPUs, and claim CPUs 0-95 (all arms use the same
  0-95 footprint for fairness). Port per server. RAM: 87.2 GiB for A plus the page cache, so about 100 GiB private.
- Priority: rank 60 (low), lane gpu.

## Output
`out/RESULT.json`: the decision table (rows = arms, columns = decode@8k, decode@32k, prefill@8k, prefill@32k, D@200k,
VRAM peak per GPU, splits per decode graph, and CPU-assigned ops with justification), with the ratio of each arm to A.
File it under the H22 box (below) with `[belief: ...]` per the wrap-up belief-capture gate.
The result informs the stack decision "Q38FN: CPU-only vs 2x MI210" and nothing else.
