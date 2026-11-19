# Review: anonymous-inode publication candidate

Candidate patch: `atomic-output-otmpfile-review.patch` (review only; not applied).

## What it closes

The current candidate's named random temporary file is protected against initial name collision with `O_EXCL`, but after the writing fd is closed and before `os.link(temp_name, ...)`, a process with write access to the output directory can unlink and replace that temporary directory entry. The published inode could then be attacker-controlled. Keeping an `O_TMPFILE` descriptor open and linking `/proc/self/fd/<fd>` publishes the descriptor's anonymous inode without any replaceable temporary name. `os.link` remains no-replace and atomic at the destination. Content is fsynced before publication.

## What it cannot close

A writer with directory write permission can unlink or replace the destination immediately after publication; no file-writing scheme can make an adversarially writable directory trustworthy. Use a directory not writable by untrusted principals (or an ownership/permission boundary) for durable evidence integrity.

Directory-entry crash durability cannot be both confirmed and have no post-link uncertainty. `fsync(dirfd)` must occur after the new name exists. If it fails, the link may already be visible but durability is unknown; retrying may hit EEXIST. The candidate omits directory fsync and narrows its success contract to atomic visibility plus fsynced contents, explicitly leaving the directory entry vulnerable to loss on crash. If crash durability is required, keep post-link directory fsync and report a distinct `published_durability_unknown` outcome on its failure; do not present it as an ordinary publication failure.

## Portability / implementation caveats

This is Linux-specific: `O_TMPFILE`, procfs mounted at `/proc`, and filesystem support for linking an unnamed inode are required. Some filesystems/mount options reject this mechanism. It must fail closed, with no named-temp fallback if the threat model specifically requires eliminating replaceable temporary entries. The procfs link operation must be exercised on each supported filesystem; verify descriptor and destination inode identity in a focused test. The exact Python `os.link(..., follow_symlinks=True)` behavior and required kernel/filesystem combinations need validation before adoption.

Also retain the behavior change that any existing destination is refused, including an unrelated regular file. Opening `output.parent` pins the directory for destination operations, while `O_TMPFILE` currently uses its path separately; a path rename/symlink race between those opens could place the anonymous inode on a different filesystem. A production implementation should create the anonymous file relative to the already-open directory fd (where supported) or verify the opened file's device against `fstat(dir_fd)` before linking. Python's `os.open` supports `dir_fd` for a directory-relative basename, but `O_TMPFILE` requires a directory path; Linux `openat(dirfd, ".", O_TMPFILE|...)` via a small wrapper is the robust form. This review patch is therefore a design sketch, not ready-to-apply code.

## Isolated functional check

A standalone Python exercise on the current `/tmp` backing filesystem successfully used `openat(dirfd, ".", O_TMPFILE|...)`, fsynced contents, and linked via `/proc/self/fd/<fd>` while keeping the descriptor open. It published a distinct nested destination and refused existing source path, symlink-to-source, hardlink-to-source, and output path without changing source/output bytes. This validates the mechanism on that one filesystem and runtime only; it is not a test of the target script, all filesystems, or hostile concurrent unlink/replace behavior.

The review patch is explicitly chained after `atomic-output-guard.patch`; it is not a direct-HEAD patch. Source-bound impact and a validated implementation are still required before any downstream application.

The isolated mechanism check was repeated inside `guard15` on the `/mnt/raid0` project filesystem and passed. It still does not test the exact target script.
