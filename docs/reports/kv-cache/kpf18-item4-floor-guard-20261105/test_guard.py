import unittest
from unittest.mock import patch
import guard

class Tests(unittest.TestCase):
    def setUp(self):
        b=lambda slot,task:{'slot':slot,'task':task,'response':{'http':200,'timings':{'id_slot':slot,'id_task':task}}}
        self.kw=dict(src=b(0,10),decoders=[b(1,11),b(2,12)],target=b(3,13),prefix=8)
        self.rows=[[0,10,8,0,'prefill'],[1,11,7,1,'decode'],[2,12,7,1,'decode'],[3,13,8,0,'prefill']]
    def run_guard(self,rows):
        with patch.object(guard.layout,'witness',return_value={'rows':rows}):
            return guard.guard(b'',**self.kw)
    def test_mixed(self): self.assertEqual(self.run_guard(self.rows)['rows'],self.rows)
    def test_wrong_source(self):
        rows=[r[:] for r in self.rows]; rows[0][1]=99
        with self.assertRaises(guard.Refused):self.run_guard(rows)
    def test_missing_decoder(self):
        with self.assertRaises(guard.Refused):self.run_guard(self.rows[:2]+self.rows[3:])
    def test_extra_task(self):
        with self.assertRaises(guard.Refused):self.run_guard(self.rows+[[1,99,4,0,'prefill']])
    def test_duplicate_binding(self):
        self.kw['target']['task']=10
        with self.assertRaises(guard.Refused):self.run_guard(self.rows)
    def test_missing_http_binding(self):
        del self.kw['target']['response']['timings']['id_task']
        with self.assertRaises(guard.Refused):self.run_guard(self.rows)
    def test_geometry_refusal(self):
        with patch.object(guard.layout,'compare',return_value={'verdict':'INVALID'}):
            with self.assertRaises(guard.Refused):guard.compare({'cells':[]}, {'cells':[]})
    def test_foreign_ownership_swap(self):
        with patch.object(guard.layout,'compare',return_value={'verdict':'MATCHED'}):
            with self.assertRaises(guard.Refused):guard.compare({'cells':[[1,0,1]]}, {'cells':[[1,0,2]]})
if __name__=='__main__':unittest.main()
