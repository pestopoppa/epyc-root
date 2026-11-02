"""Sealed rowflow boundary for the Q38 isolated-arm successor.

Importers must supply a separately qualified runtime factory. The command-line
entry validates a seal only and refuses execution: native process/cgroup/mode
and loaded-model attestors have not yet been qualified on the target host.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

from q38_t7_journal import DurableJournal
from q38_t7_payloads import FrozenContext, build_plan, run_attested_plan, score


SOURCE_FILES = (
    'q38_t7_rowflow.py', 'q38_t7_payloads.py', 'q38_t7_journal.py',
    'q38_t7_isolated.py', 'q38_t7_runtime.py', 'q38_t7_transport.py',
    'q38_t7_supervisor.py', 'q38_t7_native_verify.py', 'q38_t7.py',
    'lib_gpublock.py', 'degeneracy.py',
)


def _hash(data): return hashlib.sha256(data).hexdigest()


def _load_file(pin):
    if not isinstance(pin, dict) or set(pin) != {'path', 'sha256'}:
        raise ValueError('invalid sealed input')
    path = Path(pin['path'])
    if not path.is_absolute() or str(path.resolve()) != str(path):
        raise ValueError('input path must be absolute and canonical')
    raw = path.read_bytes()
    if _hash(raw) != pin['sha256']:
        raise ValueError('sealed input digest mismatch')
    return json.loads(raw)


def _directory_identity(path):
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('STOP parent is not a directory')
    return {'device': info.st_dev, 'inode': info.st_ino}


class StopBoundary:
    def __init__(self, path, identity, deadline):
        self.path, self.identity, self.deadline = Path(path), identity, deadline

    def __call__(self):
        try:
            if time.time() >= self.deadline or _directory_identity(self.path.parent) != self.identity:
                return True
            # Any entry, including a symlink or directory, is an effective STOP.
            try:
                os.lstat(self.path)
            except FileNotFoundError:
                return False
            return True
        except (OSError, ValueError):
            return True


def prepare(manifest_path, expected_sha256, env):
    manifest_path = Path(manifest_path)
    if not manifest_path.is_absolute() or str(manifest_path.resolve()) != str(manifest_path):
        raise ValueError('manifest path must be absolute and canonical')
    raw = manifest_path.read_bytes()
    if _hash(raw) != expected_sha256:
        raise ValueError('manifest seal mismatch')
    manifest = json.loads(raw)
    required = {'schema', 'row_id', 'run_id', 'plan_input', 'recipes', 'ground_truth',
                'plan_sha256', 'journal', 'stop', 'result_path', 'source_sha256'}
    if not isinstance(manifest, dict) or set(manifest) != required or manifest['schema'] != 'q38-rowflow.v1':
        raise ValueError('manifest schema mismatch')
    if not isinstance(manifest['row_id'], str) or not manifest['row_id'] or env.get('FILLER_ID') != manifest['row_id']:
        raise ValueError('rowflow ID missing or mismatched')
    if not isinstance(manifest['run_id'], str) or not manifest['run_id']:
        raise ValueError('run ID missing')
    sources = manifest['source_sha256']
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_FILES):
        raise ValueError('source seal incomplete')
    here = Path(__file__).resolve().parent
    if any(_hash((here / name).read_bytes()) != sources[name] for name in SOURCE_FILES):
        raise ValueError('source seal mismatch')
    stop = manifest['stop']
    if not isinstance(stop, dict) or set(stop) != {'path', 'parent_identity'}:
        raise ValueError('STOP seal missing')
    stop_path = Path(stop['path'])
    if (not stop_path.is_absolute() or str(stop_path.parent.resolve()) != str(stop_path.parent)
            or env.get('FILLER_STOPFILE') != str(stop_path)
            or _directory_identity(stop_path.parent) != stop['parent_identity']):
        raise ValueError('rowflow STOP identity mismatch')
    try:
        deadline = int(env['FILLER_DEADLINE'])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError('rowflow deadline missing') from exc
    boundary = StopBoundary(stop_path, stop['parent_identity'], deadline)
    if boundary():
        raise ValueError('STOP or rowflow deadline already reached')
    source = _load_file(manifest['plan_input'])
    if not isinstance(source, dict) or set(source) != {'prompts', 'contexts', 'gen', 'gen_nodraft',
                                                        'tokenizer_sha256', 'model_sha256'}:
        raise ValueError('plan input schema mismatch')
    contexts = [FrozenContext(c['target'], c['nominal_tokens'], tuple(c['prefixes']), c['min_cached_tokens'])
                for c in source['contexts']]
    plan = build_plan(source['prompts'], contexts, gen=source['gen'], gen_nodraft=source['gen_nodraft'],
                      tokenizer_sha256=source['tokenizer_sha256'], model_sha256=source['model_sha256'])
    if plan.sha256 != manifest['plan_sha256']:
        raise ValueError('plan content does not match seal')
    recipes, truth = _load_file(manifest['recipes']), _load_file(manifest['ground_truth'])
    if not isinstance(truth, dict):
        raise ValueError('ground truth must be an object')
    binding = manifest['journal']
    if not isinstance(binding, dict) or set(binding) != {'path', 'device', 'inode', 'ledger_id'}:
        raise ValueError('canonical journal seal missing')
    journal_path = Path(binding['path'])
    if not journal_path.is_absolute() or str(journal_path.resolve()) != str(journal_path):
        raise ValueError('journal path must be absolute and canonical')
    result_path = Path(manifest['result_path'])
    if (not result_path.is_absolute() or str(result_path.parent.resolve()) != str(result_path.parent)
            or result_path.exists() or result_path.is_symlink()):
        raise ValueError('result must be a new absolute canonical path')
    journal = DurableJournal(journal_path, cohort_id=plan.sha256, model_sha256=plan.model_sha256,
                             run_id=manifest['run_id'], expected_binding=binding)
    return manifest, plan, recipes, truth, boundary, journal


def run_rowflow(manifest_path, expected_sha256, env, runtime_factory):
    """Run an attested plan only through an explicitly supplied qualified owner."""
    manifest, plan, recipes, truth, stop, journal = prepare(manifest_path, expected_sha256, env)
    try:
        if not callable(runtime_factory):
            raise ValueError('qualified runtime owner is required')
        runtime = runtime_factory(journal, stop)
        if runtime.journal is not journal or runtime.stop_requested is not stop:
            raise ValueError('runtime must use sealed journal and STOP')
        result = run_attested_plan(runtime, recipes, plan)
        report = score(plan, result, truth)
        encoded = json.dumps({'schema': 'q38-rowflow-result.v1', 'run': result, 'score': report},
                             sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        # Never replace an existing run result; exposure ledger remains the
        # source of truth if a crash interrupts this result write.
        fd = os.open(manifest['result_path'], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write(encoded); out.flush(); os.fsync(out.fileno())
        parent_fd = os.open(str(Path(manifest['result_path']).parent), os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(parent_fd)
        finally: os.close(parent_fd)
        return result, report
    finally:
        journal.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    _, _, _, _, _, journal = prepare(args.manifest, args.manifest_sha256, os.environ)
    journal.close()
    print('REFUSED: no qualified production native owner is installed', file=sys.stderr)
    return 65


if __name__ == '__main__':
    sys.exit(main())
