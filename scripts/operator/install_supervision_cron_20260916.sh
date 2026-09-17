#!/bin/bash
# OP-9 + FW-3 (operator-approved 2026-09-16): host crontab that keeps the in-container
# hub supervisor and fleet_watch alive. Run ON THE HOST (not inside the devcontainer):
# the container has no cron and its own /tmp.
#
#   --fleet-watch-only   install only the fleet_watch line (safe now: fleet_watch.sh
#                        takes a single-instance flock, so repeated launches exit)
#   --all                install both lines. The hub line runs a PINNED copy of
#                        hub_supervisor.sh (OP-9 option B, operator 2026-09-17; see below)
#   --pin-sha SHA        pin this commit instead of origin/main (it must contain the files)
#   --dry-run            show the pin and the resulting crontab, and change nothing
#                        (no fetch, no pin directory, no crontab write)
#
# The script finds nothing relative to its own path, so it can run from anywhere,
# including `bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:<this file>) --all`.
#
# PINNED COPY (OP-9 option B, 2026-09-17). Cron must not run the mutable shared clone
# /mnt/raid0/llm/epyc-root: any session can edit or check out files there, and bash
# reads a running script incrementally. It must not run the auto-reset hub view
# /mnt/raid0/llm/views/epyc-root-main either, because that view is force-checked-out
# every 180 s. So --all does three things:
#   1. It fetches origin in the shared clone (remote refs only, no working-tree change)
#      and resolves origin/main to a full sha, unless --pin-sha is given.
#   2. It `git archive`s the supervisor's whole closure at that sha into
#        /mnt/raid0/llm/ops/hub-supervisor/<sha>/scripts/dashboard/
#      {hub_supervisor.sh, hub_launch_spec.py, refresh_hub_view.sh}. The supervisor
#      finds the other two as its siblings. The copy is written to a temp dir, checked
#      byte-for-byte against the commit, stamped (PINNED.txt, SHA256SUMS), made
#      read-only and renamed into place. An existing pin is reused only if its
#      SHA256SUMS still verify.
#   3. It points the cron line at that copy and passes the supervisor's DATA locations
#      explicitly: EPYC_ROOT/HUB_CANONICAL_ROOT (its home: logs, pidfiles, state) and
#      HUB_LAUNCH_MANIFEST (which names the hub source, currently the view).
# Single instance: the pinned `once` takes the same flock as the long-running daemon
# (/tmp/hub_supervisor_8100.lock, inside the container). While the daemon is alive,
# every cron pass logs "another supervisor already holds" and exits 0.
# To move the pin later, re-run --all (or --all --pin-sha SHA). Old pins stay on disk.
# Once no crontab line names a pin, delete it with `chmod -R u+w DIR && rm -rf DIR`.
#
# Idempotent: lines are keyed by marker comments and replaced, never duplicated.
# The previous crontab is backed up under logs/ before any change.
set -euo pipefail

CONTAINER="epyc-root"
ROOT="/mnt/raid0/llm/epyc-root"
MANIFEST="/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml"
PIN_BASE="/mnt/raid0/llm/ops/hub-supervisor"
LOG="${ROOT}/logs/cron_supervision.log"
# Host-side only; overridden by the regression test so it never writes into logs/.
BACKUP_DIR="${SUPERVISION_CRON_BACKUP_DIR:-${ROOT}/logs}"
MARK_HUB="# epyc-op9-hub-supervisor"
MARK_FW="# epyc-fw3-fleet-watch"
PIN_FILES=(scripts/dashboard/hub_supervisor.sh scripts/dashboard/hub_launch_spec.py scripts/dashboard/refresh_hub_view.sh)

LINE_FW="*/5 * * * * docker exec -d -u node -e PATH=/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin ${CONTAINER} setsid -f ${ROOT}/scripts/coordination/fleet_watch.sh ${MARK_FW}"

mode=""
dry=0
pin_sha=""
while (( $# )); do
  case "$1" in
    --fleet-watch-only) mode="fw" ;;
    --all) mode="all" ;;
    --dry-run) dry=1 ;;
    --pin-sha)
      shift
      pin_sha="${1:-}"
      [[ -n "$pin_sha" ]] || { echo "--pin-sha needs a value" >&2; exit 2; } ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done
[[ -n "$mode" ]] || { echo "usage: $0 --fleet-watch-only|--all [--pin-sha SHA] [--dry-run]" >&2; exit 2; }

in_ctr() { docker exec -u node "$CONTAINER" "$@"; }

# Preflight: host, docker, container, scripts. SUPERVISION_CRON_ALLOW_CONTAINER=1 exists
# only for the regression test, which runs with fake docker and crontab shims.
if [[ -f /.dockerenv && "${SUPERVISION_CRON_ALLOW_CONTAINER:-0}" != "1" ]]; then
  echo "ERROR: this looks like a container; run it on the host" >&2; exit 3
fi
command -v docker >/dev/null || { echo "ERROR: docker not found" >&2; exit 3; }
command -v crontab >/dev/null || { echo "ERROR: crontab not found" >&2; exit 3; }
running="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
[[ "$running" == "true" ]] || { echo "ERROR: container ${CONTAINER} is not running" >&2; exit 3; }
in_ctr test -x "${ROOT}/scripts/coordination/fleet_watch.sh" \
  || { echo "ERROR: fleet_watch.sh not executable inside ${CONTAINER}" >&2; exit 3; }

LINE_HUB=""
if [[ "$mode" == "all" ]]; then
  in_ctr test -f "$MANIFEST" \
    || { echo "ERROR: launch manifest ${MANIFEST} missing inside ${CONTAINER}" >&2; exit 3; }
  if [[ -z "$pin_sha" ]]; then
    if (( dry )); then
      echo "dry run: not fetching; the pin is the shared clone's current origin/main"
    else
      in_ctr git -C "$ROOT" fetch --quiet origin \
        || { echo "ERROR: git fetch origin failed in ${ROOT}" >&2; exit 3; }
    fi
    pin_sha="$(in_ctr git -C "$ROOT" rev-parse --verify 'origin/main^{commit}')" \
      || { echo "ERROR: cannot resolve origin/main in ${ROOT}" >&2; exit 3; }
  else
    pin_sha="$(in_ctr git -C "$ROOT" rev-parse --verify "${pin_sha}^{commit}")" \
      || { echo "ERROR: --pin-sha does not name a commit in ${ROOT}" >&2; exit 3; }
  fi
  [[ "$pin_sha" =~ ^[0-9a-f]{40}$ ]] || { echo "ERROR: bad pin sha '${pin_sha}'" >&2; exit 3; }
  # The pinned commit must carry the whole closure and the manifest-launch supervisor
  # (034dccbe+31d95ad8).
  for f in "${PIN_FILES[@]}"; do
    in_ctr git -C "$ROOT" cat-file -e "${pin_sha}:${f}" \
      || { echo "ERROR: ${pin_sha:0:12} lacks ${f}" >&2; exit 3; }
  done
  in_ctr git -C "$ROOT" grep -q 'HUB_SUPERVISOR_MANIFEST_LAUNCH_V1' "$pin_sha" -- scripts/dashboard/hub_supervisor.sh \
    || { echo "ERROR: hub_supervisor.sh at ${pin_sha:0:12} lacks the manifest-launch fix (034dccbe+31d95ad8)" >&2; exit 3; }

  PIN_DIR="${PIN_BASE}/${pin_sha}"
  PIN_SUP="${PIN_DIR}/scripts/dashboard/hub_supervisor.sh"
  LINE_HUB="*/2 * * * * docker exec -u node -e EPYC_ROOT=${ROOT} -e HUB_CANONICAL_ROOT=${ROOT} -e HUB_LAUNCH_MANIFEST=${MANIFEST} ${CONTAINER} ${PIN_SUP} once >>${LOG} 2>&1 ${MARK_HUB}"

  echo "pin: ${pin_sha} -> ${PIN_DIR}"
  if (( dry )); then
    if in_ctr test -d "$PIN_DIR"; then
      echo "dry run: the pin directory exists; a real run re-verifies and reuses it"
    else
      echo "dry run: a real run creates the pin directory with ${PIN_FILES[*]}"
    fi
  else
    # Runs inside the container as node, where git and the clone are known to work.
    # Positional args: $1 root, $2 sha, $3 pin dir, $4 pin base, $5... files.
    # shellcheck disable=SC2016
    in_ctr bash -c '
      set -euo pipefail
      root="$1"; sha="$2"; dir="$3"; base="$4"; shift 4
      verify() {
        (cd "$dir" && sha256sum --quiet -c SHA256SUMS) \
          && [[ -x "$dir/scripts/dashboard/hub_supervisor.sh" ]] \
          && grep -qx "pinned_sha=$sha" "$dir/PINNED.txt"
      }
      if [[ -d "$dir" ]]; then
        verify || { echo "ERROR: existing pin $dir does not verify; inspect it, do not reuse it" >&2; exit 4; }
        echo "pin exists and verifies: $dir"
        exit 0
      fi
      mkdir -p "$base"
      tmp="$(mktemp -d "$base/.tmp-${sha:0:12}-XXXXXX")"
      trap "chmod -R u+w \"$tmp\" 2>/dev/null; rm -rf \"$tmp\"" EXIT
      git -C "$root" archive --format=tar "$sha" -- "$@" | tar -x -C "$tmp"
      for f in "$@"; do
        [[ -f "$tmp/$f" ]] || { echo "ERROR: archive lacks $f" >&2; exit 4; }
        # Byte-identical to the commit, never to a working tree.
        git -C "$root" show "$sha:$f" | cmp -s - "$tmp/$f" \
          || { echo "ERROR: $f differs from $sha" >&2; exit 4; }
      done
      [[ -x "$tmp/scripts/dashboard/hub_supervisor.sh" && -x "$tmp/scripts/dashboard/refresh_hub_view.sh" ]] \
        || { echo "ERROR: pinned scripts lost their exec bit" >&2; exit 4; }
      bash -n "$tmp/scripts/dashboard/hub_supervisor.sh"
      bash -n "$tmp/scripts/dashboard/refresh_hub_view.sh"
      (cd "$tmp" && sha256sum "$@" > SHA256SUMS)
      {
        echo "pinned_sha=$sha"
        echo "source_repo=$root"
        echo "pinned_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "purpose=OP-9 option B (operator 2026-09-17): the host cron runs this immutable copy"
        echo "files=$*"
      } > "$tmp/PINNED.txt"
      chmod -R a-w "$tmp"
      # A same-parent rename needs write access on the parent only. It fails if the
      # target appeared meanwhile, and the trap then removes the temp dir.
      mv -T "$tmp" "$dir"
      trap - EXIT
      verify
      echo "pinned: $dir"
    ' _ "$ROOT" "$pin_sha" "$PIN_DIR" "$PIN_BASE" "${PIN_FILES[@]}" \
      || { echo "ERROR: pinning failed; crontab left unchanged" >&2; exit 3; }
    in_ctr test -x "$PIN_SUP" || { echo "ERROR: ${PIN_SUP} not executable inside ${CONTAINER}" >&2; exit 3; }
  fi
fi

current="$(crontab -l 2>/dev/null || true)"
new="$(printf '%s\n' "$current" | grep -vF -e "$MARK_FW" -e "$MARK_HUB" || true)"
new="$(printf '%s\n%s\n' "$new" "$LINE_FW")"
if [[ "$mode" == "all" ]]; then
  new="$(printf '%s\n%s\n' "$new" "$LINE_HUB")"
fi
new="$(printf '%s\n' "$new" | sed '/^$/d')"

echo "----- resulting crontab -----"
printf '%s\n' "$new"
echo "-----------------------------"
if (( dry )); then
  echo "dry run: nothing installed"
  exit 0
fi

backup="${BACKUP_DIR}/crontab.bak-$(date -u +%Y%m%dT%H%M%SZ)"
printf '%s\n' "$current" > "$backup"
printf '%s\n' "$new" | crontab -
echo "installed; previous crontab saved to ${backup}"
crontab -l | grep -F -e "$MARK_FW" -e "$MARK_HUB"
