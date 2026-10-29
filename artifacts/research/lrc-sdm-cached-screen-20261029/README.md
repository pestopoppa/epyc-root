# Historical observed-outcome routing screen, 2026-10-29

**Disposition: data-limited descriptive diagnostic; no pilot or deployment.** The original producer and strict research-screen profile landed before fitting (orchestrator `af8a6d09e1a09ad1e05776b31df6a88f84fd271e`, root `72d81e66fb84def67b799928e6fe896178010ea9`; root `f3d7a58d10dc9c800c72fa9e816f8bf0ada689fd` adds distinct-case tests). The original receipt projects through the shared measurement grader as Judged/Located, not decision-gating: no codified measurement protocol is claimed.

The exact historical cache and labels matched the preregistered hashes. A June 28 pool backup resolved all 540 qids. Grouping and seed-42 suite stratification froze 538 connected text groups into 324 training, 110 calibration and 106 test questions. The five-token shingle, first-4096-character grouping rule is an operational near-duplicate screen, not proof that all related questions were grouped. The current cache's seven invalid embeddings included three in test. Train/calibration/test outcomes were used only at their designated stage; `FIT_STARTED` and `TEST_OPENED` are original one-shot markers. No production weights or service were changed.

The historical refitted hard-label MLP is a P4.5 comparator, not the production Q-weighted router. The HGB regressor used the fixed recipe and observed role cells only, with equal weight per question. The train-only role mean and shuffled-label negative control used the same partition. No configured serving correctness-rate floor was found; the diagnostic choices are unconstrained model outputs, while the experimental serving policy would abstain and use its incumbent fallback. This is not an adoption test.

| Diagnostic | Result |
|---|---:|
| HGB raw observed-cell RMSE | 0.41647 (136 cells) |
| Train-role-mean raw observed-cell RMSE | 0.44390 (136 cells) |
| Shuffled-label raw observed-cell RMSE | 0.48326 (136 cells) |
| HGB selected outcome available | 59 / 106 test questions |
| MLP selected outcome available | 72 / 106 test questions |
| Both selected outcomes available | 57 / 106 (53.8%), 57 independent groups |
| Paired mean HGB minus MLP outcome | 0.0000; group-bootstrap 95% lower bound 0.0000 |

The 53.8% paired coverage fails the predeclared 90% criterion, and the gain and lower bound fail the 2pp/positive-bound criteria. The available outcomes do not establish a negative technique result: unobserved alternatives remain unknown. Architect-general (17 training, 10 calibration groups) and ingest-long-context (8, 1) fail the sparse-evidence minima; four roles meet those minima, which are not proof of calibration or adequate precision. The historical inventory lacks model/configuration identity, per-role sample counts and timestamps, and its task/image/context features are not attested live TaskIR values.

This directory is a byte-identical preservation copy of the producer's original evidence directory. The receipt and original manifest retain the original absolute custody paths under `/mnt/raid0/llm/tmp/lrc-sdm-cached-screen-20261029-final`; they are not rewritten to manufacture a later receipt. Preserve that original directory for live adapter ingestion. The original receipt SHA-256 is `39a3d3f25c91a2ffe5cda838d802c157b74b8f759729705071f847c2e124cad1` and the report SHA-256 is `b0f069fab8f5d81975e12b88f235d9db6a5984eb585a2ead5da4cd476c171997`.
