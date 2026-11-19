#!/usr/bin/env python3
"""Reconstruct the published successor packet and replay offline controls."""
import argparse
import base64
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


ARCHIVE = Path(__file__).resolve().parent
PACKET = ARCHIVE.parent
REPO = PACKET.parents[2]
SCRATCH = Path('/mnt/raid0/llm/tmp/vidya-belief-substrate')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(path):
    record = json.loads(path.read_bytes())
    raw = base64.b64decode(record['bytes_b64'], validate=True)
    if digest(raw) != record['sha256']:
        raise ValueError(f'archived envelope digest differs: {path}')
    return raw


def archived_bytes(name):
    for directory in (ARCHIVE, PACKET):
        path = directory / name
        if path.is_file():
            return path.read_bytes()
        envelope = directory / f'{name}.original-bytes.json'
        if envelope.is_file():
            return decode(envelope)
    raise FileNotFoundError(name)


def reconstruct(directory):
    manifest = (ARCHIVE / 'SOURCE.sha256').read_bytes()
    for line in manifest.decode().splitlines():
        expected, name = line.split('  ', 1)
        raw = archived_bytes(name)
        if digest(raw) != expected:
            raise ValueError(f'published SOURCE.sha256 differs: {name}')
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    with (directory / 'SOURCE.sha256').open('xb') as stream:
        stream.write(manifest)


def rejects(check, expected):
    try:
        check()
    except ValueError as exc:
        if expected not in str(exc):
            raise
    else:
        raise AssertionError(f'accepted invalid input, expected {expected!r}')


def stage_witness(capture, expected, directory):
    # The archive keeps the original plan bytes. Rebind scratch paths only
    # in the in-memory plan used to emulate staging in an isolated directory.
    plan = copy.deepcopy(expected)
    witness = next(entry for entry in plan['source_witnesses']
                   if Path(entry['path']).name == 'cpu-feasibility.json')
    original_inode = witness['stat'][1]
    target = directory / 'cpu-feasibility.json'
    witness['path'] = str(target)
    for key in ('smoke_model', 'model_hash_witness', 'prior_frontdoor_json_mismatch'):
        snapshot = plan[key]['snapshot']
        plan[key]['snapshot'] = str(directory / Path(snapshot).name)
    assert target.stat().st_ino != original_inode
    capture.verify_files(plan)
    print('PASS staged witness with a new inode and the original bytes')
    target.write_bytes(target.read_bytes() + b' ')
    rejects(lambda: capture.verify_files(plan), 'copied source witness content drift')
    print('PASS corrupted staged witness refused')


def pair_controls(capture, pair, plan, directory):
    validator_path = REPO / '.claude/skills/kernel-promotion/scripts/quality_parity.py'
    spec = importlib.util.spec_from_file_location('quality_parity', validator_path)
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)

    items = plan['items']
    pair.verify_pairs(items)
    capture.read_requests(plan)
    previous = {path.read_bytes() for other in PACKET.parent.glob('quality-pack-*')
                if other != PACKET for path in other.glob('requests/*.json')}
    grouped = {}
    for item in items:
        body = item['request_body']
        validator._request(body, '/completion')
        wire = (directory / plan['request_files'][item['id']]['path']).read_bytes()
        assert capture.canonical(body) == wire
        assert wire not in previous
        cap_free = {key: value for key, value in body.items() if key != pair.CAP_KEY}
        grouped.setdefault(item['dflash_pair'], []).append(
            (body[pair.CAP_KEY], 'dspark-dflash', validator._json_hash(cap_free), 'one-test-server'))
    validator._pair_check(grouped, 'offline-control')
    print('PASS four cap-0/7 pairs, exact request bytes, cross-packet uniqueness, comparator pair admission')

    changed = copy.deepcopy(items)
    changed[1]['request_body']['seed'] += 1
    rejects(lambda: pair.verify_pairs(changed), 'pair bodies differ beyond cap')
    changed = copy.deepcopy(grouped)
    key = next(iter(changed))
    cap, shape, body_hash, _ = changed[key][1]
    changed[key][1] = (cap, shape, body_hash, 'different-test-server')
    rejects(lambda: validator._pair_check(changed, 'offline-control'), 'server instance')
    print('PASS changed cap-free request and cross-server pair refused')


def telemetry_controls(pair, plan):
    raw = decode(ARCHIVE / 'native-smoke.response.json.original-bytes.json')
    response = json.loads(raw)
    assert pair.verify_response(response, plan['smoke_items'][0], plan['recipes']['smoke_control']) == {}
    print('PASS original v10 small-model no-spec response replay')

    # The changed envelopes below are fixtures for the response validator.
    recipe = plan['recipes']['cpu_slice']
    disabled, enabled = plan['items'][:2]
    response['stop_type'] = 'eos'
    settings = response['generation_settings']
    settings.update({'speculative.types': 'none,draft-dflash', pair.CAP_KEY: 0})
    assert pair.verify_response(response, disabled, recipe) == {}
    settings[pair.CAP_KEY] = 7
    response['timings'].update(draft_n=35, draft_n_accepted=5)
    assert pair.verify_response(response, enabled, recipe) == {'draft_n': 35, 'draft_n_accepted': 5}
    for field, value in (('draft_n', 0), ('draft_n_accepted', 36)):
        broken = copy.deepcopy(response)
        broken['timings'][field] = value
        rejects(lambda: pair.verify_response(broken, enabled, recipe), 'native draft counters contradict cap')
    broken = copy.deepcopy(response)
    broken['generation_settings'][pair.CAP_KEY] = 0
    rejects(lambda: pair.verify_response(broken, enabled, recipe), 'native response cap differs')
    print('PASS cap echo and draft-counter fixtures, including three corrupted-response refusals')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reconstruct', type=Path,
                        help='decode and verify the packet into a new directory, without running controls')
    args = parser.parse_args()
    if args.reconstruct:
        args.reconstruct.mkdir()
        reconstruct(args.reconstruct)
        print('PASS reconstructed original successor SOURCE.sha256')
        return
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dflash2-offline-', dir=SCRATCH) as temporary:
        directory = Path(temporary).resolve()
        reconstruct(directory)
        print('PASS reconstructed original successor SOURCE.sha256')
        sys.path.insert(0, str(directory))
        capture = importlib.import_module('capture')
        pair = importlib.import_module('pair')
        plan = json.loads((directory / 'plan.json').read_bytes())
        stage_witness(capture, plan, directory)
        pair_controls(capture, pair, plan, directory)
        telemetry_controls(pair, plan)


if __name__ == '__main__':
    main()
