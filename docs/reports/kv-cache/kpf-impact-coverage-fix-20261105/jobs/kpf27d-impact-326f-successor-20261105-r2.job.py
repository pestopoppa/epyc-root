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
D = Path(__file__).resolve().parent
TREE = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf27d-impact-326f-successor-20261105-source')
HEAD = '326f502759986c9846027f8187972969139c0089'
GUARD = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf27d-impact-326f-successor-20261105-r2/gitnexus-guard.py')
SYMBOLS = [('get_status', 'src/scheduling/kv_pool_admission.py'), ('get_shared_pool_admission', 'src/scheduling/kv_pool_admission.py'), ('status', 'src/inference/prefix_index.py'), ('passthrough_chat_completions', 'src/api/routes/passthrough.py'), ('passthrough_responses', 'src/api/routes/passthrough.py'), ('run_scouts', 'src/api/routes/chat_pipeline/scout_stage.py')]
ENV = dict(os.environ, GITNEXUS_HOME=str(D/'private-graph'), GITNEXUS_REPO_NAME='kpf27d-impact-326f-successor-20261105-r2', GITNEXUS_VERBOSE='1', GITNEXUS_WORKER_POOL_SIZE='1', GITNEXUS_PARSE_CHUNK_CONCURRENCY='1', GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS='120000', GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS='600000', GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES='131072')

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

# gitnexus dist core/ingestion/scope-resolution/pipeline/run.js: sr-extract-end skipped=N counts files for which
# extractParsedFile() returned undefined: whitespace-only source, or an extractor exception (which also logs
# "scope extraction failed for <path>"). Such files get no scope model, so require every one to be a whitespace-only
# tracked file (no symbols, so outside every impact target) and record them; anything else fails coverage.
SCOPE_EXTS={'python':('.py','.pyi'),'c':('.c','.h'),'cpp':('.cpp','.cc','.cxx','.hpp','.hh','.hxx','.h','.cu','.cuh'),
            'typescript':('.ts','.tsx','.mts','.cts'),'javascript':('.js','.jsx','.mjs','.cjs')}
def verified_scope_skips(lines,clean):
    assert 'scope extraction failed for' not in clean, 'scope extractor exception'
    starts={}; out=[]
    named=[]
    for line in lines:
        m=re.match(r'^\[KPF_SCOPE_SKIPPED\] (\{.*\})\s*$',line)
        if m: named.append(json.loads(m.group(1)))
    for line in lines:
        if not line.startswith('[gitnexus-heap] '): continue
        m=re.search(r' sr-extract-start .*\blang=(\S+) files=(\d+)\b',line)
        if m: starts[m.group(1)]=int(m.group(2)); continue
        m=re.search(r' sr-extract-end .*\blang=(\S+) parsedFiles=(\d+) preExtractedHits=\d+ skipped=(\d+)\s*$',line)
        if not m:
            assert not re.search(r'(?i)skip',line), f'unparsed heap skip line: {line!r}'
            continue
        lang,parsed,skipped=m.group(1),int(m.group(2)),int(m.group(3))
        assert lang in starts and starts.pop(lang)==parsed+skipped, f'scope extract count mismatch: {line!r}'
        entry={'lang':lang,'files':parsed+skipped,'parsed':parsed,'skipped':skipped}
        if skipped:
            assert lang in SCOPE_EXTS, f'unverifiable scope skips for {lang}'
            tracked=[p for p in run(['git','ls-files','-z']).split('\0') if p.endswith(SCOPE_EXTS[lang])]
            blank=sorted(p for p in tracked if (TREE/p).is_file() and not (TREE/p).read_bytes().strip())
            assert len(blank)>=skipped, f'{lang}: {skipped} scope skips but only {len(blank)} whitespace-only files'
            ours=[n['path'] for n in named if n.get('language')==lang]
            if ours:
                assert len(ours)==skipped and set(ours)<=set(blank), f'{lang}: named scope skips not whitespace-only'
            assert not {s for _,s in SYMBOLS}&set(blank), 'impact target file has no scope model'
            entry.update(whitespace_only_candidates=blank,named_paths=ours)
        out.append(entry)
    return out

def verified_coverage(status,large):
    logs={name:(D/'out'/name).read_text() for name in ('analyze.stdout','analyze.stderr')}
    combined='\n'.join(logs.values())
    clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',combined)
    assert 'Repository indexed successfully (' in clean, 'missing native analyze completion'
    assert ENV['GITNEXUS_VERBOSE']=='1', 'verbose diagnostics disabled'
    assert not re.search(r'(?:\.\.\.and|…and) \d+ more|set GITNEXUS_VERBOSE=1 to list',clean), 'truncated skipped-file diagnostics'
    assert not re.search(r'(?i)\b(?:failed|failure|timeout|timed out|parse error|partial|incomplete|aborted)\b',clean), 'parser/incomplete diagnostics require review'
    lines=clean.splitlines(); blocks=[]; covered=set()
    for index,line in enumerate(lines):
        match=re.search(r'Skipped (\d+) large files \(>',line)
        if not match: continue
        count=int(match.group(1)); paths=[]
        for offset,following in enumerate(lines[index+1:],index+1):
            path=re.match(r'^\s*- (.+?)\s*$',following)
            if path: paths.append(path.group(1)); covered.add(offset); continue
            if following.strip(): break  # blank = ANSI erase-line residue between entries
        assert len(paths)==count and len(set(paths))==count, 'skipped-file summary/list mismatch'
        assert all((TREE/path).is_file() for path in paths), 'skipped path missing'
        covered.add(index)
        blocks.append({'count':count,'paths':paths})
    # Unknown skip classes cannot silently pass as complete native coverage.
    # [gitnexus-heap] lines are GitNexus memory instrumentation; their skip counts are verified, not trusted.
    scope_skips=verified_scope_skips(lines,clean)
    heap={i for i,line in enumerate(lines) if line.startswith('[gitnexus-heap] ')}
    unknown=[line for i,line in enumerate(lines) if i not in covered and i not in heap and
             re.search(r'(?i)\b(?:skip|skipped|skipping|omitted|truncated)\b',line)]
    assert not unknown, f'unverified skip diagnostics: {unknown[:8]!r}'
    result={'head':HEAD,'graph_status':status,'large_tracked_files':large,
            'limit_bytes':512*1024,'native_large_skip_blocks':blocks,
            'skip_logs':list(logs),'log_sha256':{n:hashlib.sha256(t.encode()).hexdigest() for n,t in logs.items()},
            'scope_extract_skips':scope_skips,'native_analyze_complete':True,'verbose_skip_coverage_verified':True,
            'scope':'Native default-cap scan completed; skipped/ignored files are outside edit-safety claims.'}
    (D/'out/coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def check():
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
assert str(TREE) in status and ('326f502' in status), 'missing candidate-bound graph status'
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
(D/'out/COMPLETE').write_text('Six native upstream impact records and skipped-file coverage retained.\n')
