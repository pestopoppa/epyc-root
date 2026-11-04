import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('isolated_selector', BASE/'select_run.py')
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root/'out/runs/20261104T160700Z'
        self.run.mkdir(parents=True)
        (self.run/'calls.jsonl').write_text('{}\n')
        self.grant = self.root/'ufh14-b4k-test-20261104.grant'
        self.grant.write_text('regions=mi210_0,184-191 start=2026-11-04T16:06Z end=2026-11-04T16:08Z holds=mi210_0,q3\n')
        self.ended = self.grant.with_suffix('.ended')
        self.ended.write_text('rc=0 time=2026-11-04T16:07:59Z reason=complete\njob_id='+self.grant.stem+'\n')
        self.complete = self.root/'COMPLETE'
        self.binding = dict(run=str(self.run), grant_id=self.grant.stem, grant_start='2026-11-04T16:06Z', grant_end='2026-11-04T16:08Z', grant_sha256=hashlib.sha256(self.grant.read_bytes()).hexdigest())
        self.save()
    def save(self):
        self.complete.write_text(json.dumps(self.binding))
    def select(self):
        return selector.select_run(self.root,self.complete,self.grant,self.ended)
    def test_native_exact(self):
        self.assertEqual(self.select(),self.run)
    def test_timezone_normalization(self):
        self.binding['grant_start']='2026-11-04T17:06:00+01:00'; self.save()
        self.assertEqual(self.select(),self.run)
    def test_naive_timezone(self):
        self.binding['grant_start']='2026-11-04T16:06:00'; self.save()
        with self.assertRaises(ValueError): self.select()
    def test_ambiguous_even_without_calls(self):
        (self.run.parent/'20261104T160701Z').mkdir()
        with self.assertRaisesRegex(ValueError,'exactly'): self.select()
    def test_ungranted_run(self):
        outside=self.run.parent/'20261104T160643Z'
        # Same second shape as accidental run, but fixture grant starts later.
        self.grant.write_text(self.grant.read_text().replace('16:06Z','16:07Z'))
        self.binding.update(grant_start='2026-11-04T16:07Z',grant_sha256=hashlib.sha256(self.grant.read_bytes()).hexdigest())
        outside.mkdir(); self.binding['run']=str(outside); self.save()
        with self.assertRaisesRegex(ValueError,'outside'): self.select()
    def test_missing_binding(self):
        del self.binding['grant_sha256']; self.save()
        with self.assertRaises(ValueError): self.select()
    def test_forged_binding(self):
        for key,value in [('grant_id','forged'),('grant_sha256','0'*64),('grant_start','2026-11-04T16:05Z')]:
            with self.subTest(key=key):
                old=self.binding[key]; self.binding[key]=value; self.save()
                with self.assertRaises(ValueError): self.select()
                self.binding[key]=old
    def test_failed_receipt(self):
        self.ended.write_text('rc=1 time=2026-11-04T16:07:59Z reason=failed\n')
        with self.assertRaises(ValueError): self.select()
    def test_receipt_job_id_mismatch(self):
        self.ended.write_text(self.ended.read_text().replace(self.grant.stem,'foreign'))
        with self.assertRaises(ValueError): self.select()
    def test_duplicate_complete(self):
        self.complete.write_text(self.complete.read_text()[:-1]+',"grant_id":"forged"}')
        with self.assertRaisesRegex(ValueError,'duplicate'): self.select()
    def test_duplicate_grant(self):
        self.grant.write_text(self.grant.read_text().strip()+' start=2026-11-04T16:06Z\n')
        with self.assertRaisesRegex(ValueError,'duplicate'): self.select()
    def test_duplicate_receipt(self):
        self.ended.write_text(self.ended.read_text()+'rc=0\n')
        with self.assertRaisesRegex(ValueError,'duplicate'): self.select()
    def test_malformed_receipt(self):
        for raw in ['', 'rc=0 time=bad reason=complete\n','rc=0 time=2026-11-04T16:07:59Z\n', 'rc=0 time=2026-11-04T16:07:59Z reason=complete\nbad\n']:
            with self.subTest(raw=raw):
                self.ended.write_text(raw)
                with self.assertRaises(ValueError): self.select()
    def test_invalid_grant_window(self):
        self.grant.write_text(self.grant.read_text().replace('end=2026-11-04T16:08Z','end=2026-11-04T16:05Z'))
        self.binding['grant_sha256']=hashlib.sha256(self.grant.read_bytes()).hexdigest(); self.save()
        with self.assertRaises(ValueError): self.select()
    def test_foreign_receipt_filename(self):
        self.ended=self.ended.rename(self.root/'foreign.ended')
        with self.assertRaises(ValueError): self.select()
    def test_relative_or_symlink_run(self):
        self.binding['run']='out/runs/'+self.run.name; self.save()
        with self.assertRaises(ValueError): self.select()
    def test_help_and_unknown_parse_before_any_job_action(self):
        # Extract only the parser prefix: never execute/import job.py or its CLI.
        tree=ast.parse((BASE/'job.py').read_text())
        main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        prefix=[]
        for node in main.body:
            prefix.append(node)
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='args' for t in node.targets): break
        self.assertEqual(len(prefix),3)
        func=ast.FunctionDef(name='parse_only',args=main.args,body=prefix,decorator_list=[],returns=None)
        import argparse
        scope={'argparse':argparse}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[func],type_ignores=[])),'<isolated-parser>','exec'),scope)
        for argv,code in [(['--help'],0),(['--definitely-unknown'],2)]:
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error: scope['parse_only'](argv)
                self.assertEqual(error.exception.code,code)

if __name__=='__main__': unittest.main()
