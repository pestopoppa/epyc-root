# Disk is a bin

`/mnt/raid0` holds every output root, every worktree and the trash. One row that fills it breaks
every other row's writes (ENOSPC), so disk is admitted the same way RAM is.

- **Admission.** Each row declares `est_output_GiB` and `scratch_root`. Admit the row only if the
  free space on `/mnt/raid0` (`df --output=avail`) minus `est_output_GiB` stays above the floor.
  The standing floor is **150 GiB**. On 10-27 an interim floor of **50 GiB** applied while space
  was reclaimed.
- **The trash frees nothing until it is swept.** `/mnt/raid0/llm/.trash` is on the same filesystem,
  so moving files with `guarded_rm.sh` reclaims zero bytes. The calendar owner schedules
  `scripts/safety/trash-sweep.sh --older-than 1` daily, and every per-task wrap-up runs it
  (wrap-up Step 7b).
- **Profiling rows are heavy.** rocprof writes about 7 GB per run. After the result is accepted,
  compress the raw output with `xz`, check that the sha256 of the decompressed stream matches the
  original, and only then remove the original. `est_output_GiB` is the raw size, not the
  compressed size.
- **Scratch is cleaned only if it was declared.** Wrap-up cleans declared `**Scratch**` roots
  only, and on 10-27 137 handoffs declared none. A new row's `scratch_root` must also appear in
  the owning handoff's `**Scratch**:` header.

Origin: raid0 reached 100 % on 10-27 (98 GB of unswept trash plus about 45 GB of HSF raw rocprof
output), and an ORCH run died with ENOSPC.
