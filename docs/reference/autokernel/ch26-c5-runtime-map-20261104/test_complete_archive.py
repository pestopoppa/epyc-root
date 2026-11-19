import unittest
from unittest.mock import patch
import complete

class CompleteArchive(unittest.TestCase):
    def test_bound_sources_and_terminal_positions_forwarded(self):
        native = {"source_provenance": [{"event_id": 42, "cpu": 2}], "rings": [{"event_id": 42, "ring": {"head": 9, "tail": 9}}], "archive_receipt": {"digest": "x"}}
        with patch.object(complete, "verify_archive") as verify:
            complete.verify_compact_evidence("/tmp/proof", native)
        args, kw = verify.call_args
        self.assertEqual(args, ("/tmp/proof.rings", native["archive_receipt"]))
        self.assertEqual(kw["expected_sources"], {42})
        self.assertEqual(kw["expected_terminals"], {42: (9, 9)})
        self.assertEqual(kw["source_provenance"], {42: native["source_provenance"][0]})
    def test_missing_archive_refuses(self):
        with self.assertRaises(KeyError):
            complete.verify_compact_evidence("/tmp/proof", {})

if __name__ == "__main__": unittest.main()
