import importlib.util
import unittest
import socket
import os
from pathlib import Path
s=importlib.util.spec_from_file_location('runner',Path(__file__).resolve().parents[2]/'scripts/benchmark/copyspec_27b.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Test(unittest.TestCase):
 def test_port_belongs_to_child_fd(self):
  with socket.socket() as sock:
   sock.bind(('127.0.0.1',0));sock.listen()
   port=sock.getsockname()[1]
   self.assertTrue(m.owns_port(os.getpid(),port))
   self.assertFalse(m.owns_port(os.getpid(),0))
 def test_direction_and_weighted_acceptance(self):
  rs=[]
  for arm in m.ARMS:
   for i,(n,ms,d,a) in enumerate([(10,1000,10,5),(30,1000,30,0)]):
    r=m.counters({'timings':dict(predicted_n=n,predicted_ms=ms,draft_n=d,draft_n_accepted=a)},arm)
    rs.append(dict(arm=arm,id=str(i),content_sha256='x',**r))
  out=m.summarize(rs,2)
  self.assertEqual(out['NM8']['tps'],20)
  self.assertEqual(out['NM8']['acceptance'],.125)
  self.assertEqual(out['P2']['identity_vs_P'],2)
  self.assertEqual(out['NM8']['ratio_vs_P'],1)
  with self.assertRaises(ValueError):m.summarize(rs[:-1],2)
  with self.assertRaises(ValueError):m.summarize(rs[:-1]+[rs[0]],2)
 def test_missing_and_invalid_draft_counters_refuse(self):
  for tm in [dict(draft_n=True,draft_n_accepted=0),dict(draft_n=1),dict(draft_n=1,draft_n_accepted=2),{}]:
   with self.assertRaises(ValueError):m.counters({'timings':dict(predicted_n=10,predicted_ms=10,**tm)},'P')
  self.assertIsNone(m.counters({'timings':dict(predicted_n=10,predicted_ms=10)},'NO')['acceptance'])
unittest.main()
