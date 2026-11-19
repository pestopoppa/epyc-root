import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('probe', Path(__file__).parents[1] / 'scripts/harness/hs_td3_probe.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ContextSelectionTests(unittest.TestCase):
    def test_closed_set_and_confidence(self):
        for value in ({'ids':['x'], 'confidence':.5}, {'ids':['a','a'], 'confidence':.5},
                      {'ids':[], 'confidence':.5}, {'ids':['a'], 'confidence':True},
                      {'ids':['a'], 'confidence':float('nan')}, {'ids':['a'], 'confidence':2}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.selection(value, {'a':'body'})

    def test_assembly_canonical_and_verbatim(self):
        c = {'z':'original z', 'a':'original a'}
        self.assertEqual(p.assemble(c, ['z','a']), p.assemble(c, ['a','z']))
        self.assertEqual(list(p.assemble(c, ['z','a'])), ['a','z'])
        self.assertEqual(p.assemble(c, ['z']), {'z':'original z'})

    def test_unknown_and_smoke_denominators(self):
        r = p.summarize([{'phase':'smoke'}, {'phase':'full','arm':'typed','case_id':'x',
                           'status':'unknown','elapsed_s':1}], 6)
        self.assertFalse(r['complete'])
        self.assertEqual(r['typed']['unknown'], 2)
        self.assertEqual(r['baseline']['unknown'], 2)
        self.assertEqual(r['paired_valid'], 0)

    def test_paired_scores(self):
        rows = [{'phase':'full','arm':arm,'case_id':'x','status':'ok','elapsed_s':1,
                 'correct': arm == 'typed'} for arm in ('baseline','typed')]
        r = p.summarize(rows, 3)
        self.assertEqual((r['typed_wins'],r['baseline_wins'],r['paired_valid']), (1,0,1))

    def test_wire_strictness(self):
        for content,finish in [('{"value":true}','stop'),('{"value":1,"value":2}','stop'),('{"value":1}','length')]:
            with self.subTest(content=content), self.assertRaises(ValueError):
                p.answer(p.payload({'choices':[{'finish_reason':finish,'message':{'content':content}}]}))

    def test_frozen_references_and_baseline(self):
        cases=json.loads((Path(__file__).parents[1]/'scripts/harness/hs_td3_cases.json').read_text())
        self.assertEqual(len(cases),12)
        for c in cases:
            self.assertEqual(c['baseline'],c['candidates'])
            routing=json.loads(c['candidates']['routing.json'])
            active=routing['active_profile']+'.json'
            self.assertEqual(c['gold_ids'],sorted(['routing.json',active]))
            self.assertIn(c['reference_value'], json.loads(c['candidates'][active]).values())


if __name__ == '__main__':
    unittest.main()
