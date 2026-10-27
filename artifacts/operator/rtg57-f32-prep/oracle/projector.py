#!/usr/bin/python3
"""Project the native model-free oracle record without inventing missing warrant."""
import hashlib,json,math,pathlib,re,sys
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(D.parent/'packet'))
from claim_tuple import ClaimTuple,grade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def project(p):
 p=pathlib.Path(p).resolve(); out=p.parent; r=json.loads(p.read_text()); saved=r.pop('content_sha256')
 if hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()!=saved: raise ValueError('receipt hash')
 if r['schema']!='epyc.rtg57.vkq_oracle.native.v1' or r['protocol_id'] is not None or r['n_positive']!=1 or r['n_negative']!=1: raise ValueError('scope')
 if r['rule_sha256']!=sha(D/'PREDECLARED.md'): raise ValueError('rule digest')
 for n,h in r['evidence_sha256'].items():
  if pathlib.PurePath(n).name!=n or (out/n).is_symlink() or sha(out/n)!=h: raise ValueError('evidence digest')
 for n in ('positive.log','mutation.log','positive.rc','mutation.rc','loaded-map.txt','environ.txt','compiled-knob.txt','linkage.txt'):
  if n not in r['evidence_sha256']: raise ValueError('missing proof')
 if (out/'positive.rc').read_text().strip()!='0' or (out/'mutation.rc').read_text().strip()!='1': raise ValueError('status')
 def line(n):
  m=re.search(r'^ORACLE_1ROW max_nmse=([^ ]+) tol=([^ ]+) finite=1 mutation=([01])$',(out/n).read_text(),re.M)
  if not m: raise ValueError('oracle line')
  return float(m[1]),float(m[2]),int(m[3])
 x,t,a=line('positive.log'); y,t2,b=line('mutation.log')
 if not (math.isfinite(x) and math.isfinite(y) and x==r['positive_n1_nmse'] and y==r['mutation_n1_nmse'] and t==t2==r['existing_nmse_threshold'] and x<=t<y and a==0 and b==1): raise ValueError('metric/control mismatch')
 if 'GGML_FA_VKQ_F32=1' not in (out/'environ.txt').read_text().splitlines() or 'GGML_FA_SPLIT_KV=0' not in (out/'environ.txt').read_text().splitlines(): raise ValueError('environment')
 if 'libggml-cpu.so.0.16.0' not in (out/'loaded-map.txt').read_text() or 'GGML_FA_VKQ_F32' not in (out/'compiled-knob.txt').read_text(): raise ValueError('kernel binding')
 tup=ClaimTuple(measurement_id='rtg57-vkq-oracle-'+saved[:16],metric='vkq_n1_oracle_nmse_max',value=x,date=r['completed_utc'],category='CANDIDATE',claim='C5 CPU F16-V D256 KV8192 causal N1 max NMSE against FP64, one model-free sample',metric_direction='lower_better',protocol_id='',reps=1,reps_basis='scored:1 model-free shape',unit='nmse',attestation_locator=str(p),attestation_sha256=sha(p),attestation_present=True,attestation_verified=True,source_kind='measurement',extra={'receipt_content_sha256':saved,'rule_sha256':r['rule_sha256'],'producer_script_hashes':'not recorded in original receipt'})
 return {'measurement_id':tup.measurement_id,'metric':tup.metric,'value':tup.value,'claim':tup.claim,'protocol_id':tup.protocol_id,'reps':tup.reps,'grade':grade(tup),'attestation_sha256':tup.attestation_sha256,'note':'No producer script hashes were present in the original native receipt.'}
if __name__=='__main__': print(json.dumps(project(sys.argv[1]),sort_keys=True,indent=2))
