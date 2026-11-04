"""Model-free wiring controls only; no historical GPU evidence manufactured."""
import copy
import json

import pytest
from adapters import gpu_pool_native as g
from claim_tuple import grade


def fixture(tmp_path, family='matmul'):
    identity = {'source': {'commit': 'a' * 40, 'removed_worktree_dirty_state': 'UNKNOWN'},
                'artifacts': [{'path': '/synthetic/test', 'sha256': 'b' * 64}],
                'shim': {'path': '/synthetic/shim', 'sha256': 'c' * 64,
                         'original_source_digest_receipt': 'd' * 64,
                         'later_recreated_source_matches_receipt': False}}
    op = sorted(g.FAMILIES[family])[0]
    request = g.begin(family, f'ni-gpu-pool-{family}-20990101-v1', identity, [op], producer=__file__)
    argv = ['synthetic', '-o', op, '--suite-seed', '7']
    log = tmp_path / f'{family}.log'
    failed = f'  {op}(case=3) FAIL'
    log.write_text('ARGV ' + json.dumps(argv) + '\n' + f'  {op}(case=0) OK\n  {op}(case=1) not supported\n' + failed + '\n')
    native = dict(schema=g.NATIVE, model_free=True, row_id=request['row_id'],
                  invocation_token=request['invocation_token'], **copy.deepcopy(identity),
                  scope='candidate-local native CPU reference only',
                  environment={'GPU_POOL_SYNTHETIC':'control'},
                  runs=[dict(op=op, observed=3, passed=1, unsupported=1, failed=[failed],
                             argv=argv, log=str(log), log_sha256=g.file_sha(log), seed=7, rc=1)])
    return request, native


@pytest.mark.parametrize('family', sorted(g.FAMILIES))
def test_write_read_shared_grade_and_exact_limits(tmp_path, family):
    request, native = fixture(tmp_path, family)
    path = tmp_path / 'prospective.json'
    g.write_capture(path, request, native)
    claim, = g.read_capture(path)
    assert claim.value == 1 and claim.metric_direction == 'higher_better'
    assert grade(claim)[:2] == ('Judged', 'T0')
    assert claim.protocol_id == '' and claim.reps is None
    assert claim.extra['candidate_identity'] == request['identity']
    assert claim.extra['native_context']['environment'] == native['environment']
    assert claim.extra['native_run']['unsupported'] == 1
    assert claim.extra['native_run']['failed'] == native['runs'][0]['failed']
    assert 'device' not in claim.applicability and 'model_file' not in claim.applicability
    assert g.LIMIT in claim.claim
    assert g.frames_for_capture(path, as_of='2099-01-01T00:00:00+00:00')
    with pytest.raises(FileExistsError):
        g.write_capture(path, request, native)


@pytest.mark.parametrize('mutation', ['token', 'identity', 'partition', 'bool', 'argv', 'seed', 'log', 'count'])
def test_binding_and_log_controls(tmp_path, mutation):
    request, native = fixture(tmp_path)
    run = native['runs'][0]
    if mutation == 'token': native['invocation_token'] = '0' * 32
    if mutation == 'identity': native['source']['commit'] = 'e' * 40
    if mutation == 'partition': run['observed'] = 4
    if mutation == 'bool': run['passed'] = True
    if mutation == 'argv': run['argv'][2] = 'BAD_OP'
    if mutation == 'seed': run['seed'] = 8
    if mutation == 'log': run['log_sha256'] = 'f' * 64
    if mutation == 'count': run.update(passed=2, unsupported=0)
    with pytest.raises(g.ProjectionError): g.finish(request, native)


def test_pre_hook_attention_list_and_native_objects_have_no_projection():
    for history in ([], {}, {'schema': g.NATIVE, 'runs': []}, [{'op': 'ROPE'}]):
        assert g.project(history) == []


def test_resealed_capture_cannot_hide_changed_raw_log(tmp_path):
    request, native = fixture(tmp_path)
    path = tmp_path / 'prospective.json'
    g.write_capture(path, request, native)
    log = tmp_path / 'matmul.log'
    log.write_text(log.read_text().replace(' OK', ' FAIL'))
    with pytest.raises(g.ProjectionError): g.read_capture(path)


def test_tamper_and_missing_terminal_are_refused(tmp_path):
    request, native = fixture(tmp_path)
    record = g.finish(request, native)
    record['native']['runs'][0]['passed'] = 99
    with pytest.raises(g.ProjectionError): g.project(record)
    del native['runs'][0]['rc']
    with pytest.raises(g.ProjectionError): g.finish(request, native)
