"""Read-only official and explicitly sealed publisher-smoke entry checks.

No grant/lock acquisition or dispatch authority.

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
NATIVE_ROLES = {'ggml', 'ggml_base', 'ggml_cpu', 'ggml_hip',
                'server_impl', 'llama', 'llama_common', 'mtmd'}
ROLES = {'python', 'shell', 'flock', 'server'} | NATIVE_ROLES


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
    mode = config.get('mode', 'official')
    if mode not in ('official', 'publisher-smoke'):
        raise ValueError('unknown sealed execution mode')
    smoke = mode == 'publisher-smoke'
    dry = FLAGS / 'dryrun' / row
    grants = dry / 'grants' if smoke else FLAGS / 'grants'
    expected_env = [('FILLER_FLAGS_DIR', FLAGS), ('ROWFLOW_FLAGS', FLAGS),
                    ('FILLER_GRANTS_DIR', grants)]
    if smoke:
        expected_env += [('FILLER_DRYRUN_DIR', dry), ('FILLER_STATE_DIR', dry / 'state')]
    for key, expected in expected_env:
        if env.get(key, '' if smoke and key != 'ROWFLOW_FLAGS' else str(expected)) != str(expected):
            raise ValueError('redirected official rowflow namespace')
    if smoke:
        if env.get('FILLER_DRYRUN') != '1' or env.get('FILLER_SMOKE') != '1':
            raise ValueError('publisher smoke context absent')
        refused = ('FILLER_PREFLIGHT', 'FILLER_DIRECT', 'KPF_SMOKE')
    else:
        refused = ('FILLER_PREFLIGHT', 'FILLER_DRYRUN', 'FILLER_SMOKE', 'KPF_SMOKE', 'FILLER_DIRECT')
    if any(env.get(key) not in (None, '', '0') for key in refused):
        raise ValueError('full-run admission refuses smoke/dryrun/direct context')
    if env.get('FILLER_ID') != row or env.get('FILLER_STOPFILE') != str(stop):
        raise ValueError('row/STOP identity mismatch')
    # Refuse symlinked namespaces, including dangling STOP leaves.
    directories = [grants, stop.parent]
    result = None
    if smoke:
        result = Path(env.get('FILLER_DRYRUN_RESULT_PATH', ''))
        if (result.parent.parent != dry / 'native-attempts'
                or not re.fullmatch(r'attempt-[A-Za-z0-9_-]+', result.parent.name)
                or result.name != 'native-result.json' or result.is_symlink()):
            raise ValueError('publisher smoke requires isolated native result')
        directories.extend([dry / 'state', result.parent])
    for path in directories:
        for component in (path, *path.parents):
            if component.is_symlink() or not component.is_dir():
                raise ValueError('unsafe rowflow directory')
    grant = grants / (row + '.grant')
    raw = regular(grant)
    fields = {}
    for token in raw.split():
        key, sep, value = token.partition('=')
        if not sep or not value or key in fields:
            raise ValueError('malformed or duplicate grant field')
        fields[key] = value
    required = {'regions', 'start', 'end', 'holds'}
    optional = {'cpus', 'lock'}
    if smoke:
        required |= {'schema', 'id', 'kind'}
        optional |= {'admission_class'}
        if (fields.get('schema') != 'epyc.rowflow.dryrun-grant.v1'
                or fields.get('id') != row or fields.get('kind') != 'rowflow-dryrun'):
            raise ValueError('publisher smoke grant identity')
    if not required <= fields.keys() or fields.keys() - required - optional:
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
    if (not affinity or not affinity <= allowed
            or (smoke and (len(allowed) != 4 or affinity != allowed))):
        raise ValueError('CPU affinity escape')
    terminals = [stop, grant.with_suffix('.ended'), grant.with_suffix('.complete')]
    if smoke:
        terminals += [dry / 'ended', dry / 'complete', dry / 'stop']
    for path in terminals:
        if path.exists() or path.is_symlink():
            raise ValueError('STOP or terminal row')
    # Match current rowflow operator_holds; historical wildcard holds are obsolete.
    for path in FLAGS.glob('HOLD_*'):
        if re.fullmatch(r'HOLD_[A-Za-z0-9_-]+', path.name) and path.is_file():
            raise ValueError('operator HOLD')
    return (raw, str(result)) if smoke else raw


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


def native_mappings(seal, pid, proc_root=Path('/proc')):
    """Bind application DSOs to the owned child's mappings, not just its wrapper.

    System/ROCm libraries are outside this application-library closure. No
    library is loaded here, and neither model files nor process names are read.
    """
    if type(pid) is not int or pid <= 0:
        raise ValueError('captured native PID required')
    root = proc_root / str(pid)
    def birth():
        fields = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
        if fields[0] == 'Z':
            raise ValueError('native child is zombie')
        return fields[19]
    started = birth()
    expected = {role: Path(seal['execution']['artifacts'][role]) for role in NATIVE_ROLES}
    # Keep the exact map spelling/device/inode. resolve()/samefile() alone can
    # silently attest a replacement file while an older inode remains mapped.
    mapped = {}
    for line in (root / 'maps').read_text().splitlines():
        fields = line.split(None, 5)
        if len(fields) != 6:
            continue
        name = fields[5]
        if not name.startswith('/') or not any(
                Path(name).name.startswith(prefix) for prefix in ('libllama', 'libggml', 'libmtmd')):
            continue
        if name.endswith(' (deleted)'):
            raise ValueError('deleted native application mapping')
        major, minor = (int(x, 16) for x in fields[3].split(':'))
        identity = (major, minor, int(fields[4]))
        if name in mapped and mapped[name] != identity:
            raise ValueError('ambiguous native application mapping')
        mapped[name] = identity
    identities = {}
    result = {}
    for role, path in expected.items():
        st = path.stat()
        identity = (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino)
        # Every application-library role must identify its own sealed artifact.
        if identity in identities:
            raise ValueError('aliased native application roles')
        identities[identity] = role
        names = [name for name, observed in mapped.items() if observed == identity]
        if len(names) != 1 or Path(names[0]).resolve() != path.resolve():
            raise ValueError('missing or mismatched native application mapping: ' + role)
        expected_sha = seal['sources'].get(str(path))
        if expected_sha is None or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise ValueError('native mapped artifact drift: ' + role)
        result[role] = {'path': names[0], 'sha256': expected_sha,
                        'device': [identity[0], identity[1]], 'inode': identity[2]}
    if set(mapped.values()) != set(identities):
        raise ValueError('unsealed native application mapping')
    if birth() != started:
        raise ValueError('native child changed during mapping check')
    return result
