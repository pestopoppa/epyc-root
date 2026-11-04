#!/bin/bash
# =============================================================================
# daemon_source_tree.sh — a daemon PUBLISHES the committed tree it was launched from
# =============================================================================
#
# NIB2-89 (the H-4 generalisation named in NIB2-81's "Remaining" line). H-4 compares
# a watched daemon's own published `source_tree` (captured at ITS start) against
# `git rev-parse HEAD:<pkg>` NOW. This file is the PUBLISHING half for any registered
# daemon: `dp_publish_source_tree` amends the provenance record `dp_attest` wrote
# (daemon_provenance.sh is deliberately NOT edited — hub_supervisor.sh re-sources it
# on every host-cron tick and install_supervision_cron pins it) with a `source_tree`
# key. bus_supervisor.sh's `registry_source_tree_is_stale` is the consuming half,
# reached only by a registry row with `runtime.stale_predicate: "source_tree"`.
#
# DORMANT BY CONSTRUCTION, three independent ways:
#   1. nothing sources this file (the NIB2-89 test asserts it);
#   2. even if sourced and called, it is a NO-OP unless DP_PUBLISH_SOURCE_TREE=1;
#   3. even if published, nothing reads it unless a registry row opts in — none does,
#      and bus_supervisor.sh is operator-held DOWN (ruling 2026-09-23).
#
# Sourced, not executed: defines functions only; every failure is guarded so it can
# never abort the caller's `set -euo pipefail` shell.
# =============================================================================

# dp_publish_source_tree <script_path> <provenance_file> [tree_path]
#
#   tree_path defaults to the script's directory, repo-relative (H-4 uses the
#   package dir the same way: scripts/coordination). Must be called by the daemon
#   itself, AFTER dp_attest, so $$ is the pid the supervisor will resolve.
#   Returns 0 always (a publishing failure means "cannot tell" downstream, which
#   fails closed — it must never stop a daemon from starting).
dp_publish_source_tree() {
  [[ "${DP_PUBLISH_SOURCE_TREE:-0}" == "1" ]] || return 0
  local script="${1:-}" prov="${2:-}" tree_path="${3:-}" real top tree
  [[ -n "$script" && -n "$prov" && -r "$prov" ]] || return 0
  real="$(readlink -f -- "$script" 2>/dev/null || true)"
  [[ -n "$real" ]] || return 0
  top="$(git -C "$(dirname -- "$real")" rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "$top" ]] || return 0
  if [[ -z "$tree_path" ]]; then
    tree_path="$(dirname -- "${real#"$top"/}")"
  fi
  tree="$(git -C "$top" rev-parse --verify -q "HEAD:${tree_path}" 2>/dev/null || true)"
  [[ -n "$tree" ]] || return 0
  python3 - "$prov" "$$" "$tree" "$tree_path" <<'PY_EOF' 2>/dev/null || true
import json, os, sys
path, pid, tree, tree_path = sys.argv[1:5]
try:
    rec = json.load(open(path))
except Exception:
    raise SystemExit(0)
rec["pid"] = int(pid)
rec["source_tree"] = tree
rec["source_tree_path"] = tree_path
tmp = path + ".tmp." + pid
with open(tmp, "w") as f:
    f.write(json.dumps(rec) + "\n")
os.replace(tmp, path)
PY_EOF
  return 0
}
