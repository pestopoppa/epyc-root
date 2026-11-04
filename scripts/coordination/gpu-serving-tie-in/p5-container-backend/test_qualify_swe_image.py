import unittest

from qualify_swe_image import select_tracked_python


class FakeEnv:
    def __init__(self, listing, files):
        self.listing = listing
        self.files = files

    def _exec(self, command, timeout):
        return 0, self.listing, ''

    def read_file(self, path):
        return self.files.get(path)


class SelectionTests(unittest.TestCase):
    def test_selects_sorted_safe_readable_tracked_python(self):
        env = FakeEnv('z.py\n../bad.py\na-link.py\nb.py\n',
                      {'a-link.py': None, 'b.py': 'value = 1\n', 'z.py': 'z = 1\n'})
        self.assertEqual(select_tracked_python(env), ('b.py', 'value = 1\n'))

    def test_refuses_no_safe_file(self):
        with self.assertRaisesRegex(RuntimeError, 'no safe tracked'):
            select_tracked_python(FakeEnv('../bad.py\nx.py\n', {'x.py': None}))


if __name__ == '__main__':
    unittest.main()
