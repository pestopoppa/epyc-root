# ESC-7 Decision Package — MEASUREMENT.md Amendment Draft (values pending)

**Status: TEMPLATE — populated by the session when EV-11c + EV-4b terminal data lands; the operator
applies §2 by hand (human-amendment-only). Prepared 2026-07-21 per the standing instruction
(op-bundle ESC-7-FINAL).**

## 1. Evidence summary (code columns FILLED 2026-07-22 from EV-4c; math columns pending overnight E7c rerun)

**Run provenance**: the code columns are **EV-4c** (`eval_tower_calibration_baseline_HE-R+/{frontdoor,worker_general}_ev4c/`),
superseding EV-4b whose calibration was void (chat-path n_probs never reached llama — fixed `83f53382`) —
EV-4b remains the accuracy-only record and reproduced EV-4 exactly. Both EV-4c arms: decision_grade=True,
zero reasons — the first decision-grade calibration rows in the project.

**Code-domain decision-test reading (preliminary, pending math)**:
- AUROC materially above 0.5: **PASS** (frontdoor 0.634; worker 0.575 — weaker but consistent direction).
- ECE stable across the domain's arms: **PASS with note** — 0.253 vs 0.322, same overconfidence signature,
  ordering coherent (weaker model → worse calibration AND discrimination); Δ0.069 recorded, not an artifact
  of one role.
- Provenance clean: **PASS** (both confidence_is_real=True, source completion_probabilities_geomean fleet-wide).

| Axis | EV-11c math (worker_general) | EV-11c math (worker_math) | EV-4b code HE-R+ (frontdoor) | EV-4b code HE-R+ (worker_general) |
|---|---|---|---|---|
| n scored | ⟨n⟩ (E7c rerun overnight 07-22) | ⟨n⟩ (E7c rerun) | **820** ✅ | **817** ✅ |
| accuracy | ⟨v⟩ | ⟨v⟩ | **0.7085** (3rd exact reproduction) | **0.6585** (EV-4: 0.6572 — within 1.1q) |
| ECE (closed-bin, real confidence) | ⟨v⟩ | ⟨v⟩ | **0.2532** ✅ | **0.3216** ✅ |
| AUROC | ⟨v⟩ | ⟨v⟩ | **0.6337** ✅ | **0.5751** ✅ |
| confidence_is_real | must be True | must be True | **True** ✅ | **True** ✅ |
| Top-1 / Bottom-1 / ρ / MAE | n/a (math) | n/a | **1.0 / 0.0 / 0.2105 / 0.2949** | **1.0 / 0.0 / 0.1234 / 0.3454** |

**Decision test the data must pass before §2 is applied** (else the package recommends staying
observational, with the specific gap named):
- AUROC materially above 0.5 on ≥1 domain (confidence discriminates correct from incorrect);
- ECE stable across the two arms of a domain (not an artifact of one role);
- no `confidence_not_real` blocker on the terminal rows (provenance clean).

## 2. The MEASUREMENT.md edit (operator applies by hand, verbatim once values are inline)

Append to the protocol section (alongside P-QUAL rows):

```
### P-CAL — Verifier/answer calibration (ECE / AUROC)                    [added YYYY-MM-DD]
- Instruments: eval-tower.math-rebaseline (GSM8K+MATH-500, n=1,819/arm, math_verify, seed 42,
  production sampling) and eval-tower.calibration-baseline.v1 (Scoring Verifiers HE-R+,
  n=820/arm candidate-level, code_execution labels, seed 42). Era: E7-eval-instrument and later
  ONLY — pre-E7 calibration rows are void (proxy confidence).
- ECE = closed-top-bin stat_tests definition (ece_instrument_era=ev11b_closed_bin_2026_07_20),
  10 bins. Confidence = completion-probability geomean; a row gates ONLY when its aggregate
  carries confidence_is_real=True — proxy or mixed-provenance ECE is an observation FOREVER.
- Decision-capable uses: (a) RLVR reward calibration/discrimination components re-enter at their
  existing weights (rlvr_tiers) for rows passing the provenance requirement; (b) verifier-model
  promotion (EV-5/EV-7) may gate on ECE ≤ ⟨measured baseline + margin TBD from data⟩ and
  AUROC ≥ ⟨measured baseline − margin⟩ against the same-domain P-CAL baseline.
- Baselines (era anchor, this amendment): math ECE ⟨v⟩/⟨v⟩, AUROC ⟨v⟩/⟨v⟩ (worker_general/
  worker_math); code ECE ⟨v⟩/⟨v⟩, AUROC ⟨v⟩/⟨v⟩ (frontdoor/worker_general). Ledger rows:
  ⟨run_ids⟩.
```

## 3. Follow-on agent changes (queued; execute after the operator applies §2)

- [ ] Un-gate `rlvr_tiers` calibration+discrimination for provenance-clean rows (keep the
  `confidence_not_real` blocker path for everything else — it becomes the enforcement of §2's
  provenance clause, not a neutralizer).
- [ ] Thread `confidence_is_real` through `export_rlvr_environment`'s SimpleNamespace so exported
  rows can earn calibration credit (currently all fail-closed).
- [ ] Add the P-CAL protocol ids to the entries' `journal_quarantine_rule` references and cite the
  amendment date in the next EV-5/EV-7 entry authored.

## 4. If the data fails the decision test

Recommend: ECE/AUROC stay observational; file the specific gap (e.g. code-geomean compression →
consider salient-token confidence as an EV-CONF follow-up; or AUROC ≈ 0.5 → confidence carries no
signal at current temperature and the calibration program needs a different confidence source
before any gating). No MEASUREMENT.md change; ESC-7 remains open with the evidence attached.
