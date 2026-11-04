import unittest
import control

class Stub:
 def __init__(self):self.calls=[]
 def erase_all(self):self.calls.append(('erase',))
 def vram_sample(self):return 1024
 def request(self,role,ids,slot,fork,n,cell,ckpt=None):
  self.calls.append((role,len(ids),slot,fork,n,ckpt))
  hit=1984 if role.endswith('seed3') or cell.endswith('-B') else 2048
  return {'role':role,'response':{'timings':{'n_fork_tokens':hit if fork else 0,'fork_src_slot':3 if cell.endswith('-A') and not role.endswith('seed3') else 0,'cache_n':hit}},'witness':{}}
class Tests(unittest.TestCase):
 def test_a_native_steps(self):
  s=Stub();cell={'trunk_ids':list(range(2048)),'suffix_ids':[8,9],'fork_tokens':2048,'group':3,'suffix_tokens':2}
  control.Runner.trial(s,cell,'A',1,'fork')
  self.assertEqual([(x[1],x[2],x[3],x[4]) for x in s.calls[1:]],[(1984,0,False,0),(2048,3,True,0),(2050,1,True,64)])
 def test_b_control_partition(self):
  s=Stub();cell={'trunk_ids':list(range(2048)),'suffix_ids':[8],'fork_tokens':1984,'group':3,'suffix_tokens':1}
  control.Runner.trial(s,cell,'B',1,'control')
  self.assertEqual([(x[1],x[2],x[3],x[4]) for x in s.calls[1:]],[(1984,2,False,0),(2049,2,False,64)])
 def test_bad_repeat_rejected(self):self.assertEqual(control.judge([])['verdict'],'INVALID')
 def test_judges_matched_and_layout_mismatch(self):
  def result(role,slot):
   return {'role':role,'response':{'tokens':[1]*64,'probs':[{'top_logprobs':[{'id':1,'logprob':-.1},{'id':2,'logprob':-1.0}]}]*64},'witness':{'capacity':8,'used':2,'nseq':1,'tokens':1,'prefix':2,'mapping':[(0,0),(1,1)],'head':2,'slot':slot,'cells':[[0,0,1<<slot],[1,1,1<<slot]],'rows':[[slot,42,2,1,'prefill']]}}
  runs=[result('fork1',1),result('fork2',1),result('control1',2),result('control2',2),result('control3',2)]
  self.assertEqual(control.judge(runs)['verdict'],'PROSPECTIVE_ONLY')
  runs[0]['witness']['mapping'][1]=(1,3)
  self.assertEqual(control.judge(runs)['verdict'],'INVALID_LAYOUT')
 def test_nonfinite_fork_logprob_rejected(self):
  runs=self.numeric_runs()
  runs[0]['response']['probs'][0]['top_logprobs'][0]['logprob']=float('nan')
  self.assertEqual(control.judge(runs)['verdict'],'INVALID')
 def test_nonfinite_each_arm_rank_and_position_rejected(self):
  for run in range(5):
   for position in (0,63):
    for rank in (0,1):
     for value in (float('nan'),float('inf'),float('-inf')):
      with self.subTest(run=run,position=position,rank=rank,value=value):
       runs=self.numeric_runs()
       runs[run]['response']['probs'][position]['top_logprobs'][rank]['logprob']=value
       self.assertEqual(control.judge(runs)['verdict'],'INVALID')
 def test_late_mixed_units_and_missing_rank_rejected(self):
  for item in ({'id':2,'prob':.2},{'id':2,'logprob':None},{'id':float('inf'),'logprob':-1.}, {'id':1,'logprob':-1.}):
   runs=self.numeric_runs()
   runs[0]['response']['probs'][63]['top_logprobs'][1]=item
   self.assertEqual(control.judge(runs)['verdict'],'INVALID')
  runs=self.numeric_runs()
  runs[4]['response']['probs'][63]['top_logprobs'].pop()
  self.assertEqual(control.judge(runs)['verdict'],'INVALID')
 def test_second_rank_floor_controls_divergence_verdict(self):
  runs=self.numeric_runs()
  for run in runs[:2]:run['response']['tokens'][0]=2
  # Baseline margin .9; control second-rank movement 1.0 must prevent
  # residual classification, although chosen-token values never move.
  runs[3]['response']['probs'][63]['top_logprobs'][1]['logprob']=-2.
  result=control.judge(runs)
  self.assertEqual(result['aa_floor'],1.)
  self.assertEqual([r['verdict'] for r in result['results']],['UNDETERMINED_NEAR_TIE']*2)
  runs[3]['response']['probs'][63]['top_logprobs'][1]['logprob']=-1.
  self.assertEqual([r['verdict'] for r in control.judge(runs)['results']],['RESIDUAL']*2)
 def test_second_rank_aa_floor(self):
  runs=self.numeric_runs()
  runs[3]['response']['probs'][0]['top_logprobs'][1]['logprob']=-1.5
  self.assertAlmostEqual(control.judge(runs)['aa_floor'],.5)
 def test_unstable_control_identity_rejected(self):
  runs=self.numeric_runs()
  runs[3]['response']['probs'][0]['top_logprobs'][1]['id']=3
  self.assertEqual(control.judge(runs)['verdict'],'INVALID')
 @staticmethod
 def numeric_runs():
  import copy
  def result(role,slot):
   return {'role':role,'response':{'tokens':[1]*64,'probs':[{'top_logprobs':[{'id':1,'logprob':-.1},{'id':2,'logprob':-1.0}]} for _ in range(64)]},'witness':{'capacity':8,'used':2,'nseq':1,'tokens':1,'prefix':2,'mapping':[(0,0),(1,1)],'head':2,'slot':slot,'cells':[[0,0,1<<slot],[1,1,1<<slot]],'rows':[[slot,42,2,1,'prefill']]}}
  return [result('fork1',1),result('fork2',1),result('control1',2),result('control2',2),result('control3',2)]
 def test_real_prompt_set_integrity(self):
  import hashlib,json
  data=json.loads((control.D/'exact-inputs.json').read_text())
  self.assertEqual(len(data['cells']),5)
  for c in data['cells']:
   payload=json.dumps(c['trunk_ids']+c['suffix_ids'],sort_keys=True,separators=(',',':'),default=str).encode()
   self.assertEqual(hashlib.sha256(payload).hexdigest(),c['prompt_sha256'])
if __name__=='__main__':unittest.main()
