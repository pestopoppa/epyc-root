import json, tempfile, unittest
from pathlib import Path
import mode_guard as g

class ModeGuardTests(unittest.TestCase):
    def test_qualification_cannot_enable_target(self):
        self.assertEqual(g.mode_check('qualification','1'), 'qualification')
        self.assertFalse(g.target_allowed('qualification'))
        for mode,flag in [('full','1'),('qualification','0'),('qualification',None),('bad','1')]:
            with self.assertRaises(RuntimeError): g.mode_check(mode,flag)
        self.assertEqual(g.mode_check('full','0'), 'full')
        self.assertTrue(g.target_allowed('full'))
    def test_exposure_guard_and_stop(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); self.assertFalse(g.exposure_seen(d)); (d/'hybrid.exposure.json').write_text('{}')
            self.assertTrue(g.exposure_seen(d))
            self.assertFalse(g.stopped(d/'stop',str(d/'engine-stop'),4,5))
            self.assertTrue(g.stopped(d/'stop',str(d/'engine-stop'),5,5))
            (d/'engine-stop').touch(); self.assertTrue(g.stopped(d/'stop',str(d/'engine-stop'),4,5))
    def test_append_produces_jsonl_units(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'events.jsonl';g.emit(p,{'kind':'qualification_control'});g.emit(p,{'kind':'target_terminal'})
            self.assertEqual([json.loads(x)['kind'] for x in p.read_text().splitlines()],['qualification_control','target_terminal'])

if __name__=='__main__':unittest.main()
