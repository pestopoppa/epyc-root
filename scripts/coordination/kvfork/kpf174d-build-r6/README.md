# KPF-17.4d fresh full HIP build prerequisite

Row: `kvu-kpf174-custody-r6-20261119`. This rebuilds prospective source
`6ec877068936588b6d63dbba5842bbd540b92031`, parent
`84d0a31603d495377dee24e1159bbbf02f1e2f21`, after the R5 binaries were reclaimed.
Historical verdicts remain unchanged.

`prepare.py` relocates the retained R5 recipe only after verifying its sealed
runtime list (SHA-256 `4162b7a1e3241ec90b7c884a2d515f8c593c8d2b4a42fa6de0f9bf47505f2e5c`).
It verifies all source/input bytes before publication, refreshes stat inventories,
and creates fresh launcher/runtime pins. Immutable source inputs are referenced
by symlinks; no archive or tree is copied. The detached source worktree is
`/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-build-r6-20261119/source`.

Prepared row spec at the same root: `spec.json`, SHA-256
`227a72130a90b129e7427df4f9abf3b4a1c3a26f3f377c5f7eaf568c52780dc8`.
Launcher SHA-256 `97adf4420f04f7b4001589b6f94250eadddaa35625decfac8a2167165e4c417b`;
runtime-list SHA-256 `1d2377ada7baa3f13f48acace0991fa94907c055ccfd19dc6de641a84ac73633`;
linkage-helper SHA-256 `57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33`.

The 4-CPU publisher smoke compiles the real KV-cache first object and checks its
layout knob and source/options identity. It proves first progress only. The full
CPU allocation builds HIP gfx90a with the reviewed reference options, verifies
own-library linkage and all three knobs, and produces `RESULT.json` plus
`CUSTODY.json`. Completion reopens all eight binary/library attestations and host
compiler digests. Retain the full build for its successor; no model is loaded.

After full build acceptance, pin the new receipt, custody manifest and helper in
the prospective GPU successor, excluding exposed cells g0-S2-B and g1-S2-B.

The first R6 publisher attempt failed before any build: `/usr/bin/chroot` is
absent on this host. The relocated recipe uses `/usr/sbin/chroot` in both the
build job and completion compiler check; runtime/launcher pins above include
that correction. No full-build or inference result is inherited.

Publisher qualification: **SMOKE PASS**, rc0, CPUs 116–119,
2026-11-19T08:09:49Z. Evidence: `/mnt/raid0/llm/tmp/compute-flags/dryrun/kvu-kpf174-custody-r6-20261119/PASS.json`,
SHA-256 `3688912c34357c2b644dcbef6dde9890ec791d3cc91f5cb81d23140570d175f6`.
Full build remains pending.
