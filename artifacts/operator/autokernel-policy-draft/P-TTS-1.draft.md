<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Authored by an agent under AK9; an agent cannot ratify
     and `measurement/protocols/` is hook-blocked.
     Target: the TTS half of NEW FILE measurement/protocols/speech (Annex S). Container, annex
     placement, core-file deltas and operator items: Annex-S-speech-container.draft.md.
     Owning handoff: handoffs/active/autokernel-research-loop.md §13.4, §14 AK9. -->

# Annex S — speech protocols · TTS family (draft text)

**Backend:** `qwentts_tts`. **Source tree:** `qwentts.cpp`. **Frozen production branch:**
`production-speech-v1` (`2c1b5182e7e9f1acaa04405ff21747d8a7acf4d5`, ggml 0.17.0, ggml submodule
`b86f660238dcc1a83b7cbf5a72d355a965de9245`). **Stable path:**
`/mnt/raid0/llm/kernels/production/tts` → `qwentts.cpp/build`.

**Two structural asymmetries, stated first because assuming uniformity is how an adapter gets one of
them wrong:**

1. **The stable path points at `build`, not `build/bin`.** The other three production binaries
   (`cpu`, `gpu`, `stt`) resolve into a `bin/` subdirectory; this one does not (§1.5). A path
   constructor that appends `bin/` for every backend produces a non-existent path here.
2. **`ggml` is a git SUBMODULE, not vendored in-tree.** `whisper.cpp` edits
   `ggml/src/ggml-cuda/vendors/hip.h` as a file in its own tree; `qwentts.cpp` carries a gitlink. The
   consequence is load-bearing for §3.2 and §10.6: the production commit `2c1b5182` shows
   **`ggml | 2 +-`, one file, one insertion, one deletion** in the superproject, while the submodule
   commit it points at (`b86f6602`) changes **4 files and 115 lines** — the thread-strided bitonic
   argsort plus the ROCm 6.2 FP8 guard. A source-closure diff or a complexity assessment computed on
   the superproject alone under-reports this change by two orders of magnitude.

**Independently freezable.** `qwentts.cpp` serves exactly one backend, so its freeze scope is one tree
and one backend (§1.5), independent of `whisper.cpp` and of `llama.cpp`.

---

## P-TTS-1 — text/audio identity and deterministic/numerical checks

**Purpose.** To make *"the candidate synthesizes the same speech"* a checkable fact at the layer where
it is checkable, rather than an inference from a downstream quality score. A vocoder is float and a
language model is discrete; conflating them into one "does it sound right" question throws away the
sharpest oracle available.

**Scope.** Any decision-gating `qwentts_tts` identity, determinism or numerical-safety verdict.
Emits a **verdict, not a claim** — identity is not a metric and MUST NOT be averaged, ranked, or
traded against speed.

---

### 1.1 Input identity — everything that determines the output is hashed

A synthesis run is reproducible only if every input is bound. **All of the following are recorded per
utterance, and a missing one VOIDS the cell:**

- **Prompt text** — SHA-256 of the exact UTF-8 bytes, plus the byte length. Not the "normalized" text
  and not a display form: whitespace and punctuation change the tokenization and therefore the audio.
- **Tokenizer identity** — path and SHA-256 of the tokenizer GGUF (the 12 Hz tokenizer in the current
  production pair). A tokenizer swap is a different instrument, not a different run.
- **Talker / CodePredictor weights** — path, SHA-256, and quant of each model file.
- **Speaker conditioning** — SHA-256 of every `.spk` / `.rvq` / reference-audio input where voice
  cloning is exercised. A clone reference is an *input*; unrecorded, the arm is unreproducible and its
  output is not comparable to anything.
- **Sampling policy** — temperature, top-k/top-p, seed, and whether `--greedy` was in force.
- **Cache state** — declared in every record (`kernel-research.md:362-364`). `served_from_cache`
  **FAILs**.

---

### 1.2 The greedy arm gates; a sampled arm is diagnostic

**A `--greedy` (temperature 0) arm is MANDATORY and is the arm the release rule reads.** Reason: under
greedy decoding the codec token sequence is a deterministic function of the inputs and the weights, so
identity is *observable*. Under sampling it is not, and every check degrades from an identity test to
a distributional one, which needs orders of magnitude more samples to reach the same resolution.

A sampled arm MAY be measured and reported alongside as a diagnostic. It MUST NOT be the arm a release
verdict is taken on, and it MUST NOT be substituted for the greedy arm when the greedy arm fails.

This is not a hypothetical convenience: the 2026-07-31 measurement recorded that **under `--greedy`
the GPU and CPU transcripts were identical** across the full utterance set, which is precisely the
property that makes a cross-backend identity oracle available here at all.

---

### 1.3 Two layers, two oracles, and the reason they are separate

**Layer 1 — codec token-sequence identity (the sharp oracle).** The Talker and CodePredictor emit a
discrete code sequence before the vocoder runs. Under greedy decoding this sequence is exactly
reproducible, so the check is `candidate_codes == anchor_codes`, element-wise, per utterance.

- Verdict: `IDENTICAL` / `DIVERGENT` / `COULD_NOT_CHECK`.
- The record carries the SHA-256 of the emitted code sequence for both arms and, on divergence, the
  index of the first differing position and the length of both sequences.
- **This layer isolates the LM half from the vocoder half.** A candidate that changes only vocoder
  arithmetic must be `IDENTICAL` here; a divergence means the change reached further than declared,
  which is an affected-surface finding (invariant 18: declared equals traced).
- `COULD_NOT_CHECK` when the build does not expose the code sequence. It is not a pass, and the
  coverage gap is journaled rather than worked around.

**Layer 2 — waveform numerical bound (the tolerant oracle).** The vocoder is floating-point and its
output is not expected to be bitwise identical across backends or across a legitimate arithmetic
change. The check is therefore a bound, and **the bound is derived, never chosen**:

- **Sample-count identity comes first and is exact.** The candidate MUST emit the same number of PCM
  samples as the anchor for the same input under greedy. A length change means the model stopped
  somewhere else; it is categorical, and averaging a distance over two waveforms of different lengths
  produces a number with no interpretation. A length mismatch is `DIVERGENT` at layer 2 with reason
  `sample_count`, full stop.
- **Per-sample maximum absolute difference** and a **spectral distance**, both against the anchor
  waveform, both `lower-better`, both computed by the pinned evaluator-bundle reducer whose id and
  hash are recorded.
- **The tolerance is the anchor's own run-to-run dispersion under the identical recipe**, established
  by the A/A control (`kernel-research.md:332-334`) and computed by the calibration block. **If the
  anchor is bitwise stable, the dispersion is exactly zero and layer 2 collapses to identity** — which
  is the strong form and is what MUST be used when it is available. A tolerance is only ever as wide
  as the instrument's own measured noise.

---

### 1.4 Numerical safety — checked on the samples, not on the impression

- **NaN / Inf scan over the complete PCM output, and over the codec logits wherever the build exposes
  them.** Any NaN or Inf is a **FAIL regardless of how the audio sounds**. A NaN that clips to silence
  is inaudible in a five-second clip and catastrophic in production, and it will not move a round-trip
  word-error rate at all.
- **Clipping fraction** — the proportion of samples at or beyond full scale — and **DC offset**, both
  reported with the anchor's calibrated band. A kernel change that introduces a scale error surfaces
  here long before it surfaces in any intelligibility proxy.
- **Silence and truncation guards.** An all-zero or near-all-zero output, or an output whose duration
  falls outside the anchor's observed duration envelope for the same text, is a categorical failure and
  is reported as such — never folded into a distance. The 2026-07-31 in-flight GPU bench produced
  `utt0: NO AUDIO PRODUCED` on all six utterances; a pipeline that averages that into a waveform
  distance reports a small number for a total failure.
- **Determinism class is an interface** (invariant 12). Same-seed run-to-run bitwise stability is
  measured, declared per record as `bitwise_stable` / `bitwise_unstable` / `not_measured`, and a
  **change of class is itself release-relevant** even when every other check passes. `not_measured` is
  in the vocabulary so that "we did not check" is sayable without implying stability.

**Decision-grade requires ALL of:** this ratified protocol; a `--greedy` arm; complete input identity
per §1.1; layer-1 verdict recorded per utterance with code-sequence hashes; sample-count identity;
layer-2 distances against a tolerance derived from the anchor's A/A dispersion; a clean NaN/Inf scan;
clipping and DC within the anchor's calibrated bands; no silence or truncation failures; a declared
determinism class; a declared cache state; an explicit immutable anchor re-verified at window open and
close; and retained raw PCM and code sequences from which every reduction is recomputable. Missing ANY
→ **observation**, and inside search → `INVALID`.

**Prospective.** Applies only to runs started after ratification. No pre-ratification qwentts.cpp
artifact becomes a claim by virtue of this protocol existing.

**Grammar:**
`TTS identity <IDENTICAL|DIVERGENT|COULD_NOT_CHECK>, n=<utterances> [P-TTS-1, greedy=<true>, codes=<n_identical>/<n>, code_sha=<candidate[:12]>/<anchor[:12]>, samples=<n_identical>/<n>, maxabs=<v> tol=<t>, spectral=<v> tol=<t>, reducer=<id>@<sha[:12]>, nan=<none|COUNT>, clip=<frac> band=[<lo>,<hi>], det=<determinism-class>, cache=<state>, YYYY-MM-DD, attest <ref>]`

---

## P-TTS-2 — intelligibility floor and reference-waveform distance (human-independent)

**Purpose.** To provide a quality signal for synthesized speech **with no human in the loop**, while
being explicit that the available human-independent signals are a *floor* and a *distance*, and that
neither is a quality score.

**Scope.** Any decision-gating `qwentts_tts` quality verdict. Metrics below are `lower-better`.

---

### 2.1 The intelligibility floor — round-trip word error rate

**Definition.** Synthesize the utterance from a held reference text, transcribe the resulting audio
with a **pinned STT instrument**, normalize both sides with the **pinned `P-STT-1` normalizer**, and
compute the pooled WER by `P-STT-1` §1.4. Direction `lower-better`. Call it `roundtrip_wer`.

**The instrument is pinned to a FROZEN PRODUCTION STT binary, never to the STT champion.** Identified
by binary SHA-256, model path and SHA-256, decode parameters, and the `P-STT-1` normalizer id and
hash — all recorded in every TTS record. Three consequences, all normative:

1. **A change of STT instrument is an instrument-version boundary for TTS records.** Records produced
   under two STT instruments MUST NOT be pooled, differenced, or compared
   (`MEASUREMENT.md:83-84`). The TTS number moved; the TTS kernel may not have.
2. **A campaign MUST NOT simultaneously advance the `whisper_stt` champion and use it as the TTS
   oracle.** The two backends are independently freezable and independently researched (§1.5), and an
   oracle that is itself under optimization confounds every reading taken through it. The TTS oracle
   is the frozen production STT kernel, full stop.
3. **A `roundtrip_wer` regression is ambiguous until the STT instrument is proven unchanged.** The
   record carries the STT instrument's identity precisely so that this ambiguity is resolvable rather
   than argued about.

**It is a FLOOR. It never ranks.** `roundtrip_wer` may gate (below the floor ⇒ FAIL) and may never
order two passing candidates. Two reasons, both concrete:

- **It saturates.** The CPU Q8_0 production pair measured **0.0 % round-trip WER** on 2026-07-31 —
  word-perfect. A metric at its ceiling cannot detect improvement and detects only large regressions
  (`feedback_eval_saturation_masks_model_gap`). Where the anchor is saturated the record MUST say so:
  `intelligibility=floor_only (saturated at anchor)`. A saturated floor is a pass/fail gate, never
  evidence of quality parity.
- **It is gameable in exactly the direction the degraded-negative control exists to catch.** A
  candidate that returns a cached waveform, or that degenerates to a flat, robotic, perfectly legible
  monotone, scores *better* on round-trip WER while being worse speech. Control 3
  (`kernel-research.md:329-331`) for this backend MUST include such a candidate, and it MUST receive
  no rank at all.

**The floor itself is DERIVED.** It is the anchor's own `roundtrip_wer` plus the A/A dispersion of
that quantity through the identical pipeline, computed by the calibration block. It is not a literal
and it is not a round number. Where the anchor is saturated at 0.0 %, the derived floor is the A/A
dispersion alone, and the campaign records that the floor's resolution is bounded by the corpus size
via the `P-STT-1` §1.4 derivation.

---

### 2.2 The non-saturated companion — reference-waveform distance

Because §2.1 saturates, a floor alone leaves the campaign blind to exactly the vocoder degradations a
kernel change produces. A second **human-independent** signal is therefore REQUIRED alongside it:

**`spectral_distance`** — the distance between the candidate waveform and the **anchor** waveform for
the same input under greedy, computed by the pinned evaluator-bundle reducer (a mel-cepstral-style
spectral distortion; the exact construction is a property of the bundle, fixed at the bundle hash, and
a campaign selects among constructions the bundle already implements and records which). Direction
`lower-better`.

- It does **not** saturate, because it measures distance from a reference rather than success at a
  task.
- It is sensitive to scale, phase, band-limiting and vocoder artifacts that round-trip WER is blind
  to — an ASR front end is deliberately robust to precisely those.
- Its acceptance band is the **anchor's own A/A dispersion**, derived by the calibration block. Zero
  when the anchor is bitwise stable.
- **It is a distance from the anchor, not a quality score.** A candidate further from the anchor is
  *different*, not *worse*; the release rule treats distance beyond the band as a failure of the
  non-inferiority gate, never as a quality ranking.

**Neither signal is MOS and neither may be described as one.** No claim of naturalness, prosody,
speaker similarity, or listener preference may be made from either. The project's own precedent is
explicit that an automated intelligibility observation *"is not MOS, voice quality, latency,
production readiness, or lineup evidence"* (`multimodal-pipeline.md`, M-2QA, 2026-07-27), and this
protocol does not lift that.

**Human evaluation is out of scope and is not a gate.** If a human listening test is ever run, it is a
separate instrument requiring its own protocol; it MUST NOT be substituted for either signal here, and
its absence MUST NOT be described as a limitation of this protocol. This protocol's remit is exactly
the human-independent floor the design asked for.

**Decision-grade requires ALL of:** this ratified protocol; the pinned STT instrument's complete
identity including model and normalizer hashes; the pinned normalizer's symmetry/idempotence/
determinism assertions from `P-STT-1` §1.3; the `P-STT-1` failure taxonomy applied to the transcripts;
`roundtrip_wer` with its bootstrap interval and its derived floor; an explicit saturation declaration
where the anchor is at ceiling; `spectral_distance` with its reducer id and hash and its derived band;
a passing degraded-negative control; a declared cache state; and retained raw audio and transcripts.
Missing ANY → **observation**.

**Prospective.** Applies only to runs started after ratification. The 2026-07-31 round-trip WER
figures — 0.0 % on CPU Q8_0 and 1.49 % on MI210, the latter carried in
`artifacts/operator/ratify_speech_kernel_freeze_20260731.json` — are observations and remain so. Note
they were taken through **different** STT instruments than each other and than any future run, which is
the confounding §2.1 clause 1 exists to prevent.

**Grammar:**
`TTS roundtrip WER <value> % lower-better, n=<utterances> [P-TTS-2, floor=<derived_floor> (<saturated|unsaturated> at anchor), boot95=[<lo>,<hi>], spectral=<value> band=[<lo>,<hi>] reducer=<id>@<sha[:12]>, stt_instrument=<binary_sha256[:12]>/<model_sha256[:12]>, norm=<normalizer_id>@<norm_sha256[:12]>, taxonomy=<ok>/<empty>/<reploop>/<numeral>/<marker>/<decode_err>, control_negative=<PASS>, cache=<state>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

---

## P-TTS-3 — first-audio latency, real-time factor, and synthesis throughput

**Purpose.** To fix one definition of each TTS speed quantity, in a project that currently carries the
same measurement in two reciprocal conventions across two durable artifacts (container draft §4).

**Scope.** Any decision-gating `qwentts_tts` speed number.

**Metrics, each with its direction and its denominator stated:**

- **`ttfa_ms` — time to first audio, `lower-better`.** Wall milliseconds from the last byte of the
  request being written to the transport, to the **first PCM sample being available to the consumer**.
  Not to the first internal codec buffer, not to the first token, not to the first log line. The
  measurement point is the consumer's boundary, because that is the quantity a conversational voice
  loop experiences. Reported as median **and** p95.
- **`rtf` = `wall_seconds / audio_seconds`, `lower-better`.** The canonical form. `audio_seconds` is
  the duration of the **emitted PCM**, computed from its sample count and rate — never a requested or
  estimated duration.
- **`xrt` = `audio_seconds / wall_seconds`, `higher-better`.** Permitted only when labelled `xrt`. A
  bare "real-time factor" with no direction is **non-conforming**. `rtf` and `xrt` are reciprocals and
  a record quoting one MUST NOT be compared against a record quoting the other without conversion.
- **`throughput_audio_s_per_wall_s`, `higher-better`** — audio-seconds synthesized per wall-second at a
  **declared concurrency**. Measured directly at that concurrency; reconstructing it from a
  single-stream `rtf` times a stream count is FORBIDDEN (`gpu-cross-device.md:106-111`).

**Stage attribution is REQUIRED, not optional.** The pipeline has three stages that behave completely
differently — `Talker`, `CodePredictor`, `CodecDecode` — and an end-to-end RTF hides which one moved.
The record carries per-stage wall time and per-stage share. The 2026-07-31 CPU→GPU transition is the
precedent for why: `CodecDecode` fell from **64 % to 10.4 %** of wall while `CodePredictor` rose to
**65.5 %**, i.e. the bottleneck *moved to a different stage*. A campaign reading only end-to-end RTF
would have kept optimizing the vocoder after it stopped being the problem.

**Preconditions.** As `P-STT-2`: acquired resource claim covering the exact footprint (a device claim
for MI210 cells — idle sensing is never a claim); host-health tier per `bench-cpu.md:17-19`; an
explicit immutable anchor by source commit, binary SHA-256 and linkage SHA-256, re-verified at window
open and close; evaluator bundle hash and runtime source-label attestation; codified recipe
constructor — hand-typed argv voids the run; storage headroom.

**Linkage.** Before any measurement, `scripts/utils/verify_ggml_linkage.sh <binary> <tree_root>` (in
the research repo) MUST be executed against the candidate binary and its complete output retained.
qwentts.cpp runs **ggml 0.17.0** while whisper.cpp runs 0.18.0 and llama.cpp 0.16.0; a binary that
inherits another tree's ggml runs silently wrong. The two `P-STT-2` clauses apply verbatim: a verifier
`PASS` is **necessary and not sufficient** (backends are `dlopen`ed and `ldd` does not see them, so the
engine's own device line is also required, and a `use gpu = 1` flag reports what was *requested*), and
a verifier run that resolved **no** libraries is `COULD_NOT_CHECK`, never `PASS`. A third clause is
qwentts-specific: the verifier's library-name filter enumerates `libggml*`, `libwhisper*`, `libllama*`
and `libmtmd*`, so any qwentts-specific shared object outside that set is **unchecked by the script**;
the record MUST additionally confirm every library in the adapter's declared expected set appeared in
the report, and treat a missing one as `COULD_NOT_CHECK`.

**Reps and reduction.** Per the P-BENCH-1 rule (`bench-cpu.md:21-22`), never fewer than the calibrated
`B_min` paired blocks. Median + MAD. Candidate and anchor interleaved and order-randomized within every
paired block; blocked designs forbidden. Anchor measured first in every window against its calibrated
acceptance band; outside the band the window is **VOID**.

**Decision-grade requires ALL of:** this ratified protocol; each metric named with its direction and
denominator; TTFA measured at the consumer boundary and reported as median and p95; `audio_seconds`
derived from the emitted sample count; per-stage attribution for Talker, CodePredictor and CodecDecode;
throughput measured at its declared concurrency and never reconstructed; an acquired claim re-verified
at window close; a passing host-health tier; an explicit immutable anchor; a passing anchor gate; the
linkage verifier's complete output plus the engine's device line plus the expected-library
confirmation; the codified recipe constructor id and hash; reps per the P-BENCH-1 rule; median + MAD; a
published MDE; an e-process verdict against its calibrated threshold — never an ad-hoc bound and never
an LCB in its place; and retained raw samples. Missing ANY → **observation**.

**Prospective.** Applies only to runs started after ratification. The 2026-07-31 figures — CPU TTFA
67.9 ms and 6820.7 ms for 5.84 s of audio, MI210 TTFA 37.8 ms, and the `rtf: 0.169` / `xRT 5.47`
pair — are observations and remain so; the container draft §4 records that the two are reciprocals of
one another whose values do not agree, which is itself a reason no future record may inherit either.

**Grammar:**
`TTS <ttfa_ms|rtf|xrt|throughput_audio_s_per_wall_s> <value> <lower-better|higher-better>, n=<reps> [P-TTS-3, median+MAD=<med>±<mad>, p95=<v>, stages Talker=<ms>(<pct>%)/CodePredictor=<ms>(<pct>%)/CodecDecode=<ms>(<pct>%), audio_s=<v> from <n_samples>@<rate>Hz, concurrency=<c>, MDE=<mde>, e=<e-value>/thr=<1/α>, linkage=<PASS|COULD_NOT_CHECK>+device=<device_line>, recipe=<id>@<sha[:12]>, res=<claim_receipt>, host=<host_receipt>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

---

## TTS stability and op-coverage integrity

Governed by **`P-STT-3`**, whose clauses are written backend-agnostically and are cited here rather
than duplicated — where a rule already lives, the amendment goes (`kernel-research.md:22-23`). All of
it binds `qwentts_tts`: the derived memory-slope band, the teardown and cleanup verdict, the service
smoke that gates nothing, and the op-coverage enumeration rule.

**The op-coverage rule was written from this backend's own scar and applies to it with full force.**
The gfx90a `ARGSORT` defect — `ne0=2048` launching 2048 threads per block against gfx90a's 1024 cap,
**705 times per utterance** — was invisible while `test-backend-ops` reported `ARGSORT 46/46` and
`TOP_K 170/170`, because the failing shapes were **silently skipped**. After the fix the same suite
reported `74/74` and `292/292`. Both readings are "100 % pass" and only the enumeration distinguishes
them. Under `P-STT-3`, a `qwentts_tts` candidate whose attempted-case count for any op falls below the
anchor's **FAILS**, at any pass rate.

---

## P-TTS-REL-1 — the TTS kernel-release decision rule

**Purpose.** One rule that reads `P-TTS-1`, `P-TTS-2`, `P-TTS-3` and `P-STT-3` together and produces a
release verdict for a qwentts.cpp candidate. **It is an input to an operator's freeze decision and is
never a freeze trigger.**

**Scope.** A sealed qwentts.cpp release candidate evaluated at T3 (§10). Emits
`PASS` / `FAIL` / `PASS_WITH_WAIVER` — a **verdict, not a claim**.

**What this protocol does NOT authorize.** No freeze, no cutover, no era-registry row, no AutoPilot
baseline apply, no commit to `production-speech-v1` or any future `production-speech-vN`, no repointing
of `/mnt/raid0/llm/kernels/production/tts`. Those are the human-only writes at
`MEASUREMENT.md:140-142`.

### 4.1 Release identity

`bench-cpu.md:38-44` governs candidate release identity and is **cited, not restated**. Three
qwentts-specific additions:

- **The source closure MUST traverse the `ggml` submodule.** A closure computed on the superproject
  alone reports the production change as one line when it is 115 across four files (header, §3.2
  stage 1). The closure is obtained from the build system's own dependency information
  (CMake/Ninja depfiles), never from a hand-maintained list or a directory-prefix guess, and the
  submodule's commit is recorded as part of candidate identity in its own right.
- **The stable path is `build`, not `build/bin`.** Any release-transaction dry-run that constructs the
  install path by appending `bin/` is wrong for this backend and MUST be caught at §10.2 phase 8, not
  discovered at cutover.
- **The linkage proof of `P-TTS-3` is part of release identity**, not merely of the speed cell.

### 4.2 The backend-unchanged test, in its single-backend form

As `P-STT-REL-1` §4.2: `qwentts.cpp` serves exactly one backend, so no cell-dropping transfer exists.
Both stages still run to establish that the candidate differs from the incumbent at all, and a
**no-op candidate** is refused rather than passing every gate trivially. Stage disagreement is a hard
finding filed against the build-identity machinery. **Stage 1 here is the submodule-traversing
closure**, and a stage-1 result computed without traversal is not a stage-1 result.

### 4.3 The rule

**Lexicographic, correctness first** (`kernel-research.md:355-360`):

1. **Identity and numerical gate (P-TTS-1).** Greedy arm present; layer-1 codec-token identity on every
   utterance the determinism class permits; sample-count identity; layer-2 distances within the derived
   tolerance; zero NaN/Inf; clipping and DC within band; no silence or truncation failures; determinism
   class unchanged or its change explicitly declared and accepted. A failure here yields **no speed
   rank at all, not a penalised one**.
2. **Intelligibility gate (P-TTS-2).** `roundtrip_wer` at or below its derived floor through the pinned
   frozen STT instrument, with saturation declared where it applies; `spectral_distance` within the
   anchor's derived band; the degraded-negative control receiving no rank.
3. **Integrity gate (P-STT-3).** Memory slope within the anchor's band; clean teardown; op-test
   enumeration not smaller than the anchor's.
4. **Speed gate (P-TTS-3).** Per metric, at the **production-optimal recipe for every protected cell**,
   the §1.6 objective: non-inferior on every phase, improved on at least one, with per-stage attribution
   recorded. Baseline / off-recipe cells are diagnostic and never veto or justify a release
   (invariant 15).

**Bands are DERIVED per cell by the campaign calibration block** (`kernel-research.md:193-268`). No band
in this protocol is a literal.

**The decision-rule SHAPE — and only the shape — is adopted from `bench-cpu.md:83-88`:** a pass region,
an inconclusive region resolved by one fresh reversed-order pair pooled to a pre-declared threshold, and
a fail region. Its literals (`≥0.98`, `<0.95`) are **explicitly NOT imported**; they were calibrated on
CPU `llama-bench` prefill dispersion and mean nothing for a TTFA or a spectral distance
(`feedback_gate_scope_must_match_measured_subset`). Same discipline as `P-AK-SEARCH-1-A1`
(`kernel-research.md:445-448`).

**Mechanism plausibility.** A banked qwentts.cpp candidate requires an explanation backed by bytes,
FLOPs, counters, or a clean A/B (`P-AK-SEARCH-1-A1` clause 1). The argsort fix is the model case: the
mechanism was *"2048 threads requested against a 1024-thread hardware limit, 705 times per utterance"*,
which is a bytes-and-counters explanation, not an observed speedup in search of a story.

**Capability-claim gate.** Do not claim that this backend supports a kernel, dtype, quant or performance
tier unless it has **both correctness and performance evidence** (`P-AK-SEARCH-1-A1` clause 2). The FP8
guard is the standing example: gfx90a has no FP8 hardware, the guard exists only to make the tree
compile under ROCm 6.2, and no FP8 capability may be claimed for this backend on the strength of the
code compiling.

### 4.4 Waivers

As `P-STT-REL-1` §4.4: a hash-pinned, human-only `epyc.autokernel.operator_waiver.v1` object. The
evaluator verifies its hash and predicate and never judges its merits; a waived cell suppresses the
corresponding claim in the release receipt; the verdict becomes `PASS_WITH_WAIVER`.

### 4.5 Complexity ceiling

Per §10.6, derived from the backend's own accepted production history: the maximum changed-lines and
files-touched across every commit on `production-speech-v1` beyond its upstream base, **computed with
the submodule expanded**. That history is currently one superproject commit whose expanded closure is
**4 files and 115 changed lines**, all of it inside `ggml/src/ggml-cuda/` — i.e. shared core. The
adapter therefore declares `shared_core_modification_requires_review = true` unconditionally for this
backend, and the ceiling is low enough that most LLM-authored changes here will be marked
`REQUIRES_HUMAN_CODE_REVIEW`. That is the correct outcome for a third-party tree this project does not
own and whose upstream it does not control. Recomputed at every freeze.

**Decision-grade requires ALL of:** this ratified protocol; a sealed candidate meeting §4.1 including
the submodule-traversing closure; both stages of §4.2 run and agreeing; the identity and numerical gate
passed on a greedy arm; the intelligibility gate passed through a pinned **frozen production** STT
instrument with saturation declared; the integrity gate passed with op enumeration; the speed gate
passed at production-optimal recipes with per-stage attribution; every band derived by a completed and
accepted calibration block; the pre-committed stopping rule unmodified; controls 1–4 available and
passing and control 5 either passing or explicitly recorded `HISTORICAL_REPLAY_UNAVAILABLE` with an
operator escalation on the record; a mechanism explanation; any active waiver hash-pinned and its
predicate verified; the complexity assessment; and the complete sealed evidence bundle. Missing ANY →
the verdict is `FAIL`, or `PASS_WITH_WAIVER` only where a conforming waiver covers exactly the failing
cell.

**Prospective.** Applies only to runs started after ratification. No pre-ratification qwentts.cpp
artifact may be retro-certified, and the 2026-07-31 speech freeze — executed under no TTS protocol,
because none existed — is not retro-conforming and is not reopened by this protocol's existence.

**Grammar:**
`TTS release verdict <PASS|FAIL|PASS_WITH_WAIVER> for qwentts.cpp <candidate_commit[:12]>+ggml<submodule_commit[:12]> vs <anchor_commit[:12]>/<anchor_binary_sha256[:12]>/<anchor_linkage_sha256[:12]> [P-TTS-REL-1, identity=<PASS|FAIL> (det=<determinism-class>), intelligibility=<PASS|FAIL> (floor=<v>, <saturated|unsaturated>, stt=<binary_sha256[:12]>), integrity=<PASS|FAIL>, speed=<PASS|FAIL> (cells <n_pass>/<n_total>), unchanged_test=<stage1_submodule_traversed>/<stage2>, controls=<4/5|5/5>, waivers=<none|waiver_sha256[:12]…>, review=<REQUIRES_HUMAN_CODE_REVIEW|none>, eval=<bundle_sha256[:12]>, bundle=<release_bundle_sha256[:12]>, YYYY-MM-DD, attest <ref>]`

**This verdict authorizes nothing.** It is evidence an operator reads before executing a freeze.
