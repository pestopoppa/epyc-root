# CPU speech vs CPU LLM roles, and the GPU constraints behind it (2026-09-24)

Reference for anyone planning STT/TTS layout, voice turns, or :8083 capacity. It collects what was measured
on 2026-09-24 so the next plan starts from numbers, not from memory. **Decision 2026-09-24: the operator chose
option D (no change to the layout)** because a larger STT/TTS integration plan is being drafted; options A-C below
are input to that plan, not pending work. The decision history is in [`handoffs/active/kv-unified-stack-rollout.md`](../../../handoffs/active/kv-unified-stack-rollout.md)
(RTG-57, KVU-11 and KVU-11b).

**Primary sources.** Each number below comes from one of these. Where they disagree with this page, the
sources win.
- Speech study: `/mnt/raid0/llm/epyc-inference-research/artifacts/speech_cpu_realtime_20260924/README.md`
  - research `21cf444c`: CPU solo and concurrent runs, snapshot at 17:14Z;
  - research `07060eaa`: option C, SMT siblings;
  - research `6afc7eed`: addendum 3, the live production layout under CPU LLM load. The harness is
    `live_llm_contention.py`.
- GPU study: `/mnt/raid0/llm/epyc-inference-research/artifacts/np_context_kvu_study_20260924/README.md`
  - research `21cf444c`: the 27B split vs unified matrix, the pool-full repro and MTP depth;
  - research `07060eaa`: the 35B-A3B matrix, the load-only table, M-3 and M-4.
- Signed package, revision 3:
  [`artifacts/operator/stack-change-kvu-20260924/revision-3/PACKAGE.md`](../../../artifacts/operator/stack-change-kvu-20260924/revision-3/PACKAGE.md),
  applied as orchestrator `0a564a1f` and research `75ee1b8e`.

Every cell is n = 1 or 2 unless stated. Claim class: locally measured, not decision-grade under
`MEASUREMENT.md`.

## 1. Production layout (live since 2026-09-24 ~18:50Z)

| Service | Kernel | Placement |
|---|---|---|
| STT `:9000` | whisper.cpp `production-speech-v1` `b3073792` (ggml 0.18.0), `ggml-large-v3-turbo.bin` | CPU `-t 24 -ng`, `taskset -c 0-23`, `HIP_VISIBLE_DEVICES=-1` |
| TTS `:9002` | qwentts.cpp `production-speech-v1` `2c1b518` (ggml 0.17.0), Qwen3-TTS 0.6B Q8_0 talker + 12 Hz tokenizer | CPU `taskset -c 24-39`, `GGML_BACKEND=CPU`, `HIP_VISIBLE_DEVICES=-1`, `LD_PRELOAD=/mnt/raid0/llm/cache/shims/nprocs_shim.so`, `SHIM_NPROCS=32` → 16 threads |
| CPU LLM roles | v10 CPU kernel | `-t 96` on physical cores 0-95, OMP spread one per core, active wait; frontdoor `:8070` (+ halves `:8080`/`:8180`), architect_critic `:8074` |
| `:8083` architect_general | v10 GPU kernel, Qwen3.8-27B Q8_0 + MTP | MI210: `-np 4 -c 196608 --kv-unified --spec-draft-n-max 4 -ub 2048 --cache-ram 65536` |

Things to know about the speech layout:
- **qwentts has no thread flag.** `src/backend.h` uses `hardware_concurrency()/2`, which ignores affinity
  and gives 96 threads on this host. The shim in orchestrator `scripts/voice/` interposes on `get_nprocs()`,
  and the launcher refuses to start the service if the `LD_PRELOAD` file is missing. The durable fix is a
  thread flag in qwentts.cpp in the next speech kernel version (RTG-57 KVU-11c).
- **whisper collapses on some core layouts.** A 30 s encode hangs for more than 60–300 s at `20@0-19`,
  `28@0-27`, `24@0-31`, `32@0-31` and `32@24-55`. It is healthy at `16@0-15`, `16@0-23`, `24@0-23`,
  `32@0-39` and `32@0-47`.
  - Only measured layouts may be deployed: orchestrator `scripts/voice/speech_layouts.yaml` and
    `check_speech_layout.py`.
  - Inferred cause: per-graph thread spawn combined with spin barriers.
- Both speech services still open `/dev/kfd`, even with `HIP_VISIBLE_DEVICES=-1` set. That variable was read
  from `/proc/<pid>/environ` on 2026-09-24. They use 0 VRAM.

## 2. Speech alone and together, with the CPU quiet

| Measurement | Result |
|---|---|
| STT solo, 11 s clip / 86.5 s clip | RTF 0.197 / 0.167 at 24@0-23; 0.140 / 0.122 at 32@0-39 |
| STT, short utterance | whisper pads every input to 30 s, so a 3.5 s utterance costs about 2 s at 24 threads (1.92–2.03 s). The GPU did the 11 s clip in 0.21 s |
| TTS solo, pcm stream | first packet 75–113 ms for a sentence and 185–330 ms for a paragraph; RTF 0.55–0.61 at 16 threads or more (GPU RTF at freeze: 0.169). No gain above about 16 threads, because it is latency-bound |
| STT + TTS together (`main40`: 24@0-23 + 16@24-39) | neither slows down: STT RTF 0.199 / 0.243, TTS RTF 0.59–0.61 |
| Live production layout, quiet (addendum 3, n = 2) | STT RTF 0.20–0.39; TTS first packet 0.09–0.17 s for a sentence and 0.22–0.23 s for a paragraph; TTS RTF 0.55–0.63 |
| Idle residency | costs the frontdoor nothing: 41–46 tok/s with both speech servers resident but idle |

## 3. SMT siblings (option C): not real time

- STT ran 16@96-111 and TTS ran 16@120-135, which are the siblings of cores 0-15 and 24-39.
- **With the frontdoor generating:**
  - STT RTF 1.20 (11 s clip) and 3.90 (86.5 s clip);
  - TTS RTF 18.8–21.6, i.e. 20–37× slower than real time;
  - the frontdoor fell to a median of 16.9 tok/s (n = 51).
- **Frontdoor idle:** siblings are still slower than physical cores (STT RTF 0.36–0.45, TTS RTF 0.79–0.90).
  That leaves TTS only about 1.1–1.3× headroom.

## 4. The production layout under a generating CPU LLM: both sides collapse

Addendum 3 ran 19:19–19:43Z against the live services. The LLM had one 1000-token `ignore_eos` generation in
flight, and every speech request overlapped it.

| Condition | STT | TTS | LLM decode |
|---|---|---|---|
| `:8074` architect_critic generating (`-t 96` on 0-95) | **RTF ≥ 58**: one 11 s clip took about 10.7 min and finished only when the generation was aborted | **first packet 13.6 s**, then 0.56 s of audio in 164 s | **0.59 tok/s** (solo 31.1–31.3) |
| `:8070` frontdoor generating (`-t 96` on 0-95) | not reached | **first packet 13.4 s**, then 0.41 s of audio in 96 s | **1.05 tok/s** (solo 36.8) |
| TEST Flash-Next `-t 56` on 40-95 (partitioned) generating | RTF 0.22–0.44 (quiet level) | first packet 0.24–1.0 s, RTF 0.93–1.40: marginal | 20.0–22.8 tok/s during speech; solo 23.0 / 24.5 = **−22..26%** vs `-t 96` |

**Why both sides collapse.** The CPU LLM roles run OMP active-wait threads, one per core, across all of 0-95.
Speech threads on 0-39 therefore sit inside the LLMs' core masks:
- a time-sliced LLM thread stalls every LLM barrier;
- a time-sliced speech thread stalls every speech barrier.

So a speech request damages the LLM as badly as the LLM damages speech. With disjoint cores (the partition
test), what remains is inferred to be DRAM bandwidth contention: MoE decode saturates memory, and TTS's
per-frame autoregressive loop is sensitive to latency. That was not isolated.

**No priority-pause mechanism exists.** Nothing in the launch flags or the orchestrator pauses LLM decode for
a speech request (inferred from the launch flags, not verified in code). A pause also could not take effect
mid-token, so a speech request would still wait for the current token.

Not measured: the frontdoor under the same partition. It is inferred to behave like Flash-Next, since both are
bandwidth-bound MoE decode.

## 5. Design options (input to future planning; tradeoffs as measured)

| Option | What it is | Gains | Costs / risks |
|---|---|---|---|
| A | Partition the CPU LLM roles to 40-95 (e.g. `-t 56`) **and** move TTS back to the GPU | STT back at quiet levels; TTS back at GPU speed (RTF 0.169 at freeze) | LLM decode −22..26% (measured on Flash-Next only); TTS needs about 0.92 GB of weights plus its KV on the GPU. Re-check headroom first (§6: projected free is 1.88 GiB with speech off the GPU) |
| B | Partition only; speech stays on CPU 0-39 | STT fine | TTS marginal (RTF 0.93–1.40, first packet up to 1.0 s, needs a playback buffer); same LLM loss as A |
| C | Keep the layout; add a decode throttle that pauses LLM decode while TTS streams | no permanent LLM loss | needs new code; cannot act mid-token; STT still collides unless it is throttled too |
| D | No change | none | any speech request during a `-t 96` generation wrecks both the speech and the LLM (§4) |

VRAM arithmetic for moving services: **STT on the GPU costs about 2.2 GB** (2.23 GB per `rocm-smi`, 2.06 GiB in the
registry record). Moving it off the GPU is what freed room for `:8083 -np 4`. **TTS on the GPU costs about
0.92 GB of weights** (1–2 GB with KV, inferred).

Layout hygiene seen during the runs: `megasync` (unpinned) ran at 60–100% on core 16, inside whisper's 0-23
mask. It is a possible source of stragglers (quiet STT RTF spread 0.22–0.39).

## 6. GPU-side facts voice work depends on (MI210, 65,520 MiB)

- **Voice turns route their reasoning step to `architect_general` (`:8083`, the 27B on the GPU),** not the CPU
  frontdoor. This applies to voice turns only; it is an operator requirement recorded in RTG-57 KVU-11. A CPU
  frontdoor generation is exactly what collapses CPU speech (§4).
- **`:8083` shape:** `-np 4 -c 196608 --kv-unified`, MTP draft depth 4, F16 draft KV. O-2 (q8_0 draft KV) was
  dropped because it adds a 768 MiB FA conversion buffer. Each request can use up to 196,608 tokens of the
  shared pool (split KV used to cap it at 98,304).
- **The unified KQ mask costs about 0.75 GiB (~768 MiB) more than split** at `-c 196608`. That is a package
  buffer-model figure, not a separate measurement. Total attention-KV bytes are the same in both modes; only the
  partition changes.
- **Load-only VRAM (27B, server MiB above a 2,139 MiB base, n = 1 each):**

  | Shape | server MiB |
  |---|---:|
  | old: `-np 2 -c 196608`, split, depth 8 | 39,018 |
  | `-np 2 -c 196608`, unified, depth 4, O-2 | 39,026 |
  | `-np 4 -c 196608`, unified, depth 4, O-2 | 40,522 |
  | `-np 2 -c 262144`, unified, depth 4, O-2 | 42,362 |
  | `-np 4 -c 262144`, unified, depth 4, O-2 | 43,858 |

  Each extra pair of slots adds about 1.5 GiB, which is per-slot recurrent (GDN) state. Going from 196k to 262k
  context adds about 3.3 GiB.
- **np 4 at 196k fits only with whisper off the GPU.** The capacity budget:
  - live shape (F16 draft) ≈ 40,114 MiB, plus 567 MiB first-execution growth;
  - VL-30B on `:8086`: 22,869 MiB;
  - driver: about 45 MiB.

  That leaves about **1,925 MiB (1.88 GiB) free with speech at 0 VRAM**. Adding whisper's ~2.2 GB back does not
  fit, and TTS alone (0.92 GB of weights before its KV) would leave under 1 GiB.
- **MTP + a full unified pool crashes one request.** With the pool exhausted (`-np 2 -c 4096 --kv-unified`, two
  2048-token generations), v10 `ffc1bac82` fails exactly one request, in 4 of 4 runs, with
  `speculative batch index 8 is not inside the current sub-batch [0, 8)`. It should return the clean
  context-exceeded error. Split KV never errors and truncates silently instead.
  - This is a v11 kernel candidate (RTG-57 KVU-7, guarded).
  - The orchestrator classifies the error as `pool_exhausted` (orchestrator `8a0c0944`).
- **Throughput: unified KV costs nothing measurable.**
  - 35B-A3B, fixed-length cells: unified is within 2% of split.
  - 27B, cells where every request ran to the cap: unified aggregate +5.1% at np 4.
  - Live np 4 at fixed length (M-4): 95.3 / 93.1 tok/s aggregate at concurrency 4.
- **MTP depth 4 on production traffic is not confirmed** (M-3, log-only). A projection from the depth-8 log puts
  it at 0.93× for the median request. Resolving it needs about 175 organic depth-4 requests (RTG-57 KVU-1b /
  M-3b).
- Unified and split produce different completions at the same seed at np ≥ 2 (and at np 1 on the 35B). Compare
  per-request decode across KV modes, not aggregates of different answers.
