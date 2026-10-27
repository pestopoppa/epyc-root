"""Future real graph audit; MAIN exact packet review and real canonical grant."""
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess as sp
import sys
import types
import time
BASE = 'c72ec82f5417bb2937310326120f149b665e8400'
PROD = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
CANON = Path('/mnt/raid0/llm/llama.cpp')
rows = []
current = None
stop_reason = None
owns_results = False
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
    signal.signal(sig, lambda s, f: globals().__setitem__('stop_reason', 'signal-'+str(s)))

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(name, obj):
    (R/name).write_text(json.dumps(obj, indent=2)+'\n')

def proc(pid):
    try:
        raw = Path(f'/proc/{pid}/stat').read_text()
        v = raw[raw.rindex(')')+2:].split()
        return {'pid':int(pid), 'pgid':int(v[2]), 'sid':int(v[3]), 'start':int(v[19]),
                'rss':int(v[21])*os.sysconf('SC_PAGE_SIZE'), 'state':v[0]}
    except FileNotFoundError:
        return None

def members(identity):
    found=[]
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            q=proc(p.name)
            if q and q['sid']==identity['sid'] and q['pgid']==identity['pgid']:
                found.append(q)
    return found

def guard():
    if stop_reason:
        raise RuntimeError(stop_reason)
    if time.time() >= min(int(os.environ['FILLER_DEADLINE']),int(os.environ['FILLER_END'])-300):
        raise RuntimeError('HELD: cleanup reserve/deadline')
    # Explicit child return code is checked, including when caller is in an exception handler.
    q=sp.run(['/bin/bash','-c','source "$1"; canonical_guard || exit 6','guard',str(B/'guard.sh')],
             stdout=sp.DEVNULL, stderr=sp.PIPE, timeout=10)
    if q.returncode:
        raise RuntimeError('HELD: canonical guard refused '+q.stderr.decode(errors='replace'))

def cleanup(p, ident):
    evidence={'identity':ident,'steps':[]}
    # A captured group whose leader died remains ours; new unrelated PID reuse fails closed.
    q=proc(p.pid)
    if q and (q['start']!=ident['start'] or q['sid']!=ident['sid'] or q['pgid']!=ident['pgid']):
        raise RuntimeError('FAILED: captured leader identity changed; no signal sent')
    for sig, seconds in ((signal.SIGTERM,10),(signal.SIGKILL,10)):
        live=members(ident)
        evidence['steps'].append({'signal':int(sig),'before':live})
        if not live:
            break
        os.killpg(ident['pgid'],sig)
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            p.poll()  # reap our direct child, even if descendants remain
            if not members(ident):
                break
            time.sleep(.2)
    p.wait(timeout=5)
    evidence['after']=members(ident)
    evidence['leader_after']=proc(p.pid)
    save('cleanup-'+str(p.pid)+'.json',evidence)
    if evidence['after'] or evidence['leader_after']:
        raise RuntimeError('FAILED: owned group death not proved')

def run(name, argv, seconds=120, cwd=None, env=None, allowed=(0,)):
    global current
    guard()  # Never spawn after a failing admission/deadline check.
    start=time.time()
    out=R/(name+'.stdout'); err=R/(name+'.stderr')
    with out.open('wb') as fo, err.open('wb') as fe:
        p=sp.Popen([str(x) for x in argv],cwd=cwd,env=env,stdout=fo,stderr=fe,start_new_session=True)
        current=p
        ident=proc(p.pid)
        # Parent captures start ticks immediately; session creation is done by Popen before return.
        if not ident or ident['pid']!=ident['sid'] or ident['pid']!=ident['pgid']:
            raise RuntimeError('FAILED: cannot prove captured phase session identity')
        save(name+'.identity.json',ident)
        failure=None; peak=0
        try:
            while p.poll() is None:
                guard()
                if time.time()-start>=seconds:
                    raise RuntimeError('HELD: phase timeout '+name)
                live=members(ident); rss=sum(x['rss'] for x in live)+(proc(os.getpid()) or {}).get('rss',0);peak=max(peak,rss)
                with (R/'rss.jsonl').open('a') as f:
                    f.write(json.dumps({'time':time.time(),'phase':name,'rss':rss,'members':live})+'\n')
                if rss>LIMIT:
                    raise RuntimeError('HELD: aggregate RSS exceeds 20GiB')
                time.sleep(.5)
            rc=p.wait()
            if rc not in allowed:
                raise RuntimeError('FAILED: phase '+name+' rc='+str(rc))
        except BaseException as e:
            failure=e
        finally:
            cleanup(p,ident)
            current=None
            rows.append({'phase':name,'argv':[str(x) for x in argv],'cwd':str(cwd),
                         'start':start,'end':time.time(),'rc':p.returncode,'peak_rss':peak,
                         'stdout':str(out),'stderr':str(err),'failure':str(failure) if failure else None})
            save('phases.json',rows)
        if failure:
            raise failure
    return out.read_text(errors='replace')

def git(name,*args,**kw):
    return run(name,['git','-C',str(TREE),*args],**kw).strip()

def manifest(root):
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise RuntimeError('FAILED: symlink in sealed asset tree '+str(p))
        if p.is_file():result[str(p.relative_to(root))]=digest(p)
    assert result
    return result

def binary_manifest(root):
    result={}
    for p in sorted(root.rglob('*')):
        if p.is_file():
            assert p.resolve().is_relative_to(root.resolve()), 'binary symlink escapes build'
            result[str(p.relative_to(root))]={'sha256':digest(p),'mtime':p.stat().st_mtime,
                'symlink':os.readlink(p) if p.is_symlink() else None}
    assert result

# New job: only graph/control-plane evidence; never applies SOURCE.patch or builds.
B = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/packet')
R = B.parent / 'results'
P = B.parent / 'private'
TREE = P / 'inf50-c5-c72ec82-edge-repair'
ALIAS = 'inf50-c5-c72ec82-edge-repair-20261027'
LIMIT = 20 * 1024**3
WRAPPER = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-c5-graph-call-edge-repair/writer/gitnexus-analyze.sh')
H=B.parent/'helpers'
CATALOG = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-raid-catalog-full/catalog/registry.json')
PATCH = '8669cf08f9fe33ddd5cd91d8548dbf35bdfe79ca2a570b24b0dbf0779a5127d3'

def proc(pid):
    try:
        root=Path('/proc')/str(pid)
        raw=(root/'stat').read_text();v=raw[raw.rindex(')')+2:].split()
        uid=int(next(x for x in (root/'status').read_text().splitlines() if x.startswith('Uid:')).split()[1])
        return {'pid':int(pid),'pgid':int(v[2]),'sid':int(v[3]),'start':int(v[19]),
                'uid':uid,'rss':int(v[21])*os.sysconf('SC_PAGE_SIZE'),'state':v[0]}
    except FileNotFoundError:
        return None

def members(identity):
    found=[]
    for p in Path('/proc').iterdir():
        if p.name.isdigit():
            q=proc(p.name)
            if q and q['sid']==identity['sid'] and q['pgid']==identity['pgid']:
                if q['uid']!=identity['uid']:raise RuntimeError('group UID changed; refuse signal')
                found.append(q)
    return found

def native_high_critical(obj):
    # Preserve the engine's risk independently of completeness/consumer validity.
    return isinstance(obj,dict) and obj.get('risk') in ('HIGH','CRITICAL')

def qualify_impact(obj,symbol,path,uid):
    # Structured fields only. Missing/ambiguous/unavailable/partial can never be LOW.
    if not isinstance(obj,dict):raise ValueError('impact must be object')
    target=obj.get('target')
    if not isinstance(target,dict) or target.get('name')!=symbol or target.get('filePath')!=path or target.get('id')!=uid:
        raise ValueError('unresolved or wrong impact target')
    if obj.get('candidates') or obj.get('error') or obj.get('partial') or obj.get('truncated') or obj.get('pagination',{}).get('truncated'):
        raise ValueError('ambiguous/error/partial impact')
    if obj.get('risk') not in ('LOW','MEDIUM','HIGH','CRITICAL'):
        raise ValueError('unknown risk')
    if type(obj.get('impactedCount')) is not int:raise ValueError('missing impact count')
    epistemic=obj.get('epistemic')
    boundaries=obj.get('boundaries',[])
    if epistemic not in ('exact','lower-bound'):raise ValueError('missing/unknown native epistemic field')
    if not isinstance(boundaries,list) or any(not isinstance(x,str) or not x.strip() for x in boundaries):
        raise ValueError('malformed native boundaries')
    if epistemic=='lower-bound' and not boundaries:raise ValueError('lower-bound lacks native boundaries')
    if epistemic=='exact' and boundaries:raise ValueError('contradictory native epistemic fields')
    return {'risk':obj['risk'],'epistemic':epistemic,'boundaries':boundaries,
            'complete_for_fold':epistemic=='exact','stop_fold':native_high_critical(obj)}

def context_uids(obj,symbol,path):
    if obj.get('status')=='found':
        item=obj.get('symbol',{})
        if item.get('name')!=symbol or item.get('filePath')!=path:raise ValueError('context mismatch')
        return [item['uid']]
    # Overloads are resolved individually, never assigned the aggregate UNKNOWN risk.
    candidates=obj.get('candidates')
    if not isinstance(candidates,list) or not candidates:raise ValueError('context unavailable')
    selected=[x['uid'] for x in candidates if x.get('name')==symbol and x.get('filePath')==path]
    if len(selected)!=len(candidates) or len(set(selected))!=len(selected):raise ValueError('context ambiguity')
    return selected

def load_helpers():
    source={}
    for line in (B/'HELPERS.SHA256').read_text().splitlines():
        expected,name=line.split(maxsplit=1);p=B.parent/name
        raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==expected
        source[p.name]=raw
    modules={}
    for name in ('catalog_binding','owned_session','query_route','graph_result'):
        module=types.ModuleType(name);module.__file__=str(H/(name+'.py'))
        sys.modules[name]=module
        exec(compile(source[name+'.py'],module.__file__,'exec'),module.__dict__)
        modules[name]=module
    return modules

def qualify_query_stderr(stderr, record):
    ready = 'GNX_READONLY_READY native_mapped=true readOnly=true autoCheckpoint=false\n'
    if stderr == ready:
        return
    captured = record.get('death_proof', {}).get('captured', [])
    if not captured or type(captured[0].get('pid')) is not int:
        raise ValueError('missing captured query PID')
    expected = captured[0]['pid']
    pattern = (r'GNX_READONLY_READY native_mapped=true readOnly=true autoCheckpoint=false\n'
               r'GNX_NATIVE_CAP pid=([1-9][0-9]*) requested=([0-9]+) applied=1 observed=1\n')
    match = re.fullmatch(pattern, stderr)
    if not match or int(match.group(1)) != expected:
        raise ValueError('unexpected query stderr or native PID/cap')

def query(name,args,env):
    guard()
    if time.time()+40>=min(int(os.environ['FILLER_END'])-300,int(os.environ['FILLER_DEADLINE'])):
        raise RuntimeError('HELD: query plus owned cleanup cannot fit before reserve')
    # Same supervisor executes the unchanged helper: <=23 sampled child tasks
    # plus this one supervisor, with no additional resident controller process.
    started=time.time()
    record=HELPERS['query_route'].run_query(TREE,args,H/'readonly_query.cjs',R/name,seconds=30)
    rows.append({'phase':name,'start':started,'end':time.time(),'native_record':record})
    save('phases.json',rows)
    guard()
    if record['rc']!=0:raise RuntimeError('native query failed '+name+' rc='+str(record['rc']))
    out=(R/(name+'.stdout')).read_text()
    err=(R/(name+'.stderr')).read_text()
    try:
        qualify_query_stderr(err, record)
    except ValueError as exc:
        raise RuntimeError('unexpected query stderr '+name+': '+str(exc)) from exc
    return out

def source_manifest(env,label):
    records=git('tracked-source-'+label,'ls-files','-s',env=env)
    if any(x.startswith('160000 ') for x in records.splitlines()):
        raise RuntimeError('submodule requires explicit source qualification')
    files={}
    for line in records.splitlines():
        meta,path=line.split('\t',1)
        p=TREE/path
        files[path]={'git_record':meta,'link_text':os.readlink(p)} if p.is_symlink() else {'git_record':meta,'sha256':digest(p)}
    return files

def validate_prepared_paths():
    if R.exists():raise RuntimeError('non-resumable results directory already exists')
    if not P.is_dir() or P.is_symlink() or not TREE.is_dir() or TREE.is_symlink():
        raise RuntimeError('exact prepared private C5 clone missing')

def main():
    global HELPERS, owns_results
    validate_prepared_paths()
    guard()
    R.mkdir()
    owns_results = True
    assert os.environ.get('HOME')=='/home/node' and os.environ.get('GITNEXUS_HOME')=='/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-raid-catalog-full/catalog'
    HELPERS=load_helpers()
    (R/'catalog-before.json').write_bytes(CATALOG.read_bytes())
    save('provenance.json',{'schema':'inf50-real-graph-r7','base':BASE,'patch':PATCH,'source_patch_applied':False,
        'HOME':os.environ['HOME'],'catalog':str(CATALOG),'wrapper':str(WRAPPER),'wrapper_profile':'adopted APP index7 guards/caps; exact-private-C5 RAID writer-lock storage variant',
        'query_profile':'unchanged D9 generic RO/native cap, sampled lifecycle limits; no fixed37 prerequisite',
        'native_predecessor':'/mnt/raid0/llm/tmp/codex-ni-20261026-inf50-window-successor/margin-recovery/results/RESULT.json',
        'speed_claim':None,'INF50_complete':False})
    run('input-seals',['sha256sum','-c',B/'EXTERNAL.SHA256'],30,cwd=B.parent)
    run('source-compile',['/usr/bin/python3','-I','-B','-c',
        'import pathlib,sys;[(compile(p.read_bytes(),str(p),"exec")) for root in sys.argv[1:] for p in pathlib.Path(root).glob("*.py")]',str(B),str(H)],30)
    run('consumer-fixtures',['/usr/bin/python3','-I','-B',B/'test_graph_contract.py'],30)
    run('actual-cli-fixture',['/bin/bash',B.parent/'fixture-final.sh'],180)
    fixture=P/'constructor-db';foreign=P/'foreign-db';fixture.write_text('fixture');foreign.write_text('foreign')
    run('constructor-fixtures',['/usr/local/bin/node','--v8-pool-size=1','--max-old-space-size=128',H/'query_constructor_fixtures.cjs',fixture,foreign],30)
    assert digest(B/'SOURCE.patch')==PATCH
    assert run('owner-pin',['git','-C',CANON,'rev-parse','ak/champion/llama-cpp-ffc1bac82eec'],15).strip()==BASE
    env=dict(os.environ)
    for k in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES',
              'PYTHONPATH','PYTHONHOME','LD_LIBRARY_PATH','LD_PRELOAD'):
        env.pop(k,None)
    env.update(TMPDIR=str(P/'tmp'),XDG_CACHE_HOME=str(P/'cache'),GIT_CONFIG_NOSYSTEM='1',
        GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0',PYTHONDONTWRITEBYTECODE='1')
    for d in ('tmp','cache','hooks'):(P/d).mkdir(exist_ok=True)
    assert not (TREE/'.git/objects/info/alternates').exists() and not (TREE/'.git/shallow').exists()
    assert (TREE/'.git').stat().st_ino!=(CANON/'.git').stat().st_ino
    assert git('head','rev-parse','HEAD',env=env)==BASE
    assert not (TREE/'.gitnexus').exists(),'prepared private clone must not contain an inherited index'
    run('ancestor',['git','-C',TREE,'merge-base','--is-ancestor',PROD,BASE],15,env=env)
    assert git('clean-before','status','--porcelain','--untracked-files=all',env=env)==''
    for p in (TREE/'.git/objects').rglob('*'):
        if p.is_file():assert p.stat().st_nlink==1
    orch_result=json.loads(Path('/mnt/raid0/llm/tmp/codex-ni-20261027-orch-registration-recovery-v2/result/RESULT.json').read_bytes())
    assert orch_result['rc']==0 and orch_result['stage']=='complete-private-orch-baseline-registration'
    before=source_manifest(env,'before');save('analyzed-source-before.json',before)
    # Correct cwd is material: the versioned APP writer admits this exact v3 tree.
    run('analyze',['/bin/bash',WRAPPER,TREE,'--name',ALIAS,'--force','--index-only','--workers','19'],3000,cwd=TREE,env=env)
    analyze_errors=(R/"analyze.stderr").read_text()
    forbidden=("timed out", "timeout budget", "retiring without", "dropping slot",
        "quarantin", "Failed to parse file", "Query execution failed",
        "scope extraction failed", "parse exceeded", "Query compilation failed")
    assert not any(marker.lower() in analyze_errors.lower() for marker in forbidden), "INCOMPLETE: native parser degradation; graph unqualified"
    run('c72-parsed-sites',['/usr/bin/python3','-I','-B',B/'c72-site-check.py',TREE],90)
    after=source_manifest(env,'after');save('analyzed-source-after.json',after)
    assert before==after,'analyze modified tracked source'
    meta=json.loads((TREE/'.gitnexus/meta.json').read_text())
    assert meta.get('lastCommit')==BASE and meta.get('repoPath')==str(TREE)
    save('graph-meta.json',meta)
    catalog=json.loads(CATALOG.read_text());entries=[x for x in catalog if x.get('name')==ALIAS]
    assert len(entries)==1 and entries[0].get('path')==str(TREE) and entries[0].get('lastCommit')==BASE
    assert entries[0].get('storagePath')==str(TREE/'.gitnexus')
    others=[x for x in catalog if x.get('name')!=ALIAS]
    assert others==json.loads((R/'catalog-before.json').read_bytes()), 'unrelated catalog entries changed'
    save('catalog-after.json',catalog)
    save('CATALOG-RECEIPT.json',{**HELPERS['catalog_binding'].provenance(os.environ),
        'registry_sha256':digest(CATALOG),'producer_packet_sha256':digest(B/'PACKET.sha256'),
        'orch_producer_receipt_sha256':digest(Path('/mnt/raid0/llm/tmp/codex-ni-20261027-orch-registration-recovery-v2/result/CATALOG-RECEIPT.json')),
        'baseline_commit':BASE,'alias':ALIAS,'graph_repository':str(TREE)})
    db_before=digest(TREE/'.gitnexus/lbug');meta_before=digest(TREE/'.gitnexus/meta.json')
    catalog_before_query=digest(CATALOG)
    snapshot_before_query=HELPERS['catalog_binding'].provenance(os.environ)
    save('graph-identity-before-query.json',{'db_sha256':db_before,'meta_sha256':meta_before,'catalog_entry':entries[0]})
    try:
        audit(env)
    finally:
        assert digest(CATALOG)==catalog_before_query, 'full catalog changed during RO query window'
        assert HELPERS['catalog_binding'].provenance(os.environ)==snapshot_before_query, 'authentic snapshot drift'
        final_entries=[x for x in json.loads(CATALOG.read_text()) if x.get('name')==ALIAS]
        assert final_entries==entries,'private C5 catalog binding changed'
        assert digest(TREE/'.gitnexus/lbug')==db_before and digest(TREE/'.gitnexus/meta.json')==meta_before,'private graph changed during RO queries'
        save('graph-identity-after-query.json',{'db_sha256':db_before,'meta_sha256':meta_before,'unchanged':True})
def audit(env):
    status=query('status',['status'],env)
    assert 'Status: ✅ up-to-date' in status and str(TREE) in status
    results=[];high=False;incomplete=False
    for symbol,path in [x.split('\t') for x in (B/'GNX-TARGETS.tsv').read_text().splitlines()]:
        raw=query('context-'+symbol,['context',symbol,'--repo',ALIAS,'--file',path],env)
        obj=json.loads(raw);uids=context_uids(obj,symbol,path)
        for number,uid in enumerate(uids):
            # Every overload has its own context and impact evidence.
            prefix=symbol+'-'+str(number)
            c=json.loads(query('resolved-context-'+prefix,['context',symbol,'--repo',ALIAS,'--file',path,'--uid',uid],env))
            assert context_uids(c,symbol,path)==[uid]
            impact=json.loads(query('impact-'+prefix,['impact',symbol,'--repo',ALIAS,
                '--file',path,'--uid',uid,'--direction','upstream','--include-tests','--limit','100'],env))
            # A native HIGH/CRITICAL stops folding even if subsequent UID,
            # pagination, completeness or other consumer checks refuse evidence.
            if native_high_critical(impact):
                high=True
                (R/'HIGH-CRITICAL-STOP.flag').write_text('Native HIGH/CRITICAL observed; explicit operator continuation required before dependent fold.\n')
                save('HIGH-CRITICAL-'+prefix+'.json',{'requested_uid':uid,'impact':impact})
            disposition=qualify_impact(impact,symbol,path,uid)
            native_coverage=HELPERS['graph_result'].qualify({'metadata_commit':BASE},BASE,
                {symbol:path},{symbol:c},{symbol:impact},True)
            # Reuse the final D9 native-consumer contract for detailed count,
            # direction and context completeness; keep native grading untouched.
            if native_coverage['missing_or_partial_targets']:
                disposition['complete_for_fold']=False
            incomplete |= not disposition['complete_for_fold']
            results.append({'symbol':symbol,'path':path,'uid':uid,**disposition,
                'native_coverage':native_coverage,'impact':impact})
    # Independent c72 source-site canaries: parse sites are distinct even
    # though the native graph deduplicates repeated caller-to-callee edges.
    sampler=(TREE/'src/llama-sampler.cpp').read_text().splitlines()
    sites={2444:'llama_grammar_accept_impl(',2451:'llama_grammar_apply_impl(',2480:'llama_grammar_init_impl(',2502:'llama_grammar_clone_impl(',2562:'llama_grammar_init_impl(',2564:'llama_grammar_init_impl('}
    assert all(text in sampler[line-1] for line,text in sites.items()), 'source-site sentinel drift'
    expected={'llama_grammar_accept_impl':{'llama_sampler_grammar_accept_impl'},'llama_grammar_apply_impl':{'llama_sampler_grammar_apply'},'llama_grammar_clone_impl':{'llama_sampler_grammar_clone'},'llama_grammar_init_impl':{'llama_sampler_grammar_reset','llama_sampler_init_grammar_impl'}}
    for symbol, callers in expected.items():
        found=set()
        for item in results:
            if item['symbol']!=symbol or (symbol=='llama_grammar_init_impl' and '#8~' not in item['uid']): continue
            impact=item['impact']
            for nodes in impact.get('byDepth',{}).values():
                found.update(n.get('name') for n in nodes if n.get('filePath')=='src/llama-sampler.cpp' and n.get('relationType')=='CALLS')
        assert callers<=found, 'missing real c72 upstream callers: '+symbol+' '+str(callers-found)
    save('C72-SOURCE-SENTINELS.json',{'sites':sites,'callers':{k:sorted(v) for k,v in expected.items()},'note':'Two init call sites in one caller share one native caller/callee edge.'})
    save('GNX-RESULT.json',{'coverage':'fresh-pinned-baseline-graph','base':BASE,'analyzed_patch':None,
        'targets':results,'qualified_index':True,'trust_scope':'audited C5 grammar targets and mandatory sampler caller sentinels only; namespace, indirect include and ambiguous C++ resolution remain unqualified', 'fold_evidence_complete':not incomplete,
        'fold_gate':'STOP-HIGH-CRITICAL' if high else 'INCOMPLETE-NATIVE-EPISTEMIC' if incomplete else 'REVIEW-REQUIRED',
        'new_candidate_symbols_covered':False,'speed_claim':None,'INF50_complete':False})
    if high:
        (R/'HIGH-CRITICAL-STOP.flag').write_text('Operator explicit continuation required before dependent fold.\n')
        raise RuntimeError('HIGH/CRITICAL: fold STOP; raw audit retained')
    if incomplete:
        raise RuntimeError('INCOMPLETE: native context/impact coverage or epistemic boundary; fold HELD, raw risk/boundaries retained')

if __name__=='__main__':
    status='FAILED';error=None
    try:
        main();status='GRAPH-AUDIT-COMPLETE-FOLD-REVIEW-ONLY'
    except BaseException as e:
        error=str(e)
    finally:
        if owns_results:
            save('RESULT.json',{'schema':'inf50-real-graph-v1','status':status,'error':error,'phases':rows,
                'source_patch_applied':False,'speed_claim':None,'INF50_complete':False})
            save('RAW-SEALS.json',{str(p.relative_to(R)):digest(p) for p in sorted(R.rglob('*'))
                if p.is_file() and p.name!='RAW-SEALS.json'})
            (B.parent/'REPORT-READY.flag').write_text(status+'\n')
        elif error:
            refusal = B.parent / ('refusal-'+str(os.getpid())+'-'+str(time.time_ns())+'.json')
            with refusal.open('x') as stream:
                json.dump({'status':'REFUSED','error':error,'results_untouched':True},stream)
    if error:raise SystemExit(1)
