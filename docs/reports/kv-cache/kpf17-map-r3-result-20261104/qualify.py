#!/usr/bin/env python3
"""Exercise source-sealed KPF-17 custody.validate_maps on private fixture DSOs."""
import hashlib, importlib.util, json, os, secrets, tempfile, threading
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXPECTED_CUSTODY_SHA256='ab6d10e509d7483963a39b0da2caccab4ac8b85ee33a9e0b117107601d8d8702'
EXPECTED_BINDING_SHA256='5b56f806a39f24a2f68dafe147b5b56295a2975fea3914bca2a388e571b16b82'
ROW_ID='kvu-kpf17-map-revalidation-r3-20261104'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def load_custody():
 seal=json.loads((ROOT/'input_seal.json').read_text()); binding=json.loads((ROOT/'binding.json').read_text())
 source=ROOT/'custody.py'
 if seal.get('custody_source_sha256')!=EXPECTED_CUSTODY_SHA256 or sha(source)!=EXPECTED_CUSTODY_SHA256:raise ValueError('custody source seal mismatch')
 if seal.get('source_binding_sha256')!=EXPECTED_BINDING_SHA256 or sha(ROOT/'binding.json')!=EXPECTED_BINDING_SHA256:raise ValueError('binding seal mismatch')
 if binding.get('runner_files',{}).get('custody.py')!=EXPECTED_CUSTODY_SHA256:raise ValueError('binding does not pin custody source')
 spec=importlib.util.spec_from_file_location('kpf17_alt17_safe_custody',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m,seal
def fixture_maps(paths):
 lines=[];expected={}
 for i,p in enumerate(paths):
  p=Path(p).resolve(strict=True);st=p.stat();a=0x100000+i*0x1000
  lines.append(f'{a:x}-{a+0x1000:x} r-xp 00000000 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {p}')
  expected[str(p)]=sha(p)
 return lines,expected
def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp')
 tmp.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');os.replace(tmp,path)
def run():
 dryrun=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
 out=ROOT/'out';out.mkdir(parents=True,exist_ok=True)
 context_path=out/'attempt.json';full=out/'RESULT.json';ctx=None
 if not dryrun:
  attempt=os.environ.get('FILLER_ID')
  if attempt!=ROW_ID:raise ValueError('full run FILLER_ID does not match sealed row id')
  # Fresh start record first; an interrupted attempt cannot leave an older RESULT eligible.
  full.unlink(missing_ok=True);context_path.unlink(missing_ok=True)
  ctx={'schema':'kpf17.alt17-attempt.v1','state':'STARTED','row_id':ROW_ID,'attempt_id':attempt,
       'nonce':secrets.token_hex(24),'result_path':str(full),'input_seal_sha256':sha(ROOT/'input_seal.json'),
       'runner_sha256':sha(ROOT/'qualify.py')}
  atomic_json(context_path,ctx)
 custody,seal=load_custody()
 with tempfile.TemporaryDirectory(prefix='alt17-safe-fixture-',dir=ROOT) as td:
  fixture=Path(td);names=('libggml.so','libggml-base.so','libggml-cpu.so','libllama.so','libllama-common.so');paths=[]
  for name in names:
   p=fixture/name;p.write_bytes((b'private approved fixture '+name.encode()+b'\0')*128);paths.append(p)
  lines,expected=fixture_maps(paths);baseline=custody.validate_maps(lines,expected)
  if len(baseline)!=5:raise ValueError('sealed validator rejected complete baseline')
  checked=threading.Event();mutated=threading.Event();outcome={};target=paths[0]
  def revalidate():
   checked.set()
   if not mutated.wait(5):outcome['error']='mutation barrier timeout';return
   try:custody.validate_maps(lines,expected);outcome['result']='ACCEPTED'
   except ValueError as e:outcome.update(result='REFUSED',reason=str(e))
  def writer():
   if not checked.wait(5):outcome['error']='validation barrier timeout';return
   target.write_bytes(b'private mutated fixture\0'*128);mutated.set()
  a=threading.Thread(target=revalidate);b=threading.Thread(target=writer);a.start();b.start();a.join(6);b.join(6)
  if a.is_alive() or b.is_alive():raise RuntimeError('barrier worker did not terminate')
  if outcome.get('error'):raise RuntimeError(outcome['error'])
  if outcome.get('result')!='REFUSED' or 'unattested mapped library' not in outcome.get('reason',''):raise RuntimeError('sealed validator did not refuse mutation: '+repr(outcome))
 result={'schema':'kpf17.alt17-custody-race.v1','status':'PASS','sealed':True,'case_count':1,'unit_key':'case_count',
 'input_seal_sha256':sha(ROOT/'input_seal.json'),'custody_source_sha256':seal['custody_source_sha256'],
 'tested_function':'custody.validate_maps','baseline':'ACCEPTED_COMPLETE_FIVE_DSO_FIXTURE',
 'case':{'id':'same-uid-in-place-overwrite-between-map-captures','barrier':'PASS','revalidation':'REFUSED','reason':outcome['reason'],'fixture_scope':'private temporary directory'},
 'limitations':'Only post-write second-call detection is tested; no claim for mutation after final revalidation, build_identity, native loading, or full custody chain.'}
 if dryrun:
  result.update(result_kind='synthetic-smoke',attempt_id='smoke:'+ROW_ID)
  atomic_json(dryrun,result)
 else:
  result.update(result_kind='full',attempt_id=ctx['attempt_id'],attempt_nonce=ctx['nonce'],attempt_context_sha256=sha(context_path))
  atomic_json(full,result)
 print(json.dumps({'progress':'ALT17-QUALIFICATION-COMPLETE','case_count':1,'unit_key':'case_count','result_kind':'smoke' if dryrun else 'full'},sort_keys=True),flush=True)
if __name__=='__main__':run()
