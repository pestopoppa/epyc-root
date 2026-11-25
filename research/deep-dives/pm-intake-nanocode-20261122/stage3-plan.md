# Stage-3 plan — nanocode intake (pm-intake-nanocode-20261122) — APPROVED 2026-11-22 (operator "Approve all")

Entries: intake-2789 nanocode, intake-2790 harnesslang, intake-2791 nanoeval (all dive-verified, PARTIAL).
Subagents: 4 sonnet/medium (3 Stage-2 dives, 1 Stage-2b wave). Waves: Stage 2 + one Stage-2b wave.
Compute: none in any packet below except where marked "inference row", and those need their own booking.

## Packets

P1 — Tool retry-safety class + unknown outcome on crash (owner: harness-program.md, CODEMODE-REL area)
- Decision: should a REPL/taskflow restart re-run side-effecting tools? Today: no retry-safety axis
  (orchestrator src/registry/tool_registry.py:88-149 has SideEffect for approval only; session_log.py has
  no open-call recovery) [intake-2790 dive].
- Deliverable: effect class {none, idempotent, external} on every registered tool (derived from SideEffect,
  undeclared = external); write-ahead call record before an external dispatch; on resume an open external
  call returns an explicit unknown result to the model instead of being re-run.
- Rigor (deterministic infra; six-control floor replaced by): unit tests plus a seeded crash-injection test
  with planted mutations (redispatch-after-recovery, flush-after-dispatch) that must each be caught;
  scripted model, no inference. Benefit: correctness of resumed loops (no double side effects).
- Stop rule: the planted mutations are caught and the existing REPL suite passes, so the box closes.
  Trigger for broader work (cell-level replay divergence check, harnesslang's same_step): fires only if
  P1 lands and code-mode cells become resumable. Until then it is monitor prose.

P2 — Code-mode cell guards borrowed from nanocode (owner: harness-program.md CODEMODE-REL)
- Gap: our code mode has no per-tool call cap and no explicit truncation policy for oversized cell output
  [intake-2789 dive; verify in the orchestrator before coding].
- Deliverable, flag-gated and on the autopilot surface (operator rule 2026-11-18):
  (a) a per-tool call cap per cell with a structured non-retryable `call_limit` error ("batch or split");
  (b) head+tail middle truncation of cell output, with a marker giving the original token count.
- Rigor: unit tests (cheap). The quality effect is measured inside P3's arm, not separately.

P3 — Compact vs full code-mode prompt, plus a direct-vs-code-mode hypothesis check (owner: harness-program.md CM-4/CM-5)
- Decision: does a compact tool-catalog prompt (nanocode keeps compact and full exec descriptions) cut
  prompt tokens at equal success on local models?
- Zero-inference step first: measure prompt tokens, compact vs current, on the CODEMODE-AB task set.
- Inference row (needs a separate booking, not run by intake): paired A/B, C3 vs C3+compact, on the
  existing CODEMODE-AB-V2 tasks, 35B and 27B, reusing that harness.
- Six controls: same task set, paired seeds, same model/kernel build, flag-only arm difference, primary
  metric = success at prompt tokens, predeclared stop.
- Sufficiency: reuse 30 pairs per arm. Stop-on-answer is a token reduction of 25% or more with a success
  delta inside the pair noise. Stop-on-futility is a token reduction under 10%.
- Context only: nanocode-ts DECISIONS.md L72 is a self-reported, unpublished claim (no n) that direct tools
  beat Code Mode in TB2.1. It is consistent with our tentative "direct calls win". It is not citable, so no
  task is created from it.
  Correction 2026-11-25 (status audit): the sentence above is wrong. CODEMODE-AB-V2 closed 2026-11-19 with code mode WINNING (27B 42/42 vs 0.62; 35B 9/10 vs 3/10, p 0.031; harness-program.md CODEMODE-AB-V2), so our "direct calls win" was not the standing result and the nanocode claim is not consistent with it. Outcome (no task created) is unchanged.

P4 — Eval outcome typing, version digests and regression verdict from nanoeval (owner: eval-tower-program.md)
- Gap: whether our scorers separate infra errors from failures, and pin suite versions, is to be confirmed
  by grep before coding (memory: "classify eval failures by reason").
- Deliverable:
  (a) a typed `errored` outcome with failure classes, excluded from pass-rate denominators and counted per
      class;
  (b) a SHA-256 suite digest stamped on every run record;
  (c) an optional stratified exact one-sided regression test plus a per-task lost/gained call (Fisher) as a
      DESCRIPTIVE report. Formal-gate use waits on OP-ABSEQ/OP-PQP/OP-ALPHAWIN, so P4 is futility-only.
- Rigor: deterministic. Replay over existing run records; the digest must be stable across two reads; the
  verdict is checked against hand-computed fixtures.

P5 — Terminal-Bench 2.1 unsound-task list (owner: benchmark-suites.md, intake-726 Harbor line)
- Deliverable: a skip/flag list with provenance. Confirmed so far: build-cython-ext (TB2.1 issue 240),
  qemu-startup and qemu-alpine-ssh (issue 233), protein-assembly (PR 247). The remaining nanoeval entries
  are mcmc-sampling-stan, torch-tensor-parallelism and crack-7z-hash, carried as nanoeval-reported and
  unverified upstream. Report a sound-subset rate beside the full rate.
- An oracle pass on our setup is NOT intake work. It becomes a CPU row when TB2.1 is next run.

M1 (monitor) — nanocode as an external harness arm against llama-server.
- The plumbing exists: NANOCODE_ANTHROPIC_BASE_URL / OPENAI_BASE_URL, and nanocode-ts runs in Node.
- The OpenAI path is Responses-only. Messages-API support in v10 llama-server is unverified.
- Next step when it triggers: a read-only check of whether llama-server v10 serves /v1/messages.
- Trigger: an operator wants a third-party harness comparison on CODEMODE-AB. This is a build cost, not a
  decline.

K1 (knowledge-only) — harnesslang compiler/prover/targets, nanoeval microVM runners, Hands, and the
cloud demos. They have no consumer on our single-host stack. The patterns are taken in P1 and P4.
Reopen if the orchestrator gains a multi-host or serverless deployment.

## Proposed handoff edits (Stage 4 only, after approval)
harness-program.md, under the CODEMODE-REL section:
- [ ] **CODEMODE-EFFECT — tool retry-safety class and unknown outcome on resume (intake-2790).** Add effect class {none, idempotent, external} to ToolRegistry (from SideEffect; undeclared = external), a write-ahead call record before external dispatch, and an explicit unknown result for an open external call on resume; seeded crash-injection test with planted redispatch/flush-order mutations, scripted model, no inference. Done when every planted mutation is caught and the REPL suite passes.
- [ ] **CODEMODE-GUARDS — per-tool call cap and middle truncation in code mode (intake-2789).** Flag-gated, on the autopilot surface: per-cell per-tool cap with a structured non-retryable `call_limit` error, and head+tail truncation of oversized cell output with an original-token-count marker; unit tests.
- [ ] **CM-COMPACT — compact code-mode prompt A/B (intake-2789).** Step 1 (no inference): prompt tokens compact vs current on the CODEMODE-AB tasks. Step 2 (booked row): paired C3 vs C3+compact, 35B and 27B, 30 pairs per arm reused from CODEMODE-AB-V2; stop on a token cut of 25% or more at equal success, futility below 10%.
eval-tower-program.md:
- [ ] **EV-TYPED-OUTCOME — errored outcome class, suite digest and descriptive stratified regression report (intake-2791).** Errored attempts are excluded from pass rates and counted by class; a SHA-256 suite digest goes on each run record; a stratified exact one-sided test plus a per-task Fisher lost/gained call, reported descriptively only (futility-only until OP-ABSEQ/OP-PQP/OP-ALPHAWIN).
benchmark-suites.md, at the intake-726 entry:
- [ ] **TB21-UNSOUND — Terminal-Bench 2.1 unsound-task list with provenance (intake-2791).** Flag build-cython-ext (TB2.1 #240), qemu-startup and qemu-alpine-ssh (#233), and protein-assembly (PR #247); carry mcmc-sampling-stan, torch-tensor-parallelism and crack-7z-hash as nanoeval-reported; report a sound-subset rate beside the full rate.

Index rows: none. All tasks land in handoffs that already have a row, and no new stubs are created.
Intake entries at Stage 4:
- intake-2789 and intake-2790: handoffs_updated [harness-program.md], integration_disposition integrated.
- intake-2791: handoffs_updated [eval-tower-program.md, benchmark-suites.md], integrated.
Steering ledger: operator 2026-11-22 instructions (accept all dives/waves; no compute; never dismiss;
prepare, don't apply; STOP after Stage 3). All are context-only.
