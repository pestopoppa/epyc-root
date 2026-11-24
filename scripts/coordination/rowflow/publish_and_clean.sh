#!/bin/bash
# Publish a row and clean explicitly named, guarded scratch/worktree targets.
# Usage: publish_and_clean.sh SPEC [--flags DIR] [--smoke-now] [--rerun]
#        [--cleanup-root DIR]... [--cleanup-worktree PATH]...
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
[ "$#" -gt 0 ] || { echo 'usage: publish_and_clean.sh SPEC [--flags DIR] [--smoke-now] [--rerun] [--cleanup-root DIR]... [--cleanup-worktree PATH]...' >&2; exit 2; }
SPEC=$1; shift
FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
PUB_ARGS=(); CLEAN_ARGS=(); TARGETS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --flags) [ "$#" -ge 2 ] || exit 2; FLAGS=$2; shift 2 ;;
    --smoke-now|--rerun) PUB_ARGS+=("$1"); shift ;;
    --cleanup-root|--cleanup-worktree)
      [ "$#" -ge 2 ] || exit 2
      TARGETS+=("$2")
      if [ "$1" = --cleanup-root ]; then CLEAN_ARGS+=(--root "$2"); else CLEAN_ARGS+=(--worktree-glob "$2"); fi
      shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
REPO=${ROWFLOW_REPO:-/mnt/raid0/llm/views/epyc-root-main}
CLEANUP="$REPO/scripts/system/scratch_cleanup.py"
if [ "${#TARGETS[@]}" -gt 0 ] && [ ! -f "$CLEANUP" ]; then
  echo "REFUSED cleanup: $CLEANUP missing" >&2; exit 2
fi
python3 "$HERE/publish_row.py" "$SPEC" --flags "$FLAGS" "${PUB_ARGS[@]}"
[ "${#TARGETS[@]}" -gt 0 ] || exit 0
# Fail closed unless the actual published manifest is available and all targets are disjoint from its live inputs/outputs.
python3 - "$HERE" "$SPEC" "$FLAGS" "${TARGETS[@]}" <<'PY'
import json, os, re, sys
here, spec_path, flags, *targets = sys.argv[1:]
sys.path.insert(0, here)
try:
    import rowflow as rf
    with open(spec_path) as f:
        spec = json.load(f)
    rid = spec.get("id", "")
    if not isinstance(rid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]+", rid):
        raise ValueError("invalid row id")
    dd = os.path.join(flags, "dryrun", rid)
    manifests = []
    for p in (os.path.join(dd, "unpublished.json"), os.path.join(flags, "ready", rid + ".json"),
              os.path.join(dd, "completed-manifest.json")):
        try:
            with open(p) as f:
                candidate = json.load(f)
            if candidate.get("id") == rid:
                manifests.append(candidate)
        except (OSError, ValueError, AttributeError):
            continue
    if not manifests:
        raise ValueError("published manifest unavailable; no cleanup performed")
    protected = [os.path.realpath(flags)]
    for manifest in manifests:
        launcher = (manifest.get("launcher") or {}).get("path")
        if not isinstance(launcher, str) or not os.path.isabs(launcher):
            raise ValueError("published launcher path unavailable")
        paths = [manifest.get("scratch_root"), manifest.get("workdir"), manifest.get("result_path"),
                 manifest.get("stop_file"), launcher, os.path.dirname(launcher), (manifest.get("engine") or {}).get("path")]
        paths.extend(rf.referenced_paths(rf.parse_launcher(launcher)))
        for p in paths:
            if isinstance(p, str) and os.path.isabs(p):
                p = re.split(r"[*?\[]", p, maxsplit=1)[0]
                protected.append(os.path.realpath(p))
    for target in targets:
        if not os.path.isabs(target) or any(c in target for c in "*?["):
            raise ValueError(f"cleanup target must be an absolute literal path: {target!r}")
        real = os.path.realpath(target)
        roots = ("/mnt/raid0/llm/tmp", "/mnt/raid0/llm/worktrees")
        if not any(real != root and os.path.commonpath((root, real)) == root for root in roots):
            raise ValueError(f"cleanup target is outside allowed scratch/worktree roots: {target!r}")
        for live in protected:
            if os.path.commonpath((real, live)) in (real, live):
                raise ValueError(f"cleanup target {target!r} overlaps the published row path {live!r}")
except Exception as e:  # a missing/invalid manifest or launcher must never permit cleanup
    print(f"REFUSED cleanup: {e}", file=sys.stderr)
    sys.exit(2)
PY
# The existing tool applies worktree, live-reference and trash-first guards again immediately before removal.
python3 "$CLEANUP" apply "${CLEAN_ARGS[@]}"
