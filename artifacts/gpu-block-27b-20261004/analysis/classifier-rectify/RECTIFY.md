# INF-70 classifier rectification: references, owners, prepared diffs

Date 2026-10-04. Operator-approved. Read-only investigation: no inference was run, no server was started, nothing
was committed, and no handoff, wiki, doc or memory file was edited.

**Background:**
- `/mnt/raid0/llm/tmp/q38t7-rescore/AUDIT.md` and `RESCORE.md`.
- The classifier is `/mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/classify.py`. It has a byte-identical git copy at
  `/workspace/scripts/inf70/harness1/classify.py`, promoted in root `b57b1efb`.
- It is replaced by the shared `coherence_gate` library, being built in `epyc-inference-research` on branch
  `feat/coherence-gate-ec`. That branch does not exist in the shared clone yet, so the diffs below name the tiers but
  do not import its API.

**Replacement procedure.** Every rectification points at the same procedure:
- **Tier 0:** paired byte-identity against a named anchor.
- **Tier 1:** ground-truth answer checks, plus `degeneracy.v2`, which takes real token ids and refuses synthetic ones.
- **Tier 2:** a paired, orchestrator-hosted judge for residual divergences.
- Full texts and token ids are stored, so every verdict can be replayed.

**Defect demonstrated.** I ran the current `/workspace/scripts/inf70/harness1/classify.py` locally (no inference) on a
200-token stuck loop:

    classify(dict(tokens=list(range(200)), stop_type="stop", content="the the the the " * 50))
    -> {'cls': 'COHERENT', 'uniq': 1.0, 'top': 0.005, 'run': 1, 'words': 200, 'ascii_ok': 1.0}

**Prepared files** (all in this directory; `git apply --check` passes on each against the current working tree):

| file | target repo | applies to |
|---|---|---|
| `01-cpu-decode-roofline-program.patch` | root | `handoffs/active/cpu-decode-roofline-program.md` |
| `02-autokernel-unified-surface-program.patch` | root | `handoffs/active/autokernel-unified-surface-program.md` |
| `03-research-recipe-constant.patch` | epyc-inference-research | `scripts/lib/qwen38_flash_next_recipe.py` |
| `04-harness1-classify-client.patch` | root | `scripts/inf70/harness1/{classify,client}.py`, new `tests/inf70/test_harness1_classify_refusal.py` |
| `05-vidya-inf70-arm-capture.patch` | root | `scripts/vidya/adapters/inf70_serving_arm_capture.py`, `tests/vidya/test_inf70_serving_arm_adapter.py` |
| `06-wiki-classifier-correction.patch` | root | `wiki/{benchmark-methodology,speculative-decoding,hardware-optimization}.md` |
| `07-instrument-era-row.DRAFT.yaml` | epyc-orchestrator | `orchestration/instrument_eras.yaml`. **Human-only: the operator ratifies it.** |
| `staged/` | — | the full post-patch files the diffs were cut from |

**Ownership.** Both affected handoffs are owned by `inference-research-index.md`:
- `INF-70` → `cpu-decode-roofline-program.md`.
- `INF-73` → `autokernel-unified-surface-program.md`.

The roster lane for that index is the **`inference`** session (`coordination/session-bus/config.yaml:27`, role
`inference-main`). INF-73's AutoKernel work runs in that lane's AK seat. EVL-47 (vidya) is owned by
`research-evaluation-index.md`.

---

## 1. `cpu-decode-roofline-program.md`: G2-CONC, E-GATE, PROD-1 and the historical labels

**Owner:** INF-70 (`inference-research-index.md:29`), `inference` lane. **Must apply:** the `inference` session.
This is not a subagent write, and not the caller's.

**Problem:**
- **G2-CONC (~4811)** is a blocking promotion gate that has never been run. It defines its verdict as classify.py's
  classes. Its repro client, `agents/mtp-conc/client.py`, scores a distinct-*word* ratio ≥ 0.35, which is
  length-biased and has no token ids.
- **E-GATE Criterion 1 (~4742)** says "ALREADY MET" on `mtp-tip2`'s 12/12 COHERENT. That label came from synthetic
  ids, so only the words and ascii rules could fire.
- **PROD-1 (~652) and PROD-3 (~737)** require G2-CONC but never name its instrument.
- The historical "20 COHERENT + 4 SHORT" figures (~920, 1756, 2639, 4191, 4236, 4560) are all synthetic-id labels.
  BE-1's "zero EARLY-EOS" is vacuous, because chat `finish_reason` is never `eos`.

**Affected results (from AUDIT §1):**
- **None flip.** All 403 rows files recompute to 0 SALAD, and no keep, reject or promotion rested on a uniq-only SALAD.
- MTP to production, Axis E and BE-1 (AUDIT #2) are held by the 2026-10-04 paired divergence read.
- CHAMPION-1/-3, CHAMP-2, SYNC and harness1 (AUDIT #6) are held by sha256 identity.
- B4-r2 is held by paired PPL/KLD.
- Re-anchor #2 is held by 27/27 identity.
- GDN-ROWEXACT is held by byte-identity plus multi-reason, real-id pre-fix SALADs.

**Rectification (patch 01):**
- **G2-CONC.** The procedure is fully re-specified:
  - Instrument: `coherence_gate`, never classify.py.
  - Arms (a) and (b) are kept.
  - **Anchor:** each prompt is also served alone on the same binary. Identity against incumbent production is
    recorded as information only.
  - **Prompt set:** at least half the items gradable, with `max_tokens` high enough to reach the answer.
  - **Tier 0:** byte-identity of text and ids against the anchor. Identity is REQUIRED on row-exact routes (OP-39
    policy C). On full-throughput routes, identical streams are cleared and divergent ones go on to tier 1.
  - **Tier 1:** a divergent stream FAILS on ground truth if it is wrong where the anchor is right. It also FAILS if
    its `degeneracy.v2` severity on real ids exceeds the anchor's. Shared non-OK rows are listed, not failed.
  - **Tier 2:** a paired judge, on a server not under test, rules on residual divergences. Without a judge the
    result is INCOMPLETE, with the rows eyeballed and listed, never PASS.
  - **Report:** by reason (IDENTICAL / DIVERGENT-CLEARED(gt|judge) / WRONG / DEGENERATE / SHORT / EMPTY /
    HTTP-ERROR). Throughput is reported only beside the verdict.
  - **Storage:** text, ids, native `stop_type`, the anchor pairing and the classifier ids are stored before the
    verdict.
  - **PASS** means zero FAIL, 100% identity on row-exact routes, and every residual divergence adjudicated.
  - Binary proven with `strings` (HYG-1b).
- **E-GATE Criterion 1** is re-grounded on the paired divergence read and becomes a standing tier 0–2 gate against
  the same binary's MTP-off arm. Divergence alone is not a failure, which preserves the "exactness is NOT a gate"
  ruling.
- **PROD-1 and PROD-3** name the instrument and require the recipe constant to be re-worded (patch 03).
- The historical labels are **annotated in place, not rewritten**, with a CLS-RECT tag.
- A new open item, **CLS-RECT-1**, ledgers which paired evidence holds each result and when the rectification is done.

## 2. `autokernel-unified-surface-program.md:1255, 2117` (also 2010)

**Owner:** INF-73 (`inference-research-index.md:69`), `inference` lane / AK seat. **Must apply:** the `inference`
session.

**Problem:** these lines are pointer rows to G2-CONC. They are not a classifier definition, but line 1255 reads as
though G2-CONC is self-contained. Lines 2117 and 2010 only assert candidate-binary identity and stay correct, so they
need no change.

**Affected results:** none.

**Rectification (patch 02):** the 1255 pointer row now names the `coherence_gate` tier procedure and states that it
is never `classify.py`.

## 3. `wiki/benchmark-methodology.md` rule 5 (~5283), plus two sibling wiki claims

**Owner:** the compiled wiki. Edits land only in the **wiki compilation sweep inside an operator-invoked `/wrap-up`**
(`agents/shared/SESSION_LIFECYCLE.md`, *Wrap-up cadence*). **Must apply:** the main session, at its next operator
`/wrap-up`.

**Problem:**
- Rule 5 codifies classify.py's design, MIN_N and its class names as methodology. It makes no mention of real ids,
  length bias, or the lack of any semantic check.
- `speculative-decoding.md:2443` cites "120/120 coherent … classified by reason" as the no-garbage evidence.
- `hardware-optimization.md:5222` says "coherence must be checked every round" without saying how. That statement is
  correct, but it is incomplete.

**Affected results:** the MTP no-garbage criterion's cited evidence. It is now held by the paired read.

**Rectification (patch 06):**
- A 2026-10-04 correction appended under rule 5, stating the three defects and the tier 0–2 replacement. The rule
  itself still stands.
- The source list is updated with the audit, rescore and this file.
- The speculative-decoding claim is re-grounded on the 12/24-identical, fluent-divergence read.
- hardware-optimization gets a "paired, never absolute" clause.

## 4. `scripts/inf70/harness1/classify.py` and `client.py:45`: the fake-token bug

**Owner:** root-tracked code, VB-WIRE-2 / INF-70 harness. **Must apply:** the main (caller) session, as owner of
this operator-approved rectification. Notify `inference` first, because it runs the arms. Do not commit until both
are aware.

**Problem:**
- (a) `client.py:45` passes `tokens=list(range(npred))`. This leaves uniq/top/run vacuous and records `n_uniq`
  identically as 1.0.
- (b) **Second defect, found here.** The client passes OpenAI `finish_reason` ("stop"/"length") as `stop_type`, so
  EARLY-EOS can never fire on the chat path.
- (c) The fixed `uniq < 0.35` is length-biased above ~300 tokens.

**Affected results:** all harness1 / champion-3 / SYNC chat verdicts. None flip (see §1).

**Blast radius (structural grep):**
- `client.py` is invoked only by `arm_cold.sh:87` and `arm_hot.sh:101`.
- `classify` is imported only by `client.py`. `tools/cpuoverlap.py classify()` is unrelated.
- `analyze.py` reads `verdict` only to count reasons.
- The SC75 adapter (§6b) consumes `verdict`.
- `gitnexus impact classify` was ambiguous: several `epyc-root` indexes are registered. The applying session should
  re-run it with the repo specified.

**Rectification (patch 04)**, a deprecation path plus a hard refusal now:
- **`classify.py`:**
  - The v1 rules are kept byte-for-byte, so old labels stay replayable.
  - The class names `CLASSIFIER_ID = "inf70-classify.v1.1"` and a DEPRECATED header pointing at `coherence_gate`.
  - New `check_input()` raises `SyntheticTokenIds` for any ≥16-long consecutive id run or non-integer ids. It raises
    `MissingTokenIds` for non-empty content without ids, and `OutOfCalibratedRange` above `V1_MAX_N = 256` unless
    the caller passes `allow_long=True`.
  - The CLI prints `REFUSED` instead of crashing.
- **`client.py`:**
  - The request adds `return_tokens: true, verbose: true`. On the v10 tree (`server-schema.cpp:17,34`,
    `server-task.cpp:482`) this puts the real generated ids in `__verbose.tokens`. It does not change sampling.
  - If those ids are missing, the client falls back to `POST /tokenize` on the content. Otherwise the row is
    `NO-TOKEN-IDS`, and a fake id is never constructed.
  - Each row records `classifier`, `token_source`, `token_ids` and `stop_type_native`.
  - The native stop is deliberately **not** fed to v1. Feeding it would turn correct 1–4-token answers into EARLY-EOS
    failures, the lib_gpublock false-positive mode.
  - `classify_row()` is the single seam to swap for `coherence_gate` `degeneracy.v2` once
    `feat/coherence-gate-ec` lands.
  - The script body moved into `main()` under `__main__`. The arm scripts are unaffected, because they call
    `python3 client.py <label> <port>`.
- **Test:** `tests/inf70/test_harness1_classify_refusal.py`, 15 tests. **All pass on the patched copy.**
  - It pins that the fake-id pattern raises. It also documents the old defect: the soup above is COHERENT under
    fake ids and SALAD (`top=1.0, run=200`) under real ids.
  - It pins the long-n refusal, and that the client contains no `range()` call (checked through the AST).
  - It checks the token-id fallback order, and that ids are never fabricated.

**Verify on the first live arm:** that `token_source == "response"`. I confirmed that the verbose and return_tokens
fields reach the chat response by reading the source, not with a request.

**Instrument change.** Labels change once real ids flow, so per MEASUREMENT_POLICY this needs an era row. The draft
is `07-instrument-era-row.DRAFT.yaml` (scope `inf70_chat_coherence_label`, verb retire-view for pre-boundary labels).
`instrument_eras.yaml` is human-only (`human_only_paths.yaml:48`), so **the operator ratifies it**.

**Scratch copies are not patched.** `/mnt/raid0/llm/tmp/inf70/agents/*/client.py` keep fake ids. Run arms only from
`/workspace/scripts/inf70/harness1`.

## 5. Memory note `feedback_coherence_gate_at_production_prompt_length.md`

**Owner:** the main session (memory). **Must apply:** the main session. I did not edit it.

**Problem:** the note predates classify.py and does not cite it. Its *How to apply* still prescribes "a degeneracy
check (unique-token ratio, top-token share, repeat runs) AND an eyeball" as an **absolute** check. That has the same
length insensitivity: a fixed unique-ratio false-flags coherent text above ~300–500 tokens. It also has no anchor.
Its prompt-length lesson (gate at ~40/~90/~200+ prompt tokens) is still correct.

**Recommended change.** Keep the description and the *Why*. Replace the degeneracy clause in *How to apply* with:

> gate PAIRED against a named anchor (same prompts, reference binary or MTP-off arm) via the shared
> `coherence_gate`: tier 0 byte-identity, tier 1 ground truth + length-aware `degeneracy.v2` on REAL token ids
> (never `list(range(n))`; the library refuses them), tier 2 paired judge or eyeball for residual divergences;
> store full texts + ids. A fixed unique-ratio threshold is length-biased (false SALAD > ~300 tokens of reasoning)
> and a token statistic never certifies correctness.

Then add `[[feedback_vacuous_verification_empty_input]]`-style links to the AUDIT and to this file.

## 6. Other references found by the sweep

**a. `epyc-inference-research/scripts/lib/qwen38_flash_next_recipe.py:786`**
- This is the live canonical recipe constant `HEADLINES["champion3"]["coherence"] = "20 COHERENT + 4 SHORT in all 48
  arms …"`.
- **Owner:** the `inference` lane (PROD-1). **Must apply:** `inference`.
- **Patch 03** re-words it to cite the paired sha256 identity (24/24 production rows, plus full-stream digests at
  41/109/240 prompt tokens, from the CHAMPION-3 gates at handoff ~918/2637) and tags the label as a synthetic-id
  label. The key name is unchanged, and the recipe's 55 tests pass on the patched copy.
- **The owner should confirm the identity wording against the champion3 evidence before applying.**
- The frozen drafts at `docs/design/inf70-close-out-20260908/…recipe.py.draft:540` and
  `data/inf70-prod1-recipe-draft-2026-09-08/…:540` are dated snapshots. Leave them.

**b. `scripts/vidya/adapters/inf70_serving_arm_capture.py:248-275, 404, 520`**
- SC75 belief rows carry `extra.coherence_by_reason` from client verdicts. That field is required, but it is never
  graded.
- **Owner:** EVL-47 (`research-evaluation-index.md:52`, vidya program). **Must apply:** the EVL-47 owning session.
- **Patch 05** adds an informational `extra.coherence_classifier` census. Rows with no `classifier` are named
  `inf70-classify.v1|synthetic-ids(uniq/top/run vacuous)`. It also adds one test. **All 37 adapter tests pass** on the
  patched copy, and the grade is unchanged.

**c. Belief-kernel wiring (CLAUDE.md, *wiring new sources*)**
- `coherence_gate` will produce verified findings, so its write-side hook should be filed now.
- **Draft for the EVL-47 owner to apply.** Add an adapters README row: *"coherence_gate verdicts (tier 0–2, per
  stream: anchor id, identity, ground-truth result, degeneracy.v2 class + classifier id, judge verdict, text/ids
  digests) | measurement | NOT WIRED — write-side hook to be added when feat/coherence-gate-ec lands"*.
- Add a matching task in `vidya-belief-substrate-program.md`. A subagent may only prepare this, so it is
  prepare-only here.

**d. Already rectified by the Q38-T7 lane (the caller)**
- `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/{lib_gpublock.py:466, q38_t7.py}` now use `degeneracy.py`, the v2
  degeneracy classifier, with a paired design. No action.

**e. No change needed** (these use the gate's name, not its classifier, or are historical):
- `docs/design/inf70-close-out-apply-list-20260908.md:126,129` (historical apply list).
- `docs/research-intake/orch-prior-art-stage3-plan-20260926.md:789` (pointer to G2-CONC).
- `epyc-inference-research/scripts/lib/deepseek_v41_flash_recipe.py:369`, which says "coherence gate at production
  prompt length". This is a future requirement and should consume `coherence_gate` when it is implemented.
- `wiki/knowledge-management.md:573` (provenance).
- `vidya-belief-substrate-program.md:1632-2465` (harness wiring pointers).
- `handoffs/completed` and `archived` (10 hits) and `progress/` (44 hits): historical, so they are not edited.

**f. Not dependent, but the same design**
- The orchestrator's `classifiers/quality_detector.py:42-48,120`, `pipeline_monitor/anomaly.py:137-148` and
  `llm_primitives/inference.py:50` are independent fixed unique-ratio repetition guards.
- They are not this classifier, but they may carry the same length bias.
- **Suggested:** an orchestrator-lane follow-up to check their thresholds against output length.

## Routing summary

| who | applies |
|---|---|
| `inference` session (INF-70 / INF-73 / PROD-1 owner) | 01, 02, 03. 01 is a prerequisite for running G2-CONC. |
| main (caller) session | 04, after notifying `inference`; run its test. Also 05 if the EVL-47 owner delegates it. Also the memory note (§5). Also 06 at the next operator `/wrap-up` wiki sweep. |
| EVL-47 owner (vidya) | 05, plus the §6c wiring row and task. |
| operator | ratify `07-instrument-era-row.DRAFT.yaml` into `instrument_eras.yaml`, with `from:` set to 04's commit time. |
| coherence_gate builder (`feat/coherence-gate-ec`) | expose a `degeneracy.v2` entry point that refuses synthetic ids. `client.classify_row()` and G2-CONC tiers 0–2 then bind to it. |
