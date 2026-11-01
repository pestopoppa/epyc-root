#!/bin/bash
# ws58 2026-10-31 (operator: code quota 50/day per Codex session). Zero-token. Hourly: resolve every item of
# WORK-<worker>-code.md against the CURRENT handoff text on origin/main (task text is the identity), count ticked items,
# and compare the ticks gained since the 00:00Z baseline with the pace 50 * hours_elapsed / 24. Writes
# CODE-SCOREBOARD.md; nudges a behind worker in its tmux pane at most every 2 h. Read-only except its own files.
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
echo "$(date -u +%FT%TZ) code-scoreboard start pid=$$" >> $F/code-scoreboard.log
while :; do
  git -C /workspace fetch -q origin 2>/dev/null || true
  python3 -I - <<'PY' >> /mnt/raid0/llm/tmp/compute-flags/code-scoreboard.log 2>&1 || true
import re, json, os, subprocess, datetime, time
F = '/mnt/raid0/llm/tmp/compute-flags/'
QUOTA = 50
PANES = {'ni': 'agent:2', 'refactor': 'agent:3', 'codex3': 'agent:4'}
now = datetime.datetime.now(datetime.timezone.utc); day = now.strftime('%Y-%m-%d')
BASE_REV = subprocess.run(['git', '-C', '/workspace', 'rev-list', '-1', '--before=' + day + 'T00:00:00Z', 'origin/main'], capture_output=True, text=True).stdout.strip()
def show(p, rev='origin/main'):
    for q in (p, p.replace('/active/', '/completed/'), p.replace('/active/', '/archived/')):
        r = subprocess.run(['git', '-C', '/workspace', 'show', rev + ':' + q], capture_output=True, text=True)
        if r.returncode == 0: return r.stdout
    return None
cache = {}; bcache = {}; done = {}; today_n = {}; dec = {}; uns = {}
def ticked_at_base(f, key):
    # 2026-10-31 audit: score a tick on the day its box FIRST flipped, not the day evidence was added
    if f not in bcache: bcache[f] = show(f, BASE_REV) if BASE_REV else None
    b = bcache[f]
    if not b: return False
    i = b.find(key)
    if i < 0: return False
    ln = b[b.rfind('\n', 0, i) + 1:i]
    return '[x]' in ln or '[X]' in ln
for w in PANES:
    n = 0; tn = 0
    for l in open(F + f'WORK-{w}-code.md'):
        m = re.match(r'- \[\w+\] (handoffs/\S+?):\d+ — (.{0,60})', l)
        if not m: continue
        f, t = m.groups(); key = t.strip()[:40]
        if f not in cache: cache[f] = show(f)
        s = cache[f]
        if not s: continue
        i = s.find(key)
        if i < 0: continue
        ln = s[s.rfind('\n', 0, i) + 1:i]
        if '[x]' in ln or '[X]' in ln:
            full = s[s.rfind('\n', 0, i) + 1:s.find('\n', i) if s.find('\n', i) > 0 else len(s)]
            if re.search(r'DECLIN|not filed because|obsolete|superseded|won.t do|no-belief: declined', full, re.I): dec[w] = dec.get(w, 0) + 1
            elif re.search(r'\b[0-9a-f]{7,40}\b', full) and re.search(r'(test|pass|artifact|/|\.py|\.md|\.json)', full):
                n += 1
                if not ticked_at_base(f, key): tn += 1
            else: uns.setdefault(w, []).append(f + ': ' + key)
    done[w] = n; today_n[w] = tn
bp = F + 'code-scoreboard-baseline.json'
b = json.load(open(bp)) if os.path.exists(bp) else {}
if b.get('day') != day: b = {'day': day, 'base': done, 'nudged': {}}; json.dump(b, open(bp, 'w'))
hrs = now.hour + now.minute / 60
pace = int(QUOTA * hrs / 24)
rows = [f'# CODE scoreboard {now:%Y-%m-%dT%H:%MZ} (quota {QUOTA}/day each; pace now {pace})', '',
        '| worker | evidenced ticks today | pace | evidenced total | declines (not counted) | unsupported ticks | status |', '|---|---|---|---|---|---|---|']
for w, pane in PANES.items():
    today = today_n[w]
    st = 'OK' if today >= pace else f'BEHIND by {pace - today}'
    rows.append(f'| {w} | {today} | {pace} | {done[w]} | {dec.get(w, 0)} | {len(uns.get(w, []))} | {st} |')
    last = b['nudged'].get(w, 0)
    if st != 'OK' and hrs >= 2 and time.time() - last > 7200:
        msg = (f'ws58 CODE SCOREBOARD: you have ticked {today} code-queue items today against a pace of {pace} '
               f'(quota {QUOTA}/day, OWNER-ORDER amendment 2026-10-31). Work WORK-{w}-code.md now, S items first, '
               'and push the ticks. Do inference prep only if a READY bin is below its floor.')
        subprocess.run(['tmux', 'send-keys', '-t', pane, '-l', msg]); time.sleep(1)
        subprocess.run(['tmux', 'send-keys', '-t', pane, 'Enter'])
        b['nudged'][w] = time.time()
json.dump(b, open(bp, 'w'))
rows += ['', '## Unsupported ticks (no commit SHA + test/artifact on the box line; not counted)'] + [f'- {w}: {u}' for w in uns for u in uns[w]]
open(F + 'CODE-SCOREBOARD.md', 'w').write('\n'.join(rows) + '\n')
print(now.strftime('%FT%TZ'), done, 'pace', pace)
PY
  sleep 3600
done
