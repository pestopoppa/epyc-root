---
schema: epyc.brief.v1
id: AK-SHORT-ROW-CENSUS
box_text_sha: t:5cf15d96529da300
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/autokernel-loop.md
- epyc-root:research/deep-dives/intake-nov26-kernels/33019.md
approach: 'Pin trace digests, graph and candidate SHA. Emit op, quant type, K, rows, fused flag, width and frequency or unknown
  for every cell. Check later traces from each role. A verified zero closes that role. For hits compare split only, threshold
  only and both against current dispatch around exact-fit K. Include odd expert tails on wave64 before measuring time.

  '
acceptance: AK-SHORT-ROW-CENSUS.json contains quant_type, K, output_rows, fused, ncols, eligible_calls. All requested model/width
  cells have a count or an explicit unresolved reason.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/autokernel-loop.md: 8a642c938f4ee6c16d3e4f40d7b8eb7121363663
    epyc-root:research/deep-dives/intake-nov26-kernels/33019.md: 253bc6e997f06ed2d023cc63cc27b6eede6a4ef9
---
