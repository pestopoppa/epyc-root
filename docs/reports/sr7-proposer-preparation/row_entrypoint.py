#!/usr/bin/env python3
"""SR-7 pinned private window entrypoint and non-science rowflow smoke."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from contained_lifecycle import SmokeAdmission, capture_contained, _write_once, _json
from startup_identity import StartupIdentity
from keeper_admission import KeeperAdmission
from bench_claim import FullHostBenchClaim
from window_coordinator import run_window

SEAL = Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr7-next-20261102/plan-seal.json')
SEAL_SHA = '19de2b1838b9a9e3176c0f5dd1b99b0fce5978295c6bec1b863dca884ff22391'
PREFLIGHT_SHA = '406a231e6ab233c2c8bd071977858ab1a929c8241cd90429302fc33fe445d44b'


def _read(path, sha):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError('real absolute input required')
    raw = path.read_bytes()
    if len(raw) > 32*1024*1024 or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('pinned input mismatch')
    return raw


def _dir(root, path):
    root, path = Path(root), Path(path)
    if (not root.is_absolute() or not root.is_dir() or root.is_symlink() or
            not path.is_absolute() or not path.is_dir() or path.is_symlink() or
            root.resolve() not in path.resolve().parents):
        raise ValueError('existing directory beneath scratch required')
    return path


def run(config, env):
    if not isinstance(config, dict) or config.get('schema') != 'sr7.row-config.v1':
        raise ValueError('invalid row config')
    if env.get('FILLER_ID') != config['row_id']:
        raise ValueError('row identity mismatch')
    seal = json.loads(_read(SEAL, SEAL_SHA))
    if seal.get('schema') != 'sr7.preguarded-plan.v1' or config['window'] not in seal['windows']:
        raise ValueError('invalid plan seal or window')
    inputs = {name: _read(v['path'], v['sha256']) for name, v in seal['inputs'].items()}
    plan = json.loads(inputs['runtime_plan'])
    if plan.get('schema') != 'sr7.runtime-plan.v1' or plan['model_preflight_sha256'] != PREFLIGHT_SHA:
        raise ValueError('invalid runtime plan')
    preflight = Path(plan['model_preflight_path'])
    receipt = json.loads(_read(preflight, PREFLIGHT_SHA))
    root = Path(config['scratch_root'])
    output = _dir(root, config['output_root'])
    exposure = Path('/mnt/raid0/llm/tmp/speculative-decoding-mtp/sr7-next-20261102/exposure')
    if (str(exposure) != config['exposure_root'] or exposure.is_symlink() or not exposure.is_dir()
            or exposure.resolve() != exposure):
        raise ValueError('campaign exposure directory mismatch')
    smoke_root = _dir(root, config['smoke_output_root'])
    stop, deadline = Path(env['FILLER_STOPFILE']), int(env['FILLER_DEADLINE'])
    smoke = env.get('FILLER_DRYRUN') == '1'
    if smoke:
        admission = SmokeAdmission(stop_path=stop, deadline=min(deadline, time.time() + 300))
    else:
        grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (config['row_id'] + '.grant')
        claim = FullHostBenchClaim(config['row_id'], config['guard_sha256'], Path(config['guard_path']))
        admission = KeeperAdmission(env=env, row_id=config['row_id'], grant_path=grant,
                                    stop_path=stop, ownership_check=claim)
    if admission() is not True:
        raise ValueError('admission unavailable')
    cpus = set(os.sched_getaffinity(0))
    libdir = str(Path(receipt['build_root']) / 'bin')
    child_env = dict(env, LD_LIBRARY_PATH=libdir, HIP_VISIBLE_DEVICES='-1',
                     ROCR_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='1')
    port = plan['port']
    if smoke:
        smoke_dir = smoke_root / ('attempt-' + uuid.uuid4().hex)
        smoke_dir.mkdir(mode=0o700)
        argv = [str(Path(libdir)/'llama-server'), '-m', receipt['smoke_model']['path'],
                '--host', '127.0.0.1', '--port', str(port), '-ngl', '0', '-c', '512',
                '-t', str(len(cpus)), '-np', '1', '--spec-type', 'none']
        verify = StartupIdentity(preflight=preflight, preflight_sha256=PREFLIGHT_SHA,
                                 expected_argv=argv, cpus=cpus, admission=admission,
                                 timeout_s=120, smoke=True)
        result = capture_contained(root=smoke_dir, request_id='smoke',
            payload={'prompt':'The answer is', 'seed':101, 'cache_prompt':False, 'stream':False,
                     'n_predict':8, 'temperature':0.0}, expected_names=[], port=port, timeout_s=30,
            admission=admission, argv=argv, env=child_env, cwd=str(root), verify=verify,
            trace_path=smoke_dir / 'server.log')
        _write_once(Path(env['FILLER_DRYRUN_RESULT_PATH']), _json(result))
        return result
    arms = plan['arms']
    if set(arms) != set(seal['arms']):
        raise ValueError('arm mismatch')
    verifiers = {}
    for name, argv in arms.items():
        if argv[:2] != ['/usr/bin/numactl', '--interleave=all']:
            raise ValueError('NUMA launch mismatch')
        verifiers[name] = StartupIdentity(preflight=preflight, preflight_sha256=PREFLIGHT_SHA,
            expected_argv=argv[2:], cpus=cpus, admission=admission, timeout_s=1800)
    timeout = config['request_timeout_s']
    def config_for_arm(window, prompt, mode, width):
        name = ('composed' if mode == 'composed' else 'mtp') + str(width)
        sampler = dict(plan['sampler'])
        payload = dict(sampler, prompt=prompt['rendered_prompt'], seed=prompt['seed'],
                       cache_prompt=False, stream=False, return_tokens=True)
        return dict(payload=payload, port=port, timeout_s=timeout, argv=arms[name], env=child_env,
                    cwd=str(root), verify=verifiers[name])
    corpus_sha = seal['inputs']['corpus']['sha256']
    result = run_window(packet_bytes=inputs['corpus'], expected_sha256=corpus_sha,
        authenticate=lambda data, digest: digest == corpus_sha and hashlib.sha256(data).hexdigest() == corpus_sha,
        window_id=config['window'], root=output, exposure_root=exposure,
        config_for_arm=config_for_arm, admission=admission)
    result_path = Path(config['result_path'])
    if not result_path.is_absolute() or root.resolve() not in result_path.parent.resolve().parents and result_path.parent.resolve() != root.resolve():
        raise ValueError('result path escapes scratch')
    _write_once(result_path, _json(result))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    args = parser.parse_args()
    run(json.loads(_read(args.config, args.config_sha256)), dict(os.environ))

if __name__ == '__main__':
    main()
