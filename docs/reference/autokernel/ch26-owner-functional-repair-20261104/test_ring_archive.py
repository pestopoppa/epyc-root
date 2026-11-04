import hashlib
import json
import pathlib
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent/'native'))
from ring_archive import MAX_RING_BYTES, RingArchive, verify


def frame(tail, data, size=64):
    ring=bytearray(size)
    for i,b in enumerate(data): ring[(tail+i)%size]=b
    return bytes(ring), tail+len(data), tail

class ArchiveTests(unittest.TestCase):
 def test_wrapped_window_and_empty_continuity(self):
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/'capture'
   a=RingArchive(path,max_bytes=20000)
   record=struct.pack('<IHH',9,0,16)+b'abcdefgh'
   ring,head,tail=frame(60,record)
   a.append(1,ring,head=head,tail=tail)
   a.append(1,bytes(64),head=head,tail=head)
   a.append(2,bytes(64),head=0,tail=0)
   receipt=a.finish(); self.assertEqual(verify(path,receipt,max_bytes=20000),receipt)
 def test_discontinuity_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   a=RingArchive(pathlib.Path(d)/'a',max_bytes=20000)
   a.append(1,bytes(64),head=0,tail=0)
   with self.assertRaises(ValueError): a.append(1,bytes(64),head=1,tail=1)
   a.abort()
 def test_explicit_loss_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   a=RingArchive(pathlib.Path(d)/'a',max_bytes=20000)
   record=struct.pack('<IHHQQ',2,0,24,3,1)
   ring,head,tail=frame(0,record)
   with self.assertRaises(ValueError): a.append(1,ring,head=head,tail=tail)
   a.abort()
 def test_quota_removes_partial_archive(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a';a=RingArchive(p,max_bytes=256)
   rec=struct.pack('<IHH',9,0,56)+bytes(48)
   ring,head,tail=frame(0,rec)
   with self.assertRaises(ValueError): a.append(1,ring,head=head,tail=tail)
   self.assertFalse(p.exists())
 def test_tamper_and_truncation_refuse(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a';a=RingArchive(p,max_bytes=20000)
   a.append(1,bytes(64),head=0,tail=0); receipt=a.finish(); original=p.read_bytes()
   p.write_bytes(original[:-1])
   with self.assertRaises(ValueError): verify(p,receipt,max_bytes=20000)
   doc=json.loads(original); doc['frame']['head']=1
   p.write_text(json.dumps(doc)+'\n')
   with self.assertRaises(ValueError): verify(p,receipt,max_bytes=20000)
 def test_malicious_ring_size_refuses_before_allocation(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a'
   f={'source':1,'size':MAX_RING_BYTES*2,'head':0,'tail':0,'data':'','previous':'0'*64}
   raw=json.dumps(f,sort_keys=True,separators=(',',':')).encode(); digest=hashlib.sha256(raw).hexdigest()
   line=json.dumps({'frame':f,'sha256':digest},sort_keys=True,separators=(',',':')).encode()+b'\n'
   p.write_bytes(line); receipt={'count':1,'bytes':len(line),'last_sha256':digest}
   with self.assertRaisesRegex(ValueError,'invalid ring size'): verify(p,receipt,max_bytes=20000)
 def test_symlink_and_replacement_refuse(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a';a=RingArchive(p,max_bytes=20000)
   a.append(1,bytes(64),head=0,tail=0);receipt=a.finish()
   link=pathlib.Path(d)/'link';link.symlink_to(p)
   with self.assertRaises(OSError): verify(link,receipt,max_bytes=20000)
   # Replace the path after open; fstat still addresses the original inode.
   from unittest.mock import patch
   real_lstat=__import__('os').lstat
   replacement=pathlib.Path(d)/'replacement';replacement.write_bytes(p.read_bytes())
   def swap(path):
    replacement.replace(p)
    return real_lstat(path)
   with patch('ring_archive.os.lstat',side_effect=swap):
    with self.assertRaisesRegex(ValueError,'identity mismatch'):verify(p,receipt,max_bytes=20000)
 def test_fifo_rejected_without_writer(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'fifo';os.mkfifo(p)
   with self.assertRaisesRegex(ValueError,'invalid archive file'): verify(p,{},max_bytes=20000)
 def test_mutation_during_replay_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'a';a=RingArchive(p,max_bytes=20000)
   a.append(1,bytes(64),head=0,tail=0);receipt=a.finish()
   import os
   from unittest.mock import patch
   real_fstat=os.fstat; calls=[]
   def mutate(fd):
    calls.append(fd)
    if len(calls)==2:
     with p.open('ab') as out:out.write(b'x')
    return real_fstat(fd)
   with patch('ring_archive.os.fstat',side_effect=mutate):
    with self.assertRaisesRegex(ValueError,'changed during replay'):verify(p,receipt,max_bytes=20000)
 def test_overrun_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   a=RingArchive(pathlib.Path(d)/'a',max_bytes=20000)
   with self.assertRaises(ValueError): a.append(1,bytes(64),head=65,tail=0)
   a.abort()
if __name__=='__main__':unittest.main()
