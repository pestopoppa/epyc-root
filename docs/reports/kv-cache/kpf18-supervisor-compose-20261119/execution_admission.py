"""Read-only full-run entry checks. No grant/lock acquisition or dispatch authority.

The manifest supplies reviewed artifact identities, never identities learned at
entry. Hashing excludes model weights. This binds files, not mapped native DSOs.
"""
import datetime
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys
import time

FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
ROLES = {'python', 'shell', 'flock', 'server', 'ggml', 'ggml_base', 'ggml_cpu', 'ggml_hip'}


def regular(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('nonregular execution input')
        return stream.read()


def custody(seal):
    config = seal.get('execution')
    if not isinstance(config, dict) or set(config.get('artifacts', {})) != ROLES:
        raise ValueError('complete current execution custody required')
    required = set(config['artifacts'].values()) | {config['provider']}
    required.update(config['provider_sources'])
    sources = seal['sources']
    for name in required:
        path = Path(name)
        if (not path.is_absolute() or path.suffix.lower() == '.gguf'
                or not re.fullmatch('[0-9a-f]{64}', sources.get(name, ''))):
            raise ValueError('unsealed execution input: ' + name)
    # Provider capture verifies the same expected identities independently.
    if any(sources.get(name) != sha for name, sha in config['provider_sources'].items()):
        raise ValueError('provider custody mismatch')
    # Verify the whole inventory again after driver imports, before main.
    for name, expected in sources.items():
        if Path(name).suffix.lower() == '.gguf':
            raise ValueError('model weights forbidden in execution source inventory')
        h = hashlib.sha256()
        with Path(name).open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        if h.hexdigest() != expected:
            raise ValueError('execution source drift: ' + name)
    if Path('/proc/self/exe').resolve() != Path(config['artifacts']['python']).resolve():
        raise ValueError('executing interpreter mismatch')
    return config


def cpus(value):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', value):
        raise ValueError('invalid grant CPUs')
    result = set()
    for part in value.split(','):
        lo, _, hi = part.partition('-')
        lo, hi = int(lo), int(hi or lo)
        if not 0 <= lo <= hi < 192 or result.intersection(range(lo, hi + 1)):
            raise ValueError('invalid grant CPU range')
        result.update(range(lo, hi + 1))
    return result


def epoch(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z', value):
        raise ValueError('invalid UTC grant timestamp')
    return int(datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())


def contract(config):
    env = os.environ
    row = config['row_id']
    stop = Path(config['stop_file'])
    if not re.fullmatch('[a-zA-Z0-9_-]+', row) or not stop.is_absolute():
        raise ValueError('invalid sealed row/STOP identity')
    for key, expected in (('FILLER_FLAGS_DIR', FLAGS), ('ROWFLOW_FLAGS', FLAGS),
                          ('FILLER_GRANTS_DIR', FLAGS / 'grants')):
        if env.get(key, str(expected)) != str(expected):
            raise ValueError('redirected official rowflow namespace')
    if any(env.get(key) not in (None, '', '0') for key in
           ('FILLER_PREFLIGHT', 'FILLER_DRYRUN', 'FILLER_SMOKE', 'KPF_SMOKE', 'FILLER_DIRECT')):
        raise ValueError('full-run admission refuses smoke/dryrun/direct context')
    if env.get('FILLER_ID') != row or env.get('FILLER_STOPFILE') != str(stop):
        raise ValueError('row/STOP identity mismatch')
    # Refuse symlinked namespaces, including dangling STOP leaves.
    for path in (FLAGS / 'grants', stop.parent):
        for component in (path, *path.parents):
            if component.is_symlink() or not component.is_dir():
                raise ValueError('unsafe rowflow directory')
    grant = FLAGS / 'grants' / (row + '.grant')
    raw = regular(grant)
    fields = {}
    for token in raw.split():
        key, sep, value = token.partition('=')
        if not sep or not value or key in fields:
            raise ValueError('malformed or duplicate grant field')
        fields[key] = value
    if not {'regions', 'start', 'end', 'holds'} <= fields.keys() or fields.keys() - {
            'regions', 'start', 'end', 'holds', 'cpus', 'lock'}:
        raise ValueError('unknown current grant schema')
    gpu, sep, host = fields['regions'].partition(',')
    if gpu != 'mi210_0' or not sep or 'gpu-quiet' not in fields['holds'].split(','):
        raise ValueError('official GPU grant absent')
    allowed = cpus(fields.get('cpus', host))
    if 'lock' in fields:
        raise ValueError('unexpected GPU lock CPU override')
    start, end = epoch(fields['start']), epoch(fields['end'])
    if end - start != config['window_s'] or not start <= time.time() < end - 90:
        raise ValueError('grant window/deadline mismatch')
    if (env.get('FILLER_END') != str(end) or env.get('FILLER_DEADLINE') != str(end - 90)
            or env.get('FILLER_NEEDGPU') != '1' or env.get('FILLER_CPUS') != fields.get('cpus', host)
            or env.get('FILLER_THREADS') != str(len(allowed))):
        raise ValueError('grant-derived environment mismatch')
    affinity = os.sched_getaffinity(0)
    if not affinity or not affinity <= allowed:
        raise ValueError('CPU affinity escape')
    for path in (stop, grant.with_suffix('.ended'), grant.with_suffix('.complete')):
        if path.exists() or path.is_symlink():
            raise ValueError('STOP or terminal row')
    # Match current rowflow operator_holds; historical wildcard holds are obsolete.
    for path in FLAGS.glob('HOLD_*'):
        if re.fullmatch(r'HOLD_[A-Za-z0-9_-]+', path.name) and path.is_file():
            raise ValueError('operator HOLD')
    return raw


def capture(seal):
    config = custody(seal)
    grant = contract(config)
    # The provider imports src.runtime peers: disk hashes do not attest loaded objects.
    if any(name == 'src' or name.startswith('src.') for name in sys.modules):
        raise ValueError('preloaded official provider dependency')
    spec = importlib.util.spec_from_file_location('_current_execution_provider', config['provider'])
    provider = importlib.util.module_from_spec(spec)
    exec(compile(Path(config['provider']).read_bytes(), config['provider'], 'exec'), provider.__dict__)
    if set(config['provider_sources']) != {
            str(provider.ORCHESTRATOR / name) for name in provider.SOURCES}:
        raise ValueError('incomplete official provider inventory')
    expected = {name: config['provider_sources'][str(provider.ORCHESTRATOR / name)]
                for name in provider.SOURCES}
    witness = provider.capture(config['row_id'], expected)
    # No driver import if admission changed while the writer was captured.
    if contract(config) != grant:
        raise ValueError('grant changed during admission')
    return provider, witness, grant


def recheck(seal, captured):
    config = custody(seal)
    provider, witness, grant = captured
    if contract(config) != grant:
        raise ValueError('grant changed before driver main')
    provider.recheck(witness)
