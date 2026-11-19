#!/usr/bin/env python3
"""One-shot CS-5 reference job; use through publish_row.py, never standalone compute.

Preparation supplies stat receipts for already-hashed weights/inputs. This job
never hashes weights, downloads inputs, or constructs an evaluation corpus.
"""
import argparse
import hashlib
import json
import importlib.metadata
from pathlib import Path
import re
import subprocess
import traceback


def read_config(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('configuration digest mismatch')
    return json.loads(raw)


def admit(config):
    if config['schema'] != 'epyc.cs5.reference_job.v1':
        raise ValueError('unsupported job schema')
    if config['candidate'] not in ('step', 'qwen'):
        raise ValueError('unsupported candidate')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', config['run_id']):
        raise ValueError('invalid run_id')
    if config['expects_audio'] is not True:
        raise ValueError('qualification requires audio input')
    receipts = config['prepared_files']
    if not receipts:
        raise ValueError('prepared file identities required')
    paths = set()
    for receipt in receipts:
        path = Path(receipt['path']).resolve(strict=True)
        if str(path) in paths or not path.is_file():
            raise ValueError('duplicate or invalid prepared file')
        paths.add(str(path))
        if not re.fullmatch(r'[a-f0-9]{64}', receipt['sha256']):
            raise ValueError('prepared digest required')
        stat = path.stat()
        observed = dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns,
                        device=stat.st_dev, inode=stat.st_ino)
        if observed != receipt['stat']:
            raise ValueError(f'prepared file changed: {path}')
    # Require every local input and the Step voice prompt to have a receipt.
    inputs = list(config['input_paths'])
    actual_audio = []
    for message in config['messages']:
        content = message['content']
        if isinstance(content, str) or content is None:
            continue
        for item in content:
            if item['type'] == 'audio':
                actual_audio.append(str(Path(item['audio']).resolve()))
            elif item['type'] != 'text':
                raise ValueError('qualification accepts text/local audio only')
    if not actual_audio or set(actual_audio) != {str(Path(p).resolve()) for p in inputs}:
        raise ValueError('message audio differs from prepared inputs')
    if config['candidate'] == 'step':
        inputs.append(config['prompt_wav'])
    if not inputs or any(str(Path(p).resolve()) not in paths for p in inputs):
        raise ValueError('unreceipted input')
    model_root = Path(config['model_dir']).resolve(strict=True)
    model_files = {str(p.resolve()) for p in model_root.rglob('*') if p.is_file()}
    if not model_files or not model_files.issubset(paths):
        raise ValueError('complete model file receipts required')
    for package in ('torch', 'transformers', 'qwen-omni-utils') if config['candidate'] == 'qwen' else ('torch', 'transformers'):
        if importlib.metadata.version(package) != config['environment']['versions'][package]:
            raise ValueError(f'environment version mismatch: {package}')
    command = config['co_tenant_command']
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError('co-tenant sampler argv required')
    # No shell, inferred idle state or unbounded sampler execution.
    return paths


def sample_tenant(command):
    sample = json.loads(subprocess.check_output(command, text=True, timeout=10))
    if type(sample.get('present')) is not bool or sample.get('sampled_during_row') is not True:
        raise ValueError('sampler must report an observed co-tenant state')
    return sample


def execute(config, *, backend=None, sampler=sample_tenant):
    """Load once, execute one prepared turn and retain all terminal failures.

    Fresh output reservation occurs before admission/model loading, so a failed
    attempt cannot silently be rerun into the same evidence directory.
    """
    out = Path(config['result_dir'])
    out.mkdir(parents=True, exist_ok=False)
    (out / 'request.json').write_text(json.dumps(config, indent=2) + '\n')
    summary = dict(schema='epyc.cs5.reference_job_result.v1', run_id=config.get('run_id'),
                   candidate=config.get('candidate'), verdict='inconclusive')
    try:
        admit(config)
        if backend is None:
            if config['candidate'] == 'step':
                import cs5_step_reference as backend
            else:
                import cs5_qwen_reference as backend
        common = dict(expects_audio=True,
            sample_co_tenant=lambda: sampler(config['co_tenant_command']),
            harness=config['harness'], generation=config['generation'])
        if config['candidate'] == 'step':
            model, vocoder, sync = backend.load_models(config['source_dir'],
                config['model_dir'], config['device'])
            result = backend.run_turn(model, vocoder, config['messages'],
                prompt_wav=config['prompt_wav'], synchronize=sync, **common)
        else:
            model, processor, process, sync = backend.load_models(config['source_dir'],
                config['model_dir'], config['device'], environment=config['environment'])
            result = backend.run_turn(model, processor, config['messages'],
                process_mm_info=process, synchronize=sync,
                environment=config['environment'], **common)
        result['prepared_job'] = config
        native, sidecar = backend.write_turn(out / 'turn', result,
            run_id=config['run_id'], subject=config['subject'])
        summary.update(native_path=str(native), sidecar_path=str(sidecar) if sidecar else None,
            verdict='pass' if result['error'] is None and sidecar else 'fail',
            error=result['error'], completion_ms=result['completion_ms'],
            scope='reference turn engineering only; not accuracy, TTFA or ROCm qualification')
    except Exception as error:
        summary.update(error_type=type(error).__name__, error=str(error),
                       traceback=traceback.format_exc())
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    args = parser.parse_args()
    result = execute(read_config(args.config, args.config_sha256))
    return 0 if result['verdict'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
