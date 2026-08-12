#!/bin/bash
# Mutation test for scripts/session/host_prep.sh.
# Every assertion is COUNTED and the exit code is derived from the count, so a
# suite that executes nothing cannot report green.
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/host_prep.sh"
PASS=0; FAIL=0

t() {  # t <label> <expected_rc> <actual_rc>
  if [[ "$2" == "$3" ]]; then PASS=$((PASS+1)); printf '  [PASS] %-62s rc=%s\n' "$1" "$3"
  else FAIL=$((FAIL+1)); printf '  [FAIL] %-62s rc=%s want=%s\n' "$1" "$3" "$2"; fi
}
tgrep() {  # tgrep <label> <file> <pattern> <should_match:0|1>
  if grep -qE "$3" "$2"; then got=1; else got=0; fi
  if [[ "$got" == "$4" ]]; then PASS=$((PASS+1)); printf '  [PASS] %-62s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  [FAIL] %-62s (match=%s want=%s)\n' "$1" "$got" "$4"; fi
}

ROOT=$(mktemp -d)
# --install-boot writes via sudo, so the fake-host artifacts end up root-owned.
# Cleanup and the G-series mutations therefore need sudo too.
trap 'sudo -n rm -rf "$ROOT" 2>/dev/null || rm -rf "$ROOT"' EXIT

mkfake() {  # build a clean, all-at-target fake /proc + /sys
  rm -rf "$ROOT/proc" "$ROOT/sys"
  mkdir -p "$ROOT/proc/sys/kernel" "$ROOT/sys/kernel/mm/transparent_hugepage" \
           "$ROOT/sys/devices/system/cpu/cpufreq"
  echo 0 > "$ROOT/proc/sys/kernel/numa_balancing"
  echo 1 > "$ROOT/proc/sys/kernel/perf_event_paranoid"
  echo "100.0 200.0" > "$ROOT/proc/uptime"
  echo "[always] madvise never" > "$ROOT/sys/kernel/mm/transparent_hugepage/enabled"
  echo "[always] defer madvise never" > "$ROOT/sys/kernel/mm/transparent_hugepage/defrag"
  echo 1 > "$ROOT/sys/devices/system/cpu/cpufreq/boost"
  for i in 0 1 2 3; do
    mkdir -p "$ROOT/sys/devices/system/cpu/cpu$i/cpufreq"
    echo performance   > "$ROOT/sys/devices/system/cpu/cpu$i/cpufreq/scaling_governor"
    echo performance   > "$ROOT/sys/devices/system/cpu/cpu$i/cpufreq/energy_performance_preference"
    echo 4500000       > "$ROOT/sys/devices/system/cpu/cpu$i/cpufreq/scaling_max_freq"
  done
}
run() { EPYC_PROC_ROOT="$ROOT/proc" EPYC_SYS_ROOT="$ROOT/sys" bash "$SCRIPT" "$1" >"$ROOT/out.txt" 2>&1; echo $?; }

echo "=== A. baseline: clean fake root ==="
mkfake
t "A1 --check on clean fake root -> 0" 0 "$(run --check)"
tgrep "A2 report is non-empty (8 checks executed, not vacuous)" "$ROOT/out.txt" 'checks=8 drift=0' 1

echo
echo "=== B. per-setting mutation: --check must DETECT each one ==="
declare -a MUT=(
  "numa_balancing|$ROOT/proc/sys/kernel/numa_balancing|1"
  "perf_event_paranoid|$ROOT/proc/sys/kernel/perf_event_paranoid|4"
  "governor|$ROOT/sys/devices/system/cpu/cpu2/cpufreq/scaling_governor|powersave"
  "thp_enabled|$ROOT/sys/kernel/mm/transparent_hugepage/enabled|always [madvise] never"
  "thp_defrag|$ROOT/sys/kernel/mm/transparent_hugepage/defrag|always defer [madvise] never"
  "epp|$ROOT/sys/devices/system/cpu/cpu1/cpufreq/energy_performance_preference|power"
  "boost|$ROOT/sys/devices/system/cpu/cpufreq/boost|0"
  "freq_cap|$ROOT/sys/devices/system/cpu/cpu3/cpufreq/scaling_max_freq|2000000"
)
for m in "${MUT[@]}"; do
  IFS='|' read -r name path val <<< "$m"
  mkfake; printf '%s\n' "$val" > "$path"
  t "B:$name mutated -> --check detects drift (rc 1)" 1 "$(run --check)"
done

echo
echo "=== C. --apply must RESTORE each settable mutation, then verify clean ==="
for m in "${MUT[@]}"; do
  IFS='|' read -r name path val <<< "$m"
  [[ "$name" == "freq_cap" ]] && continue   # check-only by design (throttle evidence)
  mkfake; printf '%s\n' "$val" > "$path"
  before=$(run --check)
  after=$(run --apply)
  t "C:$name  drift=$before -> after --apply rc" 0 "$after"
done

echo
echo "=== D. freq_cap is deliberately NOT auto-repaired (throttle evidence) ==="
mkfake; echo 2000000 > "$ROOT/sys/devices/system/cpu/cpu3/cpufreq/scaling_max_freq"
t "D1 --apply leaves a frequency cap unrepaired (rc 1)" 1 "$(run --apply)"
tgrep "D2 and says do NOT auto-raise" "$ROOT/out.txt" 'do NOT auto-raise' 1

echo
echo "=== E. vacuity guards: the check must not pass over an EMPTY tree ==="
rm -rf "$ROOT/proc" "$ROOT/sys"; mkdir -p "$ROOT/proc" "$ROOT/sys"
t "E1 --check on an empty tree -> 1 (does not pass vacuously)" 1 "$(run --check)"

echo
echo "=== F. boot persistence: install into a FAKE host root, then verify ==="
FAKEHOST="$ROOT/fakehost"
mkdir -p "$FAKEHOST/etc/sysctl.d" "$FAKEHOST/etc/systemd/system"
# seed the file exactly as the real host has it: numa_balancing only
printf '# EPYC inference tuning\nkernel.numa_balancing = 0\n' > "$FAKEHOST/etc/sysctl.d/99-epyc-inference.conf"
bootrun() { EPYC_HOST_ROOT="$FAKEHOST" bash "$SCRIPT" "$1" >"$ROOT/out.txt" 2>&1; echo $?; }

t "F1 --verify-boot BEFORE install -> 1 (perf_event_paranoid + unit absent)" 1 "$(bootrun --verify-boot)"
t "F2 --install-boot -> 0" 0 "$(bootrun --install-boot)"
t "F3 --verify-boot AFTER install -> 0" 0 "$(bootrun --verify-boot)"
tgrep "F4 sysctl.d now persists perf_event_paranoid" "$FAKEHOST/etc/sysctl.d/99-epyc-inference.conf" '^kernel\.perf_event_paranoid = 1' 1
tgrep "F5 numa_balancing line preserved (append, not overwrite)" "$FAKEHOST/etc/sysctl.d/99-epyc-inference.conf" '^kernel\.numa_balancing = 0' 1
tgrep "F6 unit covers scaling_governor" "$FAKEHOST/etc/systemd/system/epyc-host-prep.service" 'scaling_governor' 1
tgrep "F7 unit covers THP enabled" "$FAKEHOST/etc/systemd/system/epyc-host-prep.service" 'transparent_hugepage/enabled' 1
tgrep "F8 unit covers THP defrag"  "$FAKEHOST/etc/systemd/system/epyc-host-prep.service" 'transparent_hugepage/defrag' 1
if [[ -L "$FAKEHOST/etc/systemd/system/multi-user.target.wants/epyc-host-prep.service" ]]; then r=0; else r=1; fi
t "F9 enable symlink created" 0 "$r"
t "F10 --install-boot is idempotent (second run -> 0)" 0 "$(bootrun --install-boot)"
n=$(grep -c '^kernel\.perf_event_paranoid' "$FAKEHOST/etc/sysctl.d/99-epyc-inference.conf")
t "F11 idempotent: perf_event_paranoid line appears exactly once" 1 "$n"

echo
echo "=== G. MUTATE the installed boot artifacts -> --verify-boot must FAIL ==="
WANTS="$FAKEHOST/etc/systemd/system/multi-user.target.wants/epyc-host-prep.service"
# guard: if the artifact is not actually there, G1 would pass for the wrong reason
if sudo -n test -L "$WANTS"; then PASS=$((PASS+1)); echo "  [PASS] G0 symlink present before the G1 mutation (mutation is real)";
else FAIL=$((FAIL+1)); echo "  [FAIL] G0 symlink absent — G1 would be vacuous"; fi
sudo -n mv "$WANTS" "$ROOT/stash"
t "G1 unit disabled (symlink removed) -> verify 1" 1 "$(bootrun --verify-boot)"
sudo -n mv "$ROOT/stash" "$WANTS"
t "G1b restored -> verify 0 again" 0 "$(bootrun --verify-boot)"
sudo -n sed -i 's/^kernel\.perf_event_paranoid.*/# removed/' "$FAKEHOST/etc/sysctl.d/99-epyc-inference.conf"
t "G2 perf_event_paranoid line removed -> verify 1" 1 "$(bootrun --verify-boot)"
sudo -n sed -i 's/scaling_governor/REMOVED_KNOB/g' "$FAKEHOST/etc/systemd/system/epyc-host-prep.service"
t "G3 unit no longer covers governor -> verify 1" 1 "$(bootrun --verify-boot)"

echo
echo "=== H. REGRESSION: host-root resolution must not fall back to the overlay ==="
# The bug: /proc/1/root is root-traversable only, so an unprivileged `[[ -d ]]`
# probe returned false, resolve_host_root() fell back to "/", and --install-boot
# wrote the CONTAINER's /etc — reporting success while changing nothing at boot.
if [[ -e /.dockerenv ]]; then
  bash "$SCRIPT" --verify-boot >"$ROOT/h.out" 2>&1 || true
  tgrep "H1 containerised: resolves to the HOST root, not '/'" "$ROOT/h.out" "host root '/proc/1/root'" 1
  tgrep "H2 does NOT claim the container overlay is the host" "$ROOT/h.out" "host root '/'\$" 0
  # the host really does persist numa_balancing; if we were reading the overlay
  # this line would report DRIFT, so it doubles as a wrong-root detector
  tgrep "H3 sees the host's real numa_balancing persistence" "$ROOT/h.out" 'ok.*persists kernel\.numa_balancing' 1
else
  echo "  [skip] not containerised"
fi

echo
echo "============================================================"
echo "  host_prep.sh mutation tests:  PASS=$PASS  FAIL=$FAIL"
echo "============================================================"
[[ $PASS -gt 0 && $FAIL -eq 0 ]] || exit 1
exit 0
