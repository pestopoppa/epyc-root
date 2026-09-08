"""What this pins for `adapters/inf70_roofline_ledger.py` (SC53 write side).

The three failures this program has actually had, in this order:

1. **Identity collided.** Distinct arms merged into one belief. A run holds
   several blocks at the SAME thread count that differ only by a free-form
   banner, so identity carries the source file and the block ordinal, and the
   corpus replay asserts `distinct ids == rows`.
2. **Absence got back-filled.** A record that cannot be rederived is REFUSED
   with a named reason — never projected against an assumed recipe, an
   invented hash, or a guessed category. A real, complete run without
   `artifact.sha256` is refused, and the refusal names what the producer must
   add.
3. **The adapter graded.** It must not. Every grade asserted below is whatever
   `claim_tuple.grade()` returns for the projected tuple, and the placement
   proof — the thing INF-70 exists to defend — is pinned as PROVENANCE that
   does not move the grade in either direction.

The fixture is a real run directory, copied file-for-file from
`results-c5v2-20260902T103808Z` (plus one `d0-barrier.txt`); two of its five
arms carry bench logs and three do not, which is why the refusal path is
exercised against real text rather than a mock.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import inf70_roofline_ledger as reader  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inf70_run"
AS_OF = "2026-09-02T12:00:00Z"


def _rows(kind: str | None = None) -> tuple[dict, ...]:
    rows = reader.native_rows(FIXTURE)
    return tuple(r for r in rows if kind is None or r["kind"] == kind)


def _tuple_for(kind: str, **match):
    for row in _rows(kind):
        tup = reader.project(row)
        if all(tup.extra.get(k) == v for k, v in match.items()):
            return tup
    raise AssertionError(f"no {kind} row matching {match}")


# --- projection + the shared ladder -----------------------------------------

def test_arm_projection_carries_the_whole_measurement():
    tup = _tuple_for("arm", arm="c5-omp-off", threads=48, test="tg128")
    assert tup.metric == "llama_bench.tg128"
    assert tup.value == 9.76
    assert tup.unit == "t/s"
    assert tup.metric_direction == "higher_better"
    assert tup.protocol_id == reader.PROTOCOL_ARM
    assert tup.reps == 5
    assert tup.reps_basis.startswith("scored")
    assert tup.date == "2026-09-02T11:16:28Z"
    assert tup.source_kind == reader.SOURCE_KIND
    assert tup.extra["build"] == "58c345093 (10196)"
    assert tup.extra["artifact_sha256"] == (
        "4bfb98496364f8721c1e3ea084a238d690c52b1042a317e05fb43b756c9f8957")
    assert tup.extra["artifact_path"].endswith("IQ4_XS-uniform.gguf")
    assert tup.extra["stddev"] == 0.09
    assert tup.extra["ms_per_token"] == pytest.approx(102.46, abs=0.01)
    recipe = tup.extra["recipe"]
    assert recipe["cpu_list"] == "0-95"
    assert recipe["numactl_policy"] == "--interleave=all"
    assert recipe["mmap"] == "0"
    assert recipe["env"]["GGML_IQK"] == "1"
    # the ladder decides, not this adapter. The fixture is IN this repo tree, so
    # the honest answer is Attested; the real corpus lives under /mnt/raid0 and
    # answers Anchored (pinned below).
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons


def test_readbw_projection_keeps_the_counting_convention():
    """40 GB/s `copy` and 152 GB/s `read-sum` are not the same measurement."""
    tup = _tuple_for("readbw", kernel="copy", threads=48)
    assert tup.metric == "bench_readbw.copy"
    assert tup.unit == "GB/s"
    assert tup.metric_direction == "higher_better"
    assert tup.protocol_id == reader.PROTOCOL_READBW
    assert tup.reps == 5
    assert "read+write counted" in tup.extra["counting_convention"]
    assert "read+write counted" in tup.claim
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Attested"), reasons


def test_barrier_direction_is_recorded_not_inferred():
    tup = _tuple_for("barrier", impl="libgomp", measure="omp", threads=48)
    assert tup.metric == "bench_barrier.libgomp.omp"
    assert tup.value == 1.93
    assert tup.unit == "us/barrier"
    assert tup.metric_direction == "lower_better"
    # bench_barrier's tables print no repetition count, so n stays absent and
    # the ladder says so rather than the adapter inventing one.
    assert tup.reps is None
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Verified", "Located"), reasons
    assert any("n/reps" in r for r in reasons)


# --- identity ----------------------------------------------------------------

def test_every_row_gets_a_distinct_claim_id():
    rows = _rows()
    ids = {reader.project(r).measurement_id for r in rows}
    assert len(ids) == len(rows), "distinct claims must equal input rows"


def test_same_thread_count_different_condition_does_not_collide():
    """Two c0 blocks at different thread counts / banners stay distinct."""
    ids = {reader.project(r).measurement_id for r in _rows("readbw")
           if r["kernel"] == "read-sum"}
    assert len(ids) == 2


def test_locator_is_run_level_but_names_the_file_read():
    tup = _tuple_for("arm", arm="c5-t1", threads=1)
    assert tup.attestation_locator.startswith(str(FIXTURE))
    assert tup.attestation_locator.endswith("bench-c5-t1.log")
    assert len(tup.attestation_sha256) == 64


# --- refusal: absence is named, never back-filled ----------------------------

def test_arms_without_a_bench_log_are_refused_by_name():
    refused = reader.arm_refusals(FIXTURE)
    assert set(refused) == {"c5-omp-on", "inf68-asis", "inf68-evicted"}
    for arm, why in refused.items():
        assert f"no bench-{arm}.log" in why
    projected = {r["arm"] for r in _rows("arm")}
    assert projected == {"c5-omp-off", "c5-t1"}


def test_missing_artifact_sha_refuses_the_arm(tmp_path):
    run = tmp_path / "results-20260902T999999Z"
    run.mkdir()
    for name in ("DONE", "arms.log", "bench-c5-t1.log"):
        (run / name).write_bytes((FIXTURE / name).read_bytes())
    why = reader.arm_refusals(run)["c5-t1"]
    assert "artifact.sha256" in why
    assert not [r for r in reader.native_rows(run) if r["kind"] == "arm"]


def test_artifact_sha_naming_a_different_model_refuses_the_arm(tmp_path):
    run = tmp_path / "results-20260902T999999Z"
    run.mkdir()
    for name in ("DONE", "arms.log", "bench-c5-t1.log"):
        (run / name).write_bytes((FIXTURE / name).read_bytes())
    (run / "artifact.sha256").write_text("0" * 64 + "  /mnt/raid0/llm/models/other.gguf\n")
    assert "names" in reader.arm_refusals(run)["c5-t1"]


def test_dateless_run_is_refused():
    assert reader.refusal_reason("/nonexistent/inf70/run") == "no emissions"


def test_run_without_a_stamp_or_done_is_refused(tmp_path):
    run = tmp_path / "results-nostamp"
    run.mkdir()
    (run / "arms.log").write_bytes((FIXTURE / "arms.log").read_bytes())
    assert reader.refusal_reason(run).startswith("malformed:")
    assert reader.native_rows(run) == ()


def test_empty_directory_yields_no_emissions(tmp_path):
    run = tmp_path / "results-20260902T000000Z"
    run.mkdir()
    assert reader.refusal_reason(run) == "no emissions"


def test_a_new_arms_log_field_does_not_silently_hide_the_arm(tmp_path):
    """c5_followup.sh added `model=`; a positional regex read that as 'no arms'."""
    run = tmp_path / "results-20260902T000001Z"
    run.mkdir()
    (run / "DONE").write_text("done 2026-09-02T00:00:01Z\n")
    text = (FIXTURE / "arms.log").read_text().replace(
        " threads=", " model=some-model.gguf threads=", 1)
    (run / "arms.log").write_text(text)
    refused = reader.arm_refusals(run)
    assert "c5-omp-off" in refused, "the arm must be SEEN and refused, not invisible"


# --- strictness: project() cannot be driven around native_rows ---------------

def test_project_rejects_bare_or_mutated_native():
    good = _rows("arm")[0]
    with pytest.raises(ct.ProjectionError):
        reader.project("not a dict")
    with pytest.raises(ct.ProjectionError):
        reader.project({"kind": "arm"})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "kind": "something-else"})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "category": "GREAT"})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "build": ""})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "artifact_sha256": ""})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "recipe": {}})
    with pytest.raises(ct.ProjectionError):
        reader.project({**good, "run_dir": "/nonexistent"})


def test_readbw_without_a_counting_convention_is_refused():
    row = _rows("readbw")[0]
    with pytest.raises(ct.ProjectionError):
        reader.project({**row, "counting_convention": ""})
    with pytest.raises(ct.ProjectionError):
        reader.project({**row, "block": {**row["block"], "reps": None}})


# --- category: the non-asserting floor, unless the producer declares ---------

def test_undeclared_arms_are_candidates_never_optimum(tmp_path):
    for row in _rows():
        tup = reader.project(row)
        assert tup.category == "CANDIDATE"
        if row["kind"] == "arm":
            assert tup.extra["category_declared_by_producer"] is False


def test_producer_declared_category_is_honoured(tmp_path):
    run = tmp_path / "results-20260902T000002Z"
    run.mkdir()
    for path in FIXTURE.iterdir():
        (run / path.name).write_bytes(path.read_bytes())
    (run / "arms.meta").write_text("c5-omp-off BASELINE\nc5-t1 NONSENSE\n")
    cats = {r["arm"]: reader.project(r).category
            for r in reader.native_rows(run) if r["kind"] == "arm"}
    assert cats["c5-omp-off"] == "BASELINE"
    assert cats["c5-t1"] == "CANDIDATE", "an unrecognised label must not be adopted"


# --- placement proof is provenance, never a grade ---------------------------

def test_placement_proof_is_carried_and_distinguishes_absent_from_skewed():
    with_proof = _tuple_for("arm", arm="c5-omp-off", threads=48, test="tg128")
    without = _tuple_for("arm", arm="c5-t1", threads=1)
    proof = with_proof.extra["placement_proof"]
    assert proof["present"] is True
    assert proof["source"] == "state-c5-omp-off.log"
    assert len(proof["per_node_mb"]) == 4
    assert proof["even_share_pct"] == 25.0
    assert 0 < proof["max_share_pct"] <= 100
    absent = without.extra["placement_proof"]
    assert absent["present"] is False
    assert "no state-" in absent["reason"]


def test_placement_proof_does_not_move_the_grade():
    """A skewed arm and a clean arm grade identically: the ladder grades
    protocol/n/date/attestation, and a second private rule here would be the
    constitution re-derived in an adapter (pilot spec §4.7)."""
    row = [r for r in _rows("arm") if r["arm"] == "c5-omp-off"][0]
    clean = reader.project(row)
    skewed = reader.project({
        **row,
        "placement": {"present": True, "source": "state-x.log", "per_node_mb": [57700, 10700, 8000, 17700],
                      "total_mb": 94100, "max_node": 0, "max_share_pct": 61.3, "even_share_pct": 25.0},
    })
    assert ct.grade(clean)[:2] == ct.grade(skewed)[:2]
    assert skewed.extra["placement_proof"]["max_share_pct"] == 61.3


# --- attestation honesty -----------------------------------------------------

def test_in_tree_run_is_attested():
    tup = _tuple_for("arm", arm="c5-t1", threads=1)
    assert tup.attestation_path == "tests/vidya/fixtures/inf70_run/bench-c5-t1.log"
    assert tup.attestation_present is True
    assert ct.grade(tup)[:2] == ("Witnessed", "Attested")


def test_out_of_tree_run_is_anchored_not_attested(tmp_path):
    """Every real INF-70 run lives under /mnt/raid0/llm/tmp, outside this repo.

    The collect-time hash is honest, but the artifact is not repo-resolvable,
    so the ladder must say Anchored — never claim an in-tree pin it does not
    have."""
    run = tmp_path / "results-20260902T000003Z"
    run.mkdir()
    for path in FIXTURE.iterdir():
        (run / path.name).write_bytes(path.read_bytes())
    row = [r for r in reader.native_rows(run)
           if r["kind"] == "arm" and r["arm"] == "c5-t1"][0]
    tup = reader.project(row)
    assert tup.attestation_path == ""
    assert tup.attestation_locator.startswith(str(run))
    assert len(tup.attestation_sha256) == 64
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Witnessed", "Anchored"), reasons


# --- carrier conformance -----------------------------------------------------

def test_projection_is_registered_under_one_source_kind():
    assert reader.SOURCE_KIND in ct.registered()
    assert ct.registered()[reader.SOURCE_KIND] is reader.project


def test_adapter_declares_no_ladder():
    """INF-70 is `measurement` class; that class's one ladder is claim_tuple.py."""
    for source_class, (module, _fn) in ct.ladders().items():
        assert "inf70" not in module, (source_class, module)
    assert ct.ladders()["measurement"][0] == "scripts/vidya/claim_tuple.py"


def test_frames_are_emitted_through_the_shared_carrier():
    frames = reader.frames_for_run(FIXTURE, as_of=AS_OF)
    rows = _rows()
    assert len(frames) == 3 * len(rows)
    kinds = [f["frame_type"] for f in frames[:3]]
    assert kinds == [
        "epyc.vidya/frame/source_observed/v1",
        "epyc.vidya/frame/claim_proposed/v1",
        "epyc.vidya/frame/evidence_supports_claim/v1",
    ]
    support = frames[2]["assertion"]
    assert support["grade"]["Q"] in {"Judged", "Verified", "Witnessed"}
    assert support["category"] == "CANDIDATE"
    assert support["metric_direction"] in {"higher_better", "lower_better"}


def test_frames_for_a_refused_run_are_empty(tmp_path):
    run = tmp_path / "results-nostamp"
    run.mkdir()
    assert reader.frames_for_run(run, as_of=AS_OF) == []


# --- the warm corpus, priced -------------------------------------------------

@pytest.mark.skipif(not reader.DEFAULT_CORPUS.is_dir(), reason="INF-70 corpus not on this host")
def test_real_corpus_replays_with_unique_identity():
    rows: list[dict] = []
    for run in reader.discover():
        rows.extend(reader.native_rows(run))
    if not rows:
        pytest.skip("corpus present but holds no projectable run yet")
    ids = {reader.project(r).measurement_id for r in rows}
    assert len(ids) == len(rows), "identity collision on the real corpus"
    for row in rows:
        ct.grade(reader.project(row))  # must not raise


# --- the write side actually fires -------------------------------------------
#
# The AutoKernel adapters were built, tested and verified against a real corpus
# and had never persisted a row, because `cli.py ingest` only accepted the names
# in its `choices` list. Wiring the name IS the write side, so it gets pinned
# here rather than assumed.

class _Ledger:
    def __init__(self):
        self.frames = []

    def append(self, frame):
        self.frames.append(frame)


class _RefusingLedger:
    def append(self, frame):  # pragma: no cover - must never run
        raise AssertionError("a dry run must not append")


@pytest.fixture
def corpus(tmp_path):
    """A corpus root holding the fixture under a real `results-<UTC>` name.

    `discover()` only walks `results*` directories, which is how the corpus root
    stays free of the helper scripts and logs that share it.
    """
    run = tmp_path / "results-20260902T103808Z"
    run.mkdir()
    for path in FIXTURE.iterdir():
        (run / path.name).write_bytes(path.read_bytes())
    return tmp_path


def test_ingest_appends_three_frames_per_row(corpus):
    led = _Ledger()
    report = reader.ingest_corpus(led, root=corpus, as_of=AS_OF)
    assert report["runs_matched"] == 1
    assert report["rows_projected"] == len(_rows())
    assert report["frames_emitted"] == 3 * report["rows_projected"]
    assert len(led.frames) == report["frames_emitted"]
    assert report["by_kind"] == {"arm": 3, "barrier": 24, "readbw": 12}
    assert report["dry_run"] is False


def test_ingest_dry_run_writes_nothing(corpus):
    report = reader.ingest_corpus(_RefusingLedger(), root=corpus,
                                  as_of=AS_OF, dry_run=True)
    assert report["frames_emitted"] == 3 * len(_rows())
    assert report["dry_run"] is True


def test_ingest_limit_is_honoured(corpus):
    led = _Ledger()
    report = reader.ingest_corpus(led, root=corpus, as_of=AS_OF, limit=5)
    assert report["rows_projected"] == 5
    assert len(led.frames) == 15


def test_ingest_separates_the_three_refusal_channels(corpus):
    """Run-level, arm-level and row-level refusals are different problems.

    Folding them into one count is how a producer gap (an arm that exists and
    cannot be cited) hides behind a directory that was never a run at all.
    """
    report = reader.ingest_corpus(_RefusingLedger(), root=corpus,
                                  as_of=AS_OF, dry_run=True)
    assert report["runs_refused"] == []
    assert {r["arm"] for r in report["arms_refused"]} == {
        "c5-omp-on", "inf68-asis", "inf68-evicted"}
    assert all(r["run"] == "results-20260902T103808Z" for r in report["arms_refused"])
    # native_rows only emits what it could rederive, so project() must never
    # refuse one of its rows. A non-zero count is a defect, not a tolerance.
    assert report["rows_refused"] == []


def test_ingest_of_a_root_with_no_runs_is_empty_not_an_error(tmp_path):
    report = reader.ingest_corpus(_Ledger(), root=tmp_path, as_of=AS_OF)
    assert report["runs_matched"] == 0
    assert report["rows_projected"] == 0
    assert report["frames_emitted"] == 0


def test_cli_accepts_the_inf70_adapter_name():
    """Without the name in `choices`, everything above can never fire."""
    import cli  # noqa: PLC0415

    action = next(a for a in cli.build_parser()._subparsers._group_actions[0]
                  .choices["ingest"]._actions if a.dest == "adapter")
    assert "inf70" in action.choices


def test_cli_corpus_root_does_not_drift_from_the_adapter():
    import cli  # noqa: PLC0415

    assert cli.INF70_CORPUS_ROOT == reader.DEFAULT_CORPUS


def test_cli_ingest_dispatches_to_the_inf70_walk(monkeypatch, capsys):
    import cli  # noqa: PLC0415

    seen = {}

    def fake_ingest(ledger, *, root, as_of, limit, dry_run):
        seen.update(root=root, as_of=as_of, limit=limit, dry_run=dry_run)
        return {"root": str(root), "runs_matched": 1, "rows_projected": 2,
                "frames_emitted": 6, "by_kind": {"arm": 2}, "runs_refused": [],
                "arms_refused": [{"run": "r", "arm": "a", "reason": "no artifact.sha256"}],
                "rows_refused": [], "dry_run": dry_run}

    monkeypatch.setattr(reader, "ingest_corpus", fake_ingest)
    monkeypatch.setattr(cli, "_ledger", lambda args: _Ledger())
    rc = cli.main(["ingest", "inf70", "--as-of", AS_OF, "--dry-run",
                   "--root", str(FIXTURE.parent)])
    assert rc == 0
    assert seen["dry_run"] is True and seen["as_of"] == AS_OF
    out = capsys.readouterr().out
    assert "rows projected=2" in out
    # a refused arm is NAMED in the operator-facing output, never silent
    assert "no artifact.sha256" in out


def test_cli_ingest_rejects_a_missing_root(capsys):
    import cli  # noqa: PLC0415

    rc = cli.main(["ingest", "inf70", "--as-of", AS_OF, "--root", "/nonexistent/inf70"])
    assert rc == 2
    assert "no such INF-70 corpus root" in capsys.readouterr().err


# --- the multi-shard sidecar contract ----------------------------------------
#
# A sharded model (UD-IQ4_XS is 3 shards) must pin every shard, but the command
# names only the first. The producer (`c5_followup.sh`) therefore writes the
# LOADED shard first and the siblings after; the reader takes the first line.
# Both halves of that contract are pinned here, because a producer that ordered
# the lines by filename would silently hand the reader the wrong shard.

def _sharded_run(tmp_path, lines: list[str]):
    run = tmp_path / "results-20260902T111721Z"
    run.mkdir()
    for name in ("DONE", "arms.log", "bench-c5-t1.log"):
        (run / name).write_bytes((FIXTURE / name).read_bytes())
    model = reader.parse_command((run / "bench-c5-t1.log").read_text())["model"]
    (run / "artifact.sha256").write_text("".join(lines).replace("{MODEL}", model))
    return run, model


def test_loaded_shard_first_is_accepted_and_is_the_sha_carried(tmp_path):
    run, model = _sharded_run(tmp_path, [
        "a" * 64 + "  {MODEL}\n",
        "b" * 64 + "  /mnt/raid0/llm/models/x-00002-of-00003.gguf\n",
        "c" * 64 + "  /mnt/raid0/llm/models/x-00003-of-00003.gguf\n",
    ])
    # only c5-t1 carries a bench log in this trimmed run; the point is that it is
    # NOT refused for an artifact reason
    assert "c5-t1" not in reader.arm_refusals(run)
    sha, path = reader.artifact_sha_and_path(run)
    assert sha == "a" * 64 and path == model
    arm = [r for r in reader.native_rows(run) if r["kind"] == "arm"][0]
    assert reader.project(arm).extra["artifact_sha256"] == "a" * 64


def test_a_sibling_shard_first_is_refused_not_silently_adopted(tmp_path):
    run, _ = _sharded_run(tmp_path, [
        "b" * 64 + "  /mnt/raid0/llm/models/x-00002-of-00003.gguf\n",
        "a" * 64 + "  {MODEL}\n",
    ])
    why = reader.arm_refusals(run)["c5-t1"]
    assert "names" in why and "00002-of-00003" in why
