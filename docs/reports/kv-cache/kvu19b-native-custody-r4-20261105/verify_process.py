import copy,json,re,sys
from pathlib import Path

def verify(log,obs,exe):
 m=re.search(r'^IDENTITY pid=(\d+) birth=(\d+) bdf=([0-9a-fA-F:.]+) device=(\d+)$',log,re.M)
 if not m or len(obs)!=2: raise ValueError('identity or observations missing')
 pid,birth=int(m[1]),int(m[2])
 for o in obs:
  if o['pid']!=pid or o['birth']!=birth or o['exe']!=str(exe.resolve()): raise ValueError('live process identity mismatch')
 if not 0<obs[0]['observed_monotonic_ns']<obs[1]['observed_monotonic_ns']: raise ValueError('observation ordering')
 w=re.search(r'^WITNESS 0 (\d+) (\d+)$',log,re.M)
 if not w or obs[-1]['observed_monotonic_ns']>=int(w[1]): raise ValueError('observation must precede first witness')

def main(d):
 log=(d/'witness.log').read_text(); obs=json.loads((d/'process_observations.json').read_text()); exe=d/'clock';verify(log,obs,exe)
 cases={'pid':lambda o:o[0].update(pid=o[0]['pid']+1),'birth':lambda o:o[0].update(birth=o[0]['birth']+1),'exe':lambda o:o[0].update(exe='/wrong'),'missing':lambda o:o.pop(),'order':lambda o:o[1].update(observed_monotonic_ns=o[0]['observed_monotonic_ns'])}
 for name,mut in cases.items():
  x=copy.deepcopy(obs);mut(x)
  try:verify(log,x,exe)
  except (ValueError,KeyError,TypeError):continue
  raise ValueError('mutation accepted: '+name)
 (d/'process_verification.json').write_text(json.dumps({'status':'PASS','mutations':list(cases),'gpu_id_to_bdf':'UNKNOWN'},indent=2)+'\n')
if __name__=='__main__':main(Path(sys.argv[1]))
