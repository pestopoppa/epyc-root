#!/usr/bin/python3
"""Small GGUF control of the candidate bench and writer; not a target load."""
import hashlib,json,os,pathlib,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
out=pathlib.Path(os.environ['RTG57_OUT']);out.mkdir(parents=True,exist_ok=True)
model=pathlib.Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q4_0.gguf')
if hashlib.sha256(model.read_bytes()).hexdigest()!='444406ddd926550c724ec18d5120a9d40ded44908a063b0e66e9a7e5464c652c': raise SystemExit('control model changed')
b=pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin')
env=dict(os.environ,LD_LIBRARY_PATH=str(b),OMP_NUM_THREADS='1',GGML_IQK='1',GGML_FUSED_DECODE_OFF='1',GGML_FA_SPLIT_KV='0')
cmd=[str(b/'llama-bench'),'-m',str(model),'-t','2','-fa','1','-mmp','1','-p','8','-n',('2048' if os.environ.get('RTG57_STOP_CONTROL')=='1' else '32'),'-r','10','-o','jsonl','--progress']
with (out/'control.jsonl').open('w') as stdout,(out/'control.err').open('w') as stderr:
 p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env,start_new_session=True)
 (out/'STARTED.json').write_text(json.dumps({'pid':p.pid,'model':str(model),'target_tested':False})+'\n')
 if os.environ.get('RTG57_STOP_CONTROL')=='1':
  deadline=time.monotonic()+120
  while time.monotonic()<deadline and p.poll() is None:
   if 'benchmark 1/' in (out/'control.err').read_text(errors='replace'):
    (D/'STOP').touch(); break
   time.sleep(.05)
  else: raise RuntimeError('control did not enter real compute')
 rc=p.wait()
if rc: raise SystemExit(rc)
rows=[json.loads(x) for x in (out/'control.jsonl').read_text().splitlines() if x.startswith('{')]
if not rows or not any(x.get('n_gen',0)>0 and x.get('avg_ts',0)>0 for x in rows): raise SystemExit('no real decode')
(out/'CONTROL.json').write_text(json.dumps({'real_compute':True,'result_writer_ok':True,'target_load_tested':False,'rows':len(rows)})+'\n')
