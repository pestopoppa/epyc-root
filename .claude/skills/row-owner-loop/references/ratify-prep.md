# Ratify-bundle preparation

The operator signs; everything up to the signature is ours. Origin: three bundles signed 2026-11-19
(Fable review 21:25Z–21:39Z cut a 46-file ratchet to a 37-file subset, 6 trims, 3 decisions).

1. **Write the script** in a lane worktree from `origin/main`; it touches only the protected paths it
   names and refuses if a protected file moved since it was pinned (re-pin, never force).
2. **Apply-test it** on a throwaway worktree through the REAL hooks (pre-commit, human-only path
   guards): run it exactly as the operator will, confirm the commit it produces, then discard the
   throwaway worktree with plain `git worktree remove`. A dry-run is not an apply-test.
3. **One single-line command.** Bundle every pending signature into ONE line the operator pastes.
   It must be fish-safe (the operator's login shell is fish): no `$(...)`, no `&&`-less here-docs,
   no bash-only `[[ ]]`, quote every argument; prefer `python3 /abs/path/ratify_x.py --apply`.
4. **Independent review before handing it over.** A read-only Fable (or opus/high) reviewer gets the
   script and the diff, not your conclusion, and answers sign / trim / decide per file.
   Apply its trims; route its "decide" items as one AskUserQuestion package.
5. **Hand over** with: the command, what it changes (file list), what the review changed.
6. **After the signature lands:** verify the commit on origin/main, tick the box with the commit,
   add the register row if it is a decision (`cli.py conclusion add --kind decision`).

Never create files under `compute-flags/operator-ratify/` yourself, and never apply for real.
