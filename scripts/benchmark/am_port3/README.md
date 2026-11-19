# AM-PORT-3 offline fitter

`fit.py` implements the per-layer, per-KV-head beta and value solve for the
faithful AM port. It is independent of the native server and changes no default
decode path. Seven model-free tests cover analytic 5x compaction, an independent
normal-equations oracle, rank deficiency, masks, invalid inputs, undefined cosine,
and content identity/query split enforcement.

```bash
OPENBLAS_NUM_THREADS=1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python \
  -m unittest discover -s scripts/benchmark/am_port3 -v
```

The mathematics follows research repo `scripts/benchmark/attention_matching.py`,
blob `1ff2f885f005a784acc83d288940b20983a23d93` at commit
`a794f5b54bea1a1f0752e0e3514ce07fa14c5ff2`. Like its fast path,
beta is `log(max(lstsq(exp_scores[:, indices], sum(exp_scores)), 1e-12))`;
C2 solves compact attention weights against the original attention output.
Clamping least squares is the specified fast approximation to NNLS, not the
constrained optimum. This implementation uses float64 SVD internally rather than
the reference's float32 Torch `gels`, and exports float32 beta/C2. It does not
claim bitwise Torch agreement. No source files are copied from the research repo.

Each input NPZ contains ONE layer and KV head:

| Array | Shape | Meaning |
|---|---|---|
| K | T × Dk | Original keys after native QK normalization and RoPE |
| V | T × Dv | Original dequantized values, before any rewrite |
| Q_fit | Nfit × Dk | Calibration queries after native QK normalization and RoPE |
| Q_eval | Neval × Dk | Separate held-out queries in the same coordinates |
| indices | t | Sorted unique original cache row indices |
| fit_ids, eval_ids | Nfit, Neval | Unique strings encoding sequence, position, and query head |
| bias_fit, bias_eval | T or N × T | Optional original additive attention bias/mask |

GQA query heads belonging to this KV head are pooled on the query row axis.
Do not mix distinct KV heads or layers. The native cell carrier shares retained
positions across heads **and layers**, so the capture/selection stage must supply
the same indices to every shard. Independent per-head top-k selection cannot be
loaded into that carrier. Selection itself is not implemented here.

The sidecar JSON requires `source_commit`, `model_identity`, `capture_id`, integer
`layer`, integer `kv_head`, positive `attention_scale`, `coordinates: "post_rope"`,
and `capture_sha256`. Record the actual graph scale; do not infer it from model
embedding width. Identity strings must refer to the actual capture/build/model;
the digest check proves file binding, not the truth of caller-supplied identities.
Query ID disjointness refuses declared leakage; capture must also guarantee the
split's provenance. Use a frozen original cache for both query sets.

```bash
OPENBLAS_NUM_THREADS=1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python \
  scripts/benchmark/am_port3/fit.py --capture /scratch/head.npz \
  --metadata /scratch/head.json --out /scratch/new-fit-directory
```

Output `carrier.npz` contains indices, beta[t], and C2[t,Dv]. `FIT.json` binds
capture metadata, capture bytes, fitter source, and carrier bytes by SHA-256;
records rank/clamp diagnostics; and reports held-out mean/min cosine (higher is
better), relative L2 (lower is better), and undefined cosine count. Zero-norm
outputs have undefined cosine and cannot silently pass a threshold. Existing
output directories are refused. These records are offline diagnostics, with no
automatic native quality verdict or belief grade.

Original attention may include a mask; compact weights use beta alone, following
the reference. This is suitable for the frozen-cache decode view. It does not
establish correctness for arbitrary causal prefill masks, sliding windows, key
repositioning, future RoPE positions, or quantized carrier loading. Future native
integration must keep original retained positions, verify the export/reload
attention output, and measure cache quantization effects explicitly.

The solver holds N×T full attention and N×t least-squares matrices for one shard;
capture must bound N before scheduling. No 32K model run, 36 GiB memory proof,
16-layer cosine verdict, or default-off throughput/KLD comparison has been run.
AM-PORT-3 remains open for native capture, per-layer/head graph bias, C2 cache
loading and a published calibration/decode row. This code does not alter the
existing per-cell beta implementation.
