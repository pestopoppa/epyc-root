import json
import os

import pytest

from scripts.harness.hs4_file_scoring import canonical, load_native_scorer, score, validate_answer
from scripts.harness.hs4_file_suite import prepare_suite, seal_suite, verify_seal


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


def test_scorer_pin_refuses_changed_source_and_symlink(tmp_path):
    path = tmp_path / "scorer.py"
    path.write_text("def score_answer(*args): return True\n")
    with pytest.raises(ValueError, match="digest"):
        load_native_scorer(path)
    link = tmp_path / "link.py"
    link.symlink_to(path)
    with pytest.raises(OSError):
        load_native_scorer(link)


def test_seal_detects_changed_fixture_or_writable_path(tmp_path):
    public, oracle = tmp_path / "public", tmp_path / "private"
    prepare_suite(public, oracle)
    digest = seal_suite(public, oracle)
    try:
        verify_seal(public, oracle, digest)
        target = public / "development-00" / "records"
        target.chmod(0o700)
        with pytest.raises(ValueError, match="writable"):
            verify_seal(public, oracle, digest)
        target.chmod(0o500)
        fixture = next(target.iterdir())
        fixture.chmod(0o600)
        fixture.write_text("changed")
        fixture.chmod(0o400)
        with pytest.raises(ValueError, match="differs"):
            verify_seal(public, oracle, digest)
    finally:
        # chmod is deliberately reversible and permits test cleanup.
        for root in (public, oracle):
            for directory, dirs, files in os.walk(root):
                os.chmod(directory, 0o700)
                for name in dirs:
                    os.chmod(os.path.join(directory, name), 0o700)
                for name in files:
                    os.chmod(os.path.join(directory, name), 0o600)
