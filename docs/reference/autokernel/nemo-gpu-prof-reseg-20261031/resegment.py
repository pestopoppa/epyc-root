#!/usr/bin/env python3
"""Source-specific graph fingerprint attribution of the retained 2026-10-25 L/B traces."""
import csv, hashlib, json, statistics
from collections import Counter
from pathlib import Path
BASE=Path('/mnt/raid0/llm/epyc-inference-research/data/nemo-gpu-prof/retained-raw-20261025')
OUT=Path(__file__).resolve().parent/'resegmentation.json'
EXPECTED_CSV={'L':'c1bebdff0cfb35e98df39ba3fb729f9114b0f676cf3bf6ef4ba76ce267d8ca94','B':'4bfb3cdd73c7ff8cda2c8bab783ee9bbd21f46d19fec540b6add518a25e000ad'}
EXPECTED={'L':{2065:'4070ef32141057d213c0439f8b09b7a736641d52941c13cd752418e17df2f6cc',2081:'d5d9ff850d2e69462cee89ce4547df4ca4165e515977ffc611406bf412a184a7'},'B':{1845:'ea8c887a6af65a262c2fd93c9047fa67c4ded6264fd31e4536f086f241f891a8'}}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def load(p):
 out=[]
 with p.open(newline='') as f:
  for r in csv.DictReader(f):
   if r['Kind']=='KERNEL_DISPATCH' and not r['Kernel_Name'].startswith('__amd_rocclr'):
    s,e=int(r['Start_Timestamp']),int(r['End_Timestamp']);assert e>=s
    out.append((s,e,r['Kernel_Name']))
 return sorted(out)
def bursts(rows):
 result=[];group=[];end=None
 for r in rows:
  if end is not None and r[0]-end>2_000_000_000:result.append(group);group=[]
  group.append(r);end=max(end or 0,r[1])
 if group:result.append(group)
 return result
def fingerprint(g):return hashlib.sha256('\n'.join(n for _,_,n in g).encode()).hexdigest()
def stat(v):return {'n':len(v),'mean_ms':round(statistics.mean(v),4),'median_ms':round(statistics.median(v),4),'min_ms':round(min(v),4),'max_ms':round(max(v),4)}
def metrics(g):return sum(e-s for s,e,_ in g)/1e6,(max(e for s,e,_ in g)-min(s for s,e,_ in g))/1e6
def calc(p):
 rd=BASE/f'pass-{p}';run=json.loads((rd/'run.json').read_text());csvp=rd/'trace/prof_kernel_trace.csv'
 assert sha(csvp)==EXPECTED_CSV[p]
 assert run['status']=='complete' and run['teardown']['verified_dead'] and run['vram']['nonzero_samples']>=5
 assert all(x['graphs']=='ON' for x in run['proofs'])
 bs=bursts(load(csvp)); b=bs[-1];names=[n for _,_,n in b]
 if p=='L':
  assert len(bs)==5 and len(b)==332946
  mark=next(x for x in run['marks'] if x['label']=='P');assert mark['predicted_n']==160
  starts=[i for i in range(len(names)-4) if names[i].startswith('void k_set_rows<float, long, __half>') and names[i+1].startswith('void rms_norm_f32<1024') and names[i+2].startswith('void k_get_rows_float') and names[i+3].startswith('quantize_q8_1_1d')]
  assert len(starts)==159 and starts[0]==2601 and starts[-1]==330864
  spans=[b[x:y] for x,y in zip(starts,starts[1:])]+[b[starts[-1]:]]
  kept=[g for g in spans if len(g) in EXPECTED[p] and fingerprint(g)==EXPECTED[p][len(g)]]
  assert len(kept)==156 and Counter(len(g) for g in kept)=={2065:55,2081:101}
  excluded=[{'position':i,'dispatches':len(g),'fingerprint':fingerprint(g),'busy_ms':round(metrics(g)[0],4)} for i,g in enumerate(spans) if g not in kept]
  assert len(excluded)==3 and [x['dispatches'] for x in excluded]==[2250,2257,2082]
  prefill=b[:starts[0]]
  expected_graphs=160
 else:
  assert len(bs)==2 and len(b)==179633
  mark=next(x for x in run['marks'] if x['label']=='M');assert mark['predicted_n']==96
  scans=[i for i,n in enumerate(names) if 'ssm_scan_f32_group' in n];assert len(scans)==3880
  starts=[scans[q*40]-8 for q in range(2,97)]
  assert len(starts)==95 and starts[0]==4342 and starts[-1]==177788
  spans=[b[x:y] for x,y in zip(starts,starts[1:])]+[b[starts[-1]:]]
  kept=[g for g in spans if len(g)==1845 and fingerprint(g)==EXPECTED[p][1845]]
  assert len(kept)==94
  excluded=[{'position':i,'dispatches':len(g),'fingerprint':fingerprint(g),'busy_ms':round(metrics(g)[0],4)} for i,g in enumerate(spans) if g not in kept]
  assert len(excluded)==1 and excluded[0]['dispatches']==1861
  prefill=b[:starts[0]]
  expected_graphs=97
 busy=[metrics(g)[0] for g in kept];elapsed=[metrics(g)[1] for g in kept]
 wall=1000/mark['predicted_per_second']
 assert len(kept)+len(excluded)+(1 if p=='L' else 2)==expected_graphs
 return {'status':'COMPLETE','source_csv_sha256':EXPECTED_CSV[p],'source_run_sha256':sha(rd/'run.json'),'source_burst_dispatches':len(b),'server_predicted_n':mark['predicted_n'],'server_wall_ms_per_generated_token':round(wall,4),'boundary_method':'repeated ordered full kernel-name graph fingerprint anchored by k_set_rows/rms_norm/k_get_rows (L) or 40 SSM scans per graph (B)','fingerprints_by_dispatch_count':EXPECTED[p],'complete_steady_graphs':len(kept),'steady_dispatch_counts':dict(Counter(len(g) for g in kept)),'gpu_kernel_busy_ms_per_token':stat(busy),'gpu_elapsed_span_ms_per_token':stat(elapsed),'busy_to_server_wall_ratio':round(statistics.mean(busy)/wall,4),'excluded_graphs':excluded,'prefill_and_early_dispatches':len(prefill),'accounting':'GPU kernel busy sums each dispatch End-Start; elapsed graph span and server wall are separate, with host idle and overlap. Results are observed sample descriptive statistics, not a throughput claim or causal hardware counter.'}
def main():
 result={'schema':'nemo-gpu-prof.reseg.v1','source':'2026-10-25 retained rocprofv3 traces, HIP graphs ON','passes':{p:calc(p) for p in 'LB'}}
 OUT.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({p:{'n':result['passes'][p]['complete_steady_graphs'],'busy_ms':result['passes'][p]['gpu_kernel_busy_ms_per_token'],'span_ms':result['passes'][p]['gpu_elapsed_span_ms_per_token'],'wall_ms':result['passes'][p]['server_wall_ms_per_generated_token']} for p in 'LB'},indent=2))
if __name__=='__main__':main()
