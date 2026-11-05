import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import runtime_linkage as m

class MapProof(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.build=Path(self.tmp.name)
  for n in m.REQUIRED:(self.build/n).touch()
 def tearDown(self):self.tmp.cleanup()
 def line(self,p,perms='r-xp'):
  st=p.stat();return f'1000-2000 {perms} 00000000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {p}'
 def metadata(self,n):
  st=(self.build/n).stat();return {'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
 def maps(self):return '\n'.join(self.line(self.build/n) for n in sorted(m.REQUIRED))+'\n'
 def test_exact_mapped_inode_set(self):
  result=m.parse_maps(self.maps(),self.build);self.assertEqual(set(result['files']),m.REQUIRED);self.assertEqual(result['measurement_admission'],'none')
 def test_missing_and_nonexecuting_rejected(self):
  for text in ('\n'.join(self.maps().splitlines()[1:]),self.maps().replace('r-xp','r--p')):
   with self.assertRaises(ValueError):m.parse_maps(text,self.build)
 def test_wrong_inode_deleted_and_foreign_ggml_rejected(self):
  base=self.maps();p=self.build/'libggml.so.0.16.0';bad=self.build/'libggml-malicious.so';bad.touch()
  for text in (base.replace(self.line(p),self.line(p).replace(str(p.stat().st_ino)+' ',str(p.stat().st_ino+1)+' ')),base.replace(str(p),str(p)+' (deleted)'),base+self.line(bad)+'\n'):
   with self.assertRaises(ValueError):m.parse_maps(text,self.build)
 def test_prepared_digest_is_bound_to_original_inode(self):
  mapped=m.parse_maps(self.maps(),self.build);prep={'schema':'epyc.ch26.c5-mapped-preparation.v1','files':{n:{**v,**self.metadata(n),'sha256':'b'*64} for n,v in mapped['files'].items()}}
  self.assertEqual(m.bind_prepared(mapped,prep)['prepared_sha256']['llama-server'],'b'*64)
  prep['files']['llama-server']['inode']+=1
  with self.assertRaisesRegex(ValueError,'mapped inode'):m.bind_prepared(mapped,prep)
 def test_partial_mapped_set_is_refused(self):
  mapped=m.parse_maps(self.maps(),self.build);prep={'schema':'epyc.ch26.c5-mapped-preparation.v1','files':{n:{**v,**self.metadata(n),'sha256':'b'*64} for n,v in mapped['files'].items()}}
  mapped['files'].pop('llama-server')
  with self.assertRaisesRegex(ValueError,'incomplete mapped binary set'):m.bind_prepared(mapped,prep)
 def test_same_inode_mutation_refused(self):
  target=self.build/'llama-server';target.write_bytes(b'a')
  mapped=m.parse_maps(self.maps(),self.build);prep={'schema':'epyc.ch26.c5-mapped-preparation.v1','files':{n:{**v,**self.metadata(n),'sha256':'b'*64} for n,v in mapped['files'].items()}}
  before=target.stat();target.write_bytes(b'b');os.utime(target,ns=(before.st_atime_ns,before.st_mtime_ns))
  with self.assertRaisesRegex(ValueError,'changed after hash'):m.bind_prepared(mapped,prep)
 def test_replaced_path_cannot_authenticate_old_mapping(self):
  text=self.maps();p=self.build/'llama-server';p.rename(self.build/'original-server');p.write_text('replacement')
  with self.assertRaisesRegex(ValueError,'inode'):m.parse_maps(text,self.build)
 def test_identity_change_and_oversize_maps_refused(self):
  proc=self.build/'proc';(proc/'11').mkdir(parents=True);(proc/'11'/'maps').write_text(self.maps()); (proc/'11'/'exe').symlink_to(self.build/'llama-server')
  mapped=m.parse_maps(self.maps(),self.build); prep={'schema':'epyc.ch26.c5-mapped-preparation.v1','files':{n:{**v,**self.metadata(n),'sha256':'a'*64} for n,v in mapped['files'].items()}}
  with patch.object(m,'identity',side_effect=[{'pid':11,'start_ticks':1},{'pid':11,'start_ticks':2}]):
   with self.assertRaisesRegex(ValueError,'identity changed'):m.capture(11,prep,self.build,proc)
  (proc/'11'/'maps').write_text('x'*(4*1024*1024+1))
  with patch.object(m,'identity',return_value={'pid':11,'start_ticks':1}):
   with self.assertRaisesRegex(ValueError,'exceeds bound'):m.capture(11,prep,self.build,proc)
 def test_capture_requires_exec_inode_to_match_mapped_server(self):
  proc=self.build/'proc';(proc/'11').mkdir(parents=True);(proc/'11'/'maps').write_text(self.maps())
  exe=proc/'11'/'exe';exe.symlink_to(self.build/'llama-server')
  mapped=m.parse_maps(self.maps(),self.build);prep={'schema':'epyc.ch26.c5-mapped-preparation.v1','files':{n:{**v,**self.metadata(n),'sha256':'a'*64} for n,v in mapped['files'].items()}}
  with patch.object(m,'identity',return_value={'pid':11,'start_ticks':1}):
   self.assertEqual(m.capture(11,prep,self.build,proc)['executable'],mapped['files']['llama-server'])
   exe.unlink();exe.symlink_to(self.build/'libggml.so.0.16.0')
   with self.assertRaisesRegex(ValueError,'executable inode mismatch'):m.capture(11,prep,self.build,proc)
if __name__=='__main__':unittest.main()
