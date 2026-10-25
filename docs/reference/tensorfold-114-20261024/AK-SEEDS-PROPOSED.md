# AK hypothesis seeds proposed from TensorFold 1.1.4 (2026-10-24)

The paste-ready seed text is in `inbox-drafts/<campaign>/<NN>-….md`. This file is the index: ranking, overlaps and how
the seeds are loaded.

## Ranking (ROI on measured bottlenecks)

| Rank | ID | Lane | Focus symbols | Class | Expected effect | Cheapest falsification | Port cost | Overlap |
|---|---|---|---|---|---|---|---|---|
| 1 | `akg-fa-gqa-adjacent-grid-order` (G2) | 27B MI210 | `launch_fattn` grid (`fattn-common.cuh:1176-1178`), `flash_attn_ext_f16` (wmma) | bit-exact | −8…−20% of the 80k step if FA re-reads K/V per GQA head; nil ≤8k | rocprof `FETCH_SIZE`/`TCC_HIT` on FA at 1×80k (arbiter); then `test-backend-ops -o FLASH_ATTN_EXT` byte-equal and one quarter-hour MI210 micro-bench | low | new (route AKX-ALL-19; FA owner note 10 §4) |
| 2 | `akg-fa-q8-kv-tile-widen-no-convert` (G3) | 27B MI210 | `ggml_get_to_fp16_cuda` call in `fattn-common.cuh:1022-1041`; wmma/tile K/V loaders | bit-exact | −8 ms at 80k (−6.6% of step) plus FA K/V bytes ~−45% | kv_convert time on the champion at 80k < 2 ms → dead; else byte-equal FA plus timing | medium | new |
| 3 | `akg-fa-gqa-rows-packed-mfma-tile` (G1) | 27B MI210 | new MFMA FA tile at D=256 (`ncols2` GQA packing as in `fattn.cu:113-150`) | TOL / RI | with G3, up to −20…−28% of the 80k step (ceiling) | after G2+G3: FA within 1.5× of the q8 single-read floor → dead | high | distinct from KVU-19b c2 (held out) |
| 4 | `akm-q38fn-cpy-producer-writes-consumer-layout` (Q1) | Q38FN CPU | CPY nodes feeding `MUL_MAT` in `src/models/qwen4exp*.cpp` | bit-exact | 2-4% (ceiling 9.4%) | node-profile CPY classification; CPY < 3% after norm-to-q8 → dead | low-medium | partial: norm-to-q8-fusion (KEEP) |
| 5 | `akm-ds41-1017-dsa-indexer-fused-scan` (D1) | DS41-1017 CPU | indexer subgraph in `deepseek41.cpp` (mul_mat, relu, weighting, head sum) | bit-exact | unknown; long context only | at-depth node profile: indexer < 2% → dead | medium | record-only like note 30 S5; needs AKX-ALL-12 |
| 6 | `akm-q38fn-gdn-prologue-into-chain` (Q2) | Q38FN CPU | `GATED_DELTA_NET` (`ops.cpp`), `ssm_conv`, l2norm nodes | bit-exact | 1-3% | is the prologue already in `qwen4exp-fused.cpp`? Prologue nodes < 1% → dead | medium | small-node-prelude-collapse, fused-decode-nle8 |
| 7 | `akg-dflash2-drafter-vocab-span-head` (G4) | 27B MI210 | DFlash2 drafter `lm_head` (`src/models/dflash.cpp`) | target-output-neutral | ≤1% | the drafter already projects only its vocabulary, or the head is < 1% of the round | low-medium | new |

Evidence-only (no new id): H4 (#1138), H3/H13 (#1079 L42), H7 (`11e9b4db18`), H8 (#1079 series); Q38FN
sibling-gemv-pack and norm-to-q8 (#1138, `11e9b4db18`).

Harness proposal (not a hypothesis): AKX-ALL-31, the planted-control non-finite and fp32-accumulator gates (TensorFold
`docs/kernel-contract.md` gates 1 and 4).

## How to load (instructions; NOT applied)

1. **Mechanism.** There is no JSON/YAML seed file and no `focus_symbols` field. AK reads Markdown notes from
   `<store>/inbox/*.md`:
   - `controller/inbox.py:34` `read_inbox()` reads them;
   - `loop/run.py:3808` `build_context()` re-reads them every iteration;
   - `loop/actors.py:2971-2974` renders them under "Operator suggestions";
   - the planner turns them into its `HYPOTHESIS_FIELDS` (`mechanism_id, statement, falsifier, target_surface,
     target_symbol`, `loop/actors.py:1569`).

   Ids use `akm-` for CPU and `akg-` for GPU. Scope comes from the routes and owned targets plus the profiler's
   `kernel_hotspots`.
2. **When.** After the operator approves the Stage-3 plan **and** lifts the 2026-10-24 "DO NOT LAUNCH AUTOKERNEL" hold.
3. **Who.** The campaign owner of each store (single-writer).
4. **What.** Copy byte-exact into the three stores:
   - `inbox-drafts/ak-27b-gpu-verify-20261004/60-tensorfold-114-fa-at-depth-seeds-20261024.md` →
     `/mnt/raid0/llm/autokernel/campaigns/ak-27b-gpu-verify-20261004/store/inbox/`. Also into
     `store-b0ba1d427-np1-r12-20261007/inbox/` if that is the active store when the hold lifts; confirm first.
   - `inbox-drafts/ak-q38fn-cpu-decode-20261003/65-tensorfold-114-seeds-20261024.md` →
     `…/ak-q38fn-cpu-decode-20261003/store/inbox/`.
   - `inbox-drafts/ak-ds41-1017-cpu-decode-20261021/32-tensorfold-114-seeds-20261024.md` →
     `…/ak-ds41-1017-cpu-decode-20261021/store/inbox/`.
5. **Record.** Record each copy's sha256 under AKX-ALL-30.
6. **Before any GPU seed is authored.** Run AKX-ALL-30a (the arbiter) in a granted MI210 window, and admit AKX-ALL-19
   (G3 route with the DF2-9 gate).
7. **What not to touch.** Do NOT add these to `loop/seeds/hypotheses/` (repo-level seeds installed by `loop/seed.py`):
   they are lane-specific. Do NOT confuse them with the `seeds` key in `campaign-manifest.json`, which holds target specs.
