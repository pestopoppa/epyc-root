#!/usr/bin/env python3
"""Qualify the private graph using native read-only C72 context/impact queries."""
import hashlib, json, os, pathlib, runpy, subprocess, time
ROOT=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-gnx-split-phase')
P=ROOT/'stage2-packet-r2'; TREE=ROOT/'source-view'; OUT=ROOT/'stage2-results-r2'
DB=TREE/'.gitnexus/lbug'; META=TREE/'.gitnexus/meta.json'; CATALOG=ROOT/'stage1-state/registry/registry.json'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p):digest(p) for p in (DB,META,CATALOG)}
env={k:os.environ[k] for k in ('HOME','PATH','TMPDIR','XDG_CACHE_HOME','LANG','LC_ALL') if k in os.environ}
env.update(GITNEXUS_HOME=str(CATALOG.parent), UV_THREADPOOL_SIZE='1', OMP_NUM_THREADS='1',
           OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', GITNEXUS_LBUG_EXTENSION_INSTALL='never',
           GITNEXUS_LBUG_BUFFER_BYTES='536870912', GITNEXUS_LBUG_MAX_DB_SIZE='8589934592',
           LD_PRELOAD=str(ROOT/'tool/gitnexus-lbug-cap.so'))
def query(name, args):
    if time.time()+40 >= min(int(os.environ['FILLER_END'])-300,int(os.environ['FILLER_DEADLINE'])):
        raise RuntimeError('insufficient query reserve')
    cmd=['/usr/local/bin/node','--v8-pool-size=1','--max-old-space-size=1024',str(P/'readonly-query.cjs'),str(DB),*args]
    with (OUT/(name+'.stdout')).open('wb') as o, (OUT/(name+'.stderr')).open('wb') as e:
        p=subprocess.Popen(cmd,env=env,cwd=TREE,stdout=o,stderr=e)
        peak=0; start=time.monotonic()
        try:
            while p.poll() is None:
                if time.monotonic()-start>30: raise RuntimeError('query timeout')
                try: tids=list(pathlib.Path(f'/proc/{p.pid}/task').iterdir())
                except FileNotFoundError: break
                peak=max(peak,len(tids))
                if len(tids)>12: raise RuntimeError('query node TID cap')
                for t in tids:
                    try:
                        if os.sched_getaffinity(int(t.name)) != {72,73}: raise RuntimeError('query affinity')
                    except ProcessLookupError: pass
                time.sleep(.1)
            rc=p.wait()
        finally:
            if p.poll() is None:
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
    err=(OUT/(name+'.stderr')).read_text()
    if rc or 'GNX_READONLY_READY native_mapped=true readOnly=true autoCheckpoint=false' not in err:
        raise RuntimeError('native read-only query failed '+name)
    (OUT/(name+'.profile.json')).write_text(json.dumps({'peak_node_tids':peak,'returncode':rc,'argv':cmd}))
    return json.loads((OUT/(name+'.stdout')).read_text())
sites={2444:'llama_grammar_accept_impl(',2451:'llama_grammar_apply_impl(',2480:'llama_grammar_init_impl(',2502:'llama_grammar_clone_impl(',2562:'llama_grammar_init_impl(',2564:'llama_grammar_init_impl('}
sampler=(TREE/'src/llama-sampler.cpp').read_text().splitlines()
assert all(text in sampler[line-1] for line,text in sites.items()), 'source-site drift'
expected={'llama_grammar_accept_impl':{'llama_sampler_grammar_accept_impl'},'llama_grammar_apply_impl':{'llama_sampler_grammar_apply'},'llama_grammar_clone_impl':{'llama_sampler_grammar_clone'},'llama_grammar_init_impl':{'llama_sampler_grammar_reset','llama_sampler_init_grammar_impl'}}
results=[]
qualify=runpy.run_path(str(P/'graph-result.py'))['qualify']
for line in (P/'targets.tsv').read_text().splitlines():
    symbol,path=line.split('\t')
    ctx=query('context-'+symbol,['context',symbol,'--repo',str(TREE),'--file',path])
    candidates=[ctx['symbol']] if ctx.get('status')=='found' else ctx.get('candidates',[])
    assert candidates and all(c.get('name')==symbol and c.get('filePath')==path for c in candidates)
    uids=[c['uid'] for c in candidates]; assert len(uids)==len(set(uids))
    if symbol=='llama_grammar_init_impl': assert len(uids)==2 and any('#4~' in u for u in uids) and any('#8~' in u for u in uids)
    found=set()
    for i,uid in enumerate(uids):
        resolved=query(f'resolved-context-{symbol}-{i}',['context',symbol,'--repo',str(TREE),'--file',path,'--uid',uid])
        impact=query(f'impact-{symbol}-{i}',['impact',symbol,'--repo',str(TREE),'--file',path,'--uid',uid,'--direction','upstream','--include-tests','--limit','100'])
        target=impact.get('target',{})
        assert target.get('id')==uid and target.get('name')==symbol and target.get('filePath')==path
        assert impact.get('risk') in ('LOW','MEDIUM') and impact.get('epistemic')=='exact' and impact.get('boundaries',[])==[]
        assert not (impact.get('candidates') or impact.get('error') or impact.get('partial') or impact.get('truncated') or impact.get('pagination',{}).get('truncated'))
        # Reuse r11's native per-depth completeness contract. Source identity
        # is independently established from the sealed C72 capsule; do not
        # claim a git metadata commit for this deliberately gitless view.
        coverage=qualify({},None,{symbol:path},{symbol:resolved},{symbol:impact},True)
        assert not coverage['missing_or_partial_targets'] and not coverage['high_critical'], 'native coverage incomplete'
        if symbol!='llama_grammar_init_impl' or '#8~' in uid:
            for nodes in impact.get('byDepth',{}).values():
                found.update(n.get('name') for n in nodes if n.get('filePath')=='src/llama-sampler.cpp' and n.get('relationType')=='CALLS')
        results.append({'symbol':symbol,'uid':uid,'risk':impact['risk'],'epistemic':impact['epistemic']})
    if symbol in expected: assert expected[symbol] <= found, f'missing callers: {symbol} {expected[symbol]-found}'
after={str(p):digest(p) for p in (DB,META,CATALOG)}
assert before==after, 'graph or registry changed during queries'
receipt={'status':'SCOPED_C72_SENTINELS_PASS_REVIEW_ONLY','sites':sites,'callers':{k:sorted(v) for k,v in expected.items()},'targets':results,'graph_hashes':after,'scope':'audited C72 grammar targets and callers only','fold_authority':False}
tmp=OUT/'SENTINELS.json.tmp'; tmp.write_text(json.dumps(receipt,indent=2)+'\n'); tmp.replace(OUT/'SENTINELS.json')
print('SCOPED_C72_SENTINELS_PASS_REVIEW_ONLY')
