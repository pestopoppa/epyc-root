# K-shift model test: inconclusive sensitivity gate

Row `kshift-fix-model-test-20261119-r1` ended rc=0 on 2026-11-19. Its native verdict is `FUTILITY_INSENSITIVE`; the filed verdict is **inconclusive**. The predeclared stop rule ended the run after the first candidate/baseline pair, two of ten planned runs. This does not validate the complete H1–H3 package or satisfy KSHIFT-FIX-MODEL-TEST step (1).

The observed arm used Qwen3-1.7B-Q8_0, f16 K, native RoPE, 24 CPU threads, 448 prefix tokens and 64 probe positions. Lower KLD and fewer top-1 mismatches are better. The no-shift noise KLD was 0.001426211, giving threshold 0.004278633. The half-shift negative control reached only 0.003770928 KLD against a required 0.03, so harness sensitivity failed.

| Scenario | Candidate mean KLD | Baseline mean KLD | Candidate top-1 mismatches | Rule |
|---|---:|---:|---:|---|
| translate x1 | 0.002114893 | 0.002114893 | 2 | fails mismatch ceiling of 1 |
| translate x4 | 0.001501084 | 0.001501084 | 0 | passes this arm |
| round trip | 0.001092505 | 0.001092505 | 1 | passes this arm |
| seq_div | 0 | 3.025076 | 0 | candidate passes; baseline has 48 mismatches |

The seq_div comparison detects the H2 sign defect in this arm: candidate and reference maximum positions both equal 223. This bounded observation does not override the failed sensitivity gate. The x1 translation mismatch is identical in both libraries and therefore does not isolate a regression from these patches. YaRN, quantized-K and Llama arms did not run; neither available model covers H3's partial-rotary defect.

Candidate source was champion C10 `7f1bd044b` plus H2/H3 patches. Native build proofs bind candidate libllama SHA-256 `79459a2c8a17e2dd5bbba8d04a1cfe74c42680e117d2e084dc6acb054a87e94a`, baseline libllama `94697aa1909e987faa6b394bd9db982521b6fd8af16f9300ab55d388afce7338`, and test binary `4caf5702a16a8555c8600d406c9ee27ddfb64c40d0cbe2627f277b78ae01ba54`; both runs reported the expected mapped libraries. No production change was made.

Native evidence stays at `/mnt/raid0/llm/tmp/kshift-fix-model-test-20261119-r1/` (retention/reclaim is owned by filing):

- `out/results.jsonl`: SHA-256 `9f0a43ef8cdc78f00ea69c5ee29e31f04f2ca4960001f35154acb89005653b7a`.
- `out/RESULT.json`: SHA-256 `c95af8a45ff19d60f2de323e24fbcc9d539daf0a8a8fad5ed6277327665b1acf`.
- `out/BUILD.json`: SHA-256 `1980e80f90e966212f271b83168f26d86dd8234e946c9db5f57eab1b29bfc607`.
- `job.py`: SHA-256 `0c78be689492a633c1fc2f4b1070e1b55ac9627a0ef266806fd4a172a4826a7d`.
- Test source `out/src/tests/test-kshift-model.cpp`: SHA-256 `73748c6be895d4728ffeca07b5e8f48d3c295166f70336397be35f2b24da088a`.

Next action: inspect why the half-cache shift is weak and why uniform translation changes two top-1 decisions in both libraries; design a stronger control and justify any revised protocol before another row. Preserve the original thresholds and this verdict. Champion folding and upstream draft remain open. This report records a committed conclusion (`[belief: cc]`), without retrofitting measurement warrants; prospective source capture belongs to VB-YARN-E1.
