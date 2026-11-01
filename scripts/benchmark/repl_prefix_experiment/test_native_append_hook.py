import asyncio
import types
import unittest

from native_append_hook import NativeAppendHook


class Builder:
    def build_root_lm_prompt(self, **kwargs):
        return kwargs


class NativeHookTests(unittest.TestCase):
    def setUp(self):
        self.features = types.SimpleNamespace(prefix_stable_order=True,
                                              repl_turn_counter_tail=True,
                                              context_arm_ab=False)
        self.ctx = types.SimpleNamespace(state=types.SimpleNamespace(task_id='task', turns=0, prompt='question'))

    def test_native_post_spill_injection_and_restoration(self):
        original = Builder.build_root_lm_prompt
        async def execute(ctx, role):
            ctx.state.turns += 1
            return Builder().build_root_lm_prompt(turn=ctx.state.turns - 1, state='x=1',
                last_output='already spilled', original_prompt=ctx.state.prompt, last_error='err')
        hook = NativeAppendHook('task', Builder, execute, lambda: self.features)
        first = asyncio.run(hook.turn(self.ctx, 'frontdoor'))
        second = asyncio.run(hook.turn(self.ctx, 'frontdoor'))
        self.assertTrue(second['state'].startswith(first['state']))
        self.assertIn('already spilled', first['state'])
        self.assertEqual(first['last_error'], 'err')
        self.assertIs(Builder.build_root_lm_prompt, original)

    def test_refuses_wrong_task_flags_and_missing_builder(self):
        async def no_builder(ctx, role):
            return None
        hook = NativeAppendHook('task', Builder, no_builder, lambda: self.features)
        self.ctx.state.task_id = 'other'
        with self.assertRaises(ValueError): asyncio.run(hook.turn(self.ctx, 'role'))
        self.ctx.state.task_id = 'task'
        self.features.repl_turn_counter_tail = False
        with self.assertRaises(ValueError): asyncio.run(hook.turn(self.ctx, 'role'))
        self.features.repl_turn_counter_tail = True
        original = Builder.build_root_lm_prompt
        with self.assertRaises(ValueError): asyncio.run(hook.turn(self.ctx, 'role'))
        self.assertIs(Builder.build_root_lm_prompt, original)

    def test_exception_restores_builder(self):
        async def raises(ctx, role):
            raise RuntimeError('native failure')
        original = Builder.build_root_lm_prompt
        hook = NativeAppendHook('task', Builder, raises, lambda: self.features)
        with self.assertRaisesRegex(RuntimeError, 'native failure'):
            asyncio.run(hook.turn(self.ctx, 'role'))
        self.assertIs(Builder.build_root_lm_prompt, original)

    def test_missing_builder_releases_lock(self):
        async def execute(ctx, role):
            ctx.state.turns += 1
            return Builder().build_root_lm_prompt(turn=ctx.state.turns - 1, state='',
                last_output='', original_prompt=ctx.state.prompt)
        hook = NativeAppendHook('task', object, execute, lambda: self.features)
        with self.assertRaises(AttributeError):
            asyncio.run(hook.turn(self.ctx, 'role'))
        hook = NativeAppendHook('task', Builder, execute, lambda: self.features)
        self.assertIn('state', asyncio.run(hook.turn(self.ctx, 'role')))

    def test_known_builder_bypasses_refused_before_execution(self):
        calls = []
        async def execute(ctx, role):
            calls.append(True)
        hook = NativeAppendHook('task', Builder, execute, lambda: self.features)
        self.ctx.state.escalation_prompt = 'escalated'
        with self.assertRaisesRegex(ValueError, 'escalation'):
            asyncio.run(hook.turn(self.ctx, 'role'))
        self.ctx.state.escalation_prompt = ''
        self.ctx.deps = types.SimpleNamespace(repl=types.SimpleNamespace(timed_out=True))
        with self.assertRaisesRegex(ValueError, 'timed-out'):
            asyncio.run(hook.turn(self.ctx, 'role'))
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
