import json
import unittest

from append_state import PrefixAppendExperiment


class AppendExperimentTests(unittest.TestCase):
    def test_native_builder_fields_and_reconstructable_append(self):
        seen = []
        def builder(**kwargs):
            seen.append(kwargs)
            return kwargs['state']
        wrapped = PrefixAppendExperiment('t').wrap_builder(builder)
        args = dict(turn=0, state='x=1\ny=2\n', last_output='spilled', last_error='err', original_prompt='task')
        first = wrapped(**args)
        args.update(turn=1, state='x=3\nz=4\n', last_output='next')
        second = wrapped(**args)
        self.assertTrue(second.startswith(first))
        self.assertEqual(seen[-1]['last_output'], 'next')
        self.assertEqual(json.loads(second.splitlines()[-1])['last_output'], 'next')
        self.assertEqual(seen[-1]['last_error'], 'err')
        lines = []
        for event in second.splitlines()[1:]:
            for edit in reversed(json.loads(event)['edits']):
                lines[edit['start']:edit['end']] = edit['insert']
        self.assertEqual(''.join(lines), args['state'])
        self.assertEqual(wrapped(**args), second)

    def test_refuses_wrong_task_gap_or_mutating_retry(self):
        arm = PrefixAppendExperiment('t')
        with self.assertRaises(ValueError): arm.render(task_id='other', turn=0, state='', visible_output='')
        with self.assertRaises(ValueError): arm.render(task_id='t', turn=1, state='', visible_output='')
        arm.render(task_id='t', turn=0, state='x', visible_output='')
        with self.assertRaises(ValueError): arm.render(task_id='t', turn=0, state='changed', visible_output='')
        with self.assertRaises(ValueError): arm.wrap_builder(lambda **kw: kw)(state='x', turn=1, as_structured=True)

if __name__ == '__main__':
    unittest.main()
