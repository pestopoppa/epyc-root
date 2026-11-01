import json
import tempfile
import unittest
from pathlib import Path
from result_journal import output_root, notify_completed

class JournalTest(unittest.TestCase):
    def test_disjoint_output_namespaces(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); env={'FILLER_RESULTS_DIR':str(p/'production'),'FILLER_DRYRUN':'1','FILLER_DRYRUN_DIR':str(p/'attempt')}
            self.assertEqual(output_root(env), (p/'attempt/yarn-e1-results').resolve())
            self.assertEqual(output_root(dict(env,FILLER_DRYRUN='0')), (p/'production').resolve())
            for d in [str(p/'production'), str(p/'production/child')]:
                with self.assertRaises(ValueError): output_root(dict(env,FILLER_DRYRUN_DIR=d))
    def test_missing_or_bad_environment_refuses(self):
        for env in [{}, {'FILLER_RESULTS_DIR':'/tmp/out','FILLER_DRYRUN':'1'}, {'FILLER_RESULTS_DIR':'/tmp/out','FILLER_DRYRUN':'yes'}]:
            with self.assertRaises(ValueError): output_root(env)
    def test_crash_after_marker_recovers_once(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); marker=root/'E1-A0-low/complete.json'; marker.parent.mkdir()
            marker.write_text(json.dumps({'status':'COMPLETE','image':'E1','arm':'A0','level':'low'}))
            self.assertTrue(notify_completed(root,('E1','A0','low')))
            self.assertFalse(notify_completed(root,('E1','A0','low')))
            self.assertEqual(len((root/'completed-cells.jsonl').read_text().splitlines()),1)
    def test_torn_journal_and_wrong_identity_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); marker=root/'E1-A0-low/complete.json'; marker.parent.mkdir()
            marker.write_text(json.dumps({'status':'COMPLETE','image':'W','arm':'A0','level':'low'}))
            with self.assertRaises(ValueError): notify_completed(root,('E1','A0','low'))
            marker.write_text(json.dumps({'status':'COMPLETE','image':'E1','arm':'A0','level':'low'}))
            (root/'completed-cells.jsonl').write_text('{')
            with self.assertRaises(ValueError): notify_completed(root,('E1','A0','low'))
    def test_duplicate_notification_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); marker=root/'E1-A0-low/complete.json'; marker.parent.mkdir()
            marker.write_text(json.dumps({'status':'COMPLETE','image':'E1','arm':'A0','level':'low'}))
            notify_completed(root,('E1','A0','low'))
            journal=root/'completed-cells.jsonl'; journal.write_text(journal.read_text()*2)
            with self.assertRaises(ValueError): notify_completed(root,('E1','A0','low'))
if __name__=='__main__': unittest.main()
