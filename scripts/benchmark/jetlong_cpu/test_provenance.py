import tempfile
import unittest
from pathlib import Path
import provenance as p
import server_lifecycle as lifecycle
from unittest.mock import patch

class Tests(unittest.TestCase):
    def test_maps_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); base=root/'libggml-base.so.0'; cpu=root/'libggml-cpu.so.0'
            base.touch(); cpu.touch()
            line=lambda path: f'1000-2000 r-xp 0000 00:00 0 {path}\n'
            self.assertEqual(len(p.check_runtime_maps(line(base)+line(cpu), root, [base,cpu])),2)
            for maps, allowed in [(line(base),[base,cpu]),(line(base)+line(cpu),[base]),(line(base)+line(cpu)+'100-200 r--p 0 00:00 0 /tmp/libggml.so (deleted)\n',[base,cpu])]:
                with self.assertRaises(p.ProvenanceError): p.check_runtime_maps(maps,root,allowed)
    def test_hash_and_weights_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'lib.so'; f.write_bytes(b'x')
            p.check_artifacts({'artifacts':{str(f):p.sha256(f)}})
            with self.assertRaises(p.ProvenanceError): p.check_artifacts({'artifacts':{str(f):'0'*64}})
            with self.assertRaises(p.ProvenanceError): p.check_artifacts({'artifacts':{str(f)+'.gguf':'0'*64}})

    def test_verified_entry_pins_executable_and_checks_live_pid(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            server = root / 'server'
            server.write_bytes(b'executable')
            manifest = {'artifacts': {str(server): p.sha256(server)}}
            def fake_owned(*, runtime_check, **kwargs):
                runtime_check(123)
                return 75
            with patch.object(lifecycle, 'run_owned', side_effect=fake_owned), \
                 patch.object(p, 'check_live') as check:
                self.assertEqual(lifecycle.run_verified(manifest=manifest, expected_dir=root,
                    command=[str(server)], env={'LD_LIBRARY_PATH': str(root)}), 75)
                check.assert_called_once_with(123, root, manifest)
            with self.assertRaises(p.ProvenanceError):
                lifecycle.run_verified(manifest=manifest, expected_dir=root,
                    command=[str(root / 'other')], env={'LD_LIBRARY_PATH': str(root)})
            with self.assertRaises(p.ProvenanceError):
                lifecycle.run_verified(manifest=manifest, expected_dir=root,
                    command=[str(server)], env={'LD_LIBRARY_PATH': '/untrusted'})

if __name__=='__main__': unittest.main()
