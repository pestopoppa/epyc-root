DS41 1017 TARGET-ONLY BASELINE  --  matched_process_v2 instrument, built 2026-10-21 (built, NOT run)
====================================================================================================
Directory: /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/    (the only place anything here writes)

FILES
  gate_1017.py                      the instrument driver (sha256 3bf046751387f1635ec075c7ed46ce102d46ec16c7cc0ab17bee611a41f4a9a4 at build time)
  sept_launch.snapshot.json         frozen copy of the DS41 runtime-adopted Sept launch (CanonicalResolvedRecipe.to_dict();
                                    pinned sha256 a09f6056...bc5c0; from_dict re-verifies its snapshot/execution digests)
  prompt-manifest.ds41-decode.json  byte copy of the campaign's frozen prompt manifest (1 prompt: ds41-decode-p01, token-id prompt,
                                    n_predict 256, temp 0, top_k 1, seed 42); pinned sha256 cb033a1d...a190
  model_identity_1017.json          the pinned split-model identity (9 shards: size + sha256 + logged-at time + mtime)
  gguf_meta.py / gguf_meta.json     read-only GGUF KV-header reader / its output for 1017 shard 1 vs the Sept Q4 file
  snapshot_sept.py                  how sept_launch.snapshot.json + the manifest copy were produced (read-only on the campaign store)
  dryrun.out                        output of `gate_1017.py --dry-run --aa-pairs 24 --cmp-pairs 5` at build time

THE RECIPE (ds41-1017-mxfp4-cpu-t48-targetonly)
  template_hash 65f1c793e12f37a2055e2f4b84c345663a09c4491b29553f7321f40461274e4b
  request_digest e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58   (1 frozen request)
  execution_digest  champion dd3d9721c  c70c8066c533d0cdf93daa117a9919f34dc561cc0938e966ce544e8d94d54dbb
                    candidate f0c96dc1f 4a175f16309a54be582e91255146fdb97b5ef5359269de67a0a2edace37b5f30
  argv: taskset -c 0-95 numactl --interleave=all <build>/bin/llama-server -m <1017 shard 1> -np 1 -c 8192 -t 48 -tb 48 -b 2048 -ub 512
        -ctk f16 -ctv f16 --device none -ngl 0 -fa on --host 127.0.0.1 --port 18741 --metrics --slots --no-kv-unified --no-mmap
        --no-webui --load-threads 48
  env (explicit, nothing inherited): GGML_IQK=1 OMP_DYNAMIC=false OMP_PLACES=cores OMP_PROC_BIND=spread OMP_WAIT_POLICY=active
                                     + LD_LIBRARY_PATH=<build>/bin

HOW THE SPLIT-MODEL DIGEST IS DEFINED  (ArtifactDigest(role=model).sha256)
  path   = shard 1 (what `-m` must name; llama.cpp split-loads shards 2..9 from the same directory)
  sha256 = sha256( canonical JSON {"schema":"epyc.split_gguf_model_digest.v1","shards":[{"index":i,"file":NAME,"size":BYTES,"sha256":HEX}, i=1..9]} )
         = ba9f129c15f823503d00b088ff07e42aa3953d58cf287d019229af052b2e12b2
  The 9 per-shard sha256 values are NOT recomputed (500 GB): they are the values the download job logged in
  /mnt/raid0/llm/tmp/ds41-1017-swap/download_1017.log -- `sha256sum` of each local shard, which the job also checked against the HF LFS
  sha256 before renaming the file into place. On every run gate_1017.py re-checks each shard's size, that its mtime is not later than
  the logged hash time, and that the GGUF header says split.no == index-1, split.count == 9 (first few MB of each file only); sum of
  per-shard tensor counts must be 1046. This detects replacement/truncation/edit since hashing; it does NOT re-prove the bytes.
  resolved_recipe.validate_launch never opens or hashes the model (it checks only the sealed snapshot/execution digests, template
  consistency, build_dir/port and capability); the dry-run proves it with an audit hook: 0 files opened during validate_launch,
  0 model-dir opens during recipe resolution.

LAUNCH COMMANDS  (nothing here has been run)  -- one 502 GB server at a time; do step 1 first, step 2 reuses its floor file
  Choose N_CMP (comparison pairs, 1..64) BEFORE step 1: a matched floor is tied to the comparison pair count it was computed for
  (row.comparison_pairs must equal compare --pairs). `gate_1017.py rederive-floor --floor-file F --cmp-pairs K --out DIR` can re-derive a
  sealed floor for another K from the SAME raw A/A samples (no new measurement; row is marked `rederived_from`).

  1. A/A calibration on the CHAMPION build (N_AA >= 24, e.g. 24; 2*N_AA launches):
     /mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --gpu-quiet shared --timeout-s 1800 --tag ds41-1017-baseline -- python3 -I /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/gate_1017.py calibrate --pairs 24 --cmp-pairs 5 --out /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/aa --execute
     -> aa/floor-store/serving-floor.ds41-1017-mxfp4-cpu-t48-targetonly.requests-e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58.matched_process_v2.pairs-<N_CMP>.json
        aa/calibrate-summary.json, aa/launches-calibrate.jsonl

  2. champion vs candidate (2*N_CMP launches), judged against that floor:
     /mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --gpu-quiet shared --timeout-s 1800 --tag ds41-1017-baseline -- python3 -I /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/gate_1017.py compare --pairs 5 --floor-file /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/aa/floor-store/serving-floor.ds41-1017-mxfp4-cpu-t48-targetonly.requests-e50732d9ce365259d5bb95fe31e36995f98bcd0986dc0e48d489f99390e42f58.matched_process_v2.pairs-5.json --anchor-build /mnt/raid0/llm/kernels/builds/cpu-20261020-dd3d9721c --cand-build /mnt/raid0/llm/kernels/builds/cpu-20261020-f0c96dc1f --out /mnt/raid0/llm/tmp/ds41-1017-baseline-20261021/cmp --execute
     -> cmp/compare-1017.json, cmp/launches-compare.jsonl (and cmp/invalid-attempt-*.json if the instrument archived an invalid arm)

  Without --execute, calibrate/compare only print the plan and run admission (nothing launches).
  Notes on the lock: --cpu-list 0-95 claims regions q0..q3. gate_1017.py --execute REFUSES unless q0-q3 are all held under a tag
  containing `ds41-1017-baseline` (override: --no-lock-check). `--timeout-s 1800` only bounds LOCK ACQUISITION (exit 75 on expiry), not the
  job. At build time q0 (spq-g1-language), q1 (ds41-w6) and q3 (kpf18) were held by other sessions, so acquisition can easily outlast 1800 s:
  re-issue, or use --timeout-s 0 to block. Run `region-lock status` before launching.

COUNTS, TIME, MEMORY
  calibrate: 2*N_AA launches (N_AA=24 -> 48).  compare: 2*N_CMP launches (N_CMP=5 -> 10).  Each launch = server boot + 1 warmup round + 1
  measured round (np=1, 256 tokens each) + teardown.
  Wall time is an ESTIMATE ONLY: the Sept Q4+DSpark launches took ~218 s each (10 launches / 2180.8 s). 1017 target-only is unmeasured, so
  48 launches ~ 2.9 h and 10 launches ~ 0.6 h are the order of magnitude, nothing more.
  Memory: model files total 501,602,535,360 B (467.2 GiB / 501.6 GB). --no-mmap copies it all into anonymous memory (+ KV for ctx 8192, small),
  so ~502 GB resident per launch, one launch at a time. --execute refuses if MemAvailable < 1.10 x 501.6 GB (host: 1133 GB total).
  Teardown: a --no-mmap server unmaps ~0.5 TB on SIGTERM; serving._measure_once waits up to 180 s.

EVERY DEVIATION FROM THE SEPT RECIPE (ds41-00d118d44-cpu-t48-dspark-b2, adopted receipt runtime-recipe-adoption-dfd1fec2e06ec71b)
  Recipe / launch semantics (intended):
   1. model:   DeepSeek-V4.1-Flash-Q4.gguf (518.6 GB)  ->  DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf (+8 sibling shards)
   2. speculation removed (target-only): spec_decode {"type":"none"}; dropped -md <DSpark.gguf>, -ngld 0, --spec-type draft-dspark,
      --spec-draft-n-max 2, --device-draft none.  extra_flags: ('--device-draft','none','--load-threads','48') -> ('--load-threads','48').
   3. env: dropped LLAMA_SPEC_EXACT=batched-greedy-inexact.  Not optional: the resolved-recipe layer REFUSES that variable (set or unset)
      with speculation 'none'.  The environment policy therefore loses that measurement key + witness (policy version
      ds41-cpu-t48-dspark-v1 -> ds41-1017-cpu-t48-targetonly-v1).  The server env is explicit (Popen env=launch_env), so the variable is
      absent from the process by construction.
  Identity labels / plumbing (no effect on what is measured):
   4. recipe name ds41-1017-mxfp4-cpu-t48-targetonly.
   5. port 18641 -> 18741 (own port; port is replaced by <listen-port> in execution_digest).  Free at build time.
   6. provenance dict: the Sept build/export fields do not apply; export_sha256 is a hash of the 1017 template JSON, NOT a production
      export hash; provenance names the derivation and the Sept snapshot digest.
   7. the resolved recipe is derived from the Sept snapshot by gate_1017.py (token surgery on command_argv, asserted against an expected
      literal) and re-bound to each measured build with run._cpu_arm -- the loop's own function.
  Harness additions (do not change the returned value or any digest):
   8. serving._measure_once is wrapped in-process by gate_1017.py: (a) refuses/waits (<=300 s) if the port already has a listener, so a
      foreign server's /health cannot be mistaken for ours; (b) injects boot_timeout_s=900 (serving default 360; a cold 502 GB --no-mmap
      load can exceed 360 s and calibrate_floor cannot resume after an abort; --boot-timeout-s 0 leaves the default); (c) appends every
      launch to launches-*.jsonl.  The instrument source is untouched (pinned worktree research-ds41-run10 @ 5d947693c).
   9. compare: on MeasurementInvalid the invalid attempt is archived and the instrument's single same-tail reschedule is applied
      (the loop's own policy, loop.py ~1906).  calibrate has no reschedule: any failed launch aborts it (see "partial data").
  10. calibrate must be told N_CMP (--cmp-pairs): matched_process_v2 refuses calibrate_floor without `pairs`, and the floor scalar is the
      p95 effect AT that pair count.  (gate_compare.py never calibrated, so it did not meet this.)
  Unchanged: np1 c8192 t48/tb48 b2048 ub512 f16/f16 fa on, --no-kv-unified, --no-mmap --no-webui --load-threads 48, taskset 0-95 +
  numactl --interleave=all, n_predict 256, temp 0, top_p 0.95, top_k 1, metric aggregate_tok_s, GGML_IQK=1, OMP_*.

ADMISSION (matched_process_v2) -- what was checked
  Real calibrate_floor -> _validate_matched_floor(resolved=champion arm) -> write_floor -> load_floor -> serving.compare ran in the dry-run
  with ONE function (serving._measure_once) replaced by a synthetic stand-in and subprocess.Popen poisoned.  Result: a floor row produced by
  calibrate_floor IS admitted by compare (instrument/estimator/unit=process/order/calibration_pairs in 24..256/recipe_hash/request_digest/
  pair membership/reducer replay/content seal/interval/frame), the matched frame is identical for the two builds (it excludes executable and
  DSOs), and four negative controls are refused (wrong pair count, tampered A/A sample, different request bytes, different recipe).
  Conditions for admission at run time: compare --pairs == floor comparison_pairs; same recipe and request bytes; unit process (derived).
  gate_1017.py ADDS one check the instrument itself does not make: the floor's baseline_resolved_recipe.execution_digest must equal the
  anchor arm's execution_digest (i.e. the A/A build IS the compare anchor, champion dd3d9721c).
  The synthetic rows were kept only in memory / a scratch dir that was deleted; none of those numbers mean anything.

PARTIAL DATA
  calibrate_floor returns its sealed row only at the end.  If launch k fails, the run aborts and no floor is written; launches-calibrate.jsonl
  keeps the k-1 completed tok/s values (consecutive launches are the (anchor, candidate) pair members; both are the SAME build, so they are
  usable as an informal dispersion check, not as a sealed floor).

COULD NOT VERIFY (no launches were allowed)
  - That either build can actually LOAD and serve this MXFP4 GGUF.  Checked only: GGUF headers parse; arch deepseek41, config keys and the
    full tokenizer (tokens/merges/types) are identical to the Sept Q4 file (so the Sept token-id prompt means the same text); 1046 tensors in
    both; strings(1) shows MXFP4 kernels, GGML_IQK and --load-threads compiled into libggml-cpu / libllama-common of BOTH builds.
    IQK coverage of MXFP4 expert matmuls (vs the generic path) is unknown.
  - Boot time, per-launch wall time, cold-cache first-load time, teardown time and tok/s of the 1017 target-only launch.
  - Page-cache state: the first launch may read ~502 GB from disk.
  - Real region-lock behaviour under --execute: the lock-status parser was tested on synthetic text and on the live status, not on a lock
    taken by this job.
  - CPU-lifecycle validity (task affinity outside 0-95) and the CPU observer in a standalone (non-campaign) process: same code as the loop,
    but untested here; procguard's campaign guard is not installed (its watch is a no-op outside run.py).
  - The 9 shard sha256 values are the download job's, not recomputed now.
  - Build provenance: dd3d9721c's PROVENANCE.md calls it "champion FOLD CANDIDATE slotdraft (NOT production, NOT yet the champion)";
    f0c96dc1f (10404) has no PROVENANCE.md.  Its tip commit message is "iqk mmid: weighted thread partition of the bounded slab path for
    row-exact Q4_K/Q5_K verify" -- that path is the speculative-verify/Q4_K route, so a ~0 effect on MXFP4 target-only decode would not be
    surprising.  Judge only against the measured floor.
  - Nothing here is wired into the belief kernel (CLAUDE.md "Belief Kernel"): the compare row carries a serving_beliefs v3 capture, but
    only the campaign's serving_beliefs.export() writes those, and this standalone run never calls it.  The owning session must add the
    adapters/README.md source row + vidya-belief-substrate-program task before the results are cited.
