"""DP-5: actual wake helper against an owned disposable PTY; no tmux endpoint."""
import importlib.util
import os
import pty
import select
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
OWNER = Path(os.environ.get('DP5_OWNER_ROOT', ROOT))
spec = importlib.util.spec_from_file_location('dp5_real_adapter', OWNER / 'scripts/coordination/tmux_adapter.py')
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)
FIXTURE = Path(__file__).with_name('composer_tui_fixture.py')


class Composer:
    def __init__(self, glyph='claude', mode='wake'):
        self.master, slave = pty.openpty()
        self.child = subprocess.Popen([sys.executable, str(FIXTURE), '--mode', mode,
                                       '--glyph', glyph, '--pending', 'queued'],
                                      stdin=slave, stdout=slave, stderr=slave, close_fds=True)
        os.close(slave)
        self.output = b''
        self.sent = []
        self.wait_frame()

    def wait_frame(self):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.master], [], [], max(0, deadline-time.monotonic()))
            if not ready:
                break
            chunk = os.read(self.master, 65536)
            self.output += chunk
            # Every draw flushes a complete frame in one write; drain any queued frames.
            if not select.select([self.master], [], [], .02)[0]:
                return self.frame
        raise AssertionError('disposable composer produced no frame')

    @property
    def frame(self):
        return self.output.decode().rsplit('\x1b[2J\x1b[H', 1)[-1]

    def transport(self, *args):
        assert args[:3] == ('send-keys', '-t', 'disposable-only'), args
        key = args[-1]
        assert key in (' ', 'Enter', 'C-u'), args
        self.sent.append(key)
        os.write(self.master, {' ': b' ', 'Enter': b'\r', 'C-u': b'\x15'}[key])
        self.wait_frame()
        return 0, ''

    def close(self):
        os.write(self.master, b'\x04')
        self.child.wait(timeout=3)
        assert self.child.returncode == 0
        os.close(self.master)


class WakeTests(unittest.TestCase):
    def test_existing_modes_preserve_their_enter_behavior(self):
        expected = {'submit': '❱ queued\r\n❱ ', 'swallow': '❱ queued',
                    'picker': '❱ src/completed_path.py', 'cancel': '❱ '}
        for mode, frame in expected.items():
            view = Composer(mode=mode)
            try:
                view.transport('send-keys', '-t', 'disposable-only', 'Enter')
                self.assertEqual(view.frame, frame)
            finally:
                view.close()

    def test_bare_submit_and_clear_are_honest_noops(self):
        view = Composer()
        try:
            self.assertEqual(view.frame, '❱ queued')
            view.transport('send-keys', '-t', 'disposable-only', 'Enter')
            self.assertEqual(view.frame, '❱ queued')
            view.transport('send-keys', '-t', 'disposable-only', 'C-u')
            self.assertEqual(view.frame, '❱ queued')
        finally:
            view.close()

    def test_actual_wake_submit_consumes_and_records_exact_space(self):
        for glyph, marker in [('claude', '❱'), ('codex', '›')]:
            view = Composer(glyph)
            try:
                with patch.object(adapter, '_tmux', view.transport):
                    self.assertEqual(adapter._press_key_with_wake('disposable-only', 'Enter'), (0, ''))
                self.assertEqual(view.sent, [' ', 'Enter'])
                self.assertEqual(view.frame, f'{marker} queued \r\n{marker} ')
            finally:
                view.close()

    def test_actual_wake_clear_consumes_without_transcript(self):
        view = Composer()
        try:
            with patch.object(adapter, '_tmux', view.transport):
                self.assertEqual(adapter._press_key_with_wake('disposable-only', 'C-u'), (0, ''))
            self.assertEqual(view.sent, [' ', 'C-u'])
            self.assertEqual(view.frame, '❱ ')
        finally:
            view.close()

    def test_swallowed_key_keeps_real_wake_space_queued(self):
        view = Composer(mode='swallow')
        try:
            with patch.object(adapter, '_tmux', view.transport):
                self.assertEqual(adapter._press_key_with_wake('disposable-only', 'Enter'), (0, ''))
            self.assertEqual(view.frame, '❱ queued ')
            self.assertNotIn('\r\n', view.frame)
            # Helper success means keys accepted; the unchanged/nonempty composer is NOT delivery.
        finally:
            view.close()

    def test_failed_key_reports_failure_and_keeps_space(self):
        view = Composer()
        try:
            def fail_key(*args):
                if args[-1] == 'Enter':
                    return 7, 'synthetic key refused'
                return view.transport(*args)
            with patch.object(adapter, '_tmux', fail_key):
                code, detail = adapter._press_key_with_wake('disposable-only', 'Enter')
            self.assertEqual(code, 7)
            self.assertIn('Enter failed', detail)
            self.assertEqual(view.frame, '❱ queued ')
        finally:
            view.close()

    def test_failed_wake_does_not_send_key(self):
        with patch.object(adapter, '_tmux', return_value=(9, 'synthetic wake refused')) as tmux:
            code, detail = adapter._press_key_with_wake('disposable-only', 'Enter')
        self.assertEqual(code, 9)
        self.assertIn('wake-character failed', detail)
        tmux.assert_called_once_with('send-keys', '-t', 'disposable-only', ' ')


if __name__ == '__main__':
    unittest.main()
