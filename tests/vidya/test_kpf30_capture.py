"""KPF-30 writer-to-shared-ladder contract, using synthetic stream fixtures only."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'vidya'))
from adapters import kpf30_capture as cap, kv_prefix_fork as kpf  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402

LINE = ('llama: KPF30 row=0 seq=3 n_tokens=2 n_seqs=2 swa=0 causal=1 n_kv=512 '
        'blocks=2 live=2 mixed=1 unknown=0 live_unknown=0 invalid_mask=0')


def start(p):
    return cap.Capture(p, run_id='r1', window_id='w1', host='host', binary_sha256='a' * 64,
                       prompt_set_sha256='b' * 64, argv=['server', '--device', 'none'], category='CANDIDATE')


def test_live_writer_projection_and_tamper(tmp_path):
    writer = start(tmp_path)
    assert not writer.feed('unrelated server log')
    assert writer.feed(LINE)
    row = writer.finish(0)
    native, = kpf.native_rows(tmp_path / 'belief_measurements.jsonl')
    claim = kpf.project(native)
    assert claim.value == 1 and claim.reps == 1
    assert claim.extra['counts']['live'] == 2 and grade(claim)[0]
    assert row['record_sha256'] == cap._digest({k: v for k, v in row.items() if k != 'record_sha256'})
    # A mutated witness cannot be verified as the attested bytes.
    (tmp_path / 'kpf30_rows.jsonl').write_text('{}\n')
    native, = kpf.native_rows(tmp_path / 'belief_measurements.jsonl')
    assert not kpf.project(native).attestation_present


def test_unknown_counts_remain_explicit_not_gate_result(tmp_path):
    writer = start(tmp_path)
    writer.feed(LINE.replace('unknown=0 live_unknown=0', 'unknown=1 live_unknown=1'))
    writer.finish(0)
    claim = kpf.project(kpf.native_rows(tmp_path / 'belief_measurements.jsonl')[0])
    assert claim.extra['counts']['unknown'] == 1
    assert 'decode-only or threshold verdict' in claim.claim


def test_failed_empty_or_malformed_no_sealed_claim(tmp_path):
    writer = start(tmp_path / 'failed')
    writer.feed(LINE)
    with pytest.raises(ValueError):
        writer.finish(1)
    assert not (tmp_path / 'failed' / 'belief_measurements.jsonl').exists()
    writer = start(tmp_path / 'empty')
    with pytest.raises(ValueError):
        writer.finish(0)
    assert not (tmp_path / 'empty' / 'belief_measurements.jsonl').exists()
    with pytest.raises(ValueError):
        cap.parse_observer(LINE.replace('mixed=1', 'mixed=3'))
    poisoned = start(tmp_path / 'poisoned')
    poisoned.feed(LINE)
    with pytest.raises(ValueError):
        poisoned.feed(LINE.replace('invalid_mask=0', 'invalid_mask=oops'))
    with pytest.raises(ValueError):
        poisoned.finish(0)
    assert not (tmp_path / 'poisoned' / 'belief_measurements.jsonl').exists()


def test_resealed_aggregate_refused_against_sealed_rows(tmp_path):
    writer = start(tmp_path)
    writer.feed(LINE)
    row = writer.finish(0)
    row['counts']['mixed'] = 2
    row['record_sha256'] = cap._digest({k: v for k, v in row.items() if k != 'record_sha256'})
    (tmp_path / 'belief_measurements.jsonl').write_text(json.dumps(row) + '\n')
    native, = kpf.native_rows(tmp_path / 'belief_measurements.jsonl')
    with pytest.raises(ProjectionError):
        kpf.project(native)


def test_owner_wrapper_streams_actual_child_and_seals_before_read(tmp_path):
    import sys
    manifest = tmp_path / 'prompts.json'
    manifest.write_text('{"fixture":true}')
    child = tmp_path / 'emit.py'
    child.write_text('import os\nassert os.environ["LLAMA_KPF30_MIXED_BLOCKS"] == "1"\n'
                     f'print({LINE!r})\n')
    out = tmp_path / 'out'
    assert cap.main(['--output', str(out), '--run-id', 'r2', '--window-id', 'w2',
                     '--prompt-manifest', str(manifest), '--category', 'BASELINE', '--',
                     sys.executable, str(child)]) == 0
    native, = kpf.native_rows(out / 'belief_measurements.jsonl')
    claim = kpf.project(native)
    assert claim.value == 1 and claim.attestation_present and grade(claim)[0]
