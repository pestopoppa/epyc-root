"""Run a sealed supervisor; expose progress only after its owned cleanup returns."""
import importlib.util
import json
import os
from pathlib import Path
import sys


def selection(root):
    smoke = os.environ.get('FILLER_SMOKE') == '1'
    mode = 'publisher-smoke' if smoke else 'official'
    if smoke != (os.environ.get('FILLER_DRYRUN') == '1'):
        raise ValueError('inconsistent lifecycle mode')
    destination = root / mode
    seal = json.loads((destination / 'manifest.json').read_text())
    if seal['execution']['mode'] != mode:
        raise ValueError('sealed lifecycle mode mismatch')
    output = (Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).parent if smoke
              else Path(seal['execution']['output_root']))
    result = output / ('native-result.json' if smoke else 'RESULT.json')
    return destination, seal, output, result


def complete(root):
    _, _, _, path = selection(root)
    if not path.is_file():
        return 1
    record = json.loads(path.read_text())
    return 0 if (record.get('schema') == 'kpf18.current-lifecycle.v1'
                 and record.get('rc') == 0 and record.get('owned_cleanup_returned') is True) else 1


def run(root):
    destination, seal, output, result = selection(root)
    config = seal['execution']
    if result.exists():
        raise ValueError('lifecycle result already exists; no overwrite')
    path = destination / 'supervisor.py'
    spec = importlib.util.spec_from_file_location('_owned_lifecycle_supervisor', path)
    supervisor = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), supervisor.__dict__)
    sys.argv = [str(path), 'item3', '--out', str(output),
                '--fork-bin', config['artifacts']['server'],
                '--argv-file', config['prepared']['argv'],
                '--prompt-set', config['prepared']['prompts'],
                '--window-id', config['row_id'], '--gpu-window-id', config['row_id'],
                '--port', '18486', '--budget-min', '145', '--load-timeout-s',
                '240' if config['mode'] == 'publisher-smoke' else '900']
    rc = supervisor.run_driver()
    # run_driver's finally must finish first. Refusal and cleanup exceptions
    # propagate without a success record; successful return alone is not work.
    if rc != 0:
        return rc
    payload = ('SMOKE-REQUEST.json' if config['mode'] == 'publisher-smoke'
               else 'conformance/VERDICT.json')
    native = json.loads((output / payload).read_text())
    if config['mode'] == 'publisher-smoke' and not (
            native.get('first_request_ok') is True and native.get('gpu_samples', 0) > 0
            and native.get('tokens', 0) > 0):
        raise ValueError('native smoke work not established')
    record = {'schema': 'kpf18.current-lifecycle.v1', 'rc': rc,
              'owned_cleanup_returned': True, 'mode': config['mode'],
              'native_record': str(output / payload), 'native': native,
              'scope': 'native lifecycle; no parent completion or layout promotion'}
    with result.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    action, root = sys.argv[1:]
    root = Path(root)
    if action == 'complete':
        raise SystemExit(complete(root))
    if action == 'check':
        # Model-free source verification. Runtime independently captures the
        # provider and checks admission before importing any retained driver.
        for mode in ('official', 'publisher-smoke'):
            seal = json.loads((root / mode / 'manifest.json').read_text())
            import hashlib
            for name, expected in seal['sources'].items():
                if Path(name).suffix.lower() == '.gguf':
                    raise ValueError('model in lifecycle source seal')
                if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
                    raise ValueError('lifecycle input drift: ' + name)
        raise SystemExit(0)
    if action != 'run':
        raise ValueError('unknown lifecycle action')
    raise SystemExit(run(root))
