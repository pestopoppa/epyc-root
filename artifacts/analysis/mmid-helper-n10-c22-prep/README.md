# MMID-HELPER-N10 C22 source preparation

Status: **partial; not ready to run**. `c22-n10.patch` adapts the existing
feature-and-test commit `dd20d4b020c11dba4f44623d887267053cb1ce41` from C21
onto ratified C22 `b1e1864cb6e9f8a012b0be422e6c72ab477ded62`. The original
helper hunk applied unchanged; the opt-in test block was moved to the current
MUL_MAT_ID case section. The patch was checked against files extracted from
that exact commit. It is not a fork commit, build, or correctness result.
The upstream origin is f1793c1c4. The opt-in `mmid_n10` cases cover 16 and
512 experts, 10 used, 16/33/64/129/512/2048 tokens, Q8_0 and IQ4_XS, plus
F16 broadcast. No handoff box is changed.

The existing `ak-mmid-n10-gate-gpu-20261124-r2` result reports KEEP+RL_DROP
against C21 and N10 commit `233dbc3c1` (which includes the readlane arm):
helper ratios 0.3646–0.3650 and Q38FN pp ratios 1.0258–1.0602 across
three pairs; its N10 ROCm MUL_MAT_ID slice reports 883 passed, zero failed.
It does not establish C22 results. The existing `ak-mmid-n10-kld-gpu-20261125`
result is FAIL_KLD under its fixed 0.003 rule; A3B N10/A-A KLD is
0.003215/0.004953 and Q38FN is 0.031323/0.032079. Do not relabel that
result: the handoff explicitly says a relative KLD gate is pending.

Remaining: create the feature commit on a fresh C22 fork branch, CPU and HIP
build/proof, and composite ROCm slice; prepare the current gate packet and
rehearse it with the deployed generator without publishing. The user prohibits
builds and touching `/mnt/raid0/llm/tmp/compute-flags`, where the deployed
rowflow generator and publisher reside, as well as work in another worktree.
These constraints prevent completing the fork commit and the required deployed
generator rehearsal in this lane. An operator must provide an authorized
location/copy of the deployed tools and a permitted fork worktree (or relax the
respective restrictions); compute-dependent verification must be scheduled
separately. No inference, GPU tools, or benchmarks were run in this preparation.
