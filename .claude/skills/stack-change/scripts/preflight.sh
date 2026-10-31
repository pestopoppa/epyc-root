#!/bin/bash
# preflight.sh — phase 3. Run EVERY gate once and emit ONE classified list.
#
# WHY ONE LIST. On 2026-09-22 the cutover was done by running a gate, reading
# its single error, fixing it, and running again -- nine times in sixteen
# minutes with the stack down. Each error was real; none of them told you about
# the next one. The cost is not the fixing, it is the serialisation.
#
# The classification is the load-bearing part. A violation is one of three
# things, and they have different owners:
#
#   fixable-by-transform  the transform missed a surface -> go back to phase 2
#   needs-measurement     a model newly holds a role and has no evidence for it
#                         -> phase 4 RUNS the suite. It does not offer a waiver.
#   needs-operator        a genuine choice: a context/quality tradeoff, a waiver,
#                         a deletion. Phase 6 territory, never decided here.
#
# `--allow-known-gaps` is deliberately NOT used here. A gap is a thing to
# measure or a thing to decide, and printing it as a blocker is how it stays
# visible long enough to become one of those.
set -uo pipefail

ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
PY="${PYTHON:-$ORCH/.venv/bin/python}"
NUMA="${NUMA_MODE:-both}"
OUT="${1:-/mnt/raid0/llm/tmp/stack-change-preflight-$(date -u +%Y%m%dT%H%M%SZ).txt}"

[ -x "$PY" ] || { echo "REFUSING: orchestrator venv missing at $PY" >&2; exit 2; }
[ -f "$ORCH/scripts/registry/stack_change_pipeline.py" ] || {
  echo "REFUSING: complete orchestrator checkout missing at $ORCH" >&2; exit 2;
}

raw="$(mktemp)"; trap 'rm -f "$raw"' EXIT
pipeline_rc=0
"$PY" "$ORCH/scripts/registry/stack_change_pipeline.py" check --repo-root "$ORCH" --numa-mode "$NUMA" > "$raw" 2>&1 || pipeline_rc=$?

# Classify. The patterns come from the errors this actually emitted on
# 2026-09-22; anything unmatched lands in needs-operator, because an
# unrecognised violation is exactly the thing a human should look at.
"$PY" - "$raw" "$OUT" "$pipeline_rc" <<'PY'
import re, shutil, sys
raw, out, pipeline_rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
lines = [l.rstrip() for l in open(raw) if re.search(r'^\s*(error|warn):', l)]
TRANSFORM = (
    r'declaration parity', r'numa_ports', r'numa_instances', r'NUMA topology',
    r'Role-server conflict', r'no NUMA_CONFIG entry', r'role enum',
    r'stale_role_fact_table', r'Missing live server binding',
    r'hash mismatch', r'stale or missing', r'phantom',
)
MEASURE = (r'quality suite_vector', r'known gap', r'known_global_gaps', r'Missing quality')
buckets = {'fixable-by-transform': [], 'needs-measurement': [], 'needs-operator': []}
if pipeline_rc != 0 and not lines:
    # A traceback or parser/import failure has no canonical violation line.
    # Retain the full producer output and refuse rather than printing 0 violations.
    shutil.copyfile(raw, out + '.raw')
    buckets['needs-operator'].append(
        f'unclassified pipeline failure (exit {pipeline_rc}); raw diagnostic: {out}.raw'
    )
for l in lines:
    t = l.strip()
    if   any(re.search(p, t, re.I) for p in MEASURE):   buckets['needs-measurement'].append(t)
    elif any(re.search(p, t, re.I) for p in TRANSFORM): buckets['fixable-by-transform'].append(t)
    else:                                               buckets['needs-operator'].append(t)
w = open(out, 'w')
def emit(s=''):
    print(s); w.write(s + '\n')
emit(f'stack-change preflight — {sum(map(len, buckets.values()))} violation(s)')
for k in ('fixable-by-transform', 'needs-measurement', 'needs-operator'):
    v = sorted(set(buckets[k]))
    emit(); emit(f'== {k} ({len(v)})')
    for x in v: emit(f'   {x[:200]}')
emit(); emit(f'report: {out}')
w.close()
# Exit code carries the verdict so a driver can branch without parsing.
#   0 clean · 3 transform work remains · 4 measurement owed · 5 operator decision
sys.exit(0 if not any(buckets.values()) else
         3 if buckets['fixable-by-transform'] else
         4 if buckets['needs-measurement'] else 5)
PY
