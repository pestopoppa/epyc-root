# mainD — resume ODL-P2 (Unlimited-OCR single-pass arm + demo run)

## 1. Drain first

```
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python scripts/coordination/session_bus.py drain --agent mainD
```

Act on MUST-ACT items. Refresh your heartbeat after draining.

## 2. Assigned row

**Task text (the identity):** `opendataloader-pipeline-integration--P2-L615`
**Row ref (a hint only):** `handoffs/active/opendataloader-pipeline-integration.md:615`

Your prior session already built the Unlimited-OCR arm:
- `unlimited_ocr.py` NEW producer (Q5_K_M + mmproj-F16, port 19331, max_tokens 4096, DRY guard
  `--dry-multiplier 0.8 --dry-penalty-last-n 128`), wired through `odl_bench/adapter.py`,
  `manifest_stubs.py` stub, +3 tests. **26/26 passed.**

Remaining next steps from your morning log:
1. Confirm the model download completed (Q5_K_M + mmproj-F16, ~3 GB to
   `/mnt/raid0/llm/models/Unlimited-OCR-GGUF/`); verify file sizes + GGUF header.
2. On inference grant: `adapter.py run-model --engine unlimited_ocr --gt OmniDocBench_demo.json
   --image-root .../demo_data/omnidocbench_demo/images --run-dir ... --allow-inference --score`
   under the window.
3. Score, record CER/TEDS + latency, update handoff row + log, commit + push.

Note your own finding: `paddleocr_vl.py DEFAULT_BINARY` points at stale `build-hip`; use
`build-v9-hip`. Compute is inference-owned — send a `compute-request` for the MI210 window
(BUS_PROTOCOL rule 11) and wait for the grant.

## 3. Wrap-up at checkpoints

Run the wrap-up skill at every checkpoint boundary. Write your own progress file at
`progress/2026-08/2026-08-13-mainD.md` (update the one from this morning).

## 4. Compute

Compute windows are granted by `inference` at its discretion. Do not self-claim CPU regions or the
MI210 (operator directive 2026-08-13, BUS_PROTOCOL rule 11).
