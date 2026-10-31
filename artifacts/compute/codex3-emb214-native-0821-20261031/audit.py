from pathlib import Path
import json,hashlib,math,sys
p=Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/emb214/run'); out=Path(sys.argv[1]);h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest(); rows=[]
for i in range(200):
 q=json.loads((p/f'{i:03}.pair.json').read_text()); vs=[];rec={'ordinal':i,'id':q['id'],'text_sha256':q['text_sha256'],'sample_sha256':q['sample_sha256']}
 for arm in ('v9','v10'):
  rp=p/f'{i:03}-{arm}.result.json';vp=p/f'{i:03}-{arm}.vector.json';ep=p/f'{i:03}-{arm}.exposure.json';r=json.loads(rp.read_text());e=json.loads(ep.read_text());v=json.loads(vp.read_text())
  assert h(rp)==q[f'{arm}_result_sha256'] and h(vp)==r['vector_file_sha256'] and h(ep)==r['exposure_sha256'] and r['rc']==0 and len(v)==1024 and e['ordinal']==i and e['text_sha256']==q['text_sha256'];rec[arm]={'result_sha256':h(rp),'vector_sha256':h(vp),'exposure_sha256':h(ep),'binary_sha256':e['binary_sha256']};vs.append(v)
 a,b=vs;c=math.fsum(x*y for x,y in zip(a,b))/math.sqrt(math.fsum(x*x for x in a)*math.fsum(y*y for y in b));assert abs(c-q['cosine'])<1e-12 and c>=.9999 and q['status']=='pass';rec['cosine']=c;rows.append(rec)
assert len({r['id'] for r in rows})==200
out.write_text(json.dumps({'schema':'emb214.independent_audit.v1','sample_sha256':rows[0]['sample_sha256'],'count':200,'threshold':.9999,'pass':200,'unknown':0,'min_cosine':min(r['cosine'] for r in rows),'max_cosine':max(r['cosine'] for r in rows),'rows':rows},indent=2)+'\n')
