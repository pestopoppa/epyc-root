"""Generation-bound spawn warnings through the native temporary-bus CLI."""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.coordination import session_bus as bus


@pytest.fixture
def setup_bus(tmp_path, monkeypatch):
    root = tmp_path / 'bus'
    root.mkdir()
    shutil.copy(ROOT / 'coordination/session-bus/session_bus.schema.json', root)
    (root / 'config.yaml').write_text('roster:\n  - {id: sender, role: service}\n  - {id: current, role: service}\n  - {id: retired, role: retired}\n')
    for area in ('inbox', 'outbox', 'cursors', 'heartbeats'):
        (root / area).mkdir()
    (root / 'inbox/current.jsonl').touch()
    monkeypatch.setenv('SESSION_BUS_SPAWN_ID', 'current-generation')
    return root


def receipt(ts, token='current-generation', agent='current', kind='spawn'):
    return {'ts': ts, 'spawn_id': token, 'agent': agent, 'kind': kind,
            'detail': 'window agent:current cmd=echo native'}


def ledger(root, *rows):
    (root / 'adapter-ledger.jsonl').write_text('\n'.join(
        r if isinstance(r, str) else json.dumps(r) for r in rows) + '\n')


def run(root, capsys, *args):
    rc = bus.main(['--bus-root', str(root), *args])
    capture = capsys.readouterr()
    assert rc == 0, capture.err
    return capture.out, capture.err


def mail(root, capsys, ts, label):
    run(root, capsys, 'append', '--agent', 'sender', '--target', 'outbox', '--json',
        json.dumps({'kind': 'finding', 'to': 'current', 'ts': ts,
                    'needs_routing_to': ['current'], 'action_required': True,
                    'task_id': label, 'payload': {'summary': label}}))
    row = json.loads((root / 'outbox/sender.jsonl').read_text().splitlines()[-1])
    with (root / 'inbox/current.jsonl').open('a') as fh:
        fh.write(json.dumps(row) + '\n')
    return row


def test_native_drain_marks_generation_not_age_and_preserves_mail(setup_bus, capsys):
    root = setup_bus
    now = datetime.now(timezone.utc)
    birth = now - timedelta(hours=1)
    # Deliberately reordered: old session later in file, unrelated newer spawn.
    ledger(root, receipt(birth.isoformat()),
           receipt((now - timedelta(days=3)).isoformat(), 'previous-generation'),
           receipt(now.isoformat(), 'foreign', 'sender'))
    pre = mail(root, capsys, (now - timedelta(hours=2)).isoformat(), 'new-but-prebirth')
    post = mail(root, capsys, (now - timedelta(minutes=30)).isoformat(), 'postbirth')
    out, err = run(root, capsys, 'drain', '--agent', 'current', '--peek', '--no-boundary-checks')
    assert [json.loads(line) for line in out.splitlines()] == [pre, post]
    assert 'PREDATE THIS SESSION' in err and 'task=new-but-prebirth' in err
    assert 'task=postbirth' not in err
    assert not (root / 'cursors/current.json').exists()
    before = (root / 'inbox/current.jsonl').read_bytes()
    run(root, capsys, 'drain', '--agent', 'current', '--no-boundary-checks')
    assert (root / 'inbox/current.jsonl').read_bytes() == before
    cursor = json.loads((root / 'cursors/current.json').read_text())
    assert cursor['offset'] == len(before)
    out, _ = run(root, capsys, 'triage', '--agent', 'current')
    assert out.count('PREDATES THIS SESSION') == 1
    assert 'new-but-prebirth' in out and 'postbirth' in out
    # A native actionable disposition still clears routed work as before.
    run(root, capsys, 'append', '--agent', 'current', '--target', 'outbox', '--json',
        json.dumps({'kind': 'status', 'to': 'sender', 'corr_id': pre['id'],
                    'payload': {'summary': 'completed'}}))
    assert all(e['row']['id'] != pre['id'] for e in bus.routed_view(root, 'current')['pending'])


def test_old_mail_after_birth_keeps_age_banner_without_spawn_mark(setup_bus, capsys):
    root = setup_bus
    now = datetime.now(timezone.utc)
    ledger(root, receipt((now - timedelta(days=4)).isoformat()))
    mail(root, capsys, (now - timedelta(days=2)).isoformat(), 'old-but-postbirth')
    out, err = run(root, capsys, 'drain', '--agent', 'current', '--no-boundary-checks')
    assert 'OLDER THAN 24h' in err
    assert 'PREDATE THIS SESSION' not in err and 'UNKNOWN' not in err


@pytest.mark.parametrize('case', ['missing', 'legacy', 'malformed', 'wrong-agent',
    'wrong-kind', 'duplicate', 'naive', 'no-token', 'previous-only', 'retired'])
def test_unproven_birth_stays_unknown_without_losing_mail(setup_bus, capsys, monkeypatch, case):
    root = setup_bus
    ts = datetime.now(timezone.utc).isoformat()
    r = receipt(ts)
    if case == 'legacy':
        r.pop('spawn_id')
    elif case == 'malformed':
        r['ts'] = 'broken'
    elif case == 'wrong-agent':
        r['agent'] = 'sender'
    elif case == 'wrong-kind':
        r['kind'] = 'spawn-died'
    elif case == 'naive':
        r['ts'] = '2026-10-31T00:00:00'
    elif case == 'no-token':
        monkeypatch.delenv('SESSION_BUS_SPAWN_ID')
    elif case == 'previous-only':
        r['spawn_id'] = 'previous-generation'
    if case != 'missing':
        ledger(root, r, *([r] if case == 'duplicate' else []), '[broken', 'null', '[]')
    row = mail(root, capsys, ts, case)
    if case == 'retired':
        (root / 'config.yaml').write_text((root / 'config.yaml').read_text().replace('id: current, role: service', 'id: current, role: retired'))
    out, err = run(root, capsys, 'drain', '--agent', 'current', '--no-boundary-checks')
    assert json.loads(out) == row
    assert ('spawn UNKNOWN' in err) == (case != 'no-token')
    assert 'PREDATE THIS SESSION' not in err


def test_malformed_unrelated_records_do_not_hide_unique_birth(setup_bus):
    root = setup_bus
    ts = '2026-10-30T12:00:00+00:00'
    ledger(root, 'null', '[broken', '[]', receipt(ts))
    assert bus.current_session_spawn(root, 'current') == datetime.fromisoformat(ts).timestamp()
    assert not bus._predates_spawn({'ts': 'broken'}, bus.current_session_spawn(root, 'current'))
    assert not bus._predates_spawn({'ts': ts}, bus.current_session_spawn(root, 'current'))


def test_absolute_cli_works_outside_repository(setup_bus, capsys, tmp_path):
    root = setup_bus
    now = datetime.now(timezone.utc)
    ledger(root, receipt(now.isoformat()))
    row = mail(root, capsys, (now - timedelta(minutes=2)).isoformat(), 'external-cwd')
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/coordination/session_bus.py'),
        '--bus-root', str(root), 'drain', '--agent', 'current', '--no-boundary-checks'],
        cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == row
    assert 'PREDATE THIS SESSION' in result.stderr


def test_unbound_legacy_receipt_keeps_current_drain_quiet(setup_bus, capsys, monkeypatch):
    root = setup_bus
    monkeypatch.delenv('SESSION_BUS_SPAWN_ID')
    now = datetime.now(timezone.utc).isoformat()
    legacy = receipt(now)
    legacy.pop('spawn_id')
    ledger(root, legacy)
    row = mail(root, capsys, now, 'legacy-quiet')
    out, err = run(root, capsys, 'drain', '--agent', 'current', '--no-boundary-checks')
    assert json.loads(out) == row
    assert bus.current_session_spawn(root, 'current') is None
    assert 'spawn UNKNOWN' not in err and 'PREDATE THIS SESSION' not in err
