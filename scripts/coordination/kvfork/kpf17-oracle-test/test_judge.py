import unittest
from gdb_job import judge

def witness():
    return {'error':None,'entries':[{'mode':0},{'mode':8}],
            'samples':[{'mode':n,'point':p} for n in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')]}

def log():
    return '\n'.join(f'Test 6 mutation n_rs_seq={n} mechanism=detected_stale_logits_above_aa_floor\nTest 6 PASS n_rs_seq={n} restored=0 A/A=0 source=0 source_A/A=0 mutation=detected' for n in (0,8))

class JudgeTests(unittest.TestCase):
    def test_complete_test_and_both_in_test_mappings(self):
        self.assertEqual(judge(log(),witness(),0)['status'],'PASS')
    def test_missing_mapping_or_control_is_invalid(self):
        w=witness();w['samples'].pop();self.assertEqual(judge(log(),w,0)['status'],'INVALID')
        self.assertEqual(judge(log().replace('detected_stale_logits_above_aa_floor','invalid_valid_restore',1),witness(),0)['status'],'INVALID')
    def test_skip_failure_and_duplicate_are_invalid(self):
        for text,rc in ((log()+'\nTest 6 SKIP',0),(log(),1),(log()+'\nTest 6 mutation n_rs_seq=0 mechanism=detected_stale_logits_above_aa_floor',0)):
            self.assertEqual(judge(text,witness(),rc)['status'],'INVALID')

if __name__=='__main__':unittest.main()
