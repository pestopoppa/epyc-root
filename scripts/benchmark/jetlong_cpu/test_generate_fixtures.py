import unittest
from generate_fixtures import assemble, coordinate

class GeometryTests(unittest.TestCase):
    def test_coordinates(self):
        keys = {(coordinate(d, n, s)['depth_fraction'], n, s) for d in (10, 30, 50, 70, 90) for n in range(5) for s in range(3)}
        self.assertEqual(len(keys), 75)
        self.assertIn((0.3, 4, 2), keys)
        with self.assertRaises(ValueError): coordinate(10, 5, 0)
    def test_geometry(self):
        for d in (10,30,50,70,90):
            ids,pos=assemble(list(range(17)),[101,102],[500,501],[600],1000,d,1701)
            self.assertEqual(len(ids),1000)
            self.assertEqual(pos,d*10)
            self.assertEqual(ids[pos:pos+2],[500,501])
    def test_reproducible_and_seeded(self):
        a=assemble(list(range(100)),[101],[500],[600],1000,50,1701)
        self.assertEqual(a,assemble(list(range(100)),[101],[500],[600],1000,50,1701))
        self.assertNotEqual(a,assemble(list(range(100)),[101],[500],[600],1000,50,1702))
    def test_reject_impossible(self):
        with self.assertRaises(ValueError): assemble([1],[1]*20,[2],[3],100,10,1)

if __name__=='__main__': unittest.main()
