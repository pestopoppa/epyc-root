#!/usr/bin/env python3
import hashlib,json,pathlib,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r3')
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def check(tag):
 out=D/tag; r=json.loads((out/'RESULT.json').read_text()); pins_path=pathlib.Path('/mnt/raid0/llm/tmp/lb49-r11-source-draft-20261028/pins.json'); pins=json.loads(pins_path.read_text()); smoke=tag!='full'
 assert sha(pins_path)=='6c4e01faedc0ccf2f34db2829917261a4f3e2736be28809c73e65ef3a27fd02a'==r['pins_sha256']
 assert r['partial'] is False and r['diagnostic_only'] is True and r['full_target_tested'] is (not smoke)
 modelset=[pins['smoke_model']] if smoke else pins['models']; assert r['models_verified']==[{'path':x['path'],'sha256':x['sha256'],'size':x['size']} for x in modelset]
 assert len(r['arms'])==3
 for arm,(name,build,extra) in zip(r['arms'],[('baseline-1','off',[]),('baseline-2','off',[]),('candidate','feature',['--cpu-iqk-fa','on'])]):
  bindir=pathlib.Path('/mnt/raid0/llm/tmp/lb49-codex-evidence-20261028')/('build-deterministic-'+build)/'bin'; exe=bindir/'llama-cli'; log=out/(name+'.log'); n='2' if smoke else '24'
  assert arm['arm']==name and arm['rc']==0 and arm['log']==str(log) and arm['sha256']==sha(log)
  assert sha(exe)==pins['files'][str(exe)]['sha256'] and sha(bindir/'libggml-cpu.so')==pins['files'][str(bindir/'libggml-cpu.so')]['sha256']
  assert arm['argv']==[str(exe),'-m',modelset[0]['path'],'--device','none','-ngl','0','-fa','on','--perf','-t',n,'-tb',n,'-c','512','-n','8','--temp','0','--seed','42','--single-turn','--no-display-prompt','-p','The capital of France is']+extra
  text=log.read_bytes();assert b'Generation:' in text and b'Exiting...' in text
  assert (out/(name+'-linkage.log')).is_file()
 return True
if __name__=='__main__':
 try: check(sys.argv[1]);print('FU03 completion verified',sys.argv[1])
 except Exception as e: print('FU03 completion refused:',type(e).__name__,e,file=sys.stderr);sys.exit(1)
