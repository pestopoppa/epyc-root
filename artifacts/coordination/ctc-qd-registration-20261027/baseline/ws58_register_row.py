#!/usr/bin/env python3
"""ws58 helper: copy ONE canonical 18-col row (by id) from a Codex row file into FILLERS.md
(replace if present, else append after the last codex-ni row) and append/replace its queue line.
usage: ws58_register_row.py ID SRCFILE PID WINDOW_S GIB REGIONS"""
import sys, os, shutil, time
rid, src, pid, win, gib, regs = sys.argv[1:7]
F = '/mnt/raid0/llm/tmp/compute-flags/'
rows = [l for l in open(src).read().split('\n') if l.startswith('| ' + rid + ' |')]
assert len(rows) == 1, f'{len(rows)} rows for {rid} in {src}'
c = rows[0].split('|'); assert len(c) == 20, f'{len(c)-2} cols'
import re as _re
if not _re.search(r'(^|[^_a-z])pid='+pid+r'\b', c[3]):
    print('normalizing col3 (Codex template lacks pid=NNN)'); c[3] = f' `/mnt/raid0/llm/tmp/fillers-3c4ca599/filler_run8.sh` pid={pid}; (codex text:{c[3].strip()}) '
    rows[0] = '|'.join(c)
p = F + 'FILLERS.md'; shutil.copy(p, p + '.bak-ws58-reg-' + time.strftime('%H%M%S'))
L = open(p).read().split('\n')
ex = [i for i, l in enumerate(L) if l.startswith('| ' + rid + ' |')]
if ex: L[ex[0]] = rows[0]
else:
    last = max(i for i, l in enumerate(L) if l.startswith('| codex-ni-')); L.insert(last + 1, rows[0])
open(p, 'w').write('\n'.join(L))
q = F + 'ws58-quarters-20261026.queue'; Q = [l for l in open(q).read().split('\n') if not l.startswith(rid + '|')]
line = f'{rid}|{pid}|{win}|{gib}|{regs}'
if Q and Q[-1] == '': Q.insert(len(Q) - 1, line)
else: Q.append(line)
open(q + '.tmp', 'w').write('\n'.join(Q)); os.replace(q + '.tmp', q)
d = F + 'ws58-quarters-20261026.queue.done'; D = [l for l in open(d).read().split('\n') if l != rid]
open(d + '.tmp', 'w').write('\n'.join(D)); os.replace(d + '.tmp', d)
print('registered', rid, 'replaced' if ex else 'appended', line)
