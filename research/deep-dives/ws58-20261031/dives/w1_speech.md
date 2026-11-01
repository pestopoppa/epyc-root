# ws58 2026-10-31 dive record: w1_speech

Markdown rendering of `w1_speech.yaml` (the original is kept beside it) so the wiki scanner sees this dive. Intake IDs are as the dive recorded them; read them as `#record` references. Digit runs of 12+ digits are written grouped.

```yaml
entries:
- id: intake-2552
  verification: dive-verified
  read_depth: FULL
  source_revision: 'HF LiquidAI/LFM3-Audio-2B @0295e413 (lastModified 2026-10-31T00:51Z), raw README sha256-12 90a0abb9e3e4, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/speech/LFM3-Audio-2B.clean.txt
  key_claims:
  - '~2B end-to-end audio model: text or 16 kHz audio in; text, 24 kHz speech or interleaved out; tool calling from speech. Voice chat and LiveASR are English-only; 19 speech locales (incl. Italian) for ASR/TTS/translation.'
  - 'Main card does not say whether audio works under llama.cpp (its GGUF row says only local CPU/GPU inference); the separate GGUF card (intake-2575) states llama.cpp b11960+ and upstream PR #31257 merged 2026-10-27 implements it.'
  - 'Vendor-run (Liquid AI) table: English ASR WER 6.23 (ESB/Open ASR avg; Voxtral Mini 5.51 and NVIDIA Audex 5.99 are better, LFM2.5-Audio 6.13), multilingual WER/CER 6.03 (FLEURS 9 langs), English TTS UTMOSv2 3.83, VoiceBench 73.13, tool calling 58.50 (internal eval; Gemma 4E4B 72.40 higher), MMAR 50.60.'
  - 'License is lfm1.0 (front matter license: other); not Apache/MIT.'
  - 'Streaming: vendor says time to first token can be as low as 50 ms (hardware and conditions not stated) and LiquidCodec decodes about 87x real time on one Apple M4 Max CPU thread; codec = 80 ms of speech per 12 discrete tokens.'
  reported_results:
  - 'Benchmarks table (Performance section): English ASR WER 6.23; Multilingual ASR 6.03; English TTS UTMOSv2 3.83; VoiceBench 73.13; Tool calling 58.50; MMAR 50.60; peers listed in the same row (LFM2.5-Audio 6.13/-/3.22/55.17/-/25.85; Gemma 4E4B 7.82/6.54/-/72.90/72.40/49.10; Voxtral Mini 5.51/7.76/-/65.78/44.50/50.10).'
  - 'Streaming performance: TTFT as low as 50 ms; LiquidCodec about 87x real time single CPU thread Apple M4 Max.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Model details table and bullet list; English-only voice chat is an added limitation absent from stage 1.'}
  - {claim_index: 1, verdict: PARTIAL, evidence: 'True of the main card alone; the GGUF card and upstream PRs settle it (see intake-2575).'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Table read verbatim; the model is NOT best on ASR WER or tool calling among listed peers.'}
  - {claim_index: 3, verdict: PARTIAL, evidence: 'Front matter license_name lfm1.0; the Audio card license table cell is empty after HTML strip, Omni card names LFM Open License v1.0.'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'New claim; vendor figures with no hardware for the 50 ms.'}
  claim_anchors:
  - {claim_index: 0, locator: 'card intro + Voice chat bullet', quote: 'Voice chat:** ask questions aloud and receive streaming replies in text and speech. For text-only responses, the model can reason before answering. Currently supports English only.'}
  - {claim_index: 2, locator: 'Performance > Benchmarks table', quote: 'English ASRWER ↓ | 6.23 | 6.13 | 8.26 | 7.82 | 6.30 | 5.99 | 5.51 |'}
  - {claim_index: 2, locator: 'Performance > Benchmarks table', quote: 'Tool callinginternal eval ↑ | 58.50 | — | 55.60 | 72.40 | 44.30 | — | 44.50 |'}
  - {claim_index: 4, locator: 'Performance > Streaming performance', quote: 'Time to first token can be **as low as 50 ms**.'}
  claim_corrections:
  - {claim_index: 1, effect: narrowed, note: 'Not a defect of the card set: the GGUF card (intake-2575) states the llama.cpp release; stage-1 should have bound them.'}
  - {claim_index: 2, effect: narrowed, note: 'Stage 1 said the table compares against small omni models; correct, but the model loses to Voxtral Mini and Audex on English ASR and to Gemma 4E4B on tool calling and is vendor-run.'}
  depends_on: []
  dive_corrections: 'Stage 1 filing confirmed. Added: English-only voice chat/LiveASR, concrete table numbers showing the model is not the ASR or tool-call leader, TTFT 50 ms is unqualified by hardware. The WER metric is ESB average, not comparable with our FLEURS-based whisper anchor (3.37 percent, n=1870 words).'
  reader_should_conclude: 'Cite as a vendor card with vendor-run numbers only. Do not carry 50 ms TTFT or 6.23 WER as evidence for our hardware or our corpora; both need our own measurement. Do not claim it replaces ASR on accuracy grounds.'
  not_read: 'Fine-tuning notebooks; liquid.ai/blog/lfm3 (not fetched); weights (forbidden).'
- id: intake-2554
  verification: dive-verified
  read_depth: FULL
  source_revision: 'HF LiquidAI/LFM3-Omni-2B @5797d07c (lastModified 2026-10-28T23:16Z), raw README sha256-12 2574663e12ee, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/speech/LFM3-Omni-2B.clean.txt
  key_claims:
  - '2.17B-parameter (card prose: 2.2B) omni model: text, images, video (with or without soundtrack) and 16 kHz audio in; text, 24 kHz speech or interleaved out; non-reasoning; 32K context; 19 speech locales; 16 text languages.'
  - 'GGUF row: llama.cpp local CPU/GPU inference including a realtime speech server (realtime speech needs llama.cpp b11960+, see intake-2575).'
  - 'Vendor-run (all scores measured by Liquid AI): English ASR WER 6.36 (Phi-4-multimodal 5.14 better), multilingual 6.72, TTS UTMOSv2 3.80, VoiceBench 64.73, tool calling 52.20 (Gemma 4E4B 72.40, E2B 55.60 higher), MMAR 51.40; Daily-Omni 70.09, WorldSense 47.10, OmniBench 46.32.'
  - 'Omni is weaker than the Audio sibling on voice-assistant metrics (VoiceBench 64.73 vs 73.13, tool calling 52.20 vs 58.50) but adds vision/video.'
  reported_results:
  - 'Audio table: English ASR 6.36; Multilingual 6.72; TTS 3.80; VoiceBench 64.73; Tool calling 52.20; MMAR 51.40.'
  - 'Omni table: Daily-Omni 70.09; WorldSense 47.10; AV-SpeakerBench 46.79; OmniBench overall 46.32 / speech 48.25.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Model details table (2.17B total).'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Inference table GGUF row.'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Evaluation details: All scores were measured by Liquid AI.'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'New: cross-card comparison of the two tables.'}
  claim_anchors:
  - {claim_index: 0, locator: 'Model details table', quote: 'Parameters | 2.17B total'}
  - {claim_index: 1, locator: 'Inference table', quote: 'GGUF | llama.cpp | Local inference on CPUs and GPUs, including a realtime speech server.'}
  - {claim_index: 2, locator: 'Audio table', quote: 'Tool callinginternal eval ↑ | 52.20 | 44.30 | 55.60 | 72.40 | — |'}
  - {claim_index: 2, locator: 'Evaluation details', quote: 'All scores were measured by Liquid AI.'}
  claim_corrections:
  - {claim_index: 0, effect: unaffected, note: 'Stage 1 said about 2.2B; exact figure 2.17B.'}
  depends_on: []
  dive_corrections: 'Confirmed. Added exact rows and the cross-card finding that Omni underperforms Audio on VoiceBench/tool calling.'
  reader_should_conclude: 'Cite for modality coverage only; all numbers vendor-measured. Omni does not beat Audio-2B on speech-assistant metrics.'
  not_read: 'Vision/video usage code samples in the card body (skimmed); weights.'
- id: intake-2575
  verification: dive-verified
  read_depth: FULL
  source_revision: 'HF LiquidAI/LFM3-Audio-2B-GGUF @02355c1a (2026-10-29) + LFM3-Omni-2B-GGUF @3d29af2a; upstream ggml-org/llama.cpp PRs #31257 (19ff817fb), #31269 (8ca4060b7), #31287 (d1eb0deba), #30629 (2851b3bcb), #30636 (1242be66f), #31386, #31283 read via gh pr view, retrieved 2026-10-31'
  source_text_path: scratch:dive-ws58-20261031/dive/speech/LFM3-Audio-2B-GGUF.README.md
  key_claims:
  - 'Cards state llama.cpp support from b11960 (tag v0.8.0, published 2026-10-28), including real-time voice conversations with tool calls on the /v1/realtime WebSocket API of `llama serve`.'
  - 'Speech output goes through an audio mmproj (llama-tts -m model -mm mmproj); files BF16, F16, Q8_0, Q4_K_M, Q4_0 for model and mmproj each.'
  - 'Stage 1 said no PR is linked: true of the cards, but the implementing PRs are findable upstream: #31252 (LFM3 arch, merged 2026-10-27), #31257 (audio+omni, +2721/-160, 31 files, merged 2026-10-27), #30629 (mtmd_audio_stream, merged 2026-10-15), #30636 (/v1/realtime transcription, 2026-10-20), #31269 (realtime conversation + live ASR, 2026-10-28), #31287 (tool calls in realtime, 2026-10-28), #31386 (codec quantization), #31283 (video).'
  - 'Upstream test coverage stated in PR #31269: F32/Q8_0/Q4_0 smoke-tested on Mac and CUDA; no HIP/ROCm or CPU-only EPYC result exists. PR #31287 shows 277 ms first output after end of input on unstated hardware.'
  - 'Distance: our frozen v10 is build 10303 (b10303 published 2026-08-07); b11960 is 1657 builds ahead (gh compare b10303...b11960 ahead_by=1657). v10 has /v1/audio/transcriptions (PR #21863) and tools/tts but no lfm3 arch, mtmd_audio_stream or server-realtime.'
  reported_results:
  - 'PR #31287 body: first output 277 ms after end of input; audio 2.56 s (demo, hardware unstated).'
  - 'PR #31386 body: Audio mmproj Q4_0 213.6 MB -> 161.4 MB; Omni mmproj Q4_0 322.8 -> 270.6 MB.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'GGUF README note, plus gh release b11960/v0.8.0 dates.'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'HF API siblings list and llama-tts command.'}
  - {claim_index: 2, verdict: PARTIAL, evidence: 'Cards link no PR (true) but PRs exist and were found; stage-1 gap closed.'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'PR #31269 body.'}
  - {claim_index: 4, verdict: CONFIRMED, evidence: 'gh compare and local tree grep (no realtime/lfm3 in /mnt/raid0/llm/llama.cpp).'}
  claim_anchors:
  - {claim_index: 0, locator: 'GGUF README Use with llama.cpp note', quote: 'Supported in [llama.cpp](https://github.com/ggml-org/llama.cpp) [b11960](https://github.com/ggml-org/llama.cpp/releases/tag/b11960) ([v0.8.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0)) and newer'}
  - {claim_index: 1, locator: 'GGUF README llama-tts example', quote: 'llama-tts -m LFM3-Audio-2B-Q4_K_M.gguf -mm mmproj-LFM3-Audio-2B-Q8_0.gguf'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'PR numbers and merge dates recorded; PR bodies are the primary source for the live-ASR, hardware and test statements (locator pr<N>.json in the dive dir).'}
  depends_on: []
  dive_corrections: 'Resolved the open question: implementing PRs located, release b11960, distance 1657 builds, and the realtime path has only been smoke-tested on Mac and CUDA. LiveASR for LFM3-Audio is in #31269 ("Supports live ASR") though #31257 table said follow up.'
  reader_should_conclude: 'Cite b11960 / PR numbers for the port scope. Do not claim ROCm or EPYC CPU support: untested upstream. The 277 ms figure is a PR demo on unstated hardware.'
  not_read: 'Full diffs of the PRs (bodies and file lists only); docs.liquid.ai llama.cpp guide.'
- id: intake-2573
  verification: dive-verified
  read_depth: PARTIAL
  source_revision: 'github.com/anomalyco/hex @eef51da7 (commit date 2026-10-31), clone depth 1; pinned transcribe.cpp fork rev 7045d1c0 (Cargo.toml)'
  source_text_path: scratch:dive-ws58-20261031/dive/speech/hex/README.md
  key_claims:
  - 'Hex (Rust, MIT) transcribes on device with user-selected Parakeet or Whisper models (Parakeet Unified English, v2, v3, Whisper large-v3-turbo; GGUF Q8_0 artifacts from handy-computer HF repos).'
  - 'Depends on transcribe-cpp =0.4.1 patched to a pinned anomalyco/transcribe.cpp fork rev 7045d1c0 (Vulkan shader subset and Parakeet vocabulary rescoring); Vulkan on Windows/Linux, Metal path exists on macOS. Different pin from our CS-8.STT2 build (db678a03, ggml 0.26.0).'
  - 'Streaming Parakeet Unified English: README says text arrives within about 100 ms of release; per src/transcription_models.rs it streams only on a GPU device after a load probe, otherwise whole-clip. "Rolling" transcript is a meeting-chunk feature documented in docs/, not the dictation path.'
  - 'Self-reported model table: Unified English ~163x realtime, WER 1.60 ("English benchmark", unspecified); docs/plans cite 5.91 percent 8-set WER and ~188x on Metal. Internally inconsistent figures, unverified; no ROCm or HIP path in hex.'
  reported_results:
  - 'src/transcription_models.rs MODELS: ParakeetUnifiedEnglish realtime ~163x, word_error_rate 1.60, streams true; ParakeetV2 ~55x, 1.69, streams false.'
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'transcription_models.rs and README.'}
  - {claim_index: 1, verdict: PARTIAL, evidence: 'Fork pin and Vulkan confirmed (Cargo.toml); Metal claim is for hex UI (rune) and transcribe-cpp macOS, README cites Metal speeds.'}
  - {claim_index: 2, verdict: PARTIAL, evidence: 'Streaming real but GPU-only; rolling is meeting transcript.'}
  - {claim_index: 3, verdict: CONFIRMED, evidence: 'New; vendor-style self-report.'}
  claim_anchors:
  - {claim_index: 2, locator: 'README Windows Beta', quote: 'Parakeet Unified English streams while you speak, so text arrives within'}
  - {claim_index: 0, locator: 'README Dictate Anywhere', quote: 'between combinations such as English with Parakeet and French with Whisper'}
  claim_corrections:
  - {claim_index: 2, effect: narrowed, note: 'Streaming is GPU-only in hex (transcription_models.rs:157-159); not a CPU streaming path.'}
  depends_on: []
  dive_corrections: 'The STT path is a thin Rust wrapper over transcribe.cpp; it adds no new runner for us because transcribe.cpp is already built and under test in conversation-stack CS-8.STT2/STT3/STT4. Hex is a UX reference for vocabulary biasing and chunked meeting transcripts only.'
  reader_should_conclude: 'Cite hex only as evidence that transcribe.cpp 0.4.1 serves Parakeet Unified streaming on Vulkan GPUs. Do not carry its WER or xRT numbers; they are self-reported and inconsistent. No new STT runner action from this entry.'
  not_read: 'transcribe.cpp fork source itself (not cloned); most of the 6k lines of src; macOS/iOS code.'
- id: intake-2564
  verification: dive-verified
  read_depth: FULL
  source_revision: 'block.xyz/dessa raw HTML retrieved 2026-10-31, text extract sha256-12 over dessa.txt'
  source_text_path: scratch:dive-ws58-20261031/dive/speech/dessa.txt
  key_claims:
  - 'Full-duplex speech-to-speech model trained from scratch on human conversation audio only (no text, no pretrained models), on one NVIDIA GB200 NVL72.'
  - 'Page claims backchanneling, cut-ins, faster-than-real-time inference and local operation on a MacBook Pro M4 Max or better; all claims are unquantified marketing.'
  - 'Access: waitlist plus early access for AI safety researchers; no paper, weights, API, benchmarks, or architecture details on the page.'
  reported_results: []
  claim_verdicts:
  - {claim_index: 0, verdict: CONFIRMED, evidence: 'Page text.'}
  - {claim_index: 1, verdict: CONFIRMED, evidence: 'Page text; "M4 Max or better" is a hardware floor, no latency number.'}
  - {claim_index: 2, verdict: CONFIRMED, evidence: 'Join the waitlist; safety-researcher early access.'}
  claim_anchors:
  - {claim_index: 0, locator: 'What is this?! / This is crazy!', quote: 'we figured out how to train Dessa on only'}
  - {claim_index: 1, locator: 'What is this?!', quote: 'And it runs locally on a MacBook Pro M4 Max or better.'}
  - {claim_index: 2, locator: 'Calling all safety researchers', quote: 'We’re giving a small group of AI safety researchers early access'}
  claim_corrections:
  - {claim_index: 0, effect: unaffected, note: 'Training hardware (one GB200 NVL72) added.'}
  depends_on: []
  dive_corrections: 'Filing confirmed; the page has no technical spec at all. Availability: waitlist only.'
  reader_should_conclude: 'Cite only as a monitor-trigger source for audio-only full-duplex models. No numbers or architecture to carry.'
  not_read: 'Audio clips; linked X posts.'
ledger:
- {row: SPEECH-1, entries: [intake-2552, intake-2554, intake-2575], action: 'Bounded probe LFM3-1: build an experimental llama.cpp tree (fresh v10 + upstream b11960 audio path: PRs 31252, 30629, 30636, 31257, 31269, 31287, 31386) on CPU only first; run LFM3-Audio-2B Q8_0 ASR over the 40 pinned FLEURS clips (en/it/de/fr x10) and compare WER with the frozen whisper large-v3-turbo and parakeet-cli rows through the CS-8.STT1 scorer.', grounding: 'handoffs/active/conversation-stack.md CS-8.STT0/STT1/STT5 (40 pinned FLEURS clips, stt_norm/v1 scorer); CS-8 bake-off lists only Step-Audio 2 mini and Qwen3-Omni (conversation-stack.md:282-290).', owner: 'handoffs/active/conversation-stack.md', posture: cheap-screen-now, benefit: 'Tests whether a 2B end-to-end model matches the cascade STT on it/de/fr; direction lower WER better; must stay correct: same clips, same normaliser, vendor ESB WER not reused.', decision_rule: 'Advance to GPU only if paired 95 percent bootstrap WER difference vs whisper turbo is not above +1.0 pp in en and it; reject otherwise. Controls: frozen manifest = 40 FLEURS; baseline = frozen whisper large-v3-turbo; per-item records; holdout = FLEURS validation used for settings only; denominator = all 40 incl. failures; decision rule as stated.', reason: 'Italian and English both in LFM3 speech locales (D2 gate); cheap and correctness-class.'}
- {row: SPEECH-2, entries: [intake-2552, intake-2554, intake-2575], action: 'Add LFM3-Audio-2B/Omni-2B as a third challenger in the CS-8 G1/G3/G4 interlocutor bake-off: G1 en/it TTS intelligibility via llama-tts (note voice chat is English-only per card, so Italian only for TTS/ASR), G3 tool-call slot quality from speech, G4 TTFA/RTF/VRAM on MI210 BF16 vs Q4_K_M; measure first-audio latency after end of input through /v1/realtime with a fixed 60 clip set.', grounding: 'conversation-stack.md:282-290 (CS-8 gates G1-G4), D1/D2 at lines 56-58; D4 requires own llama.cpp-family runtime, which LFM3 uniquely already has.', owner: 'handoffs/active/conversation-stack.md', posture: monitor, benefit: 'Only candidate with a native llama.cpp runtime; but 2B size means tool-call accuracy is vendor 58.5 vs 72.4 for a larger peer, and voice chat is English-only, so it likely fails D2 as a full interlocutor.', decision_rule: 'Trigger: SPEECH-1 passes and the second MI210 bench window opens (CS-7). Then run G1->G4 with the cascade as baseline, six controls as CS-8; reject at first failed gate.', reason: 'Gated behind the existing bake-off ordering; do not pre-empt the Step-Audio/Qwen3-Omni runs.'}
- {row: SPEECH-3, entries: [intake-2575], action: 'Estimate and record forward-port cost: experimental branch from current production-consolidated-v10, merge/cherry-pick the 7 LFM3 audio PRs plus their upstream prerequisites (b10303..b11960 is 1657 builds; PR 31257 alone +2721/-160 over 31 files, 30629 +998, 31269 +1423); expected conflicts with AK champion in ggml-cpu/ggml-hip and server files; build CPU and HIP gfx90a variants in an isolated prefix, own LD_LIBRARY_PATH, verify_ggml_linkage.sh proof.', grounding: 'v10 tree /mnt/raid0/llm/llama.cpp has no lfm3 arch, no mtmd_audio_stream, no server-realtime (grep); CLAUDE.md experimental workflow steps 1-4.', owner: 'handoffs/active/conversation-stack.md', posture: cheap-screen-now, benefit: 'Unblocks SPEECH-1/2 and any future Voxtral-Realtime/realtime-API model; estimate 3-6 working days incl. conflict resolution and HIP build (estimate, not measured).', decision_rule: 'Stop if conflicts touch more than the audio/server surfaces or HIP build fails op-support; record costed op-gap list as with CS-8.STT4.', reason: 'Missing software is a build cost; also no production kernel change (new experimental tree only).'}
- {row: SPEECH-4, entries: [intake-2575], action: 'Reuse the upstream /v1/realtime (OpenAI-compatible) and Voxtral-Realtime support as a CS-20 backend interface option: write a realtime client adapter in the voice controller that speaks /v1/realtime beside the whisper :9000 / qwentts :9002 cascade.', grounding: 'src/voice/cascade.py Transcriber/SpeechSynthesizer protocols; src/voice/http_clients.py:28-31 hardcode WHISPER_BASE_URL 9000 and QWEN_TTS_BASE_URL 9002.', owner: 'handoffs/active/conversation-stack.md', posture: monitor, benefit: 'Single backend interface covers LFM3 and Voxtral realtime without per-model clients.', decision_rule: 'Trigger: SPEECH-3 produces a working realtime server; then 1-2 days adapter.', reason: 'No consumer until a runtime exists.'}
- {row: SPEECH-5, entries: [intake-2573], action: 'No new STT action. Hex confirms the transcribe.cpp Parakeet Unified streaming path (Vulkan GPU only). Parakeet streaming vs whisper.cpp is already a measured-pending candidate: CS-8.STT0 40/40 CPU==GPU identity done, transcribe.cpp CPU 40-clip run 37/40 identical, HIP build done; STT3 parity, STT4 residency and STT5 WER are open.', grounding: 'conversation-stack.md:670-684 (STT0-STT6) and lines 876-884 (native results).', owner: 'handoffs/active/conversation-stack.md', posture: knowledge-only, benefit: 'Avoids duplicate work.', decision_rule: 'n/a', reason: 'Already owned by CS-8.STT2-STT6.'}
- {row: SPEECH-6, entries: [intake-2573], action: 'Add Parakeet Unified English (streaming, lookahead variants) as a named arm check in CS-8.STT5 if not already present, noting hex pins fork rev 7045d1c0 (transcribe.cpp 0.4.1) while our build pins db678a03; record both pins.', grounding: 'conversation-stack.md CS-8.STT5 arm list names parakeet-unified-en as English-only challenger; hex Cargo.toml patch.crates-io pin.', owner: 'handoffs/active/conversation-stack.md', posture: knowledge-only, benefit: 'Pin provenance only.', decision_rule: 'n/a', reason: 'Arm already listed; no change needed.'}
- {row: SPEECH-7, entries: [intake-2564], action: 'Monitor Dessa for paper, weights or API; trigger = any released checkpoint or paper with benchmark numbers, then fold into the M8 full-duplex reference slot check (language gate D2 likely fails if English-only).', grounding: 'conversation-stack.md:646 (M8 full-duplex reference) and :89 (PersonaPlex/Moshi blocker note).', owner: 'handoffs/active/conversation-stack.md', posture: monitor, benefit: 'Possible audio-only full-duplex reference.', decision_rule: 'Trigger above; nothing to test today.', reason: 'No weights, paper or numbers; waitlist only.'}
dive_surfaced_sources:
- {source: 'https://github.com/ggml-org/llama.cpp/pull/31269 (server : add realtime conversation and transcription on /v1/realtime)', settles: 'exact scope of realtime conversation and live ASR path and tested platforms', bears_on: intake-2575, recommend: 'ingest-and-dive'}
- {source: 'https://github.com/ggml-org/llama.cpp/pull/30629 (mtmd: add mtmd_audio_stream + support voxtral-realtime)', settles: 'streaming audio infrastructure that is the prerequisite for the port; also gives a Voxtral Mini 4B Realtime path', bears_on: intake-2575, recommend: 'ingest-and-dive'}
artifact_audit: clean
```
