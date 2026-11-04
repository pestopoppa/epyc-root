import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
D = Path('/mnt/raid0/llm/tmp/kvu/k35-native-validation-20261102')
s = importlib.util.spec_from_file_location('native_job_fixture', D / 'native_job.py')
j = importlib.util.module_from_spec(s)
s.loader.exec_module(j)
RF = Path('/mnt/raid0/llm/tmp/compute-flags/bin/rowflow')
sys.path.insert(0, str(RF))
import rowflow
import publish_row


class NativeRowTests(unittest.TestCase):
    def test_launcher_is_parsed_and_has_no_in_grant_preparation(self):
        o = rowflow.parse_launcher(str(D / 'launcher.sh'))
        self.assertEqual(o['ports'], [19761, 19762])
        self.assertEqual(o['claim_cpus'], '0-95')
        self.assertEqual(o['min_window'], 600)
        self.assertIsNone(publish_row.prep_in_grant(str(D / 'launcher.sh')))
        spec = json.loads((D / 'row-spec.json').read_text())
        self.assertEqual(publish_row.lint(spec), [])
        publish_row.check_handoff(spec, '/mnt/raid0/llm/worktrees/mains/h-kvu')

    def test_existing_35b_scenario_and_no_draft_command(self):
        m = j.load_runner()
        no, yes = j.scenarios(m)
        self.assertEqual(no.model, j.MODEL)
        self.assertEqual(yes.model, j.MODEL)
        a = m.build_server_argv(no, binary=j.BINARY, port=j.PORT, nominal_context=2048, max_tokens=16)
        b = m.build_server_argv(yes, binary=j.BINARY, port=j.PORT+1, nominal_context=2048, max_tokens=16)
        self.assertEqual(a[a.index('--spec-type')+1], 'none')
        self.assertNotIn('-md', a)
        self.assertFalse(any(x.startswith('--spec-draft-') for x in a))
        self.assertEqual(b[b.index('--spec-type')+1], 'draft-mtp')
        self.assertNotIn('speculative.n_max', m.build_chat_request_body(no, 'p', max_tokens=16))
        self.assertIsNone(yes.draft_model)  # existing same-file MTP head

    def test_changed_prepared_identity_refused_before_runner_or_process(self):
        record = json.loads((D/'prepared.json').read_text())
        bad = dict(record['identities'][0], size=-1)
        with patch.object(j, 'identity', return_value=bad), patch.object(j, 'load_runner') as loader:
            with self.assertRaisesRegex(RuntimeError, 'identity changed'):
                j.main()
            loader.return_value.run_cell.assert_not_called()

    def test_completion_requires_ok_and_proven_cleanup(self):
        m = j.load_runner()
        self.assertTrue(j.check_result(m, {'status':'ok','cleanup':{'dead':True,'completed':True}}))
        for r in ({'status':'ok'}, {'status':'ok','cleanup':{'dead':False,'completed':True}},
                  {'status':'sampling_failed','cleanup':{'dead':True,'completed':True}}):
            self.assertFalse(j.check_result(m, r))


if __name__ == '__main__':
    unittest.main()
