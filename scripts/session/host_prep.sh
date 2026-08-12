#!/bin/bash
# host_prep.sh — apply and persist the host tunables the benchmark gates require.
#
# WHY THIS EXISTS
# ---------------
# Several host tunables are set at runtime and were believed to have no boot-time
# persistence, so the first post-reboot benchmark window burned while somebody
# worked out why the health gate had swapped one warning for another.
#
# THE ACTUAL SITUATION ON THIS HOST (measured 2026-08-12, not assumed):
#   * We run inside a Docker container whose  /  is an overlayfs. The HOST root is
#     reachable at /proc/1/root (the container shares the host PID namespace, so
#     PID 1 is the host's systemd). Writing the CONTAINER's /etc/sysctl.d is a
#     NO-OP for host boot -- that is the trap this script exists to avoid.
#   * The HOST already persists kernel.numa_balancing=0 by TWO mechanisms:
#       /etc/sysctl.d/99-epyc-inference.conf   (kernel.numa_balancing = 0,
#            overriding /etc/sysctl.d/20-numa.conf which sets it to 1)
#       numa-balancing-off.service             (enabled in multi-user.target.wants)
#   * The HOST does NOT persist: kernel.perf_event_paranoid, scaling_governor,
#     transparent_hugepage/enabled, transparent_hugepage/defrag. Those DO reset
#     at boot (canonical_recipe.py notes perf_event_paranoid returns to 4).
#
# WHAT THE GATES ACTUALLY CHECK (verified against source, not against prose):
#   server_np_sweep.host_health_warnings()          uptime<=7d, numa_balancing==0,
#                                                   no llama-server/bench/cli procs
#   server_numa_np_sweep.cpu_freq_static_warnings() cpufreq/boost!=0,
#                                                   every scaling_max_freq>=2500000
#   scripts/session/health_check.sh                 governor==performance, numa_balancing==0,
#                                                   THP enabled/defrag==always,
#                                                   perf_event_paranoid<=1, RAM>100GB
#   canonical_recipe.validate_host_environment()    THP enabled/defrag, governor,
#                                                   numa_balancing, perf_event_paranoid<=1
#   cpu_bench_clean_preflight.py                    uniform performance governor,
#                                                   energy_performance_preference in
#                                                   {performance,balance_performance},
#                                                   boost=="1" or absent
#
# MODES
#   --check         read-only drift report. exit 0 clean, 1 drift.
#   --apply         apply the runtime values (idempotent), then re-check.
#   --install-boot  install the HOST-side boot persistence (sysctl.d line +
#                   systemd unit + enable symlink). Inert until boot: it starts
#                   nothing, restarts nothing, and changes no running value.
#   --verify-boot   verify the host-side persistence artifacts. exit 0/1.
#
# TEST HOOKS (used by the mutation test; default to the real host)
#   EPYC_PROC_ROOT=/proc  EPYC_SYS_ROOT=/sys  EPYC_HOST_ROOT=<host filesystem root>
#   EPYC_HOSTPREP_DRYRUN=1  print what would be written, write nothing
set -euo pipefail

PROC_ROOT="${EPYC_PROC_ROOT:-/proc}"
SYS_ROOT="${EPYC_SYS_ROOT:-/sys}"
DRYRUN="${EPYC_HOSTPREP_DRYRUN:-0}"

# Targets. Single source of truth for this script; mirrors canonical_recipe.py
# REQUIRED_* constants and server_np_sweep.REQUIRED_NUMA_BALANCING.
TARGET_NUMA_BALANCING=0
TARGET_PERF_EVENT_PARANOID=1
TARGET_GOVERNOR=performance
TARGET_THP_ENABLED=always
TARGET_THP_DEFRAG=always
FREQ_BOOST_THRESHOLD_KHZ=2500000

SYSCTL_CONF_NAME="99-epyc-inference.conf"
UNIT_NAME="epyc-host-prep.service"

DRIFT=0
CHECKS=0
FIXED=0

log()  { printf '%s\n' "$*"; }
ok()   { CHECKS=$((CHECKS+1)); printf '  [ ok ]   %s\n' "$*"; }
bad()  { CHECKS=$((CHECKS+1)); DRIFT=$((DRIFT+1)); printf '  [DRIFT]  %s\n' "$*"; }
info() { printf '  [info]   %s\n' "$*"; }

# --------------------------------------------------------------------------- #
# Host root resolution
# --------------------------------------------------------------------------- #
resolve_host_root() {
  if [[ -n "${EPYC_HOST_ROOT+x}" ]]; then printf '%s' "$EPYC_HOST_ROOT"; return 0; fi
  # If /etc and /proc/1/root/etc are on different devices we are in a container
  # whose /etc is NOT the host's; then the host root is /proc/1/root.
  #
  # NOTE: /proc/1/root is traversable ONLY as root. An unprivileged `[[ -d ... ]]`
  # here silently returns false, the function falls back to "/", and the installer
  # then writes the CONTAINER's /etc — an install that reports success and does
  # nothing at boot. That bug shipped once; every probe below must use sudo.
  local here there
  here=$(stat -c %d /etc 2>/dev/null || echo x)
  there=$(sudo -n stat -c %d /proc/1/root/etc 2>/dev/null || echo y)
  if sudo -n test -d /proc/1/root/etc && [[ "$here" != "$there" ]]; then
    printf '/proc/1/root'; return 0
  fi
  # Containerised but the host root could not be identified -> FAIL CLOSED.
  # Writing the overlay would look like success and change nothing at boot.
  if [[ -e /.dockerenv && "$here" == "$there" ]]; then
    printf ''; return 0   # same device: /etc really is the host's
  fi
  if [[ -e /.dockerenv ]]; then
    echo "FATAL: running in a container but could not resolve the HOST filesystem root." >&2
    echo "       /etc dev=$here  /proc/1/root/etc dev=$there  (needs root to traverse /proc/1/root)" >&2
    echo "       Refusing to write the container overlay — that would be a silent no-op at boot." >&2
    echo "       Set EPYC_HOST_ROOT explicitly if you know the correct path." >&2
    return 1
  fi
  printf ''
}

# --------------------------------------------------------------------------- #
# Writers (all no-op under EPYC_HOSTPREP_DRYRUN=1)
# --------------------------------------------------------------------------- #
write_val() {  # write_val <path> <value>
  local path="$1" val="$2"
  if [[ "$DRYRUN" == "1" ]]; then log "    DRYRUN: would write '$val' -> $path"; return 0; fi
  if [[ -w "$path" ]]; then
    printf '%s\n' "$val" > "$path" 2>/dev/null && return 0
  fi
  printf '%s\n' "$val" | sudo -n tee "$path" >/dev/null
}

# --------------------------------------------------------------------------- #
# Individual settings — each returns 0 if at target
# --------------------------------------------------------------------------- #
read_first() { [[ -r "$1" ]] && head -1 "$1" 2>/dev/null | tr -d '\n' || return 1; }

# Real sysfs renders the active THP mode in brackets ("[always] madvise never")
# and re-renders on write, so the bracket parse is the primary path and always
# wins on a live host. The bracketless fallback exists only so the setting is
# testable against a plain-file fixture; it can never mask a real drift, because
# a real sysfs read always contains brackets.
thp_active() {
  local raw active
  [[ -r "$1" ]] || return 1
  raw=$(head -1 "$1" 2>/dev/null) || return 1
  active=$(printf '%s' "$raw" | awk -F'[][]' '{print $2}')
  if [[ -n "$active" ]]; then printf '%s' "$active"; else printf '%s' "${raw// /}"; fi
}

check_scalar() {  # check_scalar <label> <path> <target> [le]
  local label="$1" path="$2" target="$3" mode="${4:-eq}" cur
  if ! cur=$(read_first "$path"); then bad "$label: unreadable ($path)"; return 1; fi
  if [[ "$mode" == "le" ]]; then
    if [[ "$cur" =~ ^-?[0-9]+$ ]] && (( cur <= target )); then ok "$label = $cur (<= $target)"; return 0; fi
  else
    if [[ "$cur" == "$target" ]]; then ok "$label = $cur"; return 0; fi
  fi
  bad "$label = '$cur', expected '$target'  [$path]"
  return 1
}

check_thp() {  # check_thp <label> <path> <target>
  local label="$1" path="$2" target="$3" cur
  if ! cur=$(thp_active "$path"); then bad "$label: unreadable ($path)"; return 1; fi
  if [[ "$cur" == "$target" ]]; then ok "$label = $cur"; return 0; fi
  bad "$label = '$cur', expected '$target'  [$path]"
  return 1
}

check_governors() {
  local govs n_total n_bad
  mapfile -t govs < <(cat "$SYS_ROOT"/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor 2>/dev/null || true)
  n_total=${#govs[@]}
  if (( n_total == 0 )); then bad "scaling_governor: no cpufreq CPUs readable"; return 1; fi
  n_bad=$(printf '%s\n' "${govs[@]}" | grep -cv "^${TARGET_GOVERNOR}$" || true)
  if (( n_bad == 0 )); then ok "scaling_governor = $TARGET_GOVERNOR on all $n_total CPUs"; return 0; fi
  bad "scaling_governor: $n_bad/$n_total CPUs not '$TARGET_GOVERNOR'"
  return 1
}

check_epp() {
  local vals n_total n_bad
  mapfile -t vals < <(cat "$SYS_ROOT"/devices/system/cpu/cpu[0-9]*/cpufreq/energy_performance_preference 2>/dev/null || true)
  n_total=${#vals[@]}
  if (( n_total == 0 )); then info "energy_performance_preference: not exposed (skipped)"; return 0; fi
  n_bad=$(printf '%s\n' "${vals[@]}" | grep -cvE '^(performance|balance_performance)$' || true)
  if (( n_bad == 0 )); then ok "energy_performance_preference acceptable on all $n_total CPUs"; return 0; fi
  bad "energy_performance_preference: $n_bad/$n_total CPUs outside {performance,balance_performance}"
  return 1
}

check_boost() {
  local path="$SYS_ROOT/devices/system/cpu/cpufreq/boost" cur
  if [[ ! -r "$path" ]]; then info "cpufreq/boost: absent (amd-pstate active mode) — gate treats this as OK"; return 0; fi
  cur=$(read_first "$path")
  if [[ "$cur" != "0" ]]; then ok "cpufreq/boost = $cur"; return 0; fi
  bad "cpufreq/boost = 0 — host cannot boost (throttled)"
  return 1
}

check_freq_caps() {
  # CHECK ONLY, never auto-written: a cap is EVIDENCE of thermal/BIOS throttle
  # and papering over it would defeat feedback_host_throttle_check.
  local capped total
  read -r capped total < <(cat "$SYS_ROOT"/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_max_freq 2>/dev/null \
    | awk -v t="$FREQ_BOOST_THRESHOLD_KHZ" '$1<t{c++} END{print (c+0), NR}')
  if (( total == 0 )); then bad "scaling_max_freq: no CPUs readable"; return 1; fi
  if (( capped == 0 )); then ok "scaling_max_freq: 0/$total CPUs below $FREQ_BOOST_THRESHOLD_KHZ kHz"; return 0; fi
  bad "scaling_max_freq: $capped/$total CPUs capped below $FREQ_BOOST_THRESHOLD_KHZ kHz (investigate, do NOT auto-raise)"
  return 1
}

report_non_settable() {
  local up days
  up=$(awk '{print int($1)}' "$PROC_ROOT/uptime" 2>/dev/null || echo 0)
  days=$(awk -v s="$up" 'BEGIN{printf "%.2f", s/86400}')
  if (( up > 604800 )); then
    info "uptime = ${days} d — EXCEEDS the 7 d decision-grade ceiling. NOT fixable by this script; only a reboot clears it."
  else
    info "uptime = ${days} d — within the 7 d decision-grade ceiling."
  fi

  # DELIBERATELY NOT OBSERVED HERE: "are llama processes running?".
  #
  # An earlier revision counted them by listing every process's argv and grepping for
  # the llama binary names. (The literal command is not repeated here on purpose: the
  # observer census discovers subjects by pattern-matching the source, so quoting the
  # idiom in a comment re-triggers the very finding this note explains.)
  #
  # That is the observer defect class (scripts/coordination/observer_guard.sh): with
  # `set -o pipefail`, grep exiting 1 on a genuine zero and the process lister failing
  # outright BOTH land in the `|| true` branch and print "0". A real absence and a blind
  # probe were byte-identical — two states where the contract requires three, and it
  # fails OPEN (reports "nothing running" when it cannot see).
  #
  # It was also redundant: nothing in this script branches on it, and the authoritative
  # detector already exists and is better — server_np_sweep.find_llama_processes()
  # resolves /proc/<pid>/exe rather than matching argv, and host_health_warnings()
  # is what actually gates the benchmark. Deleting beats enrolling a second, worse
  # copy of an observation this script does not need.
  info "llama-process precondition is NOT evaluated here — server_np_sweep.host_health_warnings()"
  info "  owns it ('existing llama processes present during attestation'). Ask that gate, not this script."
}

# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
do_check() {
  log "=== host tunables — runtime state (proc=$PROC_ROOT sys=$SYS_ROOT) ==="
  check_scalar "kernel.numa_balancing"      "$PROC_ROOT/sys/kernel/numa_balancing"      "$TARGET_NUMA_BALANCING"      || true
  check_scalar "kernel.perf_event_paranoid" "$PROC_ROOT/sys/kernel/perf_event_paranoid" "$TARGET_PERF_EVENT_PARANOID" le || true
  check_governors || true
  check_thp "transparent_hugepage/enabled" "$SYS_ROOT/kernel/mm/transparent_hugepage/enabled" "$TARGET_THP_ENABLED" || true
  check_thp "transparent_hugepage/defrag"  "$SYS_ROOT/kernel/mm/transparent_hugepage/defrag"  "$TARGET_THP_DEFRAG"  || true
  check_epp        || true
  check_boost      || true
  check_freq_caps  || true
  log ""
  log "--- not settable by this script (reported for the runbook) ---"
  report_non_settable
  log ""
  log "checks=$CHECKS drift=$DRIFT"
  (( DRIFT == 0 ))
}

do_apply() {
  log "=== applying host tunables (idempotent) ==="
  local cur

  cur=$(read_first "$PROC_ROOT/sys/kernel/numa_balancing" || echo "")
  if [[ "$cur" != "$TARGET_NUMA_BALANCING" ]]; then
    log "  numa_balancing: '$cur' -> $TARGET_NUMA_BALANCING"
    write_val "$PROC_ROOT/sys/kernel/numa_balancing" "$TARGET_NUMA_BALANCING"; FIXED=$((FIXED+1))
  else log "  numa_balancing already $cur"; fi

  cur=$(read_first "$PROC_ROOT/sys/kernel/perf_event_paranoid" || echo "")
  if [[ ! "$cur" =~ ^-?[0-9]+$ ]] || (( cur > TARGET_PERF_EVENT_PARANOID )); then
    log "  perf_event_paranoid: '$cur' -> $TARGET_PERF_EVENT_PARANOID"
    write_val "$PROC_ROOT/sys/kernel/perf_event_paranoid" "$TARGET_PERF_EVENT_PARANOID"; FIXED=$((FIXED+1))
  else log "  perf_event_paranoid already $cur"; fi

  local g changed=0
  for g in "$SYS_ROOT"/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do
    [[ -e "$g" ]] || continue
    if [[ "$(read_first "$g")" != "$TARGET_GOVERNOR" ]]; then
      write_val "$g" "$TARGET_GOVERNOR"; changed=$((changed+1))
    fi
  done
  if (( changed )); then log "  scaling_governor: set $changed CPUs -> $TARGET_GOVERNOR"; FIXED=$((FIXED+1));
  else log "  scaling_governor already $TARGET_GOVERNOR everywhere"; fi

  local p t
  for p in "$SYS_ROOT/kernel/mm/transparent_hugepage/enabled:$TARGET_THP_ENABLED" \
           "$SYS_ROOT/kernel/mm/transparent_hugepage/defrag:$TARGET_THP_DEFRAG"; do
    t="${p##*:}"; p="${p%:*}"
    [[ -e "$p" ]] || continue
    if [[ "$(thp_active "$p")" != "$t" ]]; then
      log "  $(basename "$p"): -> $t"; write_val "$p" "$t"; FIXED=$((FIXED+1))
    else log "  $(basename "$p") already $t"; fi
  done

  local e ec=0
  for e in "$SYS_ROOT"/devices/system/cpu/cpu[0-9]*/cpufreq/energy_performance_preference; do
    [[ -e "$e" ]] || continue
    case "$(read_first "$e")" in
      performance|balance_performance) ;;
      *) write_val "$e" performance; ec=$((ec+1)) ;;
    esac
  done
  (( ec )) && { log "  energy_performance_preference: set $ec CPUs -> performance"; FIXED=$((FIXED+1)); } || true

  local b="$SYS_ROOT/devices/system/cpu/cpufreq/boost"
  if [[ -e "$b" && "$(read_first "$b")" == "0" ]]; then
    log "  cpufreq/boost: 0 -> 1"; write_val "$b" 1; FIXED=$((FIXED+1))
  fi

  log ""
  log "applied $FIXED change-group(s); re-checking"
  log ""
  DRIFT=0; CHECKS=0
  do_check
}

do_install_boot() {
  local host_root sysctl_path unit_path wants_link
  host_root=$(resolve_host_root)
  log "=== installing HOST boot persistence ==="
  if [[ -n "$host_root" ]]; then
    log "  containerised: HOST filesystem root resolved to '$host_root'"
    log "  (writing the container's own /etc would be a NO-OP at host boot)"
  else
    log "  not containerised (or EPYC_HOST_ROOT forced empty): using /"
  fi
  sysctl_path="$host_root/etc/sysctl.d/$SYSCTL_CONF_NAME"
  unit_path="$host_root/etc/systemd/system/$UNIT_NAME"
  wants_link="$host_root/etc/systemd/system/multi-user.target.wants/$UNIT_NAME"

  # 1. sysctl.d — perf_event_paranoid (numa_balancing is already persisted here)
  if sudo -n grep -qs '^[[:space:]]*kernel\.perf_event_paranoid' "$sysctl_path"; then
    log "  sysctl.d: kernel.perf_event_paranoid already present in $sysctl_path"
  else
    log "  sysctl.d: appending kernel.perf_event_paranoid = $TARGET_PERF_EVENT_PARANOID to $sysctl_path"
    if [[ "$DRYRUN" == "1" ]]; then log "    DRYRUN: no write"; else
      sudo -n tee -a "$sysctl_path" >/dev/null <<EOF

# User-mode HW perf events need <= 1. Kernel/distro default is 4, so without
# this line the value silently reverts at every boot and the canonical bench
# preflight (canonical_recipe.validate_host_environment) fails.
kernel.perf_event_paranoid = $TARGET_PERF_EVENT_PARANOID
EOF
    fi
  fi

  # 2. systemd unit — the knobs sysctl.d cannot express
  log "  unit: writing $unit_path"
  if [[ "$DRYRUN" == "1" ]]; then log "    DRYRUN: no write"; else
    sudo -n tee "$unit_path" >/dev/null <<EOF
[Unit]
Description=EPYC inference host prep (governor, THP, EPP) — benchmark gate prerequisites
Documentation=file:///workspace/scripts/session/host_prep.sh
# sysctl.d covers kernel.numa_balancing and kernel.perf_event_paranoid; these
# sysfs knobs cannot be expressed as sysctls and reset to kernel defaults at boot.
After=systemd-sysctl.service
Wants=systemd-sysctl.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_governor; do echo $TARGET_GOVERNOR > "\$g" 2>/dev/null || true; done'
ExecStart=/bin/sh -c 'echo $TARGET_THP_ENABLED > /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || true'
ExecStart=/bin/sh -c 'echo $TARGET_THP_DEFRAG > /sys/kernel/mm/transparent_hugepage/defrag 2>/dev/null || true'
ExecStart=/bin/sh -c 'for e in /sys/devices/system/cpu/cpu[0-9]*/cpufreq/energy_performance_preference; do echo performance > "\$e" 2>/dev/null || true; done'

[Install]
WantedBy=multi-user.target
EOF
  fi

  # 3. enable — the symlink IS what `systemctl enable` creates. We cannot call
  #    systemctl from inside the container (no bus to the host manager), and we
  #    deliberately do not need to: systemd re-reads units at boot.
  log "  enable: $wants_link"
  if [[ "$DRYRUN" == "1" ]]; then log "    DRYRUN: no symlink"; else
    sudo -n mkdir -p "$(dirname "$wants_link")"
    sudo -n ln -sfn "/etc/systemd/system/$UNIT_NAME" "$wants_link"
  fi
  log ""
  log "installed. NOTHING was started or restarted; this takes effect at the next boot."
  log "to verify:  $0 --verify-boot"
}

do_verify_boot() {
  local host_root sysctl_path unit_path wants_link
  host_root=$(resolve_host_root)
  sysctl_path="$host_root/etc/sysctl.d/$SYSCTL_CONF_NAME"
  unit_path="$host_root/etc/systemd/system/$UNIT_NAME"
  wants_link="$host_root/etc/systemd/system/multi-user.target.wants/$UNIT_NAME"
  log "=== verifying HOST boot persistence (host root '${host_root:-/}') ==="

  if sudo -n grep -qs "^[[:space:]]*kernel\.numa_balancing[[:space:]]*=[[:space:]]*$TARGET_NUMA_BALANCING" "$sysctl_path"; then
    ok "sysctl.d persists kernel.numa_balancing = $TARGET_NUMA_BALANCING"
  else bad "sysctl.d does NOT persist kernel.numa_balancing ($sysctl_path)"; fi

  if sudo -n grep -qs "^[[:space:]]*kernel\.perf_event_paranoid[[:space:]]*=[[:space:]]*$TARGET_PERF_EVENT_PARANOID" "$sysctl_path"; then
    ok "sysctl.d persists kernel.perf_event_paranoid = $TARGET_PERF_EVENT_PARANOID"
  else bad "sysctl.d does NOT persist kernel.perf_event_paranoid ($sysctl_path)"; fi

  if sudo -n test -f "$unit_path"; then ok "unit present: $unit_path"
  else bad "unit MISSING: $unit_path"; fi

  if sudo -n test -L "$wants_link"; then ok "unit ENABLED (wants symlink present)"
  else bad "unit NOT enabled: $wants_link missing"; fi

  for k in scaling_governor transparent_hugepage/enabled transparent_hugepage/defrag; do
    if sudo -n grep -qs "$k" "$unit_path"; then ok "unit covers $k"; else bad "unit does NOT cover $k"; fi
  done

  log ""
  log "checks=$CHECKS drift=$DRIFT"
  (( DRIFT == 0 ))
}

case "${1:---check}" in
  --check)        do_check ;;
  --apply)        do_apply ;;
  --install-boot) do_install_boot ;;
  --verify-boot)  do_verify_boot ;;
  -h|--help)      sed -n '1,60p' "$0" ;;
  *) echo "usage: $0 [--check|--apply|--install-boot|--verify-boot]" >&2; exit 2 ;;
esac
