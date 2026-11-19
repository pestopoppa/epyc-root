#!/usr/bin/env python3
"""Pinned CPU exactness job; builds and runs occur only under a keeper grant."""
import hashlib, json, math, os, pathlib, re, signal, struct, subprocess, sys, time, uuid
from source_worktrees import verify as verify_source
D=pathlib.Path(__file__).resolve().parent
R=D/'out'
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def atom(p,v):
    q=p.with_suffix(p.suffix+'.tmp'); q.write_text(json.dumps(v,indent=2)+'\n'); q.replace(p)
def stopped(): return pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE'])
def pause():
    if stopped(): raise SystemExit(75)
def run(cmd,log,env=None):
    pause()
    with log.open('wb') as f:
        p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        while p.poll() is None:
            if stopped():
                os.killpg(p.pid,signal.SIGTERM)
                try: p.wait(timeout=8)
                except subprocess.TimeoutExpired: os.killpg(p.pid,signal.SIGKILL); p.wait()
                assert p.poll() is not None
                raise SystemExit(75)
            time.sleep(.1)
    if p.returncode: raise RuntimeError(f'command rc={p.returncode}; see {log}')
def fnv(data):
    n=0x14650fb0739d0383
    for b in data: n=((n^b)*0x100000001b3)&((1<<64)-1)
    return n
def validate(log,dump,case,shared):
    rows=[r for r in log.read_text().splitlines() if r.startswith('case ')]
    assert len(rows)==1 and int(rows[0].split()[1])==case, 'missing/duplicate case'
    row=rows[0]; assert 'unsupported' not in row, 'CPU requires every case supported'
    hs=re.search(r'\bhs=(\d+)/(\d+)',row); assert hs
    def field(k): return int(re.search(r'\b'+k+r'=(\d+)',row)[1])
    assert field('nan')==0
    data=(dump/f'out_{case:02d}.bin').read_bytes()
    assert len(data)==int(hs[2])*field('nh')*field('nr2')*field('nb')*4
    assert all(math.isfinite(v[0]) for v in struct.iter_unpack('=f',data))
    assert fnv(data)==int(re.search(r'\bhash=([0-9a-f]+)',row)[1],16)
    if shared: assert field('shared')>0
    alls=[r for r in log.read_text().splitlines() if r.startswith('ALL ')]
    assert alls==[f'ALL {((0x14650fb0739d0383^fnv(data))*0x100000001b3)&((1<<64)-1):016x}']
    return row,data
C=json.loads((D/'identity.json').read_text())
assert C['reviewed'] is True
assert all(sha(D/p)==h for p,h in C['inputs'].items()), 'input changed'
for arm in ('baseline', 'champion'):
    verify_source(D/'sources'/arm, C['sources'][arm], C['source_repository'])
binding=sha(D/'identity.json')
if '--check' in sys.argv:
    print('static input hashes verified; no builds or inference'); sys.exit(0)
assert os.environ.get('FILLER_CPUS') and os.environ.get('FILLER_THREADS'), 'keeper CPU grant required'
R.mkdir(exist_ok=True)
if (R/'binding').exists(): assert (R/'binding').read_text()==binding
else: (R/'binding').write_text(binding)
threads=str(int(os.environ['FILLER_THREADS'])); assert int(threads)>0
builds=[]
for arm in ('baseline','champion'):
    pause(); src=D/'sources'/arm; B=D/f'build-{arm}'
    verify_source(src, C['sources'][arm], C['source_repository'])
    B.mkdir(exist_ok=True); receipt=B/'identity.json'
    flags=['-DCMAKE_BUILD_TYPE=Release','-DGGML_NATIVE=ON','-DGGML_HIP=OFF','-DGGML_CUDA=OFF','-DGGML_BACKEND_DL=OFF','-DLLAMA_CURL=OFF','-DBUILD_SHARED_LIBS=ON']
    if receipt.exists():
        previous=json.loads(receipt.read_text())
        if not all(pathlib.Path(p).is_file() and sha(p)==h for p,h in previous['files'].items()):
            import shutil
            shutil.rmtree(B); B.mkdir()
    if not receipt.exists():
        run(['cmake','-S',str(src),'-B',str(B),*flags],B/'configure.log')
        run(['cmake','--build',str(B),'--target','ggml','ggml-cpu','-j',threads],B/'build.log')
        for h in ('original','shared'):
            run(['g++','-O2','-std=c++17',str(D/'input'/f'{h}.cpp'),'-I'+str(src/'ggml/include'),'-L'+str(B/'bin'),'-lggml','-lggml-base','-lggml-cpu','-Wl,-rpath,'+str(B/'bin'),'-o',str(B/f'harness-{h}')],B/f'compile-{h}.log')
        libs=[p for p in (B/'bin').glob('libggml*.so*') if p.is_file()]; assert libs
        files=[B/'harness-original',B/'harness-shared',B/'CMakeCache.txt',*libs]
        atom(receipt,{'binding':binding,'source':C['sources'][arm],'flags':flags,'files':{str(p):sha(p) for p in files}})
    m=json.loads(receipt.read_text()); assert m['binding']==binding and m['source']==C['sources'][arm] and m['flags']==flags
    assert all(sha(p)==h for p,h in m['files'].items())
    builds.append(B)
# Independent original baseline first;
# Shared harness retains original 86 plus 25 shared cases.
for harness,count in (('shared',111),('original',86)):
    for case in range(count):
        pause(); done=R/f'{harness}-{case:03d}.json'
        if done.exists():
            m=json.loads(done.read_text()); assert m['binding']==binding
            assert all(sha(p)==h for p,h in m['files'].items()); continue
        A=R/f'{harness}-{case:03d}-{uuid.uuid4().hex}'; A.mkdir()
        rows=[]; data=[]
        for arm,B in zip(('baseline','champion'),builds):
            dump=A/arm; dump.mkdir()
            env=dict(os.environ,LD_LIBRARY_PATH=str(B/'bin'),GGML_BACKEND_PATH=str(B/'bin'),FA_CASE=str(case),FA_DUMP_DIR=str(dump))
            env.pop('GGML_CUDA_FA_MASK_SKIP',None)
            run(['taskset','-c',os.environ['FILLER_CPUS'],str(B/f'harness-{harness}'),'CPU','exact',threads],A/f'{arm}.txt',env)
            row,raw=validate(A/f'{arm}.txt',dump,case,harness=='shared' and case>=86); rows.append(row); data.append(raw)
        assert rows[0]==rows[1] and data[0]==data[1], f'CPU bit mismatch {harness} {case}'
        # Re-run the unchanged original under this same grant, with the same
        # thread count, to avoid cross-thread reduction-order comparisons.
        if harness=='shared' and case<86:
            for arm,B in zip(('baseline','champion'),builds):
                dump=A/(arm+'-original-paired'); dump.mkdir()
                env=dict(os.environ,LD_LIBRARY_PATH=str(B/'bin'),FA_CASE=str(case),FA_DUMP_DIR=str(dump))
                env.pop('GGML_BACKEND_PATH',None); env.pop('GGML_CUDA_FA_MASK_SKIP',None)
                run(['taskset','-c',os.environ['FILLER_CPUS'],str(B/'harness-original'),'CPU','exact',threads],A/(arm+'-original-paired.txt'),env)
                _,raw=validate(A/(arm+'-original-paired.txt'),dump,case,False)
                assert raw==(A/arm/f'out_{case:02d}.bin').read_bytes(), f'original output changed in paired {arm} case {case}'
        files={str(p):sha(p) for p in A.rglob('*') if p.is_file()}
        result={'schema':'kpf17a.cpu.case.v1','status':'PASS','harness':harness,'case':case,'binding':binding,'attempt':str(A),'files':files,'criterion':'CPU bit-identical; no tolerance','commits':{a:C['sources'][a]['commit'] for a in ('baseline','champion')}}
        result.update({'backend':'CPU','condition':'independent-pre-skip-vs-champion','mask_identity':{'harness_sha256':C['inputs']['input/'+harness+'.cpp'],'case':case,'shared_trunk':harness=='shared' and case>=86},'original_source_sha256':C['inputs']['input/original.cpp'],'build_identity':{arm:json.loads((B/'identity.json').read_text()) for arm,B in zip(('baseline','champion'),builds)},'tool_identity':{'job_sha256':C['inputs']['job.py'],'argv':sys.argv,'python':sys.version},'run_identity':{'attempt':str(A),'filler_id':os.environ.get('FILLER_ID'),'cpus':os.environ['FILLER_CPUS'],'threads':threads,'timestamp':time.time()}})
        atom(done,result)
        with (R/'results.jsonl').open('a') as f: f.write(json.dumps(result)+'\n'); f.flush(); os.fsync(f.fileno())
# Verify input/source/build custody again before claiming complete.
assert all(sha(D/p)==h for p,h in C['inputs'].items())
for arm,B in zip(('baseline','champion'),builds):
    verify_source(D/'sources'/arm, C['sources'][arm], C['source_repository'])
    assert all(sha(p)==h for p,h in json.loads((B/'identity.json').read_text())['files'].items())
for harness,count in (('original',86),('shared',111)):
    for case in range(count):
        rec=json.loads((R/f'{harness}-{case:03d}.json').read_text())
        assert rec['binding']==binding and rec['status']=='PASS'
        assert all(sha(p)==h for p,h in rec['files'].items())
atom(R/'verdict.json',{'status':'PASS','binding':binding,'original_cases':86,'extended_cases':111,'new_shared_cases':25,'criterion':'all CPU outputs bit-identical; original outputs preserved'})
(R/'COMPLETE').write_text(binding)
