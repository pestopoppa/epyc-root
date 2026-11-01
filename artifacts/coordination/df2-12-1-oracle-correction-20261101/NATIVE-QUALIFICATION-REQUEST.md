# ws58 scheduling request: DF2-12.1 same-image native test and calibration

**Operator-approved preparation; no target exposure, READY, keeper nonce, official grant, FILED receipt, or science verdict exists.** ws58 owns the live boundary and distinct pregrant qualification resource claims. This packet does not authorize a live :8070/:8083 reload or request. These scratch servers are instrumented production-code frontends linked to exact frozen v10 libllama/ggml, not observed live production binary equality. The champion owner fold-in remains requested in `OWNER-BUILD-REQUEST.md`.

**Correction to native gate interpretation:** `NATIVE-DIRTY-FAILURE.md` retains the two genuine frozen-test rc1 results and exact library/model receipts, but `dirty-diagnostic/TEST-ORACLE-ROOT-CAUSE.md` proves the test overwrites its FULL replay reference during the PARTIAL stage, then compares the dirty FULL restore against the wrong oracle. The minimal test-only correction passed on the same small qwen35/frozen libraries and an omitted-restore negative control failed. No kernel dirty-restore defect is established by the original rc1 results. The *original frozen test still fails*, so the predeclared gate remains unmet for the final measurement image and all 304 science identities remain unissued. NI may build and test its own D2 scratch measurement image with the corrected test immediately under standing admitted smoke rules, without champion-owner acknowledgment. The champion owner separately folds/reviews the test-only patch in its existing candidate before adoption/promotion. Full-host calibration, live keeper deployment, HARD qualification and science retain their respective owner/resource boundaries. The 0.8B unit tests are not 35B/27B cross-slot parity verdicts.

**R7 standing GPU smoke path:** `OWNER-RULINGS-20261028.md` R7 authorizes a ≤300-second real GPU smoke without a FILLERS grant or ws58 approval, using `region-lock --gpu-quiet exclusive` with no CPU-list and inner `taskset 184-185`. `r7_gpu_dirty_smoke.py` is a bounded entry for the **exact 29 GB architect target** rollback test. The no-admission probe returned rc75 while INF12 held MI210; its watcher was stopped before admission when the small CPU unit model became available. No GPU model was loaded. This optional diagnostic does not bypass the failed CPU same-image gate or create a HARD qualification receipt.

**Runnable owner entry (after ws58 writes the bounded authority files under compute-flags):**

```bash
R=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101
"$R/owner_pregrant.sh" test cpu --authority "$WS58_CPU_TEST_AUTHORITY"
"$R/owner_pregrant.sh" test gpu --authority "$WS58_GPU_TEST_AUTHORITY"
"$R/owner_pregrant.sh" calibrate cpu --authority "$WS58_CPU_CAL_AUTHORITY"
"$R/owner_pregrant.sh" calibrate gpu --authority "$WS58_GPU_CAL_AUTHORITY"
```

`owner_pregrant.sh` fixes the exact CPU/GPU binary, same-source test, target model/hash, frozen prompt SHA, scratch proof/output paths, and region-lock syntax. Only the owner authority paths and their time windows are runtime inputs. Each JSON authority is issued/custodied by ws58 under `/mnt/raid0/llm/tmp/compute-flags/`, with `kind:"ws58.pregrant.native_test.v1"` for test or `kind:"ws58.pregrant.calibration.v1"` for calibration; `issuer:"ws58"`, `id:"codex-ni-df2-12-1-..."`, `purpose`, `role`, exact `regions`, `host_cpus`, `manifest_sha256`, `binary_sha256`, `max_rss_gib:120`, `start_epoch`, `end_epoch` (≤1800s), and `model_sha256` for tests. The wrapper refuses missing/mismatched/out-of-window authority and rehashes every image artifact before any lock or model load. It enforces 120 GiB group RSS and owner deadline; group signals require the captured leader's exact birth/UID/PGID, with exact captured-PID fallback if the leader exited. Model-free regression refused a wrong leader birth and a stale artifact without signaling/dispatch. A harmless `/dev/null` dry run returned rc2 `OWNER_PREGRANT_REFUSED` before dispatch. The expanded commands below document what the wrapper executes; ws58 should invoke the entry above.

## Accepted scratch build artifacts and source custody

Root: `/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101` (`R` below). Immutable source commit `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`; production server-context source SHA `f45a212c0a71e648fae6133ef7ae541ad8c2e00d850240a9d100339993bca902`; trace patch SHA `af9fbaf7ed56b92ea9aa1ab8cb401b97d02915e0a71a62d2a1930ca0bd1b9271`. `build_trace_frontend.py` compiled only patched `server-context.cpp` in scratch, replaced one object in a copied archive and linked scratch `libllama-server-impl.so` with unchanged production objects/DSOs. Frozen build/source/store hashes and mtimes remained identical. CPU DSO SHA `8b38b9f2444aaa367125e4409ad3eecbfe6b97f2d9961f58f4ac1dbbc2bb70df`; GPU DSO SHA `16466579feac479f27c15083ec8e78b1dc105aa8f7546f58796ccaa7df635d20`. `frontend-instrument/{cpu,gpu}/BUILD-RECEIPT.json` holds exact compile/link argv and every input SHA. `frontdoor_mtp/IMAGE-PREFLIGHT.json` and `architect_dflash/IMAGE-PREFLIGHT.json` PASS static identity, fresh executable/DSO/test markers and split linkage: official frozen `verify_ggml_linkage.sh` PASS for the underlying kernel plus exact own frontend DSO/frozen DSO realpath checks. Actual `/proc/<pid>/maps`, GPU KFD/VRAM and trace-off token equivalence still need native run proofs.

**Architecture correction before any owner handoff:** the 2.06 GB DFlash2 drafter GGUF has `general.architecture=dflash`; frozen `llm_arch_is_recurrent`, `llm_arch_is_hybrid`, and `llm_arch_supports_rs_rollback` do **not** include DFlash. It would skip the test and is invalid as a rollback model. The actual CPU target GGUF `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` is `qwen35moe` (37,801,097,504 bytes, SHA-256 `c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131`); the GPU target GGUF `Qwen3.8-27B-Q8_0.gguf` is `qwen35` (29,047,086,048 bytes, SHA-256 `a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348`). Both hashes were locally rechecked under bounded R6, and both architectures are in frozen `llm_arch_is_hybrid` and `llm_arch_supports_rs_rollback` at `src/llama-arch.cpp:1040-1087`. `MODEL-ARCH-PREFLIGHT.json` records the exact fields and source SHA. This only establishes architectural eligibility; the test must still reach actual dirty-context PASS. The 0.6B ASR GGUF failed architecture load; synthetic granitehybrid/mamba2 skipped `n_rs_seq`, qwen4exp synthetic exited −11. None is a PASS; current `frontend-instrument/cpu/ROLLBACK-TEST.json` is a retained failed synthetic check and must never be cited for target qualification.

## Step 1: owner-held CPU native rollback test, then GPU native rollback test

The CPU test loads the **37.8 GB** `qwen35moe` target and needs a free whole-host physical `0-95` claim, 120 GiB RAM cap, 1800 s hard authority window, and own PID/birth/PGID/peak-RSS receipt. The alternative longer GPU test loads the **29.0 GB** `qwen35` target and needs GPU-quiet exclusive plus free host threads `184-191` (no CPU-list region fold), 120 GiB host RAM cap, 1800 s authority, sampled KFD/VRAM and own PID drain. These are distinct pregrant qualification resource claims, not the R6 small-prep permission or R7 short smoke. `image_preflight.py test` inherits the region-lock process group and registers `pid birth_ticks` in the isolated PIDFILE; on timeout it TERM→KILLs only that captured test PID, verifies death and writes `.process.json`. Both runs must reach `recurrent rollback checkpoint restored successfully`, without skip or dirty-context mismatch, on the exact respective library image. ws58 writes and retains its limited qualification resource authority, region-lock log, start/end and process custody. No official FILLERS grant is issued for these tests.

```bash
R=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101
CPU_MODEL=/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf
GPU_MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
CPU_MODEL_SHA=c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131
GPU_MODEL_SHA=a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348
CPU_BIN="$R/frontend-instrument/cpu/bin"
GPU_BIN="$R/frontend-instrument/gpu/bin"
mkdir -p "$R/native-test-cpu/state" "$R/native-test-gpu/state"
# ws58 first creates isolated state dirs and pregrant authority for full target models.
FILLER_ID=df2-12-1-pregrant-cpu-test FILLER_STATE_DIR="$R/native-test-cpu/state" \
FILLER_PIDFILE="$R/native-test-cpu/state/df2-12-1-pregrant-cpu-test.pids" \
/workspace/repos/epyc-orchestrator/scripts/region-lock run \
  --cpu-list 0-95 --role test-cpu --timeout-s 60 --tag df2-12-1-cpu-test -- \
  taskset -c 0-95 /usr/bin/python3 "$R/image_preflight.py" test --backend cpu \
  --identity "$R/frontdoor_mtp/IMAGE-PREFLIGHT.json" \
  --test-binary "$CPU_BIN/test-recurrent-state-rollback" --hybrid-model "$CPU_MODEL" \
  --hybrid-model-sha "$CPU_MODEL_SHA" --ld-library-path "$CPU_BIN" --timeout 1650 \
  --out "$R/frontdoor_mtp/ROLLBACK-TEST.json"

FILLER_ID=df2-12-1-pregrant-gpu-test FILLER_STATE_DIR="$R/native-test-gpu/state" \
FILLER_PIDFILE="$R/native-test-gpu/state/df2-12-1-pregrant-gpu-test.pids" \
/workspace/repos/epyc-orchestrator/scripts/region-lock run \
  --gpu-quiet exclusive --role test-gpu --timeout-s 60 --tag df2-12-1-gpu-test -- \
  taskset -c 184-191 /usr/bin/python3 "$R/image_preflight.py" test --backend gpu \
  --identity "$R/architect_dflash/IMAGE-PREFLIGHT.json" \
  --test-binary "$GPU_BIN/test-recurrent-state-rollback" --hybrid-model "$GPU_MODEL" \
  --hybrid-model-sha "$GPU_MODEL_SHA" --ld-library-path "$GPU_BIN:/opt/rocm/lib" --timeout 1650 \
  --out "$R/architect_dflash/ROLLBACK-TEST.json"
```

The 60-second `region-lock --timeout-s` bounds **lock acquisition**; the native test's 1650-second timeout and keeper's 1800-second authority/watchdog bound full compute exposure. ws58 records the isolated state directories and exact owner/custody. Do not use the CPU test as the GPU image test or vice versa. Active correctness bookings currently occupy 0-95 and GPU+184-191; wait for owner serialization, then recheck actual resources.

## Step 2: rendered-token preflight and matched production-thread rates

After both test receipts PASS, ws58 holds distinct qualification resources to load each exact scratch role image and call `/apply-template` then `/tokenize` with `add_special=true,parse_special=true`. Require equal rendered salted lengths A–E for both roles; freeze the maximum actual rendered planned request length and production recipe SHA into the final manifest **before** keeper nonce. Raw vocab-only salt length 95 is not this value. Use `CALIBRATION-FIRST.md` for a separate keeper-owned pregrant t96 CPU whole-host request and t8 GPU quiet request; no unqualified official FILLERS grant. Those two observations produce separate recipe-bound `calibrated-production` rate evidence for v14. No 2-SMT rate is extrapolated to production threads.

## Step 3: HARD admission and scoped science

The canonical v14 gate is still a source candidate under `/mnt/raid0/llm/tmp/codex-ni-hard-qual-gate-20261101/`, not a deployed keeper allowlist. Once ws58 deploys it at its owner boundary, NI freezes the two exact production manifests with target tokenizer lengths, `kv_cache_mode` parsed from native startup (`split` CPU, `unified` GPU), saved production recipe SHA, 304 completion identities/106 phases, and the two calibrated rates. Keeper-issued normal and active-cutoff qualification must use the same pinned job entry and record the native first request, live PID/birth, STOP observation, UNKNOWN partial and verified child drain; no prework rc75. Only a legitimate FILED receipt permits the scoped parity verdict. Five issued requests at np4 leave at least one queued; a zero-defect observation cannot close the literal five-way one-step co-prefill condition or G2-CONC.
