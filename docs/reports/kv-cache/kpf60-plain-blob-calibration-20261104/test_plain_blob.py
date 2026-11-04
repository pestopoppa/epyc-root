import struct
import unittest
from plain_blob import Layer, MAX_U64, parse_plain_f16

F16 = 1
LAYERS = (Layer(8, 4), Layer(4, None), Layer(2, 6))

def fixture(cells):
    # Independent construction from fixed F16 fixture geometry.
    blob = bytearray(struct.pack('<II', 0, 3))
    for role in ('K', 'V'):
        for layer in LAYERS:
            n = layer.k_row_bytes if role == 'K' else layer.v_row_bytes
            if n is not None:
                blob += struct.pack('<IQ', F16, n)
                blob += bytes([len(blob) % 251]) * (cells * n)
    return bytes(blob)

class ParseTests(unittest.TestCase):
    def test_two_lengths_and_layer_subtotals(self):
        for cells in (1, 7):
            b = fixture(cells); r = parse_plain_f16(b, cells, LAYERS, F16)
            self.assertEqual((r['k_bytes'], r['v_bytes'], r['metadata_bytes']), (14*cells, 10*cells, 68))
            self.assertEqual(r['total_bytes'], len(b))
            self.assertEqual([(p['layer'],p['role'],p['length']) for p in r['payloads']], [(0,'K',8*cells),(1,'K',4*cells),(2,'K',2*cells),(0,'V',4*cells),(2,'V',6*cells)])
    def test_corrupted_headers_and_truncation(self):
        b = fixture(2)
        for mutant in (struct.pack('<I',1)+b[4:], b[:4]+struct.pack('<I',4)+b[8:], b[:8]+struct.pack('<I',2)+b[12:], b[:12]+struct.pack('<Q',10)+b[20:], b[:-1], b+b'x'):
            with self.assertRaises(ValueError): parse_plain_f16(mutant,2,LAYERS,F16)
    def test_invalid_geometry_and_overflow(self):
        for n, layers in ((0, LAYERS),(MAX_U64,LAYERS),(1,(Layer(3,4),)),(1,(Layer(None,4),)),(1,())):
            with self.assertRaises(ValueError): parse_plain_f16(b'',n,layers,F16)

if __name__ == '__main__': unittest.main()
