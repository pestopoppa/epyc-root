# KPF-30 native row position fix — 2026-11-04

The observer at integrated candidate `8952a0f693fb923918157eb25117641b74766230`
emits `row,seq,n_tokens,...`; the phase parser requires `row,seq,pos,n_tokens,...`
and joins on `(seq,pos)`. Consequently even correctly bracketed native output is
rejected as a malformed mask row. The existing synthetic parser fixtures already
include `pos`, concealing this producer/consumer mismatch.

`native-row-position.patch` adds `pos=%d` and its matching
`int(ubatch->pos[i])` argument to the native log statement. This follows the
same token position used by the mask calculation. Counts, mask computation,
allocation and the default-off observer switch are untouched. The patch is an
**unapplied review artifact**; no source tree or shared coordination code changed.

`source-identity.json` binds the inspected source and its digest.
`native-log-statement.inc` preserves the exact original statement for the tests.
Before authoring the patch, upstream GitNexus impact on `set_input_kq_mask`
returned LOW with zero impacted symbols on indexed P3 `c72ec82`; the saved
`impact-p3-reference.json` repeats that result. This is reference evidence only:
P3 lacks the observer, and it does **not** establish source-bound clearance for
the integrated candidate. The current root worktree reports unindexed. Obtain
candidate-bound impact evidence before applying the patch.

Validation (all model-free):

* `git -C /mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104/source apply --check <absolute-patch-path>` passed; no patch was applied.
* `python3 docs/reports/kv-cache/kpf30-phase-fix-20261104/test_native_position.py`: 4 passed. The extracted native statement is compiled in an isolated C++17 format harness with `-Wformat=2 -Werror`; old output reproduces rejection, patched output joins decode/verify rows of one sequence at distinct nonsequential positions, wrong positions fail closed, and unbracketed rows still fail.
* `PYTHONPATH=scripts/vidya python3 -m unittest discover -s scripts/vidya/adapters/tests -p test_kpf30_phase_capture.py`: 5 passed.

The format harness is not a linked kernel build or evidence of native token
shapes. No inference, runtime qualification, deployment, publishing or threshold
decision occurred. This patch does not supply `KPF30_BEGIN/PHASE/END`, infer
phases from batch size, establish multisequence token semantics, or close the
runner canary/two-window gate. Those prerequisites remain with the owning runner.
