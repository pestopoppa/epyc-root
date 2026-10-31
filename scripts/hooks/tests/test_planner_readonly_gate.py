"""Exercise native JSON through a subprocess and a fixture actor seat."""
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import unittest

HOOK = Path(__file__).resolve().parents[1] / 'planner_readonly_gate.py'
spec = importlib.util.spec_from_file_location('gate', HOOK)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def invoke(seat, tool, args, **extra):
    payload = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': args, **extra}
    result = subprocess.run([sys.executable, str(HOOK), seat], input=json.dumps(payload),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)['hookSpecificOutput']['permissionDecision']


class GateTest(unittest.TestCase):
    def test_external_verbs_are_real_absolute_commands(self):
        for verb in gate.EXTERNAL_VERBS:
            with self.subTest(verb=verb):
                self.assertTrue(Path(verb).is_absolute() and Path(verb).is_file())
                self.assertTrue(__import__('os').access(verb, __import__('os').X_OK))

    def test_native_seat_boundary(self):
        # Simulated host only executes the one approved controlled cat fixture.
        fixture = Path(__file__).resolve()
        for seat in ('planner', 'critic'):
            decision = invoke(seat, 'Bash', {'command': '/usr/bin/cat ' + str(fixture)})
            self.assertEqual(decision, 'allow')
            if decision == 'allow':
                run = subprocess.run(['/usr/bin/cat', str(fixture)], capture_output=True, check=True)
                self.assertIn(b'GateTest', run.stdout)
            self.assertEqual(invoke(seat, 'Read', {'file_path': str(fixture)}), 'allow')
            self.assertEqual(invoke(seat, 'Glob', {'pattern': '*.md'}), 'allow')
            self.assertEqual(invoke(seat, 'Grep', {'pattern': 'evidence'}), 'allow')

    def test_unknown_and_action_inputs_ask(self):
        commands = ['make', 'benchmark', 'cat file', '/usr/bin/cat -n file',
                    '/usr/bin/cat file;make', '/usr/bin/cat $(make)',
                    '/usr/bin/cat file > out', '/usr/bin/cat file &',
                    'ROLE=critic /usr/bin/cat file', '/usr/bin/env /usr/bin/cat file',
                    'rg --pre=make pattern', 'find . -exec make {} +',
                    'sed -e 1e file', 'git -c core.pager=make log',
                    '/usr/bin/cat "file"', '/usr/bin/cat file\nmake']
        for cmd in commands:
            with self.subTest(cmd=cmd):
                self.assertEqual(invoke('planner', 'Bash', {'command': cmd}), 'ask')
        for tool, args in [('Write', {'file_path': 'x'}), ('unknown', {}),
                           ('Read', {'file_path': 'x', 'extra': True}),
                           ('Grep', {'pattern': 'x', 'pre': 'make'})]:
            self.assertEqual(invoke('planner', tool, args), 'ask')
        self.assertEqual(invoke('unknown', 'Read', {'file_path': 'x'}, role='planner'), 'ask')
        self.assertEqual(invoke('unknown', 'Bash', {'command': '/usr/bin/cat x'}, authorized=True), 'ask')

    def test_malformed_payload_asks(self):
        p = subprocess.run([sys.executable, str(HOOK), 'planner'], input='{', text=True,
                           capture_output=True, check=True)
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'], 'ask')


    def test_deep_and_oversize_stdin_ask(self):
        for raw in ('[' * 20000 + '0' + ']' * 20000,
                    '{"padding":"' + 'x' * gate.MAX_INPUT_BYTES + '"}'):
            with self.subTest(length=len(raw)):
                p = subprocess.run([sys.executable, str(HOOK), 'planner'], input=raw,
                                   text=True, capture_output=True, check=True)
                self.assertEqual(p.stderr, '')
                response = json.loads(p.stdout)
                self.assertEqual(response['hookSpecificOutput']['permissionDecision'], 'ask')

    def test_example_config_and_simulated_host_failure_contract(self):
        # This is a test host, not Claude: apply the documented onFailure rule.
        doc = (HOOK.parent / 'PLANNER_READONLY_SPIKE.md').read_text()
        settings = json.loads(re.search(r'```json\n(.*?)\n```', doc, re.S).group(1))
        groups = settings['hooks']['PreToolUse']
        self.assertEqual(len(groups), 1)
        self.assertNotIn('matcher', groups[0])
        hook, = groups[0]['hooks']
        self.assertEqual(hook['onFailure'], 'block')
        self.assertEqual(hook['type'], 'command')
        self.assertEqual(hook['timeout'], 5)
        self.assertIn('planner_readonly_gate.py planner', hook['command'])

        def simulated_host(argv, timeout):
            try:
                result = subprocess.run(argv, input='{}', text=True, capture_output=True,
                                        timeout=timeout)
                if result.returncode != 0:
                    return 'block' if hook['onFailure'] == 'block' else 'continue'
                data = json.loads(result.stdout)
                if data['hookSpecificOutput']['permissionDecision'] not in ('allow', 'ask', 'deny'):
                    raise ValueError('bad decision')
                return data['hookSpecificOutput']['permissionDecision']
            except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
                return 'block' if hook['onFailure'] == 'block' else 'continue'

        commands = [(['/nonexistent/s3ach01-hook'], 1),
                    ([sys.executable, '-c', 'raise RuntimeError("fixture crash")'], 1),
                    ([sys.executable, '-c', 'import time; time.sleep(2)'], .1),
                    ([sys.executable, '-c', 'print("{bad")'], 1)]
        for command, timeout in commands:
            with self.subTest(command=command):
                self.assertEqual(simulated_host(command, timeout), 'block')
        self.assertEqual(simulated_host([sys.executable, str(HOOK), 'planner'], 1), 'ask')


if __name__ == '__main__':
    unittest.main()
