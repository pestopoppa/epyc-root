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
GATE="${HUB_VIEW_REGEN_GATE:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../coordination/index_regen.py}"
GATE_FLAGS="${HUB_VIEW_GATE_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}"
GATE_QUIET_S="${HUB_VIEW_GATE_QUIET_S:-180}"
# The ONE quiet-host check (scripts/coordination/quiet_host.py). Heavy regeneration (index_state.py, and
# build_handoff_timeline.py's `git log -M -p` over handoffs/) defers under a live whole-host grant and otherwise
# runs niced; the cheap fetch + checkout above it always runs. Origin: 2026-11-10 23:36Z, AutoKernel
# ak-c10-q38fn-floor-r4-20261110 failed closed on this job's `git log -p -- handoffs/`.
QUIET="${HUB_VIEW_QUIET_HOST:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../coordination/quiet_host.py}"

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

# Report every outcome where the hub can read it (dashboard/server.py, /api/hub_view).
# In the git dir, so it never dirties the view. Best-effort: reporting cannot fail a refresh.
STATUS_F="$(git -C "${VIEW}" rev-parse --path-format=absolute --git-dir)/epyc-view-refresh.json"
report_status() {  # ok(true|false) stage detail regenerated(0|1)
  [[ -n "${PY}" ]] || return 0
  "${PY}" - "${STATUS_F}" "$1" "$2" "$3" "$4" "$(git -C "${VIEW}" rev-parse HEAD 2>/dev/null || true)" \
    <<'PYEOF' 2>/dev/null || true
import json, os, sys, time
path, ok, stage, detail, regen, head = sys.argv[1:7]
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
try:
    prev = json.load(open(path, encoding="utf-8"))
except (OSError, ValueError):
    prev = {}
success = ok == "true"
doc = {"attempted_at": now, "ok": success, "stage": stage, "detail": detail or None, "head": head,
       "last_ok_at": now if success else prev.get("last_ok_at"),
       "last_regen_at": now if regen == "1" else prev.get("last_regen_at")}
tmp = f"{path}.tmp.{os.getpid()}"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(doc, fh)
os.replace(tmp, path)
PYEOF
}

# --- 2. advance -------------------------------------------------------------- #
old="$(git -C "${VIEW}" rev-parse -q --verify HEAD 2>/dev/null || echo none)"
if ! git -C "${VIEW}" fetch --quiet "${REMOTE}" >/dev/null 2>&1; then
  log "fetch ${REMOTE} FAILED in ${VIEW} (offline?) — view left at ${old:0:12}"
  report_status false fetch "git fetch ${REMOTE} failed; view left at ${old:0:12}" 0
  exit 1
fi
# Refresh index stat info first: `checkout --force` rewrites any file whose stat
# no longer matches the index even when its content is identical, which would
# bump dashboard/*.py mtimes (and restart the hub) after a mere `touch`.
git -C "${VIEW}" update-index -q --refresh >/dev/null 2>&1 || true
if ! git -C "${VIEW}" checkout --quiet --detach --force "${REMOTE}/${BRANCH}" >/dev/null 2>&1; then
  log "checkout --detach --force ${REMOTE}/${BRANCH} FAILED in ${VIEW} — view left at ${old:0:12}"
  report_status false checkout "git checkout ${REMOTE}/${BRANCH} failed; view left at ${old:0:12}" 0
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
gated="no"
if [[ "${SKIP_REGEN}" == "1" ]]; then
  regen_reason=""
else
  # TOKEN-REGEN-TRIPLE-DEBOUNCE: a head move alone is not a reason -- every batch
  # commit and the central index-regen commit each moved it, so the view regenerated
  # once per commit. Ask index_regen.py's once-per-batch quiet-window gate on EVERY
  # pass (exit 0 = run, 10 = skip): it holds regeneration inside a batch AND releases
  # it when the batch ends even though the head has stopped moving. A missing gate or
  # any other result falls back to the old head-moved rule (fail open), and the
  # missing/aged artifact checks below always apply.
  grc=99
  if [[ -f "${GATE}" ]]; then
    grc=0
    "${PY:-python3}" "${GATE}" --gate hub-view --worktree "${VIEW}" --flags "${GATE_FLAGS}" \
      --quiet-s "${GATE_QUIET_S}" >/dev/null 2>>"${LOG_FILE:-/dev/stderr}" || grc=$?
  fi
  if [[ "${grc}" == "0" ]]; then
    if [[ "${old}" != "${new}" ]]; then regen_reason="head-moved"; else regen_reason="batch-ended"; fi
  elif [[ "${grc}" == "10" ]]; then
    if [[ "${old}" != "${new}" ]]; then gated="yes"; fi
  elif [[ "${old}" != "${new}" ]]; then
    regen_reason="head-moved"
  fi
  if [[ -z "${regen_reason}" ]]; then
    now="$(date +%s)"
    for f in "${STATE_F}" "${GRAPH_F}" "${TIMELINE_F}"; do
      if [[ ! -f "${f}" ]]; then regen_reason="missing:${f#"${VIEW}"/}"; break; fi
      if (( now - $(stat -c %Y "${f}") > REGEN_MAX_AGE_S )); then
        regen_reason="aged:${f#"${VIEW}"/}"; break
      fi
    done
  fi
fi

rc=0
regen="no"
deferred=0
if [[ -n "${regen_reason}" ]]; then
  regen="yes(${regen_reason})"
  if [[ -z "${PY}" ]]; then
    log "regen SKIPPED: no python3"; rc=1
  else
    # quiet_host.py exec: exit 75 under a live grant (DEFER-QUIET-HOST on stderr -> the log), else nice/ionice.
    # A missing helper fails open to a plain nice -n 19 run.
    qexec() {  # TAG cmd...  (cwd = view)
      local tag="$1"; shift
      if [[ -f "${QUIET}" ]]; then
        "${PY}" "${QUIET}" exec "${tag}" -- "$@"
      else
        nice -n 19 "$@"
      fi
    }
    for step in index_state build_handoff_timeline; do
      if [[ "${step}" == "index_state" ]]; then
        cmd=("${PY}" scripts/handoffs/index_state.py)
      else
        cmd=("${PY}" scripts/handoffs/build_handoff_timeline.py --repo "${VIEW}")
      fi
      src=0
      (cd "${VIEW}" && qexec "hub-view-${step}" "${cmd[@]}" >/dev/null 2>>"${LOG_FILE:-/dev/stderr}") || src=$?
      if [[ "${src}" == "75" ]]; then
        log "DEFER-QUIET-HOST hub-view-${step}: quiet-host grant live; regeneration skipped this pass"
        deferred=1
      elif [[ "${src}" != "0" ]]; then
        log "WARN: ${step} failed in ${VIEW}"; rc=1
      fi
    done
  fi
  # --- 4. keep the view byte-identical to origin/main ----------------------- #
  # index_state.py splices its rollup into the tracked master index. Revert any
  # tracked edit. Only the touched files are rewritten, so dashboard/ mtimes stay.
  # Record the regen against the gate so the next head move is judged since THIS one.
  if [[ "${rc}" == "0" && "${deferred}" == "0" && -f "${GATE}" ]]; then
    "${PY:-python3}" "${GATE}" --gate hub-view --record --worktree "${VIEW}" --flags "${GATE_FLAGS}" \
      >/dev/null 2>>"${LOG_FILE:-/dev/stderr}" || log "WARN: could not record hub-view regen state"
  fi
  git -C "${VIEW}" update-index -q --refresh >/dev/null 2>&1 || true
  if ! git -C "${VIEW}" diff --quiet 2>/dev/null; then
    git -C "${VIEW}" checkout --quiet --detach --force "${new}" >/dev/null 2>&1 \
      || { log "WARN: could not revert generated edits to tracked files"; rc=1; }
  fi
fi

[[ "${gated}" == "yes" ]] && regen="no(gated)"
[[ "${deferred}" == "1" ]] && regen="no(quiet-host-deferred)"
log "refresh view=${VIEW} head=${moved} regen=${regen} rc=${rc}"
if [[ "${rc}" == "0" ]]; then
  regenerated=0; [[ -n "${regen_reason}" && "${deferred}" == "0" ]] && regenerated=1
  report_status true done "" "${regenerated}"
else
  report_status false regen "artifact regeneration failed; see ${LOG_FILE:-stderr}" 0
fi
exit "${rc}"
