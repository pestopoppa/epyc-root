import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpu_witness as g


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvfork', prefix='g3-gpu-')
        self.root = Path(self.tmp.name)
        self.drm = self.root/'drm'; self.drm.mkdir()
        self.nodes = self.root/'nodes'; self.nodes.mkdir()
        self.device = self.root/'0000:43:00.0'; self.device.mkdir()
        for key, value in {'vendor':'0x1002', 'device':'0x740f', 'unique_id':'c6cb1cf088bd97ec', 'mem_info_vram_used':'100'}.items():
            (self.device/key).write_text(value)
        for name in ('card17', 'renderD129'):
            (self.drm/name).mkdir(); (self.drm/name/'device').symlink_to(self.device)
        self.node = self.nodes/'5'; self.node.mkdir()
        (self.node/'gpu_id').write_text('77')
        (self.node/'properties').write_text('unique_id 14324563317617088492\nvendor_id 4098\ndevice_id 29711\nlocation_id 17152\ndomain 0\ndrm_render_minor 129\n')
        # Use the helper's actual identity rather than an unrelated fixture ID.
        text=(self.node/'properties').read_text().splitlines()
        text[0]='unique_id '+str(g.helper().UNIQUE)
        (self.node/'properties').write_text('\n'.join(text)+'\n')
        self.proc = self.root/'proc'; self.pid = self.proc/'42'; self.pid.mkdir(parents=True)
        self.birth(123)
        self.binary=self.root/'llama-server'; self.binary.write_bytes(b'elf')
        (self.pid/'exe').symlink_to(self.binary)
        self.backend=self.root/'libggml-hip.so'; self.backend.write_bytes(b'hip')
        st=self.backend.stat()
        self.map_line=f'1-2 r-xp 0 {os.major(st.st_dev):x}:{os.minor(st.st_dev):x} {st.st_ino} {self.backend}\n'
        (self.pid/'maps').write_text(self.map_line)
        self.kfd=self.root/'kfd'; (self.kfd/'42').mkdir(parents=True)
        (self.kfd/'42/vram_77').write_text('50')
        self.mechanism=g.helper()
        self.identity=self.mechanism.discover(self.drm,self.nodes)

    def tearDown(self): self.tmp.cleanup()

    def birth(self, value):
        (self.pid/'stat').write_text('42 (server with spaces) '+' '.join(['S']+['0']*18+[str(value)]))

    def witness(self):
        return g.Witness(self.identity,backend=self.backend,binary=self.binary,proc_root=self.proc,kfd_root=self.kfd,mechanism=self.mechanism)

    def test_dynamic_card_and_own_device_allocation(self):
        self.assertEqual(self.identity['card'],'card17')
        self.assertEqual(self.identity['gpu_id'],77)
        (self.kfd/'42/vram_99').write_text('5000000000')
        sample=self.witness().sample(42)
        self.assertEqual(sample['status'],'RESIDENT_SNAPSHOT')
        self.assertEqual(sample['own_vram_bytes'],50)
        self.assertEqual(sample['device_vram_bytes'],100)

    def test_device_wide_allocation_never_substitutes_for_own(self):
        for value in (None,'0'):
            path=self.kfd/'42/vram_77'
            if value is None: path.unlink()
            else: path.write_text(value)
            sample=self.witness().sample(42)
            self.assertEqual(sample['status'],'UNKNOWN')
            self.assertEqual(sample['own_vram_bytes'],None if value is None else 0)

    def test_birth_reuse_and_topology_drift_refuse(self):
        witness=self.witness();witness.sample(42);self.birth(124)
        with self.assertRaisesRegex(ValueError,'PID/birth changed'):witness.sample(42)
        self.birth(123);(self.node/'gpu_id').write_text('78')
        with self.assertRaisesRegex(ValueError,'topology changed'):self.witness().sample(42)

    def test_wrong_kfd_render_mapping_and_duplicate_card_refuse(self):
        (self.drm/'renderD129/device').unlink()
        (self.drm/'renderD129/device').symlink_to(self.root)
        with self.assertRaisesRegex(ValueError,'render device mismatch'):
            self.mechanism.discover(self.drm,self.nodes)
        (self.drm/'renderD129/device').unlink();(self.drm/'renderD129/device').symlink_to(self.device)
        (self.drm/'card18').mkdir();(self.drm/'card18/device').symlink_to(self.device)
        with self.assertRaisesRegex(ValueError,'ambiguous'):self.mechanism.discover(self.drm,self.nodes)

    def test_wrong_map_inode_or_executable_is_unknown(self):
        (self.pid/'maps').write_text(self.map_line.replace('libggml-hip.so','libggml-hip-other.so'))
        self.assertEqual(self.witness().sample(42)['status'],'UNKNOWN')
        (self.pid/'maps').write_text(self.map_line)
        other=self.root/'other';other.write_bytes(b'other');(self.pid/'exe').unlink();(self.pid/'exe').symlink_to(other)
        self.assertEqual(self.witness().sample(42)['status'],'UNKNOWN')

    def test_birth_change_during_executable_check_refuses(self):
        original=os.path.samefile
        def changed(*args):
            result=original(*args);self.birth(125);return result
        with patch.object(os.path,'samefile',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'during witness'):self.witness().sample(42)

    def test_source_pin_and_caller_card_refusal(self):
        with self.assertRaisesRegex(ValueError,'pin mismatch'):g.pinned(self.binary,'0'*64)
        with patch.object(g,'pinned',return_value=b''),patch.object(g,'helper',return_value=self.mechanism),patch.object(self.mechanism,'discover',return_value=self.identity):
            for argv in (['driver','--card','other'],['driver','--card=other']):
                with patch.object(sys,'argv',argv):
                    with self.assertRaisesRegex(ValueError,'card override'):g.install(types.SimpleNamespace())

    def test_install_keeps_lifecycle_and_native_card(self):
        class Sampler:
            def __init__(self,*args):pass
        start=object();stop=object()
        gate=types.SimpleNamespace(Sampler=Sampler,Server=types.SimpleNamespace(start=start,stop=stop))
        with patch.object(g,'pinned',return_value=b''),patch.object(g,'helper',return_value=self.mechanism),patch.object(self.mechanism,'discover',return_value=self.identity),patch.object(sys,'argv',['driver']):
            self.assertEqual(g.install(gate),self.identity)
            self.assertEqual(sys.argv[-2:],['--card',str(Path(self.identity['device_vram']).parent)])
            self.assertIs(gate.Server.start,start);self.assertIs(gate.Server.stop,stop)
            with self.assertRaisesRegex(ValueError,'already installed'):g.install(gate)


if __name__=='__main__':unittest.main()
