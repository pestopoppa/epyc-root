# Turn-taking measurands (CS-45 measurand note)

**Status**: frozen 2026-10-20 by CS-45 ([`handoffs/active/conversation-stack.md`](../../../handoffs/active/conversation-stack.md)).
**Consumers**: CS-2 (reads this when the Annex S package is prepared; no package text is written here), CS-22, CS-23, CS-47, CS-48, CS-49.
**Authority**: this note names and orients the quantities. It is not an amendment of `measurement/protocols/speech.md` (Annex S) and ratifies nothing; the Annex S trust boundary (human-only amendment) is untouched.
**Evidence this note binds to** (in `epyc-inference-research`, `data/turn-taking-cs45-v1/`): `label_contract.json`, `corpus.json` + `SHA256SUMS`, `pins.json`, `measurement_era_changes.json`, `external_crosscheck.json`, `manifest/*`.

## 0. Rules that apply to every quantity below

1. **Direction is part of the name.** Every row says higher-better, lower-better, or *scenario-dependent*. A number quoted without its direction and its denominator is not a result.
2. **Denominator = every manifest item.** A crash, timeout or never-fire counts as a miss, never as a missing row.
3. **Strata.** `synthesized` evidence can reject or rank an arm; **only `human_recorded` evidence can ADVANCE one** (operator rule). The human stratum is empty today (CS-4 sets 2 and 5 are not recorded), so no arm can advance yet.
4. **Era.** Scorers run through the pinned instrument set (`pins.json`): one Silero VAD (sha256 `4cbf549b…17d2`), Full-Duplex-Bench `3e799c45`, TurnBench `38a6f87`, one CPU ASR for word timestamps. Each substitution of an upstream script is a measurement-era boundary (`measurement_era_changes.json`). Numbers produced by patched scorers are **not comparable** to the organisers' published numbers or to any pre-CS-45 number.
5. **Published rows are reference rows only.** TurnBench's published baselines, the VAP paper's weighted F1 and ECHO's published PASR/PKC are quoted as tagged reference rows, never mixed with measured rows or with each other.
6. **No cloud judge.** The Full-Duplex-Bench GPT-4o behaviour classifier and gpt-4-turbo interruption rating are never invoked; anything they would produce is replaced by deterministic, event-log-derived labels and is labelled **non-comparable**.
7. Correctness legs (scoring, parity, label arithmetic) run under `region-lock` **build** claims; timing legs (per-decision CPU latency) need an exclusive window. This note defines quantities; it measures nothing.

## 1. Corpus-level contract (what the labels mean)

Four turn states, mutually exclusive per decision point (full definitions in `label_contract.json`): `complete` (floor released, response due), `incomplete` (mid-turn pause, hold), `backchannel` (acknowledgement while the other party holds the floor, keep the floor), `wait` (explicit hold request, floor reserved). Only `complete` has an end-of-turn positive; the other three are negatives whose violation is a *false cut* (`incomplete`, `wait`) or a *false yield / interruption false positive* (`backchannel`).

Pairs (matched minimal contrasts, one spliced recording, 2.0 s of exactly matched trailing silence): `CUT_IC` (complete vs incomplete), `CUT_WAIT` (complete vs wait), `CTX_BC` (complete vs backchannel; same waveform, different preceding assistant context).

## 2. Quantities

### 2.1 Full-Duplex-Bench v1 / v1.5 (pinned `3e799c45`, scorers patched per `measurement_era_changes.json`)

| Quantity | Definition (as the pinned code computes it) | Direction |
|---|---|---|
| **TOR** (turn-over rate) | `eval_*` scripts: a model turn is *taken* when its time-aligned output spans ≥ 1.0 s or contains > 3 words; TOR = taken / items. | **Scenario-dependent**: *lower is correct* for `pause_handling` and `backchannel` (the user is not done / is only acknowledging); *higher is correct* for `smooth_turn_taking` and `user_interruption`. |
| **Smooth-turn latency** | `smooth_turn_taking`: first output word start − user turn end (`turn_taking.json`), taken only over items where the turn was taken. | lower-better, **conditional on TOR**: always read with TOR; a model that never answers has no latency. |
| **t_stop** | `get_timing.py`: the overlap interval of the user's speech and the model's speech after the user barges in (model stop − user start in the intended reading). | **Scenario-dependent**: *lower-better* after a genuine interruption; **a HIGH t_stop is correct** for backchannel, off-talk (talking to others) and background speech, where the model should keep talking. A scorer that reports t_stop without the scenario label inverts its meaning. |
| **t_resp** | `get_timing.py`: model first speech start after the user's speech end − that user end. | lower-better; defined only when a response exists, so report the response rate beside it. |
| **Merge gaps** | `USER_MERGE_GAP = 0.6 s`, `MODEL_MERGE_GAP = 0.5 s` in the code; the inline comments say 300 ms and 50 ms. The two disagree. | CS-48 reports t_stop / t_resp under **both** readings (code 0.6 / 0.5 s and comment 0.3 / 0.05 s) and says which reading any single number uses. |
| **Behaviour labels / interruption rating** | GPT-4o classifier, gpt-4-turbo rating. | **Not used.** Replaced by event-log-derived Respond / Resume labels (CS-48), tagged NON-comparable. |
| **Backchannel JSD** (FDB v1 `eval_backchannel.py`) | Jensen-Shannon divergence between the model's backchannel timing distribution and a reference distribution. | **Excluded** from the programme: it rewards imitating a reference rate rather than correct floor-keeping. The script's TOR is retained. |

### 2.2 TurnBench (pinned `38a6f87`; `turnbench.score`, local CPU, no judge)

Predictions are `predictions.json` event times per speaker; a timestamp is the time by which every sample the decision used has been heard (lookahead is folded into the time). Gold event at `t` is searched in `[t − 0.25 s, min(t + 3.0 s, next same-task gold)]`, one-to-one.

| Quantity | Definition | Direction |
|---|---|---|
| **EOT recall** | matched / gold end-of-turn events | higher-better |
| **EOT FPR** (false cut) | predicted EOTs inside a mid-turn-pause span or backchannel, at most one per span; per-pause rate | lower-better; operating points are chosen at FPR ≤ 0.10 on the *selection* split (TurnBench's own leaderboard qualifies at ≤ 0.15 on test) |
| **Signed latency** p10 / p50 / p90 | `t_pred − t_gold` over matched EOTs; **negative = the system fired before the gold time** | closer to a small positive value is better; a negative p10 means cut-ins and is reported, never clipped. Model-only latency is separated from any wrapper gate (e.g. the 1 s silence gate in front of Smart Turn). |
| **INT recall / INT FPR** | interruption events on the interrupter's channel; INT FPR counts an interruption fired on a backchannel | recall higher-better, FPR lower-better |
| Excluded regions | spans where annotators disagree are neither rewarded nor penalised | n/a |

The local TurnBench dev snapshot is recorded **by hash and id only** (`external_crosscheck.json`); the scorer hard-codes a different dev revision than the snapshot, so scoring is run with `--dataset <local>` and both revisions are tagged on every score.

### 2.3 ECHO-style pair metrics (PASR / PKC) and the constant-policy baselines

Defined on action-flip pairs (ECHO paper definitions; our pairs are the matched `CUT_*` / `CTX_BC` set):

| Quantity | Definition | Direction |
|---|---|---|
| **PASR** (pairwise action success rate) | fraction of pairs where the system takes the right action on **both** members (member a: take the turn / yield; member b: hold / keep the floor) | higher-better |
| **PKC** (pairwise keep consistency) | fraction of pairs of two non-floor-claiming items where the system keeps the floor on **both** | higher-better, but **meaningless alone** |
| **Constant-policy baselines** | `always-end` (always take the floor / yield) and `never-end` (always keep) | rows in every table |

**Read together, always:** a constant-keep policy maximises PKC and scores 0 PASR; constant-yield scores 0 on both. PKC is only evidence when PASR is above both constant rows. Pairs here are **acoustically matched** (one spliced recording), which removes the independent-synthesis confound ECHO's own caveat names; the synthesized stratum still cannot advance an arm.

### 2.4 HumDial Track-2 style timing (organiser code read at `f51d8eb`)

| Quantity | Definition | Direction |
|---|---|---|
| **First-response delay** | first model-output (ASR-timed) word start − end of the user's first speech segment; kept only when positive | lower-better |
| **Timing rejection rule** | a rejection scenario (backchannel, pause, third-party, directed-at-others) counts as *rejected correctly* when the first model audio begins **after** the user segment end (positive difference); model audio before that point is an early interrupt | higher-better (rejection rate) |
| Denominator caveat | the organiser's script drops items whose output is empty from the denominator | **We do not**: empty or absent output stays in the denominator, so our rate is not comparable to the organisers' |
| Class names | URB, PH, TPS, SDO (rejection); FQ, ND, RR, TS, ST (interruption) | labels only, with our own definitions in `label_contract.json`; mapping to our four states is nearest-equivalent |

First-response delay is computed from the event-log first-audio time and cross-checked against the pinned Silero on `output.wav` (CS-48).

### 2.5 Controller-side quantities (CS-23 / CS-47 / CS-49)

| Quantity | Definition | Direction |
|---|---|---|
| Cancel latency p50 / p95 | user onset (or confirmed-interruption time) → last ordered cancel hook completed (queue, generation, vocoder, orchestrator, per-hook timestamps) | lower-better (CS-2 proposed target ≤ 200 ms p95) |
| False-yield rate | stops / yields on backchannel, off-talk or background speech | lower-better |
| Interruption Respond rate | genuine interruptions followed by a new response | higher-better (non-inferiority margin set in CS-49) |
| Per-decision CPU latency p50 / p95 | featurisation + inference per decision, ≥ 30 repeats, A/A dispersion, at the declared pinned core count and at 1 core | lower-better; timing legs only |

## 3. Reading rules that prevent the known misreadings

- **t_stop without the scenario flips meaning.** A long t_stop on a backchannel clip is a pass.
- **TOR without the scenario flips meaning.** TOR 0.9 is excellent on `smooth_turn_taking` and a failure on `pause_handling`.
- **Latency without its rate is censored data.** Report latency beside TOR / response rate / recall.
- **Operating points on selection, confirmation touched once.** Selection and confirmation are disjoint by speaker and dialogue (`corpus.json`, checked by `tt_verify.py`).
- **Synthesized pairs are matched, not natural.** They prove an arm can or cannot separate contrasts when the acoustics are identical; they say nothing about real hesitation prosody. That is the human stratum's job.
- **A reference row is a different instrument.** Quote it with its tag; do not difference it against a measured row.
