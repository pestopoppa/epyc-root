"""sq3fix 2026-11-05: kpf17/kpf41 -sq3 packets sealed the live filler_run15.sh digest; a routine engine redeploy while
their grants waited made both jobs assert at start (rc=1, empty out/). publish refuses a packet that pins the engine."""
import hashlib
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402


class EngineSeal(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.eng = os.path.join(self.t.name, "filler_run15.sh")
        with open(self.eng, "w") as f:
            f.write("#!/bin/bash\necho engine\n")
        self.job = os.path.join(self.t.name, "job")
        os.makedirs(self.job)
        self.launcher = os.path.join(self.job, "launch.sh")
        with open(self.launcher, "w") as f:
            f.write(f"exec bash {self.eng} --id x\n")
        with open(os.path.join(self.job, "job.py"), "w") as f:
            f.write("print('ok')\n")

    def tearDown(self):
        self.t.cleanup()

    def test_clean_packet_passes(self):
        rf.check_engine_not_sealed(self.launcher, self.eng)

    def test_sealed_engine_digest_refused(self):
        d = hashlib.sha256(open(self.eng, "rb").read()).hexdigest()
        with open(os.path.join(self.job, "seals.sha256"), "w") as f:
            f.write(f"{d}  {self.eng}\n")
        with self.assertRaises(rf.Refused):
            rf.check_engine_not_sealed(self.launcher, self.eng)

    def test_nested_runtime_json_refused(self):
        d = hashlib.sha256(open(self.eng, "rb").read()).hexdigest()
        os.makedirs(os.path.join(self.job, "meta"))
        with open(os.path.join(self.job, "meta", "runtime.json"), "w") as f:
            f.write('{"external_files": {"rowflow": {"sha256": "%s"}}}' % d)
        with self.assertRaises(rf.Refused):
            rf.check_engine_not_sealed(self.launcher, self.eng)


if __name__ == "__main__":
    unittest.main()
