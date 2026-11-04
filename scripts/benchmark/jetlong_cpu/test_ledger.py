import json
import tempfile
import unittest
from pathlib import Path
import ledger

class LedgerTests(unittest.TestCase):
    def test_resume_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            plan_file = Path(d)/'plan.json'
            plan_file.write_text(json.dumps({'items':[{'id':'x','expected':'answer','length':300000}]}))
            run=Path(d)/'run'; plan, pin = ledger.initialize(run, plan_file)
            ledger.start(run, plan, pin, 'x', 'J')
            self.assertEqual(ledger.inventory(run, plan, pin)['unknown'], [('x','J')])
            with self.assertRaises(FileExistsError): ledger.start(run, plan, pin, 'x', 'J')
            ledger.finish(run, pin, 'x', 'J', 'timeout')
            self.assertEqual(ledger.inventory(run, plan, pin)['finished'], [('x','J')])
            with self.assertRaises(FileExistsError): ledger.finish(run, pin, 'x', 'J', 'timeout')
            plan_file.write_text(plan_file.read_text()+' ')
            with self.assertRaises(ValueError): ledger.initialize(run, plan_file)
    def test_invalid_reference_and_unstarted_finish(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'p'; p.write_text(json.dumps({'items':[{'id':'x','expected':'','length':300000}]}))
            with self.assertRaises(ValueError): ledger.initialize(Path(d)/'run', p)
            with self.assertRaises(FileNotFoundError): ledger.finish(d,'sha','x','Y','timeout')

if __name__ == '__main__': unittest.main()
