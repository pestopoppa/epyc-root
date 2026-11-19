import unittest
from types import SimpleNamespace
from source_guard import verify_checkout


class Container:
    def __init__(self, failure=None, untracked=b'', different=False):
        self.failure, self.untracked, self.different, self.calls = failure, untracked, different, []
    def exec_run(self, args):
        self.calls.append(args)
        if self.failure and self.failure in args:
            return SimpleNamespace(exit_code=1, output=b'changed')
        if 'rev-parse' in args:
            return SimpleNamespace(exit_code=0, output=(b'a' * 40) + b'\n')
        if 'ls-tree' in args:
            base = args[-1] != 'HEAD'
            oid = b'b' * 40 if base and self.different else b'a' * 40
            mode = b'100644' if base else b'100755'
            return SimpleNamespace(exit_code=0, output=mode+b' blob '+oid+b'\tfile.py\0')
        if 'ls-files' in args:
            return SimpleNamespace(exit_code=0, output=self.untracked)
        return SimpleNamespace(exit_code=0, output=b'')


class SourceGuardTests(unittest.TestCase):
    def test_content_equal_ignores_only_regular_exec_mode(self):
        c = Container()
        proof = verify_checkout(c, 'b' * 40)
        self.assertEqual(proof['base_tree'], 'a' * 40)
        self.assertTrue(proof['tracked_content_matches_base'])
        self.assertEqual(sum('diff' in x for x in c.calls), 2)
    def test_rejects_bad_base_changed_tree_dirty_checkout_and_untracked(self):
        with self.assertRaises(ValueError): verify_checkout(Container(), 'bad')
        with self.assertRaises(RuntimeError): verify_checkout(Container(different=True), 'b' * 40)
        with self.assertRaises(RuntimeError): verify_checkout(Container('diff'), 'b' * 40)
        with self.assertRaises(RuntimeError): verify_checkout(Container(untracked=b'evil.py\n'), 'b' * 40)

if __name__ == '__main__': unittest.main()
