#!/usr/bin/env python3
"""Conservative native journal inventory; prospective plan, never an execution grant."""
import collections,hashlib,json,pathlib,re,sys
P=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json')
EXPECTED_PLAN='63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68'
ROOTS=[pathlib.Path(x) for x in ['/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh','/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh','/mnt/micron/codex3-pip-pool1-r32-20261031/campaigns-fresh','/mnt/micron/codex3-pip-pool2-r30-v2-20261031/campaigns-fresh','/mnt/micron/codex3-pip-pool3-tail-r31-20261031/campaigns-fresh','/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh','/mnt/micron/codex3-pip-pool0-merged-r35-20261031/campaigns-fresh']]
SUCCESSOR=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-v2-repair-20261101/campaigns-fresh')
R25=pathlib.Path('/mnt/micron/codex3-pip-relocatable-r25-20261030/campaigns-fresh')
RUNS=[pathlib.Path('/mnt/micron')/x for x in ['codex3-pip-pool1-r32-20261031','codex3-pip-pool2-r30-v2-20261031','codex3-pip-pool3-tail-r31-20261031','codex3-pip-split-r22-20261030','codex3-pip-relocatable-r25-20261030','codex3-pip-head-r26-20261030','codex3-pip-pool0-merged-r35-20261031']]+[pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029')]
ATTEMPT_SEARCH_ROOTS=[pathlib.Path('/mnt/micron'),pathlib.Path('/mnt/raid0/llm/tmp')]
def discover_attempt_roots():
 out=[]
 for base in ATTEMPT_SEARCH_ROOTS:
  if not base.is_dir():raise ValueError('attempt search root inaccessible '+str(base))
  for p in base.glob('*pip*'):
   if p.is_symlink():raise ValueError('ambiguous attempt root symlink '+str(p))
   if p.is_dir() and (p/'attempts').is_dir():out.append(p)
 return out
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):
 a=p.stat(follow_symlinks=False)
 if not p.is_file() or p.is_symlink():raise ValueError('unsafe file '+str(p))
 b=p.read_bytes();z=p.stat(follow_symlinks=False)
 if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns):raise ValueError('file changed '+str(p))
 return b
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def region_provenance_ok(shard,prov,caps):
 if not isinstance(prov,dict):return False
 ref=prov.get('origin_capture_sha256');meta=caps.get(ref);identity=prov.get('identity',{});grant=prov.get('origin_grant')
 models={'binary':'0aadef69f2b75a1bf5a839a22ed88a5e2f895e5dc492acaae058354690ea9b05','mmproj':'204d757d7610d9b3faab10d506d69e5b244e32bf765e2bab2d0167e65e0a058a','model':'f3ae46ec885050acf4b3d31944431e1fd90d50664fb09126af4a3c050ba14ee8'}
 return bool(meta and shard in meta['shards'] and isinstance(identity,dict) and identity.get('campaign_sha256')=='7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15' and identity.get('model_pins')==models and isinstance(identity.get('source_pins'),dict) and identity['source_pins']==meta.get('source_pins') and isinstance(grant,str) and bool(grant) and grant==meta.get('grant') and digest(grant.encode())==meta.get('grant_sha256'))
def inventory():
 raw=read(P)
 if digest(raw)!=EXPECTED_PLAN:raise ValueError('original plan hash mismatch')
 plan=json.loads(raw);pages=plan['pages']; unknown=set(plan['prior_original_page_exposures_unknown'])
 if len(pages)!=755 or len({x['image'] for x in pages})!=755 or len({x['index'] for x in pages})!=755 or any(type(x['index']) is not int for x in pages):raise ValueError('population invalid')
 roots=list(ROOTS)
 if SUCCESSOR.exists() or SUCCESSOR.is_symlink():
  if not SUCCESSOR.is_dir() or SUCCESSOR.is_symlink():raise ValueError('successor root invalid')
  roots.append(SUCCESSOR)
 if not R25.parent.is_dir():raise ValueError('r25 campaign parent inaccessible')
 if R25.exists():
  if not R25.is_dir() or R25.is_symlink():raise ValueError('r25 root invalid')
  roots.append(R25)
 for root in roots:
  if not root.is_dir() or root.is_symlink():raise ValueError('campaign root inaccessible '+str(root))
 caps={}; missing=[]
 discovered=discover_attempt_roots()
 attempt_roots=sorted(set(RUNS+[SUCCESSOR.parent]+discovered))
 for root in attempt_roots:
  for cap in sorted((root/'attempts').glob('*/capture.json')):
   b=read(cap); obj=json.loads(b); key=digest(b)
   if key in caps:raise ValueError('duplicate capture hash')
   shards=obj.get('shards')
   if shards is None and type(obj.get('shard')) is int:shards=[obj['shard']]
   if not isinstance(shards,list) or not shards or any(type(n) is not int or n<0 for n in shards):raise ValueError('capture shard scope invalid '+str(cap))
   def validate_root(declared):
    path=pathlib.Path(declared);parts=path.parts
    if 'campaigns-fresh' not in parts:
     if obj.get('smoke') is not True:raise ValueError('unscanned non-control root: '+declared)
     return
    j=parts.index('campaigns-fresh');base=pathlib.Path(*parts[:j+1]);tail=parts[j+1:]
    if base not in roots:raise ValueError('unscanned capture-declared root: '+str(base))
    if len(tail)!=2 or not all(re.fullmatch(r'shard-[0-9]+',x) for x in tail) or int(tail[0][6:])!=int(tail[1][6:]) or int(tail[0][6:]) not in shards:raise ValueError('unsupported capture journal layout: '+declared)
    for c in (base,base/tail[0],path):
     if c.is_symlink():raise ValueError('symlink capture journal component: '+str(c))
   for field in ('output_roots','legacy_roots','prior_output_roots'):
    def flatten(x):
     if isinstance(x,str):yield x
     elif isinstance(x,list):
      for y in x:yield from flatten(y)
     else:raise ValueError('ambiguous capture root: '+str(cap))
    for declared in flatten(obj.get(field,[])):
     validate_root(declared)
   config=cap.parent/'worker-config.json'
   if obj.get('smoke') is not True and (config.exists() or not obj.get('output_roots')):
    if not config.is_file() or config.is_symlink():raise ValueError('capture worker config missing '+str(cap))
    cfg=json.loads(read(config))
    if 'output_roots' in cfg:
     declared=cfg.get('output_roots')
     if cfg.get('capture_path')!=str(cap) or cfg.get('shards')!=shards or cfg.get('mode')!='normal' or not isinstance(declared,list) or len(declared)!=len(shards) or (obj.get('output_roots') and obj['output_roots']!=declared):raise ValueError('capture worker config mismatch '+str(cap))
    else:
     allowed={'cpu_english_job_fresh_v2.py':'a24d84d8a8969128996fad41ead4ef1f908209d4cdaba6eeeb0f1ea6716820e8','cpu_english_job_generic.py':'9a3cfb4eb99963fdae3642ea20c01ea2c5c2ad57fb9616b5bcab87abee7ab4f4','cpu_english_job_checkpoint.py':'bd811d16795fd6e33348eeb64d4d549a2aea3452be647c88057b81fc99639153'}
     pins=obj.get('source_pins',{});matched=[n for n,h in allowed.items() if pins.get(n)==h and digest(read(pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029')/n))==h]
     if len(shards)!=1 or cfg.get('shard_index')!=shards[0] or cfg.get('population_sha256')!=EXPECTED_PLAN or len(matched)!=1:raise ValueError('legacy worker config identity mismatch '+str(cap))
     declared=[cfg.get('output')]
    for x in declared:
     if not isinstance(x,str):raise ValueError('worker root malformed '+str(cap))
     validate_root(x)
   rp=cap.parent/'result.json';proof=cap.parent/'result.json.durable';valid=False;reason='result missing';result_sha=None
   if rp.is_file() and not rp.is_symlink():
    try:
     raw_result=read(rp);result_sha=digest(raw_result);result=json.loads(raw_result)
     valid=(config.is_file() and not config.is_symlink() and isinstance(result,dict) and result.get('schema')=='pip02-paddle-parallel-owner/v1' and result.get('capture_sha256')==key and result.get('shards')==shards and result.get('smoke')==obj.get('smoke') and result.get('rc')==0 and result.get('partial') is False and result.get('error') is None and isinstance(result.get('factory'),dict) and result['factory'].get('worker_rc')==0 and proof.is_file() and not proof.is_symlink() and read(proof).decode().strip()==result_sha)
     reason='verified_complete' if valid else 'unbound_or_incomplete_result'
    except (ValueError,TypeError,KeyError,OSError,UnicodeError):reason='corrupt_or_changed_result'
   caps[key]={'path':str(cap),'id':obj.get('id'),'shards':shards,'result_present':rp.is_file(),'result_sha256':result_sha,'terminal_verified':valid,'terminal_reason':reason,'source_pins':obj.get('source_pins'),'grant':obj.get('grant'),'grant_sha256':obj.get('grant_sha256')}
   if not valid:missing.append(key)
 groups={0:list(range(0,151,3))}
 result=[]
 for pool,starts in groups.items():
  for g in starts:
   for shard in range(g,min(g+3,151)):
    dirs=[r/f'shard-{shard:02d}'/inner for r in roots for inner in sorted({f'shard-{shard:02d}',f'shard-{shard}'})]
    files=[]
    for d in dirs:
     if d.is_symlink():raise ValueError('symlink journal')
     if d.exists():
      if not d.is_dir():raise ValueError('invalid journal directory')
      files.extend(d.iterdir())
    expected_pages=pages[shard*5:shard*5+5]
    region_prefixes={'region-'+digest(canon(p))[:24]+'-' for p in expected_pages}
    page_keys={digest(canon({'campaign':'7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15','page':p})) for p in expected_pages}
    names=collections.defaultdict(list)
    for f in files:
     if f.is_file():names[f.name].append(f)
    # Duplicate logical keys across immutable layers make replay ambiguous.
    duplicate=[k for k,v in names.items() if len(v)>1 and not k.startswith('.')]
    unattributed=[k for k in names if (k.startswith('region-') and not any(k.startswith(p) for p in region_prefixes)) or (re.fullmatch(r'[0-9a-f]{64}\.(?:start|sent|result|finish\.json)',k) and k.split('.')[0] not in page_keys)]
    for page in pages[shard*5:shard*5+5]:
     prefix='region-'+digest(canon(page))[:24]+'-'; region=[]; bad=[]; caprefs=set(); page_starts=[]; page_results=[]
     pagekey=digest(canon({'campaign':'7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15','page':page}))
     if any(pagekey+suffix in names for suffix in ('.sent','.result','.finish.json')) and pagekey+'.start' not in names:bad.append('orphan page journal')
     for key in names:
      if key.startswith(prefix) and key.endswith('.result.json') and key[:-len('.result.json')]+'.start.json' not in names:bad.append('orphan region result:'+key)
     for name,paths in names.items():
      if name.startswith(prefix) and name.endswith('.start.json'):
       if len(paths)!=1:bad.append('duplicate:'+name);continue
       p=paths[0]; start=read(p); obj=json.loads(start); key=name[:-len('.start.json')]; ref=(obj.get('provenance') or {}).get('origin_capture_sha256');
       if ref:caprefs.add(ref)
       res=names.get(key+'.result.json',[]); state='unknown'
       if len(res)==1:
        rb=read(res[0]);val=json.loads(rb);dur=names.get(key+'.result.json.durable',[])
        valid=(digest(bytes.fromhex(obj['body_hex']))==obj.get('body_sha256') and val.get('start_sha256')==digest(start) and val.get('request_sha256')==obj.get('body_sha256') and digest(bytes.fromhex(val['body_hex']))==val.get('response_sha256') and val.get('status')==200)
        if res[0].as_posix().startswith('/mnt/micron/'):
         valid=valid and len(dur)==1 and read(dur[0]).decode()==digest(rb)
        state='complete' if valid else 'invalid'
       elif len(res)>1:state='invalid'
       region.append({'start':str(p),'request_sha256':obj.get('body_sha256'),'state':state,'capture_sha256':ref,'provenance':obj.get('provenance',{})})
      elif re.fullmatch(r'[0-9a-f]{64}\.start',name):
       for path in paths:
        val=json.loads(read(path))
        if val.get('page')==page:page_starts.append(str(path))
      elif re.fullmatch(r'[0-9a-f]{64}\.finish\.json',name):
       for path in paths:
        val=json.loads(read(path))
        if val.get('page')==page:
         key=name[:-len('.finish.json')]; result_files=names.get(key+'.result',[]); durable=names.get(name+'.durable',[]); verified=False
         if len(result_files)==1:
          rb=read(result_files[0]); rv=json.loads(rb); st=names.get(key+'.start',[])
          verified=(val.get('result_sha256')==digest(rb) and val.get('markdown_sha256')==rv.get('markdown_sha256') and digest(rv.get('markdown','').encode())==rv.get('markdown_sha256') and len(st)==1 and digest(read(st[0]))==rv.get('start_sha256') and json.loads(read(st[0])).get('page')==page and json.loads(read(st[0])).get('campaign')=='7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15' and val.get('capture_sha256') in caps)
          if str(path).startswith('/mnt/micron/'):verified=verified and len(durable)==1 and read(durable[0]).decode()==digest(read(path))
         owner=caps.get(val.get('capture_sha256'));grant=owner.get('grant') if owner else None
         valid_source=(digest(json.dumps(owner['source_pins'],sort_keys=True,separators=(',',':')).encode())==val.get('source_pins_sha256')) if owner and isinstance(owner.get('source_pins'),dict) else False
         verified=verified and bool(owner) and shard in owner['shards'] and val.get('campaign_sha256')=='7df42c37a8df3a4d35133a8adbeb82af834a06a13ecd074c42bbbee1330f2e15' and isinstance(grant,str) and digest(grant.encode())==val.get('grant_sha256') and valid_source
         page_results.append({'path':str(path),'verified':verified});caprefs.add(val.get('capture_sha256'))
     if duplicate:bad.append('duplicate journal keys present in shard')
     if unattributed:bad.append('unattributed journal key in shard')
     for z in region:
      if not region_provenance_ok(shard,z.get('provenance',{}),caps):
       bad.append('region provenance absent or mismatched: '+z['start'])
      z['provenance_sha256']=digest(canon(z.pop('provenance',{})))
     unknown_captures=[key for key in missing if shard in caps[key]['shards']]
     if unknown_captures:disposition='PROTECTED_SCOPE_UNKNOWN'
     elif any(x['state']!='complete' for x in region): disposition='PROTECTED_REGION_UNKNOWN'
     elif page['index'] in unknown:disposition='PROTECTED_ORIGINAL_UNKNOWN'
     elif bad:disposition='PROTECTED_INVALID'
     elif page_results:disposition='EXISTING_FINISH_VERIFIED' if len(page_results)==1 and page_results[0]['verified'] else 'EXISTING_FINISH_REVIEW'
     elif page_starts or region:disposition='PROTECTED_PRIOR_START'
     else:disposition='ELIGIBLE_NEVER_STARTED'
     result.append({'pool':pool,'group':g,'shard':shard,'page':page,'disposition':disposition,'page_starts':page_starts,'finish_records':page_results,'regions':region,'capture_refs':sorted(x for x in caprefs if x),'scope_unknown_shard':shard if unknown_captures else None,'issues':bad})
 scope_unknown={str(shard):sorted(key for key in missing if shard in caps[key]['shards']) for shard in range(151)}
 scope_unknown={k:v for k,v in scope_unknown.items() if v};pinsets={}
 for meta in caps.values():
  pins=meta.pop('source_pins',None)
  if isinstance(pins,dict):
   key=digest(canon(pins));pinsets[key]=pins;meta['source_pins_sha256']=key
 return {'schema':'pip02-exposure-inventory/v2','plan_sha256':digest(raw),'roots':[str(x) for x in roots],'r25_root_absent':not R25.exists(),'captures':caps,'source_pin_sets':pinsets,'scope_unknown_by_shard':scope_unknown,'attempt_roots':[str(r) for r in attempt_roots],'captures_without_result':missing,'captures_without_verified_complete_result':missing,'counts':dict(collections.Counter(x['disposition'] for x in result)),'pages':result,'warning':'Snapshot only: hold native pool/shard locks and repeat inventory before any start; eligibility does not grant execution.'}
if __name__=='__main__':
 try:
  data=inventory();p=pathlib.Path(sys.argv[1]);p.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n');print(json.dumps({'counts':data['counts'],'captures_without_result':len(data['captures_without_result'])}))
 except Exception as e:print('REFUSED: '+repr(e),file=sys.stderr);raise
