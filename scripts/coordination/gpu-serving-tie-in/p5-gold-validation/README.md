# P5 known-gold binding helper

`gold_binding.py` is a prospective, model-free input binder and native-report coverage checker; it does not execute SWE-bench or establish scorer correctness. The P5 agentic harness and its exact scorer are not yet bound. Do not present the historical `gold.gold-slice-20260724.json` 40/40 as validation of a new P5 scorer: that report belongs to the earlier oracle-mode instrument. The historical question file's `exact_match` setting is a placeholder, not the official patch-scoring result.

Before exposing questions to a model, freeze the actual question JSON list (`id`), original SWE-bench JSON list (`instance_id`, `patch`, `repo`, `base_commit`, `FAIL_TO_PASS`), and the actual scorer entrypoint:

```sh
python3 gold_binding.py freeze --questions QUESTIONS.json --dataset DATASET.json --scorer SCORER.py --output BINDING.json
```

The output is create-only. Store and hash it before executing any gold run; retain all input bytes and the entire scorer's transitive source/environment separately, since the tool hashes only the supplied scorer file. Gold patches and tests stay in the dataset, not the generated binding. Run the **actual P5 scorer** under an authorized model-free booking with the exact bound gold patches, preserve native results and command/environment identity, and then check:

```sh
python3 gold_binding.py check --questions QUESTIONS.json --dataset DATASET.json --scorer SCORER.py --binding BINDING.json --report GOLD_REPORT.json
```

The checker requires exactly the bound IDs to complete and resolve without errors and verifies source bytes/counters. `REPORT_COVERAGE_MATCH` means report consistency only: it does not authenticate who produced the report, establish fresh execution, or prove the scorer behaves correctly. A valid instrument review must separately demonstrate that controlled unpatched or intentionally broken patches fail their named `FAIL_TO_PASS` tests, positive gold patches pass without regressions in `PASS_TO_PASS`, and incomplete/error cases never count as resolved. Preserve the raw logs and per-case verdicts; do not substitute a report label for negative controls.

The checker intentionally requires a fully scoped report: `total_instances` and any supplied submitted IDs/count must equal the bound cases, and any supplied incomplete or empty-patch IDs/count must be empty or zero. Some native SWE-bench subset reports count or list cases outside the selected slice; those valid reports are refused by this helper. Use an evaluation and predictions file scoped to the bound cases, or extend and test the checker against the exact native subset semantics before relying on it. Do not trim or rewrite a native report to make it pass.

On 2026-11-02, `python3 -m unittest discover -s scripts/coordination/gpu-serving-tie-in/p5-gold-validation -p 'test_*.py'` passed all nine model-free helper controls. These synthetic controls exercise binding and report-coverage handling only; they do not run the P5 instrument or validate a gold patch or scorer.
