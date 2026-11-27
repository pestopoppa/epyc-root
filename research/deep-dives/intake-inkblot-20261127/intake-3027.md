# Fix native looping, checkpoint exports, and auditable training

**intake-3027 · Sweep 2 · partial source read**

[Primary source](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/pull/1)

## Evidence

- Confirmed. The PR tests exact uncached native three-pass agreement on a tiny initialized model. [tests/test_model_integration.py:L13-L40 @ ad15629](https://raw.githubusercontent.com/tryingET/Recursive-Self-Improving-Loopers/ad15629dfd09856a03a3313be5a08d2718f44829/tests/test_model_integration.py)
- Confirmed. The historical evidence checker reads six existing summaries and does not rerun the experiment. [rse_looper/evidence.py:L400-L425 @ ad15629](https://raw.githubusercontent.com/tryingET/Recursive-Self-Improving-Loopers/ad15629dfd09856a03a3313be5a08d2718f44829/rse_looper/evidence.py)
- Confirmed. The repaired run returns the last accepted checkpoint. [README.md:L133-L145 @ ad15629](https://raw.githubusercontent.com/tryingET/Recursive-Self-Improving-Loopers/ad15629dfd09856a03a3313be5a08d2718f44829/README.md)
- Confirmed. The contributor audit reconstructs an accepted sequence containing a total-score regression from 118 to 114. [docs/REPRODUCIBILITY.md:L40-L46 @ ad15629](https://raw.githubusercontent.com/tryingET/Recursive-Self-Improving-Loopers/ad15629dfd09856a03a3313be5a08d2718f44829/docs/REPRODUCIBILITY.md)

## Limits and corrections

Open and unmerged at review. Compared base and head git bytes, forward/optimizer, tests and documentation. Pretrained, distributed and GPU execution untested here. Repaired training changes sampling. The contributor reports 190 passing CPU tests and a 409-key base metadata check. Scores in the original six JSONs are unchanged.

2026-11-27. The proposed repair supplies regression fixtures and prospective evidence capture. No independent replay of the historical accuracy. Changed sampling and final selection policy would define a new experiment. The in-memory candidate is scored before final export, which leaves a need to evaluate the actual reloaded artifact.

## Recommendations

- RI-ART. Bind both source and converted checkpoints, prove the scope of changes and preserve reload identities before the quality comparison.
- RI-TRAIN. Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control.

## Sources surfaced

The native Transformers pin and contributor tests were read as implementation dependencies of the PR. Base metadata was already covered. The PR supplies no independent checkpoint benchmark.

Artifact audit clean. External code and model weights were not executed.
