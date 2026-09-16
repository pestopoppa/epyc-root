"""`cli.py ingest <file source>` end to end, one fixture per wired adapter.

What is pinned:

* every name in ``ingest_sources.SOURCES`` is accepted by the CLI (without the name in
  ``choices`` the adapter can never persist a row -- the lesson of `autokernel`/`inf70`);
* each source ingests a producer-shaped fixture THROUGH THE CLI into a real temp ledger;
* the grade on every appended support frame is exactly what ``claim_tuple.grade()`` returns
  for the adapter's own projection of the same native row -- the dispatcher adds no ladder;
* ``--dry-run`` appends nothing, a pre-hook/absent unit is DECLINED (never filled), and a
  record that does not re-derive is REFUSED by name.

Fixtures come from each adapter's own test module, so writer and reader drift is caught there
and this file only proves the wiring.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
import ingest_sources  # noqa: E402
from ledger import Ledger  # noqa: E402

AS_OF = "2026-09-16T09:00:00Z"
SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"


def _helpers(name: str):
    spec = importlib.util.spec_from_file_location(f"_ingest_fx_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- fixture builders: (source name, build(tmp) -> path, expected rows) -------------------------

def _kb_rag(tmp: Path) -> Path:
    h = _helpers("test_kb_rag_query_length_adapter")
    rows = [h._row(), h._row("kb_rag.query_tokens_p50", "p50", 12)]
    path = tmp / "kb_rag_query_length_report.json"
    path.write_text(json.dumps(h._report(rows)))
    return path


def _inf70_arms(tmp: Path) -> Path:
    h = _helpers("test_inf70_serving_arm_adapter")
    (tmp / "agents" / "s3").mkdir(parents=True)
    runs = h.make_arm(tmp / "agents" / "s3")
    h.write(runs)
    return tmp / "agents"


def _contention_gate(tmp: Path) -> Path:
    h = _helpers("test_contention_gate_adapter")
    return h.write_capture(tmp / "capture.jsonl", h.envelope(),
                           h.envelope(request_id="api-def456"))


def _contention_matrix(tmp: Path) -> Path:
    h = _helpers("test_contention_matrix_adapter")
    h.write_run(tmp / "cm", "post-hook-run", stamp=h.CLEAN_STAMP)
    return tmp / "cm"


def _beam(tmp: Path) -> Path:
    h = _helpers("test_beam_memory_adapter")
    h.write_sidecar(h.make_run(tmp))
    return tmp


def _tulving(tmp: Path) -> Path:
    h = _helpers("test_tulving_episodic_adapter")
    return h.write_sidecar(h.make_run(tmp))


def _chat_template(tmp: Path) -> Path:
    h = _helpers("test_chat_template_ab_adapter")
    return h.write_sidecar(h.make_run(tmp))


def _occ1(tmp: Path) -> Path:
    h = _helpers("test_occ1_optical_compression_adapter")
    return h.write_sidecar(h.make_run(tmp))


def _tale_budget(tmp: Path) -> Path:
    h = _helpers("test_tale_budget_adapter")
    h.emit(h.make_run(tmp))
    return tmp


def _review_f1(tmp: Path) -> Path:
    h = _helpers("test_review_f1_adapter")
    summary = h.write(tmp, h.summary())
    h.capture.write_belief_measurements(summary, run_id="ev13b-ingest", producer="test",
                                        emitted_at="2026-09-16T10:00:00Z")
    return tmp


def _opencode_shell(tmp: Path) -> Path:
    h = _helpers("test_opencode_shell_run_adapter")
    h.write_sidecar(h.make_run(tmp / "runs"))
    return tmp / "runs"


def _memento(tmp: Path) -> Path:
    h = _helpers("test_memento_lora_adapter")
    row = copy.deepcopy(h._load_fixture())
    return h._write_belief(tmp, row, (h.FIXTURE.parent / "stage1_metrics.json").read_bytes())


def _pareval(tmp: Path) -> Path:
    h = _helpers("test_pareval_adapter")
    records, _ = h.write_fixture(tmp)
    return records


def _band(tmp: Path) -> Path:
    h = _helpers("test_eval_tower_band_adapter")
    return h.build(tmp)


def _fanout(tmp: Path) -> Path:
    h = _helpers("test_fanout_outcome_adapter")
    return h.write_corpus(tmp)


def _sweep_g1(tmp: Path) -> Path:
    h = _helpers("test_research_sweeps_adapter")
    h.write_run(tmp / "g1" / "run-a", h.g1_row(),
                h.g1_row(prompt_length_target=8201, prompt_length_actual=8200))
    return tmp / "g1"


def _sweep_g234(tmp: Path) -> Path:
    h = _helpers("test_research_sweeps_adapter")
    return h.write_sweep_file(tmp, h._g2_row())


def _autopilot(tmp: Path) -> Path:
    h = _helpers("test_autopilot_journal_adapter")
    h.write_journal(tmp, [h.row()])
    return tmp


def _mhs_guard(tmp: Path) -> Path:
    return _helpers("test_mhs_guard_adapter").copy_fixture(tmp)


BUILDERS = {
    "kb-rag-qlen": _kb_rag,
    "inf70-arms": _inf70_arms,
    "contention-gate": _contention_gate,
    "contention-matrix": _contention_matrix,
    "beam": _beam,
    "tulving": _tulving,
    "chat-template-ab": _chat_template,
    "occ1": _occ1,
    "tale-budget": _tale_budget,
    "review-f1": _review_f1,
    "opencode-shell": _opencode_shell,
    "memento-lora": _memento,
    "pareval": _pareval,
    "eval-tower-band": _band,
    "fanout-outcome": _fanout,
    "research-sweep-g1": _sweep_g1,
    "research-sweep-g234": _sweep_g234,
    "autopilot-journal": _autopilot,
    "mhs-guard-verdicts": _mhs_guard,
    "mhs-guard-ops": _mhs_guard,
}
#: sealed-manifest is exercised by its own real-corpus test (tests/vidya/test_sealed_manifest.py);
#: its unit discovery is pinned below instead of a synthetic seal.
FRAME_LEVEL = {"autopilot-journal", "sealed-manifest"}


@pytest.fixture(autouse=True)
def _mhs_guard_hook_epoch(monkeypatch):
    """The verdict source declines without a hook epoch; the fixture's producer went live here."""
    monkeypatch.setenv("VIDYA_MHS_GUARD_HOOK_SINCE", "2026-09-17T10:00:00+00:00")


def test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift():
    action = next(a for a in cli.build_parser()._subparsers._group_actions[0]
                  .choices["ingest"]._actions if a.dest == "adapter")
    assert set(ingest_sources.SOURCES) <= set(action.choices)
    assert set(cli._FILE_SOURCES) == set(ingest_sources.SOURCES)


def test_every_source_has_an_end_to_end_fixture_or_a_named_exemption():
    assert set(ingest_sources.SOURCES) == set(BUILDERS) | {"sealed-manifest"}


def test_every_wired_adapter_projects_through_a_registered_projection():
    for src in ingest_sources.SOURCES.values():
        if src.frames:
            continue
        mod = src.load()
        if not src.selector:
            assert callable(getattr(mod, src.project, None)), src.name
        owners = {getattr(fn, "__module__", "") for fn in ct.registered().values()}
        assert mod.__name__ in owners, f"{src.name}: no registered projection in {mod.__name__}"


def _cli(tmp: Path, name: str, path: Path, *extra: str) -> tuple[int, Path]:
    ledger = tmp / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", name, "--path", str(path),
                   "--as-of", AS_OF, *extra])
    return rc, ledger


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_source_ingests_a_fixture_end_to_end(tmp_path, capsys, name):
    fixture_root = tmp_path / "fx"
    fixture_root.mkdir()
    path = BUILDERS[name](fixture_root)
    rc, ledger = _cli(tmp_path, name, path)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [], report["refused"]
    assert report["rows_projected"] >= 1, report
    assert report["frames_emitted"] == 3 * report["rows_projected"]

    frames = [r.frame for r in Ledger(ledger).read_all()]
    assert len(frames) == report["frames_emitted"]
    supports = [f for f in frames if f["frame_type"] == SUPPORT]
    assert len(supports) == report["rows_projected"]
    assert len({f["assertion"]["claim_id"] for f in supports}) == len(supports)

    if name in FRAME_LEVEL:
        return
    # The grade in the ledger is claim_tuple.grade() of the adapter's own projection.
    src = ingest_sources.SOURCES[name]
    mod = src.load()
    expected = {}
    for unit in src.units(path):
        for native in getattr(mod, src.natives)(unit):
            project = src.selector(mod, native) if src.selector else getattr(mod, src.project)
            tup = project(native)
            q, t, _ = ct.grade(tup)
            expected[f"clm_{tup.measurement_id}"] = {"Q": q, "T": t}
    got = {f["assertion"]["claim_id"]: f["assertion"]["grade"] for f in supports}
    assert got == expected


def test_dry_run_appends_nothing(tmp_path, capsys):
    path = _contention_gate(tmp_path)
    rc, ledger = _cli(tmp_path, "contention-gate", path, "--dry-run")
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["frames_emitted"] == 6 and report["dry_run"] is True
    assert not ledger.exists() or len(Ledger(ledger).read_all()) == 0


def test_pre_hook_arm_is_declined_not_filled(tmp_path, capsys):
    """An INF-70 runs dir with rows + coresidency but no sidecar projects nothing."""
    h = _helpers("test_inf70_serving_arm_adapter")
    (tmp_path / "agents" / "old").mkdir(parents=True)
    runs = h.make_arm(tmp_path / "agents" / "old")
    (runs / "stray.belief_measurements.jsonl").write_text("")
    rc, _ = _cli(tmp_path, "inf70-arms", tmp_path / "agents")
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 0 and report["frames_emitted"] == 0
    assert len(report["declined"]) == 1


def test_foreign_report_is_refused_by_name(tmp_path, capsys):
    bad = tmp_path / "query_length_report.json"
    bad.write_text(json.dumps({"schema": "something.else"}))
    rc, ledger = _cli(tmp_path, "kb-rag-qlen", bad)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] and "not a" in report["refused"][0]["reason"]
    assert not ledger.exists() or len(Ledger(ledger).read_all()) == 0


def test_missing_path_is_reported_and_a_defaultless_source_needs_a_path(tmp_path, capsys):
    rc, _ = _cli(tmp_path, "beam", tmp_path / "nope")
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["missing"] == [str(tmp_path / "nope")]
    rc = cli.main(["--ledger", str(tmp_path / "l.jsonl"), "ingest", "kb-rag-qlen",
                   "--as-of", AS_OF])
    assert rc == 2
    assert "pass --path" in capsys.readouterr().err


def test_sealed_manifest_discovery_matches_its_own_walk(tmp_path):
    from adapters import sealed_manifest as sm  # noqa: PLC0415

    manifest = tmp_path / "artifacts" / "run" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}")
    units = ingest_sources.SOURCES["sealed-manifest"].units(tmp_path)
    assert units == list(sm.discover(tmp_path))
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert digest  # an unsealed manifest is declined by frames_for_manifest, never graded
    assert sm.frames_for_manifest(manifest, as_of=AS_OF) == []


def test_autopilot_journal_accepts_a_shard_file_and_declines_a_foreign_file(tmp_path, capsys):
    """A shard path must not silently match nothing (review fix, 2026-09-16)."""
    h = _helpers("test_autopilot_journal_adapter")
    root = h.write_journal(tmp_path / "fx", [h.row(1), h.row(2)])
    shard = next((root / "repos/epyc-orchestrator/orchestration").glob("autopilot_journal*.jsonl"))
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    rc, _ = _cli(tmp_path / "a", "autopilot-journal", root)
    by_root = json.loads(capsys.readouterr().out)
    rc2, _ = _cli(tmp_path / "b", "autopilot-journal", shard)
    by_shard = json.loads(capsys.readouterr().out)
    assert rc == rc2 == 0
    assert by_shard["rows_projected"] == by_root["rows_projected"] == 2
    assert by_shard["frames_emitted"] == by_root["frames_emitted"]

    foreign = tmp_path / "notes.jsonl"
    foreign.write_text(json.dumps({"hello": "world"}) + "\n")
    (tmp_path / "c").mkdir()
    rc3, _ = _cli(tmp_path / "c", "autopilot-journal", foreign)
    report = json.loads(capsys.readouterr().out)
    assert rc3 == 0 and report["rows_projected"] == 0
    assert report["declined"] == [str(foreign)]


def test_mhs_guard_verdicts_decline_without_a_hook_epoch(tmp_path, capsys, monkeypatch):
    """Pre-hook data gets zero rows: no epoch, no rows -- the unit is declined, not filled."""
    monkeypatch.delenv("VIDYA_MHS_GUARD_HOOK_SINCE")
    path = _mhs_guard(tmp_path / "fx")
    rc, ledger = _cli(tmp_path, "mhs-guard-verdicts", path)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["units_matched"] == 1 and report["rows_projected"] == 0
    assert report["declined"] == [str(path)]
    assert not ledger.exists() or len(Ledger(ledger).read_all()) == 0


def test_mhs_guard_rows_counts(tmp_path, capsys):
    path = _mhs_guard(tmp_path / "fx")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _cli(tmp_path / "a", "mhs-guard-verdicts", path)
    verdicts = json.loads(capsys.readouterr().out)
    _cli(tmp_path / "b", "mhs-guard-ops", path)
    ops = json.loads(capsys.readouterr().out)
    assert (verdicts["rows_projected"], ops["rows_projected"]) == (4, 2)


def test_limit_is_a_global_row_limit(tmp_path, capsys):
    a = _contention_gate(tmp_path / "a")
    b = _contention_gate(tmp_path / "b")
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "contention-gate",
                   "--path", str(a), "--path", str(b), "--as-of", AS_OF, "--limit", "3",
                   "--dry-run"])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 3 and report["frames_emitted"] == 9


def test_every_dispatched_adapter_declares_its_authority():
    for src in ingest_sources.SOURCES.values():
        assert getattr(src.load(), "AUTHORITY", None), src.name


def test_tale_budget_pre_hook_results_are_declined_and_foreign_sidecars_too(tmp_path, capsys):
    """A PRB-T4 dir with a pre-hook results file (no sidecar) projects nothing, and a review-F1
    sidecar sitting in the same dir is declined by the TALE reader rather than coerced."""
    t = _helpers("test_tale_budget_adapter")
    r = _helpers("test_review_f1_adapter")
    t.make_run(tmp_path)  # results + meta, never captured
    stray = tmp_path / "stray.beliefs.jsonl"
    stray.write_text("")
    summary = r.write(tmp_path, r.summary())
    r.capture.write_belief_measurements(summary, run_id="x", producer="t")
    rc, ledger = _cli(tmp_path, "tale-budget", tmp_path)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 0 and report["refused"] == []
    assert len(report["declined"]) == 2
    assert not ledger.exists() or len(Ledger(ledger).read_all()) == 0


def test_review_f1_mutated_summary_still_ingests_as_an_unverified_observation(tmp_path, capsys):
    r = _helpers("test_review_f1_adapter")
    summary = r.write(tmp_path, r.summary())
    r.capture.write_belief_measurements(summary, run_id="x", producer="t",
                                        emitted_at="2026-09-16T10:00:00Z")
    summary.write_text(summary.read_text() + " ")
    (tmp_path / "l").mkdir()
    rc, ledger = _cli(tmp_path / "l", "review-f1", tmp_path)
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 3
    supports = [f for f in (x.frame for x in Ledger(ledger).read_all()) if f["frame_type"] == SUPPORT]
    assert len(supports) == 3
    assert {(f["assertion"]["grade"]["Q"], f["assertion"]["grade"]["T"]) for f in supports} == {
        ("Judged", "Located")}
    natives = ingest_sources.SOURCES["review-f1"].load().rows_for_summary(summary)
    assert natives and all(
        ingest_sources.SOURCES["review-f1"].load().project(n).attestation_present is False
        for n in natives)
