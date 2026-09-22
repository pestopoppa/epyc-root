#!/bin/bash
# STEPS 2-3: assert the candidate is PROMOTABLE. Mechanical assertions only -- no eyeballing.
# usage: preflight.sh <build-dir> <backend>
set -uo pipefail
BUILD="${1:?usage: preflight.sh <build-dir> <backend>}"; B="${2:?}"
K=/mnt/raid0/llm/kernels; RC=0
BIN="$BUILD/bin/llama-server"
[ -x "$BIN" ] || { echo "FAIL: no llama-server in $BUILD/bin"; exit 1; }

echo "== RUNPATH =="
RP=$(readelf -d "$BIN" | awk -F'[][]' '/RUNPATH/{print $2}')
# Split on ':' WITHOUT letting the shell eat a trailing/leading/double empty element --
# `tr ':' '\n'` silently drops a trailing one, which is the very defect this asserts against.
BAD=$(printf '%s' "$RP" | awk -F: '{for(i=1;i<=NF;i++) print "[" $i "]"}' \
      | grep -vxE '\[\$ORIGIN\]|\[/opt/rocm/lib\]' || true)
if [ -n "$BAD" ]; then
  echo "  FAIL: non-relocatable or EMPTY RUNPATH element(s):"
  echo "$BAD" | sed 's/^/     /'
  echo "     An ABSOLUTE element pins the binary to its build dir, so a scratch build cannot be"
  echo "     promoted at all. An EMPTY element makes the loader also search the CWD."
  echo "     NOTE: grep RUNPATH | grep ORIGIN passes on '/abs/path:\$ORIGIN' and is not a check."
  RC=1
else
  echo "  OK: $(readelf -d "$BIN" | grep -oE 'Library runpath.*')"
fi

echo "== standalone linkage (LD_LIBRARY_PATH UNSET) =="
if env -u LD_LIBRARY_PATH bash \
   /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$BIN" "$BUILD/bin" \
   2>&1 | grep -q '^PASS'; then echo "  OK"
else echo "  FAIL: ggml does not resolve inside the build dir without help"; RC=1; fi

echo "== binary-set parity vs the rollback anchor =="
ANCHOR=$(ls -dt "$K"/archive/"$B"-* 2>/dev/null | head -1)
if [ -z "$ANCHOR" ]; then
  echo "  FAIL: no anchor for '$B' -- run anchor.sh first (parity has nothing to compare against)"
  RC=1
else
  exe(){ find "$1" -maxdepth 1 -type f -perm -u+x ! -name '*.so*' -printf '%f\n' | sort; }
  MISSING=$(comm -23 <(exe "$ANCHOR/bin") <(exe "$BUILD/bin"))
  if [ -n "$MISSING" ]; then
    echo "  FAIL: present in the incumbent, ABSENT from the candidate:"
    echo "$MISSING" | sed 's/^/     /'
    echo "     A partial --target produces a kernel that passes every other check and then fails at"
    echo "     LAUNCH: executor.py resolves llama-completion / llama-speculative / llama-lookup /"
    echo "     llama-mtmd-cli through the store. (2026-09-22: 2 binaries promoted where the"
    echo "     incumbent shipped 92; the store verifier passed it because it checked llama-server.)"
    echo "     Compare EXECUTABLES only -- sonames are versioned and always differ."
    RC=1
  else
    echo "  OK: nothing the incumbent ships is missing from the candidate"
  fi
fi
[ "$RC" = 0 ] && echo "PREFLIGHT PASS" || echo "PREFLIGHT FAIL"
exit $RC
