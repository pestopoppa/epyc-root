# Kernel-store stray-file incident, 2026-11-03

Tracking box: LOOP-59 (`handoffs/active/engineering-hygiene-backlog.md`); LOOP-48 is the sibling custody item.
Source analysis: `artifacts/analysis/kernel-store-custody-20261109/proposal.md` (2026-11-09). This page states
what is proven, what is bounded, and what is unknown. Affected results are re-judged by their owners, not here.

## What happened

On 2026-11-03 a stray, unlisted, regular-file `libggml-hip.so` (68,101,784 bytes, sha256
`daf086c2a805a8cac8ab800198762a379e3d6852342f86539bf7d83837280d80`, mtime 2026-10-27T23:00:07) was found in
the frozen production v10 GPU build `kernels/builds/gpu-20260921-ffc1bac82/bin`. It had replaced the symlink
`libggml-hip.so -> libggml-hip.so.0`. With operator approval it was quarantined at
`/mnt/raid0/llm/kernels/quarantine/gpu-20260921-ffc1bac82-stray-20261103/libggml-hip.so.stray-20261027` and the
symlink was restored (2026-11-03 07:38).

## Why the store check missed it

`verify_kernel_store.sh` tested presence with `[ -e ]` (true for a file or a symlink), never read `SHA256SUMS`,
hashed no library and never compared symlink against regular file. The linkage check only judges libraries
that `ldd <binary>` lists; in v10 `libggml.so` needs the versioned `libggml-hip.so.0`, so the unversioned name
is reached only by a dlopen or directory scan that `ldd` never shows. Binary sha256 covered `llama-server` only.

## What is proven about the file

- Built from `/mnt/raid0/llm/tmp/champ2` (compile paths in `.rodata`), AMD clang 18 / ROCm 6.2.0, gfx90a,
  SONAME `libggml-hip.so.0`, same RUNPATH as the listed v10 library, 148,840 bytes smaller than it.
  It matches no other `libggml-hip` on `/mnt/raid0/llm` by size or hash. `champ2` no longer exists.
- The mtime is the file's content (build) time. Quarantine was a `mv`, and the `bin/` directory mtime was reset
  on 11-03, so the time the file entered the store is not recorded.

## Runs proven to have mapped the stray

- DF2-12-1 R7 GPU dirty smoke / rollback test (`test-recurrent-state-rollback`, pid 2217934, about
  2026-11-01 03:19Z). Maps/hash capture lists `libggml-hip.so` = `daf086c2...`.
- BRF EXP-04 r3, arm A1 (`llama-bench`), 2026-11-02. The owner had already judged r3 invalid.

## Runs proven not to have mapped it

- `ufh14-lb51-residual-r1` (2026-10-30, full and cutoff runs): `maps.txt` of a v10 `llama-server` shows only
  `libggml-hip.so.0.16.0` (the listed library), though the stray was on disk then.
  This covers that run, not other `llama-server` runs.

## Bounded unknown

The window is 2026-10-27 23:00 to 2026-11-03 07:38. It holds 93 GPU (mi210) grants that ended, sampled by
path-named artifacts to depth 3:

| Class (by path-named artifacts) | Grants |
|---|---|
| Reference the v10 gpu dir | 6 |
| Reference only other builds (C5/C6 etc.) | 5 |
| No binary evidence either way | **82** |

The two proven-stray runs and the proven-listed-only run above come from run-dir captures; the source analysis
does not map them one-to-one onto these 93 grants. "No evidence" is not "clean". For any run without a `/proc` maps or hash capture, what
the loader mapped cannot be reconstructed after the fact. Possible but unproven: orchestrator production
`:8083` (launched 2026-10-27T23:30:10Z, stopped 23:44:37Z, the only server launch recorded after 23:00 in this
window). By analogy with ufh14 a `llama-server` probably mapped only the listed library; this is not proven.
Binary kind matters: `llama-bench` and test binaries showed the stray, `llama-server` showed it was not mapped
in the one captured case.

## Origin: writer unknown

Searched with no finding: Claude transcripts 10-27 15:00 to 10-28 08:00; fish history (no entries 10-27 18:00
to 10-28 03:00) and bash history (ends 10-27 11:39); every Codex rollout with activity after 10-27 22:00
mentioning `libggml-hip` (only reads, strings and mapping code; none writes into the v10 directory); scripts in
origin/main (no script copies or installs into `kernels/builds`, runbook text aside); library or binary files
written 22:40 to 23:20 on 10-27 under `tmp/worktrees/autokernel` (unrelated fixtures).

Consistent with, but not shown by, the evidence: another build out of `champ2/build-hip*` (the tree held
`build-hip` and `build-hip-mmqoff`, and builds of one commit there are documented as non-deterministic in
libggml-hip). Temporal neighbours only, no causal link found: the `:8083` reload at 23:30 and GPU grants
starting 22:57, 22:58 and 23:31. Not searched: sessions with no transcript on disk, other shells, `champ2`
itself.

**The writer, the method and the exact source build are unknown.**

## Remediation status

The store check now fails on an unlisted regular file, a hash mismatch, a missing `SHA256SUMS`, a regular
`lib*.so` shadowing a versioned sibling, and dangling or non-local symlinks (branch
The custody check in `scripts/session/verify_kernel_store.sh` landed on main on 2026-11-09, with a fixture in `tests/test_verify_kernel_store_custody.py`.
`/workspace` as of the source analysis). Backfilling `SHA256SUMS` for 55 builds is gated on the operator and owners.
