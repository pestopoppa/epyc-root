#!/usr/bin/env python3
"""One item per command; no implicit stage transition or successor scheduling."""
import argparse,datetime,fcntl,hashlib,json,subprocess,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--state',required=True,type=Path);sp=p.add_subparsers(dest='cmd',required=True)
i=sp.add_parser('init');i.add_argument('--manifest',required=True,type=Path);i.add_argument('--binding',required=True,type=Path);i.add_argument('--parity-manifest',required=True,type=Path);i.add_argument('--review',required=True,type=Path)
a=sp.add_parser('advance');a.add_argument('--decision',required=True,type=Path)
r=sp.add_parser('run');r.add_argument('--item',required=True);r.add_argument('--length',type=int,required=True);r.add_argument('--arm',required=True);r.add_argument('--repeat',type=int,default=1)
a=p.parse_args()
a.state.parent.mkdir(parents=True,exist_ok=True)
lock_file=Path(str(a.state.resolve())+'.lock').open('a')
try:fcntl.flock(lock_file,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit('controller state is locked by another invocation')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(s):
 tmp=a.state.with_suffix('.tmp');tmp.write_text(json.dumps(s,sort_keys=True,indent=2)+'\n');tmp.replace(a.state)
def now():return time.time()
if a.cmd=='init':
 if a.state.exists():raise SystemExit('state already exists')
 review=json.loads(a.review.read_text()); declaration=sha(P/'DECLARATION.md')
 if review.get('reviewed') is not True or review.get('declaration_sha256')!=declaration or review.get('manifest_sha256')!=sha(a.manifest) or review.get('parity_manifest_sha256')!=sha(a.parity_manifest) or review.get('binding_sha256')!=sha(a.binding):raise SystemExit('review must bind exact declaration, manifest and binding hashes')
 s={'schema':'lsa-staged-controller-v1','stage':'parity','status':'paused','manifest':str(a.manifest.resolve()),'manifest_sha256':sha(a.manifest),'parity_manifest':str(a.parity_manifest.resolve()),'parity_manifest_sha256':sha(a.parity_manifest),'binding':str(a.binding.resolve()),'binding_sha256':sha(a.binding),'declaration_sha256':declaration,'review_sha256':sha(a.review),'stage_started':None,'records':[],'decisions':[],'selected_item':None,'selected_length':None}
 a.state.parent.mkdir(parents=True,exist_ok=True);write(s);print('initialized paused');sys.exit()
s=json.loads(a.state.read_text());
for record in s['records']:
 try:valid=bool(record.get('sha256')) and sha(record['path'])==record['sha256']
 except (OSError,KeyError,TypeError):valid=False
 if not valid:raise SystemExit('record missing or digest mismatch; stop and preserve evidence')
if any((sha(s['manifest'])!=s['manifest_sha256'],sha(s['parity_manifest'])!=s['parity_manifest_sha256'],sha(s['binding'])!=s['binding_sha256'],sha(P/'DECLARATION.md')!=s['declaration_sha256'])):raise SystemExit('reviewed bytes changed')
limits={'parity':3600,'dev':43200,'timing':43200,'heldout':86400}
if s['status']=='stopped':raise SystemExit('controller permanently stopped')
if s.get('pending_unit'):raise SystemExit('interrupted unit has no sealed result; stop and preserve evidence')
if s['stage_started'] is not None and now()-s['stage_started']>limits[s['stage']]:s['status']='stopped';write(s);raise SystemExit('stage wall-clock cap exhausted')
if a.cmd=='advance':
 d=json.loads(a.decision.read_text());
 if s['records'] and s['records'][-1]['runner_rc']!=0 and d.get('decision') not in ('stop','inconclusive'):raise SystemExit('unsealed/failed runner record blocks continuation')
 if d.get('stage')!=s['stage'] or d.get('decision') not in ('continue','next_stage','stop','inconclusive'):raise SystemExit('decision stage/outcome invalid')
 # Decision must bind every existing record digest; cannot overlook a failure or invalid.
 if d.get('records_sha256')!=[x['sha256'] for x in s['records']]:raise SystemExit('decision does not bind current complete record sequence')
 if d.get('timing_extended'):
  pairrows=[x for x in s['records'] if x['stage']=='timing' and x['key'][4] in (1,2,3)]
  if s['stage']!='timing' or any(sum(x['key'][3]==arm for x in pairrows)!=3 for arm in ('dense',s.get('selected_arm'))) or not d.get('direction_unresolved'):raise SystemExit('timing extension needs three matched pairs and unresolved direction')
 s['decisions'].append({'path':str(a.decision.resolve()),'sha256':sha(a.decision),'outcome':d['decision'],'timing_extended':bool(d.get('timing_extended'))})
 if d['decision'] in ('stop','inconclusive'):s['status']='stopped'
 elif d['decision']=='next_stage':
  stages=['parity','dev','timing','heldout'];j=stages.index(s['stage'])
  if j==3:raise SystemExit('no stage after heldout')
  if not d.get('basis'):raise SystemExit('stage transition needs explicit basis')
  if s['stage']=='parity':
   if not d.get('all_keys_parity_pass'):raise SystemExit('all-keys parity decision required')
   pair=[x for x in s['records'] if x['stage']=='parity']
   if pair and (len(pair)!=2 or any(json.loads(Path(x['path']).read_text())['status']!='pass' for x in pair)):raise SystemExit('if retrieval check is run, both parity outputs must pass')
   proof=json.loads(Path(d.get('parity_artifact','/nonexistent')).read_text())
   pm=json.loads(Path(s['parity_manifest']).read_text());binding=json.loads(Path(s['binding']).read_text())
   if proof.get('compared_logits')!=proof.get('vocabulary_size') or not proof.get('vocabulary_size') or proof.get('tolerance')!=0.00001 or proof.get('max_abs_logit_error',float('inf'))>0.00001 or proof.get('all_logits_finite') is not True or proof.get('argmax_equal') is not True or proof.get('model_sha256')!=pm['model_sha256'] or proof.get('input_token_ids_sha256')!=pm['rows'][0]['token_ids_sha256'] or proof.get('source_commit')!=binding.get('source_commit') or proof.get('candidate_patch_sha256')!=binding.get('candidate_patch_sha256') or not proof.get('logits_dumper_sha256') or not proof.get('raw_logits_sha256'):
    raise SystemExit('complete-vocabulary native logits parity missing, mismatched or outside tolerance')
   s['decisions'][-1]['parity_artifact_sha256']=sha(d['parity_artifact'])
  if s['stage']=='dev':
   dev=[x for x in s['records'] if x['stage']=='dev' and x['length']==d.get('selected_length')]
   if any(sum(x['key'][3]==arm for x in dev)<4 for arm in ('dense','pca','distilled','window')):raise SystemExit('selected length needs all four groups in each development arm')
   if any(json.loads(Path(x['path']).read_text())['status'] in ('invalid','timeout') for x in dev):raise SystemExit('invalid development cells cannot establish a useful candidate')
   if not d.get('useful_candidate') or not d.get('selected_item') or d.get('selected_length') not in (8192,32768,131072,262144):raise SystemExit('dev decision must select useful candidate/item/length')
   s.update(selected_item=d['selected_item'],selected_length=d['selected_length'],selected_arm=d.get('selected_arm'))
   if s['selected_arm'] not in ('pca','distilled'):raise SystemExit('candidate arm required')
  if s['stage']=='timing':
   pairs=[x for x in s['records'] if x['stage']=='timing']
   need=5 if d.get('speed_claim') else 3
   if any(sum(x['key'][3]==arm for x in pairs)<need for arm in ('dense',s['selected_arm'])):raise SystemExit('insufficient paired timing repetitions')
   if not d.get('quality_candidate_selected'):raise SystemExit('heldout requires quality candidate decision')
  s['stage']=stages[j+1];s['stage_started']=None;s['status']='paused'
 else:s['status']='ready'
 write(s);print(s['status'],s['stage']);sys.exit()
if s['status']!='ready':raise SystemExit('paused: record a decision before each unit')
active_manifest=s['parity_manifest'] if s['stage']=='parity' else s['manifest'];m=json.loads(Path(active_manifest).read_text());row=next((x for x in m['rows'] if x['id']==a.item and x['nominal']==a.length),None)
if row is None:raise SystemExit('unknown item')
stage=s['stage'];arms={'parity':('dense','all_keys'),'dev':('dense','pca','distilled','window'),'timing':('dense',s.get('selected_arm')),'heldout':('dense',s.get('selected_arm'))}
if a.arm not in arms[stage]:raise SystemExit('arm not permitted for stage')
if stage in ('parity','dev') and row['split']!='dev' or stage=='heldout' and row['split']!='heldout':raise SystemExit('split is not permitted')
if stage=='parity' and (a.length!=m['rows'][0]['nominal'] or a.item!=m['rows'][0]['id']):raise SystemExit('parity is one fixed short item')
if stage=='parity' and a.arm=='all_keys':
 dense=[x for x in s['records'] if x['stage']=='parity' and x['key'][3]=='dense']
 if len(dense)!=1 or json.loads(Path(dense[0]['path']).read_text())['status']!='pass':raise SystemExit('dense baseline did not answer; stop and repair development prompt, no LSA conclusion')
if stage=='dev':
 allowed={next(x['id'] for x in m['rows'] if x['split']=='dev' and x['group']==g) for g in ('code','multihop','document_qa','agent_history')}
 if a.item not in allowed:raise SystemExit('outside fixed four-item development subset')
 sentinel=next(x['id'] for x in m['rows'] if x['split']=='dev' and x['group']=='document_qa')
 if a.item==sentinel and a.length==8192 and a.arm!='dense':
  baseline=[x for x in s['records'] if x['stage']=='dev' and x['length']==8192 and x['key'][1]==sentinel and x['key'][3]=='dense']
  if len(baseline)!=1 or json.loads(Path(baseline[0]['path']).read_text())['status']!='pass':raise SystemExit('dense retrieval baseline failed or missing: stop and repair dev prompt; no LSA conclusion')
 if a.item!=sentinel:
  first=[x for x in s['records'] if x['stage']=='dev' and x['length']==8192 and x['key'][1]==sentinel]
  if {x['key'][3] for x in first}!={'dense','pca','distilled','window'}:raise SystemExit('initial 8192 document sentinel requires all arms before expansion')
 lengths={x['length'] for x in s['records'] if x['stage']=='dev'}|{a.length}
 if len(lengths)>2 or (not lengths-{a.length} and a.length!=8192):raise SystemExit('development starts at 8192 and caps at two lengths')
if stage=='timing' and not json.loads(Path(s['binding']).read_text()).get('later_timing_window_id'):raise SystemExit('later reserved timing window identity required')
if stage=='timing' and (a.item!=s['selected_item'] or a.length!=s['selected_length'] or not 1<=a.repeat<=7):raise SystemExit('timing must use selected item/length, max 7 repetitions')
if stage=='heldout' and (a.length!=s['selected_length'] or a.repeat!=1):raise SystemExit('heldout once at selected length')
if stage!='timing' and a.repeat!=1:raise SystemExit('quality items cannot repeat')
key=(stage,a.item,a.length,a.arm,a.repeat)
if any(tuple(x['key'])==key for x in s['records']):raise SystemExit('duplicate unit')
if stage=='timing' and a.repeat>1:
 prior=[x for x in s['records'] if x['stage']=='timing' and x['key'][4]==a.repeat-1]
 if {x['key'][3] for x in prior}!={'dense',s['selected_arm']}:raise SystemExit('complete the preceding matched pair before the next')
if stage=='timing' and a.repeat>3 and not any(x['outcome']=='continue' for x in s['decisions'] if x.get('timing_extended')):raise SystemExit('extension after repeat 3 requires a declared unresolved timing look')
out=a.state.parent/'records'/('-'.join(map(str,key))+'.json');out.parent.mkdir(exist_ok=True)
if out.exists():raise SystemExit('unit output already exists; stop and preserve evidence')
cmd=[sys.executable,str(P/'runner_v2.py'),'--manifest',active_manifest,'--binding',s['binding'],'--id',a.item,'--length',str(a.length),'--arm',a.arm,'--phase','timing' if stage=='timing' else 'quality','--repeat',str(a.repeat),'--output',str(out)]
s['status']='paused';s['pending_unit']=key
if s['stage_started'] is None:s['stage_started']=now()
write(s) # crash or interruption never launches another unit
r=subprocess.run(cmd);s['records'].append({'key':key,'stage':stage,'length':a.length,'path':str(out),'sha256':sha(out) if out.exists() else None,'runner_rc':r.returncode});s['pending_unit']=None;write(s);print('paused after unit; inspect record before next decision')
