#!/usr/bin/env python3
"""CS22.T1 event-to-clip accounting. This does not select a latency match or claim a verdict."""
import argparse,collections,json,math,pathlib,statistics

def evaluate(clips,events,candidates):
 byclip=collections.defaultdict(list)
 expected={c['candidate_id']:c['clip_id'] for c in candidates}
 if len(expected)!=len(candidates) or any(cid not in clips for cid in expected.values()):raise ValueError('invalid candidate manifest')
 if any(e.get('candidate_id') not in expected or expected[e['candidate_id']]!=e.get('clip_id') for e in events):raise ValueError('event outside candidate manifest')
 observed_results=len(events)
 present={e['candidate_id'] for e in events}
 events=events+[{'candidate_id':cid,'clip_id':clip,'status':'missing'} for cid,clip in expected.items() if cid not in present]
 for e in events:
  if e['clip_id'] not in clips:raise ValueError('unknown clip')
  if not isinstance(e['candidate_id'],str) or not e['candidate_id']:raise ValueError('missing candidate identity')
  byclip[e['clip_id']].append(e)
 if len({e['candidate_id'] for e in events})!=len(events):raise ValueError('duplicate candidate identity')
 out=[]
 for cid,c in clips.items():
  rows=byclip[cid];label=c['label'];gold=c['gold'];bad=[];fires=[];latencies=[]
  for e in rows:
   answer=e.get('answer');pause=e.get('pause_audio_s');delta=e.get('pause_to_decision_s');raw=e.get('result_sha256')
   if e.get('status')!='ok' or answer not in ('finished','unfinished','wait') or not isinstance(pause,(int,float)) or not math.isfinite(pause) or not isinstance(delta,(int,float)) or not math.isfinite(delta) or not raw:
    bad.append(e['candidate_id']);continue
   latencies.append(delta)
   if answer=='finished':fires.append(pause+delta)
  # Every missing/malformed candidate is wrong, including negatives; a clip
  # with zero enumerated candidates has no fire, preserving original scope.
  if bad:
   status='missing_wrong';wrong=True
  elif label=='complete':
   g=gold.get('eot_gold_s')
   if not isinstance(g,(int,float)):raise ValueError('missing EOT gold')
   premature=[x for x in fires if x<g];hits=[x for x in fires if x>=g]
   status='premature' if premature else 'hit' if hits else 'miss';wrong=status!='hit'
  else:
   status='false_cut' if fires else 'ok';wrong=bool(fires)
  eot=gold.get('eot_gold_s');hit_latency=min(x for x in fires if x>=eot)-eot if status=='hit' and eot is not None else None
  out.append({'clip_id':cid,'label':label,'status':status,'wrong':wrong,'candidate_count':len(rows),'malformed_or_missing_ids':bad,'fires_audio_s':fires,'signed_pause_to_decision_s':latencies,'end_of_speech_to_fire_s':hit_latency})
 def ratio(label,fn):
  seq=[x for x in out if fn(x['label'])];return {'n':len(seq),'n_matching':sum(label(x) for x in seq),'value':sum(label(x) for x in seq)/len(seq) if seq else None}
 metrics={'eot_recall':ratio(lambda x:x['status']=='hit',lambda x:x=='complete'),'eot_fpr':ratio(lambda x:x['status'] in ('false_cut','missing_wrong'),lambda x:x=='incomplete'),'int_fpr':ratio(lambda x:x['status'] in ('false_cut','missing_wrong'),lambda x:x=='backchannel')}
 vals=[x['end_of_speech_to_fire_s'] for x in out if x['end_of_speech_to_fire_s'] is not None];metrics['end_of_speech_to_fire_median_s']=statistics.median(vals) if vals else None
 return {'items':out,'metrics':metrics,'expected_clips':len(clips),'expected_candidates':len(candidates),'observed_results':observed_results,'missing_results':len(candidates)-observed_results,'matched_latency_baseline':'UNRESOLVED','paired_interval':'UNCOMPUTED','verdict':'UNCOMPUTED'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--clips',required=True);p.add_argument('--events',required=True);p.add_argument('--candidates',required=True);p.add_argument('--split',choices=['selection','confirmation'],required=True);p.add_argument('--frozen-selection');p.add_argument('--out',required=True);a=p.parse_args()
 if a.split=='confirmation':
  if not a.frozen_selection:raise SystemExit('confirmation requires the original task selection freeze')
  f=json.loads(pathlib.Path(a.frozen_selection).read_text())
  if f.get('state')!='selection_frozen' or not f.get('prompt_sha256') or not f.get('model_sha256') or not f.get('baseline_config'):raise SystemExit('selection freeze incomplete')
 clips={x['clip_id']:x for x in map(json.loads,pathlib.Path(a.clips).read_text().splitlines()) if x['split']==a.split};events=list(map(json.loads,pathlib.Path(a.events).read_text().splitlines()));candidates=list(map(json.loads,pathlib.Path(a.candidates).read_text().splitlines()));r=evaluate(clips,events,candidates);r['split']=a.split;pathlib.Path(a.out).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
