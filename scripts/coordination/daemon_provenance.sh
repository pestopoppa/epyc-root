#!/bin/bash
# =============================================================================
# daemon_provenance.sh — startup self-attestation for long-running daemons
# =============================================================================
#
# WHY (NIB2-81, tmp/daemon-staleness-20260917/report.md). bash opens a script's
# inode once at launch and reads it incrementally for the process's whole life.
# git never writes a tracked file in place — checkout/reset/merge unlink and
# recreate it — so every commit to a tracked script leaves any daemon that had
# already started on an ORPHANED inode, silently. Three shapes were observed
# live on this host on 2026-09-17: (1) a lane-launched daemon holding a stale,
# diverged lane copy (the reaper, 461 iterations on pre-fix code); (2) two
# supervisors holding `(deleted)` inodes, content-identical that day but one
# commit away from silent divergence; (3) an orphaned-tree daemon whose whole
# checkout was gone.
#
# THIS FILE closes remedy (a) from that report: a cheap STARTUP check — not
# the generalised H-4 supervision loop, which is remedy (b) (a registry
# `runtime:` field + `observer_census.py --live`, tracked separately under
# NIB2-81 in handoffs/active/non-inference-backlog.md, out of scope here).
# "A lane may develop a daemon, never run it": `dp_attest` REFUSES to start a
# daemon whose own script does not resolve under the canonical root, and any
# daemon that calls it can additionally poll `dp_stale_since_start` once per
# loop iteration to LOG — never act; no self-re-exec here — that a commit has
# since replaced the file it is executing.
#
# RELATIONSHIP TO H-4 (bus_supervisor.sh, 2026-08-12, `daemon_source_is_stale`).
# H-4 compares a WATCHED daemon's own published `source_tree` (captured at ITS
# start) against `git rev-parse HEAD:<pkg>` NOW, from a separate supervision
# loop that can act (restart the watched daemon). This file is the same idea
# turned on its own author: a daemon attests ITSELF at its own start, with no
# external supervisor required and no restart capability — it can only refuse
# to start, warn, and log. The two are complementary: H-4 catches drift in a
# daemon it watches even if that daemon never attests itself; dp_attest catches
# drift (and, at step 1, a lane launch outright) in a daemon that has no
# external watcher at all — which describes the reaper, and describes the
# hub/bus supervisors themselves (nothing watches the watchers' own inode).
#
# Sourced, not executed: `set -euo pipefail` compatible — defines functions
# only, touches nothing at source time, and every internal failure is guarded
# with `|| true` / `|| return N` so a failing command substitution can never
# abort the CALLER's shell out from under it.
# =============================================================================

# ---------------------------------------------------------------- canonical roots
#
# Two spellings are the SAME inode tree — see scripts/lib/env.sh's B1 note:
# `/workspace` is a bind-mount alias of `/mnt/raid0/llm/epyc-root`. Root A is
# the literal spelling; root B is its realpath. DP_CANONICAL_ROOT overrides
# BOTH, for TESTS ONLY (mirrors the EPYC_BUS_ROOT override convention in
# bus_supervisor.sh) — production code must never set it.
dp_canonical_root_a() { printf '%s\n' "${DP_CANONICAL_ROOT:-/workspace}"; }
dp_canonical_root_b() {
  local a
  a="$(dp_canonical_root_a)"
  readlink -f -- "$a" 2>/dev/null || printf '%s\n' "${DP_CANONICAL_ROOT:-/mnt/raid0/llm/epyc-root}"
}

# Root C is the read-only VIEW of main that the hub already serves from
# (hub_supervisor.sh refresh_hub_view): a git worktree tracking origin/main, so
# it is canon too. DP_VIEW_ROOT overrides it, for TESTS ONLY.
dp_view_root() { printf '%s\n' "${DP_VIEW_ROOT:-/mnt/raid0/llm/views/epyc-root-main}"; }

# Which accepted root (canon A/B or the view) contains the already-realpath-
# resolved $1 — that is the git root step 2 needs. Non-zero when none does.
_dp_matching_root() {
  local p="$1" r
  for r in "$(dp_canonical_root_a)" "$(dp_canonical_root_b)" "$(dp_view_root)"; do
    if [[ -n "$r" && ( "$p" == "$r" || "$p" == "$r"/* ) ]]; then printf '%s\n' "$r"; return 0; fi
  done
  return 1
}

_dp_under_canonical_root() { _dp_matching_root "$1" >/dev/null; }

dp_log() { printf '%s [daemon_provenance] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }

# ---------------------------------------------------------------------- dp_attest
#
# dp_attest <script_path> [provenance_file]
#
#   1. Resolve the script's real path. Not under a canonical root => REFUSE
#      (return 3) with a one-line explanation naming the canonical root to
#      launch from. "A lane may develop a daemon, never run it."
#   2. Compare the running script's content to the committed blob at HEAD.
#      Mismatch (an uncommitted local edit) => loud WARNING, never a refusal —
#      a hotfix on canon is legitimate.
#   3. If a provenance_file is given, record
#      {pid, script_realpath, inode, blob, started_at} to it as one JSON line,
#      for dp_stale_since_start to compare against later.
#
# Returns 0 on a successful (possibly warned) attestation, 3 on refusal.
dp_attest() {
  local script="${1:?dp_attest: script_path required}"
  local prov_file="${2:-}"
  local real inode git_root relpath head_blob local_blob started_at lane_root guess

  real="$(readlink -f -- "$script" 2>/dev/null || true)"
  if [[ -z "$real" || ! -e "$real" ]]; then
    dp_log "REFUSING: cannot resolve a real path for '$script' — nothing to attest."
    return 3
  fi

  if ! _dp_under_canonical_root "$real"; then
    # Best-effort: name a concrete canonical launch path by re-rooting the
    # script's path relative to ITS OWN repo toplevel (the lane) onto
    # canonical root B. Falls back to the bare filename if that fails —
    # naming the canonical ROOT is the load-bearing part, the exact suffix
    # is a convenience.
    lane_root="$(cd "$(dirname -- "$real")" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || true)"
    if [[ -n "$lane_root" && "$real" == "$lane_root"/* ]]; then
      guess="${real#"$lane_root"/}"
    else
      guess="$(basename -- "$real")"
    fi
    dp_log "REFUSING to start: '$real' is not under the canonical root ($(dp_canonical_root_a) or $(dp_canonical_root_b)) or the view ($(dp_view_root)) — a lane may develop a daemon, never run it. Launch from $(dp_canonical_root_b)/${guess} instead."
    return 3
  fi

  git_root="$(_dp_matching_root "$real")"
  relpath="${real#"$git_root"/}"
  inode="$(stat -c %i -- "$real" 2>/dev/null || true)"
  local_blob="$(git hash-object -- "$real" 2>/dev/null || true)"
  head_blob="$(git -C "$git_root" rev-parse "HEAD:${relpath}" 2>/dev/null || true)"

  if [[ -n "$head_blob" && -n "$local_blob" && "$head_blob" != "$local_blob" ]]; then
    dp_log "WARNING: '$relpath' differs from its committed blob at HEAD — running UNCOMMITTED local edits (running blob ${local_blob}, HEAD blob ${head_blob}). This is allowed (a hotfix on canon is legitimate); not refusing."
  fi

  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  if [[ -n "$prov_file" ]]; then
    mkdir -p -- "$(dirname -- "$prov_file")" 2>/dev/null || true
    python3 - "$prov_file" "$$" "$real" "${inode:-}" "${local_blob:-}" "$started_at" <<'PY_EOF' 2>/dev/null || \
      dp_log "WARNING: could not write provenance to $prov_file (continuing)"
import json, sys
path, pid, real, inode, blob, started_at = sys.argv[1:7]
rec = {
    "pid": int(pid),
    "script_realpath": real,
    "inode": (int(inode) if inode else None),
    "blob": (blob or None),
    "started_at": started_at,
}
with open(path, "w") as f:
    f.write(json.dumps(rec) + "\n")
PY_EOF
  fi
  return 0
}

# --------------------------------------------------------- dp_stale_since_start
#
# dp_stale_since_start <script_path> <provenance_file>
#
# Cheap per-iteration check: has the inode AT THE SCRIPT'S PATH changed since
# dp_attest recorded it? A changed inode means a commit (or any rewrite-by-
# rename, which is how git always writes) landed on that path — the running
# process still holds its OLD inode open and is now executing stale code.
#
#   0 = STALE (on-disk inode differs from the one recorded at attest time).
#   1 = unchanged.
#   2 = cannot tell (missing/unreadable provenance, or the path no longer
#       stats) — FAIL CLOSED to unknown, never claimed stale, mirroring H-4's
#       daemon_source_is_stale() in bus_supervisor.sh.
dp_stale_since_start() {
  local script="${1:?dp_stale_since_start: script_path required}"
  local prov_file="${2:?dp_stale_since_start: provenance_file required}"
  local real recorded_inode current_inode

  [[ -r "$prov_file" ]] || return 2
  recorded_inode="$(python3 - "$prov_file" <<'PY_EOF' 2>/dev/null || true
import json, sys
try:
    v = json.load(open(sys.argv[1])).get("inode")
    if isinstance(v, int):
        print(v)
except Exception:
    pass
PY_EOF
)"
  [[ -n "$recorded_inode" ]] || return 2

  real="$(readlink -f -- "$script" 2>/dev/null || true)"
  [[ -n "$real" ]] || return 2
  current_inode="$(stat -c %i -- "$real" 2>/dev/null || true)"
  [[ -n "$current_inode" ]] || return 2

  [[ "$current_inode" != "$recorded_inode" ]]
}
