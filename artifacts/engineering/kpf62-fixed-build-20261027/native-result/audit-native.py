import collections,hashlib,json,math,pathlib
B=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf62-fixed-build'); R=B/'native-20261027T205829Z'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(B/'SOURCE.SHA256SUMS')=='5a043e80063a824998b7132b6a3acf5ebf340b4cfa76d8ac90976d2faf4febd0'
assert sha(B/'build-receipt.json')=='6cddb24429ce2a590f83a0303d88719ee2183b5c036ee4ac861d42f1a883fdca'
assert sha(B/'assembly.json')=='d46fe46c1cdff973f641df81d1d8e384db5e43371f7edfbb2890c6eb5f0abcc6'
build=json.loads((B/'build-receipt.json').read_text()); assembly=json.loads((B/'assembly.json').read_text()); inv=json.loads((R/'invocation.json').read_text())
assert assembly['champion']=='c72ec82f5417bb2937310326120f149b665e8400' and assembly['api_origin']=='b40f8c60f36ad25a418ccc836d1ac0ab0a05a0c9'
for p,h in build['files'].items(): assert sha(pathlib.Path(p))==h,p
for name,h in assembly['files'].items(): assert sha(pathlib.Path(assembly['candidate'])/name)==h,name
for a in inv['artifacts']: assert sha(pathlib.Path(a['path']))==a['sha256'],a
assert (pathlib.Path(inv['binary']['path']).read_bytes()[:4]==b'\x7fELF') and sha(pathlib.Path(inv['binary']['path']))==inv['binary']['sha256']
raw=(R/'g1-position.jsonl').read_bytes(); assert hashlib.sha256(raw).hexdigest()==inv['capture']['sha256']==json.loads((R/'finalized/ACCEPTED.json').read_text())['raw_sha256']; assert raw==(R/'finalized/g1-position.jsonl').read_bytes()
rows=[json.loads(x) for x in raw.splitlines()]; groups=collections.defaultdict(list)
for x in rows:
 assert x['schema']=='epyc.chunk_kv.g1_position.v1' and math.isfinite(x['sum_sq_error']) and math.isfinite(x['reference_sq_norm']) and x['sum_sq_error']>=0 and x['reference_sq_norm']>=0
 groups[(x['delta'],x['component'],x['comparison'])].append(x)
assert len(rows)==324 and len(groups)==18
for (delta,component,comparison),g in sorted(groups.items()):
 assert delta in (1,17,300) and component in ('k','v','logits') and comparison in ('inject_vs_seq_add','inject_vs_in_place_ref')
 want=range(delta,delta+24) if component in ('k','v') else range(delta+24,delta+30)
 assert sorted(x['position'] for x in g)==list(want), (delta,component,comparison,[x['position'] for x in g])
 err=sum(x['sum_sq_error'] for x in g); norm=sum(x['reference_sq_norm'] for x in g); mismatch=sum(x['mismatch_count'] for x in g)
 print(delta,component,comparison,'n',len(g),'sse',err,'refnorm',norm,'nmse',err/norm if norm else None,'mismatch',mismatch)
 if comparison=='inject_vs_seq_add': assert mismatch==0 and err==0
controls=json.loads((R/'native-controls.json').read_text()); assert controls['unsupported_capture']['exit_code']==2 and controls['unsupported_memory_api_and_decode']['exit_code']==0 and all(controls[x]['child_drained'] for x in ('unsupported_capture','unsupported_memory_api_and_decode')); assert not (R/'unsupported-position.jsonl').exists()
grades=json.loads((R/'finalized/grades.json').read_text()); assert len(grades)==27 and all(x['quality']=='Judged' and x['truth']=='Located' for x in grades)
print('AUDIT PASS rows=324 groups=18 buildfiles=',len(build['files']),'assemblyfiles=',len(assembly['files']),'invocation_artifacts=',len(inv['artifacts']),'grades=27 Judged/Located')
for name,h in build['manifest_evidence'].items(): assert sha(B/name)==h,name
for receipt in ('build-receipt.json','assembly.json'):
 assert sha(B/receipt)==inv['artifacts'][[a['kind'] for a in inv['artifacts']].index('build_receipt')]['sha256'] if receipt=='build-receipt.json' else True
assert inv['capture']['exit_code']==0 and inv['lifecycle']['child_drained'] and not inv['lifecycle']['timed_out']
print('MANIFEST PASS evidence=',len(build['manifest_evidence']),'capture exit0 drained timeout_false')
