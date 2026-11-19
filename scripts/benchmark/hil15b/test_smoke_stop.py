import os
from pathlib import Path
import tempfile
import types
import unittest

from repair_smoke_stop import NEW, OLD, repair_source


class StopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("HIL15B_CONTROLLER_SOURCE")
        if not path:
            raise unittest.SkipTest("set HIL15B_CONTROLLER_SOURCE for native controller regressions")
        source = Path(path).read_text().replace(NEW, OLD, 1)
        cls.module = types.ModuleType("controller_under_test")
        exec(compile(repair_source(source), path, "exec"), cls.module.__dict__)

    def test_explicit_stop_preserves_attempt_and_resume_refuses_redraw(self):
        with tempfile.TemporaryDirectory() as tmp:
            stopped = [False]
            controller = self.module.Controller(Path(tmp), "unit-18", "fixed-plan")
            def runner(attempt, slot, deadline, stop):
                (attempt / "exposed").write_text("retained")
                stopped[0] = True
                return "censored"
            kwargs = dict(deadline=10**12, load_margin=0, cleanup_margin=0,
                          stop=lambda: stopped[0], preflight=lambda i: None, runner=runner,
                          validate=lambda a, i: None, assess=lambda unit, slots: None)
            try:
                result = controller.run(**kwargs)
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["completed_slots"], 0)
                exposed = controller.unit / result["exposed_attempt"]
                self.assertEqual((exposed / "exposed").read_text(), "retained")
                stopped[0] = False
                with self.assertRaisesRegex(self.module.Refusal, "incomplete attempt"):
                    controller.run(**kwargs)
                self.assertEqual(len(list((controller.unit / "slot-0").iterdir())), 1)
            finally:
                controller.close()

    def test_censored_without_stop_and_unknown_status_still_refuse(self):
        for status, stopped in [("censored", False), ("interrupted", True)]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                active = [False]
                controller = self.module.Controller(Path(tmp), "unit-18", "fixed-plan")
                def runner(*args):
                    active[0] = stopped
                    return status
                try:
                    with self.assertRaisesRegex(self.module.Refusal, "incomplete attempt"):
                        controller.run(deadline=10**12, load_margin=0, cleanup_margin=0,
                                       stop=lambda: active[0], preflight=lambda i: None, runner=runner,
                                       validate=lambda a, i: None, assess=lambda unit, slots: None)
                finally:
                    controller.close()


if __name__ == "__main__":
    unittest.main()
