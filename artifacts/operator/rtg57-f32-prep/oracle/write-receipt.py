import datetime, hashlib, json, pathlib, re, sys
D=pathlib.Path(__file__).resolve().parent; O=D/'out'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pos=(O/'positive.log').read_text(); neg=(O/'mutation.log').read_text()
def metric(s):
 m=re.search(r'^ORACLE_1ROW max_nmse=([^ ]+) tol=([^ ]+) finite=1 mutation=([01])$',s,re.M)
 if not m: raise ValueError('missing oracle line')
 return float(m[1]),float(m[2]),int(m[3])
a,t,ma=metric(pos); b,t2,mb=metric(neg)
if not (a <= t == t2 == 0.0005 and b > t and ma==0 and mb==1): raise ValueError('oracle or mutation conditions unmet')
files={p.name:sha(p) for p in sorted(O.iterdir()) if p.is_file()}
r={'schema':'epyc.rtg57.vkq_oracle.native.v1','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_id':None,'source_commit':'c72ec82f5417bb2937310326120f149b665e8400','rule_sha256':sha(D/'PREDECLARED.md'),'instrument_source_sha256':sha(D/'source/test-fa-rowexact.cpp'),'instrument_binary_sha256':sha(D/'test-fa-rowexact-c5'),'libggml_cpu_sha256':sha(pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin/libggml-cpu.so.0.16.0')),'case':{'type':'f16','head_dim':256,'kv':8192,'mask':'causal','threads':1,'split_kv':0,'vkq_f32':1},'positive_n1_nmse':a,'mutation_n1_nmse':b,'existing_nmse_threshold':t,'n_positive':1,'n_negative':1,'evidence_sha256':files}
r['content_sha256']=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
(O/'native-receipt.json').write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
print('native oracle receipt written')
