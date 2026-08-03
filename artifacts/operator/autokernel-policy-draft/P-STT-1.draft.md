<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Authored by an agent under AK9; an agent cannot ratify
     and `measurement/protocols/` is hook-blocked.
     Target: the STT half of NEW FILE measurement/protocols/speech (Annex S). Container, annex
     placement, core-file deltas and operator items: Annex-S-speech-container.draft.md.
     Owning handoff: handoffs/active/autokernel-research-loop.md §13.3, §14 AK9. -->

# Annex S — speech protocols · STT family (draft text)

**Backend:** `whisper_stt`. **Source tree:** `whisper.cpp`. **Frozen production branch:**
`production-speech-v1` (`b307379226d93d9c5ed790d7cea0626613c0ef4b`, ggml 0.18.0). **Stable path:**
`/mnt/raid0/llm/kernels/production/stt` → `whisper.cpp/build/bin`.

**Independently freezable.** `whisper.cpp` serves exactly one backend, so its freeze scope is one
tree and one backend (§1.5). Unlike `llama_cpu`/`llama_gpu` it shares no tree with anything, and a
whisper freeze creates no obligation on any other backend.

---

## P-STT-1 — STT transcription correctness: corpus, normalization, and the match rule

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
(`kernel-research.md:25-26`, `:381-400`).

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
as a drifted anchor does not (`kernel-research.md:302-305`).

**Duration is recorded per utterance, from the decoded sample count**, never from a container header
and never from the engine's own report. `P-STT-2`'s real-time factor divides by this number, and a
self-reported duration would let the instrument set its own denominator.

---

### 1.3 Output normalization — the pinned pipeline

The normalizer is a **named, versioned, content-hashed** component of the evaluator bundle
(`stt_norm/vN`, hash recorded in every record). It lives under the measurement trust boundary and
MUST NOT be modified by any process inside the loop (`kernel-research.md:120-125`). **A change of
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
     (`kernel-research.md:120-125`).
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
substantially on 4 (container draft §7). A standard error computed as if the differences were
normal is wrong by an amount nobody can bound. The instrument resamples utterances with replacement,
re-pools numerator and denominator, and reports a percentile interval; the resample count and the
seed derive from the campaign seed and are recorded.

**Corpus size is DERIVED, never fixed by this protocol.** The corpus must be large enough that the
paired MDE is at or below the campaign's declared `contribution_floor`
(`kernel-research.md:181-183`). Procedure: measure the paired-difference bootstrap half-width on the
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
strata by the `P-AK-SEARCH-1` rule (`kernel-research.md:306-316`), keyed on the campaign seed, before
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
Recomputed whenever anchor identity changes (`kernel-research.md:198-200`).

**Any utterance not `ok` and not an excluded class is a correctness FAIL for the candidate, and
correctness is lexicographically prior to speed** (`kernel-research.md:355-360`,
`bench-cpu.md:89-90`). Such a candidate receives **no speed rank at all — not a penalised one**.

---

### 1.6 Oracles, caching, and the degraded-negative control

- Correctness verdicts are produced by the evaluator against the declared reference corpus and are
  **NEVER self-reported by the candidate** (`kernel-research.md:362-364`).
- **A candidate output MUST NEVER be cached or reused as a correctness oracle.** Cache state is
  declared in every record; `served_from_cache` FAILs.
- The degraded-negative control (`kernel-research.md:329-331`) for this backend is a candidate that is
  **fast because it is doing less** — a shortened mel window, a skipped decoder pass, a returned
  cached transcript. It MUST receive no speed rank at all. A control that merely scores *worse* is not
  a degraded-negative control; the control must be one that looks *faster and plausible*.

---

**Decision-grade requires ALL of:** this ratified protocol; a production-named whisper.cpp kernel per
`P-STT-REL-1` §4 (or, inside search, `P-AK-SEARCH-1`'s complete precondition set); layer-0 audio
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
in the container draft §4 — remain observations, and this protocol neither corrects nor certifies
them.

**Grammar:**
`STT corpus WER <value> % lower-better, n=<utterances> [P-STT-1, norm=<normalizer_id>@<norm_sha256[:12]>, corpus=<corpus_id>@<manifest_sha256[:12]>, boot95=[<lo>,<hi>], MDE=<mde>, identity=<n_identical>/<n_utterances>, taxonomy=<ok>/<empty>/<reploop>/<numeral>/<marker>/<decode_err>, cache=<cache_state>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

Inside search this record additionally carries the full `P-AK-SEARCH-1` grammar and the words
**SEARCH RECORD, NOT A CLAIM**.

---

## P-STT-2 — STT speed: real-time factor, latency, and throughput

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
  single-stream RTF times a stream count (`gpu-cross-device.md:106-111`).

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
executing `scripts/utils/verify_ggml_linkage.sh <binary> <tree_root>` **in the research repo** and
retaining its complete output. On 2026-07-31 a HIP-built `whisper-cli` loaded the production
CPU-only ggml through an ambient `LD_LIBRARY_PATH`, found no GPU, and ran full-CPU **while printing
`use gpu = 1`** — the run completed, the output was well-formed, and only the throughput was quietly
wrong. Three ggml generations coexist on this host (llama 0.16.0, qwentts 0.17.0, whisper 0.18.0), so
this is a standing hazard and not a historical one.

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
are forbidden (`gpu-cross-device.md:136-137`). Anchor measured first in every window and compared
against its calibrated acceptance band; outside the band the window is **VOID**
(`bench-cpu.md:231-233`).

**Decision-grade requires ALL of:** this ratified protocol; the metric named with its direction and
its denominator; per-stratum RTF with the strata declared before measurement; the fitted `a` and `b`
with intervals; median **and** p95 latency; throughput measured at its declared concurrency and never
reconstructed; an acquired claim re-verified at window close; a passing host-health tier; an explicit
immutable anchor re-verified byte-for-byte; a passing anchor gate; the linkage verifier's complete
output **plus** the engine's own device line; the codified recipe constructor id and hash; reps per
the P-BENCH-1 rule; median + MAD; a published MDE; an e-process verdict against its calibrated
threshold — never an ad-hoc bound and never an LCB in its place (`kernel-research.md:274-283`); and
retained raw samples. Missing ANY → **observation**.

**Prospective.** Applies only to runs started after ratification. The 2026-07-31 STT speed figures —
CPU wall `4.18 + 0.010 × audio_s`, MI210 wall median 0.124 s / max 0.218 s, encode 3751 → 110 ms —
are observations and remain so.

**Grammar:**
`STT <rtf|xrt|latency_s|throughput_audio_s_per_wall_s> <value> <lower-better|higher-better>, stratum <label>, n=<reps> [P-STT-2, median+MAD=<med>±<mad>, MDE=<mde>, e=<e-value>/thr=<1/α>, fit a=<a>s b=<b>, concurrency=<c>, linkage=<PASS|COULD_NOT_CHECK>+device=<device_line>, recipe=<id>@<sha[:12]>, res=<claim_receipt>, host=<host_receipt>, category=<OPTIMUM|BASELINE|CANDIDATE>, YYYY-MM-DD, attest <ref>]`

---

## P-STT-3 — STT stability, memory, and op-coverage integrity

**Purpose.** To catch the failures that a correctness corpus and a stopwatch both miss: a leak, a
teardown race, and a test suite that got *smaller* while its pass rate stayed at 100 %.

**Scope.** Any `whisper_stt` release gate, and any search record whose candidate touches memory
management, backend dispatch, or op registration. Emits a **verdict, not a claim**.

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
`STT stability <PASS|FAIL|NO_DETECTABLE_DIFFERENCE>, cycles=<n> [P-STT-3, rss_slope=<v>MiB/cycle lower-better CI=[<lo>,<hi>], anchor_band=[<lo>,<hi>], vram_slope=<v>MiB/cycle, teardown=<n_clean>/<n>, ops=<attempted>/<skipped>/<passed> vs anchor <attempted>/<skipped>/<passed>, YYYY-MM-DD, attest <ref>]`

---

## P-STT-REL-1 — the STT kernel-release decision rule

**Purpose.** One rule that reads `P-STT-1`, `P-STT-2` and `P-STT-3` together and produces a release
verdict for a whisper.cpp candidate. **It is an input to an operator's freeze decision and is never a
freeze trigger.**

**Scope.** A sealed whisper.cpp release candidate evaluated at T3 (§10). Emits
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
  source-closure identity test (§3.2 stage 1) therefore operates on the superproject alone — **and
  the adapter MUST assert this rather than assume it**, because the sibling TTS tree is the opposite
  case and a shared assumption would be wrong for one of them.
- **The linkage proof of `P-STT-2` is part of release identity**, not merely of the speed cell. A
  candidate whose libraries resolve outside its own tree has no valid cells at all.

### 4.2 The backend-unchanged test, in its single-backend form

`whisper.cpp` serves exactly one backend, so §3.2's cell-dropping transfer — where an unchanged
backend's evidence transfers by identity — has **no counterpart here**: there is no second backend to
drop. Both stages still run, for the opposite purpose: to establish that the candidate binary
**differs from the incumbent at all**. A candidate whose source closure is empty and whose normalized
binary comparison reports identity is a **no-op candidate** and is refused before it consumes a
release matrix, rather than passing every gate trivially. A disagreement between stage 1 and stage 2
is a hard finding filed against the build-identity machinery, never a silent preference for the
cheaper answer.

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
   for every protected cell**, the §1.6 objective: non-inferior on every phase, improved on at least
   one. Baseline / off-recipe cells are diagnostic and never veto or justify a release (invariant 15).

**Bands are DERIVED per cell by the campaign calibration block** (`kernel-research.md:193-268`). No
band in this protocol is a literal.

**The decision-rule SHAPE — and only the shape — is adopted from `bench-cpu.md:83-88`:** a pass region,
an inconclusive region resolved by **one fresh reversed-order pair pooled to a pre-declared
threshold**, and a fail region. The CPU protocol's literals (`≥0.98 PASS`, `<0.95 FAIL`) are
**explicitly NOT imported**: they were calibrated on `llama-bench` CPU prefill dispersion, and applying
them to an STT RTF cell whose dispersion is a different quantity is the category error
`feedback_gate_scope_must_match_measured_subset` names. This is the same adopt-shape-not-thresholds
discipline `P-AK-SEARCH-1-A1` applied to its own source (`kernel-research.md:445-448`).

**Mechanism plausibility.** A banked whisper.cpp candidate requires an explanation backed by bytes,
FLOPs, counters, or a clean A/B (`P-AK-SEARCH-1-A1` clause 1). *"It got faster and I don't know why"*
is a reason to keep measuring, not to release.

### 4.4 Waivers

An operator waiver is a first-class input (§10.4). It is a hash-pinned, human-only
`epyc.autokernel.operator_waiver.v1` object carrying scope, reason, forfeited claims, protocol
binding, campaign binding, and an expiry/reopen predicate. **The evaluator verifies the waiver's hash
and predicate; it never judges its merits.** A waived cell suppresses the corresponding claim in the
release receipt, and the verdict becomes `PASS_WITH_WAIVER`.

### 4.5 Complexity ceiling

Per §10.6 the backend adapter declares a complexity/blast-radius ceiling, and above it the release
package is marked `REQUIRES_HUMAN_CODE_REVIEW` and says so on its first page. For `whisper_stt` the
ceiling is **derived from the backend's own accepted production history**: the maximum changed-lines
and files-touched across every commit on `production-speech-v1` beyond its upstream base. That history
is currently **one commit, one file, two changed lines**, so the ceiling is very low and essentially
every LLM-authored change to this tree will be marked for human review. That is the correct outcome
for a third-party tree this project does not own, and inflating the ceiling to make the loop
convenient would be a downgrade dressed as a calibration. Recomputed at every freeze.

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
`STT release verdict <PASS|FAIL|PASS_WITH_WAIVER> for whisper.cpp <candidate_commit[:12]> vs <anchor_commit[:12]>/<anchor_binary_sha256[:12]>/<anchor_linkage_sha256[:12]> [P-STT-REL-1, correctness=<PASS|FAIL> (margin=<m>, det=<determinism-class>), integrity=<PASS|FAIL>, speed=<PASS|FAIL> (cells <n_pass>/<n_total>), unchanged_test=<stage1>/<stage2>, controls=<4/5|5/5>, waivers=<none|waiver_sha256[:12]…>, review=<REQUIRES_HUMAN_CODE_REVIEW|none>, eval=<bundle_sha256[:12]>, bundle=<release_bundle_sha256[:12]>, YYYY-MM-DD, attest <ref>]`

**This verdict authorizes nothing.** It is evidence an operator reads before executing a freeze.
