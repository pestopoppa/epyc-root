"""Unit tests for PDF Router."""

import os

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.services.pdf_router import (
    PDFRouter,
    PDFExtractionResult,
    BoundingBox,
    ExtractedFigure,
    ODL_TABLE_BACKEND_ENV,
    ODL_HYBRID_BACKEND_ENV,
    ODL_HYBRID_FALLBACK_ENV,
    ODL_HYBRID_TIMEOUT_MS_ENV,
    ODL_HYBRID_URL_ENV,
    extract_pdf,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""

    def test_bounding_box_fields(self):
        bbox = BoundingBox(x0=0.1, y0=0.2, x1=0.9, y1=0.8, page=1, width_px=100, height_px=200)
        assert bbox.x0 == 0.1
        assert bbox.y0 == 0.2
        assert bbox.x1 == 0.9
        assert bbox.y1 == 0.8
        assert bbox.page == 1
        assert bbox.width_px == 100
        assert bbox.height_px == 200


class TestExtractedFigure:
    """Tests for ExtractedFigure dataclass."""

    def test_extracted_figure_fields(self):
        bbox = BoundingBox(x0=0.1, y0=0.2, x1=0.9, y1=0.8, page=1)
        figure = ExtractedFigure(index=1, bbox=bbox, image_path="/tmp/fig1.png", format="png")
        assert figure.index == 1
        assert figure.bbox == bbox
        assert figure.image_path == "/tmp/fig1.png"
        assert figure.format == "png"


class TestPDFExtractionResult:
    """Tests for PDFExtractionResult dataclass."""

    def test_extraction_result_defaults(self):
        result = PDFExtractionResult(text="Hello world")
        assert result.text == "Hello world"
        assert result.figures == []
        assert result.page_count == 0
        assert result.method == "unknown"
        assert result.quality_score == 0.0
        assert result.latency_ms == 0.0
        assert result.ocr_required is False


class TestPDFRouterQuality:
    """Tests for text quality assessment."""

    def test_calculate_entropy_english(self):
        router = PDFRouter()
        # English text has high entropy
        text = "The quick brown fox jumps over the lazy dog."
        entropy = router._calculate_entropy(text)
        assert entropy > 3.5  # Typical English entropy

    def test_calculate_entropy_repetitive(self):
        router = PDFRouter()
        # Repetitive text has low entropy
        text = "aaaaaaaaaa"
        entropy = router._calculate_entropy(text)
        assert entropy < 1.0

    def test_calculate_entropy_empty(self):
        router = PDFRouter()
        assert router._calculate_entropy("") == 0.0

    def test_calculate_garbage_ratio_clean(self):
        router = PDFRouter()
        text = "This is clean text with no garbage."
        ratio = router._calculate_garbage_ratio(text)
        assert ratio < 0.05  # Very low garbage

    def test_calculate_garbage_ratio_binary(self):
        router = PDFRouter()
        text = "\x00\x01\x02\x03\x04\x05"
        ratio = router._calculate_garbage_ratio(text)
        assert ratio > 0.9  # High garbage

    def test_avg_word_length(self):
        router = PDFRouter()
        text = "The cat sat"  # 3, 3, 3
        avg = router._calculate_avg_word_length(text)
        assert avg == 3.0

    def test_assess_quality_good_text(self):
        router = PDFRouter()
        text = """
        This is a well-formatted document with proper English text.
        It contains multiple sentences and paragraphs of content.
        The text should have high entropy and low garbage ratio.
        We expect this to pass the quality check with flying colors.
        """
        score, needs_ocr = router._assess_text_quality(text)
        assert score > 0.7
        assert needs_ocr is False

    def test_assess_quality_garbage_text(self):
        router = PDFRouter()
        text = "x x x x x x x x x x x x x x x x x x x x x x x x x x x"
        score, needs_ocr = router._assess_text_quality(text)
        assert score < 0.5
        assert needs_ocr is True

    def test_assess_quality_short_text(self):
        router = PDFRouter()
        text = "Hi"
        score, needs_ocr = router._assess_text_quality(text)
        assert score == 0.0
        assert needs_ocr is True


class TestPDFRouterExtraction:
    """Tests for PDF extraction methods."""

    @patch("subprocess.run")
    def test_pdftotext_extraction(self, mock_run):
        router = PDFRouter()

        # Mock successful pdftotext output
        mock_run.return_value = MagicMock(
            returncode=0, stdout="This is extracted PDF text.", stderr=""
        )

        text, latency = router._extract_with_pdftotext(Path("/fake/test.pdf"))

        assert text == "This is extracted PDF text."
        assert latency > 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_pdftotext_failure(self, mock_run):
        router = PDFRouter()

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

        text, latency = router._extract_with_pdftotext(Path("/fake/test.pdf"))

        assert text == ""

    def test_extract_figures_no_pymupdf(self):
        router = PDFRouter()
        router._has_pymupdf = False

        figures = router._extract_figures_pymupdf(Path("/fake/test.pdf"))
        assert figures == []

    def test_extract_figures_from_odl_structured_normalizes_points(self):
        from src.models.odl_structured import (
            FigureContext,
            ODLBoundingBox,
            ODLStructuredDocument,
        )

        router = PDFRouter()
        structured = ODLStructuredDocument(
            figures=[
                FigureContext(
                    figure_index=7,
                    bbox=ODLBoundingBox(page=2, x0=100, y0=200, x1=500, y1=400),
                    semantic_type="chart",
                )
            ]
        )

        with patch.object(router, "_page_dimensions_pymupdf", return_value={2: (1000, 800)}):
            figures = router._extract_figures_from_odl_structured(
                Path("/fake/structured.pdf"),
                structured,
            )

        assert len(figures) == 1
        assert figures[0].index == 7
        assert figures[0].bbox.page == 2
        assert figures[0].bbox.x0 == pytest.approx(0.1)
        assert figures[0].bbox.y0 == pytest.approx(0.25)
        assert figures[0].bbox.x1 == pytest.approx(0.5)
        assert figures[0].bbox.y1 == pytest.approx(0.5)

    def test_extract_figures_from_odl_structured_needs_page_dimensions(self):
        from src.models.odl_structured import (
            FigureContext,
            ODLBoundingBox,
            ODLStructuredDocument,
        )

        router = PDFRouter()
        structured = ODLStructuredDocument(
            figures=[
                FigureContext(
                    figure_index=1,
                    bbox=ODLBoundingBox(page=1, x0=10, y0=10, x1=20, y1=20),
                )
            ]
        )

        with patch.object(router, "_page_dimensions_pymupdf", return_value={}):
            figures = router._extract_figures_from_odl_structured(
                Path("/fake/structured.pdf"),
                structured,
            )

        assert figures == []

    @pytest.mark.asyncio
    async def test_extract_structured_odl_uses_odl_figures_not_pymupdf(
        self, tmp_path, monkeypatch
    ):
        from src.models.odl_structured import (
            FigureContext,
            ODLBoundingBox,
            ODLStructuredDocument,
        )

        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        structured = ODLStructuredDocument(
            figures=[
                FigureContext(
                    figure_index=1,
                    bbox=ODLBoundingBox(page=1, x0=100, y0=100, x1=500, y1=400),
                )
            ]
        )
        odl_figure = ExtractedFigure(
            index=1,
            bbox=BoundingBox(x0=0.1, y0=0.1, x1=0.5, y1=0.4, page=1),
        )

        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")
        monkeypatch.setenv("ORCHESTRATOR_ODL_STRUCTURED", "1")

        router = PDFRouter()
        with patch.object(router, "_page_dimensions_pymupdf", return_value={1: (1000, 1000)}):
            with patch.object(
                router,
                "_extract_with_opendataloader_structured",
                return_value=("Enough text for quality", structured, 5.0),
            ) as mock_odl:
                with patch.object(router, "_assess_text_quality", return_value=(0.9, False)):
                    with patch.object(
                        router,
                        "_extract_figures_from_odl_structured",
                        return_value=[odl_figure],
                    ) as mock_odl_figures:
                        with patch.object(router, "_extract_figures_pymupdf") as mock_pymupdf:
                            result = await router.extract(pdf_path, extract_figures=True)

        mock_odl.assert_called_once_with(pdf_path)
        mock_odl_figures.assert_called_once_with(pdf_path, structured)
        mock_pymupdf.assert_not_called()
        assert result.figures == [odl_figure]
        assert result.structured_data is structured
        assert result.method == "opendataloader_structured"

    def test_odl_hybrid_table_backend_uses_official_client(self, tmp_path, monkeypatch):
        from src.models.odl_structured import HeadingNode, ODLStructuredDocument

        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        structured = ODLStructuredDocument(headings=[HeadingNode(level=1, text="Intro")])

        monkeypatch.setenv(ODL_TABLE_BACKEND_ENV, "hybrid")
        monkeypatch.setenv(ODL_HYBRID_BACKEND_ENV, "docling-fast")
        monkeypatch.setenv(ODL_HYBRID_URL_ENV, "http://127.0.0.1:5002")
        monkeypatch.setenv(ODL_HYBRID_TIMEOUT_MS_ENV, "12345")
        monkeypatch.setenv(ODL_HYBRID_FALLBACK_ENV, "0")

        router = PDFRouter()
        with patch.object(
            router,
            "_extract_with_opendataloader_hybrid",
            return_value=("Intro\nBody", structured, 12.0),
        ) as mock_hybrid_odl:
            with patch.object(router, "_extract_with_opendataloader_structured") as mock_local_odl:
                with patch.object(router, "_extract_figures_from_odl_structured") as mock_figures:
                    result = router.extract_opendataloader_structured(
                        pdf_path,
                        extract_figures=False,
                    )

        mock_hybrid_odl.assert_called_once_with(pdf_path)
        mock_local_odl.assert_not_called()
        mock_figures.assert_not_called()
        assert result.text == "Intro\nBody"
        assert result.structured_data is structured
        assert result.method == "opendataloader_hybrid"

    def test_odl_hybrid_table_backend_falls_back_to_local_when_empty(
        self,
        tmp_path,
        monkeypatch,
    ):
        from src.models.odl_structured import HeadingNode, ODLStructuredDocument

        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        structured = ODLStructuredDocument(headings=[HeadingNode(level=1, text="Intro")])

        monkeypatch.setenv(ODL_TABLE_BACKEND_ENV, "hybrid")

        router = PDFRouter()
        with patch.object(
            router,
            "_extract_with_opendataloader_hybrid",
            return_value=("", None, 12.0),
        ) as mock_hybrid_odl:
            with patch.object(
                router,
                "_extract_with_opendataloader_structured",
                return_value=("Intro\nBody", structured, 4.0),
            ) as mock_local_odl:
                result = router.extract_opendataloader_structured(
                    pdf_path,
                    extract_figures=False,
                )

        mock_hybrid_odl.assert_called_once_with(pdf_path)
        mock_local_odl.assert_called_once_with(pdf_path)
        assert result.text == "Intro\nBody"
        assert result.structured_data is structured
        assert result.method == "opendataloader_structured"

    @pytest.mark.asyncio
    async def test_extract_structured_odl_reports_hybrid_backend(
        self,
        tmp_path,
        monkeypatch,
    ):
        from src.models.odl_structured import HeadingNode, ODLStructuredDocument

        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        structured = ODLStructuredDocument(headings=[HeadingNode(level=1, text="Intro")])

        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")
        monkeypatch.setenv("ORCHESTRATOR_ODL_STRUCTURED", "1")
        monkeypatch.setenv(ODL_TABLE_BACKEND_ENV, "hybrid")

        router = PDFRouter()
        with patch.object(router, "_page_dimensions_pymupdf", return_value={1: (1000, 1000)}):
            with patch.object(
                router,
                "_extract_with_opendataloader_hybrid",
                return_value=("Intro\nBody", structured, 12.0),
            ) as mock_hybrid_odl:
                with patch.object(router, "_extract_with_opendataloader_structured") as mock_local_odl:
                    with patch.object(router, "_assess_text_quality", return_value=(0.9, False)):
                        with patch.object(
                            router,
                            "_extract_figures_from_odl_structured",
                            return_value=[],
                        ):
                            result = await router.extract(pdf_path, extract_figures=True)

        mock_hybrid_odl.assert_called_once_with(pdf_path)
        mock_local_odl.assert_not_called()
        assert result.method == "opendataloader_hybrid"
        assert result.structured_data is structured

    def test_extract_with_opendataloader_reads_temp_markdown(self, tmp_path):
        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        sibling_md = tmp_path / "structured.md"

        router = PDFRouter()
        with patch.dict("sys.modules", {"opendataloader_pdf.wrapper": MagicMock()}):
            from opendataloader_pdf.wrapper import convert as mock_convert

            def write_markdown(path: str, **kwargs):
                output_dir = Path(kwargs["output_dir"])
                (output_dir / "structured.md").write_text("Intro\nBody", encoding="utf-8")
                return None

            mock_convert.side_effect = write_markdown
            text, latency = router._extract_with_opendataloader(pdf_path)

        assert text == "Intro\nBody"
        assert latency >= 0
        assert not sibling_md.exists()
        mock_convert.assert_called_once()
        _, kwargs = mock_convert.call_args
        assert kwargs["format"] == "markdown"
        assert kwargs["quiet"] is True
        assert Path(kwargs["output_dir"]).name.startswith("odl_md_")

    def test_extract_with_opendataloader_hybrid_passes_client_options(
        self,
        tmp_path,
        monkeypatch,
    ):
        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")

        monkeypatch.setenv(ODL_HYBRID_BACKEND_ENV, "docling-fast")
        monkeypatch.setenv(ODL_HYBRID_URL_ENV, "http://127.0.0.1:5002")
        monkeypatch.setenv(ODL_HYBRID_TIMEOUT_MS_ENV, "12345")
        monkeypatch.setenv(ODL_HYBRID_FALLBACK_ENV, "false")

        router = PDFRouter()
        with patch.dict("sys.modules", {"opendataloader_pdf.wrapper": MagicMock()}):
            from opendataloader_pdf.wrapper import convert as mock_convert

            with patch.object(
                router,
                "_read_odl_structured_outputs",
                return_value=("Intro\nBody", None),
            ) as mock_read:
                text, structured, latency = router._extract_with_opendataloader_hybrid(
                    pdf_path
                )

        assert text == "Intro\nBody"
        assert structured is None
        assert latency >= 0
        mock_convert.assert_called_once()
        _, kwargs = mock_convert.call_args
        assert kwargs["format"] == ["markdown", "json"]
        assert kwargs["hybrid"] == "docling-fast"
        assert kwargs["hybrid_url"] == "http://127.0.0.1:5002"
        assert kwargs["hybrid_timeout"] == "12345"
        assert kwargs["hybrid_fallback"] is False
        mock_read.assert_called_once()

    def test_extract_with_opendataloader_hybrid_failure_returns_empty(self, tmp_path):
        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")

        router = PDFRouter()
        with patch.dict("sys.modules", {"opendataloader_pdf.wrapper": MagicMock()}):
            from opendataloader_pdf.wrapper import convert as mock_convert

            mock_convert.side_effect = RuntimeError("sidecar unavailable")
            text, structured, latency = router._extract_with_opendataloader_hybrid(
                pdf_path
            )

        assert text == ""
        assert structured is None
        assert latency >= 0

    def test_read_odl_structured_outputs_replays_hybrid_fixture(self, tmp_path):
        pdf_path = tmp_path / "odl_hybrid_sample.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        (tmp_path / "odl_hybrid_sample.md").write_text(
            (FIXTURE_DIR / "odl_hybrid_sample.md").read_text(),
            encoding="utf-8",
        )
        (tmp_path / "odl_hybrid_sample.json").write_text(
            (FIXTURE_DIR / "odl_hybrid_sample.json").read_text(),
            encoding="utf-8",
        )

        text, structured = PDFRouter()._read_odl_structured_outputs(tmp_path, pdf_path)

        assert "OpenDataLoader hybrid mode" in text
        assert structured is not None
        assert structured.tables[0].rows[1] == ["frontdoor", "42 ms"]
        assert structured.tables[0].bbox.page == 1

    def test_odl_local_table_backend_stays_local(self, tmp_path, monkeypatch):
        from src.models.odl_structured import HeadingNode, ODLStructuredDocument

        pdf_path = tmp_path / "structured.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        structured = ODLStructuredDocument(headings=[HeadingNode(level=1, text="Intro")])

        monkeypatch.setenv(ODL_TABLE_BACKEND_ENV, "local")

        router = PDFRouter()
        with patch.object(
            router,
            "_extract_with_opendataloader_structured",
            return_value=("Intro\nBody", structured, 12.0),
        ) as mock_local_odl:
            with patch.object(router, "_extract_figures_from_odl_structured") as mock_figures:
                result = router.extract_opendataloader_structured(
                    pdf_path,
                    extract_figures=False,
                )

        mock_local_odl.assert_called_once_with(pdf_path)
        mock_figures.assert_not_called()
        assert result.text == "Intro\nBody"
        assert result.structured_data is structured
        assert result.method == "opendataloader_structured"


@pytest.mark.skipif(
    os.environ.get("ORCHESTRATOR_MOCK_MODE", "").lower() == "true",
    reason="Skipped in CI: requires local PDF files and extraction tools",
)
class TestPDFRouterIntegration:
    """Integration tests with real PDFs."""

    @pytest.mark.integration
    def test_extract_real_pdf(self):
        """Test extraction with a real PDF file (pinned to the pdftotext path)."""
        pdf_path = _REPO_ROOT / "tmp/Twyne_V1_Whitepaper.pdf"
        if not pdf_path.exists():
            pytest.skip("Test PDF not available")
        if not os.access(pdf_path, os.R_OK):
            pytest.skip("Test PDF not readable")

        router = PDFRouter()
        # Default fast path is now OpenDataLoader; pin pdftotext to keep this
        # test exercising the born-digital pdftotext path specifically.
        with patch.dict(os.environ, {"PDF_EXTRACTOR": "pdftotext"}):
            result = router.extract_sync(pdf_path)

        assert result.text
        assert len(result.text) > 10000
        assert result.method == "pdftotext"
        assert result.quality_score > 0.8
        assert result.page_count > 0
        assert result.ocr_required is False

    @pytest.mark.integration
    def test_extract_with_figures(self):
        """Test figure extraction with a real PDF."""
        pdf_path = _REPO_ROOT / "tmp/Twyne_V1_Whitepaper.pdf"
        if not pdf_path.exists():
            pytest.skip("Test PDF not available")

        router = PDFRouter()
        with patch.dict(os.environ, {"PDF_EXTRACTOR": "pdftotext"}):
            result = router.extract_sync(pdf_path, extract_figures=True)

        assert len(result.figures) > 0
        for fig in result.figures:
            assert fig.index > 0
            assert 0 <= fig.bbox.x0 <= 1
            assert 0 <= fig.bbox.y0 <= 1
            assert fig.bbox.page >= 1


class TestExtractPdfFunction:
    """Tests for convenience function."""

    @patch.object(PDFRouter, "extract_sync")
    def test_extract_pdf_calls_router(self, mock_extract):
        mock_extract.return_value = PDFExtractionResult(text="test")

        result = extract_pdf("/fake/path.pdf")

        mock_extract.assert_called_once()
        assert result.text == "test"


# ─── Phase-1 default flip: ODL fast path + pdftotext fallback ─────────────────


class TestResolveExtractor:
    """The fast-path extractor resolution honours the 2026-07 default flip."""

    def test_default_is_opendataloader_when_runtime_available(self, monkeypatch):
        monkeypatch.delenv("PDF_EXTRACTOR", raising=False)
        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=True,
        ):
            assert router._resolve_extractor() == "opendataloader"

    def test_default_is_pdftotext_when_runtime_unavailable(self, monkeypatch):
        """JVM-unavailable graceful degrade: default stays inert on pdftotext."""
        monkeypatch.delenv("PDF_EXTRACTOR", raising=False)
        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=False,
        ):
            assert router._resolve_extractor() == "pdftotext"

    def test_explicit_pdftotext_selects_pdftotext(self, monkeypatch):
        monkeypatch.setenv("PDF_EXTRACTOR", "pdftotext")
        router = PDFRouter()
        # Explicit env wins even when the ODL runtime is available.
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=True,
        ):
            assert router._resolve_extractor() == "pdftotext"

    def test_explicit_opendataloader_honoured_even_if_runtime_probe_false(
        self, monkeypatch
    ):
        """Explicit opt-in is honoured verbatim; per-doc empty->pdftotext handles
        an actually-broken JVM (so mocked tests that patch the extractor work)."""
        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")
        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=False,
        ):
            assert router._resolve_extractor() == "opendataloader"


class TestOpendataloaderRuntimeProbe:
    """The cached runtime probe degrades gracefully with a logged reason."""

    def test_probe_false_when_java_missing(self):
        from src.services import pdf_router as pr

        pr._opendataloader_runtime_available.cache_clear()
        try:
            with patch("src.services.pdf_router.shutil.which", return_value=None):
                assert pr._opendataloader_runtime_available() is False
        finally:
            pr._opendataloader_runtime_available.cache_clear()

    def test_probe_true_when_java_and_sdk_present(self):
        from src.services import pdf_router as pr

        # The probe is java-on-PATH AND `import opendataloader_pdf`. Only the
        # former is mocked here, so this test genuinely requires the SDK to be
        # installed. `opendataloader-pdf` is an OPTIONAL extra (pdf_router degrades
        # to pdftotext with a logged reason when it is absent, and the package is
        # not in pyproject's dependency list), so skip rather than fail — the
        # absent-SDK behaviour is covered by test_probe_false_when_java_missing and
        # the extractor-resolution tests that patch this probe directly.
        pytest.importorskip(
            "opendataloader_pdf",
            reason="optional extra; PDF fast path degrades to pdftotext without it",
        )

        pr._opendataloader_runtime_available.cache_clear()
        try:
            with patch(
                "src.services.pdf_router.shutil.which", return_value="/usr/bin/java"
            ):
                assert pr._opendataloader_runtime_available() is True
        finally:
            pr._opendataloader_runtime_available.cache_clear()


class TestFastPathDefaultFlip:
    """extract() now defaults to ODL, with pdftotext as the safety fallback."""

    @pytest.mark.asyncio
    async def test_default_path_uses_opendataloader(self, tmp_path, monkeypatch):
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.delenv("PDF_EXTRACTOR", raising=False)

        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=True,
        ):
            with patch.object(
                router,
                "_extract_with_opendataloader",
                return_value=("Clean extracted paragraph text.", 12.0),
            ) as mock_odl:
                with patch.object(router, "_extract_with_pdftotext") as mock_pt:
                    with patch.object(
                        router, "_assess_text_quality", return_value=(0.9, False)
                    ):
                        with patch.object(
                            router, "_page_dimensions_pymupdf", return_value={}
                        ):
                            result = await router.extract(pdf_path, extract_figures=False)

        mock_odl.assert_called_once_with(pdf_path)
        mock_pt.assert_not_called()
        assert result.method == "opendataloader"
        assert result.ocr_required is False

    @pytest.mark.asyncio
    async def test_default_inert_pdftotext_when_runtime_unavailable(
        self, tmp_path, monkeypatch
    ):
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.delenv("PDF_EXTRACTOR", raising=False)

        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=False,
        ):
            with patch.object(
                router,
                "_extract_with_pdftotext",
                return_value=("Clean pdftotext body content.", 5.0),
            ) as mock_pt:
                with patch.object(router, "_extract_with_opendataloader") as mock_odl:
                    with patch.object(
                        router, "_assess_text_quality", return_value=(0.9, False)
                    ):
                        with patch.object(
                            router, "_page_dimensions_pymupdf", return_value={}
                        ):
                            result = await router.extract(pdf_path, extract_figures=False)

        mock_odl.assert_not_called()
        mock_pt.assert_called_once_with(pdf_path)
        assert result.method == "pdftotext"

    @pytest.mark.asyncio
    async def test_odl_empty_falls_back_to_pdftotext(self, tmp_path, monkeypatch):
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")

        clean = "Recovered clean pdftotext body text."
        router = PDFRouter()
        with patch.object(
            router, "_extract_with_opendataloader", return_value=("", 8.0)
        ) as mock_odl:
            with patch.object(
                router, "_extract_with_pdftotext", return_value=(clean, 4.0)
            ) as mock_pt:
                # Empty ODL text fails the quality check; clean pdftotext passes.
                with patch.object(
                    router,
                    "_assess_text_quality",
                    side_effect=lambda t: (0.9, False) if t else (0.0, True),
                ):
                    with patch.object(router, "_page_dimensions_pymupdf", return_value={}):
                        result = await router.extract(pdf_path, extract_figures=False)

        mock_odl.assert_called_once_with(pdf_path)
        mock_pt.assert_called_once_with(pdf_path)
        assert result.method == "pdftotext"
        assert result.text == clean

    @pytest.mark.asyncio
    async def test_garbage_check_parity_odl_garbled_uses_pdftotext(
        self, tmp_path, monkeypatch
    ):
        """ODL output that fails the quality check falls back to pdftotext (never
        emits garbage), exactly as the checks would gate pdftotext."""
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")

        garbled = "\x00\x01\x02 x x x x x x x x x x x x x x x x x x x x x"
        clean = "A well-formed paragraph of readable English prose."
        router = PDFRouter()
        with patch.object(
            router, "_extract_with_opendataloader", return_value=(garbled, 9.0)
        ) as mock_odl:
            with patch.object(
                router, "_extract_with_pdftotext", return_value=(clean, 4.0)
            ) as mock_pt:
                with patch.object(
                    router,
                    "_assess_text_quality",
                    side_effect=lambda t: (0.9, False) if t == clean else (0.1, True),
                ):
                    with patch.object(router, "_page_dimensions_pymupdf", return_value={}):
                        result = await router.extract(pdf_path, extract_figures=False)

        mock_odl.assert_called_once_with(pdf_path)
        mock_pt.assert_called_once_with(pdf_path)
        assert result.method == "pdftotext"
        assert result.text == clean
        assert result.ocr_required is False

    @pytest.mark.asyncio
    async def test_both_fast_paths_garbled_falls_through_to_ocr(
        self, tmp_path, monkeypatch
    ):
        """If ODL and pdftotext both fail the garbage check, go to OCR."""
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")

        garbled = "\x00\x01\x02 x x x x x x x x x x x x x x x x x x x x x"
        router = PDFRouter()
        with patch.object(
            router, "_extract_with_opendataloader", return_value=(garbled, 9.0)
        ):
            with patch.object(
                router, "_extract_with_pdftotext", return_value=(garbled, 4.0)
            ):
                with patch.object(
                    router, "_assess_text_quality", return_value=(0.1, True)
                ):
                    with patch.object(router, "_page_dimensions_pymupdf", return_value={}):
                        with patch.object(
                            router,
                            "_extract_with_lightonocr",
                            new=AsyncMock(return_value=("OCR recovered text.", [], 50.0)),
                        ) as mock_ocr:
                            result = await router.extract(pdf_path, extract_figures=False)

        mock_ocr.assert_awaited_once()
        assert result.method == "lightonocr"
        assert result.ocr_required is True

    @pytest.mark.asyncio
    async def test_structured_odl_empty_falls_back_and_clears_structured_data(
        self, tmp_path, monkeypatch
    ):
        pdf_path = tmp_path / "doc.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
        monkeypatch.setenv("PDF_EXTRACTOR", "opendataloader")
        monkeypatch.setenv("ORCHESTRATOR_ODL_STRUCTURED", "1")

        clean = "Recovered clean body text from pdftotext."
        router = PDFRouter()
        with patch.object(
            router,
            "_extract_with_odl_table_backend",
            return_value=("", None, 9.0, "local"),
        ):
            with patch.object(
                router, "_extract_with_pdftotext", return_value=(clean, 4.0)
            ) as mock_pt:
                with patch.object(
                    router,
                    "_assess_text_quality",
                    side_effect=lambda t: (0.9, False) if t else (0.0, True),
                ):
                    with patch.object(router, "_page_dimensions_pymupdf", return_value={}):
                        result = await router.extract(pdf_path, extract_figures=False)

        mock_pt.assert_called_once_with(pdf_path)
        assert result.method == "pdftotext"
        assert result.structured_data is None


class TestExtractBatchOpendataloader:
    """Batch warming: one JVM invocation amortized across many PDFs."""

    def test_batch_single_convert_call(self, tmp_path):
        pdfs = []
        for i in range(3):
            p = tmp_path / f"doc{i}.pdf"
            p.write_bytes(b"%PDF-1.4\n%EOF\n")
            pdfs.append(p)

        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=True,
        ):
            with patch.dict("sys.modules", {"opendataloader_pdf.wrapper": MagicMock()}):
                from opendataloader_pdf.wrapper import convert as mock_convert

                def write_all(paths, **kwargs):
                    out = Path(kwargs["output_dir"])
                    for pth in paths:
                        (out / f"{Path(pth).stem}.md").write_text(
                            f"Body of {Path(pth).stem}", encoding="utf-8"
                        )
                    return None

                mock_convert.side_effect = write_all
                results = router.extract_batch_opendataloader(pdfs)

        # Exactly ONE convert() call for the whole batch (single JVM).
        mock_convert.assert_called_once()
        args, kwargs = mock_convert.call_args
        assert len(args[0]) == 3
        assert kwargs["format"] == "markdown"
        for p in pdfs:
            text, latency = results[str(p)]
            assert text == f"Body of {p.stem}"
            assert latency >= 0

    def test_batch_runtime_unavailable_returns_empty(self, tmp_path):
        p = tmp_path / "doc.pdf"
        p.write_bytes(b"%PDF-1.4\n%EOF\n")
        router = PDFRouter()
        with patch(
            "src.services.pdf_router._opendataloader_runtime_available",
            return_value=False,
        ):
            results = router.extract_batch_opendataloader([p])
        assert results[str(p)] == ("", 0.0)

    def test_batch_empty_input(self):
        assert PDFRouter().extract_batch_opendataloader([]) == {}
