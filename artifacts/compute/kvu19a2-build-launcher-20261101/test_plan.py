import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('plan', Path(__file__).with_name('plan.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def valid():
    return {'commit':p.COMMIT, 'tree':p.TREE, 'patch_sha256':p.PATCH,
            'cmake':'/usr/bin/cmake', 'cmake_sha256':'a'*64,
            'hip_compiler':'/opt/rocm/llvm/bin/clang++', 'hip_compiler_sha256':'b'*64,
            'scratch_root':'/mnt/raid0/llm/tmp/kvu19-new', 'parallel':24,
            'baseline_source_manifest_sha256':'c'*64, 'candidate_source_manifest_sha256':'d'*64}


class PlanTests(unittest.TestCase):
    def test_modes_disjoint_and_target_is_two_hip_builds(self):
        q, t = p.make_plan(valid(), True), p.make_plan(valid(), False)
        self.assertIn('/qualification/', q['event'])
        self.assertIn('/target/', t['event'])
        self.assertEqual(len(t['commands']), 4)
        self.assertTrue(all('/target/' not in str(x) and '/sources/' not in str(x) for x in q['commands']))
        self.assertIn('-DAMDGPU_TARGETS=gfx90a', t['commands'][0])
        self.assertIn('/candidate', str(t['commands'][2]))

    def test_refuse_unbound_identity_and_paths(self):
        for key, value in [('commit','bad'), ('patch_sha256','bad'), ('cmake_sha256','x'*64),
                           ('scratch_root','/mnt/raid0/llm/tmp/compute-flags/x'), ('parallel',True),
                           ('hip_compiler','/opt/../outside')]:
            r=copy.deepcopy(valid()); r[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): p.make_plan(r, False)

    def test_target_requires_arm_manifests(self):
        r=valid(); del r['candidate_source_manifest_sha256']
        with self.assertRaises(ValueError): p.make_plan(r, False)
        self.assertEqual(p.make_plan(r, True)['mode'], 'qualification')

    def test_refuse_ambiguous_mode(self):
        with self.assertRaises(ValueError): p.make_plan(valid(), '1')

if __name__ == '__main__': unittest.main()
