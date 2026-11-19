import hashlib
import tempfile
import unittest
from pathlib import Path

from verify_build_receipt import COMMITS, REQUIRED, verify


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.commit = sorted(COMMITS)[0]
        self.names = sorted(REQUIRED | {"build/bin/libggml-cpu.so", "build/a.gcno"})
        for name in self.names:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(self.commit + "\n" if name == "source-commit.txt" else name)
        self.receipt = self.root / "receipt"
        self.write_receipt()

    def write_receipt(self):
        self.receipt.write_text("".join(
            f"{hashlib.sha256((self.root / n).read_bytes()).hexdigest()}  {n}\n" for n in self.names))

    def test_valid_then_modified_output_refuses(self):
        verify(self.root, self.receipt, self.commit)
        (self.root / "build/bin/llama-server").write_text("substituted")
        with self.assertRaises(ValueError):
            verify(self.root, self.receipt, self.commit)

    def test_missing_coverage_and_wrong_commit_refuse(self):
        self.names.remove("build/a.gcno")
        self.write_receipt()
        with self.assertRaises(ValueError):
            verify(self.root, self.receipt, self.commit)
        self.names.append("build/a.gcno")
        self.write_receipt()
        with self.assertRaises(ValueError):
            verify(self.root, self.receipt, next(c for c in COMMITS if c != self.commit))

    def test_duplicate_and_unsafe_paths_refuse(self):
        for suffix in (self.receipt.read_text().splitlines()[0], "0" * 64 + "  ../escape"):
            self.write_receipt()
            with self.receipt.open("a") as stream:
                stream.write(suffix + "\n")
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                verify(self.root, self.receipt, self.commit)


if __name__ == "__main__":
    unittest.main()
