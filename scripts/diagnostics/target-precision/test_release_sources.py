import hashlib
import json
from pathlib import Path

import pytest
import release_sources as r


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setattr(r, 'NAMESPACES', (tmp_path,))
    task = tmp_path/'task'
    source, controls = task/'source', task/'controls'
    source.mkdir(parents=True)
    controls.mkdir()
    data = b'tiny source'
    (source/'weights').write_bytes(data)
    s = dict(path='weights', size=len(data), sha256=sha(data),
             url='https://huggingface.co/Qwen/Qwen3.8-27B/resolve/'+'a'*40+'/weights')
    plan = dict(schema='epyc.target-precision.weight-plan.v1', base=dict(repo='Qwen/Qwen3.8-27B', revision='a'*40),
                converter_commit='b'*40, sources=[s])
    raw = json.dumps(plan).encode()
    common = dict(status='COMPLETE', plan_sha256=sha(raw))
    def put(name, obj):
        p = controls/name
        p.write_text(json.dumps(obj))
        return dict(path=str(p), sha256=sha(p.read_bytes()))
    acquisition = dict(**common, worker_reaped=True, worker_returncode=0,
                       files=[dict(source=s, path=str(source/'weights'), size=len(data), sha256=sha(data))])
    ar = put('acquisition.json', acquisition)
    output_path = task/'BF16.gguf'
    output_path.write_bytes(b'output')
    output = dict(path=str(output_path), quant='BF16', size=6, sha256=sha(b'output'))
    tool = task/'converter'
    tool.write_bytes(b'tool')
    log = controls/'conversion.log'
    log.write_bytes(b'log')
    build = dict(**common, source_commit=plan['converter_commit'], tool=dict(path=str(tool), sha256=sha(b'tool')))
    br = put('build.json', build)
    report = dict(**common, verdict='PASS', output=output, acquisition=ar)
    tr, kr = put('tensor.json', report), put('tokenizer.json', report)
    conversion = dict(**common, schema='epyc.target-precision.conversion.v1', base=plan['base'],
                      acquisition=ar, source_root=str(source), tensor_correspondence='verified',
                      tokenizer_correspondence='verified', build=br, tensor_report=tr, tokenizer_report=kr,
                      output=output, log=dict(path=str(log), sha256=sha(b'log')))
    cr = put('conversion.json', conversion)
    return dict(raw_plan=raw, task_root=task, source=source, controls=controls,
                acquisition_ref=ar, conversion_ref=cr, event=controls/'release.json'), put, conversion, acquisition


def test_release_only_sources_and_retain_evidence(case):
    args, _, _, _ = case
    before = set(args['controls'].iterdir())
    result = r.release_sources(**args)
    assert result['status'] == 'RELEASED' and result['removed'] == ['weights']
    assert result['verified_weights'] is False
    assert list(args['source'].iterdir()) == []
    assert before <= set(args['controls'].iterdir())
    assert (args['task_root']/'BF16.gguf').read_bytes() == b'output'
    assert json.loads(args['event'].read_text()) == result
    with pytest.raises(ValueError):
        r.release_sources(**args)


@pytest.mark.parametrize('mode', ['source-corrupt', 'foreign', 'symlink', 'hardlink', 'output-corrupt',
    'receipt-corrupt', 'failed-acquisition', 'not-reaped', 'wrong-base', 'tensor', 'tokenizer',
    'wrong-plan', 'wrong-root', 'tool-corrupt', 'log-corrupt', 'report-fail', 'report-output', 'build-commit',
    'namespace', 'event-symlink', 'source-symlink'])
def test_refusal_preserves_sources(case, monkeypatch, mode):
    args, put, conv, acquired = case
    source = args['source']
    if mode == 'source-corrupt': (source/'weights').write_bytes(b'bad')
    elif mode == 'foreign': (source/'other').write_bytes(b'foreign')
    elif mode == 'symlink':
        (source/'weights').unlink()
        (source/'weights').symlink_to(args['task_root']/'BF16.gguf')
    elif mode == 'hardlink':
        import os
        os.link(source/'weights', args['task_root']/'other-link')
    elif mode == 'output-corrupt': (args['task_root']/'BF16.gguf').write_bytes(b'bad')
    elif mode == 'receipt-corrupt': Path(args['acquisition_ref']['path']).write_text('{}')
    elif mode in ('failed-acquisition', 'not-reaped'):
        acquired['status' if mode == 'failed-acquisition' else 'worker_reaped'] = 'FAILED' if mode == 'failed-acquisition' else False
        args['acquisition_ref'] = put('acquisition.json', acquired)
    elif mode == 'wrong-base': conv['base'] = {}
    elif mode == 'tensor': conv['tensor_correspondence'] = 'partial'
    elif mode == 'tokenizer': conv['tokenizer_correspondence'] = 'unknown'
    elif mode == 'wrong-plan': conv['plan_sha256'] = '0'*64
    elif mode == 'wrong-root': conv['source_root'] = '/elsewhere'
    elif mode == 'tool-corrupt': (args['task_root']/'converter').write_bytes(b'bad')
    elif mode == 'log-corrupt': (args['controls']/'conversion.log').write_bytes(b'bad')
    elif mode in ('report-fail', 'report-output'):
        report = json.loads(Path(conv['tensor_report']['path']).read_text())
        report['verdict' if mode == 'report-fail' else 'output'] = 'FAIL' if mode == 'report-fail' else {}
        conv['tensor_report'] = put('tensor.json', report)
    elif mode == 'build-commit':
        build = json.loads(Path(conv['build']['path']).read_text())
        build['source_commit'] = 'c'*40
        conv['build'] = put('build.json', build)
    elif mode == 'namespace': monkeypatch.setattr(r, 'NAMESPACES', (Path('/unused'),))
    elif mode == 'event-symlink': args['event'].symlink_to(args['task_root']/'BF16.gguf')
    elif mode == 'source-symlink':
        source.rename(args['task_root']/'renamed')
        source.symlink_to(args['task_root']/'renamed')
    args['conversion_ref'] = put('conversion.json', conv)
    with pytest.raises((ValueError, OSError)):
        r.release_sources(**args)
    assert (source/'weights').exists()


def test_partial_unlink_failure_retains_failed_journal(case, monkeypatch):
    args, _, _, _ = case
    def refuse(*a, **k): raise OSError('injected unlink failure')
    monkeypatch.setattr(r.os, 'unlink', refuse)
    with pytest.raises(OSError): r.release_sources(**args)
    receipt = json.loads(args['event'].read_text())
    assert receipt['status'] == 'FAILED' and receipt['removed'] == []
    assert (args['source']/'weights').exists()
