import hashlib
import struct
import unittest
from inspect_abi import SITES, inspect, Invalid


def make_image():
    # Synthetic ELF with one executable LOAD covering all sampled addresses.
    blob = bytearray(0x11000)
    blob[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', blob, 18, 62)
    struct.pack_into('<Q', blob, 32, 64)
    struct.pack_into('<HH', blob, 54, 56, 1)
    struct.pack_into('<IIQQQQQQ', blob, 64, 1, 5, 0x1000, 0x150000, 0, 0x10000, 0x10000, 4096)
    for va, sig in SITES.items():
        off = 0x1000 + va - 0x150000
        b = bytes.fromhex(sig); blob[off:off+len(b)] = b
    return blob

def digest(b): return hashlib.sha256(b).hexdigest()

class Tests(unittest.TestCase):
    def test_accept_exact_fixture(self):
        b = make_image(); self.assertEqual(inspect(b, digest(b))['checked_sites'], len(SITES))
    def test_image_digest_mismatch(self):
        b = make_image(); b[-1] = 1
        with self.assertRaises(Invalid): inspect(b)
    def test_each_sampled_opcode_is_checked(self):
        for va in SITES:
            b = make_image(); b[0x1000+va-0x150000] ^= 1
            with self.subTest(site=hex(va)), self.assertRaises(Invalid): inspect(b, digest(b))
    def test_nonexecutable_and_wrong_arch_refused(self):
        for off, fmt, value in [(68, '<I', 4), (18, '<H', 183), (54, '<H', 8)]:
            b = make_image(); struct.pack_into(fmt,b,off,value)
            with self.subTest(offset=off), self.assertRaises(Invalid): inspect(b, digest(b))
    def test_duplicate_loads_refused(self):
        b = make_image(); struct.pack_into('<H', b, 56, 2); b[120:176] = b[64:120]
        with self.assertRaises(Invalid): inspect(b, digest(b))
    def test_truncated_and_nonsense_refused(self):
        for b in [b'', b'not an elf', bytes(64)]:
            with self.subTest(length=len(b)), self.assertRaises(Invalid): inspect(b, digest(b))

if __name__ == '__main__': unittest.main()
