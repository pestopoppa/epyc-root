import tempfile
import unittest
from pathlib import Path
import check_source


class CustodyTests(unittest.TestCase):
    def test_user_owned_directory_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                check_source.protected(Path(temp))

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'target'
            target.mkdir()
            alias = root / 'alias'
            alias.symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                check_source.protected(alias)


if __name__ == '__main__':
    unittest.main()
