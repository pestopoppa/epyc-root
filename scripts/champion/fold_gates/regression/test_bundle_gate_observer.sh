#!/bin/bash
# Synthetic observer regressions through each runnable gate's real dry-run preflight.
set -euo pipefail
HERE=$(cd -- "$(dirname -- "$0")/.." && pwd)
SELECTED=${1:-all}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/campaigns/ak-ds41-fixture/store" "$TMP/proc" "$TMP/alerts"

cat > "$TMP/bin/ps" <<'SH'
#!/bin/sh
case "${PS_FIXTURE_MODE:-absent}" in
    absent) printf '%s\n' "$$ synthetic-ps" ;;
    present) printf '%s\n' "555 python -m scripts.kernel_rnd.autokernel.loop.run --store /synthetic/ak-ds41-cpu-decode/store" ;;
    empty) exit 0 ;;
    fail) exit 2 ;;
    *) exit 64 ;;
esac
SH
cat > "$TMP/bin/python3" <<'SH'
#!/bin/sh
[ "${1:-}" = "-" ] && exit 0
printf '%s\n' launched > "$PYTHON_FIXTURE_MARKER"
exit 0
SH
chmod +x "$TMP/bin/ps"
chmod +x "$TMP/bin/python3"

cat > "$TMP/bin/region-lock" <<'SH'
#!/bin/bash
while [[ $# -gt 0 && "$1" != -- ]]; do shift; done
[[ "${1:-}" == -- ]] || exit 64
shift
[[ $# -ge 2 && "$1" == /bin/bash ]] || exit 64
printf '%s\n' "$2" > "$LOCK_TARGET_MARKER"
exec "$@"
SH
chmod +x "$TMP/bin/region-lock"

write_status() {
    local mode=$1
    /usr/bin/python3 -I - "$TMP/campaigns/ak-ds41-fixture/store" "$mode" <<'PY'
import json
import os
from pathlib import Path
import sys
store = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
status_path = store / "loop-status.json"
if mode == "missing":
    status_path.unlink(missing_ok=True)
    raise SystemExit(0)
if mode == "legacy":
    status_path.write_text(json.dumps({"schema": "epyc.autokernel.loop_status.v1",
                                      "state": "running"}) + "\n")
    raise SystemExit(0)
if mode == "present":
    pid = os.getppid()
    raw = Path(f"/proc/{pid}/stat").read_text()
    start_ticks = int(raw[raw.rfind(")") + 2:].split()[19])
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
else:
    pid, start_ticks, boot_id = 2147483647, 123, "fixture-boot"
body = {
    "schema": "epyc.autokernel.loop_status.v1",
    "state": "running",
    "process_identity": {
        "schema": "epyc.autokernel.loop_process_identity.v1",
        "pid": pid,
        "start_ticks": start_ticks,
        "boot_id": boot_id,
        "source_identity": "scripts.kernel_rnd.autokernel.loop.run",
        "store_path": str(store),
    },
}
status_path.write_text(json.dumps(body) + "\n")
PY
}

run_observe() {
    local gate=$1 ps_mode=$2 identity_mode=$3 want_state=$4 want_rc=$5
    local gate_name=${gate##*/}; gate_name=${gate_name%.sh}
    write_status "$identity_mode"
    local proc_root=/proc boot_id=/proc/sys/kernel/random/boot_id
    if [[ "$identity_mode" == absent ]]; then
        proc_root="$TMP/proc"
        boot_id="$TMP/boot_id"
        printf 'fixture-boot\n' > "$boot_id"
    elif [[ "$identity_mode" == proc-missing || "$identity_mode" == proc-file ]]; then
        proc_root="$TMP/proc-missing"
        [[ "$identity_mode" == proc-missing ]] || { proc_root="$TMP/proc-not-directory"; : > "$proc_root"; }
        boot_id="$TMP/boot_id"
        printf 'fixture-boot\n' > "$boot_id"
    fi
    local marker="$TMP/${gate_name}.instrument.launched"
    rm -f "$marker"
    local rc=0 output
    output=$(env PATH="$TMP/bin:$PATH" PS_FIXTURE_MODE="$ps_mode" \
        OG_LOOP_CAMPAIGNS_ROOT="$TMP/campaigns" OG_PROC_ROOT="$proc_root" \
        OG_BOOT_ID_PATH="$boot_id" OG_STATE_DIR="$TMP/alerts" \
        PYTHON_FIXTURE_MARKER="$marker" \
        C3_GATE_DIR="$TMP/c3" C4_GATE_DIR="$TMP/c4" C5_GATE_DIR="$TMP/c5" \
        bash "$gate" observe 2>&1) || rc=$?
    [[ "$rc" -eq "$want_rc" ]] || { printf '%s --observe rc=%s expected %s\n%s\n' "$gate_name" "$rc" "$want_rc" "$output" >&2; return 1; }
    [[ "$output" == *"state=$want_state"* ]] || { printf '%s --observe state expected %s\n%s\n' "$gate_name" "$want_state" "$output" >&2; return 1; }

    rc=0
    local items=()
    [[ "$gate_name" == bundle_gate_c4 ]] && items=(--items c)
    [[ "$gate_name" == bundle_gate_c5 ]] && items=(--items b)
    rm -f "$marker"
    output=$(env PATH="$TMP/bin:$PATH" PS_FIXTURE_MODE="$ps_mode" \
        OG_LOOP_CAMPAIGNS_ROOT="$TMP/campaigns" OG_PROC_ROOT="$proc_root" \
        OG_BOOT_ID_PATH="$boot_id" OG_STATE_DIR="$TMP/alerts" \
        PYTHON_FIXTURE_MARKER="$marker" \
        C3_GATE_DIR="$TMP/c3" C4_GATE_DIR="$TMP/c4" C5_GATE_DIR="$TMP/c5" \
        bash "$gate" --dry-run "${items[@]}" 2>&1) || rc=$?
    if [[ "$want_state" == absent ]]; then
        [[ "$rc" -eq 0 && -e "$marker" ]] || { printf '%s absent preflight did not reach synthetic instrument (rc=%s)\n%s\n' "$gate_name" "$rc" "$output" >&2; return 1; }
    else
        [[ "$rc" -eq 3 && ! -e "$marker" ]] || { printf '%s %s preflight did not refuse before synthetic instrument (rc=%s)\n%s\n' "$gate_name" "$want_state" "$rc" "$output" >&2; return 1; }
    fi
}

run_execute_handoff() {
    local gate=$1 ps_mode=$2 identity_mode=$3
    local gate_name=${gate##*/}; gate_name=${gate_name%.sh}
    local item=b
    [[ "$gate_name" == bundle_gate_c4 ]] && item=c
    local gate_dir="$TMP/$gate_name" lock_target="$TMP/lock-target" marker="$TMP/$gate_name.instrument.launched"
    mkdir -p "$gate_dir/slots"
    date -u -d '2 minutes ago' +%Y-%m-%dT%H:%M:%SZ > "$gate_dir/slots/$item.slot"
    date -u -d '20 minutes' +%Y-%m-%dT%H:%M:%SZ >> "$gate_dir/slots/$item.slot"
    write_status "$identity_mode"
    local proc_root=/proc boot_id=/proc/sys/kernel/random/boot_id
    if [[ "$identity_mode" == absent ]]; then
        proc_root="$TMP/proc"
        boot_id="$TMP/boot_id"
        printf 'fixture-boot\n' > "$boot_id"
    fi
    rm -f "$lock_target" "$marker"
    local lock_var gate_dir_var
    case "$gate_name" in
        bundle_gate_c3) lock_var=C3_REGION_LOCK; gate_dir_var=C3_GATE_DIR ;;
        bundle_gate_c4) lock_var=C4_REGION_LOCK; gate_dir_var=C4_GATE_DIR ;;
        bundle_gate_c5) lock_var=C5_REGION_LOCK; gate_dir_var=C5_GATE_DIR ;;
    esac
    local rc=0 output
    output=$(env PATH="$TMP/bin:$PATH" PS_FIXTURE_MODE="$ps_mode" \
        OG_LOOP_CAMPAIGNS_ROOT="$TMP/campaigns" OG_PROC_ROOT="$proc_root" \
        OG_BOOT_ID_PATH="$boot_id" OG_STATE_DIR="$TMP/alerts" \
        LOCK_TARGET_MARKER="$lock_target" PYTHON_FIXTURE_MARKER="$marker" \
        "$lock_var"="$TMP/bin/region-lock" "$gate_dir_var"="$gate_dir" \
        bash "$gate" --execute --items "$item" --lock-timeout-s 1 2>&1) || rc=$?
    [[ "$rc" -eq 3 ]] || { printf '%s --execute handoff rc=%s expected observer refusal 3\n%s\n' "$gate_name" "$rc" "$output" >&2; return 1; }
    [[ -r "$lock_target" && "$(cat "$lock_target")" == "$(readlink -f -- "$gate")" ]] || {
        printf '%s region-lock did not receive the resolved tracked script path\n%s\n' "$gate_name" "$output" >&2
        return 1
    }
    [[ ! -e "$marker" ]] || { printf '%s launched instrument after blind re-exec\n%s\n' "$gate_name" "$output" >&2; return 1; }
}

GATES=("$HERE/bundle_gate_c3.sh" "$HERE/bundle_gate_c4.sh" "$HERE/bundle_gate_c5.sh")
if [[ "$SELECTED" != all ]]; then
    selected_name=$(basename -- "$SELECTED")
    GATES=("$HERE/$selected_name")
    [[ "$selected_name" == bundle_gate_c3.sh || "$selected_name" == bundle_gate_c4.sh \
        || "$selected_name" == bundle_gate_c5.sh ]] || { echo "invalid gate selection: $SELECTED" >&2; exit 64; }
fi
for gate in "${GATES[@]}"; do
    run_observe "$gate" absent absent absent 1
    run_observe "$gate" present present present 0
    run_observe "$gate" absent present unobservable 3
    run_observe "$gate" fail absent unobservable 3
    run_observe "$gate" present absent unobservable 3
    run_observe "$gate" empty absent unobservable 3
    run_observe "$gate" absent legacy unobservable 3
    run_observe "$gate" absent missing unobservable 3
    run_observe "$gate" absent proc-missing unobservable 3
    run_observe "$gate" absent proc-file unobservable 3
    run_execute_handoff "$gate" absent present
    run_execute_handoff "$gate" present absent
    run_execute_handoff "$gate" empty absent
done

printf 'bundle gate observer: %s gate(s) x 10 observe states plus 3 execute handoffs each PASS; only fully observed absence reached the synthetic instrument\n' "${#GATES[@]}"
