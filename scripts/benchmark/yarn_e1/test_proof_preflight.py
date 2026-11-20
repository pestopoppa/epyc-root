#!/usr/bin/env python3
"""Boundary tests for the live checker, not a repeat of the matcher tests."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import proof_preflight as checker


class LiveCheckerTests(unittest.TestCase):
    def run_case(self, preflight):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "server.log"
            log.write_text("historical evidence must remain unchanged")
            output = Path(tmp) / "result.json"
            def inspect(args, base):
                self.assertFalse(hasattr(args, "force_preflight"))
                self.assertEqual(base, "http://127.0.0.1:18083")
                return preflight()
            with contextlib.redirect_stdout(io.StringIO()):
                rc = checker.main(["--arm", "A1", "--server-log", str(log),
                                   "--output", str(output)],
                                  loader=lambda repo: SimpleNamespace(preflight=inspect))
            self.assertEqual(log.read_text(), "historical evidence must remain unchanged")
            return rc, json.loads(output.read_text())

    def test_live_problems_refuse_even_with_complete_log_proof(self):
        rc, result = self.run_case(lambda: {"proof": {"metadata": True},
                                           "problems": ["server PID is not a KFD process"]})
        self.assertEqual(rc, 3)
        self.assertFalse(result["ok"])

    def test_full_preflight_pass(self):
        rc, result = self.run_case(lambda: {"proof": {"metadata": True}, "problems": []})
        self.assertEqual(rc, 0)
        self.assertEqual(result["source_commit"], checker.SOURCE_COMMIT)

    def test_unavailable_host_inspection_refuses(self):
        def unavailable():
            raise FileNotFoundError("ss unavailable")
        rc, result = self.run_case(unavailable)
        self.assertEqual(rc, 3)
        self.assertIn("FileNotFoundError", result["error"])

    def test_source_uses_git_object_and_restores_import_state(self):
        prior = SimpleNamespace(marker=True)
        helper = b"def check_proof(): return 'pinned'\n"
        runner = b"from yarn_proof import check_proof\n"
        with patch.dict(sys.modules, {"yarn_proof": prior}):
            with patch.object(checker.subprocess, "check_output", side_effect=[helper, runner]) as call:
                module = checker.load_runner("/example/research")
            self.assertIs(sys.modules["yarn_proof"], prior)
            self.assertEqual(module.check_proof(), "pinned")
            self.assertIs(module.port_pid, checker.port_pid)
            for item in call.call_args_list:
                self.assertIn(checker.SOURCE_COMMIT + ":" + checker.SOURCE_ROOT, item.args[0][-1])

    def test_existing_output_refused_without_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prior.json"
            output.write_text("keep")
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                checker.main(["--arm", "A1", "--server-log", "/unused", "--output", str(output)],
                             loader=lambda repo: self.fail("must refuse before loading"))
            self.assertEqual(output.read_text(), "keep")


class ListenerOwnershipTests(unittest.TestCase):
    def fixture(self, root, entries, owners):
        (root/'net').mkdir()
        rows = ['header']
        for port, state, inode in entries:
            rows.append(f'0: 0100007F:{port:04X} 00000000:0000 {state} '
                        f'00000000:00000000 00:00000000 00000000 1000 0 {inode}')
        (root/'net/tcp').write_text('\n'.join(rows)+'\n')
        for pid, inode in owners:
            fds = root/str(pid)/'fd'
            fds.mkdir(parents=True, exist_ok=True)
            (fds/str(inode)).symlink_to(f'socket:[{inode}]')

    def test_real_ipv4_listener_without_external_tools(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with patch.object(checker.subprocess, 'run', side_effect=AssertionError('no ss')):
                self.assertEqual(checker.port_pid(listener.getsockname()[1]), os.getpid())

    def test_real_ipv6_listener(self):
        with socket.socket(socket.AF_INET6) as listener:
            try:
                listener.bind(('::1', 0))
            except OSError as exc:
                self.skipTest(str(exc))
            listener.listen()
            self.assertEqual(checker.port_pid(listener.getsockname()[1]), os.getpid())

    def test_absent_and_non_listening_ports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [(18761, '01', 42)], [])
            self.assertIsNone(checker.port_pid(18761, proc=root))
            self.assertIsNone(checker.port_pid(8083, proc=root))

    def test_missing_owner_refuses_including_production_port(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [(8083, '0A', 42)], [])
            with self.assertRaisesRegex(RuntimeError, 'ownership unavailable'):
                checker.port_pid(8083, proc=root)

    def test_shared_listener_and_partially_hidden_listeners_refuse(self):
        for entries, owners in (
            ([(18761, '0A', 42)], [(123, 42), (456, 42)]),
            ([(18761, '0A', 42), (18761, '0A', 43)], [(123, 42)]),
        ):
            with self.subTest(entries=entries), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.fixture(root, entries, owners)
                with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
                    checker.port_pid(18761, proc=root)

    def test_two_listeners_owned_by_same_pid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, [(18761, '0A', 42), (18761, '0A', 43)],
                         [(123, 42), (123, 43)])
            self.assertEqual(checker.port_pid(18761, proc=root), 123)

    def test_unreadable_socket_table_refuses(self):
        with patch.object(Path, 'read_text', side_effect=PermissionError('hidden')):
            with self.assertRaises(PermissionError):
                checker.port_pid(8083)


if __name__ == "__main__":
    unittest.main()
