import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import strict_audit as a

VALID = '''header\n---\namdhsa.kernels:\n  - .name: flash_attn_test\n    .vgpr_count: 123\n    .agpr_count: 3\n    .vgpr_spill_count: 0\n    .sgpr_spill_count: 0\n    .group_segment_fixed_size: 0\n    .private_segment_fixed_size: 0\n...\n'''

class MetadataTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(a.parse_notes(VALID), [('flash_attn_test',123,3,0,0,0,0)])
    def test_missing_metadata_is_not_silently_skipped(self):
        for text in ('', '---\namdhsa.kernels: []', '---\n: malformed\n...', '---\nother: []\n...'):
            with self.subTest(text=text), self.assertRaises(a.AuditError):
                a.parse_notes(text)
    def test_missing_or_boolean_resource_is_not_zero(self):
        for replacement in ('', '    .vgpr_count: true\n', '    .vgpr_count: -1\n'):
            with self.subTest(replacement=replacement), self.assertRaises(a.AuditError):
                a.parse_notes(VALID.replace('    .vgpr_count: 123\n', replacement))

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.lib = self.base/'lib.so'
        self.lib.write_bytes(b'header' + a.MAGIC + b'payload')
        self.work = self.base/'work'
        self.work.mkdir()
    def fake(self, *, list_result=None, unbundle_fails=False, notes=VALID, demangle='nice-name\n'):
        def run(args, *, text=False, input=None):
            if '--list' in args:
                return a.TARGET+'\n' if list_result is None else list_result
            if '--unbundle' in args:
                if unbundle_fails: raise a.AuditError('unbundle failed')
                Path(next(x.split('=',1)[1] for x in args if x.startswith('--output='))).write_bytes(b'co')
                return b''
            if '--notes' in args: return notes
            if args[0]=='c++filt': return demangle
            raise AssertionError(args)
        return run
    def test_success_and_counted_nontarget(self):
        with patch.object(a, 'call', self.fake()):
            rows, receipt = a.audit(self.lib, self.work)
        self.assertEqual(rows, [('nice-name',123,3,0,0,0,0)])
        self.assertEqual(receipt['target_bundles'], 1)
    def test_unbundle_error_refuses(self):
        with patch.object(a, 'call', self.fake(unbundle_fails=True)), self.assertRaises(a.AuditError):
            a.audit(self.lib, self.work)
    def test_readelf_bad_notes_refuses(self):
        with patch.object(a, 'call', self.fake(notes='bad')), self.assertRaises(a.AuditError):
            a.audit(self.lib, self.work)
    def test_target_absent_refuses_not_empty_success(self):
        with patch.object(a, 'call', self.fake(list_result='host-x86_64\n')), self.assertRaises(a.AuditError):
            a.audit(self.lib, self.work)
    def test_demangler_lost_rows_refuses(self):
        with patch.object(a, 'call', self.fake(demangle='')), self.assertRaises(a.AuditError):
            a.audit(self.lib, self.work)
    def test_no_bundles_refuses(self):
        self.lib.write_bytes(b'plain')
        with self.assertRaises(a.AuditError): a.audit(self.lib, self.work)

if __name__ == '__main__': unittest.main()
