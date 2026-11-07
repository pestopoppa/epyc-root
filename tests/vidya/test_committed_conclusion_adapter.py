"""VB-CC-1 / VB-CC-PILOT: committed-conclusion register -> Judged/Located OBSERVATION tuples.

Every test builds a throwaway git repo in tmp_path, so the quote audit runs against real git.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import committed_conclusion as ccm  # noqa: E402
from ledger import Ledger  # noqa: E402

WHEN = "2026-11-01T12:00:00Z"
HANDOFF = "handoffs/active/demo.md"
TEXT = """# demo
- [x] **H1** fused thing for the model ✅ 2026-11-06
    - *(2026-11-06)* **RESULT: KEEP** — op 1.50x, e2e +4.0%. [belief: cc]
- [ ] **H2** open box
"""


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    (r / "handoffs/active").mkdir(parents=True)
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    (r / HANDOFF).write_text("# demo\n- [ ] **H1** fused thing for the model\n")
    git(r, "add", ".")
    git(r, "commit", "-qm", "file")
    (r / HANDOFF).write_text(TEXT)
    git(r, "commit", "-qam", "conclude")
    monkeypatch.setattr(ccm, "REPO", r)
    return r


def row(repo, **kw):
    base = dict(path=HANDOFF, line=2, ref="HEAD", facet="27B",
                stated={"verdict_native": "KEEP", "metrics": [
                    {"metric": "op_speedup", "value": 1.5, "unit": "x"},
                    {"metric": "e2e_decode", "value": 1.04, "unit": "x", "effect_rel": 0.04}]},
                scope={"model_file": "M.gguf", "backend": "gpu", "device": "gfx90a"},
                scope_evidence="line", category="CANDIDATE", direction="higher_better",
                actor="test", at=WHEN, retrofit=True, mechanism={"id": "gfx90a-asm:demo"})
    base.update(kw)
    return ccm.build_row(repo=repo, **base)


def write(tmp_path, rows):
    p = tmp_path / "committed_conclusions.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def test_anchor_resolves_concluding_commit_and_item_extent(repo):
    r = row(repo)
    a = r["anchor"]
    assert a["commit_concluded"] == git(repo, "rev-parse", "HEAD")
    assert a["commit_introduced"] == git(repo, "rev-parse", "HEAD~1")
    assert (a["line_start"], a["line_end"]) == (2, 3)
    assert "RESULT: KEEP" in a["quote"] and "H2" not in a["quote"]
    assert "[belief" not in a["head_norm"] and "✅" not in a["head_norm"]


def test_projection_is_judged_located_with_no_warrant(repo, tmp_path):
    natives = ccm.native_rows(write(tmp_path, [row(repo)]), repo=repo)
    assert len(natives) == 2
    for n in natives:
        tup = ccm.project(n)
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert tup.protocol_id == "" and tup.reps is None
        assert "run_id" not in tup.applicability
        assert tup.observation["outcome"] == "improved"
        assert tup.observation["mechanism"]["id"] == "gfx90a-asm:demo"
        assert tup.attestation_locator.startswith("git:")


@pytest.mark.parametrize("field", ["protocol_id", "reps", "run_id"])
def test_warrant_fields_are_refused(repo, tmp_path, field):
    r = row(repo)
    if field == "run_id":
        r["scope"]["run_id"] = "x"
    else:
        r["stated"]["metrics"][0][field] = "p"
    with pytest.raises(ct.ProjectionError):
        ccm.native_rows(write(tmp_path, [r]), repo=repo)


def test_mutated_quote_is_refused(repo, tmp_path):
    r = row(repo)
    r["anchor"]["quote"] = r["anchor"]["quote"].replace("1.50x", "1.60x")
    r["anchor"]["quote_sha256"] = ccm.quote_sha(r["anchor"]["quote"])
    with pytest.raises(ct.ProjectionError, match="quote audit"):
        ccm.native_rows(write(tmp_path, [r]), repo=repo)


def test_identity_unique_and_move_invariant(repo, tmp_path):
    a, b = row(repo), row(repo, facet="A3B")
    assert a["cc_id"] != b["cc_id"]
    moved = ccm.cc_id("handoffs/completed/demo.md", a["anchor"]["head_norm"], "27B")
    assert moved == a["cc_id"]
    with pytest.raises(ct.ProjectionError, match="duplicates"):
        ccm.native_rows(write(tmp_path, [a, a]), repo=repo)


def test_decision_and_covered_rows_decline(repo, tmp_path):
    d, c = row(repo, kind="decision"), row(repo, facet="other")
    c["covered_by"] = "clm_native"
    p = write(tmp_path, [d, c])
    assert ccm.native_rows(p, repo=repo) == []
    assert {x["reason"] for x in ccm.declined(p)} == {"decision", "covered_by"}


def test_sign_checked_curated_outcome(repo):
    with pytest.raises(ct.ProjectionError):
        row(repo, stated={"verdict_native": "DROP", "metrics": [
            {"metric": "op", "value": 1.2, "unit": "x", "outcome": "regressed"}]})
    r = row(repo, stated={"verdict_native": "DROP", "metrics": [
        {"metric": "op", "value": 0.48, "unit": "x", "outcome": "regressed"}]})
    assert ccm.project({"row": r, "k": 0}).observation["outcome"] == "regressed"
    # decision tokens map to no outcome by themselves (design §2.4)
    r = row(repo, stated={"verdict_native": "DROP", "metrics": [
        {"metric": "op", "value": 0.48, "unit": "x"}]})
    assert "outcome" not in ccm.project({"row": r, "k": 0}).observation


def test_reingest_only_new_emits_nothing(repo, tmp_path):
    p = write(tmp_path, [row(repo)])
    led = Ledger(tmp_path / "ledger.jsonl")
    first = ingest_sources.ingest(led, "committed-conclusion", [p], as_of=WHEN, only_new=True)
    assert first["frames_emitted"] == 6 and not first["refused"]
    again = ingest_sources.ingest(led, "committed-conclusion", [p], as_of=WHEN, only_new=True)
    assert again["frames_emitted"] == 0 and again["frames_skipped"] == 6


def test_append_row_is_idempotent(repo, tmp_path):
    reg = tmp_path / "reg.jsonl"
    r = row(repo)
    assert ccm.append_row(reg, r) is True
    assert ccm.append_row(reg, r) is False
    assert len(reg.read_text().splitlines()) == 1


def test_vbcc3_register_marker_makes_a_changed_register_stale(repo, tmp_path):
    import sync as vsync
    data = write(tmp_path, [row(repo)]).read_bytes()
    ledger_path = tmp_path / "ledger.jsonl"
    led = Ledger(ledger_path)
    led_frames = vsync._fold_cc(led, ledger_path, data, WHEN)
    assert led_frames == 6
    assert vsync.cc_status(ledger_path, data)["cc_fresh"] is True
    changed = data + (json.dumps(row(repo, facet="A3B")) + "\n").encode()
    assert vsync.cc_status(ledger_path, changed)["cc_fresh"] is False
    assert vsync._fold_cc(led, ledger_path, changed, WHEN) == 6  # only the new row
    assert vsync.cc_status(ledger_path, None)["cc_fresh"] is True


def test_rev_supersedes_projects_only_the_corrected_rev(repo, tmp_path):
    """031c7aa1b: `conclusion add --rev/--supersedes`; native_rows skips a superseded rev."""
    r1 = row(repo)
    r2 = row(repo, rev=2, supersedes=f"{r1['cc_id']}:1",
             stated={"verdict_native": "KEEP", "metrics": [
                 {"metric": "op_speedup", "value": 1.21, "unit": "x"}]})
    assert (r2["cc_id"], r2["rev"], r2["supersedes"]) == (r1["cc_id"], 2, f"{r1['cc_id']}:1")
    natives = ccm.native_rows(write(tmp_path, [r1, r2]), repo=repo)
    assert len(natives) == 1 and natives[0]["row"]["rev"] == 2
    assert ccm.project(natives[0]).observation is not None
    # alone, rev 1 projects both metrics: the skip comes from the supersedes link
    assert len(ccm.native_rows(write(tmp_path, [r1]), repo=repo)) == 2


def test_cli_conclusion_add_passes_rev_and_supersedes():
    import cli
    args = cli.build_parser().parse_args(
        ["conclusion", "add", "--rev", "2", "--supersedes", "cc:v1:abc:1", "--actor", "t",
         *_cli_required()])
    assert args.rev == 2 and args.supersedes == "cc:v1:abc:1"
    default = cli.build_parser().parse_args(["conclusion", "add", "--actor", "t", *_cli_required()])
    assert default.rev == 1 and default.supersedes is None


def _cli_required():
    return ["--path", HANDOFF, "--line", "2", "--stated-json", "{}"]
