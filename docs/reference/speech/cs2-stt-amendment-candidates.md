# CS-2 STT-scoring amendment candidates (Annex S, P-STT-1)

**Status**: CANDIDATE TEXT, NOT RATIFIED. Drafted 2026-10-22 by CS-2.STT1 ([`handoffs/active/conversation-stack.md`](../../../handoffs/active/conversation-stack.md)).
**Authority**: none. `MEASUREMENT.md` and `measurement/protocols/speech.md` are human-amendment-only and are **not edited** by this document. Every item below is a recommended wording for the operator to accept, change or reject when the CS-2 package is ratified. Nothing here changes any scorer, record or gate until then.
**Quoted text** is from `measurement/protocols/speech.md` (P-STT-1, RATIFIED 2026-08-03), line numbers as of this worktree.
**Intake records** (discussed, not relied on as assertions): intake-2346#record, intake-2352#record, intake-2353#record, intake-2354#record, intake-2366#record, intake-2372#record, intake-2374#record, intake-2381#record, intake-2382#record.
**In-house implementation**: `epyc-inference-research/scripts/speech/stt_bakeoff/` implements `stt_norm/v1` plus a `v2`-candidate column (being written concurrently; path only, not verified here). The v2 column is a candidate instrument, not a conforming Annex S number.

## Item 1. `stt_norm/v2` for it / de / fr

Source: intake-2346#record (ledger D1, D7, D8), intake-2352#record (R1, R9), intake-2353#record (A8). Status: **CANDIDATE, not ratified.**

**Current text** (`speech.md:255-261`): "A change of normalizer is a change of instrument: records produced under two normalizer versions MUST NOT be pooled, differenced, or compared." Order and steps at `:274-326`; numeral step at `:305-325` ("Direction: hypothesis → reference form, never both sides → digits"; "closed table"; "An uncovered numeral form is `COULD_NOT_CHECK`"); apostrophes at `:299` ("`'` is inside the retained class at step 3"); three properties at `:263-271` (Symmetry, Idempotence, Determinism); forbidden transforms at `:327-331` ("No stemming. No lemmatization. No stopword removal. No synonym or homophone mapping. No spell correction. No fuzzy or edit-distance-tolerant token matching. No truncation of long outputs.").

**Proposed wording** (a version bump to `stt_norm/v2`, a new instrument; v1 records are never pooled with it):

1. **Order kept.** The P-STT-1 §1.3 step order is unchanged; v2 adds only the per-language content below.
2. **Numerals.** Step 6 gains one closed, hypothesis-side numeral table per language (it, de, fr), enumerated at calibration by scanning the reference corpus and the anchor's own hypotheses. Hypothesis to reference form only; the uncovered-form rule (`COULD_NOT_CHECK`, `numeral_uncovered_count`, derived cap) applies per language.
3. **Elision (fr, it).** The apostrophe is kept (step 4 unchanged), so `l'ho`, `c'est`, `qu'il` are one token each on both sides. No elision splitting or joining. The rule is tested on recorded (CS-4 `human_recorded`) clips before the table is frozen, because the elision tokenisation decides the reference token count.
4. **German compounds.** A split or joined compound (`Haus Tür` vs `Haustür`) is **not forgiven**. It is scored as the substitution/deletion/insertion it is under §1.4, and additionally reported as its own counted error class (`compound_split_join_count`, per arm) in the §1.5 failure taxonomy, so it is visible without being excused.
5. **Property 4, REFERENCE-BLIND (new).** The normaliser is `f(text, lang) -> text`. It never receives the partner string. No compound-pair merging (`normalize_compound_pairs`, `merge_compounds` style) in the primary score. Hypothesis post-processing inside a harness may not read the reference.
6. **Property 5, PINNED DEPENDENCIES (new).** Every imported package is version-pinned, and the pins are inside the recorded normaliser id + hash. An unpinned numeral library (the HF scorer uses `num2words`) makes the instrument a function of host state, violating Property 3.
7. **Forbidden list extended** with: name / spelling / compound / acronym tables; filler-regex families (see Item 2); digits on both sides; apostrophe-to-space.

**Rationale.** The Hugging Face multilingual normaliser deletes bracketed text, maps spellings and names, joins acronyms, strips fillers by regex, converts both sides to digits, replaces apostrophes with spaces and forgives compounds pairwise; each of those is already or should be forbidden here. A reference-aware harness path was shown to exist in that repository, which is why Property 4 is a property and not a convention (intake-2352#record R1, R9). The Artificial Analysis normaliser is unpublished, revised several times in 2026 and carries dataset-fitted proper-noun equivalences, so it is not copied (intake-2353#record A8). A cleaned reference track is a different utterance set, not the standard track with fixes, so v2 reports reference tracks as separate columns and never pools them (intake-2346#record D8).

## Item 2. Filler policy (decision package DP-B)

Source: intake-2353#record (ledger A2), intake-2352#record (R1), intake-2346#record (D7). Status: **CANDIDATE; DP-B decision belongs to the operator, ratified with the CS-2 package.**

**Current text**: P-STT-1 §1.3 has no filler step (the step list at `:274-326` runs NFKC/casefold, enumerated marker removal, punctuation, apostrophes, hyphen, numerals, whitespace). The Earnings22-Cleaned-AA reference carries about 3.8% fillers (intake-2353#record A2).

| Option | What | Tradeoffs |
|---|---|---|
| (a) | Closed, counted filler list removed on both sides as a v2 step | Comparable with filler-stripping anchors; deletes real words when a filler is lexical; hides disfluency errors |
| (b) | Fillers scored as ordinary words; corpus records `fillers_in_ref`; a closed counted list only inside the labelled secondary scorer for external anchors | Faithful to what was said, simplest to audit; external-anchor numbers need the secondary column to be comparable |
| (c) | Regex filler deletion | Rejected in the dives: deletes real words; on the extended forbidden list |

**Recommended wording (option b; also the default if undecided)**: "stt_norm/v2 performs no filler removal. Fillers are ordinary tokens. For references we author (CS-4), the transcription guide fixes one rule (transcribe or omit once, freeze one reference text per clip) and each set carries a `fillers_in_ref` flag. A closed, enumerated, counted filler list may be applied on both sides only inside the separately labelled secondary scorer used for external anchors, never in a primary or gating score."

## Item 3. Record fields for every STT-arm WER record

Source: intake-2346#record (D1, D5), intake-2352#record (R2, R3). Status: **CANDIDATE, not ratified.**

**Current text**: "A WER carried without the normalizer id and version is not a conforming number under this protocol" (`speech.md:188-189`) and the normaliser hash recorded in every record (`:257`); corpus identity manifest at `:371-375`.

**Proposed wording**: every STT-arm WER record carries, at write time: `normaliser_id` + `normaliser_hash` (including Property 5 pins); `reference_set_id` and `reference_track` (standard / cleaned / CS-4); `scorer_sha`; `set_list` (every set contributing); `n` (utterances) and reference token count; `language_mode` (forced language or auto-LID, both reported for Whisper arms); `unk_count` and the unk ban policy; `segmentation_mode` (e.g. VAD cut at 30 s, with chunk-index concatenation scored against the unsplit reference; non-contiguous chunk indices VOID the utterance as a harness fault rather than counting deletions); `metric_direction = lower`. Manifests carry RAW reference and RAW hypothesis; a score whose manifest hash or normaliser hash differs from the manifest is stale and recomputed, so a normaliser bump rescoring needs no re-inference.

**Rationale.** Leaderboard WERs differ by language mode and segmentation; without these fields two numbers that look alike are different instruments (intake-2346#record D1/D5, intake-2352#record R2/R3).

## Item 4. Comparability note (Hugging Face multilingual leaderboard)

Source: intake-2352#record (ledger R4, R5, R7), intake-2346#record (D3, D4). Status: **CANDIDATE, not ratified.**

**Proposed wording** (one line to append to the normaliser section): "it, de and fr WER under `stt_norm/v2` is NOT comparable with Hugging Face multilingual leaderboard numbers (elision tokenisation, double compound forgiveness, numerals converted on both sides, language auto-detection for Whisper rows). The reference token count is printed beside every fr and it WER. A Hugging Face comparable figure comes only from a labelled secondary run `hf-scorer@7e8d1a1` (kaldialign pinned, numeral library pinned and recorded), reported as a separate column."

**Rationale and cautions**: the quoted FLEURS anchors come from a 2026-03-26 scorer snapshot, so only ordering is expected to reproduce, not equality (intake-2352#record R5). Leaderboard RTFx is architecture ranking only and is never imported as a serving number (intake-2346#record D4).

## Item 5. Public anchors versus the headline gate (confirmation stratum)

Source: intake-2372#record (F1, F3), intake-2354#record (H1, H2, H3), decision package DP-A (OP-PUBLICREPOS). Status: **CANDIDATE, not ratified.**

**Current text** (`speech.md:376-380`): "The corpus is partitioned into disjoint selection and confirmation strata by the `P-AK-SEARCH-1` rule ... Confirmation utterances MUST NOT appear in planner context." and corpus identity/durability at `:371-375` ("A corpus living only under an ephemeral root ... MUST NOT be used to calibrate a release gate").

**Proposed wording**:
1. Public anchor sets (LibriSpeech, FLEURS, VoxPopuli, Earnings22-Cleaned-AA) are labelled `public-anchor`. They give ordering and sanity only, are never a headline gate and are never pooled with private sets. Public-trained arms may have seen them (intake-2372#record F1, intake-2354#record H3).
2. The headline gate is the operator-recorded confirmation stratum, speakers absent from any public corpus. An i.i.d. split of a public set cannot be the confirmation stratum.
3. The stratum is **withheld by design**: audio and reference text live in the custody store chosen under OP-PUBLICREPOS (DP-A: recommended option (b), a separate private corpus repository; default (a), on-disk custody outside git with SHA256SUMS); public repos carry only the manifest `(utterance_id, pcm_sha256, reference_text_sha256)`. Only aggregates leave the custody path: a loop-visible record `{wer, ci, n, taxonomy counts, stratum}`; the per-utterance output is a sealed file readable only by the operator and the audit path. No process inside the loop (planner, AutoKernel, autopilot) receives per-utterance outputs. Every scoring of the stratum is logged. The stratum is refreshed with newly recorded clips when the scoring count passes a ratified budget (the budget number is the operator's to set).
4. Reports print each arm's rank on every public set and on the private stratum with the rank delta; a large gap in favour of a public set is the fitting signal (intake-2372#record F3).

## Item 6. Secondary measurands for lexicon biasing

Source: intake-2366#record (ledger T2). Status: **CANDIDATE, not ratified; secondary, never gating on its own.**

**Proposed wording**: a lexicon-biased arm additionally reports: **term recall** (higher-better) and **term precision** (higher-better), reported separately and never merged into a single F-score alone; **lexicon-term insertions per hour on lexicon-free audio** (lower-better); and **non-list-word WER** (lower-better) under the primary `stt_norm/v2`. The record carries `lexicon_sha` and the `boost` value (and the list size). Rationale: shared lists cost precision and insertions on audio that never contained the terms, which a recall-only measure cannot see (intake-2366#record T2).

## Item 7. Language-gate human check (it / de / fr)

Source: intake-2382#record (ledger R2, R3), intake-2381#record (V1, V3), decision package DP-C. Status: **CANDIDATE, not ratified.**

**Proposed wording**: raters are native speakers of the target language only, screened per language; three raters per clip where available; clips shuffled across arms so no rater hears a single-arm block. Intelligibility is the human check; naturalness is scored by human ear plus a second ASR, because UTMOS is English-trained and the paper reports no it/de/fr naturalness number to rely on (intake-2381#record V3). Agent QA does not substitute (circular).

**Rater count (DP-C)**:

| Option | What | Tradeoffs |
|---|---|---|
| (a) | Model draft plus two independent human corrections and adjudication for en/it confirmation clips; three native raters for the it gate check where available | Meets the intake-2382#record R2/R3 shape; needs one native speaker per language besides the operator |
| (b) | Model draft plus operator's single correction, independent second ASR flags disagreements; records labelled `single_rater` | Recording not blocked; weaker reference; every verdict carries the label |
| (c) | Three raters per clip in every language | Strongest; impractical for a single operator, especially de/fr |

Plan recommendation: (a) for en and it, (b) for optional de and fr. Default if undecided: (b) for all languages, labelled `single_rater`, so recording proceeds and the label travels with every verdict.

## Not adopted (recorded so they are not re-proposed)

The HF English/multilingual normaliser and the Artificial Analysis normaliser as primary instruments (Items 1, 2). OmniVoice as the CS-26 CPU fallback (intake-2381#record V6, no CPU number). Judge-model leaderboards (intake-2382#record R7).
