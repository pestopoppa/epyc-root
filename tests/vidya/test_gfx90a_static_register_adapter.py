"""SC84/SC84a: gfx90a static register/ISA audit documents -> ClaimTuple, refusal, ingest.

The governed fixture is a real producer document (``gfx90a_isa_audit.py audit --category
BASELINE --source-commit ffc1bac82...`` over production v10 ``libggml-hip.so``, Q8_0 J=64,
2026-09-27): both rows unchanged, only ``code_objects`` trimmed to the one code object the rows
name. The reader executes the research producer pinned by sha256; when the research checkout
has not pulled e603216f yet, the pinned bytes are materialized from its git object store (set
``GFX90A_ISA_AUDIT_TEST_PRODUCER`` to point at a copy instead). The pin applies either way.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct
from adapters import gfx90a_static_register as reader
from ingest_sources import SOURCES, ingest
from ledger import Ledger

FIXTURE = Path(__file__).resolve().parent / "fixtures/gfx90a_isa_audit/governed_q8_excerpt.json"
RESEARCH = Path("/workspace/repos/epyc-inference-research")
PRODUCER_REV = "e603216f"
PRODUCER_REL = "scripts/kernel_rnd/gfx90a_isa_audit.py"
#: the ledger refuses future-stamped frames, so ingest at the wall clock
AS_OF = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
METRICS = ("vgpr_total", "arch_vgpr", "agpr", "sgpr", "vgpr_spill", "sgpr_spill",
           "private_bytes", "hot_spill_reloads", "hot_accvgpr_copies")


@pytest.fixture(scope="module")
def producer_path(tmp_path_factory):
    candidates = [os.environ.get("GFX90A_ISA_AUDIT_TEST_PRODUCER"), str(reader.DEFAULT_PRODUCER)]
    for candidate in filter(None, candidates):
        try:
            reader._producer(candidate)
            return Path(candidate)
        except ct.ProjectionError:
            continue
    try:
        data = subprocess.run(["git", "-C", str(RESEARCH), "show", f"{PRODUCER_REV}:{PRODUCER_REL}"],
                              capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        pytest.skip(f"pinned gfx90a ISA-audit producer unavailable here: {exc}")
    path = tmp_path_factory.mktemp("producer") / "gfx90a_isa_audit.py"
    path.write_bytes(data)
    try:
        reader._producer(path)
    except ct.ProjectionError as exc:
        pytest.skip(f"pinned gfx90a ISA-audit producer unavailable here: {exc}")
    return path


@pytest.fixture()
def pinned(monkeypatch, producer_path):
    monkeypatch.setattr(reader, "DEFAULT_PRODUCER", producer_path)
    return reader._producer()


def _doc() -> dict:
    return json.loads(FIXTURE.read_text())


def _write(tmp_path: Path, doc: dict, name: str = "audit_q8_governed.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return path


def _reseal(module, row: dict) -> None:
    row["self_sha256"] = hashlib.sha256(
        module.canonical({k: v for k, v in row.items() if k != "self_sha256"})).hexdigest()


def test_governed_document_projects_one_observation_per_row_metric(tmp_path, pinned):
    path = _write(tmp_path, _doc())
    natives = reader.native_rows(path)
    doc = _doc()
    assert len(natives) == len(doc["rows"]) * len(METRICS)
    tuples = [reader.project(n) for n in natives]
    assert len({t.measurement_id for t in tuples}) == len(tuples)

    row = doc["rows"][0]
    by_id = {t.measurement_id: t for t in tuples}
    spill = by_id[f"{row['row_id']}:hot_spill_reloads"]
    assert spill.metric == "gfx90a_static.hot_spill_reloads"
    assert spill.value == row["hot_spill_reloads"] == 12
    assert spill.unit == "instructions_per_iteration"
    assert spill.category == "BASELINE" and spill.metric_direction == "lower_better"
    assert spill.date == "2026-09-27" and spill.reps == 1 and spill.protocol_id == ""
    assert spill.source_kind == reader.SOURCE_KIND == "epyc.gfx90a.isa_audit.v1"
    assert spill.attestation_path == str(path) and spill.attestation_present is True
    assert spill.attestation_verified is True
    assert json.loads(spill.attestation_locator) == [row["binary_sha256"], row["code_object"],
                                                     row["kernel"], "hot_spill_reloads"]
    assert spill.extra["source_commit"] == doc["source_commit"]
    assert spill.extra["mfma_form_regime"] == ["mayneedagprs_rule_pre_159493"]
    assert spill.extra["accum_offset"] == row["accum_offset"]
    assert spill.extra["promotion_authority"] is False
    assert by_id[f"{row['row_id']}:vgpr_total"].value == 256
    assert by_id[f"{row['row_id']}:agpr"].value == 0

    # OBSERVATION grade, decided by the shared ladder alone.
    for tup in tuples:
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("OBSERVATION" in r for r in reasons)


def test_gzip_document_reads_the_same_claims(tmp_path, pinned):
    plain = reader.native_rows(_write(tmp_path, _doc()))
    gz = tmp_path / "audit_q8_governed.json.gz"
    gz.write_bytes(gzip.compress(json.dumps(_doc()).encode()))
    zipped = reader.native_rows(gz)
    assert [(n["measurement_id"], n["value"]) for n in zipped] == \
        [(n["measurement_id"], n["value"]) for n in plain]


@pytest.mark.parametrize("category", ["absent", None])
def test_pre_hook_document_emits_zero_tuples_without_the_producer(tmp_path, monkeypatch,
                                                                  category):
    doc = _doc()
    for key in ("category", "source_commit", "flags_pragmas"):
        doc.pop(key)
    if category is None:
        doc["category"] = None
    # A pre-hook audit asserts nothing, so it must decline even where the producer is absent.
    monkeypatch.setattr(reader, "DEFAULT_PRODUCER", tmp_path / "no-such-producer.py")
    assert reader.native_rows(_write(tmp_path, doc)) == []


def test_foreign_document_declines(tmp_path):
    diff = {"baseline": "a", "candidate": "b", "counts": {}, "findings": [], "n_common": 0}
    assert reader.native_rows(_write(tmp_path, diff, "audit_diff.json")) == []


def test_stub_rows_and_absent_metrics_are_not_filled(tmp_path, pinned):
    doc = _doc()
    doc["rows"][0]["stub"] = True
    del doc["rows"][1]["hot_accvgpr_copies"]
    for row in doc["rows"]:
        _reseal(pinned, row)
    natives = reader.native_rows(_write(tmp_path, doc))
    assert len(natives) == len(METRICS) - 1
    assert all(n["measurement_id"].startswith(doc["rows"][1]["row_id"]) for n in natives)
    assert not any(n["metric"].endswith("hot_accvgpr_copies") for n in natives)


def _tamper_value(doc, module):
    doc["rows"][0]["hot_spill_reloads"] = 0  # self_sha256 no longer re-derives


def _duplicate_row(doc, module):
    doc["rows"][1] = copy.deepcopy(doc["rows"][0])


def _foreign_binary(doc, module):
    doc["rows"][0]["binary_sha256"] = "0" * 64
    _reseal(module, doc["rows"][0])


def _missing_claim_field(doc, module):
    del doc["rows"][0]["params"]  # claim_projection needs it; never invented
    _reseal(module, doc["rows"][0])


def _bad_category(doc, module):
    doc["category"] = "PROMOTED"


def _no_date(doc, module):
    doc["created_utc"] = ""


def _short_count(doc, module):
    doc["n_rows"] = 3


def _no_toolchain(doc, module):
    doc["toolchain"] = []


def _foreign_row(doc, module):
    doc["rows"][0]["schema"] = "epyc.other.v1"
    _reseal(module, doc["rows"][0])


def _missing_rows(doc, module):
    del doc["rows"]


@pytest.mark.parametrize("mutate", [_tamper_value, _duplicate_row, _foreign_binary,
                                    _missing_claim_field, _bad_category, _no_date, _short_count,
                                    _no_toolchain, _foreign_row, _missing_rows])
def test_malformed_governed_document_is_refused_never_repaired(tmp_path, pinned, mutate):
    doc = _doc()
    mutate(doc, pinned)
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(_write(tmp_path, doc))


def test_unreadable_document_is_refused(tmp_path):
    path = tmp_path / "audit_broken.json"
    path.write_text('{"schema": "epyc.gfx90a.isa_audit.v1", ')
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(path)


def test_producer_pin_is_enforced(tmp_path, producer_path):
    altered = tmp_path / "gfx90a_isa_audit.py"
    altered.write_bytes(producer_path.read_bytes() + b"\n# edited\n")
    with pytest.raises(ct.ProjectionError, match="reviewed bytes"):
        reader._producer(altered)


@pytest.mark.parametrize("change", [
    lambda n: n.pop("unit"),
    lambda n: n.__setitem__("invented", 1),
    lambda n: n.__setitem__("protocol_id", "P-SOMETHING"),
    lambda n: n.__setitem__("value", 1.5),
    lambda n: n.__setitem__("value", True),
    lambda n: n.__setitem__("source_kind", "measurement"),
    lambda n: n.__setitem__("category", "UNLABELLED"),
])
def test_projection_refuses_rows_not_shaped_by_the_pinned_producer(tmp_path, pinned, change):
    native = reader.native_rows(_write(tmp_path, _doc()))[0]
    change(native)
    with pytest.raises(ct.ProjectionError):
        reader.project(native)


def test_attestation_is_rederived_at_projection(tmp_path, pinned):
    path = _write(tmp_path, _doc())
    natives = reader.native_rows(path)
    path.write_text(path.read_text() + " ")
    with pytest.raises(ct.ProjectionError, match="changed since"):
        reader.project(natives[0])
    path.unlink()
    tup = reader.project(natives[0])
    assert tup.attestation_present is False and tup.attestation_verified is None
    assert ct.grade(tup)[:2] == ("Judged", "Located")


def test_registered_and_wired_as_an_ingest_source():
    assert ct.registered()[reader.SOURCE_KIND].__module__ == reader.__name__
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.MEASUREMENT_CLASS
    src = SOURCES["gfx90a-static-register"]
    assert src.module == "gfx90a_static_register" and src.default is None


def test_ingest_projects_governed_declines_pre_hook_refuses_tampered(tmp_path, pinned):
    root = tmp_path / "audits"
    root.mkdir()
    _write(root, _doc(), "audit_v10_governed.json")
    pre = _doc()
    pre.pop("category")
    _write(root, pre, "audit_v10_prehook.json")
    bad = _doc()
    _tamper_value(bad, pinned)
    _write(root, bad, "audit_v10_tampered.json")
    (root / "diff_v9_to_v10.json").write_text("{}")  # not an audit unit: never matched

    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest(ledger, "gfx90a-static-register", [root], as_of=AS_OF)
    assert report["units_matched"] == 3
    assert report["units_projected"] == 1
    assert report["rows_projected"] == 2 * len(METRICS)
    assert report["declined"] == [str(root / "audit_v10_prehook.json")]
    assert [r["unit"] for r in report["refused"]] == [str(root / "audit_v10_tampered.json")]
    frames = [r.frame for r in ledger.read_all()]
    assert len(frames) == report["frames_emitted"] == 3 * report["rows_projected"]
    grades = {f["assertion"]["grade"]["Q"] + "/" + f["assertion"]["grade"]["T"] for f in frames
              if f["frame_type"] == "epyc.vidya/frame/evidence_supports_claim/v1"}
    assert grades == {"Judged/Located"}
