from pathlib import Path
import tempfile
import unittest
import device_identity as I
import sampler

class DeviceBindingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.drm=self.root/'drm';self.drm.mkdir();self.nodes=self.root/'nodes';self.nodes.mkdir()
  self.dev=self.root/'devices'/I.BDF;self.dev.mkdir(parents=True)
  (self.dev/'vendor').write_text('0x1002');(self.dev/'device').write_text('0x740f')
  (self.dev/'unique_id').write_text(f'{I.UNIQUE:x}');(self.dev/'mem_info_vram_used').write_text('123')
  for name in ('card9','renderD130'):
   p=self.drm/name;p.mkdir();(p/'device').symlink_to(self.dev,target_is_directory=True)
  self.node=self.nodes/'7';self.node.mkdir();(self.node/'gpu_id').write_text('987')
  self.props={'vendor_id':I.VENDOR,'device_id':I.DEVICE,'location_id':I.LOCATION,'domain':I.DOMAIN,'drm_render_minor':130,'unique_id':I.UNIQUE}
  self.write_props()
  self.proc=self.root/'proc'/'42';self.proc.mkdir(parents=True)
  (self.proc/'stat').write_text('42 (test proc) S ' + ' '.join(['0']*18 + ['123'] + ['0']*5))
  (self.proc/'maps').write_text('1000-2000 r-xp 00000000 00:00 0 /hip-real.so\n')
  self.kfd=self.root/'kfd';(self.kfd/'42').mkdir(parents=True)
  (self.kfd/'42'/'vram_987').write_text('100')
 def tearDown(self):self.tmp.cleanup()
 def write_props(self): (self.node/'properties').write_text(''.join(f'{k} {v}\n' for k,v in self.props.items()))
 def test_discover_renumbered_card_and_own_pid(self):
  device=I.discover(self.drm,self.nodes);self.assertEqual(device['card'],'card9');self.assertEqual(device['gpu_id'],987)
  row=sampler.read_sample(42,123,'/hip-real.so',self.root/'proc',self.kfd,device=device)
  self.assertEqual((row['own_vram_b'],row['card_used_b'],row['gpu_id']),(100,123,987));self.assertTrue(row['hip_resident'])
 def test_card_renumber_or_gpu_id_change_refuses(self):
  d=I.discover(self.drm,self.nodes);(self.node/'gpu_id').write_text('988')
  with self.assertRaisesRegex(RuntimeError,'binding changed'):I.revalidate(d)
 def test_wrong_render_device_refuses(self):
  other=self.root/'other';other.mkdir();render=self.drm/'renderD130'/'device';render.unlink();render.symlink_to(other,target_is_directory=True)
  with self.assertRaisesRegex(RuntimeError,'same PCI'):I.discover(self.drm,self.nodes)
 def test_wrong_unique_or_bdf_refuses(self):
  (self.dev/'unique_id').write_text('1')
  with self.assertRaisesRegex(RuntimeError,'unique id'):I.discover(self.drm,self.nodes)
 def test_unbound_gpu_residency_refuses(self):
  d=I.discover(self.drm,self.nodes);(self.kfd/'42'/'vram_12345').write_text('7')
  with self.assertRaisesRegex(RuntimeError,'unbound GPU'):
   sampler.read_sample(42,123,'/hip-real.so',self.root/'proc',self.kfd,device=d)
 def test_missing_target_entry_allowed_only_at_startup(self):
  d=I.discover(self.drm,self.nodes);(self.kfd/'42'/'vram_987').unlink()
  self.assertEqual(sampler.read_sample(42,123,'/hip-real.so',self.root/'proc',self.kfd,device=d,allow_uninitialized=True)['own_vram_b'],0)
  with self.assertRaisesRegex(RuntimeError,'target KFD'):
   sampler.read_sample(42,123,'/hip-real.so',self.root/'proc',self.kfd,device=d)
if __name__=='__main__':unittest.main()
