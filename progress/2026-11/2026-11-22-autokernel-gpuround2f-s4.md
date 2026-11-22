# 2026-11-22 — autokernel: GPU-RESIDENT-ROUND-2f phase 3 step 4(a)-(c)

Box: `handoffs/active/autokernel-loop.md` → GPU-RESIDENT-ROUND-2f. Fork `llama.cpp-experimental-gpuround2f-20261121` @ `d81fb3367` (pushed).

- `a9a95691b` `LLAMA_DEVICE_CPOS=1`: device-mask cell positions come from the ring formula over the control block (p0 row plus a new high-water row 3), and csel is computed on the device. A host check against the cells falls back to host cpos.
- `f4022cf38` `LLAMA_DEVICE_SCOPY=1`: recurrent s_copy is device-resident with a host mirror. Nothing is written while it stays the identity.
- `d81fb3367` `LLAMA_DEVICE_DRAFT_IN=1`: the drafter's token batch comes from target vtok col 0 plus the mask id. Its positions come from target ctl row 0. Greedy dsel inputs are graph constants, and the vtok set_rows index is derived on the device. `llama_ctl_resolve` predicts the target mirrors before the draft.
- Gates (CPU, q3 pocket build claim held, then released) PASS for each step: test-kq-mask-dev bitwise, test-kv-layout-evict + FA_VKQ_F32, test-gdn-replay-identity. llama-server 27B+DFlash2 -np 2 rs_replay greedy ON == OFF, including concurrent requests.
- Counters, full stack: cpos 20 rounds on the device, 0 on the host. scopy hits 17 / writes 3. Drafter inputs device-fed in 12 of 16 drafts; the 4 misses are fresh sequences.
- Next: step 4(d), the K-round replay loop (NEXT note in the box). [no-belief: code checkpoint, CPU identity test]
- `b6273012f` `LLAMA_DEVICE_DSEL_RNG=1`: device Philox-Gumbel draft-selection noise (new GGML_OP_PHILOX_GUMBEL, CPU + HIP, bit-identical to common/philox.h) with a device-advanced per-seq counter. Gates PASS: test-philox-gumbel bitwise; 27B+DFlash2 -np 2 greedy, concurrent and temp-1 (seed 7) ON == OFF. Still open: fixed-shape inject / gather rows, drafter ctl path, the K-round loop, the row (RESUME NOTE 3 in the box). [no-belief: code checkpoint, CPU identity test]
