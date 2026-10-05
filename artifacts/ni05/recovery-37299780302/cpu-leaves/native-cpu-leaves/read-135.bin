"""Tests for the structural/table-heavy PDF manifest builder."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmark import build_pdf_probe_manifest as builder
from scripts.benchmark import pdf_fastpath_probe


def test_build_manifest_selects_table_like_pdf(tmp_path: Path, monkeypatch) -> None:
    table_pdf = tmp_path / "annual_table_report.pdf"
    plain_pdf = tmp_path / "plain.pdf"
    table_pdf.write_bytes(b"%PDF-1.4 table\n")
    plain_pdf.write_bytes(b"%PDF-1.4 plain\n")

    monkeypatch.setattr(builder, "_pdf_page_count", lambda path: 12 if path == table_pdf else 1)
    monkeypatch.setattr(
        builder,
        "_sample_pdf_text",
        lambda path, sample_pages: (
            "Metric  Value  Delta\nRevenue  10  2\n"
            if path == table_pdf
            else "plain paragraph\n"
        ),
    )

    manifest = builder.build_manifest(
        [tmp_path],
        limit=10,
        max_files=None,
        sample_pages=2,
        min_table_like_lines=1,
        corpus_name="unit",
        corpus_kind="structural_table_heavy",
    )

    assert manifest["schema_version"] == "pdf_probe_manifest.v1"
    assert manifest["selection"]["candidate_count"] == 1
    assert manifest["selection"]["selected_count"] == 1
    assert manifest["pdfs"][0]["path"] == str(table_pdf.resolve())
    assert manifest["pdfs"][0]["table_like_line_count"] == 2


def test_manifest_is_consumable_by_fastpath_probe(tmp_path: Path, monkeypatch) -> None:
    pdf = tmp_path / "table.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(builder, "_pdf_page_count", lambda path: 3)
    monkeypatch.setattr(builder, "_sample_pdf_text", lambda path, sample_pages: "A  B  C\n")

    manifest = builder.build_manifest(
        [pdf],
        limit=1,
        max_files=None,
        sample_pages=1,
        min_table_like_lines=0,
        corpus_name="unit",
        corpus_kind="structural_table_heavy",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert pdf_fastpath_probe.load_manifest_paths(manifest_path) == [pdf.resolve()]
