"""AK-HR-3 prospective append preserves legacy rows and counts nested gate once."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from adapters import ak_history
from adapters._native_sidecar import CaptureError


def trial(name: str, *, seven: bool) -> dict:
    stages = {"planner": 1.0, "critic": None, "author": 2.0,
              "gate": 5.0, "measure": 3.0}
    if seven:
        stages.update(build=2.0, correctness=2.0)
    return {"trial_id": name, "trial_ordinal": 1 if name == "a" else 2,
            "cumulative_tokens": 100 if name == "a" else 200,
            "trial_tokens": 100, "failure_class": None,
            "stage_seconds": stages, "mechanism_family_bucket": None,
            "knob_descriptor": None}


def append(root: Path, t: dict) -> Path:
    return ak_history.append_belief_measurement(
        root, campaign_id="c", store_id="s", epoch="e", producer="loop",
        trial=t, emitted_at="2026-10-31T00:00:00Z")


def test_legacy_and_seven_stage_rows_append_without_double_count(tmp_path: Path) -> None:
    old = trial("a", seven=False)
    path = append(tmp_path, old)
    first_line = path.read_bytes()
    assert append(tmp_path, trial("b", seven=True)) == path
    assert path.read_bytes().startswith(first_line)
    rows = ak_history.native_rows(path)
    assert len(rows) == 2 and all(row["attestation_present"] for row in rows)
    assert [row["row"]["value"] for row in rows] == [11.0, 11.0]
    assert ak_history.project(rows[1]).value == 11.0
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    assert append(tmp_path, trial("b", seven=True)) == path
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with pytest.raises(CaptureError, match="different identity"):
        append(tmp_path, {**trial("b", seven=True), "trial_tokens": 101})
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_bad_old_receipt_refuses_without_replacing_sidecar(tmp_path: Path) -> None:
    path = append(tmp_path, trial("a", seven=False))
    before = path.read_bytes()
    rows = ak_history.native_rows(path)
    receipt = Path(rows[0]["row"]["results_path"])
    receipt.write_text("tampered")
    with pytest.raises(CaptureError, match="custody"):
        append(tmp_path, trial("b", seven=True))
    assert path.read_bytes() == before


@pytest.mark.parametrize("bad_id", ["./a", "../a", "a/../a", "a/b", "a\\b", ".a"])
def test_unsafe_new_id_cannot_alias_an_existing_receipt(tmp_path: Path, bad_id: str) -> None:
    path = append(tmp_path, trial("a", seven=False))
    before = path.read_bytes()
    receipt = tmp_path / ak_history.RECEIPT_DIR / "a.json"
    old_receipt = receipt.read_bytes()
    with pytest.raises(CaptureError, match="safe receipt filename"):
        append(tmp_path, trial(bad_id, seven=True))
    assert path.read_bytes() == before
    assert receipt.read_bytes() == old_receipt


def test_symlink_and_conflicting_receipt_refuse_before_any_write(tmp_path: Path) -> None:
    path = append(tmp_path, trial("a", seven=False))
    receipt_dir = tmp_path / ak_history.RECEIPT_DIR
    first_receipt = (receipt_dir / "a.json").read_bytes()
    first_sidecar = path.read_bytes()
    second = receipt_dir / "b.json"
    second.symlink_to(receipt_dir / "a.json")
    with pytest.raises(CaptureError, match="symlink"):
        append(tmp_path, trial("b", seven=True))
    assert path.read_bytes() == first_sidecar
    assert (receipt_dir / "a.json").read_bytes() == first_receipt
    second.unlink()
    second.write_bytes(b"conflict")
    with pytest.raises(CaptureError, match="conflicting bytes"):
        append(tmp_path, trial("b", seven=True))
    assert path.read_bytes() == first_sidecar
    assert (receipt_dir / "a.json").read_bytes() == first_receipt
    assert second.read_bytes() == b"conflict"


def test_retry_with_omitted_nullable_fields_is_idempotent(tmp_path: Path) -> None:
    original = trial("a", seven=False)
    path = append(tmp_path, original)
    before = path.read_bytes()
    receipt = tmp_path / ak_history.RECEIPT_DIR / "a.json"
    receipt_before = receipt.read_bytes()
    subset = {key: value for key, value in original.items()
              if key not in {"failure_class", "mechanism_family_bucket", "knob_descriptor"}}
    assert append(tmp_path, subset) == path
    assert path.read_bytes() == before
    assert receipt.read_bytes() == receipt_before


def test_batch_write_also_rejects_unsafe_new_id(tmp_path: Path) -> None:
    with pytest.raises(CaptureError, match="safe receipt filename"):
        ak_history.write_belief_measurements(
            tmp_path, campaign_id="c", store_id="s", epoch="e",
            producer="loop", trials=[trial("../outside", seven=True)],
        )
    assert not (tmp_path / ak_history.SIDECAR_NAME).exists()
    assert not (tmp_path.parent / "outside.json").exists()


def test_receipt_directory_symlink_refuses_before_write(tmp_path: Path) -> None:
    (tmp_path / ak_history.RECEIPT_DIR).symlink_to(tmp_path.parent)
    with pytest.raises(CaptureError, match="directory is a symlink"):
        append(tmp_path, trial("a", seven=True))
    assert not (tmp_path / ak_history.SIDECAR_NAME).exists()


def test_existing_receipt_symlink_refuses_even_when_bytes_match(tmp_path: Path) -> None:
    path = append(tmp_path, trial("a", seven=False))
    before = path.read_bytes()
    receipt = tmp_path / ak_history.RECEIPT_DIR / "a.json"
    saved = tmp_path / ak_history.RECEIPT_DIR / "saved.json"
    receipt.rename(saved)
    receipt.symlink_to(saved)
    with pytest.raises(CaptureError, match="symlink"):
        append(tmp_path, trial("a", seven=False))
    with pytest.raises(CaptureError, match="symlink"):
        append(tmp_path, trial("b", seven=True))
    assert path.read_bytes() == before
    assert saved.read_bytes() == receipt.read_bytes()
