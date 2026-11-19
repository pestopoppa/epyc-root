"""Bounded HS-9 chat transport and durable, runner-owned tool capture.

No model calls occur on import. Publication must still pin model/build identities,
policy, cases and evaluator prospectively; a model name is not a weight digest.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import urllib.request

_spec = importlib.util.spec_from_file_location('hs9_capture', Path(__file__).with_name('hs9_capture.py'))
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)


class ChatTransport:
    """OpenAI-compatible JSON transport; limits the entire HTTP response body."""

    def __init__(self, endpoint, *, timeout_s=60, max_response_bytes=65536):
        if timeout_s <= 0 or type(max_response_bytes) is not int or max_response_bytes < 1:
            raise ValueError('invalid transport limits')
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self.max_response_bytes = max_response_bytes

    def __call__(self, request):
        req = urllib.request.Request(self.endpoint, data=json.dumps(request).encode(),
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as response:
            raw = response.read(self.max_response_bytes + 1)
        if len(raw) > self.max_response_bytes:
            raise ValueError('HTTP response exceeds byte limit')
        result = json.loads(raw)
        content = result['choices'][0]['message']['content']
        if not isinstance(content, str):
            raise ValueError('missing textual response')
        return content


def _save(directory, name, value):
    # Exclusive creation prevents accidental overwrite/reuse of a prior run.
    with (directory / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def run_live(case, *, policy, task, model, transport, output_dir,
             max_turns=12, max_bytes=16384, max_tokens=1024):
    """Execute only fake tools, persisting requests, responses and partial traces.

    `transport` takes an isolated chat request and returns raw model text. It must
    enforce its own wall-time and HTTP-body limits (ChatTransport does). Captured
    JSON content is validated by run_script; it cannot populate runner fields.
    Offline tests may inject a fake transport; that does not establish inference.
    """
    if (type(max_turns) is not int or max_turns < 1 or
            type(max_bytes) is not int or max_bytes < 1 or
            type(max_tokens) is not int or max_tokens < 1 or
            not all(isinstance(v, str) and v.strip() for v in (policy, task, model))):
        raise ValueError('invalid live capture inputs')
    capture._simulator.Simulator(case)  # Validate before creating output.
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=False)
    messages = [
        {'role': 'system', 'content': policy + '\nReturn exactly one JSON object per turn: '
         '{"tool":"inspect|check|delegate|perform","args":{...}} or {"report":{...}}. '
         'Tools are simulated; observations arrive in the next user message.'},
        {'role': 'user', 'content': task},
    ]
    responses = []
    for turn in range(max_turns):
        request = {'model': model, 'messages': deepcopy(messages),
                   'temperature': 0, 'max_tokens': max_tokens, 'stream': False}
        _save(directory, f'{turn:03d}-request.json', request)
        try:
            raw = transport(deepcopy(request))
        except Exception as exc:
            trace = capture.run_script(case, responses + [None], max_turns=max_turns, max_bytes=max_bytes)
            trace['termination'] = 'timeout' if isinstance(exc, TimeoutError) else 'transport_error'
            _save(directory, f'{turn:03d}-error.json', {'type': type(exc).__name__})
            break
        _save(directory, f'{turn:03d}-response.json', {'response': raw})
        responses.append(raw)
        trace = capture.run_script(case, responses, max_turns=max_turns, max_bytes=max_bytes)
        _save(directory, f'{turn:03d}-trace.json', trace)
        if trace['termination'] != 'incomplete':
            break
        messages.extend([
            {'role': 'assistant', 'content': raw},
            {'role': 'user', 'content': json.dumps({'observation': trace['events'][-1]})},
        ])
    else:
        trace['termination'] = 'turn_limit'
    _save(directory, 'trace.json', trace)
    return trace
