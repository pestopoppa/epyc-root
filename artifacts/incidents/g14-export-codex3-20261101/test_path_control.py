import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from path_control import fresh_output


class PathControlTests(unittest.TestCase):
    def test_fresh_and_existing_protected_candidate_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            scratch.mkdir()
            old = scratch / "old"
            old.mkdir()
            with self.assertRaises((ValueError, FileExistsError)):
                fresh_output(scratch, "old", [old])
            result = fresh_output(scratch, "new", [old])
            self.assertEqual(result.parent, scratch)
            self.assertFalse(any(result.iterdir()))

    def test_symlink_and_hardlink_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            scratch.mkdir()
            old = root / "model"
            old.write_text("fixture")
            (scratch / "sym").symlink_to(old)
            os.link(old, scratch / "hard")
            for name in ("sym", "hard"):
                with self.assertRaises((ValueError, FileExistsError)):
                    fresh_output(scratch, name, [old])
            (root / "alias").symlink_to(scratch)
            with self.assertRaises(ValueError):
                fresh_output(root / "alias", "new", [old])

    def test_escape_and_scratch_inside_protected_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            scratch.mkdir()
            for name in ("../outside", "/absolute", ".", ""):
                with self.assertRaises(ValueError):
                    fresh_output(scratch, name, [root / "scratch"])
            with self.assertRaises(ValueError):
                fresh_output(scratch, "new", [root])


if __name__ == "__main__":
    unittest.main()
