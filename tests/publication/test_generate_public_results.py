from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "publication"))

from generate_public_results import (  # noqa: E402
    apply_scrub_gate,
    collect_rows,
    missing_protocol_fields,
    parse_protocol_reference,
    render_page,
    scrub_status,
)


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


def test_collect_rows_marks_case_insensitive_evidence_for_backfill():
    text = """# Results

## Production Throughput - Verified

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | canonical sweep |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "evidence-linked; needs protocol tag"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_collect_rows_marks_protocol_tagged_rows_as_publishable_when_complete():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-04-26, attest a3f2] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol-tagged [P-BENCH-2; n=5; 2026-04-26; attest a3f2]"
    assert rows[0].scrub_status == "public-safe surface"
    assert rows[0].action == "publish_candidate"


def test_collect_rows_marks_protocol_tagged_rows_for_hold_when_incomplete():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-04-26] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol-tagged (missing attestation) [P-BENCH-2; n=5; 2026-04-26]"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_collect_rows_lists_each_missing_protocol_component():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | [P-BENCH-2] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol-tagged (missing n/reps, date, attestation) [P-BENCH-2]"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_missing_protocol_fields_reports_attestation_gap():
    protocol = parse_protocol_reference("Protocol: P-BENCH-2, n=5, 2026-04-26")

    assert protocol is not None
    assert missing_protocol_fields(protocol) == ["attestation"]


def test_collect_rows_holds_unparseable_protocol_markers():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | protocol-id pending |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol marker present; needs structured protocol backfill"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_parse_protocol_reference_from_protocol_id_prefix():
    protocol = parse_protocol_reference("Protocol: P-BENCH-2, n=5, 2026-04-26, attest a3f2")

    assert protocol is not None
    assert protocol.protocol_id == "P-BENCH-2"
    assert protocol.n == "5"
    assert protocol.date == "2026-04-26"
    assert protocol.attestation == "a3f2"


def test_render_page_is_generated_claim_triage_surface():
    rows = collect_rows("""# Results

## Bench

| Model | PPL | Throughput |
|---|---|---|
| A | 6.1 | 100 tok/s |
""")

    page = render_page(rows, Path("RESULTS.md"))

    assert "Status: generated draft, not publication-ready." in page
    assert "- Total rows: 1" in page
    assert "- `hold_for_protocol_backfill`: 1" in page
    assert "### Public Scrub Summary" in page
    assert "- `public-safe surface`: 1" in page
    assert "Rows without explicit protocol tags are held for backfill" in page
    assert "| Results / Bench | A |  | PPL: 6.1; Throughput: 100 tok/s | unverified historical row | public-safe surface" in page


def test_scrub_status_flags_public_surface_blockers():
    scrub = scrub_status(
        "Production / frontdoor",
        "Qwen",
        "Quant: Q4",
        "log: /mnt/raid0/private/run.json http://localhost:8080",
    )

    assert scrub == "needs public scrub: local path, loopback endpoint, internal role alias"


def test_scrub_gate_holds_protocol_complete_internal_role_alias():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| frontdoor | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-04-26, attest a3f2] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol-tagged [P-BENCH-2; n=5; 2026-04-26; attest a3f2]"
    assert rows[0].scrub_status == "needs public scrub: internal role alias"
    assert rows[0].action == "hold_for_public_scrub"


def test_scrub_gate_only_demotes_publish_candidates():
    assert apply_scrub_gate("publish_candidate", "needs public scrub: local path") == "hold_for_public_scrub"
    assert apply_scrub_gate("hold_for_protocol_backfill", "needs public scrub: local path") == "hold_for_protocol_backfill"
