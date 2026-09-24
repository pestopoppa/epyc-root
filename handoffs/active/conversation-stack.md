# Conversation stack: speech-native interlocutor, orchestrator voice-turn contract, cascade fallback

**Status**: ACTIVE. The vision was ratified by the operator on 2026-09-24 (below). Phase 0 is open and no build work has started. The operator does not need the build-out finished soon. This handoff records the end-state intent and the ordered route to it, so later work never has to re-derive the design.
**Created**: 2026-09-24 (operator vision-alignment session: an audit of the operator's draft, then decisions D1–D8 plus follow-ups)
**Priority**: MEDIUM overall. The one near-term item is Phase 2 (the cascade moves onto the second MI210). It clears the measured CPU speech collapse without partitioning the CPU LLMs.
**Categories**: speech, multimodal, inference_serving, orchestration, gpu, kernel_port
**Parent index**: [inference-research-index.md](inference-research-index.md) (row INF-79)
**Depends on**: none by row. The physical installation of the second MI210 is an external event, expected within about a month of 2026-09-24.
**Related**:
- [`multimodal-pipeline.md`](multimodal-pipeline.md) (INF-41). Vision stays there. Speech moved here on 2026-09-24.
- [`kv-unified-stack-rollout.md`](kv-unified-stack-rollout.md) (RTG-57), KVU-11 / KVU-11b / KVU-11c.
- [`gpu-serving-tie-in-program.md`](gpu-serving-tie-in-program.md) (INF-22), P2-5j (host-thread placement) and P2-9 (stale "whisper as a GPU tenant").
- [`heterogeneous-slot-fabric-residency.md`](heterogeneous-slot-fabric-residency.md) (the GPU host-thread slot gap).
- [`fable5-window2-findings-02-heterogeneous-gpu.md`](fable5-window2-findings-02-heterogeneous-gpu.md) (35B-A3B solo on an MI210; no PCIe H2D measurement).
- [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md), VB-SPEECH-CONV-1.

**Source documents**:
- The operator's draft, preserved verbatim with a correction banner: [`docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md`](../../docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md).
- The CPU contention study: [`docs/reference/speech/cpu-speech-contention-20260924.md`](../../docs/reference/speech/cpu-speech-contention-20260924.md).
- The speech measurement annex: [`measurement/protocols/speech.md`](../../measurement/protocols/speech.md) (Annex S).
- Prior art:
  - [`research/deep-dives/kame-tandem-s2s-architecture.md`](../../research/deep-dives/kame-tandem-s2s-architecture.md) (intake-511#record)
  - [`research/deep-dives/qwen35-omni-tts-unblock.md`](../../research/deep-dives/qwen35-omni-tts-unblock.md) (intake-432#record)

---

## Vision (ratified 2026-09-24)

> **A permanently resident speech-native interlocutor hears, interprets and speaks. It has one external tool, the
> orchestrator, which supplies the cognition. Preserve speech-native state locally; export only the cognitive problem.**

```
                 ┌──────────────────────── SPEECH PLANE ─────────────────────────┐
 audio in ──────▶│ VOICE CONTROLLER (model-agnostic; lives in epyc-orchestrator) │
                 │  VAD · turn detection · barge-in · session · routing policy   │
                 │  context budget · degraded mode · event log                   │
                 │        │ Interlocutor backend interface (pluggable)           │
                 │        ├─ candidate: Step-Audio 2 mini   (bake-off lead)      │
                 │        ├─ candidate: Qwen3-Omni-30B-A3B  (bake-off challenger)│
                 │        └─ cascade: whisper :9000 → (text) → qwentts :9002     │
 audio out ◀─────│           (baseline + permanent fallback)                     │
                 └───────────────┬───────────────────────────────────────────────┘
                                 │ ONE tool: the voice-turn contract (streaming)
                 ┌───────────────▼──────── COGNITION PLANE ───────────────────────┐
                 │ ORCHESTRATOR: reasoning · retrieval · web · code · memory ·    │
                 │ tools · model routing. Replaceable without touching speech.    │
                 └────────────────────────────────────────────────────────────────┘
```

The interlocutor and the orchestrator split the work like this.
- **The interlocutor** hears, reads the paralinguistic signal, handles timing and turn-taking, gives social and backchannel responses, and decides the delivery.
- **The orchestrator** remembers, reasons, retrieves, calculates, writes code, searches and acts.
- **The orchestrator never takes over the conversation.** It returns the substance, and the speech plane decides how that substance is spoken.

## Ratified decisions

| # | Decision (operator, 2026-09-24) |
|---|---|
| D1 | **The interlocutor is chosen by a bake-off.** Step-Audio 2 mini is the lead and Qwen3-Omni-30B-A3B the challenger. Today's whisper+qwentts cascade is the baseline. The controller is model-agnostic, so the winner is a backend, not an architecture. |
| D1a | Quantizing the Qwen3-Omni Thinker to about Q4 is acceptable. The intelligence ceiling comes from the orchestrator, not the interlocutor. |
| D2 | **Languages.** English is mandatory. Italian is strongly wanted, and en+it is acceptable. German and French are desirable. Language is the **first** bake-off gate. |
| D3 | **Placement is decided by measurement.** PyTorch serves as a *measurement-only* reference. The operator leans towards the GPU. The decisive numbers are (a) CPU-LLM throughput after a core partition and (b) whether one MI210 can serve LLM and speech requests concurrently without either side missing its target. |
| D4 | **The production runtime is our own llama.cpp-family port**, built on an experimental tree and promoted as a new kernel version. vLLM and PyTorch are measurement instruments only, per the standing rule in `wiki/inference-serving.md` ("vLLM is a measurement instrument, not a second deployment engine"). |
| D5 | **Routing.** The controller sends every *substantive* turn to the orchestrator. Local answers are limited to social, backchannel and interaction-control turns. The operator will reassess model-decided routing once routing accuracy has been measured. |
| D6 | **A dedicated voice-turn contract** in the orchestrator: real token streaming, a session-keyed conversation store, a spoken-form answer plus an optional display payload with preserve/verbatim fields, and a voice routing policy. It should be whatever is simplest to implement that meets this. |
| D7 | **The client and transport are deferred.** Recorded end-state constraint: the operator will eventually talk to the machine *remotely*, from a travel laptop or a phone. Nothing may assume the microphone is on the host. |
| D8 | **The cascade is kept** as the baseline and as the permanent fallback / degraded mode. |
| D9 | **Second MI210.** It arrives within about a month. The operator's plan is Qwen3.6-35B-A3B on it, possibly co-hosting the speech plane. It may serve as the **bench** before 35B-A3B is commissioned. |
| D10 | **A custom or cloned persona voice is nice to have, not mandatory.** It is a tie-break criterion in the bake-off. Any cloning obeys the default-deny guardrail carried below. |
| D11 | **Latency hiding is a ladder, cheapest rung first:** native preamble, then streamed answer, then untrained mid-generation injection. KAME-style training of the front-end is a **gated research track**. |
| D12 | **This handoff is the one home for speech.** It is the conversation-stack handoff that KVU-11 anticipated, and it absorbs the open speech items from `multimodal-pipeline.md`. |

## Facts that constrain the design (verified 2026-09-24)

**Host**
- **One MI210 today** (gfx90a, ROCm 6.2.0-66, NUMA node 1, PCIe Gen4 x16).
  - It holds :8083 Qwen3.8-27B np4/kvu (42.9 GB) and :8086 Qwen3-VL-30B-A3B (24.0 GB), with **0.9–1.9 GiB free** (contention doc §6; `wiki/inference-serving.md:138`).
  - Host threads use `GPU_HOST_LANE` 184-191, which is cross-node from the GPU (`heterogeneous-slot-fabric-residency.md:132`).
  - Nothing measured exists for PCIe H2D/D2H bandwidth.
- **The second MI210 (D9).** The planned occupant is Qwen3.6-35B-A3B-MTP Q8_0. Measured VRAM:

  | np | VRAM (GB) | tok/s |
  |---|---|---|
  | 1 | 36.6 | 112.68 |
  | 4 | 37.5 | 189.57 aggregate |
  | 16 | 41.4 | 310.96 aggregate, still climbing |

  Estimated VRAM for the other co-tenants (verify in CS-9):

  | Co-tenant | VRAM |
  |---|---|
  | Cascade (whisper.cpp large-v3-turbo about 2.2–2.6 GB, plus qwentts about 1.2 GB) | ≈ 4 GB |
  | Step-Audio 2 mini: Q8 decoder, BF16 encoder, Token2Wav, 16k KV | ≈ 11–12 GB |
  | Step-Audio 2 mini at BF16 | ≈ 19–20 GB |
  | Qwen3-Omni with a Q4 Thinker, plus Talker, Code2Wav and AuT | ≈ 23 GB |
  | Qwen3-Omni with a Q8 Thinker | ≈ 36+ GB, which does **not** fit beside a Q8 35B-A3B |

- **CPU decode bandwidth.** Decode-usable bandwidth is about **150–220 GB/s**, not the 460.8 GB/s theoretical figure (`wiki/hardware-optimization.md:75-78,119,223`).
  - CPU speech **collapses on both sides** while a `-t 96` CPU LLM generates: STT RTF ≥ 58, TTS first packet 13.4–13.6 s, and the LLM falls to 0.59–1.05 tok/s (contention doc §4).
  - Partitioning the LLMs to `-t 56` on cores 40-95 restores STT, leaves TTS marginal, and costs the LLM 22–26%. **The frontdoor under that partition was never measured.**
- **No free physical core.** Even correctly pinned GPU host threads degraded the CPU A/A floor from 0.80% to 7.22%.

**Orchestrator (epyc-orchestrator @ fd4f49cc)**
- **No voice path exists.** STT and TTS are launched and health-checked (`scripts/server/orchestrator_stack.py:2678-2813`; `orchestration/launch_manifest.yaml:757-865`) but never called. There is no VAD, turn detection, barge-in, websocket or client.
- **`/v1/chat/completions` streaming is fake.** The answer is fully generated, then replayed character by character (`src/api/routes/openai_compat.py:1211-1232`). Real llama-server chunks already exist in `src/llm_primitives/inference.py` `_call_caching_backend` (`on_chunk` closures at :1221/:1253/:1292), but they feed only the tap, the repetition guard and cancellation. `primitives.llm_call` (`src/llm_primitives/primitives.py:663`) returns `str`.
- **No conversation store.** `x_session_id` is "RECORDED ONLY" (`src/api/models/openai.py:192-202`). The session sqlite store has no messages table (`src/session/sqlite_store.py:123-257`). The trace store (`src/trace/navigation.py:117` `get_conversation`) is the closest thing.
- **The MCP `orchestrator_chat` tool wraps `/chat`** (prompt plus a context string), not `/v1` (`src/mcp_server.py:451-500`).
- **Voice routing to :8083 is unimplemented.** "Voice turns reason on architect_general (:8083)" (KVU-11) is written in docs only; no routing code implements it.

**Speech kernels today**
- **whisper.cpp** is `production-speech-v1` `b3073792` (ggml 0.18.0).
  - It serves `POST /v1/audio/transcriptions`: one shot, WAV only, no streaming. It pads to 30 s, so a 3.5 s utterance costs about 2 s on CPU and about 0.12 s on GPU.
  - Built-in Silero VAD flags exist but are unused.
  - Its WER is **3.37%** (n=100, CI [2.26, 4.67], Annex S Appendix S-A). This is **not** the 2.35% quoted in multimodal S-10, which was the faster-whisper CPU arm.
- **qwentts.cpp** is `2c1b518` (ggml 0.17.0).
  - It serves `POST /v1/audio/speech` and streams PCM (24 kHz s16 mono) by default.
  - Runtime voice registration exists; no voice is registered at start-up.
  - It supports 10 languages, including en/it/de/fr, **so the cascade already covers D2 in full**.
  - GPU figures at freeze: RTF 0.169, TTFA 37.8 ms, round-trip WER 1.49%.

**Candidates.** Primary sources were checked on 2026-09-24; URLs are in *Sources* below.

| | Step-Audio 2 mini | Qwen3-Omni-30B-A3B-Instruct |
|---|---|---|
| Shape | 8.315B total. The AR core is a Qwen2.5-7B derivative, ~7.66B dense, 16,384 context. The audio encoder is ~0.64B (Qwen2-Audio). Token2Wav is ~1.23 GB (CosyVoice2-style flow DiT 512×16 plus HiFT and CAM++). | The Thinker is 30B-A3B MoE (~3B active). The Talker is 3B-A0.3B MoE plus an MTP module. Code2Wav is ~200M. AuT is ~650M. |
| Output clock | **1 text token : 4 audio tokens** (TA4) at 25 Hz, so **about 31.25 AR steps per second of speech** (StepFun maintainer: "~32 Hz", issue #42) | The Talker runs at 12.5 Hz with MTP. The theoretical first packet is 234 ms. |
| Input tokens | 12.5 tokens per second of audio. The official pattern re-feeds past turns, so 16k fills in **about 9–12 minutes** of conversation. | Not yet measured here (CS-8). |
| Speech output languages | **No evidence for it/de/fr.** Published evaluations are zh/en only, and English is weaker than Chinese (URO-Bench Pro 61.25 vs 69.57). | **en, zh, fr, de, ru, it, es, pt, ja, ko** (model card) |
| Tool calling | Only in the StepFun vLLM fork's parser. A call comes **only after `<tts_end>`**, as `<tts_start>[optional spoken preamble]<tts_end><tool_call>…`, so a tool use takes two generations. **No published tool-call accuracy for mini**; the table covers the full Step-Audio 2 only. Issue #27 reports poor slot filling. | Tools and RAG act on the Thinker's text output. The Talker voices whatever text it is given, so orchestrator text could go to the Talker directly. |
| Paralinguistics | StepEval-Paralinguistic average 80.00. That is 50 samples per dimension, LLM-judged, so each dimension carries about ±7–14 pp of noise. | Strong on published audio benchmarks; not compared on StepEval. |
| Voice | Zero-shot from a prompt wav via CAM++ and flow conditioning (tie-break per D10) | 3 fixed voices, no cloning |
| Duplex | Half-duplex. No VAD is shipped. | Half-duplex |
| Runtime status | **None on our hardware.** No llama.cpp support. `token2wav.py` hard-codes `.cuda()` (the CPU PR #30 was closed unmerged). Issue #86 shows only a server *starting* on gfx1151 with ROCm 7.11: no generation, no audio. vLLM-Omni ROCm is validated on gfx942 only. | Our llama.cpp supports Thinker audio input (open bug #27136 on the ggml-org GGUF). There is **no Talker or Code2Wav** in llama.cpp. vLLM-Omni is NVIDIA-only. |
| Published serving numbers | vLLM-Omni on 4×3090: TTFP 1437 ms, RTF 0.949 (async chunk). StepFun estimate on an L40S: about 1 s to first audio. | Not collected |
| Known issues | #75 repetition loops (open), #58/#33 system-prompt fragility, #83 text-only output | |
| License | Apache-2.0 | Apache-2.0 |

**Corrections to the operator draft.** They are recorded so nobody re-imports them.
1. There is one MI210 today, not two. Topology B needs D9.
2. There are 31.25 decode steps per second of speech, not 25. The bandwidth math in draft §8/§10 is 25% optimistic.
3. The 460 GB/s-class figure is theoretical. On this host, Q8 on CPU at 31.25 steps/s needs about 250 GB/s, which is unrealistic. Q4 needs about 140 GB/s and is plausible only on a quiet CPU.
4. Issue #86 is not a working ROCm inference.
5. The tool-call strength is proven for the full model, not mini.
6. The context must be managed from Phase 1 onward, not Phase 4.
7. The "existing chat endpoint" lacks streaming and memory.
8. The STITCH paper (arXiv 2507.15375) is Microsoft/NTU work, not Kyutai's.

---

## Start here

1. Read **Vision**, **Ratified decisions** and **Facts**. Do not re-open D1–D12.
2. The next actions do not need the second GPU. They are Phase 0 (CS-1…CS-6), Phase 3 (the orchestrator contract, CS-13…) and Phase 4 (the controller and cascade backend, CS-20…). **Phases 3 and 4 can be built end to end on today's cascade** before any new model exists.
3. When the second MI210 is physically installed, Phase 1 (the bench window) starts **before** 35B-A3B is commissioned (D9).

## Tasks

### Phase 0: groundwork (now; no second GPU needed)

- [ ] **CS-1 — run research intake on the design's sources.** None are in `research/intake_index.yaml` yet (checked 2026-09-24):
  - Step-Audio 2: arXiv 2507.16632, `github.com/stepfun-ai/Step-Audio2`, HF `stepfun-ai/Step-Audio-2-mini`, the StepFun vLLM fork branch `step-audio2-mini`
  - Qwen3-Omni: arXiv 2509.17765, HF `Qwen/Qwen3-Omni-30B-A3B-Instruct`
  - Kyutai Unmute
  - SHANKS: arXiv 2510.06917
  - STITCH: arXiv 2507.15375
  - Kimi-Audio: arXiv 2504.18425
  - Moshi: arXiv 2410.00037
  - vLLM-Omni `examples/online_serving/step_audio2`

  Use the research-intake skill; the operator selects the deep dives. Until an entry exists, cite these by URL or arXiv id only, never by a placeholder intake number.
- [ ] **CS-2 — prepare the Annex S amendment package for operator ratification** (a human-only trust boundary; `MEASUREMENT.md:151-157`). Annex S admits only single-backend STT or TTS on `whisper_stt`/`qwentts_tts` (speech.md:7-19), so no interlocutor or end-to-end turn is measurable under it today. The package must:
  - add a protocol family for voice turns (proposed P-VOICE-*):
    - end-of-user-speech → first audio (median and p95), split into LOCAL and ORCH turns
    - sustained RTF
    - barge-in cancel latency
    - routing precision and recall
    - a paralinguistic accuracy set
    - semantic fidelity and exact-value retention after revoicing (judged; SC58 frame rules apply)
    - a language gate (round-trip WER through the frozen STT oracle, plus a human intelligibility check for it/de/fr)
    - co-residency slowdown of the co-tenant LLM
  - fix the stale MI210 premise at speech.md:69-71 (production speech is on CPU since OP-56) and define CPU placement proof and co-tenant state as part of the measurand;
  - issue a superseding receipt for the 2.35% → 3.37% whisper WER defect (speech.md:147-154);
  - fix the MEASUREMENT.md:71/:72 index inconsistencies.

  Proposed initial acceptance targets, for the operator to set in the amendment:

  | Metric | Target |
  |---|---|
  | LOCAL turn, end-of-speech → first audio | p95 ≤ 1.0 s |
  | ORCH turn, to first audio (bridge allowed) | p95 ≤ 1.5 s |
  | Sustained RTF | p95 ≤ 0.7 |
  | Barge-in cancel | ≤ 200 ms |
  | Exact-value retention on the preserve set | 100% |
  | Co-tenant LLM slowdown | ≤ 15% |
- [ ] **CS-3 — wire the belief-kernel write side before the first measured run.** The task is VB-SPEECH-CONV-1 in [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). The source row is in `scripts/vidya/adapters/README.md` → *Known and candidate sources*, filed 2026-09-24. Every CS-8/CS-9/CS-12 harness emits `protocol_id`, reps, attestation and `metric_direction` at write time.
- [ ] **CS-4 — build the voice evaluation corpus** under Annex S corpus rules: PCM-SHA-256 bound, in-repo and durable, selection and confirmation splits disjoint. It needs five sets.
  1. **Language:** en and it are mandatory; de and fr are optional.
  2. **Paralinguistic:** neutral, quiet, whisper, hesitation, sarcasm, laughter, frustration and noise, in en and it. **Real human recordings are required.** Synthetic TTS cannot test paralinguistic perception. The operator can record the Italian and English core set; public sets are used where their licence allows.
  3. **Routing:** labelled LOCAL vs ORCH turns (social, backchannel, control vs factual, reasoning, code, memory, current events).
  4. **Exact-value fidelity:** numbers, proper nouns, commands and URLs inside orchestrator answers.
  5. **Multi-turn referent and interruption scripts.**
- [ ] **CS-5 — build the PyTorch reference harness for both candidates**, measurement-only per D4, in `epyc-inference-research`, with pinned upstream commits.
  - It must run on ROCm gfx90a. That means patching Step's `token2wav.py` off its `.cuda()` hard-coding, and using the StepFun prompt format rather than the HF `tokenizer_config.json` chat template, which does not match training.
  - It emits CS-3 records.
  - It is prepared now and runs in the CS-8 bench window.
- [ ] **CS-6 — write the second-GPU bench-window run plan**: an ordered run list, per-run duration estimates, the exact measurands, and exit criteria, so the window before 35B-A3B is commissioned is used fully. Order: CS-7, then CS-8 G1 (language, cheapest and most decisive), then CS-9, then the rest of CS-8, then CS-10.

### Phase 1: second-GPU bench window (before 35B-A3B is commissioned)

- [ ] **CS-7 — verify the second MI210 on arrival and place its host lane.** BLOCKED until the second MI210 is physically installed (an external event, expected about 2026-10).
  - Confirm with `rocminfo` / `rocm-smi` (two gfx90a agents), the NUMA node of each card, the PCIe link, and **measured H2D/D2H bandwidth** (the gap from fable5 F3).
  - Choose a second GPU host-thread lane, feeding and consuming INF-22 P2-5j. Today's 184-191 lane is already cross-node for card 1. Record the CPU-floor impact.
- [ ] **CS-8 — run the interlocutor bake-off on the reference harness (CS-5), in gate order**, with the cascade measured on the same clips as the baseline. A candidate that fails a gate stops there. Gates:
  - **G1 language:** intelligible en and it speech output; de/fr recorded as a bonus.
  - **G2 paralinguistic perception** on the CS-4 set.
  - **G3 routing:** forced-policy compliance (D5) and tool-call slot quality, plus semantic fidelity and exact-value retention when revoicing orchestrator text.
  - **G4 serving:** TTFA, RTF, VRAM and repetition/corruption rate on the MI210 at BF16, plus a quantized proxy.

  Tie-break: voice identity (D10). Deliver a winner recommendation with the numbers to the operator through the master decision queue. If both candidates fail G1 or G3, the recommendation says so. Kimi-Audio (12.5 Hz, 19 GB detokenizer) is not in the bake-off; it re-enters only if both candidates fail.
- [ ] **CS-9 — measure GPU co-residency and CU partitioning on the second MI210.** This is the D3 decision input. Run 35B-A3B as a test tenant at np {1, 4, 16} decoding at the same time as (a) the cascade and (b) each candidate interlocutor. Record both sides at p95: LLM tok/s per slot, speech TTFA and RTF.
  - Then test soft partitioning: ROCm per-queue **CU masking** (`HSA_CU_MASK`, `hipExtStreamCreateWithCUMask`). First establish whether it works on gfx90a at all. If it does, measure whether a speech CU reservation protects speech latency, and what it costs the LLM. MI210 has no hard compute partitioning, unlike MI300.
  - Also record real VRAM per co-tenant, replacing the estimates in *Facts*.
- [ ] **CS-10 — probe latency hiding on the stock models (no training), on the reference harness.**
  - (a) Step: native spoken-preamble → `<tool_call>`. Measure how often the preamble is emitted and how natural it is, and the dispatch time relative to playback.
  - (b) Step: *untrained* mid-generation injection. Append orchestrator text as a segment at a TA4 group boundary and continue. Measure coherence, the rate at which the injected content is used, and exact-value retention.
  - (c) Qwen3-Omni: stream orchestrator text straight into the Talker, conditioned on the user-audio features. Measure prosody appropriateness against a plain Talker, and the first-audio time.

  This feeds the D11 ladder and the gate on CS-40.
- [ ] **CS-11 — measure the CPU-placement alternative, for D3 completeness.** Measure the frontdoor (:8070) and :8074 under the `-t 56`@40-95 partition, which KVU-11b never measured, then compute the CPU-LLM loss against the GPU co-residency cost from CS-9. With the second MI210 present, this decides whether any speech component ever needs CPU placement. It can run before the second GPU arrives, in a quiet CPU window.

### Phase 2: commission the second MI210 with 35B-A3B plus the cascade

- [ ] **CS-12 — prepare the stack-change package that puts the cascade (whisper + qwentts) on the second MI210 beside 35B-A3B.** It uses the `stack-change` skill and one operator signature, and is coordinated with whichever package commissions 35B-A3B there.
  - Carry the standing rule from multimodal S-11a: **re-cut the capacity-gate speech-VRAM fold (whisper 2.06 + tts 2.62 GiB) and key the reservation on the service's device before speech returns to any GPU.** The reference patch is `artifacts/operator/inf41-capacity-gate-aux-vram-20260924.patch`, on orch branch `noninf/inf41-speech`.
  - Give each service its own `HIP_VISIBLE_DEVICES` and prove ggml linkage plus the engine's device line (Annex S).
  - Acceptance, carried from KVU-11b: re-run the live-contention harness with a CPU LLM generating, and require **STT RTF < 0.5 and TTS first packet < 1 s**. Record the 35B-A3B slowdown from CS-9.
  - Landing this resolves the CPU speech collapse that led the operator to choose option D.
  - It retires the TTS `nprocs` shim concern for the GPU path; KVU-11c stays in RTG-57 for any CPU-fallback path.

### Phase 3: orchestrator voice-turn contract (independent of hardware; can start now)

- [ ] **CS-13 — write the voice-turn contract design note** at `docs/design/voice-turn-contract.md`. Keep it short and pick the most straightforward shape (D6).
  - **Recommended:** a dedicated thin route, `POST /v1/voice/turn`, returning **SSE events** (`answer.delta`, `display`, `preserve`, `done`, `error`) and reusing the direct-answer (`disable_repl`) path internally. The OpenAI-compatible `/v1/chat/completions` stays untouched.
  - Request fields: `session_id`, `user_request`, `conversation_context`, `response_goal` (spoken | display), `language`, `max_spoken_seconds`, `cancel_token`.
  - Also define cancellation semantics and the error and timeout budget.
- [ ] **CS-14 — make token streaming real end to end.**
  - Thread a chunk sink (a parameter or contextvar) through `primitives.llm_call` → `_real_call` (inference.py:419) → `_real_call_impl` (:559) → `_real_call_single` (:703) → `_call_caching_backend` (:844). Forward it from the existing `on_chunk` closures (:1221/:1253/:1292).
  - Bridge the sink into the async generator (via a queue) for the voice route and for `/v1` `disable_repl` and client_mode.
  - Drop the character replay (`openai_compat.py:1211-1232`) wherever real chunks exist.
  - The REPL branch cannot stream a FINAL answer; voice turns use the direct path.
  - Acceptance: time to first token at the client boundary is within 50 ms of the backend's first token.
- [ ] **CS-15 — add a session-keyed conversation store.** Add a messages/turns table to `src/session/sqlite_store.py`, keyed by `session_id` (fields: role, text, spoken_text, display, timestamps, turn_id), with a retention policy.
  - Honour `x_session_id` on the voice route, and on `/v1` behind a flag.
  - Add a **summary-refresh** call that returns a compact semantic state for the interlocutor's context trim (CS-25).
  - Check overlap with the trace store (`src/trace/navigation.py`) and with the HS-4 P1/P3 plans (UFH-01) before building, so there is one store, not two.
- [ ] **CS-16 — implement spoken form, display payload and preserve fields.**
  - Add a voice response profile: a system prompt that yields short, speakable answers within `max_spoken_seconds`, with no markdown.
  - Add an optional `display` payload for code, commands, URLs and tables. Exact artefacts are *shown*, not spoken.
  - Add `must_preserve[]` (numbers, proper nouns, caveats) and `response_mode: normal | verbatim`.
  - The speech plane must not alter `must_preserve` values. The CS-4 exact-value set tests this.
- [ ] **CS-17 — implement voice routing as configuration.** The default voice cognition target is architect_general (:8083), per the operator requirement in KVU-11.
  - After CS-12, measure 35B-A3B on the second MI210 (112.68 tok/s solo, measured) as the voice cognition target against :8083 (about 42 tok/s per slot at np4) on the CS-4 routing and fidelity sets.
  - The operator then chooses the default; this is a config change, not a code change.
- [ ] **CS-18 — implement cancellation.** A barge-in cancels the in-flight orchestrator generation through the existing cancel path (`_cancel_only`, inference.py:1297). Expose the controller's retain/cancel decision: "yeah, exactly" retains the result; "no, forget that" cancels it.
- [ ] **CS-19 — write the contract acceptance tests**:
  - a streaming first-token test;
  - exact-value retention through the contract;
  - session continuity across turns;
  - cancel latency;
  - no regression on `/v1` and `/chat` (existing suites);
  - MCP `orchestrator_chat` unaffected.

### Phase 4: voice controller and cascade backend (can start now)

- [ ] **CS-20 — build the voice-controller skeleton and the interlocutor backend interface** in `epyc-orchestrator` (proposed `src/voice/`).
  - Interface: `ingest(audio_chunk)`, `respond(turn) → stream of events {text_delta, audio_chunk, tool_call, end}`, `inject(text)`, `cancel()`, `health()`.
  - Test harness: WAV in → PCM/WAV out plus a JSONL event log, with no client (D7).
  - The transport abstraction must not assume the microphone is on the host, because the end state is remote laptop and phone access.
- [ ] **CS-21 — implement the cascade backend**: whisper :9000 → the voice-turn contract (Phase 3) → qwentts :9002, streaming PCM. This is the first end-to-end voice path, the permanent fallback (D8), and the bake-off baseline. It exercises the whole controller and contract before any new model exists.
- [ ] **CS-22 — add VAD and turn detection.**
  - Evaluate whisper.cpp's built-in Silero VAD flags against a standalone Silero VAD in the controller, plus an end-of-turn policy (silence threshold; semantic end-of-turn is optional).
  - Measure end-of-turn detection latency and the false-cut rate on the CS-4 hesitation clips.
  - The production Silero weights must be pinned; the only copy on disk is a test fixture.
- [ ] **CS-23 — implement the barge-in cancellation chain**: stop the queued audio, then the interlocutor generation and vocoder, then the orchestrator call (CS-18 policy). Measure the cancel latency in the harness with simulated overlap. Echo cancellation is a client concern and is deferred (D7).
- [ ] **CS-24 — implement the D5 routing policy in the controller and measure it.** Options:
  - (i) a prompt-level policy: call the tool for any non-social turn;
  - (ii) a short first-pass classification decode;
  - (iii) a parallel text classifier on a cascade transcript.

  Pick by precision and recall on the CS-4 routing set. Log every routing decision for CS-41.
- [ ] **CS-25 — implement interlocutor context management.**
  - A budget and trim policy for the 16k window (Step fills it in about 9–12 minutes).
  - Compare full audio history, text-only replacement of old turns (untested against training), and an orchestrator summary refresh (CS-15).
  - Measure multi-turn referent accuracy on the CS-4 scripts.
- [ ] **CS-26 — implement degraded mode and language fallback.**
  - If the interlocutor is unhealthy, the controller switches to the cascade.
  - Per-language routing: languages the bake-off winner cannot speak go to the cascade, which covers en/it/de/fr. This is how D2's de/fr stays satisfiable whichever model wins.
- [ ] **CS-27 — add a persona voice (nice-to-have, D10)** under the carried voice-cloning guardrail (default deny):
  - references only through an enrolled `voice_id`, with a recorded authorisation from the rightsholder;
  - refuse minors, public figures and "in the style of" requests;
  - synthetic-audio disclosure and an audit record;
  - per-voice revocation plus a global disable;
  - a signed operator decision before enabling.

  The guardrail is the full text at multimodal-pipeline.md:586. Applies to qwentts voice registration and Step prompt-wav conditioning.

### Phase 5: llama.cpp-family port of the bake-off winner (D4)

Kernel rules apply throughout: work on an experimental branch pulled fresh from production; production trees are never modified; promote a full candidate.
- [ ] **CS-28 — decide where the port lives and design it, after CS-8 names the winner.**
  - The AR decoder and audio encoder belong in the llama.cpp tree (mtmd).
  - The speech-output half (Step Token2Wav, or the Omni Talker plus Code2Wav) may fit the speech tree better. `qwentts.cpp` already carries a ggml codec runtime with gfx90a patches.
  - Record the split, the ggml-generation and `LD_LIBRARY_PATH` implications (three ggml generations today), and the promotion path: llama.cpp v11 and/or `production-speech-v2`.
- [ ] **CS-29 — port the decoder and conversion.**
  - Step: Qwen2 architecture with the extended 158,720 vocabulary; TA4 interleave handling; the `<tts_start>` / `<tts_end>` / `<tool_call>` grammar in the server.
  - Omni: the Thinker is already supported. Fix audio input on the ggml-org GGUF (upstream llama.cpp #27136).
- [ ] **CS-30 — port the audio encoder as an mtmd projector.**
  - Step: the Qwen2-Audio encoder plus the stride-2 adapter. Check reuse of the existing QWEN2A / whisper-enc projectors (`tools/mtmd/clip-impl.h:343-362`) first.
  - Omni: verify AuT parity.
- [ ] **CS-31 — port speech output to ggml with streaming.**
  - Step Token2Wav: UpsampleConformerEncoderV2, the flow DiT (512 wide, 16 deep, 10 ODE steps), HiFT, and CAM++ run once per enrolled voice. Stream in chunks of 25 tokens plus 3 lookahead, with a flow attention cache and HiFT crossfade.
  - Omni: the Talker (MoE plus MTP) and Code2Wav.
  - The one precedent is MiniCPM-o Token2Wav on CPU at RTF ≈ 2.4 (`progress/2026-07/2026-07-27.md:895`). It sets the bar the GPU path must beat by a wide margin.
- [ ] **CS-32 — prove numerics parity against the PyTorch reference (CS-5).**
  - The decoder: greedy token identity on the CS-4 subset.
  - The vocoder: mel/waveform distance plus round-trip WER through the frozen STT oracle (P-TTS-2 shape).
  - First prove the binary under test contains the port (a `strings` / mtime check, per the build-artifact rule).
- [ ] **CS-33 — run the quantization ladder on the AR core only**: BF16 → Q8 → Q6 → Q5 → Q4. The encoder, adapter and vocoder stay at higher precision initially.
  - Judge each step on the CS-4 paralinguistic, routing, fidelity and corruption/repetition sets plus RTF, **never on text perplexity**.
  - The Omni Thinker at about Q4 is pre-accepted by D1a, subject to G3.
- [ ] **CS-34 — build the server surface and promote.**
  - Server: audio-in plus a streamed event-out endpoint (text deltas, PCM chunks, tool calls), `inject`, `cancel`, health.
  - Bake in the agent-file overlay.
  - Promote through the `kernel-promotion` skill with one ratification package, and extend `verify_speech_kernels.sh` / `verify_llama_cpp.sh` accordingly.

### Phase 6: the interlocutor in service

- [ ] **CS-35 — prepare the stack-change package that makes the interlocutor resident** at the placement CS-9/CS-11 selected (the operator leans towards the second MI210). It includes:
  - a capacity-gate reservation keyed on device;
  - health probes;
  - an automatic fallback to the cascade (CS-26);
  - a registry row by model and quant;
  - attestation through the three stack gates.
- [ ] **CS-36 — run end-to-end acceptance against the CS-2 protocol**: interlocutor against the cascade baseline on the CS-4 confirmation split. Report LOCAL and ORCH turn latencies, RTF, barge-in, routing, fidelity, and the co-tenant LLM slowdown.

### Phase 7: latency-hiding ladder (D11)

- [ ] **CS-37 — use the native bridge in production.** Step: spoken preamble, then tool call. Omni: a Thinker bridge sentence while the orchestrator works. Measure perceived latency (end of speech → first *meaningful* audio), not only compute latency.
- [ ] **CS-38 — stream the orchestrator's answer into the speech path.** Omni: Talker fed directly from `answer.delta`. Step: chunked injection. This uses CS-14 streaming and CS-10 findings.
- [ ] **CS-39 — implement untrained mid-generation injection in our runtime.** KV-append the oracle text at TA4 group boundaries in the CS-34 server, taking over from CS-10(b) once the port exists. Measure how often content is used and exact-value retention.
- [ ] **CS-40 — test speculative orchestration (SHANKS-like).** Launch the orchestrator call from a *partial* user turn once intent is clear, then refine or cancel at end of turn. Measure the hit rate, the wasted cognition compute, and the perceived-latency gain. This needs streaming partial transcription from the interlocutor or cascade.

### Phase 8: gated research

- [ ] **CS-41 — reassess model-decided routing (D5 → model-decided LOCAL answers).** Proceed only after CS-24 shows routing precision and recall at or above the operator-set target on the confirmation split. The operator decides.
- [ ] **CS-42 — KAME-style oracle-stream fine-tune of the front-end.** Open this only after CS-39 shows untrained injection falls short on perceived latency or fidelity.
  - Feasibility, estimated 2026-09-24 and unmeasured:
    - LoRA on an 8B model fits one MI210 (BF16 weights 16.6 GB plus gradient checkpointing).
    - A full fine-tune (≈16 B/param ≈ 130 GB plus activations) needs two MI210s with ZeRO-3/FSDP, or CPU optimizer offload (1.1 TB RAM).
    - About 85M tokens per epoch (56k dialogues × ~1.5k tokens) ≈ 4e18 FLOPs. At 30–40% of the MI210's 181 BF16 TFLOPS that is **≈15–20 h per epoch per GPU**.
    - Generating hint targets at six levels per dialogue is about 340k short orchestrator calls, around 2 days.
  - **The binding risk is data realism, not compute.** Synthetic TTS training speech can erode the paralinguistic perception the interlocutor was chosen for, so every run needs a CS-4 paralinguistic regression guard and a mix of real expressive speech.
  - Format: Step is single-stream, so the oracle becomes injected segments at TA4 boundaries rather than KAME's fourth stream. It needs the CS-34 runtime.
  - Prior art: intake-511#record (KAME) and SHANKS (arXiv 2510.06917, intake pending).

## Deferred by operator decision (D7): client and transport

No boxes until the operator opens this. Recorded constraints for when it opens:
- **Remote use.** Travel laptop and phone over the network: a WebRTC-class transport with NAT traversal.
- **Echo cancellation.** Browser AEC was judged inadequate in pibot (intake-688#record).
- **A display channel** for CS-16 payloads.
- **Authentication and a security review** before any externally reachable audio endpoint (use the `security-review` skill).
- **Bandwidth and jitter tolerance.**

## Absorbed from other handoffs (2026-09-24)

- From `multimodal-pipeline.md` (INF-41):
  - **S-14** upstream argsort fix, carried as CS-43 below.
  - The S-11a standing rule, carried into CS-12.
  - The voice-cloning guardrail at :586, carried into CS-27.
  - The Qwen3-Omni quarterly watch at :684. It is superseded, because Qwen3-Omni is now a bake-off candidate.
  - The Qwen-Audio-3.0 open-weights monitor hook, carried as CS-44.
  - The stale Path-C action items at :583-585, closed there as superseded by S-2/S-6/S-9/S-11.

  S-16 and S-17 (vision and GPU budget) stay in INF-41. S-17's rule, "do not add a fifth resident model before the budget audit", applies to card 1. CS-9/CS-12 do that audit for the second card.
- From `kv-unified-stack-rollout.md` (RTG-57):
  - KVU-11's requirement "voice turns reason on :8083" becomes CS-17's default.
  - KVU-11b's measurements and acceptance become CS-12 and CS-11.
  - KVU-11c (qwentts thread flag) **stays in RTG-57**, because it matters only for a CPU speech path.

- [ ] **CS-43 — upstream the gfx90a argsort fix** (thread-strided bitonic sort) to the qwentts.cpp / ggml fork as hygiene. Moved 2026-09-24 from `multimodal-pipeline.md` S-14. It is operator-sanctioned and does not depend on our kernel cycle.
- [ ] **CS-44 — keep the Qwen-Audio-3.0 open-weights watch.** Moved 2026-09-24 from `multimodal-pipeline.md` (intake-826#record).
  - Re-intake if Alibaba publishes weights or technical details.
  - If it lands, add it to the CS-8 bake-off as a challenger.
  - The same applies to a Qwen3.5-Omni open-weight "Light" release, which is unverified on the HF Qwen org as of 2026-09-24.

## Dependency graph

```
CS-4 -> CS-8
CS-5 -> CS-8
CS-6 -> CS-8
CS-7 -> CS-8
CS-7 -> CS-9
CS-8 -> CS-28
CS-9 -> CS-12
CS-13 -> CS-14
CS-14 -> CS-38
CS-15 -> CS-25
CS-20 -> CS-21
CS-21 -> CS-26
CS-28 -> CS-29
CS-29 -> CS-32
CS-30 -> CS-32
CS-31 -> CS-32
CS-32 -> CS-33
CS-33 -> CS-34
CS-34 -> CS-35
CS-35 -> CS-36
CS-34 -> CS-39
CS-39 -> CS-42
CS-24 -> CS-41
```

## Not filed here (explicit)

- **Kyutai Unmute as a target.** It remains a reference. Our own cascade (CS-21) is the in-house baseline.
- **Kimi-Audio.** It is outside the bake-off (D1) and re-enters only if both candidates fail G1 or G3.
- **An "emotionally annotated transcript" cascade.** Rejected as the target architecture in the operator draft §2. The cascade here is only a fallback.
- **Transplanting a stronger LLM into the interlocutor backbone.** Rejected in draft §19.
- **Partitioning the CPU LLM roles or a decode throttle as standalone work.** Superseded by this plan (KVU-11b, option D). CS-11 measures the partition only as a D3 input.
- **Vision and GPU-budget items (S-16, S-17).** These stay in INF-41.

## Sources

The primary sources were checked on 2026-09-24. None are ingested yet (CS-1):
- https://github.com/stepfun-ai/Step-Audio2 (README, `token2wav.py`, issues #15 #27 #30 #33 #42 #43 #46 #55 #58 #75 #83 #86)
- https://huggingface.co/stepfun-ai/Step-Audio-2-mini (`config.json`, `model.safetensors.index.json`, `modeling_step_audio_2.py`, `token2wav/flow.yaml`)
- https://github.com/stepfun-ai/vllm/tree/step-audio2-mini (TA4 tokenizer `build_tts_interleave_data`, `step_audio_2_tool_parser.py`)
- arXiv 2507.16632 (Step-Audio 2 technical report)
- https://github.com/vllm-project/vllm-omni (`examples/online_serving/step_audio2/README.md`)
- https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct and arXiv 2509.17765
- arXiv 2507.15375 (STITCH)
- arXiv 2510.06917 (SHANKS)
- arXiv 2504.18425 (Kimi-Audio)
- arXiv 2410.00037 (Moshi)
- Upstream llama.cpp issues #21956 (mtmd audio output, planning) and #27136 (Qwen3-Omni audio input)

## Key files

| What | Where |
|---|---|
| Operator draft (input) | `docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md` |
| CPU contention study | `docs/reference/speech/cpu-speech-contention-20260924.md` |
| Speech measurement annex | `measurement/protocols/speech.md` |
| Speech launch declarations | orch `orchestration/launch_manifest.yaml:757-865`, `scripts/server/orchestrator_stack.py:2678-2813` |
| Measured-safe CPU speech layouts | orch `scripts/voice/speech_layouts.yaml`, `check_speech_layout.py` |
| /v1 streaming replay | orch `src/api/routes/openai_compat.py:926-1293` |
| Real backend chunks | orch `src/llm_primitives/inference.py:844-1300` |
| Session store | orch `src/session/sqlite_store.py:123-257` |
| MCP chat tool | orch `src/mcp_server.py:451-500` |
| Speech registry rows | research `orchestration/model_registry.yaml:2064,2159`. Their descriptions still say "HIP/gfx90a, MI210" and the dashboard still labels speech "GPU (MI210)"; fix both in CS-12. |
| mtmd audio projectors | `/mnt/raid0/llm/llama.cpp/tools/mtmd/clip-impl.h:343-362` |

## Reporting

1. Flip the box here (`- [x] … ✅ YYYY-MM-DD`).
2. Update INF-79's `Next action` in [inference-research-index.md](inference-research-index.md).
3. Append to `progress/YYYY-MM/`.

Operator decisions go through the master index's decision queue as options with tradeoffs and a recommendation: CS-2 ratification, the CS-8 winner, CS-17's default target, the CS-12 and CS-35 packages, and CS-41. Every measurement goes through CS-3 wiring before it runs.
