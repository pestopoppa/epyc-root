import subprocess
import sys
import unittest
from pathlib import Path


class NestedContainmentTest(unittest.TestCase):
    def test_requested_stop_reaps_nested_adopted_child(self):
        path=Path(__file__).with_name('nested_fixture.py')
        result=subprocess.run([sys.executable,'-B',str(path)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('nested adopted and reaped; interrupted outcome',result.stdout)


if __name__=='__main__':unittest.main()
