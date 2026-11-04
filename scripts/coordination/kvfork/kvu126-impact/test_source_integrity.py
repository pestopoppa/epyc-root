#!/usr/bin/env python3
"""Model-free regression checks for sealed source-tree custody."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from source_integrity import untracked_index_affecting_paths


class SourceIntegrityTests(unittest.TestCase):
    def test_untracked_inputs_fail_closed_but_ignored_gitnexus_metadata_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            subprocess.run(["git", "init", "-q", str(tree)], check=True)
            subprocess.run(["git", "-C", str(tree), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(tree), "config", "user.name", "Model-free test"], check=True)
            (tree / "tracked.cpp").write_text("int pinned;\n")
            subprocess.run(["git", "-C", str(tree), "add", "tracked.cpp"], check=True)
            subprocess.run(["git", "-C", str(tree), "commit", "-qm", "fixture"], check=True)

            exclude = tree / ".git" / "info" / "exclude"
            exclude.write_text(".gitnexus/\n")
            private = tree / ".gitnexus" / "cache.json"
            private.parent.mkdir()
            private.write_text("{}\n")
            self.assertEqual(untracked_index_affecting_paths(tree), [])

            (tree / "untracked.cpp").write_text("int changes_index_scope;\n")
            self.assertEqual(untracked_index_affecting_paths(tree), ["untracked.cpp"])


if __name__ == "__main__":
    unittest.main()
