"""Transport completion only; this is not scientific floor admission."""
import hashlib
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
from floor_binding import verify_bound_receipt
from request_observer_join import validate_receipt
sys.path.insert(0, str(D / 'native'))
from source_census import validate as validate_source_census
from evidence_custody import read_receipt
from ring_archive import verify as verify_archive


def verify_compact_evidence(path, native):
    sources = native["source_provenance"]
    rings = native["rings"]
    verify_archive(str(path) + ".rings", native["archive_receipt"],
                   max_bytes=256 * 1024 * 1024,
                   expected_sources={x["event_id"] for x in sources},
                   source_provenance={x["event_id"]: x for x in sources},
                   expected_terminals={x["event_id"]: (x["ring"]["head"], x["ring"]["tail"]) for x in rings})


def main():
    runtime_prepared = json.loads((D / 'build-runtime-prepared.json').read_text())
    summary_path = D / 'input/full/calibrate-summary.json'
    event_path = D / 'input/full/request-boundaries.jsonl'
    summary = json.loads(summary_path.read_text())
    rows = [json.loads(line) for line in event_path.read_text().splitlines() if line.strip()]
    floor = json.loads(Path(summary['floor_file']).read_text())
    ok = (summary['schema'] == 'epyc.ds41_1017.calibrate_summary.v1'
          and summary['aa_pairs'] == 24 and summary['cmp_pairs'] == 5
          and summary['unit'] == 'process'
          and summary['build'] == '/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5'
          and len(rows) == 96 and verify_bound_receipt(floor, runtime_prepared=runtime_prepared)
          and summary['floor_content_sha256'] == floor['content_sha256'])
    binding = floor['request_binding']
    durable = {(launch['launch_ordinal'], phase): launch['phases'][phase]
               for launch in binding['launches']
               for phase in ('warmup', 'measurement')}
    seen = set()
    for row in rows:
        key = (row['launch_ordinal'], row['phase'])
        ref = durable.get(key)
        if ref is None or key in seen:
            return False
        seen.add(key)
        before, after = row['before'], row['after']
        ok = ok and all(row[k] == ref[k] for k in (
            'prompt_id', 'request_sha256', 'target', 'before', 'after',
            'placement_window_ns', 'placement_samples', 'placement_observation',
            'placement_continuous', 'contention_continuous', 'no_inference_scope',
            'native_observer'))
        ok = ok and row['status'] == 'observed-at-boundaries'
        ok = ok and before['target'] == after['target'] == row['target']
        ok = ok and before['tasks'] == after['tasks']
        ok = ok and before['global_holders'] == after['global_holders']
        ok = ok and before['monotonic_ns'] < after['monotonic_ns']
        ok = ok and before['preflight']['verdict'] == after['preflight']['verdict'] == 'PASS'
        ok = ok and row['placement_observation'] == 'sampled-during-request'
        ok = ok and 2 <= len(row['placement_samples']) <= 4096
        ok = ok and row['placement_continuous'] == row['contention_continuous'] == 'unproven'
        observer = row['native_observer']
        context = {field: row[field] for field in (
            'launch_ordinal', 'phase', 'slot_index', 'prompt_id', 'request_sha256')}
        validate_receipt(observer, request_context=context, target=row['target'],
                         placement_window_ns=row['placement_window_ns'])
        raw, _ = read_receipt(observer['evidence_path'], observer['evidence_sha256'])
        native = json.loads(raw)
        validate_source_census(native, set(range(96)))
        verify_compact_evidence(observer["evidence_path"], native)
        ok = ok and native.get('measurement_admission') == 'none'
        ok = ok and native.get('errors') == []
        ok = ok and native.get('markers') == observer['markers']
        ok = ok and native.get('target_observations') == observer['target_observations']
    return ok and seen == set(durable)


if __name__ == '__main__':
    try:
        raise SystemExit(0 if main() else 1)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise SystemExit(1)
