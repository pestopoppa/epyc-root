"""Prospective current-rowflow contract. No enrollment, lock acquisition or dispatch.

The entry and completion predicate deliberately refuse until qualification closes.
The boundary is read-only and is called in addition to the retained provider witness.
"""
import datetime
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import time

ROW = 'kpf18-g3-provider-transport-prep-20261104'
BASE = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')
WINDOW = 9000


def regular(path):
    # Opening the already checked descriptor avoids following a swapped final link.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('nonregular rowflow grant')
        return stream.read()


def cpus(value):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', value):
        raise ValueError('invalid rowflow CPU list')
    result = set()
    for part in value.split(','):
        lo, _, hi = part.partition('-')
        lo, hi = int(lo), int(hi or lo)
        if not 0 <= lo <= hi < 192:
            raise ValueError('invalid rowflow CPU range')
        result.update(range(lo, hi + 1))
    return result


def epoch(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z', value):
        raise ValueError('invalid UTC rowflow timestamp')
    return int(datetime.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp())


def parse_grant(raw):
    fields = {}
    for token in raw.split():
        key, sep, value = token.partition('=')
        if not sep or key in fields or not value:
            raise ValueError('malformed or duplicate rowflow grant field')
        fields[key] = value
    if set(fields) not in ({'regions', 'start', 'end'}, {'regions', 'start', 'end', 'cpus'}):
        raise ValueError('unknown rowflow grant schema')
    gpu, sep, host = fields['regions'].partition(',')
    if gpu != 'mi210_0' or not sep:
        raise ValueError('rowflow GPU region absent')
    allowed = cpus(host)
    if 'cpus' in fields:
        cpus(fields['cpus'])  # v15 claim list is independent of the taskset host list.
    start, end = epoch(fields['start']), epoch(fields['end'])
    if end - start != WINDOW:
        raise ValueError('retained exact9000 GPU window invalid')
    return fields, allowed, start, end


def boundary():
    env = os.environ
    for key in ('FILLER_FLAGS_DIR', 'ROWFLOW_FLAGS'):
        if env.get(key, str(FLAGS)) != str(FLAGS):
            raise ValueError('redirected rowflow flags')
    if env.get('FILLER_GRANTS_DIR', str(FLAGS/'grants')) != str(FLAGS/'grants'):
        raise ValueError('redirected rowflow grants')
    if any(env.get(key) not in (None, '', '0') for key in
           ('FILLER_PREFLIGHT', 'FILLER_DRYRUN', 'FILLER_SMOKE', 'KPF_SMOKE')):
        raise ValueError('smoke/dryrun is not qualified for exclusive G3 runtime')
    grant = FLAGS/'grants'/(ROW+'.grant')
    fields, allowed, start, end = parse_grant(regular(grant))
    stop = BASE/'STOP'
    if env.get('FILLER_ID') != ROW or env.get('FILLER_STOPFILE') != str(stop):
        raise ValueError('rowflow row/STOP identity mismatch')
    if env.get('FILLER_NEEDGPU') != '1' or env.get('FILLER_CPUS') != fields['regions'].split(',', 1)[1]:
        raise ValueError('rowflow GPU/taskset identity mismatch')
    if (env.get('FILLER_END') != str(end) or env.get('FILLER_DEADLINE') != str(end-90)
            or env.get('FILLER_THREADS') != str(len(allowed))):
        raise ValueError('rowflow grant-derived boundary mismatch')
    if not start <= time.time() < end-90:
        raise ValueError('rowflow grant not active or deadline reached')
    affinity = os.sched_getaffinity(0)
    if not affinity or not affinity <= allowed:
        raise ValueError('rowflow CPU affinity escape')
    for path in (stop, grant.with_suffix('.ended'), grant.with_suffix('.complete')):
        if path.exists() or path.is_symlink():
            raise ValueError('rowflow STOP or terminal lifecycle marker')
    if list(FLAGS.glob('HOLD_*')) or list(FLAGS.parent.glob('HOLD_*')):
        raise ValueError('rowflow HOLD')
    return end


def command(base=BASE):
    """Reviewable v15 wiring only; this module never executes the returned argv."""
    base = Path(base)
    shell = lambda name: shlex.join(['/bin/bash', str(base/name)])
    return ['/bin/bash', str(base/'filler_run15.sh'), '--id', ROW, '--class', 'gpu',
            '--role', 'bench', '--gpu-quiet', 'exclusive', '--no-fold-siblings',
            '--min-window', str(WINDOW), '--stop', str(base/'STOP'), '--workdir', str(base),
            '--precond-cmd', shell('precondition.sh'), '--complete-cmd', shell('complete.sh'),
            '--cmd', shell('launch.sh')]


if __name__ == '__main__':
    print('REFUSED: rowflow preparation only; runtime and completion unqualified', file=sys.stderr)
    raise SystemExit(78)
