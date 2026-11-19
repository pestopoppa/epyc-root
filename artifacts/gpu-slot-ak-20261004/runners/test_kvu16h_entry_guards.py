"""Verify tracked unsafe runner entrypoints refuse before any inference."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
Q38 = HERE.parent.parent / 'gpu-block-27b-20261004' / 'runners'


class EntryGuardsTest(unittest.TestCase):
    def test_q38_cli_refuses_default_and_ab_before_preflight(self):
        for options in (['--dry-run'], ['--phases', 'A'], ['--phases=B,C'],
                        ['--dry-run', '--phases', 'A,C']):
            result = subprocess.run([sys.executable, '-B', str(Q38 / 'q38_t7.py'), *options],
                                    text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('KVU-16h', result.stderr)
            self.assertEqual(result.stdout, '')

    def test_q38_direct_phase_calls_refuse(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import q38_t7 as q; "
                "getattr(q, sys.argv[2])(*([None] * int(sys.argv[3])))")
        for name, count in [('phase_a', 2), ('phase_b', 6)]:
            result = subprocess.run([sys.executable, '-B', '-c', code, str(Q38), name, str(count)],
                                    text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('KVU-16h', result.stderr)

    def test_gpu_slot_wrapper_uses_tracked_dedicated_runners(self):
        wrapper = HERE / 'gpu_slot_ak.sh'
        source = wrapper.read_text()
        self.assertIn('p3_kvu_probe_isolated.py', source)
        self.assertIn('"$RUNNERS/slot_claim.py"', source)
        self.assertIn('"$RUNNERS/slot_run.py"', source)
        self.assertEqual(subprocess.run(['bash', '-n', str(wrapper)], check=False).returncode, 0)

    def test_p3_sequencer_dry_plan_targets_isolated_driver(self):
        code = ("import sys,types; sys.path.insert(0, sys.argv[1]); import slot_run as s; "
                "s.subprocess.run=lambda cmd,**kw: types.SimpleNamespace(returncode=0); "
                "sys.argv=['slot_run','--results','/tmp/not-created','--order','p3','--p3-pairs','1','--dry-run']; "
                "assert s.main()==0")
        result = subprocess.run([sys.executable, '-B', '-c', code, str(HERE)], text=True,
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('p3_kvu_probe_isolated.py', result.stdout)
        self.assertNotIn('p3_kvu_probe_slot.py', result.stdout)

    def test_non_p3_dry_plan_remains_available_without_p3_child(self):
        code = ("import sys,types; sys.path.insert(0, sys.argv[1]); import slot_run as s; "
                "seen=[]; s.subprocess.run=lambda cmd,**kw: seen.append(cmd) or types.SimpleNamespace(returncode=0); "
                "sys.argv=['slot_run','--results','/tmp/not-created','--order','kvu_on_b512','--dry-run']; "
                "assert s.main()==0; assert len(seen)==2; "
                "assert all('p3_kvu_probe_slot.py' not in ' '.join(cmd) for cmd in seen)")
        result = subprocess.run([sys.executable, '-B', '-c', code, str(HERE)], text=True,
                                capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_remains_available(self):
        for command in ([sys.executable, '-B', str(Q38 / 'q38_t7.py'), '--help'],
                        ['bash', str(HERE / 'gpu_slot_ak.sh'), '--help'],
                        [sys.executable, '-B', str(HERE / 'slot_run.py'), '--help']):
            self.assertEqual(subprocess.run(command, capture_output=True, check=False).returncode, 0)


if __name__ == '__main__':
    unittest.main()
