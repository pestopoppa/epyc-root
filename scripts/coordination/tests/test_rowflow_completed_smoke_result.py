"""Completed-smoke filing only: all resources/files are temporary, no smoke or qualification."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rowflow'))
import publish_row as pr


class CompletedSmokeResultTests(unittest.TestCase):
    def fixture(self, root, pattern=True):
        root=Path(root);scratch=root/'job';scratch.mkdir();flags=root/'flags'
        (flags/'ready').mkdir(parents=True);dry=flags/'dryrun'/'control';dry.mkdir(parents=True)
        result=scratch/'control'/'attempt-1'/'RESULT.json';result.parent.mkdir(parents=True)
        result.write_text('{"complete": true}\n')
        engine=scratch/'filler_run15.sh';engine.write_text('#!/bin/bash\nexit 99 # MUST NEVER RUN\n')
        checker=scratch/'checker.py';checker.write_text('import json,sys\nsys.exit(0 if json.load(open(sys.argv[1])).get("complete") is True else 1)\n')
        launcher=scratch/'launch.sh'
        launcher.write_text(f'#!/bin/bash\nexec bash {engine} --id control --class cpu --min-window 300 --stop {scratch}/STOP --workdir {scratch} --cmd "false" --complete-cmd "python3 {checker} {result}"\n')
        declared=str(scratch/'control'/'*'/'RESULT.json') if pattern else str(result)
        row=dict(schema=pr.rf.SCHEMA,id='control',owner='test',scratch_root=str(scratch),result_path=declared,result_format='json',decision_rule='source capture only',launcher=dict(path=str(launcher),sha256=pr.rf.sha256(launcher)),engine=dict(path=str(engine),sha256=pr.rf.sha256(engine)))
        ready=flags/'ready'/'control.json';ready.write_text(json.dumps(row))
        passed=dict(id='control',job_complete=True,result_path=declared,result_format='json',launcher_sha256=row['launcher']['sha256'],engine_sha256=row['engine']['sha256'])
        (dry/'PASS.json').write_text(json.dumps(passed));(dry/'ended').write_text('rc=0 reason=complete\n');(dry/'complete').write_text('complete\n')
        return flags,scratch,dry,result,row

    def file(self, flags, row):
        with contextlib.redirect_stdout(io.StringIO()):
            return pr.file_if_complete(str(flags),'control',row)

    def test_literal_and_glob_archive_one_resolved_result_without_copying(self):
        for pattern in (False,True):
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td,pattern)
                original_pass=(dry/'PASS.json').read_bytes();original_result=result.read_bytes()
                with patch.object(pr.shutil,'copyfile',side_effect=AssertionError('must not copy native results')):
                    self.assertTrue(self.file(flags,row))
                archived=json.loads((dry/'completed-manifest.json').read_text())
                self.assertEqual(archived['result_path'],str(result.resolve()))
                self.assertEqual(archived['declared_result_path'],row['result_path'])
                self.assertEqual(archived['completed_result_sha256'],pr.rf.sha256(result))
                self.assertEqual(json.loads((dry/'published-manifest.json').read_text()),row)
                self.assertEqual((dry/'PASS.json').read_bytes(),original_pass)
                self.assertEqual(result.read_bytes(),original_result)
                self.assertFalse((scratch/'control'/'*').exists())
                self.assertFalse((flags/'ready'/'control.json').exists())
                self.assertTrue((flags/'grants'/'control.complete').is_file())

    def test_missing_ambiguous_and_escape_refused_before_terminal_writes(self):
        for change in ('missing','ambiguous','symlink_escape','parent_escape'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                if change=='missing':result.unlink()
                elif change=='ambiguous':
                    other=scratch/'control'/'attempt-2'/'RESULT.json';other.parent.mkdir();other.write_text('{}')
                else:
                    outside=Path(td)/'outside';outside.mkdir();(outside/'RESULT.json').write_text('{}');result.unlink()
                    if change=='symlink_escape':result.symlink_to(outside/'RESULT.json')
                    else:
                        result.parent.rmdir();result.parent.symlink_to(outside,target_is_directory=True)
                with self.assertRaises(pr.rf.Refused):self.file(flags,row)
                self.assertFalse((flags/'grants').exists())
                self.assertFalse((flags/'ready'/'control.json').exists())
                self.assertTrue((dry/'unpublished.json').exists())

    def test_resume_legacy_completed_or_unpublished_without_rerun_or_pass_rewrite(self):
        for manifest in ('unpublished.json','completed-manifest.json'):
            with self.subTest(manifest=manifest),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                (flags/'ready'/'control.json').unlink();(dry/manifest).write_text(json.dumps(row))
                original_pass=(dry/'PASS.json').read_bytes()
                with patch.object(pr.rf,'dryrun_run',side_effect=AssertionError('no smoke rerun')),patch.object(pr.rf,'publish',side_effect=AssertionError('no republication')),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(pr.main(['--resume-complete','control','--flags',str(flags)]),0)
                self.assertEqual((dry/'PASS.json').read_bytes(),original_pass)
                self.assertTrue((flags/'grants'/'control.complete').exists())

    def test_resume_is_idempotent_and_preserves_pass_and_terminal_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            flags,scratch,dry,result,row=self.fixture(td)
            self.file(flags,row)
            originals={str(x):x.read_bytes() for x in (flags/'grants').iterdir()}
            passed=(dry/'PASS.json').read_bytes()
            with patch.object(pr.rf,'dryrun_run',side_effect=AssertionError('no smoke rerun')),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pr.resume_complete(str(flags),'control'),0)
            self.assertEqual(originals,{str(x):x.read_bytes() for x in (flags/'grants').iterdir()})
            self.assertEqual((dry/'PASS.json').read_bytes(),passed)

    def test_conflicting_prior_manifests_and_archived_hash_drift_refused(self):
        for change in ('manifests','archive_hash'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                (flags/'ready'/'control.json').unlink()
                if change=='manifests':
                    (dry/'unpublished.json').write_text(json.dumps(row))
                    (dry/'published-manifest.json').write_text(json.dumps(dict(row,decision_rule='changed')))
                else:
                    archived=dict(row,result_path=str(result),declared_result_path=row['result_path'],completed_result_sha256='0'*64)
                    (dry/'completed-manifest.json').write_text(json.dumps(archived))
                with self.assertRaises(pr.rf.Refused):pr.resume_complete(str(flags),'control')
                self.assertFalse((flags/'grants').exists())

    def test_resume_refuses_content_hash_drift(self):
        for change in ('result','launcher','engine','pass','referenced_source'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                self.file(flags,row)
                if change=='result':result.write_text('{"complete": true,"changed":true}')
                elif change in ('launcher','engine'):
                    path=Path(row[change]['path']);path.write_text(path.read_text()+'\n# changed\n')
                elif change=='pass':
                    path=dry/'PASS.json';passed=json.loads(path.read_text());passed['passed_at']='changed';path.write_text(json.dumps(passed))
                else:
                    path=scratch/'checker.py';path.write_text(path.read_text()+'\n# changed\n')
                before={str(x):x.read_bytes() for x in (flags/'grants').iterdir()}
                with self.assertRaises(pr.rf.Refused),contextlib.redirect_stdout(io.StringIO()):pr.resume_complete(str(flags),'control')
                self.assertEqual(before,{str(x):x.read_bytes() for x in (flags/'grants').iterdir()})

    def test_pass_recorded_result_hash_and_identity_drift_refused(self):
        for mutation in (dict(result_sha256='0'*64),dict(id='other'),dict(engine_sha256='0'*64),dict(result_format='jsonl')):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                path=dry/'PASS.json';passed=json.loads(path.read_text());passed.update(mutation);path.write_text(json.dumps(passed))
                with self.assertRaises(pr.rf.Refused):self.file(flags,row)
                self.assertFalse((flags/'grants').exists())

    def test_missing_or_incomplete_pass_cannot_resume(self):
        for passed in (None,dict(id='control',job_complete=False)):
            with self.subTest(passed=passed),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                (flags/'ready'/'control.json').unlink();(dry/'unpublished.json').write_text(json.dumps(row))
                if passed is None:(dry/'PASS.json').unlink()
                else:(dry/'PASS.json').write_text(json.dumps(passed))
                with self.assertRaises(pr.rf.Refused):pr.resume_complete(str(flags),'control')
                self.assertFalse((flags/'grants').exists())

    def test_original_no_branch_and_full_completion_checks_remain(self):
        for change in ('branch','predicate'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as td:
                flags,scratch,dry,result,row=self.fixture(td)
                checker=scratch/'checker.py'
                if change=='branch':checker.write_text(checker.read_text()+'\n# FILLER_DRYRUN\n')
                else:result.write_text('{"complete":false}')
                self.assertFalse(self.file(flags,row))
                self.assertFalse((flags/'grants').exists())

if __name__=='__main__':unittest.main()
