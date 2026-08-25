# mainA — 2026-08-25: PII candidate-gate failure — ownership + resolution

## Task
Operator-directed ownership of the pre-existing root candidate-gate failure surfaced by EVL-38:
`scripts/validate/candidate_eval_gate.sh` exiting 1 since ~2026-08-03 (`pii_fixture_eval` 39/40).

## Root cause (verified)
- Fixture `research/fixtures/pii_hygiene_eval.jsonl` (2026-07-29, commit `788dc3dc2`) case 1:
  `aws_access_key_id = AKIAIOSFODNN7EXAMPLE` → `expected_match: true` (must block).
- Hook `scripts/hooks/pii_precommit.sh` allowlists the exact literal `AKIAIOSFODNN7EXAMPLE` in
  `KNOWN_PLACEHOLDERS` (commit `8eeaf6c3`, 2026-08-03): AWS's published documentation example,
  used as a fake secret by real production tests
  (`epyc-orchestrator/tests/unit/test_episodic_work_payload.py:222`, `test_credential_redaction.py`).
- The allowlist (newer policy, explicit security rationale: exact-match, all-must-pass-per-line,
  lookalikes blocked) directly contradicts the fixture's case-1 expectation → 39/40.
- The asymmetry with fixture case 3 (`aws_secret_access_key = wJalrXUtnFEMI/...EXAMPLEKEY`, also a
  docs example, passing) is a regex-shape accident: the AKIA regex captures the bare key while the
  secret-key regex captures the assignment prefix, so only case 1 collides with the placeholder check.

## Resolution (fixture-evolution event, not a hook change)
The hook's placeholder policy is newer, documented, and protects real test code — it stands. The
fixture is now a two-direction contract for the placeholder mechanism:
1. Case 1 flips to `expected_match: false` with a `note` pinning the 8eeaf6c3 policy.
2. Added case: one-char-off lookalike `AKIAIOSFODNN7EXAMPLX` → must block (exact-match boundary).
3. Added case: placeholder + real-shaped key on one line → must block (all-must-pass boundary).

## Validation
- `python3 scripts/validate/pii_fixture_eval.py` → **42/42 passed**.
- `bash scripts/validate/candidate_eval_gate.sh` → **exit 0** ("candidate eval gate passed"),
  all legs green including the regenerated repo-readiness + focused tests (26 passed).

## Records updated
- `handoffs/active/repo-readiness-scorer.md` — 2026-08-25 closeout note: defect marked RESOLVED.
- `wiki/safety.md` — open question answered (RESOLVED 2026-08-25).
- `wiki/benchmark-methodology.md` — compiled 2026-08-25 section amended: repair landed.
- Bus: follow-up finding appended (ownership + resolution; corr_id EVL38-pii-gate-findings).
