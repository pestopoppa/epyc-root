import copy
import hashlib
import json
from pathlib import Path
import unittest
from binding import InvalidPlan, invoke_bound

GUARD = (Path(__file__).resolve().parent.parent / 'kpf174-oracle-preflight-20261105' / 'preflight.py').read_bytes()
digest = lambda b: hashlib.sha256(b).hexdigest()

class BindingTest(unittest.TestCase):
    def setUp(self):
        self.plan = {'schema': 'kpf174-plan/v1', 'role': 'mut_partial_noop', 'length': 14336,
                     'swa_cells': 8704, 'cells': [{'id': 'g1-c2148', 'group': 1, 'c': 2148}]}
        self.cells = {'g1-c2148': {'group': 1, 'c': 2148, 'pruned': True, 'controls': [{}, {}, {}],
                                    'arms': [{'fork_src_slot': 0}, {'fork_src_slot': 0}]}}
        self.calls = []
    def run_case(self, plan=None, cells=None, guard=GUARD, guard_pin=None, plan_pin=None):
        payload = json.dumps(self.plan if plan is None else plan).encode()
        return invoke_bound(payload, digest(payload) if plan_pin is None else plan_pin,
                            guard, digest(GUARD) if guard_pin is None else guard_pin,
                            self.cells if cells is None else cells, lambda x: self.calls.append(x) or 'called')
    def test_success_calls_once_with_copy(self):
        self.assertEqual(self.run_case(), 'called')
        self.assertEqual(len(self.calls), 1)
        self.calls[0]['g1-c2148']['c'] = 1
        self.assertEqual(self.cells['g1-c2148']['c'], 2148)
    def test_digest_refusal(self):
        for kw in ({'plan_pin': '0'*64}, {'guard': GUARD+b'\n'}):
            with self.assertRaises(InvalidPlan): self.run_case(**kw)
        self.assertFalse(self.calls)
    def test_bad_inputs_refuse_before_judge(self):
        for mutation in ('missing', 'geometry', 'source', 'pruned', 'arms'):
            cells = copy.deepcopy(self.cells)
            if mutation == 'missing': cells.clear()
            if mutation == 'geometry': cells['g1-c2148']['group'] = 2
            if mutation == 'source': cells['g1-c2148']['arms'][1]['fork_src_slot'] = None
            if mutation == 'pruned': cells['g1-c2148']['pruned'] = False
            if mutation == 'arms': cells['g1-c2148']['arms'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(InvalidPlan): self.run_case(cells=cells)
        self.assertFalse(self.calls)
    def test_bad_plan_refusal(self):
        for change in ('empty', 'duplicate_id', 'duplicate_geometry', 'bad_role', 'bool_group'):
            plan = copy.deepcopy(self.plan)
            if change == 'empty': plan['cells'] = []
            if change == 'duplicate_id': plan['cells'].append(copy.deepcopy(plan['cells'][0]))
            if change == 'duplicate_geometry': plan['cells'].append({'id': 'another', 'group': 1, 'c': 2148})
            if change == 'bad_role': plan['role'] = 'other'
            if change == 'bool_group': plan['cells'][0]['group'] = True
            with self.subTest(change=change), self.assertRaises(InvalidPlan): self.run_case(plan=plan)
        self.assertFalse(self.calls)
    def test_duplicate_json_key_refused(self):
        payload = b'{"schema":"kpf174-plan/v1","schema":"kpf174-plan/v1"}'
        with self.assertRaises(InvalidPlan):
            invoke_bound(payload, digest(payload), GUARD, digest(GUARD), self.cells, lambda x: self.calls.append(x))
        self.assertFalse(self.calls)

if __name__ == '__main__': unittest.main()
