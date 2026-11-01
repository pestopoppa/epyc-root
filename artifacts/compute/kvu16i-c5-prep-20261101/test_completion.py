from pathlib import Path
import json
import tempfile
import unittest
from completion import complete
class CompletionTests(unittest.TestCase):
    def test_only_expected_native_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'terminal';self.assertFalse(complete('full',p))
            for verdict in ('UNKNOWN','CONTROL_COMPLETE','FAILS','HOLDS'):
                p.write_text(json.dumps({'schema':'kvu16i.c5.complete.v1','mode':'full','verdict':verdict}))
                self.assertEqual(complete('full',p),verdict in ('FAILS','HOLDS'))
            self.assertFalse(complete('qualification',p))
            p.write_text(json.dumps({'schema':'kvu16i.c5.complete.v1','mode':'qualification','verdict':'CONTROL_COMPLETE'}))
            self.assertTrue(complete('qualification',p))
if __name__=='__main__':unittest.main()
