"""Unit tests for ODL structured-output Phase 2 path.

Live ODL invocation requires Java 11+ + a real PDF; these tests use
synthetic JSON dicts shaped like ODL output to exercise the parsing,
chunking, and figure-prompt-enrichment helpers.

Per handoffs/active/opendataloader-pipeline-integration.md Phase 2.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Mock mode so config loading doesn't try to reach servers.
os.environ.setdefault("ORCHESTRATOR_MOCK_MODE", "1")

import pytest

from src.models.odl_structured import (
    FigureContext,
    HeadingNode,
    ODLBoundingBox,
    ODLStructuredDocument,
    TableContext,
    coerce_structured_document,
    build_heading_tree,
    flatten_heading_tree,
)
from src.services.figure_analyzer import (
    DEFAULT_FIGURE_PROMPT,
    FigureAnalyzer,
    build_figure_prompt_with_context,
)
from src.services.document_chunker import DocumentChunker, chunk_by_odl_headings, _split_long_body
from src.models.document import BoundingBox, FigureRef, OCRResult, PageOCRResult
from src.services.pdf_router import PDFExtractionResult

FIXTURE_DIR = Path(__file__).parent / "fixtures"


# ─── ODLStructuredDocument parsing ────────────────────────────────────────────

def test_odl_doc_empty_payload_returns_empty_collections() -> None:
    doc = ODLStructuredDocument.from_json({})
    assert doc.page_count == 0
    assert doc.headings == []
    assert doc.figures == []
    assert doc.tables == []


def test_odl_doc_non_dict_input_returns_empty() -> None:
    doc = ODLStructuredDocument.from_json("not a dict")  # type: ignore[arg-type]
    assert doc.page_count == 0


def test_odl_doc_parses_headings_figures_tables() -> None:
    payload = {
        "page_count": 3,
        "headings": [
            {"level": 1, "text": "Introduction", "bbox": [72, 100, 540, 130], "page": 1},
            {"level": 2, "text": "Background", "bbox": [72, 200, 540, 230], "page": 1},
            {"level": 1, "text": "Results", "bbox": [72, 100, 540, 130], "page": 2},
        ],
        "figures": [
            {
                "bbox": [100, 200, 500, 400],
                "page": 2,
                "type": "chart",
                "caption": "Figure 1: throughput",
                "surrounding_text": "We measured...",
            }
        ],
        "tables": [
            {"bbox": [72, 600, 540, 700], "page": 2, "rows": [["a", "b"]], "markdown": "| a | b |"}
        ],
    }
    doc = ODLStructuredDocument.from_json(payload)
    assert doc.page_count == 3
    assert len(doc.headings) == 3
    assert doc.headings[0].text == "Introduction"
    assert doc.headings[1].level == 2
    assert len(doc.figures) == 1
    assert doc.figures[0].caption.startswith("Figure 1")
    assert len(doc.tables) == 1
    assert doc.tables[0].markdown_form == "| a | b |"


def test_odl_doc_tolerates_partial_payload() -> None:
    """Missing keys / mixed types must not crash parsing."""
    payload = {
        "headings": [
            "not a dict — should be skipped",
            {"level": 2, "text": "OK"},
            None,
        ],
        "figures": [{"page": 1}],  # no bbox keys; from_dict tolerates
    }
    doc = ODLStructuredDocument.from_json(payload)
    assert len(doc.headings) == 1  # one valid dict, two skipped
    assert doc.headings[0].text == "OK"
    assert len(doc.figures) == 1
    assert doc.figures[0].bbox.page == 1


def test_coerce_structured_document_accepts_dict_and_instance() -> None:
    payload = {"headings": [{"level": 1, "text": "Intro"}]}
    doc_from_dict = coerce_structured_document(payload)
    assert doc_from_dict is not None
    assert doc_from_dict.headings[0].text == "Intro"

    doc_from_instance = coerce_structured_document(doc_from_dict)
    assert doc_from_instance is doc_from_dict
    assert coerce_structured_document(None) is None


def test_ocr_result_preserves_structured_data_payload() -> None:
    payload = {"headings": [{"level": 1, "text": "Intro"}]}
    result = OCRResult.from_dict(
        {
            "pages": [{"page": 1, "text": "Intro\nBody", "bboxes": []}],
            "total_pages": 1,
            "elapsed_sec": 0.0,
            "pages_per_sec": 0.0,
            "structured_data": payload,
        }
    )

    assert result.structured_data == payload
    assert result.to_cache_dict()["structured_data"] == payload
    assert OCRResult.from_cache_dict(result.to_cache_dict()).structured_data == payload


def test_ocr_result_extraction_method_is_backward_compatible() -> None:
    """New OCRResult.extraction_method defaults None and round-trips through
    dict/cache without breaking older payloads that omit it."""
    # Legacy payloads without the field still parse.
    legacy = OCRResult.from_dict(
        {"pages": [], "total_pages": 0, "elapsed_sec": 0.0, "pages_per_sec": 0.0}
    )
    assert legacy.extraction_method is None
    assert "extraction_method" in legacy.to_cache_dict()

    # A stamped method survives dict + cache round-trips.
    stamped = OCRResult.from_dict(
        {
            "pages": [{"page": 1, "text": "Intro", "bboxes": []}],
            "total_pages": 1,
            "elapsed_sec": 0.0,
            "pages_per_sec": 0.0,
            "extraction_method": "opendataloader",
        }
    )
    assert stamped.extraction_method == "opendataloader"
    assert OCRResult.from_cache_dict(stamped.to_cache_dict()).extraction_method == (
        "opendataloader"
    )


def test_ocr_result_adapter_stamps_extraction_method() -> None:
    """document_client adapter carries PDFExtractionResult.method into OCRResult."""
    from src.services.document_client import _ocr_result_from_pdf_extraction

    ocr = _ocr_result_from_pdf_extraction(
        PDFExtractionResult(text="Body", method="opendataloader_structured")
    )
    assert ocr.extraction_method == "opendataloader_structured"


def test_document_preprocessor_extracts_structured_data_from_ocr_result() -> None:
    from src.services.document_preprocessor import DocumentPreprocessor

    payload = {"headings": [{"level": 1, "text": "Intro"}]}
    ocr_result = OCRResult(
        pages=[PageOCRResult(page=1, text="Intro\nBody", bboxes=[])],
        total_pages=1,
        elapsed_sec=0.0,
        pages_per_sec=0.0,
        structured_data=payload,
    )

    structured = DocumentPreprocessor()._extract_structured_document({}, ocr_result)

    assert structured is not None
    assert structured.headings[0].text == "Intro"


def test_bbox_from_list_or_kwargs() -> None:
    a = ODLBoundingBox.from_dict({"bbox": [10, 20, 30, 40], "page": 5})
    b = ODLBoundingBox.from_dict({"x0": 10, "y0": 20, "x1": 30, "y1": 40, "page": 5})
    assert a == b


def test_bbox_from_official_odl_alias_keys() -> None:
    bbox = ODLBoundingBox.from_dict(
        {"bounding box": [10, 20, 30, 40], "page number": 5}
    )
    assert bbox == ODLBoundingBox(page=5, x0=10, y0=20, x1=30, y1=40)


def test_odl_hybrid_fixture_replay_parses_aliases() -> None:
    payload = json.loads((FIXTURE_DIR / "odl_hybrid_sample.json").read_text())

    doc = ODLStructuredDocument.from_json(payload)

    assert doc.page_count == 2
    assert doc.headings[0].text == "Results"
    assert doc.headings[0].bbox is not None
    assert doc.headings[0].bbox.page == 1
    assert doc.figures[0].bbox.page == 2
    assert doc.figures[0].semantic_type == "chart"
    assert "throughput" in doc.figures[0].surrounding_text
    assert doc.tables[0].bbox.page == 1
    assert doc.tables[0].rows[1] == ["frontdoor", "42 ms"]
    assert "frontdoor" in doc.tables[0].markdown_form


# ─── heading tree ─────────────────────────────────────────────────────────────

def test_build_heading_tree_simple() -> None:
    flat = [
        HeadingNode(level=1, text="A"),
        HeadingNode(level=2, text="A.1"),
        HeadingNode(level=2, text="A.2"),
        HeadingNode(level=1, text="B"),
        HeadingNode(level=2, text="B.1"),
        HeadingNode(level=3, text="B.1.a"),
    ]
    roots = build_heading_tree(flat)
    assert [r.text for r in roots] == ["A", "B"]
    assert [c.text for c in roots[0].children] == ["A.1", "A.2"]
    assert [c.text for c in roots[1].children] == ["B.1"]
    assert roots[1].children[0].children[0].text == "B.1.a"


def test_flatten_heading_tree_breadcrumbs() -> None:
    flat = [
        HeadingNode(level=1, text="A"),
        HeadingNode(level=2, text="A.1"),
        HeadingNode(level=3, text="A.1.a"),
        HeadingNode(level=1, text="B"),
    ]
    roots = build_heading_tree(flat)
    pairs = flatten_heading_tree(roots)
    crumbs = [c for _, c in pairs]
    assert ["A"] in crumbs
    assert ["A", "A.1"] in crumbs
    assert ["A", "A.1", "A.1.a"] in crumbs
    assert ["B"] in crumbs


# ─── figure_analyzer prompt enrichment ────────────────────────────────────────

def test_build_figure_prompt_with_none_context_unchanged() -> None:
    out = build_figure_prompt_with_context(DEFAULT_FIGURE_PROMPT, None)
    assert out == DEFAULT_FIGURE_PROMPT


def test_build_figure_prompt_includes_breadcrumb_caption_text() -> None:
    ctx = FigureContext(
        figure_index=1,
        bbox=ODLBoundingBox(page=2, x0=0, y0=0, x1=100, y1=100),
        semantic_type="chart",
        caption="Figure 3: latency vs throughput",
        surrounding_text="The system scales linearly to 96 threads.",
        heading_breadcrumb=["Results", "Throughput"],
    )
    out = build_figure_prompt_with_context(DEFAULT_FIGURE_PROMPT, ctx)
    assert "Results > Throughput" in out
    assert "chart" in out
    assert "Figure 3" in out
    assert "scales linearly" in out


def test_build_figure_prompt_skips_empty_fields() -> None:
    ctx = FigureContext(
        figure_index=1,
        bbox=ODLBoundingBox(page=1, x0=0, y0=0, x1=10, y1=10),
        # All optional fields empty — should not produce stray punctuation.
    )
    out = build_figure_prompt_with_context(DEFAULT_FIGURE_PROMPT, ctx)
    # Base prompt should still be present.
    assert "Describe this figure" in out
    # No stray "appears under:" / "Caption:" / "Surrounding text:".
    assert "appears under" not in out
    assert "Caption:" not in out
    assert "Surrounding text:" not in out


# ─── document_chunker ODL-driven path ─────────────────────────────────────────

def test_chunk_by_odl_headings_returns_section_per_heading() -> None:
    text = (
        "Introduction\nThis paper describes a system.\n\n"
        "Background\nPrior work covered X.\n\n"
        "Results\nWe measured Y.\n"
    )
    doc = ODLStructuredDocument(
        headings=[
            HeadingNode(level=1, text="Introduction"),
            HeadingNode(level=2, text="Background"),
            HeadingNode(level=1, text="Results"),
        ]
    )
    sections = chunk_by_odl_headings(text, doc)
    titles = [s.title for s in sections]
    assert "Introduction" in titles
    assert any("Background" in t for t in titles)  # breadcrumb may be "Introduction > Background"
    assert "Results" in titles


def test_chunk_by_odl_headings_no_doc_falls_back_single_section() -> None:
    text = "Just a wall of text without headings."
    doc = ODLStructuredDocument()  # empty
    sections = chunk_by_odl_headings(text, doc)
    assert len(sections) == 1
    assert sections[0].title == "(unstructured)"
    assert sections[0].content == text


def test_chunk_by_odl_headings_skips_missing_titles() -> None:
    """When ODL reports a heading whose verbatim text isn't in the markdown,
    that heading is skipped rather than producing a wrong slice."""
    text = "Introduction\nbody1\n\nResults\nbody2"
    doc = ODLStructuredDocument(
        headings=[
            HeadingNode(level=1, text="Introduction"),
            HeadingNode(level=1, text="MissingHeading"),  # not in text
            HeadingNode(level=1, text="Results"),
        ]
    )
    sections = chunk_by_odl_headings(text, doc)
    titles = [s.title for s in sections]
    assert "Introduction" in titles
    assert "Results" in titles
    assert "MissingHeading" not in titles


def test_chunk_by_odl_headings_subsplits_long_section() -> None:
    text_body = "Introduction\n" + ("paragraph one. " * 200 + "\n\n") * 5
    doc = ODLStructuredDocument(headings=[HeadingNode(level=1, text="Introduction")])
    sections = chunk_by_odl_headings(text_body, doc, max_section_length=2000)
    assert len(sections) >= 2
    for s in sections:
        assert len(s.content) <= 2200  # max_chars + small slack


def test_document_chunker_uses_structured_headings_when_available() -> None:
    text = (
        "Introduction\nThis is the introduction paragraph.\n\n"
        "Results\nThe results section follows.\n"
    )
    ocr_result = OCRResult(
        pages=[PageOCRResult(page=1, text=text, bboxes=[])],
        total_pages=1,
        elapsed_sec=0.0,
        pages_per_sec=1.0,
    )
    structured_doc = ODLStructuredDocument(
        headings=[
            HeadingNode(level=1, text="Introduction"),
            HeadingNode(level=1, text="Results"),
        ]
    )

    result = DocumentChunker().process(ocr_result, "/doc.pdf", structured_doc=structured_doc)
    titles = [section.title for section in result.sections]

    assert len(result.sections) == 2
    assert "Introduction" in titles
    assert "Results" in titles


def test_document_chunker_extracts_structured_tables_when_available() -> None:
    text = "Results\nThe table summarizes latency."
    ocr_result = OCRResult(
        pages=[PageOCRResult(page=1, text=text, bboxes=[])],
        total_pages=1,
        elapsed_sec=0.0,
        pages_per_sec=1.0,
    )
    structured_doc = ODLStructuredDocument(
        headings=[HeadingNode(level=1, text="Results")],
        tables=[
            TableContext(
                table_index=1,
                bbox=ODLBoundingBox(page=1, x0=72, y0=120, x1=540, y1=300),
                rows=[["model", "latency"], ["frontdoor", "42 ms"]],
                markdown_form="| model | latency |\n|---|---|\n| frontdoor | 42 ms |",
                caption="Table 1: latency",
            )
        ],
    )

    result = DocumentChunker().process(ocr_result, "/doc.pdf", structured_doc=structured_doc)

    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.id == "p1_table1"
    assert table.page == 1
    assert table.caption == "Table 1: latency"
    assert "frontdoor" in table.markdown
    assert table.rows[1] == ["frontdoor", "42 ms"]
    assert table.bbox is not None
    assert table.bbox.normalized is False
    assert table.section_id == "s1"


def test_split_long_body_breaks_at_paragraphs() -> None:
    body = "para1\n\n" + ("para2 line. " * 200) + "\n\npara3"
    pieces = _split_long_body(body, max_chars=1000)
    assert len(pieces) >= 2
    for p in pieces:
        assert len(p) <= 1100


# ─── PDFExtractionResult schema ───────────────────────────────────────────────

def test_pdf_extraction_result_has_structured_data_field_default_none() -> None:
    """Phase 2: PDFExtractionResult.structured_data must default to None
    so existing call sites continue to work without modification."""
    r = PDFExtractionResult(text="hello")
    assert r.structured_data is None


def test_pdf_extraction_result_carries_structured_doc() -> None:
    doc = ODLStructuredDocument(page_count=2)
    r = PDFExtractionResult(text="t", structured_data=doc)
    assert r.structured_data is doc
    assert r.structured_data.page_count == 2


@pytest.mark.asyncio
async def test_analyze_figures_uses_matching_figure_context_prompt(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")

    analyzer = FigureAnalyzer()

    figures = [
        FigureRef(
            id="p1_fig0",
            page=1,
            bbox=BoundingBox(id=0, x1=100, y1=100, x2=500, y2=400),
        )
    ]
    figure_contexts = [
        FigureContext(
            figure_index=1,
            bbox=ODLBoundingBox(page=1, x0=100, y0=100, x1=500, y1=400),
            semantic_type="chart",
            caption="Figure 1: accuracy",
            surrounding_text="The system improves accuracy.",
            heading_breadcrumb=["Results", "Throughput"],
        )
    ]

    with patch.object(analyzer, "_render_pdf_page") as mock_render, patch.object(
        analyzer,
        "_analyze_single_figure",
        new=AsyncMock(return_value="A chart."),
    ) as mock_analyze:
        from PIL import Image

        mock_render.return_value = Image.new("RGB", (1000, 1000), color="white")

        result = await analyzer.analyze_figures(
            pdf_path,
            figures,
            figure_contexts=figure_contexts,
        )

    assert result[0].description == "A chart."
    prompt = mock_analyze.await_args.args[2]
    assert "Results > Throughput" in prompt
    assert "chart" in prompt
    assert "Figure 1: accuracy" in prompt
    assert "improves accuracy" in prompt
