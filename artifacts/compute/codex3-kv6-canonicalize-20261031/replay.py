import ast,hashlib,json,re
from pathlib import Path
root=Path('/mnt/raid0/llm/tmp/codex3-kv6-evidence-20261031'); prior=Path('/mnt/raid0/llm/tmp/inf05-kv6-canonicalize-20261029');h=lambda b:hashlib.sha256(b).hexdigest()
def load(name):
 s=(root/name).read_text();tree=ast.parse(s);f=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='canonicalize_prompt');text=ast.get_source_segment(s,f);ns={'re':re};exec(compile(ast.Module(body=[f],type_ignores=[]),name,'exec'),ns);return ns[f.name],h(text.encode())
a,ah=load('prefix_cache-original.py');b,bh=load('prefix_cache-current.py');assert ah==bh
raw=next(json.loads(x) for x in (prior/'measurement.log').read_text().splitlines() if x.startswith('{"affinity"'));rows=[]
patterns={'plain':'A simple example of a text prompt with ordinary words.\n','mixed':'2024-01-15T10:30:00Z 550e8400-e29b-41d4-a716-446655440000\r\n\n\nHello world! '}
for r in raw['rows']:
 text=(patterns[r['pattern']]*(r['chars']//len(patterns[r['pattern']])+1))[:r['chars']];old=a(text);new=b(text);assert old==new and len(old)==r['output_chars'];assert len(r['samples_ns_per_call'])==9
 rows.append({'chars':r['chars'],'pattern':r['pattern'],'input_sha256':h(text.encode()),'output_sha256':h(old.encode()),'output_chars':len(old),'router_projection_sha256':h(old[:256].encode()),'median_wall_ms':r['median_ns_per_call']/1e6,'sample_wall_ms':[x/1e6 for x in r['samples_ns_per_call']],'calls_per_batch':r['reps_per_batch'],'batch_count':9})
out={'schema':'kv6-retained-evidence-audit/v1','original_commit':'84f6f6f15f713d21098dbad2b153d32f8cc13624','current_commit':'9ca8511726afddea9c4e0fc2af4a43fb27d2adf4','exact_function_sha256':ah,'current_function_sha256':bh,'original_file_sha256':h((root/'prefix_cache-original.py').read_bytes()),'current_file_sha256':h((root/'prefix_cache-current.py').read_bytes()),'prior_raw_log_sha256':h((prior/'measurement.log').read_bytes()),'prior_harness_sha256':h((prior/'measure.py').read_bytes()),'equal_outputs':True,'affinity':raw['affinity'],'python':raw['python'],'mode':'retained wall time per call from shared-host synthetic R6 batches; no process CPU timing or production latency','rows':rows}
(root/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print('8 fixtures same outputs; samples',sum(len(x['sample_wall_ms']) for x in rows),'total calls',sum(x['calls_per_batch']*9 for x in rows),'function',ah)
