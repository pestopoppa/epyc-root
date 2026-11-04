import unittest

from offline_eval import CHECK, INSTALL, digest_lines, make_offline_eval


class OfflineEvalTests(unittest.TestCase):
    def setUp(self):
        self.lines = ['activate', INSTALL, 'git checkout x tests/test_x.py', 'git apply patch', 'pytest -rA tests/test_x.py']
        self.sha = digest_lines(self.lines)
        self.image = 'sha256:' + 'a' * 64

    def test_only_one_setup_line_changes(self):
        out, evidence = make_offline_eval(self.lines, self.sha, self.image, self.image)
        self.assertEqual(out, ['activate', CHECK, *self.lines[2:]])
        self.assertEqual(evidence['official_script_sha256'], self.sha)
        self.assertEqual(evidence['offline_script_sha256'], digest_lines(out))
        self.assertEqual(evidence['setup_index'], 1)

    def test_refuses_wrong_pins_and_changed_script(self):
        for original, actual in [('0' * 64, self.image), (self.sha, 'sha256:' + 'b' * 64)]:
            with self.assertRaises(ValueError): make_offline_eval(self.lines, original, actual, self.image)
        changed = self.lines[:-1] + ['pytest another_test']
        with self.assertRaises(ValueError): make_offline_eval(changed, self.sha, self.image, self.image)

    def test_refuses_extra_setup_or_fetch(self):
        for line in (INSTALL, 'pip install something', 'curl https://example.test/a'):
            lines = self.lines + [line]
            with self.assertRaises(ValueError): make_offline_eval(lines, digest_lines(lines), self.image, self.image)


if __name__ == '__main__': unittest.main()
