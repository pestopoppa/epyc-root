from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "publication"))

from generate_public_results import collect_rows, render_page  # noqa: E402


def test_collect_rows_marks_unprotocolled_results_for_backfill():
    text = """# Results

## Production Throughput - verified

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | verified sweep |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].entity == "Qwen-test"
    assert rows[0].quant_or_size == "Quant: Q4_K_M"
    assert rows[0].metrics == "t/s: 42.0"
    assert rows[0].protocol_status == "evidence-linked; needs protocol tag"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_render_page_is_generated_claim_triage_surface():
    rows = collect_rows("""# Results

## Bench

| Model | PPL | Throughput |
|---|---|---|
| A | 6.1 | 100 tok/s |
""")

    page = render_page(rows, Path("RESULTS.md"))

    assert "Status: generated draft, not publication-ready." in page
    assert "Rows without explicit protocol tags are held for backfill" in page
    assert "| Results / Bench | A |  | PPL: 6.1; Throughput: 100 tok/s" in page
