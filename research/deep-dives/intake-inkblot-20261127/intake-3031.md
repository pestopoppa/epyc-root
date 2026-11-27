# TML-d24-varloop-research

**intake-3031 · Sweep 2 · partial source read**

[Primary source](https://huggingface.co/thinkingmachines/TML-d24-varloop-research)

## Evidence

- Confirmed. The variable-depth checkpoint used a 1:2:6:2:1 sampling ratio for one through five passes during later midtraining. [README.md:L104-L106 @ 91a57fe](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/raw/91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d/README.md)
- Confirmed. The publisher cautions against direct comparison because the two models diverge in later training. [README.md:L104-L110 @ 91a57fe](https://huggingface.co/thinkingmachines/TML-d24-varloop-research/raw/91a57fe2b779bbd12c0f74d1f518cbd5b84e8d0d/README.md)

## Limits and corrections

Read the pinned training description, evaluation notes and loop config. No weight download or model evaluation. This release shares pretraining and first midtraining with Mini but continued with variable depths and post-trained at three passes.

2026-11-27. An adjustable native research release is evidence about a separately trained model. It cannot substitute for forcing four passes on the fixed checkpoint.

## Recommendations

- RI-DEPTH. Gate a four-pass study on a successful three-pass screen and independently validated runtime parity.

## Sources surfaced

The official launch post and base card repeat the distinction or were previously covered. No additional experiment on the derivative surfaced.

Artifact audit clean. External code and model weights were not executed.
