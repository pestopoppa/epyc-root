#!/bin/bash
set -euo pipefail
# Install the pre-commit wrapper into every owned repo. Idempotent.
#
# WHY THIS EXISTS
# ---------------
# Each repo's .git/hooks/pre-commit announced itself as "Auto-installed by
# epyc-root" — but no installer existed in tracked code in any of the three
# repos. The wrapper was untracked working-tree state, so:
#
#   * a fresh clone had NO pre-commit hook at all, silently;
#   * a fix applied to one wrapper reached only that one checkout;
#   * nothing could review or diff the wrappers, because they were in no repo.
#
# That is how the 2026-08-03 status-propagation defect survived: epyc-root and
# epyc-orchestrator both called their hooks BARE, so the wrapper exited with the
# status of the LAST hook and a failing pii_precommit.sh was discarded by a
# passing hermes_drift_precommit.sh. Reproduced with a real AWS key staged: the
# hook printed "BLOCKED: [secret] AWS secret access key" and the commit landed.
# Every secret pattern was advisory-only in two of three repos.
#
# CONTRACT OF THE GENERATED WRAPPER
#   1. Run ALL shared hooks — never stop at the first failure, or one hook's
#      findings hide another's.
#   2. Accumulate status; exit non-zero if ANY hook failed.
#      Deliberately NOT `|| exit $?`, which short-circuits (see 1).
#   3. Source an optional per-repo extras file if present. Extras use the same
#      `status=1` accumulation. A repo that VERSIONS its extras at
#      scripts/hooks/pre-commit.extras has that tracked file installed over the
#      local one (added 2026-08-04 — `.git/` reaches no clone, so an extras file
#      that exists only there is a one-host artifact, which is the very defect
#      this installer was written to fix for the wrapper). A repo that tracks no
#      extras keeps whatever local extras it has, un-clobbered, as before.
#
# Verified end-to-end by scripts/hooks/tests/test_precommit_wrapper.sh, which
# drives each INSTALLED wrapper against a throwaway repo with a known-bad blob
# and asserts non-zero, and against a clean set and asserts zero (so a wrapper
# cannot pass by always failing).
#
# Usage:  bash scripts/hooks/install_git_hooks.sh [--check | --emit-commit-msg | --emit-pre-push]
#         --check            verify without writing; non-zero if any repo is wrong.
#         --emit-commit-msg  print the generated commit-msg wrapper and exit (tests).
#         --emit-pre-push    print the generated pre-push wrapper and exit (tests).
#
# COMMIT-MSG: D9 JUDGED AT THE COMMIT (2026-11-02, LOOP-46)
# ---------------------------------------------------------
# A repo that tracks scripts/hooks/check_d9_loop_plane.py (epyc-root) also gets a
# generated commit-msg wrapper that runs that checker in git-hook mode. Inside the
# commit, git has already set GIT_INDEX_FILE to the exact index being recorded (a
# pathspec commit's temporary index, a private index, a lane worktree's own index),
# so D9 judges the commit's own paths and message instead of guessing from command
# text and the shared clone's dirty tree. Repos without the checker get no
# commit-msg wrapper, and an existing one there is left alone.
#
# The same wrapper also runs check_instruction_surface_ratified.py (AUD-15, operator
# decision 2026-11-02): a commit touching CLAUDE.md/AGENTS.md,
# agents/AGENT_INSTRUCTIONS.md or agents/shared/*.md needs an `Operator-Ratified: yes`
# trailer. Both judges run; the status accumulates.
#
# PRE-PUSH: PUSH SERIALIZATION GUARD (operator decision 2026-11-02, decision tool)
# ------------------------------------------------------------------------------
# Every repo gets a generated pre-push wrapper that runs
# scripts/hooks/pre_push_serialization_guard.sh (a push of main/master that does not
# hold the serialized_push.py lock is refused; lane branches, tags and no-op pushes
# pass) and then git-lfs's own pre-push, which is what these repos' pre-push held
# before. Until 2026-11-02 the guard was wired into /workspace only, by a hand-written
# .git/hooks/pre-push that no clone and no review could see; the sibling repos had
# none. The guard resolves the same way as the wrappers above (EPYC_HOOK_SRC_DIR,
# committing worktree, primary tree, /workspace). It is ADVISORY by construction:
# `--no-verify` skips it; only a server-side pre-receive would be structural.
#
# WORKTREE CORRECTNESS (2026-08-12, guard-universe-and-worktree-isolation P1/3a)
# ------------------------------------------------------------------------------
# `.git/hooks/` is SHARED across a repo and every one of its worktrees — a
# worktree's `.git` is a file pointing at the common store, and
# `git rev-parse --git-path hooks` from inside one resolves to the SAME
# `/workspace/.git/hooks` every other worktree uses (verified: run it from
# /workspace/worktrees/mainA). So there is exactly one emitted pre-commit
# file, shared by every worktree, and it must work out AT RUNTIME which
# worktree is committing — it cannot know that at generation time.
#
# The emitted wrapper therefore no longer has HOOK_SRC_DIR baked in as a
# generation-time literal (the old body interpolated the installer's own
# ${HOOK_SRC_DIR} into the heredoc, so every installed wrapper — in every
# repo, from every worktree — carried the SAME literal "/workspace/scripts/
# hooks" regardless of who was committing). It now resolves its own
# HOOK_SRC_DIR each time it runs via `git rev-parse --show-toplevel` — the
# committing worktree's own root — falling back to the git-common-dir's
# primary tree when that worktree has no scripts/hooks of its own (a sparse
# worktree checkout). This mirrors scripts/handoffs/install_timeline_hook.sh,
# whose post-commit/post-merge/post-checkout hooks already resolve their repo
# root the same way (`git -C "$(dirname "$0")" rev-parse --show-toplevel`)
# rather than baking in a path at install time.

REPOS=(
  "/workspace"
  "/mnt/raid0/llm/epyc-orchestrator"
  "/mnt/raid0/llm/epyc-inference-research"
  # SEC-SECRETS-1 (2026-10-21): the public-facing site repo had NO pre-commit hook at all (its .git/hooks held only
  # samples), so a token committed there was never scanned. Like the sibling repos it carries no hook sources of
  # its own: the wrapper resolves to the primary /workspace/scripts/hooks via tier 4.
  "/mnt/raid0/llm/epyc-web"
)

CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

emit_wrapper() {
  # Fully-quoted heredoc delimiter ('WRAPPER'): nothing in this body is
  # expanded at generation time — HOOK_SRC_DIR is resolved by the emitted
  # script itself, at hook-execution time, not baked in here. That is the
  # whole worktree-correctness fix; see the header comment above.
  cat <<'WRAPPER'
#!/bin/bash
# GENERATED by epyc-root scripts/hooks/install_git_hooks.sh — do not hand-edit.
# Repo-specific checks belong in .git/hooks/pre-commit.extras (sourced below).
# Version them at <repo>/scripts/hooks/pre-commit.extras: the installer copies a
# tracked source over this file, and a hand-written .git/hooks/pre-commit.extras
# reaches no clone. Repos that track no extras keep their local file untouched.
#
# STATUS PROPAGATION IS LOAD-BEARING. Run every hook, accumulate, fail if any
# failed. Do NOT revert to bare calls (status silently discarded) and do NOT use
# `|| exit $?` (stops at the first failure, hiding the rest).
#
# HOOK_SRC_DIR IS RESOLVED HERE, AT RUNTIME — never baked in at install time,
# tried in order, first real match wins:
#
#   1. EPYC_HOOK_SRC_DIR override, for tests only (mirrors EPYC_BUS_ROOT in
#      scripts/coordination/session_bus.py::get_bus_root). Production commits
#      never set it. It exists because a test driving this installed file
#      end-to-end (scripts/hooks/tests/test_precommit_wrapper.sh) does so
#      from a throwaway sandbox repo with no relationship to any real
#      checkout, where git-plumbing resolution has nothing correct to find;
#      the override lets that test supply the real scripts/hooks dir.
#   2. The COMMITTING worktree's own scripts/hooks/, if it actually has the
#      hook scripts checked out. .git/hooks/ is shared by every worktree of a
#      repo, so this exact file runs for a commit made in ANY of them — this
#      is the fix: ask git which worktree is committing right now and prefer
#      ITS checkout (so a worktree testing a hook change sees its own edit).
#   3. The git-common-dir's primary tree (the canonical checkout every
#      worktree's .git file points back to) — covers a sparse worktree that
#      omitted scripts/.
#   4. Literal /workspace/scripts/hooks, last resort. This is NOT the old bug
#      reintroduced: the old wrapper used this path UNCONDITIONALLY, baked in
#      at generation time, for every repo and every worktree. This is reached
#      only when tiers 2-3 found no real checkout of the scripts — which is
#      the case, BY DESIGN, for the sibling repos (epyc-orchestrator,
#      epyc-inference-research): they have never carried their own copy of
#      these shared governance hooks and have no git-worktree relationship to
#      epyc-root through which to discover its location, so there is no
#      git-plumbing answer to fall back to. Verified empirically 2026-08-12:
#      neither repo has scripts/hooks/pii_precommit.sh on disk.
if [[ -n "${EPYC_HOOK_SRC_DIR:-}" ]]; then
    HOOK_SRC_DIR="$EPYC_HOOK_SRC_DIR"
else
    HOOK_SRC_DIR=""
    repo="$(git rev-parse --show-toplevel 2>/dev/null)"
    if [[ -n "$repo" && -f "${repo}/scripts/hooks/pii_precommit.sh" ]]; then
        HOOK_SRC_DIR="${repo}/scripts/hooks"
    fi
    if [[ -z "$HOOK_SRC_DIR" ]]; then
        common="$(git rev-parse --git-common-dir 2>/dev/null)"
        case "$common" in
            /*) : ;;                          # already absolute
            "") ;;                            # unresolvable — leave empty
            *)  common="${repo}/${common}" ;; # relative to the worktree root
        esac
        if [[ -n "$common" ]]; then
            primary="$(dirname "$common")"
            if [[ -f "${primary}/scripts/hooks/pii_precommit.sh" ]]; then
                HOOK_SRC_DIR="${primary}/scripts/hooks"
            fi
        fi
    fi
    if [[ -z "$HOOK_SRC_DIR" ]]; then
        HOOK_SRC_DIR="/workspace/scripts/hooks"
    fi
fi

status=0
"${HOOK_SRC_DIR}/pii_precommit.sh" "$@" || status=1
"${HOOK_SRC_DIR}/hermes_drift_precommit.sh" "$@" || status=1

# Per-repo extras. Must accumulate into $status, not exit directly.
if [[ -r "$(dirname "$0")/pre-commit.extras" ]]; then
    # shellcheck disable=SC1091
    source "$(dirname "$0")/pre-commit.extras"
fi

exit "$status"
WRAPPER
}

emit_commit_msg() {
  # Quoted delimiter: resolved at hook-execution time, exactly like the pre-commit
  # wrapper above, because .git/hooks/ is shared by every worktree of the repo.
  cat <<'WRAPPER'
#!/bin/bash
# GENERATED by epyc-root scripts/hooks/install_git_hooks.sh — do not hand-edit.
# Commit-time judges, each reading the exact index being committed (git sets
# GIT_INDEX_FILE before it runs this hook), never the shared clone's working tree:
#   1. D9 loop plane (LOOP-46, 2026-11-02): check_d9_loop_plane.py --git-hook
#   2. instruction surfaces (AUD-15, 2026-11-02): check_instruction_surface_ratified.py
# Both run and the status accumulates, so one refusal cannot hide the other.
#
# Checker resolution, first CAPABLE match wins (an older checkout may lack a checker
# or carry a D9 checker without git-hook mode; it is skipped, not trusted):
#   1. EPYC_HOOK_SRC_DIR (tests only)
#   2. the committing worktree's scripts/hooks/
#   3. the git-common-dir's primary tree
#   4. /workspace/scripts/hooks
_d9_capable() { [[ -f "$1/check_d9_loop_plane.py" ]] && grep -q 'def git_hook_main' "$1/check_d9_loop_plane.py" 2>/dev/null; }
_surface_capable() { [[ -f "$1/check_instruction_surface_ratified.py" ]]; }
_candidates=()
if [[ -n "${EPYC_HOOK_SRC_DIR:-}" ]]; then
    _candidates=("$EPYC_HOOK_SRC_DIR")
else
    _repo="$(git rev-parse --show-toplevel 2>/dev/null)"
    _common="$(git rev-parse --git-common-dir 2>/dev/null)"
    case "$_common" in
        /*) : ;;
        "") ;;
        *)  _common="${_repo}/${_common}" ;;
    esac
    _candidates=("${_repo:+${_repo}/scripts/hooks}" "${_common:+$(dirname "$_common")/scripts/hooks}" "/workspace/scripts/hooks")
fi
_d9_dir=""
_surface_dir=""
for _cand in "${_candidates[@]}"; do
    [[ -n "$_cand" ]] || continue
    if [[ -z "$_d9_dir" ]] && _d9_capable "$_cand"; then _d9_dir="$_cand"; fi
    if [[ -z "$_surface_dir" ]] && _surface_capable "$_cand"; then _surface_dir="$_cand"; fi
done

status=0
if [[ -n "$_d9_dir" ]]; then
    python3 "${_d9_dir}/check_d9_loop_plane.py" --git-hook commit-msg "$1" || status=1
else
    # Transitional only: no checkout on this host has git-hook mode yet, so the
    # older PreToolUse check (which does not step aside then) still guards.
    echo "D9 commit-msg: no checker with git-hook mode found; commit-time D9 skipped" >&2
fi
if [[ -n "$_surface_dir" ]]; then
    python3 "${_surface_dir}/check_instruction_surface_ratified.py" --git-hook commit-msg "$1" || status=1
else
    echo "AUD-15 commit-msg: no instruction-surface checker found; commit-time gate skipped" >&2
fi
exit "$status"
WRAPPER
}

emit_pre_push() {
  cat <<'WRAPPER'
#!/bin/bash
# GENERATED by epyc-root scripts/hooks/install_git_hooks.sh — do not hand-edit.
# pre-push, in order, stdin (the ref-update lines) captured once and fed to each:
#   1. push serialization guard (operator decision 2026-11-02): a push of a protected
#      ref (main/master) that does not hold the serialized_push.py lock is refused.
#   2. git-lfs pre-push, the hook these repos carried before.
# Guard resolution, first real match wins: EPYC_HOOK_SRC_DIR (tests only), the pushing
# worktree's scripts/hooks/, the git-common-dir's primary tree, /workspace/scripts/hooks.
input="$(cat)"
_guard=""
if [[ -n "${EPYC_HOOK_SRC_DIR:-}" ]]; then
    _cands=("$EPYC_HOOK_SRC_DIR")
else
    _repo="$(git rev-parse --show-toplevel 2>/dev/null)"
    _common="$(git rev-parse --git-common-dir 2>/dev/null)"
    case "$_common" in
        /*) : ;;
        "") ;;
        *)  _common="${_repo}/${_common}" ;;
    esac
    _cands=("${_repo:+${_repo}/scripts/hooks}" "${_common:+$(dirname "$_common")/scripts/hooks}" "/workspace/scripts/hooks")
fi
for _c in "${_cands[@]}"; do
    if [[ -n "$_c" && -f "${_c}/pre_push_serialization_guard.sh" ]]; then
        _guard="${_c}/pre_push_serialization_guard.sh"
        break
    fi
done
if [[ -z "$_guard" ]]; then
    echo "PUSH REFUSED — pre-push serialization guard: the guard script was not found in ${_cands[*]}" >&2
    echo "Refusing rather than publishing unguarded. Emergency: git push --no-verify, and say so." >&2
    exit 1
fi
printf '%s\n' "$input" | bash "$_guard" "$@" || exit $?

if command -v git-lfs >/dev/null 2>&1; then
    printf '%s\n' "$input" | git lfs pre-push "$@" || exit $?
elif [[ -f "$(git rev-parse --show-toplevel 2>/dev/null)/.gitattributes" ]] &&
     grep -s 'filter=lfs' "$(git rev-parse --show-toplevel)/.gitattributes" >/dev/null; then
    printf >&2 "\n%s\n\n" "This repository tracks Git LFS files but 'git-lfs' was not found on your path."
    exit 2
fi
exit 0
WRAPPER
}

if [[ "${1:-}" == "--emit-pre-push" ]]; then
  emit_pre_push
  exit 0
fi

if [[ "${1:-}" == "--emit-commit-msg" ]]; then
  emit_commit_msg
  exit 0
fi

rc=0
for repo in "${REPOS[@]}"; do
  hook="${repo}/.git/hooks/pre-commit"
  if [[ ! -d "${repo}/.git" ]]; then
    # A worktree has .git as a FILE; resolve it rather than skipping silently.
    if [[ -f "${repo}/.git" ]]; then
      gitdir="$(git -C "$repo" rev-parse --git-common-dir 2>/dev/null || true)"
      [[ -n "$gitdir" ]] && hook="${gitdir}/hooks/pre-commit"
    else
      echo "  SKIP ${repo} — not a git repo"
      continue
    fi
  fi

  desired="$(emit_wrapper)"
  if [[ -f "$hook" ]] && [[ "$(cat "$hook")" == "$desired" ]]; then
    echo "  ok   ${repo}"
  elif (( CHECK_ONLY )); then
    echo "  WRONG ${repo} — wrapper differs from the generated contract"
    rc=1
  else
    mkdir -p "$(dirname "$hook")"
    if [[ -f "$hook" ]]; then
      cp "$hook" "${hook}.bak-$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    fi
    printf '%s\n' "$desired" > "$hook"
    chmod +x "$hook"
    echo "  installed ${repo}"
  fi

  # -- commit-msg: D9 at the commit (LOOP-46) --------------------------------
  # Only where the repo tracks the checker. Anything else keeps its own commit-msg.
  if [[ -f "${repo}/scripts/hooks/check_d9_loop_plane.py" ]]; then
    cm_hook="$(dirname "$hook")/commit-msg"
    cm_desired="$(emit_commit_msg)"
    if [[ -f "$cm_hook" ]] && [[ "$(cat "$cm_hook")" == "$cm_desired" ]]; then
      echo "  ok   ${repo} — commit-msg"
    elif (( CHECK_ONLY )); then
      echo "  WRONG ${repo} — commit-msg differs from the generated contract"
      rc=1
    else
      if [[ -f "$cm_hook" ]]; then
        cp "$cm_hook" "${cm_hook}.bak-$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"
      fi
      # Write-then-rename: a commit in another session may be running this hook now.
      printf '%s\n' "$cm_desired" > "${cm_hook}.tmp.$$"
      chmod +x "${cm_hook}.tmp.$$"
      mv -f "${cm_hook}.tmp.$$" "$cm_hook"
      echo "  installed ${repo} commit-msg"
    fi
  fi

  # -- pre-push: push serialization guard (operator 2026-11-02) ---------------
  pp_hook="$(dirname "$hook")/pre-push"
  pp_desired="$(emit_pre_push)"
  if [[ -f "$pp_hook" ]] && [[ "$(cat "$pp_hook")" == "$pp_desired" ]]; then
    echo "  ok   ${repo} — pre-push"
  elif (( CHECK_ONLY )); then
    echo "  WRONG ${repo} — pre-push differs from the generated contract"
    rc=1
  else
    if [[ -f "$pp_hook" ]]; then
      cp "$pp_hook" "${pp_hook}.bak-$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    fi
    # Write-then-rename: a push in another session may be running this hook now.
    printf '%s\n' "$pp_desired" > "${pp_hook}.tmp.$$"
    chmod +x "${pp_hook}.tmp.$$"
    mv -f "${pp_hook}.tmp.$$" "$pp_hook"
    echo "  installed ${repo} pre-push"
  fi

  # -- per-repo extras -------------------------------------------------------
  # Added 2026-08-04. A repo may VERSION its extras at scripts/hooks/pre-commit.extras;
  # if it does, that tracked file is the source of truth and is installed to
  # .git/hooks/pre-commit.extras, where the wrapper sources it.
  #
  # WHY. `.git/` is versioned by nothing. epyc-inference-research's evidence-durability
  # extras was hand-written straight into `.git/hooks/` on 2026-08-03: it worked on that
  # one host, no clone ever received it, and no review ever saw it — the same defect this
  # installer exists to fix for the wrapper (which announced "Auto-installed by epyc-root"
  # while no installer existed in tracked code), reintroduced one layer down.
  #
  # The no-clobber promise in the wrapper's header is NARROWED, not broken: a repo that
  # does not track an extras file still keeps whatever local extras it has, untouched.
  # Opting in by committing the file is what makes it managed. A local-only extras that
  # a repo later decides to version is meant to be replaced by the versioned copy —
  # otherwise the tracked file is decorative and the host stays the real policy.
  src_extras="${repo}/scripts/hooks/pre-commit.extras"
  dst_extras="$(dirname "$hook")/pre-commit.extras"
  [[ -f "$src_extras" ]] || continue

  if [[ -f "$dst_extras" ]] && cmp -s "$src_extras" "$dst_extras"; then
    echo "  ok   ${repo} — extras match the tracked source"
  elif (( CHECK_ONLY )); then
    echo "  WRONG ${repo} — .git/hooks/pre-commit.extras differs from ${src_extras#"$repo"/}"
    rc=1
  else
    if [[ -f "$dst_extras" ]]; then
      cp "$dst_extras" "${dst_extras}.bak-$(git -C "$repo" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    fi
    # Write-then-rename: a commit in another session may be sourcing this file right
    # now, and rename is atomic on the same filesystem while `>` is not.
    cp "$src_extras" "${dst_extras}.tmp.$$"
    mv -f "${dst_extras}.tmp.$$" "$dst_extras"
    echo "  installed ${repo} extras"
  fi
done

exit "$rc"
