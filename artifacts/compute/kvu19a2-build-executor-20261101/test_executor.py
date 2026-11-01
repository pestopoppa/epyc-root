import importlib.util
import unittest
from pathlib import Path
p = Path(__file__).with_name('executor.py')
spec = importlib.util.spec_from_file_location('executor', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Journal:
    def __init__(self): self.events = []
    def start(self, i, digest): self.events.append(('start', i, digest))
    def end(self, i, rc, cleanup): self.events.append(('end', i, rc, cleanup))
    def complete(self, verified): self.events.append(('complete', verified))

class Supervisor:
    def __init__(self, result=(0, True)): self.result, self.calls = result, []
    def run(self, argv):
        self.calls.append(argv)
        if isinstance(self.result, BaseException): raise self.result
        return self.result

class Tests(unittest.TestCase):
    def setUp(self):
        self.plan = {'mode': 'qualification', 'commands': [['/cmake', '-S', '/src'], ['/cmake', '--build', '/out']]}
        self.j = Journal()
    def run_case(self, sup, check=lambda mode: True, out=lambda mode: True, stop=lambda: False):
        return m.execute(self.plan, self.j, sup, check, out, stop)
    def test_complete_in_order(self):
        sup = Supervisor()
        self.assertTrue(self.run_case(sup))
        self.assertEqual([x[0] for x in self.j.events], ['start','end','start','end','complete'])
        self.assertEqual(len(sup.calls), 2)
    def test_failed_or_unverified_cleanup_stops(self):
        for receipt in ((0, False), (1, True), (0, None)):
            self.j = Journal(); sup = Supervisor(receipt)
            with self.assertRaises(m.Incomplete): self.run_case(sup)
            self.assertEqual(len(sup.calls), 1)
            self.assertNotIn('complete', [x[0] for x in self.j.events])
    def test_exception_and_unverified_inputs_fail_closed(self):
        sup = Supervisor(RuntimeError('failed'))
        with self.assertRaises(m.Incomplete): self.run_case(sup)
        self.assertEqual(len(sup.calls), 1)
        self.assertNotIn('complete', [x[0] for x in self.j.events])
        self.j = Journal(); sup = Supervisor()
        with self.assertRaises(m.Incomplete): self.run_case(sup, check=lambda mode: False)
        self.assertEqual(sup.calls, [])
    def test_stop_and_output_verification(self):
        sup = Supervisor()
        with self.assertRaises(m.Incomplete): self.run_case(sup, stop=lambda: True)
        self.assertEqual(sup.calls, [])
        with self.assertRaises(m.Incomplete): self.run_case(sup, out=lambda mode: False)
        self.assertNotIn('complete', [x[0] for x in self.j.events])
    def test_malformed_command_refused_before_start(self):
        self.plan['commands'] = [['/cmd'], ['bad\x00arg']]
        sup = Supervisor()
        with self.assertRaises(ValueError): self.run_case(sup)
        self.assertEqual(sup.calls, [])

    def test_mode_mutation_during_command_fails_closed(self):
        plan = self.plan
        class MutatingSupervisor(Supervisor):
            def run(self, argv):
                self.calls.append(argv)
                plan['mode'] = 'target'
                return (0, True)
        sup = MutatingSupervisor()
        seen_outputs = []
        with self.assertRaisesRegex(m.Incomplete, 'mode changed'):
            self.run_case(sup, out=lambda mode: seen_outputs.append(mode) or True)
        self.assertEqual(len(sup.calls), 1)
        self.assertEqual(seen_outputs, [])
        self.assertNotIn('complete', [x[0] for x in self.j.events])

    def test_mode_mutation_inside_verifier_refused(self):
        def mutate(mode):
            self.assertEqual(mode, 'qualification')
            self.plan['mode'] = 'target'
            return True
        sup = Supervisor()
        with self.assertRaisesRegex(m.Incomplete, 'mode changed'):
            self.run_case(sup, check=mutate)
        self.assertEqual(sup.calls, [])
        self.assertNotIn('complete', [x[0] for x in self.j.events])

if __name__ == '__main__': unittest.main()
