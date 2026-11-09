"""SCRATCH-LEASE-P3 coverage pin: which KEEP-marker consumers under scripts/ honour scratch leases.

A lease only bounds a KEEP marker's veto (scripts/system/scratch_lease.py: marker_blocks); it deletes nothing, so no
reaper is retired by it. This test pins the inventory so "retire old reapers once leases cover all scratch roots"
can be decided from a list instead of memory: a NEW lease-blind KEEP-marker consumer fails here until it is made
lease-aware or added (with a reason) to LEASE_BLIND. Read-only; scans source text only.
"""
import os
import re
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER_RE = re.compile(r"epyc-keep|KEEP_MARKERS|epyc-load-bearing")
AWARE_RE = re.compile(r"scratch_lease|marker_blocks")

# Consumers that read KEEP markers but never ask the lease (so their marker veto is still permanent), with why.
LEASE_BLIND = {
    "scripts/system/kernel_store_gc.py": "kernels/builds/* (not under tmp/; leases only exist for tmp/ top-level entries)",
    "scripts/system/worktree_salvage.py": "salvage-retire refusal for any registered worktree; no lease lookup",
    "scripts/coordination/churn/reclaim_row.py": "row scratch at filing; KEEP at any depth honoured forever",
    "scripts/coordination/rowflow/ws58-calendar-keeper-v11.sh": "inert history keeper (runbook: runs only if .current names it)",
}
# Consumers that do consult the lease (the lease-aware set).
LEASE_AWARE = {
    "scripts/system/scratch_lease.py",
    "scripts/system/scratch_cleanup.py",
    "scripts/system/worktree_gate.py",
    "scripts/coordination/rowflow/ws58-calendar-keeper-v12.sh",
    "scripts/coordination/rowflow/ws58-calendar-keeper-v13.sh",
}


def scan(root):
    """(aware, blind) sets of repo-relative paths under root/scripts that reference KEEP markers."""
    aware, blind = set(), set()
    for dp, dn, fn in os.walk(os.path.join(root, "scripts")):
        dn[:] = [d for d in dn if d not in ("__pycache__", "tests")]
        for f in fn:
            p = os.path.join(dp, f)
            try:
                text = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            if MARKER_RE.search(text):
                (aware if AWARE_RE.search(text) else blind).add(os.path.relpath(p, root))
    return aware, blind


class LeaseCoverage(unittest.TestCase):
    def test_inventory_is_exactly_the_pinned_lists(self):
        aware, blind = scan(ROOT)
        self.assertEqual(blind, set(LEASE_BLIND), "lease-blind KEEP-marker consumers changed; update LEASE_BLIND or make it lease-aware")
        self.assertEqual(aware, LEASE_AWARE)

    def test_negative_control_scanner_flags_a_new_blind_consumer(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "scripts"))
            open(os.path.join(td, "scripts", "new_reaper.py"), "w").write("if os.path.exists(p + '/.epyc-keep'): skip\n")
            open(os.path.join(td, "scripts", "ok.py"), "w").write("import scratch_lease\nKEEP_MARKERS=()\n")
            aware, blind = scan(td)
        self.assertEqual(blind, {"scripts/new_reaper.py"})
        self.assertEqual(aware, {"scripts/ok.py"})

    def test_leases_cover_only_tmp_creation_paths(self):
        # Coverage fact behind the list: allocate/backfill default root is tmp/; nothing leases worktrees/ or kernels/.
        text = open(os.path.join(ROOT, "scripts/system/scratch_lease.py")).read()
        self.assertIn('TMP_ROOT = "/mnt/raid0/llm/tmp"', text)
        self.assertEqual(len(re.findall(r'--root", default=TMP_ROOT', text)), 3)
        jan = open(os.path.join(ROOT, "scripts/coordination/churn/disk_janitor.sh")).read()
        self.assertEqual(len(re.findall(r"scratch_lease\.py\" backfill", jan)), 2)  # dry + apply, no --root: tmp only
        self.assertNotIn("backfill --apply --root", jan)


if __name__ == "__main__":
    unittest.main()
