#!/usr/bin/env python3
"""Read recorded native logs through the unchanged owned CPU op_correctness predicate."""
from pathlib import Path
import argparse,dataclasses,hashlib,json,subprocess,sys
from unittest.mock import patch
D=Path(__file__).resolve().parent
sys.path[:0]=[str(D/'owned-code'),str(D/'owned-code/scripts/kernel_rnd')]
from scripts.kernel_rnd.autokernel.loop import gates

def replay_native(op,row):
 raw=Path(row['raw_log']);data=raw.read_bytes()
 if hashlib.sha256(data).hexdigest()!=row['raw_sha256']:raise ValueError('native raw log changed')
 if not row.get('confirmed_dead') or row.get('gpu_maps_during') or row.get('image')!='/mnt/raid0/llm/kernels/builds/cpu-20261030-729599d69-c6':raise ValueError('wrong native identity/death/image')
 stderr=b''
 if row.get('stderr_log'):
  stderr=Path(row['stderr_log']).read_bytes()
  if hashlib.sha256(stderr).hexdigest()!=row['stderr_sha256']:raise ValueError('native stderr changed')
 done=subprocess.CompletedProcess([],row['native_rc'],data.decode(errors='replace'),stderr.decode(errors='replace'))
 # Replaying the native stdout is read-only; the original predicate itself remains unchanged.
 with patch.object(gates.subprocess,'run',return_value=done):verdict=gates.op_correctness(Path(row['image']),op=op,backend='CPU',require_reference=False)
 return dataclasses.asdict(verdict)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
 if a.smoke:
  root=D/'qualification';rows=json.loads((root/'native-records.json').read_text())['records'];selected=[r for r in rows if r['name']=='qualification-first-native-case']
  row=dict(selected[0]);row['raw_log']=str(root/'qualification-first-native-case.log');print(json.dumps(replay_native('MUL_MAT',row),default=str));return
 pointer=D/'CPU-OPS-LATEST.json'
 if not pointer.exists():print(json.dumps({'status':'NOT_STARTED','gate_pass':None}));return
 result=json.loads(pointer.read_text());run=Path(result['argv'][result['argv'].index('--out')+1])
 if result.get('source_sha')!='729599d69871181d67af715a4c2f9162d5153a2e' or result.get('action')!='cpu-ops':raise ValueError('wrong runtime source/action')
 if result['status']!='NATIVE_COMPLETE':print(json.dumps({'status':result['status'],'gate_pass':None,'run':str(run)}));return
 rows=json.loads((run/'native-records.json').read_text())['records'];verdicts={}
 for op in ['MUL_MAT','MUL_MAT_ID','FLASH_ATTN_EXT']:
  selected=[r for r in rows if r['name']=='C6-'+op]
  if len(selected)!=1:raise ValueError('missing/duplicate native op result '+op)
  verdicts[op]=replay_native(op,selected[0])
 print(json.dumps({'source_sha':result['source_sha'],'status':result['status'],'op_verdicts':verdicts,'rule':'unchanged owned gates.op_correctness CPU/default comparator; unsupported remains separate','full_G_AK_pass':None},default=str))
if __name__=='__main__':main()
