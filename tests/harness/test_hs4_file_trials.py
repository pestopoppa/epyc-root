import pytest

from scripts.harness.hs4_file_trials import _files, fixture_identity, prepare_attempt


def prepare(source, dest, **overrides):
    args = dict(fixture=source, destination=dest, prompt="Read the inventory.", task="inventory-1",
                arm="baseline", trial=1, catalog="catalog-1",
                identity={"model": "m", "server": "s", "plugin": "p", "base_catalog": "c"},
                expected_fixture=fixture_identity(_files(source)))
    args.update(overrides)
    return prepare_attempt(**args)


def test_fresh_attempt_is_bound_and_independent(tmp_path):
    source = tmp_path / "public"
    (source / "data").mkdir(parents=True)
    (source / "data" / "items.txt").write_text("apples: 2\n")
    private = tmp_path / "private"
    private.mkdir()
    (private / "answer.txt").write_text("2")
    first = tmp_path / "first"
    metadata = prepare(source, first)
    second = tmp_path / "second"
    prepare(source, second, arm="candidate", trial=2)
    (first / "workspace" / "data" / "items.txt").write_text("mutated")
    assert (second / "workspace" / "data" / "items.txt").read_text() == "apples: 2\n"
    assert not list((first / "workspace").rglob("answer.txt"))
    assert metadata["status"] == "prepared_only"
    assert metadata["isolation"] == "not_verified"
    with pytest.raises(FileExistsError):
        prepare(source, first)


def test_rejects_unpinned_or_symlinked_fixture(tmp_path):
    source = tmp_path / "public"
    source.mkdir()
    (source / "a").write_text("x")
    with pytest.raises(ValueError, match="digest"):
        prepare(source, tmp_path / "no", expected_fixture="0" * 64)
    assert not (tmp_path / "no").exists()
    (source / "escape").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        _files(source)


def test_refuses_nested_outputs_and_ambiguous_identity(tmp_path):
    source = tmp_path / "public"
    source.mkdir()
    (source / "a").write_text("x")
    with pytest.raises(ValueError, match="disjoint"):
        prepare(source, source / "out")
    with pytest.raises(ValueError, match="identity"):
        prepare(source, tmp_path / "out", trial=True)
