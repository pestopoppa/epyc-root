"""Explicit task-scoped hook for the native REPL turn executor.

Only use in a dedicated process with exactly one in-flight task. The class
patch is process-wide across an await: the lock excludes other hooked calls,
not unrelated native builder calls. This adapter does not start a server,
obtain a grant, prove process isolation or measure quality; the experiment
runner must establish those separately.
"""
from __future__ import annotations

import threading
from unittest.mock import patch

from append_state import PrefixAppendExperiment

_ACTIVE = threading.Lock()


class NativeAppendHook:
    """Wrap the actual ``_execute_turn`` builder call for one task at a time."""

    def __init__(self, task_id, builder_class, execute_turn, features):
        if not isinstance(task_id, str) or not task_id:
            raise ValueError('task id required')
        if not callable(execute_turn) or not callable(features):
            raise TypeError('executor and feature provider must be callable')
        self.task_id = task_id
        self.builder_class = builder_class
        self.execute_turn = execute_turn
        self.features = features
        self.transform = PrefixAppendExperiment(task_id)

    async def turn(self, ctx, role):
        if getattr(ctx.state, 'task_id', None) != self.task_id:
            raise ValueError('task ownership mismatch')
        # Native _execute_turn skips the builder for escalation prompts, which
        # would otherwise run uninstrumented inference before the hit check.
        if getattr(ctx.state, 'escalation_prompt', ''):
            raise ValueError('escalation turn bypasses instrumented builder')
        repl = getattr(getattr(ctx, 'deps', None), 'repl', None)
        if repl is not None and getattr(repl, 'timed_out', False) is True:
            raise ValueError('timed-out REPL bypasses instrumented builder')
        f = self.features()
        if (getattr(f, 'prefix_stable_order', None) is not True
                or getattr(f, 'repl_turn_counter_tail', None) is not True
                or getattr(f, 'context_arm_ab', None) is not False):
            raise ValueError('stable ordering and counter tail required; context arm must be off')
        if not _ACTIVE.acquire(blocking=False):
            raise RuntimeError('another instrumented turn is active')
        try:
            original = self.builder_class.build_root_lm_prompt
            hits = 0

            def patched(builder, *args, **kwargs):
                nonlocal hits
                hits += 1
                if hits != 1 or getattr(ctx.state, 'task_id', None) != self.task_id:
                    raise ValueError('unexpected builder invocation or task identity')
                if kwargs.get('turn') != ctx.state.turns - 1:
                    raise ValueError('builder turn does not match native state')
                if kwargs.get('original_prompt') != ctx.state.prompt:
                    raise ValueError('builder prompt does not match native task')
                return self.transform.wrap_builder(lambda **kw: original(builder, **kw))(*args, **kwargs)

            with patch.object(self.builder_class, 'build_root_lm_prompt', patched):
                result = await self.execute_turn(ctx, role)
            if hits != 1:
                raise ValueError('native builder was not invoked exactly once')
            return result
        finally:
            _ACTIVE.release()
