"""Offline regression for the captured GitNexus argument defect; executes no scan."""
import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).with_name('repaired_job.py').read_text()

class RepairTests(unittest.TestCase):
    def test_every_context_and_impact_uses_exact_worktree_path(self):
        tree = ast.parse(SOURCE)
        commands = []
        for node in ast.walk(tree):
            if isinstance(node, ast.List) and len(node.elts) > 1:
                if all(isinstance(v, ast.Constant) for v in node.elts[:2]):
                    if [v.value for v in node.elts[:2]] in [['gitnexus', 'context'], ['gitnexus', 'impact']]:
                        commands.append(node)
        self.assertEqual(len(commands), 2)
        for command in commands:
            values = [v.value if isinstance(v, ast.Constant) else ast.unparse(v) for v in command.elts]
            idx = values.index('--repo')
            self.assertEqual(values[idx+1], 'str(TREE)')

    def test_partial_and_truncated_results_are_refused(self):
        tree = ast.parse(SOURCE)
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.If) and 'data.get(\'risk\')' in ast.unparse(n.test))
        test = compile(ast.Expression(node.test), '<predicate>', 'eval')
        valid = {'risk':'LOW'}
        for defect in ({'partial':True}, {'truncated':True}, {'error':'bad'}, {'status':'ambiguous'}, {'risk':'UNKNOWN'}):
            self.assertTrue(eval(test, {}, {'data':dict(valid, **defect), 'kind':'impact'}))
        self.assertFalse(eval(test, {}, {'data':valid, 'kind':'impact'}))

    def test_completion_record_is_explicit(self):
        self.assertIn("'type':'scan_complete'", SOURCE)
        self.assertIn("'partial':False", SOURCE)

if __name__ == '__main__': unittest.main()
