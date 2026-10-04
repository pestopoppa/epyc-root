# Audit: decisions that relied on the INF-70 degeneracy classifier

Date 2026-10-04. Read-only: no inference was run and no process was started. The classifier is
`/mnt/raid0/llm/tmp/inf70/agents/gdn-rowexact/classify.py` (md5 `e939eaaa…`). It has a byte-identical
promoted copy at `/workspace/scripts/inf70/harness1/classify.py` and a re-implementation in
`/mnt/raid0/llm/tmp/gpu-block-27b-20261003/lib_gpublock.py:466`.

## 0. The structural finding that decides most of this

**On the INF-70 chat path, the `uniq`, `top` and `run` criteria never ran on real data.** Every
24-prompt production-mix client calls:

    classify(dict(tokens=list(range(npred)), stop_type=ch.get("finish_reason"), content=content))

These are synthetic, all-distinct ids. As a result, on every run:
- `uniq` = 1.0,
- `top` = 1/n,
- `run` = 1.

That leaves only `words < 0.25·n` and `ascii < 0.85` live.

Separately, chat `finish_reason` is "stop", never "eos", so EARLY-EOS cannot fire and short
answers come out as SHORT. That is the standing "20 COHERENT + 4 SHORT".

The clients that do this are:
- `agents/{speed-claim, champion1, champ2, champion3, sync14 (client24), sync15, sync16, sync17, sync19-20, b12, b4r2, harness1, be1-ship, be2-fa, e3-run}/client.py`
- `agents/mtp-tip2/chatperf.py`
- `inf70/reanchor2/client.py`
- the promoted `/workspace/scripts/inf70/harness1/client.py:45`

Consequences:
1. **The uniq false positive could not fire anywhere in INF-70's chat verdicts.** I recomputed all
   403 `*.rows.jsonl` files on disk: 8,046 COHERENT, 1,608 SHORT, **0 SALAD**.
2. **On that path, the semantic blind spot is wider than advertised.** Any output with enough
   spaces and ordinary ASCII passes.
3. **The two live criteria ran with thin margins.**
   - The lowest COHERENT ascii share was 0.873 (`phybench_electricity_25`, `gsm8k_00739`), against
     a 0.85 floor.
   - The lowest words/n was 0.26 (`debugbench_flood-fill_cpp`), against a 0.25 floor.
   - So code-heavy or LaTeX-heavy text is one step from a false SALAD. lib_gpublock defuses the
     ascii-only case with its `review` flag; classify.py does not.

Real token ids reached the classifier in only three places:
- **gdn-rowexact `/completion` runs** (n_predict 128/160): 15 SALAD. **None is uniq-only**; every
  one also tripped `top`, and most tripped `run`, `words` or `ascii`. These were genuine `2222…`
  loops.
- **batch-envelope `conc.py`**, which carries its own two-criterion copy (n_predict 96). Its
  verdicts rest on byte-identity.
- **lib_gpublock / Q38-T7**, the only place uniq was live on chat output.

## 1. Decisions ranked by risk

| # | date | decision | gen length | paired / absolute | could flip? | raw outputs on disk | quick re-verification |
|---|---|---|---|---|---|---|---|
| 1 | 2026-10-04 | **Q38-T7, 27B DFlash2 coherence gate: correctness FAIL, speed INVALID**. Explicitly not marked as a reject on uniq alone. | A: 200 tok. B: 1500 (thinking on, 2k–80k ctx). C: 4×1001 | ABSOLUTE on the dflash2 arm. The nodraft arm in A is informational only; B and C have no classified pair. | **Yes, likely wrongly rejected.** A: both SALAD rows (gsm8k_00739 uniq 0.28, gsm8k_00115 uniq 0.335) are `['uniq']` only and are SALAD in nodraft too. The other 5 A failures are EARLY-EOS of 1–8 tokens (MCQ letter or short answer), identical in both arms. That is a second false-positive mode: lib_gpublock treats chat "stop" as eos, while classify.py would call them SHORT. B: 8/8 SALAD on `['uniq']` alone (0.247–0.32, top ≤ 0.044, run ≤ 2, words ≈ 0.5n). C: 3/4 SALAD, same reason. The 80k needle "wrong" is an injection-abstain, which is a needle-design issue, not degeneracy. | **Partial.** `calls.jsonl` holds the full stats, but phase A keeps only 160-char `text_head` and **phase B/C store no text at all**. | A is settled by the paired rescore already in this dir (`rescore.json`: class-equal across arms). B/C need a **short paired re-run**: drafted vs `speculative.n_max 0` at ~2k and ~16k context, 1500 tokens, with full text saved. Then eyeball it and compare the `uniq` of both arms. Stats alone cannot clear the blind spot. |
| 2 | 2026-09-03…04 | **MTP to production**: operator ruling "exactness is NOT a gate; Criterion 1 no-garbage met" (mtp-tip2, 12/12 COHERENT). Axis E merge `10acba0ab` "120/120 zero SALAD" (e3-run). BE-1 n-max 4 / p_min 0.5 "432 requests zero garbage". speed-claim 23.16 t/s / 1.876× becomes the PROD-1 recipe (OP-35). | 200 | ABSOLUTE. MTP and plain diverge by design. | The false positive cannot apply (synthetic ids). The **blind spot was the only exposure**: MTP output differs from plain on 11–12 of 24 prompts. | Yes: full `text` is in `agents/{speed-claim,e3-run,be1-ship}/runs/*.rows.jsonl`. mtp-tip2 `M.chat.jsonl` keeps only heads. | **Done here, read-only.** speed-claim A1-plain vs B1-MTP: 12/24 byte-identical. All 12 divergent rows are fluent, on-task alternative continuations from the first differing character, with 6-gram dup ≤ 0.03; e3-run and be1-ship show the same divergence set. **Settled: safe.** |
| 3 | 2026-09-03 | **Re-anchor #2** deployable numbers, uniform 12.61 vs r16 12.73, "27/27, 0 SALAD", feeding OP-37's r16 choice | 200 | ABSOLUTE | No. uniform vs r16 is **27/27 byte-identical** (checked). OP-38 already demotes the label ("not a fidelity claim"). | Yes, `inf70/reanchor2/*.rows.jsonl` | None needed. |
| 4 | 2026-09-03 | **GDN-ROWEXACT fix `99425578d` → `42332502c`**, "safe at every length 8–361" (the iqk long-prompt-garbage fix in v8/v9/v10 lineage) | `/completion` 128/160, probe sweep | Class counts are ABSOLUTE, alongside PAIRED evidence: n=1 byte-identity vs control, a same-prompt PRE/P table, and e3-alpha's manual "GARBAGE (inspected)" pre-fix rows | No. Pre-fix SALADs are multi-reason genuine loops, never uniq-only. The post-fix COHERENT is backed by byte-identity and by 24/24 chat outputs that are fluent (and also byte-identical across later champion arms). | Yes, `agents/gdn-rowexact/runs/`, `agents/e3-alpha/plain-reclassified.tsv` | None needed. |
| 5 | 2026-09-04…05 | **B4-r2** F16 router (8/24 identical), **B12** IQ4_XS head (NO-GO), **B7/B9/B10** | 200 | ABSOLUTE labels, used as a supplement | No. B4-r2 quality was decided by paired PPL/KLD (`ln PPL ratio +0.0038 ± 0.0037`). B12/B10 were NO-GO on speed. MTP head precision cannot change verified output. | Yes | None needed. A divergence eyeball of B4-r2 plain A vs B is optional. |
| 6 | 2026-09-06…08 | **CHAMPION-1/-3, CHAMP-2 THP shim KEEP, SYNC-14…20, be2-fa FA-split, harness1**: the CPU champion that was folded into v10 | 200 (gates 256) | **PAIRED byte-identity** (sha256 24/24, 5/5, 16/16, 18/18), with "20+4" as an ABSOLUTE supplement | No. Every lever is bit-identical by construction and by measurement, so the classifier is redundant. | Yes | None needed. |
| 7 | 2026-09-22 | **v10 freeze** | — | Quality gate is paired MMLU-Pro/GPQA accuracy at max_tokens 64 (`.claude/skills/kernel-promotion/promotion_gates.yaml:63-120`). The GPU DFlash2-vs-MTP gate is speed-only. | Not via this classifier. The known weakness there is the 64-token cap, already flagged by `truncation_audit`. | n/a | n/a |
| 8 | — | **DS41 serving-gate keeps; AK T0 coherence gate (`kernel_rnd/autokernel/evaluator/correctness.py:3132`, paired byte or token agreement vs the anchor); DFlash2 DF2-6 / SL-5; Flash-Next cap raise; DAR-LAT T96 thread verdict (`critic_thread_gate.v2.py:148`, 4-gram uniq ≥ 0.3, paired `ref-1`); orchestrator `detect_repetition_loop` / `apply_garbage_gate`** | — | Own instruments, mostly PAIRED | Not this classifier. Note that DAR-LAT's 4-gram uniq ≥ 0.3 at 200/400 tokens is a cousin criterion, but it is paired, so a length bias cancels. | — | — |

**Rejected or blocked as degenerate on `uniq` alone: only #1 (Q38-T7).** No INF-70 reject,
keep or promote ever had a uniq-only SALAD.

## 2. Gate files and notes that cite the classifier as authoritative (future exposure)

- `/workspace/handoffs/active/cpu-decode-roofline-program.md`:
  - E-GATE Criterion 1, a standing gate on every MTP arm (~:4742-4745);
  - **G2-CONC**, a blocking promotion gate, "classify by REASON", **never yet run** (~:4811-4818);
  - PROD-1, "recipe must carry G2-CONC" (~:652-657, :737-739).
- `/workspace/handoffs/active/autokernel-unified-surface-program.md:1255,2117`: G2-CONC.
- `/workspace/wiki/benchmark-methodology.md` ~:5240-5300, rule 5. `/workspace/wiki/hardware-optimization.md` ~:5300.
- `/workspace/scripts/inf70/harness1/{classify.py,client.py}`, promoted 2026-09-16.
- `/mnt/raid0/llm/tmp/gpu-block-27b-20261003/{lib_gpublock.py:466, q38_t7.py:57-58,253-272, RUNBOOK.md}`.
- Memory: `feedback_coherence_gate_at_production_prompt_length.md` predates classify.py and does not
  cite it. It prescribes the same uniq/top/run statistics plus a mandatory eyeball, so it carries
  the same length-insensitivity unless the eyeball is honoured.
- Documents that already *limit* the label:
  - `artifacts/operator/staged/p-kld-annex-20260915.md:19,336-341`
  - `artifacts/operator/op38-pkld-decision-20260915.md:77`
- MEASUREMENT_POLICY.md and OPERATING_CONSTRAINTS.md do not cite it.

## 3. Defects to fix before the next use

1. **`uniq < 0.35` is length-insensitive.** Make it paired (candidate vs base on the same prompt),
   or length-normalise it, or drop it in favour of `top`/`run`/n-gram-loop detection.
2. The INF-70 clients pass `list(range(npred))`. Any future gate built on them, G2-CONC included,
   inherits a vacuous token check: pass real ids from `/tokenize`.
3. **lib_gpublock counts chat "stop" as eos**, which turns legitimate 1–8-token answers into
   EARLY-EOS failures. Mirror classify.py: below MIN_N with "stop" means SHORT.
4. Q38-T7 phase B/C saved no text. Every gate must persist the full text, or a later audit cannot
   re-read it.
5. **There is no semantic check.** For any non-bit-identical candidate, pair the candidate with its
   base and eyeball or score the divergent rows. This audit's MTP check (#2) is the template.
