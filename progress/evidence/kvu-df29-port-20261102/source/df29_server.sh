#!/bin/bash
# DF2-9 server-based reproducer (GPU). Run ONLY inside an exclusive GPU window.
#
# usage: df29_server.sh <arm_build_dir> <out_dir> [--arm X] [--configs orig,prod] [--cap SEC] [--port P]
#                       [--max-tokens N] [--n-orig N] [--no-long] [--ctx N] [--np N] [--no-pin]
#                       [--target-only] [--restarts N]
#   <arm_build_dir>  e.g. /mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-B (needs bin/llama-server)
#                    or  /mnt/raid0/llm/tmp/v11-fa-ab-20261004/build-master-11fe02151 (arm M)
#
# Two server configs per arm (each a fresh server process on a private port):
#   orig  the 2026-08-27 DF2-9 command (df2_bisect.sh / df2_req_bisect.sh): -np 1 -c 32768 -t 8 -tb 8
#         -b 2048 -ub 2048 -ctk f16 -ctv f16 -ngl 99 -ngld 99 -fa on, DFlash2 n-max 8, no --jinja file;
#         prompts: 25-char control FIRST, then the 12 pinned olympiadbench prompts; sampling as the
#         DF2-5 runner (temp 0.6, top_p 0.95, top_k 20, seed 42, enable_thinking=false).
#   prod  the live :8083 recipe (q8_0 K/V, --kv-unified, -ub 2048, -ngl all, --no-mmap, --jinja +
#         epyc-qwen3x-v1-terse template, DFlash2 n-max 7, both devices ROCm0, numactl/taskset 184-191)
#         with -np 1 -c 8192 and --cache-ram 0 (no slot-save path); prompts: control, the 12, and two
#         synthetic ~2k-token prompts; greedy (temperature 0, top_k 1).
#
# Signals per request (primary first): server-log "non-finite target features" (champion fork guard,
# common/speculative.cpp:1542), "failed to process speculative batch", HTTP status, garbage text
# ("!!!!" = NaN-logits signature, empty), drafter acceptance. Upstream master has NO non-finite guard,
# so for arm M the garbage/acceptance signals carry the verdict (printed as guard=absent).
#
# Verdict line per (arm, config):
#   DF29 arm=B config=orig mode=dflash2 guard=present verdict=FAIL k=12/13 tested=13/13 control=OK ...
#   PASS = every planned prompt tested and finite; FAIL = k of tested prompts non-finite; ERROR = could not run.
#
# Hygiene: refuses a busy port; VRAM preflight; owns and kills exactly its own PIDs (trap; TERM->KILL->ps -p);
# env -u LD_LIBRARY_PATH + LD_LIBRARY_PATH=<arm>/bin:/opt/rocm/lib; verify_ggml_linkage.sh on the binary and
# /proc/<pid>/maps of the running server; VRAM sampled every second during the run; hard wall cap per arm.
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/df29_lib.sh"

[ $# -ge 2 ] || { sed -n 2,12p "$0"; exit 2; }
ARMDIR=$(readlink -f "$1"); OUT=$2; shift 2
ARM=""; CONFIGS="orig,prod"; CAP=300; PORT=auto; MAXTOK=32; NORIG=12; LONG=1; CTX=8192; NP=1
TARGET_ONLY=0; RESTARTS=2; LOAD_CAP=150; SELECT_PORT_ONLY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --arm) ARM=$2; shift 2 ;;
        --configs) CONFIGS=$2; shift 2 ;;
        --cap) CAP=$2; shift 2 ;;
        --port) PORT=$2; shift 2 ;;
        --select-port-only) SELECT_PORT_ONLY=1; shift ;;
        --max-tokens) MAXTOK=$2; shift 2 ;;
        --n-orig) NORIG=$2; shift 2 ;;
        --no-long) LONG=0; shift ;;
        --ctx) CTX=$2; shift 2 ;;
        --np) NP=$2; shift 2 ;;
        --no-pin) export DF29_PIN=0; shift ;;
        --target-only) TARGET_ONLY=1; shift ;;
        --restarts) RESTARTS=$2; shift 2 ;;
        --load-cap) LOAD_CAP=$2; shift 2 ;;
        *) echo "unknown arg $1"; exit 2 ;;
    esac
done
# A probe is not a reservation; the busy check and normal startup refusal remain.
if ! PORT=$(python3 "$DF29_DIR/port_selection.py" --port "$PORT" \
    --first "${DF29_PORT_FIRST:-18093}" --last "${DF29_PORT_LAST:-18192}"); then
    echo "DF29 arm=${ARM:-?} config=- verdict=ERROR reason=no-free-port" >&2
    exit 2
fi
if [ "$SELECT_PORT_ONLY" = 1 ]; then printf '%s\n' "$PORT"; exit 0; fi
BIN=$ARMDIR/bin
[ -x "$BIN/llama-server" ] || { echo "DF29 arm=${ARM:-?} config=- verdict=ERROR reason=no-llama-server-in-$BIN"; exit 2; }
if [ -z "$ARM" ]; then
    case "$(basename "$ARMDIR")" in
        build-master-*) ARM=M ;;
        *-[A-Z]) ARM=${ARMDIR##*-} ;;
        *) ARM=$(basename "$ARMDIR") ;;
    esac
fi
mkdir -p "$OUT"
OUT=$(readlink -f "$OUT")
T0=$(date +%s); DEADLINE=$((T0 + CAP))
VERDICTS="$OUT/verdicts.txt"; : > "$VERDICTS"

trap 'df29_cleanup' EXIT
trap 'echo "signal: cleaning up"; df29_cleanup; exit 130' INT TERM

exec > >(tee -a "$OUT/df29_server.log") 2>&1
df29_log "DF29 arm=$ARM dir=$ARMDIR out=$OUT cap=${CAP}s configs=$CONFIGS port=$PORT"

if df29_port_busy "$PORT"; then
    echo "DF29 arm=$ARM config=- verdict=ERROR reason=port-$PORT-busy" | tee -a "$VERDICTS"; exit 2
fi
if ! df29_vram_preflight > "$OUT/vram_preflight.txt"; then
    cat "$OUT/vram_preflight.txt"
    echo "DF29 arm=$ARM config=- verdict=ERROR reason=vram-preflight" | tee -a "$VERDICTS"; exit 2
fi
cat "$OUT/vram_preflight.txt"

# provenance + linkage
{
    echo "arm=$ARM dir=$ARMDIR"
    if [ -f "$ARMDIR/PROVENANCE.md" ]; then grep -E 'source|CMakeCache|VERDICT|version' "$ARMDIR/PROVENANCE.md" | head -12 || true; fi
    grep -E '^GGML_HIP_ROCWMMA_FATTN:' "$ARMDIR/CMakeCache.txt" 2>/dev/null || true
    sha256sum "$BIN/llama-server" "$BIN/libggml-hip.so" 2>/dev/null || true
} > "$OUT/provenance.txt"
env -u LD_LIBRARY_PATH bash "$DF29_LINKAGE" "$BIN/llama-server" "$ARMDIR" > "$OUT/linkage.txt" 2>&1 || true
env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$BIN:/opt/rocm/lib" bash "$DF29_LINKAGE" "$BIN/llama-server" "$ARMDIR" > "$OUT/linkage_withpath.txt" 2>&1 || true
tail -2 "$OUT/linkage.txt"

DF29_MMAP_FLAG=(); DF29_HAS_DFLASH=0; DF29_HAS_NONFINITE_CHECK=0
df29_probe_flags "$BIN"
GUARD=$([ "$DF29_HAS_NONFINITE_CHECK" = 1 ] && echo present || echo absent)
df29_log "flags: mmap=[${DF29_MMAP_FLAG[*]}] dflash=$DF29_HAS_DFLASH nonfinite_guard=$GUARD"

PROMPTS=$DF29_DIR/prompts/server_prompts.json
df29_start_sampler "$OUT/vram_samples.txt"
# hard wall cap: a watchdog we own TERMs this script (-> trap -> kills the server) at CAP+60 s
df29_start_watchdog $((CAP + 60)) df29_server.sh

config_args() {  # $1=config $2=mode(dflash2|target-only)
    local cfg=$1 mode=$2 a=()
    if [ "$cfg" = orig ]; then
        a=(-m "$DF29_TARGET" -np 1 -c 32768 -t 8 -tb 8 -b 2048 -ub 2048 -ctk f16 -ctv f16
           --device ROCm0 -ngl 99 -fa on --metrics --slots)
        [ "$mode" = dflash2 ] && a+=(-md "$DF29_DRAFTER" --spec-type draft-dflash --spec-draft-n-max 8 -ngld 99)
    else
        a=(-m "$DF29_TARGET" -np "$NP" -c "$CTX" -t 8 -ub 2048 --flash-attn on --jinja -ctk q8_0 -ctv q8_0
           --kv-unified "${DF29_MMAP_FLAG[@]}" -ngl all --cache-ram 0 --chat-template-file "$DF29_TEMPLATE"
           --device ROCm0 --metrics --slots)
        [ "$mode" = dflash2 ] && a+=(-md "$DF29_DRAFTER" -ngld 99 --spec-type draft-dflash --spec-draft-n-max 7 --device-draft ROCm0)
    fi
    printf '%s\n' "${a[@]}"
}

run_config() {  # $1 = orig|prod  $2 = this config's deadline (epoch s)
    local cfg=$1 cdir="$OUT/$1" mode kinds sampling n_plan start=0 restarts=0 deaths=0 crc hrc log args
    local DEADLINE=$2
    mkdir -p "$cdir"; : > "$cdir/requests.jsonl"
    mode=dflash2
    { [ "$TARGET_ONLY" = 1 ] || [ "$DF29_HAS_DFLASH" = 0 ]; } && mode=target-only
    if [ "$cfg" = orig ]; then kinds=control,orig; sampling=orig; else kinds=control,orig; sampling=greedy; fi
    [ "$cfg" = prod ] && [ "$LONG" = 1 ] && kinds=$kinds,long2k
    # cap the 12 orig prompts at --n-orig (keep the control and long ones)
    python3 - "$PROMPTS" "$cdir/prompts.json" "$kinds" "$NORIG" <<'PY'
import json, sys
src, dst, kinds, norig = sys.argv[1], sys.argv[2], set(sys.argv[3].split(",")), int(sys.argv[4])
items, n = [], 0
for it in json.load(open(src)):
    if it["kind"] not in kinds: continue
    if it["kind"] == "orig":
        if n >= norig: continue
        n += 1
    items.append(it)
# order: control first (must pass), then the long ~2k prompts (most diagnostic), then the 12 originals
rank = {"control": 0, "long2k": 1, "orig": 2}
items.sort(key=lambda it: rank[it["kind"]])
json.dump(items, open(dst, "w"), indent=1)
PY
    n_plan=$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$cdir/prompts.json")

    while :; do
        if [ $((DEADLINE - $(date +%s))) -lt 30 ]; then df29_log "$cfg: arm deadline reached before (re)start"; break; fi
        log="$cdir/server.$restarts.log"
        mapfile -t args < <(config_args "$cfg" "$mode")
        df29_log "$cfg: start server ($mode) try=$restarts"
        df29_start_server "$BIN" "$log" "$PORT" "${args[@]}"
        local hdl=$(( $(date +%s) + LOAD_CAP )); [ "$hdl" -gt "$DEADLINE" ] && hdl=$DEADLINE
        set +e; df29_wait_health "$PORT" "$hdl"; hrc=$?; set -e
        if [ "$hrc" -ne 0 ]; then
            df29_log "$cfg: server not healthy (rc=$hrc); tail of log:"; tail -15 "$log" | sed 's/^/    /'
            df29_stop_server
            if [ "$hrc" -ne 3 ] && [ "$mode" = dflash2 ] && [ "$ARM" = M ] && [ "$restarts" -eq 0 ]; then
                df29_log "$cfg: arm M could not start with the DFlash2 drafter -> falling back to target-only"
                mode=target-only; restarts=$((restarts + 1)); continue
            fi
            echo "DF29 arm=$ARM config=$cfg mode=$mode guard=$GUARD verdict=ERROR reason=server-start-rc$hrc" | tee -a "$VERDICTS"
            return 0
        fi
        df29_log "$cfg: healthy after $(( $(date +%s) - T0 ))s since arm start; pid=$DF29_SERVER_PID"
        df29_server_maps "$DF29_SERVER_PID" > "$cdir/server_maps.$restarts.txt" || true
        grep -E 'libggml-hip|libllama\.so' "$cdir/server_maps.$restarts.txt" | sed 's/^/    maps: /' || true
        echo "$(date +%s) $(df29_vram_used)" > "$cdir/vram_after_load.$restarts.txt"
        grep -m3 -E 'DFlash|n_extract|target_layer|flash_attn|ROCm0 model buffer' "$log" | sed 's/^/    log: /' || true

        set +e
        python3 "$DF29_DIR/df29_client.py" --mode seq --port "$PORT" --pid "$DF29_SERVER_PID" --log "$log" \
            --prompts "$cdir/prompts.json" --out "$cdir" --sampling "$sampling" --max-tokens "$MAXTOK" \
            --req-timeout 60 --deadline "$DEADLINE" --start "$start" &
        local cpid=$!; DF29_PIDS+=("$cpid")
        wait "$cpid"; crc=$?
        set -e
        df29_stop_server
        [ "$crc" -eq 10 ] && deaths=$((deaths + 1))
        if [ "$crc" -eq 10 ] && [ "$restarts" -lt "$RESTARTS" ]; then
            start=$(cat "$cdir/resume_at"); restarts=$((restarts + 1))
            df29_log "$cfg: server died mid-run; restarting from prompt $start (restart $restarts/$RESTARTS)"
            continue
        fi
        break
    done

    # verdict for this config
    python3 - "$cdir" "$n_plan" "$ARM" "$cfg" "$mode" "$GUARD" "$VERDICTS" "$deaths" <<'PY'
import json, sys, glob, re
cdir, n_plan, arm, cfg, mode, guard, vfile, deaths = sys.argv[1], int(sys.argv[2]), *sys.argv[3:]
rows = [json.loads(l) for l in open(f"{cdir}/requests.jsonl") if l.strip()]
tested = len(rows)
bad = [r for r in rows if not r["finite_ok"]]
nf = sum(r["log_nonfinite"] for r in rows)
san = sum(r["log_sanitized"] for r in rows)
gar = sum(1 for r in rows if r["garbage"])
http_err = sum(1 for r in rows if r["http"] != 200)
ctrl = next((r for r in rows if r["kind"] == "control"), None)
ctrl_s = "untested" if ctrl is None else ("OK" if ctrl["finite_ok"] else "BAD")
long_bad = sum(1 for r in rows if r["kind"] == "long2k" and not r["finite_ok"])
dn = sum(r["draft_n"] or 0 for r in rows); da = sum(r["draft_n_accepted"] or 0 for r in rows)
acc = f"{da/dn:.3f}" if dn else "NA"
tps = [r["predicted_per_second"] for r in rows if r["finite_ok"] and r["predicted_per_second"]]
tps_s = f"{sum(tps)/len(tps):.1f}" if tps else "NA"
logs = sorted(glob.glob(f"{cdir}/server.*.log"))
specfail = sum(len(re.findall(r"failed to process speculative batch", open(p, errors="replace").read())) for p in logs)
aborts = sum(len(re.findall(r"terminate called|GGML_ASSERT|GGML_ABORT|Aborted", open(p, errors="replace").read())) for p in logs)
reason = ""
if tested == 0:
    verdict = "ERROR"; reason = " reason=nothing-tested(load-fail-or-deadline)"
elif bad:
    verdict = "FAIL"
elif tested < n_plan:
    verdict = "INCOMPLETE"
else:
    verdict = "PASS"
line = (f"DF29 arm={arm} config={cfg} mode={mode} guard={guard} verdict={verdict} k={len(bad)}/{tested} "
        f"tested={tested}/{n_plan} control={ctrl_s} long2k_bad={long_bad} nonfinite_log={nf} sanitized_log={san} "
        f"garbage={gar} http_err={http_err} spec_fail_logs={specfail} abort_logs={aborts} server_deaths={deaths} "
        f"acceptance={acc} mean_tg_tps={tps_s}{reason}"
        + (" note=k-bounded-by-server-deaths(see-probe-for-full-N)" if int(deaths) > 0 and tested < n_plan else ""))
print(line)
open(vfile, "a").write(line + "\n")
PY
}

# the arm cap is split evenly across configs so a crash-looping first config cannot starve the second
IFS=',' read -r -a CFG_LIST <<< "$CONFIGS"
NCFG=${#CFG_LIST[@]}; i=0
for c in "${CFG_LIST[@]}"; do
    i=$((i + 1))
    case "$c" in orig|prod) run_config "$c" $((T0 + CAP * i / NCFG)) ;; *) echo "unknown config $c" ;; esac
done

df29_kill_pid "$DF29_SAMPLER_PID" 5 || true
read -r PEAK BASE < <(awk 'NR==1{b=$2} {if($2>m)m=$2} END{if(NR==0) print "NA NA"; else printf "%.2f %.2f\n", m/1073741824, b/1073741824}' "$OUT/vram_samples.txt")
WALL=$(( $(date +%s) - T0 ))
df29_log "arm $ARM done in ${WALL}s; VRAM peak ${PEAK} GiB (baseline ${BASE} GiB) — residency proof: peak-baseline must be >= ~29 GiB"
sed -i "s/\$/ vram_peak_gib=${PEAK} vram_base_gib=${BASE} arm_wall=${WALL}s/" "$VERDICTS"
echo "== verdicts ($OUT/verdicts.txt)"
cat "$VERDICTS"
