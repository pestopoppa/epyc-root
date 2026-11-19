#!/usr/bin/env python3
"""Standalone verifier for epyc.vidya/certificate/v1 (VB-CERT-1, spec §11.2).

DELIBERATELY IMPORTS NOTHING FROM fold.py, gate.py, lattice.py or canonical.py. A checker that
shares code with the emitter shares its bugs; this file carries its own lattice ordinals, its own
canonical-JSON hasher and its own statement of the DV/SE rule. A test cross-checks the tables
against the real lattice so drift is caught there, not by importing here.

What it checks:
  1. grammar (_type, result vocabulary, required fields)
  2. certificate_hash recomputes (integrity ONLY: it is a self-hash, so a forger who edits and
     rehashes passes this step -- steps 3-6 are what stop them)
  3. policy digest recomputes from the stated policy fields
  4. every input_attestation is the sha256 digest of a stated input; label-only attestations and
     missing/extra digests are refused
  5. the verdict is RE-DERIVED from the stated inputs + policy and must equal `result`
  6. frontier and as_of equal the values the CALLER expects (required arguments, never defaulted):
     a certificate cannot vouch for its own freshness.

Proves the derivation is consistent with its stated inputs. It does not prove the inputs are the
ledger's (that needs frame coordinates + authentication, spec §15) and not that the claim is true.
"""
from __future__ import annotations

import hashlib
import json
import sys

CERT_TYPE = "epyc.vidya/certificate/v1"
Q_LEVELS = ("Q0", "Hinted", "Judged", "Verified", "Witnessed")
T_LEVELS = ("T0", "Located", "MachineLocated", "Anchored", "Attested")
CERTIFIABLE = ("SE", "DV")
RESULTS = ("PASSED", "FAILED", "ADVISORY")
POLICY_FIELDS = ("use", "floor", "standard", "conjunctive", "allow_conflicted",
                 "allow_review_required", "allow_labelled_stale", "min_disjoint_supports")
HASH_RE_LEN = 64


class CertificateRejected(Exception):
    """The certificate failed verification; args[0] names the failed check."""


def _chash(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _is_digest(x) -> bool:
    if not (isinstance(x, str) and x.startswith("sha256:") and len(x) == 7 + HASH_RE_LEN):
        return False
    return all(c in "0123456789abcdef" for c in x[7:])


def _grade(d, where):
    try:
        return Q_LEVELS.index(d["Q"]), T_LEVELS.index(d["T"])
    except (KeyError, ValueError, TypeError):
        raise CertificateRejected(f"{where}: unknown or missing grade {d!r}")


def _dominates(a, b):
    return a[0] >= b[0] and a[1] >= b[1]


def verify(cert: dict, *, expected_frontier: int, expected_as_of: str) -> dict:
    """Return a report dict on success; raise CertificateRejected on any failure."""
    if not isinstance(cert, dict):
        raise CertificateRejected("grammar: certificate is not an object")
    if cert.get("_type") != CERT_TYPE:
        raise CertificateRejected(f"grammar: _type {cert.get('_type')!r} != {CERT_TYPE}")
    for k in ("policy", "inputs", "input_attestations", "frontier", "as_of", "result",
              "verified_levels", "satisfying_paths", "disjoint_supports", "certificate_hash"):
        if k not in cert:
            raise CertificateRejected(f"grammar: missing field {k!r}")
    if cert["result"] not in RESULTS:
        raise CertificateRejected(f"grammar: result {cert['result']!r} not in {RESULTS}")

    # 2. self-hash (integrity only)
    body = {k: v for k, v in cert.items() if k != "certificate_hash"}
    try:
        if _chash(body) != cert["certificate_hash"]:
            raise CertificateRejected("certificate_hash: does not match certificate body")
    except (TypeError, ValueError) as e:
        raise CertificateRejected(f"certificate_hash: body not canonicalizable ({e})")

    # 6. freshness -- explicit, caller-supplied, type-strict
    fr = cert["frontier"]
    if isinstance(fr, bool) or not isinstance(fr, int) or fr != expected_frontier:
        raise CertificateRejected(
            f"frontier: certificate says {fr!r}, caller expects {expected_frontier!r}")
    if cert["as_of"] != expected_as_of:
        raise CertificateRejected(
            f"as_of: certificate says {cert['as_of']!r}, caller expects {expected_as_of!r}")

    # 3. policy
    pol = cert["policy"]
    fields = pol.get("fields") if isinstance(pol, dict) else None
    if not isinstance(fields, dict) or set(fields) != set(POLICY_FIELDS):
        raise CertificateRejected("policy: stated policy fields missing or malformed")
    if _chash(fields) != pol.get("digest"):
        raise CertificateRejected("policy: digest does not match stated policy fields")
    if pol.get("standard") != fields["standard"]:
        raise CertificateRejected("policy: standard disagrees with stated policy fields")
    if fields["standard"] not in CERTIFIABLE:
        raise CertificateRejected(f"policy: standard {fields['standard']!r} is not certifiable")
    floor = _grade(fields["floor"], "policy.floor")

    # 4. attestations: digests of stated inputs, exactly
    inputs = cert["inputs"]
    if not isinstance(inputs, list):
        raise CertificateRejected("inputs: not a list")
    atts = cert["input_attestations"]
    if not isinstance(atts, list) or not all(_is_digest(a) for a in atts):
        raise CertificateRejected(
            "input_attestations: entries must be sha256:<64 hex> digests (label-only refused)")
    try:
        expect = sorted(_chash(r) for r in inputs)
    except (TypeError, ValueError):
        raise CertificateRejected("inputs: not canonicalizable")
    if sorted(atts) != expect:
        raise CertificateRejected("input_attestations: digests do not match the stated inputs")

    # 5. re-derive
    pro, con = [], []
    for r in inputs:
        if not isinstance(r, dict) or r.get("side") not in ("pro", "con") or "label" not in r:
            raise CertificateRejected(f"inputs: malformed record {r!r}")
        (pro if r["side"] == "pro" else con).append((r["label"], _grade(r, "inputs")))
    if fields["conjunctive"]:
        satisfying = sorted(l for l, g in pro if _dominates(g, floor))
        pro_ok = bool(satisfying)
        con_ok = any(_dominates(g, floor) for _, g in con)
    else:
        satisfying = sorted(l for l, _ in pro)
        pro_ok = bool(pro) and _dominates(_join([g for _, g in pro]), floor)
        con_ok = bool(con) and _dominates(_join([g for _, g in con]), floor)
    if cert["satisfying_paths"] != satisfying:
        raise CertificateRejected(
            f"satisfying_paths: stated {cert['satisfying_paths']!r}, derived {satisfying!r}")
    for side, paths in (("pro", pro), ("con", con)):
        stated = cert["verified_levels"].get(side) if isinstance(cert["verified_levels"], dict) else None
        derived = _join([g for _, g in paths]) if paths else (0, 0)
        if stated != {"Q": Q_LEVELS[derived[0]], "T": T_LEVELS[derived[1]]}:
            raise CertificateRejected(f"verified_levels.{side}: stated {stated!r} not derivable")
    ds = cert["disjoint_supports"]
    if isinstance(ds, bool) or not isinstance(ds, int) or ds < 0:
        raise CertificateRejected("disjoint_supports: not a non-negative integer")

    derived_ok = (pro_ok
                  and (not con_ok or fields["allow_conflicted"])
                  and ds >= fields["min_disjoint_supports"])
    derived = "PASSED" if derived_ok else "FAILED"
    if cert["result"] != derived:
        raise CertificateRejected(f"result: stated {cert['result']!r}, re-derived {derived!r}")
    return {"ok": True, "result": derived, "frontier": fr, "as_of": cert["as_of"],
            "caveat": "derivation consistent with stated inputs; inputs not tied to ledger frames"}


def _join(grades):
    return (max(g[0] for g in grades), max(g[1] for g in grades))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("certificate", help="path to certificate JSON")
    ap.add_argument("--expected-frontier", type=int, required=True)
    ap.add_argument("--expected-as-of", required=True)
    a = ap.parse_args(argv)
    with open(a.certificate) as fh:
        cert = json.load(fh)
    try:
        print(json.dumps(verify(cert, expected_frontier=a.expected_frontier,
                                expected_as_of=a.expected_as_of), indent=2))
        return 0
    except CertificateRejected as e:
        print(f"REJECTED: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
