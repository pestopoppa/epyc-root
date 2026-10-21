# CS-11 PREDECLARED (written before any measurement; amendments only by a new file + new APPROVED)

Task: `handoffs/active/conversation-stack.md` CS-11 — measure the CPU-placement alternative: the frontdoor (:8070 recipe)
and the :8074 recipe under the KVU-11b partition `-t 56` @ cores 40-95, then compute the CPU-LLM loss against the GPU
co-residency cost from CS-9. Method and reference numbers: `handoffs/active/kv-unified-stack-rollout.md` KVU-11b and
research `artifacts/speech_cpu_realtime_20260924/` (harness `live_llm_contention.py`, `raw/llm_solo_baselines.txt`).

## What is measured (and what is not)

CPU LLM **decode throughput under the partition vs the full-host recipe**, nothing else. Speech is NOT run here:
KVU-11b already measured speech beside a partitioned Flash-Next (STT RTF 0.22-0.44 OK; TTS first packet 0.24-1.0 s, RTF
0.93-1.40 = marginal, i.e. it MISSES the CS-12 acceptance TTS first packet < 1 s on the worst cell). CS-11 adds the
missing half: the LLM loss, for BOTH roles (KVU-11b measured only Flash-Next; the frontdoor was "inferred similar").

## Roles and recipes (resolved from code, frozen in `dry/recipes.json`, sha256 in APPROVED)

Resolved by `resolve_recipes.py` through the orchestrator's own `build_server_command` / `_numa_prefix` / `build_launch_env`
(registry + compiled stack priors, orch HEAD recorded in the json). Nothing hand-typed.

| role (recipe) | model | shape |
|---|---|---|
| `frontdoor` (:8070) | Qwen3.6-35B-A3B-MTP-Q8_0.gguf | `-np 4 -c 262144 -ub 2048 -ctk/-ctv q8_0 --mlock --no-mmap --cache-ram 32768`, terse chat template, `--spec-type draft-mtp --spec-draft-n-max 4`, `--reasoning off` |
| `architect_general` (:8074) | Qwen3.8-Flash-Next UD-IQ4_XS + `-md` MTP head | `-np 1 -c 262144 -ub 2048 -ctk/-ctv f16 --mlock --no-mmap --cache-ram 32768`, `--spec-type draft-mtp --spec-draft-n-max 4 --draft-p-min 0.5`, `--reasoning off` |

Env exactly as codified: `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false KMP_BLOCKTIME=10
GGML_IQK=1 LD_LIBRARY_PATH=/usr/lib/llvm-20/lib`; prefix `numactl --interleave=all -- taskset -c <cpus>`; the codified
`numa_pre_evict_gib: 40` forced eviction runs before every launch. Binary: `/mnt/raid0/llm/kernels/production/cpu/llama-server`
(v10 store, read-only; version 10303 / ffc1bac82; it is the same build dir the recipe resolves to). The ONLY differences
between arms are `-t` and the taskset cpu list (asserted by the harness; any other difference aborts). Ports 18070/18074
(non-production); slot-save dir is private; `--cache-ram` kept (allocates on demand only). `ulimit -c 0` everywhere.

## Arms

- **F** (full-host baseline, the recipe as codified): `-t 96`, `taskset -c 0-95`.
- **P** (partition, the KVU-11b layout): `-t 56`, `taskset -c 40-95` (= exactly the 56 physical cores of nodes 1(part)-3).

Per role, one fresh server launch per arm, sequence **F P F P F P F** (4 F, 3 P; every P is bracketed by two F = alternating
ABA pairs; the two roles run back to back, frontdoor first). 14 launches, est. ~49 min, plus claim wait. Per arm: warm 1 x 128
tokens (discarded), then **K = 4** measured requests, identical every time: the KVU-11b prompt (numerical-weather-prediction
essay), `max_tokens 500`, `ignore_eos`, `temperature 0.7`, `seed 42`, `cache_prompt false`, non-streaming; tok/s =
server `timings.predicted_per_second`. A request counts only if HTTP 200 and `predicted_n == 500`.
Attested per arm: our PID owns the port (health only counts then), `/proc/<pid>/status` Cpus_allowed_list equals the arm's list,
every mapped ggml/llama lib resolves inside the production store dir, cmdline carries our port. Pre-arm host busy% sampled
(flag if > 3 % of 192 CPUs); numa_maps placement recorded; draft acceptance recorded per arm as a covariate.

## Metric and direction

Primary: **decode tok/s, higher = better.** Arm value = mean of its K good requests. For each P arm i with bracketing F arms:
`loss_i = 1 - P_i / mean(F_{i-1}, F_{i+1})` (positive = partition is slower). Role loss = median of its 3 `loss_i`.

**Noise floor (with its unit): NF = (max F - min F) / mean F over the 4 F arms of the role, in percent of the arm-mean tok/s**
(F arms are repeated launches of the identical config, so this covers launch-to-launch and host drift over the ~25 min of a role).
Within-arm CV is reported alongside. KVU-11b's own repeat spread was 0.6 % (31.1 vs 31.3, n = 2).

## Decisive for the LLM-loss measurement

A role's loss is **resolved** iff it has >= 3 valid pairs, every `loss_i > NF`, and the median loss >= 2 x NF. Otherwise it is
reported as "inside the noise floor" and is NOT used to decide. The CS-11 measurement as a whole is **decisive** iff both roles
are resolved. Prediction made now (so a surprise is visible): both losses 18-30 %, consistent with KVU-11b's 22-26 % on Flash-Next;
reproduction check (reported, not gating): F within +-5 % of KVU-11b (31.2 tok/s :8074, 36.8 tok/s :8070), P of :8074 within the
KVU-11b 23.0-24.5 band +-10 %. Pairs/arms with errors, `n_good < 3`, or a deadline skip are dropped and listed, never imputed;
`pre_busy_flag` arms are kept but listed (sensitivity: analysis is also reported without them if any are flagged).

## Decision rule: CPU-LLM loss vs CS-9 co-residency cost

- `C_cpu` = mean of the two role median losses (both CPU roles must be partitioned together, because both collide with speech under
  `-t 96`; the max is reported too). Fraction of decode tok/s lost.
- `G` = CS-9 p95 loss fraction of LLM tok/s per slot on the GPU tenant while the cascade (whisper + qwentts) decodes beside it, at the
  deployed np (35B-A3B, the np4 shape); `speech_ok` = CS-9 shows STT RTF < 0.5 and TTS first packet < 1 s in that configuration.
- `m` = max of the two roles' NF (a fraction).
- If `speech_ok = no`: the GPU option is infeasible as measured; no cost comparison; operator decision with both numbers.
- **R1 (GPU wins):** `G + m <= C_cpu` -> GPU co-residency is cheaper; no speech component ever needs CPU placement; CS-12 proceeds.
- **R2 (CPU wins):** `C_cpu + m <= G` AND both roles resolved -> the CPU partition is cheaper on LLM cost. This is NOT sufficient to place
  speech on CPU: KVU-11b's TTS cell (first packet up to 1.0 s, RTF up to 1.40) fails the acceptance, so R2 only triggers a speech co-load
  re-measure under the partition and an operator decision package.
- **R3 (tie):** anything else -> within margin; default GPU (operator lean, and TTS on CPU is unproven); report both numbers.
CS-9 does not exist yet: this run produces `C_cpu`, `m` and the resolved flags; `analyze.py --cs9-loss G --cs9-speech-ok yes|no` applies the
rule when CS-9 lands. The rule above is fixed now and may not be tuned after seeing either side.

## Run mechanics and safety

Claim: `region-lock run --cpu-list 0-95 --role bench --gpu-quiet exclusive` (FIFO on). Production stack stays DOWN and is never started;
own PIDs only (captured Popen pids), SIGTERM -> SIGKILL, death verified; no name-pattern kills; no core dumps. Arms stop starting with
< 6 min to the harness deadline (12:10Z); launcher hard stop 12:15Z; a start after 11:10Z is refused (cannot fit). Launcher waits for C2
item e's end flag (`/mnt/raid0/llm/tmp/c2-regate-20261021/flags/e.{DONE,FAILED,SKIPPED}`) and not before 2026-10-22T10:45:00Z, refuses
without a matching `APPROVED`, and always writes `flags/CS11_DONE` (rc inside) via trap. Outputs: `raw/arms.jsonl`, `raw/server_*.log`,
`results.json`, `RESULTS.md`.

## Belief-kernel wiring (CS-3 / VB-SPEECH-CONV-1)

The run emits `protocol_id=cs11-cpu-partition-v1`, reps (K, N pairs), attestation, and `metric_direction=higher_is_better` in `raw/arms.jsonl`
rows (attestation fields) and results.json; the source-table row for the adapter README is owed by the owning session (see report).
