# Containment-scanner changes on `refactor/containment-scanner` — OPERATOR REVIEW REQUIRED

This branch changes the guard that enforces the standing directive "do not touch anything outside
/mnt/raid0/llm/" (INC-20260823). It must be reviewed by the operator, not only by a session, before it
lands on main (workspace-58, 2026-10-24). Delete this file when the branch is merged or rejected.

Commits: `hooks: close containment-scanner bypasses …` and `hooks: restore the containment wrapper's
degraded-mode refusals`. Files: `scripts/hooks/filesystem_containment_scan.py`, `scripts/hooks/shell_scan.py`,
`scripts/hooks/check_filesystem_containment.sh`, `scripts/hooks/tests/test_filesystem_containment.py`,
`scripts/hooks/tests/live_holder_interference_cases.json`. `--dump-rules` output is byte-identical, so the
generated opencode configuration does not change. The containment roots and the allowlist are unchanged.

## Newly ALLOWED (refused before)

None of these widens the set of paths a command may write to; each was a mis-parse that refused a write
whose real target is inside a root (or no write at all).

| Form | Before | Now | Why |
|---|---|---|---|
| fd duplication: `cmd 2>&1`, `>&2`, `1>&2`, `>&-` | refused as a write to a FILE named `1`/`2` in the cwd when the cwd was outside the roots (on the host the cwd is usually inside a root, which masked it) | allowed: not a file write | `&N` is a descriptor, not a path. `&>F`, `&>>F`, `>&F` (F not a number or `-`), `>\|F`, `<>F` are still checked as writes to F |
| `git worktree add <path> <branch>` | checked `<branch>` as the target (e.g. refused `git worktree add /workspace/x mybranch` from an out-of-root cwd) | checks `<path>` (first operand after `add`, skipping `-b/-B/--reason` values) | the branch name is not a filesystem target |
| `git clone URL` with no directory, `git init` with no directory | `clone` was refused as unresolvable | checks the cwd it writes into: allowed if the cwd is inside a root, refused otherwise | it writes into the cwd |
| a quoted in-root target, e.g. `cp a "/mnt/raid0/llm/x"` | refused as unresolvable (quotes were not removed) | quote removal is applied; the unquoted path is checked against the roots as usual | `"/x"` IS the path `/x` to bash. A quote glued to other text (`"$D"/x`) is still refused as unresolvable |
| relative targets resolved against the SESSION's cwd (payload `cwd`) | resolved against the hook's own working directory (the project dir) | resolved against the payload's `cwd` | the Bash tool's cwd persists across calls; this also REFUSES `cd /outside && mkdir x` patterns that the old resolution allowed |

## Newly REFUSED (allowed before) — the bypasses this branch closes

- Redirect words counted as operands: `cp secret /outside 2>/dev/null` checked `2>/dev/null`, not `/outside`.
- `git worktree add /outside/x mybranch` from an in-root cwd (it checked `mybranch`).
- Boolean flags parsed as value-taking, swallowing the destination: `rm -r /x`, `rm -f /x`, `rmdir -v /x`,
  `tee -a /x`, `cp a --preserve /x`, `cp a -s /x`, `borg create --stats /x::a`.
- Multi-target writers checked only the last operand: `tee`, `chown`, `chmod`, `install -d`.
- `-t DIR` forms (`-at DIR`, `-tDIR`, `--target=DIR`, `--targ DIR`), values after the destination
  (`cp a /x --suf .bak`), `tar -cf /outside/b.tgz`, `tar -C/x`, `--directory /x`, `borg --repo /x`.
- A lone `&` hid the next command (`sleep 1 & mkdir /x`); `xargs -I{} cp {} /x` lost the `cp`.
- Shell structure the old strip-based reader missed (replaced by a one-pass lexer `lex()` in shell_scan.py):
  line continuations, `\rm`/quoted verbs, `for/if/case/!/exec/function` bodies, `$(...)`, backticks,
  process substitution, `sh -c '…'`/`bash -lc "…"`, heredocs and here-strings fed to a shell, escapes and
  comments that hid separators.
- Relative writes after a `cd` the scanner cannot resolve (`cd $X`, `cd -`); a `cd` inside a subshell no
  longer leaks to later commands.
- Degraded mode (no python3 / no scanner): main since 84b0de13 ALLOWED `sudo mount …`, `apt-get install`,
  `dpkg -i` because the LINT-PIPEFAIL rewrite put `>/dev/null` before a continued pattern line; restored.
- Ambiguous option abbreviations from an out-of-root cwd (`rsync --backup src dst`, `install --strip`).

## Still NOT covered (documented in the scanner docstring)

A verb from a variable or substitution (`$RM -rf x`); text piped into a shell (`echo cmd | sh`);
interpreter code (`python -c`, `perl -i`, awk `system()`), `trap`, `watch`; operands on stdin
(`… | xargs rm`); symlinks created and used within one command; `git -C DIR` for subcommands other than
clone/init/worktree add; `restic restore --target`, `borg extract`, `rclone copyto/moveto/mkdir` (adding
them changes `--dump-rules` and requires regenerating the opencode config). Paths containing spaces are
refused (fail closed).

## Evidence

- `scripts/hooks/tests/test_filesystem_containment.py`: new table-driven classes `TestOperandExtraction`
  and `TestShellStructure` (~190 subtests, both directions, cwd pinned inside and outside the roots) and
  `test_degraded_mode_still_refuses_privileged_verbs`. 78 of the new containment cases fail against the
  pre-branch scanner.
- Full `scripts/hooks/tests` + `tests/hooks`: 313 passed vs 296 at base; the 11 failed / 25 errors are the
  same pre-existing set on both sides (opencode generator drift, provenance and trust-boundary suites).
- 40,000- and 60,000-call fuzz runs of `scan_command`: no exceptions; every pathological input scans in < 1 s.
