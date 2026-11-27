# Recursive Self-Improving Loopers (paper and author web report)

**intake-3028 · Sweep 2 · full source read**

[Primary source](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/paper/main.pdf)

## Evidence

- Confirmed within the stated scope. The authors attribute forced-depth instability to a layer-17 direction accounting for 75.5% of pass-shift energy. [Paper §2 and author web report docs/index.html:L47-L49 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/docs/index.html)
- Confirmed within the stated scope. The paper attributes the final checkpoint to merging accepted generations, without supplying the realized weights or parent hashes. [Paper §4 and docs/index.html:L62-L64 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/docs/index.html)
- Confirmed. The supplied Harbor 4.1 summary records zero tasks resolved by the edited model, matching base on its ten tasks. [Paper §5 and results/terminal_bench.json:L13-L22 @ 765453d](https://raw.githubusercontent.com/eelbaz/Recursive-Self-Improving-Loopers/765453d13878804c49876a656f39b57a4384dca4/results/terminal_bench.json)

## Limits and corrections

Read all four pages, equations, table and references plus same-commit HTML companion and result JSON. PDF sha256 ecc6351a086c5c6541c8fcd4cf4df0952c62c41ffbd3717f4c1cd0c7523f1ec2. §3 presents the preserve/edit/ridge objective. The layer-17 statistic is descriptive. No independent intervention isolates that direction. Harbor command count rises 10 to 63, while Terminal-Bench Core uses different tasks and forced four-pass base (0/10 versus 6/10).

2026-11-27. Paper and model card come from the same experiment. Keep Harbor and Core separate. Accepted-generation aggregation is mismatched with the released code. Distinguish FP-Solve label-free calibration from answer-verified GSPO. Other ES and self-programming papers describe different interventions and do not determine checkpoint quality.

## Recommendations

- RI-DEPTH. Gate a four-pass study on a successful three-pass screen and independently validated runtime parity.
- RI-TRAIN. Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control.
- RI-PROVENANCE. Distinguish author-shared figures, inherited benchmark YAML and distinct task suites from independent evidence.

## Sources surfaced

The deterministic comparison was selected for sweep 3. Self-WSP (2611.28833), continual test-time ES (2610.24137) and EGGROLL (2609.10980) investigate distinct optimization methods. None compares the released checkpoints or explains their provenance; retain as bibliography only.

Artifact audit clean. External code and model weights were not executed.
