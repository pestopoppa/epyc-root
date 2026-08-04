<!-- RATIFIED 2026-08-03. Annex S of MEASUREMENT.md (same trust boundary, same
     amendment rules). Speech protocol families — STT and TTS. Remit, admission
     test and section-reference convention below are normative. -->

# Annex S — Speech protocols (STT & TTS)

**Remit.** Annex S holds protocols that govern **speech measurement** on the two single-purpose
speech kernels: `whisper_stt` (source tree `whisper.cpp`) and `qwentts_tts` (source tree
`qwentts.cpp`). It is filed by **modality**, and it holds each modality's correctness half and speed
half together, because the release decision for a speech kernel reads both and is lexicographically
ordered between them.

**Admission to Annex S requires ALL of:**

1. the protocol's subject is a speech instrument — transcription of audio, or synthesis of audio —
   on `whisper_stt` or `qwentts_tts`;
2. the protocol is **single-backend** (which is why it is inadmissible to Annex K, whose condition 2
   requires cross-backend scope) **and** its metric is neither Annex B's CPU `llama-bench` tokens/s
   nor Annex G's cross-device `task_rate`;
3. no existing annex (B, Q, G, K) already **states** the rule this protocol **establishes**; and
4. where an instrument has a correctness half and a speed half, **both halves are filed here**. An
   instrument is not split across annexes. Splitting one instrument across two annexes creates two
   amendment histories for one authority and leaves the rule that spans both halves with no owner.

**Every protocol filed in Annex S MUST state, in its own grammar line, the class of record it
emits** — a claim, or a verdict that is not a claim.

**Attestation, and why four grammars here carry no `attest <ref>`.** Attestation in this
constitution refers to a **claim** (`MEASUREMENT.md:13`). Annex S emits records of both classes, so
the field is not uniform across it and must not be made uniform: `P-STT-1`, `P-STT-2`, `P-TTS-2` and
`P-TTS-3` emit measured values and their grammars carry `attest <ref>`; `P-STT-3`, `P-STT-REL-1`,
`P-TTS-1` and `P-TTS-REL-1` emit **verdicts**, which are not claims, and their grammars carry no
such field. What makes a verdict auditable is its receipts — `res`, `host`, `recipe`, `eval` and
`bundle` — not an attestation it is not entitled to. This follows Annex K, which reasoned the same
way for its own non-claim record (`kernel-research.md:404-408`): *"The grammar carries no `attest
<ref>` field. Attestation in this constitution refers to a claim, and this record is not one."* Two
annexes disagreeing about what a verdict attests would make the distinction decorative in both.

**Comparison scope.** Records emitted under an Annex S protocol are comparable **only within one
backend and one instrument version**. For this annex the instrument version includes, in addition to
the binary and its linkage: the pinned output normalizer (`P-STT-1` §1.3), the pinned decode step
that produces PCM (`P-STT-1` §1.2), the pinned evaluator-bundle reducers, and — for `P-TTS-2` — the
pinned frozen STT oracle. A change to any of them is an instrument-version boundary, and records do
not compare across it (`MEASUREMENT.md:83-84`). Cross-modality roll-ups are labelled analysis and
never gate.

**Section references (normative convention).** Inside this annex a bare `§n.m` is a subsection of the
protocol in which it appears. A reference to another protocol's subsection names that protocol
(`P-STT-1 §1.4`). A reference to the AutoKernel design document is written **owning handoff §n**.

---

**Why a separate annex, and not B, Q, G or K.** Recorded because it is the precedent this annex's
admission test rests on, and because the same question will be asked of the next modality.

`measurement/protocols/` contained **nothing** for STT or TTS. That was not an oversight to be
patched by squeezing speech into an existing family. The four prior annexes are declared by family
(`MEASUREMENT.md:16-21`, `:45-47`): **B** = `bench-cpu.md` (CPU bench), **Q** = `quality-eval.md`
(quality / eval / significance), **G** = `gpu-cross-device.md` (GPU and cross-device), **K** =
`kernel-research.md` (kernel research & release, cross-backend).

- **Annex K does not admit them.** Its admission test is a conjunction of three conditions
  (`kernel-research.md:11-17`), and condition 2 requires the protocol to be *"cross-backend — it
  governs at least two of `llama_cpu`, `llama_gpu`, `whisper_stt`, `qwentts_tts`,
  `serving_runtime`"*. An STT protocol governs `whisper_stt` and nothing else; a TTS protocol governs
  `qwentts_tts` and nothing else. Neither is cross-backend, both fail condition 2, and filing them in
  K anyway would make K's own admission test decorative — which is worse than a fifth annex, because
  that test is what stops K becoming the drawer everything cross-cutting is swept into.
- **Annex B does not admit them.** B is the *CPU* bench family and its protocols are built on
  `llama-bench`, `taskset -c 0-95 -t 96 -fa 1`, and tokens/s. The production STT and TTS binaries run
  on the MI210 under HIP; the STT metric is a word-error rate and a real-time factor, not tokens/s;
  and P-BENCH-1's core recipe is not expressible for either binary.
- **Annex G does not admit them.** G's subject is *cross-device* comparison and MI210 canonical
  throughput in tokens/s. Speech cells are single-device, and their metrics are not G's metric.
  Filing them in G would also drag P-GPU-1's production-named-kernel provenance rule
  (`gpu-cross-device.md:16-21`) across a boundary it was never written for.
- **Annex Q admits half of one of them, which is the trap.** The STT correctness half is a quality
  instrument and would sit plausibly in Q. Its speed half would not. Splitting one instrument across
  Q and B is exactly the alternative rejected for Annex K on 2026-08-02: it *"would fragment one
  instrument across three files with three amendment histories, and would obscure the property that
  matters most about it."* The same argument applies here with the same force, and it applies twice,
  since STT and TTS each have a correctness half and a speed half.

Hence a fifth annex, filed by modality — the Annex K precedent applied a second time, and consistent
with the core file's own layout sentence, under which protocol text lives in annexes *"filed by
family or instrument class"* (`MEASUREMENT.md:17-19`).

**What Annex S is NOT.**

- **It is not a second search authority.** Search inside experimental worktrees on `whisper_stt` and
  `qwentts_tts` is already authorized by `P-AK-SEARCH-1`, whose scope is *"Tiers T0, T1 and T2 of the
  AutoKernel loop, **on every declared backend adapter**"* (`kernel-research.md:51-52`). Annex S adds
  no search authority, lifts no consumption prohibition, and creates no exception to any denial in
  `kernel-research.md:89-135`. What it adds is the thing `P-AK-SEARCH-1` does not supply for these
  backends: **the owning protocol under which a speech number becomes a claim**, which
  `P-AK-SEARCH-1` requires to exist and names as *"its owning protocol in Annex B, Q or G"*
  (`kernel-research.md:55-58`) — a list that had no entry a speech number could be re-measured under.
  Annex S closes that gap and extends that list to *"B, Q, G or S"*.
- **It is not a release authority.** `MEASUREMENT.md:140-142` reserves era-registry rows,
  constitution amendments, AutoPilot baseline applies, production freezes/cutovers and host reboots
  to humans. A `PASS` verdict under a protocol in Annex S is an input to an operator's freeze decision
  and is never a freeze trigger. AutoKernel produces a release package; a human executes it (owning
  handoff §1.3, invariant 5).

**Prospective.** Creating Annex S neither retro-certifies nor upgrades any artifact. No speech
measurement taken before the apply timestamp becomes a claim, or a conforming record of any Annex S
protocol, by virtue of this annex existing. In particular the 2026-07-31 speech measurements — the
WER figures, the round-trip WER figures, the TTFA and RTF figures, and every number in
`artifacts/operator/ratify_speech_kernel_freeze_20260731.json` — remain **observations**. They are
cited throughout this annex as *calibration precedent*: they establish that a quantity is measurable,
what order of magnitude it takes, and how much dispersion it carries. They are never cited as
thresholds, and **no threshold in Annex S is set equal to one of them**. Annex S MUST NOT be used to
relocate an existing protocol; protocols already filed in B, Q, G or K stay there.

---

## Metric-direction defect closed by this annex (finding of record)

`MEASUREMENT.md:39-41` requires metric direction to be stated wherever ambiguous, and CLAUDE.md's
debugging rule opens with *"Always confirm metric direction."* At the time this annex was written the
project carried the **same TTS measurement in two reciprocal conventions**, in two durable artifacts:

- `artifacts/operator/ratify_speech_kernel_freeze_20260731.json` records
  `qwentts_cpp.measurements_anchored.rtf: 0.169` — wall-over-audio, **lower-better**;
- `handoffs/active/multimodal-pipeline.md` and the master handoff index record `xRT 0.86× → 5.47×` —
  audio-over-wall, **higher-better**.

They are reciprocals of one another and neither artifact says which it is. `1/0.169 = 5.92` and
`1/5.47 = 0.183`, so the two numbers are also not the same measurement; without a stated direction and
a stated denominator there is no way to tell a unit convention from a different run. `P-TTS-3` fixes
one definition (`rtf = wall_s / audio_s`, lower-better), requires the reciprocal to be labelled `xrt`
when quoted, and makes a bare "real-time factor" without a direction non-conforming.

**A second, sharper instance, recorded rather than repaired.** The same ratified freeze receipt
records, under `whisper_cpp`:

```
"measurements_anchored": { "model": "whisper large-v3-turbo f16", "wer_pct": 2.35, ... }
```

The raw artifact that number comes from is `/mnt/raid0/llm/tmp/stt_wer_results.json`, which contains
six arms. In that file, `2.35` is the **`faster-whisper large-v3-turbo int8 CPU 48t`** arm — the
CTranslate2 CPU incumbent, a *different engine on a different runtime*. The `whisper.cpp
large-v3-turbo f16 MI210 GPU` arm in the same file records **63 errors over 1870 reference words =
3.37 %**. The receipt therefore anchors the whisper.cpp kernel to a WER measured on a binary that is
not whisper.cpp.

This is not a rounding disagreement and it is not repairable from inside this annex: the receipt is a
ratified operator artifact, and `MEASUREMENT.md:174-175` forbids destroying primary records. It is
recorded here because it is precisely the failure `P-STT-1` is built to prevent — *a correctness
number attached to the wrong instrument* — and because the anchor a future `whisper_stt` campaign
compares against is wrong by ~1 pp in the flattering direction. Correcting it is a **human-only
receipt amendment**, whose recommended form is a *superseding* receipt naming the prior path and
SHA-256, never an in-place edit (`MEASUREMENT.md:116-118`; `bench-cpu.md:163-168` precedent). Note
also that the two arms' 95 % bootstrap intervals overlap heavily (Appendix S-A), so *"identical to the
CPU incumbent"* was not supportable from that corpus in either direction; the honest statement was
**no detectable difference at n=100**, which is a result (`gpu-cross-device.md:154-155`).

---

# STT family — `whisper_stt`

**Backend:** `whisper_stt`. **Source tree:** `whisper.cpp`. **Frozen production branch:**
`production-speech-v1` (`b307379226d93d9c5ed790d7cea0626613c0ef4b`, ggml 0.18.0). **Stable path:**
`/mnt/raid0/llm/kernels/production/stt` → `whisper.cpp/build/bin`.

**Independently freezable.** `whisper.cpp` serves exactly one backend, so its freeze scope is one
tree and one backend (owning handoff §1.5). Unlike `llama_cpu`/`llama_gpu` it shares no tree with
anything, and a whisper freeze creates no obligation on any other backend.

---

## P-STT-1 — STT transcription correctness: corpus, normalization, and the match rule (RATIFIED 2026-08-03)

**Purpose.** To make *"the candidate transcribes correctly"* a checkable fact rather than an
impression. This protocol defines what a transcription **match** is, what a transcription **error**
is, and — the case the project has actually been burned by — which apparent errors are **artifacts of
the scorer** and must never be counted as either.

**Scope.** Any decision-gating STT correctness number, and every correctness verdict consumed by a
`whisper_stt` release gate or search record. It governs the *scoring* of transcripts. It does not
govern how the transcripts were produced, which is `P-STT-2`'s and `P-STT-3`'s subject, nor what may
be concluded from them, which is `P-STT-REL-1`'s.

**Metric.** Two, and they are not interchangeable:

- **transcript-identity verdict** — `IDENTICAL` / `DIVERGENT` / `COULD_NOT_CHECK` against a named
  anchor. Not a number and never averaged.
- **corpus WER**, `lower-better`, defined in §1.4 as a **pooled** ratio. A WER carried without the
  normalizer id and version is not a conforming number under this protocol.

**Record class.** A conforming P-STT-1 record produced on a production-named whisper.cpp kernel is a
**claim**. A conforming record produced inside an experimental worktree during search is a **search
record, not a claim**, and carries `P-AK-SEARCH-1`'s grammar in addition to this protocol's
(`kernel-research.md:25-26`, `:383-402`).

---

### 1.1 The decision has four layers, evaluated in order, and skipping one is a category error

A kernel change is not a model change. The question *"did this kernel change the transcription?"* and
the question *"is this transcription right?"* are different questions with different instruments, and
answering the second when the first was available is both more expensive and less sensitive.

**Layer 0 — audio-input identity (precondition, §1.2).** Establishes that the two arms were given the
same sound. Without it nothing below means anything.

**Layer 1 — raw transcript identity.** Byte-for-byte comparison of the candidate's emitted transcript
against the anchor's, per utterance, before any normalization. `IDENTICAL` at layer 1 ends the
correctness evaluation for that utterance with a PASS, costs nothing, and is the **strongest**
available evidence — it excludes every normalization question by construction. Layer 1 MUST be run
and its per-utterance result MUST be recorded even when it is expected to fail.

**Layer 2 — normalized token-sequence identity (§1.3).** For utterances that diverge at layer 1,
apply the pinned normalizer to both sides and compare token sequences. `IDENTICAL` here means the
candidate differs from the anchor only in a dimension the normalizer is declared to ignore. That is
a PASS *for the identity oracle*, and the count of utterances that needed it is recorded as
`normalization_rescued_count` — a rising count across a lineage is a signal that the candidate is
drifting in formatting, which is release-relevant even when it never costs a word.

**Layer 3 — WER against the reference corpus (§1.4).** Runs on every utterance regardless of layers
1 and 2. It answers a different question: *is the anchor itself right?* Layer 3 is what detects a
candidate that matches a **wrong** anchor, and it is the only layer that speaks at all when the
determinism class is `bitwise_unstable`.

**Ordering rule (normative).** A candidate whose determinism class permits it MUST be evaluated at
layers 1–2 and MUST NOT be released on layer 3 alone. Substituting a WER band for an available
identity check is forbidden: a WER band is a *tolerance*, and a tolerance applied where an exact
answer was available silently authorizes drift up to the width of the tolerance.

---

### 1.2 Audio-input identity — bound to decoded samples, never to a file

**Every utterance MUST be bound by the SHA-256 of its decoded PCM**, together with sample rate,
channel count, sample format, and total sample count. The container file's hash is NOT sufficient and
MUST NOT be substituted: the identical audio stored as FLAC and as WAV has two file hashes and one
content; a resampler or dither change alters what was measured while leaving the file untouched.

The decode step (container demux → PCM) is part of the **instrument**, not part of the candidate. Its
identity — tool, version, and exact parameters — is recorded in every record, and a change to it is
an instrument-version boundary: records do not compare across it (`MEASUREMENT.md:83-84`).

A corpus whose per-utterance PCM hashes do not match those recorded for the anchor run **VOIDS the
window**. It is journaled `INVALID` with the mismatching utterance ids and is never recorded as a
candidate correctness failure — a different corpus says nothing whatever about the candidate, exactly
as a drifted anchor does not (`kernel-research.md:304-307`).

**Duration is recorded per utterance, from the decoded sample count**, never from a container header
and never from the engine's own report. `P-STT-2`'s real-time factor divides by this number, and a
self-reported duration would let the instrument set its own denominator.

---

### 1.3 Output normalization — the pinned pipeline

The normalizer is a **named, versioned, content-hashed** component of the evaluator bundle
(`stt_norm/vN`, hash recorded in every record). It lives under the measurement trust boundary and
MUST NOT be modified by any process inside the loop (`kernel-research.md:122-127`). **A change of
normalizer is a change of instrument**: records produced under two normalizer versions MUST NOT be
pooled, differenced, or compared.

Three properties are asserted by the instrument on every run, and a failure of any of them VOIDS the
window rather than degrading the score:

1. **Symmetry.** The identical normalizer is applied to reference, anchor hypothesis, and candidate
   hypothesis. A normalizer applied to one side manufactures errors on the other.
2. **Idempotence.** `norm(norm(x)) == norm(x)` for every string in the corpus. A non-idempotent
   normalizer makes the score depend on how many times it happened to run.
3. **Determinism.** No locale dependence, no dictionary lookup that can change, no host state. The
   normalizer's output for a fixed input is a function of the pinned bundle alone.

**The pipeline, in this exact order. The order is normative; several steps are not commutative.**

1. **Unicode NFKC, then `casefold()`.** Not `lower()`. `lower()` does not fold `ß`, `İ`, or the
   Kelvin sign; `casefold()` is the Unicode-correct operation and the two disagree on real
   transcription output. NFKC first, so that compatibility forms fold before case does.
2. **Non-lexical marker removal, from an ENUMERATED list.** whisper.cpp emits event tags where other
   engines emit nothing — `[BLANK_AUDIO]`, `[MUSIC]`, `[SOUND]`, `(silence)`, `[ Silence ]`, a bare
   `*`. Unremoved, each is a pure insertion against a reference that has no such convention, and the
   whole difference is a difference of *output convention*, not of recognition.
   - The list is **enumerated in the bundle and closed**. A general "delete anything inside brackets"
     rule is FORBIDDEN: a reference containing a genuine bracket would be silently truncated, and a
     candidate that learned to wrap its errors in brackets would score perfectly. This is the
     `feedback_fixture_must_not_remove_signal_under_test` failure in its scoring-side form.
   - **Removal is counted, per utterance and per arm.** A cross-arm asymmetry in
     `markers_removed_count` is itself a finding and is reported with the record. The project has
     already been bitten by the general case — a cross-arm gap in a scoring-side counter was a scorer
     bug, not a model difference (`feedback_parse_failure_rate_is_a_scoring_artifact`) — so the
     counter is mandatory, not optional telemetry.
   - An encountered marker-shaped span that is **not** on the list is NOT removed. It is recorded as
     `unknown_marker`, the utterance is routed to the failure taxonomy (§1.5), and the coverage gap is
     journaled. The controller RECORDS the gap; it does not extend the list
     (`kernel-research.md:122-127`).
3. **Punctuation → separator, never deletion.** Every character outside `[\w\s']` is replaced by a
   **space**, not removed. Deleting `,` in `a,b` yields one token where there were two and inflates
   both a deletion and a substitution. This is the token-level form of the comma-brittleness that
   already changed which model "won" on this project (`feedback_substring_scorer_comma_brittle`).
4. **Apostrophes preserved.** `'` is inside the retained class at step 3, deliberately. `don't` stays
   one token. Stripping it produces `dont`, which matches nothing on either side and converts a
   perfect transcription into a substitution.
5. **Hyphen split.** A hyphen is a separator (it was already replaced by a space at step 3); this step
   exists only to state that the choice is deliberate and symmetric. `large-v3` and `large v3` are the
   same two tokens on both sides.
6. **Numeral normalization — hypothesis side only, table-driven, and it FAILS rather than guesses.**
   This is the largest single source of spurious WER and the step the 2026-07-31 harness did not
   perform at all. LibriSpeech references spell numbers out (`nineteen twenty`); whisper emits digits
   (`1920`). One hypothesis token against two reference tokens is a substitution **plus** a deletion —
   two errors for a perfect transcription.
   - Direction: **hypothesis → reference form**, never both sides → digits. The reference is the fixed
     side. Converting the reference to digits is ambiguous in the wrong direction (`two thousand`,
     `twenty hundred` and `two zero zero zero` all map to `2000`, and the inverse map is not a
     function).
   - The converter is a **closed table** covering the numeral forms the corpus actually contains,
     enumerated at calibration time by scanning the reference corpus and the anchor's own hypotheses.
   - **An uncovered numeral form is `COULD_NOT_CHECK`, not a pass and not an error.** The utterance is
     excluded from the scored denominator, its exclusion is recorded with the offending token, and it
     is counted in `numeral_uncovered_count`. Silently scoring it as an error fabricates a regression;
     silently passing it through fabricates a match. Inability to evaluate is a third outcome.
   - **Exclusion is bounded by a derived cap, not by a literal.** The cap is the **anchor's own
     `numeral_uncovered` rate on the same corpus**, plus the A/A dispersion of that rate. A candidate
     whose exclusion rate exceeds the anchor's beyond that dispersion FAILS: it is emitting numeral
     forms the anchor does not, and a scorer that quietly drops them would be hiding the change under
     study.
7. **Whitespace collapse and strip.** Always last.

**Forbidden transforms, enumerated so that a later "improvement" is visibly out of contract.** No
stemming. No lemmatization. No stopword removal. No synonym or homophone mapping. No spell
correction. No fuzzy or edit-distance-tolerant token matching. No truncation of long outputs. Each of
these can convert a genuine recognition error into a match, and each is individually plausible as a
convenience. A normalizer that performs one is not a version of this normalizer; it is a different
instrument and requires a new protocol id.

---

### 1.4 The match rule and the reduction

- **Token** = a whitespace-delimited unit of the normalized string. Nothing else is a token.
- **Utterance error count** = the Levenshtein edit distance between the normalized reference token
  sequence and the normalized hypothesis token sequence, with unit cost for substitution, deletion
  and insertion. `S + D + I`, no weighting.
- **Corpus WER** = `Σ_utterances errors / Σ_utterances reference_tokens`, `lower-better`. This is the
  **pooled** estimator and it is the one this protocol defines.
  - **The mean of per-utterance WERs is a different quantity and MUST NOT be reported as corpus WER.**
    It weights a three-word utterance equally with a forty-word one and is dominated by short
    utterances, where a single error is 33 %. If a per-utterance distribution is wanted it is reported
    separately and labelled.
- **A match** — the layer-2 verdict — is `normalized_candidate_tokens == normalized_anchor_tokens`,
  element-wise. Not a similarity, not a threshold, not a ratio above some cutoff.
- **A mismatch is not automatically an error.** Every layer-2 mismatch is routed to the failure
  taxonomy (§1.5) *before* it is allowed to contribute to any number.

**Uncertainty is an utterance-level bootstrap, and a normal approximation is FORBIDDEN.** The paired
difference distribution between two STT arms is a point mass at zero with a heavy tail — measured on
the 2026-07-31 corpus, two real arms agreed exactly on 96 of 100 utterances and differed
substantially on 4 (Appendix S-A). A standard error computed as if the differences were normal is
wrong by an amount nobody can bound. The instrument resamples utterances with replacement, re-pools
numerator and denominator, and reports a percentile interval; the resample count and the seed derive
from the campaign seed and are recorded.

**Corpus size is DERIVED, never fixed by this protocol.** The corpus must be large enough that the
paired MDE is at or below the campaign's declared `contribution_floor`
(`kernel-research.md:185-186`). Procedure: measure the paired-difference bootstrap half-width on the
anchor at the calibration corpus size; half-width scales as `n^(-1/2)`; solve for the smallest `n`
meeting the floor; if that `n` exceeds the available corpus, the campaign **cannot** evaluate its
declared floor on this corpus and MUST record that and stop, rather than proceeding at a resolution it
has already computed to be insufficient. Worked precedent, descriptive only: at n=100 the observed
paired half-width was 0.67 pp, so a 0.30 pp floor needs ≈ 500 utterances and a 0.10 pp floor needs
≈ 4500 — the latter exceeding all of LibriSpeech test-clean (2620).

**Corpus identity and durability.** The corpus is named, versioned, and its manifest of
`(utterance_id, pcm_sha256, reference_text_sha256)` is recorded in the campaign manifest and resolves
in-repo per `MEASUREMENT.md:146-156`. A corpus living only under an ephemeral root
(`/mnt/raid0/llm/tmp`, `/tmp`, …) MUST NOT be used to calibrate a release gate.

**Selection / confirmation split.** The corpus is partitioned into disjoint selection and confirmation
strata by the `P-AK-SEARCH-1` rule (`kernel-research.md:308-318`), keyed on the campaign seed, before
the first candidate is scored. Confirmation utterances MUST NOT appear in planner context.

---

### 1.5 Failure taxonomy — a categorical failure MUST NOT be averaged into a rate

`feedback_classify_eval_failures_by_reason`. Every utterance receives exactly one class, and the class
is recorded:

| class | meaning | effect |
|---|---|---|
| `ok` | scored normally | contributes to WER |
| `empty` | hypothesis normalizes to zero tokens against a non-empty reference | **correctness FAIL**, not a WER contribution |
| `repetition_loop` | hypothesis token count exceeds the derived envelope (below) | **correctness FAIL** |
| `numeral_uncovered` | §1.3 step 6 | excluded from the denominator, counted, capped |
| `unknown_marker` | §1.3 step 2 | excluded from the denominator, counted, coverage gap journaled |
| `decode_error` | the engine returned a non-zero status or malformed output | **correctness FAIL** |

**Why this is mandatory and not bookkeeping.** The Qwen3-ASR arm on this host measured 29.36 % WER,
and that number was *not* a scoring artifact — it was a **degenerate repetition loop on 21 of 100
utterances carrying 94.7 % of all errors**, with the clean rows at 2.27 %. A corpus WER that averages
a repetition loop into a rate reports a model that is uniformly mediocre when the truth is a model
that is excellent and occasionally catastrophic. Those are different production risks and the release
decision differs between them.

**The repetition-loop envelope is DERIVED, not chosen.** It is the **maximum ratio of normalized
hypothesis tokens to normalized reference tokens observed on the ANCHOR over the calibration corpus**.
The detector therefore fires only outside the anchor's own observed behaviour, and its threshold is a
measured property of the instrument under this host state rather than a number somebody liked.
Recomputed whenever anchor identity changes (`kernel-research.md:202`).

**Any utterance not `ok` and not an excluded class is a correctness FAIL for the candidate, and
correctness is lexicographically prior to speed** (`kernel-research.md:355-360`,
`bench-cpu.md:89-90`). Such a candidate receives **no speed rank at all — not a penalised one**.

---

### 1.6 Oracles, caching, and the degraded-negative control

- Correctness verdicts are produced by the evaluator against the declared reference corpus and are
  **NEVER self-reported by the candidate** (`kernel-research.md:364-366`).
- **A candidate output MUST NEVER be cached or reused as a correctness oracle.** Cache state is
  declared in every record; `served_from_cache` FAILs.
- The degraded-negative control (`kernel-research.md:331-332`) for this backend is a candidate that is
  **fast because it is doing less** — a shortened mel window, a skipped decoder pass, a returned
  cached transcript. It MUST receive no speed rank at all. A control that merely scores *worse* is not
  a degraded-negative control; the control must be one that looks *faster and plausible*.

---

**Decision-grade requires ALL of:** this ratified protocol; a production-named whisper.cpp kernel per
`P-STT-REL-1` §4.1 (or, inside search, `P-AK-SEARCH-1`'s complete precondition set); layer-0 audio
identity verified against the anchor run; the pinned normalizer id and hash, with symmetry,
idempotence and determinism asserted in-run; layer-1 and layer-2 verdicts recorded per utterance; the
pooled corpus WER with its bootstrap interval, resample count and seed; a published MDE and a corpus
size derived from the campaign's `contribution_floor`; the complete failure taxonomy with counts for
every class; the derived repetition envelope and the derived numeral-exclusion cap; the corpus
manifest with per-utterance PCM hashes, resolving in-repo; the stratum; cache state; and retained raw
per-utterance transcripts from which the reduction is recomputable. Missing ANY → **observation**, and
inside search → `INVALID`.

**Prospective.** Applies only to runs started after ratification. It retro-certifies no artifact,
issues no ruling over any existing corpus, and upgrades no pre-ratification speech measurement. In
particular the 2026-07-31 WER figures — including `wer_pct: 2.35` as carried in
`artifacts/operator/ratify_speech_kernel_freeze_20260731.json`, whose engine attribution is questioned
in *Metric-direction defect closed by this annex* above — remain observations, and this protocol
neither corrects nor certifies them.

**Grammar:**
`STT corpus WER <value> % lower-better, n=<utterances> [P-STT-1, norm=<normalizer_id>@<norm_sha256[:12]>, corpus=<corpus_id>@<manifest_sha256[:12]>, boot95=[<lo>,<hi>], MDE=<mde>, identity=<n_identical>/<n_utterances>, taxonomy=<ok>/<empty>/<reploop>/<numeral>/<marker>/<decode_err>, cache=<cache_state>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

Inside search this record additionally carries the full `P-AK-SEARCH-1` grammar and the words
**SEARCH RECORD, NOT A CLAIM**.

---

## P-STT-2 — STT speed: real-time factor, latency, and throughput (RATIFIED 2026-08-03)

**Purpose.** To make an STT speed number interpretable. The project's existing STT speed figures are
not: a single "xRT" was carried for the CPU incumbent until the 2026-07-31 measurement showed wall
time was **~constant at `4.18 s + 0.010 × audio_s`** — a fixed per-request floor from 30-second mel
padding — which makes a single ratio meaningless and makes the ratio's value a function of the corpus'
duration mix rather than of the engine.

**Scope.** Any decision-gating `whisper_stt` speed number. Metric definitions below are exclusive;
substituting one for another is forbidden (`MEASUREMENT.md:25-26`).

**Metrics, each with its direction stated because a bare number is unusable:**

- **`rtf` = `wall_seconds / audio_seconds`, `lower-better`.** The canonical form.
- **`xrt` = `audio_seconds / wall_seconds`, `higher-better`.** Permitted only when labelled `xrt`.
  A bare "real-time factor" with no direction is **non-conforming**.
- **`latency_s`, `lower-better`** — per-request wall time, reported as median **and** p95. The tail is
  first-class, not a footnote: a conversational voice loop is governed by its worst request.
- **`throughput_audio_s_per_wall_s`, `higher-better`** — audio-seconds transcribed per wall-second at
  a declared concurrency. **Measured directly at that concurrency, never reconstructed** from a
  single-stream RTF times a stream count (`gpu-cross-device.md:111-116`).

**RTF is never reported as a single scalar for a corpus with mixed durations.** It is reported
**per duration stratum**, with the strata declared in the campaign manifest and derived from the
corpus' own duration distribution (equal-count quantiles, count derived from the corpus size and the
per-stratum MDE requirement). A corpus-wide RTF MAY be quoted alongside, labelled as such, and never
as the headline. The 2026-07-31 CPU figures are the precedent: median xRT 0.80 under 5 s, 1.49 at
5–10 s, 2.89 at 10–20 s, 7.22 on a 57 s clip — four numbers for one engine, and any one of them
presented alone is a claim about the corpus rather than about the kernel.

**The fixed-cost term is reported, not hidden.** The instrument fits `wall = a + b × audio_s` by least
squares over the corpus and records `a` (per-request fixed cost, seconds) and `b` (marginal cost,
dimensionless) with their intervals. A kernel change that halves `b` while leaving `a` untouched is a
different release proposition from one that removes `a`, and an RTF ratio cannot tell them apart.

**Preconditions.** All of `P-AK-SEARCH-1`'s preconditions apply to a search run, and their release
analogues to a release run: an acquired resource claim covering the exact footprint (a device claim
for MI210 cells; idle sensing is never a claim); host-health tier per `bench-cpu.md:17-19`; an
explicit immutable anchor by source commit, binary SHA-256 and linkage SHA-256, re-verified at window
open and close; the evaluator bundle hash and runtime source-label attestation; a codified recipe
constructor — **hand-typed argv voids the run** (`bench-cpu.md:8-10`); and storage headroom.

**Linkage is a precondition of every STT speed number, and it is the one that has already failed.**
Before any measurement the runner MUST prove the candidate binary resolves its **own** tree's ggml, by
executing `epyc-inference-research/scripts/utils/verify_ggml_linkage.sh <binary> <tree_root>` (the
script lives in the research repo, not in epyc-root) and retaining its complete output. On 2026-07-31
a HIP-built `whisper-cli` loaded the production CPU-only ggml through an ambient `LD_LIBRARY_PATH`,
found no GPU, and ran full-CPU **while printing `use gpu = 1`** — the run completed, the output was
well-formed, and only the throughput was quietly wrong. Three ggml generations coexist on this host
(llama 0.16.0, qwentts 0.17.0, whisper 0.18.0), so this is a standing hazard and not a historical one.

Two clauses follow, and both are normative:

1. **A `PASS` from the linkage verifier is necessary and NOT sufficient.** ggml backends are
   `dlopen`ed at runtime and `ldd` does not see them. The record MUST additionally carry the engine's
   own startup device line (e.g. `Device 0: AMD Instinct MI210`). A `use gpu = 1` flag reports what
   was **requested**, never what was **loaded**, and MUST NOT be accepted as device evidence.
2. **A verifier run that resolved no libraries at all is `COULD_NOT_CHECK`, never `PASS`.** The script
   prints `(no ggml/whisper/llama libs in ldd output — statically linked, or ldd failed)` and then
   exits 0; a consumer that reads only the exit status converts "the check could not run" into "the
   check passed". Records under this protocol read the *report*, not the status.

**Reps and reduction.** Per the P-BENCH-1 rule (`bench-cpu.md:21-22`) — ≥5 for ≥5 % effects, ≥10 for
≤2 % effects — and never fewer than the calibrated `B_min` paired blocks. Report median + MAD.
Candidate and anchor **interleaved and order-randomized within every paired block**; blocked designs
are forbidden (`gpu-cross-device.md:141-142`). Anchor measured first in every window and compared
against its calibrated acceptance band; outside the band the window is **VOID**
(`bench-cpu.md:231-233`).

**Decision-grade requires ALL of:** this ratified protocol; the metric named with its direction and
its denominator; per-stratum RTF with the strata declared before measurement; the fitted `a` and `b`
with intervals; median **and** p95 latency; throughput measured at its declared concurrency and never
reconstructed; an acquired claim re-verified at window close; a passing host-health tier; an explicit
immutable anchor re-verified byte-for-byte; a passing anchor gate; the linkage verifier's complete
output **plus** the engine's own device line; the codified recipe constructor id and hash; reps per
the P-BENCH-1 rule; median + MAD; a published MDE; an e-process verdict against its calibrated
threshold — never an ad-hoc bound and never an LCB in its place (`kernel-research.md:277-285`); and
retained raw samples. Missing ANY → **observation**.

**Prospective.** Applies only to runs started after ratification. The 2026-07-31 STT speed figures —
CPU wall `4.18 + 0.010 × audio_s`, MI210 wall median 0.124 s / max 0.218 s, encode 3751 → 110 ms —
are observations and remain so.

**Grammar:**
`STT <rtf|xrt|latency_s|throughput_audio_s_per_wall_s> <value> <lower-better|higher-better>, stratum <label>, n=<reps> [P-STT-2, median+MAD=<med>±<mad>, MDE=<mde>, e=<e-value>/thr=<1/α>, fit a=<a>s b=<b>, concurrency=<c>, linkage=<PASS|COULD_NOT_CHECK>+device=<device_line>, recipe=<id>@<sha[:12]>, res=<claim_receipt>, host=<host_receipt>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

---

## P-STT-3 — STT stability, memory, and op-coverage integrity (RATIFIED 2026-08-03)

**Purpose.** To catch the failures that a correctness corpus and a stopwatch both miss: a leak, a
teardown race, and a test suite that got *smaller* while its pass rate stayed at 100 %.

**Scope.** Any `whisper_stt` release gate, and any search record whose candidate touches memory
management, backend dispatch, or op registration. Its clauses are written backend-agnostically and
are cited by reference from the TTS family, which they bind with full force. Emits a **verdict, not a
claim**.

**Memory stability.** Repeated load → transcribe → unload cycles at a declared count derived from the
campaign's `contribution_floor` for the memory metric. Record host RSS and, for MI210 cells, VRAM,
sampled at a fixed point in each cycle. The reported quantity is the **slope** of the resident set
over cycles, `lower-better`, with its interval. **The acceptance band is the anchor's own slope
distribution under the identical recipe**, computed by the calibration block — never a literal "must
not grow by more than X MB". A candidate whose slope interval lies within the anchor's band passes; a
candidate above it fails; a candidate whose interval straddles the band boundary is
`no detectable difference`, which is a result.

**Teardown and cleanup.** Every cycle verifies that the process exits, that its device memory is
released, and that no file descriptor or shared-memory segment survives. A cleanup failure is a FAIL
regardless of throughput (`bench-cpu.md:89-90`).

**Op-coverage integrity — a pass count is meaningless without its enumeration.** This clause exists
because of a concrete event on this host: the gfx90a argsort defect was found only after
`test-backend-ops` reported **ARGSORT 74/74 and TOP_K 292/292** where it had previously reported
**46/46 and 170/170 — with the failing shapes silently skipped**. Both readings are "100 % pass". The
rule:

- Every op-test record MUST carry the **enumeration**: the number of cases *attempted*, the number
  *skipped*, and the skip reasons, alongside the number passed.
- **A candidate whose attempted-case count is lower than the anchor's for the same op FAILS**, even at
  100 % pass. A shrinking enumeration is the signature of a shape becoming unsupported and being
  silently dropped, which is indistinguishable from a fix if only the ratio is read.
- A skip whose reason the harness does not report is `COULD_NOT_CHECK` for that op, and the coverage
  gap is journaled.

**Service smoke.** For cells that exercise `whisper-server`, a smoke check of the served endpoint's
contract (accepts audio, returns a transcript, honours its declared parameters) is required. It
**unblocks work and gates nothing** — it is `P-SMOKE-1`-grade and MUST NOT be reported as correctness
evidence.

**Decision-grade requires ALL of:** this ratified protocol; the declared cycle count with its
derivation; per-cycle RSS/VRAM samples retained; the slope with its interval and the anchor's
calibrated band; a clean teardown verdict for every cycle; op-test records carrying attempted /
skipped / passed with skip reasons for every op in the affected-surface manifest; and the anchor's
corresponding enumeration for comparison. Missing ANY → **observation**.

**Prospective.** Applies only to runs started after ratification.

**Grammar:**
`STT stability <PASS|FAIL|NO_DETECTABLE_DIFFERENCE>, cycles=<n> [P-STT-3, rss_slope=<v>MiB/cycle lower-better CI=[<lo>,<hi>], anchor_band=[<lo>,<hi>], vram_slope=<v>MiB/cycle, teardown=<n_clean>/<n>, ops=<attempted>/<skipped>/<passed> vs anchor <attempted>/<skipped>/<passed>, YYYY-MM-DD]`

---

## P-STT-REL-1 — the STT kernel-release decision rule (RATIFIED 2026-08-03)

**Purpose.** One rule that reads `P-STT-1`, `P-STT-2` and `P-STT-3` together and produces a release
verdict for a whisper.cpp candidate. **It is an input to an operator's freeze decision and is never a
freeze trigger.**

**Scope.** A sealed whisper.cpp release candidate evaluated at T3 (owning handoff §10). Emits
`PASS` / `FAIL` / `PASS_WITH_WAIVER` — a **verdict, not a claim**.

**What this protocol does NOT authorize.** No freeze, no cutover, no era-registry row, no AutoPilot
baseline apply, no commit to `production-speech-v1` or any future `production-speech-vN`, no repointing
of `/mnt/raid0/llm/kernels/production/stt`. Those are the human-only writes at
`MEASUREMENT.md:140-142`, and a `PASS` here MUST NOT be cited as a reason any of them may be performed
automatically.

### 4.1 Release identity

The candidate MUST be a **clean committed tree whose binary reports that commit**, with recorded
branch, commit, dirty status, binary and shared-library SHA-256s, `ldd`, model path/size/SHA-256,
complete argv, complete effective environment, and date. This is `bench-cpu.md:38-44` and is **cited,
not restated** — where a rule already lives, the amendment goes (`kernel-research.md:22-23`). Two
whisper-specific additions:

- **The tree vendors ggml in-tree, not as a submodule.** whisper.cpp's own production patch
  (`b3073792`, `ggml/src/ggml-cuda/vendors/hip.h`, 1 file, 2 changed lines) is a direct file edit. The
  source-closure identity test (owning handoff §3.2, stage 1) therefore operates on the superproject
  alone — **and the adapter MUST assert this rather than assume it**, because the sibling TTS tree is
  the opposite case and a shared assumption would be wrong for one of them.
- **The linkage proof of `P-STT-2` is part of release identity**, not merely of the speed cell. A
  candidate whose libraries resolve outside its own tree has no valid cells at all.

### 4.2 The backend-unchanged test, in its single-backend form

`whisper.cpp` serves exactly one backend, so the owning handoff §3.2 cell-dropping transfer — where an
unchanged backend's evidence transfers by identity — has **no counterpart here**: there is no second
backend to drop. Both stages still run, for the opposite purpose: to establish that the candidate
binary **differs from the incumbent at all**. A candidate whose source closure is empty and whose
normalized binary comparison reports identity is a **no-op candidate** and is refused before it
consumes a release matrix, rather than passing every gate trivially. A disagreement between stage 1
and stage 2 is a hard finding filed against the build-identity machinery, never a silent preference
for the cheaper answer.

### 4.3 The rule

**Lexicographic, correctness first** (`kernel-research.md:355-360`):

1. **Correctness gate (P-STT-1).** Zero utterances in `empty`, `repetition_loop` or `decode_error`.
   Layer-1/layer-2 identity against the anchor on every utterance the determinism class permits.
   Where identity is not available, the paired ΔWER non-inferiority e-process must clear its
   calibrated threshold against a **derived** margin: `margin = max(φ_corr, contribution_floor_corr)`,
   where `φ_corr` is the correctness instrument's A/A noise floor measured through the identical
   pipeline. **When the determinism class is `bitwise_stable`, `φ_corr` is exactly 0 and the rule
   collapses to identity** — which is the strong form and is what MUST be used whenever it is
   available. A failure here yields **no speed rank at all, not a penalised one**.
2. **Integrity gate (P-STT-3).** Memory slope within the anchor's band; clean teardown; op-test
   enumeration not smaller than the anchor's.
3. **Speed gate (P-STT-2).** Per metric and per duration stratum, at the **production-optimal recipe
   for every protected cell**, the owning handoff §1.6 objective: non-inferior on every phase,
   improved on at least one. Baseline / off-recipe cells are diagnostic and never veto or justify a
   release (owning handoff §4 invariant 15).

**Bands are DERIVED per cell by the campaign calibration block** (`kernel-research.md:195-270`). No
band in this protocol is a literal.

**The decision-rule SHAPE — and only the shape — is adopted from `bench-cpu.md:83-88`:** a pass region,
an inconclusive region resolved by **one fresh reversed-order pair pooled to a pre-declared
threshold**, and a fail region. The CPU protocol's literals (`≥0.98 PASS`, `<0.95 FAIL`) are
**explicitly NOT imported**: they were calibrated on `llama-bench` CPU prefill dispersion, and applying
them to an STT RTF cell whose dispersion is a different quantity is the category error
`feedback_gate_scope_must_match_measured_subset` names. This is the same adopt-shape-not-thresholds
discipline `P-AK-SEARCH-1-A1` applied to its own source (`kernel-research.md:446-450`).

**Mechanism plausibility.** A banked whisper.cpp candidate requires an explanation backed by bytes,
FLOPs, counters, or a clean A/B (`P-AK-SEARCH-1-A1` clause 1). *"It got faster and I don't know why"*
is a reason to keep measuring, not to release.

### 4.4 Waivers

An operator waiver is a first-class input (owning handoff §10.4). It is a hash-pinned, human-only
`epyc.autokernel.operator_waiver.v1` object carrying scope, reason, forfeited claims, protocol
binding, campaign binding, and an expiry/reopen predicate. **The evaluator verifies the waiver's hash
and predicate; it never judges its merits.** A waived cell suppresses the corresponding claim in the
release receipt, and the verdict becomes `PASS_WITH_WAIVER`.

### 4.5 Complexity ceiling

Per owning handoff §10.6 the backend adapter declares a complexity/blast-radius ceiling, and above it
the release package is marked `REQUIRES_HUMAN_CODE_REVIEW` and says so on its first page. For
`whisper_stt` the ceiling is **derived from the backend's own accepted production history**: the
maximum changed-lines and files-touched across every commit on `production-speech-v1` beyond its
upstream base. That history is currently **one commit, one file, two changed lines**, so the ceiling is
very low and essentially every LLM-authored change to this tree will be marked for human review. That
is the correct outcome for a third-party tree this project does not own, and inflating the ceiling to
make the loop convenient would be a downgrade dressed as a calibration. Recomputed at every freeze.

**Decision-grade requires ALL of:** this ratified protocol; a sealed candidate meeting §4.1; both
stages of §4.2 run and agreeing; the correctness gate passed with its derived margin; the integrity
gate passed; the speed gate passed at production-optimal recipes on every protected cell, per stratum,
under `P-STT-2`; every band derived by a completed and accepted calibration block; the pre-committed
stopping rule unmodified; controls 1–4 available and passing and control 5 either passing or explicitly
recorded `HISTORICAL_REPLAY_UNAVAILABLE` with an operator escalation on the record; a mechanism
explanation; any active waiver hash-pinned and its predicate verified; the complexity assessment; and
the complete sealed evidence bundle. Missing ANY → the verdict is `FAIL`, or `PASS_WITH_WAIVER` only
where a conforming waiver covers exactly the failing cell.

**Prospective.** Applies only to runs started after ratification. No pre-ratification whisper.cpp
artifact may be retro-certified under this protocol, and the 2026-07-31 speech freeze — which was
executed under no STT protocol, because none existed — is not retro-conforming and is not reopened by
this protocol's existence.

**Grammar:**
`STT release verdict <PASS|FAIL|PASS_WITH_WAIVER> for whisper.cpp <candidate_commit[:12]> vs <anchor_commit[:12]>/<anchor_binary_sha256[:12]>/<anchor_linkage_sha256[:12]> [P-STT-REL-1, correctness=<PASS|FAIL> (margin=<m>, det=<determinism-class>), integrity=<PASS|FAIL>, speed=<PASS|FAIL> (cells <n_pass>/<n_total>), unchanged_test=<stage1>/<stage2>, controls=<4/5|5/5>, waivers=<none|waiver_sha256[:12]…>, review=<REQUIRES_HUMAN_CODE_REVIEW|none>, eval=<bundle_sha256[:12]>, bundle=<release_bundle_sha256[:12]>, YYYY-MM-DD]`

**This verdict authorizes nothing.** It is evidence an operator reads before executing a freeze.

---

# TTS family — `qwentts_tts`

**Backend:** `qwentts_tts`. **Source tree:** `qwentts.cpp`. **Frozen production branch:**
`production-speech-v1` (`2c1b5182e7e9f1acaa04405ff21747d8a7acf4d5`, ggml 0.17.0, ggml submodule
`b86f660238dcc1a83b7cbf5a72d355a965de9245`). **Stable path:**
`/mnt/raid0/llm/kernels/production/tts` → `qwentts.cpp/build`.

**Two structural asymmetries, stated first because assuming uniformity is how an adapter gets one of
them wrong:**

1. **The stable path points at `build`, not `build/bin`.** The other three production binaries
   (`cpu`, `gpu`, `stt`) resolve into a `bin/` subdirectory; this one does not (owning handoff §1.5).
   A path constructor that appends `bin/` for every backend produces a non-existent path here.
2. **`ggml` is a git SUBMODULE, not vendored in-tree.** `whisper.cpp` edits
   `ggml/src/ggml-cuda/vendors/hip.h` as a file in its own tree; `qwentts.cpp` carries a gitlink. The
   consequence is load-bearing for owning handoff §3.2 and §10.6: the production commit `2c1b5182`
   shows **`ggml | 2 +-`, one file, one insertion, one deletion** in the superproject, while the
   submodule commit it points at (`b86f6602`) changes **4 files and 115 lines** — the thread-strided
   bitonic argsort plus the ROCm 6.2 FP8 guard. A source-closure diff or a complexity assessment
   computed on the superproject alone under-reports this change by two orders of magnitude.

**Independently freezable.** `qwentts.cpp` serves exactly one backend, so its freeze scope is one tree
and one backend (owning handoff §1.5), independent of `whisper.cpp` and of `llama.cpp`.

---

## P-TTS-1 — text/audio identity and deterministic/numerical checks (RATIFIED 2026-08-03)

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
- **Cache state** — declared in every record (`kernel-research.md:364-366`). `served_from_cache`
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
  which is an affected-surface finding (owning handoff §4 invariant 18: declared equals traced).
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
  by the A/A control (`kernel-research.md:333-336`) and computed by the calibration block. **If the
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
- **Determinism class is an interface** (owning handoff §4 invariant 12). Same-seed run-to-run bitwise
  stability is measured, declared per record as `bitwise_stable` / `bitwise_unstable` /
  `not_measured`, and a **change of class is itself release-relevant** even when every other check
  passes. `not_measured` is in the vocabulary so that "we did not check" is sayable without implying
  stability.

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
`TTS identity <IDENTICAL|DIVERGENT|COULD_NOT_CHECK>, n=<utterances> [P-TTS-1, greedy=<true>, codes=<n_identical>/<n>, code_sha=<candidate[:12]>/<anchor[:12]>, samples=<n_identical>/<n>, maxabs=<v> tol=<t>, spectral=<v> tol=<t>, reducer=<id>@<sha[:12]>, nan=<none|COUNT>, clip=<frac> band=[<lo>,<hi>], det=<determinism-class>, cache=<state>, YYYY-MM-DD]`

---

## P-TTS-2 — intelligibility floor and reference-waveform distance, human-independent (RATIFIED 2026-08-03)

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
   oracle.** The two backends are independently freezable and independently researched (owning handoff
   §1.5), and an oracle that is itself under optimization confounds every reading taken through it.
   The TTS oracle is the frozen production STT kernel, full stop.
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
  (`kernel-research.md:331-332`) for this backend MUST include such a candidate, and it MUST receive
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
production readiness, or lineup evidence"* (`handoffs/active/multimodal-pipeline.md`, M-2QA,
2026-07-27), and this protocol does not lift that.

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

## P-TTS-3 — first-audio latency, real-time factor, and synthesis throughput (RATIFIED 2026-08-03)

**Purpose.** To fix one definition of each TTS speed quantity, in a project that carried the same
measurement in two reciprocal conventions across two durable artifacts (*Metric-direction defect
closed by this annex*, above).

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
  single-stream `rtf` times a stream count is FORBIDDEN (`gpu-cross-device.md:111-116`).

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

**Linkage.** Before any measurement,
`epyc-inference-research/scripts/utils/verify_ggml_linkage.sh <binary> <tree_root>` (the script lives
in the research repo) MUST be executed against the candidate binary and its complete output retained.
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
pair — are observations and remain so; *Metric-direction defect closed by this annex* above records
that the two are reciprocals of one another whose values do not agree, which is itself a reason no
future record may inherit either.

**Grammar:**
`TTS <ttfa_ms|rtf|xrt|throughput_audio_s_per_wall_s> <value> <lower-better|higher-better>, n=<reps> [P-TTS-3, median+MAD=<med>±<mad>, p95=<v>, stages Talker=<ms>(<pct>%)/CodePredictor=<ms>(<pct>%)/CodecDecode=<ms>(<pct>%), audio_s=<v> from <n_samples>@<rate>Hz, concurrency=<c>, MDE=<mde>, e=<e-value>/thr=<1/α>, linkage=<PASS|COULD_NOT_CHECK>+device=<device_line>, recipe=<id>@<sha[:12]>, res=<claim_receipt>, host=<host_receipt>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

---

## TTS stability and op-coverage integrity — governed by `P-STT-3`

There is deliberately no `P-TTS-4`. TTS stability, memory growth and op-coverage integrity are
governed by **`P-STT-3`**, whose clauses are written backend-agnostically and are cited here rather
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

## P-TTS-REL-1 — the TTS kernel-release decision rule (RATIFIED 2026-08-03)

**Purpose.** One rule that reads `P-TTS-1`, `P-TTS-2`, `P-TTS-3` and `P-STT-3` together and produces a
release verdict for a qwentts.cpp candidate. **It is an input to an operator's freeze decision and is
never a freeze trigger.**

**Scope.** A sealed qwentts.cpp release candidate evaluated at T3 (owning handoff §10). Emits
`PASS` / `FAIL` / `PASS_WITH_WAIVER` — a **verdict, not a claim**.

**What this protocol does NOT authorize.** No freeze, no cutover, no era-registry row, no AutoPilot
baseline apply, no commit to `production-speech-v1` or any future `production-speech-vN`, no repointing
of `/mnt/raid0/llm/kernels/production/tts`. Those are the human-only writes at
`MEASUREMENT.md:140-142`.

### 4.1 Release identity

`bench-cpu.md:38-44` governs candidate release identity and is **cited, not restated**. Three
qwentts-specific additions:

- **The source closure MUST traverse the `ggml` submodule.** A closure computed on the superproject
  alone reports the production change as one line when it is 115 across four files (TTS family header
  above; owning handoff §3.2 stage 1). The closure is obtained from the build system's own dependency
  information (CMake/Ninja depfiles), never from a hand-maintained list or a directory-prefix guess,
  and the submodule's commit is recorded as part of candidate identity in its own right.
- **The stable path is `build`, not `build/bin`.** Any release-transaction dry-run that constructs the
  install path by appending `bin/` is wrong for this backend and MUST be caught at owning handoff
  §10.2 phase 8, not discovered at cutover.
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
   the owning handoff §1.6 objective: non-inferior on every phase, improved on at least one, with
   per-stage attribution recorded. Baseline / off-recipe cells are diagnostic and never veto or justify
   a release (owning handoff §4 invariant 15).

**Bands are DERIVED per cell by the campaign calibration block** (`kernel-research.md:195-270`). No band
in this protocol is a literal.

**The decision-rule SHAPE — and only the shape — is adopted from `bench-cpu.md:83-88`:** a pass region,
an inconclusive region resolved by one fresh reversed-order pair pooled to a pre-declared threshold, and
a fail region. Its literals (`≥0.98`, `<0.95`) are **explicitly NOT imported**; they were calibrated on
CPU `llama-bench` prefill dispersion and mean nothing for a TTFA or a spectral distance
(`feedback_gate_scope_must_match_measured_subset`). Same discipline as `P-AK-SEARCH-1-A1`
(`kernel-research.md:446-450`).

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

Per owning handoff §10.6, derived from the backend's own accepted production history: the maximum
changed-lines and files-touched across every commit on `production-speech-v1` beyond its upstream base,
**computed with the submodule expanded**. That history is currently one superproject commit whose
expanded closure is **4 files and 115 changed lines**, all of it inside `ggml/src/ggml-cuda/` — i.e.
shared core. The adapter therefore declares `shared_core_modification_requires_review = true`
unconditionally for this backend, and the ceiling is low enough that most LLM-authored changes here
will be marked `REQUIRES_HUMAN_CODE_REVIEW`. That is the correct outcome for a third-party tree this
project does not own and whose upstream it does not control. Recomputed at every freeze.

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
`TTS release verdict <PASS|FAIL|PASS_WITH_WAIVER> for qwentts.cpp <candidate_commit[:12]>+ggml<submodule_commit[:12]> vs <anchor_commit[:12]>/<anchor_binary_sha256[:12]>/<anchor_linkage_sha256[:12]> [P-TTS-REL-1, identity=<PASS|FAIL> (det=<determinism-class>), intelligibility=<PASS|FAIL> (floor=<v>, <saturated|unsaturated>, stt=<binary_sha256[:12]>), integrity=<PASS|FAIL>, speed=<PASS|FAIL> (cells <n_pass>/<n_total>), unchanged_test=<stage1_submodule_traversed>/<stage2>, controls=<4/5|5/5>, waivers=<none|waiver_sha256[:12]…>, review=<REQUIRES_HUMAN_CODE_REVIEW|none>, eval=<bundle_sha256[:12]>, bundle=<release_bundle_sha256[:12]>, YYYY-MM-DD]`

**This verdict authorizes nothing.** It is evidence an operator reads before executing a freeze.

---

## Appendix S-A — derivations for the figures cited in this annex (descriptive, never thresholds)

Every figure below is a **re-reduction of an existing artifact**, computed without inference, without
a benchmark and without a build. The source is `/mnt/raid0/llm/tmp/stt_wer_results.json` (2026-07-31,
LibriSpeech test-clean, n=100 utterances, 1870 reference words), which is an **ephemeral-root
artifact** under `MEASUREMENT.md` §5 durability classes — it is not carried in git and may not exist
tomorrow. It is used here to establish *procedure* and *order of magnitude*, never as a threshold, and
`P-STT-1` requires the corpus it eventually calibrates on to be durable.

Reduction: corpus WER is pooled, `Σ errors / Σ reference tokens`. Uncertainty is an
utterance-level bootstrap, 2000 resamples, seed 42, percentile interval.

| arm | errors / ref words | WER | bootstrap 95 % interval | half-width |
|---|---|---|---|---|
| faster-whisper large-v3-turbo int8, CPU 48t | 44 / 1870 | 2.35 % | [1.56, 3.20] | 0.83 pp |
| whisper.cpp large-v3-turbo f16, MI210, greedy | 63 / 1870 | 3.37 % | [2.26, 4.67] | 1.21 pp |
| whisper.cpp large-v3-turbo f16, MI210, beam 5 | 61 / 1870 | 3.26 % | [2.25, 4.37] | 1.06 pp |
| whisper.cpp large-v3 f16, MI210, greedy | 62 / 1870 | 3.32 % | [2.28, 4.63] | 1.18 pp |

**Paired reduction, greedy vs beam-5 on the identical corpus** (4000 resamples, seed 42, resampling
utterances and re-pooling numerator and denominator): the two arms produce different transcripts on
**4 of 100** utterances; paired ΔWER point estimate **+0.107 pp**, 95 % interval **[−0.43, +0.91] pp**,
half-width **0.67 pp**.

Three things follow, and all three are used as *derivations* by the protocols above rather than as
numbers:

1. **Pairing helps, but far less than for a rate metric.** 1.21 pp unpaired → 0.67 pp paired is a
   factor of 1.8, not the order of magnitude a paired design buys on a throughput cell. The reason is
   visible in the raw data: the arms agree exactly on 96 of 100 utterances and disagree substantially
   on 4, so the paired difference distribution is a point mass at zero with a heavy tail. A normal
   approximation on this distribution is wrong; the bootstrap is not optional.
2. **A 100-utterance corpus cannot resolve a 0.1 pp difference,** which is the size of the difference
   actually observed between three real candidate configurations. `P-STT-1` therefore sizes the
   corpus from the campaign's declared `contribution_floor` rather than fixing a count: half-width
   scales as `n^(-1/2)`, so reaching a 0.3 pp paired half-width from this dispersion needs
   `100 × (0.67 / 0.30)² ≈ 500` utterances, and reaching 0.1 pp needs ≈ 4500. LibriSpeech test-clean
   holds 2620 utterances in total, so a 0.1 pp floor is **not reachable on this corpus** — a fact a
   campaign must confront at calibration time rather than discover after spending its budget.
3. **The three whisper.cpp arms are one verdict, not three.** 3.37 / 3.26 / 3.32 with a 0.67 pp paired
   half-width is `no detectable difference`, which `gpu-cross-device.md:154-155` makes a result and a
   decision rather than a failed experiment. Reporting them as a ranking would be a scoring artifact
   of exactly the class `feedback_per_suite_gate_resolution_artifact` names.
