#!/usr/bin/env python3
import datetime as dt, importlib.util, json, pathlib, tempfile, unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('keeper_qual_gate',BASE/'keeper_qual_gate.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
class Breaker(unittest.TestCase):
 def test_owner_only_three_failures_and_fresh_qual_releases(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   f=pathlib.Path(td);(f/'grants').mkdir();(f/'ready').mkdir();(f/'ws58-keeper-state').mkdir()
   rows=[]
   for name,owner in [('a','ni'),('b','ni'),('c','ni'),('d','codex3')]:
    cells=[name,owner]+['x']*16;rows.append('| '+' | '.join(cells)+' |')
    (f/'grants'/(name+'.ended')).write_text('rc=1 time=2026-11-01T00:00:00Z reason=native\n')
   (f/'FILLERS.md').write_text('\n'.join(rows)+'\n')
   (f/'ready/ni-row.json').write_text(json.dumps({'id':'ni-row','owner':'ni','schema':'epyc.ready.v2','hold':None}))
   (f/'ready/c3-row.json').write_text(json.dumps({'id':'c3-row','owner':'codex3','schema':'epyc.ready.v2','hold':None}))
   actions=g.reconcile_failures(f)
   self.assertIn('worker-breaker ni',actions)
   self.assertTrue(json.loads((f/'ws58-keeper-state/qual-failure-breakers.json').read_text())['owners']['ni']['active'])
   self.assertIsNone(json.loads((f/'ready/ni-row.json').read_text())['hold'])
   self.assertIsNone(json.loads((f/'ready/c3-row.json').read_text())['hold'])
   old=g.q.verify
   g.q.verify=lambda *_args,**_kw:{'ran_at':(dt.datetime.now(dt.timezone.utc)+dt.timedelta(seconds=2)).isoformat()}
   try:
    actions=g.reconcile_failures(f)
    self.assertTrue(any(x.startswith('worker-breaker-released ni') for x in actions))
    self.assertFalse(json.loads((f/'ws58-keeper-state/qual-failure-breakers.json').read_text())['owners']['ni']['active'])
    self.assertIsNone(json.loads((f/'ready/ni-row.json').read_text())['hold'])
   finally:g.q.verify=old
if __name__=='__main__':unittest.main()
