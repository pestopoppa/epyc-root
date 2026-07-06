from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "publication"))

from generate_public_results import (  # noqa: E402
    apply_scrub_gate,
    apply_review_decisions,
    backfill_target_counts,
    historical_attestation_review_counts,
    collect_rows,
    decision_for_row,
    review_decision_counts,
    missing_protocol_fields,
    parse_protocol_reference,
    protocol_status_counts,
    public_scrub_text,
    render_page,
    render_review_queue,
    review_queue_counts,
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
| Qwen-test | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-06-14] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == "protocol-tagged (missing attestation) [P-BENCH-2; n=5; 2026-06-14]"
    assert rows[0].action == "hold_for_protocol_backfill"


def test_collect_rows_marks_pre_attestation_rows_for_historical_review():
    text = """# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Qwen-test | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-03-21] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].protocol_status == (
        "protocol-tagged (pre-attestation-era; missing attestation; "
        "needs historical attestation or remeasurement) [P-BENCH-2; n=5; 2026-03-21]"
    )
    assert rows[0].action == "hold_for_historical_attestation_review"


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


def test_parse_protocol_reference_accepts_punctuated_attestation():
    protocol = parse_protocol_reference("Protocol: P-BENCH-2, n=5, 2026-04-26, attestation: a3f2")

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
    assert "### Protocol Backfill Summary" in page
    assert "- `verification decision`: 1" in page
    assert "### Protocol Status Summary" in page
    assert "- `unverified historical row`: 1" in page
    assert "### Public Scrub Summary" in page
    assert "- `public-safe surface`: 1" in page
    assert "Rows without explicit protocol tags are held for backfill" in page
    assert "| Results / Bench | A |  | PPL: 6.1; Throughput: 100 tok/s | unverified historical row | public-safe surface" in page


def test_protocol_and_backfill_summaries_are_actionable():
    rows = collect_rows("""# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Complete | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-04-26, attest a3f2] |
| Missing attest | Q4_K_M | 43.0 | [P-BENCH-2, n=5, 2026-06-14] |
| Historical attest | Q4_K_M | 43.5 | [P-BENCH-2, n=5, 2026-03-21] |
| Missing all | Q4_K_M | 44.0 | [P-BENCH-2] |
| Needs tag | Q4_K_M | 45.0 | verified sweep |
| Historical | Q4_K_M | 46.0 | old note |
""")

    assert protocol_status_counts(rows) == {
        "evidence-linked; needs protocol tag": 1,
        "protocol-tagged (missing attestation) [P-BENCH-2; n=5; 2026-06-14]": 1,
        "protocol-tagged (missing n/reps, date, attestation) [P-BENCH-2]": 1,
        (
            "protocol-tagged (pre-attestation-era; missing attestation; "
            "needs historical attestation or remeasurement) [P-BENCH-2; n=5; 2026-03-21]"
        ): 1,
        "protocol-tagged [P-BENCH-2; n=5; 2026-04-26; attest a3f2]": 1,
        "unverified historical row": 1,
    }
    assert backfill_target_counts(rows) == {
        "attestation": 1,
        "n/reps, date, attestation": 1,
        "protocol tag": 1,
        "verification decision": 1,
    }
    assert historical_attestation_review_counts(rows) == {
        "historical attestation or remeasurement": 1,
    }
    assert review_queue_counts(rows) == {
        "historical-attestation-review": 1,
        "protocol-tag-needed": 1,
        "publish-candidate-review": 1,
        "structured-protocol-backfill": 2,
        "verification-decision-needed": 1,
    }


def test_structured_protocol_markers_are_queued_for_backfill():
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
    assert backfill_target_counts(rows) == {"structured protocol backfill": 1}
    assert review_queue_counts(rows) == {"structured-protocol-backfill": 1}

    page = render_review_queue(rows, Path("RESULTS.md"))

    assert "## structured-protocol-backfill" in page
    assert "Normalize partial protocol metadata into MEASUREMENT.md claim grammar or keep on hold." in page


def test_render_review_queue_groups_next_actions():
    rows = collect_rows("""# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Needs tag | Q4_K_M | 45.0 | verified sweep |
| Historical | Q4_K_M | 43.5 | [P-BENCH-2, n=5, 2026-03-21] |
| Old row | Q4_K_M | 46.0 | old note |
""")

    page = render_review_queue(rows, Path("RESULTS.md"))

    assert "Status: generated triage queue, not publication-ready." in page
    assert "- `historical-attestation-review`: 1" in page
    assert "- `protocol-tag-needed`: 1" in page
    assert "- `verification-decision-needed`: 1" in page
    assert "## historical-attestation-review" in page
    assert "Find a real historical attestation artifact" in page
    assert "| 7 | Results / Production | Needs tag | t/s: 45.0 | evidence-linked; needs protocol tag" in page
    assert "| 8 | Results / Production | Historical | t/s: 43.5 | protocol-tagged (pre-attestation-era" in page


def test_scrub_status_flags_public_surface_blockers():
    scrub = scrub_status(
        "Production",
        "Qwen",
        "Quant: Q4",
        "log: /mnt/raid0/private/run.json http://localhost:8080",
    )

    assert scrub == "needs public scrub: local path, loopback endpoint"


def test_public_scrub_text_replaces_internal_role_aliases():
    text = "frontdoor delegates to architect_general and ingest_long_context"

    assert public_scrub_text(text) == (
        "routing entrypoint delegates to architecture specialist and long-context worker"
    )


def test_collect_rows_scrubs_internal_role_aliases_before_rendering():
    text = """# Results

## Production frontdoor

| Model | Quant | t/s | Notes |
|---|---|---|---|
| architect_general | Q4_K_M | 42.0 | [P-BENCH-2, n=5, 2026-04-26, attest a3f2] |
"""

    rows = collect_rows(text)

    assert len(rows) == 1
    assert rows[0].section == "Results / Production routing entrypoint"
    assert rows[0].entity == "architecture specialist"
    assert rows[0].protocol_status == "protocol-tagged [P-BENCH-2; n=5; 2026-04-26; attest a3f2]"
    assert rows[0].scrub_status == "public-safe surface"
    assert rows[0].action == "publish_candidate"


def test_scrub_gate_only_demotes_publish_candidates():
    assert apply_scrub_gate("publish_candidate", "needs public scrub: local path") == "hold_for_public_scrub"
    assert apply_scrub_gate("hold_for_protocol_backfill", "needs public scrub: local path") == "hold_for_protocol_backfill"


def test_review_decision_overlay_can_retire_unverified_bucket_by_default():
    rows = collect_rows("""# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Old row | Q4_K_M | 46.0 | old note |
| Needs tag | Q4_K_M | 45.0 | verified sweep |
""")
    decisions = {
        "default_decisions": {
            "verification-decision-needed": {
                "decision": "retired_from_public_claims",
                "reason": "no row-specific evidence bundle",
            }
        }
    }

    decisioned = apply_review_decisions(rows, decisions)

    assert decisioned[0].action == "retired_from_public_claims"
    assert decisioned[0].review_decision == "retired_from_public_claims"
    assert decisioned[0].review_reason == "no row-specific evidence bundle"
    assert decisioned[1].action == "hold_for_protocol_backfill"
    assert review_decision_counts(decisioned) == {"retired_from_public_claims": 1}
    assert review_queue_counts(decisioned) == {
        "protocol-tag-needed": 1,
        "retired_from_public_claims": 1,
    }


def test_review_decision_overlay_allows_row_specific_override():
    rows = collect_rows("""# Results

## Production

| Model | Quant | t/s | Notes |
|---|---|---|---|
| Old row | Q4_K_M | 46.0 | old note |
""")
    decisions = {
        "default_decisions": {
            "verification-decision-needed": {
                "decision": "retired_from_public_claims",
                "reason": "default",
            }
        },
        "rows": {
            "7": {
                "decision": "remeasure_required",
                "reason": "important comparison row",
            }
        },
    }

    assert decision_for_row(rows[0], decisions) == ("remeasure_required", "important comparison row")
    decisioned = apply_review_decisions(rows, decisions)

    assert decisioned[0].action == "remeasure_required"
    assert decisioned[0].review_reason == "important comparison row"
