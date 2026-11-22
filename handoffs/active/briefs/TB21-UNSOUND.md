---
schema: epyc.brief.v1
id: TB21-UNSOUND
box_text_sha: t:62b1a325f658068a
author: intake
written: '2026-11-22'
accepted: pending
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Write a Terminal-Bench 2.1 unsound-task list (task, cause, upstream link, status) as a data file beside the Harbor/TB
  tooling: build-cython-ext (harbor-framework/terminal-bench-2-1 issue 240), qemu-startup and qemu-alpine-ssh (issue 233),
  protein-assembly (PR 247) confirmed upstream; mcmc-sampling-stan, torch-tensor-parallelism, crack-7z-hash marked nanoeval-reported
  (nanoeval c2a11dd unsound.json). Make the TB summary report a sound-subset pass rate beside the full rate. The oracle pass
  on our host is a CPU row at the next TB2.1 run.

  '
acceptance: test -s /workspace/repos/epyc-inference-research/benchmarks/terminal_bench/tb21_unsound.json
non_goals:
- no TB2.1 run by intake
tier: terra
grounded:
  at: '2026-11-22'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: 6581facd03c3dd8915a19f84d18f9cdc7f56662c
---
