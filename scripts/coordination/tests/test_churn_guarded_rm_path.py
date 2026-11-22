"""guarded_rm.sh resolution when worktree_salvage/worktree_gate run from the INSTALLED layout (compute-flags/bin/churn),
where a __file__-relative repo root has no scripts/safety (RECLAIM-ERROR ... guarded_rm.sh: No such file)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SYS = os.path.join(REPO, "scripts", "system")
sys.path.insert(0, SYS)
import worktree_gate as wg  # noqa: E402

REL = "scripts/safety/guarded_rm.sh"


class ResolveTest(unittest.TestCase):
    def test_order(self):
        here = "/x/flags/bin/churn"
        have = lambda *ps: (lambda p: p in ps)
        self.assertEqual(wg.resolve_guarded_rm(here, {"GUARDED_RM": "/e/g.sh"}, have("/e/g.sh", f"/workspace/{REL}")), "/e/g.sh")
        self.assertEqual(wg.resolve_guarded_rm("/r/scripts/system", {}, have(f"/r/{REL}", f"/workspace/{REL}")), f"/r/{REL}")
        v = f"/mnt/raid0/llm/views/epyc-root-main/{REL}"
        self.assertEqual(wg.resolve_guarded_rm(here, {}, have(v, f"/workspace/{REL}")), v)
        self.assertEqual(wg.resolve_guarded_rm(here, {}, have(f"/workspace/{REL}")), f"/workspace/{REL}")
        self.assertIsNone(wg.resolve_guarded_rm(here, {}, have()))
        # a stale GUARDED_RM that does not exist falls through
        self.assertEqual(wg.resolve_guarded_rm(here, {"GUARDED_RM": "/nope"}, have(f"/workspace/{REL}")), f"/workspace/{REL}")


class InstalledLayoutTest(unittest.TestCase):
    def test_salvage_resolves_guarded_rm_from_installed_copy(self):
        with tempfile.TemporaryDirectory() as d:
            inst = os.path.join(d, "compute-flags", "bin", "churn")
            os.makedirs(inst)
            for m in ("worktree_gate.py", "worktree_salvage.py", "scratch_lease.py"):
                shutil.copy(os.path.join(SYS, m), inst)
            fake = os.path.join(d, "g.sh")
            open(fake, "w").write("#!/bin/bash\n")
            code = "import worktree_salvage as s; print(s.GUARDED_RM)"
            env = dict(os.environ, GUARDED_RM=fake)
            out = subprocess.run([sys.executable, "-c", code], cwd=inst, env=env, capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), fake, out.stderr)
            # without the env var: never the compute-flags-relative path
            env.pop("GUARDED_RM")
            out = subprocess.run([sys.executable, "-c", code], cwd=inst, env=env, capture_output=True, text=True)
            self.assertNotIn(os.path.join(d, "compute-flags", "scripts"), out.stdout, out.stderr)
            self.assertTrue(out.stdout.strip().endswith(REL), out.stderr)


if __name__ == "__main__":
    unittest.main()
