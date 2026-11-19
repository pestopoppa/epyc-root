#!/usr/bin/env python3
"""Candidate-bound static impact; compute requires filler_run15 grant."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from source_integrity import untracked_index_affecting_paths
D = Path(__file__).resolve().parent
TREE = Path('/mnt/raid0/llm/worktrees/kpf30-impact-8952-20261104')
HEAD = '8952a0f693fb923918157eb25117641b74766230'
GUARD = Path('/mnt/raid0/llm/tmp/kvfork/kpf30-impact-8952-20261104-r4/gitnexus-guard.py')
SYMBOLS = [('handle_last_sampled_token', 'tools/server/server-context.cpp'), ('pre_decode', 'tools/server/server-context.cpp'), ('decode', 'tools/server/server-context.cpp'), ('sample_and_accept_dspark_serial', 'tools/server/server-context.cpp'), ('spec_exact_bonus', 'tools/server/server-context.cpp'), ('set_input_kq_mask', 'src/llama-kv-cache.cpp')]
ENV = dict(os.environ, GITNEXUS_REPO_NAME='kpf30-impact-8952-20261104', GITNEXUS_VERBOSE='1', GITNEXUS_WORKER_POOL_SIZE='1', GITNEXUS_PARSE_CHUNK_CONCURRENCY='1', GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS='120000', GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS='600000', GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES='131072')

def run(args, log=None):
    p = subprocess.run(args, cwd=TREE, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200)
    if log:
        (D/'out'/f'{log}.stdout').write_text(p.stdout)
        (D/'out'/f'{log}.stderr').write_text(p.stderr)
    if p.returncode: raise RuntimeError(f'{args!r} rc={p.returncode}; see {log}')
    return p.stdout

def check():
    assert run(['git','rev-parse','HEAD']).strip() == HEAD
    p = subprocess.run(['git','symbolic-ref','-q','HEAD'],cwd=TREE,stdout=subprocess.PIPE)
    assert p.returncode == 1, 'source must remain detached'
    assert not run(['git','diff','--name-only','HEAD']).strip()
    assert (TREE/'.git').is_file(), 'isolated git worktree required'
    identity=json.loads((D/'identity.json').read_text())
    assert identity.get('source_worktree') == str(TREE), 'identity worktree path mismatch'
    untracked = untracked_index_affecting_paths(TREE)
    assert not untracked, f'untracked index-affecting files present: {untracked[:20]!r}'
    for name, digest in identity['sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest, name

def emit(record, path=None):
    with (path or D/'out/results.jsonl').open('a') as f:
        f.write(json.dumps(record,sort_keys=True)+'\n'); f.flush(); os.fsync(f.fileno())

check()
if '--check' in sys.argv:
    print('Pinned detached worktree and sealed input digests verified; no graph compute')
    raise SystemExit(0)
(D/'out').mkdir(exist_ok=True)
refs={symbol:run(['git','grep','-n','-w',symbol,HEAD,'--',source]).splitlines() for symbol,source in SYMBOLS}
assert all(refs.values())
record={'type':'source_reference_scan','status':'partial','head':HEAD,'references':refs,'counts':{s:len(v) for s,v in refs.items()}}
if os.environ.get('FILLER_SMOKE')=='1':
    p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']);p.parent.mkdir(parents=True,exist_ok=True)
    emit(record,p);raise SystemExit(75)
emit(record)
run(['/usr/bin/python3','-I',str(GUARD),'--repo','app'],'guard')
run(['bash',str(TREE/'scripts/gitnexus-analyze.sh'),'--skip-agents-md','--skip-skills','--workers','1','--force'],'analyze')
status=run(['gitnexus','status'],'status')
assert str(TREE) in status and ('8952a0f' in status), 'missing candidate-bound graph status'
# Preserve full verbose skipped-file diagnostics and tracked file-size coverage.
tracked=run(['git','ls-files','-z']).split('\0')
large=[{'path':p,'bytes':(TREE/p).stat().st_size} for p in tracked if p and (TREE/p).is_file() and (TREE/p).stat().st_size>512*1024]
(D/'out/coverage.json').write_text(json.dumps({'head':HEAD,'graph_status':status,'large_tracked_files':large,'limit_bytes':512*1024,'skip_logs':['analyze.stdout','analyze.stderr'],'scope':'native default cap; omissions are not zero-impact evidence'},indent=2)+'\n')
for symbol,source in SYMBOLS:
    run(['/usr/bin/python3','-I',str(GUARD),'--repo','app'])
    raw=run(['gitnexus','impact',symbol,'--repo',str(TREE),'--direction','upstream','--file',source],symbol)
    data=json.loads(raw)
    assert isinstance(data,dict) and not data.get('error') and not data.get('partial') and not data.get('truncated') and data.get('status') not in ('ambiguous','not_found') and data.get('risk') in ('LOW','MEDIUM','HIGH','CRITICAL'), f'unresolved impact: {symbol}'
    emit({'type':'native_impact','head':HEAD,'symbol':symbol,'source':source,'impact':data})
    if data['risk'] in ('HIGH','CRITICAL'):
        (D/'out/OWNER_WARNING').write_text(f'STOP: {symbol} upstream impact {data["risk"]}; owner review required before source edits.\n')
        emit({'type':'risk_stop','head':HEAD,'symbol':symbol,'risk':data['risk'],'partial':True})
        raise SystemExit(3)
check()
emit({'type':'scan_complete','head':HEAD,'impact_count':len(SYMBOLS),'partial':False,'coverage':'out/coverage.json'})
(D/'out/COMPLETE').write_text('Six native upstream impact records and skipped-file coverage retained.\n')
