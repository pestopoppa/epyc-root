# PREFIX-4 landed native contract repair — 2026-10-31

**Landed on APP origin/main: `7d92b1a8c198c2b3cd86e0920bc7f1c54364454f`. No deployment, stack action, index rebuild or production/model mutation. Final exact encoder SHA-256: `ae9ae18481eb64e7c2bd022c86cb396524ef4ecd0946318be1e424107e212492`.**

Final exact tracked-source run: 13.00882575684227 s, sampled peak RSS 2,092,527,616 bytes, rc 0, captured child reaped. 76 tracked tests pass (15 new + 61 existing); make gates, explicit ruff format/check and normal commit/push hooks pass. The preparation steps below describe the audit leading to the landed change; final canonical facts are in `capsule/SUMMARY.json`.

The candidate makes cosine computable for **44/44 rows** against untouched native PyLate 1.4 public `ColBERT.encode`: exact full input IDs, masks, retained positions, matrix shapes and effective document contract agree before numerics. Reason has **19 PASS / 3 NUMERIC_FAIL** at the unchanged maximum per-token divergence threshold `<=1e-2`; LateOn has **22 PASS**. Reason's maximum divergence is `0.012336671352386475`, LateOn's `0.001204848289489746`. Computability does not establish retrieval quality, model adoption, or Reason numerical parity.

## Authority and source

Fresh ROOT origin/main `7a9e291a4cc3805e7a4033ecf0c5ca57b0fcedac`, `handoffs/active/colbert-reranker-web-research.md`, PREFIX-4: fix encoder contract divergence and rerun the same 44-row/20-snippet harness until cosine computable, zero-to-light CPU, no model change.

Fresh APP origin/main `src/retrieval/colbert_encoder.py` is byte-identical to canonical PREFIX-3 source: SHA-256 `23bee710f784bdcdbf7e67be82be3f186c82695bb185098313377b684bd39510`, originally commit `de6c56e34f5f23c2155d2b7dc839554ae692f771`. Original and candidate snapshots and proposed patch are retained here. No worktree was created or switched; pinned research lane untouched.

GitNexus status on owned APP lane: not indexed there. Query against existing `epyc-orchestrator` index resolved exact `Function:src/retrieval/colbert_encoder.py:encode`: LOW, 3 impacted, 2 direct. Generic encode's HIGH belongs to unrelated toon_encoder. Direct source audit additionally identifies web colbert_reranker and kb_rag callers and stored-convention routing; graph results alone are incomplete caller evidence.

## Producer defect and faithful fix

Native source is `.../codex-ni-g14-reason32m-20261030/overlay/pylate/models/colbert.py`: lines 413–421 choose effective skiplist; 685–726 prune document punctuation and normalize; 1049–1105 tokenize body at cap-1 then insert trained marker at position 1.

* Native Transformer reads Reason lowercasing from `sentence_bert_config.json` (`do_lower_case=true`), while APP read only ColBERT/export metadata. Candidate falls back to Transformer metadata.
* Native PyLate 1.4 uses `self.skiplist_words or list(string.punctuation)` when no explicit constructor override is provided. Therefore Reason's saved `skiplist_words=[]` becomes the punctuation list in native public encode. Candidate reproduces that effective contract rather than changing native reference metadata or model files.
* Native singleton document encoding is unpadded. APP padded to cap using default token ID 0. Native's MASK-token padding override (50284) is irrelevant to this unpadded singleton harness; all final IDs and masks match exactly with no padding rows to excuse. Native code handles batching separately, outside this single-text API.
* Candidate tokenizes stripped/lowercased body at cap-1, inserts the trained role ID after CLS, keeps SEP at the truncation boundary, and masks document vocabulary skip IDs after forward. It retains query punctuation. It never drops an arbitrary row to obtain shape equality.

First Reason snippet at cap64: feed length18, CLS50281 at position0, D50369 at1, period15 at16, SEP50282 at17. Both producer and native reference remove precisely position16 and retain positions0–15,17, yielding17×128. CLS, D and SEP are retained. Full per-row IDs/masks and position lists are in `results/ROWS.json`.

The candidate refuses zero/nonfinite token embeddings instead of producing undefined cosine directions. Native run contains none: actual/reference minimum norms both `0.9999998807907104`. Independently computed true cosine denominator values are recorded per row, alongside the unchanged original unit-vector dot-product divergence rule; no zero vectors, NaN replacement or threshold changes.

## Same harness and old-fail/new-computable evidence

Canonical old run retained at `/mnt/raid0/llm/tmp/codex-ni-prefix3-native-20261030/baseline-current-app/results/RESULT.json`: Reason22/22 OUTPUT_CONTRACT_MISMATCH, LateOn22/22 TOKEN_OR_POSITION_MISMATCH, no cosine. This candidate's44 rows use the same original models,20 banked texts, public native reference call, caps,128 coordinates and threshold.

The22 observations/backend are **20 snippets**, with snippet0 repeated at caps32/64/128 and snippets1–19 at64. There are **no query/control rows** in this cohort. Each backend is compared only with its own native checkpoint; no cross-model embedding comparison is made.

Harness diff (`HARNESS-OBSERVATION.patch`) changes the known-wrong observer assumptions (raw saved config versus native effective config; all-attended versus actual producer retained mask). It also adds finite/nonzero norm checks and true-cosine denominators, and corrects candidate/source metadata. It leaves cohort, thresholds, reference encode and original metric computation unchanged. Final report metadata is normalized after execution; no row was removed or relabeled numerically.

Reason failures preserved: snippet1 cap64 divergence0.011357784271240234; snippet8 cap64 0.010066449642181396; snippet10 cap64 0.012336671352386475. All3 are now honest numerical comparisons rather than preprocessing mismatches. Fixing that separate quantization fidelity issue or re-exporting is outside this no-model-change contract task.

## Compatibility and regression

`PREFIX_CONVENTION` changes qd-v1→qd-v2 because tokenization/row selection changes. Existing kb_rag `_roles_for_convention` accepts only current PREFIX_CONVENTION or legacy none, so qd-v1 reads/writes refuse explicitly and require a fresh index, preventing silent cross-contract comparisons. Existing index files are not changed. `ROLE_NONE` preserves old preprocessing/padding/lowercase behavior for prefix-free stores.

`test_contract.py` has14 passing model-free checks using the canonical tokenizer: old/new ROLE_NONE feed/count/vector exactness for3 cases; marker/CLS/SEP/cap/native row masks across6 cases; query punctuation; zero/NaN refusal; singleton clear; qd-v2 segregation. They use a fake nonzero session only to test producer plumbing and never claim model fidelity. The real full44-row native run supplies fidelity evidence.

## Resource and provenance

`GRANTS-BEFORE.json` captures fresh grant files/classes before execution: all5 grants block-correctness, including GPU184–191. Native CPU smoke ran explicit CPU-only torch2.6.0+cpu (no CUDA/HIP build), ONNX CPUExecutionProvider only, GPU visibility disabled, OMP/BLAS/ORT1, taskset128,129, under R11 <=300s without region-lock. Harness asserts no self FD references `/dev/kfd`. Resource supervisor enforces8GiB and290s, samples RSS and child PID list, waits/reaps its captured child. Final sampled peak2,092,527,616 bytes, clean rc0, captured PID absent. `RESOURCE.json` holds exact timings/samples. This is a bounded resource receipt, not a performance measurement. Model-free tests used standing pair32–33 mutex on SMT128,129 under R6 all-correctness fallback.

`BEFORE-PINS.json` and `AFTER-PINS.json` verify original graphs, native weights and JSON size/inode/hash unchanged. No weights were copied, chmodded, downloaded or substituted. Source snapshots/harness are pinned in `SOURCE.sha256`. `first-run/` preserves the preliminary computability run before final regression/denominator hardening.

## Filing and belief capture

Existing SC50 native ColBERT source family applies; no new source class or grading ladder is introduced. A conclusion can be filed as committed observation `[belief: cc]` by the owning publisher after review. This private packet invents no retrospective measurement warrant or adapter/canary completion. APP patch and tracked regression tests are now landed in the existing APP lane with all validations above. Main should apply only the prepared handoff/progress text and capsule through its sole ROOT publisher. No index/source-table rows are edited here.

Additional existing consumer validation: scratch candidate injected under the real module name in the pinned Python3.12 runtime; existing pure-Python pytest dependency reused read-only from APP env, plugin autoload and root conftest disabled. Existing `test_colbert_lock_contract.py` and `test_colbert_reranker.py`: **61 passed** in0.65s, with one asyncio_mode config warning from disabled async plugin. Exact runner and log retained. The initially selected APP venv lacks numpy; its import failure is retained separately, with no package installation.

Stored-convention runtime checks additionally passed: real kb_rag routes qd-v2→query/document, none→none/none, and raises ValueError for qd-v1. Existing61 tests pass with these checks in the retained runner.
