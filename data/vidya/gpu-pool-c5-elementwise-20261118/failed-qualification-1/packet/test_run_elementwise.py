import importlib.util
import unittest
from pathlib import Path
P = Path(__file__).parent
spec = importlib.util.spec_from_file_location("producer", P / "run_elementwise.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
class PacketTests(unittest.TestCase):
    def test_exact_original_partition(self):
        plan = m.read_case_plan()
        self.assertEqual({k: len(v) for k, v in plan.items()}, {"NORM": 10, "SUM": 1, "SUM_ROWS": 6})
    def test_pins(self):
        m.pinned_inputs()
    def test_parser_preserves_statuses(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            op, selector, n, unsupported = m.CASES[0]
            names = list(m.read_case_plan()[op])
            path = out / (op + ".log")
            argv = m.argv_for(op, selector)
            import json
            lines = ["ARGV " + json.dumps(argv), "Backend 1/1: ROCm0", "  Device description: AMD Instinct MI210", f"  {op}({names[0]}): OK", f"  {op}({names[1]}): not supported [ROCm0]", f"  {op}({names[2]}): compare failed FAIL", "  1/2 tests passed", "  Backend ROCm0: FAIL"]
            path.write_text("\n".join(lines) + "\n")
            run = dict(op=op,argv=argv,log=str(path),log_sha256=m.sha(path),seed=m.SEED,generated_expected=n,status="native_exit_recorded",rc=1,observed=3,passed=1,unsupported=1,failed=[lines[5]])
            original = m.qualified
            try:
                m.qualified = lambda *args: {1, 2}
                result = m.check_run(out,run,op,selector,n,unsupported,{},m.read_case_plan()[op])
                self.assertEqual((result["passed"],result["unsupported"],result["failed"],len(result["missing"]),result["backend_status"]),(1,1,1,7,"FAIL"))
                path.write_text(path.read_text().replace("AMD Instinct MI210", "wrong device"))
                run["log_sha256"] = m.sha(path)
                with self.assertRaisesRegex(ValueError, "backend terminal identity"):
                    m.check_run(out,run,op,selector,n,unsupported,{},m.read_case_plan()[op])
            finally: m.qualified = original
if __name__ == "__main__": unittest.main()
