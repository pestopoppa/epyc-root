import importlib.util,json,sys,tempfile,pathlib,hashlib
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet')
spec=importlib.util.spec_from_file_location('monitor',D/'monitor.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
good='| qwen4exp | Meta | MoE | OK (0.0e+00) | SKIP |\n'
assert m.validate(0,good,2)['meta_moe_nmse']=='OK'
for rc,text,n in [(1,good,2),(0,good,1),(0,good.replace('OK','FAIL'),2),(0,good+good,2),(0,good.replace('SKIP','OK'),2),(0,good.replace('MoE','Dense'),2)]:
 try: m.validate(rc,text,n)
 except ValueError: pass
 else: raise AssertionError((rc,text,n))
with tempfile.TemporaryDirectory(dir=D) as t:
 t=Path(t); dev=t/'0000:ca:00.0';dev.mkdir();drm=t/'drm';drm.mkdir();c=drm/'card2';c.mkdir();(c/'device').symlink_to(dev); topo=t/'nodes';topo.mkdir();n=topo/'1';n.mkdir();(n/'properties').write_text('domain 0\nlocation_id 51712\n');(n/'gpu_id').write_text('81\n')
 assert m.identity('0000:ca:00.0',drm,topo)==(c,81)
 n2=topo/'2';n2.mkdir();(n2/'properties').write_text((n/'properties').read_text());(n2/'gpu_id').write_text('82')
 try: m.identity('0000:ca:00.0',drm,topo)
 except ValueError: pass
 else: raise AssertionError('ambiguous KFD accepted')
 sys.path.insert(0,'/mnt/raid0/llm/worktrees/meta-gpu-arch-ready/scripts/vidya')
 from adapters import speech_ggml_optest as a
 r=t/'results.json'
 for name in ('stdout','stderr','linkage.log'): (t/name).write_text('synthetic only')
 (t/'residency.jsonl').write_text(''.join(json.dumps({'pid':1,'start_ticks':'42','time_ns':2,'kfd_gpu_id':2,'pid_in_kfd':True,'vram_bytes':5})+'\n' for _ in range(2)))
 raw={name:hashlib.sha256((t/name).read_bytes()).hexdigest() for name in ('stdout','stderr','linkage.log','residency.jsonl')}
 r.write_text(json.dumps({'schema':'epyc.model_free_backend_correctness.v1','source_commit':'520ad4f55d805a544862be88d652ec68fcd194ab','source_seal_sha256':'b'*64,'binding_sha256':'c'*64,'pid':1,'start_ticks':'42','start_ns':1,'end_ns':3,'kfd_gpu_id':2,'reaped':True,'gates':{'fixture_process_rc':0,'meta_moe_nmse':'OK','positive_device_samples':2},'raw_sha256':raw})+'\n')
 f={'backend':'ROCm0','device_arch':'gfx90a','op':'qwen4exp-meta-moe-nmse','binary_sha256':'a'*64,'source_seal_sha256':'b'*64,'binding_sha256':'c'*64,'residency_proof':'synthetic fixture','positive_device_samples':2,'suite_case_count':1,'n_failed':0,'tree':{'commit':'520ad4f55d805a544862be88d652ec68fcd194ab'}}
 p=m.emit_native(a,t,f); rows=a.native_rows(p); assert len(rows)==1
 claim=a.project(rows[0]); assert claim.value==0 and claim.protocol_id=='' and claim.attestation_present
 (t/'residency.jsonl').write_text('tampered')
 try: a.project(rows[0])
 except Exception: pass
 else: raise AssertionError('tampered residency accepted')
 data=json.loads(p.read_text());data['value']=1;p.write_text(json.dumps(data)+'\n');assert not a.native_rows(p)
print('CONTROLS_PASS: parser refusal, unique KFD, native carrier projection and tamper')
