# DAR-4 bilinear selection — bounded source evidence

APP source commit `58598acd1031a500c41eef9034d26c165eab0a4f` (`Add opt-in bilinear candidate selection`) is published on orchestrator `origin/main`. Its parent is `a643cb331b1389eda0b414eb54bdac9bf90fe04b`; source scope is exactly five paths: four retriever/scorer files plus `tests/unit/test_bilinear_selection.py` (+508/-14).

The implementation adds an optional candidate-value callback after the existing retrieval filters. Empirical per-action Q continues to drive confidence, learned-use thresholds, and risk gates. Bilinear ranking requires the separate `HybridRouter(bilinear_selection_enabled=True)` opt-in and a scorer with versioned integer metadata, positive update count, expected dimensions, finite weights and bias, and valid model features. The existing `BILINEAR_SCORER_ENABLED` telemetry flag alone never enables selection. Unsupported roles, bools, numeric strings, invalid predictions, untrained/random state, legacy weights, malformed archives, and scoring failures retain empirical-Q ranking. A failed load preserves an already loaded valid scorer; a fresh scorer remains untrained and not selection-ready.

## Verification

R6 ran 61 model-free tests: selection controls, scorer tests, actual `HybridRouter.route()` integration, and router risk-gate regressions. Ruff checks and `git diff --check` passed. Run was 2026-11-01 05:36:54–05:37:14 UTC on CPUs 132–133 under the 36–37 mutex; elapsed 19.306 s; sampled process-tree peak RSS 203,198,464 bytes; captured processes drained; no native or GPU execution.

- Receipt: `R6-RECEIPT.json` SHA-256 `75dd4668817b7e6c8c31764c36dc623bc84f5caeb540390bffb3f29b4a0a4237`
- Pytest/validation output: `test.log` SHA-256 `548119495157b78dc6f8340423dde247022fe0b8ae1fee20e3da3c3504ee1ad1`
- Adapted accepted R6 wrapper: `run_r6.py` SHA-256 `4b82e2561e41240c2c7485e5feb406b4a7fbbeb822acd73a2ce1b67eb435e125`
- Full source review draft SHA-256: `e4f6b1cdc8d6d08ff973b3953e8b51cbdf059a89f35fa4492fd28606c3016669` (task scratch)

This is a controlled code-path proof, not model-quality, native cold-start, retraining-provenance, deployment, or adoption evidence. No live selection flag, weight file, model, process, server, or API was changed. The scorer's existing feature extraction and score direction were reused; no confidence threshold or grading ladder was added.
