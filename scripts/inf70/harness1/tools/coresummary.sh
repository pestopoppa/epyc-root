#!/bin/bash
# Per-arm co-residency verdict. Reports DIRECT and SMT-SIBLING contention SEPARATELY --
# collapsing them is what produced the wrong "disjoint" label in the first place.
# NB: `grep -c` exits 1 on zero matches, so `|| echo 0` would append a SECOND line and
# corrupt the arithmetic. `|| true` keeps grep's own "0".
set -u
f=${1:-}
[ -n "$f" ] && [ -f "$f" ] || { echo "no coresidency file"; exit 0; }
c(){ grep -c "$1" "$f" 2>/dev/null || true; }
s=$(c '^==='); d=$(c 'DIRECT-OVERLAP'); m=$(c 'SMT-SIBLING-CONTENTION'); j=$(c 'DISJOINT-FROM-BENCH-CORES')
printf 'samples=%s direct_overlap=%s smt_sibling=%s disjoint=%s' "$s" "$d" "$m" "$j"
[ "$(( d + m ))" -gt 0 ] && printf '  <-- CONTENDED WINDOW'
echo
