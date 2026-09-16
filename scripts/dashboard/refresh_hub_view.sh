#!/bin/bash
# =============================================================================
# refresh_hub_view.sh — advance the read-only hub VIEW checkout to origin/main.
# =============================================================================
#
# WHY (2026-09-16, operator-approved "dashboard fix A"). The :8100 hub reads
# handoffs, the index graph and "today's activity" from the checkout it is
# launched from (dashboard/server.py: REPO = parents[1]). The launch manifest
# pointed that at an AutoKernel lane that sat 141 commits behind origin/main, so
# pushed progress never appeared. The hub now serves a dedicated VIEW: a
# standalone clone (NOT a linked worktree) at /mnt/raid0/llm/views/epyc-root-main,
# detached at origin/main, whose only writer is this script.
#
# WHAT IT DOES, in order:
#   1. refuses unless the view carries the marker file `.epyc-view-readonly`, is a
#      git top-level, and is NOT a linked worktree (a lane is never a view);
#   2. `git fetch origin` + `git checkout --detach --force origin/main`
#      (discarding local edits is the point: nobody may write here);
#   3. regenerates the untracked, gitignored artifacts the hub reads —
#      handoffs/active/.index-state.json + .index-graph.json (index_state.py) and
#      data/handoff_timeline.json (build_handoff_timeline.py) — when HEAD moved,
#      an artifact is missing, or the oldest is older than HUB_VIEW_REGEN_MAX_AGE_S;
#   4. index_state.py also rewrites the TRACKED master index rollup block; that
#      edit is reverted (checkout --force HEAD) so the view stays byte-identical to
#      origin/main and `git status` never shows the view as dirty.
#
# git checkout only rewrites files whose content changed, so dashboard/*.py
# mtimes move only when dashboard code changed. hub_supervisor.sh's stale-source
# check therefore restarts the hub on a dashboard change and NOT on every
# handoff refresh.
#
# Invoked by hub_supervisor.sh (refresh_hub_view, every HUB_VIEW_REFRESH_INTERVAL_S)
# using the supervisor's OWN sibling copy of this script — never the view's copy,
# which this script overwrites while bash may still be reading it.
#
# Usage: refresh_hub_view.sh [VIEW_DIR]     (default $HUB_VIEW_DIR)
# Exit:  0 refreshed (or already current) · 1 fetch/checkout/regen failure
#        3 refused (no marker / not a view)
# Env:   HUB_VIEW_DIR HUB_VIEW_MARKER HUB_VIEW_REMOTE HUB_VIEW_BRANCH
#        HUB_VIEW_REGEN_MAX_AGE_S HUB_VIEW_PYTHON HUB_VIEW_LOG HUB_VIEW_SKIP_REGEN
# =============================================================================
set -euo pipefail

VIEW="${1:-${HUB_VIEW_DIR:-/mnt/raid0/llm/views/epyc-root-main}}"
MARKER="${HUB_VIEW_MARKER:-.epyc-view-readonly}"
REMOTE="${HUB_VIEW_REMOTE:-origin}"
BRANCH="${HUB_VIEW_BRANCH:-main}"
REGEN_MAX_AGE_S="${HUB_VIEW_REGEN_MAX_AGE_S:-3600}"
SKIP_REGEN="${HUB_VIEW_SKIP_REGEN:-0}"
LOG_FILE="${HUB_VIEW_LOG:-}"
PY="${HUB_VIEW_PYTHON:-$(command -v python3 || true)}"

log() {
  local line
  line="$(date '+%Y-%m-%dT%H:%M:%S%z') [hub-view] $*"
  if [[ -n "${LOG_FILE}" ]]; then
    printf '%s\n' "${line}" >>"${LOG_FILE}" 2>/dev/null || printf '%s\n' "${line}" >&2
  else
    printf '%s\n' "${line}" >&2
  fi
}

# --- 1. is this a view? ------------------------------------------------------ #
if [[ ! -d "${VIEW}" ]]; then
  log "REFUSED: view dir ${VIEW} does not exist"; exit 3
fi
VIEW="$(cd "${VIEW}" && pwd -P)"
if [[ ! -f "${VIEW}/${MARKER}" ]]; then
  log "REFUSED: ${VIEW} has no ${MARKER} marker — not a read-only view, will not force-checkout it"
  exit 3
fi
top="$(git -C "${VIEW}" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${top}" || ! "${top}" -ef "${VIEW}" ]]; then
  log "REFUSED: ${VIEW} is not a git top-level (toplevel='${top}')"; exit 3
fi
dirs="$(git -C "${VIEW}" rev-parse --path-format=absolute --git-dir --git-common-dir 2>/dev/null || true)"
if [[ "$(sed -n 1p <<<"${dirs}")" != "$(sed -n 2p <<<"${dirs}")" ]]; then
  log "REFUSED: ${VIEW} is a LINKED worktree (lane-owned); a view must be a standalone clone"
  exit 3
fi

# --- single writer ----------------------------------------------------------- #
LOCK="$(git -C "${VIEW}" rev-parse --path-format=absolute --git-dir)/epyc-view-refresh.lock"
exec 8>"${LOCK}"
if ! flock -n 8; then
  log "another refresh holds ${LOCK}; skipping this pass"
  exit 0
fi

# --- 2. advance -------------------------------------------------------------- #
old="$(git -C "${VIEW}" rev-parse -q --verify HEAD 2>/dev/null || echo none)"
if ! git -C "${VIEW}" fetch --quiet "${REMOTE}" >/dev/null 2>&1; then
  log "fetch ${REMOTE} FAILED in ${VIEW} (offline?) — view left at ${old:0:12}"
  exit 1
fi
# Refresh index stat info first: `checkout --force` rewrites any file whose stat
# no longer matches the index even when its content is identical, which would
# bump dashboard/*.py mtimes (and restart the hub) after a mere `touch`.
git -C "${VIEW}" update-index -q --refresh >/dev/null 2>&1 || true
if ! git -C "${VIEW}" checkout --quiet --detach --force "${REMOTE}/${BRANCH}" >/dev/null 2>&1; then
  log "checkout --detach --force ${REMOTE}/${BRANCH} FAILED in ${VIEW} — view left at ${old:0:12}"
  exit 1
fi
new="$(git -C "${VIEW}" rev-parse HEAD)"
if [[ "${old}" == "${new}" ]]; then
  moved="unchanged"
else
  n="$(git -C "${VIEW}" rev-list --count "${old}..${new}" 2>/dev/null || echo '?')"
  moved="${old:0:12}->${new:0:12} (+${n})"
fi

# --- 3. regenerate the hub's untracked artifacts ----------------------------- #
STATE_F="${VIEW}/handoffs/active/.index-state.json"
GRAPH_F="${VIEW}/handoffs/active/.index-graph.json"
TIMELINE_F="${VIEW}/data/handoff_timeline.json"
regen_reason=""
if [[ "${SKIP_REGEN}" == "1" ]]; then
  regen_reason=""
elif [[ "${old}" != "${new}" ]]; then
  regen_reason="head-moved"
else
  now="$(date +%s)"
  for f in "${STATE_F}" "${GRAPH_F}" "${TIMELINE_F}"; do
    if [[ ! -f "${f}" ]]; then regen_reason="missing:${f#"${VIEW}"/}"; break; fi
    if (( now - $(stat -c %Y "${f}") > REGEN_MAX_AGE_S )); then
      regen_reason="aged:${f#"${VIEW}"/}"; break
    fi
  done
fi

rc=0
regen="no"
if [[ -n "${regen_reason}" ]]; then
  regen="yes(${regen_reason})"
  if [[ -z "${PY}" ]]; then
    log "regen SKIPPED: no python3"; rc=1
  else
    if ! (cd "${VIEW}" && "${PY}" scripts/handoffs/index_state.py >/dev/null 2>>"${LOG_FILE:-/dev/stderr}"); then
      log "WARN: index_state.py failed in ${VIEW}"; rc=1
    fi
    if ! (cd "${VIEW}" && "${PY}" scripts/handoffs/build_handoff_timeline.py --repo "${VIEW}" >/dev/null 2>>"${LOG_FILE:-/dev/stderr}"); then
      log "WARN: build_handoff_timeline.py failed in ${VIEW}"; rc=1
    fi
  fi
  # --- 4. keep the view byte-identical to origin/main ----------------------- #
  # index_state.py splices its rollup into the tracked master index. Revert any
  # tracked edit. Only the touched files are rewritten, so dashboard/ mtimes stay.
  git -C "${VIEW}" update-index -q --refresh >/dev/null 2>&1 || true
  if ! git -C "${VIEW}" diff --quiet 2>/dev/null; then
    git -C "${VIEW}" checkout --quiet --detach --force "${new}" >/dev/null 2>&1 \
      || { log "WARN: could not revert generated edits to tracked files"; rc=1; }
  fi
fi

log "refresh view=${VIEW} head=${moved} regen=${regen} rc=${rc}"
exit "${rc}"
