# KPF-60 GPU attention-KV load estimate

This is a **derived estimate**, not a measured chunk-KV crossover or an end-to-end speed claim. `python3 crossover.py` regenerates the table from the retained P0 benchmark records and verifies their SHA-256s. No new inference was run.

The 2026-10-23 P0 `llama-bench` records identify MI210, model `Qwen3.8-27B-Q8_0.gguf`, build `dd3d9721c`, batch 2048 and **f16 K and V**. The model's Q8_0 name describes weights, not these KV types. Its currently available GGUF metadata reports 65 total blocks, one NextN block, full-attention interval 4, four KV heads and K and V head lengths 256. The 64-layer trunk therefore has 16 full-attention layers, assuming the default every-fourth-layer pattern: the current GGUF has no explicit recurrent-layer override. The existing design's independent layer inventory agrees. This model path and metadata are not proof that the historical run consumed the exact same model bytes.

- Current GGUF: `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf`; 29,036,089,344 bytes reported by the historical benchmark. SHA-256 of current bytes `[0, 10996704)` (GGUF metadata and tensor descriptors, not the whole model): `bc85f42a131e0aab2ca3e661859588b9b39101c803cb6d87bb4dab3afa978e92`. Metadata extracted with `gguf-py` `GGUFReader`; it reported `data_offset=10996704`. This pin is for the current header only, not historical full-file custody.
- **f16 payload per token:** `16 layers × 4 KV heads × (256 K + 256 V) elements × 2 bytes = 65,536 bytes`.
- Illustrative q8_0 K and V would use `16 × 4 × (256 + 256) × (34 / 32) = 34,816 bytes/token`, including the two-byte scale per 32-element GGML q8_0 block. That is **not** the KV type measured by the P0 benchmark. Other cache formats, padding or layout may differ.
- Only attention K/V bytes are modeled: the recurrent GDN state, checkpoint and chunk headers, allocator/alignment overhead, transfer setup, packing/unpacking, inject/shift, selector, sparse recompute, suffix processing, traffic contention and compression are not measured here and are not included. No KV payload has been serialized or counted for this table.

For each row `size = tokens × 65536`, PCIe time is `size / (28.9 × 10^9 bytes/s)` and NVMe time is `size / (4.5 × 10^9 bytes/s)`; their sum assumes serial cold NVMe-to-host then host-to-device transfer, no overlap. PCIe 28.9 GB/s is the approximate P0 pinned/pageable bulk H2D observation (64 MiB–2 GiB); 4.5 GB/s is the handoff's representative NVMe approximation, while the retained 1 GiB cold reads span 3.9–4.6 GB/s. **These bulk bandwidths have not been verified for these chunk I/O sizes or this serialization.** The recompute column is `tokens / avg_ts` from the corresponding P0 benchmark, with no inference about quality or equivalent end-to-end behavior.

| ubatch | prompt tokens | measured pp tok/s | f16 KV MiB | PCIe ms | NVMe ms | NVMe + PCIe ms | recompute ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | 512 | 851.65 | 32 | 1.16 | 7.46 | 8.62 | 601.19 |
| 512 | 2048 | 839.42 | 128 | 4.64 | 29.83 | 34.47 | 2439.77 |
| 512 | 8192 | 788.12 | 512 | 18.58 | 119.30 | 137.88 | 10394.37 |
| 2048 | 512 | 839.87 | 32 | 1.16 | 7.46 | 8.62 | 609.62 |
| 2048 | 2048 | 919.44 | 128 | 4.64 | 29.83 | 34.47 | 2227.44 |
| 2048 | 8192 | 867.36 | 512 | 18.58 | 119.30 | 137.88 | 9444.76 |

Under this idealized model the load component is smaller at each listed size, but it does not establish a net win: the 27B is a hybrid recurrent model and attention-only KV is not a complete reusable state. A native per-chunk byte counter, actual chunk-load/inject timing, recurrent-state handling and quality validation remain necessary. KPF-60.GPU-X remains open until qualified native bytes are available; the above is preparation and no new measurement warrant is asserted.

Original P0 source: `/mnt/raid0/llm/tmp/overnight-gpu-arm-20261022/runs/kpf60-p0-gpu/out/`. Retained `bench-ub512.json`, `bench-ub2048.json`, `pcie.json`, `nvme-1024m.txt` are byte-for-byte copies of that run. The calculation script checks their full SHA-256s. Source for the P0 inventory and planned drift corpus: `/mnt/raid0/llm/tmp/cacheclip-port-20261021/DESIGN.md` §2.1 and `p0_timing_plan.md`.
