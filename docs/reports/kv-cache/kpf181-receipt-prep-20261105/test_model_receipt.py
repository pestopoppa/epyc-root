import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import model_receipt as m

class ReceiptTests(unittest.TestCase):
    def test_bound_receipt_and_mutations(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); a=root/'a'; b=root/'b'; a.write_bytes(b'a'); b.write_bytes(b'b')
            expected={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a,b)}
            receipt=root/'receipt'
            with patch.object(m, 'EXPECTED', expected), patch.dict(os.environ, {}, clear=True):
                m.prepare(receipt)
                pin=hashlib.sha256(receipt.read_bytes()).hexdigest()
                m.verify(receipt,pin)
                with self.assertRaises(ValueError):m.verify(receipt,'0'*64)
                with self.assertRaises(FileExistsError):m.prepare(receipt)
                a.write_bytes(b'c')
                with self.assertRaises(ValueError):m.verify(receipt,pin)
                with self.assertRaises(ValueError):m.prepare(root/'wrong')
                a.unlink(); a.symlink_to(b)
                with self.assertRaises((OSError, ValueError)):m.verify(receipt,pin)
                with self.assertRaises((OSError, ValueError)):m.capture(str(a),expected[str(a)])
                with patch.dict(os.environ, {'FILLER_ID':'test'}):
                    with self.assertRaises(ValueError):m.prepare(root/'grant')

if __name__=='__main__':unittest.main()
