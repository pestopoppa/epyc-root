# Inkblot as a candidate in the Inkling 2 Mini study

**Use native three-pass Inkling 2 Mini as the baseline.** On the authors’ 64-item DeepScaleR slice, Inkblot solves 12 more problems at the same depth. Four passes add one more solve on that slice. The available aggregates cannot tell us which items changed or whether the result will transfer to our worker workload. [Publisher’s model card](https://huggingface.co/Ex0bit/Inkblot-2-mini/blob/fb0b924f46a74331e34ce4f4288177f9dc0383c8/README.md#L30)

| Author-reported outcome | Base, 3 passes | Inkblot, 3 passes | Base, forced 4 passes | Inkblot, 4 passes |
|---|---:|---:|---:|---:|
| DeepScaleR, 64 items | 32 | 44 | 2 | 45 |
| GSM8K, 128 items | 120 | 121 | 4 | 123 |
| LiveCodeBench, 32 items | 11 | 13 | 1 | 13 |

The card’s +3.1-point three-pass GSM8K result belongs to the intermediate FP-Solve checkpoint (124/128). Inkblot’s gain at that depth is 0.78 points. Three-pass ARC-Challenge, HellaSwag and WinoGrande each decline. The same publisher supplied the paper, card and summary JSON. The accepted training sequence, held-out results, task suite and pass count must each keep their own denominator. [Model evaluation table](https://huggingface.co/Ex0bit/Inkblot-2-mini/blob/fb0b924f46a74331e34ce4f4288177f9dc0383c8/README.md#L34)

## Checkpoint identity

The Hub manifests identify a changed main shard and an identical separate MTP shard. The text/vision config, weight map, template and quantization metadata match. The candidate’s packaged evaluation YAML is byte-identical to the parent’s. [Base files](https://huggingface.co/thinkingmachines/Inkling-2-Mini/tree/c9d028302cd0f035fdf8e7e91f089a4ce94d2195) · [Candidate files](https://huggingface.co/Ex0bit/Inkblot-2-mini/tree/fb0b924f46a74331e34ce4f4288177f9dc0383c8)

| LFS object | Bytes | SHA-256 reported by Hub |
|---|---:|---|
| Base main shard | 19,526,019,168 | `65e60f51aa1284d4fb022584908c315270334d991828bb774af60584523539d1` |
| Inkblot main shard | 19,526,019,168 | `59312c8841614cff95b6531cd259235d0175b09220aed84eddeae8f3ed354b58` |
| MTP, both releases | 635,801,416 | `7c3b651317f01f73bcf4e1dceba66ef8b7e1a1eac6bc171e882e690a4b10a1d2` |

The edit list names 327 distinct changed tensors, including 48 in layers 18–23 and 39 global attention-residual tensors. The list’s arithmetic mean relative change is 0.0921%. The model’s separate audit names a Looper output, 321 modified tensors and a 0.8211% mean. The repository’s multi-generation summary reports 327 and 0.843%. The reports lack enough common provenance to establish that they measured the same output with the same reduction. Per-tensor byte comparison remains part of the proposed study. [Edit list](https://huggingface.co/Ex0bit/Inkblot-2-mini/blob/fb0b924f46a74331e34ce4f4288177f9dc0383c8/weight_edit_report.json) · [Model audit](https://huggingface.co/Ex0bit/Inkblot-2-mini/blob/fb0b924f46a74331e34ce4f4288177f9dc0383c8/integrity_audit.json) · [Repository audit](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/results/integrity_audit.json)

## Can the released training recipe explain the result?

The reported method first fits a regularized edit to align the forced fourth pass with the third, then uses answer-verified generations to update the controls. The paper attributes instability to a layer-17 sign reversal. Its small-slice observation gives a reason to instrument repetition and completion. A causal claim would require a controlled intervention. [Author paper](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/paper/main.pdf)

The released gate rejects a transition that decreases the total number correct. The published accepted totals are **111 → 112 → 114 → 118 → 114 → 116** out of 192. A separately reported merge reaches 120. The released runner lacks the inputs and merge lineage needed to recreate that sequence. An external contributor’s open PR adds native-runtime tests and an audit that detects the mismatch. Its software tests use small initialized models, and its revised selection policy returns the last accepted checkpoint. [Original gate](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/rse_looper/gspo.py#L120) · [Original run summary](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/blob/765453d13878804c49876a656f39b57a4384dca4/results/gspo_results.json) · [Repair and audit PR](https://github.com/eelbaz/Recursive-Self-Improving-Loopers/pull/1)

## Existing EPYC owner

The active EVL-02 track owns the experimental base port, CPU comparison, MI210 placement and indexed-bias HIP support. Its recorded pre-v11 build restriction and the separate HIP acceptance still govern those tasks. The approved EVL-02 tasks add artifact verification, a matched derivative arm and a GPU concurrency check. For GPU interpretation, the stock-Base report on two RX 9070 XTs is a reason to compare one versus two **busy** slots on the same MI210 server. That report did not isolate the cause. [Current Inkling study](../../../handoffs/active/model-evaluation-queue.md#track-model-evaluation-queue) · [HIP report](https://github.com/ggml-org/llama.cpp/issues/33150) · [Approved filing and protocol](stage3-plan.md)

## Source register

| Sweep | Sources | Question |
|---|---|---|
| 1 | [Released implementation](intake-3025.md) · [Inkblot checkpoint](intake-3026.md) | What changed, and how large is the matched-depth result? |
| 2 | [Independent repair PR](intake-3027.md) · [Author paper and web report](intake-3028.md) · [HIP field report](intake-3030.md) · [Official variable-depth control](intake-3031.md) | Can the release replay its claims, and what else could produce repetition or a depth effect? |
| 3 | [Merged HIP implementation](intake-3029.md) · [Deterministic weight-edit control study](intake-3032.md) | Which implementation and experimental controls transfer to the planned study? |

No further source surfaced that could independently establish the checkpoint’s quality, lineage or behavior on MI210. The fourth authorized sweep was unused. The bounded search included the model hub’s candidate, derivative and discussion records, the source and repair histories, the paper’s references, and previous EPYC intakes on the official base and GGUF port. This intake used source code, reports, and artifact metadata. No model weights were downloaded and no local inference or training was run.
