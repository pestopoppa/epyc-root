# kernel-champion-and-promotion — compacted ticked boxes (2026-11-20, handoff_compact.py)

- [x] **FOLD-1 (champion owner)** ✅ 2026-09-08: loop stopped at the boundary (verified dead), pre-fold GPU tip
      tagged `ak/pre-fold-gpu-tip-20260908` (pushed), fold candidate `ef81196d5` built at
      `/mnt/raid0/llm/tmp/build-fold-ef81196d5`; `verify_ggml_linkage.sh` PASS.
- [x] **FOLD-2 gates, SAME merged tree** ✅ 2026-09-08 — all PASS with real tallies on `ef81196d5`:
      G1 `test-backend-ops -o SSM_SCAN -b ROCm0` 7/7 OK (incl. K=4/K=3 rollback), G2 MUL_MAT 1140/1140 OK
      (326 unsupported type combos), G3 GATED_DELTA_NET 39/39, G4 dispatch **observed** (`llama-bench -v` +
      `GGML_SCHED_DEBUG=2`: 27,516 nodes, SSM_SCAN=0, SSM_CONV 576 + GATED_DELTA_NET 576 on ROCm0, CPU holds only
      12 GET_ROWS), G5 tg128 vs gen-021 **+0.052%** (20 pairs, floor 0.638%, not decisive). Result file
      `/mnt/raid0/llm/tmp/fold-window-20260908/fold2-result.json`. NOTE: the first G1-G4 run reported PASS with
      **OK=0** (ANSI-coloured verdicts defeated the `\bOK\b` match; `llama-bench` swallowed scheduler logs
      without `-v`) — structural guards added: a gate PASSES only with ≥1 case run AND an agreeing `N/N tests
      passed` tally, and the graph check only with a plausible node count AND the expected recurrent ops present.
- [x] **FOLD-4 — consolidation is CLOSED; there are no CPU keeps pending** ✅ 2026-09-08. INF-70 reported
      its final RETEST-1 results at ~12:10Z with **no keeps to fold**. The consolidated champion is
      **`ef81196d5`** on `ak/champion/llama-cpp-0db32c06e3e5` = GPU tip `bff30cebe` + CPU champion3
      `9c4f73e29`, FOLD-2 G1–G5 all PASS. The operator's standing condition — *no kernel research until a
      FULLY consolidated champion* — is **satisfied**. Loop relaunch remains a **separate operator go**;
      nothing on this page launches or schedules it.
- [x] **V6R-4 — parallel model load (repack + reader), lost in the v6 bundled revert.** ✅ 2026-09-25 (main-ak-seat)
      The OpenMP repack parallelization (`52ddd3200`, 2025-12-21; upstream PR #18239 closed unmerged) left the
      lineage when v6 Stage 1a `814e81782` was reverted as a whole (`358f0c748`); full record in
      `docs/reference/agent-config/INCIDENT_LOG.md` → INC-20260925. Re-ported onto the v10-lineage champion as
      `25132e042` (test restored and extended, 150/150 bit-exact) plus a parallel pread reader run as an OpenMP team,
      `90c12df42` (`--load-threads` / `LLAMA_ARG_LOAD_THREADS`; the old loader thread was pinned to CPU 0 by libgomp
      under `OMP_PROC_BIND=spread`). Bit-exact (tokens, KL on logits); 27B load 3.2x warm / 2.1x cold. Under
      `GGML_IQK=1` the DS41 recipe touches no CPU_REPACK tensor, so the reader is the whole DS41 win.
      **Champion advanced** `ak/champion/llama-cpp-ffc1bac82eec` `2b57340bf` → `90c12df42`, pushed to the fork
      (workspace-8d notified). Gates (research `a5906f24`, `data/champion-advance-fastload-20260925/`): DS41 519 GB
      load 254.0 / 277.7 s (anchor) → 98.2 s (fast loader), with a 262.6 s single-thread control on the same binary;
      production-recipe decode A/B cut by the operator after one pair (frontdoor 42.23 vs 41.79 tok/s, 0.99,
      identical output). Builds: `kernels/builds/cpu-20260925-90c12df42` (candidate) and
      `cpu-20260925-2b57340bf` (base), ggml linkage PASS. The DS41 campaign re-anchored on it (INF-77 DS41-C32).
  - **V6R-4a** and **V6R-4b** (fast loader into v11; forward-port rule ratification) moved 2026-11-07 to [v11-promotion-checklist.md](v11-promotion-checklist.md) (operator decision C, INF-22 split). [moved: handoffs/active/v11-promotion-checklist.md]
- [x] **HEAD-1 — file the maximum-performance sweep as a canonical citable artifact** ✅ 2026-09-08
      (`docs/design/champion-max-performance-20260908.md`; referenced from this page).
- [x] **HEAD-2 — Qwen3.6-35B-A3B GPU concurrency sweep measured and filed** ✅ 2026-09-08
      (24 launches, residency proven 24/24; recipe `qwen3.6-35b-a3b-q8-gpu-mtp` committed at research
      `c3e362a1`; numbers in `docs/design/champion-max-performance-20260908.md` §6).
- [x] **HEAD-4 — promote the 35B sweep out of scratch into the research repo `data/`.** ✅ 2026-09-16
      Research `data/ak-champion-maxperf-35b-2026-09-08/` (JSON/logs/`sweep.py` at `8c5a9652`; the other two
      as-executed scripts, `SHA256SUMS` and a README step correction at `1eb4a89b`). Files byte-identical to
      scratch; every table value recomputed from the JSON and matched `docs/design/champion-max-performance-20260908.md` §6.
      Belief-kernel write-side wiring filed as SC82 in `vidya-belief-substrate-program.md` (the 2026-09-08 sweeps are pre-hook).
- [x] **PROD-BASE-1 — if a champion-vs-production headline is ever wanted, measure production AT ITS OWN BEST.** ✅ 2026-09-21
      Its own `np` sweep, whatever spec configuration it actually supports (MTP self-draft for Qwen3.8-27B),
      under the same host discipline and with residency proven — **never** forcing production through the DFlash2
      recipe, which measures a lane it does not have and would report a capability gap as a speed gap. Until that
      exists, the champion headline stands **alone**, as an absolute number, with no ratio attached. Not blocked
      on anything; not scheduled — it needs the host and an operator go.
- [x] **METH-BENCH-1 — the bench-vs-serving distinction is recorded where headlines are formed** ✅ 2026-09-08
      (this page, `docs/design/champion-max-performance-20260908.md`, and the wiki compile).
- [x] **G0 · α from live logs (zero inference, today)** — parse per-role MTP acceptance from production llama-server logs; publish per-role α_MTP with a loud zero-lines failure. *Owner: gpu-drafter-mi200-investigation.md (retitle its Gating Measurement).* [findings-02 M0] ✅ 2026-07-17 (`scripts/benchmark/mtp_alpha_from_logs.py` `aa3b35a7`; live: worker_general draft-mtp α=0.994, frontdoor 0.603, architect 0.629; loud-fails on zero evidence)
- [x] **I1 · `seq_refuted` learning exclusion + strategy-store quarantine parity** (code + tests, zero inference). [findings-01 R1] ✅ 2026-07-17 (code was already wired in aa20d029; parity locked by test_seq_refuted_learning_exclusion_parity.py `0492c07a`)
- [x] Forward-port base Laguna arch (merged PR #25165 commits, ~350 LOC: `src/models/laguna.cpp` +332, `models.h`, 1-3-line touches to `llama-arch`/`llama-model`/`llama-vocab`, `conversion/laguna.py` +207) onto a FRESH-pulled `llama.cpp-experimental` off `production-consolidated-v7`; validate S-2.1 Q4_K_M loads + coherence/garbage smoke ✅ 2026-07-25 — landed as `afa770382` on `experimental-v8-refresh-20260724` (superset: includes the DFlash spec path NOT in the PR). Required CPU Q4 evidence is at `epyc-inference-research/data/kernel-v8-candidate/laguna-cpu-dflash-exact-tip/run-20260725T112845Z-67a433bf4-noswap/` (nested `run-20260725T113030Z`): base median `7.078103` t/s, DFlash median `8.028143` t/s, but acceptance `17.2267%` fails the lineup floor. Final hardened GPU IQ2 artifact `epyc-inference-research/data/gpu-mi210/laguna-iq2-kv-sweep-exact-tip/run-20260725T125201Z` is post-identity, `15/15`, and observation-only: A q8/FA-on `33.992845`, B f16/FA-on `35.490117`, C f16/FA-off `33.782293`; B/A `+4.404668%`. `test-llama-archs`/`test-chat-auto-parser` pass in ctest; 2026-07-25 audit verified graph idioms match sibling archs (NEOX rope group, Qwen3-style QK-RMSNorm, per-layer YaRN/plain-RoPE split sound, softplus gate width-checked on both target and drafter sides)
- [x] Confirm the PR-author-flagged "GQA head-ratio backend dispatch" bug does not hit the CPU build ✅ 2026-07-25 — exact-tip CPU Q4 evidence completed all `5/5` base and `5/5` DFlash replicates on the real S.2 model at `data/kernel-v8-candidate/laguna-cpu-dflash-exact-tip/run-20260725T112845Z-67a433bf4-noswap/` (nested `run-20260725T113030Z`; `q4_k_m_base`/`q4_k_m_dflash` both `status=complete`). Source audit confirms `laguna.cpp` reads per-layer `n_head` (`48` full / `72` SWA) with `n_head_kv=8` and passes both values to the shared `build_qkv` graph; `afa770382` changes no `ggml/` backend code. This closes the target CPU concern with real-model execution evidence, not a claim about every hypothetical Laguna variant.
- [x] **L-1 (silent-wrong risk) — make the SWA contract explicit in conversion.** ✅ 2026-07-25 — landed in `89d55f161`.
  Before the fix, `conversion/laguna.py` never wrote `SLIDING_WINDOW_PATTERN` (only `add_sliding_window`,
  `laguna.py:86-89`) — the 4-dense-first layer pattern is an implicit code-side default
  (`laguna.cpp:39-41`); and `rope_freq_base_train_swa` silently defaults to the full-attn
  YaRN base (500000) when `ROPE_FREQ_BASE_SWA` is absent (`laguna.cpp:47-49`) though SWA
  layers intend θ=10000. The landed conversion writes both keys and makes the C++ fallback loud.
- [x] **L-2 (integration gap) — validate encoder input width explicitly.** ✅ 2026-07-25 — landed in `89d55f161`. DFlash encoder
  previously assumed draft `n_embd` == target hidden size (`dflash.cpp:15` vs `speculative.cpp:1325`);
  `LLM_KV_TARGET_HIDDEN_SIZE` existed in `llama-arch.h` but was never read; there was no
  divisibility assert on `n_feat = n_embd_inp_enc()/n_aux` (`dflash.cpp:128`). Mismatch
  previously failed only indirectly via `fc` shape at load. The landed change reads the key
  and checks explicitly.
- [x] **L-3 (masking risk) — bound the non-finite feature sanitize.** ✅ 2026-07-25 — landed in `89d55f161`. `speculative.cpp`
  (+1471-1490) previously unconditionally clamped target features to ±65504/NaN→0 on ALL backends
  (comment blames Metal f16), warning once per process — after the first warning it silently
  masks real target-model numerical bugs. The landed change bounds that sanitize behavior.
- [x] **L-7 (minor) — tighten the normalize prompt.** ✅ 2026-07-25 — research commit
  `daa4c926` removes the disclosed `must be 1.0` answer while retaining the independent exact
  normalized-vector and computed-sum validator; focused Laguna runner tests pass. Before the
  repair, `bed4a1d4` disclosed "JSON `sum` … must be 1.0", so that sub-check did not test
  computation even though the normalized values 0/0.2/0.3/0.5 remained independently checked.
- [x] **L-8 (hygiene) — promote the ad-hoc GPU smoke artifact to a script.** ✅ 2026-07-29 — research
  commit `5fd85268` makes the compatibility projection durable: `laguna_pgpu1_dflash_runner.py`
  deterministically emits `candidate_smoke_summary.json` with schema
  `epyc.laguna_iq2_dflash_candidate_smoke.v2` from formal-run results. It retains the historic
  smoke's per-cell prompt/semantic/completion/cleanup evidence and DFlash acceptance totals, but
  is explicitly `non_gating` and `observation_only`; it cannot create a promotion or performance
  verdict. Reproduced with `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/pytest -q
  scripts/benchmark/test_laguna_pgpu1_dflash_runner.py`: 52 passed. No GPU process, production
  server, or production-kernel tree was touched.
- [x] **L-9 (post-v8 candidate bench) — Laguna Q4_K_M CPU quant-axis screen** ✅ 2026-07-27.
  The operator decoupled this arm from E8 and authorized a paired quality shortcut instead
  of an expensive full-suite discovery. Harness readiness remained complete:
  `laguna_q4_cpu_bench_runner.py` now uses a full `taskset 0-95` /
  `numactl --interleave=all` model prewarm before each suite, the sealed arm-neutral v4
  capture/converter contract, free ports `18094/18095`, and semantic validation of the
  frozen-v8 24-port both-mode stack. Concurrent HIP work is allowed only when every
  sidecar thread is disjoint from benchmark cores; exact argv/model/executable/listener
  identity and all thread affinities are sampled every five seconds. GPU-coexistent
  throughput is explicitly observation-only and forbidden as a role-decision input.
  Focused validation: `35 passed`. The completed SWE40 generation was deterministically
  replayed through the sealed v4 converter and official evaluator: Q4 `19/40` versus IQ2
  `17/40`, zero harness errors, paired discordants `6:4`, exact two-sided `p=.75390625`.
  This `n=40` screen does not resolve a quant-axis difference and is not equivalence
  evidence. The queued LCB53 arm is stopped under the operator's shortcut because the
  quant axis no longer changes the current architect decision. Reproducible evidence:
  `epyc-inference-research/artifacts/laguna-q4-cpu-v8-20260726/laguna-q4-swe-v4-tail-replay-20260727T165223Z/`
  (research `f7ab3ec4`).
- [x] **Former no-consumer blocker reassessed ✅ 2026-07-18**: the 2026-07-03 live MTP acceptance report proves current verification-batch consumers exist (`frontdoor` α=0.6582, `worker_general` α=0.8256, `architect_general` α=0.6854, failed MTP roles `[]`). Registry integration remains blocked until current sweep evidence exists.
- [x] **REOPEN-ASSESS zero-inference decision ✅ 2026-07-18**: reopen to a current live-MTP MoE verifier B-sweep, not to registry integration.
- [x] **Current live-MTP MoE verifier B-sweep**: run on actual frontdoor/worker/architect verification batches with speed, acceptance, and quality/bit-exact guard before any registry integration. ✅ 2026-08-27 — **GATE MET (architect +10.7% at B=n_expert/2)**, decision-grade record at `epyc-inference-research/data/moe-spec-bsweep-2026-08-25/` (findings.md + summary.json + summary_receipt.json). Canonical run (region lock q0-q3, binary v10126 `c7c37a0d9` = MoE-Spec `6b2cbf539` on v9 `0db32c06e`, MTP posture, greedy, 3 reps/cell):
  | role | B | t/s mean±std | Δ vs B=0 | α | α Δ |
  |---|---|---|---|---|---|
  | architect (122B Q4_K_M, n_expert=256) | 0 | 10.84±0.39 | ref | 0.487 | — |
  | | 128 | 12.00±0.41 | **+10.7%** | 0.463 | −2.4pp |
  | | 192 | 11.53±0.22 | +6.4% | 0.462 | −2.5pp |
  | frontdoor (35B-A3B Q8, 256) | 0 | 36.19±2.19 | ref | 0.577 | — |
  | | 128 | 32.05±2.98 | −11.4% | 0.517 | −6.0pp |
  | | 192 | 33.09±0.55 | −8.6% | 0.533 | −4.4pp |
  | worker (gemma4-26B Q4, 128) | 0 | 57.25±4.09 | ref | 0.570 | — |
  | | 64 | 55.77±19.16 | −2.6% | 0.548 | −2.2pp |
  | | 96 | 51.24±13.58 | −10.5% | 0.461 | −10.9pp |
  | | 128 (gate-skip) | 58.54±4.75 | +2.3% (noise) | 0.570 | 0 |

