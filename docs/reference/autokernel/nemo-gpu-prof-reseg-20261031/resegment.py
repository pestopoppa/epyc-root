#!/usr/bin/env python3
"""Re-segment retained 2026-10-25 L/B traces inside server-timed decode requests."""
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

 # The request marks and rocprof timestamps use the same monotonic clock. Use the
 # measured server request interval as the decode window, then divide its total
 # device busy time by the server-reported generated-token count. This avoids
 # assigning a token boundary from a kernel-name fingerprint. The timing log is
 # an independent token-count / wall-time check for the same measured request.
 window_rows=[]
 with csvp.open(newline='') as f:
  for r in csv.DictReader(f):
   if r['Kind']!='KERNEL_DISPATCH' or r['Kernel_Name'].startswith('__amd_rocclr'):
    continue
   s,e=int(r['Start_Timestamp']),int(r['End_Timestamp'])
   if s>=mark['start_monotonic_ns'] and e<=mark['end_monotonic_ns']:
    window_rows.append((s,e,r['Kernel_Name']))
 assert window_rows, f'{p}: no kernels in server request timing window'
 request_busy_ns=sum(e-s for s,e,_ in window_rows)
 request_tokens=mark['predicted_n']
 request_busy_ms_per_token=request_busy_ns/1e6/request_tokens
 request_span_ms=(max(e for _,e,_ in window_rows)-min(s for s,_,_ in window_rows))/1e6
 assert request_tokens == (160 if p=='L' else 96)
 assert 0 < request_busy_ms_per_token < wall
 server_log=(rd/'server.log').read_text(errors='replace')
 timing_rows=[line for line in server_log.splitlines() if 'slot print_timing:' in line and 'eval time =' in line]
 assert timing_rows, f'{p}: server eval timing absent'
 timing_row=timing_rows[-1]
 import re
 match=re.search(r'eval time =\s*([0-9.]+) ms /\s*(\d+) tokens \(\s*([0-9.]+) ms per token,\s*([0-9.]+) tokens per second\)',timing_row)
 assert match, f'{p}: cannot parse final server eval timing: {timing_row}'
 server_eval_ms,server_tokens,server_ms_per_token,server_tps=map(float,match.groups())
 assert int(server_tokens)==request_tokens
 assert abs(server_ms_per_token-wall) <= 0.02*wall
 assert abs(1000/server_tps-wall) <= 0.02*wall
 return {'status':'COMPLETE','source_csv_sha256':EXPECTED_CSV[p],'source_run_sha256':sha(rd/'run.json'),'source_server_log_sha256':sha(rd/'server.log'),'server_request_mark':{'label':mark['label'],'start_monotonic_ns':mark['start_monotonic_ns'],'end_monotonic_ns':mark['end_monotonic_ns'],'generated_tokens':request_tokens,'request_window_kernel_dispatches':len(window_rows),'request_window_first_kernel_ns':min(s for s,_,_ in window_rows),'request_window_last_kernel_ns':max(e for _,e,_ in window_rows),'request_window_kernel_busy_ms':round(request_busy_ns/1e6,4),'request_window_kernel_span_ms':round(request_span_ms,4),'gpu_kernel_busy_ms_per_generated_token':round(request_busy_ms_per_token,4)},'server_eval_timing':{'eval_ms':server_eval_ms,'generated_tokens':int(server_tokens),'wall_ms_per_generated_token':round(server_ms_per_token,4),'tokens_per_second':server_tps},'busy_to_server_wall_ratio':round(request_busy_ms_per_token/wall,4),'boundary_method':'The run.json server timing mark bounds one measured request in the same monotonic clock as rocprof Start_Timestamp/End_Timestamp. All complete GPU kernel dispatches inside that interval are summed and divided by the server-reported generated-token count. The final server eval-time row independently confirms the token count and wall ms/token. No per-token kernel boundary is inferred from kernel-name fingerprints.','prior_fingerprint_crosscheck':{'fingerprint_steady_graphs':len(kept),'fingerprint_busy_ms_per_token':stat(busy),'fingerprint_span_ms_per_token':stat(elapsed),'excluded_graphs':excluded,'note':'Fingerprint groups are retained only as a secondary cross-check; the server-marked interval is the primary measurement.'},'accounting':'GPU kernel busy is summed End_Timestamp - Start_Timestamp divided by server-reported generated tokens. Request-window busy and per-token wall are distinct observables; their ratio is descriptive and does not assign host/GPU idle or overlap causes.'}
def main():
 result={'schema':'nemo-gpu-prof.reseg.v1','source':'2026-10-25 retained rocprofv3 traces, HIP graphs ON','passes':{p:calc(p) for p in 'LB'}}
 OUT.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({p:{'n':result['passes'][p]['server_request_mark']['generated_tokens'],'busy_ms':result['passes'][p]['server_request_mark']['gpu_kernel_busy_ms_per_generated_token'],'span_ms':result['passes'][p]['server_request_mark']['request_window_kernel_span_ms'],'wall_ms':result['passes'][p]['server_eval_timing']['wall_ms_per_generated_token']} for p in 'LB'},indent=2))
if __name__=='__main__':main()
