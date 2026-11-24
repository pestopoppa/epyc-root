"""REAP-DEFER-QUIET (pipeline-mgmt 2026-11-24): while a quiet-sensitive row holds a grant the reap pass defers its heavy work
(vault copies, deletes, du scans). The predicate is extracted from the keeper heredoc's REAP-RULES block."""
import os
import tempfile
import unittest

import test_keeper_reap_rules_20261123 as rules

H = rules.H


class QuietHolders(unittest.TestCase):
    def setUp(self):
        self.g = tempfile.mkdtemp()

    def grant(self, rid, body="regions=0-23 holds=q0\n", term=None):
        open(os.path.join(self.g, rid + ".grant"), "w").write(body)
        if term:
            open(os.path.join(self.g, rid + term), "w").write("")

    def test_declared_manifest_holds(self):
        self.grant("c20-fold-cpu-r4")
        self.grant("plain-row")
        mans = {"c20-fold-cpu-r4": ({"requires_quiet_host": True}, "p"), "plain-row": ({"lane": "cpu"}, "p")}
        self.assertEqual(H.quiet_holders(self.g, mans), ["c20-fold-cpu-r4"])

    def test_quiet_guard_regions_and_grant_text(self):
        self.grant("a")
        self.grant("b", "regions=0-23 requires_quiet_host=1\n")
        mans = {"a": ({"quiet_guard_regions": ["q2"]}, "p")}
        self.assertEqual(H.quiet_holders(self.g, mans), ["a", "b"])

    def test_ended_or_complete_grant_is_not_running(self):
        self.grant("a", term=".ended")
        self.grant("b", term=".complete")
        mans = {"a": ({"requires_quiet_host": True}, "p"), "b": ({"requires_quiet_host": True}, "p")}
        self.assertEqual(H.quiet_holders(self.g, mans), [])

    def test_rowflow_predicate_used_and_fails_closed(self):
        self.grant("a")
        self.grant("b")
        mans = {"a": ({"x": 1}, "p"), "b": ({"y": 1}, "p")}
        self.assertEqual(H.quiet_holders(self.g, mans, lambda m: "x" in m), ["a"])
        def boom(m):
            raise RuntimeError("bad")
        self.assertEqual(H.quiet_holders(self.g, mans, boom), ["a", "b"])

    def test_no_manifest_no_token_is_not_quiet(self):
        self.grant("gpu-row", "regions=mi210_0,88-95 holds=gpu-quiet\n")
        self.assertEqual(H.quiet_holders(self.g, {}), [])

    def test_real_rowflow_quiet_sensitive(self):
        import importlib.util
        rf = os.path.join(rules.HERE, "..", "rowflow", "rowflow.py")
        sp = importlib.util.spec_from_file_location("rowflow_q_test", rf)
        m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        self.grant("q"); self.grant("n")
        mans = {"q": ({"quiet_sensitive": True}, "p"), "n": ({"lane": "gpu"}, "p")}
        self.assertEqual(H.quiet_holders(self.g, mans, m.quiet_sensitive), ["q"])


class HeavyWorkGated(unittest.TestCase):
    def test_every_heavy_site_checks_quiet(self):
        src = open(rules.KEEPER).read()
        for needle in ("    if quiet_defer(): return False, 'deferred",            # vault copies
                       "    if quiet_defer(): out('DEFERRED', tag",                  # really_delete
                       "    if not PRESSURE or quiet_defer(): return (0, name)",     # du-scan sort
                       "  if quiet_defer(): break",                                  # group pass
                       "        if quiet_defer(): break",                            # idle + worktree pass
                       "and os.path.isdir(TRASH) and not quiet_defer():"):           # trash sweep
            self.assertIn(needle, src)
        self.assertIn("'DEFER-QUIET'", src.split("ALWAYS = ", 1)[1].split("\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
