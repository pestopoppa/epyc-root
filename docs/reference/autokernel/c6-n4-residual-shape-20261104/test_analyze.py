import hashlib
import struct
import unittest
import tempfile
from pathlib import Path
from analyze import unpack_pair, check_source, capture_path

def metadata(data, ne='2,2,1,1', nb='4,8,16,16'):
    return {'type': 0, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'ne': ne, 'nb': nb}

class CaptureTest(unittest.TestCase):
    def setUp(self):
        self.a=struct.pack('<4f',1,2,3,4)
        self.b=struct.pack('<4f',0,0,1,1)
        self.am=metadata(self.a); self.bm=metadata(self.b)
    def test_result_pin_rejects_changed_data(self):
        with self.assertRaisesRegex(ValueError,'retained result changed'):
            check_source(b'{}')
    def test_paths_are_confined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); dest=root/'runs'/('run-' + '1793821833' + '552414812')/'0'; dest.mkdir(parents=True)
            external=root/'external'; external.write_bytes(b'bad')
            (dest/'candidate_output.bin').symlink_to(external)
            with self.assertRaisesRegex(ValueError,'escaped retained root'):
                capture_path(root,('/elsewhere/run-' + '1793821833' + '552414812/0'),'candidate_output.bin')
            with self.assertRaisesRegex(ValueError,'unexpected run path'):
                capture_path(root,'/elsewhere/wrong/0','candidate_output.bin')
    def test_valid_pair(self):
        shape, (a,b)=unpack_pair(self.a,self.b,self.am,self.bm)
        self.assertEqual(shape,[2,2,1,1]); self.assertEqual([x-y for x,y in zip(a,b)],[1,2,2,3])
    def test_unaligned(self):
        with self.assertRaisesRegex(ValueError,'unaligned'):
            unpack_pair(self.a,self.b[:-1],self.am,metadata(self.b[:-1]))
    def test_different_lengths(self):
        with self.assertRaisesRegex(ValueError,'lengths differ'):
            unpack_pair(self.a,self.b[:8],self.am,metadata(self.b[:8]))
    def test_different_shapes(self):
        with self.assertRaisesRegex(ValueError,'shapes or strides differ'):
            unpack_pair(self.a,self.b,self.am,metadata(self.b,ne='1,2,2,1'))
    def test_noncontiguous(self):
        with self.assertRaisesRegex(ValueError,'not complete contiguous'):
            unpack_pair(self.a,self.b,metadata(self.a,nb='4,12,24,24'),metadata(self.b,nb='4,12,24,24'))
    def test_digest_mismatch(self):
        with self.assertRaisesRegex(ValueError,'digest mismatch'):
            unpack_pair(self.a,self.b,self.am,dict(self.bm,sha256='0'*64))
    def test_nonfinite(self):
        b=struct.pack('<4f',0,float('nan'),1,1)
        with self.assertRaisesRegex(ValueError,'nonfinite'):
            unpack_pair(self.a,b,self.am,metadata(b))

if __name__=='__main__': unittest.main()
