import hashlib,json,os,pathlib,shutil,subprocess,time
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-ultra-torch-reference-v2');P='96,97'
base=[ 'sudo','-n','chroot','/proc/1/root','setpriv','--reuid=1000','--regid=1000','--groups=992','taskset','-c',P,'env','FILLER_CPUS='+P]
def call(name,*env):
 p=subprocess.run(base+list(env)+[str(D/'launch.sh'),'--smoke'],capture_output=True,text=True);(D/(name+'.log')).write_text(p.stdout+p.stderr);return p.returncode
orig=D/'smoke-final';case=next(p for p in orig.iterdir() if p.is_dir() and (p/'q8.result.json').exists())
before={str(p.relative_to(orig)):hashlib.sha256(p.read_bytes()).hexdigest() for p in orig.glob('*/*.result.json')};old=(case/'q8.comparison.txt').stat().st_mtime_ns
rc=call('fixture-resume');after={str(p.relative_to(orig)):hashlib.sha256(p.read_bytes()).hexdigest() for p in orig.glob('*/*.result.json')};assert rc==0 and before==after and (case/'q8.comparison.txt').stat().st_mtime_ns>old
bad=D/'smoke-tamper';shutil.copytree(orig,bad);target=bad/case.name/'f32/encoder.f32'
with target.open('r+b') as f:b=f.read(1);f.seek(0);f.write(bytes([b[0]^1]))
rc=call('fixture-tamper','CS8_SMOKE_DIR=smoke-tamper');assert rc==2 and json.loads((bad/'TERMINAL.json').read_text())['counts']['fault']>=1
result_bad=D/'smoke-result-tamper';shutil.copytree(orig,result_bad);result_file=result_bad/case.name/'torch.result.json';value=json.loads(result_file.read_text());value['rc']=7;result_file.write_text(json.dumps(value,sort_keys=True)+'\n');rc=call('fixture-result-tamper','CS8_SMOKE_DIR=smoke-result-tamper');assert rc==2 and json.loads((result_bad/'TERMINAL.json').read_text())['counts']['fault']>=1
limit=D/'smoke-admission';shutil.copytree(orig,limit);c=limit/case.name
for n in ('q8.exposure.json','q8.result.json','q8.seal.json','q8-run.stdout','q8-run.stderr','q8.comparison.txt','verdict.json'):(c/n).unlink(missing_ok=True)
shutil.rmtree(c/'q8');rc=call('fixture-admission','CS8_SMOKE_DIR=smoke-admission','CS8_DEADLINE='+str(time.time()+200));assert rc==75 and not (c/'q8.exposure.json').exists() and (c/'torch.result.json').exists() and (c/'f32.result.json').exists()
print(json.dumps({'resume_rc':0,'tamper_rc':2,'result_tamper_rc':2,'admission_rc':75,'completed_arm_results_unchanged':before==after,'comparison_reexecuted':True,'unexposed_q8_remains_unexposed':True}))
