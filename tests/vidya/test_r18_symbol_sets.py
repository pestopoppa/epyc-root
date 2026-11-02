import importlib.util
import json
from pathlib import Path
import pytest

MODULE = Path(__file__).resolve().parents[2] / 'scripts/vidya/producers/r18_symbol_sets.py'
spec = importlib.util.spec_from_file_location('r18_symbol_sets', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(tmp_path):
    comparator = tmp_path / 'comparator.py'
    comparator.write_text("def symbols(path,label): return set(path.read_text().split())\n"
                          "def device_symbols(path,label): return set(path.read_text().split()), 1\n")
    paths = [tmp_path / n for n in ('ac', 'cc', 'ah', 'ch')]
    for path, data in zip(paths, ('a b', 'a c', 'x y', 'x z')):
        path.write_text(data)
    rows = {}
    for kind, ai, ci in [('cpu', 0, 1), ('hip_host', 2, 3), ('hip_device', 2, 3)]:
        a, c = (set(paths[i].read_text().split()) for i in (ai, ci))
        row = dict(anchor_count=len(a), candidate_count=len(c), added=sorted(c-a), removed=sorted(a-c))
        if kind == 'hip_device': row.update(anchor_code_objects=1, candidate_code_objects=1)
        else: row.update(anchor_sha256=m.sha(paths[ai]), candidate_sha256=m.sha(paths[ci]))
        rows[kind] = row
    result = tmp_path / 'native.json'
    result.write_text(json.dumps(dict(schema='r18a.independent_symbol_identity.v1', comparisons=rows, symbol_identity_pass=False)))
    return comparator, result, paths


def test_valid_negative_preserves_exact_sets(tmp_path):
    comparator, result, paths = fixture(tmp_path)
    out = tmp_path / 'sets'
    receipt = m.capture(comparator, result, 1, *paths, out)
    assert len(receipt['artifacts_sha256']) == 6
    assert json.loads((out / 'cpu-anchor.json').read_text()) == ['a', 'b']
    assert all(m.sha(out / name) == digest for name, digest in receipt['artifacts_sha256'].items())


def test_mismatch_and_failed_comparator_leave_no_output(tmp_path):
    comparator, result, paths = fixture(tmp_path)
    out = tmp_path / 'sets'
    with pytest.raises(ValueError): m.capture(comparator, result, 2, *paths, out)
    paths[0].write_text('changed')
    with pytest.raises(ValueError): m.capture(comparator, result, 1, *paths, out)
    assert not out.exists()
