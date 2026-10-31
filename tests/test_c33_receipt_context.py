"""Receipt-context controls with mkdir-only retained synthetic fixture data."""

import json
import os
from pathlib import Path
import re
import uuid
import pytest
from scripts.coordination import session_bus_coordinator as c

GATE = "TEST-C33-RECEIPT-CONTEXT"
EVENT = "token-prevalidation-receipt-context"


def request(validated=False):
    payload = {"gate_id": GATE, "block_ref": "handoffs/active/synthetic.md"}
    if validated:
        payload["validated"] = {
            "cmd": "echo synthetic",
            "dry_run_exit": 0,
            "dry_run_evidence": "synthetic.log",
        }
    return {
        "schema_version": 1,
        "id": "msg-c33-fixture-alice",
        "ts": "2026-10-31T00:00:00Z",
        "from": "alice",
        "to": "coordinator-agent",
        "kind": "token-request",
        "task_id": "synthetic-c33",
        "action_required": True,
        "needs_routing_to": ["coordinator-agent"],
        "payload": payload,
    }


@pytest.fixture
def retained_case(request):
    """Intentionally retained; no pytest numbered directory or cleanup callback."""
    base = Path(os.environ.get("C33_RETAINED_BASE", "/tmp/c33-retained-tests"))
    if base.is_symlink():
        raise RuntimeError("retained fixture base must not be a symlink")
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", request.node.name)[:80]
    case = base / (name + "-" + uuid.uuid4().hex)
    case.mkdir(mode=0o700)
    return case


@pytest.fixture
def isolated(retained_case, monkeypatch):
    root = retained_case / "bus"
    (root / "tokens").mkdir(parents=True)
    (root / "tokens/token-queue.md").write_text("# operator tokens\n")
    for name in ["outbox", "inbox"]:
        (root / name).mkdir()
    receipts = retained_case / "receipts"
    receipts.mkdir()
    monkeypatch.setattr(c, "REPO_ROOT", retained_case)
    monkeypatch.setattr(c, "RECEIPTS_DIR", receipts)
    config = {"roster": [{"id": "alice"}, {"id": "coordinator-agent"}]}
    return root, receipts, config


def append_request(root, validated=False):
    with (root / "outbox/alice.jsonl").open("a") as stream:
        stream.write(json.dumps(request(validated)) + "\n")


def notices(root):
    p = root / "inbox/coordinator-agent.jsonl"
    return (
        []
        if not p.exists()
        else [json.loads(line)["payload"] for line in p.read_text().splitlines()]
    )


@pytest.mark.parametrize("status", ["ratified", "spent", "applied", "attested"])
def test_unvalidated_receipted_request_has_review_context_but_never_permission(
    isolated, status
):
    root, receipts, _ = isolated
    (receipts / (GATE + ".json")).write_text(json.dumps({"status": status}))
    blocks, rows = c.relay_tokens(root, {"synthetic-c33": [request()]}, {}, 1)
    assert blocks == []
    context = [row for row in rows if row.get("check") == EVENT]
    assert len(context) == 1
    assert context[0]["receipt_status"] == status
    assert context[0]["receipt"].endswith(GATE + ".json")
    assert "lacks dry-run evidence" in context[0]["detail"]
    assert "NOT in token-queue.md" not in context[0]["detail"]
    assert not [row for row in rows if row.get("status") in ("READY", "COMPLETED")]


def test_receipt_transition_gets_one_new_notice_after_old_notice_was_consumed(isolated):
    root, receipts, config = isolated
    append_request(root)
    c.relay_token_blocks(root, config, 1)
    assert (
        len(
            [
                p
                for p in notices(root)
                if p.get("event") == "token-request-not-presented"
            ]
        )
        == 1
    )
    (receipts / (GATE + ".json")).write_text('{"status":"ratified"}')
    for epoch in range(2, 5):
        c.relay_token_blocks(root, config, epoch)
    receipt_notices = [p for p in notices(root) if p.get("event") == EVENT]
    assert len(receipt_notices) == 1
    action = receipt_notices[0]["action"]
    assert "OPERATOR" in action and "Do not" in action
    assert "re-file it with" not in action
    assert GATE not in (root / "tokens/token-queue.md").read_text()


@pytest.mark.parametrize("contents", [None, "not json", '{"status":"pending"}'])
def test_absent_unreadable_unspent_receipt_retains_original_refusal(isolated, contents):
    root, receipts, config = isolated
    append_request(root)
    if contents is not None:
        (receipts / (GATE + ".json")).write_text(contents)
    for epoch in [1, 2]:
        c.relay_token_blocks(root, config, epoch)
    payloads = notices(root)
    assert (
        len([p for p in payloads if p.get("event") == "token-request-not-presented"])
        == 1
    )
    assert not [p for p in payloads if p.get("event") == EVENT]
    assert GATE not in (root / "tokens/token-queue.md").read_text()


def test_validated_receipted_request_is_still_presented_unchecked(isolated):
    root, receipts, _ = isolated
    (receipts / (GATE + ".json")).write_text('{"status":"ratified"}')
    blocks, rows = c.relay_tokens(root, {"synthetic-c33": [request(True)]}, {}, 1)
    assert len(blocks) == 1 and "- [ ] **" + GATE + "**" in blocks[0]
    assert "already exists" in blocks[0]
    assert not [row for row in rows if row.get("check") == EVENT]


def test_receipted_invalid_request_preserves_existing_operator_block(isolated):
    root, receipts, _ = isolated
    original = "# operator tokens\n\n- [ ] **" + GATE + "** — original request\n"
    path = root / "tokens/token-queue.md"
    path.write_text(original)
    (receipts / (GATE + ".json")).write_text('{"status":"ratified"}')
    blocks, rows = c.relay_tokens(root, {"synthetic-c33": [request()]}, {}, 1)
    assert blocks == [] and path.read_text() == original
    assert len([row for row in rows if row.get("check") == EVENT]) == 1
    assert not any(
        "operator has not been asked" in row.get("detail", "") for row in rows
    )


def test_malformed_unvalidated_gate_cannot_trigger_an_extra_path_read(
    isolated, monkeypatch
):
    root, _, _ = isolated
    bad = request()
    bad["payload"]["gate_id"] = "../../outside"

    def forbidden(_):
        raise AssertionError("malformed unvalidated gate reached receipt read")

    monkeypatch.setattr(c, "spent_receipt_for", forbidden)
    blocks, rows = c.relay_tokens(root, {"synthetic-c33": [bad]}, {}, 1)
    assert blocks == [] and len(rows) == 1 and rows[0]["check"] == "token-prevalidation"


@pytest.mark.parametrize(
    "contents", ['"ratified"', '[{"status":"ratified"}]', "true", "1"]
)
def test_non_mapping_receipt_cannot_drop_existing_validation_refusal(
    isolated, contents
):
    root, receipts, config = isolated
    append_request(root)
    (receipts / (GATE + ".json")).write_text(contents)
    c.relay_token_blocks(root, config, 1)
    assert any(p.get("event") == "token-request-not-presented" for p in notices(root))
    assert GATE not in (root / "tokens/token-queue.md").read_text()
