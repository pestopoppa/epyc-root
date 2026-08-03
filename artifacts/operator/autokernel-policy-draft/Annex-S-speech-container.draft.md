<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Authored by an agent under AK9; an agent cannot
     ratify and `measurement/protocols/` is hook-blocked.
     Target: NEW FILE measurement/protocols/speech, plus the core-file layout, registry and
     CHANGELOG deltas transcribed below. Restore the `.md` extension at transcription time
     (see README.md, "A note on filenames in this directory").
     Owning handoff: handoffs/active/autokernel-research-loop.md §13.3, §13.4, §14 AK9, AK-D24. -->

# Annex S — speech protocols (container draft)

**Creates:** a fifth annex file, `measurement/protocols/speech`, holding the STT and TTS protocol
families drafted in [`P-STT-1.draft.md`](P-STT-1.draft.md) and [`P-TTS-1.draft.md`](P-TTS-1.draft.md).

**Status:** DRAFT. Nothing here is in force. This document is the *container* decision — where the
two families are filed, what the core file must say once they exist, and which attestation carries
them. The normative protocol text lives in the two sibling drafts.

---

## 1. Why a new annex, and not B, Q, G or K

`measurement/protocols/` contains **nothing** for STT or TTS. That is not an oversight to be patched
by squeezing speech into an existing family; it is the reason AK-D24 split speech into its own phase.
The four existing annexes are declared by family (`MEASUREMENT.md:15-20`, `:45-46`):

| Annex | File | Family |
|---|---|---|
| B | `measurement/protocols/bench-cpu.md` | CPU bench |
| Q | `measurement/protocols/quality-eval.md` | quality / eval / significance |
| G | `measurement/protocols/gpu-cross-device.md` | GPU and cross-device |
| K | `measurement/protocols/kernel-research.md` | kernel research & release, cross-backend |

**Annex K does not admit them.** Its admission test is a conjunction of three conditions
(`kernel-research.md:11-17`), and condition 2 requires the protocol to be *"cross-backend — it
governs at least two of `llama_cpu`, `llama_gpu`, `whisper_stt`, `qwentts_tts`, `serving_runtime`"*.
An STT protocol governs `whisper_stt` and nothing else; a TTS protocol governs `qwentts_tts` and
nothing else. Neither is cross-backend, both fail condition 2, and filing them in K anyway would
make K's own admission test decorative — which is worse than a fifth annex, because the test is
what stops K becoming the drawer everything cross-cutting is swept into.

**Annex B does not admit them.** B is the *CPU* bench family and its protocols are built on
`llama-bench`, `taskset -c 0-95 -t 96 -fa 1`, and tokens/s. The production STT and TTS binaries run
on the MI210 under HIP; the STT metric is a word-error rate and a real-time factor, not tokens/s;
and P-BENCH-1's core recipe is not expressible for either binary.

**Annex G does not admit them.** G's subject is *cross-device* comparison and MI210 canonical
throughput in tokens/s. Speech cells are single-device, and their metrics are not G's metric.
Filing them in G would also drag P-GPU-1's production-named-kernel provenance rule
(`gpu-cross-device.md:16-21`) across a boundary it was never written for.

**Annex Q admits half of one of them, which is the trap.** The STT correctness half is a quality
instrument and would sit plausibly in Q. Its speed half would not. Splitting one instrument across Q
and B is exactly the alternative the operator **rejected** for Annex K on 2026-08-02
(README.md, "Annex placement — RESOLVED"): *"would fragment one instrument across three files with
three amendment histories, and would obscure the property that matters most about it."* The same
argument applies here with the same force, and it applies twice, since STT and TTS each have a
correctness half and a speed half.

**Therefore: Annex S, a fifth annex, filed by modality.** This is the Annex K precedent applied a
second time and is consistent with the core file's own layout sentence — protocol text lives in
annexes *"filed by family or instrument class"* (`MEASUREMENT.md:17-19`).

### 1.1 The alternative, stated so it can be chosen instead

**Alternative A (rejected here, available to the operator):** file `P-STT-CORRECT-1` and
`P-TTS-QUALITY-1` in Annex Q; file `P-STT-SPEED-1` and `P-TTS-SPEED-1` in a new Annex B section or
in Annex G depending on the device. Cost: four protocol ids across two or three annexes, two or
three amendment histories per modality, and a standing question at every future amendment about
which annex owns the release decision rule that spans both halves. Benefit: no new annex file, and
the core-file layout paragraph is untouched.

**Recommendation: Annex S.** The release decision rule for a speech kernel is a single rule that
reads correctness and speed together and is lexicographically ordered between them
(`kernel-research.md:355-360`). A rule that spans two halves cannot live in the annex of one half.

---

## 2. What Annex S is NOT

**It is not a second search authority.** Search inside experimental worktrees on `whisper_stt` and
`qwentts_tts` is already authorized by `P-AK-SEARCH-1`, whose scope is *"Tiers T0, T1 and T2 of the
AutoKernel loop, **on every declared backend adapter**"* (`kernel-research.md:50-51`). Annex S adds
no search authority, lifts no consumption prohibition, and creates no exception to any denial in
`kernel-research.md:87-133`. What it adds is the thing P-AK-SEARCH-1 explicitly does not supply for
these backends: **the owning protocol under which a speech number becomes a claim**, which
P-AK-SEARCH-1 requires to exist and names as *"its owning protocol in Annex B, Q or G"*
(`kernel-research.md:54-56`) — a list that today has no entry a speech number can be re-measured
under. Annex S closes that gap and extends that list to *"B, Q, G or S"*.

**It is not a release authority.** `MEASUREMENT.md:140-142` reserves era-registry rows, constitution
amendments, AutoPilot baseline applies, production freezes/cutovers and host reboots to humans. A
`PASS` verdict under a protocol in Annex S is an input to an operator's freeze decision and is never
a freeze trigger. AutoKernel produces a release package; a human executes it (§1.3, invariant 5).

**It is not retroactive.** See §5.

---

## 3. Core-file deltas (changed words only)

Three edits to `MEASUREMENT.md`, one appended cross-reference, one new file.

### 3a. Layout paragraph — `MEASUREMENT.md:15-20`

The clause currently reads *"four annexes in `measurement/protocols/`"* as amended by the Annex K
apply. It becomes:

> **Document layout (v2).** This core file holds the constitution: claim grammar, metric scoping,
> protocol index, noise table, governance, and retroactivity. Full normative protocol text lives in
> **five** annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment
> rules as this file — they are the constitution, filed by family or instrument class, not commentary
> on it. Daily-use guidance for sessions is the digest at `agents/shared/MEASUREMENT_POLICY.md`; when
> in doubt, this file and its annexes win.

Changed words: `four` → `five`. Nothing else in the paragraph moves.

### 3b. Registry header — `MEASUREMENT.md:45-47`

> Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
> `measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
> **K** = `measurement/protocols/kernel-research.md`, **S** = `measurement/protocols/speech`.

Changed words: the `, **S** = …` clause appended. (Restore `.md` at transcription.)

### 3c. Registry rows — `MEASUREMENT.md` §2 table

Appended after the `P-AK-SEARCH-1` row. Each row's metric and direction are stated because a bare
speech number is unusable — the project already carries **both** conventions for the same TTS
measurement (see §4 below), which is the defect these rows exist to end.

| Protocol | Scope | Metric (direction) | Status | Annex |
|---|---|---|---|---|
| P-STT-1 | STT transcription correctness: corpus, normalization, match rule, failure taxonomy | corpus WER (↓) + transcript-identity verdict | 📋 staged | S |
| P-STT-2 | STT speed: real-time factor, per-request latency, batch throughput | RTF (↓) · latency s (↓) · audio-s/wall-s (↑) | 📋 staged | S |
| P-STT-3 | STT stability, memory growth, audio-input identity, op-coverage integrity | verdict — not a claim | 📋 staged | S |
| P-STT-REL-1 | STT kernel-release decision rule (whisper.cpp tree) | verdict `PASS`/`FAIL`/`PASS_WITH_WAIVER` | 📋 staged | S |
| P-TTS-1 | TTS text/audio identity and deterministic/numerical checks | identity + numerical verdict — not a claim | 📋 staged | S |
| P-TTS-2 | TTS intelligibility floor and reference-waveform distance (human-independent) | round-trip WER (↓) floor + spectral distance (↓) | 📋 staged | S |
| P-TTS-3 | TTS speed: first-audio latency, real-time factor, synthesis throughput | TTFA ms (↓) · RTF (↓) · audio-s/wall-s (↑) | 📋 staged | S |
| P-TTS-REL-1 | TTS kernel-release decision rule (qwentts.cpp tree) | verdict `PASS`/`FAIL`/`PASS_WITH_WAIVER` | 📋 staged | S |

`P-TTS-4` is deliberately absent: TTS stability and op-coverage integrity are governed by
`P-STT-3`'s clauses, which are written backend-agnostically and cited by reference from the TTS
family rather than duplicated. Where a rule already lives, the amendment goes
(`kernel-research.md:22-23`).

### 3d. CHANGELOG line — `MEASUREMENT.md` §CHANGELOG

> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created,
>   holding the STT (`P-STT-1`, `P-STT-2`, `P-STT-3`, `P-STT-REL-1`) and TTS (`P-TTS-1`, `P-TTS-2`,
>   `P-TTS-3`, `P-TTS-REL-1`) protocol families. First measurement protocols of any kind for the
>   `whisper_stt` and `qwentts_tts` backends. Prospective; retro-certifies nothing. Layout paragraph
>   `four` → `five`; registry header gains **S**; eight registry rows appended.

### 3e. Appended cross-reference — `measurement/protocols/kernel-research.md`

`P-AK-SEARCH-1`'s scope clause names the annexes a search number must be re-measured under
(`kernel-research.md:54-56`). Annex S extends that set, and per the narrowing carve-out
(`kernel-research.md:19-23`) the owning annex receives an appended cross-reference **in the same
apply** rather than a silent change of meaning:

> *Extended `<APPLY_DATE>`: the set of owning annexes named in this clause is **B, Q, G or S**.
> Annex S (`measurement/protocols/speech.md`) supplies the owning protocols for `whisper_stt` and
> `qwentts_tts`, which had none when this protocol was ratified. Nothing else in this clause changes,
> and no denial in "What this protocol does NOT authorize" is narrowed.*

This is an **append**, not an edit of the existing sentence.

---

## 4. The direction defect this annex closes on its first day

`MEASUREMENT.md:39-41` requires metric direction to be stated wherever ambiguous, and CLAUDE.md's
debugging rule opens with *"Always confirm metric direction."* The project currently carries the
**same TTS measurement in two reciprocal conventions**, in two durable artifacts:

- `artifacts/operator/ratify_speech_kernel_freeze_20260731.json` records
  `qwentts_cpp.measurements_anchored.rtf: 0.169` — wall-over-audio, **lower-better**;
- `handoffs/active/multimodal-pipeline.md` and the master index record `xRT 0.86× → 5.47×` —
  audio-over-wall, **higher-better**.

They are reciprocals of one another and neither artifact says which it is. `1/0.169 = 5.92` and
`1/5.47 = 0.183`, so the two numbers are also not the same measurement; without a stated direction
and a stated denominator there is no way to tell a unit convention from a different run. `P-TTS-3`
fixes one definition (`RTF = wall_s / audio_s`, lower-better), requires the reciprocal to be labelled
`xRT` when quoted, and makes a bare "real-time factor" without a direction non-conforming.

**A second, sharper instance, surfaced while drafting this annex and reported rather than repaired.**
The same ratified freeze receipt records, under `whisper_cpp`:

```
"measurements_anchored": { "model": "whisper large-v3-turbo f16", "wer_pct": 2.35, ... }
```

The raw artifact that number comes from is `/mnt/raid0/llm/tmp/stt_wer_results.json`, which contains
six arms. In that file, `2.35` is the **`faster-whisper large-v3-turbo int8 CPU 48t`** arm — the
CTranslate2 CPU incumbent, a *different engine on a different runtime*. The `whisper.cpp
large-v3-turbo f16 MI210 GPU` arm in the same file records **63 errors over 1870 reference words =
3.37 %**. The receipt therefore anchors the whisper.cpp kernel to a WER measured on a binary that is
not whisper.cpp.

This is not a rounding disagreement and it is not repairable by an agent: the receipt is a ratified
operator artifact, and `MEASUREMENT.md:174-175` forbids destroying primary records. It is filed here
as an operator item (§6, item S4) because it is precisely the failure `P-STT-1` is built to prevent —
*a correctness number attached to the wrong instrument* — and because the anchor a future
`whisper_stt` campaign compares against is currently wrong by ~1 pp in the flattering direction.
Note also that the two arms' 95 % bootstrap intervals overlap heavily (§7), so *"identical to the CPU
incumbent"* was not supportable from that corpus in either direction; the honest statement was
**no detectable difference at n=100**, which is a result (`gpu-cross-device.md:149-150`).

---

## 5. Prospective

**Creating Annex S neither retro-certifies nor upgrades any artifact.** No speech measurement taken
before the apply timestamp becomes a claim, or a conforming record of any Annex S protocol, by virtue
of this annex existing. In particular the 2026-07-31 speech measurements — the WER figures, the
round-trip WER figures, the TTFA and RTF figures, and every number in
`ratify_speech_kernel_freeze_20260731.json` — remain **observations**. They are cited throughout the
two sibling drafts as *calibration precedent*: they establish that a quantity is measurable, what
order of magnitude it takes, and how much dispersion it carries. They are never cited as thresholds,
and no threshold in Annex S is set equal to one of them.

Annex S MUST NOT be used to relocate an existing protocol. Protocols already filed in B, Q, G or K
stay there.

---

## 6. Operator items, listed separately so lines may be struck

Per `MEASUREMENT_POLICY.md:77-78`, batched into one attestation with each item strikeable.

| # | Item | Strike consequence |
|---|---|---|
| **S1** | Create Annex S at `measurement/protocols/speech.md`; apply core-file deltas §3a–3d | No annex; STT/TTS have no owning protocol; every speech number stays an observation forever and no speech kernel can be frozen on evidence. `P-AK-SEARCH-1` search on the two speech backends is unaffected — it is already authorized — so striking this blocks *release*, not *research* |
| **S2** | `P-STT-1`, `P-STT-2`, `P-STT-3`, `P-STT-REL-1` (the STT family) | whisper.cpp cannot be frozen on measured evidence; a whisper.cpp campaign may still run T0–T2 under `P-AK-SEARCH-1` and bank candidates, and stops at the release gate |
| **S3** | `P-TTS-1`, `P-TTS-2`, `P-TTS-3`, `P-TTS-REL-1` (the TTS family) | as S2, for qwentts.cpp. Note S2 and S3 are genuinely independent: §1.5 makes whisper.cpp and qwentts.cpp **independently freezable**, unlike CPU and GPU which share `llama.cpp` |
| **S4** | Correct or supersede the `wer_pct: 2.35` anchor in `ratify_speech_kernel_freeze_20260731.json` (§4) | The whisper.cpp release anchor stays a CPU-incumbent number. Every future `whisper_stt` non-inferiority comparison inherits a denominator measured on a different engine. **This item is a receipt amendment and is human-only regardless of whether S1–S3 are applied.** The recommended form is a *superseding* receipt naming the prior path and SHA-256, never an in-place edit (`MEASUREMENT.md:116-118`, `bench-cpu.md:163-168` precedent) |
| **S5** | §3e appended cross-reference in `kernel-research.md` | `P-AK-SEARCH-1`'s owning-annex list stays "B, Q or G" while Annex S exists, so a speech search record has a re-measurement route the protocol text does not name. Strike only together with S1 |

**Attestation routing.** S1, S2, S3 and S5 belong to a *release-authorization* attestation
(attestation 2 in the README's split, presented before the first speech freeze): their referents are
release instruments and nothing they authorize is needed for T0–T2 search. **S4 is independent of
both attestations and should be actioned on its own schedule** — it is a defect in a landed receipt,
not a new authority.

---

## 7. Derivation appendix — the numbers used by §4 and by the two sibling drafts

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

Three things follow, and all three are used as *derivations* in the sibling drafts rather than as
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
   half-width is `no detectable difference`, which `gpu-cross-device.md:149-150` makes a result and a
   decision rather than a failed experiment. Reporting them as a ranking would be a scoring artifact
   of exactly the class `feedback_per_suite_gate_resolution_artifact` names.
