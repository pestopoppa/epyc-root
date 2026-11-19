def main():
    import importlib.util,json,os,pathlib,subprocess,sys
    D=pathlib.Path(os.environ.get('KPF62_BUILD_ROOT','/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104'))
    subprocess.run([sys.executable,str(D/'check.py')],check=True)
    S=D/'source/scripts/chunk-kv'
    sys.path.insert(0,str(S))
    spec=importlib.util.spec_from_file_location('fixture',S/'tests/test_g3_manifest.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    f=mod.FrozenGateTest();f.setUp()
    try:
     p=f.root;run=p/'run';run.mkdir();(run/'meta.json').write_text(json.dumps({'n_cont':64}))
     with (run/'requests.jsonl').open('w') as rf,(run/'positions.jsonl').open('w') as pf:
      for (rid,mode),row in f.reqs.items():
       rf.write(json.dumps(dict(row,id=rid,mode=mode,r=.2,mean_kl=.01,bit_identical_to_ref=mode=='all-inject'))+'\n')
       for point in f.pos[(rid,mode)]:pf.write(json.dumps(dict(point,id=rid,mode=mode,kl=.1 if mode=='none' else .01,nmse=.001,top1=1))+'\n')
     for o in f.outcomes:o['finish_reason']='eog'
     f.op.write_text(''.join(json.dumps(x)+'\n' for x in f.outcomes))
     seg=p/'segments.jsonl'; segments=[{'id':rid,'arm':arm,'segment':0,'start':0,'tokens':[7,i],'finish_reason':'eog'} for i,rid in enumerate(f.ids) for arm in ('full','reuse')];seg.write_text(''.join(json.dumps(x)+'\n' for x in segments))
     t=p/'thresholds.md';t.write_text(f'## 8. Corpus manifest\n- manifest path / sha256: x / {mod.gm.sha(f.mp)}\n## 9. Amendments\n')
     shim='''import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); import g3_manifest as m; m.BUCKETS=((12,16),(16,20),(20,24),(24,28));m.GATE_MIN_REQUESTS=4;m.GATE_MIN_PER_BUCKET=1; p=sys.argv[0]; exec(compile(open(p).read(),p,"exec"),{"__name__":"__main__","__file__":p})'''
     # Override only gate statistical coverage constants for this synthetic four-request exercise.
     shim=shim.replace('p=sys.argv[0];','p=sys.argv[0];').replace('exec(compile(open(p).read(),p,"exec"),{"__name__":"__main__","__file__":p})','d={"__name__":"fixture_gate","__file__":p};exec(compile(open(p).read(),p,"exec"),d);d["BUCKETS"]=[("a",12,16),("b",16,20),("c",20,24),("d",24,28)];d["CORPUS_MIN_REQUESTS"]=4;d["CORPUS_MIN_PER_BUCKET"]=1;sys.exit(d["main"]())')
     # -c leaves argv[0] = -c: rebind explicitly to the real entrypoint.
     shim=shim.replace('p=sys.argv[0];','p=sys.argv.pop(1);sys.argv[0]=p;')
     cmd=[sys.executable,'-B','-c',shim,str(S),str(S/'g3_gate.py'),'gate','--run',str(run),'--thresholds',str(t),'--manifest',str(f.mp),'--corpus',str(f.cp),'--tasks',str(f.tp),'--retention',str(f.op),'--outcome-segments',str(seg),'--out',str(p/'result')]
     a=subprocess.run(cmd,text=True,capture_output=True);print('valid:',a.returncode,a.stdout[-300:],a.stderr[-300:]);assert a.returncode==0
     j=json.loads((p/'result.json').read_text());assert j['task_scores']['retention']==1 and j['task_scores']['outcome_segments_sha256']==mod.gm.sha(seg)
     (p/'result.json').unlink();(p/'result.md').unlink()
     for name,rows in [('interrupted',segments[:-1]),('exhausted',[dict(x,finish_reason='length') if x['arm']=='reuse' and x['id']==f.ids[0] else x for x in segments])]:
      seg.write_text(''.join(json.dumps(x)+'\n' for x in rows)); b=subprocess.run(cmd,text=True,capture_output=True);print(name+':',b.returncode,b.stdout[-300:],b.stderr[-300:]);assert b.returncode==3 and 'REFUSED' in b.stdout and not (p/'result.json').exists()
    finally:f.doCleanups()


def test_all():
    assert main() is None


if __name__ == "__main__":
    main()
