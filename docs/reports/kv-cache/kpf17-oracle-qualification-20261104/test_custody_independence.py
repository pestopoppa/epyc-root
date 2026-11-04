import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import custody

class IndependentCustody(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads(custody.COPY_MANIFEST.read_text())
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.external=Path(self.tmp.name)/'outside'
        self.external.write_text('outside')

    def check_refused(self, edit):
        data=copy.deepcopy(self.manifest)
        edit(data)
        manifest=Path(self.tmp.name)/'manifest.json'
        manifest.write_text(json.dumps(data))
        with patch.object(custody,'COPY_MANIFEST',manifest):
            with self.assertRaisesRegex(ValueError,'outside successor custody'):
                custody.build_identity()

    def test_current_copies_are_valid(self):
        build=custody.build_identity()
        self.assertTrue(Path(build['binary']).is_relative_to(custody.D/'runtime'))
        self.assertEqual(len(build['libraries']),5)

    def test_external_receipt_rejected(self):
        self.check_refused(lambda data:data.update(receipt_path=str(self.external)))

    def test_external_build_marker_rejected(self):
        self.check_refused(lambda data:data.update(ended_path=str(self.external)))

    def test_external_runtime_manifest_rejected(self):
        self.check_refused(lambda data:data.update(runtime_manifest_path=str(self.external)))

    def test_external_artifact_rejected(self):
        self.check_refused(lambda data:next(iter(data['artifacts'].values())).update(path=str(self.external)))

    def test_external_runtime_input_rejected(self):
        self.check_refused(lambda data:next(iter(data['runtime_inputs'].values())).update(path=str(self.external)))

    def test_external_runtime_rejected(self):
        self.check_refused(lambda data:data.update(runtime_bin=str(self.external.parent)))

if __name__=='__main__': unittest.main()
