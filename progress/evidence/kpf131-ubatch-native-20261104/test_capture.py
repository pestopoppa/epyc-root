import os
import struct
import tempfile
import unittest
from probe_native import capture

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.TemporaryFile(); self.addCleanup(self.f.close)
        b = bytearray(256); struct.pack_into('<I', b, 0x10, 3); struct.pack_into('<Q', b, 0x40, 128); struct.pack_into('<iii', b, 128, 11, 22, 33)
        self.f.write(b); self.f.flush()
    def test_exact(self): self.assertEqual(capture(self.f.fileno(), 0, 128), (3,[11,22,33]))
    def test_out_of_bounds_counts_refuse(self):
        for count in [0,4,0xffffffff]:
            os.pwrite(self.f.fileno(),struct.pack('<I',count),0x10)
            with self.subTest(count=count), self.assertRaises(ValueError): capture(self.f.fileno(),0,128)
    def test_wrong_pointer_refuses(self):
        os.pwrite(self.f.fileno(),struct.pack('<Q',136),0x40)
        with self.assertRaises(ValueError): capture(self.f.fileno(),0,128)
    def test_short_read_refuses(self):
        os.ftruncate(self.f.fileno(), 130)
        with self.assertRaises(ValueError): capture(self.f.fileno(),0,128)

if __name__ == '__main__': unittest.main()
