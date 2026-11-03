"""VB-CERT-1: the independent certificate checker accepts a real certificate and rejects forgeries."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import cert_check  # noqa: E402
from cert_check import CertificateRejected, verify  # noqa: E402
from fold import Belief, FoldResult  # noqa: E402
from gate import Outcome, UsePolicy, evaluate  # noqa: E402
from lattice import Grade, Q_LEVELS, T_LEVELS, parse_grade  # noqa: E402

AS_OF = "2026-11-03T00:00:00Z"
FRONTIER = 7


def _real_cert(policy_kw=None, con=()):
    b = Belief(claim_id="c1")
    b.pro_paths = [("e1", Grade(3, 3)), ("e2", Grade(2, 1))]
    b.con_paths = list(con)
    b.pro_sources = ["s1", "s2"]
    b.pro = Grade(3, 3)
    b.con = Grade(*(max(g.q for _, g in con), max(g.t for _, g in con))) if con else Grade(0, 0)
    fr = FoldResult(beliefs={"c1": b}, iterations=1, frontier=FRONTIER, as_of=AS_OF,
                    ignored_frame_types={})
    kw = dict(use="wiki-authoritative", floor=Grade(3, 3), standard="DV", min_disjoint_supports=2)
    kw.update(policy_kw or {})
    res = evaluate("c1", fr, UsePolicy(**kw))
    assert res.outcome == Outcome.ALLOW, res.reasons
    return res.certificate


def _ok(cert):
    return verify(cert, expected_frontier=FRONTIER, expected_as_of=AS_OF)


def _rehash(cert):
    cert["certificate_hash"] = cert_check._chash({k: v for k, v in cert.items() if k != "certificate_hash"})
    return cert


def test_tables_match_real_lattice():
    assert tuple(Q_LEVELS) == cert_check.Q_LEVELS and tuple(T_LEVELS) == cert_check.T_LEVELS


def test_real_certificate_rederives():
    r = _ok(_real_cert())
    assert r["ok"] and r["result"] == "PASSED"


def test_checker_shares_no_imports_with_emitter():
    src = (REPO / "scripts/vidya/cert_check.py").read_text()
    for banned in ("import fold", "from fold", "import gate", "from gate", "lattice", "canonical import",
                   "import canonical"):
        assert banned not in src.split('"""', 2)[2], banned


def test_altered_verdict_rejected_even_when_rehashed():
    c = _real_cert()
    c["result"] = "FAILED"
    with pytest.raises(CertificateRejected, match="certificate_hash"):
        _ok(c)
    with pytest.raises(CertificateRejected, match="result"):
        _ok(_rehash(c))


def test_forged_pass_on_insufficient_inputs_rejected():
    c = copy.deepcopy(_real_cert())
    for r in c["inputs"]:
        r["Q"], r["T"] = "Hinted", "Located"       # downgrade the evidence, keep PASSED
    with pytest.raises(CertificateRejected):
        _ok(_rehash(c))


def test_swapped_frontier_rejected():
    c = _real_cert()
    c["frontier"] = FRONTIER + 5
    with pytest.raises(CertificateRejected, match="certificate_hash"):
        _ok(c)
    with pytest.raises(CertificateRejected, match="frontier"):
        _ok(_rehash(c))
    with pytest.raises(CertificateRejected, match="frontier"):
        verify(_real_cert(), expected_frontier=FRONTIER + 5, expected_as_of=AS_OF)


def test_stale_as_of_rejected():
    c = _real_cert()
    with pytest.raises(CertificateRejected, match="as_of"):
        verify(c, expected_frontier=FRONTIER, expected_as_of="2026-11-04T00:00:00Z")
    c["as_of"] = "2026-10-01T00:00:00Z"
    with pytest.raises(CertificateRejected, match="as_of"):
        _ok(_rehash(c))


def test_label_only_attestation_rejected():
    c = _real_cert()
    c["input_attestations"] = ["e1", "e2"]
    with pytest.raises(CertificateRejected, match="label-only"):
        _ok(_rehash(c))


def test_attestation_digest_mismatch_rejected():
    c = _real_cert()
    c["input_attestations"][0] = "sha256:" + "0" * 64
    with pytest.raises(CertificateRejected, match="input_attestations"):
        _ok(_rehash(c))


def test_policy_tamper_rejected():
    c = _real_cert()
    c["policy"]["fields"]["min_disjoint_supports"] = 0
    with pytest.raises(CertificateRejected, match="policy"):
        _ok(_rehash(c))


def test_conflict_rederived():
    c = _real_cert({"allow_conflicted": True}, con=[("x", Grade(3, 3))])
    assert _ok(c)["result"] == "PASSED"
    c["policy"]["fields"]["allow_conflicted"] = False
    c["policy"]["digest"] = cert_check._chash(c["policy"]["fields"])
    with pytest.raises(CertificateRejected, match="result"):
        _ok(_rehash(c))
