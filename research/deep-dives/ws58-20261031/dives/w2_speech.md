# ws58 2026-10-31 dive record: w2_speech

Markdown rendering of `w2_speech.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
entries:
- id: intake-2579
  verification: dive-verified
  read_depth: FULL
  source_revision: ggml-org/llama.cpp PR 31269 merge commit 8ca4060b7e30e76baaa5670ee1ec1b760b7f8552, GitHub API 2026-10-31
  source_text_path: scratch:dive-ws58-20261031/dive/w2speech/pr31269.all.txt
  key_claims: &id001
  - PR 31269 (merged 2026-10-28, commit 8ca4060b7, +1423/-14 in 10 files; server-realtime.cpp is 949 new lines) extends the llama-server /v1/realtime
    WebSocket endpoint from transcription-only to a realtime conversation with streaming audio input and audio output plus live ASR, for LFM3-Audio-2B-GGUF
    and LFM3-Omni-2B-GGUF.
  - 'Testing stated in the PR body: correctness checked against the reference HF implementations; F32/Q8_0/Q4_0 quantizations smoke-tested on
    Mac and CUDA. No HIP/ROCm, no CPU-only x86 result, and no latency number appears in the PR body.'
  - 'Protocol: OpenAI-realtime-shaped. Client events session.update, input_audio_buffer.append/commit, conversation.item.create, response.create,
    response.cancel; server events response.output_text.delta and response.output_audio.delta (base64 PCM16 mono) plus transcription deltas; session.type
    is realtime (conversation, default) or transcription; output_modalities text/audio/interleaved.'
  - 'There is NO server-side VAD or turn detection: session.created advertises turn_detection null, so the client decides when the user turn ends
    (commit / response.create) and barge-in is a client-sent response.cancel. The audio is prefilled as it arrives so the response starts right
    after the last chunk.'
  - 'Tool calls are NOT in this PR (no tool handling in its 10 files; the index records them in follow-up PR 31287). Dependencies: builds on the
    earlier /v1/realtime transcription endpoint (PR 30636), the mtmd streaming-audio infrastructure (PR 30629) and the LFM3 audio architecture
    (PR 31257); the README diff edits an existing realtime section.'
  - 'Live ASR (LFM3-Audio checkpoints, template asr): text for every 0.96 s of audio; context restarts at a pause after 15 s and always after
    30 s; live transcription only in sessions opened with ?intent=transcription.'
  reported_results: &id002
  - 'PR body: F32/Q8_0/Q4_0 smoke-tested on Mac and CUDA (no timing figures)'
  - examples/realtime_client.py prints "first output N ms after the end of the input" per run; the PR reports no value (277 ms is quoted by PR
    31287, recorded in intake-2575)
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: PR body Overview/Works with; pulls API additions=1423 deletions=14 changed_files=10
  - claim_index: 1
    verdict: CONFIRMED
    evidence: body states Mac+CUDA smoke tests only; no timings in body
  - claim_index: 2
    verdict: CONFIRMED
    evidence: README patch client/server event lists
  - claim_index: 3
    verdict: CONFIRMED
    evidence: server-realtime.cpp builds audio_in with turn_detection nullptr; only response.cancel exists for interruption
  - claim_index: 4
    verdict: PARTIAL
    evidence: absence of tool handling is established by reading the diff files, not by a quote; dependency PR numbers come from the intake-2575
      dive and the README patch editing an existing section
  - claim_index: 5
    verdict: CONFIRMED
    evidence: README patch live ASR paragraph
  claim_anchors:
  - claim_index: 0
    locator: pr31269 body Overview
    quote: Supports streaming audio input and audio output.
  - claim_index: 1
    locator: pr31269 body Additional information
    quote: F32/Q8_0/Q4_0 quantization smoke-tested on Mac and CUDA.
  - claim_index: 2
    locator: tools/server/README.md @8ca4060b7
    quote: '`response.cancel`: stops the response being generated'
  - claim_index: 3
    locator: tools/server/server-realtime.cpp @8ca4060b7
    quote: '{"turn_detection", nullptr}'
  - claim_index: 3
    locator: tools/server/README.md @8ca4060b7
    quote: The audio is prefilled as it arrives, so the response starts right after the last chunk.
  - claim_index: 5
    locator: tools/server/README.md @8ca4060b7
    quote: the text of every 0.96 s of audio follows it). A live ASR model restarts its context at a pause after 15 s and always after 30 s
  claim_corrections: []
  depends_on: []
  dive_corrections: 'New entry. Settles protocol (events and modalities), tested backends (Mac/CUDA only), no VAD (client-driven turns), no latency
    number in the PR, tool calls out of scope. One evidence-gap: the "tool calls" statement is an absence read from the diff.'
  reader_should_conclude: Cite for the /v1/realtime event contract and for the fact that llama-server provides no turn detection, so CS-22 (VAD
    / endpointing) stays our job. Do not claim ROCm or EPYC CPU support or any latency from this PR.
  not_read: Full diffs of server-context.cpp, server-task.cpp, server-chat.cpp; the three gists/demos in comments.
- id: intake-2580
  verification: dive-verified
  read_depth: FULL
  source_revision: ggml-org/llama.cpp PR 30629 merge commit 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40, GitHub API 2026-10-31
  source_text_path: scratch:dive-ws58-20261031/dive/w2speech/pr30629.all.txt
  key_claims: &id003
  - PR 30629 (merged 2026-10-15, 2851b3bcb, +998/-20 in 27 files) adds an EXPERIMENTAL stateful C API mtmd_audio_stream that turns PCM pushed
    in small chunks into decoder-ready embedding rows, keeping encoder state between calls; the PR says it adds only internal infrastructure and
    CLI/server are a follow-up.
  - 'API shape: mtmd_support_audio_stream, mtmd_audio_stream_init (params.step_ms, default 320 ms, rounded up to the model step), push (PCM F32
    at the model sample rate), flush(end) (end=false on a pause for a partial transcript), step(last_token) (rows ready / need more audio / end
    / error), get_output_embd.'
  - 'Model support added in the same PR: Voxtral Realtime (conversion class VoxtralRealtimeModel for mistralai/Voxtral-Mini-4B-Realtime-2602 on
    the MISTRAL3 arch, with the trained delay-token count stored as a GGUF key) and a causal conv + sliding-window ring-KV audio encoder graph
    (tools/mtmd/models/voxtral-rt.cpp, 111 lines).'
  - 'Streaming STT path: yes, in llama.cpp itself. The PR also adds a mtmd-cli mode that feeds an audio file chunk by chunk and prints tokens
    as they are produced (run_audio_stream), timing mel+encoder and decoder separately; the PR body carries no WER, latency or hardware numbers,
    and only the CPU-side C API was added, no GPU backend claim.'
  - 'The index already carries the Voxtral Realtime model facts (delay setting, vendor WER by language, GGUFs, MI210 fit): reuse intake-2383 rather
    than restating them. This entry adds only the llama.cpp API and the follow-up server wiring (PR 30636, per intake-2575).'
  reported_results: &id004
  - 'PR body: no benchmark numbers'
  - 'pulls API: additions 998, deletions 20, changed_files 27'
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: PR body; files API totals
  - claim_index: 1
    verdict: CONFIRMED
    evidence: mtmd.h patch
  - claim_index: 2
    verdict: CONFIRMED
    evidence: conversion/mistral3.py and voxtral-rt.cpp patches
  - claim_index: 3
    verdict: CONFIRMED
    evidence: mtmd-cli.cpp patch run_audio_stream; no numbers in PR body
  - claim_index: 4
    verdict: CONFIRMED
    evidence: index intake-2383 grep; PR 30636 attribution comes from intake-2575, not re-read here
  claim_anchors:
  - claim_index: 0
    locator: PR body Overview
    quote: 'Note: this PR only adds the internal infrastructure, the user-facing part (CLI and server) is a follow-up PR'
  - claim_index: 1
    locator: tools/mtmd/mtmd.h @2851b3bcb
    quote: int32_t mtmd_audio_stream_step(mtmd_audio_stream * stream, llama_token last_token);
  - claim_index: 1
    locator: tools/mtmd/mtmd.h @2851b3bcb
    quote: 'audio encoded per encoder call, rounded up to the model step (default: 320)'
  - claim_index: 2
    locator: conversion/mistral3.py @2851b3bcb
    quote: '@ModelBase.example("mistralai/Voxtral-Mini-4B-Realtime-2602")'
  - claim_index: 3
    locator: tools/mtmd/mtmd-cli.cpp @2851b3bcb
    quote: feed an audio file to a realtime model chunk by chunk, printing the transcript as it is produced
  claim_corrections: []
  depends_on:
  - entry: intake-2383
    claim_index: 0
    why: model-level quality and delay facts are carried there, not here
  dive_corrections: New entry. Confirms the API surface and that Voxtral Realtime has a native llama.cpp streaming path; adds that the PR is infrastructure
    only and reports no latency or WER, so every performance claim on the Voxtral path still comes from the vendor paper/card recorded in intake-2383.
  reader_should_conclude: Cite for the mtmd_audio_stream signatures and the Voxtral Realtime GGUF/arch path. Do not attribute WER or latency to
    this PR; they live in intake-2383. EXPERIMENTAL API, subject to breaking change per the header.
  not_read: clip.cpp, mtmd.cpp, llama-model.cpp, mtmd-audio.cpp diffs.
- id: intake-2581
  verification: dive-verified
  read_depth: FULL
  source_revision: HF LiquidAI/d1-Omni-2B-GGUF @c53ae0b1 (lastModified 2026-10-28), README + HF API, retrieved 2026-10-31; sha256-12 3bd98c1af0d5
  source_text_path: scratch:dive-ws58-20261031/dive/w2speech/d1-Omni-2B-GGUF.README.md
  key_claims: &id005
  - 'Serving contract: llama-server -hf LiquidAI/d1-Omni-2B-GGUF:Q8_0 -b 8192 -ub 8192, then POST /v1/systemone with state, optional images, files
    (audio/video as data URIs) and named questions; "supported in llama.cpp b11960 (v0.8.0) and newer".'
  - Answer types served by llama.cpp are noul, choice and score only; multiple choice, extraction, estimates and boxes are not supported yet (the
    Transformers path supports them). A question is read in one batch, so -b and -ub must hold its state and media.
  - Questions can themselves be spoken (instructions as an input_audio part) and audio clips can be the state; videos are read as frames and need
    ffmpeg in PATH.
  - 'Files in the repo: d1-Omni-2B BF16/F16 3.47 GB, Q8_0 1.85 GB; mmproj BF16/F16 0.61 GB, Q8_0 0.33 GB. There is NO Q4_K_M for Omni (the text
    d1-2B and d1-3B have one). Licence tag is lfm1.0 (LFM Open License v1.0), not an OSI licence.'
  - 'The upstream /v1/systemone endpoint itself predates b11960: it was added by PR 29818 (merged 2026-10-02) for laya, julia-1, lev, openjev
    and kev; b11960 adds the LFM3 architecture the d1 2B models need.'
  reported_results: &id006
  - GGUF sizes from HF API blobs listing (see key_claims)
  - no latency or accuracy numbers on this card; those are on the d1-Omni-2B / d1-2B cards (see intake-2553)
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: card Use with llama.cpp
  - claim_index: 1
    verdict: CONFIRMED
    evidence: card Use with llama.cpp
  - claim_index: 2
    verdict: CONFIRMED
    evidence: card Audio+Text / Spoken question sections
  - claim_index: 3
    verdict: CONFIRMED
    evidence: HF API ?blobs=true siblings; license tag
  - claim_index: 4
    verdict: CONFIRMED
    evidence: PR 29818 title/body and merge date from issues API; b11960 from the card
  claim_anchors:
  - claim_index: 0
    locator: GGUF card Use with llama.cpp
    quote: llama-server -hf LiquidAI/d1-Omni-2B-GGUF:Q8_0 -b 8192 -ub 8192
  - claim_index: 1
    locator: GGUF card Use with llama.cpp
    quote: 'Multiple choice (`"multiple": true`), extraction, estimates and boxes are not supported yet.'
  - claim_index: 1
    locator: GGUF card Use with llama.cpp
    quote: A question is read in one batch, so `-b` and `-ub` must hold its state and media.
  - claim_index: 2
    locator: GGUF card Spoken question
    quote: 'A question can be spoken: its `instructions` are an `input_audio` part.'
  claim_corrections: []
  depends_on: []
  dive_corrections: 'Adds beyond intake-2553: the exact serve command and batch flags, the supported type subset, file sizes (no Q4_K_M for Omni),
    and that /v1/systemone is an older upstream endpoint (PR 29818) independent of the d1 models. Nothing overturned.'
  reader_should_conclude: Cite for the serve contract and the noul/choice/score-only limit. Do not assume the Transformers capabilities (boxes,
    extraction) exist on the llama.cpp path. No quality, calibration or latency number comes from this card.
  not_read: LICENSE file; mmproj conversion details.
- id: intake-2582
  verification: dive-verified
  read_depth: FULL
  source_revision: HF LiquidAI/d1-2B-GGUF @e968f657 (2026-10-28) + d1-2B @10e7671d (2026-10-29) + d1-3B-GGUF @bb1e436e (2026-10-07) + d1-3B @051bcc46;
    cards and HF API, retrieved 2026-10-31
  source_text_path: scratch:dive-ws58-20261031/dive/w2speech/d1-2B.txt
  key_claims: &id007
  - 'd1-2B (1.92B, built on LFM3-VL-2B, 24 layers: 13 gated short conv, 5 sliding-window attention, 6 global attention) takes text/JSON state,
    pictures and video, NOT audio; d1-3B (3.1B) is built on LFM2.5-VL-3B. Neither is text-only: both have vision towers (mmproj files). Both carry
    the LFM Open License v1.0 (license tag "other", lfm1.0).'
  - 'Quant files: d1-2B BF16/F16 3.47 GB, Q8_0 1.85 GB, Q4_K_M 1.10 GB, mmproj Q8_0 0.20 GB; d1-3B BF16/F16 5.40 GB, Q8_0 2.87 GB, Q4_K_M 1.67
    GB, mmproj Q8_0 0.58 GB. Serve: llama-server -hf LiquidAI/d1-2B-GGUF:Q8_0 -b 8192 -ub 8192 then POST /v1/systemone; the llama.cpp path answers
    noul, choice and score only (multiple choice, extraction, estimates, boxes not yet). d1-2B-GGUF states b11960 (v0.8.0) or newer; the d1-3B-GGUF
    card gives no build and is dated 2026-10-07, so its minimum build is unverified (the endpoint itself exists since PR 29818, merged 2026-10-02).'
  - 'Decision-board results on the d1-2B card (vendor-run; columns d1-2B / d1-omni-600M / d1-Omni-2B / d1-3B): Decision Index public v0.3 51.1
    / 18.3 / 49.0 / 49.0; DecisionBench v1 77.1 / 58.7 / 76.4 / 73.1; Decision Bench v4 85.2 / 57.9 / 84.7 / 83.6; Fast Decisions 58.8 / - / 56.8
    / 59.3; JevBench 77.9 / 58.0 / 75.3 / 76.2; ImajevBench 75.5 / 21.7 / 72.3 / 64.0; WorkflowEvals 81.6 / 48.8 / 77.1 / 74.4; Typed Decisions
    61.3 / 57.5 / 63.1 / 65.0; their board 63.2 / - / 61.8 / 58.8. So the text+vision d1-2B beats d1-Omni-2B on 8 of these 9 rows (Omni wins Typed
    Decisions) and beats d1-3B on 7 of 9 (d1-3B wins Fast Decisions and Typed Decisions); the card itself says to use d1-2B when there is no audio.'
  - 'Speed on the d1-2B card (bf16, warm after model.compile(), Transformers, median of 20): one question 5.7 ms H100 PCIe, 3.8 ms MI325X, 18.6
    ms Apple M5 Pro; 5K-token state 52 / 44 / 753 ms; 64 states in one call 1,132 / 1,699 / 109 per s. There is no x86 CPU row and no MI210 row,
    and none of these timings is from llama.cpp.'
  - 'Calibration: the cards call the answers "calibrated" but report no ECE/Brier/reliability figure; the d1-2B card says "Calibrate any decision
    threshold on data from your own use". Limits stated: answers get less reliable past about 64K tokens of state; knowledge-heavy questions favour
    larger models. Related upstream risk: issue 30064 (closed) found Q8_0 GGUF of a different decision model (Clef) collapsing /v1/systemone probabilities
    toward uniform because decision-head tensors were quantized, while BF16 and a Kev Q8_0 were fine, so BF16-versus-Q8_0 probability parity must
    be checked per d1 file before any calibration claim.'
  reported_results: &id008
  - 'see key_claims: board table and speed table of the d1-2B card; sizes from HF API'
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: d1-2B card Model details; d1-3B card base_model
  - claim_index: 1
    verdict: CONFIRMED
    evidence: HF API blobs; GGUF cards
  - claim_index: 2
    verdict: CONFIRMED
    evidence: d1-2B card Benchmarks table; counts are mine from that table
  - claim_index: 3
    verdict: CONFIRMED
    evidence: d1-2B card Speed table
  - claim_index: 4
    verdict: CONFIRMED
    evidence: d1-2B card; GitHub issue 30064 body (other model)
  claim_anchors:
  - claim_index: 0
    locator: d1-2B card, intro
    quote: d1-2B is a **decision model for text, pictures, and video**, built on [LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B).
  - claim_index: 2
    locator: d1-2B card, Benchmarks
    quote: Evaluation details
  - claim_index: 3
    locator: d1-2B card, Speed
    quote: Warm calls after `model.compile()` in bf16, median of 20 calls, and best of three runs on the H100 and the M5 Pro.
  - claim_index: 4
    locator: d1-2B card, Question types
    quote: Calibrate any decision threshold on data from your own use.
  - claim_index: 4
    locator: d1-2B card, Model details
    quote: answers get less reliable past about 64K tokens of state.
  claim_corrections:
  - claim_index: 0
    effect: reattributed
    note: The brief calls d1-2B/3B text-only; both are vision-language decision models (text works without media).
  depends_on: []
  dive_corrections: New entry. Corrects "text-only" (d1-2B and d1-3B are VL models), supplies quant sizes, the nine-row board comparison (d1-2B
    above d1-Omni on 8 of 9; the earlier intake-2553 count of 7 of 9 is not reproduced from this card), and the Q8_0 head-quantization risk from
    upstream issue 30064.
  reader_should_conclude: Cite for sizes, board rows and the Transformers-only speed table. Do not present any speed as llama.cpp, EPYC or MI210.
    Do not call the answers calibrated for our data; no ECE is reported and quantized heads have a documented failure in a sibling model.
  not_read: LICENSE; the d1-3B card vision benchmark rows.
- id: intake-2583
  verification: dive-verified
  read_depth: FULL
  source_revision: liquid.ai/blog/open-d1 HTML sha256-12 555ce078e6cf, retrieved 2026-10-31
  source_text_path: scratch:dive-ws58-20261031/dive/w2speech/open-d1.txt
  key_claims: &id009
  - The post (dated OCT 7, 2026) releases d1-3B and d1-omni-600M, NOT the later LFM3-based d1-2B / d1-Omni-2B. d1-3B is trained from LFM2.5-VL-3B
    (text+image); d1-omni-600M from the bidirectional LFM2.5-Encoder-350M with vision and audio encoders added.
  - 'Vendor-reported: d1-3B 48.57 on Decision Index v0.2.1 (public split), "ahead of every model under 10B and on par with Decider 35B-A3B"; d1-omni-600M
    15.95. Text means over seven public benchmarks: d1-3B 82.9, d1-omni-600M 78.4, Decider 2B 77.1, Decider 4B 81.1. The post says dedicated audio
    decision benchmarks are "currently an open problem" and reports no audio result.'
  - 'Latency table for d1-3B, one request at a time (one question / 3 questions / 3.4K-token state / 384px image / 64 states packed): RTX 4090
    8 / 21 / 102 / 17 ms, 475 per s; MI325X 9 / 14 / 44 / 18 ms, 1,106 per s; Apple M5 Pro 30 / 41 / 640 / 62 ms, 78 per s; Jetson AGX Thor 16
    ms, AGX Orin 26 ms, Orin Nano 50 ms for one question. Stack and precision of these timings are not stated in the text read; the post says
    "day-one support for llama.cpp". No x86 server CPU and no MI210.'
  - 'Licence wording conflict: the post says "Open-weight - Download, fine-tune, and deploy without restrictions" while the model cards carry
    the LFM Open License v1.0 (license: other, lfm1.0); read the licence text before any commercial reliance.'
  - The post reports no calibration metric (ECE/Brier) although the models are described as calibrated; the quality evidence is accuracy-style
    benchmark means and an index run by the vendor.
  reported_results: &id010
  - Table 1 text benchmark means; Tables 2 and 3 latency (see key_claims)
  claim_verdicts:
  - claim_index: 0
    verdict: CONFIRMED
    evidence: 'post body: "Today, we release d1-3B and d1-omni-600M"'
  - claim_index: 1
    verdict: CONFIRMED
    evidence: intro + Table 1 + Vision and audio performance paragraph
  - claim_index: 2
    verdict: CONFIRMED
    evidence: Tables 2 and 3
  - claim_index: 3
    verdict: CONFIRMED
    evidence: Get Started bullets vs card license tag
  - claim_index: 4
    verdict: CONFIRMED
    evidence: 'absence: no ECE/Brier/reliability string in the post'
  claim_anchors:
  - claim_index: 0
    locator: Intro
    quote: Today, we release d1-3B and d1-omni-600M, two open-weight models in our d1 decision model family.
  - claim_index: 1
    locator: Vision and audio performance
    quote: Dedicated audio decision benchmarks are currently an open problem.
  - claim_index: 2
    locator: Fast Inference Everywhere
    quote: d1-3B and d1-omni-600M run the full NVIDIA stack
  - claim_index: 3
    locator: Get Started
    quote: Open-weight — Download, fine-tune, and deploy without restrictions
  claim_corrections: []
  depends_on: []
  dive_corrections: New entry. Dates the post (2026-10-07) and narrows it to d1-3B / d1-omni-600M; the 2B and Omni-2B models in intake-2553/2581/2582
    are later and not in it. Records the licence-wording mismatch and the absent audio and calibration evidence.
  reader_should_conclude: Cite only for d1-3B / d1-omni-600M vendor figures and the licence-wording mismatch. Do not use its numbers for the 2B
    models. All figures are vendor-reported.
  not_read: Figures 2-3, Jetson AI Lab pages, playground demos.
new_entries:
- id: intake-2579
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/pull/31269
  source_type: repo
  title: 'llama.cpp PR 31269: server realtime conversation and live transcription on /v1/realtime (LFM3-Audio / LFM3-Omni)'
  categories:
  - multimodal
  - inference_serving
  - local_inference
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2575
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - tdakhran (PR author)
  - ngxson (contributor/reviewer)
  key_claims: *id001
  techniques:
  - stateful streaming audio prefill
  - OpenAI-realtime-compatible WebSocket events
  - interleaved text+audio output modalities
  reported_results: *id002
  cross_references:
    chapters: []
    handoffs:
    - conversation-stack.md
    experiments: []
    intake_entries:
    - intake-2575
    - intake-2554
    - intake-2383
  recommended_actions:
  - 'Do not port for ASR alone: the realtime server needs the LFM3 audio arch (PR 31257) which is outside frozen v10 (10303). If the interlocutor
    bake-off (CS-8 D1) is opened, a scratch upstream build of this PR is the cheapest native-duplex arm; the CS-22 controller keeps owning turn
    detection because the server provides none.'
  credibility_score: 'Vendor/author PR; read the PR body, issue comments (4, none carry measurements), the 10-file diff metadata and the README/server-realtime/client
    patches. Not read: full diff of server-context.cpp/server-task.cpp.'
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: null
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: ggml-org/llama.cpp PR 31269 merge commit 8ca4060b7e30e76baaa5670ee1ec1b760b7f8552, GitHub API 2026-10-31
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2580
  arxiv_id: null
  url: https://github.com/ggml-org/llama.cpp/pull/30629
  source_type: repo
  title: 'llama.cpp PR 30629: mtmd_audio_stream streaming-audio API and Voxtral Realtime support'
  categories:
  - multimodal
  - inference_serving
  - local_inference
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2575
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - ngxson (PR author)
  key_claims: *id003
  techniques:
  - stateful streaming audio encoder
  - sliding-window ring KV cache for the audio encoder
  - embedding-row feeding into the text decoder
  reported_results: *id004
  cross_references:
    chapters: []
    handoffs:
    - conversation-stack.md
    experiments: []
    intake_entries:
    - intake-2575
    - intake-2383
  recommended_actions:
  - 'Add a CS-8.STT cell: Voxtral-Mini-4B-Realtime GGUF (ggml-org) through the mtmd-cli run_audio_stream mode on a scratch upstream build, scored
    by the CS-8.STT1 scorer on the CS-45 clips, against Nemotron streaming and whisper.cpp. Screen only; promotes nothing.'
  credibility_score: 'Author PR. Read PR body, 27-file list, and the mtmd.h, mtmd-cli.cpp, mistral3.py, voxtral-rt.cpp patches; issue comments
    none relevant. Not read: clip.cpp / mtmd.cpp / llama-model.cpp diffs.'
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: null
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: ggml-org/llama.cpp PR 30629 merge commit 2851b3bcbf8d993a2243ae751c0a7dfa8e944a40, GitHub API 2026-10-31
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2581
  arxiv_id: null
  url: https://huggingface.co/LiquidAI/d1-Omni-2B-GGUF
  source_type: repo
  title: 'd1-Omni-2B-GGUF (Liquid AI): llama.cpp /v1/systemone serving of the audio+vision+text decision model'
  categories:
  - routing_intelligence
  - multimodal
  - local_inference
  - inference_serving
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2553
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - Liquid AI
  key_claims: *id005
  techniques:
  - one-forward-pass typed decisions served through llama-server
  - batched named questions
  - audio mmproj for spoken state and spoken questions
  reported_results: *id006
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    - routing-intelligence.md
    - conversation-stack.md
    experiments: []
    intake_entries:
    - intake-2553
    - intake-2575
    - intake-1498
    - intake-1514
  recommended_actions:
  - Do not use Omni for text-only routing (d1-2B text path beats it on 8 of 9 decision rows per the d1-2B card); reserve it for a spoken-state
    decision probe (turn completeness, intent) only after human-recorded CS-45 strata exist.
  credibility_score: 'Vendor model-card repo; the card is a short README. Not read: LICENSE text, the original d1-Omni-2B card (intake-2553 covers
    it), convert logs.'
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: null
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: HF LiquidAI/d1-Omni-2B-GGUF @c53ae0b1 (lastModified 2026-10-28), README + HF API, retrieved 2026-10-31; sha256-12 3bd98c1af0d5
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2582
  arxiv_id: null
  url: https://huggingface.co/LiquidAI/d1-2B-GGUF
  source_type: repo
  title: 'd1-2B-GGUF and d1-3B-GGUF (Liquid AI): text, picture and video decision models served by llama.cpp /v1/systemone'
  categories:
  - routing_intelligence
  - cost_aware_routing
  - local_inference
  - inference_serving
  novelty: medium
  relevance: high
  discovered_via: expansion
  expanded_from: intake-2553
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - Liquid AI
  key_claims: *id007
  techniques:
  - one-pass typed decisions
  - multi-question batching with shared state prefix
  - LFM3 hybrid conv/attention backbone
  reported_results: *id008
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    - routing-intelligence.md
    - learned-routing-controller.md
    experiments: []
    intake_entries:
    - intake-2553
    - intake-2581
    - intake-2583
    - intake-1498
    - intake-1514
    - intake-1502
    - intake-1517
  recommended_actions:
  - 'TD-23 candidate: d1-2B-GGUF Q8_0 (1.85 GB) via /v1/systemone on a scratch upstream build as the "one available local compact decision backend"
    against the constrained incumbent on the TD-11/CJ-15 sealed routing set (see ledger W2SP-3).'
  credibility_score: 'Vendor cards. Read: d1-2B-GGUF and d1-3B-GGUF READMEs, d1-2B and d1-3B model cards (text), HF API metadata. Not read: LICENSE
    text, vision benchmark rows beyond the table header, issue 30402 repro scripts in full.'
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: null
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: HF LiquidAI/d1-2B-GGUF @e968f657 (2026-10-28) + d1-2B @10e7671d (2026-10-29) + d1-3B-GGUF @bb1e436e (2026-10-07) + d1-3B @051bcc46;
    cards and HF API, retrieved 2026-10-31
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
- id: intake-2583
  arxiv_id: null
  url: https://www.liquid.ai/blog/open-d1
  source_type: repo
  title: 'Open d1: Edge decision models for text, vision, and audio (Liquid AI blog, 2026-10-07)'
  categories:
  - routing_intelligence
  - local_inference
  - multimodal
  - benchmark_methodology
  novelty: medium
  relevance: medium
  discovered_via: expansion
  expanded_from: intake-2553
  verdict: worth_investigating
  ingested_date: '2026-10-31'
  authors:
  - Liquid AI
  key_claims: *id009
  techniques:
  - model merging (weight averaging of LFM2.5-2.6B and the VL text backbone)
  - answer-option shuffling and shortcut removal in training
  - one-pass decision heads
  reported_results: *id010
  cross_references:
    chapters: []
    handoffs:
    - typed-decision-plane.md
    - routing-intelligence.md
    experiments: []
    intake_entries:
    - intake-2553
    - intake-2581
    - intake-2582
  recommended_actions:
  - 'Use only as vendor context: the actionable artefacts are the GGUFs (intake-2581 / intake-2582). Treat its latency table as the only llama.cpp-era
    timing and predeclare our own.'
  credibility_score: Vendor blog, curl HTML to disk and stripped (JS-light page, text present). Figures 2-3 (architecture diagrams) not viewable
    as text.
  contradicting_evidence: null
  referenced_arxiv_ids: []
  notes: null
  verification: stage1-unverified
  handoffs_updated: []
  handoffs_created: []
  source_revision: liquid.ai/blog/open-d1 HTML sha256-12 555ce078e6cf, retrieved 2026-10-31
  reader_should_conclude: 'Stage-1 unverified: do not cite.'
ledger:
- row: W2SP-1
  entries:
  - intake-2579
  - intake-2575
  action: Build upstream master (or tag b11960+) as a SCRATCH llama-server on llama.cpp-experimental from fresh production; run examples/realtime_client.py
    with LFM3-Audio-2B Q8_0 and Q4_0 on the EPYC CPU and MI210 and record first-output-after-end-of-input, with a per-chunk RTF. Plus a /v1/realtime
    ROCm correctness check against the CPU build (token-identical greedy where defined).
  grounding: handoffs/active/conversation-stack.md:153 ("No voice path exists... no VAD, turn detection, barge-in, websocket or client") and :92
    (D1 bake-off has not run); PR 31269 tests were Mac+CUDA only
  owner: handoffs/active/conversation-stack.md
  posture: cheap-screen-now
  benefit: lower end-of-turn-to-first-audio latency than the STT->LLM->TTS cascade; must stay correct on gfx90a (untested upstream)
  decision_rule: Promote to a CS-8 bake-off arm only if first-output <= the cascade median on the same clips AND ROCm output matches CPU on the
    fixed prompts; stop on any ROCm divergence, file as build cost
  reason: Cheapest native duplex arm; settles backend portability before any quality work
- row: W2SP-2
  entries:
  - intake-2579
  action: 'Specify the server-turn contract in CS-22: because /v1/realtime has turn_detection null, our controller (VAD + CS-47 semantic gate)
    must send commit/response.create/response.cancel; add this as the integration seam in CS-22.A1 rather than waiting on a server VAD.'
  grounding: handoffs/active/conversation-stack.md:359-360 (CS-22 text), :81-85 (turn detection evidence, human_recorded stratum empty)
  owner: handoffs/active/conversation-stack.md
  posture: knowledge-only
  benefit: keeps endpointing under our measured policy; no change to correctness
  decision_rule: n/a
  reason: Doc fact; no compute
- row: W2SP-3
  entries:
  - intake-2582
  - intake-2581
  - intake-2583
  action: 'TD-23 screen: d1-2B-GGUF Q8_0 via /v1/systemone (scratch upstream build, CPU quarter or MI210 window) versus the constrained incumbent
    readout, on a frozen, row-pinned labelled routing set (the TD-11 / CJ-15 sealed workload; labels from the routing-replay snapshot, not from
    either arm). Six controls: (1) pinned model/GGUF sha256 and llama.cpp commit recorded in decision_receipt.v1; (2) incumbent run on the same
    rows in the same window; (3) candidate-order and key permutations (TD-16 style) plus explicit unknown option; (4) BF16 vs Q8_0 probability
    parity on the same rows (guards the issue-30064 head-quantization failure); (5) single-request vs batched/-np>=2 invariance (guards issue
    30402 batch dependence) ; (6) held-out calibration split with ECE/Brier and a resampled noise floor, repeated runs for latency. Optional arm:
    d1-3B Q8_0 as size/quality contrast; d1-Omni excluded for text routing.'
  grounding: handoffs/active/typed-decision-plane.md:599 (TD-23 text), :419 (TD-11 acceptance), :464 (TD-18 receipt), :460 (TD-16 label-word bias);
    orchestrator src/typed_decisions/native.py and routing_counterfactual.py hold the incumbent readout/harness
  owner: handoffs/active/typed-decision-plane.md
  posture: cheap-screen-now
  benefit: router/triage accuracy and calibration per millisecond; correctness (no regression vs incumbent) must hold
  decision_rule: 'Predeclare in the run-plan: advance only if d1-2B accuracy >= incumbent with paired CI excluding a loss, ECE no worse than incumbent
    on the held-out split, Q8 vs BF16 top-choice agreement >= 99%, batch invariance within the repeat-noise floor; otherwise decline and record.
    Timing is reported but never gates quality.'
  reason: Honors operator ruling Q1 (local models only); d1-2B is the best-scoring text+vision d1 model on the vendor board and has a 1.85 GB
    GGUF
- row: W2SP-4
  entries:
  - intake-2582
  action: Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score
    only; routing questions are choice+score so the subset is sufficient.
  grounding: 'handoffs/active/typed-decision-plane.md:663 (M1/M6/M7/M8 prose: one compatible local candidate)'
  owner: handoffs/active/typed-decision-plane.md
  posture: knowledge-only
  benefit: avoids a wrong premise (text-only; Transformers-only types)
  decision_rule: n/a
  reason: Corrects stage-1 framing
- row: W2SP-5
  entries:
  - intake-2581
  action: Spoken-state decision probe (turn completeness / intent) with d1-Omni-2B on the CS-45 turn-taking corpus once human_recorded strata
    exist; score with the CS-45 measurands against the CS-47 semantic-gate arms.
  grounding: handoffs/active/conversation-stack.md:85 (human_recorded stratum EMPTY, only it can advance an arm), :116-118
  owner: handoffs/active/conversation-stack.md
  posture: monitor
  benefit: a one-pass decision model could replace a semantic end-of-turn gate; must not raise false-cut rate
  decision_rule: Blocked by the empty stratum, a real dependency (recording, not software); vendor audio rows are mixed (spoken short states 22.8
    heard vs 42.0 written, per intake-2553)
  reason: Genuine data dependency on human recordings
- row: W2SP-6
  entries:
  - intake-2580
  - intake-2383
  action: Add a Voxtral-Mini-4B-Realtime GGUF through mtmd-cli run_audio_stream arm to the CS-8.STT5 screen (ranks and rejects only) on a scratch
    upstream build; record encoder and decoder times separately as the CLI already prints them.
  grounding: handoffs/active/conversation-stack.md:680 (CS-8.STT5 text), :704 (CS-22.A1 streaming runner acceptance)
  owner: handoffs/active/conversation-stack.md
  posture: cheap-screen-now
  benefit: a streaming STT inside llama.cpp (one runtime) instead of a separate ggml speech tree; WER at the 480 ms delay must not lose to the
    whisper.cpp arm on our four languages
  decision_rule: Vendor WER at 480 ms is behind offline Whisper on en/de/fr/it per intake-2383; advance only if our measured WER within 1 point
    of whisper.cpp and RTF < 1 on CPU quarter
  reason: API is native upstream; cost is a build and a GGUF download
dive_surfaced_sources:
- source: https://github.com/ggml-org/llama.cpp/pull/29818
  settles: The /v1/systemone endpoint implementation (server-decision.cpp, 681 lines), supported decision architectures, shared-prefix batching
    and the reference-vs-llama.cpp probability parity table
  bears_on: intake-2582
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/issues/30064
  settles: Q8_0 quantization of decision-head tensors collapsed probabilities toward uniform on Clef; the control for any d1 Q8_0 calibration
    claim
  bears_on: intake-2582
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/issues/30402
  settles: Batch dependence of /v1/systemone answers for a non-causal model; whether LFM3 (causal) d1 files are exposed
  bears_on: intake-2582
  recommend: ingest-and-dive
- source: https://github.com/ggml-org/llama.cpp/pull/31287
  settles: Tool calls over /v1/realtime and the 277 ms first-output demo (already summarized in intake-2575)
  bears_on: intake-2579
  recommend: 'decline: already summarized in intake-2575 dive; re-read only if CS-8 bake-off opens'
artifact_audit: clean
```
