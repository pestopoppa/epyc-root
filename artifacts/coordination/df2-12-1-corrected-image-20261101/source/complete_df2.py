#!/usr/bin/env python3
"""Canonical v14 --complete-cmd for one DF2 role, normal and real runs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib

from df2_parity import phase_requests
from run_role import phase_specs

ROOT = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape', choices=('frontdoor_mtp', 'architect_dflash'), required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--manifest', required=True)
    args = ap.parse_args()
    phase = os.environ.get('FILLER_QUAL_PHASE')
    if phase in ('normal', 'cutoff'):
        if phase != 'normal':
            return 1
        root = pathlib.Path(os.environ['FILLER_RESULTS_DIR'])
        normal = root / 'normal/QUAL-RESULT.json'
        proof = pathlib.Path(os.environ['WS58_QUAL_PROOF'])
        if not normal.is_file() or not proof.is_file():
            return 1
        data = json.loads(proof.read_text())
        writer = data.get('result_writer', {})
        return 0 if (writer.get('ok') is True and
                     writer.get('result_path') == str(normal) and
                     writer.get('sha256') == sha(normal)) else 1
    if phase:
        return 1
    out = pathlib.Path(args.out)
    terminal = out / 'TERMINAL.json'
    closure = out / 'BELIEF-ROLE-CLOSURE.json'
    if not terminal.is_file() or not closure.is_file():
        return 1
    term = json.loads(terminal.read_text())
    closed = json.loads(closure.read_text())
    if (term.get('state') != 'COMPLETE' or term.get('shape') != args.shape or
        term.get('manifest_sha256') != sha(args.manifest) or
        closed.get('status') != 'COMPLETE' or closed.get('shape') != args.shape or
        closed.get('manifest_sha256') != sha(args.manifest) or
        closed.get('planned_request_count') != 152):
        return 1
    if len(closed.get('identities', [])) != 152:
        return 1
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    expected = {(phase, c, request_id)
                for phase, c, _np, _spec in phase_specs()
                for request_id, _prompt in phase_requests(manifest, phase, c)}
    observed = [(item.get('phase'), item.get('c'), item.get('request_id'))
                for item in closed['identities']]
    if len(expected) != 152 or len(set(observed)) != 152 or set(observed) != expected:
        return 1
    for identity in closed['identities']:
        phase, c, request_id = (identity.get('phase'), identity.get('c'),
                                identity.get('request_id'))
        if (not isinstance(phase, str) or type(c) is not int or
            not isinstance(request_id, str) or '/' in request_id):
            return 1
        folder = out / f'{phase}-c{c}' / 'responses' / 'BELIEF-WRITE'
        record_path = folder / (request_id + '.json')
        binding_path = folder / 'NATIVE-BINDING.json'
        if not record_path.is_file() or not binding_path.is_file():
            return 1
        if (sha(record_path) != identity.get('record_sha256') or
            sha(binding_path) != identity.get('native_binding_sha256')):
            return 1
        record = json.loads(record_path.read_text())
        binding = json.loads(binding_path.read_text())
        responses = folder.parent
        wire = responses / 'wire' / (request_id + '.completion')
        response_path = responses / (request_id + '.response.json')
        if (record.get('status') != identity.get('status') or
            record.get('status') not in ('ok', 'error') or
            not record.get('response_record_sha256') or
            not record.get('completion_request_sha256') or
            not record.get('completion_wire_sha256') or
            binding.get('server_drain_pass') is not True):
            return 1
        if record['status'] == 'error' and not record.get('error'):
            return 1
        for path, checksum in ((response_path, record['response_record_sha256']),
                               (pathlib.Path(str(wire) + '.request.bin'), record['completion_request_sha256']),
                               (pathlib.Path(str(wire) + '.wire.json'), record['completion_wire_sha256'])):
            if not path.is_file() or sha(path) != checksum:
                return 1
        response_bytes = pathlib.Path(str(wire) + '.response.bin')
        if (record.get('completion_response_sha256') is not None and
            (not response_bytes.is_file() or sha(response_bytes) != record['completion_response_sha256'])):
            return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
