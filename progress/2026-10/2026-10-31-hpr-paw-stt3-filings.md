# HPR, PAW and STT3 results — 2026-10-31

### 2026-10-31 HPR FIX2 64k R5 — bounded partial

`hpr-fix2-prospective64k-r5-20261030` ended outer rc75 on `FILLER_DEADLINE_EXCEEDED`, with captured-process cleanup verified. The native work receipt separately reports rc1 and partial=false; its underlying cause is not established. Five of six dense/coarse × three-wave cells have logged OK; 35 requests completed of 36 attempted, with 35 native request and 35 wire records. The last coarse wave remains incomplete and its exposed request must retain its original custody. The outer policy verdict is null: the predeclared six-cell `decide_121` diagnostic is not complete and no timing, adoption or holdout pass follows. Owner action: preserve all request/cell evidence and investigate the native failure and safe continuation under original no-redraw policy. [Bounded receipts and raw hashes](../../artifacts/compute/codex3-filing-hpr-paw-stt3-20261031-0439/). [belief: cc]

### 2026-10-31 PAW superlative control — launcher failure

**FAILED-RUN, class harness:** `codex3-paw-superlative-control-20261030` ended rc127 before its inner job when the host could not execute `/workspace/repos/epyc-orchestrator/scripts/region-lock`. The predeclared eight paired cases have no native result files or DONE; arm/category correct, incorrect, UNSURE, invalid and missing outcomes are unknown. Selected cases were not exposed by this attempt. Owner action: qualify a host-visible lock path, preserving the failed attempt and original declaration before any safe successor; no efficacy or superiority conclusion follows. [Bounded receipt and declaration hash](../../artifacts/compute/codex3-filing-hpr-paw-stt3-20261031-0439/). [belief: cc]

### 2026-10-31 CS-8.STT3 shared chunk preparation

`codex3-cs8-stt3-chunks-20261030` completed its preparation diagnostic rc0. The frozen-plan manifest SHA-256 `a1dc8fb416d50702136cf2debd3e9d21b3c5e7a21f20a3990bc77a82bfb8d8aa` records 3,070 inputs: 3,069 OK, one `void_no_vad_boundary`, and 3,098 chunks. A metadata replay found contiguous coverage and no chunk over 480,000 samples for every OK record. For `it_it:10896702735150958436.wav`, the 508,800-sample input has a single VAD speech segment ending at 485,856, beyond the 480,000-sample boundary; the frozen no-cut-inside-speech policy therefore retains VOID without replacement. This completes the chunk-preparation output including its VOID, not the STT3 parity gate or an ASR-quality verdict. Preserve the VOID and original manifest in later comparison. [Bounded receipt and audit](../../artifacts/compute/codex3-filing-hpr-paw-stt3-20261031-0439/). [belief: cc]

No scientific checkbox changed.
