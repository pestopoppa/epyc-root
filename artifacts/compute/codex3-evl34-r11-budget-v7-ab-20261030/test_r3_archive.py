import json,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import archive_control as a

class ArchiveTests(unittest.TestCase):
 def test_members_tamper_refusal_and_floor_safe_resume(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d)/'ram';root.mkdir();(root/'x').write_bytes(b'alpha');(root/'link').symlink_to('x');before=a.snapshot(root);archive=Path(d)/'control.tar.gz'
   with tarfile.open(archive,'w:gz',dereference=False) as t:t.add(root,arcname='control')
   a.verify_archive(archive,before)
   bad={**before,'x':{**before['x'],'sha256':'0'*64}}
   with self.assertRaisesRegex(RuntimeError,'bytes mismatch'):a.verify_archive(archive,bad)
   out=Path(d)/'copy';need=a.FLOOR+a.RECEIPT_RESERVE+archive.stat().st_size
   with self.assertRaises(a.Pause):a.copy_admitted(archive,out,free=lambda _:need-1)
   self.assertFalse(out.exists());partial=archive.read_bytes()[:12];out.write_bytes(partial)
   a.copy_admitted(archive,out,free=lambda _:need+1);self.assertEqual(a.sha(archive),a.sha(out))
   out.write_bytes(b'bad')
   with self.assertRaisesRegex(RuntimeError,'prefix mismatch'):a.copy_admitted(archive,out,free=lambda _:need+1)
 def test_qualification_requires_writer_drain_and_gpu(self):
  with tempfile.TemporaryDirectory(dir='/dev/shm') as d:
   root=Path(d);attempt=root/'campaign-control-1';attempt.mkdir()
   (root/'campaign-supervisor.json').write_text(json.dumps({'rc':0,'drained':True,'reason':None}))
   result={'failure':None,'partial':False,'server_drained':True,'statuses':{'21/a':'complete','21/b':'complete'},'wire_capture':{'first_tools':['delegate','wait'],'tool_choice':None}}
   (attempt/'result.json').write_text(json.dumps(result));gpu={'kind':'fast-kfd-residency','hip_mapped':True,'gpu_own_pid_vram_bytes':1};(attempt/'gpu-witness.jsonl').write_text(json.dumps(gpu)+'\n'+json.dumps(gpu)+'\n')
   self.assertTrue(a.qualify(root)[-1]);result['statuses']['21/b']='unknown';(attempt/'result.json').write_text(json.dumps(result));self.assertFalse(a.qualify(root)[-1])
   (root/'campaign-supervisor.json').write_text(json.dumps({'rc':1,'drained':False,'reason':None}))
   with self.assertRaisesRegex(RuntimeError,'drain'):a.qualify(root)
if __name__=='__main__':unittest.main()
