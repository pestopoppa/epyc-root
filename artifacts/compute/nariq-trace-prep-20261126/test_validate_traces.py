import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('validate_traces', Path(__file__).with_name('validate_traces.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rows():
    return [dict(session_id='a', split='calibration', token_ids=[1, 2, 3], model_written=[0, 1, 1]),
            dict(session_id='b', split='heldout', token_ids=[4, 5], model_written=[0, 1])]


def write(path, data):
    path.write_text(''.join(json.dumps(row) + '\n' for row in data))


def test_counts_and_digest(tmp_path):
    path = tmp_path / 'traces.jsonl'
    write(path, rows())
    result = module.validate(path)
    assert result['splits']['calibration'] == {'sessions': 1, 'tokens': 3, 'model_written': 2}
    assert len(result['sha256']) == 64


@pytest.mark.parametrize('mutation', ['length', 'boolean', 'zero', 'duplicate', 'missing_split'])
def test_reject_bad_inputs(tmp_path, mutation):
    data = rows()
    if mutation == 'length': data[0]['model_written'].pop()
    if mutation == 'boolean': data[0]['model_written'][0] = True
    if mutation == 'zero': data[0]['model_written'] = [0, 0, 0]
    if mutation == 'duplicate': data[1]['session_id'] = 'a'
    if mutation == 'missing_split': data.pop()
    path = tmp_path / 'traces.jsonl'
    write(path, data)
    with pytest.raises(ValueError): module.validate(path)
