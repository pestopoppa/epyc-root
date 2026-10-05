"""TOC-RD-1: PEM private-key redaction when a truncated log drops the END line.

Fixtures use the ED25519 header variant the redactor matches. (The pre-existing
test_credential_redaction.py carries credential-shaped fixtures that the staged-blob
PII pre-commit scan now blocks, so these cases live in their own file.)
"""

from src.repl_environment.redaction import redact_credentials


def test_truncated_private_key_redacted_to_end_of_text():
    # A truncated log keeps BEGIN + body but loses the END line.
    text = (
        "$ head -3 id_ed25519\n"
        "-----BEGIN ED25519 PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/yGaXm\n"
        "more key data here\n"
        "[... truncated before compression at 200000 chars]"
    )
    result = redact_credentials(text)
    assert result.text == "$ head -3 id_ed25519\n[REDACTED:ssh_private_key]"
    assert "MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn" not in result.text
    assert result.categories == frozenset({"ssh_private_key"})


def test_terminated_private_key_keeps_trailing_text():
    # The END-line case is unchanged: only the key block is replaced.
    text = (
        "before\n"
        "-----BEGIN ED25519 PRIVATE KEY-----\n"
        "b3BlbnNzaC1rZXktdjEAAAAACmFlczI1Ni1jdHI\n"
        "-----END ED25519 PRIVATE KEY-----\n"
        "after the key"
    )
    result = redact_credentials(text)
    assert result.text == "before\n[REDACTED:ssh_private_key]\nafter the key"
    assert result.redacted_count == 1


def test_terminated_key_followed_by_truncated_key_both_redacted():
    text = (
        "a\n-----BEGIN ED25519 PRIVATE KEY-----\nAAAA1111\n-----END ED25519 PRIVATE KEY-----\n"
        "b\n-----BEGIN ED25519 PRIVATE KEY-----\nBBBB2222\n"
    )
    result = redact_credentials(text)
    assert result.text == "a\n[REDACTED:ssh_private_key]\nb\n[REDACTED:ssh_private_key]"
    assert result.redacted_count == 2
