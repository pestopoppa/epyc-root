"""Shared canonical model vocabulary computation; never loads tensors/server."""
import ast,hashlib,json,os,pathlib,signal,subprocess,time
D=pathlib.Path(__file__).resolve().parent
TOKENIZER=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu/llama-tokenize').resolve()
def run(out,recipe,capture,endnow,owned,alive,cutoff=False):
 assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest()==recipe['tokenizer_sha256'],'production tokenizer binary digest drift'
 env={k:v for k,v in os.environ.items() if not k.startswith(('GGML_','LLAMA_ARG_')) and k not in ['LD_PRELOAD','SHIM_NPROCS']};env.update(recipe['env']);env['OMP_NUM_THREADS']='1'
 model=pathlib.Path(recipe['argv'][recipe['argv'].index('-m')+1]);assert model.stat().st_size==recipe['model_edge_pin']['size'],'model size drift'
 edge=hashlib.sha256()
 with model.open('rb') as f:
  edge.update(f.read(64*1024**2));f.seek(-64*1024**2,2);edge.update(f.read())
 assert edge.hexdigest()==recipe['model_edge_pin']['sha256_first_last_64MiB'],'model edge pin drift'
 prompt='Reply with the numeral four only. What is two plus two?'
 cmd=[str(TOKENIZER),'-m',recipe['argv'][recipe['argv'].index('-m')+1],'-p',prompt,'--ids','--offline','--device','none','-ngl','0']
 with (out/'tokenizer.stdout').open('w') as stdout,(out/'tokenizer.stderr').open('w') as stderr:
  p=capture(subprocess.Popen(cmd,env=env,stdout=stdout,stderr=stderr));native_seen=False;cut=False;peak=0;maps='';native_ticks=0
  while p.poll() is None:
   try:
    maps=pathlib.Path(f'/proc/{p.pid}/maps').read_text()
    if str(TOKENIZER) in maps and 'libllama.so' in maps:
     native_seen=True;(out/'tokenizer-native-maps.txt').write_text(maps)
     stats=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split();native_ticks=int(stats[11])+int(stats[12])
    for line in pathlib.Path(f'/proc/{p.pid}/status').read_text().splitlines():
     if line.startswith('VmRSS:'):peak=max(peak,int(line.split()[1])*1024)
    if cutoff and native_seen and native_ticks>=10 and peak>=16*1024**2:
     cut=True;p.send_signal(signal.SIGTERM)
   except OSError:pass
   if endnow():p.terminate();cut=True
   if peak>8*1024**3:p.kill();raise RuntimeError('native preflight exceeds8GiB')
   time.sleep(.005)
  p.wait(timeout=3)
 record={'scope':'TOKENIZER_ONLY; full frontdoor and production API owner check UNTESTED','argv':cmd,'pid':p.pid,'birth':owned[p.pid],'native_seen':native_seen,'returncode':p.returncode,'peak_rss_bytes':peak,'tokenizer_sha256':hashlib.sha256(TOKENIZER.read_bytes()).hexdigest(),'first_model_request_ok':False,'cutoff':cut,'observed_native_cpu_ticks':native_ticks,'tensor_model_loaded':False}
 if cut:
  record['partial']=True;(out/'native-preflight.json').write_text(json.dumps(record,indent=2));return False
 assert p.returncode==0 and native_seen,'native tokenizer failed or residency not observed'
 assert 'libggml-hip.so' not in maps,'HIP backend appeared'
 tokens=ast.literal_eval((out/'tokenizer.stdout').read_text().strip());assert tokens and all(isinstance(x,int) for x in tokens)
 record.update(token_ids=tokens,token_count=len(tokens),partial=False,first_native_compute_ok=True)
 (out/'native-preflight.json').write_text(json.dumps(record,indent=2)+'\n');return True
