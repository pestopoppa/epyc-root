#!/bin/bash
# OP-9 + FW-3 (operator-approved 2026-09-16): host crontab that keeps the in-container
# hub supervisor and fleet_watch alive. Run ON THE HOST (not inside the devcontainer):
# the container has no cron and its own /tmp.
#
#   --fleet-watch-only   install only the fleet_watch line (safe now: fleet_watch.sh
#                        takes a single-instance flock, so repeated launches exit)
#   --all                install both lines; only after the main session says the
#                        hub_supervisor fix (034dccbe) is merged and the supervisor was
#                        relaunched from the canonical root
#   --dry-run            show the resulting crontab without installing it
#
# Idempotent: lines are keyed by marker comments and replaced, never duplicated.
# The previous crontab is backed up under logs/ before any change.
set -euo pipefail

CONTAINER="epyc-root"
ROOT="/mnt/raid0/llm/epyc-root"
LOG="${ROOT}/logs/cron_supervision.log"
MARK_HUB="# epyc-op9-hub-supervisor"
MARK_FW="# epyc-fw3-fleet-watch"

LINE_HUB="*/2 * * * * docker exec -u node ${CONTAINER} ${ROOT}/scripts/dashboard/hub_supervisor.sh once >>${LOG} 2>&1 ${MARK_HUB}"
LINE_FW="*/5 * * * * docker exec -d -u node -e PATH=/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin ${CONTAINER} setsid -f ${ROOT}/scripts/coordination/fleet_watch.sh ${MARK_FW}"

mode=""
dry=0
for arg in "$@"; do
  case "$arg" in
    --fleet-watch-only) mode="fw" ;;
    --all) mode="all" ;;
    --dry-run) dry=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done
[[ -n "$mode" ]] || { echo "usage: $0 --fleet-watch-only|--all [--dry-run]" >&2; exit 2; }

# Preflight: host, docker, container, scripts.
if [[ -f /.dockerenv ]]; then
  echo "ERROR: this looks like a container; run it on the host" >&2; exit 3
fi
command -v docker >/dev/null || { echo "ERROR: docker not found" >&2; exit 3; }
command -v crontab >/dev/null || { echo "ERROR: crontab not found" >&2; exit 3; }
running="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
[[ "$running" == "true" ]] || { echo "ERROR: container ${CONTAINER} is not running" >&2; exit 3; }
docker exec -u node "$CONTAINER" test -x "${ROOT}/scripts/coordination/fleet_watch.sh" \
  || { echo "ERROR: fleet_watch.sh not executable inside ${CONTAINER}" >&2; exit 3; }
if [[ "$mode" == "all" ]]; then
  docker exec -u node "$CONTAINER" test -x "${ROOT}/scripts/dashboard/hub_supervisor.sh" \
    || { echo "ERROR: hub_supervisor.sh not executable inside ${CONTAINER}" >&2; exit 3; }
  # The fix must be live: the merged supervisor launches the hub from the launch manifest.
  docker exec -u node "$CONTAINER" grep -q 'HUB_SUPERVISOR_MANIFEST_LAUNCH_V1' "${ROOT}/scripts/dashboard/hub_supervisor.sh" \
    || { echo "ERROR: hub_supervisor.sh in ${ROOT} lacks the manifest-launch fix (034dccbe+31d95ad8); wait for the merge" >&2; exit 3; }
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

backup="${ROOT}/logs/crontab.bak-$(date -u +%Y%m%dT%H%M%SZ)"
printf '%s\n' "$current" > "$backup"
printf '%s\n' "$new" | crontab -
echo "installed; previous crontab saved to ${backup}"
crontab -l | grep -F -e "$MARK_FW" -e "$MARK_HUB"
