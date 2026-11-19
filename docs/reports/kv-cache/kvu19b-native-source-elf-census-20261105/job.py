#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
ID='kvu19b-native-source-elf-census-20261105'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def result_path():
 smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
 if smoke:
  p=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']); root=Path(os.environ['FILLER_DRYRUN_DIR']).resolve()
  if not p.is_absolute() or p.is_symlink() or root not in p.resolve().parents: raise ValueError('unsafe smoke path')
  return p
 if os.environ.get('FILLER_DRYRUN_RESULT_PATH'): raise ValueError('unexpected smoke path')
 return D/'out/RESULT.json'
def main():
 p=result_path();p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists(): raise RuntimeError('refuse overwrite')
 files=json.loads((D/'provenance.json').read_text())['files']; inputs=[]; issues=[]
 for x in files:
  f=Path(x['path'])
  try:
   h=digest(f); inputs.append({'path':str(f),'sha256':h,'expected_sha256':x['sha256'],'url':x['url'],'match':h==x['sha256']})
   if h!=x['sha256']:issues.append('source hash mismatch: '+str(f))
  except OSError as e: issues.append('missing source: '+str(f))
 elfs=[Path('/mnt/raid0/llm/tmp/kvfork/kpf50-clock-qual-r6-20261104/profiler/lib/rocprofiler/librocprof-tool.so'),Path('/mnt/raid0/llm/tmp/kvfork/kpf50-clock-qual-r6-20261104/profiler/lib/librocprofiler64.so.1.0.60200')]
 tool_seals=[]
 for t in ('/usr/bin/nm','/usr/bin/strings','/usr/bin/readelf'):
  try: tool_seals.append({'path':t,'sha256':digest(Path(t))})
  except OSError: issues.append('tool missing: '+t)
 evidence=[]
 for i,f in enumerate(elfs):
  try:
   h=digest(f); entry={'path':str(f),'realpath':str(f.resolve(strict=True)),'sha256_before':h}
   for name,args in [('symbols',['/usr/bin/nm','-D','-C',str(f)]),('strings',['/usr/bin/strings','-a',str(f)]),('elf',['/usr/bin/readelf','-n',str(f)])]:
    cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,check=True)
    out=p.parent/f'elf-{i}-{name}.txt';out.write_bytes(cp.stdout);entry[name]={'path':out.name,'sha256':digest(out)}
   entry['sha256_after']=digest(f)
   if entry['sha256_after']!=h: issues.append('ELF changed: '+str(f))
   evidence.append(entry)
  except (OSError,subprocess.SubprocessError) as e:issues.append('ELF or tool unavailable: '+str(f)+' '+str(e))
 citations=[{'file':'src/util/hsa_rsrc_factory.cpp','lines':'413-420','subject':'agent dev_index assigned HSA driver node ID'}, {'file':'src/core/intercept_queue.h','lines':'192-208','subject':'dev_index passed to dispatch callback'}, {'file':'src/tools/tool.cpp','subject':'candidate tool source, serializer not established'}]
 result={'schema':'kvu19b.source-elf-census.v1','row_id':ID,'status':'CENSUS_COMPLETE' if not issues else 'UNKNOWN','issues':issues,'sources':inputs,'elfs':evidence,'tool_seals':tool_seals,'candidate_source_citations':citations,'serializer_source':'UNKNOWN','binary_source_equivalence':'UNKNOWN','profiler_gpu_id_to_bdf':'UNKNOWN','model':None,'gpu_work':False,'scope':'CPU-only byte inventory; no source/binary equivalence or device mapping claim'}
 p.write_text(json.dumps(result,indent=2)+'\n');return 0
if __name__=='__main__': sys.exit(main())
