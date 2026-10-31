#!/bin/bash
# ws58 2026-10-28 (operator: "Tasks should be ready to go. There should be a backlog of inference tasks ready to be launched!").
# Zero-token READY-depth alarm. Every 10 min counts valid, unheld ready/*.json per bin (cpu-quarter work, gpu work,
# whole-host timing) and, when a bin is below its floor, writes ONE nudge to each Codex channel with the deficit.
# Floors: CPU >= 8 (two per quarter), GPU >= 3, whole-host >= 1. Read-only except the two channels and its own log.
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
echo "$(date -u +%FT%TZ) ready-depth start pid=$$" >> $F/ready-depth.log
while :; do
  python3 -I - <<'PY' >> /mnt/raid0/llm/tmp/compute-flags/ready-depth.log 2>&1 || true
import json, glob, os, datetime
F = '/mnt/raid0/llm/tmp/compute-flags/'
now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
n = dict(cpu=0, gpu=0, host=0)
for p in glob.glob(F + 'ready/*.json'):
    try: m = json.load(open(p))
    except Exception: continue
    rid = os.path.basename(p)[:-5]
    if m.get('hold') or os.path.exists(F + 'grants/' + rid + '.complete'): continue
    r = str(m.get('regions', ''))
    if r in ('0-95',) or r.count('q') >= 4: n['host'] += 1
    elif 'mi210' in r: n['gpu'] += 1
    else: n['cpu'] += 1
floor = dict(cpu=8, gpu=3, host=1)
short = {k: floor[k] - n[k] for k in n if n[k] < floor[k]}
print(f'{now} depth cpu={n["cpu"]} gpu={n["gpu"]} host={n["host"]} short={short}')
if short:
    msg = (f'READY-DEPTH LOW {now}: ready/ holds cpu={n["cpu"]}/8, gpu={n["gpu"]}/3, whole-host={n["host"]}/1. '
           f'Deficit {short}. Build AHEAD: smoke and publish ready/ manifests for the next backlog-priority.json inference items NOW, '
           'before slots free. Never build on the spot when a slot opens (operator 2026-10-28).')
    with open('/mnt/raid0/llm/tmp/refactor-01a16fc3/compute-coordination-20261026/owner-reply.md', 'a') as f:
        f.write(f'\n## {now} ws58 ready-depth alarm -> refactor\n- {msg}\n')
    p = '/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/OWNER-REPLY.json'
    d = json.load(open(p)); d['updates'].append({'at': now, 'from': 'ws58 ready-depth alarm', 'text': msg})
    json.dump(d, open(p + '.tmp', 'w'), indent=1); os.replace(p + '.tmp', p)
    for extra in glob.glob('/mnt/raid0/llm/tmp/compute-flags/codex-channels/*.md'):
        with open(extra, 'a') as f: f.write(f'\n## {now} ws58 ready-depth alarm\n- {msg}\n')
PY
  sleep 600
done
