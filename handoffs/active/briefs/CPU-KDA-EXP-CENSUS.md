---
schema: epyc.brief.v1
id: CPU-KDA-EXP-CENSUS
box_text_sha: t:8f4df37bed9b3ff1
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/cpu-decode-roofline-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/33077.md
approach: 'Pin graph, model, ISA, row lengths and trace windows; emit per-loop counts, time share and missing fields. Repeat
  on a later prompt. Stop on proven zero or an Amdahl bound smaller than the paired timing error. Otherwise compare scalar
  and AVX-512 at actual sizes, scalar tails, exceptional inputs and recurrent-state error before throughput.

  '
acceptance: CPU-KDA-EXP-CENSUS.json contains model, graph, cpu_isa, kda_count, self_time, upper_bound. Both decode and prefill
  have a confirmed upper bound or an identified missing witness.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/cpu-decode-roofline-program.md: 78e49998dc4a253717b5f591ab72856d295c1c91
    epyc-root:research/deep-dives/intake-nov26-kernels/33077.md: d71245767f46d1451b4f68777642d0d237570fcc
---
