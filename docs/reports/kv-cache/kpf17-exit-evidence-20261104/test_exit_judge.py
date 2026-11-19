import unittest
from unittest.mock import patch
from gdb_job import judge

def log():
 return '\n'.join(f'Test 6 mutation n_rs_seq={n} mechanism=detected_stale_logits_above_aa_floor\nTest 6 PASS n_rs_seq={n} restored=0 A/A=0 source=0 source_A/A=0 mutation=detected' for n in (0,8))
def witness():
 return {'error':None,'entries':[{'mode':0},{'mode':8}],'samples':[{'mode':n,'point':p} for n in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')], 'debug_events':[{'kind':'exit','inferior_num':1,'exit_code':0}],'continue_return':{'inferior_num':1,'pid':0,'live':False}}
class ExitJudgement(unittest.TestCase):
 @patch('runtime_witness.validate',return_value=True)
 def test_requires_real_zero_exit(self,_):
  w=witness();self.assertEqual(judge(log(),w,0,{}, {})['status'],'PASS')
  for patcher in (lambda w:w.update(debug_events=[]),lambda w:w['debug_events'][0].update(exit_code=None),lambda w:w['debug_events'][0].update(exit_code=1),lambda w:w['continue_return'].update(live=True,pid=4),lambda w:w['continue_return'].update(inferior_num=2)):
   x=witness();patcher(x);self.assertEqual(judge(log(),x,0,{}, {})['status'],'INVALID')
if __name__=='__main__':unittest.main()
