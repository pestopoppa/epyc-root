import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from verify_packet import verify, PacketError

class VerifyPacket(unittest.TestCase):
    def test_pinned_file_and_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root/'x').write_text('ok')
            manifest = root/'m.json'; manifest.write_text(json.dumps({'x': hashlib.sha256(b'ok').hexdigest()}))
            pin = hashlib.sha256(manifest.read_bytes()).hexdigest()
            self.assertEqual(verify(root,manifest,pin),1)
            (root/'x').write_text('bad')
            with self.assertRaises(PacketError): verify(root,manifest,pin)
    def test_manifest_pin_and_escape(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); manifest=root/'m.json'
            manifest.write_text(json.dumps({'../foreign':'0'*64}))
            with self.assertRaises(PacketError): verify(root,manifest,'0'*64)
            pin=hashlib.sha256(manifest.read_bytes()).hexdigest()
            with self.assertRaises(PacketError): verify(root,manifest,pin)

if __name__ == '__main__': unittest.main()
