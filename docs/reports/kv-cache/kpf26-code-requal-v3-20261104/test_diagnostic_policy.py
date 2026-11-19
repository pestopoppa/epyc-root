import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

D=Path(__file__).parent
spec=importlib.util.spec_from_file_location('diagnostic_policy',D/'diagnostic_policy.py')
policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy)


class PolicyTests(unittest.TestCase):
    def test_explicit_cap_retains_native_fraction_and_corrects_effective_budget(self):
        stage=SimpleNamespace(PER_CALL_TIMEOUT_S=180.0,REQUEST_BUDGET_FRACTION=.4)
        row=policy.apply(stage)
        self.assertEqual(stage.PER_CALL_TIMEOUT_S,600)
        self.assertEqual(stage.REQUEST_BUDGET_FRACTION,.4)
        self.assertEqual(row['initial_effective_scout_budget_s'],600)
        self.assertEqual(row['original_per_call_timeout_s'],180)

    def test_unexpected_native_fraction_is_refused(self):
        stage=SimpleNamespace(PER_CALL_TIMEOUT_S=180.0,REQUEST_BUDGET_FRACTION=.5)
        with self.assertRaises(ValueError):policy.apply(stage)
        self.assertEqual(stage.PER_CALL_TIMEOUT_S,180)

    def test_packet_preparation_and_full_failure_sealing_are_explicit(self):
        rebind=(D/'rebind_packet.py').read_text()
        self.assertIn('timeout_s=1800',rebind)
        job=(D/'job.sh').read_text()
        self.assertIn('collector_rc=$?',job)
        self.assertIn("'status':'completed' if rc==0 else 'incomplete'",job)
        self.assertIn('[[ "$collector_rc" == 0 ]] || exit "$collector_rc"',job)
        self.assertLess(job.index('[[ "$collector_rc" == 0 ]] || exit "$collector_rc"'),job.index('touch "$D/$arm.COMPLETE"'))
        self.assertIn('FILLER_DRYRUN_RESULT_PATH',job)

    def test_terminal_off_id_is_replaced_without_resetting_lineage(self):
        off=json.loads((D/'off-spec.json').read_text());on=json.loads((D/'on-spec.json').read_text())
        self.assertEqual(off['id'],'rtg58-kpf26-code-off-diag-r2-20261104')
        self.assertEqual(off['lineage'],'rtg58-kpf26-code-off-diag-20261102')
        self.assertEqual(off['supersedes'],off['lineage'])
        self.assertEqual(on['id'],'rtg58-kpf26-code-on-diag-20261102')
        self.assertNotEqual(off['result_path'],on['result_path'])


if __name__=='__main__':unittest.main()
