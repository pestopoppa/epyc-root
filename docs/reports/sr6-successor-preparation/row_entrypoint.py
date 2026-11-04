#!/usr/bin/env python3
"""Sealed SR-6 window entrypoint; publication requires independent preflight.

The config digest is pinned in the launcher. Weights are never hashed here:
the pre-publication hash must be bound to the recorded stat by the author.
Each smoke is a separate, tiny, non-science completion; it cannot establish
performance, containment on a differently configured machine, or SR-6.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from bench_claim import FullHostBenchClaim
from keeper_admission import KeeperAdmission
from lifecycle_adapter import LifecycleAdapters
from native_worker import ARMS, canonical, capture_request, digest, exclusive_json
from runtime_manifest import verify_runtime_manifest
from server_lifecycle import with_server
from verified_post import VerifiedPost, process_starttime
from window_capture import capture_window
from worker import build_schedule


def _load(path, sha):
    if not isinstance(path, str) or not Path(path).is_absolute() or Path(path).is_symlink():
        raise ValueError('absolute non-symlink input required')
    data = Path(path).read_bytes()
    if len(data) > 32 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != sha:
        raise ValueError('pinned input digest mismatch')
    return json.loads(data)


def _model(path, expected):
    p = Path(path)
    if not p.is_absolute() or p.is_symlink() or not p.is_file():
        raise ValueError('model path unavailable')
    stat = p.stat()
    actual = dict(dev=stat.st_dev, ino=stat.st_ino, size=stat.st_size,
                  mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns)
    if actual != expected:
        raise ValueError('model changed since pre-publication hashing')


def _below(root, child):
    root, child = Path(root), Path(child)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ValueError('invalid scratch root')
    if not child.is_absolute() or child.is_symlink() or not child.is_dir():
        raise ValueError('invalid output root')
    if root.resolve() not in child.resolve().parents:
        raise ValueError('output escapes scratch root')
    return child


def _argv(argv, *, binary, model, port, spec, width=None):
    if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x for x in argv):
        raise ValueError('server executable mismatch')
    if argv[:2] == ['/usr/bin/numactl', '--interleave=all']:
        argv = argv[2:]
    if not argv or argv[0] != binary:
        raise ValueError('server executable mismatch')
    required = {'-m':model, '--host':'127.0.0.1', '--port':str(port), '-ngl':'0', '--spec-type':spec}
    if width is not None:
        required['--spec-draft-n-max'] = str(width)
    for flag, expected in required.items():
        if argv.count(flag) != 1 or argv.index(flag) + 1 >= len(argv) or argv[argv.index(flag) + 1] != expected:
            raise ValueError('server argument mismatch: ' + flag)


def run(config, env):
    if not isinstance(config, dict) or config.get('schema') != 'sr6.row-config.v1':
        raise ValueError('invalid row config')
    if config.get('preflight_status') != 'VERIFIED':
        raise ValueError('pre-publication input preflight incomplete')
    receipt = _load(config['preflight_receipt'], config['preflight_receipt_sha256'])
    if receipt.get('schema') != 'sr6.model-preflight.v1':
        raise ValueError('model preflight receipt unavailable')
    for prefix in ('model', 'smoke_model'):
        for suffix in ('path', 'sha256'):
            if receipt.get(prefix + '_' + suffix) != config.get(prefix + '_' + suffix):
                raise ValueError('model receipt does not match sealed config')
        if (receipt.get(prefix + '_stat_before') != config.get(prefix + '_stat') or
                receipt.get(prefix + '_stat_after') != config.get(prefix + '_stat')):
            raise ValueError('model identity changed during preflight')
    smoke = env.get('FILLER_DRYRUN') == '1'
    root = Path(config['scratch_root'])
    output = _below(root, config['smoke_output'] if smoke else config['output'])
    if smoke:
        output = output / ('attempt-' + uuid.uuid4().hex)
        output.mkdir(mode=0o700)
    if env.get('FILLER_ID') != config['row_id']:
        raise ValueError('row identity mismatch')
    packet = _load(config['packet_path'], config['packet_file_sha256'])
    if digest(canonical(packet)) != config['packet_sha256']:
        raise ValueError('packet semantic digest mismatch')
    build_schedule(packet)
    if digest(canonical(config['argv_by_arm'])) != packet['seals']['launch']:
        raise ValueError('launch seal mismatch')
    build_root = Path(config['build_root'])
    verify_runtime_manifest(build_root, config['runtime_manifest_sha256'])
    _model(config['smoke_model_path'] if smoke else config['model_path'],
           config['smoke_model_stat'] if smoke else config['model_stat'])
    if packet['seals']['model'] != config['model_sha256']:
        raise ValueError('model seal mismatch')
    binary = str(build_root / 'bin' / 'llama-server')
    if set(config['argv_by_arm']) != set(ARMS):
        raise ValueError('arm set mismatch')
    for arm, (spec, width) in ARMS.items():
        _argv(config['argv_by_arm'][arm], binary=binary, model=config['model_path'],
              port=config['port'], spec=spec, width=width)
    _argv(config['smoke_argv'], binary=binary, model=config['smoke_model_path'],
          port=config['port'], spec='none')
    if config['smoke_model_path'] == config['model_path']:
        raise ValueError('smoke model must be separate')
    stop = Path(env['FILLER_STOPFILE'])
    deadline = int(env['FILLER_DEADLINE'])
    if smoke:
        if len(os.sched_getaffinity(0)) > 4:
            raise ValueError('smoke must be limited to four CPUs')
        admission = lambda: not os.path.lexists(stop) and time.time() < deadline
    else:
        grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (config['row_id'] + '.grant')
        admission = KeeperAdmission(env=env, row_id=config['row_id'], grant_path=grant,
            stop_path=stop, ownership_check=FullHostBenchClaim(config['row_id'], config['guard_sha256'], Path(config['guard_path'])))
    if admission() is not True:
        raise ValueError('admission unavailable')
    if smoke:
        argv = {arm: config['smoke_argv'] for arm in config['argv_by_arm']}
    else:
        argv = config['argv_by_arm']
    child_env = dict(env, LD_LIBRARY_PATH=str(build_root / 'bin'), HIP_VISIBLE_DEVICES='-1',
                     ROCR_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='1')
    evidence_dir = output / 'servers'
    evidence_dir.mkdir(exist_ok=False)
    adapter = LifecycleAdapters(argv_by_arm=argv, env=child_env, cwd=str(root),
        library_dir=str(build_root / 'bin'), build_root=build_root, port=config['port'],
        admission_check=admission, evidence_dir=evidence_dir,
        startup_timeout_s=120 if smoke else 1800)
    def verify_and_capture(process, arm):
        proof = adapter.verify_ready_and_identity(process, arm)
        birth = proof['starttime_ticks']
        proc = Path('/proc') / str(process.pid)
        status = (proc / 'status').read_text()
        numa = (proc / 'numa_maps').read_text()
        if ('Cpus_allowed_list:' not in status or not numa or
                process.poll() is not None or process_starttime(process.pid) != birth or
                admission() is not True):
            raise ValueError('placement evidence unavailable')
        if not smoke and not any('interleave:' in line for line in numa.splitlines()):
            raise ValueError('interleave policy not observed in NUMA maps')
        name = f'{process.pid}-{birth}.placement.json'
        proof['placement_record_sha256'] = exclusive_json(evidence_dir / name,
            {'schema':'sr6.placement.v1', 'pid':process.pid, 'starttime_ticks':birth,
             'status':status, 'numa_maps':numa,
             'limitations':['point-in-time observation; residency and placement require analysis']})
        return proof
    if smoke:
        prompt = {'id': 'smoke-private', 'rendered': config['smoke_prompt'], 'seed': 101,
                  'rendered_sha256': digest(config['smoke_prompt'].encode())}
        post = VerifiedPost(port=config['port'], timeout_s=30, max_response_bytes=1024*1024,
                            deadline=deadline, stop_file=stop, admission_check=admission)
        def one(server):
            return capture_request(output, window='smoke', block=0, arm='mtp3', prompt=prompt,
                sampler={'temperature': 0.0, 'n_predict': 8},
                server_record_sha256=server.evidence['server_record_sha256'],
                post=lambda payload: post(server, payload))
        record = with_server(arm='mtp3', admission_check=admission, spawn=adapter.spawn,
            verify_ready_and_identity=verify_and_capture, run=one, drain=adapter.drain)
        if record.get('state') != 'raw' or record.get('http_status') != 200:
            raise ValueError('smoke completion failed')
        result = {'schema':'sr6.smoke.v1', 'state':'COMPLETE', 'science':False, 'verdict':None}
        result_path = Path(env['FILLER_DRYRUN_RESULT_PATH'])
    else:
        result_path = Path(config['result_path'])
        if root.resolve() not in result_path.resolve().parents:
            raise ValueError('result path escapes scratch root')
        try:
            result = capture_window(packet=packet, packet_sha256=config['packet_sha256'],
                window=config['window'], output=output,
                keeper_args={'env':env, 'row_id':config['row_id'], 'grant_path':grant,
                             'stop_path':stop, 'guard_sha256':config['guard_sha256'],
                             'guard_path':Path(config['guard_path'])},
                spawn=adapter.spawn, verify_ready_and_identity=verify_and_capture,
                port=config['port'], timeout_s=config['request_timeout_s'], max_response_bytes=4*1024*1024,
                drain=adapter.drain)
        except Exception as exc:
            exclusive_json(result_path, {'schema':'sr6.window-result.v1', 'state':'PARTIAL',
                'decision':'UNKNOWN', 'window':config['window'], 'error_type':type(exc).__name__,
                'error':str(exc), 'verdict':None})
            raise
        result['decision'] = 'UNKNOWN'
        result['limitations'].append('one window only; placement and residency must be analyzed')
    exclusive_json(result_path, result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    args = parser.parse_args()
    config = _load(args.config, args.config_sha256)
    run(config, dict(os.environ))


if __name__ == '__main__':
    main()
