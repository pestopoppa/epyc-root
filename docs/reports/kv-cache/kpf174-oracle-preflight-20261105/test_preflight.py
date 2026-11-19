import copy
import unittest
from preflight import validate_launch


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.cells = {'g1-c2148': {'c': 2148, 'pruned': True,
                      'controls': [{}, {}, {}],
                      'arms': [{'fork_src_slot': 0}, {'fork_src_slot': 0}]}}
        self.ids = ['g1-c2148']

    def check(self, cells=None, ids=None):
        return validate_launch(self.cells if cells is None else cells,
                               self.ids if ids is None else ids,
                               length=14336, swa_cells=8704, mutant_partial=True)

    def test_complete_shape(self):
        self.assertEqual(self.check(), [])

    def test_missing_or_extra_cell(self):
        self.assertTrue(self.check(ids=['g1-c2148', 'g1-c4096']))
        self.assertTrue(self.check(ids=[]))
        self.assertTrue(self.check(ids=['g1-c2148', 'g1-c2148']))

    def test_empty_and_malformed_plan_fails_closed(self):
        for ids in ([], [None], [''], [['unhashable']], [{'bad': 'id'}]):
            self.assertTrue(self.check(cells={}, ids=ids), ids)

    def test_one_arm_or_unknown_source(self):
        for arms in ([{'fork_src_slot': 0}],
                     [{'fork_src_slot': 0}, {'fork_src_slot': None}],
                     [{'fork_src_slot': 0}, {'fork_src_slot': False}]):
            cells = copy.deepcopy(self.cells)
            cells['g1-c2148']['arms'] = arms
            self.assertTrue(self.check(cells), arms)

    def test_scope_must_follow_geometry(self):
        for value in (None, False, 1):
            cells = copy.deepcopy(self.cells)
            cells['g1-c2148']['pruned'] = value
            self.assertTrue(self.check(cells), value)

    def test_missing_controls(self):
        cells = copy.deepcopy(self.cells)
        cells['g1-c2148']['controls'].pop()
        self.assertTrue(self.check(cells))

    def test_invalid_geometry(self):
        self.assertTrue(validate_launch(self.cells, self.ids, length=0, swa_cells=8704))


if __name__ == '__main__':
    unittest.main()
