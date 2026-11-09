# Kernel-store integrity proposal (LOOP-48 / LOOP-59) — 2026-11-09

PROPOSAL ONLY. Nothing was deployed. No write under /mnt/raid0/llm/kernels or /mnt/raid0/llm/llama.cpp.
Branch `ni/kernel-store-check-20261109`, worktree `/mnt/raid0/llm/worktrees/kernel-store-check-20261109`,
commit `e745229a8` (not pushed). Test: `python3 -B tests/test_verify_kernel_store_custody.py -v` -> 12/12 OK.
Scratch under /mnt/raid0/llm/tmp/rtg22-audit-20261109/ (old-verify_kernel_store.sh = origin/main copy for the
control run, base-tree/ = origin/main extract for the receipt-test baseline, mapped-files.txt,
gpu-grant-ended-files.json, gpu-job-artifacts.json, gpu-job-classes.json).

## 1. What the checkers do today, and why the stray passed

`verify_kernel_store.sh` (origin/main) per backend: production/<b> is a symlink; target resolves to a readable
dir; primary binary executable; 5 companion tools (cpu/gpu); `libggml-hip.so` present via `[ -e ... ]`
(gpu/stt/tts must have it, cpu should not); provenance WARN; linkage through `verify_ggml_linkage.sh`;
archive listing; >=4 backends. It never reads SHA256SUMS, hashes no library, lists no files, never tests
symlink-vs-regular.
`verify_llama_cpp.sh`: source-tree branch/commit/clean; `readlink -e` of the store symlinks; sha256 of the two
`llama-server` binaries only; the same linkage script. No library hash, no store inventory.

Why the regular-file `libggml-hip.so` passed:
1. `-e` is true for any file, symlink or regular.
2. The linkage script judges only libraries appearing in `ldd <binary>`. In v10, `libggml.so.0.16.0` has
   DT_NEEDED `libggml-hip.so.0`, so ldd lists the VERSIONED soname (which was intact); the unversioned name
   is only reached by a dlopen/scan of the exe dir, which ldd never shows. It also canonicalises with
   `readlink -f` and accepts any path whose real path is inside the tree; a regular file in the same dir is inside.
3. Binary sha256 covers llama-server only.
So the stray was invisible to presence, linkage and binary identity; only a per-file hash/inventory could see it.

## 2. Store survey (read-only; 172 builds, candidates, archive, quarantine)

- production: cpu/gpu -> builds/{cpu,gpu}-20260921-ffc1bac82/bin (v10). stt/tts -> whisper.cpp/build/bin and
  qwentts.cpp/build (SOURCE trees, not store builds; store copies exist as builds/stt-20260731-b30737922 and
  builds/tts-20260731-2c1b5182e). archive: 2 symlinks (v9 cpu/gpu) to builds/*-20260810-0db32c06e.
- SHA256SUMS: 117/172 builds; the 55 without are 19 cpu + 36 gpu, all 10-30..11-09 (C6/C7/C8/C9 + zos22).
  C5 builds DO have one now (LOOP-48's premise is stale for C5). candidates/* have SHA256SUMS + PROVENANCE.
- Manifests: 55 builds carry PROVENANCE.md/.txt; no MANIFEST file anywhere.
- SHA256SUMS path spelling differs: `bin/x` (15 builds), `./x` bin-relative (102), `./bin/x` build-root-relative
  (v9 pair, stt, tts). The patch resolves each row against both the SHA256SUMS dir and the target dir.
- Aliases: 15,921 entries scanned: no regular `X.so` with an `X.so.0` sibling anywhere; no dangling symlinks;
  no slash-bearing symlink targets. v10 `libggml-hip.so` is a symlink again (restored 11-03 07:38).
- Hashes: `sha256sum -c` clean for v10 cpu+gpu (gpu 106 rows = 106 regular files), v9 cpu+gpu; stt only
  PROVENANCE.md differs (edited after the sums; benign). C5/C6 `libggml-hip.so.0.16.0` match their sums.
  Other builds were screened by mtime-vs-SHA256SUMS only (nothing newer except v10 gpu symlink, C5, C6).
- Unlisted regular files today (the full list): C5 and C6 gpu: `libggml-hip.so.0.16.0.objcopy-rewritten-20261105`
  (71,117,424 / 70,868,408 B); cpu+gpu `*-20261109-d210f85c2-c9fold`: bench-grammar-sampler, test-chat,
  test-hc-fuse-plan.
- Quarantined stray: kernels/quarantine/gpu-20260921-ffc1bac82-stray-20261103/libggml-hip.so.stray-20261027,
  sha256 daf086c2a805a8cac8ab800198762a379e3d6852342f86539bf7d83837280d80, 68,101,784 B. The patched verifier
  on the real store: cpu 105 and gpu 106 files custody-verified, PASS; stt/tts WARN (no manifest).

## 3. Origin of the 10-27 23:00 file — proven vs unknown

Proven:
- Built from `/mnt/raid0/llm/tmp/champ2` (compile paths in .rodata), AMD clang 18 roc-6.2.0, gfx90a, SONAME
  libggml-hip.so.0, RUNPATH `$ORIGIN::/opt/rocm/lib` (identical to the listed v10 lib's), 148,840 B smaller than
  the listed v10 lib. Matches no other libggml-hip on /mnt/raid0/llm (size and hash). champ2 is gone.
- champ2 held `build-hip` and `build-hip-mmqoff` (du listing in a 10-27 16:38Z transcript), and `champ2/build-hip/bin`
  is documented as an in-place dir of several vintages (autokernel-loop.md:8481). Builds of one commit out of
  champ2 are documented as non-deterministic in libggml-hip (autokernel-loop.md:8023). So the stray is
  consistent with "another build out of champ2/build-hip*". NOT proven which; not provable (tree gone).
- mtime 2026-10-27 23:00:07.143 is content time. Quarantine was a `mv`; the bin/ dir mtime was reset on 11-03.
  The time it entered the store is unrecorded (a `cp -p` would carry the build time).
- Nearest recorded events: orchestrator `reload server_8083` launched 2026-10-27T23:30:10Z (pid 2055785, launcher
  pid 2055669, binary = v10 gpu dir, LD path = that dir) and stopped 23:44:37Z by `orchestrator_stack.py stop
  server_8083` (epyc-orchestrator/logs/llama-server-8083.log, server_launches/launches.jsonl,
  compute-flags/q38-8083-reload-2335.log; stack-stopped marker `when` 23:44Z). GPU grants started 22:57:49
  (inf75-c5-gpu-native-abi-canary, rc=1 at 22:58:06), 22:58:19 (refactor-cme7t-v2) and 23:31:01 (q38-t7b-c-cachepair).
  Temporal neighbours only; no causal link found.
- First sighting by anyone: progress/2026-10/2026-10-29.md (INF37) and the 10-30 NI-GPU prep boundary.
Searched, nothing found: Claude transcripts 10-27 15:00..10-28 08:00 (only CLAUDE.md quotations of libggml-hip);
fish history (0 entries 10-27 18:00..10-28 03:00) and bash history (ends 10-27 11:39); every Codex rollout with
activity after 10-27 22:00 that mentions libggml-hip: only two had 22:00-23:59 hits (01a16d6b, 01a16fc3), all are
reads/strings/mapping code, none writes into the v10 dir; scripts in origin/main (no script cp/installs into
kernels/builds except runbook text); files named libggml*/libllama*/llama-server/llama-bench written 22:40..23:20 on
10-27 under tmp/worktrees/autokernel (only unrelated fixtures).
Unknown: who wrote it, how, and from which build. Unsearched: sessions with no transcript on disk, other shells,
champ2 itself (deleted).

## 4. Runs that could have loaded the stray (10-27 23:00 .. 11-03 07:38)

Mechanism note: in v10 `libggml.so` links `libggml-hip.so.0` (the versioned file). The unversioned name matters
only to a dlopen/scan of the exe dir. Captured evidence shows binaries behave differently:
- PROVEN-STRAY (maps/hash capture lists `libggml-hip.so` = daf086c2.. alongside the listed lib):
  * DF2-12-1 R7 GPU dirty smoke / rollback test, pid 2217934, test-recurrent-state-rollback, 2026-11-01 ~03:19Z
    (tmp/codex-ni-df2-12-1-prep-20261101/.../ROLLBACK-TEST.json.process.json). 1.5 s smoke.
  * BRF EXP-04 r3, A1 arm (llama-bench), 2026-11-02 (results.r3-invalid-20261103.jsonl; owner already judged invalid).
- PROVEN-LISTED-ONLY (maps.txt of a v10 llama-server in the window shows only libggml-hip.so.0.16.0, inode
  110022320 = the listed lib): ufh14-lb51-residual-r1 (2026-10-30 20:52; full and cutoff runs). The stray was on disk
  then (its hash is already in that plan.json), so llama-server there did not map the stray.
- POSSIBLE / UNKNOWN (used the v10 gpu dir; no maps capture; ldd/linkage text is not proof):
  * orchestrator production :8083, the only server launch recorded after 10-27 23:00 (pid 2055785, 23:30:10 to
    23:44:37Z). By analogy with ufh14 a llama-server probably mapped only the listed lib; unproven. launches.jsonl
    has no later launch; the earlier 8083 launches (10:52, 12:02) predate the file's content time.
  * v10-referencing grant jobs found by sampling: brf-cap04-pilot-20261102-v3, codex3-prbt4-r1-20261031,
    handoff-kvu16h-k35-native-20261102, ufh14-a3a-single-warm-r11-20261028, yarn-128k-mi210-r1-20261029,
    yarn-128k-mi210-r3-20261030; plus run dirs inf34-dr3e-pgpu1 smoke (10-28), gpu-leak-1e (10-29), yarn-agg1g
    (10-31), kvu k35 validation (11-02).
- Sampling bound: 93 GPU (mi210) grant `.ended` files in the window (10-27:5, 10-28:21, 10-29:6, 10-30:21, 10-31:15,
  11-01:10, 11-02:15). By path-named artifacts to depth 3: 6 reference v10, 5 only other builds (champion C5/C6
  etc.), 82 have no binary evidence at that depth. "No evidence" is not "clean".
Unknowable: for any run without a /proc maps or hash capture, what the loader mapped cannot be reconstructed after
the fact (the stray itself is preserved in quarantine). Owners re-judge their own results; this only bounds
exposure: 2 proven-stray, 1 proven-clean-by-maps, everything else unknown, llama-server runs lower risk than
llama-bench/test-binary runs.

## 5. Patch (committed on the branch, not applied anywhere)

`scripts/session/verify_kernel_store.sh`: new `custody()` per resolved target (hashing in read-only Python):
1. SHA256SUMS beside the target or at the build root (target basename `bin`): FAIL for versioned store dirs
   (builds/archive/candidates) with none; WARN (counted, noted) for targets outside versioned dirs (today stt/tts).
2. every row must exist and hash-match (rows inside the target FAIL, rows outside like PROVENANCE.md only WARN);
   an empty manifest FAILs.
3. exact-file allowlist: every regular file directly in the target must be a row; unlisted = FAIL (dot-files WARN).
4. alias check: a regular `lib*.so[.N]` with a versioned sibling (`.<digits/dots>` suffix) FAILs (the incident
   shape); every symlink must be a bare same-dir basename, not dangling, resolving to a listed file.
`tests/test_verify_kernel_store_custody.py`: 12 controls on a synthetic store. Clean passes; the five required
mutations: M1 regular file replaces alias (+M1b identical bytes still fails), M2 unlisted file, M3 hash mismatch,
M4 missing SHA256SUMS, M5 dangling alias; plus path-target symlink, cpu-build stray, dot-file WARN, empty manifest,
and the three SHA256SUMS spellings. Negative control proven: the origin/main script exits 0 on M1.
Receipt-test fallout: `tests/test_kernel_store_receipt.py` fixtures now write SHA256SUMS in setUp; it is back to its
baseline (11 pass, 1 fail = `NI28_BASELINE_CHECKOUT` unset). WHEN that baseline is supplied, the
`ordinary_mode_matches_prechange_copied_script` parity test will FAIL because the verifier now prints extra
`custody:` lines: the NI28 receipt owner must re-pin its baseline revision (3872413f..) and expect receipt
verifier-digest changes. I did not touch the receipt producer.
D9/human-only: NOT guarded. `scripts/session/` is not in check_d9_loop_plane.py GUARDED_PREFIXES
(scripts/coordination/, scripts/hooks/), is not in human_only_paths.yaml, and the commit passed the hooks. It is
a store verifier referenced by the v10 ratify script and the freeze runbook, so land via normal review. Not applied
to /workspace.

## 6. SHA256SUMS generation without touching frozen production — options

- A. Sidecar manifests outside kernels/ (e.g. repo-tracked artifacts/kernel-store/sums/<build>.sha256) read by the
  checker. Zero writes under kernels/. Drift risk; a second file per build elsewhere.
- B. (working recommendation) `SHA256SUMS` at the build root of each of the 55 non-production, unfrozen builds,
  written by a writer added to the build/stage/promotion step so new builds ALWAYS get one (`sha256sum` over regular
  files in bin/, `bin/x` spelling, written once, mode 0444, never edited). Production v10/v9 already carry sums:
  no write. Not executed here; the one-time backfill of the 55 builds is gated by the operator/owners and should
  start only after the C5/C6 objcopy siblings below are dispositioned.
- C. Content-addressed store: out of scope.
Additional hardening (no kernels/ write): pin the SHA-256 of the v10 gpu/cpu SHA256SUMS file in verify_llama_cpp.sh
next to the binary digests, so the manifest itself cannot be silently rewritten.
Follow-up (not done): an `--audit-builds` read-only mode that runs the same helper over every build and prints a
rollup, so strays in non-production builds are visible before promotion.

## 7. Proposed handling of the stray families found today (propose only)

- `libggml-hip.so.0.16.0.objcopy-rewritten-20261105` (C5 and C6 gpu): left by an 11-04/11-05 objcopy experiment; the
  real lib was rewritten then restored (hashes match their sums). The name does not end in `.so`, so ggml's scan
  and ld.so will not pick it up: low risk. Recommend keeping it as evidence and MOVING both into `<build>/aux/`
  (outside bin/) with rows in the regenerated SHA256SUMS, after the objcopy lane's owner confirms; never delete
  without confirmation. Until then the checker would flag them if pointed at those builds.
- c9fold unlisted `bench-grammar-sampler`, `test-chat`, `test-hc-fuse-plan` (cpu and gpu, built 11-09): SHA256SUMS
  lists 25/28 files, i.e. written before the last targets finished or deliberately scoped to the served set. Not
  libraries. Recommend the build/stage writer regenerates SHA256SUMS AFTER the final target (no hand-edit) and
  that someone decides once whether test/bench binaries belong in the served dir (else build them outside bin/).
  No action is needed for the production gate; these are not production.
