# Do We Really Need an LLM for Weight-Space Programming? A Deterministic Forward-Only Paradigm and Its Capability Boundaries

**intake-3032 · Sweep 3 · partial source read**

[Primary source](https://arxiv.org/abs/2611.34612v1)

## Evidence

- Confirmed. The blind dispatch comparison holds the validation guard and two-step horizon constant. [§4.2, matched-search comparison and Table 1(b)](https://arxiv.org/html/2611.34612v1)
- Confirmed within the stated scope. The authors tested open optimizers on structured faults. [§5, limitations](https://arxiv.org/html/2611.34612v1)

## Limits and corrections

Versioned HTML read from disk, focused on §4–5 and Table 1(b). Six DINOv2-Base faults × three seeds. Author reports 15/18 deterministic and 6/18 model exact dispatches. Same small tool library and bounded horizon. Other experiments concern different models, faults and optimization methods. No Inkblot or EPYC experiment.

2026-11-27. The deterministic-control design transfers. Exact dispatch rates on synthetic vision faults do not measure language-model training, checkpoint ability, CPU inference or MI210 runtime.

## Recommendations

- RI-TRAIN. Gate a training attribution experiment on recoverable lineage and include a simple matched-budget control.

## Sources surfaced

The original Self-WSP paper is a separate study of weight-edit proposals. It cannot identify the cause of any Inkblot gain. No further primary comparison warranting a fourth sweep surfaced.

Artifact audit clean. External code and model weights were not executed.
