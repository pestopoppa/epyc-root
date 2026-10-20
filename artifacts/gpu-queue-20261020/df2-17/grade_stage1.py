import json, re
from pathlib import Path
D = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17/stage1')
q = {x['id']: x for x in json.load(open('/workspace/tmp/questions_mtp_ab.json'))}
def norm(s): return re.sub(r'\\left|\\right|\\!|\\,|\;|\s|\$|\\text\{[^}]*\}|\{|\}', '', s).replace('\\dfrac', '\\frac')
def boxed(t):
    m = []
    for mm in re.finditer(r'\\boxed\{', t):
        i = mm.end(); depth = 1; j = i
        while j < len(t) and depth:
            depth += (t[j] == '{') - (t[j] == '}'); j += 1
        m.append(t[i:j-1])
    return m[-1] if m else None
def grade(r, exp):
    b = boxed(r['content'] or '')
    if b is None: return {'answered': False, 'stop': r['stop_type'], 'correct': None}
    return {'answered': True, 'boxed': b, 'correct': norm(b) == norm(exp), 'stop': r['stop_type']}
def L(a): return {r['id']: r for r in map(json.loads, open(D / a / 'records.jsonl'))}
base = L('off_A'); out = []
for arm in sorted(p.name for p in D.iterdir() if (p / 'arm.json').exists() and p.name != 'off_A'):
    A = L(arm)
    for pid, b in base.items():
        a = A[pid]
        if a['tokens'] == b['tokens']: continue
        gb, ga = grade(b, q[pid]['expected']), grade(a, q[pid]['expected'])
        flip = gb['correct'] is not None and ga['correct'] is not None and gb['correct'] != ga['correct']
        out.append({'arm': arm, 'id': pid, 'base': gb, 'arm_grade': ga, 'graded_flip': flip,
                    'status': 'graded flip' if flip else ('both answered, same correctness' if gb['correct'] is not None and ga['correct'] is not None else 'ungradable (answer missing: truncated at cap or no boxed)')})
Path(D / 'grading.json').write_text(json.dumps(out, indent=1))
import collections
print(collections.Counter(o['status'] for o in out))
print([ (o['arm'], o['id'][-10:], o['base'], o['arm_grade']) for o in out if o['status']!='ungradable (answer missing: truncated at cap or no boxed)'])
