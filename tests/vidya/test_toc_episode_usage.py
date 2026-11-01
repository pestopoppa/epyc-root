"""Strict trajectory binding for prospective TOC episode usage."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'vidya'))
from adapters import toc_ab, _native_sidecar as ns
from claim_tuple import to_frames


def capture(tmp_path, usage, events_extra=()):
    events = [{'task_id': 't', 'event': 'final'}, *events_extra,
              {'task_id': 't', 'event': 'episode_usage', 'graph_attempts': 1, 'usage': usage}]
    events[0].update(terminal_state='finished', turns=1, rolling_input_tokens=10,
                     rolling_input_tokens_observed_turns=1, prefix_cache_invalidations=0,
                     compressor_wall_s=0)
    for seq, event in enumerate(events, 1):
        event.update(schema='epyc.orchestrator.trajectory_event.v1', seq=seq)
    raw = b''.join((json.dumps(e) + '\n').encode() for e in events)
    trajectory = tmp_path / 'traj'
    trajectory.write_bytes(raw)
    task = {'task_id': 't', 'terminal_state': 'finished', 'solved': True,
            'turns': 1, 'rolling_input_tokens': 10, 'prefix_cache_invalidations': 0,
            'compressor_wall_s': 0, 'episode_usage': usage,
            'trajectory_segment': {'offset': 0, 'length': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}
    arm = {'policy_digest': 'a'*64, 'trigger_fraction': None, 'window_denominator': 'ctx',
           'summary_placement': 'none', 'is_control': True, 'tasks': [task]}
    sidecar = toc_ab.write_belief_measurements(tmp_path, run_id='r', producer='fixture',
                trajectory_path=trajectory, arms={'a': arm}, emitted_at='2026-10-21T10:00:00Z')
    return sidecar, trajectory


def test_usage_reopens_and_projects_each_observed_value(tmp_path):
    usage = {'status':'complete', 'backend_attempts': 2, 'cached_replays': 1,
             'observed_input_calls': 2, 'observed_output_calls': 2,
             'total_input_tokens': 10, 'total_output_tokens': 3, 'total_tokens': 13}
    sidecar, trajectory = capture(tmp_path, usage)
    natives = toc_ab.native_rows(sidecar)
    projected = {n.get('episode_field'): toc_ab.project(n) for n in natives}
    assert projected['total_tokens'].value == 13
    assert 'cached_replays=1' in projected['total_tokens'].claim
    assert 'usage=complete' in projected['status'].claim
    frames = to_frames(projected['total_tokens'], as_of='2026-10-21T10:00:00Z', adapter_id='test')
    assert frames[2]['assertion']['value'] == 13
    row = json.loads(sidecar.read_text())
    row['extra']['tasks'][0]['episode_usage']['total_tokens'] = 14
    ns.seal(row)
    sidecar.write_text(json.dumps(row) + '\n')
    assert toc_ab.native_rows(sidecar) == ()
    trajectory.write_text('tampered')
    assert toc_ab.native_rows(sidecar) == ()


def test_partial_and_unknown_never_become_zero(tmp_path):
    usage = {'status':'partial', 'backend_attempts': 2, 'cached_replays': 0,
             'observed_input_calls': 1, 'observed_output_calls': 1,
             'total_input_tokens': None, 'total_output_tokens': None, 'total_tokens': None}
    sidecar, _ = capture(tmp_path, usage)
    natives = toc_ab.native_rows(sidecar)
    assert {n.get('episode_field') for n in natives} == {None, 'status'}
    status = toc_ab.project(next(n for n in natives if n.get('episode_field') == 'status'))
    assert 'backend_attempts=2' in status.claim and 'usage=partial' in status.claim
    unknown = dict(toc_ab.UNKNOWN_USAGE)
    sidecar, _ = capture(tmp_path, unknown)
    natives = toc_ab.native_rows(sidecar)
    assert len(natives) == 2 and 'usage=unknown' in toc_ab.project(natives[1]).claim


def test_duplicate_event_refuses_claimed_complete(tmp_path):
    usage = {'status':'complete', 'backend_attempts': 1, 'cached_replays': 0,
             'observed_input_calls': 1, 'observed_output_calls': 1,
             'total_input_tokens': 1, 'total_output_tokens': 2, 'total_tokens': 3}
    sidecar, _ = capture(tmp_path, usage, [{'task_id':'t', 'event':'episode_usage', 'usage':usage, 'graph_attempts':1}])
    assert toc_ab.native_rows(sidecar) == ()
