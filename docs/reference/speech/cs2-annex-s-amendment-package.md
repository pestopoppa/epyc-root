# CS-2 — Annex S voice-turn amendment package

Status: PROPOSED, NOT RATIFIED. Prepared 2026-11-19. This package completes the
preparation requested by CS-2; issuance and application remain human-only under
MEASUREMENT.md §5. No protocol, scorer, freeze receipt or production placement is
changed by this document. Existing measurements retain their original status.

## Decision requested

Approve the prospective scope and protocol text below, select the quantitative
acceptance policy in the decision table, and issue the narrowly superseding receipt
in §5. Recommended: adopt the definitions and correction together, retain existing
STT/TTS protocols, and calibrate missing quality thresholds before any voice-turn
gate. The operator records accepted sections, rejected sections, final thresholds,
apply timestamp and package commit in a reviewed ratification. Approval of this
package does not deploy a speech stack or authorize a kernel change.

## 1. Proposed scope amendment (append to Annex S)

> Effective only from the ratified apply timestamp, Annex S additionally admits
> the `voice_turn` instrument: a complete declared input-audio → routing/model/tool
> → output-audio stack, including its co-tenant environment. P-VOICE protocols own
> both its correctness and speed halves. A stack may contain multiple backends;
> comparison is between fully identified stack configurations on the same pinned
> instrument and corpus, never a pooling of component-protocol results. Existing
> P-STT/P-TTS protocols and their within-backend comparison limits are unchanged.
> An interlocutor reference-harness observation is not evidence of serving-port
> performance. No P-VOICE verdict is a release, cutover or freeze authorization.
>
> For the new family, Annex S admission conditions 1–2 additionally admit
> `voice_turn` as defined above. Conditions 3–4 remain in force: a P-VOICE protocol
> must establish a new voice-instrument rule, not restate or relocate a rule already
> owned by another annex. Existing cross-backend kernel protocols remain in Annex K.

The operator appends a corresponding scope note to Annex K's admission section:
“Multi-backend composition alone does not relocate a P-VOICE voice-instrument
protocol from Annex S; existing P-AK protocols remain owned here.” This resolves
scope overlap explicitly instead of silently moving a kernel protocol.

## 2. Proposed common P-VOICE contract

The following text applies to every family member in §3:

> Each run predeclares its question, arms, baseline, expected effect, pilot-based
> uncertainty and sample size, independent sampling unit, fixed endpoint/checkpoints,
> timeouts and stop rules in a committed plan. Reuse valid evidence first. Correctness
> precedes speed. Formal decision gates remain futility-only at interim looks until
> the applicable sequential-testing decisions are ratified; no repeated-peek success
> stopping. Stop on source/input drift, failed residency/linkage, or unrecoverable
> harness failure; retain all exposed units and explain the terminal disposition.
>
> Seal PCM hashes plus sample rate, channel/sample format and sample count, raw
> references, stack/runner/model/weight digests, decode/prompt parameters, normalizer,
> scorer and dependency pins before exposure. Selection and confirmation are disjoint
> by speaker and dialogue. Choose settings on selection; confirmation is withheld
> from planning and used only under a predeclared scoring budget. Public-anchor and
> synthetic strata rank/reject only; advancement requires human-recorded confirmation.
>
> Every manifest item stays in the denominator. Crashes, timeouts, empty/corrupt
> outputs and never-fire events count as failures, not missing successful examples.
> A genuine input or harness invalidation is separately journaled and stops its
> window; never silently redraw an exposed item. Publish successes, failures,
> eligibility counts and uncertainty by language, route and recording stratum.
>
> Timings use one monotonic clock or a measured cross-clock alignment and recorded
> uncertainty. Save per-item timestamps, audio outputs and raw events at write time.
> State repetition count AND independent unit; repeats of one clip do not add speakers.
> Predeclare quantile estimator and paired/bootstrap cluster unit (speaker/dialogue
> or process-launch as appropriate), seed and confidence level. No-response latency
> is right-censored at its timeout; report response rate, counts and censored bounds
> beside completed-item quantiles. An unbounded required quantile cannot PASS a finite
> cap. Never emit an infinity as a JSON number or substitute zero latency for failure.
>
> The write-side record contains run/measurement IDs, metric, unit, direction,
> protocol version, record class, subject, reps/reps_basis, corpus/manifest digest,
> instrument/config identities, placement/co-tenant proof and result attestation.
> Use the existing conversation_stack_measurement producer and shared ClaimTuple
> grader. Until ratification, protocol_id remains null and rows are observations.
> Ratification does not automatically make existing adapter allowlists admit the new
> IDs: update the producer/reader with tested versioned mappings before first use.
> Do not invent a new grading ladder. Register new source kinds only if these rows
> cannot be projected through the existing conversation-stack source.

Proposed measured-value grammar (a claim only after owning-protocol admission and
all durability/attestation conditions are met; otherwise explicitly an observation):

`[P-VOICE-<ID>/v1, stack=<digest>, corpus=<digest>, eval=<digest>, host=<proof>,
placement=<digest>, cotenant=<digest>, metric=<name>, value=<value-or-censored>,
unit=<unit>, direction=<higher|lower>, n=<eligible>, failures=<count>,
reps=<count>, reps_basis=<unit>, split=<split>, YYYY-MM-DD, attest <ref>]`

Proposed decision grammar, explicitly a verdict and not a claim:

`[P-VOICE-REL-1/v1, verdict=<PASS|FAIL|COULD_NOT_CHECK>, plan=<digest>,
res=<receipts>, host=<proof>, recipe=<digest>, eval=<digest>, bundle=<digest>]`

## 3. Proposed protocols and operational definitions

| ID | Measurand and denominator | Direction and required companions |
|---|---|---|
| P-VOICE-1 | End of gold user speech → first audible output sample at playback, median/p95 ms, separately LOCAL and ORCH; all eligible turns | Lower; report model-first-PCM and playback time separately. ORCH reports bridge-first audio AND first content-bearing answer audio, bridge rate, response rate and false cut-ins. A bridge cannot satisfy the content-answer metric. |
| P-VOICE-2 | Sustained synthesis RTF = wall seconds from accepted response text/model-generation start to final generated PCM / decoded output-audio seconds; playback excluded; p95 over utterances | Lower; record pipeline boundaries and wall/audio totals, include streaming stalls, separately report full-turn delay. Zero-duration output is a failure, never RTF zero. Reciprocal, if shown, is named xRT (higher). |
| P-VOICE-3 | Genuine user interruption onset → final audible assistant sample, p50/p95 ms; all labelled interruption events | Lower; report detector/confirmed-interruption time and each cancel-hook completion separately. Genuine-onset includes detection delay. Report false yields on backchannel/off-talk/background speech (lower) and respond/resume rates (higher). A completed cancel hook alone does not prove audible silence. |
| P-VOICE-4 | Per-class routing precision TP/(TP+FP), recall TP/(TP+FN), confusion matrix and forced-policy/tool-slot compliance; all labelled LOCAL/ORCH turns | Higher; absent support is COULD_NOT_CHECK, never precision 1. Failures count as missed required routes and compliance failures. Tool name, required arguments and exact values are scored separately. |
| P-VOICE-5 | Paralinguistic correct/eligible per label and macro mean over frozen labels; real en/it neutral, quiet, whisper, hesitation, sarcasm, laughter, frustration, noise | Higher; also print class support/confusion and speaker-cluster uncertainty. Missing required human strata gives COULD_NOT_CHECK. Synthetic evidence cannot advance an arm. |
| P-VOICE-6 | Semantic preservation passed/eligible answers and exact-value matches/required value occurrences after revoicing; numbers, names, commands, URLs | Higher; print all-preserved-answer rate and each value class. An omitted value fails retention; hallucinated added values are separately counted (lower). Pin rubric, source answer and judge artifacts; do not replace intelligibility with semantic similarity. |
| P-VOICE-7 | Pooled frozen-oracle round-trip WER per language plus native-human intelligible/eligible rate | WER lower, intelligibility higher; print reference words, utterance n, normalizer and oracle binary/model/decode digests, human rubric/rater count/agreement. en/it required, de/fr optional and separately labelled. Empty audio is full deletion and human failure. No inference of naturalness from WER. |
| P-VOICE-8 | Co-tenant slowdown = 100 × (1 − Q_co/Q_solo), Q = aggregate generated LLM tokens / measured wall seconds at fixed load; paired A/B/A launches | Lower; Q_solo must be positive. Pin model, np, prompts/output lengths and CPU/GPU/CU placement. Report per-slot p50/p95 tok/s (higher) and speech P-VOICE-1/2 concurrently. No mixing synthetic CU tests with real-tenant results; no CPU-placement arm resurrects declined CS-11. |

P-VOICE-6 judged results carry `llm_judged`, judge model DIGEST, prompt hash,
rubric and raw output hash. Any `judgment_recorded` frame additionally names
`assertion.claim_id`, a non-empty read_set of named SHA-256-pinned artifacts,
replay prompt/seed/model_version/temperature and real `tool_output_hash` (SC58).
A judgment pinned to changed bytes becomes dirty until re-judged; a judge's model
name alone is insufficient. Human assessments retain rater IDs, native-language
screening, blind randomized arm order and disagreement/adjudication, separately
from model judgments. Preserve the existing no-cloud-judge turn-taking restriction.

P-VOICE-REL-1 evaluates G1 language → G2 paralinguistics → G3 routing/fidelity →
G4 serving in that order, on ratified thresholds and one frozen configuration.
Failure stops that candidate. Missing evidence or unset required thresholds yields
COULD_NOT_CHECK, never PASS. The result is an operator recommendation only.

## 4. Device and placement amendment (replace stale historical premise prospectively)

> The GPU-only rationale in Annex S's “Annex B does not admit them” paragraph
> describes the July calibration environment, not a permanent serving placement.
> Production speech moved to CPU under OP-56. Current placement is proved for each
> run; CPU and HIP records are distinct instrument configurations and are never
> relabelled from executable paths or old freeze-receipt metadata. Card-2 placement
> with the frontdoor/35B-A3B is a candidate requiring its own operator cutover.
>
> Bind every record to physical PCI BDF/unique GPU ID, visible-device-to-physical
> mapping, CPU affinity/NUMA policy, runner/library digests and environment, including
> HIP_VISIBLE_DEVICES, ROCR_VISIBLE_DEVICES and LD_LIBRARY_PATH. Run the research
> repo's verify_ggml_linkage.sh for each ggml generation; a PyTorch reference instead
> pins torch/HIP and loaded runtime paths. Executable ldd alone cannot prove HIP
> residency because ggml HIP is dynamically loaded.
>
> During each measured GPU interval sample nonzero VRAM and attributable KFD PIDs
> together with linkage and visible-device mapping. Require overlapping samples,
> including two persistent samples before acting on an anomaly; predeclare cadence
> and required coverage. Save sample timestamps and owned process identities.
> Missing interval coverage means residency unproved, not CPU execution proved.
> For CPU rows record CPU flags/backend residency and enforced device fence; hidden
> devices alone do not prove no KFD context. Prove no owned KFD PID during the run.
> Co-tenant state is sampled during the same intervals: model/config, physical
> device, np, generating yes/no, placement and CU mask. “Idle” cannot be inferred
> from a pre-run snapshot. Each launcher isolates its own ggml library generation.

## 5. Superseding receipt ready for human issuance

The original receipt must remain byte-for-byte intact. Issue a new receipt with
an operator-chosen timestamp/signature and this payload (add the ratified package
commit on issuance). `status` must remain DRAFT until that human action:

```json
{
  "status": "DRAFT \u2014 human issuance required",
  "ratification": "speech-kernel-freeze-v1-wer-attribution-supersession",
  "supersedes": {
    "path": "artifacts/operator/ratify_speech_kernel_freeze_20260731.json",
    "sha256": "a773e3a1dc8654ac51d4d91d212aad4f18050b34c087e40a9d108c31bfba17f8",
    "scope": "kernels.whisper_cpp.measurements_anchored.wer_pct only"
  },
  "old_value": 2.35,
  "corrected_observation": {
    "wer_pct": 3.37,
    "errors": 63,
    "reference_words": 1870,
    "utterances": 100,
    "engine": "whisper.cpp",
    "model": "large-v3-turbo f16",
    "device": "MI210 GPU",
    "decode": "greedy"
  },
  "misattributed_observation": {
    "wer_pct": 2.35,
    "errors": 44,
    "reference_words": 1870,
    "engine": "faster-whisper",
    "model": "large-v3-turbo int8",
    "device": "CPU 48t"
  },
  "evidence": {
    "path": "measurement/protocols/speech.md",
    "git_blob": "a070f76cfea59cc995b6e0980183cea31aa7d0d5",
    "section": "Metric-direction defect; Appendix S-A"
  },
  "record_class": "historical observation, not a retro-certified claim",
  "raw_artifact_verification": "unavailable: original ephemeral artifact absent",
  "other_receipt_fields": "preserved as historical records; no current placement or new freeze implied",
  "operator_apply_timestamp": null,
  "operator_signature": null
}
```

The raw `/mnt/raid0/llm/tmp/stt_wer_results.json` no longer exists at preparation
time. The correction cites the committed Appendix S-A finding and the incorrect
receipt, not a new raw-data verification or a reconstructed measurement warrant.
The 63/1870 arithmetic rounds to 3.37%; the separate 44/1870 CPU arm rounds to
2.35%. Historical intervals overlap; no superiority/equivalence conclusion follows.
The correction changes attribution only and grants no deployment authority.

## 6. Exact core-index correction and apply sequence

Append a superseding index note to MEASUREMENT.md (do not silently replace history):

> The P-STT-1 index description is superseded by its owning protocol's record-class
> rule: conforming production-named-kernel records are claims; experimental search
> records are not claims. P-STT-REL-1 emits a release verdict, not a claim; the index
> must not imply that a release protocol retroactively creates a correctness claim.
> The P-STT-2 metric label “first-token latency” is superseded by the owning
> protocol's full-utterance latency/RTF/throughput definitions; retain those units
> and bounds rather than inventing a streaming token endpoint for offline Whisper.

Add one index row per P-VOICE-1..8 and P-VOICE-REL-1, with the above directions and
record classes, only once ratified. Append the scope/definitions to Annex S, the
scope clarification to Annex K, and one dated superseding CHANGELOG entry in the
core. Operator updates the boundary-owned agent digest if needed. Version scorer/
producer admission separately; validate its claim/observation distinction before
use. Keep every prior receipt and artifact. No pre-apply voice observation is
retro-certified.

## 7. Operator acceptance decisions (prospective, no calibrated thresholds asserted)

| Decision | Recommended option | Alternative and tradeoff |
|---|---|---|
| Scope and receipt | Adopt §§1–6 prospectively and issue the attribution-only correction | Defer voice-protocol admission while still issuing the correction; exploratory observations remain possible, formal voice claims wait |
| Existing handoff targets | Adopt p95 LOCAL ≤1.0 s, ORCH bridge-first ≤1.5 s, synthesis RTF ≤0.7, genuine-onset audible cancel p95 ≤200 ms, exact-value retention 100%, aggregate LLM slowdown ≤15% as initial engineering targets | Calibrate caps before adoption; avoids speculative hard gates but delays a numerical acceptance policy. Set a separate ORCH content-answer cap; bridge-only performance cannot PASS that metric |
| Missing quality thresholds | Require a committed calibration package to set routing precision AND recall floors, tool-slot compliance, per-label paralinguistic floors, semantic-retention and language WER/human-intelligibility bounds before confirmation; no PASS until ratified | Choose explicit values now with a declared minimum meaningful effect and sample-size rationale; faster policy, weaker empirical justification |
| Human ratings and custody | Use the linked STT candidate DP-A/B/C choices: private confirmation custody; fillers ordinary words; independent native corrections/raters for en/it where available | Single-rater labelled observations permit collection sooner; they do not silently satisfy an unratified multi-rater gate |
| STT-scoring v2 candidates | Review the seven linked items independently; keep v1 primary and v2 labelled candidate pending explicit versioned ratification | Adopt selected v2 items with a fresh instrument ID; requires tested bundle pins and separate historical columns |

No default in this table constitutes operator assent. Calibration may be made
ready without waiting for ratification; decision-gating confirmation may not.

## 8. Evidence and review boundaries

All Git object IDs below refer to this repository. These pin the records used to
prepare the proposal; no source tree, log or executable is copied into this package.

- `MEASUREMENT.md` — blob `6c537cb5d9018a453a6832444272cf83323ccfad`.
- `measurement/protocols/speech.md` — blob `a070f76cfea59cc995b6e0980183cea31aa7d0d5`.
- `artifacts/operator/ratify_speech_kernel_freeze_20260731.json` — blob `795941cd265aaffcaf0ee2dd04857db0d3394662`.
- `docs/reference/speech/cs2-stt-amendment-candidates.md` — blob `988b5a732fa174bb7b1b660f746b06afdb6eba76`.
- `docs/reference/speech/turn-taking-measurands.md` — blob `88ec1fe3d9a0f1833a164a0ce52ba17a4dc00473`.
- `scripts/vidya/adapters/conversation_stack_measurement.py` — blob `a167742e288ec2e93738286eaa2a9f86fa48105a`.
- `scripts/vidya/adapters/README.md` — blob `ec6031b0f1a6cc046c0eb8ee0607e86f3e956cf9`.

The companion [STT-scoring candidates](cs2-stt-amendment-candidates.md) remain
candidates. [Turn-taking measurands](turn-taking-measurands.md) fixes scenario
orientation and censoring cautions. This package introduces no empirical finding
or new belief source, changes no shared grader and runs no inference.
