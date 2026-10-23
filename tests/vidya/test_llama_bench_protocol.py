"""VB-LLAMA-BENCH-HARDEN-PROTOCOL: llama-bench rows must match their request before they are projected.

Builds from 0492c2319 through the champion 49550eda5 leave `autokernel_harden` uninitialised, so about half of
processes started WITHOUT --autokernel-harden say `autokernel_hardened: true`. The shared helper is a projection
precondition only; `claim_tuple.grade()` stays the only grader.
"""
import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _llama_bench_protocol as lbp  # noqa: E402
from adapters import autokernel_aux_receipt as aux  # noqa: E402
from adapters import autokernel_gpu_screening as gpu  # noqa: E402
from adapters import inf70_roofline_ledger as inf70  # noqa: E402
import test_autokernel_gpu_screening as gpu_fx  # noqa: E402

PLAIN = ["llama-bench", "-m", "x.gguf", "-r", "3"]
HARDENED = PLAIN + ["--autokernel-harden", "42"]
DEFECT_BUILD = "49550eda5"
FIXED_BUILD = "141e4bcf5"


def row(flag="keep", build=DEFECT_BUILD, **extra):
    value = {"build_commit": build, "avg_ts": 10.0}
    if flag != "keep" and flag is not None:
        value["autokernel_hardened"] = flag
    value.update(extra)
    return value


# --- the four controls from the task text -----------------------------------

def test_requested_hardened_row_is_accepted():
    ident = lbp.assess(row=row(True), argv=HARDENED)
    assert ident["autokernel_hardened"] == "hardened"
    assert ident["autokernel_harden_requested"] is True


def test_unrequested_hardened_row_is_refused():
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        lbp.assess(row=row(True), argv=PLAIN)
    assert err.value.code == "unrequested_hardened"
    assert isinstance(err.value, ct.ProjectionError)
    assert lbp.refusal_code(str(err.value)) == "unrequested_hardened"


def test_request_unknown_row_from_a_v11_103_build_grades():
    # hardened state, no argv, build carries the fix: the flag is honest, so it is accepted
    assert lbp.assess(row=row(True, build=FIXED_BUILD), argv=None)["build_carries_v11_103"] is True
    # ordinary / unknown rows with no argv are accepted from any build
    assert lbp.assess(row=row(False), argv=None)["autokernel_hardened"] == "ordinary"
    assert lbp.assess(row=row(None, build=FIXED_BUILD), argv=None)["autokernel_hardened"] == "unknown"


def test_request_unknown_hardened_row_from_49550eda5_is_refused():
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        lbp.assess(row=row(True, build=DEFECT_BUILD), argv=None)
    assert err.value.code == "hardened_request_unrecoverable"


# --- the remaining directions and the unknown policy --------------------------

def test_requested_but_ordinary_row_is_refused():
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        lbp.assess(row=row(False), argv=HARDENED)
    assert err.value.code == "requested_not_attested"


def test_missing_key_is_unknown_never_false():
    assert lbp.hardened_state({"avg_ts": 1.0}) == "unknown"
    assert lbp.hardened_state({"autokernel_hardened": False}) == "ordinary"
    # a BenchRow.to_dict() style False that was never reported is unknown too
    assert lbp.hardened_state({"autokernel_hardened": False,
                               "autokernel_hardened_reported": False}) == "unknown"
    # hardened-only receipt fields prove hardened even when the flag is dropped
    assert lbp.hardened_state({"autokernel_input_hashes": "ab,cd"}) == "hardened"
    ident = lbp.assess(row=row(None), argv=PLAIN)
    assert ident["autokernel_hardened"] == "unknown"      # accepted by default, identity says unknown
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        lbp.assess(row=row(None), argv=PLAIN, strict_unknown=True)
    assert err.value.code == "unknown_protocol_strict"
    with pytest.raises(lbp.LlamaBenchProtocolRefusal):
        lbp.assess(row=row(None), argv=HARDENED)           # requested hardened, no receipt


def test_dropped_flag_with_receipt_fields_is_refused_when_unrequested():
    with pytest.raises(lbp.LlamaBenchProtocolRefusal):
        lbp.assess(row=row(None, autokernel_output_hashes="a/a"), argv=PLAIN)


def test_argv_as_string_and_equals_form():
    assert lbp.requested_from_argv("llama-bench --autokernel-harden 7") is True
    assert lbp.requested_from_argv(["x", "--autokernel-harden=7"]) is True
    assert lbp.requested_from_argv(PLAIN) is False
    assert lbp.requested_from_argv(None) is None
    assert lbp.requested_from_argv([]) is None


def test_tally_counts_refusals_by_code_and_still_raises():
    tally = lbp.RefusalTally()
    tally.assess(row=row(True), argv=HARDENED)
    for _ in range(2):
        with pytest.raises(lbp.LlamaBenchProtocolRefusal):
            tally.assess(row=row(True), argv=PLAIN)
    report = tally.report()
    assert report["assessed"] == 3 and report["refused"] == 2
    assert report["refused_by_code"]["unrequested_hardened"] == 2


# --- adapters -----------------------------------------------------------------

def _gpu_bank(raw_row, argv):
    receipt = gpu_fx.bank_receipt()
    receipt["anchor_runs"][0]["raw_row"] = raw_row
    if argv is not None:
        receipt["anchor_runs"][0]["argv"] = argv
    gpu_fx.resign(receipt)
    return receipt


def test_gpu_screening_requested_hardened_projects_and_records_protocol():
    receipt = _gpu_bank({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, HARDENED)
    natives = gpu.native_rows(receipt, receipt_locator="gpu:v27/baseline-bank.json",
                              receipt_sha256="1" * 64, attestation_present=True)
    tup = gpu.project(natives[0])
    assert tup.extra["llama_bench_protocol"]["autokernel_hardened"] == "hardened"
    assert tup.extra["llama_bench_protocol"]["autokernel_harden_requested"] is True
    assert ct.grade(tup)[:2] == ("Witnessed", "Anchored")


def test_gpu_screening_unrequested_hardened_is_refused_before_grading():
    receipt = _gpu_bank({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, PLAIN)
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        gpu.native_rows(receipt, receipt_sha256="1" * 64)
    assert err.value.code == "unrequested_hardened"


def test_gpu_screening_request_unknown_hardened_from_defect_build_is_refused():
    receipt = _gpu_bank({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, None)
    with pytest.raises(lbp.LlamaBenchProtocolRefusal) as err:
        gpu.native_rows(receipt, receipt_sha256="1" * 64)
    assert err.value.code == "hardened_request_unrecoverable"


def test_gpu_screening_legacy_run_without_flag_or_argv_is_unknown_and_still_projects():
    receipt = gpu_fx.bank_receipt()          # fixture run: raw_row has no flag, no argv
    natives = gpu.native_rows(receipt, receipt_sha256="1" * 64)
    tup = gpu.project(natives[0])
    assert tup.extra["llama_bench_protocol"]["autokernel_hardened"] == "unknown"
    assert tup.extra["llama_bench_protocol"]["autokernel_harden_requested"] == "unknown"


def test_aux_gpu_run_protocol_uses_the_same_helper():
    ok = {"raw_row": {"autokernel_hardened": True, "build_commit": DEFECT_BUILD}, "argv": HARDENED}
    assert aux._gpu_run_protocol(ok, "anchor_runs[0]")["autokernel_hardened"] == "hardened"
    bad = copy.deepcopy(ok)
    bad["argv"] = PLAIN
    with pytest.raises(lbp.LlamaBenchProtocolRefusal):
        aux._gpu_run_protocol(bad, "anchor_runs[0]")


def test_inf70_markdown_rows_record_unknown_row_protocol_with_the_commands_request():
    rows = [r for r in inf70.native_rows(
        ROOT / "tests" / "vidya" / "fixtures" / "inf70") if r["kind"] == "arm"] \
        if (ROOT / "tests" / "vidya" / "fixtures" / "inf70").exists() else []
    if not rows:
        import test_inf70_roofline_ledger_adapter as fx
        rows = [r for r in fx._rows("arm")]
    tup = inf70.project(rows[0])
    proto = tup.extra["llama_bench_protocol"]
    assert proto["autokernel_hardened"] == "unknown"          # markdown has no hardened column
    assert proto["autokernel_harden_requested"] is False      # the recorded command did not ask for it
    assert proto["build_carries_v11_103"] is False


def test_corpus_dry_run_accepts_requested_and_counts_the_two_refusals_by_code(tmp_path):
    import json
    from adapters import autokernel_corpus as corpus
    cases = {
        "requested": ({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, HARDENED),
        "unrequested": ({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, PLAIN),
        "unrecoverable": ({"avg_ts": 1.0, "autokernel_hardened": True, "build_commit": DEFECT_BUILD}, None),
    }
    for name, (raw, argv) in cases.items():
        receipt = _gpu_bank(raw, argv)
        (tmp_path / f"{name}.json").write_text(json.dumps(receipt))

    class _Ledger:
        def append(self, frame):
            raise AssertionError("dry run must not append")

    report = corpus.ingest_corpus(_Ledger(), root=tmp_path, as_of="2026-10-23T00:00:00Z", dry_run=True)
    assert report["documents_matched"] == 3
    assert report["rows_projected"] == 1
    assert report["refused"] == 2
    assert report["llama_bench_protocol_refused"] == {"hardened_request_unrecoverable": 1,
                                                     "unrequested_hardened": 1}
