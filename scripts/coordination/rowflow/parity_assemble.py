#!/usr/bin/env python3
"""Assemble owner-declared per-shape AK parity fragments and compare complete arms."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

FRAGMENT_SCHEMA = 'epyc.ak_gate.parity_fragment.v1'
PACK_SCHEMA = 'epyc.kernel_quality_parity_pack.v1'
CANDIDATE_SCHEMA = 'epyc.kernel_quality_parity_candidate.v1'
VALIDATOR = Path(__file__).resolve().parents[3] / '.claude/skills/kernel-promotion/scripts/quality_parity.py'


def assemble(pack_bytes, pin, fragments):
    if hashlib.sha256(pack_bytes).hexdigest() != pin:
        raise ValueError('pack SHA-256 mismatch')
    pack = json.loads(pack_bytes)
    if pack.get('schema') != PACK_SCHEMA:
        raise ValueError('unsupported parity pack schema')
    shapes = {s['id']: s for s in pack['shapes']}
    if len(shapes) != len(pack['shapes']):
        raise ValueError('duplicate pack shape')
    arms = {}
    for fragment in fragments:
        if fragment.get('schema') != FRAGMENT_SCHEMA or fragment.get('pack_sha256') != pin:
            raise ValueError('fragment schema or pack pin mismatch')
        arm, shape = fragment['arm'], fragment['shape']
        if shape not in shapes:
            raise ValueError(f'unknown shape {shape}')
        if shape in arms.setdefault(arm, {}):
            raise ValueError(f'duplicate shape {shape} for arm {arm}')
        expected = {i['id'] for i in pack['items'] if i['shape'] == shape}
        actual = [i['id'] for i in fragment['items']]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            raise ValueError(f'item coverage mismatch for {arm}/{shape}')
        arms[arm][shape] = fragment
    result = {}
    for arm, rows in arms.items():
        missing = sorted(set(shapes) - rows.keys())
        shas = {shape: row['argv_sha256'] for shape, row in sorted(rows.items())}
        if missing:
            result[arm] = {'status': 'incomplete', 'missing_shapes': missing, 'argv_sha256': shas}
            continue
        candidate = {'schema': CANDIDATE_SCHEMA, 'pack_sha256': pin,
                     'capture_source': pack['capture_source'], 'shapes': pack['shapes'],
                     'runtime': {shape: row['runtime'] for shape, row in rows.items()},
                     'items': [item for row in rows.values() for item in row['items']]}
        result[arm] = {'status': 'complete', 'argv_sha256': shas, 'candidate': candidate}
    return result


def record_report(fragment_path, fragment, report_path, verdict):
    """Attach the assembled observation to the matching row result, when present."""
    fragment_path = fragment_path.resolve()
    if fragment_path.parent.name != 'parity':
        return
    out = fragment_path.parent.parent
    result_path = out / 'RESULT.json'
    if not result_path.is_file():
        return
    result = json.loads(result_path.read_bytes())
    observed = result['correctness']['served_quality']['parity'][fragment['arm']]
    if (out / observed['fragment_path']).resolve() != fragment_path:
        raise ValueError(f'{result_path}: fragment does not match recorded observation')
    observed.update(report_path=str(report_path.resolve()), verdict=verdict, status=verdict)
    # A result may already contain a KEEP/NO_KEEP decision; assembling an
    # observation never rewrites that decision.
    with tempfile.NamedTemporaryFile(mode='w', dir=out, delete=False) as handle:
        temp = Path(handle.name)
        try:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temp, result_path)
        finally:
            temp.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack', required=True, type=Path)
    p.add_argument('--pack-sha256', required=True)
    p.add_argument('--output-dir', required=True, type=Path)
    p.add_argument('fragments', nargs='+', type=Path)
    a = p.parse_args()
    try:
        fragments = [json.loads(f.read_bytes()) for f in a.fragments]
        results = assemble(a.pack.read_bytes(), a.pack_sha256, fragments)
        a.output_dir.mkdir(parents=True, exist_ok=True)
        for arm, result in results.items():
            if not arm or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in arm):
                raise ValueError('invalid arm name')
            if result['status'] != 'complete':
                continue
            path = a.output_dir / f'{arm}.candidate.json'
            path.write_text(json.dumps(result.pop('candidate'), sort_keys=True, separators=(',', ':')) + '\n')
            cmd = [sys.executable, str(VALIDATOR), 'compare', '--pack', str(a.pack), '--pack-sha256', a.pack_sha256, '--candidate', str(path)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            report = a.output_dir / f'{arm}.report.json'
            report.write_text(proc.stdout or json.dumps({'status': 'invalid_input', 'error': proc.stderr}) + '\n')
            result.update(candidate_path=str(path), report_path=str(report), status=json.loads(report.read_text())['status'])
            for fragment_path, fragment in zip(a.fragments, fragments):
                if fragment['arm'] == arm:
                    record_report(fragment_path, fragment, report, result['status'])
        print(json.dumps(results, sort_keys=True))
        return 0 if results and all(r['status'] == 'pass' for r in results.values()) else 2
    except (ValueError, KeyError, OSError, TypeError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
