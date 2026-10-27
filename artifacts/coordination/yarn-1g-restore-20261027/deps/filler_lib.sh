#!/bin/bash
# Sourced by filler jobs. fl_wait_own_port PORT PID [maxsecs=1200]: success only if /health answers AND
# the LISTEN socket on PORT is owned by PID (a foreign server once answered a health probe on this host).
fl_wait_own_port() {
  local port=$1 pid=$2 max=${3:-1200} t=0
  while [ $t -lt "$max" ]; do
    [[ "$pid" == "${YG_OWN_PID:-}" ]] && owned_match "$pid" "$YG_OWN_BIRTH" "$YG_OWN_PGID" || { echo "server identity mismatch"; return 6; }
    if curl -sf "http://127.0.0.1:$port/health" >/dev/null && ss -ltnp "sport = :$port" | grep "pid=$pid," >/dev/null; then
      echo "health ok, port $port owned by our pid $pid"; return 0; fi
    [ -n "${FILLER_END:-}" ] && [ "$(date -u +%s)" -ge "$FILLER_END" ] && break
    sleep 5; t=$((t+5))
  done
  echo "health/own-pid proof failed port=$port pid=$pid"; return 7
}
fl_register_pid() { echo "$1" >> "${FILLER_PIDFILE:?}"; }
fl_time_left() { echo $(( ${FILLER_DEADLINE:?} - $(date -u +%s) )); }
fl_should_stop() { [ -e "${FILLER_STOPFILE:?}" ] || [ "$(date -u +%s)" -ge "${FILLER_DEADLINE:?}" ]; }
