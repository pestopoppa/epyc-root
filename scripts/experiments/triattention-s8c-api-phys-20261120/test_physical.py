"""Adversarial checks for the binary-state witness, independent synthetic data."""
import struct
import tempfile
from pathlib import Path
import unittest
from api_cases import read_state, compare


def fixture(positions):
    b=bytearray(struct.pack('<II',0x67677371,3)+struct.pack('<I',128)+b''.join(struct.pack('<i',i) for i in range(128)))
    b+=struct.pack('<II',1,len(positions))
    for pos in positions:
        b+=struct.pack('<iIi',pos,1,0)
    b+=struct.pack('<II',0,28)
    for kind in (0,1):
        for layer in range(28):
            b+=struct.pack('<iQ',1,2048)
            for pos in positions:
                b+=bytes([(pos+layer+kind)%256])*2048
    return bytes(b)

class PhysicalTests(unittest.TestCase):
    def parse(self, data):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state';p.write_bytes(data)
            return read_state(p)
    def test_real_layout_and_retained_tensor_bytes(self):
        before=self.parse(fixture(range(128)))
        after=self.parse(fixture(list(range(4))+list(range(80,128))))
        response={'n_evicted':76,'pos_max_after':127}
        self.assertTrue(all(compare(before,after,response).values()))
        after['rows']['K:27:127']='corrupt'
        self.assertFalse(compare(before,after,response)['retained_rows_identical'])
    def test_wrong_occupancy_and_recent_loss(self):
        b=self.parse(fixture(range(128)));a=self.parse(fixture(range(64)))
        checks=compare(b,a,{'n_evicted':60,'pos_max_after':127})
        self.assertFalse(checks['physical_eviction_count'])
        self.assertFalse(checks['recent16_preserved'])
        self.assertFalse(checks['response_max_matches'])
    def test_truncated_duplicate_and_wrong_version_rejected(self):
        data=fixture(range(128))
        for bad in [data[:-1],data+b'x',fixture([0,0]),data[:4]+struct.pack('<I',4)+data[8:]]:
            with self.assertRaises(ValueError):self.parse(bad)

if __name__=='__main__':unittest.main()
