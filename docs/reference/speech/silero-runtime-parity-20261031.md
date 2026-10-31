# Silero serving-runtime parity

The original CS-22.V0 run completed all 224 CS-45 clips and 672 clip/arm comparisons without errors. All three serving paths differed from the fixed CS-45 ONNX reference and remain excluded from CS-22.V1 under that comparison. The task's acceptance was a parity table and explicit exclusion of differing runtimes, so its measurement/reporting work is complete.

## Original reference and artifact pins

| Artifact | Source revision | SHA-256 |
|---|---|---|
| CS-45 v6 ONNX | Existing CS-45 pin | `4cbf549b8326f60f80f2536d9eefeb450a9abe83365a098031c89719f1be17d2` |
| Whisper BIN | ggml-org/whisper-vad `9ffd54a1` | `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987` |
| Transcribe GGUF F32 | handy-computer/silero-vad-v6.2-gguf `a9b2d61c` | `0d871a800c420fdd5d1b17a3aea4296d1c39608f0ff4a9295eb76457eb1c88e6` |
| Silero JIT | silero-vad wheel 6.2.3 | `e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720` |

Point order is threshold:min-silence seconds: 0.5:0.3, 0.5:0.5, 0.5:0.75, 0.5:1.0, 0.5:1.2, 0.6:1.2.

| Runtime | Clips | Maximum per-clip frame delta | Median per-clip maximum | Stop-equal counts | Common-segment-equal counts |
|---|---:|---:|---:|---|---|
| whisper | 224 | 0.859892 | 0.581161 | 62, 65, 65, 66, 66, 64 | 36, 40, 40, 40, 40, 35 |
| gguf | 224 | 0.860614 | 0.589078 | 62, 66, 66, 67, 67, 70 | 35, 38, 38, 38, 38, 39 |
| jit | 224 | 0.860613 | 0.589076 | 62, 66, 66, 67, 67, 70 | 35, 38, 38, 38, 38, 39 |

These are common-postprocessor comparisons. They do not establish native segment-API equivalence. The retained native result digest is `f8a68921ffc426fce16266b07ad5e7995fdbdd60972dced47d1dd1e444437eec`; the [filing capsule](../../../artifacts/compute/refactor-cs22v0-parity-filing-20261031.json) points to its predeclaration, artifact pins and independent owner readback.

## Separate version-matched diagnostic

The 2026-10-31 diagnostic extracted ONNX from the same 6.2.3 wheel as the original JIT. It ran ONNX on the same 224 input WAVs and compared the retained JIT, GGUF and Whisper arrays. JIT and GGUF matched all stop events and common segments at all six operating points; global frame deltas were respectively 5.36442e-5 and 2.30074e-5. Whisper still differed, with 205–211 matching stop decisions and 195–200 matching common segment decisions out of 224.

This supports a model-version or interface mismatch as the principal explanation for the old JIT/GGUF reference gap. It does not prove GGUF weight identity or explain the remaining Whisper differences. The original CS-45 reference and negative verdict remain intact; V1 reference selection and the native frontend audit remain separate work.

The ONNX/JIT assets are canonical under `/mnt/raid0/llm/models/silero-vad-v6.2.3-official-wheel-20261031/`; retained private paths are hardlinks to the same inodes. The filing capsule references the custody receipt. No model bytes or signed result changed.

The bounded CPU diagnostic included a normal control, full 224-clip native ONNX execution, active STOP/drain and corrupted-raw refusal. Owner replay reopened all input/native hashes and rederived the six point decisions. Co-tenancy is unknown. No latency, quality, promotion or new grading claim follows. The conclusion is captured through `[belief: cc]`; no original measurement warrant is invented.
