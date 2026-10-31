# NEMO-PROF-RESEG accepted closure — 2026-10-31

Closed the original NEMO-PROF-RESEG and its explicit parent NEMO-BOLT-PROF from the 2026-10-25 retained `nemo-gpu-prof` ROCm profiler traces. No GPU run, model download, serving change or production-kernel edit occurred. The prior 50 µs gap segmenter yielded invalid L plain and B step busy numbers under HIP graphs; the new artifact pins graph boundaries by exact repeated ordered kernel-name fingerprints and records all excluded edges.

| Pass | Complete steady graphs | Mean kernel busy | Mean graph span | Server wall/token |
|---|---:|---:|---:|---:|
| L, Qwen3.8-27B Q8_0 plain | 156 | 32.8851 ms | 57.3104 ms | 56.9829 ms |
| B, Nemotron-3.5-Bolt IQ2_XXS | 94 | 20.5130 ms | 22.0249 ms | 33.9236 ms |

B contains 97 observed groups of 40 SSM scans. The first two groups and one distinct transition are outside the 94 steady graphs. L contains 159 post-prefill graph starts, with two steady fingerprint classes and three explicit edge exclusions. Kernel busy is a sum of dispatch durations; graph span and server wall are separate observables. No paired Qwen3.6 comparison, hardware-counter causal finding, throughput/champion claim or low-bit adoption follows.

Source custody: original raw pass directories were copied byte-for-byte to `epyc-inference-research/data/nemo-gpu-prof/retained-raw-20261025/`; `SHA256SUMS` passed, with kernel CSV hashes `c1bebdff…ce267d8ca94` (L) and `4bfb3cdd…f241f891a8` (B). The compact replay artifact lives in `docs/reference/autokernel/nemo-gpu-prof-reseg-20261031/` (analyzer, result, provenance and README). Original `data/nemo-gpu-prof/` historical analysis and its category shares remain separate. Existing `VB-AK-SERVING-PROFILE-WIRE` owns future native profile write-side wiring; no duplicate source row, ladder or retrospective measurement warrant was added. Both original result ticks use `[belief: cc]` for this committed conclusion.
