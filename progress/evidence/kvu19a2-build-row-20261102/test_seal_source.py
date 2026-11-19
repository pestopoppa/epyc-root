import os
from pathlib import Path
import tempfile
import unittest

import seal_source as seal


class SealedTreeTests(unittest.TestCase):
    def test_protected_readable_tree_and_writable_refusal(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td)/'tree';root.mkdir();child=root/'source';child.mkdir()
            regular=child/'file';regular.write_text('source');regular.chmod(0o444)
            executable=child/'script';executable.write_text('script');executable.chmod(0o555)
            child.chmod(0o555);root.chmod(0o555)
            try:
                seal.check_tree(root,owner=os.geteuid())
                with self.assertRaisesRegex(ValueError,'unowned'):
                    seal.check_tree(root,owner=-1)
                regular.chmod(0o644)
                with self.assertRaisesRegex(ValueError,'writable'):seal.check_tree(root,owner=os.geteuid())
                regular.chmod(0o444)
                child.chmod(0o500)
                with self.assertRaisesRegex(ValueError,'traversable'):seal.check_tree(root,owner=os.geteuid())
            finally:
                root.chmod(0o700);child.chmod(0o700)

    def test_symlinks_and_hardlinks_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td)/'tree';root.mkdir();regular=root/'file';regular.write_text('x');regular.chmod(0o444)
            link=root/'link';link.symlink_to(regular);root.chmod(0o555)
            try:
                with self.assertRaisesRegex(ValueError,'special'):seal.check_tree(root,owner=os.geteuid())
                root.chmod(0o700);link.unlink();os.link(regular,link);root.chmod(0o555)
                with self.assertRaisesRegex(ValueError,'multiply linked'):seal.check_tree(root,owner=os.geteuid())
            finally:root.chmod(0o700)

    def test_symlink_directory_refused(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root=Path(td)/'tree';root.mkdir()
            outside=Path(td)/'outside';outside.mkdir()
            (root/'linked').symlink_to(outside,target_is_directory=True)
            root.chmod(0o555)
            try:
                with self.assertRaisesRegex(ValueError,'symlink directory'):
                    seal.check_tree(root,owner=os.geteuid())
            finally:root.chmod(0o700)


if __name__=='__main__':unittest.main()
