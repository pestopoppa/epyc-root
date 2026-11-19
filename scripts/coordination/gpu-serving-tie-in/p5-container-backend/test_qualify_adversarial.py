import json
import unittest

from qualify_adversarial import run_checks


class FakeEnv:
    def __init__(self, denial=13, traversal=False):
        self.denial, self.traversal, self.files = denial, traversal, {}

    def run(self, command, timeout):
        return 0, ''

    def _exec(self, command, timeout):
        return 0, json.dumps(dict(machine='x86_64', foreign_proc_denied=True,
                                  **{k: self.denial for k in ('socket_inet', 'socket_unix', 'unshare', 'ptrace', 'io_uring')})), ''

    def read_file(self, path):
        if self.traversal and path == '../etc/passwd':
            return 'leaked'
        return self.files.get(path)

    def write_file(self, path, content):
        if path.startswith('../'):
            return False
        self.files[path] = content
        return True


class Controls(unittest.TestCase):
    def test_expected_denials_and_positive_control(self):
        self.assertEqual(run_checks(FakeEnv())['io_uring'], 13)

    def test_unexpected_errno_and_traversal_are_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'expected EACCES'):
            run_checks(FakeEnv(denial=1))
        with self.assertRaisesRegex(RuntimeError, 'traversal read accepted'):
            run_checks(FakeEnv(traversal=True))


if __name__ == '__main__':
    unittest.main()
