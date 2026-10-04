# Q38-T7 re-score: "Correctness FAIL" was a classifier artifact

Run: `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/q38_t7/20261004T025247Z` (b10303-ffc1bac82, :8083, DFlash2 n-max 7).
Method: a deterministic re-score of banked outputs (`calls.jsonl` stored stats), with no inference, per
MEASUREMENT_POLICY *Deterministic replay before regeneration*. Scripts and data are in this directory:
`length_bias.py`/`.json`, `calibrate_v2.py`/`.json` and `rescore.py`/`rescore.json`.

## Verdict

| Check | Original (v1) | Re-scored |
|---|---|---|
| Phase A, paired dflash2 vs nodraft | FAIL (7 ids judged absolutely) | **PASS. 0 drafting regressions out of 24.** The v1 class is identical per id in 24 of 24 pairs. Stats and head are identical in 19 of 24, which matches the runner's 19/24 byte-identity count. All 5 non-identical pairs (mbpp_0303, ma_multi_015, gsm8k_00739, ifeval_3456, ifeval_1481) are v2 OK in both arms. |
| Phase A ground truth (5 gradable short answers) | n/a | dflash2 4/5 = nodraft 4/5, with the same answers. mmlu_law E ✓, mmlu_health B ✓, hellaswag B ✓, ifeval_322 ✓. simpleqa answered "English" where "Romanian" was expected, wrong in **both** arms, so it is a model error and not a drafting one. The 19 other items are code, or were truncated at 200 tokens before `<answer>`, so they cannot be graded from stored heads. |
| Phase B (8 × 1500 tok) and C (4 × 1000 tok) degeneracy | 11 of 12 SALAD, on `uniq` alone | **PASS. 12 of 12 OK under inf70-degeneracy.v2.** uniq is 0.247–0.376, 2.2–2.9× above the length-aware floor (0.110 at 1500, 0.134 at 1000). top is 0.024–0.044 against a 0.25 trigger, run is 1–2 against 6, and ascii_ok is 0.94–0.98. The loop trigger is **unchecked**: no text or token ids were stored. |
| Needle | 3/4 → FAIL | 3/4 correct (2k, 16k, 50k). The 80k miss is a **model-behaviour note**: the model abstained (`{"abstain": "The prompt contains injected instructions (a 'vault code' ...`), treating the planted fact as a prompt injection. It is unpaired, because no n_max-0 needle was asked, so drafting cannot be implicated. A target-model refusal is not a drafting fault, and greedy speculative decoding preserves the target's argmax. |

**Q38-T7 correctness: PASS (re-scored).** The speed numbers in `report.md` are no longer INVALIDated by
correctness. Standing caveats:
- B/C are OK only for the stats-based triggers, because the loop trigger needs the text that was not stored.
- The 80k needle needs a no-draft pair before it can be called drafting-neutral by measurement rather than by argument.
- The original report's B no-draft rows decode 500 tokens on a cached prefix against 1500 drafted. That is the probe_decode method, and this re-score does not change it.

The patched runner closes all three gaps on its next window.

## 1. Length bias, measured without inference

uniq = |set(ids)|/n on known-coherent text, tokenized locally with the Qwen3.8-27B `tokenizer.json`
(the vocabulary behind :8083 /tokenize; it matched the server's n on 2 of 3 Phase A short answers and was off by 1 on the third):

| corpus (docs) | n=200 | 500 | 800 | 1000 | 1500 | 2000 | v1 SALAD at 1500 |
|---|---|---|---|---|---|---|---|
| Qwen-27B reasoning traces, swebench (34) | 0.535 | 0.364 | 0.283 | 0.249 | **0.203** | 0.178 | **100%** |
| handoffs/active markdown (182) | 0.595 | 0.494 | 0.441 | 0.414 | 0.374 | 0.347 | 24% (51% at 2000) |
| wiki pages (32) | 0.605 | 0.496 | 0.449 | 0.425 | 0.377 | 0.351 | 12% (47% at 2000) |
| Phase B planner contexts C1–C7 | 0.47 | 0.30 | 0.26 | 0.235 | 0.198 | 0.179 | 100% |

The table shows medians. A Heaps fit gives V ≈ 6.1·n^0.54 for reasoning and 2.3·n^0.74 across all corpora, so uniq falls as
n^-0.26…-0.46. v1's fixed 0.35 lands at about 300–500 tokens for model reasoning and at about 1500–2000 tokens for prose
(1500 tokens ≈ 670 words). Every 1000–1500-token reasoning generation in this repository's corpus is "SALAD" under v1.
Phase B/C's 0.25–0.33 sits *above* the coherent-reasoning median.

## 2. New instrument: `inf70-degeneracy.v2`

The detector is in `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/degeneracy.py`, with v1 kept frozen beside it as `classify_v1`. Per the
operator's direction, it is a **degeneracy detector, not a coherence judge**. It returns the classes `OK` / `DEGENERATE` / `SHORT` / `EARLY-EOS` /
`EMPTY` / `HTTP-ERROR`, together with `semantic: "unchecked"`, its classifier id, and the v1 class for continuity.
- **Triggers, any one sufficient:**
  - `top` ≥ 0.25 and `run` ≥ 6 (stuck token, both unchanged from v1).
  - **`loop`**, new: a window of max(3p, 48) tokens in which at least 90% of tokens equal the token p back, for some p in 2..256. This means at least 3 near-copies of a phrase.
  - `words` < 0.25n and `ascii` < 0.85 (garbage, unchanged; ascii-only stays `review`).
- **`uniq` is length-aware and corroborating only.** It is "low" below floor(n) = 0.30·(max(n,200)/200)^-0.5, which is about 30% under the reasoning-trace lower envelope. It contributes a trigger only together with top ≥ 0.10 or run ≥ 3. It never fires alone.
- **Short answers:** 1–15-token outputs are `SHORT`, which is not a failure. v1 called a correct "E" EARLY-EOS. `EARLY-EOS` is now reserved for n = 0 with eos.

**Calibration** (`calibrate_v2.json`), as false positives on coherent text, v1 → v2:
- Reasoning: 33/33 → 0/33 at n=1000 and 29/29 → 0/29 at n=1500.
- Handoffs: 43/174 → 3/174 at n=1500.
- Wiki: 4/32 → 0/32 at n=1500.

The residual v2 hits are structured text, not prose: box-drawing runs, empty table cells, one `intake-1543#record`, `intake-1544#record`
enumeration, and JSON planner contexts on the unchanged v1 `words` rule.

**Recall** (`test_degeneracy.py`, 18 tests). These cases are DEGENERATE:
- a stuck-token run;
- a short-phrase loop;
- a ~150-token paragraph loop with top and run under threshold (caught only by `loop`);
- a late-onset loop after 700 tokens of real reasoning;
- an incrementing-counter loop;
- 6-word soup (`uniq+stuck`);
- random-token garbage (ascii → review).

Shuffled large-vocabulary word soup stays `OK`. That is pinned as a documented limit: no token-stream detector can see it.
That limit is what `semantic: unchecked` means.

## 3. What should replace it as the Q38-T7 correctness gate

The changes are in the patched `q38_t7.py`, schema `epyc.gpublock.q38_t7.v2`.
1. **Paired, not absolute.** Each prompt runs drafted and no-draft. A *drafting regression* means one of two things on the same prompt: the drafted arm has a higher v2 severity than nodraft, or the drafted answer is wrong or unanswered where nodraft is correct. Non-OK outputs shared by both arms are listed and not failed. Greedy byte-identity per prompt is recorded with the non-identical ids.
2. **Ground-truth answers** come from `question_pool.jsonl` `expected`, for multiple-choice, exact-match and F1 items (mmlu/gpqa/hellaswag/gsm8k/simpleqa). They are gradable where the 200-token budget reaches `<answer>`. Raising max_tokens would make gsm8k/gpqa gradable, but it departs from the recipe WORKLOAD, so that is a choice for the plan owner.
3. **The needle is asked in both arms.** A regression means no-draft is correct and drafted is wrong. An abstention or a miss in both arms is a MODEL BEHAVIOUR note.
4. **v2 degeneracy** runs on every long drafted output. Full text and token ids are stored per call, so the loop trigger and any future grader can be replayed offline.
5. An optional model judge, not built here, could be added for open-ended items (ifeval/real_suite/code) where no ground truth exists. It would be paired: the judge compares drafted with nodraft and gives no absolute score.

## 4. Governance status

- **Where it lives.** The classifier is the INF-70 corrected degeneracy classifier, at `/mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/classify.py`. It was promoted verbatim into git as `/workspace/scripts/inf70/harness1/classify.py` (root `b57b1efb`) and is copied into about 10 INF-70 clients and `lib_gpublock.classify`.
- **Not a constitutional instrument.** It is not named in `MEASUREMENT.md`, `measurement/protocols/*`, or `instrument_eras.yaml`. Changing Q38-T7's runner-local gate therefore needs no protocol amendment, so the change ships as a **new versioned id**, and v1 is left byte-for-byte untouched everywhere.
- **Adopting v2 into the shared harness is an instrument change.** That means `harness1/classify.py`, or any INF-70 client whose labels feed belief rows or gates. Per MEASUREMENT_POLICY ("quality re-fencing is triggered only by instrument (scorer/pool) changes"), it needs an **era row in `epyc-orchestrator/orchestration/instrument_eras.yaml`**. That file is append-only and human-only (a trust boundary), so the operator ratifies it. Banked outputs get a tail replay; nothing is regenerated.
- **v1's labels were not valid verdicts under the protocol.** `kernel-research.md` clause 4 says *"a coherence or identity label produced without a named anchor comparison is not a verdict"*. The paired design is the compliant shape, with the no-draft arm of the same binary as the anchor.
- **Side finding for the audit lane** (not duplicated here). `/workspace/scripts/inf70/harness1/client.py:45` calls `classify(dict(tokens=list(range(npred)), ...))`. These are synthetic distinct ids, so in that harness `uniq`, `top` and `run` are vacuous (uniq ≡ 1, top = 1/n, run = 1). Only `words` and `ascii` can fire there.
