#!/usr/bin/env python3
"""Model-free planning-context canary for VB-AK-R23-4-SWEEP-WIRE: loop_beliefs.prepare on a scratch
copy of the canonical ledger (which already holds the ingested sweep). No inference, no network, no
subprocess, no write outside scratch; the canonical ledger is hashed before and after."""
import hashlib, json, os, shutil, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode = True
CODE = Path(sys.argv[1]).resolve()
W = Path(sys.argv[3] if len(sys.argv) > 3 else '/mnt/raid0/llm/tmp/vb-r234-canary-20261110/state'); W.mkdir(exist_ok=True)
CAN = Path('/mnt/raid0/llm/state/vidya/ledger.jsonl')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before = sha(CAN)
led = W/'ledger.jsonl'
if led.exists(): raise SystemExit('scratch ledger exists')
SRC = Path(sys.argv[2]) if len(sys.argv) > 2 else CAN
shutil.copyfile(SRC, led)
m = Path(str(SRC)+'.sync.json')
if m.exists(): shutil.copyfile(m, Path(str(led)+'.sync.json'))
(W/'alarm.yaml').write_text('schema_version: alarm_channel.config.v1\nenabled: false\nbackend: ntfy\n')
(W/'tmp').mkdir(exist_ok=True); tempfile.tempdir = str(W/'tmp')
def audit(event, args):
    if event in ('socket.connect', 'socket.bind', 'subprocess.Popen', 'os.system'): raise PermissionError('model-free canary forbids '+event)
    if event == 'open':
        path, mode, flags = args
        writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (isinstance(flags, int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if writing and not isinstance(path, int) and not Path(path).resolve().is_relative_to(Path('/mnt/raid0/llm/tmp/vb-r234-canary-20261110')): raise PermissionError('write outside scratch: '+str(path))
sys.addaudithook(audit)
sys.path.insert(0, str(CODE/'scripts/vidya'))
import loop_beliefs
target = {'model_path': '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf', 'quant': 'Q8_0', 'backend': 'gpu'}
res = {'schema': 'epyc.vb.r234.planning_canary.v1', 'measurement': False, 'model_backend_calls': 0, 'canonical_before': before, 'target': target}
p = loop_beliefs.prepare('autokernel.planner', target, ledger=led, index_path=CODE/'research/intake_index.yaml',
    as_of=datetime.now(timezone.utc).isoformat(), known_good=W/'known-good.json', alarm_state=W/'alarm.json',
    alarm_config=W/'alarm.yaml', read_log=W/'reads.jsonl', source_memo_dir=W/'source-memo')
(W/'prepared.json').write_text(json.dumps(p, indent=2, default=str))
ev = p.get('evidence') or {}
sec = ev.get('section', '')
(W/'section.txt').write_text(sec)
claims = [c for c in ev.get('claims', []) if c.get('source_kind') == 'autokernel-r234-native-sweep']
lines = [l for l in sec.splitlines() if 'R23-4' in l or 'r234' in l.lower()]
res.update(prepare_status=p.get('status'), refusal=p.get('reason') or p.get('refusal'), r234_claims_in_evidence=len(claims),
           r234_claim_ids=[c.get('claim_id') for c in claims][:20], section_lines_mentioning_r234=lines[:6],
           tiers=sorted({c.get('tier') for c in claims}, key=str), claim_ids_total=len(ev.get('claim_ids', [])))
res['canonical_after'] = sha(CAN); res['canonical_unchanged'] = res['canonical_after'] == before
res['status'] = 'UNKNOWN' if p.get('status') != 'ready' else ('PASS' if claims and lines else 'FAIL')
print(json.dumps(res, indent=2, default=str))
