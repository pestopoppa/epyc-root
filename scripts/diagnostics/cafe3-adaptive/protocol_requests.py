#!/usr/bin/env python3
"""Bound, sequential completion capture for one declared CAFE3 arm; no grading."""
import argparse
import http.client
import json
import math
import os
from pathlib import Path
import time

import launch_context as context


def prepare(plan):
    protocol = context.bound_json(plan['protocol'])
    settings = protocol['request_settings']
    context.require(set(settings) == {'n_predict', 'seed', 'timeout_s', 'arm_widths'}, 'request settings keys')
    for key in ('n_predict', 'seed'):
        context.require(type(settings[key]) is int and settings[key] >= (1 if key == 'n_predict' else 0), 'invalid ' + key)
    timeout = settings['timeout_s']
    context.require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, 'invalid request timeout')
    widths = settings['arm_widths']
    context.require(set(widths) == set(protocol['arms']) and plan['arm'] in widths, 'arm width coverage')
    for arm, width in widths.items():
        context.require(type(width) is int and 0 <= width <= 64, 'invalid arm width')
        context.require(arm == 'adaptive' or arm == 'static-' + str(width), 'static arm width mismatch')
    corpus = plan['corpus']
    context.require(corpus == protocol['corpus'] and context.file_identity(corpus['path']) == corpus['identity'], 'corpus changed')
    data = Path(corpus['path']).read_bytes()
    context.require(context.file_identity(corpus['path']) == corpus['identity'], 'corpus changed while reading')
    prompts = [context.parse_json(line) for line in data.splitlines() if line.strip()]
    context.require(prompts and all(isinstance(p, dict) and set(p) == {'id', 'prompt'} and
                    isinstance(p['id'], str) and p['id'] and isinstance(p['prompt'], str) and p['prompt']
                    for p in prompts), 'invalid corpus records')
    context.require(len({p['id'] for p in prompts}) == len(prompts), 'duplicate corpus id')
    argv = plan['argv']
    for flag in ('--host', '--port'):
        context.require(argv.count(flag) == 1 and argv.index(flag) + 1 < len(argv), 'canonical server endpoint required')
    context.require(argv[argv.index('--host') + 1] == '127.0.0.1' and '-p' not in argv and
                    not any(a.startswith(('--host=', '--port=')) for a in argv), 'loopback endpoint required')
    port = int(argv[argv.index('--port') + 1])
    context.require(1024 <= port <= 65535, 'invalid server port')
    return protocol, settings, prompts, port


def owns_listener(pid, port):
    """Require the supervised server, rather than another service, to own TCP."""
    sockets = {p.readlink().name for p in Path(f'/proc/{pid}/fd').iterdir() if p.is_symlink()}
    for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
        fields = line.split()
        if fields[1] == f'0100007F:{port:04X}' and fields[3] == '0A':
            return 'socket:[' + fields[9] + ']' in sockets
    return False


def request(port, path, payload, timeout):
    # http.client does not consult proxy environment variables or follow redirects.
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('GET' if payload is None else 'POST', path,
                           body=None if payload is None else json.dumps(payload, allow_nan=False),
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        context.require(response.status == 200, 'HTTP status ' + str(response.status))
        return context.parse_json(response.read())
    finally:
        connection.close()


def execute(plan, pid, output):
    protocol, settings, prompts, port = prepare(plan)
    deadline = int(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    def guard():
        context.require(not stop.exists() and time.time() < deadline, 'request cutoff')
        context.require(owns_listener(pid, port), 'server does not own endpoint')
        return min(settings['timeout_s'], deadline - time.time())
    with Path(output).open('x') as stream:
        # Readiness retries are bounded by the supervisor and grant. No completions
        # are retried: an ambiguous failed POST invalidates the capture.
        while True:
            context.require(not stop.exists() and time.time() < deadline, 'readiness cutoff')
            try:
                if owns_listener(pid, port):
                    health = request(port, '/health', None, min(1, deadline - time.time()))
                    if health.get('status') == 'ok':
                        break
            except (OSError, ValueError, http.client.HTTPException):
                pass
            time.sleep(.1)
        for repetition in range(protocol['repetitions']):
            for prompt in prompts:
                timeout = guard()
                payload = dict(prompt=prompt['prompt'], n_predict=settings['n_predict'], seed=settings['seed'],
                               temperature=0, stream=False, return_tokens=True, cache_prompt=False,
                               **{'speculative.n_max': settings['arm_widths'][plan['arm']]})
                unix_started_ns = time.time_ns()
                started = time.monotonic_ns()
                response = request(port, '/completion', payload, timeout)
                elapsed = time.monotonic_ns() - started
                unix_ended_ns = time.time_ns()
                guard()
                context.require(isinstance(response, dict) and response.get('stop') is True and
                                response.get('truncated') is False and isinstance(response.get('tokens'), list) and
                                response['tokens'] and all(type(t) is int and t >= 0 for t in response['tokens']) and
                                isinstance(response.get('timings'), dict), 'incomplete token/timing response')
                record = dict(schema='epyc.cafe3.request-capture.v1', status='UNASSESSED',
                              context_sha256=plan['context_sha256'], protocol=plan['protocol'], arm=plan['arm'],
                              repetition=repetition, prompt_id=prompt['id'], payload=payload,
                              elapsed_ns=elapsed, unix_started_ns=unix_started_ns,
                              unix_ended_ns=unix_ended_ns, response=response)
                stream.write(json.dumps(record, allow_nan=False) + '\n')
                stream.flush()
                os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('sha256')
    parser.add_argument('pid', type=int)
    parser.add_argument('output')
    args = parser.parse_args()
    manifest = context.bound_json({'path': args.manifest, 'sha256': args.sha256})
    execute(dict(argv=manifest['argv'], arm=manifest['arm'], corpus=manifest['corpus'],
                 protocol=manifest['protocol'], context_sha256=args.sha256), args.pid, args.output)


if __name__ == '__main__':
    main()
