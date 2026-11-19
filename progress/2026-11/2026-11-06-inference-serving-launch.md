# 2026-11-06 — C6 inference serving launch commands (operator support)

## Scope

Operator-support session for manually launching the current champion-candidate (C6)
models outside the frozen production stack. No kernel build, no model change, no
measurement claim, no production cutover.

## Champion identity used

- C6 champion: `65da39eb1fe7fddbfa7de81cc2f39d54a6b2a428` (supersedes the earlier C6
  snapshot `729599d69`).
- CPU store: `/mnt/raid0/llm/kernels/builds/cpu-20261105-65da39eb1-c6fold2`
- GPU store: `/mnt/raid0/llm/kernels/builds/gpu-20261106-65da39eb1-c6fold2`
- Both `llama-server` binaries report `version: 10512 (65da39eb1)`.

## Canonical sources used

- 27B GPU: `epyc-inference-research/artifacts/serving-recipes/qwen3.8-27b-q8-gpu-dflash2-np4.json`
  and eval variant `.../eval/qwen3.8-27b-q8-gpu-dflash2-longctx196k-np1.json`.
- 35B GPU: `epyc-inference-research/artifacts/serving-recipes/qwen3.6-35b-a3b-q8-gpu-mtp.json`
  and eval variant `.../eval/qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4.json`.
- Canonical argv emitter: `epyc-inference-research/scripts/benchmark/m12_launch_argv.py`
  (imports `Recipe.server_argv`/`server_env`; never hand-types argv).
- Q38FN CPU recipe: `autokernel/campaigns/ak-q38fn-cpu-decode-20261003/inputs/q38fn-cpu-t48-mtp-d4.recipe.json`
  (`q38fn-dd6c9cdbd-cpu-t48-mtp-d4`; t48 bundle, MTP d4 p0.5, 48 threads, UD-IQ4_XS).
- 35B CPU serving shape: production frontdoor `:8070` shape recorded in
  `handoffs/active/harness-program.md` and `docs/reports/sr6-qwen36-width-diagnostic-20261101/`
  (`-np 4 -c 262144 -t 96 -ub 2048`, q8_0 KV, MTP d4, `--no-mmap --mlock --cache-ram 32768
  --ctx-checkpoints 32`).

## What was delivered

- GPU 27B command: canonical `qwen3.8-27b-q8-gpu-dflash2-np4`, plus a serving variant
  `-np 4 -c 262144` (64k/slot) for OpenCode. Both keep DFlash2 n-max 8.
- CPU Q38FN command: canonical t48 bundle with MTP, first at `-np 1 -c 8192`, then a
  corrected OpenCode serving variant `-np 4 -c 262144` (64k/slot).
- GPU 35B command: long-context recipe `-np 4 -c 786432` (196k/slot), MTP n-max 4,
  with `--ctx-checkpoints 8 --cache-ram 16384`.
- CPU 35B command: frontdoor-shaped `-np 4 -c 262144`, q8_0 KV, MTP n-max 4,
  `--kv-unified --no-mmap --mlock --cache-ram 32768 --ctx-checkpoints 32`.

## Live observation

A Q38FN CPU server was launched by the operator on `:8074` (PID 1344098) with the
canonical `-np 1 -c 8192` command.

- `/health` returned `{"status":"ok"}`.
- Model loaded: Qwen3.8-Flash-Next UD-IQ4_XS, `n_ctx=8192`, `total_slots=1`.
- MTP was active: test completion returned `draft_n=11`, `draft_n_accepted=9`,
  `predicted_per_second=30.13`.
- OpenCode then compacted on a 16,450-token request: the client reads `n_ctx` from
  `/props`, so the canonical 8k benchmark recipe is not a usable harness-serving shape.
- Process affinity was wrong: `taskset -pc 1344098` reported `0`, and
  `/proc/1344098/status` had `Cpus_allowed_list: 0`; all 242 threads were on CPU 0,
  not the requested `0-95`. The command text itself is correct; a fresh
  `taskset -c 0-95 numactl --interleave=all` shell returns `0-95`, so the narrowing
  happened in the operator's launch wrapper/terminal.
- NUMA placement was uneven (node totals ≈ 5.5 / 37.6 / 39.5 / 10.5 GB), consistent
  with `--interleave=all` fallback under low node free memory rather than a clean
  25/25/25/25 placement.

No process was killed or restarted by this session. The operator was advised to stop
only the captured PID and relaunch with the corrected serving shape and then verify
`Cpus_allowed_list: 0-95`.

## Open follow-ups

- Restart the Q38FN CPU server with `-np 4 -c 262144` (or `-np 1 -c 262144` if
  concurrency is not needed) so OpenCode has enough context.
- Re-check CPU affinity after every manual launch; the prior launch lost the 0-95
  mask.
- For 27B, the canonical np4 recipe is 16k total = 4k/slot; use `-c 262144` for
  64k/slot, or the long-context np1 recipe for one 196k slot.
- For 35B, use the long-context np4 recipe (`-c 786432`, 196k/slot) on GPU; on CPU use
  the frontdoor `-np 4 -c 262144` shape.

## 2026-11-06 follow-up review (live PID 1394163, C6)

**Correction to the affinity finding above.** `Cpus_allowed_list: 0` in
`/proc/PID/status` is the *main thread* mask. On the live C6 Q38FN process, 47
compute threads carry masks `2,4,...,94` and consume 4720% CPU (47 cores at
~100%); the 195 mask-0 threads are not compute. `taskset -pc` reports the main
thread only. The earlier "all 242 threads on CPU 0" reading is not supported and
is not a launch defect: `taskset -c 0-95` is working.

**Live shape.** `:8074` slot 2 was processing a **57,081-token prompt** at
`n_ctx=65,536`; `:8083` slots held 20,954- and 52,563-token prompts. The 12.5
t/s Q38FN `print_timing` is therefore long-context decode, not the 8k benchmark.
The codified Q38FN anchor is `ctx=8192`, `np1`, 102-token prompt, 256 decode,
temperature 0, top_k 1, ~50 tok/s (`q38fn-cpu-t48-mtp-d4.recipe.json`;
`ch27/qual_fixture.json`; `blockB-20261021/b/compare-q38fn.json`). The production
`:8074` log shows 37.65 tok/s at ~3.3k context.

The 27B has **two different references**: the canonical np1/16k/f16 recipe is
**76.36 ± 0.71 tok/s** (79.6 single sample) at acceptance 0.73
(`/mnt/raid0/llm/tmp/x0-27b-quants/results/report.md` shape (a));
the production `:8083` shape (np4, 393k unified, q8_0 KV, n_max 7) is
**41.2 / 37.1 tok/s at 2k / 50k** at acceptance 0.37-0.39, and agentic temp-1.0
traffic is **25-30 tok/s at 57-152k** (`progress/2026-10/2026-10-03-ak-ds41-main.md:41,93`).
The live 29-31 at 50k is the agentic band, not the 80 tok/s canonical shape.

At 12.5 t/s the CPU moves ~90 GB/s (7.2 GB/token), only ~19% of the 470 GB/s
DDR5 roofline; the 8k benchmark was ~292 GB/s. The 57k case is **attention/FA-
bound, not bandwidth-bound**, so `-t 96` and IQK-FA are the priority experiments
and the NUMA skew is a second-order latency issue, not the main cause.

**NUMA placement is out of spec.** `numastat -p 1394163`: 13.0/39.1/42.4/16.0 GiB
(max deviation 38.4% vs the recipe's <=15% precondition). The 68.3 GiB model
buffer is 10.0/28.2/17.1/13.0 GiB; the 6 GiB KV cache is 5.8 GiB on node 2.
`numa_maps` is `interleave:0-3`, so this is allocation fallback under page-cache
pressure, not a missing `numactl`. Fix: stop the captured process, run
`/mnt/raid0/llm/tmp/inf70/evict_nodes_force.sh 58`, relaunch with the same
argv, then re-check `numastat -p` (<=15%) and `THP_enabled: 0`.

**Missed CPU feature: IQK-FA.** C6 `65da39eb1` is built with
`GGML_IQK_FLASH_ATTENTION:BOOL=OFF`; `libggml-cpu.so` has no
`ggml_backend_cpu_set_iqk_fa`/`iqk_fa_*` symbols. The qualified experimental
store `cpu-20261031-729599d69-c6-iqkfa-on` (10500) has it ON; V11-102 is PEND
and its timing is owed. This is the main long-context CPU lever to A/B, with
the caveat that it is source `729599d69` (no Q8_0 prefill fold) and has
observed non-zero logit deltas with top-1 unchanged.

**GPU.** No missing flags: the C6 GPU store has HIP graphs, rocWMMA FA and
MFMA MMQ ON; live `rocm-smi` shows 100% use, 202-207 W, mclk 1600, sclk 1700.
The 262144 context is a custom 4x65k shape (canonical np4 is 16384; longctx
np1 is 196608); 83% VRAM is the trade. Optional: `--cache-ram 32768
--ctx-checkpoints 8` from the longctx recipe for prefix reuse/TTFT.

**Co-residency.** `184-191` are the SMT siblings of `88-95`, and the CPU
server's workers use even CPUs 88/90/92/94; the GPU host threads therefore
share four physical cores. The MI210 is on NUMA node 1 (`rocm-smi --showtopo`),
while `184-191` is node 3. For co-running, node-1 odd CPUs
`25,27,29,31,33,35,37,39` avoid both the SMT siblings and the worker cores.
This changes the canonical benchmark shape; test, do not assume.

## Local-launch optimization matrix (started 2026-11-06 14:18Z)

Artifact: `artifacts/compute/local-launch-optimization-20261106/`. One server at
a time under `region-lock`; fixed wikitext2 prompts; greedy `/completion`;
per-arm `result.json` with timings, acceptance, THP, thread masks and
`numastat -p`.

First CPU 32k screen (prompt 27,781 tokens, primary request = first 256-token
decode; repeats hit EOS and are raw-only):

| arm | tok/s | note |
|---|---:|---|
| champion t48, np4/262k, f16 | **16.07** | baseline; NUMA max dev 20.7% |
| champion t96 | 15.19 | all 96 cores, still slower |
| IQK-FA store t48 | 14.73 | FA path slower on this shape |
| IQK-FA store t96 | pending | |

The 8k reference on the same harness measured 46.98 tok/s. Acceptance at 27.8k
is ~0.37-0.48, down from ~0.79 at short context. This is consistent with the
live 12.5 tok/s at 57k.

Full CPU 32k screen (primary = first 256-token decode): champion t48/np4 **16.07**;
t96 15.19; IQK-FA t48 14.73; IQK-FA t96 15.15; t96/np1 15.79; t96/no-MTP 14.95;
t96/q8-KV 15.12; t96/unified 15.23. **t48/np4/f16/MTP is the winner**; `-t 96`,
IQK-FA, q8 KV, unified KV and no-MTP are all equal or worse.

CPU 55k confirmation (54,329 prompt): t48/np4/MTP **14.29**; t48/np4/no-MTP
15.07; t48/np1/MTP 14.88; **t96/np4/MTP 16.05** (best); t96/np1/MTP 14.52;
t96/np4/no-MTP **12.86**; t96/np1/no-MTP 12.75. The thread/MTP interaction is
real: t96 needs MTP (16.05 vs 12.86 without), while t48 slightly prefers no-MTP
(15.07 vs 14.29) but is still below t96+MTP. The live 12.5 at 57k with 38% NUMA
skew is the t48/MTP regime; clean placement + t96 accounts for the difference.

The 28k screen used a **wikitext prose** prompt, whose MTP acceptance is only
0.37-0.48. A matched OpenCode-like **code prompt** resolved the apparent
regression:

| code prompt | prompt_n | arm | tok/s | MTP acceptance |
|---|---:|---|---:|---:|
| orchestrator code 8k | 7,167 | t48 + MTP | **29.35 / 30.26** | 0.860 |
| orchestrator code 16k | 14,089 | t48 + MTP | **29.37 / 29.86** | 0.947 |
| orchestrator code 28k | 24,850 | t48/t96 | invalid | EOS at first token (`predicted_n=1`, 1e6 sentinel) |

The 8k/16k code results reproduce the user's live **20-30 tok/s** band. The
28k code arms are invalid because the concatenated code slice ended at a
boundary that made the model emit EOS immediately; they are not a performance
result. The prose 16.07 at 28k is a worst-case prompt, not a kernel regression.

**Sampling (official Qwen3.8 cards).** Both models: thinking
`temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=0.0`;
non-thinking `0.7, 0.80, 20, 0.0, 1.5`; repetition_penalty 1.0. Same
temperature is expected because both are Qwen3.8 hybrid thinking models; the
mode is the discriminator. The server `/props` default was 1.0/0.95/20 with
`min_p=0.05`; set `min_p=0.0` explicitly. The benchmark recipes' `temp=0,
top_k=1` are throughput controls, not production sampling.

**Manual launcher.** `scripts/session/launch_local_inference.sh` defaults to
CPU t96 + MTP + np4/262144 + f16 + no-kv-unified, and GPU np4/262144 + t8 +
f16 + DFlash2 n8 + no-kv-unified + cache flags. It supports `cpu`, `gpu`,
`both`, `stop`, `status`, `logs`, `--clean` and env overrides (`CPU_THREADS=48`
for short context, `GPU_NP=1 GPU_CTX=196608` for one long GPU stream).

GPU 54,329 prompt, greedy (primary 256 decode): np1/64k f16 n8 **42.76**;
np1/196k **43.05**; np4/262k **43.56**; np2/262k **43.77**; f16 n7 **43.50**;
node-1 host CPUs **43.16**; q8/n7 production **41.85**; q8/n7 no-kv **40.14**.
Short 16k reference **71.06** at 1,853 prompt / 384 decode, acceptance 0.64.
The np shape is **not** a speed lever at one active request; q8 KV is slower;
the live 29-31 at 50k is the agentic temp-1.0 acceptance band (25-30 at
57-152k), not a launch defect.
