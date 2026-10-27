#!/usr/bin/env python3
"""Controls derived only from THIS granted native capture, never fabricated rows."""
import argparse
import copy
import json
import sys
from pathlib import Path
import finalize

def main(raw, invocation, finalized):
    assembly = finalize.verify_sources()
    original = finalize.load(invocation)
    rows = finalize.legacy.read_rows(raw)
    complete = finalize.legacy.validate_capture_rows(rows, n_chunk=24)
    assert len(complete) == 18 and len(rows) == 324
    refusals = []
    def refused(name, function):
        try:
            function()
        except (ValueError, KeyError, OSError):
            refusals.append(name)
        else:
            raise AssertionError(name + ' accepted invalid native input')
    refused('missing native position', lambda: finalize.legacy.validate_capture_rows(rows[:-1], n_chunk=24))
    refused('duplicate native position', lambda: finalize.legacy.validate_capture_rows(rows + rows[:1], n_chunk=24))
    bad = copy.deepcopy(rows); bad[0]['comparison'] = 'invented'
    refused('unbound comparison', lambda: finalize.legacy.validate_capture_rows(bad, n_chunk=24))
    bad_count = copy.deepcopy(rows); bad_count[0]['element_count'] = 0
    refused('invalid native element count', lambda: finalize.legacy.validate_capture_rows(bad_count, n_chunk=24))
    bad_energy = copy.deepcopy(rows); bad_energy[0]['sum_sq_error'] = float('nan')
    refused('nonfinite native statistic', lambda: finalize.legacy.validate_capture_rows(bad_energy, n_chunk=24))
    # Original invocation check reads a real native payload/model/binary. Mutation
    # records stay separate and cannot overwrite the original invocation or raw.
    for label, mutate in (
        ('failed native exit', lambda r: r['capture'].update(exit_code=1)),
        ('raw hash mismatch', lambda r: r['capture'].update(sha256='0'*64)),
        ('wrong explicit cache type', lambda r: r['argv'].__setitem__(r['argv'].index('-ctk')+1, 'f16')),
        ('wrong source pin', lambda r: r.update(producer_commit='0'*40)),
        ('native finish outside grant', lambda r: r['capture'].update(finished_at_utc='2099-01-01T00:00:00Z')),
    ):
        record = copy.deepcopy(original); mutate(record)
        file = finalized.parent / ('refusal-' + label.replace(' ', '-') + '.json')
        file.write_text(json.dumps(record) + '\n')
        refused(label, lambda: finalize.legacy.read_invocation(file, raw))
    skip = copy.deepcopy(original); skip['capture']['environment']['CKV_SKIP_K_GATE'] = '0'
    refused('false friend skip K env zero', lambda: finalize.check(skip, raw))
    # Reader controls use producer-authored native carrier rows and the same shared
    # projection. Unknown protocol must retain its observation rung (no new ladder).
    assembly = finalize.verify_sources()
    sys.path.insert(0, str(Path(assembly['root_candidate']) / 'scripts/vidya'))
    import claim_tuple
    from adapters import chunk_kv
    from adapters import _native_sidecar as ns
    native = chunk_kv.native_rows(finalized / 'chunk_kv.beliefs.jsonl')
    assert len(native) == 27
    for n in native:
        tup = chunk_kv.project(n)
        assert tup.protocol_id == ''
        q, t, reasons = claim_tuple.grade(tup)
        assert (q, t) == ('Judged', 'Located') and reasons
        assert json.loads(tup.extra['detail'])['invocation'] == original
    tampered = copy.deepcopy(native[0]['row']); tampered['value'] += 1
    assert chunk_kv.validate_row(tampered)
    changed = copy.deepcopy(native[0]['row']); changed['extra']['position_rows'][0]['delta'] += 1; ns.seal(changed)
    assert chunk_kv.validate_row(changed)
    print(json.dumps({'native_positions': 324, 'shared_tuples': 27, 'refusal_controls': refusals,
                      'unknown_protocol': 'existing shared grade Judged/Located', 'native_tamper_controls': 2}, sort_keys=True))

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--raw', type=Path, required=True); p.add_argument('--invocation', type=Path, required=True); p.add_argument('--finalized', type=Path, required=True)
    a = p.parse_args(); main(a.raw, a.invocation, a.finalized)
