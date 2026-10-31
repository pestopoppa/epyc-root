"""VB-AK-PIN-REPIN: the stale-pin check and the append-only re-pin (temp git repos; no inference)."""
import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import producer_pins as pp  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                               "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"}).stdout.strip()


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = tmp_path / "research"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    monkeypatch.setitem(pp.REPOS, "research", r)
    return r


def _commit(repo, path, text, msg):
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_file_pin_current_stale_and_unresolved(repo):
    c1 = _commit(repo, "scripts/p.py", "v1\n", "v1")
    row = pp._file_row("x", "research", "HEAD", "scripts/p.py", _sha("v1\n"))
    assert row.status == "CURRENT"
    _commit(repo, "scripts/other.py", "unrelated\n", "unrelated")
    c3 = _commit(repo, "scripts/p.py", "v2\n", "change the producer")
    stale = pp._file_row("x", "research", "HEAD", "scripts/p.py", _sha("v1\n"))
    assert stale.status == "STALE" and stale.pinned_commit == c1 and stale.ref_commit == c3
    assert [c["subject"] for c in stale.changed] == ["change the producer"]  # the unrelated commit is not listed
    assert stale.new_digest == _sha("v2\n")
    lost = pp._file_row("x", "research", "HEAD", "scripts/p.py", _sha("never committed\n"))
    assert lost.status == "UNRESOLVED" and "no committed version" in lost.detail
    assert pp._file_row("x", "research", "HEAD", "scripts/gone.py", _sha("v1\n")).status == "UNRESOLVED"
    assert pp._file_row("x", "research", "nope", "scripts/p.py", _sha("v1\n")).status == "NO_REPO"


def test_closure_pin_is_stale_only_when_a_closure_file_changed(repo, monkeypatch):
    base = _commit(repo, pp.CLOSURE_FILES[0], "a\n", "closure v1")
    monkeypatch.setattr(pp, "rolling_pins", lambda: {base: "0" * 64})
    assert pp._closure_row("HEAD").status == "CURRENT"
    _commit(repo, "scripts/not_in_closure.py", "x\n", "elsewhere")
    assert pp._closure_row("HEAD").status == "CURRENT"
    _commit(repo, pp.CLOSURE_FILES[3], "b\n", "touch lifecycle_observation")
    row = pp._closure_row("HEAD")
    assert row.status == "STALE" and [c["subject"] for c in row.changed] == ["touch lifecycle_observation"]
    monkeypatch.setattr(pp, "rolling_pins", lambda: {"f" * 40: "0" * 64})
    assert pp._closure_row("HEAD").status == "UNRESOLVED"  # pinned commit not in the repo


def test_every_pin_constant_in_the_adapters_is_watched_or_exempt():
    watched = {(m, c) for m, c, *_ in pp.FILE_PINS} | set(pp.EXEMPT)
    unwatched = [p for p in pp.discover_pin_constants() if p not in watched]
    assert unwatched == []  # a new PRODUCER_SHA256 must be added to FILE_PINS or EXEMPT, with its reason
    assert not [k for k in pp.EXEMPT if k in {(m, c) for m, c, *_ in pp.FILE_PINS}]


def test_exempt_pin_names_exist_and_explain_their_nonmoving_identity():
    # A renamed/deleted constant must not leave a silent, stale exemption such
    # as SUMS_SHA256 after the reader moved to OUTER_CAPTURE_SUMS_SHA256.
    for (module, constant), reason in pp.EXEMPT.items():
        tree = ast.parse((pp.HERE / "adapters" / f"{module}.py").read_text())
        declared = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                declared.update(target.id for target in node.targets if isinstance(target, ast.Name))
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                declared.add(node.target.id)
        assert constant in declared, f"stale exemption: {module}.{constant}"
        assert isinstance(reason, str) and reason.strip(), f"unexplained exemption: {module}.{constant}"


def test_file_pins_point_at_constants_that_exist_and_are_hex():
    for module, const, repo_name, path, kind in pp.FILE_PINS:
        value = pp.adapter_constant(module, const)
        digests = [value] if kind == "file" else list(value.values())
        assert digests and all(pp._HEX64.match(d) for d in digests)
        assert repo_name in pp.REPOS and not path.startswith("/")


def test_apply_rolling_pin_is_append_only_and_idempotent_refusing():
    src = (ROOT / "scripts/vidya/adapters/autokernel_profile.py").read_text()
    new_commit, new_digest = "a" * 40, "b" * 64
    out = pp.apply_rolling_pin(src, new_commit, new_digest)
    assert out.count(new_commit) == 1 and new_digest in out
    assert out.replace(f'    "{new_commit}": (\n        "{new_digest}"),\n', "") == src  # nothing else moved
    ns: dict = {}
    block = pp._BLOCK.search(out)
    exec(block.group(0).replace("SAMPLED_CPU_SOURCE_DIGEST_07333B884", "'x'")
         .replace("SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9", "'y'"), ns)
    assert list(ns["SAMPLED_CPU_ROLLING_PINS"])[-1] == new_commit  # last entry = the tracked pin
    with pytest.raises(pp.PinError, match="already pinned"):
        pp.apply_rolling_pin(out, new_commit, "c" * 64)
    with pytest.raises(pp.PinError, match="40-hex"):
        pp.apply_rolling_pin(src, "abc", new_digest)
    with pytest.raises(pp.PinError, match="block not found"):
        pp.apply_rolling_pin("x = 1\n", new_commit, new_digest)


def test_rolling_pins_feed_the_reader_allow_list_and_keep_the_originals():
    from adapters import autokernel_profile as prof  # noqa: E402
    pins = prof.SAMPLED_CPU_ROLLING_PINS
    assert pp.rolling_pins() == pins  # the source-level reader the tool uses agrees with the imported module
    assert prof.SAMPLED_CPU_CAPTURE.bundle_source_digests == set(pins.values())
    assert prof.SAMPLED_CPU_SOURCE_DIGEST_07333B884 in pins.values()
    assert prof.SAMPLED_CPU_SOURCE_DIGEST_MAIN_B93017DC9 in pins.values()
    assert all(len(c) == 40 and len(d) == 64 for c, d in pins.items())


RESEARCH_REAL = pp.REPOS["research"]


@pytest.mark.skipif(not (RESEARCH_REAL / ".git").exists() or not Path(pp.PYTHON313).exists(),
                    reason="research clone or python3.13 not on this host")
def test_digest_method_reproduces_the_pinned_closure_digests():
    for commit, digest in pp.rolling_pins().items():
        if pp._git(RESEARCH_REAL, "cat-file", "-e", f"{commit}^{{commit}}").returncode != 0:
            pytest.skip(f"{commit[:9]} not in the research clone")
        got = pp.closure_digest(commit)
        assert got["digest"] == digest and got["closure_files_match_manifest"], commit[:9]


def test_cli_check_exit_codes(repo, monkeypatch, capsys):
    monkeypatch.setattr(pp, "FILE_PINS", ())
    monkeypatch.setattr(pp, "discover_pin_constants", lambda: [])
    base = _commit(repo, pp.CLOSURE_FILES[0], "a\n", "closure v1")
    monkeypatch.setattr(pp, "rolling_pins", lambda: {base: "0" * 64})
    assert pp.main(["check", "--ref", "HEAD"]) == 0
    _commit(repo, pp.CLOSURE_FILES[1], "b\n", "closure moved")
    assert pp.main(["check", "--ref", "HEAD"]) == 3
    assert "STALE" in capsys.readouterr().out
