#!/bin/bash
# Mutation test for the OBS-8 port-observation contract in
# scripts/session/start_orchestrator_test.sh.
#
# THE DEFECT (2026-09-15): the port gate probed with `netstat -tlnp 2>/dev/null`
# alone. `netstat` is not installed on this host, so the redirect swallowed
# "command not found" identically to "no output" — a MISSING TOOL read as an
# EMPTY PORT — and the script printed "[✓] Ports 8000 and 8080 available"
# UNCONDITIONALLY before launching a second llama-server/uvicorn on top of a
# live pair.
#
# THIS TEST NEVER EXECUTES `main` (which launches llama-server/uvicorn — forbidden
# by this task's absolute constraints, and by CLAUDE.md's zero-inference rule for
# this exact file). It sources start_orchestrator_test.sh — safe by construction,
# since every side effect lives inside `main`, gated by the BASH_SOURCE guard at
# the bottom of that file, so sourcing only defines osp_probe_tool/osp_port_pids/
# osp_port_state — then drives those against fake ss/netstat/lsof binaries placed
# on a curated PATH, mirroring scripts/nightshift/tests/test_inference_guard.sh's
# shim style.
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/start_orchestrator_test.sh"
TMP=$(mktemp -d /workspace/tmp/sub-obs/osp_test.XXXXXX 2>/dev/null || mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2', want '$3')"; fail=$((fail+1)); fi; }

# Every non-ss/netstat/lsof tool the sourced script (and env.sh, which it
# sources) needs at parse/source time. Deliberately EXCLUDES ss, netstat, lsof:
# each scenario below adds at most one of those back explicitly, so "not on
# this curated PATH" means exactly what the row describes ("netstat isn't
# installed"), not "the test forgot to shim something unrelated".
BASE_TOOLS="dirname basename git stat awk grep sed cut tr head sort printf env bash id readlink mkdir ls ln chmod find xargs date wc uname cat rm cp mv touch"
mkbase() {
  local dir="$1" c p
  mkdir -p "$dir"
  for c in $BASE_TOOLS; do
    p="$(command -v "$c" 2>/dev/null)" || continue
    ln -sf "$p" "$dir/$c"
  done
}

# run_fn <PATH dir> <shell to eval after sourcing> — a clean bash that sources
# the script (defining functions only — `main` never runs under `source`,
# since BASH_SOURCE[0] there is the script path while $0 stays "bash") and then
# evaluates the probe under test.
run_fn() {
  local path_override="$1" body="$2"
  env "PATH=${path_override}" bash -c "source '$SCRIPT'; $body" 2>&1
}

echo "== no tool on PATH -> cannot-observe (empty tool string) =="
mkbase "$TMP/notool"
out="$(run_fn "$TMP/notool" 'printf "TOOL=[%s]\n" "$(osp_probe_tool)"')"
chk "osp_probe_tool prints nothing when ss/netstat/lsof are all missing" "$out" "TOOL=[]"

echo
echo "== fake ss: port busy -> occupied =="
mkbase "$TMP/fakess"
cat > "$TMP/fakess/ss" <<'EOF'
#!/bin/bash
# Minimal `ss -tlnp` stand-in: one LISTEN line on :8080 held by pid 4242.
echo 'LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:(("llama-server",pid=4242,fd=13))'
EOF
chmod +x "$TMP/fakess/ss"
out="$(run_fn "$TMP/fakess" 'printf "TOOL=[%s]\n" "$(osp_probe_tool)"; printf "STATE8080=[%s]\n" "$(osp_port_state ss 8080)"; printf "STATE8000=[%s]\n" "$(osp_port_state ss 8000)"; printf "PIDS=[%s]\n" "$(osp_port_pids ss 8080)"')"
chk "osp_probe_tool prefers ss" "$(echo "$out" | grep -o 'TOOL=\[[^]]*\]')" "TOOL=[ss]"
chk "osp_port_state ss 8080 -> occupied" "$(echo "$out" | grep -o 'STATE8080=\[[^]]*\]')" "STATE8080=[occupied]"
chk "osp_port_state ss 8000 -> free (no line for it)" "$(echo "$out" | grep -o 'STATE8000=\[[^]]*\]')" "STATE8000=[free]"
chk "osp_port_pids ss 8080 -> extracts pid 4242" "$(echo "$out" | grep -o 'PIDS=\[[^]]*\]')" "PIDS=[4242]"

echo
echo "== fake netstat only (ss/lsof absent): tool fallback + occupied =="
mkbase "$TMP/fakenetstat"
cat > "$TMP/fakenetstat/netstat" <<'EOF'
#!/bin/bash
echo 'tcp        0      0 0.0.0.0:8000            0.0.0.0:*               LISTEN      9999/uvicorn'
EOF
chmod +x "$TMP/fakenetstat/netstat"
out="$(run_fn "$TMP/fakenetstat" 'printf "TOOL=[%s]\n" "$(osp_probe_tool)"; printf "STATE8000=[%s]\n" "$(osp_port_state netstat 8000)"; printf "PIDS=[%s]\n" "$(osp_port_pids netstat 8000)"')"
chk "osp_probe_tool falls back to netstat when ss is missing" "$(echo "$out" | grep -o 'TOOL=\[[^]]*\]')" "TOOL=[netstat]"
chk "osp_port_state netstat 8000 -> occupied" "$(echo "$out" | grep -o 'STATE8000=\[[^]]*\]')" "STATE8000=[occupied]"
chk "osp_port_pids netstat 8000 -> extracts pid 9999" "$(echo "$out" | grep -o 'PIDS=\[[^]]*\]')" "PIDS=[9999]"

echo
echo "== fake ss: both ports free -> pass path =="
cat > "$TMP/fakess/ss" <<'EOF'
#!/bin/bash
# No listeners at all.
exit 0
EOF
chmod +x "$TMP/fakess/ss"
out="$(run_fn "$TMP/fakess" 'printf "STATE8080=[%s]\n" "$(osp_port_state ss 8080)"; printf "STATE8000=[%s]\n" "$(osp_port_state ss 8000)"')"
chk "osp_port_state ss 8080 -> free" "$(echo "$out" | grep -o 'STATE8080=\[[^]]*\]')" "STATE8080=[free]"
chk "osp_port_state ss 8000 -> free" "$(echo "$out" | grep -o 'STATE8000=\[[^]]*\]')" "STATE8000=[free]"

echo
echo "== the gate's own refuse/pass decision — exactly the conditional 'main' uses =="
echo "   (source only; main() is never executed — see the header comment)"

# Case: no tool at all -> refuse (cannot-observe).
out="$(run_fn "$TMP/notool" '
  PORT_TOOL="$(osp_probe_tool)"
  if [[ -z "$PORT_TOOL" ]]; then echo DECISION=refuse-cannot-observe; else echo DECISION=BUG; fi
')"
chk "no port tool on PATH -> gate refuses (cannot-observe)" "$out" "DECISION=refuse-cannot-observe"

# Case: a tool exists and the port is occupied -> refuse.
cat > "$TMP/fakess/ss" <<'EOF'
#!/bin/bash
echo 'LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:(("llama-server",pid=4242,fd=13))'
EOF
chmod +x "$TMP/fakess/ss"
out="$(run_fn "$TMP/fakess" '
  PORT_TOOL="$(osp_probe_tool)"
  OCCUPIED=()
  for port in 8000 8080; do
    [[ "$(osp_port_state "$PORT_TOOL" "$port")" == "occupied" ]] && OCCUPIED+=("$port")
  done
  if (( ${#OCCUPIED[@]} > 0 )); then echo "DECISION=refuse-occupied:${OCCUPIED[*]}"; else echo DECISION=BUG; fi
')"
chk "tool present, 8080 occupied -> gate refuses" "$out" "DECISION=refuse-occupied:8080"

# Case: a tool exists and both ports are free -> pass.
cat > "$TMP/fakess/ss" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$TMP/fakess/ss"
out="$(run_fn "$TMP/fakess" '
  PORT_TOOL="$(osp_probe_tool)"
  OCCUPIED=()
  for port in 8000 8080; do
    [[ "$(osp_port_state "$PORT_TOOL" "$port")" == "occupied" ]] && OCCUPIED+=("$port")
  done
  if (( ${#OCCUPIED[@]} > 0 )); then echo DECISION=BUG; else echo DECISION=pass; fi
')"
chk "tool present, both ports free -> gate passes" "$out" "DECISION=pass"

echo
echo "== the auto-kill-by-port-derived-pid section is gone from the source =="
if grep -q "Stopping existing processes" "$SCRIPT"; then
  echo "  FAIL  script still contains the removed auto-kill section"; fail=$((fail+1))
else
  echo "  PASS  the auto-kill-by-port-derived-pid section is gone"; pass=$((pass+1))
fi
if grep -q "kill only PIDs you captured yourself\|kill <pid>" "$SCRIPT"; then
  echo "  PASS  refusal path tells the operator to kill manually themselves"; pass=$((pass+1))
else
  echo "  FAIL  no manual-kill operator instruction found in script"; fail=$((fail+1))
fi

echo
echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
