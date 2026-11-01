"""Task-local state-transform hook for a dedicated closed-loop REPL experiment.

This module does not launch inference or install itself in the application. A
single-task runner must install the returned builder in its own isolated process,
verify its source and flags, and restore it at task end. It changes semantics:
the model must interpret state edit events. Measurements and an accuracy gate
are required before any production use.
"""
from __future__ import annotations

import difflib
import json

HEADER = (
    'State is an append-only edit log. Apply each event in order; within an event, '
    'apply edits from highest start index to lowest. Each edit replaces lines [start:end] '
    'with insert.\n'
)


def _edits(old: str, new: str) -> list[dict]:
    before, after = old.splitlines(keepends=True), new.splitlines(keepends=True)
    seq = difflib.SequenceMatcher(a=before, b=after, autojunk=False)
    edits = [{'start': i, 'end': j, 'insert': after[k:l]}
             for tag, i, j, k, l in seq.get_opcodes() if tag != 'equal']
    check = before[:]
    for edit in reversed(edits):
        check[edit['start']:edit['end']] = edit['insert']
    if ''.join(check) != new:
        raise ValueError('state edits failed reconstruction')
    return edits


class PrefixAppendExperiment:
    """An isolated, single-task transform for the native keyword-only builder.

    Native ``turn`` is zero-based. Only the ``state`` argument is changed;
    spilled last_output, error and all other builder fields remain untouched.
    A runner must bind this instance to one task and avoid concurrent use.
    """
    def __init__(self, task_id: str):
        if not isinstance(task_id, str) or not task_id:
            raise ValueError('task id required')
        self.task_id = task_id
        self._previous = ''
        self._history = HEADER
        self._turn = -1
        self._last_inputs = None
        self._last_render = None

    def render(self, *, task_id: str, turn: int, state: str, visible_output: str) -> str:
        if task_id != self.task_id:
            raise ValueError('task ownership mismatch')
        if type(turn) is not int or turn < 0 or not isinstance(state, str) or not isinstance(visible_output, str):
            raise ValueError('invalid turn or state')
        if turn == self._turn:
            if (state, visible_output) != self._last_inputs:
                raise ValueError('retry changed state')
            return self._last_render
        if turn != self._turn + 1:
            raise ValueError('turns must be contiguous')
        event = {'edits': _edits(self._previous, state), 'last_output': visible_output}
        history = self._history + json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
        self._previous, self._history, self._turn = state, history, turn
        self._last_inputs, self._last_render = (state, visible_output), history
        return history

    def wrap_builder(self, builder):
        """Return an explicitly injected callable; caller owns task binding."""
        if not callable(builder):
            raise TypeError('builder must be callable')
        def wrapped(*args, **kwargs):
            if args or kwargs.get('as_structured'):
                raise ValueError('unexpected native builder signature')
            if not {'state', 'turn', 'last_output'} <= kwargs.keys():
                raise ValueError('native state, turn and spilled output required')
            inputs = dict(kwargs)
            inputs['state'] = self.render(task_id=self.task_id, turn=inputs['turn'], state=inputs['state'], visible_output=inputs['last_output'])
            return builder(**inputs)
        return wrapped
