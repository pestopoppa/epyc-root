"""Strict projection of the original prospective Sphinx scorer control packet."""
from datetime import datetime, timedelta
import hashlib
import json
import re
from pathlib import Path
from claim_tuple import ClaimTuple, ProjectionError, register

SOURCE_KIND = 'p5-sphinx-scorer'
ADAPTER_ID = 'vidya.adapters.p5_sphinx_scorer/v1'
AUTHORITY = 'diagnostic_observation'
METRIC = 'p5_sphinx_scorer_status'
# The terminal is not self-authenticating. Pin the original bytes rather than trusting
# a rewritten terminal and matching rewritten artifacts. Later runs need their own seal.
TERMINAL = 'dd7ac21705edcc2fdb59d7f067ff30f2a143fc86091aee715ed6b9d5e4709e80'
MANIFEST = 'c8ab38f868eae9a20b7518b38a7ae78587a3386dc0bd9282adbbeca5e876d5ed'
LAUNCHER = '3762e2e5906fd54923104166d2b8dda3577ef1d8e20aa7ba3db30e030abca9d8'
ROW = 'vb-p5-sphinx-scorer-native-20261118'
LIMIT = 'One Sphinx known-gold/no-op control, not model quality or population coverage.'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_bytes())

def require(condition, message):
    if not condition:
        raise ValueError(message)

def utc(s):
    t = datetime.fromisoformat(s.replace('Z', '+00:00'))
    require(t.tzinfo is not None and t.utcoffset() == timedelta(0), 'timestamp is not UTC')
    return t

def cpus(s):
    out = set()
    for part in s.split(','):
        parts = part.split('-')
        require(len(parts) <= 2 and all(x.isdecimal() for x in parts), 'bad CPU grant')
        a, b = int(parts[0]), int(parts[-1])
        require(a <= b <= 4095, 'bad CPU range')
        out.update(range(a, b + 1))
    return out

def units(path):
    p = Path(path)
    return [p] if p.is_file() else []

def native_rows(path):
    try:
        path = Path(path).resolve(strict=True)
        require(path.name == 'RESULT.json' and path.parent.name == 'official', 'expected official result')
        root = path.parent.parent
        require(sha(path) == TERMINAL and sha(root / 'SOURCE.sha256') == MANIFEST
                and sha(root / 'launch.sh') == LAUNCHER, 'source or terminal pin mismatch')
        for line in (root / 'SOURCE.sha256').read_text().splitlines():
            digest, name = line.split('  ', 1)
            p = (root / name).resolve(strict=True)
            require(p.is_relative_to(root) and sha(p) == digest, 'sealed source changed')
        terminal = read(path)
        require(terminal['schema'] == 'epyc.p5.scorer-control-capture.v1'
                and terminal['id'] == ROW and terminal['mode'] == 'official'
                and terminal['status'] == 'COMPLETE' and terminal['runner_rc'] == 0
                and terminal['source_manifest_sha256'] == MANIFEST
                and terminal['launcher_sha256'] == LAUNCHER, 'incomplete or wrong capture')
        attempt = (path.parent / terminal['attempt']).resolve(strict=True)
        require(attempt.parent == path.parent and sha(attempt / 'terminal.json') == TERMINAL, 'attempt mismatch')
        grant = terminal['grant']
        require(grant['row'] == ROW and grant['mode'] == 'official'
                and Path(grant['source']).name == ROW + '.grant'
                and sha(attempt / 'rowflow.grant') == grant['snapshot_sha256'], 'grant identity mismatch')
        fields = dict(x.split('=', 1) for x in (attempt / 'rowflow.grant').read_text().split())
        start, end = utc(fields['start']), utc(fields['end'])
        started, finished = utc(terminal['started_utc']), utc(terminal['completion_utc'])
        require(start <= started <= finished < end - timedelta(seconds=90)
                and grant['deadline_epoch'] == (end - timedelta(seconds=90)).timestamp(), 'grant window mismatch')
        allowed = cpus(fields['regions'])
        require(set(grant['granted_cpus']) == allowed and bool(grant['actual_cpus'])
                and set(grant['actual_cpus']) <= allowed, 'grant affinity mismatch')
        require(sha(attempt / 'native.json') == terminal['native_sha256']
                and sha(attempt / 'controls.log') == terminal['controls_sha256'], 'native bytes changed')
        names = {f'{arm}-{suffix}' for arm in ('gold', 'negative') for suffix in ('report.json', 'test_output.txt')}
        require(set(terminal['arm_artifacts_sha256']) == names, 'missing arm artifacts')
        for name, digest in terminal['arm_artifacts_sha256'].items():
            require(sha(attempt / name) == digest, 'arm artifact changed')
        raw, case, pins = read(attempt / 'native.json'), read(root / 'case.json'), read(root / 'pins.json')
        require(raw['schema'] == 'p5.gold-control.v1' and raw['status'] == 'COMPLETE'
                and raw['owned_containers_removed'] is True and not raw.get('error') and not raw.get('cleanup_error')
                and raw['producer_source_manifest_sha256'] == MANIFEST and raw['producer_launcher_sha256'] == LAUNCHER
                and raw['instance_id'] == case['instance_id'] == 'sphinx-doc__sphinx-8593'
                and raw['case_sha256'] == pins['case_sha256'] == sha(root / 'case.json')
                and raw['image_id'] == pins['image_id'] and raw['script_binding']['official_script_sha256'] == pins['official_script_sha256']
                and set(raw['arms']) == {'gold', 'negative'}, 'native identity or cleanup mismatch')
        rows = []
        for arm in ('gold', 'negative'):
            record = raw['arms'][arm]
            report = read(attempt / f'{arm}-report.json')[raw['instance_id']]
            require(type(record['resolved']) is bool and report['resolved'] is record['resolved'], 'resolution mismatch')
            log = (attempt / f'{arm}-test_output.txt').read_text()
            matches = re.findall(r'^(PASSED|FAILED) (tests/\S+)', log, re.MULTILINE)
            require(len(matches) == 3 and len({test for _, test in matches}) == 3, 'log summary coverage mismatch')
            log_status = {test: status for status, test in matches}
            for group, count in (('FAIL_TO_PASS', 2), ('PASS_TO_PASS', 1)):
                statuses = record[group]
                require(set(statuses) == set(json.loads(case[group])) and len(statuses) == count, 'selector coverage mismatch')
                native_group = report['tests_status'][group]
                require(set(native_group['success']) == {k for k, v in statuses.items() if v == 'PASSED'}
                        and set(native_group['failure']) == {k for k, v in statuses.items() if v == 'FAILED'}
                        and all(v in ('PASSED', 'FAILED') for v in statuses.values()), 'report status mismatch')
                require(all(log_status.get(test) == status for test, status in statuses.items()), 'test log status mismatch')
                for test, status in sorted(statuses.items()):
                    rows.append(dict(path=str(path), digest=TERMINAL, date=finished.date().isoformat(),
                                     arm=arm, group=group, test=test, status=status))
        gold, negative = raw['arms']['gold'], raw['arms']['negative']
        passed = (gold['resolved'] and all(v == 'PASSED' for g in ('FAIL_TO_PASS','PASS_TO_PASS') for v in gold[g].values())
                  and not negative['resolved'] and any(v == 'FAILED' for v in negative['FAIL_TO_PASS'].values())
                  and all(v == 'PASSED' for v in negative['PASS_TO_PASS'].values()))
        require(raw['decision'] == terminal['decision'] == ('PASS' if passed else 'FAIL'), 'decision mismatch')
        return tuple(rows)
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise ProjectionError(f'{SOURCE_KIND}: {exc}') from exc

@register(SOURCE_KIND)
def project(native):
    if not isinstance(native, dict) or not isinstance(native.get('path'), str) or native not in native_rows(native['path']):
        raise ProjectionError('P5 row does not rederive')
    identity = f"{native['arm']}:{native['group']}:{native['test']}"
    return ClaimTuple(measurement_id=f'{SOURCE_KIND}:' + hashlib.sha256((native['digest'] + ':' + identity).encode()).hexdigest(),
        metric=METRIC, value=int(native['status'] == 'PASSED'), date=native['date'], category='CANDIDATE',
        claim=f"Sphinx {native['arm']} {native['group']} {native['test']}: {native['status']}. {LIMIT}",
        protocol_id='', reps=1, reps_basis='one named test in one native scorer arm', unit='passed',
        attestation_path=native['path'], attestation_sha256=native['digest'],
        attestation_locator=native['path'] + '#' + identity, attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, observation={'outcome_native': native['status'], 'outcome_reason': LIMIT},
        extra={'adapter': ADAPTER_ID, 'arm': native['arm'], 'group': native['group'], 'test': native['test']})
