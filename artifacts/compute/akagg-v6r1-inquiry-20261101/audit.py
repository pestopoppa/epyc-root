#!/usr/bin/env python3
"""Read master registry and model GGUF metadata only; no inference or model weights."""
import hashlib,importlib.util,json,pathlib,subprocess,yaml
orch=pathlib.Path('/workspace/repos/epyc-orchestrator'); reg=orch/'orchestration/model_registry.yaml'; probe=orch/'scripts/analysis/gguf_arch_probe.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('v6r1_probe',probe);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
doc=yaml.safe_load(reg.read_text());root=pathlib.Path(doc['runtime_defaults']['model_base_path']);roles=doc.get('roles',{});out={}; cache={}
for role,rec in roles.items():
 m=rec.get('model',{}); raw=m.get('path'); row={'declared_name':m.get('name'),'declared_architecture':m.get('architecture'),'declared_path':raw}
 if not isinstance(raw,str) or not raw: row['header_status']='no_path';out[role]=row;continue
 path=pathlib.Path(raw); path=path if path.is_absolute() else root/path
 row['resolved_path']=str(path)
 if str(path) not in cache:
  try:
   st=path.stat();v=mod.probe(str(path));cache[str(path)]={'status':'ok','architecture':v['architecture'],'general_name':v['name'],'size_bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
  except (OSError,ValueError,EOFError,OverflowError) as e:cache[str(path)]={'status':'unavailable','error':f'{type(e).__name__}: {e}'}
 row['header']=cache[str(path)];out[role]=row
heads=subprocess.run(['git','-C',str(orch),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
dirty=subprocess.run(['git','-C',str(orch),'status','--porcelain','--',str(reg.relative_to(orch))],capture_output=True,text=True,check=True).stdout.strip()
record={'schema':'epyc.akagg.v6r1.registry-inquiry.v1','registry_path':str(reg),'registry_sha256':sha(reg),'orchestrator_checkout_head':heads,'registry_tracked_dirty':bool(dirty),'probe_path':str(probe),'probe_sha256':sha(probe),'field_examined':'roles.*.model','role_count':len(roles),'unique_header_paths':len(cache),'roles':out,'limitations':['Registry role entries and readable local GGUF headers only; inaccessible paths are unknown.','No claim that other sources, future models, or prospective imports are unsuitable.','Header file stat does not establish full model-byte digest; no model load or inference.']}
p=pathlib.Path(__file__).with_name('RESULT.json');p.write_text(json.dumps(record,indent=2)+'\n');print('receipt',sha(p));print('roles',len(roles),'headers',len(cache),'statuses',[(k,v.get('architecture'),v['status']) for k,v in cache.items()])
