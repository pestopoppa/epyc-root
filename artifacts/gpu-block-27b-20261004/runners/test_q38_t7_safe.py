"""No-inference checks for the Q38-T7 successor entry point."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest import mock

PATH = Path(__file__).with_name("q38_t7_safe.py")
spec = importlib.util.spec_from_file_location("q38_t7_safe", PATH)
safe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(safe)


class SafeEntryTest(unittest.TestCase):
    def test_ab_refused_before_original_import(self):
        for opts in ([], ["--phases", "A"], ["--phases=B,C"],
                     ["--ph", "a,c"], ["--phases", "C", "--phases", "B"]):
            with self.subTest(opts=opts), mock.patch.object(sys, "argv", [str(PATH), *opts]), \
                    mock.patch.object(safe.importlib, "import_module") as importer, \
                    self.assertRaises(SystemExit):
                safe.main()
            importer.assert_not_called()

    def test_phase_c_dispatch_installs_direct_call_guards(self):
        original = types.SimpleNamespace(main=mock.Mock(return_value=17))
        with mock.patch.object(sys, "argv", [str(PATH), "--phases", "C"]), \
                mock.patch.object(safe.importlib, "import_module", return_value=original):
            self.assertEqual(safe.main(), 17)
        original.main.assert_called_once_with()
        for phase in (original.phase_a, original.phase_b):
            with self.assertRaisesRegex(RuntimeError, "KVU-16h"):
                phase(None)

    def test_real_cli_refuses_before_original_preflight(self):
        result = subprocess.run([sys.executable, str(PATH), "--dry-run", "--phases", "A,B,C"],
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("KVU-16h", result.stderr)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
