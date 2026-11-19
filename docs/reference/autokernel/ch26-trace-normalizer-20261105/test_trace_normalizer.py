import struct
import unittest
from trace_normalizer import parse_format, decode_sample, check_continuity

FORMAT='''name: sched_switch
ID: 42
format:
 field:unsigned short common_type; offset:0; size:2; signed:0;
 field:unsigned char common_flags; offset:2; size:1; signed:0;
 field:int prev_pid; offset:4; size:4; signed:1;
 field:int next_pid; offset:8; size:4; signed:1;
'''

def sample(*, cpu=1, event=71, trace=42, t=100, prev=7, nxt=8):
 raw=struct.pack('<HBBii',trace,0,0,prev,nxt)
 return struct.pack('<QQIIQIIQI',event,71,7,7,t,cpu,0,1,len(raw))+raw

class Check(unittest.TestCase):
 def setUp(self):self.fields=parse_format(FORMAT,42)
 def test_decode(self):
  e=decode_sample(sample(),cpu=1,event_id=71,tracepoint_id=42,fields=self.fields)
  self.assertEqual((e['prev_tid'],e['next_tid'],e['timestamp_ns']),(7,8,100))
 def test_source_mismatch(self):
  for kwargs in ({'cpu':2,'event_id':71,'tracepoint_id':42},{'cpu':1,'event_id':72,'tracepoint_id':42},{'cpu':1,'event_id':71,'tracepoint_id':43}):
   with self.assertRaises(ValueError):decode_sample(sample(),fields=self.fields,**kwargs)
 def test_truncation(self):
  with self.assertRaises(ValueError):decode_sample(sample()[:-1],cpu=1,event_id=71,tracepoint_id=42,fields=self.fields)
 def test_format_mismatch(self):
  for f in (FORMAT.replace('ID: 42','ID: 43'),FORMAT.replace('next_pid; offset:8','next_pid; offset:4'),FORMAT.replace('next_pid; offset:8; size:4; signed:1','next_pid; offset:8; size:8; signed:1')):
   with self.assertRaises(ValueError):parse_format(f,42)
 def test_bracket(self):
  rows=[{'cpu':1,'timestamp_ns':90,'prev_tid':1,'next_tid':2},{'cpu':1,'timestamp_ns':110,'prev_tid':2,'next_tid':3},{'cpu':1,'timestamp_ns':130,'prev_tid':3,'next_tid':1}]
  out=check_continuity(rows,cpus={1},begin_ns=100,end_ns=120)
  self.assertEqual(out['coverage'],'unknown');self.assertEqual(out['measurement_admission'],'none')
  for changed in ([rows[0],{**rows[1],'prev_tid':9},rows[2]], rows[1:],rows[:2],[rows[1],rows[0],rows[2]]):
   with self.assertRaises(ValueError):check_continuity(changed,cpus={1},begin_ns=100,end_ns=120)
 def test_missing_cpu(self):
  with self.assertRaises(ValueError):check_continuity([],cpus={0},begin_ns=1,end_ns=2)
if __name__=='__main__':unittest.main()
