import hashlib
import tempfile
import unittest
from pathlib import Path
import verify_source_packet as v

class VerifySourcePacket(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.archive = Path(self.t.name) / 'archive.tar'
        self.archive.write_bytes(b'source')
        self.source = dict(status='NOT_BUILT_NOT_QUALIFIED', production_base=v.BASE,
          dca_tip=v.DCA, fa_tip=v.FA, prospective_tree=v.TREE, archive_size=6,
          archive_sha256=hashlib.sha256(b'source').hexdigest())
        self.audit = dict(base=v.BASE,dca=v.DCA,fa=v.FA,prospective_tree=v.TREE,violations=[],
          both_changed_require_semantic_review=[{'path': x} for x in v.REVIEWED])
        self.review = dict(base=v.BASE,candidate_tree=v.TREE,files=list(v.REVIEWED),
          checks={x:{'reverse_and_roundtrip':'PASS'} for x in ('fa','dca')})
    def test_valid_and_archive_mutation(self):
        self.assertEqual(v.verify(self.source,self.audit,self.review,self.archive)['state'],'SOURCE_PACKET_ONLY')
        self.archive.write_bytes(b'modify')
        with self.assertRaises(v.CustodyError): v.verify(self.source,self.audit,self.review,self.archive)
    def test_missing_review_or_source_mismatch(self):
        self.review['checks']['fa']['reverse_and_roundtrip'] = 'FAIL'
        with self.assertRaises(v.CustodyError): v.verify(self.source,self.audit,self.review,self.archive)
        self.review['checks']['fa']['reverse_and_roundtrip'] = 'PASS'
        self.source['prospective_tree']='other'
        with self.assertRaises(v.CustodyError): v.verify(self.source,self.audit,self.review,self.archive)
    def test_violation_or_missing_path(self):
        self.audit['violations']=['loss']
        with self.assertRaises(v.CustodyError): v.verify(self.source,self.audit,self.review,self.archive)
        self.audit['violations']=[]
        self.audit['both_changed_require_semantic_review'].pop()
        with self.assertRaises(v.CustodyError): v.verify(self.source,self.audit,self.review,self.archive)

if __name__ == '__main__': unittest.main()
