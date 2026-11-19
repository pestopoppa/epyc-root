#!/usr/bin/env python3
"""Candidate-bound static impact; compute requires filler_run15 grant."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import signal
import time
import tempfile
import ctypes
import re
import select
from source_integrity import untracked_index_affecting_paths
from tool_seal import verify as verify_tool
D = Path(__file__).resolve().parent
TREE = Path('/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105-source')
HEAD = 'a1f0c8cf9bd7102415a72577474f307b8ba94db9'
GUARD = Path('/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105/gitnexus-guard.py')
SYMBOLS = [('process_single_task', 'tools/server/server-context.cpp'), ('update_slots', 'tools/server/server-context.cpp')]
ENV = dict(os.environ, PATH='/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105/bin:' + os.environ['PATH'], GITNEXUS_HOME=str(D/'private-graph'), GITNEXUS_REPO_NAME='kpf131-native-binding-impact-a1f0-r4-20261105', GITNEXUS_VERBOSE='1', GITNEXUS_WORKER_POOL_SIZE='1', GITNEXUS_PARSE_CHUNK_CONCURRENCY='1', GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS='120000', GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS='600000', GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES='131072')

def birth(pid):
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]

# Orphan descendants reparent to this job, so an intermediate exit cannot hide them.
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0)==0, 'subreaper setup failed'

def child_setup(parent):
    libc=ctypes.CDLL(None)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid()!=parent:
        os._exit(64)

def children(pid):
    result=set()
    for task in Path(f'/proc/{pid}/task').glob('*'):
        try: result.update(map(int,(task/'children').read_text().split()))
        except FileNotFoundError: pass
    return result

def capture(pid, owned):
    if pid in owned: return
    try:
        token=birth(pid); fd=os.pidfd_open(pid)
        if birth(pid)!=token:
            os.close(fd); raise RuntimeError('child identity changed during capture')
        owned[pid]=(token,fd)
    except ProcessLookupError: pass
    except FileNotFoundError: pass

def alive(item):
    return not select.select([item[1]],[],[],0)[0]

def send(pid,item,sig):
    if alive(item):
        assert birth(pid)==item[0], 'owned process birth changed'
        signal.pidfd_send_signal(item[1],sig)

def discover(owned, freeze=False):
    # Direct children are either Popen children or adopted descendants of this job.
    # Capture/freeze parents before reading their child lists, preventing fork escape.
    queue=list(children(os.getpid()))+list(owned)
    seen=set()
    while queue:
        pid=queue.pop()
        if pid in seen: continue
        seen.add(pid); capture(pid,owned)
        item=owned.get(pid)
        if item is None or not alive(item): continue
        if freeze:
            send(pid,item,signal.SIGSTOP)
            stop_deadline=time.monotonic()+5
            while alive(item):
                try: state=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
                except FileNotFoundError: break
                if state in ('T','t','Z','X'): break
                assert time.monotonic()<stop_deadline, 'owned process failed to freeze'
                time.sleep(.01)
        queue.extend(children(pid))

def cleanup(owned,p):
    # Freeze the entire captured subtree before graceful termination; then recapture
    # any forks during TERM grace and freeze again before KILL. No process groups.
    discover(owned,freeze=True)
    for pid,item in list(owned.items()):
        send(pid,item,signal.SIGTERM); send(pid,item,signal.SIGCONT)
    deadline=time.monotonic()+5
    while any(alive(item) for item in owned.values()) and time.monotonic()<deadline:
        discover(owned)
        time.sleep(.05)
    discover(owned,freeze=True)
    for pid,item in list(owned.items()): send(pid,item,signal.SIGKILL)
    deadline=time.monotonic()+5
    while any(alive(item) for item in owned.values()) and time.monotonic()<deadline:
        time.sleep(.05)
    assert all(not alive(item) for item in owned.values()), 'owned descendant remains alive'
    p.wait(timeout=1)
    for pid,(token,fd) in owned.items():
        try: os.waitpid(pid,os.WNOHANG)
        except ChildProcessError: pass
        os.close(fd)

def run(args, log=None):
    parent=os.getpid(); owned={}
    with tempfile.TemporaryFile(mode='w+') as out, tempfile.TemporaryFile(mode='w+') as err:
        p=subprocess.Popen(args,cwd=TREE,env=ENV,text=True,stdout=out,stderr=err,
                           preexec_fn=lambda: child_setup(parent))
        try:
            capture(p.pid,owned)
            deadline=time.monotonic()+7200
            while p.poll() is None:
                discover(owned)
                if (D/'STOP').exists() or time.monotonic()>deadline:
                    raise RuntimeError('STOP or child deadline')
                time.sleep(.2)
        finally:
            try: cleanup(owned,p)
            finally:
                out.seek(0); err.seek(0)
                stdout=out.read(); stderr=err.read()
                if log:
                    (D/'out'/f'{log}.stdout').write_text(stdout)
                    (D/'out'/f'{log}.stderr').write_text(stderr)
        if p.returncode: raise RuntimeError(f'{args!r} rc={p.returncode}; see {log}')
        return stdout

def verified_full_impact(data):
    assert not data.get('partial') and not data.get('truncated'), 'partial impact'
    pagination=data.get('pagination')
    assert pagination is None or (isinstance(pagination,dict) and
        pagination.get('truncated') is False and pagination.get('offset')==0), 'unverified pagination'
    counts=data.get('byDepthCounts'); grouped=data.get('byDepth')
    assert isinstance(counts,dict) and isinstance(grouped,dict), 'unknown impact schema'
    assert set(counts)==set(grouped), 'impact depth keys differ'
    ids=[]
    for depth,count in counts.items():
        assert str(depth).isdigit() and type(count) is int and count>=0, 'unknown depth count'
        records=grouped[depth]
        assert isinstance(records,list) and len(records)==count, 'impact pagination omitted records'
        assert all(isinstance(r,dict) and isinstance(r.get('id'),str) and r['id'] for r in records), 'unknown impact record schema'
        ids.extend(r['id'] for r in records)
    assert len(ids)==len(set(ids)), 'duplicate impacted records'
    assert type(data.get('impactedCount')) is int and data['impactedCount']==len(ids), 'impact total mismatch'
    return {'returned':len(ids),'byDepthCounts':counts,'pagination_verified':True}

def verified_coverage(status,large):
    logs={name:(D/'out'/name).read_text() for name in ('analyze.stdout','analyze.stderr')}
    clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','', '\n'.join(logs.values()))
    assert 'Repository indexed successfully (' in clean, 'missing native analyze completion'
    assert not re.search(r'(?:\.\.\.and|…and) \d+ more|set GITNEXUS_VERBOSE=1 to list',clean), 'truncated diagnostics'
    assert not re.search(r'(?i)\b(?:failed|failure|timeout|timed out|parse error|partial|incomplete|aborted)\b',clean), 'parser failure'
    assert '[KPF_SCOPE_UNREADABLE]' not in clean, 'unreadable scoped input'
    lines=clean.splitlines(); blocks=[]; covered=set()
    for index,line in enumerate(lines):
        match=re.search(r'Skipped (\d+) large files \(>',line)
        if not match: continue
        count=int(match.group(1)); paths=[]
        for following in lines[index+1:]:
            item=re.match(r'^\s*- (.+?)\s*$',following)
            if item: paths.append(item.group(1)); continue
            if paths or following.strip(): break
        assert len(paths)==count and len(set(paths))==count and all((TREE/p).is_file() for p in paths), 'large skip enumeration invalid'
        covered.update(range(index,index+1+len(paths)));blocks.append({'count':count,'paths':paths})
    skips=[]
    for line in lines:
        if '[KPF_SCOPE_SKIPPED] ' in line:
            v=json.loads(line.split('[KPF_SCOPE_SKIPPED] ',1)[1]); assert set(v)=={'language','path'}
            q=Path(v['path']); assert not q.is_absolute() and '..' not in q.parts
            f=TREE/q; assert f.is_file() and not f.is_symlink() and not f.read_bytes().strip(), 'nonempty or missing skipped file'
            skips.append({'language':v['language'],'path':v['path'],'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    assert len({v['path'] for v in skips})==len(skips), 'duplicate skip witness'
    counts=re.findall(r'sr-extract-end[^\n]*lang=([a-z]+) parsedFiles=(\d+) preExtractedHits=(\d+) skipped=(\d+)',clean)
    assert counts, 'missing native scope counters'
    for lang,parsed,hits,skipped in counts:
        assert sum(v['language']==lang for v in skips)==int(skipped), 'native skip count mismatch'
    assert len(skips)==sum(int(v[3]) for v in counts), 'unmatched skip language'
    unknown=[line for i,line in enumerate(lines) if i not in covered and '[KPF_SCOPE_SKIPPED]' not in line and not re.search(r'sr-extract-end[^\n]*skipped=\d+\s*$',line) and re.search(r'(?i)\b(?:skip|skipped|skipping|omitted|truncated)\b',line)]
    assert not unknown, f'unverified skip diagnostics: {unknown[:8]!r}'
    meta=json.loads((TREE/'.gitnexus/meta.json').read_text())
    hashes=meta.get('fileHashes');assert isinstance(hashes,dict) and hashes, 'missing source manifest'
    for path,expected in hashes.items():
        assert not path.lower().endswith('.gguf'), 'model hash forbidden'
        file=TREE/path
        assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==expected, f'indexed source drift: {path}'
    for skipped in skips:
        assert hashes.get(skipped['path'])==skipped['sha256'], 'skip is not bound to indexed source manifest'
    result={'head':HEAD,'graph_status':status,'large_tracked_files':large,'native_large_skip_blocks':blocks,'large_tracked_not_named_by_native_skip':sorted({v['path'] for v in large}-{p for b in blocks for p in b['paths']}),'scope_skipped':skips,'scope_counts':counts,'skip_logs':list(logs),'log_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in logs.items()},'native_analyze_complete':True,'verbose_skip_coverage_verified':True,'scope':'Fresh instrumented index; explicitly enumerated large and empty-file skips are not indexed; edit safety excludes them.'}
    (D/'out/coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def check():
    verify_tool()
    assert run(['git','rev-parse','HEAD']).strip() == HEAD
    assert run(['git','rev-parse','--abbrev-ref','HEAD']).strip() == 'HEAD', 'source must remain detached'
    assert not run(['git','diff','--name-only','HEAD']).strip()
    assert (TREE/'.git').is_file(), 'isolated git worktree required'
    identity=json.loads((D/'identity.json').read_text())
    assert identity.get('source_worktree') == str(TREE), 'identity worktree path mismatch'
    untracked = [x for x in run(['git','ls-files','--others','--exclude-standard','-z']).split('\0') if x]
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
    assert len(os.sched_getaffinity(0)) <= 4, 'smoke requires at most four CPUs'
    p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).resolve()
    assert p != (D/'out/results.jsonl').resolve(), 'smoke output must be separate'
    p.parent.mkdir(parents=True,exist_ok=True)
    emit(record,p);raise SystemExit(75)
emit(record)
run(['/usr/bin/python3','-I',str(GUARD),'--repo','app'],'guard')
run(['bash',str(TREE/'scripts/gitnexus-analyze.sh'),'--skip-agents-md','--skip-skills','--workers','1','--force'],'analyze')
status=run(['gitnexus','status'],'status')
assert str(TREE) in status and (HEAD[:7] in status), 'missing candidate-bound graph status'
registry=json.loads((D/'private-graph/registry.json').read_text())
assert len(registry)==1 and Path(registry[0]['path']).resolve()==TREE.resolve(), 'private registry binding mismatch'
meta=json.loads((TREE/'.gitnexus/meta.json').read_text())
assert meta.get('lastCommit')==HEAD, 'exact graph commit binding mismatch'
# Preserve full verbose skipped-file diagnostics and tracked file-size coverage.
tracked=run(['git','ls-files','-z']).split('\0')
large=[{'path':p,'bytes':(TREE/p).stat().st_size} for p in tracked if p and (TREE/p).is_file() and (TREE/p).stat().st_size>512*1024]
coverage=verified_coverage(status,large)
verified_impacts=[]
for symbol,source in SYMBOLS:
    run(['/usr/bin/python3','-I',str(GUARD),'--repo','app'])
    raw=run(['gitnexus','impact',symbol,'--repo',str(TREE),'--direction','upstream','--file',source],symbol)
    data=json.loads(raw)
    # Warning precedence: publish HIGH/CRITICAL even when native output is partial.
    if isinstance(data,dict) and data.get('risk') in ('HIGH','CRITICAL'):
        (D/'out/OWNER_WARNING').write_text(f'STOP: {symbol} upstream impact {data["risk"]}; owner review required before source edits.\n')
        emit({'type':'risk_stop','head':HEAD,'symbol':symbol,'risk':data['risk'],'partial':True,'native':data})
        raise SystemExit(3)
    target=data.get('target',{}) if isinstance(data,dict) else {}
    assert target.get('name')==symbol and target.get('filePath')==source and target.get('id') and data.get('direction')=='upstream', f'native target binding failed: {symbol}'
    assert isinstance(data,dict) and not data.get('error') and not data.get('partial') and not data.get('truncated') and data.get('status') not in ('ambiguous','not_found') and data.get('risk') in ('LOW','MEDIUM','HIGH','CRITICAL'), f'unresolved impact: {symbol}'
    completeness=verified_full_impact(data)
    verified_impacts.append({'symbol':symbol,**completeness})
    emit({'type':'native_impact','head':HEAD,'symbol':symbol,'source':source,'impact':data,'completeness':completeness})
    if data['risk'] in ('HIGH','CRITICAL'):
        (D/'out/OWNER_WARNING').write_text(f'STOP: {symbol} upstream impact {data["risk"]}; owner review required before source edits.\n')
        emit({'type':'risk_stop','head':HEAD,'symbol':symbol,'risk':data['risk'],'partial':True})
        raise SystemExit(3)
check()
assert len(verified_impacts)==len(SYMBOLS) and coverage['native_analyze_complete'] and coverage['verbose_skip_coverage_verified']
emit({'type':'scan_complete','head':HEAD,'impact_count':len(verified_impacts),'partial':False,'coverage':'out/coverage.json','verified_impacts':verified_impacts,'scope':coverage['scope']})
(D/'out/COMPLETE').write_text('Two native upstream impact records and skipped-file coverage retained.\n')
