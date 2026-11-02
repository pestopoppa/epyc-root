import json

import pytest

from scripts.harness.hs4_file_scoring import canonical, score, validate_answer
from scripts.harness.hs4_file_suite import prepare_suite


def native_shape(answer, expected, method, config):
    assert method == "exact_match" and config == {"normalize": False}
    return answer == expected


@pytest.mark.parametrize("kind,answer", [
    ("lookup", {"path": "records/a.csv"}),
    ("inventory", {"total": 4}),
    ("reconciliation", {"mismatches": [{"item": "a", "left": 1, "right": 2}]}),
])
def test_strict_format_then_native_call(kind, answer):
    expected = canonical(answer)
    assert score(kind, expected, expected, native_shape)
    for invalid in ("extra\n" + expected, expected + "\n", " " + expected):
        assert not score(kind, invalid, expected, native_shape)


def test_negative_formats_and_structural_error():
    for kind, invalid in (
        ("lookup", '{"path":"a#b"}'),
        ("inventory", '{"total":true}'),
        ("inventory", '{"total":1,"total":1}'),
        ("reconciliation", '{"mismatches":[{"item":"a","left":1,"right":1}]}'),
        ("reconciliation", '{"mismatches":[{"item":"b","left":1,"right":2},{"item":"a","left":1,"right":2}]}'),
    ):
        with pytest.raises(ValueError):
            validate_answer(kind, invalid)
    assert not score("inventory", '{"total":2}', '{"total":3}', native_shape)
    assert not score("inventory", "[" * 1500 + "]" * 1500, '{"total":3}', native_shape)
    with pytest.raises(TypeError):
        score("inventory", '{"total":2}', '{"total":2}', lambda *_: None)


def test_generated_splits_keep_oracles_separate_and_distinct(tmp_path):
    public = tmp_path / "public"
    oracle = tmp_path / "private"
    rows = prepare_suite(public, oracle)
    assert len(rows) == 18
    assert sum(row["split"] == "development" for row in rows) == 6
    assert sum(row["split"] == "acceptance" for row in rows) == 12
    assert len({row["task"] for row in rows}) == 18
    for row in rows:
        expected = (oracle / f'{row["task"]}.json').read_text()
        assert validate_answer(row["family"], expected) == json.loads(expected)
        assert not list((public / row["task"]).glob("*.json"))
        assert (oracle / f'{row["task"]}.json').stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        prepare_suite(public, oracle)
    with pytest.raises(ValueError):
        prepare_suite(tmp_path / "nested", tmp_path / "nested" / "private")
