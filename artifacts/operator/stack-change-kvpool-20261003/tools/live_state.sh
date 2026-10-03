#!/bin/bash
# live_state.sh — read-only snapshot of the live :8083 process (no signals, no POSTs).
set -uo pipefail
PID="${1:-3793153}"
echo "taken_at $(date -u +%FT%TZ)"
echo "== listener"; ss -ltnp 'sport = :8083' 2>/dev/null | tail -n +2 | cut -c1-120
echo "== pid $PID"; ps -o pid=,lstart=,etime= -p "$PID"
echo "exe: $(readlink "/proc/$PID/exe")"
echo "argv: $(tr '\0' ' ' < "/proc/$PID/cmdline")"
echo "== VRAM (read-only sysfs)"
for i in 1 2; do
  echo "$(date -u +%T) card2 mem_info_vram_used=$(cat /sys/class/drm/card2/device/mem_info_vram_used) total=$(cat /sys/class/drm/card2/device/mem_info_vram_total)"
  for d in /sys/class/kfd/kfd/proc/*/; do
    p=$(basename "$d"); echo "   kfd pid=$p comm=$(ps -o comm= -p "$p") vram=$(cat "$d"/vram_* 2>/dev/null | head -1)"
  done
  [ "$i" = 1 ] && sleep 5
done
echo "== GET /props (read-only)"
curl -s --max-time 3 http://127.0.0.1:8083/props | /usr/bin/python3 -c 'import json,sys; d=json.load(sys.stdin); print({"total_slots": d.get("total_slots"), "default_generation_settings.n_ctx": d.get("default_generation_settings",{}).get("n_ctx")})'
echo "== last load block of logs/llama-server-8083.log"
grep -n -E "n_ctx_slot|block_size=|clamping|exceeds the training" /mnt/raid0/llm/epyc-orchestrator/logs/llama-server-8083.log | tail -4 | cut -c1-200
