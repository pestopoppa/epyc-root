import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

D = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch/fresh')
spec = importlib.util.spec_from_file_location('provenance', D/'provenance.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class ProvenanceTests(unittest.TestCase):
    def test_identity_refuses_content_drift(self):
        root = D/f'fixture-{os.getpid()}'; root.mkdir()
        build = root/'build'; build.mkdir(); out = root/'out'; out.mkdir(); (out/'plan').mkdir()
        (root/'fresh').mkdir(); (root/'fresh/SOURCES.sha256').write_text('source')
        (build/'llama-server').write_bytes(b'binary'); (build/'libggml.so').write_bytes(b'dso')
        model = root/'model'; model.write_bytes(b'weights'); template = root/'template'; template.write_bytes(b'template')
        for f in ('A0.recipe', 'A1.recipe', 'plan/plan.json', 'plan/items.jsonl'): (out/f).write_text(f)
        real_resolve = Path.resolve
        def resolve(x, *args, **kwargs):
            if str(x) == '/mnt/raid0/llm/kernels/production/gpu': return build
            return real_resolve(x, *args, **kwargs)
        def git(argv, text=True): return '7e7d5ef7f28f0c0ec45c16b7a90a51750006671f\n' if 'rev-parse' in argv else ''
        with patch.object(p, 'ROOT', root), patch.object(p, 'BUILD', build), patch.object(p, 'MODEL', model), patch.object(p, 'TEMPLATE', template), patch.object(Path, 'resolve', resolve), patch.object(p.subprocess, 'check_output', git), patch.object(sys, 'argv', ['provenance', str(out)]):
            p.main(); self.assertEqual(json.loads((out/'provenance.json').read_text())['model'], p.sha(model))
            model.write_bytes(b'changed')
            with self.assertRaises(SystemExit): p.main()

if __name__ == '__main__': unittest.main()
