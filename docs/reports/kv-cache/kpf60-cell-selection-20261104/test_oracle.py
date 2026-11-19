import unittest
from oracle import Layer, MAX_U64, expected_bytes

class OracleTests(unittest.TestCase):
    def test_two_lengths_and_layer_breakdown(self):
        layers = [Layer(16, 8), Layer(32, None), Layer(8, 16)]
        self.assertEqual(expected_bytes(2, layers), ([(32, 16), (64, 0), (16, 32)], 112, 48))
        self.assertEqual(expected_bytes(5, layers), ([(80, 40), (160, 0), (40, 80)], 280, 120))
    def test_invalid(self):
        for cells, layers in [(0, [Layer(1, 1)]), (-1, [Layer(1, 1)]), (True, [Layer(1, 1)]), (1, []), (1, [Layer(0, 1)]), (1, [Layer(1, 0)]), (1, [Layer(1, True)])]:
            with self.subTest(cells=cells, layers=layers), self.assertRaises(ValueError):
                expected_bytes(cells, layers)
    def test_overflows(self):
        for cells, layers in [(2, [Layer(MAX_U64, None)]), (1, [Layer(MAX_U64, 1)]), (1, [Layer(MAX_U64, None), Layer(1, None)])]:
            with self.subTest(cells=cells, layers=layers), self.assertRaises(OverflowError):
                expected_bytes(cells, layers)
    def test_boundary(self):
        self.assertEqual(expected_bytes(1, [Layer(MAX_U64, None)])[1:], (MAX_U64, 0))

if __name__ == '__main__':
    unittest.main()
