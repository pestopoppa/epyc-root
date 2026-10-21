# 2026-10-21 yarn-kshift-fix

- Confirmed by failing test (`test-yarn-kshift`, champion `dd3d9721c`): YaRN x4 round-trip K NMSE 8.79e-2, shifted-vs-fresh 1.92e-2; non-YaRN `attn_factor` 1.1 round trip 4.41e-2; m=1 models 3e-15.
- Fix `experimental/yarn-kshift-fix-20261021` @ `b67a5b9bc` (fork): `build_rope_shift` passes 1/(ext_factor != 0 ? 1+0.1 ln(1/freq_scale) : 1). All tests <= 2e-9; non-YaRN digests bit-identical; CPU ROPE 448/448.
- Manifest row V11-100 (PEND, next consolidation after C2). KPF-62.1 note added. HIP ROPE optional.
- Evidence: /mnt/raid0/llm/tmp/yarn-kshift-fix-20261021/
