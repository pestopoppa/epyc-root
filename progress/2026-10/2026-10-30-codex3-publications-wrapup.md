# Codex3 approved publication wrap-up — 2026-10-30

## Work completed

| Track | Durable change | Evidence and current limit |
|---|---|---|
| EVL-34 r11 budget-v6 | Filed the reviewed r11 READY publication and completed the specific r10 budget-repair follow-up under the existing EVL-34 task. | Actual keeper QUEUED at 20:55:01Z; validator 0 refusals / 0 warnings. Entry-only R7 smoke: 79.6326 s, 38,440,255,488-byte peak sampled RSS, both arms produced real responses and usage, GPU residency witnessed, writer completed and server/supervisor drained (PID 926192 absent). The 20-cell pilot has not run and verdict is pending. Control33 semantics remain partial/unknown; r10 eight unknowns and controls 28–32 were not regraded. One checkbox ticked with [no-belief: launch repair/qualification only; pilot verdict pending].
| CS-8.STT2 transcribe.cpp CPU arm | Filed the owner-reviewed READY publication checkpoint and retained source/build/linkage/smoke receipt. | Source db678a031cf4c524bcab2c45a0dc6a7813106e4a, ggml 0.26.0; isolated CPU build and linkage verified. One real-clip smoke only; the 40-clip comparison, three other runners and full CS-8.STT2 remain open. No parent checkbox tick.
| CS-22.A1 F32 parity subtest | Published owned READY manifest and row in canonical compute-flags ready/; filed exact manifest/row pins, plan and transfer note. | 20 frozen clips × contexts 0/3/6/13 × 2 modes = 80 planned comparisons; full parity run not executed. Two-leg smoke 12.822 s, peak RSS 2,762,678,272 bytes. Runtime accepts 0/3/6/13 and rejects 1/2, while original task lists 0/1/3/6/13; discrepancy retained. A1 acceptance and T1 remain open. No parent checkbox tick.
| EVL-34 READY-row metadata audit | Filed the reviewed 12-row audit and compact isolated-validator fixture receipt. | Own rows were corrected only for raw_globs and narrow keep_globs; source validator SHA-256 7ddfaa6b65de45a37d5f90bb9a6d186a071756977fac91d71aced55c053cd30e. Isolated armed-fixture validation reported 0 refusals; no shared grants were fabricated.

## Wrap-up gates

- Root handoffs updated: rao-redel-substrate-spike.md and conversation-stack.md; no scientific parent task was marked complete.
- No index ownership/row change, pruning, handoff compaction, wiki sweep, source/adapter edit, kernel change or scratch cleanup was performed. Reviewed scratch packets remain KEEP-marked.
- External READY publication is the canonical CS-22.A1 row/manifest under /mnt/raid0/llm/tmp/compute-flags/ready/; the row remains BACKLOG, not booked or armed.
- README freshness check exited 0 with no warnings; belief ledger sync check was FRESH at intake-2521 (0 lag). Under the wrap-up lease, index regen completed and index_state.py --check exited 0 (0 problems; it printed existing Scratch warnings for qwen-chat-template-evaluation.md and 123 handoffs without Scratch fields).
- `git diff --check` passed. Lane commit, source push, promotion, and final agent-log closure follow below.
