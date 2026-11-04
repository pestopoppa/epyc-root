import gzip,hashlib,json,subprocess,sys,tempfile
from collections import Counter
from pathlib import Path
def test_diagnostics():
    P=Path(__file__).resolve().parent;m=json.loads((P/'manifest.json').read_text());rows=m['rows']
    assert len(rows)==256 and len({(r['id'],r['nominal']) for r in rows})==256
    assert Counter((r['split'],r['group'],r['nominal']) for r in rows)=={(s,g,n):8 for s in ('dev','heldout') for g in ('code','multihop','document_qa','agent_history') for n in (8192,32768,131072,262144)}
    assert {r['source_id'] for r in rows if r['split']=='dev'}.isdisjoint({r['source_id'] for r in rows if r['split']=='heldout'})
    for r in rows:
     raw=gzip.decompress((P/r['token_ids']).read_bytes());assert hashlib.sha256(raw).hexdigest()==r['token_ids_sha256'];assert len(json.loads(raw))==r['prompt_n'];assert r['prompt_n']+r['max_output_tokens']<=262144
    with tempfile.TemporaryDirectory() as d:
     d=Path(d);binary=d/'candidate';binary.write_text('fixture');adapter=d/'adapter.py';adapter.write_text('import json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"output":"wrong","ttft_ms":10,"tpot_ms":2}))\n')
     binding={'reviewed':True,'model_sha256':m['model_sha256'],'source_commit':'fixture','effective_config':{'speculation':False},'candidate_binary':str(binary),'candidate_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'device_topology':'fixture','kv_dtype':'q8_0','context_config':{'size':8192},'batch_config':{'size':1},'supported_arms':['dense'],'adapter_argv':[sys.executable,str(adapter)]}
     (d/'binding').write_text(json.dumps(binding));r=rows[0]
     def run(arm,name):
      subprocess.run([sys.executable,str(P/'runner.py'),'--binding',str(d/'binding'),'--id',r['id'],'--length',str(r['nominal']),'--arm',arm,'--phase','quality','--output',str(d/name)],check=True,capture_output=True)
      return json.loads((d/name).read_text())
     assert run('pca','invalid')['status']=='invalid';v=run('dense','fail');assert v['status']=='invalid' and v['item']['id']==r['id']
     binding['candidate_binary_sha256']='bad';(d/'binding').write_text(json.dumps(binding));assert run('dense','bad')['status']=='invalid'
    print('256 hashes/counts; disjoint cohorts; unsupported arm, scoring, candidate digest: PASS')

if __name__ == '__main__':
    test_diagnostics()
