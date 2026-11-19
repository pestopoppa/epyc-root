#!/usr/bin/env python3
"""Bounded descriptive screen of final REPL-to-llama-server request assembly."""
import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import cmp2_runner as base
import fixture
import httpx
from semantic import canonical, digest, evaluator_messages, read_bound, strict_json

HERE = Path(__file__).resolve().parent
SCRATCH = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-final-request')
CANDIDATE = SCRATCH / 'candidate'
ROW = 'toc-cmp-3-final-request-20261118'
ALIAS = 'toc-cmp-3-final-request-qwen3-4b'
PORT = 19370



def verify():
    manifest = strict_json((HERE / 'inputs.json').read_bytes())
    if digest(canonical({k: v for k, v in manifest.items() if k != 'sha256'})) != manifest['sha256']:
        raise ValueError('input seal mismatch')
    if {p.name for p in HERE.iterdir()} != {*manifest['packet_sha256'], 'inputs.json'}:
        raise ValueError('unsealed packet files')
    for name, sha in manifest['packet_sha256'].items():
        read_bound(HERE / name, sha)
    archive = SCRATCH / 'native/prepared'
    for name in [*manifest['packet_sha256'], 'inputs.json']:
        read_bound(archive / name, digest((HERE / name).read_bytes()))
    read_bound(Path(manifest['bin_dir']).parent / 'SHA256SUMS', manifest['build_manifest_sha256'])
    for name, sha in manifest['build_sha256'].items():
        read_bound(Path(manifest['bin_dir']) / name, sha)
    if base.file_identity(Path(manifest['model']['path'])) != manifest['model']['stat_at_hash']:
        raise ValueError('model identity changed')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANDIDATE, text=True).strip() != manifest['candidate_base']:
        raise ValueError('candidate base mismatch')
    diff = subprocess.check_output(['git', 'diff', '--cached', '--binary', 'HEAD'], cwd=CANDIDATE)
    if diff != (HERE / 'candidate.patch').read_bytes():
        raise ValueError('candidate staged source mismatch')
    if subprocess.check_output(['git', 'diff', '--binary'], cwd=CANDIDATE):
        raise ValueError('candidate unstaged changes')
    if subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], cwd=CANDIDATE):
        raise ValueError('candidate untracked files')
    return manifest


def response_bytes(raw):
    choices = strict_json(raw)['choices']
    if len(choices) != 1 or choices[0]['finish_reason'] != 'stop':
        raise ValueError('incomplete evaluator response')
    content = choices[0]['message']['content']
    if not isinstance(content, str):
        raise ValueError('missing evaluator content')  # noqa: TRY004 - stable transport validation contract
    return content.encode('utf-8')


def capture_final(unit, out, evaluator_id, deadline):
    sys.path.insert(0, str(CANDIDATE))
    attempt = out / unit["id"]
    attempt.mkdir()
    called = []

    async def evaluator(case):
        if called:
            raise ValueError("more than one evaluator call")
        called.append(case["request_id"])
        base.atomic_json(attempt / "case.json", case)
        body = {"model": ALIAS, "messages": evaluator_messages(case), "max_tokens": 2048,
                "stream": False, "temperature": 0.0, "seed": 31415926, "cache_prompt": False,
                "chat_template_kwargs": {"enable_thinking": False}, "response_format": {"type": "json_object"}}
        base.atomic_json(attempt / "request.json", body)
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.post(f"http://127.0.0.1:{PORT}/v1/chat/completions", json=body,
                                         timeout=min(270, base.remaining(deadline)))
        raw = response.content
        (attempt / "response.json").write_bytes(raw)
        response.raise_for_status()
        base.remaining(deadline)
        content = response_bytes(raw)
        (attempt / "judgment.json").write_bytes(content)
        return content

    outcome = asyncio.run(fixture.capture(unit, attempt, evaluator, evaluator_id,
                                          min(280, base.remaining(deadline))))
    base.atomic_json(attempt / "OUTCOME.json", outcome)
    if (len(called) != 1 or len(outcome["audit"]) != 1
            or outcome["graph_boundaries"] != [fixture.BOUNDARY_TURN] or not outcome["prior_output_pruned"]):
        raise ValueError("fixed fixture did not traverse boundary and one final-request check")
    audit = outcome["audit"][0]
    case = audit["case"]
    if called != [case["request_id"]] or case["reference"] != fixture.config()["reference"]:
        raise ValueError("final-request evidence lost binding")
    if case["literal_delivered"] is not unit["expected_literal"]:
        raise ValueError("fixed control failed to reach the final request")
    if (audit["semantic_verdict"] not in ("entailed", "contradicted", "unknown")
            or not (attempt / "judgment.json").is_file()):
        raise ValueError("evaluator result unavailable or incomplete")
    observed = case["observed_messages"][0]["content"]
    baseline, = outcome["untouched_text"]
    if unit["mutation"] == "override" and (fixture.CONFLICT in baseline or fixture.CONFLICT not in observed):
        raise ValueError("override injection did not reach the final request")
    if unit["mutation"] == "remove_governance" and (
        case["reference"]["pinned_governance"] not in baseline
        or case["reference"]["pinned_governance"] in observed
    ):
        raise ValueError("governance removal did not reach the final request")
    if audit["blocked"] != bool(outcome["graph_error"]):
        raise ValueError("graph execution disposition disagrees with audit")
    if (audit["blocked"] is False) != (audit["semantic_verdict"] == "entailed" and case["literal_delivered"]):
        raise ValueError("authorization did not match final literal and semantic checks")
    if outcome["worker_dispatches"] != ([] if audit["blocked"] else [audit["final_request"]]):
        raise ValueError("actual worker HTTP send disagrees with audited request/disposition")
    if not audit["blocked"] and outcome["graph_result"] != ("C3-104", None, True):
        raise ValueError("synthetic worker reply did not reach the real REPL")
    if digest(canonical(audit["final_request"])) != case["custody"]["final_request_sha256"]:
        raise ValueError("final-request digest mismatch")
    outcome["actual_verdict"] = audit["semantic_verdict"]
    outcome["actual_literal"] = case["literal_delivered"]
    outcome["worker_body_sha256"] = (None if audit["blocked"] else
                                     digest((attempt / "worker-body-1.json").read_bytes()))
    outcome["synthetic_worker_response_sha256"] = (None if audit["blocked"] else
        digest((attempt / "synthetic-worker-response-1.body").read_bytes()))
    base.atomic_json(attempt / "OUTCOME.json", outcome)
    return outcome


def stop(_signal, _frame):
    raise TimeoutError('row stop signal')


def run():
    if os.environ.get('FILLER_ID') != ROW:
        raise ValueError('rowflow grant required')
    dry = os.environ.get('FILLER_DRYRUN') == '1'
    out = Path(os.environ['FILLER_DRYRUN_DIR']) / 'cmp3-final-request-native' if dry else SCRATCH / 'native'
    out.mkdir(parents=True, exist_ok=True)
    if any(p.name != 'prepared' for p in out.iterdir()):
        raise ValueError('prior capture exists')
    deadline = min(time.time() + 1440, int(os.environ['FILLER_DEADLINE']))
    manifest = verify()
    units = fixture.config()["units"]
    if dry:
        units = units[:1]
    attempts = [unit["id"] for unit in units]
    proc, results, error, server_exited = None, [], None, False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        base.PORT = PORT
        cpus = base.bind_four_cores()
        bin_dir = Path(manifest['bin_dir'])
        server = str(bin_dir / 'llama-server')
        env = {k: v for k, v in os.environ.items() if not k.startswith(('LLAMA_', 'GGML_', 'OMP_', 'KMP_', 'GOMP_'))}
        env.update(LD_LIBRARY_PATH=str(bin_dir), PYTHONDONTWRITEBYTECODE='1')
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        sys.dont_write_bytecode = True
        linkage = subprocess.run(['bash', str(HERE / 'verify_ggml_linkage.sh'), server, str(bin_dir)], env=env,
                                 check=True, capture_output=True, text=True, timeout=20)
        argv = [server, '--model', manifest['model']['path'], '--alias', ALIAS, '--host', '127.0.0.1', '--port', str(PORT),
                '--threads', '4', '--threads-batch', '4', '--ctx-size', '16384', '--parallel', '1', '--n-gpu-layers', '0', '--jinja']
        evaluator_id = f"{ALIAS}:inputs:{manifest['sha256']}"
        base.atomic_json(out / 'RECEIPT.json', {'input_sha256': manifest['sha256'], 'units': attempts,
                         'evaluator_id': evaluator_id, 'argv': argv, 'affinity': cpus, 'linkage': linkage.stdout})
        base.remaining(deadline)
        with (out / 'server.log').open('wb') as log:
            proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
            with Path(os.environ['FILLER_PIDFILE']).open('a') as pids:
                pids.write(f'{proc.pid}\n')
            models = base.server_ready(proc, deadline)
            if [item['id'] for item in models['data']] != [ALIAS]:
                raise ValueError('unexpected evaluator model')
            base.atomic_json(out / 'SERVER.json', {'models': models, **base.server_identity(proc, bin_dir)})
            for unit in units:
                if proc.poll() is not None or not base.owns_listener(proc.pid):
                    raise OSError('private listener ownership lost')
                results.append(capture_final(unit, out, evaluator_id, deadline))
                base.atomic_json(out / 'PROGRESS.json', {'unit': unit['id'], 'completed': len(results)})
    except Exception as exc:  # noqa: BLE001 - persist partial outcome on unexpected failure
        error = f'{type(exc).__name__}: {exc}'
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(timeout=5)
                server_exited = proc.poll() is not None
            except (OSError, subprocess.SubprocessError) as exc:
                error = f'private evaluator cleanup failed: {exc}'
    success = len(results) == len(attempts) and server_exited and error is None
    name = ('SMOKE.json' if dry else 'RESULT.json') if success else 'PARTIAL.json'
    base.atomic_json(out / name, {'unit': ROW, 'completed': len(results), 'planned': len(attempts),
        'coverage_complete': success, 'server_exited': server_exited, 'error': error, 'results': results,
        'unobserved': list(attempts[len(results):]), 'scope': 'synthetic final HTTP request integration; completion is coverage'})
    return int(not success)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('verify', 'run', 'smoke', 'complete'))
    mode = parser.parse_args().mode
    if mode == 'verify':
        verify()
        return 0
    if mode == 'run':
        return run()
    if mode == 'smoke':
        root = os.environ.get('FILLER_DRYRUN_DIR')
        if not root:
            return 1
        path = Path(root) / 'cmp3-final-request-native/SMOKE.json'
        if not path.is_file() or path.stat().st_mtime < float(os.environ['FILLER_SMOKE_T0']):
            return 1
        expected = 1
    else:
        path, expected = SCRATCH / 'native/RESULT.json', 3
    return int(not (path.is_file() and (result := strict_json(path.read_bytes()))['completed'] == expected
                    and result['coverage_complete'] is True and result['server_exited'] is True))


if __name__ == '__main__':
    raise SystemExit(main())
