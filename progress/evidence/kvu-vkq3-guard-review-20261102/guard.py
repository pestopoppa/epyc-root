"""Offline guard draft; caller must supply the reviewed row identity and catalog."""
import datetime as dt
import hashlib
from pathlib import Path
import re
import time

ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
STAMP = re.compile(r'\d{4}-\d\d-\d\dT\d\d:\d\dZ\Z')
QUARTERS = {f'{n*24}-{n*24+23}': f'{n*24}-{n*24+23}' for n in range(4)}
QUARTERS.update({f'q{n}': f'{n*24}-{n*24+23},{n*24+96}-{n*24+111}' for n in range(4)})


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_catalog(catalog):
    if not isinstance(catalog, dict) or not catalog:
        raise ValueError('empty identity catalog')
    for path, expected in catalog.items():
        if not Path(path).is_absolute() or not SHA.fullmatch(expected) or digest(path) != expected:
            raise ValueError('identity mismatch: ' + str(path))


def parse_grant(raw, expected_id, dryrun):
    try:
        line = raw.decode('ascii')
    except UnicodeDecodeError as exc:
        raise ValueError('non-ASCII grant') from exc
    if not re.fullmatch(r'[^\s]+(?: [^\s]+)*\n?', line):
        raise ValueError('malformed grant line')
    fields = {}
    for token in line.rstrip('\n').split(' '):
        if token.count('=') != 1:
            raise ValueError('malformed grant field')
        key, value = token.split('=', 1)
        if key not in {'regions', 'start', 'end', 'holds', 'schema', 'id', 'kind', 'admission_class'} or key in fields:
            raise ValueError('unknown or duplicate grant field')
        if not value and key != 'holds':
            raise ValueError('empty grant field')
        fields[key] = value
    if not {'regions', 'start', 'end'} <= fields.keys():
        raise ValueError('missing grant field')
    metadata = {'schema', 'id', 'kind', 'admission_class'} & fields.keys()
    if dryrun or metadata:
        if not dryrun or not {'schema', 'id', 'kind'} <= fields.keys() or fields['schema'] != 'epyc.rowflow.dryrun-grant.v1' or fields['id'] != expected_id or fields['kind'] != 'rowflow-dryrun':
            raise ValueError('invalid dry-run grant identity')
        if 'admission_class' in fields and fields['admission_class'] not in {'correctness', 'diagnostic', 'block-correctness', 'block-timing-pairable', 'block-timing-quiet', 'filler'}:
            raise ValueError('invalid admission class')
    if 'holds' in fields and fields['holds'] and not re.fullmatch(r'[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*', fields['holds']):
        raise ValueError('invalid holds')
    stamps = []
    for key in ('start', 'end'):
        value = fields[key]
        if not STAMP.fullmatch(value):
            raise ValueError('invalid grant timestamp')
        stamps.append(int(dt.datetime.strptime(value, '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp()))
    if stamps[0] >= stamps[1]:
        raise ValueError('invalid grant window')
    return fields['regions'], *stamps


class GrantGuard:
    def __init__(self, env, grant_dir, local_stop, *, expected_id, clock=time.time, margin=30):
        if not isinstance(expected_id, str) or not ID.fullmatch(expected_id) or env.get('FILLER_ID') != expected_id:
            raise ValueError('invalid row identity')
        # arm_one removes FILLER_DRYRUN; filler_run15 treats its absence as 0.
        mode = env.get('FILLER_DRYRUN', '0')
        if env.get('FILLER_NEEDGPU') != '0' or mode not in ('0', '1'):
            raise ValueError('invalid mode or GPU grant')
        dryrun = mode == '1'
        self.mode = 'qualification' if dryrun else 'full'
        self.path = Path(grant_dir) / (expected_id + '.grant')
        self.initial = self.path.read_bytes()
        regions, start, end = parse_grant(self.initial, expected_id, dryrun)
        allowed_cpus = '0-95' if regions == '0-95' else QUARTERS.get(regions) if dryrun else None
        if allowed_cpus is None or env.get('FILLER_CPUS') != allowed_cpus:
            raise ValueError('grant CPU shape mismatch')
        try:
            env_end, env_deadline = int(env['FILLER_END']), int(env['FILLER_DEADLINE'])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('invalid deadline') from exc
        if not isinstance(margin, int) or isinstance(margin, bool) or margin < 0 or env_end != end or env_deadline != end - 90 or not start <= clock() < end:
            raise ValueError('grant window or deadline mismatch')
        self.deadline = env_deadline - margin
        if self.deadline <= clock():
            raise ValueError('expired deadline')
        self.clock = clock
        self.local_stop = Path(local_stop)
        if not env.get('FILLER_STOPFILE'):
            raise ValueError('missing engine STOP')
        self.engine_stop = Path(env['FILLER_STOPFILE'])
        self.signal = False
        self.reason = None
        self.check()
        if self.reason:
            raise ValueError('grant unavailable: ' + self.reason)

    def on_signal(self, *_):
        self.signal = True

    def check(self):
        if self.reason: return True
        if self.signal: self.reason = 'signal'
        elif self.local_stop.exists() or self.engine_stop.exists(): self.reason = 'stop'
        elif self.clock() >= self.deadline: self.reason = 'deadline'
        else:
            try:
                if self.path.read_bytes() != self.initial: self.reason = 'grant_changed'
            except OSError:
                self.reason = 'grant_lost'
        return self.reason is not None

    def remaining(self):
        return max(0, self.deadline - self.clock())
