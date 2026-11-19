import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from admission import check_parent

class RefusalTests(unittest.TestCase):
    def test_writable_parent_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'cgroup.procs').write_text('')
            with patch('admission.os.access', return_value=True):
                r=check_parent(p)
            self.assertFalse(r.admitted)
            self.assertIn('can write',r.reason)
    def test_nonwritable_is_not_proof_of_containment(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'cgroup.procs').write_text('')
            with patch('admission.os.access', return_value=False):
                r=check_parent(p)
            self.assertFalse(r.admitted)
            self.assertIn('unverified',r.reason)
    def test_missing_relative_and_symlink_refuse(self):
        self.assertFalse(check_parent(Path('relative')).admitted)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); self.assertFalse(check_parent(p/'missing').admitted)
            (p/'link').symlink_to(p, target_is_directory=True)
            self.assertFalse(check_parent(p/'link').admitted)
    def test_symlink_membership_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td); (p/'target').write_text(''); (p/'cgroup.procs').symlink_to(p/'target')
            self.assertFalse(check_parent(p).admitted)

if __name__ == '__main__': unittest.main()
