import unittest
from parse_trace import classify
S='slot launch_slot_: id 0 | task 42 | processing task, is_child = 0\n'
E='slot release: id 0 | task 42 | stop processing\n'
def step(n,a=1,t=42):return f'slot sample: id 0 | task {t} | accepted {a}/{n} draft tokens\n'
class TestTrace(unittest.TestCase):
 def test_pass(self):self.assertEqual(classify(S+step(1)+step(1)+E,1,2)['status'],'WITHIN_CAP')
 def test_over(self):self.assertEqual(classify(S+step(2)+E,1,2)['status'],'OVER_CAP')
 def test_missing(self):self.assertEqual(classify(S+E,1,0)['status'],'UNKNOWN')
 def test_incomplete(self):self.assertEqual(classify(S+step(1),1,1)['status'],'UNKNOWN')
 def test_bad_total(self):self.assertEqual(classify(S+step(1)+E,1,2)['status'],'UNKNOWN')
 def test_cross_task(self):self.assertEqual(classify(S+step(1,t=41)+E,1,1)['status'],'UNKNOWN')
 def test_native_padded_format(self):self.assertEqual(classify('slot launch_slot_: id  0 | task 42 | processing task\nslot operator(): id  0 | task 42 | accepted  0/ 7 draft tokens\nslot      release: id  0 | task 42 | stop processing\n',7,7)['status'],'WITHIN_CAP')
 def test_padded_over_cap(self):self.assertEqual(classify('slot launch_slot_: id  0 | task 42 | processing task\nslot operator(): id  0 | task 42 | accepted  0/ 7 draft tokens\nslot      release: id  0 | task 42 | stop processing\n',1,7)['status'],'OVER_CAP')
 def test_bad_accept(self):self.assertEqual(classify(S+step(1,2)+E,1,1)['status'],'UNKNOWN')
if __name__=='__main__':unittest.main()
