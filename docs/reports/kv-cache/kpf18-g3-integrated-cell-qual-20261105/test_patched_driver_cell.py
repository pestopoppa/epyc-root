"""Source-bound model-free checks of the proposed actual driver cell."""
import ast
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from functools import partial
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import driver_boundary as boundary

HERE = Path(__file__).resolve().parent
SOURCE = Path('/mnt/raid0/llm/tmp/kvfork/g3-rowflow-prep-20261104/candidate/driver.py')
SOURCE_SHA = '917445e3ff39475690be391376015c02a5b37fc107844941e5277b4dd4bff903'
PATCH_SHA = '194b0bd2eb14b1a5a0752977d1f948158a29cf7692a090598220d164366964eb'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patched_cell(namespace):
    raw = SOURCE.read_bytes()
    patch_data = (HERE / 'driver-entry-refusal.patch').read_bytes()
    if sha(raw) != SOURCE_SHA or sha(patch_data) != PATCH_SHA:
        raise ValueError('driver or patch identity changed')
    with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as directory:
        (Path(directory) / 'driver.py').write_bytes(raw)
        subprocess.run(['patch', '--batch', '--forward', '-p1'], cwd=directory,
                       input=patch_data, check=True, capture_output=True)
        tree = ast.parse((Path(directory) / 'driver.py').read_text())
    item3 = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'item3')
    cell = next(n for n in item3.body if isinstance(n, ast.FunctionDef) and n.name == 'cell')
    exec(compile(ast.Module(body=[cell], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['cell']


class Abort(Exception):
    pass


class Ledger:
    def __init__(self, fail=False):
        self.entries = []
        self.fail = fail

    def json(self, name, value):
        if self.fail:
            raise OSError('ledger unavailable')
        self.entries.append((name, value))


class ActualCell(unittest.TestCase):
    def cell(self, run, ledger):
        state = {'R': None, 'record': {}, 'identity': {}, 'ledger': ledger}
        ns = {'state': state, 'srv': SimpleNamespace(sampler=None), 'ctx': object(),
              'guard': SimpleNamespace(ContextBoundary=lambda ctx: SimpleNamespace(check_boundary=lambda: None)),
              'gate': SimpleNamespace(Abort=Abort), 'run': run, 'partial': partial,
              'os': os, 'time': SimpleNamespace(time=lambda: 1),
              'RowflowContext': boundary.RowflowContext, 'EntryRefused': boundary.EntryRefused,
              'run_with_rowflow_boundary': boundary.run_with_rowflow_boundary,
              'abort_terminal_refusal': boundary.abort_terminal_refusal}
        return patched_cell(ns), state

    def test_stop_refusal_aborts_and_records(self):
        def run(gate, ctx, *args):
            ctx.check_boundary()
            self.fail('work must not follow refusal')
        ledger = Ledger()
        cell, state = self.cell(run, ledger)
        with patch.object(boundary, 'rowflow_entry', return_value=(False, 'stop-file')):
            with self.assertRaisesRegex(Abort, 'stop-file'):
                cell()
        self.assertIn('stop-file', state['record']['diagnostic_error'])
        self.assertEqual(ledger.entries[0][0], 'DIAGNOSTIC-REFUSAL.json')

    def test_unwind_failure_cannot_erase_latched_stop(self):
        def run(gate, ctx, *args):
            try:
                ctx.check_boundary()
            finally:
                raise OSError('attempt finalizer failed')
        cell, state = self.cell(run, Ledger())
        with patch.object(boundary, 'rowflow_entry', return_value=(False, 'stop-file')):
            with self.assertRaisesRegex(Abort, 'stop-file'):
                cell()
        self.assertIn('attempt finalizer failed', state['record']['diagnostic_error'])

    def test_refusal_ledger_failure_still_aborts(self):
        def run(gate, ctx, *args):
            ctx.check_boundary()
        cell, _ = self.cell(run, Ledger(fail=True))
        with patch.object(boundary, 'rowflow_entry', return_value=(False, 'deadline')):
            with self.assertRaisesRegex(Abort, 'refusal ledger write failed'):
                cell()

    def test_ordinary_diagnostic_error_is_recorded(self):
        def run(gate, ctx, *args):
            raise ValueError('bad fixture')
        ledger = Ledger()
        cell, state = self.cell(run, ledger)
        cell()
        self.assertEqual(state['record']['diagnostic_error'], 'ValueError: bad fixture')
        self.assertEqual(len(ledger.entries), 1)


if __name__ == '__main__':
    unittest.main()
