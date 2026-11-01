from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from test_worker_checkpoint import lane, dirty, git, request, wc
from scripts.coordination import checkpoint_reconcile as cr
from scripts.coordination import session_bus as bus


@pytest.fixture
def setup_checkpoint(lane, tmp_path, monkeypatch):
    dirty(lane)
    req = request(completed_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    receipt = wc.run_checkpoint(req, repo=lane)
    common = Path(git(lane, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip())
    journal = common / 'worker-checkpoints' / 'mainA' / (receipt['checkpoint_id'] + '.json')
    root = tmp_path / 'bus'
    (root / 'inbox').mkdir(parents=True)
    (root / 'outbox').mkdir()
    (root / 'inbox/coordinator-agent.jsonl').write_text('')
    (root / 'outbox/coordinator-agent.jsonl').write_text('')
    (root / 'config.yaml').write_text('roster:\n  - id: coordinator-agent\n  - id: mainA\n')
    monkeypatch.setattr(cr, '_common_dir', lambda repo: common)
    monkeypatch.setattr(bus, '_print_daemon_health', lambda *a: None)
    return root, journal, receipt


def drain(root):
    return bus.cmd_drain(argparse.Namespace(bus_root=str(root), agent='coordinator-agent',
        peek=False, stale_after_h=1, no_boundary_checks=True, triage=False))


def test_empty_drain_and_phase_transition_once(setup_checkpoint, capsys):
    root, journal, receipt = setup_checkpoint
    assert drain(root) == 0
    captured = capsys.readouterr()
    output = captured.err
    assert '(no new messages' in captured.out and 'checkpoint notice:' in output
    assert receipt['checkpoint_id'] in output and receipt['payload']['task_text'] not in output
    doc = json.loads(journal.read_text())
    doc['phase'] = 'published'
    doc['bus_message_id'] = cr._message(journal, 'mainA', datetime.now(timezone.utc).timestamp())[1]
    journal.write_text(json.dumps(doc))
    assert drain(root) == 0
    assert 'checkpoint notice:' not in capsys.readouterr().err


def test_handled_without_any_worker_bus_row(setup_checkpoint, capsys):
    root, journal, _ = setup_checkpoint
    msg = cr._message(journal, 'mainA', datetime.now(timezone.utc).timestamp())[1]
    (root / 'outbox/coordinator-agent.jsonl').write_text(json.dumps({'from':'coordinator-agent', 'kind':'ack', 'corr_id':msg, 'payload':{'disposition':'done'}}) + '\n')
    assert drain(root) == 0
    assert 'checkpoint notice:' not in capsys.readouterr().err
    assert not (root / 'outbox/mainA.jsonl').exists()


def test_failed_output_retries_and_receipt_is_after_delivery(setup_checkpoint, monkeypatch, capsys):
    root, journal, _ = setup_checkpoint
    original = __import__('builtins').print
    def fail(*args, **kwargs):
        if args and str(args[0]).startswith('checkpoint notice:'):
            raise BrokenPipeError('before delivery')
        return original(*args, **kwargs)
    monkeypatch.setattr('builtins.print', fail)
    assert drain(root) == 0
    assert not list((root / 'checkpoint-notices/coordinator-agent').glob('*.json'))
    monkeypatch.setattr('builtins.print', original)
    assert drain(root) == 0
    assert 'checkpoint notice:' in capsys.readouterr().err
    assert len(list((root / 'checkpoint-notices/coordinator-agent').glob('*.json'))) == 1


def test_crash_after_output_before_receipt_retries(setup_checkpoint, monkeypatch, capsys):
    root, _, _ = setup_checkpoint
    original = cr.tempfile.mkstemp
    monkeypatch.setattr(cr.tempfile, 'mkstemp', lambda *a, **kw: (_ for _ in ()).throw(OSError('crash')))
    drain(root)
    assert 'checkpoint notice:' in capsys.readouterr().err
    monkeypatch.setattr(cr.tempfile, 'mkstemp', original)
    drain(root)
    assert 'checkpoint notice:' in capsys.readouterr().err
    drain(root)
    assert 'checkpoint notice:' not in capsys.readouterr().err


@pytest.mark.parametrize('kind', ['malformed', 'stale', 'foreign', 'symlink', 'large', 'moving'])
def test_unknown_artifacts_are_not_announced(setup_checkpoint, monkeypatch, capsys, kind):
    root, journal, _ = setup_checkpoint
    if kind == 'malformed': journal.write_text('{')
    elif kind == 'large': journal.write_bytes(b'x' * (cr.MAX_ARTIFACT + 1))
    elif kind == 'symlink':
        saved = journal.with_suffix('.saved'); journal.rename(saved); journal.symlink_to(saved)
    elif kind == 'moving':
        original = cr._read_stable
        def moving(path, cap):
            if path == journal:
                raise ValueError('changed')
            return original(path, cap)
        monkeypatch.setattr(cr, '_read_stable', moving)
    else:
        data = json.loads(journal.read_text())
        if kind == 'stale': data['completed_at'] = '2000-01-01T00:00:00Z'
        else: data['identity']['agent'] = 'mainB'
        journal.write_text(json.dumps(data))
    assert drain(root) == 0
    assert 'checkpoint notice:' not in capsys.readouterr().err
    assert not list((root / 'checkpoint-notices/coordinator-agent').glob('*.json'))


def test_concurrent_drains_produce_one_notice(setup_checkpoint, capsys):
    import threading
    root, _, _ = setup_checkpoint
    start = threading.Barrier(3)
    errors = []
    def run():
        try:
            start.wait()
            drain(root)
        except Exception as exc:
            errors.append(exc)
    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads: thread.start()
    start.wait()
    for thread in threads: thread.join()
    assert not errors
    assert capsys.readouterr().err.count('checkpoint notice:') == 1
    assert len(list((root / 'checkpoint-notices/coordinator-agent').glob('*.json'))) == 1


def test_byte_cap_defers_without_receipt(setup_checkpoint, monkeypatch, capsys):
    root, _, _ = setup_checkpoint
    monkeypatch.setattr(cr, "MAX_NOTICE_BYTES", 1)
    assert drain(root) == 0
    assert "checkpoint notice:" not in capsys.readouterr().err
    assert not list((root / "checkpoint-notices/coordinator-agent").glob("*.json"))
    monkeypatch.setattr(cr, "MAX_NOTICE_BYTES", 4096)
    assert drain(root) == 0
    assert "checkpoint notice:" in capsys.readouterr().err


def test_handled_relay_alias_uses_source_identity(setup_checkpoint, capsys):
    root, journal, _ = setup_checkpoint
    msg = cr._message(journal, 'mainA', datetime.now(timezone.utc).timestamp())[1]
    (root / 'inbox/coordinator-agent.jsonl').write_text(json.dumps({'id':'relay-copy', 'relayed_src':msg}) + '\n')
    (root / 'outbox/coordinator-agent.jsonl').write_text(json.dumps({'from':'coordinator-agent', 'kind':'ack', 'corr_id':'relay-copy', 'payload':{'disposition':'done'}}) + '\n')
    assert drain(root) == 0
    assert 'checkpoint notice:' not in capsys.readouterr().err


def test_peek_does_not_consume_notice(setup_checkpoint, capsys):
    root, _, _ = setup_checkpoint
    args = argparse.Namespace(bus_root=str(root), agent='coordinator-agent', peek=True,
                              stale_after_h=1, no_boundary_checks=True, triage=False)
    assert bus.cmd_drain(args) == 0
    assert 'checkpoint notice:' not in capsys.readouterr().err
    assert drain(root) == 0
    assert 'checkpoint notice:' in capsys.readouterr().err
def test_fairness_after_resolved_prefix(setup_checkpoint, lane, monkeypatch, capsys):
    root, original, receipt = setup_checkpoint
    for index in range(2):
        text = f'Additional actual worker task {index}'
        handoff = lane / 'handoffs/active/worker.md'
        with handoff.open('a') as f:
            f.write(f'\n- [ ] {text}\n')
        req = request(task_text=text, task_id=f'fairness-{index}', boundary_key=f'fairness-{index}',
                      completed_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
        wc.run_checkpoint(req, repo=lane)
    journals = sorted(original.parent.glob('*.json'))
    assert len(journals) == 3
    ids = [cr._message(p, 'mainA', datetime.now(timezone.utc).timestamp()) for p in journals]
    assert all(ids)
    handled, noticed, tail = ids
    (root / 'outbox/coordinator-agent.jsonl').write_text(json.dumps({'from':'coordinator-agent','kind':'ack','corr_id':handled[1],'payload':{'disposition':'done'}})+'\n')
    drain(root)
    capsys.readouterr()
    notices = root / 'checkpoint-notices/coordinator-agent'
    (notices / (tail[0] + '.json')).unlink()
    (notices / (handled[0] + '.json')).unlink(missing_ok=True)
    (notices / (noticed[0] + '.json')).write_text(json.dumps({'checkpoint_id': noticed[0], 'message_id': noticed[1]}))
    monkeypatch.setattr(cr, 'MAX_FILES', 1)
    all_output = ''
    for _ in range(4):
        drain(root)
        all_output += capsys.readouterr().err
    assert tail[0] in all_output
    assert (notices / (tail[0] + '.json')).exists()
    assert all_output.count('checkpoint notice:') == 1


def test_handled_receipt_is_distinct_and_source_change_is_unknown(setup_checkpoint, capsys):
    root, journal, receipt = setup_checkpoint
    key, msg = cr._message(journal, "mainA", datetime.now(timezone.utc).timestamp())
    (root / "outbox/coordinator-agent.jsonl").write_text(json.dumps({"from": "coordinator-agent", "kind": "ack", "corr_id": msg, "payload": {"disposition": "done"}}) + "\n")
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result == {"scanned": 1, "unknown": 0, "truncated": False}
    saved = json.loads((root / "checkpoint-notices/coordinator-agent" / (key + ".json")).read_text())
    assert saved["kind"] == "handled"
    assert "checkpoint notice:" not in capsys.readouterr().err
    journal.write_text("{bad")
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1
    assert "checkpoint notice:" not in capsys.readouterr().err


def test_legacy_notified_receipt_upgrades_only_after_validation(setup_checkpoint, capsys):
    root, journal, receipt = setup_checkpoint
    drain(root)
    capsys.readouterr()
    key, msg = cr._message(journal, "mainA", datetime.now(timezone.utc).timestamp())
    done = root / "checkpoint-notices/coordinator-agent" / (key + ".json")
    done.write_text(json.dumps({"checkpoint_id": key, "message_id": msg}))
    drain(root)
    assert "checkpoint notice:" not in capsys.readouterr().err
    record = json.loads(done.read_text())
    assert record["kind"] == "notified" and record["source_signature"] == cr._source_signature(journal)


def test_unknown_receipt_is_not_resolved_and_cap_reports_truncation(setup_checkpoint, monkeypatch, capsys):
    root, journal, receipt = setup_checkpoint
    drain(root)
    capsys.readouterr()
    done = root / "checkpoint-notices/coordinator-agent" / (receipt["checkpoint_id"] + ".json")
    done.write_text("{bad")
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1
    assert done.read_text() == "{bad"
    done.unlink()
    monkeypatch.setattr(cr, "MAX_FILES", 0)
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["truncated"] is True
    assert not done.exists()


def test_stale_legacy_notice_migrates_but_remains_unknown(setup_checkpoint, capsys):
    root, journal, _ = setup_checkpoint
    drain(root)
    capsys.readouterr()
    doc = json.loads(journal.read_text())
    doc["completed_at"] = "2000-01-01T00:00:00Z"
    doc["receipt"]["payload"]["completed_at"] = doc["completed_at"]
    journal.write_text(json.dumps(doc))
    key, msg = cr._message(journal, "mainA", datetime.now(timezone.utc).timestamp(), allow_stale=True)
    done = root / "checkpoint-notices/coordinator-agent" / (key + ".json")
    done.write_text(json.dumps({"checkpoint_id": key, "message_id": msg}))
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1 and result["scanned"] == 1
    assert json.loads(done.read_text())["kind"] == "notified"
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1 and result["scanned"] == 0
    assert "checkpoint notice:" not in capsys.readouterr().err


def test_symlinked_worker_directory_reports_unknown(setup_checkpoint):
    root, journal, _ = setup_checkpoint
    directory = journal.parent
    saved = directory.with_name("saved")
    directory.rename(saved)
    directory.symlink_to(saved, target_is_directory=True)
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1 and result["scanned"] == 0


def test_correlated_status_is_not_a_terminal_disposition(setup_checkpoint, capsys):
    root, journal, _ = setup_checkpoint
    key, msg = cr._message(journal, "mainA", datetime.now(timezone.utc).timestamp())
    (root / "outbox/coordinator-agent.jsonl").write_text(json.dumps({"from": "coordinator-agent", "kind": "status", "corr_id": msg, "payload": {"disposition": "in_progress"}}) + "\n")
    assert drain(root) == 0
    assert key in capsys.readouterr().err
    done = json.loads((root / "checkpoint-notices/coordinator-agent" / (key + ".json")).read_text())
    assert done["kind"] == "notified"


@pytest.mark.parametrize("field", ["completed_at", "payload"])
def test_malformed_native_shapes_remain_unknown(setup_checkpoint, capsys, field):
    root, journal, _ = setup_checkpoint
    data = json.loads(journal.read_text())
    if field == "completed_at":
        data[field] = []
    else:
        data["receipt"][field] = []
    journal.write_text(json.dumps(data))
    assert drain(root) == 0
    assert "checkpoint notice:" not in capsys.readouterr().err
    result = cr.reconcile(root, "coordinator-agent", Path("."), common=journal.parents[2])
    assert result["unknown"] == 1
