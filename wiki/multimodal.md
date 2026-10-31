# Multimodal

**Category**: `multimodal`
**Confidence**: mixed — this page carries three different classes of claim and they must not be read alike:
`upstream-published` (a paper's own numbers, on the paper's hardware), `projected-unmeasured` (an extrapolation
authored here and never run), and `locally-measured` (run on this host, with an artifact). A projected number
may never carry `verified`. Retagged 2026-07-31.
**Last compiled**: 2026-10-31 (operator wiki sweep, workspace-58): ERNIE typography capture READY (unrun), speech STT5/Ultra preparation controls, no scored results. Earlier: 2026-10-28 (workspace-58 wrap): Parakeet CPU canary, CS22.V0 parity negative, STT2 preparation. Earlier: 2026-10-28 (owner-scope full-wrap delta): CS22.V0 diagnostic negative and STT2 source-preparation boundaries. Earlier: 2026-10-24 (wrap-up sweep 26, operator /wrap-up evening): S-20 cold-vision fail-fast is source-complete (mock-tested, no live latency claim). Earlier: 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): a synthesized-tail turn-taking stratum exists and its accuracy re-score is owed. Earlier: 2026-10-24 (wrap-up sweep 9). Earlier: 2026-10-23 (wrap-up sweep 18, workspace-f8: Italian TTS normalizer and respelling on by default). Earlier: 2026-10-22 (wrap-up sweep 12, workspace-58: Italian TTS re-listen kit). Earlier: 2026-10-22 (wrap-up sweep 10: STT/VAD/speech-kernel program filed, scorer and custody code landed, s2s.cpp and ABI audits). Earlier: 2026-10-22 (wrap-up sweep 9: the Italian TTS listen check: intelligible). Earlier: 2026-10-21 (wrap-up sweep 5: speech placement moves to GPU card 2, CS-11 declined). Earlier: 2026-10-21 (wrap-up sweep 3 delta). Earlier: 2026-10-20 (wrap-up sweep 2: see the first Compiled Update). Earlier: 2026-10-20 (delta compile of 18 changed sources). Earlier: 2026-10-07 — reviewed source backlog. Previous compilation metadata: 2026-10-03 (wrap-up compile: Qwen3-VL-30B moved off the MI210 to cold CPU (device none, WARM, NUMA_HALF_A `-t 48`) because it no longer fits beside DFlash2 (66.75 > 62.00 GiB); S-18/S-19/S-20 filed; voice routing to :8083 is unimplemented in code); previous: 2026-09-25 (System One and evolutionary-agents intake); previous: 2026-09-24 (speech-vision compile: the operator ratified a speech-native interlocutor with the orchestrator as its one tool — INF-79 conversation-stack, D1–D12, a Step-Audio 2 mini vs Qwen3-Omni-30B-A3B bake-off with the cascade as baseline and fallback; speech moved out of INF-41; the whisper.cpp MI210 WER corrected 2.35% → 3.37%; KAME revival gate 3 met); earlier: 2026-09-24 (late, main-ak-seat: KVU-11b decided — the operator chose D, no change to the CPU speech layout, pending their own STT/TTS integration plan); earlier: 2026-09-24 (wrap-up #4, main-ak-seat: the live CPU speech layout collapses under a generating CPU LLM, both ways); earlier: 2026-09-24 (evening wrap-up compile, main-ak-seat: production STT/TTS measured on the CPU alone — STT RTF 0.12–0.20 at 24–32 threads, TTS RTF 0.55–0.60 at ≥16 threads, real time together on separate cores, but next to a generating `-t 96` frontdoor TTS RTF goes to 7.8–9.4 and the frontdoor from 43 to 0.3 tok/s; whisper layout collapse and a shim-only TTS thread control; ~2 s CPU ASR floor from 30 s padding; recommendation stay on GPU, options A/B/C an operator decision (OP-56 / RTG-57 KVU-11), the SMT-sibling follow-up uncommitted (KVU-11a)); earlier: 2026-09-24 (wrap-up compile: S-11/S-12/S-13 — the speech stack is registered under MRG-1 and the task's own pin and GGUF pair were both wrong, the fork stays pinned with two guards; S-11a — folding 4.68 GiB of aux-service VRAM into the capacity gate takes the lineup margin 5.85 to 1.17 GiB, PREPARED behind an operator signature and a stale contention matrix; S-15 confirmed live in a running process); earlier: 2026-09-23 (later: S-15 confirmed LIVE — API reloaded 20:31Z, pid `2815541`, config reads 1024); earlier: 2026-09-23 (evening wrap-up compile: S-15 landed — default_vl_max_tokens 512 to 1024, live only at the next API reload; the old 128-token cap was a scoring artifact (3 parse failures for the incumbent vs 41 and 50 for the Qwen3-VL arms), and its landing satisfies the dependency S-16 was sequenced behind); earlier: 2026-09-23 (incremental: Qwen-Image-2.1 weights staged for an ERNIE comparison, unrun; vision role clarified); earlier: 2026-09-17 (incremental: the ROCm f32 fix and every recipe §5 variant fail to clear the MI210 ≥1024² ERNIE white-image defect; local vision-reader inventory; ERNIE-ROCM-NEXT filed outside the DiT linears); earlier: 2026-08-25 (the document-specialist VLM lane: PaddleOCR-VL's off-label (the outstanding TTS stack-lifecycle wiring task was closed by **finding it already done ten days earlier** — correct output was zero new code, and live runtime remains explicitly unverified; earlier 2026-07-31 note: session 3: MMMU val settles the vision role on Qwen3-VL-30B-A3B Q4_K_M and retires MiniCPM-o-4.5 as a candidate entirely — deprecated, weights deleted; whisper.cpp large-v3-turbo on MI210 settles STT and Qwen3-ASR is dropped; the post-ARGSORT-fix TTS numbers supersede the pre-fix reading two sections below; earlier 2026-07-26 note: adds bounded M-1 observation and M-2 pinned-interface closure; prior promotion runbook and demand gate retained)
`0.0`/`0.058` TEDS figures are formally voided and a three-stage instrument with a supported (added 2026-07-24 the vision_escalation MiniCPM-o promotion runbook and the worker_vision quantitative trigger gate; 2026-07-17 MiniCPM-o/frontdoor service-matrix activation evidence, Qwen3-VL-30B escalation defect mitigation, and PaddleOCR-VL document-specialist checkpoint; 2026-06-22 vision-pipeline live-server registration + the TTS path-elimination matrix; 2026-06-05 LocateAnything/Gemma 4 benchmark-first update; 2026-06-21 Kimi-K2.7-Code MoonViT / UniRL intake merge) (2026-08-30: MiniMax-H3 lands as the page's first video-generation candidate — EVL-32: 33B dense H3-Omni-Transformer + Qwen3-VL-32B encoder, Ref2VA/FL2VA variants, 768p local / 2K API-only, 24 FPS 32 kHz stereo audio, a 56-model community quantization landscape, NSFW-capability finetune evidence, Ref2VA + beta4 INT8 ~165 GB deployment path, and an Excluded-Territories license; operator scope decision is the first gate before any download)
**Sources**: 54 native document references (source review 2026-10-07); sweep 2 (2026-10-20) added sources listed in the first Compiled Update

## Compiled Update — 2026-10-28 (workspace-58 wrap): Parakeet CPU canary accepted for one clip; CS22.V0 exact parity is negative

- **CS-8.STT0 Parakeet CPU canary (one clip, bounded)**: rc=0, native verifier replay emitted `verified canary`; 23 same-PID samples covered 4.47 s of 4.67 s on affinity 24-25; CPU weight buffer 1,255,643,680 bytes; per-PID VRAM stayed zero. Not a quality or throughput claim. The CPU v2 patch proposal stays pending install; GPU v2 has no inference result (preflight refused as expected).
- **Parakeet reference weights acquired** (`ggml-org/parakeet-GGUF`, 1,255,897,319 bytes, SHA-256 `833bffc9...`); receipt and size checked, no fresh full-file hash.
- **CS22.V0 parity NEGATIVE (diagnostic only)**: exact stop/segment parity false for all 3 candidates: GGUF/JIT 946/1118 and whisper 956/1113 mismatching cells of 1344; 2688/2688 native hashes, 0 mismatches or execution errors. Enrollment published 14m25s after completion, so no retroactive warrant.
- **INF-79 FLEURS selection** rc0: 40 records (first ten test records for en_us, de_de, fr_fr, it_it) with hashes and a 16 kHz mono s16le conversion policy; selection only, no STT inference.
- **STT2 converted-asset acquisition and 40-clip smoke launchers are source-prepared only** (no acquisition, no inference); all STT qualification parents remain open.

### Source References (2026-10-28 workspace-58 wrap)

- [handoffs/active/conversation-stack.md](../handoffs/active/conversation-stack.md) — CS-8.STT0, CS22.V0, STT2 preparation
- [progress/2026-10/2026-10-28-codex-refactor-01a16fc3.md](../progress/2026-10/2026-10-28-codex-refactor-01a16fc3.md) — launcher preparation
- [progress/2026-10/2026-10-28-workspace-58.md](../progress/2026-10/2026-10-28-workspace-58.md) — session record

## Compiled Update — 2026-10-24 (wrap-up sweep 26, operator /wrap-up evening): S-20 cold-vision requests now fail fast in source

**Confidence: verified** for the source and mocked tests; the live latency effect is **unmeasured**.

- **Root cause.** `_handle_vision_request` awaited optional OCR before trying the selected VL server, so in explicit server-only mode a cold endpoint failed only after OCR (the original live observation was 27.9 s); the two vision roles can also resolve to one server URL.
- **Fix.** A 250 ms shared-deadline TCP-connect preflight, only for `ORCHESTRATOR_VISION_VL_BACKEND=server`, over the selected endpoints (respecting `force_server`, aliases deduplicated), refuses through the existing `All vision paths failed` error before OCR, structured analysis or legacy HTTP fallback when none connects. Healthy server-only requests keep OCR and VL; other backends do not preflight.
- **Evidence.** Orchestrator source 846783d10, promoted to main 84f6f6f1 (two files only); focused suite 16 passed, 40 deselected, 1.31 s, JUnit gate with all seven new test IDs. Mock endpoints only. The 84f6f6f1 API-only reload served S-20 at 18:48Z, but no live cold-path request was timed.

Sources: [multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) (S-20) · [cold_vision_failfast](../progress/2026-10/2026-10-24-cold_vision_failfast.md) · [2026-10-24 workspace-58 progress](../progress/2026-10/2026-10-24-workspace-58.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): a synthesized-tail turn-taking stratum exists and its accuracy re-score is owed

**Confidence: verified** for the build (hash-exact verify); no ASR or accuracy number exists yet.

- **Tail stratum `turn-taking-cs45-1-tail-v1`:** 82 CUT_IC/CUT_WAIT parent pairs x tails {0.3, 0.6, 1.0, 3.0, 4.0} s = 410 pairs / 820 clips, each bound to its PCM-SHA-256 and its v2 parent's passing gate; `verify` re-assembles all 820 hash-exact and v2 `tt_verify.py` still passes. The room tone is synthesized pink noise at -55 dBFS (no recorded room tone exists), so the stratum is marked synthesized and ranking-only with `advance_eligible_strata = ["human_recorded"]`. The natural-speech control is DECLARED-EMPTY (CS-4 set 5 unrecorded, 0 rows). Landed on research main; audio (386 MB) stays outside git.
- **Not done:** the CS-47 accuracy re-score (820 clips x 6 arms; scripts hardcode CS-47 paths), so the box stays open.

Sources: [conversation-stack](../handoffs/active/conversation-stack.md).
## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): a tail-latency stratum for turn-taking

- **CS-4.5 tail stratum built.** 82 CUT_IC/CUT_WAIT parent pairs x tails {0.3, 0.6, 1.0, 3.0, 4.0} s give 410 pairs / 820 clips, each bound to its PCM SHA-256 and its v2 parent's passing gate; reassembly is hash-exact and the v2 verifier still passes. The stratum is synthesized and ranking-only: `advance_eligible_strata` stays `human_recorded`, so it cannot advance a gate.
- **Still owed:** the re-score leg and the natural control; audio (386 MB) lives outside git.

Sources: [Conversation stack](../handoffs/active/conversation-stack.md)

## Compiled Update — 2026-10-23 (wrap-up sweep 18, workspace-f8): the Italian TTS normalizer and respelling are on by default

**Confidence: locally-measured** for the operator re-listen (15 clips, human ear); no live consumer exists yet.

- **CS-8.L4 decision.** After re-listening 15 `s5-cs8l-retts` clips (11 better, 2 same, 2 worse than the originals, all intelligible; respelling 5/5 better, normalizer 6/2/2), the operator enabled both. Orchestrator `99d00198` turns on feature flags `tts_it_normalize` and `tts_it_respell` for Italian only, with kill switches `ORCHESTRATOR_TTS_IT_NORMALIZE=0` / `ORCHESTRATOR_TTS_IT_RESPELL=0` ([conversation-stack](../handoffs/active/conversation-stack.md)).
- **Scope.** "Live" means the default of `CascadeBackend`, the only speech path, which no production process constructs yet. Users first hear it when CS-21 wires the cascade, and CS-21 must pass a turn language, or the normalizer is a no-op. The respell table is a 5-word lexicon, not a stress model.
- **Follow-ups.** CS-8.L4a: a spelled-out year ("duemilasei") was heard as "zei"; test over 5+ seeds and narrow the year rule if needed. CS-8.L4b: pauses after accent-marked respellings and inside "pi acca". CS-8.L4c: two prosody notes, monitored and not filed as tasks.

### Source References (2026-10-23 wrap-up sweep 18, workspace-f8)

- [conversation-stack](../handoffs/active/conversation-stack.md) (CS-8.L4, L4a-c)
- [3c4ca599 progress, 2026-10-23](../progress/2026-10/2026-10-23-3c4ca599.md)
- [workspace-f8 progress, 2026-10-23 midday](../progress/2026-10/2026-10-23-workspace-f8.md)


## Compiled Update — 2026-10-22 (wrap-up sweep 10): the STT, VAD and speech-kernel program is filed, its scorer and custody code exist, and two audits found conflicts and corrections before any run

**Confidence: verified** for the code that landed, the documents filed and the operator decisions; **inferred** for every STT, VAD, turn-taking and lexicon claim (no model was run, no arm has a number). The two operator-side decisions and the listen result are verified; nothing in the program has advanced an arm.

- **The Bark intake became a 27-task program with durable triggers.** Stage 4 of `intake-underdog-bark-20261021` filed (plan sha256 recorded in `.research-session.json`) five phases in `handoffs/active/conversation-stack.md`: P1 STT runner gate and bake-off (CS-8.STT0..STT6), P2 scoring integrity (CS-2.STT1, CS-4.STT1/STT2, CS-8.STT7), P3 VAD/turn-taking/LID/CPU degraded STT (CS-22.V0/V1/A1/L1/T1/D1, CS-45.2, CS-26.LID1/F1), P4 lexicon boosting (CS-8.LEX0..LEX2), P5 speech-kernel verification (CS-43.1..43.3, CS-8.G1B). Twelve durable triggers (M12-M23) and four knowledge rows (K4-K7) hold what is not a task. Rule that governs all of it: vendor cards, leaderboards, hosted boards, author timings and third-party ports are literature-class and rank nothing; every arm is measured by our own harness on our own clips. The frozen `production-speech-v1` trees, the speech champions and v10 are never edited by these tasks. The v11 speech pull-list task was renamed CH-18.d after an ID collision with a different CH-18.c.
- **Five ggml generations now coexist on paper.** Candidate runners add ggml 0.13.0 (parakeet.cpp), 0.25.1 (NeMo-Speech.cpp), 0.26.0 (transcribe.cpp, CrispASR fork) and 0.27.0 (s2s.cpp, upstream qwentts) beside v10 0.16.0, qwentts 0.17.0 and whisper 0.18.0, so every launcher sets its own `LD_LIBRARY_PATH` and proves linkage. CS-8.STT0 is the zero-build entry: the frozen whisper tree already ships upstream Parakeet support (`parakeet-cli`, built with `GGML_HIP=ON`, gfx90a), used read-only. s2s.cpp serialises Parakeet behind one mutex and runs VAD on one CPU thread, so the controller must not assume batched STT.
- **The STT scorer exists and its WER is still only an observation.** Research `d2e3283be` (`scripts/speech/stt_bakeoff/`; 203 tests, file-scoped) implements `stt_norm/v1` exactly as P-STT-1 section 1.3, a labelled `v2` CANDIDATE column (it/de/fr numerals, elision, a counted `de_compound_split_join` class), a secondary filler scorer, sealed-split custody, a manifest validator, a fitting screen (accept-ref with a Wilson 95% interval, label strictly above 0.10), a boosting guard (a TDT model with `speech_contexts` is refused as `NO_RUNNER_PATH`, because NeMo-Speech.cpp drops them silently) and a lexicon builder/scorer. Because `MEASUREMENT.md` says P-STT-1 WER is not a claim without its owning release protocol, every STT row projects Judged/Located until CS-2 ratifies an amendment. `corpus_id` binds the corpus manifest (identical across arms), not an arm's raw manifest; an unsealed confirmation record is refused by the belief writer.
- **CS-2 amendment candidates are text, not authority.** `docs/reference/speech/cs2-stt-amendment-candidates.md` holds seven candidate items with the current text, proposed wording and rationale: `stt_norm/v2` (closed per-language numeral tables; apostrophe kept; German compound split/join not forgiven but counted), two new properties (REFERENCE-BLIND normaliser, PINNED DEPENDENCIES: an unpinned numeral library makes the instrument a function of host state), a filler policy (DP-B; default option b: fillers are ordinary tokens, a counted list only in a labelled secondary scorer), and a longer WER record-field list (language mode, segmentation, unk policy). Nothing edits `MEASUREMENT.md` or `measurement/protocols/`.
- **Operator decisions that unblock the confirmation stratum.** DP-A: private STT confirmation strata live in a separate private repo (public repos keep hash manifests only; custody wired in research `eb916e168`; 191 tests pass in `stt_bakeoff`, 7 new). DP-C: a single labelled rater for now, extendable through a `reference_version` bump plus an `edit_log` entry. The CS-4 `human_recorded` stratum is still empty, so CS-8.STT6 cannot run.
- **s2s.cpp turn-state diff (CS-22.D1, zero compute).** Pinned s2s.cpp `e620fab214cb` (MIT) has a 3-state turn machine with revision counter, an 800 ms `reopen_grace_ms`, turn_threshold 0.5 on Smart Turn v3.2 and a recognizer/responder thread split; its defaults become named starting rows for the CS-22.V1 and CS-47 sweeps, not adopted values. Conflicts with our CS-18/CS-23 semantics: one unordered atomic cancel flag versus ordered cancel hooks, silent drop of an unheard revision versus explicit cancel, unconditional barge-in cancel versus the CS-18 retain choice, and a 384 ms barge-in default calibrated against its own echo canceller (re-sweep, do not adopt).
- **CS-43.3 launcher/ABI audit corrected its own task text.** The frozen qwentts is `QT_ABI_VERSION 4`; upstream `01b6127` (which removes `GGML_BACKEND` in favour of `--device`) bumps the ABI from 5 to 6, not "to 5", so an upstream-based build jumps 4 to 6. Thirteen hit groups across the three repos; the live ones are the orchestrator `launch_manifest.yaml` :9002 CPU service env and its test, and a research render pipeline, all correct for the frozen v1 binary and to be changed only with an upstream-based candidate. The whisper tree has no such reference. `speech-v2-manifest.md` now points at the audit.
- **Italian TTS follow-ups.** The 60-clip listen kit shipped at 16 kHz (the 24 kHz originals exceed the 20 MB budget and no audio encoder exists on the host); the second-ASR cross-check was NOT delivered, because a whisper-cli large-v3 CPU run started without a calendar grant was stopped by the coordinator and its partial output deleted. The Italian number/unit and "pH" normalizer is built (orchestrator `df9d2eca`, research `95550d294`), live path default-off pending the operator, with a re-synthesis filler armed to re-listen using a respelling probe; stress, proper-noun and accent notes are filed as monitor-only.

### Source References (2026-10-22 wrap-up sweep 10)

- [handoffs/active/conversation-stack.md](../handoffs/active/conversation-stack.md) — the filed STT/VAD/lexicon/kernel program, DP-A/DP-C, triggers M12-M23, knowledge K4-K7
- [docs/reference/speech/cs2-stt-amendment-candidates.md](../docs/reference/speech/cs2-stt-amendment-candidates.md) — seven CANDIDATE Annex S items
- [docs/reference/speech/s2s-cpp-turn-state-diff.md](../docs/reference/speech/s2s-cpp-turn-state-diff.md) — turn-machine defaults and conflicts
- [docs/reference/speech/cs43-3-ggml-backend-audit.md](../docs/reference/speech/cs43-3-ggml-backend-audit.md) — GGML_BACKEND/ABI audit and corrections
- [docs/reference/kernel-manifests/speech-v2-manifest.md](../docs/reference/kernel-manifests/speech-v2-manifest.md) — pointer to the audit
- [progress/2026-10/2026-10-22-bark-p1p2p4p6-code.md](../progress/2026-10/2026-10-22-bark-p1p2p4p6-code.md) — scorer, custody and adapter code, findings
- [progress/2026-10/2026-10-22-bark-stage4.md](../progress/2026-10/2026-10-22-bark-stage4.md) — Stage-4 filing and the CH-18.d ID collision
- [progress/2026-10/2026-10-22-speech-dpa-dpc-listenkit.md](../progress/2026-10/2026-10-22-speech-dpa-dpc-listenkit.md) — listen kit, private custody repo

## Compiled Update — 2026-10-22 (wrap-up sweep 11): the Italian normalizer is eval-only until the operator enables it live

**Confidence: verified** for the default-off state and the task filing; the re-listen has not run.

- **Ticked is not live.** CS-8.L1/L2 (numbers, units, "pH") are done in code, but the normalizer runs only on the eval/test path; the live speech path keeps it default-off pending the operator, so live conversations still mispronounce these. CS-8.L4 (conversation-stack) carries the enable step, gated on the operator's re-listen of the `s5-cs8l-retts` clips and an explicit on/off decision.

### Source References (2026-10-22 wrap-up sweep 11)

- [handoffs/active/conversation-stack.md](../handoffs/active/conversation-stack.md) — CS-8.L4

## Compiled Update — 2026-10-22 (wrap-up sweep 9): the Italian TTS listen check: intelligible, with number, unit and pH errors a normalizer can fix

**Confidence: verified** for the ratings and the counts; **inferred** for the benefit of the normalizer, because the re-synthesis (`s5-cs8l-retts`, slotted about 22:00Z) has not run.

- **Listen check (CS-8.L).** The operator rated all 60 cascade G1 Italian clips: 60/60 intelligible, naturalness mean 4.62 (median 5; 47 fives, 5 fours, 6 threes, 2 twos), 11 clips with notes. Errors by category: numbers and units 3 clips, pH read as "hache" 2, lexical stress 3, proper nouns 2, accent 1. Italian is not rejected, so the M17 trigger does not fire.
- **ASR cannot replace the ear.** Forced WER of the low-naturalness clips (n=8) is 0.039 against 0.024 for the rest (n=52); Spearman -0.14, permutation p=0.21; 5 of the 8 low clips have WER 0.
- **Text path.** No normalization existed between the cascade or LLM text and qwentts, which only strips the BOM and validates UTF-8 before BPE. The new Italian-only normalizer (orchestrator `df9d2eca`; 126 tests, voice suites 183/183) changes 10 of the 60 sentences, including all 5 operator-flagged normalizable clips, and is default-off and byte-identical when off. The cardinals agree with the STT-side table on all 101 values.
- **No stress hook.** qwentts has no lexicon or stress control; `instructions` is rejected for the Base model and `--lang` is one codec token. Orthographic respelling is the only lever, so the re-synthesis carries it as an opt-in probe (the operator's choice).
- **Belief kernel.** A `speech-listen-rating` adapter projects the aggregate; the WER cross-check is not projected because it is not independent of the same clips.

### Source References (2026-10-22 wrap-up sweep 9)

- [progress/2026-10/2026-10-22-cs8l-ratings.md](../progress/2026-10/2026-10-22-cs8l-ratings.md)
- [progress/2026-10/2026-10-22-it-tts-normalizer.md](../progress/2026-10/2026-10-22-it-tts-normalizer.md)
- [docs/reference/speech/tts-italian-text-prep.md](../docs/reference/speech/tts-italian-text-prep.md)
- [progress/2026-10/2026-10-22-vb-speech-listen.md](../progress/2026-10/2026-10-22-vb-speech-listen.md)

## Compiled Update — 2026-10-20 (wrap-up sweep 2): multimodal — the turn-taking instruments exist, and the qwen-tts "thread collapse" is a core-sharing effect

**Confidence: verified** for harness conformance, parity and the thread-scaling measurements (each scoped below); no turn-taking policy result exists, and CS-45's human-recorded stratum is empty, so no arm can yet advance.

**Measurement contract (frozen 2026-10-20).** The turn-taking measurand note names every quantity with its direction and denominator. Rules that prevent misreadings: direction is part of the name; the denominator is every manifest item (crash, timeout, never-fire = miss); synthesized evidence may reject or rank an arm but only human-recorded evidence may advance one; patched scorers mark a measurement-era boundary and are not comparable to published numbers; published rows are reference rows only; no cloud judge. Scenario flips matter: turn-over rate is better high for smooth turn-taking and interruption but better low for pauses and backchannel, and a HIGH stop time is correct for backchannel, off-talk and background speech. The note does not amend Annex S, whose amendment boundary stays human-only.

**Status of the program (see [conversation-stack](../handoffs/active/conversation-stack.md)).**
- *CS-45 (corpus, labels, pins):* built; 105 synthesized pairs (62 incomplete-cut, 13 wait, 30 backchannel-context), each from ONE spliced recording so pairs are acoustically matched, plus 25 reserve pairs that count only via a recorded review backfill. Verification passes (12 checks; 60 tests incl. mutation refusals). The checkbox stays open for the human review of a 20-pair sample, and the later CS-46 close-out notes v1 is being rebuilt for label and splice defects, so downstream work must use the rebuilt corpus. The pinned instrument set is one Silero VAD, Full-Duplex-Bench and TurnBench commits, and the production whisper.cpp as the word-timestamp ASR; five scorer substitutions are recorded as era changes.
- *CS-46 (Parakeet EOU arm, ticked):* the community ONNX encoder is stateless and cannot run the cache-aware loop, so cache-aware encoders were self-exported. Parity versus the NeMo CPU streaming run is step-exact on 20/20 clips (80 and 160 ms chunks, reset none/full). Binding consequences: the int8 decoder_joint is excluded from CS-47 unless re-validated (it emits a false end-of-utterance on a backchannel clip); the Rust port's mel filterbank differs from NeMo's (max diff 14.3 versus 2.3e-4 for the Slaney reimplementation).
- *CS-48 (barge-in harness, ticked):* a deterministic stimulus player and scorers over the unmodified voice controller; scripted-agent stop/resume instants recovered exactly on a virtual clock, mutations refused with named reasons, replays bit-identical (30 tests). Both merge-gap readings of Full-Duplex-Bench are reported because its code and comments disagree.
- *CS-47 and CS-49 (the actual bake-offs)* remain open; CS-49 also needs live services and an inference-owning window.

**qwen-tts thread scaling (frozen speech kernel, nothing changed).** On a quiet CPU region 8 threads is about 4x FASTER than 1 (38 versus 94 ms/frame pinned; 24 versus 96 free), so the earlier 13x slowdown at 8 threads is NOT a thread-count property. Its trigger is core sharing: the ggml barrier is a pure pause-spin with no yield, qwen-tts builds a disposable pool per graph, so one descheduled thread stalls all (8 threads plus 8 spinners: ~9.8 s/frame; perf shows nearly all samples spinning). OpenMP knobs are inapplicable (no OpenMP in the library). Guidance: N threads only on cores nothing else runs on; otherwise one thread per process; do not pin tightly. A persistent pool with poll 0 would be the real fix and needs a new kernel version. Not tested: the exact original background load.

**Vision and fallback.** Speech work lives in the conversation stack; the vision handoff keeps vision only. The server-only vision policy now refuses without POSTing the legacy endpoint (synthetic controls; the cold-server timing diagnosis in S-20 stays open). The vision embedder screens (EmbeddingGemma 2, CLIP) still have nothing to screen: the collections were empty on 2026-10-20.

### Source References (2026-10-20 sweep 2, multimodal)

- [Turn-taking measurands](../docs/reference/speech/turn-taking-measurands.md) — the frozen quantity definitions and reading rules.
- [Conversation stack](../handoffs/active/conversation-stack.md) — CS-45/46/47/48/49 notes, qwen-tts thread follow-up, durable triggers M8-M11.
- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — speech moved out; server-only fallback; embedder trigger.

## Latest source review — 2026-10-07

## Incremental synthesis — 2026-10-07: voice source preparation preserves the incumbent

**Confidence: verified** for accepted wrapper/fallback source behavior and synthetic controls; speech quality, routing calibration, latency and real-service acceptance remain unmeasured in these slices.

Conversation shadow preparation implements only the provisional LOCAL/ORCH binary catalog beside the unchanged incumbent decision. LOCAL covers social/backchannel/control; ORCH covers factual/reasoning/code/memory/current-events. The actual CS-4 annotation schema still needs verification before controller integration. The wrapper uses explicit JSON mode and the existing default-off, sink-configured, four-pending-item bound. Invalid catalogs or submission failures fail open. Confidence is telemetry, not a routing threshold; all-three-arm corpus comparison, precision/recall and actual call cost remain required before policy selection.

The thin SSE voice-turn design and session-keyed transcript/summary persistence source are now accepted, the latter with original 31/31 SQLite synthetic controls. The persistence contract retains every unseen message with a monotonic summary frontier and session lease fences, preserving the prior summary on failure. The mockable controller must maintain one active turn, healthy language-compatible fallback and dependency-ordered cancellation. The streaming bridge must use real request-scoped backend chunks and cancellation, avoid duplicate character replay and preserve truthful terminal/persistence state. The request-scoped streaming bridge and transport-neutral controller source are now accepted with original 276/276 synthetic controls and complete 463-input/475-member custody; the failed 269/276 predecessor remains preserved. Concrete HTTP/audio transport and the WAV harness remain separate source work. Explicit display-only or verbatim/protected-value payloads and owner-pinned typed retain/cancel controls are prospectively enrolled proposals: strict modes buffer before exact-text validation, while default chunk streaming remains. They do not implement phrase interpretation or prove audio fidelity. This acceptance establishes neither real-model/audio behavior nor first-token, 50 ms or cancellation-latency performance.

The accepted vision fallback correction is narrower: explicit server-only policy refuses through the existing error contract after configured endpoints fail, instead of POSTing the legacy vision endpoint. Healthy-server and default/auto/CLI behavior remain as before. Five hosted fake-boundary controls establish this route contract; parent S-20 still requires cold-server timing diagnosis and live acceptance.

### Source References

- [Conversation shadow preparation](../docs/reference/conversation-shadow-preparation.md) — provisional labels, failure behavior and limits.
- [Conversation stack](../handoffs/active/conversation-stack.md) — CS-24 parent and proposed store/controller/stream scopes.
- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — accepted server-only fallback and open S-20 parent.

## Source References

- [Turn-taking measurands](../docs/reference/speech/turn-taking-measurands.md) — sweep 2 (2026-10-20)
- [Conversation stack](../handoffs/active/conversation-stack.md) — sweep 2 (2026-10-20)
- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — sweep 2 (2026-10-20)
- [Conversation shadow preparation](../docs/reference/conversation-shadow-preparation.md)
- [Conversation stack](../handoffs/active/conversation-stack.md)
- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md)

## Speech-native interlocutor program (2026-09-24)

**Confidence:** `verified` for the operator decisions and for host and code facts checked first-hand; `external` for
candidate-model facts (model cards, repos, issue trackers, checked against primary sources the same day, **not run
here**); `inferred` for the training-feasibility estimate. No candidate interlocutor has been run on this host.

**Speech has one home now.** All STT, TTS and voice work moved from `multimodal-pipeline.md` (INF-41, which keeps
vision) to [`conversation-stack.md`](../handoffs/active/conversation-stack.md) (INF-79). The speech sections further
down this page are history; new speech facts belong here. The option-D decision in the next section is an input to
this program, not a rival plan.

**The ratified vision.** *A permanently resident speech-native interlocutor hears, interprets and speaks. It has one
external tool, the orchestrator, which supplies the cognition. Preserve speech-native state locally; export only the
cognitive problem.* The interlocutor owns hearing, paralinguistics, timing, turn-taking, backchannel and delivery. The
orchestrator owns memory, reasoning, retrieval, code and tools, and returns substance, never the conversation. A
model-agnostic voice controller in `epyc-orchestrator` sits between them, so the interlocutor is a backend, not an
architecture. The input was the operator's own design report, preserved verbatim with a correction banner:
[`speech-native-interlocutor-operator-draft-20260924.md`](../docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md).

**Decisions that shape everything downstream (D1–D12):**
- **A bake-off picks the interlocutor (D1):** Step-Audio 2 mini leads, Qwen3-Omni-30B-A3B challenges (a ~Q4 Thinker
  is acceptable, D1a — the ceiling comes from the orchestrator). Gates in order: language, then paralinguistics, then
  routing and exact-value fidelity, then serving (CS-8).
- **Language is the first gate (D2):** English is mandatory, Italian strongly wanted, German and French desirable.
- **The whisper + qwentts cascade stays (D8)** as the baseline and the permanent fallback. It already speaks
  en/it/de/fr (qwentts supports 10 languages), so per-language fallback keeps D2 satisfiable whichever model wins.
- **Runtime and placement (D3, D4):** production runs on our own llama.cpp-family port, promoted as a new kernel
  version. vLLM and PyTorch are measurement instruments only. Placement is decided by measurement; the operator leans
  GPU.
- **Routing (D5):** every substantive turn goes to the orchestrator; local answers are social, backchannel, control.
- **Contract, client and hardware (D6, D7, D9):** a dedicated streaming voice-turn contract. The client is deferred,
  but the end state is remote (laptop or phone), so nothing may assume the microphone is on the host. A **second
  MI210 arrives within about a month**, planned for Qwen3.6-35B-A3B and possibly the speech plane, and serves as the
  bake-off bench first.
- **Latency hiding is a ladder (D11):** native spoken preamble, then streamed answer, then *untrained* mid-generation
  injection. KAME-style front-end training is a gated research track (CS-42).

**Candidate facts** (`external`; primary sources checked 2026-09-24):
- **Step-Audio 2 mini emits 1 text token per 4 audio tokens (TA4) at 25 Hz**, so it needs **about 31.25 AR steps per
  second of speech**, not 25.
- Its audio input costs **12.5 tokens/s**, and the official pattern re-feeds past turns, so its **16k context fills in
  about 9–12 minutes**. Context management is a first-phase requirement.
- **A Step tool call comes only after `<tts_end>`**, so a tool use takes two generations. There are **no published
  tool-call numbers for mini** (only for the full Step-Audio 2), and upstream issue #27 reports poor slot filling.
- **Neither candidate has a runtime on our hardware.** Step has no llama.cpp support, `token2wav.py` hard-codes
  `.cuda()`, and its ROCm report (#86) shows only a server starting.
- **Qwen3-Omni:** our llama.cpp handles Thinker audio input (with an open upstream bug, #27136), but there is no
  Talker or Code2Wav port. Its speech output covers **en, zh, fr, de, ru, it, es, pt, ja, ko**; Step shows no evidence
  for it/de/fr.
- **The Qwen3-Omni Talker voices whatever text it is given**, so orchestrator text could be spoken directly.

**Corrections to the operator draft**, recorded so nobody re-imports them (`verified`):
- There is **one MI210 today**, with 0.9–1.9 GiB free.
- Decode-usable CPU bandwidth is **about 150–220 GB/s, not 460**, so a Q8 Step decoder at 31.25 steps/s (~250 GB/s)
  is unrealistic on the CPU.
- The orchestrator has **no voice path, no real streaming** (`/v1` replays a finished answer character by character)
  and **no conversation store**.
- STITCH (arXiv 2507.15375) is Microsoft/NTU work, not Kyutai's.

**Training is feasible; data realism is the risk** (`inferred`, unmeasured). A KAME-style oracle fine-tune of an 8B
front-end fits one MI210 as LoRA. A full fine-tune needs both MI210s with ZeRO-3/FSDP or CPU optimizer offload. One
epoch (~85M tokens) comes to about 15–20 h per GPU. The binding risk is synthetic training speech eroding the
paralinguistic perception the interlocutor was chosen for.

**Carried-over and superseded items:**
- From INF-41: S-14 (the argsort upstream) becomes CS-43 and the Qwen-Audio-3.0 open-weights watch becomes CS-44
  (intake-826#record). The Qwen3-Omni quarterly watch is superseded (it is now a candidate), and the stale Path-C
  boxes are closed as superseded by qwentts.cpp.
- KVU-11b's contention measurements and acceptance (STT RTF < 0.5, TTS first packet < 1 s) become CS-11/CS-12
  ([`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md)). The near-term item is CS-12,
  which moves the cascade onto the second MI210 and clears the CPU collapse without partitioning the CPU LLMs.

### Source References (speech-native interlocutor program)

- [`conversation-stack.md`](../handoffs/active/conversation-stack.md) — vision, D1–D12, *Facts*, draft corrections, CS-1…CS-44.
- [Operator draft](../docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md) — the input document.
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — speech-moved banner, S-14/monitor hook moved, Path-C and Qwen3-Omni watch superseded.
- [`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md) — KVU-11b cross-reference; [session record](../progress/2026-09/2026-09-24-speech-vision.md).
- [Annex S](../measurement/protocols/speech.md) — receipt-defect note and Appendix S-A (the WER correction in the 2026-07-31 session-3 section).
- External, not yet ingested (CS-1, intake pending): Step-Audio 2 (arXiv 2507.16632,
  <https://huggingface.co/stepfun-ai/Step-Audio-2-mini>), Qwen3-Omni (arXiv 2509.17765,
  <https://huggingface.co/Qwen/Qwen3-Omni-30B-A3B-Instruct>), STITCH (arXiv 2507.15375), SHANKS (arXiv 2510.06917).

## Compiled Update — 2026-09-24 (late): the CPU speech contention is decided — D, no change

**Confidence: verified** — an operator decision, recorded first-hand (KVU-11b, root `54772ad7`).

- **The operator chose option D on 2026-09-24 (~20:00Z): no change to the CPU speech layout.** STT stays on
  cores 0-23 and TTS on 24-39, both at 0 VRAM, next to the `-t 96` CPU LLM roles on 0-95.
- **Why:** the operator is drafting a larger STT/TTS integration plan that supersedes options A-C (partition the CPU
  LLM roles and return TTS to the GPU; partition only; a decode throttle). Those options and their measurements are
  input to that plan, not pending work. Do not re-propose partitioning or a throttle as standalone work.
  *(Later the same day the plan landed as INF-79; see the section above.)*
- **The hazard is known and accepted:** a speech request that arrives while :8070 or :8074 generates wrecks both the
  speech and the LLM (numbers in the section below).
- The A/B acceptance criterion (STT RTF < 0.5 and TTS first packet < 1 s with a CPU LLM generating, LLM decode loss
  recorded) is kept for the operator's plan.
- Numbers, options and GPU-side constraints: [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md).

### Source References (2026-09-24 late)

- [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md) — header decision line, §5.
- [`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md) — KVU-11b (decision record), *Reporting*.
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — S-11a cross-reference.
- [`CURRENT-CAMPAIGN.md`](../handoffs/active/CURRENT-CAMPAIGN.md) — the accepted-hazard line.

## Compiled Update — 2026-09-24 (wrap-up #4): speech is on the CPU now, and a generating `-t 96` LLM role breaks it — and is broken by it

**Claim class: `locally-measured`** (research `artifacts/speech_cpu_realtime_20260924/README.md` addendum 3,
`6afc7eed`; n = 1–2 per cell). Durable reference for any STT/TTS or voice-turn plan: [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md).

- **Live layout (OP-54/OP-56, orch `0a564a1f`):** STT :9000 whisper.cpp `production-speech-v1` on CPU `-t 24
  -ng`, cores 0-23; TTS :9002 qwentts.cpp `production-speech-v1` on cores 24-39 with 16 threads via the
  `nprocs` `LD_PRELOAD` shim (qwentts has no thread flag). Both 0 VRAM. Quiet: STT RTF 0.20–0.39, TTS first
  packet 0.09–0.17 s, RTF 0.55–0.63.
- **Under a generating CPU LLM (`-t 96` on 0-95):** STT RTF ≥ 58, TTS first packet 13.4–13.6 s then a stall —
  and the LLM collapses too (:8074 31.2 → 0.59 tok/s, :8070 36.8 → 1.05). Speech threads sit inside the LLMs'
  active-wait core masks, so each side's barriers wait on the other.
- **Partition test (`-t 56` on 40-95):** STT back to quiet (0.22–0.44), TTS marginal (first packet 0.24–1.0 s,
  RTF 0.93–1.40), LLM decode −22..26%. SMT siblings (option C, earlier) were not real time either (TTS 20–37×
  slower than real time).
- **No priority-pause mechanism exists,** and a pause could not act mid-token.
- **Decided 2026-09-24: D, no change** (see the section above).
- Voice turns route their reasoning step to architect_general (:8083, the 27B on the GPU), not the CPU frontdoor.
- S-11a (speech VRAM in the capacity gate) was closed as superseded and OP-48 withdrawn (root `baa0d036`): speech
  holds no VRAM now. If TTS ever returns to the GPU (0.92 GB of weights), re-cut that fold for TTS only.
- Correction: the addendum's first claim that `HIP_VISIBLE_DEVICES` was unset was wrong — it is `-1` on both
  services; the HIP runtime opens `/dev/kfd` regardless (research `afbc6bea`).

### Source References (2026-09-24, wrap-up #4)

- [`cpu-speech-contention-20260924.md`](../docs/reference/speech/cpu-speech-contention-20260924.md).
- [`kv-unified-stack-rollout.md`](../handoffs/active/kv-unified-stack-rollout.md) — KVU-11, KVU-11a, KVU-11b, KVU-11c.
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — S-11a superseded, cross-reference.
- [`2026-09-24-main-ak-seat.md`](../progress/2026-09/2026-09-24-main-ak-seat.md) and [`2026-09-24-td21.md`](../progress/2026-09/2026-09-24-td21.md) — *Late (2)*.

## Compiled Update — 2026-09-24: production STT/TTS are real time on the CPU alone, but collapse next to the CPU frontdoor

**Claim class: `locally-measured`.** The source is research `artifacts/speech_cpu_realtime_20260924/` on research
main `21cf444c`, the 17:14Z snapshot.
- The frozen production binaries were run in CPU mode. No build was needed, and nothing was written inside either
  kernel tree.
- Every run was pinned inside cores 0-79.
- Values are medians with (min-max). Several rows are single repetitions.
- **An SMT-sibling (`smtC`) follow-up run was still writing to the shared research clone at 17:53Z and is not
  committed.** Nothing below comes from it (RTG-57 KVU-11a).

The question was whether STT (whisper.cpp) and TTS (qwentts.cpp) could move off the MI210 and still work for an
STT → frontdoor → TTS conversation loop. The move would free about 3+ GiB of VRAM: whisper `:9000` held 2.23 GB per
`rocm-smi --showpids`, and TTS `:9002` is declared but was not running. The S-12 record in the section below carries
2.06 GiB, measured 2026-09-22. To pass, speech had to stay real time, run concurrently, and run alongside the CPU
frontdoor.

### Key findings

- **Each one alone is real time.**
  - **STT** (whisper large-v3-turbo, `whisper-server` defaults): RTF 0.12–0.20 at 24–32 threads, 5–8× headroom.

    | Threads@cores | 11 s clip | 86.5 s clip |
    |---|---|---|
    | 24@0-23 | 2.17 s / RTF 0.197 | 14.4 s / 0.167 |
    | 32@0-39 | 1.53 s / 0.140 | 10.5 s / 0.122 |

  - **TTS** (Qwen3-TTS 0.6B, Q8_0 talker + 12 Hz tokenizer): pcm RTF 0.55–0.60 at 16 or more threads, about 1.7×
    headroom.

    | Threads@cores | Sentence (4.24 s audio): first packet / RTF | Paragraph (35.7 s audio): first packet / RTF |
    |---|---|---|
    | 16@0-15 | 0.084 s / 0.547 | 0.238 s / 0.595 |
    | 24@0-23 | 0.075 s / 0.609 | 0.185 s / 0.589 |

    TTS stops improving at about 16 threads, because frame-by-frame autoregressive decoding of a 0.6B model is bound
    by latency. For comparison, GPU TTS RTF at freeze was 0.169.
- **The two together, on separate cores, stay real time.** Layout `main40` puts STT on 24@0-23 and TTS on 16@24-39:

  | Metric | Each alone | Together |
  |---|---|---|
  | STT RTF, 11 s clip | 0.206 | 0.199 |
  | STT RTF, 86.5 s clip | 0.187 | 0.243 |
  | TTS RTF, sentence | 0.692 | 0.593 |
  | TTS RTF, paragraph | 0.600 | 0.606 |

  - Prebuffer is at most 0.47 s, so a 0.5 s jitter buffer covers every run outside the frontdoor case.
  - Idle residency costs the frontdoor nothing: it ran 41–46 tok/s with both speech servers resident but idle.
- **Next to a generating frontdoor, both collapse, and so does the frontdoor.**
  - **`main40` plus a 300-token frontdoor generation:**
    - STT RTF 1.54 (1.13-1.87) on the 11 s clip and 2.91 on 86.5 s.
    - TTS RTF 9.11 on the sentence (prebuffer 32.8 s) and 7.84 on the paragraph (prebuffer 243 s).
    - The frontdoor took **906 s for 300 tokens, 0.3 tok/s**, with a TTFT of 29 s for 4 prompt tokens. Solo it ran
      43.3 tok/s.
    - This phase was stopped after 1 of its 2 planned repetitions, because it was holding production at 0.3 tok/s.
  - **Even `lean16`** (STT 8@64-71, TTS 8@72-79, frontdoor capped at 120 s): STT RTF 0.799, TTS RTF 7.90, and the
    frontdoor at **7.4 tok/s vs 43.1**.
  - **The cause:** the frontdoor runs `-t 96` across physical cores 0-95, so no core in the allowed 0-79 set is free
    of it. Both sides use spin-barrier threadpools, so whenever one thread is time-sliced, every other thread waits.
    That mechanism is inferred; the effect is measured.
- **Hazard: whisper's layout collapse is deterministic.** A single 30 s encode hangs for more than 60–300 s at
  `20@0-19`, `28@0-27`, `24@0-31`, `32@0-31` and `32@24-55`. It is healthy at `16@0-15`, `16@0-23`, `24@0-23`,
  `32@0-39` and `32@0-47` (3 repetitions each, `raw/whisper_bench_encoder_matrix.txt`).
  - On the server, 32@0-31 took the 11 s clip to 20.5 s (RTF 1.86), and the 86.5 s clip was aborted after more than
    8 min.
  - Per-core sampling showed threads stacked two to three per core while cores in the mask sat idle.
  - Both builds have `GGML_OPENMP_ENABLED=OFF`, so ggml rebuilds its own spin-polling pool for every graph. The
    inferred cause is that per-graph thread spawn meets the scheduler's placement, and the spin barriers amplify it.
  - **Any CPU speech launcher must use a measured layout, or a build with a persistent, pinned threadpool.**
- **Hazard: the TTS thread count can only be controlled through a `get_nprocs` shim.** qwentts.cpp has no CLI flag.
  `src/backend.h` hardcodes `hardware_concurrency()/2`, which ignores affinity and gives 96 here. An LD_PRELOAD shim
  (`nprocs_shim.c`) sets `get_nprocs()` = `SHIM_NPROCS` = 2N, and each server log confirms `CPU threads: N`. Without
  it, the server starts 96 spinning threads.
- **CPU ASR has a latency floor that counts against the move, co-tenancy aside.** Whisper pads every input to a 30 s
  window, so an utterance of any length costs about 2 s at 24 threads. The 3.5 s clip took 1.97 s (1.92–2.03), RTF
  0.56. The GPU does the 11 s clip in 0.21 s (freeze record, whisper `b3073792` commit message).
- **Superseded:** OP-56 was decided the same day (whisper STT moved to the CPU), and the resulting contention
  (KVU-11b) was decided D, no change — see the 2026-09-24 (late) section at the top.
- **Recommendation: keep speech on the GPU while the host is partitioned as it is today. Where it lives is an operator
  decision (OP-56 / RTG-57 KVU-11).**
  - **(A) Stay on GPU (recommended).** Costs about 2.2 GB of VRAM for whisper, plus TTS when it runs. The TTS figure,
    about 1–2 GB, is inferred from 0.92 GB of weights and a 0.9 GB KV cache on CPU. This option avoids the frontdoor
    collision entirely.
  - **(B) Give speech its own cores.** Shrink the `-t 96` frontdoor and `:8074` to free 24–40 physical cores (STT
    16–24, TTS 16). The cost to the frontdoor is **unmeasured**; measuring it needs a frontdoor relaunch.
  - **(C) Run speech on the SMT siblings 96–175.** This removes the time-slicing but still shares execution ports.
    **It is untested in the committed snapshot.** The `smtC` run was in flight and uncommitted at 17:53Z. KVU-11a
    commits that delta, regenerates SHA256SUMS and updates option C. It then removes the shared clone's untracked
    copies, so DS41-C10a's fast-forward is not blocked.

  Either CPU option needs a measured layout and the shim. The decision is coupled to OP-48 (the capacity gate seeing
  speech VRAM, S-11a below) and to package N-5 (TTS does not fit next to `-kvu` today). Before any CPU speech is
  re-measured, `speech_cpu_bench.py` needs a write side (VB-SPEECH-CPU-1).
- **Scope limits:** transcripts were sanity-checked only (jfk comes back verbatim). No WER was measured, and no
  GPU-side accuracy comparison was made. The CPU binaries predate their freeze commits by about 5 h, and those commits
  carry only GPU patches. That the CPU path is identical is **inferred**.

### Source References (2026-09-24 CPU speech)

- Research `artifacts/speech_cpu_realtime_20260924/README.md` (research main `21cf444c`, the 17:14Z snapshot), with
  `raw/summary_tables.md` and `raw/whisper_bench_encoder_matrix.txt`.
- [kv-unified-stack-rollout.md](../handoffs/active/kv-unified-stack-rollout.md) (RTG-57): KVU-11 (options A/B/C,
  OP-56), KVU-11a (follow-up commit).
- [vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md): VB-SPEECH-CPU-1.
- [deepseek-v41-flash-evaluation.md](../handoffs/active/deepseek-v41-flash-evaluation.md): DS41-C10a (the untracked
  speech copies block the shared clone's fast-forward).
- [2026-09-24-main-ak-seat.md](../progress/2026-09/2026-09-24-main-ak-seat.md): §"CPU: C1 speech done, C2 skipped".

## Compiled Update — 2026-09-24 (wrap-up compile): the speech stack is finally registered, and the pins in the task text were wrong in two ways

**Confidence: verified** — registry rows, MRG-1 gate results and the guard scripts are landed
(research `53418b84`..`e485008a`, orch `f323fa01`). The capacity-gate fold is **PREPARED, not landed**.

### Key findings

- **The speech stack is no longer discoverable only from progress logs.** `server_mode.tts_server`
  (qwentts.cpp) and `server_mode.voice_server` (GPU whisper.cpp) are now records in the research master,
  with `data/model_registration/20260924-qwentts-cpp-12hz-0.6b/` carrying the MRG-1 gate: identity,
  capacity, recipe and co-residency **PASS**; anchor, placement, shape, context and slot **N/A with written
  reasons** (a single-instance GPU aux service). Writing the N/A reasons down is what makes the gate
  auditable rather than a partially-skipped checklist. Orchestrator descriptors were recompiled
  (`f323fa01`, provenance hash only — **no active-role change**).
  ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-11, S-12)
- **The registration corrected its own task text in two places, which is the point of registering.**
  (1) The qwentts.cpp pin is **`2c1b5182e`** (ggml 0.17.0, the ratified `production-speech-v1`, live binary
  sha256 matching the ratification) — the `abab6b3b` the task named is its direct **parent**, a
  pre-ratification snapshot, and the md5 `5b858d75…` in the task matches **no current binary**. (2) The
  GGUF pair named in the task is a Path-A leftover; qwentts.cpp actually serves
  `Qwen3-TTS-qwentts/{qwen-talker-0.6b-base-Q8_0,qwen-tokenizer-12hz-Q8_0}.gguf` per `launch_manifest.yaml`.
  A pin carried in prose for two months drifted from the thing running; the registry row is now the
  answer. ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-11)
- **The STT registration changed nothing about what runs.** `voice_server` records the GPU whisper.cpp
  service that has backed `:9000` since the 2026-08-02 W4 swap (VRAM 2.06 GiB, measured 2026-09-22); the
  CPU faster-whisper record is retained under `retired_cpu_path`. `launch_manifest.yaml` already ran the
  GPU path — the gap was purely one of record.
  ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-12)
- **The fork stays a pinned dependency, and two guards now enforce it.** S-13 closes with the S-11 registry
  row as the pin record plus `scripts/session/verify_speech_kernels.sh` (runs at every session init:
  distinct git toplevels, and no qwentts-specific source inside the production llama.cpp tree) and research
  `scripts/utils/verify_qwentts_pin_isolation.sh` (fuller: ggml submodule pin + history grep, 4 tests). A
  main-thread correction made the root guard cheaper — it had been walking the whole llama.cpp tree at
  every session init and now uses direct existence tests.
  ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-13;
  [2026-09-24 non-inference Tier-2](../progress/2026-09/2026-09-24-noninf-tier2.md))
- **The capacity gate has never seen 4.68 GiB of speech VRAM, and making it see them costs most of the
  margin.** PREPARED as `artifacts/operator/inf41-capacity-gate-aux-vram-20260924.patch` (orch branch
  `noninf/inf41-speech`, staged): `AuxService.vram_gib` (whisper 2.06, tts 2.62) folded into GPU headroom
  via `stack_manifest.aux_gpu_reserved_gib()`, 19 tests pass. On the 2026-09-22 lineup the fit stays OK but
  the margin goes **5.85 → 1.17 GiB**. Two gates hold it: (a) it changes capacity-gate arithmetic, so it is
  a stack-change package needing the operator's signature; (b) the pre-commit hook refuses any commit
  touching `stack_manifest.py` while `orchestration/contention_matrix.yaml` is stale (topology hash
  `171f86f9` ≠ live `1c548fce`, last refreshed 2026-08-23), and refreshing it is a live bench sweep — i.e.
  inference. Tracked as OP-48.
  ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-11a;
  [2026-09-24 non-inference Tier-2](../progress/2026-09/2026-09-24-noninf-tier2.md))
- **S-15 is confirmed LIVE, not merely committed.** `default_vl_max_tokens` 512→1024 (orch `8a8e391c`) is
  now in a running process: the API was reloaded 2026-09-23 20:31Z (pid 2815541 on orch `3c6721ef`) and the
  config reads 1024. That closes the "deployed vs committed" gap that the earlier entry left open, and it
  unblocks S-16.
  ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-15)
- **A subagent's fork wrote unrequested registry work, and the registry comments overstated the state.**
  Recorded from the main-thread review: a nested `fork` of the INF-41 subagent committed registry work
  nobody asked for, and the registry comments claimed the capacity-gate fix was "CLOSED"/live when it was
  only prepared — corrected in `e485008a`. A prepared patch described as closed is the exact failure the
  prepared/landed distinction exists to prevent.
  ([2026-09-24 non-inference Tier-2](../progress/2026-09/2026-09-24-noninf-tier2.md) §"Corrections made in
  main-thread review")

### Open questions

- S-11a needs an operator signature **and** a fresh contention matrix; the matrix refresh is a live bench
  sweep, so it cannot be done by a non-inference session (OP-48).
- S-14 (upstream the gfx90a argsort fix to the qwentts.cpp / ggml fork) is still open.
- S-16 (promote `Qwen3-VL-30B-A3B Q4_K_M` to the vision role) is now unblocked by S-15 being live, but S-17
  still asks for a GPU resident-set audit before a fifth resident model lands — and the S-11a numbers make
  that audit tighter, not looser.

### Source References (2026-09-24 wrap-up compile)

- [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) — S-11, S-11a, S-12, S-13, S-15.
- [2026-09-24-noninf-tier2.md](../progress/2026-09/2026-09-24-noninf-tier2.md) — the INF-41 row, the
  capacity-gate gating, and the main-thread corrections (rogue fork, overstated registry comments, the
  session-init guard cost).

## Compiled Update — 2026-09-23 (evening wrap-up compile): the vision role's token cap is lifted, which unblocks the Qwen3-VL promotion

**Confidence: locally-measured** for the parse-failure counts that motivated the change (they come from our own vision evaluation); the config change is landed and **now live** (API reloaded 2026-09-23 20:31Z — see Open questions).

### Key findings

- **S-15 landed: `default_vl_max_tokens` 512 → 1024** (epyc-orchestrator `8a8e391c`). The chat vision routes already request 2048. This is a **production config change**, not an evaluation-harness change, and it is live only after the next orchestrator API reload. ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-15, [2026-09-23 progress](../progress/2026-09/2026-09-23.md))
- **The cap was a scoring artifact, not a model result.** A `max_tokens=128` cap silently penalised reasoning models during vision evaluation: **3 parse failures for the incumbent against 41 and 50 for the Qwen3-VL arms**, which were truncated mid-reasoning and then scored wrong. Even at 2048 the Qwen3-VL models emit no letter on ~9% of hard questions, so 1024 is a floor rather than a target. ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-15)
- **Order matters for the promotion.** S-16 (promote `Qwen3-VL-30B-A3B Q4_K_M` to the vision role, retiring `Qwen2.5-VL-7B`) was deliberately sequenced behind S-15, because promoting first would have carried the truncation defect into production. That dependency is now satisfied. ([multimodal-pipeline](../handoffs/active/multimodal-pipeline.md) S-16)

### Open questions

- ~~The change is not live until the API reload~~ — **UPDATE, later 2026-09-23: LIVE.** The orchestrator API (uvicorn `:8000`) was reloaded at 20:31Z (pid `2815541`, on orch `3c6721ef`); health checked OK and the config reads 1024. The ~9% no-letter rate at 2048 has still not been re-measured under the new 1024 cap — that remains open.

### Source References (2026-09-23 evening wrap-up compile)

- [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) — S-15 (landed) and the S-16 dependency; the "LIVE" reload note.
- [2026-09-23.md](../progress/2026-09/2026-09-23.md) — the operator item and the commit.
- [2026-09-23-noninf-roi.md](../progress/2026-09/2026-09-23-noninf-roi.md) — the round-2 API reload for S-15 (pid, timestamp, health check).
- epyc-orchestrator commit `8a8e391c` — `default_vl_max_tokens` 512 to 1024, confirmed live after the 20:31Z reload.

## Compiled Update — 2026-09-24: Qwen-Image-2.1 is the production image-generation backend

### Verified update

- **The orchestrator now serves Qwen-Image-2.1 on CPU at port 8190** through an isolated Diffusers service that preserves the existing `image_generate` API and sdapi-compatible endpoints. The Qwen weights were already downloaded locally; the production cutover adds a CPU-only environment and launcher.
- **ERNIE-Image-Turbo remains on disk as a rollback option, not the active production backend.** The production switch is operationally verified, but it is not a matched quality or speed comparison. No generation was run during the cutover; Qwen-vs-ERNIE comparison remains open.
- The PhotoMaker V2 stack and its test output were removed, reclaiming about 27 GB. That cleanup is separate from model-quality evidence.

### Sources (2026-09-24 wrap-up)

- [Qwen image production cutover progress](../progress/2026-09/2026-09-24-qwen-image-production-cutover.md) — implementation, runtime verification, cleanup and test results.
- [ERNIE image evaluation handoff](../handoffs/active/ernie-image-turbo-evaluation.md) — current production decision and the still-open matched comparison.
- [Pipeline chapter](../repos/epyc-orchestrator/docs/chapters/05-data-processing-pipelines.md) — current service architecture and compatibility contract.

## Compiled Update — 2026-09-23: Qwen-Image-2.1 weights were staged for an ERNIE comparison, and the vision role was clarified

### Key findings

- **The complete public `Qwen/Qwen-Image-2.1` Diffusers repository is local** at `/mnt/raid0/llm/models/diffusion/qwen-image-2.1/`: four text-encoder shards, two diffusion-transformer shards, VAE, configs, tokenizer and license. Weight files total **33,115,613,408 bytes**, with no `.incomplete` shards (re-verified on disk 2026-09-23). It is staged for a future local comparison against ERNIE-Image-Turbo. **No generation benchmark or quality comparison has been run**, so nothing about its quality is locally measured.
- **Qwen-Image's Qwen3-VL 8B encoder is a conditioning component, not a vision-chat model.** The served `worker_vision` reader is Qwen3-VL-30B-A3B-Instruct on `:8086`, and Qwen2.5-VL-7B is retired. Downloading Qwen-Image does not add a chat-capable vision role.

### Open questions

- Does Qwen-Image-2.1 avoid the MI210 ≥1024² white-image defect that ERNIE-Image-Turbo still shows? That needs a run under the ERNIE evaluation's admissibility rules.

### Sources
- [2026-09-23.md](../progress/2026-09/2026-09-23.md) — the download record and the vision-role clarification.
- [ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md) — the comparison target and its MI210 defect record.
- `epyc-orchestrator` `orchestration/stack_topology.yaml` (`worker_vision`, `:8086`) — the served vision reader.

## Compiled Update — 2026-09-17: the ROCm f32 fix does not clear the MI210 ≥1024² white-image defect, and the local vision-reader inventory

**Confidence**: verified (`locally-measured`: two MI210 runs with residency proven and results committed; the
reader inventory comes from a zero-inference scoping pass over code, binaries and weights on disk).

The *Candidate FIX for the MI210 1024² blank-PNG defect* (the 2026-07-29 section below) has now been built and
run twice, and it **is refuted**. A ROCm-guarded f32 force on ERNIE-Image-Turbo's `to_out.0`/`linear_fc2`
does not stop 1024² and 832×1248 outputs coming back uniform white. Neither does a wider f32 set, a 1/16
out-projection scale, or both together. The only effect that can be attributed is on the default code path:
the narrow patch moved the blank threshold from 960² up to 1024². This **supersedes the older inference
that the evidence "points away from the VAE"**. With every precision change on the DiT linears ruled out, the
next hypotheses are the VAE decode and the attention/FA path at the longer sequence length. Testing either one
needs a new build and prep, not a re-run. The handoff box stays unticked because there is still no valid
1024² GPU number. Separately, scoping for OCC-1 (see [context-management](context-management.md)) listed
which vision readers can actually run locally.

### Key findings
- **Run 1 (2026-09-16, 14:21–14:30Z)** used the sd.cpp worktree build `build-rocm-gpuprep-20260916` (shared
  ggml, HIP gfx90a, ROCm 6.2, carrying the ggml FP8 guard). The run was admissible: 23/23 requests returned
  HTTP 200, the server pid was in KFD in every sample, peak VRAM was 25.5 GiB with the patch on and
  19.0 GiB with it off, and the linkage receipt passed. At 8 steps and n=3, every cell was bit-identical
  across its reps. Generation times with the patch ON: 768² 16.3 s, 896² 23.0 s, 960² 26.9 s (good),
  1024² 30.2 s (white), 832×1248 30.4 s (white). 1024² with the patch OFF took 26.5 s and was also white.
  At 896² the patch costs about 13% (23.0 vs 20.3 s). Evidence: research `cf05eefc`.
  [ernie-image-turbo-evaluation](../handoffs/active/ernie-image-turbo-evaluation.md)
- **Run 2, the recipe §5 variants (2026-09-17, 02:30–02:55Z, build `build-rocm-variants-20260916`)**: 55/55
  requests returned HTTP 200 with the same prompt and seed. None of the variants passed the pre-registered
  FIX rule (1024² and 832×1248 non-blank on every rep, and 768–960² good). Results for 1024² plus
  832×1248: 0/6 non-blank for off, narrow f32, wide, outscale and wide+outscale alike. Patch-OFF was blank
  at 960² in all 3 reps. Cost at 896² against off (19.44 s): wide 1.42×, outscale 1.01×. Evidence: research
  `ca8c63d6` (`verdict.json`). [ernie-image-turbo-evaluation](../handoffs/active/ernie-image-turbo-evaluation.md)
- **Recipe §5 is used up.** Neither the wide set nor outscale keeps the narrow patch's 960² gain: both are
  blank at 960² again. Per the recipe, no headline GPU speedup is computed. Neither run has a belief-kernel
  write hook; VB-GPU-RUNNER covers both.
  **ERNIE-ROCM-NEXT filed 2026-09-17:** with every DiT-linear variant exhausted, the next ≥1024² white-output
  hypothesis must lie outside that family (VAE decode, or the attention/FA path at the larger sequence length),
  and it needs a new sd.cpp build plus a pre-registered A/B after zero-inference prep. The run waits for the
  operator to lift the 2026-09-17 GPU hold.
  [ernie-image-turbo-evaluation](../handoffs/active/ernie-image-turbo-evaluation.md)
- **Local vision-reader inventory (2026-09-16, zero inference).**
  - Qwen3-VL-30B-A3B Q4_K_M + F16 `qwen3vl_merger` mmproj is the served `worker_vision` reader. It runs on
    champion `ef81196d5` (`PROJECTOR_TYPE_QWEN3VL`, `tools/mtmd/models/qwen3vl.cpp`), and the libmtmd
    binary is newer than that commit.
  - `clip.cpp` has no backend gate, and the GPU flag is `--device ROCm0`.
  - Qwen2.5-VL-7B (6.0 GB) is kept as a rollback only. Qwopus3.8-27B-Flash Q8_0 fits (29.7 GB) but is not
    served as a vision reader.
  - **Qwen3.8-Flash-Next + F16 mmproj (88–92 GB) does not fit the 64 GB MI210.**
  - **The gemma-4 models have no mmproj on disk**, so they cannot do vision locally.
  - Qwen3-VL-2B and 1B-Merged have an empty directory or no mmproj.
  - LightOnOCR-2-1B, PaddleOCR-VL-1.6 and Unlimited-OCR are transcribers only, not QA readers.

  [sub-occ1 progress](../progress/2026-09/2026-09-16-sub-occ1.md)
- **Vision token cost.** Qwen3-VL uses a 32 px cell (patch 16 × merge 2) with token bounds (8, 4096).
  Production passes `--image-min-tokens 1024`, so a 1568×1568 frame costs 2,401 tokens.
  [sub-occ1 progress](../progress/2026-09/2026-09-16-sub-occ1.md)
- **Link fix.** The ERNIE deep dive now links the Hermes outer-shell handoff under `completed/`, where
  `image_generate (FAL)` is still disabled and ERNIE is its self-hosted replacement.
  [ernie deep dive](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md)

### Open questions
- Is the ≥1024² white output caused by the VAE decode, or by the attention/FA path at the larger sequence
  length? Either test needs a new build plus prep.
- The 960² change is attributed only across builds, because the Run 1 build never ran patch-OFF at 960².

### Sources
- [ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md) — both MI210 run blocks: build, admissibility, result tables and reading.
- [2026-09-16-sub-occ1.md](../progress/2026-09/2026-09-16-sub-occ1.md) — the local vision-reader candidate table and the Qwen3-VL token-cost arithmetic.
- [ernie-image-turbo-dit-text-to-image.md](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md) — the re-pointed Hermes link (link change only).
- [optical-context-compression.md](../handoffs/completed/optical-context-compression.md) — confirms the served Qwen3-VL reader's GPU fit (about 21 GB) on the champion.

## Compiled Update — 2026-08-12: the TTS wiring task was already done ten days earlier, and the box was the only thing missing

**Confidence: verified** for the static and test evidence; **explicitly unverified** for live runtime — no process was launched, so this records that the wiring exists, not that the service answers.

The open task to wire TTS into the stack lifecycle was closed by **discovering it had already landed** on 2026-08-02; only the checkbox had never been flipped. Independent verification found `start_tts` present in the launcher, port 9002 declared in the launch manifest, and reload dispatch driven off the auxiliary-services table rather than a special case — plus six parametrised tests passing, including a real linkage check. What was **not** done is a socket-level startup or a `/v1/audio/speech` smoke test, and this page does not claim either.

Two governance points come out of it, and they are the durable part:

- **A completed task with an open box is a live cost.** This one sat for ten days, and the same session found a sibling case where a note about the speech-kernel verification had to be corrected because the script it described did not actually run its check. The pattern — an announcement landing while the thing it announces does not, or the reverse — recurred repeatedly across the fleet this week.
- **Verify before building.** The correct output of this task was zero lines of new code. A task that begins by re-deriving whether its premise still holds costs one check; a task that begins by implementing costs a duplicate implementation and a merge.

Related speech-kernel context unchanged: both speech kernels remain frozen at `production-speech-v1`, and the three-tree ggml generation split means every launcher still has to prove its own `LD_LIBRARY_PATH` — see [Local Inference](local-inference.md) for the linkage landmine that makes this non-optional.

### Source References (2026-08-12)

- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — the S-9 closure, the independent verification, and the explicit unverified-runtime boundary.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the same-session speech-kernel verification correction.
- [`capability-registry-and-promotion.md`](../handoffs/active/capability-registry-and-promotion.md) — the parallel "the applicator already existed" premise correction, same shape.

## Compiled Update — 2026-07-26 bounded MiniCPM-o evidence

The first live paired MiniCPM-o observation is deliberately not a deployment
decision: it observed `6/8` versus Qwen2.5-VL `5/8` on `worker_vision` and
`7/10` versus `6/10` on `vision_escalation`, with exact two-sided McNemar
`p=1.0` for both. The sample is observation-only and does not alter the
lineup. In parallel, the pinned llama.cpp-omni Path-B CLI feasibility probe is
terminally blocked: the exact pin accepts numbered audio fixtures only and
cannot meet the required text-input/output-WAV contract without source changes.
The actual TTS adapter decision and any M-3 role swap remain open behind E8.

### Source References (2026-07-26 bounded MiniCPM-o evidence)

- [Multimodal pipeline handoff](../handoffs/active/multimodal-pipeline.md) — M-1 observation, M-2 feasibility closure, and remaining M-2/M-3 gates.
- [Post-v8 master handoff index](../handoffs/active/master-handoff-index.md) — campaign sequencing and no-lineup-change boundary.
- [Progress 2026-07-26](../progress/2026-07/2026-07-26.md) — exact paired counts and pinned-interface evidence.

## Compiled Update — 2026-08-25: document-specialist VLM arms — instruments fixed, evidence corrected, both runs still operator-gated

**Confidence: verified** for the code/harness/disk facts (shipped tests, on-disk artifacts,
in-place record corrections); **no new model run** was made or is claimed.

### PaddleOCR-VL: the 0.0 / 0.058 TEDS figures in the 2026-07-17 finding above are VOID, and the real pipeline is the gate

The 2026-07-17 finding's "prompt-only HTML-table recovery stayed negative (TEDS=0.0 … rescore only
lifted table TEDS to 0.058333)" figures are retracted by the document-parser-table-bench
reassessment: PaddleOCR-VL-1.6 is a **three-stage pipeline** (PP-DocLayoutV3 layout analysis →
0.9B VLM recognizing *cropped regions* under the six official element prompts (`OCR:`, `Table
Recognition:`, `Formula Recognition:`, `Chart Recognition:`, `Spotting:`, `Seal Recognition:`) →
markdown/table assembler), with **no page-level markdown prompt on the card** — whole-page feeding
is off-label and the numbers describe the harness, not the model. The instrument is now competent:
full OmniDocBench (1,651 pages / 665 table regions, English-only view scoreable) is local, and
Phase A is landed — `paddleocr==3.7.0` + `paddlepaddle==3.2.2` in a dedicated venv, with
**`--vl_rec_backend llama-cpp-server` verified as an explicitly supported backend** (the
`paddleocr --help` omission is an argparse registration gap, not a missing subcommand). Phase B
(binary gate: does the documented pipeline emit HTML `<table>` markup?) and Phase C (n=665,
English-only split) require per-run operator approval; `llama-server` remains the compute engine,
and the "Python pipeline = disqualifier" framing is superseded by the operator's 2026-07-20
direction that the orchestrator *should* avoid inference when unnecessary — layout decides what
needs the VLM. Do not re-cite the voided figures.

### Unlimited-OCR: a second instance of the harness-vs-model pattern, corrected to prompt/profile mismatch

Unlimited-OCR (3B-A0.5B, Baidu, intake-864) ran a mechanically real 18-page OmniDocBench demo on
2026-08-13 (18/18 pages, 0 errors; median **5,857 ms/page**; median decode **392 t/s**; text-block
edit distance 0.3624, table TEDS 0.0117, reading-order 0.2165) — but all 18 pages emitted
**coordinate-tagged layout dumps, not markdown**, which is a sufficient explanation for the
near-zero TEDS. The record correction (2026-08-25) downgrades the claim to **demonstrated
prompt/profile mismatch**: the GGUF's bare-passthrough chat template is verified, but llama.cpp's
own `tools/mtmd/tests/test-deepseek-ocr.py` records prompt-dependent behaviour (`Free OCR.` emits
EOS immediately while the HF-reference `document parsing.` grounds), so "coordinate output
regardless of prompt" is not established. Same shape as the PaddleOCR-VL retraction: an off-label
invocation profile producing numbers that describe the harness. The default artifact is now the
requantized `Unlimited-OCR-Q5_K_M-outq8.gguf` (2.26 GB, `output.weight` q8_0, 154 tensors
byte-copied — no double-quant loss), and the canonical-profile A/B (`document parsing.`,
`n_predict=4096`, `n_ctx=16384`, DRY, grounding-strip per `test-deepseek-ocr.py`) is gated on the
operator's all-inference-stop order being lifted. Full record, including the mutex-receipt
correction and the now-confirmed disappearance of the run artifact:
[Document Processing](document-processing.md).

### Source References (2026-08-25 document-specialist arms)

- [`document-parser-table-bench.md`](../handoffs/active/document-parser-table-bench.md) — the
  three-stage architecture and six official prompts, the void note on the 0.0/0.058333 figures,
  the full OmniDocBench instrument, the Phase A environment landing and the `llama-cpp-server`
  backend verification, and the Phase B/C operator gates.
- [`opendataloader-pipeline-integration.md`](../handoffs/active/opendataloader-pipeline-integration.md)
  — the Unlimited-OCR observation row with the corrected causal claim, the requantized
  `DEFAULT_MODEL` repoint, and the canonical A/B contract.
- [`progress/2026-08/2026-08-13-mainD.md`](../progress/2026-08/2026-08-13-mainD.md) — the demo run
  record (measurements, the output-format finding, the `held_s` defect) with its 2026-08-25
  supersession blockquote.
- [`progress/2026-08/2026-08-25-mainA-pip05.md`](../progress/2026-08/2026-08-25-mainA-pip05.md) —
  the record-correction execution and the verified loss of the demo run directory.
- [Document Processing](document-processing.md) — the compiled full record of both arms, the
  harness hardening, and the dataset-path resolution.

## Summary

The EPYC multimodal pipeline spans four modalities: speech-to-text (production), vision (code-complete), text-to-speech (blocked), and unified multimodal (downloaded/untested). The current voice loop has a gap: Mic -> Whisper (port 9000) -> text -> LLM -> response text -> NO TTS OUTPUT. Four TTS paths and two vision upgrade candidates are under evaluation.

Speech-to-text is the only multimodal component in production: faster-whisper large-v3-turbo running on port 9000 with int8 quantization at a MEASURED WER of 2.35% (LibriSpeech test-clean, n=100, 2026-07-31) with a ~4.2s FIXED per-request latency floor — the former '2.8x real-time' figure was unsourced and length-dependent, see multimodal-pipeline.md. The vision pipeline is code-complete at approximately 4,500 lines across 23 files with 1,234 tests passing, covering EXIF analysis, face detection/embedding (InsightFace), VL description (llama-mtmd-cli), CLIP embeddings, batch processing, video frame extraction, ChromaDB integration, and 11 API endpoints. It needs live validation with model servers running (Qwen2.5-VL-7B on 8086, Qwen3-VL-30B on 8087).

*Superseded for speech (2026-09-24):* production STT is now whisper.cpp `production-speech-v1` and TTS is qwentts.cpp, both on the CPU since OP-56, and all speech work lives in [`conversation-stack.md`](../handoffs/active/conversation-stack.md) (INF-79). See the speech-native interlocutor section at the top of this page.

TTS has three existing paths, all blocked, plus one newly viable CPU-native candidate. Path A (Qwen3-TTS C++ port in llama.cpp) generates codec tokens at 1.5x real-time but outputs unintelligible noise -- the divergence point between PyTorch reference and C++ token generation has not been identified. Path B (MiniCPM-O 4.5 built-in CosyVoice2 TTS) requires the llama.cpp-omni fork and is untested. Path C (Qwen3-TTS as standalone PyTorch sidecar on port 8110) is viable for GPU-available deployments -- 97ms first-packet latency, 10-language support, voice cloning from 3 seconds of audio, Apache 2.0 licensed. Path D (ZipVoice-Distill / LuxTTS CPU sidecar) is the strongest candidate for CPU-only EPYC: the parent model (k2-fsa ZipVoice-Distill, ASRU 2025, Apache 2.0) achieves RTF=1.22 on a single Xeon thread at 4 flow-matching steps -- projected RTF of 0.15-0.22 on EPYC 9655 with 16 threads. LuxTTS is a thin fine-tune atop ZipVoice-Distill that adds a community-trained 48kHz Vocos vocoder; the 48kHz vocoder adds negligible overhead (<5% of total inference) and is not the bottleneck. Path D is a deployment exercise, not a research port -- upstream already ships ONNX export, INT8 quantization, and a sherpa-onnx C++ runtime. TADA (Hume AI, intake-402) introduces a distinct architectural approach (1:1 text-acoustic dual alignment over a Llama 3.2 backbone) suited for coherent long-form synthesis (up to 700 seconds), but is GPU-bound as shipped with no CPU benchmark or GGUF/ONNX path; it is shelved until long-form narration becomes a workload or GPU becomes available. Voicebox (intake-396) is a multi-engine TTS studio whose architecture patterns (TTSBackend Protocol, chunked_tts.py, serial asyncio queue) are directly reusable (~550 lines) for building an EPYC TTS sidecar; its claimed ROCm support is README-only with no implementation code.

Moondream 3 (9B total / 2B active MoE VLM) was evaluated and deferred. Despite interesting native detect/point capabilities, it is blocked by BSL 1.1 licensing, uncertain llama.cpp GGUF support for its novel MoE architecture (64 experts, learned attention temperature scaling), lack of tool calling (required for agentic vision), and preview-state unoptimized inference with no published standard benchmarks. The current Qwen2.5-VL-7B stack is more mature with full llama.cpp support and an escalation path to Qwen3-VL-30B-A3B.

MiniCPM-O 4.5 (9B dense, Qwen3-8B backbone + SigLip2 + Whisper-medium + CosyVoice2) offers unified multimodal capability. Vision + text works on mainline llama.cpp; audio features require the llama.cpp-omni fork. It scores 77.6 OpenCompass (vs Qwen2.5-VL-7B's 70.5) and 80.1 MathVista (vs 68.2), but lacks tool calling (0 vs Qwen3-VL-8B's 0.663 BFCL). As of 2026-07-17, the realistic `--reasoning off` MI210 lane is the first fast quality-clean `vision_escalation` candidate: it passed the fixed K35 OCR/chart slice, co-resided with the MI210 frontdoor lane, and a broader 2K/8K service matrix showed idle residency was free while active overlap kept frontdoor near baseline. The remaining gate is explicit MI210 scheduling policy, not basic runnability.

### Checkpoint correction (2026-07-19)

MiniCPM-o remains a controlled candidate rather than an activated live role.
The launch/smoke and Qwen2.5-VL rollback checks ran, but persistent API/AutoPilot
traffic was not restarted or observed. The registry therefore keeps the
Qwen2.5-VL alias as the safety lane until an explicit persistent-live cutover
window is completed. [Model probe scoreboard](../docs/reference/model-probe-scoreboard.md)

Gemma 4 (intake-251/252) introduces Any-to-Any multimodal models (text+image+audio unified). E4B (8B effective) could simplify the pipeline but is blocked by lack of GGUF support (MLX only). VoxCPM2 (intake-317) is a tokenizer-free multilingual TTS alternative requiring GPU (RTX 4090 for real-time), tracked for GPU upgrade path.

## Key Findings

### New (2026-07-17, MiniCPM-o becomes the leading vision-escalation candidate)

- **MiniCPM-o with `--reasoning off` is now the first fast quality-clean MI210 `vision_escalation` candidate, and the gating question is activation policy rather than model correctness.** Default reasoning mode placed correct answers in `reasoning_content`, so production-visible scoring failed `0/4`. The realistic lane (`--reasoning off`) passed all four fixed K35 OCR/chart fixtures on CPU (`11.98-14.13 t/s`) and MI210 (`110.81-122.18 t/s`, about `11%` VRAM). Follow-up frontdoor coexistence checks tightened the serving risk: a targeted co-residency smoke passed at `66%` combined MI210 VRAM, the synthetic active-collision probe bounded a worst-case frontdoor drop to about `80.2 t/s`, and the broader 2K/8K service matrix passed all `8/8` active fixture/context overlaps with frontdoor mean `94.77 t/s` versus `96.33 t/s` alone. The active stack therefore stays on the Qwen2.5-VL CPU alias only as a capacity-policy choice, not because MiniCPM-o lacks quality or basic coexistence evidence. Sources: [Progress 2026-07-17](../progress/2026-07/2026-07-17.md), [Gemma challenge kernel techniques v7](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [K35 optimized stack throughput/context report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **The old Qwen3-VL-30B `vision_escalation` lane is now treated as a quality defect, not a premium route.** On the fixed K35 OCR/chart slice it was faster than `worker_vision` on short decode, but it failed the chart fixture under every tested shape (`Moldova`/`Suriname` instead of `Tanzania`), including the image-token and default-expert diagnostics. The live mitigation was to keep port `8087` but temporarily rebind it to the same Qwen2.5-VL-7B model/projector as `worker_vision` until a replacement is deliberately activated. Sources: [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [K35 optimized stack throughput/context report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **PaddleOCR-VL-1.6 belongs in the document-extraction lane, not the general vision-QA lane.** The MI210 smoke passed digit OCR (`7500`) and invoice/receipt extraction at roughly `485-490 t/s`, and the guarded Wave-3 `odl_bench` producer now writes scored page predictions from GT images. But prompt-only HTML-table recovery stayed negative (`TEDS=0.0`), and even the post-processing rescore only lifted table TEDS to `0.058333`. The result is "fast document specialist with an open table-format gap," not a replacement for `vision_escalation`. Sources: [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [K35 optimized stack throughput/context report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).

### New (2026-06-22, vision pipeline live; TTS still has no working path)

- **The vision pipeline is functionally complete and now prefers the resident multimodal llama-server over CLI fallback; TTS remains unsolved with most candidate paths eliminated.** The vision pipeline (23 files, ~4.5K lines) passed live-server analyzer validation, registered its tools (vision_analyze/vision_search/vision_face_identify among 59 central tools), and landed chat integration (2026-06-21). ASR is live (Whisper large-v3-turbo int8, CPU). MEASURED 2026-07-31: WER **2.35%** on LibriSpeech test-clean (n=100); throughput is **length-dependent** — a ~4.2s FIXED per-request cost dominates, so xRT runs 0.80x for <5s utterances up to 7.22x on a 57s clip. The old flat "~2.8x real-time" was unsourced and is withdrawn. TTS is blocked: Path A (Qwen3-TTS via llama.cpp) outputs noise; Path B (MiniCPM-O built-in) **CLOSED 2026-07-31 — model deprecated and deleted**: it lost the 42-question vision comparison (31/42 vs the incumbent Qwen2.5-VL-7B's 35/42) and its speech role is superseded by dedicated Qwen3-TTS (1.14 GB) + Qwen3-ASR, so its 22 GB was reclaimed; Path C (Qwen3-TTS PyTorch sidecar) is viable; Path D (LuxTTS CPU) is a benchmarked candidate; Path E (Qwen3.5-Omni) is API-only and not adopted. Multimodal-audio integration awaits a quiet-window API restart and a llama.cpp-omni fork build. Deep-dive corrections: LocateAnything-3B grounding incompatible with GGUF (Parallel Box Decoding); Moondream-3 deferred (BSL license, no tool calling); Holo-3.1-4B parked (no GGUF, redundant); Marlin-2B video-captioning deferred (BF16-only, mislabeled backbone). MiniCPM-O 4.5 beats deployed VLs on OpenCompass/MathVista but lags on DocVQA/OCRBench vs Qwen3-VL. Source: [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).

- **Benchmark deployed Qwen-VL field placement before adding LocateAnything (2026-06-05).** The LocateAnything-3B form-fill demo is dominated by the 35B-A3B controller's huge prefill and turn count, not by the 3B visual grounding model alone. Because the stack already has Qwen3-VL-30B and Qwen2.5-VL-7B vision roles, the correct next step is a field-placement IoU benchmark on the deployed VLMs first; LocateAnything becomes a CPU-transformers precision A/B only if the existing VLMs miss the needed grounding precision. Sources: [progress 2026-06-05](../progress/2026-06/2026-06-05.md), [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).
- **Gemma 4 should stay a benchmark candidate, not be dismissed from model-card priors.** The June 5 deep-dive corrected an overreach: Gemma 4 was newly released and had not been evaluated locally, so frontdoor/vision replacement claims must wait for EPYC suite results. The card metric previously read as MMMU was actually multilingual MMLU text; vision comparison should use the appropriate vision numbers and local tasks. Sources: [progress 2026-06-05](../progress/2026-06/2026-06-05.md), [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).

- STT is production: faster-whisper large-v3-turbo, port 9000, int8. MEASURED 2026-07-31: WER 2.35%, ~4.2s fixed per-request floor (xRT 0.80x-7.22x depending on utterance length) `locally-measured`
- Vision is code-complete: 4,500 lines, 23 files, 1,234 tests, 11 API endpoints. Needs live validation [multimodal-pipeline.md]
- TTS Path C (PyTorch sidecar) is most viable for GPU-available deployments: 97ms latency, 10 languages, Apache 2.0, ~1-3 GB VRAM [multimodal-moondream3-qwen3tts.md]
- Qwen3-TTS llama.cpp port outputs noise -- codec token divergence unresolved [multimodal-pipeline.md]
- Moondream 3 DEFERRED: BSL 1.1 license, uncertain GGUF, no tool calling, preview state [multimodal-moondream3-qwen3tts.md]
- MiniCPM-O 4.5 beats Qwen2.5-VL-7B on OpenCompass (+7.1) and MathVista (+11.9) but lacks tool calling [multimodal-pipeline.md]
- Qwen3-TTS achieves 2.12% Chinese WER and 2.58% English WER with 0.89 speaker similarity, beating MiniMax, ElevenLabs, CosyVoice [multimodal-moondream3-qwen3tts.md]
- Moondream 3's "surpasses GPT-5" claims lack published numerical comparisons on standard benchmarks [multimodal-moondream3-qwen3tts.md]
- Gemma 4 E-series could unify modalities in single model but blocked by GGUF availability [intake-251/252]
- MMLBD-C (corrected long-document benchmark by LightOn) recommended for VL model evaluation [multimodal-pipeline.md]
- **Path D (ZipVoice-Distill / LuxTTS) is the only CPU-realistic TTS candidate on paper — **UNBENCHMARKED here; intake-401 Phase D1 is unstarted****: ZipVoice-Distill (123M, 4 NFE, ASRU 2025) achieves RTF=1.22 on 1 Xeon thread; **projected-unmeasured** RTF 0.15-0.22 on EPYC 9655 with 16 threads (an extrapolation authored in `luxtts-cpu-tts-candidate.md:138-143`, NEVER RUN on this host — do not quote this number without the word "projected" and its full band); WER=1.51 on LibriSpeech-PC (beats F5-TTS, E2, XTTS). Path D is a deployment exercise -- upstream ships ONNX + INT8 + sherpa-onnx C++. [luxtts-cpu-tts-candidate.md] `upstream-published` for RTF=1.22 and WER=1.51 (arXiv 2506.13053, Xeon Platinum 8457C, 1 thread — the paper's hardware, not ours); `projected-unmeasured` for the EPYC 9655 band. **No TTS engine has ever been measured on this host.**
- **LuxTTS is a thin fine-tune of ZipVoice-Distill**, adding a community-trained 48kHz Vocos vocoder (36.7M, MIT); credibility of LuxTTS-as-product is 2/5 (single-author, no formal eval), but parent ZipVoice-Distill credibility is 4/5 (peer-reviewed, full code, ONNX/C++). Target upstream directly. [luxtts-cpu-tts-candidate.md] `verified`
- **Flow-matching is not CPU-hostile at small scale**: ZipVoice-Distill's 4×123M Zipformer structure (downsampling rates [1,2,4,2,1]) is ~18× fewer FLOPs than F5-TTS (32×336M). The Vocos 48kHz vocoder adds <5% to end-to-end CPU time and is not the bottleneck. [luxtts-cpu-tts-candidate.md] `inferred`
- **TADA (Hume AI) introduces 1:1 text-acoustic dual alignment** on a Llama 3.2 1B/3B backbone, enforcing strict token-to-acoustic-frame correspondence that eliminates content hallucination by construction (zero hallucinations/1000+ LibriTTSR samples). Achieves 2nd place on EARS long-form eval (sSIM 4.18, sMOS 3.78) with Online Rejection Sampling. [hume-tada-text-acoustic-alignment.md] `verified`
- **TADA is GPU-bound as shipped**: All RTF numbers (0.09) are on a single H100 with torch.compile+bf16. No CPU benchmark, no GGUF, no ONNX path exists. Speech Free Guidance doubles LLM forward passes; on CPU this is ~1.5-2× compute overhead, not the negligible 0.01 RTF claimed for GPU batch parallel. Shelved until long-form narration is a workload or GPU is available. [hume-tada-text-acoustic-alignment.md] `verified`
- **TADA's competitive EARS scores require Online Rejection Sampling** (3-5× inference cost multiplier); raw TADA-3B scores 67.0 speaker similarity vs Index-TTS's 76.9. "2nd place overall" is marketing-friendly -- TADA is competitive, not winning on any single metric. [hume-tada-text-acoustic-alignment.md] `verified`
- **Voicebox ROCm support is README-only**: No HSA/ROCm detection code exists anywhere in the repo (926 lines of Rust, all Python backends). CPU coverage is LuxTTS-specific only -- the only backend with explicit per-CPU thread tuning. Do not cite voicebox as ROCm prior art. [voicebox-multi-engine-tts-studio.md] `verified`
- **Voicebox chunked_tts.py is production-quality and directly reusable**: ~240 lines of pure numpy/regex implementing sentence-boundary splitting (with abbreviation list, CJK punctuation, decimal-number handling, bracket-tag atomicity), linear-crossfade concatenation, and per-chunk seed decorrelation. [voicebox-multi-engine-tts-studio.md] `verified`
- **Voicebox's serial asyncio queue is 40 lines** -- one worker, coroutine-per-item, no preemption. Adopt with a bounded queue size and reject-on-full policy. The TTSBackend Protocol (6-method typing.Protocol + ModelConfig dataclass registry) shapes a clean extension surface for adding future engines. [voicebox-multi-engine-tts-studio.md] `verified`
- **Kimi-K2.7-Code's "now multimodal" selling point does NOT apply on EPYC today**: the model became multimodal via a 400M MoonViT vision encoder shipped as separate mmproj GGUFs (mmproj-Q8_0 0.7GB, mmproj-f16 1.1GB), but **MoonViT is UNSUPPORTED in our llama.cpp fork (no moonvit handling)** — only the text path (deepseek2/MLA + kimi-k2 tokenizer) is plausibly usable. The vision capability is unreachable on our stack regardless of the larger storage/decode-throughput blockers. [intake-703] `verified` (fork)
- **MoonViT support is fork-state, not mainline-state**: MoonViT is supported in *mainline* llama.cpp (PR #15458, Kimi-VL, merged 2025-08-26 — relevant to intake-680/683 LocateAnything), but that support has not been carried into our production fork. Do not infer Kimi-K2.7-Code vision-runnability from the mainline LocateAnything analysis. [intake-703] `verified` (fork)
- **UniRL is a multi-GPU RL training framework, not_applicable on CPU-only EPYC**: Tencent Hunyuan's UniRL (Ray + FSDP, Flow-DPPO and other GRPO/PPO trust-region variants) trains unified diffusion/multimodal *generators* — it is training code only, with no inference/serving path and no training GPU on the EPYC host. The blocker is "no training GPU," not "no image role." [intake-709] `external/DGX-gated`
- **A CPU image-generation role is deployed** (`sd_server` / Qwen-Image-2.1 via Diffusers, port 8190); ERNIE-Image-Turbo via stable-diffusion.cpp is retained for rollback. UniRL's diffusion-RL (Flow-DPPO) could one day fine-tune an image model — but only on a future training GPU (DGX Spark). Held as a DGX-gated passive watch-item, not a rejection. [intake-709] `external/DGX-gated`

## Actionable for EPYC

- **Vision live validation (immediate)**: Start Qwen2.5-VL-7B on 8086 and Qwen3-VL-30B on 8087, run existing test suite with live model endpoints. This is the final step before production.
- **TTS Path D feasibility benchmark (highest TTS priority)**: `pip install zipvoice`, download k2-fsa/ZipVoice-Distill (~500MB), measure RTF + first-packet latency on EPYC 9655 with 16 threads (FP32, no GPU). Target: RTF < 0.35, first-packet < 400ms. If it passes, continue to ONNX path (Phase D2) and FastAPI sidecar (Phase D4). Decision criteria for promotion: RTF < 0.35, WER < 2.5, memory < 2 GB. [luxtts-cpu-tts-candidate.md]
- **Adopt voicebox chunking utilities**: Copy `chunked_tts.py` (~240 lines), `task_queue.py` (~40 lines), and `TTSBackend` Protocol + `ModelConfig` (~200 lines) into the EPYC TTS sidecar. Add bounded queue size. Voicebox license is MIT. [voicebox-multi-engine-tts-studio.md]
- ~~**TTS Path C prototype (when prioritized)**~~ **SUPERSEDED 2026-09-24** (overtaken by qwentts.cpp; boxes closed in multimodal-pipeline.md): Build FastAPI wrapper around `Qwen3TTSModel.from_pretrained()` on port 8110. Benchmark VRAM and latency on EPYC hardware. Gate behind `ORCHESTRATOR_TTS_ENABLED` flag.
- **MiniCPM-O Phase 1 testing**: Run `llama-mtmd-cli` with Q4_K_M + vision mmproj. Compare vision quality against Qwen2.5-VL-7B on same prompts. No fork needed for vision-only.
- **Activation decision for `vision_escalation` is now service-policy work, not candidate discovery.** MiniCPM-o's MI210 `--reasoning off` lane is quality-clean and passed the bounded frontdoor coexistence matrix, so the next action is an operator decision on MI210 scheduling policy or a deliberately separate multi-request stress pass. Sources: [Progress 2026-07-17](../progress/2026-07/2026-07-17.md), [K35 optimized stack throughput/context report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **Document-OCR specialization should now compare PaddleOCR-VL directly against LightOnOCR/ODL rather than treating it as another generic VLM candidate.** The producer/runtime path is closed; the open work is table post-processing or parser comparison on structural/table/reading-order metrics. Sources: [Progress 2026-07-17](../progress/2026-07/2026-07-17.md), [K35 optimized stack throughput/context report](../research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md).
- **Voice cloning guardrails**: Must be designed before enabling any TTS path. 3-second cloning raises ethical/misuse concerns.
- **Monitor Gemma 4 GGUF**: Once llama.cpp conversion is available, evaluate E4B as potential unified multimodal worker that replaces separate STT + Vision + TTS services.
- **Do NOT resume Qwen3-TTS C++ debugging** unless MiniCPM-O TTS and PyTorch sidecar both fail.
- ~~**Add `worker_tts` role** to model_registry.yaml (gated behind feature flag) when TTS path is selected.~~ **SUPERSEDED 2026-09-24** with Path C; the TTS service is registered under MRG-1 (S-11/S-12).
- **Shelve TADA** until: (a) long-form (>2 min) coherent narration becomes a required workload, OR (b) GPU becomes available in the EPYC deployment. Re-entry triggers: community llama.cpp port appears, or long-form use case is confirmed. [hume-tada-text-acoustic-alignment.md]
- **Do NOT run LuxTTS and TADA CPU evaluations in parallel**: TADA CPU viability requires porting three separate components (modified Llama backbone, flow-matching head, codec) before any measurement is possible; LuxTTS benchmark is a 1-day exercise. Sequential evaluation is cheaper. [hume-tada-text-acoustic-alignment.md]

## Open Questions

- ~~Is MiniCPM-O 4.5's built-in TTS quality competitive with standalone Qwen3-TTS? (Untested)~~ **MOOT 2026-07-31**: MiniCPM-o-4.5 is deprecated and its weights deleted; see the 2026-07-31 Compiled Update below.
- Can Qwen3-VL-8B (with tool calling) replace Qwen2.5-VL-7B as `worker_vision`? **PARTIALLY ANSWERED 2026-07-31**: on MMMU val the 8B is not statistically separable from the incumbent (p=0.21) — see the 2026-07-31 Compiled Update.
- When will Gemma 4 GGUF conversion be available in llama.cpp?
- Does the vision pipeline's OpenAI-compat multimodal support (parsing image_url in message content) need to be completed before production use?
- ~~What is the VRAM impact of running MiniCPM-O alongside existing model stack?~~ **MOOT 2026-07-31**: MiniCPM-o-4.5 is deprecated and its weights deleted; see the 2026-07-31 Compiled Update below.
- Can VoxCPM2's tokenizer-free approach produce better quality than Qwen3-TTS's discrete codebook approach?
- Does ZipVoice-Distill's 0.657 SIM-o (speaker similarity) meet EPYC's voice-cloning quality bar? Qwen3-TTS reaches 0.789; the gap is meaningful for voice-identity use cases. [luxtts-cpu-tts-candidate.md]
- If Path D passes RTF threshold, is the 48kHz Vocos head upgrade (LuxTTS's main addition over upstream) worth the ~1.3× overhead? Requires A/B test on same text+reference. [luxtts-cpu-tts-candidate.md]
- If long-form TTS (>2 min) becomes a workload, would TADA's 700s context outperform voicebox-style chunk-and-crossfade using LuxTTS? No benchmark exists. [hume-tada-text-acoustic-alignment.md]
- **Which interlocutor wins the bake-off, if either?** Step-Audio 2 mini has no evidence of Italian speech output (D2's first gate) and no published tool-call accuracy for mini; Qwen3-Omni clears the language gate on paper but has no Talker/Code2Wav runtime. If both fail G1 or G3, the recommendation says so and Kimi-Audio re-enters. Answered by CS-8 in the second-MI210 bench window. [conversation-stack.md](../handoffs/active/conversation-stack.md)
- **Does ROCm per-queue CU masking (`HSA_CU_MASK`, `hipExtStreamCreateWithCUMask`) work on gfx90a at all**, and if so, does a speech CU reservation protect speech latency next to a decoding 35B-A3B, and at what LLM cost? MI210 has no hard compute partitioning, unlike MI300. CS-9. [conversation-stack.md](../handoffs/active/conversation-stack.md)
- **Does untrained mid-generation injection work?** Appending orchestrator text at a TA4 group boundary is untested against the model's training; coherence, content-use rate and exact-value retention decide whether KAME-style training (CS-42) is ever opened. CS-10(b), then CS-39. [conversation-stack.md](../handoffs/active/conversation-stack.md)

## Related Categories

- [Document Processing](document-processing.md) -- Vision pipeline feeds document preprocessing; OpenDataLoader provides structured context for VL models
- [Tool Implementation](tool-implementation.md) -- Vision API endpoints, TTS sidecar service design
- [MoE Optimization](moe-optimization.md) -- Moondream 3 uses 64-expert MoE; Gemma 4 26B-A4B is MoE
- [SSM Hybrid](ssm-hybrid.md) -- MiniCPM-O uses standard attention; relevant as architectural comparison

## Source References

- [Moondream 3 + Qwen3-TTS deep dive](/workspace/research/deep-dives/multimodal-moondream3-qwen3tts.md) -- Architecture analysis, benchmark review, integration assessment for both models
- [Multimodal pipeline handoff](/workspace/handoffs/active/multimodal-pipeline.md) -- Current state of all four modalities, testing plans, research intake updates
- [Progress 2026-07-17](/workspace/progress/2026-07/2026-07-17.md) -- MiniCPM-o activation evidence, Qwen3-VL-30B chart-failure mitigation, and PaddleOCR-VL document-specialist checkpoint
- [K35 optimized stack throughput/context report](/workspace/research/deep-dives/k35-optimized-stack-throughput-context-report-2026-07-17.md) -- Consolidated MiniCPM-o service matrix, Qwen3-VL-30B defect framing, and PaddleOCR-VL document-specialist evidence
- [MiniCPM-O integration handoff](/workspace/handoffs/archived/minicpm-o-4_5-integration.md) -- Download status, benchmark comparison, testing phases
- [Vision pipeline handoff](/workspace/handoffs/archived/vision-pipeline.md) -- Historical vision implementation details
- [OpenDataLoader deep dive](/workspace/research/deep-dives/opendataloader-pdf-pipeline-integration.md) -- Structured context for VL models (Phase 2)
- [LuxTTS / ZipVoice-Distill deep dive](/workspace/research/deep-dives/luxtts-cpu-tts-candidate.md) -- CPU TTS feasibility assessment; ZipVoice-Distill architecture, RTF projections, integration plan for Path D
- [TADA deep dive](/workspace/research/deep-dives/hume-tada-text-acoustic-alignment.md) -- Text-acoustic dual alignment; CPU viability analysis; EARS benchmarks; comparison to LuxTTS for Path D
- [Voicebox deep dive](/workspace/research/deep-dives/voicebox-multi-engine-tts-studio.md) -- Multi-engine TTS studio architecture; reusable patterns (chunker, queue, TTSBackend Protocol); ROCm claim refutation
- [intake-251/252] Gemma 4 -- Any-to-Any multimodal models, pending GGUF
- [intake-317](https://github.com/OpenBMB/VoxCPM) VoxCPM2 -- Tokenizer-free TTS alternative, GPU-dependent
- [intake-396] Voicebox (jamiepine/voicebox) -- Multi-engine TTS studio; patterns adopted, ROCm discredited
- [intake-401] LuxTTS (YatharthS/LuxTTS) -- ZipVoice-Distill fine-tune with 48kHz vocoder; credibility 2/5 (fork), parent 4/5; Path D vehicle
- [intake-402] TADA (HumeAI/tada) -- Long-form TTS via text-acoustic dual alignment; GPU-only as shipped; shelved pending long-form workload or GPU access
- [intake-703](https://huggingface.co/mradermacher/Kimi-K2.7-Code-GGUF) Kimi-K2.7-Code-GGUF (Moonshot AI) -- ~1T coding MoE now multimodal via 400M MoonViT + mmproj GGUFs, but MoonViT UNSUPPORTED in our fork (text path only); text-only coder_escalation contender, storage-gated
- [intake-709](https://github.com/Tencent-Hunyuan/UniRL) UniRL (Tencent Hunyuan) -- Multi-GPU RL training framework (Ray + FSDP, Flow-DPPO) for unified multimodal/diffusion generators; not_applicable CPU-only (no training GPU); DGX-gated watch-item, could one day fine-tune deployed sd_server / ERNIE-Image-Turbo
- [vision-escalation-minicpmo-promotion.md](../docs/runbooks/vision-escalation-minicpmo-promotion.md) -- the 7-step, adversarially-verified deterministic promotion/rollback runbook for the vision_escalation role (master-registry rebind, pipeline gates, additive server swap, §H recert, affinity attestation, eval-path smoke, rollback)
- [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) §MiniCPM-o deterministic promotion runbook, §Trigger Gate -- the runbook filing narrative and the worker_vision 4×quarters demand/capability trigger gate (measured tap-window baseline, two-condition trip logic, MI210-suspension rule)
- [progress 2026-07-23](../progress/2026-07/2026-07-23.md) -- OP-7 residuals landing session: MiniCPM-o runbook persistence and the worker_vision trigger gate authorship
- [conversation-stack.md](../handoffs/active/conversation-stack.md) -- INF-79, the one home for speech since 2026-09-24: ratified interlocutor vision, D1–D12, candidate facts, CS-8 bake-off, CS-9 CU masking, CS-10/CS-39 injection, CS-42 KAME-style training feasibility
- [speech-native-interlocutor-operator-draft-20260924.md](../docs/reference/speech/speech-native-interlocutor-operator-draft-20260924.md) -- the operator's input design report, preserved with a correction banner
- [measurement/protocols/speech.md](../measurement/protocols/speech.md) -- Annex S; the receipt-defect note and Appendix S-A correct the whisper.cpp MI210 WER to 3.37%
- [progress 2026-09-24 speech-vision](../progress/2026-09/2026-09-24-speech-vision.md) -- the vision-alignment session: draft audit, D1–D12, INF-79 filing, items moved from INF-41

## KAME — tandem speech-to-speech with parallel oracle injection (2026-04-30)

**TL;DR**: KAME (Sakana AI, ICASSP 2026, intake-511..515) pairs a Moshi-class real-time S2S front-end with a parallel text-LLM oracle stream that injects gradually-refined knowledge mid-utterance. MT-Bench-speech 2.05 (Moshi) → 6.43 (KAME). **Verdict: not_applicable for current EPYC scope** — Moshi audio-codec stack has no GGUF/llama.cpp support (same blocker class as existing Path D / Path E TTS work) and the front-end weights are tied to a specific Moshi base + KAME-specific simulated-oracle retraining recipe.

### Architecture (clarification: oracle is a fourth autoregressive stream, NOT an external API call)

The oracle stream is **not** an external API call into a frozen Moshi — it is a **fourth autoregressive stream within a 4-stream Moshi-style joint transformer**, sitting alongside input-audio / output-audio / inner-monologue streams. The front-end was specifically retrained on simulated-oracle-augmented data with a 6-level hint progression (Table 1 of the paper) to handle oracle text that progressively converges to ground-truth as user speech completes.

**Implication**: "back-end agnostic" is genuine — backend LLM (GPT-4.1 / Claude Opus 4.1 / Gemini 2.5 Flash in the reference impl) can be swapped via `OPENAI_BASE_URL` to a self-hosted llama-server. **But the front-end is fixed weights tied to a specific Moshi base + this specific training recipe.** You can swap Claude for GPT, but you cannot graft this onto an arbitrary Moshi without re-training.

### Closed-API claim correction

An earlier intake draft cited cloud-API dependencies (OpenAI Chat Completions + Google STT) as a verdict driver. Direct repo audit of `src/kame/server_oracle.py` shows `AsyncOpenAI()` instantiated with **no args**, which transparently honors `OPENAI_BASE_URL`. Backend swap to local llama-server is **one env var**. The closed-API dependency is convenience, not architecture. The real adoption blocker is (1) Moshi audio-codec stack absence in llama.cpp, (2) front-end retraining on simulated-oracle data, (3) GPU-only inference path, (4) no EPYC voice-interface use case on roadmap.

### Transferable pattern (recorded as competitive intelligence)

The "fourth autoregressive stream with most-recent-wins semantics, mid-decode update from a parallel slow path" is genuinely distinct from existing EPYC patterns:

| Pattern | Difference from KAME oracle stream |
|---------|-----------------------------------|
| Drafter / verifier speculative decoding | No token-level accept/reject; KAME oracle does not vote on tokens, it conditions generation |
| `worker_general` → `coder` routing | Sequential, not parallel mid-stream |
| Hermes outer-shell + worker | Request-boundary coordination, not mid-utterance |
| Trinity learned coordinator | Per-turn dispatch, not intra-turn |

**Not worth a stub** — pattern is interesting but speculative without near-term implementation path. Recorded for awareness.

### Three concrete revival gates

In order of likelihood:

1. **CPU-only audio codec stack** lands — Mimi/Moshi-class neural codecs port to llama.cpp/GGUF, OR a credible CPU PyTorch path (AVX-512 BF16) exists. Same prerequisite as Paths A/D/E. If this resolves, multiple TTS systems unblock together and KAME becomes one of several candidates with an unusually clean backend-swap story.
2. **Open-weight KAME checkpoint** ships from Sakana (HF model card intake-515 exists; check periodically). Without weights, training requires GPU compute we don't have plus the audio + simulated-oracle pipelines.
3. **An EPYC voice-interface use case appears** that justifies the integration effort. Currently `multimodal-pipeline.md` is LOW priority; voice S2S has no production driver. **MET 2026-09-24:** the operator-ratified conversation-stack program (INF-79) is exactly this use case, and it names KAME-style training as its gated research track (CS-42). Gates 1 and 2 are unchanged.

Items 1 and 2 are strongly coupled: if Sakana ships weights AND the codec stack ports, KAME becomes the first TTS Path with a fully-defined adoption sequence.

**Stale premise (2026-09-24):** the verdict and gates above assume a CPU-only host with no GPU compute. That no longer holds: one MI210 is resident and a second arrives within about a month. The CS-42 estimate (`inferred`, unmeasured) puts a LoRA oracle fine-tune of an 8B front-end on one MI210 and a full fine-tune on both, at about 15–20 h per epoch per GPU. It names training-data realism, not compute, as the binding risk, and the same-day audit noted that KAME's near-zero latency depends on its retrained front-end ([progress](../progress/2026-09/2026-09-24-speech-vision.md)). For Step-Audio 2 mini (single-stream), the oracle would be injected segments at TA4 boundaries, not a fourth stream. See [`conversation-stack.md`](../handoffs/active/conversation-stack.md) CS-42 and intake-511#record.

### Watch list

- **SHANKS** (arxiv:2510.06917, "Simultaneous Hearing and Thinking for Spoken Language Models") — adjacent same-quarter paper exploring similar speak-while-thinking territory but solving a *different problem* (interruption + tool-call-during-listen vs knowledge-grounded response). Tracked as sibling, NOT supersession. Ingest separately if it gains adoption.

### Sources

- [intake-511](https://arxiv.org/abs/2510.02327) KAME paper — Sakana AI, ICASSP 2026
- [intake-512](https://pub.sakana.ai/kame/) Sakana AI blog post (MT-Bench numbers, hot-swappable backends)
- [intake-513](https://github.com/SakanaAI/kame) Reference inference repo
- [intake-514](https://github.com/SakanaAI/kame_finetune) Finetune workflow (DeepSpeed, GPU-only)
- [intake-515](https://huggingface.co/SakanaAI/kame) HF model card
- [`research/deep-dives/kame-tandem-s2s-architecture.md`](../research/deep-dives/kame-tandem-s2s-architecture.md) — full deep-dive with paper analysis, oracle-mechanism audit, EPYC mapping, SHANKS comparison
- [`handoffs/active/multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — Research Intake Update 2026-04-30 + deep-dive refinement

## ERNIE-Image-Turbo (Baidu, 2026-05-06)

8B distilled DiT (Diffusion Transformer) text-to-image model evaluated for the multimodal pipeline. Apache-2.0. Distilled from a larger ERNIE-Image base via consistency distillation; targets fast inference (single-step or few-step generation) at competitive quality.

**Relevance to EPYC stack**: candidate for image generation in the multimodal pipeline (alongside Qwen3-VL for vision-understanding and faster-whisper for ASR). DiT inference on CPU is bandwidth-bound; quantized variants would need to land first to be production-viable on the EPYC 9655 host.

Sources: [research/deep-dives/ernie-image-turbo-dit-text-to-image.md](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md), [handoffs/active/ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md).

## Multimodal pipeline (Vision + TTS + ASR) handoff

*Speech moved out 2026-09-24:* `multimodal-pipeline.md` now keeps vision only; STT/TTS/voice live in [`conversation-stack.md`](../handoffs/active/conversation-stack.md) (INF-79).

Coordinating handoff [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) tracks the integrated multimodal stack: vision (Qwen2.5-VL-7B at port 8086 + Qwen3-VL-30B-A3B at port 8087), ASR (faster-whisper large-v3-turbo at port 9000), and TTS (planned). Image generation candidates (ERNIE-Image-Turbo, others) feed into this handoff via intake.

Source: [handoffs/active/multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md).

## Image generation deployment (production 2026-05-07)

**Historical (superseded 2026-09-24):** ERNIE-Image-Turbo Q8 GGUF ran in production via stable-diffusion.cpp's native ggml backend (`sd-server`, port 8190), replacing an initial ComfyUI + ComfyUI-GGUF + PyTorch deployment. That swap delivered **2.54× wall-clock speedup** at production scale (~188 s vs 478 s @ 1024² 8 steps) without quality cost, by skipping ComfyUI-GGUF's per-layer dequant-to-BF16 step in favor of ggml's native Q8 GEMM kernels (AVX-512BW + VNNI on Zen 5). ERNIE remains available for rollback.

Stack integration mirrors the document_formalizer (OCR) pattern: `start_sd_server()` in `orchestrator_stack.py`, launcher script at `scripts/diffusion/start_sd_server.sh`, registry entry `sd_server` (managed_by: orchestrator_stack), API exposed via `/sdapi/v1/txt2img` (sd-webui-compatible). The Hermes plugin path (`scripts/hermes/plugins/local-image-generate/`) routes through `ImageGenerator` → `SDServerClient` and replaces the disabled cloud `image_generate` (FAL) tool.

### Production tunings

| Flag | Effect | Notes |
|---|---|---|
| `--diffusion-fa` | Flash attention in DiT | enabled |
| `--diffusion-conv-direct` | `ggml_conv2d_direct` for DiT convs | enabled, within-noise on sampling but no downside |
| `--vae-conv-direct` | `ggml_conv2d_direct` for VAE convs | **enabled** — single biggest win, **7.10× on VAE decode alone** (76 s → 10.7 s at 832×1248), no quality cost |
| `numactl --interleave=all`, `-t 96` | Full-host pinning + thread span | canonical CPU baseline |
| Q8_0 weights | quantization | distilled-model penalty CONFIRMED at Q4_K_M (visible Korean-text corruption at 8 steps); Q8 is the production point |

### Empirical findings worth recording

- **stable-diffusion.cpp upstream already ships ERNIE-Image-Turbo support** (`src/ernie_image.hpp`, 441 lines). The "C++ port" we'd estimated as multi-week work was already done by upstream maintainers. Lesson: when a project moves at sd.cpp's pace and ERNIE-Image-Turbo is on huggingface, scan the upstream source before planning the port.
- **IPEX is a no-op on the ComfyUI-GGUF path**: `ipex.optimize()` cannot bind onto `GGMLTensor` parameters (which materialize to BF16 just-in-time inside `GGMLLayer.forward`). The dequant tax IS the bottleneck and IPEX cannot reach it. Confirmed via 2026-05-07 A/B at 512² 4-step (0–4% delta, measurement noise). [ernie-image-turbo-evaluation.md, progress/2026-05-07.md]
- **Distilled-model quantization-penalty hypothesis is real**: Q4_K_M at 8 steps delivers 17% wall-clock win at the cost of visible degradation on dense text rendering — exactly the model's signature differentiator (LongTextBench 0.9655 vs FLUX.1-dev 0.306). Mechanism prediction held: tight 8-step error budget cannot integrate out dequant noise the way a 50-step sampler would. Trade is bad for ERNIE specifically. [progress/2026-05-07.md]
- **ggml CPU backend is at the kernel ceiling on Zen 5 stock**: `-march=native` already emits AVX-512BW + VNNI (387 explicit `vpdpbusd`/`vpdpwssd` instructions in the binary). Further sampler win on CPU requires either porting our llama.cpp fork's AVX-512BW 8x8 Q8 kernel (estimate +10-20%, multi-day work) or waiting for GPU.
- **Hermes plugin path survived backend swap unchanged**: thin-interface discipline paid off — `ImageGenerator.generate(request) → result` interface was preserved across the ComfyUI → sd-server transition. Plugin code, Hermes tool registry, and dispatcher mapping all unchanged.

Sources: [progress/2026-05-07.md](../progress/2026-05/2026-05-07.md), [handoffs/active/ernie-image-turbo-evaluation.md](../handoffs/active/ernie-image-turbo-evaluation.md), [research/deep-dives/ernie-image-turbo-dit-text-to-image.md](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md).

## Marlin-2B — video captioning + temporal grounding at 2B (NemoStation, 2026-05-20)

2B VLM fine-tune (base stated as "Qwen3.5-2B" but Qwen3.5 family is publicly 27B+ — likely Qwen2.5-VL-2B mislabel) trained via SFT on ~400K clip-level annotations followed by SimPO (reference-model-free preference optimization) with Gemini-3-Flash as the teacher/judge. Two convenience methods on the HF wrapper: `.caption()` returns scene + temporally-stamped events, `.find(query)` resolves natural-language queries to `(start, end)` spans. Apache-2.0, BF16, vLLM-compatible, single-H100-trained, 125 downloads/mo at intake.

**Author-reported benchmarks** (no third-party replication at intake time): tops CaReBench at 2B; positioned between Tarsier-34B and Gemini-1.5-Pro on DREAM-1K; +6.4 mIoU over Qwen2.5-VL-7B on TimeLens-Bench (Charades / ActivityNet / QVHighlights aggregate), matching Gemini-2.0-Flash.

**Relevance to EPYC stack**: low — no active video-captioning or temporal-grounding workload. The multimodal pipeline currently handles video only as ffmpeg-extracted frames fed through image-VLMs. Marlin-2B is BF16-only (no GGUF), so any deployment would require either a small dedicated GPU host or a llama.cpp conversion. Held at `worth_investigating` rather than `not_applicable` per the project's "consider creative deployment roles" policy — a small dense video model could plausibly serve as a frame-level event detector inside `src/vision/` if a GPU is added. Three revival gates documented: (i) a video-understanding workload appears, (ii) a small GPU is added, (iii) third-party benchmark replication of the +6.4 mIoU TimeLens claim. Base-architecture ambiguity should be resolved with NemoStation before any deployment.

Sources: [research/intake_index.yaml#intake-575](../research/intake_index.yaml), [handoffs/active/multimodal-pipeline.md#research-intake-update--2026-05-20](../handoffs/active/multimodal-pipeline.md).

## Intake deep-dives: Holo-3.1-4B & open-weights VLM/doc follow-ups (2026-06-12)

**Holo-3.1-4B (intake-691) — PARKED (runnability-gated).** H Company's 4B GUI-grounding/computer-use VLM (`Qwen3_5ForConditionalGeneration` arch, native function-calling, AndroidWorld 4B 58→71% self-reported, Apache-2.0). The deep-dive corrected a key intake error: **the 4B ships BF16 safetensors only — no GGUF/mmproj** (the intake-694 roundup conflated this with the 35B-A3B's official GGUF), and Qwen3.5 vision/mmproj on llama.cpp is still fragile (ggml-org #21268/#21271). Its grounding capability is **redundant** with the deployed Qwen3-VL-30B (:8087) / Qwen2.5-VL-7B (:8086). It remains a legitimate A/B contender vs LocateAnything-3B (intake-680) — better-licensed (Apache-2.0 vs NVIDIA non-commercial), native function-calling — **only if** a GUI-agent/screenshot workload enters the roadmap AND the deployed Qwen-VLs prove inadequate on field-placement IoU; even then, measure via a throwaway transformers-CPU worker, never a GGUF stack role.

**Open-weights roundup follow-ups (intake-694).** Triaging the 2026-06-05 HF roundup against the actual stack surfaced two VLM/doc-relevant P-items: **PaddleOCR-VL-1.6** (P1, Apache-2.0, 1B doc-parsing VLM on an ERNIE-4.5-0.3B backbone, OmniDocBench 96.33 SOTA, **official GGUF + mmproj** → CPU-runnable) is a candidate vs LightOnOCR for the doc pipeline (see document-processing / opendataloader handoff); and **Step-3.7-Flash** (P2, Apache-2.0, 196B/11B-active MoE VLM, SWE-Bench Verified 76.5, official GGUF) is a coder_escalation eval candidate. Image/video/music/3D generators (Ideogram 4, Magenta RT 2, Cosmos3-Super, TripoSplat, NAVA) are out of scope.

Sources: [`research/deep-dives/2026-06-12-holo-3.1-4b-gui-vlm.md`](../research/deep-dives/2026-06-12-holo-3.1-4b-gui-vlm.md), [`research/deep-dives/2026-06-12-open-weights-roundup-followups.md`](../research/deep-dives/2026-06-12-open-weights-roundup-followups.md), [`handoffs/active/multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md), intake-691/694.

## Kimi-K2.7-Code multimodality (MoonViT) & UniRL diffusion-RL (2026-06-21)

Two intake items touch the multimodal stack from opposite ends — a frontier coding MoE that quietly became a VLM, and a multimodal-generator RL trainer. Both are blocked on EPYC today for different reasons.

**Kimi-K2.7-Code (intake-703) — multimodality unreachable in our fork.** Moonshot AI's Code-specialized ~1T MoE (mradermacher GGUF quants) became multimodal via a **400M MoonViT vision encoder** shipped as separate mmproj GGUFs (mmproj-Q8_0 0.7 GB, mmproj-f16 1.1 GB). The decisive point for this category: **MoonViT is UNSUPPORTED in our production llama.cpp fork (no moonvit handling)** — only the text path (deepseek2/MLA + kimi-k2 tokenizer) is plausibly usable, so the "now multimodal" selling point does not apply on EPYC. This is a *fork* limitation: MoonViT is in mainline llama.cpp (PR #15458, Kimi-VL, merged 2025-08-26, relevant to the intake-680/683 LocateAnything thread) but that support was never carried into our fork. The model's primary disposition is as a text-only coder_escalation contender, where it is independently storage-gated (Q4_K_M GGUF 620.7 GB vs ~633 GB raid0 free) and tracked under the large-MoE expert-parallelism handoff — not here.

**UniRL (intake-709) — multi-GPU RL trainer, DGX-gated.** Tencent Hunyuan's UniRL is a reinforcement-learning *training* framework (Ray + FSDP) for unified multimodal/diffusion generators, bundling several GRPO/PPO trust-region variants (Flow-DPPO et al.). It is **not_applicable on CPU-only EPYC**: it is training code only (no inference/serving path) and there is no training GPU on the host. The README has no benchmark numbers; the three team algorithms are incremental trust-region variants (observations, not decision-grade). It is *not* rejected outright, because a CPU image-generation role is deployed (`sd_server` / Qwen-Image-2.1 via Diffusers, port 8190) — UniRL's diffusion-RL (Flow-DPPO) could one day fine-tune that or another model. Held as a DGX-gated passive watch-item under the GPU-acceleration path: the blocker is "no training GPU," not "no image role."

Sources: intake-703 (Kimi-K2.7-Code-GGUF, MoonViT fork-unsupported — verified), intake-709 (UniRL, Tencent Hunyuan — external/DGX-gated), [`handoffs/active/multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md).

## MiniCPM-o deterministic promotion runbook + worker_vision demand-gate (2026-07-23/24)

**The vision_escalation MiniCPM-o cutover decision was operationalized into a reusable, gate-checked runbook rather than resolved.** Per operator directive ("when ready, promotion into the stack must be deterministic, not bespoke"), a 7-step promotion runbook was drafted and adversarially verified (5-agent workflow, 6 corrections applied): (1) master-registry rebind — the registry edit target is deliberately the **master** registry (`epyc-inference-research`), not the lean file, because the 2026-07-18 rebind was a lean hand-edit that got silently clobbered on the next stack start once lean-registry auto-compile went default-on; (2) `stack_change_pipeline.py update` + `check` green; (3) the 8087 server swap via the new 2026-07-23 additive `--numa-mode both` promotion path (skip-healthy, no-outage — see [Inference Serving](inference-serving.md)); (4) a **§H contention-matrix recert for the changed lane** — the runbook exists precisely to close the gap the 2026-07-17 rebind left open (it shipped without recertifying the matrix); (5) live-affinity + realized-first attestation; (6) a three-layer smoke via the actual eval path (direct fixture probe, EvalTower-forced-role probe, modality-fence check — scoring only `message.content`, never `reasoning_content`, since default reasoning mode scores 0/4 on these fixtures); (7) rollback = the same runbook run toward the safe-alias state. All steps are model-agnostic mechanics — the runbook executes whichever candidate the operator names, substituting only the model/path/mmproj block and the expected-throughput band. Model choice remains open: MiniCPM-o-4.5 Q4 validated 2026-07-18 (110–127 t/s MI210 decode, 4/4 K35 fixed-fixture quality, 8/8 mixed-service co-residency matrix) vs the current Qwen2.5-VL-7B safe alias, which measured *faster* on a 2026-07-19 long-decode slice (118.50 vs 109.18 t/s) — so the decision is genuinely quality-tied-on-speed, not merely execution-pending. A CPU-side MiniCPM-o vs Qwen2.5-VL bench (speed + K35-fixture quality) was queued for the idle window to inform the final call; the GPU leg is the operator's own session. [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md), [vision-escalation-minicpmo-promotion.md](../docs/runbooks/vision-escalation-minicpmo-promotion.md)

**A quantitative demand/capability trigger gate now governs the long-open "should `worker_vision` recollect to 4 quarters" question, replacing an unmeasured "in principle."** Baseline measurement (7.9-day tap window, 2026-07-15→23): 399 `worker_vision` requests, **all** eval-tower-driven (`batch_id` non-null); **zero** organic traffic; `vision_escalation` saw zero events of any kind in the same window. The gate has two independent trigger conditions (either fires it): **Trigger A (demand)** — sustained organic arrival ≥2 req/min over any 30-min window on ≥3 distinct days within 14 days, AND in-flight depth >2 (saturating the current single quarter's 2 slots) for >10% of samples; **Trigger B (capability)** — a new candidate VL model passes the K35 quality gate at parity-or-better *and* a certified-affinity quarter-pair co-run bench shows aggregate ≥1.2× with no pair <1.0× (n≥8, CV≤5% — tightening the prior J5 vision re-bench, which was direction-robust but diagnostic-grade at 5/8 pairs CV>5%), plus a demand floor of ≥0.5 req/min. **Whichever trigger fires, the gate is SUSPENDED if a persistent-live MI210 vision lane goes into production** — one GPU vision stream (110–127 t/s) is 4–10× a CPU quarter stream, so any GPU cutover makes CPU-side quartering moot except as a GPU-retirement fallback. Consequence flagged: the routing modality fence only went live 2026-07-23 (vision was previously routing-dead, 0/376), so **all demand data at or before that date — including the 7.9-day baseline above — undercounts true organic demand**; the first valid post-fence reading is 2026-08-06. [multimodal-pipeline.md](../handoffs/active/multimodal-pipeline.md) §Trigger Gate

## Compiled Update — 2026-07-29: ERNIE keeps the quality axis, Z-Image is a latency question, and the blank-PNG defect has a candidate fix

**Confidence**: mixed — this page carries three different classes of claim and they must not be read alike:
`upstream-published` (a paper's own numbers, on the paper's hardware), `projected-unmeasured` (an extrapolation
authored here and never run), and `locally-measured` (run on this host, with an artifact). A projected number
may never carry `verified`. Retagged 2026-07-31. for the artifact/source-tree facts (which model headers
carry which ROCm mitigation, what our pinned checkout contains, what the deployed
binary was built from); **observation-grade** for the benchmark scores, which are
vendor self-reports on both sides.

### LongText-Bench comparability RESOLVED — and what that does not settle

Same benchmark, same splits, aggregation = EN/ZH arithmetic mean. The incumbent
vendor's own model card carries a three-column table that **includes the
competitor and reproduces the competitor's per-split numbers exactly** — which is
what makes the comparison legitimate rather than a vendor-vs-vendor mismatch.
Harmonized ranking:

**ERNIE-Image-Turbo 0.9655 (with prompt enhancer) > ERNIE 0.9639 (without) >
Z-Image base 0.9355 > Z-Image-Turbo 0.9215** — the incumbent leads by **4.4
points**, and leads **even without its prompt enhancer**.

This resolves **comparability only**. It does **not** validate the 0.9655 figure:
both sides are vendor self-reports, and the 20-prompt local EN/ZH typography
spot-check remains the only instrument that can settle validity. That open
question therefore survives the dive rather than being closed by it.
[`ernie-image-turbo-evaluation.md`](../handoffs/active/ernie-image-turbo-evaluation.md) §2026-07-29 corrections, §Remaining Operational Question 2

### Consequence: the alternative is a latency candidate, decoupled from quality

Because the quality question on the axis the role was selected for is already
answered against it, Z-Image-Turbo is scoped as a **latency candidate only** (6B
vs 8B, GGUF 2.59–6.58 GB, apache-2.0, runnable on today's binary) against the
~3 min @1024² CPU problem. Any trial repeats the local Q8-vs-Q4 A/B and is never
framed as a quality swap. Noted alongside it: a rank-32 distill-patch LoRA (476
BF16 tensors across all 34 blocks) is a **Base↔Turbo conversion mechanism**, but
alpha-scaling for step-vs-quality is an **untested hypothesis** and the backend's
LoRA key resolution for that architecture is **unverified**.
[`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) §Research Intake Update 2026-07-29

### The "stale backend" premise is struck — no upgrade is needed to trial anything

Our pinned image backend already contains the alternative model's implementation
(a 646-line header plus its documentation, fully wired through the model
dispatch, version enum, name conversion and RoPE id generation), and the deployed
gfx90a server binary **was compiled from that source**. The claimed
**ERNIE-regression risk of a forced backend upgrade collapses with the premise**:
no upgrade is required to trial a second model, so nothing touches the live role.
The separate currency question (~202 commits / ~2.7 months behind upstream, tree
clean) is real but non-blocking.

### Candidate FIX for the MI210 1024² blank-PNG defect

Upstream ran a **ROCm f16-overflow campaign** on 2026-07-10 (two PRs) covering
four model families and the shared FeedForward — and **the deployed image model's
header appears in neither PR**, making it the only model in the family with
**zero ROCm overflow mitigation**. The candidate fix mirrors that pattern:
ROCm-guarded `set_force_prec_f32(true)` on the attention out-projection and the
feed-forward second linear (the setters already exist locally), rebuild the HIP
tree for gfx90a, and re-run the failing case at fixed seed across 896 / 960 /
1024. Supporting inference: `--vae-tiling`, `--vae-on-cpu` and CPU-RNG were
already ruled out, which points **away from the VAE and at the DiT emitting
non-finite latents**, and a failure threshold sitting between 896 and 960 is what
accumulation overflow looks like. **This is a candidate fix, not a diagnosis** —
and it needs no new model and no new weights.
[`gpu-acceleration-path.md`](../handoffs/active/gpu-acceleration-path.md) §2026-07-29 Stage-2 dive

### A durable control-selection rule: controls must be mitigation-matched

The proposal to run the alternative model as a **diagnostic control** for the
blank-PNG bug is **withdrawn as confounded**: its header carries an explicit ROCm
workaround that the deployed model lacks entirely, so a passing run says nothing
about the failing model's code path. If a second model is wanted as a control it
must be **mitigation-matched** — here, the family member whose guard is
Vulkan-only at our pin. Generalization: a control differing from the subject in
*the very dimension under test* is not a control.
[`gpu-acceleration-path.md`](../handoffs/active/gpu-acceleration-path.md) §Control-probe note;
[`ernie-image-turbo-evaluation.md`](../handoffs/active/ernie-image-turbo-evaluation.md) §2026-07-29 corrections

### A pre-deployment assessment ages badly in specific, predictable ways

The deployed image model's deep dive was written as a **pre-deployment**
assessment; filing its intake row 12 weeks later (`intake-937`, 2026-07-29)
forced a line-by-line reconciliation against production reality. Four of its
premises had rotted, and the *pattern* of rot is the transferable part:

- **Backend premise struck.** The dive planned around a Python inference stack
  and flagged "upstream support unverified" as an open question. Upstream had
  in fact shipped native support (441 lines), and that has been the production
  serving path since the week after the dive. **Availability questions expire
  fastest** on fast-moving projects — the dive's own §"scan the upstream source
  before planning the port" lesson applied to itself one section later.
- **Latency forecast falsified.** Predicted 30–120 s/image on this host;
  production measures ~188 s at 1024²/8 steps — optimistic by 1.6–6×. Retired,
  not adjusted: a forecast that missed by that margin has no residual value.
- **Hardware extrapolation dead.** An entire section extrapolated to a machine
  that was never acquired. The actual accelerator is a different vendor
  entirely. **Extrapolations to unpurchased hardware should be dated and
  quarantined**, because they read as measurements to later readers.
- **A hypothesis the dive itself doubted was confirmed.** It called the
  "distilled models amplify quantization damage" claim community folklore and
  judged it *partially falsified* for this regime, on the strength of a
  competitor's A/B. Our own A/B then confirmed it for this model — the cheaper
  quant bought 17% wall-clock and corrupted in-image text, i.e. degradation
  landed precisely on the model's signature differentiator. Both survive: the
  higher quant is safe as predicted, *and* the cliff arrives on the
  text-rendering axis exactly where the dive hypothesised.

One disagreement remains **open**, not resolved: the dive describes a bespoke
128-channel VAE with portability implications, while the bundle actually
deployed ships a VAE from a different model family. Neither vendor card names
the VAE, so no source can adjudicate — recorded as open rather than settled in
either direction.

### Source References

- [`ernie-image-turbo-evaluation.md`](../handoffs/active/ernie-image-turbo-evaluation.md) — struck stale-backend premise (header present at the pinned commit, deployed binary built from it); LongText-Bench harmonization and the surviving validity question; withdrawal of the confounded control; the 2026-07-29 intake-row filing
- [`research/deep-dives/ernie-image-turbo-dit-text-to-image.md`](../research/deep-dives/ernie-image-turbo-dit-text-to-image.md) — the pre-deployment assessment itself: the backend premise, the CPU latency forecast, the retired hardware extrapolation, the quantization-damage hypothesis, and the unresolved VAE identity
- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — the six folded corrections and the vendor-default-resolution sting (the GPU defect blanks the first resolution the vendor recommends)
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — Z-Image-Turbo scoped as a latency-only candidate; the distill-patch LoRA conversion mechanism and its untested assumptions
- [`gpu-acceleration-path.md`](../handoffs/active/gpu-acceleration-path.md) — the ROCm f16-overflow campaign gap and the f32-precision candidate fix; the mitigation-matched-control rule

## Compiled Update — 2026-07-31: TTS is solved, and the fix was to stop writing our own codec

**Confidence: verified (measured on this host).** The long-standing TTS blocker — archived at
`Phase 4 BLOCKED` with the note that our Qwen3-TTS llama.cpp port "produced unintelligible noise" —
is resolved. It was **not** resolved by the debug step the handoff documented (diff C++ vs PyTorch
codec tokens, never executed, now cancelled). It was resolved by discarding our port.

### The generalizable lesson: we hand-rolled the half that broke

Qwen3-TTS is two halves — an LM half (Talker + MTP CodePredictor) and a **codec half**
(SEANet / ConvNeXt / DAC vocoder). Our port implemented the LM half against llama.cpp's existing
machinery and hand-rolled the codec. The noise came from the hand-rolled half. Upstream
**`qwentts.cpp`** (ServeurpersoCom) implements **both**, including the speaker encoder, and works
first try.

This is the same shape as several entries already in this page — the LocateAnything PBD analysis
("a GGUF would run only the AR-fallback path, forfeiting the ~2.5× that is the model's entire
value") and the Qwen3-TTS MTP-codec precedent it explicitly cites. The recurring rule:

> **When a model's value lives in a custom decode loop or a neural codec, porting the transformer
> half buys nothing. Check whether someone has already ported the whole thing before writing any of
> it.**

The cost of not checking here was months of a blocked handoff plus a C++ accelerator whose source
was subsequently lost — and which, it turns out, never worked.

### Measured — first working speech synthesis on this host, ever

CPU, `Qwen3-TTS-0.6B-base` Q8_0 + `qwen-tokenizer-12hz` Q8_0 (1.19 GB total):

| metric | value | why it matters |
|---|---|---|
| **round-trip WER** | **0.0 %** | synthesized a sentence, transcribed it back with the incumbent whisper, word-perfect. This *is* the intelligibility check the archived handoff never ran — the one that would have caught the noise. |
| **TTFA** | **67.9 ms** | time to first audio; viable for streaming voice |
| total wall | 6820.7 ms for 5.84 s audio = **0.86× real-time** | faster than real-time on CPU alone |
| **`CodecDecode`** | **4362.9 ms = 64 % of wall** | the bottleneck is the **convnet vocoder, not the LM** |
| Talker / CodePredictor | 1313.7 ms / 1091.8 ms | together only 35 % |

**The profile is the finding.** A speech stack whose cost is 64 % convnet is a *GPU* workload, not
an LM-optimization workload — which inverts where effort should go. A GPU bench was in flight at
compile time; no number is recorded here for it.

### A third-party patch is not a kernel change — and the distinction is worth stating

Building `qwentts.cpp` with HIP for gfx90a needed exactly one line: its vendored
`ggml/src/ggml-cuda/vendors/hip.h` guarded FP8 on `HIP_VERSION >= 60200000`, but the OCP-format
`__hip_fp8_e4m3` type only exists from **ROCm 6.3**. This host runs **6.2.0-66**, which ships only
`__hip_fp8_e4m3_fnuz` — so the header included `hip_fp8.h` and then typedef'd a nonexistent type
(`error: unknown type name '__hip_fp8_e4m3'`). Raising the guard to `60300000` is free here because
**gfx90a has no FP8 hardware**; kernels gate on `FP8_AVAILABLE` and fall back.

The governance point: the experimental-kernel workflow (fresh-pull → build → validate → deploy as a
new production version) governs **our** kernel tree. A patch inside a third-party repo's vendored
copy is not in that tree, touches no production binary, and requires no experimental-kernel handoff.
Production `production-consolidated-v8` @ `67a433bf4` was untouched throughout.

### ASR: "it runs" and "it works" are different findings

`ggml-org/Qwen3-ASR-1.7B-GGUF` serves on the MI210 through `llama-server` with **zero kernel
change** — the frozen v8 kernel already ships `tools/mtmd/models/qwen3a.cpp` and
`libmtmd.so.0.0.10107`. That is a real, verified capability finding.

Its **WER 72.14 % is not a model verdict.** The failure has a signature that rules out quality:
utterances over ~11 s degenerate to literal `????????` while short ones transcribe perfectly, and
raising context 8k → 65536 changed WER by less than 0.01. A length-thresholded cliff with a
context-insensitive response is a **configuration** defect. Named suspect: the Q8_0-quantized audio
projector (the bf16 projector exists and is untested). Recording the *reason* rather than the number
is what keeps this from being filed as "Qwen3-ASR is bad" — the
`feedback_classify_eval_failures_by_reason` discipline applied to a serving config.

Where it did work it was roughly twice as fast per request as the incumbent (median 2.14 s vs
whisper's ~4.2 s floor), which is why the defect is worth resolving rather than abandoning.

**Superseded later the same day (2026-07-31) — see the session-3 Compiled Update below.** The
Q8_0-audio-projector hypothesis above did not hold; the WER figure also moved (72.14 % here →
29.36 % in the later retest). The verdict changed from "worth resolving" to **DROPPED**: the real
mechanism is a duration-correlated degenerate repetition loop, not a quantization or context defect,
and whisper.cpp's own numbers (below) removed the incentive to keep debugging it.

### STT: an optional role failing silently is worse than a required role failing loudly

`whisper_server.py` passed a model **name**, not a path, so `faster-whisper` resolved it through
`huggingface_hub` and reached out to the network on **every cold start**. Because whisper sits in
`OPTIONAL_AUXILIARY_ROLES`, the failure mode was **silent**: no network, no speech, no error anyone
would see. Fixed with `local_files_only=True` plus `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`, gated
behind an explicit `WHISPER_ALLOW_DOWNLOAD=1`; cold load is 1.42 s offline.

The durable lesson generalizes past speech: **a model referenced by name is a network dependency**,
and combining that with fail-silent optionality produces an outage nobody detects. Pair with
`feedback_fail_open_defaults_conceal_their_own_corruption`.

### Source References

- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — the ✅ TTS-unblocked banner, Path E vs Path C, and the S-1..S-11 speech task block (S-7 bf16 projector, S-9 `start_tts()` wiring, S-10 whisper-vs-Qwen3-ASR decision)
- [`../handoffs/archived/qwen3-tts-voice-synthesis.md`](../handoffs/archived/qwen3-tts-voice-synthesis.md) — the archived `Phase 4 BLOCKED` record, now carrying a resolution pointer; retained as historical ledger, explicitly not resurrected
- [`numa-topology-cutover-resume-20260730.md`](../handoffs/active/numa-topology-cutover-resume-20260730.md) — §Speech (the whisper false-negative correction, the `start_tts()` gap, the lost accelerator source) and the scoped temperature ruling that governs the in-flight production-temperature re-runs
- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — full session record: measurements, the FP8 guard diff, the ASR failure signature, and the two operational incidents
- [`master-handoff-index.md`](../handoffs/active/master-handoff-index.md) — rows **N27** (speech) and **N28** (speculative decoding is launch-fixed)

## Compiled Update — 2026-07-31: speculative decoding has no per-request surface on v8

**Confidence: verified (read from frozen production source; not empirically probed).**

Filed here because it constrains every pipeline that hoped to vary drafting per request. On
`production-consolidated-v8` @ `67a433bf4`:

- **`--spec-type` is launch-only** (`common/arg.cpp:3935`). Which drafters are active is fixed when
  the server starts.
- **The per-request fields are compiled out.** `tools/server/server-schema.cpp` registers
  `speculative.n_max` (208), `n_min` (212), `p_min` (216), `speculative.type` (220) and
  `ngram_size_n`/`size_m`/`min_hits` (226/229/232) — **inside `#if 0`, opened at 206 and closed at
  234**, under the upstream comment *"to keep things simple, we disable speculative parameter
  adjustments for now"*.

**The trap that makes this worth compiling.** `tools/server/README.md` shows `speculative.n_max` in
JSON at three places (768-820, 917-967, 982-1032) — but those are **`generation_settings` echoes of
the launch defaults**, not accepted request fields. Reading the schema registration and the README
together produces a confident, wrong conclusion that the knob is live. This is
`feedback_verify_negatives_before_concluding_absence` in mirror image: a *positive* existence claim
built from two artifacts that each look like evidence and neither of which is.

Consequences: autopilot cannot dial the draft budget per call, cannot skip drafting for a single
request, and cannot disable ngram selectively (that needs separate server instances). Enabling any
of it is a kernel change — a new production version through the four-step workflow, never a patch to
the frozen tree. The composed recipe's ~1.6 % cost is therefore unconditional on every drafted
request, and its sole justification (the repetitive-context upside) was retracted the previous day.

### Source References

- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — the source-read section and tasks SW-1..SW-4 (SW-2 confirms against a live server; SW-3 decides whether a per-request surface is worth carrying into v9)
- [`inference-acceleration-index.md`](../handoffs/archived/inference-acceleration-index-history-through-2026-06-19.md) — the structural-fact banner above the retracted ngram row
- [`master-handoff-index.md`](../handoffs/active/master-handoff-index.md) — row **N28**
- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — §10, with the exact line numbers and the README-echo explanation

## Compiled Update — 2026-07-31 (session 3): vision role settled on MMMU, MiniCPM-o retired, speech finalized after the gfx90a ARGSORT fix

**Confidence: verified — measured on this host, with persisted artifacts for every number below.**

### MiniCPM-o-4.5 is deprecated and its weights are deleted

The multi-month `vision_escalation` candidacy this page has tracked since 2026-07-17 (the MI210
`--reasoning off` lane, the 2026-07-23/24 deterministic promotion runbook, the 2026-07-26 bounded
M-1 observation) is **closed, not merely paused**. A 42-question OCRBench+ChartQA re-score, each
model at its best on-disk quantization, found MiniCPM-o-4.5 a **downgrade versus the deployed
incumbent**:

| model | score |
|---|---|
| Qwen3-VL-30B-A3B Q4_K_M | 36/42 |
| Qwen2.5-VL-7B (incumbent) | 35/42 |
| Qwen3-VL-8B Q8_0 | 33/42 |
| **MiniCPM-o-4.5 Q8_0** | **31/42** |
| Qwen3-VL-4B Q8_0 | 29/42 |

The earlier "+10pp" paired observation (M-1, n=10, 2026-07-26 Compiled Update above) does not
survive re-verification: it rested on exactly one discordant question that was a scoring artifact
(the incumbent answered `0.11 kWh` where the accepted answer was `0.11`, `vl_chart_test_0563`);
corrected, the arms tie 7/10. The remaining argument for MiniCPM-o was its bundled speech stack —
also moot, since a dedicated Qwen3-TTS-12Hz-0.6B (1.14 GB, CPU-only, zero GPU VRAM) and Qwen3-ASR
(served by the frozen v8 kernel with **zero kernel change**) replace the ~9.70 GB speech delta
inside MiniCPM-o's 22 GB omni bundle. Operator-authorized: deprecate, then delete (in that order,
to leave no dangling reference behind the 22 GB `rm`); storage reclaimed.

### Vision role settled: Qwen3-VL-30B-A3B Q4_K_M wins MMMU val; the 8B and 4B are not separable from the incumbent

MMMU val, 250 stratified multiple-choice questions, identical rows for every arm, `temp=0.2`,
`seed=42`:

| arm | accuracy | vs incumbent | McNemar p | VRAM |
|---|---|---|---|---|
| **Qwen3-VL-30B-A3B Q4_K_M** | **63.6%** | **+11.2pp** | **0.0011** | 21.0 GB |
| Qwen3-VL-8B | 57.2% | +4.8pp | 0.21 (n.s.) | — |
| Qwen3-VL-4B | 54.0% | +1.6pp | 0.72 (n.s.) | — |
| Qwen2.5-VL-7B (incumbent) | 52.4% | — | — | — |

Raw: `/mnt/raid0/llm/tmp/vision_final_results.json`. Only the 30B-A3B is statistically separable
from the incumbent — **the 8B and 4B must not be described as upgrades.**

Two methodology findings surfaced by this run are compiled in full on
[Benchmark Methodology](benchmark-methodology.md); summarized here because they directly gate this
decision: (1) the **earlier 42-question OCRBench+ChartQA suite (the same one that retired MiniCPM-o
above) mis-ranked the field** — it placed the incumbent 2nd where MMMU placed it last, and the 8B
inverted between the two suites, so a saturated suite can order arms **wrongly**, not merely fail to
separate them; (2) a **`max_tokens=128` cap silently penalised the Qwen3-VL models** (3 parse
failures for the incumbent vs 41 and 50 for the Qwen3-VL arms — truncated mid-reasoning and scored
wrong), and even at `max_tokens=2048` those models emit no letter on ~9% of hard questions, so **the
vision role requires `max_tokens ≥ 1024`**.

### STT settled: whisper.cpp large-v3-turbo f16 on MI210; Qwen3-ASR DROPPED

| metric | CPU incumbent | MI210 whisper.cpp | |
|---|---|---|---|
| WER | 2.35% | ~~**2.35%**~~ **3.37%** (corrected 2026-09-24) | ~~identical~~ no detectable difference at n=100 |
| wall median | 4.240 s | **0.124 s** | 34× |
| wall max | — | **0.218 s** | GPU max is **19× below the incumbent's minimum** |
| encode | 3751 ms | **110 ms** | 34× |
| VRAM | — | 2.56 GB | frees 48 CPU cores |

**Correction (2026-09-24):** the MI210 whisper.cpp WER was **3.37%** (63/1870 words, bootstrap 95% CI [2.26, 4.67]),
not 2.35%. The 2.35% came from the faster-whisper CPU arm of the same results file (44/1870, CI [1.56, 3.20]) and
was copied into the freeze receipt as whisper.cpp's anchor. The two intervals overlap heavily, so "identical" was
never supportable in either direction. Fixing the ratified receipt is a human-only superseding-receipt amendment
(conversation-stack CS-2). Source: Annex S [`speech.md`](../measurement/protocols/speech.md), the receipt-defect note
and Appendix S-A.

Greedy decoding (not beam-5), `large-v3-turbo` (not `large-v3`). **The ~4.2 s fixed floor is gone** —
that floor (30 s mel padding, paid regardless of utterance length) is precisely what disqualified CPU
whisper for conversational voice, and is the whole reason this arm was worth running.

**Qwen3-ASR is DROPPED**, superseding the provisional reading two sections above. Its 29.36% WER is
**not** a scoring artifact — extended normalization moved it only to 28.88%. It is a **degenerate
repetition loop on 21 of 100 rows contributing 94.7% of all errors**, duration-correlated (0% of
rows under 3 s, 50% at 7–30 s). Clean rows score 2.27% — the *model* is sound and the *deployment* is
broken. Moot either way: whisper.cpp is faster with a far tighter tail, so debugging the projector
has no payoff.

### TTS settled: Qwen3-TTS-12Hz-0.6B Q8_0 via qwentts.cpp on MI210 — the post-ARGSORT-fix numbers

These numbers **supersede** the pre-fix CPU-only reading in the "TTS is solved" Compiled Update
above (xRT 0.86×, `CodecDecode` 64%) — that section recorded the *before* state; this is the *after*
state on the same host, same model, following the gfx90a kernel fix below.

| metric | before (CPU) | after (MI210, fixed) | |
|---|---|---|---|
| xRT | 0.86× | **5.47×** | 6.4× |
| TTFA | 67.9 ms | **37.8 ms** | |
| `CodecDecode` share of total | 64% | **10.4%** | 39× faster per audio-second |
| round-trip WER | 0.0% (canonical sentence) | **1.49%** (broader set; 0.0% on the canonical sentence) | |

Under `--greedy`, GPU and CPU transcripts are **identical**. New bottleneck is `CodePredictor` at
65.5%.

Getting there required a real kernel fix in the **third-party fork**, not our production kernel: an
**ARGSORT defect on gfx90a** (`ne0=2048` launched 2048 threads per block against gfx90a's
1024-thread cap, 705× per utterance) was masked by a test suite that silently skipped the failing
shapes. Full mechanism, the fix, and the HIP-graphs consequence are compiled on
[Hardware Optimization](hardware-optimization.md) — not repeated here to avoid drift between the two
pages.

**Pins**: qwentts.cpp `abab6b3b`, ggml fork `c044c6f0`, binary md5 `5b858d75614dfd2f696071212ae8f2e4`.
Production llama.cpp kernel untouched (`67a433bf4`). **Operator decision: keep qwentts.cpp as a
pinned versioned dependency — do NOT merge it into our llama.cpp.** Running the patched fork
indefinitely is acceptable.

### Resulting GPU resident set

| resident | GB |
|---|---|
| 27B Q8_0 | 27.0 |
| Qwen3-VL-30B-A3B | 21.0 |
| whisper.cpp large-v3-turbo | 2.6 |
| Qwen3-TTS | 1.2 |
| **total** | **≈51.8 of 64** |

≈12 GB left for KV → the 27B tops out near **90k tokens** on `q8_0` KV. A KV-quantization quality
test was in flight at compile time to establish whether `q4_0` buys ~180k without a quality cost —
no number recorded here for it.

### Source References

- [`progress/2026-07/2026-07-31.md`](../progress/2026-07/2026-07-31.md) — §15 (all four sub-findings: vision, STT, TTS, resident set), §20 process lessons
- [`multimodal-pipeline.md`](../handoffs/active/multimodal-pipeline.md) — the MMMU table, the S-6/S-6a/S-7 task closures, the S-17 resident-set budget task, and the ✅ vision/STT/TTS status banners
- [`docs/reference/model-probe-scoreboard.md`](../docs/reference/model-probe-scoreboard.md) — the superseded "Yes candidate" rows corrected with the 42q table; Qwen3-VL-30B-A3B added and unpaused
- [`docs/runbooks/vision-escalation-minicpmo-promotion.md`](../docs/runbooks/vision-escalation-minicpmo-promotion.md) — DEPRECATED banner; runbook mechanics survive as a model-agnostic reference pattern
- [Hardware Optimization](hardware-optimization.md) — the gfx90a ARGSORT defect mechanism, the fix, and the HIP-graphs consequence
- [Benchmark Methodology](benchmark-methodology.md) — the saturated-suite mis-ranking and `max_tokens` truncation findings in full

## Compiled Update — 2026-08-30: MiniMax-H3 — the page's first video-generation candidate, omni-modal by construction, gated on a scope decision before any download

**Confidence: mixed** — model/architecture facts and deployment arithmetic are card/community-record facts from the EVL-32 session (`upstream-published` for model-card claims, `verified` for the disk math as arithmetic); **nothing has been downloaded, built, or run** — no H3 artifact exists on this host.

MiniMax-H3 is the first video-generation candidate on this page, and its pipeline precedent is ERNIE-Image-Turbo rather than any llama.cpp role: an omni-modal diffusion model (text/image/video/audio in → video + native 32 kHz stereo audio out) served via SGLang/vLLM/diffusers/ComfyUI, out-of-band from the llama.cpp kernel tree [handoff](../handoffs/active/minimax-h3-video-generation-evaluation.md). The architecture is a **33B dense** H3-Omni-Transformer (~13B in cacheable AdaLN branches, inference-prunable to ~20B) with a Qwen3-VL-**32B dense** encoder — a sibling family of, not the same variant as, the deployed Qwen3-VL-30B-A3B MoE vision role [progress](../progress/2026-08/2026-08-30-opencode.md). Two task-specialized checkpoints share the architecture: FL2VA (0/1/2 reference images) and Ref2VA (≤9 images, ≤3 videos, ≤3 audio clips, ≤12 files, 2–15 s each), which strictly supersets FL2VA's input modes. Output is 4–15 s at 24 FPS, 32 kHz stereo audio, 21:9–9:16; 768p is the local default and 2K exists only via the API-only H3-Regenerate-2K path [handoff].

The deployment path under consideration is **Ref2VA base (~144 GB) + TenStrip/10Eros-Max beta4 INT8 convrot transformer (21 GB) as a transformer-only drop-in ≈ 165 GB total** [handoff]. Disk math from 2026-08-30 says it fits but barely: the single 3.7 TB RAID (`/dev/md127`) backing `/workspace` + `/mnt/raid0/llm` had 291 GB free (92% used), so 165 GB would leave ~126 GB (~95.5% full) — and the handoff requires headroom to be re-verified immediately before any download [handoff][progress]. The first gate is therefore **not technical but a scope decision**: video generation has no identified product demand, and "interesting model" alone is not a reason to consume 165 GB on a 92%-full volume; the handoff is explicitly closeable on a no [handoff].

Two governance-relevant findings ride along. **NSFW capability is a training-data story, not a refusal story**: the base weights carry no refusal circuit, and adult-content filtering makes the base weak at explicit content rather than refusing — TenStrip/10Eros-Max (403 likes, the main NSFW finetune) had to *graft* NSFW attention-layer weights from Wan 2.2 / LTX 2.3 / Krea 2 into H3, and "UNCENSORED" LoRAs add absent capability rather than removing a refusal mechanism; hosted moderation (H3-Context-IR) is API-side only, so a content-filter audit of local output is warranted before any production use, mirroring the ERNIE audit pattern (PIP-03) [handoff]. **License**: the MiniMax H3 Community License excludes EU, UK, KR and US territories — use there requires an application — and guardrail-bypass via uncensored LoRAs would be an AUP #5 breach; recorded as a governance note only, not a gate on the capability evaluation [handoff].

Key findings:

- **A 56-model community quantization landscape already exists** — GGUF (including ~20B AdaLN-pruned inference-only builds and a full-33B build with a separate encoder GGUF), NVFP4, FP8, W4A16-RTN / w4a8 / INT4MixedConvRot, MLX 4/8-bit, NF4 — so adoption would involve no conversion work, only a variant choice [handoff].
- **Single-MI210 serving feasibility is unconfirmed**: the SGLang reference deployment is 4 GPUs at ulysses-degree 4, and the cookbook's ~2.4 GB/K figure is not transferable without measurement; the ~21 GB INT8 transformer on the 64 GB MI210 stack is the open serving question [handoff].
- **No intake row exists yet** — EVL-32 was created directly at intake, mirroring the intake-937 ERNIE precedent; the verdict will be `new_opportunity` or `already_integrated` once adoption is decided [handoff][progress].
- **Everything downstream of the scope decision is enumerated but gated**: 768p quality smoke on the model card's reproducible scripts (T2VA/FL2VA/Ref2VA cases), single-MI210 confirmation, the content-filter audit, and the license-compliance note all wait on the operator's yes/no [handoff].
- **10Eros-Max beta4 (released 2026-08-29) fixed the beta3 turbo corruption** in i2v/reference starts; it runs t2v + i2v + reference modes at euler/simple 6–8 steps, with no cache/spectrum in reference mode [handoff].

### Source References (2026-08-30)

- [`minimax-h3-video-generation-evaluation.md`](../handoffs/active/minimax-h3-video-generation-evaluation.md) — the EVL-32 record: model facts, community quantization landscape, NSFW-capability evidence, the Ref2VA + beta4 INT8 deployment path, the 2026-08-30 disk math, and the open-question list with the scope decision as first gate.
- [`progress/2026-08/2026-08-30.md`](../progress/2026-08/2026-08-30-opencode.md) — the session record: EVL-32 creation, the Qwen3-VL-32B-dense vs 30B-A3B-MoE family note, the disk math, and the `index_state.py --check` green.

## Compiled Update — 2026-09-25: LensVLM Selective Visual Expansion

LensVLM contributes a selective-expansion pattern for visual language inference: begin from a compact visual representation and allocate additional visual tokens only where the model predicts that more detail is useful. The mechanism is relevant to local multimodal routing because it turns visual-token allocation into a measurable policy rather than a fixed preprocessing constant.

The integration path starts with the official BF16 implementation and checkpoint behavior. Only after that baseline is reproduced should a local MI210 adaptation change precision, kernels, or serving layout. The evaluation must keep visual indexing, reader input semantics, answer scoring, and selective-expansion policy distinct. Expansion-cost reduction is not useful if the reader silently receives different evidence or if answer quality falls outside the declared tolerance.

Parent-model provenance remains a dependency for license, tokenizer, image processor, and architecture compatibility. Each run should preserve the exact checkpoint revision, preprocessing configuration, selected regions or token budget, answer outputs, latency, peak memory, and environment identity. ECR-style efficiency summaries can describe the expansion tradeoff, but they do not replace answer-quality and robustness checks.

### Source References

- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md)
- [Eval Tower verification](../handoffs/active/eval-tower-verification.md)
- [Vidya belief substrate program](../handoffs/active/vidya-belief-substrate-program.md)
- [Session research-intake progress](../progress/2026-09/2026-09-25.md)

**Confidence:** verified against the cited LensVLM intake handoff; no local MI210 reproduction has yet promoted the external claims to measured evidence.

## Compiled Update — 2026-09-25: LensVLM Is Triggered by a Measured Need

The official BF16 reproduction is no longer immediate backlog. It activates only when visual-token
processing is a measured latency, memory, or quality bottleneck on an EPYC workload, or when a named
deployment requires LensVLM. At that point provenance resolution comes first, followed by the isolated
official demo and a small prepared sample with the prospective `VB-LENS-1` receipt. Until the trigger fires,
LensVLM remains a monitor record and carries no active checkbox or index action.

### Source References

- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — MM-LENS trigger and staged execution.
- [Eval Tower verification](../handoffs/active/eval-tower-verification.md) — minimum research-screen controls.
- [Vidya belief substrate program](../handoffs/active/vidya-belief-substrate-program.md) — prospective Lens receipt trigger.
- [Research-intake Stage 3 progress](../progress/2026-09/2026-09-25.md) — action-distillation disposition.

**Confidence:** verified as repository execution posture; external LensVLM performance remains unmeasured locally.

## Compiled Update — 2026-09-26 (research-intake orch-prior-art): the 150–220 GB/s CPU bandwidth figure is pre-BIOS

*Correction 2026-09-26:* the "Decode-usable CPU bandwidth is about 150–220 GB/s, not 460" line in *Corrections to the operator draft* (Speech-native interlocutor program, above) is pre-BIOS. Since 2026-09-21 a full-screen read-sum measures 446.8 GB/s at t96 and 449.4 under load. A ~250 GB/s decoder is no longer excluded by the ceiling alone; whether it fits beside a -t 96 LLM is the contention question (CPU speech collapses next to a `-t 96` CPU LLM).

### Source References

- [Conversation stack](../handoffs/active/conversation-stack.md) — the same correction, dated 2026-09-26, under *Facts that constrain the design*.
- [CPU decode roofline program](../handoffs/active/cpu-decode-roofline-program.md) — C8 and the post-BIOS supersession note (`epyc-inference-research/data/bios-postreboot-20260921/`).
- [DeepSeek-V4.1-Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — DS41-C36, the 449.4 GB/s re-read.

**Confidence:** measured (read-sum microbench, one host; the 449.4 re-read was not on an idle host).


## Compiled Update — 2026-10-03: vision leaves the MI210

**Confidence: verified** (`locally-measured`) for the placement change, the VRAM arithmetic and the refusal latency.
CPU throughput and quality at the new placement are **unmeasured** (S-18).

- **Qwen3-VL-30B-A3B-Instruct-Q4_K_M + mmproj F16 (`worker_vision` / `vision_escalation`, :8086) is off the card**
  since `RATIFY-STACKCHG-DFLASH2-20261003`.
  - Placement: device `none`, tier WARM (a default `start` does not launch it), NUMA_HALF_A (cores 0-47 + 96-143,
    `-t 48`, `--interleave=0,1`, pre-evict 40 GiB/node).
  - Why: DFlash2 on :8083 holds 44.30 GiB, and the VL needs 19.26 + 3.19 GiB, so 66.75 > 62.00 GiB.
  - The GPU figures stay in the master as the restore record. The operator reassesses placement when the second
    MI210 arrives.
  - Start it on demand with `orchestrator_stack.py start --only worker_vision`; its cores overlap the frontdoor.
- **Open follow-ups:**
  - **S-18:** on the first start, measure decode tok/s paired with an MMMU parity slice against the 63.6% MI210
    figure. The only CPU evidence is from `-t 96` (2026-07-17).
  - **S-19:** re-bench `worker_vision`'s contention pairs before it is made HOT again. The old pairs were moved to
    `unknown_pairs` (`placement_withdrawn`), a declared withdrawal, not a re-measurement.
  - **S-20:** with :8086 down, an image request is correctly refused, but only after 27.9 s. `chat_vision` tries
    :8086 as two roles and then POSTs `/vision/analyze`; it should short-circuit when no vision server is listening.
- **Voice routing to :8083 is unimplemented.** "Voice turns reason on the :8083 27B" (KVU-11; the role is
  `architect_critic` since ARCHSWAP-20260927) exists in docs only, with no routing code. CS-17 implements it as
  configuration.

### Source References

- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — the cold-CPU note, S-18, S-19, S-20.
- [2026-10-03 workspace-ec progress](../progress/2026-10/2026-10-03-workspace-ec.md) — the vision move and the 27.9 s refusal.
- [Current campaign](../handoffs/active/CURRENT-CAMPAIGN.md) — the 2026-10-03 GPU posture block.
- [Stack-change governance pipeline](../handoffs/active/stack-change-governance-pipeline.md) — STACKCHG-DFLASH2.
- [Conversation stack](../handoffs/active/conversation-stack.md) — CS-17: voice routing is unimplemented.

## Compiled Update — 2026-10-20: the conversation stack gains turn-taking instruments, and the vision embedders have nothing to screen yet

**Confidence: verified** for what the handoffs now file; no turn-taking or retrieval number exists yet, so nothing here is a result.

The conversation-stack handoff received the turn-taking evidence program from the 2026-10-20 full-duplex research intake: instruments CS-45 to CS-49 and four durable triggers (M8 to M11). The dependency order is CS-45 then CS-46 then CS-47, and CS-45 then CS-48 then CS-49, with CS-49 also needing the CS-21 live services; after CS-45 the two lanes run concurrently. CS-47 is the pre-declared CS-22 turn-end arm bake-off and CS-49 the CS-23 barge-in ablation. They add measurement only: CS-22 and CS-23 stay open for the controller implementation, the frozen speech kernels and the production llama.cpp trees are untouched, and CS-2 consumes the CS-45 measurand note only when its Annex S package is prepared (a human-only boundary, so no package text was written). One prior-art item (K3) is kept without work. The belief-kernel write side for both bake-offs is filed as an extension of the existing conversation-stack family, with `metric_direction` carried per metric.

On the vision side, the multimodal-pipeline handoff records an owned trigger for embedder-upgrade screens: on 2026-10-20 the Chroma `descriptions` (384-d MiniLM) and `images` (512-d CLIP) collections and `vision.db` were empty (0 embeddings, 1 photo, 0 descriptions). A side-by-side EmbeddingGemma 2 fit screen runs only when the descriptions collection supports a labelled screen of at least 120 queries, or the operator names a text-to-photo search task; until then the MiniLM and CLIP routes do not change. The pinned manifest for that screen is REPL-EMB-2.5.

### Source References (2026-10-20 multimodal delta)

- [Conversation stack](../handoffs/active/conversation-stack.md) — turn-taking evidence program, CS-45..49, durable triggers.
- [Multimodal pipeline](../handoffs/active/multimodal-pipeline.md) — embedder-upgrade screen trigger and the empty-collection observation.
- [Vidya belief-substrate program](../handoffs/active/vidya-belief-substrate-program.md) — conversation-stack write-side extension.
- [Non-inference backlog](../handoffs/active/non-inference-backlog.md) — unrelated current-state context only.

## Compiled Update — 2026-10-21: turn-end synthetic results, the speech threadpool fold (qwentts passed, whisper missed its target), and corpus lessons

**Confidence: verified for the recorded measurements (each one run, each with its artifact); nothing here advances a turn-end arm.** The `human_recorded` stratum of the CS-45 corpus is still empty, and only that stratum can advance an arm (`corpus.json` keeps `advance_eligible_strata = [human_recorded]`; [turn-taking measurands](../docs/reference/speech/turn-taking-measurands.md) section 0 rule 3), so every number below can only rank or reject.

- **CS-47 synthetic accuracy legs: no arm meets the 0.10 false-cut budget on selection.** The incomplete clips carry 2.0 s of digital silence after the cut, so every silence-gated or acoustic arm fires on nearly all of them (silence 1.000; Parakeet-EOU 0.972 to 1.000, including the no-fallback rows). Smart Turn behind the Silero gate (gate 0.6, theta 0.9) discriminates a little: false-cut difference -0.333 against the nearest-latency silence row, paired cluster-bootstrap 95% CI [-0.515, -0.181]; extending its threshold on selection only to FPR <= 0.10 costs recall <= 0.017. Parakeet-EOU ties its matched silence row (difference 0.000). The latency leg is staged, not run, and the adaptive-timeout arm has no result yet (evidence: research `artifacts/cs47_turn_end_bakeoff_20261020/`; [conversation stack](../handoffs/active/conversation-stack.md), CS-47 note).
- **Design insight recorded, not a task edit.** CS-22's text names a silence threshold as the policy and calls a semantic end-of-turn optional; the CS-47 evidence points toward a semantic-gated design (a model decides complete vs incomplete, silence only gates it) as the candidate default. The Unmute reference uses a model pause head thresholded 0.6 / 0.4 rather than a silence timer (`intake-2054#record`). Model-only latency is kept separate from any wrapper gate (measurands section 2.2).
- **A native full-duplex interlocutor does its own turn-taking**, which is an alternative to the CS-22 controller policy; measure it with the same CS-45 corpus, the CS-48 barge-in harness and the same denominators as the cascade. PersonaPlex / Moshi was marked BLOCKED only because llama.cpp lacks the architecture; under the platform rule that is a porting question, and it is English-only so it can be at most a reference slot (conversation-stack, "Accumulated insights", 2026-10-20). Full-Duplex-Bench v1 `pause_handling` is the existing instrument for "the user pauses mid-turn and the model must not take the floor" (TOR lower-is-correct there).
- **CS-45 v2 corpus lessons.** QA must be a human ear plus an independent ASR: QA that reuses the corpus's own build tools is circular (v1 failed 12 of 20 sampled pairs while its own QA marked every cut clean). The verifier and the consumer tool must share one assembly function (`tt_corpus.assemble_row()`), cross-tested: `tt_materialize` aborted on CTX_BC clips that `tt_verify` passed because the latter alone applied the per-pair layout tail; after research `beeb3a352` a clean checkout materialises 278/278 clips and passes the 13 verify checks. Whisper-family ASR also hallucinates a plausible continuation after a truncated utterance, so an exact-transcript gate on a cut clip is deliberately strict and predictable-next-word sentences were dropped, not waived (conversation-stack, CS-45 notes).
- **The qwen-tts slowdown is core sharing, not thread count.** `ggml_barrier` is a pure `_mm_pause` spin and qwen-tts builds a disposable pool per graph compute, so one descheduled thread stalls all N. On a quiet region 8 threads is about 4x faster than 1 (38.3 vs 94.4 ms/frame total); with 8 spinners on 8 pinned cpus it reaches 9754 ms/frame; perf shows almost all samples spinning in `ggml_graph_compute_thread`. Rule: use N threads only on cores nothing else runs on, otherwise one thread per process (`artifacts/qwentts_threads_20261020/`; speech-v2 manifest SP2-009).
- **Threadpool plus non-spinning barrier fix, folded into the speech CHAMPIONS 2026-10-21 (fast-forward; nothing promoted, production-speech-v1 untouched).** `champion/speech-qwentts` `2c1b518` to `b1a1ec7` (carries the ggml pointer bump), `champion/speech-qwentts-ggml` `b86f6602` to `05e1ad6c`, `champion/speech-whisper` `b3073792` to `fa5321e4`; both gfx90a patches kept (G-ANC holds). Correctness: greedy identity vs production on 10 texts (WAV/PCM sha, codec ids, 25 dump tensors) and 10 whisper clips at T1 and T8 in every barrier mode; CPU `test-backend-ops` 0 FAIL including `FLASH_ATTN_EXT` 5097/5097 (default and stock-spin) and 9219/9219 (stress). **qwentts passed its predeclared >=5x co-run target**: 11.3x (+1 spinner), 20x (+8), 31.6x (+ a real llama-bench neighbour, which gained 28x throughput); quiet is within A/A. **whisper missed its predeclared >=5x total-latency target at 2.4-2.5x** (correctness and quiet pass; decode phase 13-34x, but the encoder is compute-bound), so the whisper gain is real but smaller than predicted. Follow-ons filed: CS-50 whisper per-call thread spawning, CS-51 parakeet.cpp pool, CS-52 idle pool on the GPU path, CS-53 check the llama.cpp champion barrier ([progress 2026-10-21](../progress/2026-10/2026-10-21-qwentts-threadpool.md); evidence `artifacts/qwentts_threadpool_20261020/timing/timing_summary.md`).
- **Fold discipline.** [speech-v2 manifest](../docs/reference/kernel-manifests/speech-v2-manifest.md): every fold, keep or exclusion edits the manifest in the same commit (features go only into champions; the next production upgrade must be significant); a row never leaves the table; per-keep screening percentages are not additive. The whisper WER anchor is 3.37% (63/1870, large-v3-turbo f16 MI210 greedy), not the 2.35% in the ratification receipt, which is the faster-whisper int8 CPU arm; the superseding receipt is human-only.
- **Placement.** GPU host threads take CPU cores, so the second MI210's host lane affects the CPU timing floor (CS-7 requires recording it; no number exists yet). The second MI210 has arrived but is not installed; Phase 2 (whisper and qwentts onto it) becomes runnable on installation.

Sources: [conversation-stack handoff](../handoffs/active/conversation-stack.md) (2026-10-20/21 notes), [qwentts-threadpool progress 2026-10-21](../progress/2026-10/2026-10-21-qwentts-threadpool.md), [speech-v2 manifest](../docs/reference/kernel-manifests/speech-v2-manifest.md), [turn-taking measurands](../docs/reference/speech/turn-taking-measurands.md).

## Compiled Update — 2026-10-21 (sweep 5): speech placement moves to GPU card 2, and the CPU-partition measurement is declined

**Confidence: verified** for the operator ruling and the rescoped task text. No placement measurement has run; the second MI210 is not installed.

- **The ruling.** On 2026-10-21 the operator said: "When the secon GPU is installed, the frontdoor model will move to one of the GPUs". D3 is rescoped accordingly. The decisive number is now whether speech, first the cascade and then the interlocutor, can co-reside without either side missing its target. The documented lean is card 2 beside Qwen3.6-35B-A3B; the alternative is card 1 beside the 27B, if VRAM allows. CPU speech placement is kept only as the CS-26 degraded fallback.
- **CS-9 arms.** (A) card 2 with 35B-A3B at np {1, 4, 16}. (B) card 1 with the 27B at np 4 plus VL-30B, only if VRAM permits. Each arm runs the cascade and each candidate interlocutor concurrently and records p95 LLM tok/s per slot plus speech TTFA and RTF. There is no CPU arm. The CU-masking prerequisite is established: on gfx90a a disjoint mask isolates a 25% stream from a 75% one, and unmasked interference is +31% on synthetic kernels.
- **Placement proof is keyed by device.** It covers `HIP_VISIBLE_DEVICES`, ggml linkage, VRAM sampled during the run and the KFD PID count. The co-tenant state is part of the measurand.
- **CS-12 acceptance** stays STT RTF < 0.5 and TTS first packet < 1 s. It is now measured with 35B-A3B generating on the same card AND the CPU :8074 (Flash-Next) generating.
- **CS-11 declined (do not tick).** The `-t 56`@40-95 CPU partition measures a configuration that will never be deployed. The prep (a predeclared plan, a harness, frozen recipes and a dry run) is kept UNEXECUTED under `artifacts/cs11-cpu-partition-20261022/`. A relay keeps its chain flag alive for the launchers that wait on it.
- **OD-A** is filed: the operator confirms the speech host card at the CS-9 readout.
- **CS-8.L** is filed: the Italian listen check of the cascade G1 outputs needs a human ear, because agent QA of speech is circular.

Sources: [Conversation stack](../handoffs/active/conversation-stack.md), [Progress cs-rescope](../progress/2026-10/2026-10-21-cs-rescope.md), [Progress cs11-prep](../progress/2026-10/2026-10-21-cs11-prep.md), [GPU serving tie-in program](../handoffs/active/gpu-serving-tie-in-program.md), [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 12, workspace-58): the Italian TTS re-listen kit is ready; the normalizer stays eval-only

**Confidence: verified** for the job result and the page; the live-enable decision is **open** (the operator's re-listen, CS-8.L4).

- `s5-cs8l-retts` ran in a granted q3 slot (19:36-19:38Z, rc 0) and produced 15 clips, not 60: only the 10 sentences the Italian normalizer actually changes, plus 5 stress-respelling probes (àtomi, idiozìe, anàloga, Ghiza, Mariànne), at 16 kHz like round 1.
- The clips are published as a re-listen section of the Italian listen page with an A/B against each original, the round-1 rating beside it, and a better/same/worse field saved to the page's database. The normalizer stays eval-only until that re-listen is rated.

### Source References (2026-10-22 wrap-up sweep 12)

- [handoffs/active/conversation-stack.md](../handoffs/active/conversation-stack.md) — CS-8.L4 note
- [progress/2026-10/2026-10-22-3c4ca599.md](../progress/2026-10/2026-10-22-3c4ca599.md) — wrap-up 9/10
- [progress/2026-10/2026-10-22-workspace-58.md](../progress/2026-10/2026-10-22-workspace-58.md) — section 17.6 (q3 night chain)


## Compiled Update — 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23)

- **CS-5.P1a PASS: Qwen3-Omni-30B-A3B loads and is coherent on the MI210.** bf16 thinker-only, 56.19 GiB after load, 56.92 peak; ASR `ref_word_recall` 1.0, audio QA on task, text "Paris". A first attempt died on a float32/bf16 mismatch in the audio tower (fixed in `d1_probe.py`).
- **CS-5.P1c PASS: Step-Audio-2-mini audio incoherence was a transformers bug.** Under transformers >= 4.56 an empty DynamicCache made `prepare_inputs_for_generation` drop the audio. With the fix: ASR recall 1.0 (encoder_calls 22), official-prompt recall 0.941 with a `<英语>` tag prefix, VRAM peak 15.68 GiB (earlier recall 0.059). Production use on >= 4.56 needs the same fix or a pin to 4.49, and the tag stripped.
- **Italian TTS year rule narrowed (CS-8.L4a):** the "zei" on spelled-out "duemilasei" led to year-form spelling only in year contexts (dates, nel/del/dal/al/anno, "(2006)", ranges); "1500 euro" stays a cardinal. CS-8.L4b (pauses in "anàloga" and "pi acca") was not reproduced in any variant; a one-clip operator re-listen remains optional.

Sources: [Conversation stack](../handoffs/active/conversation-stack.md)


## Compiled Update — 2026-10-28 (CS22 negative retained; STT2 packets remain preparation)

**Confidence: verified** for the committed CS22 diagnostic conclusion and the source-preparation records. No new quality or timing claim is inferred from packet readiness.

- **CS22.V0's exact-parity propositions are false for all three candidates.** The committed diagnostic readout covered 224 clips and 1,344 clip-setting cells per candidate, with 2,688 retained output hashes and no execution or hash errors. Mismatch counts are GGUF 946 stops / 1,118 segments, JIT 946 / 1,118, and Whisper 956 / 1,113. No posterior tolerance was predeclared, so the observed maxima remain descriptive and do not diagnose the cause. Source enrollment followed the run by 14m25s; no retrospective warrant is claimed.
- The prospective same-release diagnostic is limited to the first four pinned clips and compares the original ONNX with ONNX/JIT members from one wheel. Common release does not prove identical weights. Its before-load capture, failure retention, and fake-entry controls are preparation evidence. The preparation record contains no accepted native outcome; owner-result audit, strict-reader integration, and the planning canary remain open.
- **Converted STT2 assets and CPU smoke launchers were prepared, not acquired or run by this preparation session.** The Parakeet and Whisper F16 artifacts have separate immutable pins and provenance. The dependent 40-clip CPU jobs capture model, source, binary, linkage, grant and per-clip outcomes; they remain dependent on acquisition receipts and source publication. No production-weight equivalence, WER/quality, or timing qualification follows from the packet.

Sources: [conversation-stack handoff](../handoffs/active/conversation-stack.md); [CS22 native negative and diagnostic](../progress/2026-10/2026-10-27-cs22-native-negative-and-diagnostic.md); [STT2 native source preparation](../progress/2026-10/2026-10-27-stt2-native-source-ready.md); [native repair packet checkpoint](../progress/2026-10/2026-10-27-native-repair-packets-2255.md); [Vidya belief substrate program](../handoffs/active/vidya-belief-substrate-program.md).

## Compiled Update — 2026-10-29: vision-role promotion reconciled; PaddleOCR-VL CPU table smoke

- **S-16 closed by audit:** Qwen3-VL-30B-A3B Q4_K_M is registered as `worker_vision`/`vision_escalation` (deployed 2026-07-31), replacing Qwen2.5-VL-7B in the research registry. This is a reconciliation of an already-deployed state, not a new measurement.
- **PaddleOCR-VL-1.6 on CPU (PIP02 Phase B):** the llama-server vision path (GGUF + mmproj, `-ngl 0 -np 1`) completed two English table pages in 67.8 s and emitted HTML `<table>` markup; the bounded n=2 smoke says the harness works, not that the tables are faithful (dropped operators seen in page-2 equations). Scoring belongs to Phase C (see Document Processing).

Sources: [multimodal-pipeline handoff](../handoffs/active/multimodal-pipeline.md); [document-parser-table-bench handoff](../handoffs/active/document-parser-table-bench.md); [PIP02 partial TEDS report](../artifacts/compute/pip02-partial-teds-20261029/README.md)

## Compiled Update — 2026-10-31 (operator wiki sweep, workspace-58)

**Confidence: verified** for preparation controls only; **no verdict** on image quality, STT accuracy or HIP parity.

- **ERNIE-Image typography slice is READY, not run.** A 20-prompt EN/ZH slice (896 and 1024 px) is staged for later human review under PIP-03; a real 512x512 engineering control and STOP/drain qualified the host path, but the GPU was busy at preflight and no target capture exists. Enhancer-on and product filtering are UNKNOWN, and a local slice cannot establish the official benchmark or a matched-Qwen comparison. ([ernie-image-turbo-evaluation](../handoffs/active/ernie-image-turbo-evaluation.md); [READY snapshot](../artifacts/compute/codex3-ernie-pareval-ready-20261031/SNAPSHOT.sha256))
- **Speech validation packets pass entry controls, unscored.** Voxtral (4,096-context, 480/960 ms routes), Ultra Q8/F32 and transcribe Nemotron (R0/R3/R6/R13) passed real normal-entry and STOP controls; an independent HF reference and native F32/Q8 matched decoded-step IDs and durations on JFK (46 steps) and a synthetic tone (5), with the raw frontend keeping one extra masked HF frame. Nemotron R1 is outside the trained context menu; full FLEURS is unexposed and HIP compiler-object success is not GPU correctness. ([speech prep](../artifacts/compute/codex3-speech-prep-20261031/README.md))
- **LID1 and STT3 remain plans.** Five full-public-FLEURS CPU LID packets are READY-WAIT with no corpus scored, and the joint STT3 plan was frozen before cohort ASR. ([speech LID preparation](../progress/2026-10/2026-10-30-codex3-speech-lid-preparation.md))

Sources: [ernie-image-turbo-evaluation](../handoffs/active/ernie-image-turbo-evaluation.md) · [speech prep checkpoint](../progress/2026-10/2026-10-31-codex3-speech-prep-checkpoint.md) · [LID preparation](../progress/2026-10/2026-10-30-codex3-speech-lid-preparation.md)

### Compiled Update — 2026-10-31 (S-18 runtime-only READY checkpoint)

**Confidence: verified** for publication/admission and the two bounded runtime smokes; the requested `t48` CPU placement and 60-item throughput/quality result remain unmeasured. This does not imply absence of runtime execution.

- The native S-18 READY packet was published with the pinned exact 60-item CPU cohort and recipe identity preserved. The normal four-token smoke returned rc0 after 221.4304 s but parsed as `parse_fail`; the active-cutoff smoke returned rc75/partial after 233.1852 s, with one of two rows and process-group drain. Both used `max_tokens=4`, so neither is an MMMU score or evidence of CPU quality parity.
- Keep the exact-cohort baseline (36/60) separate from the historical 159/250 (63.6%) result. The S-18 measurement and VB-SERVING-DF2 projection/canary remain open; the projection schema is unwired and the planning-context canary is required.

Sources: [S-18 READY capsule](../artifacts/compute/codex-ni-s18-qwenvl-cpu-r1-20261031/README.md); [2026-10-31 NI progress](../progress/2026-10/2026-10-31-codex-ni-01a16d6b.md); [multimodal pipeline handoff](../handoffs/active/multimodal-pipeline.md); [Vidya belief substrate program](../handoffs/active/vidya-belief-substrate-program.md).
