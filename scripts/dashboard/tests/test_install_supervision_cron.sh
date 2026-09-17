#!/bin/bash
# Regression test: scripts/operator/install_supervision_cron_20260916.sh --all installs a
# PINNED, immutable copy of hub_supervisor.sh (OP-9 option B, operator 2026-09-17) and
# points the host cron line at it, never at the shared clone or the hub view.
#
# SCOPE: fake `docker` and `crontab` shims on PATH. The docker shim runs the command
# locally and maps the installer's literal paths (/mnt/raid0/llm/epyc-root,
# /mnt/raid0/llm/epyc-orchestrator, /mnt/raid0/llm/ops) onto a fixture. Nothing here
# touches the real crontab, the shared clone, the real lock or any process. The one
# supervisor invocation runs on a fixture port whose lock this shell already holds,
# so it exits at acquire_lock before probing anything.
set -euo pipefail   # MATCH PRODUCTION
cd "$(dirname "$0")/../../.." || exit 1
REPO_DIR="$PWD"
INSTALLER="$REPO_DIR/scripts/operator/install_supervision_cron_20260916.sh"
TMP=$(mktemp -d)
trap 'chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"' EXIT

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2', want '$3')"; fail=$((fail+1)); fi; }

# --- fixture ------------------------------------------------------------------ #
FX="$TMP/llm"
ORIGIN="$TMP/origin.git"
git init -q --bare -b main "$ORIGIN"
SEED="$TMP/seed"
git init -q -b main "$SEED"
mkdir -p "$SEED/scripts/dashboard" "$SEED/scripts/coordination"
for f in hub_supervisor.sh hub_launch_spec.py refresh_hub_view.sh; do
  cp "$REPO_DIR/scripts/dashboard/$f" "$SEED/scripts/dashboard/$f"
done
chmod +x "$SEED/scripts/dashboard/hub_supervisor.sh" "$SEED/scripts/dashboard/refresh_hub_view.sh"
printf '#!/bin/bash\nexit 0\n' > "$SEED/scripts/coordination/fleet_watch.sh"
chmod +x "$SEED/scripts/coordination/fleet_watch.sh"
gitc() { git -C "$SEED" -c user.email=t@t -c user.name=t "$@"; }
gitc add -A; gitc commit -qm base
git -C "$SEED" push -q "$ORIGIN" main
git clone -q "$ORIGIN" "$FX/epyc-root"
mkdir -p "$FX/epyc-root/logs" "$FX/epyc-orchestrator/orchestration"
echo "aux_services: []" > "$FX/epyc-orchestrator/orchestration/launch_manifest.yaml"
mkdir -p "$TMP/backup"

BIN="$TMP/bin"; mkdir -p "$BIN"
cat > "$BIN/docker" <<'SH'
#!/bin/bash
set -euo pipefail
map() {
  local a="$1"
  a="${a//\/mnt\/raid0\/llm\/epyc-root/$FX/epyc-root}"
  a="${a//\/mnt\/raid0\/llm\/epyc-orchestrator/$FX/epyc-orchestrator}"
  a="${a//\/mnt\/raid0\/llm\/ops/$FX/ops}"
  printf '%s' "$a"
}
case "$1" in
  inspect) echo true; exit 0 ;;
  exec) shift ;;
  *) echo "fake docker: unsupported $1" >&2; exit 1 ;;
esac
envs=()
while [[ "$1" == -* ]]; do
  case "$1" in
    -u) shift 2 ;;
    -d) shift ;;
    -e) envs+=("$(map "$2")"); shift 2 ;;
    *) echo "fake docker: unsupported flag $1" >&2; exit 1 ;;
  esac
done
shift   # container name
args=()
for a in "$@"; do args+=("$(map "$a")"); done
exec env ${envs[@]+"${envs[@]}"} "${args[@]}"
SH
cat > "$BIN/crontab" <<'SH'
#!/bin/bash
case "$1" in
  -l) [[ -f "$FAKE_CRONTAB" ]] && cat "$FAKE_CRONTAB" || { echo "no crontab" >&2; exit 1; } ;;
  -) cat > "$FAKE_CRONTAB" ;;
  *) echo "fake crontab: unsupported $1" >&2; exit 1 ;;
esac
SH
chmod +x "$BIN/docker" "$BIN/crontab"

export FX FAKE_CRONTAB="$TMP/crontab"
printf '%s\n' "0 3 * * * /usr/bin/true # operator's own line" > "$FAKE_CRONTAB"
run() {
  PATH="$BIN:$PATH" SUPERVISION_CRON_ALLOW_CONTAINER=1 SUPERVISION_CRON_BACKUP_DIR="$TMP/backup" \
    bash "$INSTALLER" "$@"
}
hub_lines() { grep -cF '# epyc-op9-hub-supervisor' "$FAKE_CRONTAB" || true; }
fw_lines() { grep -cF '# epyc-fw3-fleet-watch' "$FAKE_CRONTAB" || true; }
SHA1="$(git -C "$SEED" rev-parse HEAD)"

echo "1. --all --dry-run changes nothing"
rc=0; out="$(run --all --dry-run 2>&1)" || rc=$?
chk "dry-run exit" "$rc" "0"
chk "dry-run names the origin/main pin" "$(grep -c "pin: $SHA1 -> /mnt/raid0/llm/ops/hub-supervisor/$SHA1" <<<"$out")" "1"
chk "dry-run created no pin dir" "$([[ -e "$FX/ops" ]] && echo yes || echo no)" "no"
chk "dry-run left the crontab alone" "$(wc -l < "$FAKE_CRONTAB" | tr -d ' ')" "1"

echo "2. --all pins and installs"
rc=0; out="$(run --all 2>&1)" || rc=$?
chk "install exit" "$rc" "0"
PIN="$FX/ops/hub-supervisor/$SHA1"
for f in hub_supervisor.sh hub_launch_spec.py refresh_hub_view.sh; do
  chk "pinned $f is byte-identical to the commit" \
    "$(git -C "$SEED" show "$SHA1:scripts/dashboard/$f" | cmp -s - "$PIN/scripts/dashboard/$f" && echo same || echo diff)" "same"
done
chk "pinned supervisor is executable" "$([[ -x "$PIN/scripts/dashboard/hub_supervisor.sh" ]] && echo yes || echo no)" "yes"
chk "pinned supervisor is read-only" "$([[ -w "$PIN/scripts/dashboard/hub_supervisor.sh" ]] && echo writable || echo ro)" "ro"
chk "pin dir is read-only" "$([[ -w "$PIN" ]] && echo writable || echo ro)" "ro"
chk "PINNED.txt records the sha" "$(grep -cx "pinned_sha=$SHA1" "$PIN/PINNED.txt")" "1"
chk "no temp dir left behind" "$(find "$FX/ops/hub-supervisor" -maxdepth 1 -name '.tmp-*' | wc -l | tr -d ' ')" "0"
line="$(grep -F '# epyc-op9-hub-supervisor' "$FAKE_CRONTAB")"
chk "one hub line" "$(hub_lines)" "1"
chk "one fleet_watch line" "$(fw_lines)" "1"
chk "operator's own line kept" "$(grep -c "operator's own line" "$FAKE_CRONTAB")" "1"
chk "hub line runs the pinned copy" \
  "$(grep -c "epyc-root /mnt/raid0/llm/ops/hub-supervisor/$SHA1/scripts/dashboard/hub_supervisor.sh once" <<<"$line")" "1"
chk "hub line never runs the shared clone's supervisor" \
  "$(grep -c '/mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh' <<<"$line" || true)" "0"
chk "hub line never runs the view" "$(grep -c 'views/epyc-root-main' <<<"$line" || true)" "0"
chk "hub line passes the home explicitly" \
  "$(grep -c -- '-e EPYC_ROOT=/mnt/raid0/llm/epyc-root -e HUB_CANONICAL_ROOT=/mnt/raid0/llm/epyc-root' <<<"$line")" "1"
chk "hub line passes the manifest explicitly" \
  "$(grep -c -- '-e HUB_LAUNCH_MANIFEST=/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml' <<<"$line")" "1"
chk "crontab backup written" "$(ls "$TMP/backup" | grep -c '^crontab.bak-')" "1"

echo "3. re-running --all is idempotent"
before="$(cat "$FAKE_CRONTAB")"
rc=0; out="$(run --all 2>&1)" || rc=$?
chk "rerun exit" "$rc" "0"
chk "rerun reuses the verified pin" "$(grep -c 'pin exists and verifies' <<<"$out")" "1"
chk "rerun crontab unchanged" "$([[ "$(cat "$FAKE_CRONTAB")" == "$before" ]] && echo same || echo diff)" "same"

echo "4. the pinned once defers to a running daemon's lock"
PORT=18173
exec 7>"/tmp/hub_supervisor_${PORT}.lock"
flock -n 7
rc=0
out="$(HUB_PORT=$PORT EPYC_ROOT="$FX/epyc-root" HUB_CANONICAL_ROOT="$FX/epyc-root" \
       HUB_LAUNCH_MANIFEST="$FX/epyc-orchestrator/orchestration/launch_manifest.yaml" \
       "$PIN/scripts/dashboard/hub_supervisor.sh" once 2>&1)" || rc=$?
exec 7>&-
rm -f "/tmp/hub_supervisor_${PORT}.lock"
chk "pinned once exits 0 under a held lock" "$rc" "0"
chk "pinned once says another supervisor holds the lock" "$(grep -c 'another supervisor already holds' <<<"$out")" "1"

echo "5. a tampered pin is refused and the crontab is untouched"
chmod u+w "$PIN/scripts/dashboard" "$PIN/scripts/dashboard/hub_launch_spec.py"
echo "# tampered" >> "$PIN/scripts/dashboard/hub_launch_spec.py"
before="$(cat "$FAKE_CRONTAB")"
rc=0; out="$(run --all 2>&1)" || rc=$?
chk "tampered pin exit" "$rc" "3"
chk "tampered pin crontab unchanged" "$([[ "$(cat "$FAKE_CRONTAB")" == "$before" ]] && echo same || echo diff)" "same"
git -C "$SEED" show "$SHA1:scripts/dashboard/hub_launch_spec.py" > "$PIN/scripts/dashboard/hub_launch_spec.py"
chmod a-w "$PIN/scripts/dashboard" "$PIN/scripts/dashboard/hub_launch_spec.py"

echo "6. a new origin/main moves the pin; the crontab still has one hub line"
echo "# next" >> "$SEED/scripts/dashboard/hub_launch_spec.py"
gitc commit -qam next
git -C "$SEED" push -q "$ORIGIN" main
SHA2="$(git -C "$SEED" rev-parse HEAD)"
rc=0; out="$(run --all 2>&1)" || rc=$?
chk "repin exit" "$rc" "0"
chk "repin fetched and pinned the new sha" "$([[ -x "$FX/ops/hub-supervisor/$SHA2/scripts/dashboard/hub_supervisor.sh" ]] && echo yes || echo no)" "yes"
chk "repin one hub line" "$(hub_lines)" "1"
chk "repin hub line names the new sha" "$(grep -c "hub-supervisor/$SHA2/" "$FAKE_CRONTAB")" "1"
chk "old pin kept on disk" "$([[ -d "$PIN" ]] && echo yes || echo no)" "yes"

echo "7. --pin-sha of a commit without the manifest-launch marker is refused"
sed -i '/HUB_SUPERVISOR_MANIFEST_LAUNCH_V1/d' "$SEED/scripts/dashboard/hub_supervisor.sh"
gitc commit -qam nomarker
git -C "$SEED" push -q "$ORIGIN" main
git -C "$FX/epyc-root" fetch -q origin
SHA3="$(git -C "$SEED" rev-parse HEAD)"
before="$(cat "$FAKE_CRONTAB")"
rc=0; out="$(run --all --pin-sha "$SHA3" 2>&1)" || rc=$?
chk "no-marker exit" "$rc" "3"
chk "no-marker made no pin" "$([[ -e "$FX/ops/hub-supervisor/$SHA3" ]] && echo yes || echo no)" "no"
chk "no-marker crontab unchanged" "$([[ "$(cat "$FAKE_CRONTAB")" == "$before" ]] && echo same || echo diff)" "same"

echo "8. --fleet-watch-only keeps working and never pins"
printf '%s\n' "0 3 * * * /usr/bin/true # operator's own line" > "$FAKE_CRONTAB"
rc=0; out="$(run --fleet-watch-only 2>&1)" || rc=$?
chk "fw-only exit" "$rc" "0"
chk "fw-only one fleet_watch line" "$(fw_lines)" "1"
chk "fw-only no hub line" "$(hub_lines)" "0"

echo
echo "passed $pass, failed $fail"
(( fail == 0 ))
