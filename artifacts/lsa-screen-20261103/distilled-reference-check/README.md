# Distilled reference preflight

PASS, limited to one synthetic layer-3 case. Existing `test_reference.py` checks real-map projection using a local formula, and selection against upstream using unrelated random index vectors; it does not join the released distilled map to upstream selection. This check joins both paths: fixed seed 20261103, 5200 synthetic keys, nine query positions including 5199 (4612 retained of 5200), released map layer 3. Exact equality is required for projected query/key tensors and the entire selected index arrays. Upstream uses `regroup_partial`, `KeyAndQueryProjection`, `build_buckets`, and `read`. The projection class is extracted unmodified by AST from upstream source to avoid importing the GPU-only cutlass dependency. No model or GPU is used. This does not establish GPU, model-level or other-layer parity.

Upstream commit `97b82d695b74ca341965a16bbc2a951c8b0c567a`. Actual released map filename is `qwen38_27b__long-16k-1M-heavy-key-and-query-d2048.pt`; its SHA-256 is `24cee934f969756db228a8df7f2bc7613979b63ac3b1d5ac3d9aa42e4339bb9b`. The candidate reference hash, upstream source hashes and comparison results are in `run.log`. The check script SHA-256 is `8afe1a92c6b5ee9b244f48e923787e3f2e2ef5641792c783860a2c76621e3b4d`.

The command below acquired real sub-quarter cores 0 and 1 in q0, role build; `run.log` records acquisition. It exited successfully, releasing the claim, and subsequent `region-lock status` showed q0 free.

```bash
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 0-1 --role build --timeout-s 15 --tag lsa-distilled-reference-check -- /usr/bin/env PYTHONPATH=/tmp/latent-sparse-attention-inspect/src OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /usr/bin/taskset -c 0-1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103/distilled-reference-check/check.py
```
