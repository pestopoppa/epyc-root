import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import source_guard as sg


def ident(p):
    st=p.stat()
    return {'dev':st.st_dev,'ino':st.st_ino,'mode':st.st_mode & 0o7777,'uid':st.st_uid}


class Tests(unittest.TestCase):
    def make(self,root):
        src=root/'source-sealed-20261102';src.mkdir()
        for name in ('base','candidate'):(src/name).mkdir()
        for name in ('base','candidate'):(src/name).chmod(0o555)
        src.chmod(0o555)
        rec={'schema':'kvu19a2.sealed-source.v1','file_count':2,'files_sha256':'a'*64,
             'identities':{n:ident(src if n=='.' else src/n) for n in ('.','base','candidate')}}
        p=root/'sealed-source-receipt.json';p.write_text(json.dumps(rec));p.chmod(0o444)
        return src,p,hashlib.sha256(p.read_bytes()).hexdigest()

    def test_held_source_fd_survives_parent_rename(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td)/'row';root.mkdir();src,receipt,pin=self.make(root)
            fd=sg.open_sealed_source(root,pin,owner=os.geteuid())
            try:
                old=Path(td)/'renamed';root.rename(old)
                self.assertEqual(sg.proc_path(fd).resolve(),old/src.name)
                self.assertTrue((sg.proc_path(fd)/'base').is_dir())
                run=subprocess.run([sys.executable,'-B','-c','import pathlib,sys; assert pathlib.Path(sys.argv[1]).is_dir()',str(sg.proc_path(fd)/'base')],capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
            finally:
                os.close(fd)
                (old/src.name/'base').chmod(0o700);(old/src.name/'candidate').chmod(0o700);(old/src.name).chmod(0o700)

    def test_receipt_and_source_substitution_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td)/'row';root.mkdir();src,receipt,pin=self.make(root)
            try:
                with self.assertRaisesRegex(ValueError,'receipt pin'):sg.open_sealed_source(root,'0'*64,owner=os.geteuid())
                src.chmod(0o777)
                with self.assertRaisesRegex(ValueError,'identity'):sg.open_sealed_source(root,pin,owner=os.geteuid())
            finally:
                (src/'base').chmod(0o700);(src/'candidate').chmod(0o700);src.chmod(0o700)


if __name__=='__main__':unittest.main()
