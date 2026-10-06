#!/bin/bash
set -euo pipefail
ROOT=/mnt/raid0/llm/epyc-root
VIEW=/mnt/raid0/llm/views/epyc-root-main
MANIFEST=/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml
PIN=00e1820bcd957e905797b3a1b9e4d9dc53a550b0
SCRATCH=/mnt/raid0/llm/tmp/ni07-29-ci-recipe-20261006/dashboard-report/host-activation-20261006
SOURCE=/mnt/raid0/llm/worktrees/codex-ni06-promote-root-k3-20261006
INSTALLER_PATH=scripts/operator/install_supervision_cron_20260916.sh
INSTALLER_SHA=7fe37e700d8799a8244c62c2ab77353508f3bb3eb8025c3a20483e7883cce9b9
HELPER_SHA=9a794584c497556f1ce0b75a465097621d73792ed456648f55ce1d156b1b9767
MODE=${1:---preview}
die() { printf 'REFUSED: %s\n' "$*" >&2; exit 3; }
in_ctr() { docker exec -u node epyc-root "$@"; }
hash() { sha256sum "$1" | awk '{print $1}'; }
[[ $# -le 1 && ( "$MODE" == --preview || "$MODE" == --apply || "$MODE" == --verify-activation ) ]] || die 'usage: run_host_activation.sh [--preview|--apply|--verify-activation]'
[[ ! -e /.dockerenv && ! -e /run/.containerenv ]] || die 'container detected; run on host'
[[ -z "${SUPERVISION_CRON_ALLOW_CONTAINER+x}" ]] || die 'container test override must be unset'
command -v docker >/dev/null || die 'docker unavailable'
command -v crontab >/dev/null || die 'crontab unavailable'
[[ "$(docker inspect -f '{{.State.Running}}' epyc-root)" == true ]] || die 'epyc-root container is not running'
[[ -d "$SCRATCH" && ! -L "$SCRATCH" ]] || die 'reviewed package directory missing or symlinked'
[[ -f "$SCRATCH/registry_patch.py" && ! -L "$SCRATCH/registry_patch.py" ]] || die 'helper missing or symlinked'
[[ "$(hash "$SCRATCH/registry_patch.py")" == "$HELPER_SHA" ]] || die 'helper differs from reviewed bytes'
# Execute the bytes just verified, as canonical node owner, with explicit deployment guard.
helper() {
  [[ "$(hash "$SCRATCH/registry_patch.py")" == "$HELPER_SHA" ]] || die 'helper hash changed'
  docker exec -i -u node epyc-root python3 - --host-parent-deploy "$@" < "$SCRATCH/registry_patch.py"
}
report="$SCRATCH/activation-report-${PIN}.txt"
verify_activation() {
  [[ -f "$report" && ! -L "$report" ]] || die 'apply report absent; run --apply first'
  helper --verify-applied
  grep -Fxq "cron_installed=yes" "$report" || die "cron install success not recorded"
  current_cron="$(crontab -l)"
  grep -Fq '# epyc-fw3-fleet-watch' <<< "$current_cron" || die 'current cron lacks fleet marker'
  grep -Fq "/mnt/raid0/llm/ops/hub-supervisor/$PIN/scripts/dashboard/hub_supervisor.sh once" <<< "$current_cron" || die 'current cron lacks reviewed hub pin'
  python3 - "$ROOT/logs/hygiene/state.json" "$ROOT/logs/hygiene/host_hygiene.log" "$report" "$PIN" <<'PY'
import datetime, json, pathlib, sys, time
report=dict(line.split('=', 1) for line in pathlib.Path(sys.argv[3]).read_text().splitlines() if '=' in line)
if report.get('pin') != sys.argv[4]:
    raise SystemExit('REFUSED: report pin differs')
import hashlib
backup=pathlib.Path(report['cron_backup'])
if hashlib.sha256(backup.read_bytes()).hexdigest() != report['cron_backup_sha256']:
    raise SystemExit('REFUSED: cron backup digest differs')
started=float(report['started_epoch'])
try:
    value=json.loads(pathlib.Path(sys.argv[1]).read_text()).get('heartbeat_at', '')
    stamp=datetime.datetime.fromisoformat(value).timestamp()
    log=pathlib.Path(sys.argv[2]); log_stat=log.stat()
    fresh=started <= stamp <= time.time() and log_stat.st_mtime >= started and log_stat.st_size > 0
except (OSError, ValueError, TypeError):
    value=''; fresh=False
print('heartbeat_status=' + ('observed' if fresh else 'not_yet_observed'))
print('heartbeat_at=' + (value or 'pending'))
print('activation_verified=' + ('yes' if fresh else 'pending'))
raise SystemExit(0 if fresh else 4)
PY
}
if [[ "$MODE" == --verify-activation ]]; then
  verify_activation
  exit 0
fi
# Import commit objects only. No checkout, pull, reset, shared-branch/ref update or staging.
if ! in_ctr git -C "$ROOT" cat-file -e "${PIN}^{commit}" 2>/dev/null; then
  in_ctr git -C "$ROOT" fetch --no-tags --no-write-fetch-head "$SOURCE" "$PIN"
fi
in_ctr git -C "$ROOT" cat-file -e "${PIN}^{commit}" || die 'reviewed commit absent'
tmp="$(mktemp -d "$SCRATCH/.host-run-XXXXXX")"
cleanup() {
  [[ -f "$tmp/install_supervision_cron.sh" ]] && unlink "$tmp/install_supervision_cron.sh"
  [[ -f "$tmp/hub_launch_spec.py" ]] && unlink "$tmp/hub_launch_spec.py"
  rmdir "$tmp"
}
trap cleanup EXIT
chmod 755 "$tmp"
in_ctr git -C "$ROOT" show "$PIN:$INSTALLER_PATH" > "$tmp/install_supervision_cron.sh"
[[ "$(hash "$tmp/install_supervision_cron.sh")" == "$INSTALLER_SHA" ]] || die 'installer source hash mismatch'
in_ctr git -C "$ROOT" show "$PIN:scripts/dashboard/hub_launch_spec.py" > "$tmp/hub_launch_spec.py"
chmod 644 "$tmp/install_supervision_cron.sh" "$tmp/hub_launch_spec.py"
# Existing pinned pure parser resolves the named service only; no stack imports/reloads.
spec="$(in_ctr python3 "$tmp/hub_launch_spec.py" --manifest "$MANIFEST" --service handoff_dashboard --local)"
[[ "$(printf '%s\n' "$spec" | sed -n 's/^HUB_M_CWD=//p')" == "$VIEW" ]] || die 'handoff_dashboard cwd is not reviewed view'
helper
preview="$SCRATCH/cron-preview-${PIN}.txt"
bash "$tmp/install_supervision_cron.sh" --pin-sha "$PIN" --all --dry-run | tee "$preview"
grep -Fq "pin: $PIN -> /mnt/raid0/llm/ops/hub-supervisor/$PIN" "$preview" || die 'preview pin mismatch'
grep -Fq '# epyc-fw3-fleet-watch' "$preview" || die 'preview fleet marker absent'
grep -Fq '# epyc-op9-hub-supervisor' "$preview" || die 'preview hub marker absent'
grep -Fq 'dry run: nothing installed' "$preview" || die 'preview dry-run confirmation absent'
if [[ "$MODE" == --preview ]]; then
  printf 'preview_only=yes\ninstaller_sha256=%s\nhelper_sha256=%s\n' "$INSTALLER_SHA" "$HELPER_SHA"
  exit 0
fi
# All runtime checks and normal installer preview succeeded before canonical mutation.
started="$(date +%s)"
printf 'pin=%s\nstarted_epoch=%s\ninstaller_sha256=%s\nhelper_sha256=%s\nactivation_verified=pending\n' "$PIN" "$started" "$INSTALLER_SHA" "$HELPER_SHA" > "$report"
helper --apply | tee "$SCRATCH/registry-apply-${PIN}.log"
helper --verify-applied
apply_log="$SCRATCH/cron-apply-${PIN}.log"
[[ "$(hash "$tmp/install_supervision_cron.sh")" == "$INSTALLER_SHA" ]] || die 'installer bytes changed after preview'
bash "$tmp/install_supervision_cron.sh" --pin-sha "$PIN" --all 2>&1 | tee "$apply_log"
backup="$(sed -n 's/^installed; previous crontab saved to //p' "$apply_log" | tail -1)"
[[ -n "$backup" && -f "$backup" ]] || die 'installer cron backup absent'
after="$SCRATCH/crontab-after-${PIN}.txt"
crontab -l > "$after"
grep -Fq '# epyc-fw3-fleet-watch' "$after" || die 'installed fleet marker absent'
grep -Fq "/mnt/raid0/llm/ops/hub-supervisor/$PIN/scripts/dashboard/hub_supervisor.sh once" "$after" || die 'installed hub pin mismatch'
{
  printf 'cron_backup=%s\ncron_backup_sha256=%s\n' "$backup" "$(hash "$backup")"
  printf 'preview=%s\napply_log=%s\ncrontab_after=%s\nregistry_apply_log=%s\n' "$preview" "$apply_log" "$after" "$SCRATCH/registry-apply-${PIN}.log"
  printf 'cron_installed=yes\nheartbeat_status=not_yet_observed\n'
} >> "$report"
cat "$report"
printf 'Run --verify-activation later to check a heartbeat after started_epoch; no waiting or daemon restart performed.\n'
