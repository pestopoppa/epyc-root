# Inkblot-2-mini

**intake-3026 · Sweep 1 · partial source read**

[Primary source](https://huggingface.co/Ex0bit/Inkblot-2-mini)

## Evidence

- Confirmed. Published config defaults to three fixed passes through layers 6–17. [config.json:L67-L72 @ fb0b924](https://huggingface.co/Ex0bit/Inkblot-2-mini/raw/fb0b924f46a74331e34ce4f4288177f9dc0383c8/config.json)
- Confirmed. On the same 64 DeepScaleR items at three passes the card reports base 32 correct and Inkblot 44. [README.md:L34 @ fb0b924](https://huggingface.co/Ex0bit/Inkblot-2-mini/raw/fb0b924f46a74331e34ce4f4288177f9dc0383c8/README.md)
- Confirmed within the stated scope. The HF audit lists 321 modified tensors for an output directory named Inkling-2-Mini-Looper. [integrity_audit.json:L2-L9 @ fb0b924](https://huggingface.co/Ex0bit/Inkblot-2-mini/raw/fb0b924f46a74331e34ce4f4288177f9dc0383c8/integrity_audit.json)
- Reattributed. At three passes the displayed GSM8K gain of 3.1 points belongs to FP-Solve. The counts for Inkblot give a one-item gain (121 versus 120 of 128). [README.md:L37 @ fb0b924](https://huggingface.co/Ex0bit/Inkblot-2-mini/raw/fb0b924f46a74331e34ce4f4288177f9dc0383c8/README.md)
- Reattributed. The packaged evaluation YAML cites the parent Inkling model card as its source. [.eval_results/Inkling-2-Mini.yaml:L6-L8 @ fb0b924](https://huggingface.co/Ex0bit/Inkblot-2-mini/raw/fb0b924f46a74331e34ce4f4288177f9dc0383c8/.eval_results/Inkling-2-Mini.yaml)

## Limits and corrections

Read author card, edit list, audit, both pinned model trees, config, index, quantization, template and copied eval metadata. Base revision c9d028302cd0f035fdf8e7e91f089a4ce94d2195. Main LFS digest differs at equal 19,526,019,168 bytes. MTP LFS digest matches. No tensor payloads were downloaded. The 327 unique positive entries include 288 BF16 and 39 FP32, and include later layers and global attention-residual tensors. Mean listed rel_change ×100 is 0.092109%.

2026-11-27. Different audit records report 321 and 327 edits, with different mean changes and no shared output digest or metric definition. Tensor-level expert/vision identity is unverified. Four-pass Inkblot scores 45/64 compared with 44/64 at three. The raw matched three-pass GSM8K gain is 0.78 points. HellaSwag, ARC-Challenge and WinoGrande decline at native depth. Exact-name HF Hub and replication searches found the author release, discussion relays and a software repair, with no independent paired evaluation or candidate GGUF in the search.

## Recommendations

- RI-ART. Bind both source and converted checkpoints, prove the scope of changes and preserve reload identities before the quality comparison.
- RI-PAIR. Compare the saved models at native three-pass depth with paired held-out correctness, cost and complete failure counts.
- RI-DEPTH. Gate a four-pass study on a successful three-pass screen and independently validated runtime parity.
- RI-PROVENANCE. Distinguish author-shared figures, inherited benchmark YAML and distinct task suites from independent evidence.

## Sources surfaced

The fixed parent already has a verified intake. The variable-depth card and HIP field report were selected for sweep 2. Release announcements, an empty discussion page and the openinterpretability review request supply no new observations.

Artifact audit clean. External code and model weights were not executed.
