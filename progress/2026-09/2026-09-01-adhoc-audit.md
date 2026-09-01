# 2026-09-01 — ad-hoc audit session (workspace-62), day 2

Continuation of the 2026-08-31 session (audit → INF-68 → OP-31/OP-8 executions; see
`../2026-08/2026-08-31-inf68-baseline-control.md` and `../2026-08/2026-08-31-disk-reclaim-menu.md`).

## Task 5 — fused-decoder overnight review + triage relay

Reviewed the INF-67 session's overnight record (worktree `470730838..4285c7913`, progress
`e37ea07f`): the full-attn rewrite landed **bit-exact via the graph's own flash kernel** (the
audit's recommendation executed — layers 0-6 bit-exact, logit diff O(10)→0.684), two more
scratch overflows fixed, then a disciplined 7-commit crash triage at the fused head — conclusion:
real, optimization-independent corruption (-O3/-O1/-O0 all crash, "ASAN clean"), lead = the
`getenv("GGML_FUSED_DECODE_TRACE")` string in the crashing call's first-arg register.

Relay drafted for the operator (delivered in-chat, operator relays): (1) the "ASAN clean" is
vacuous for ggml-side buffers — `build-asan` has `GGML_SANITIZE_ADDRESS=OFF`, zero `__asan`
symbols in `libggml-cpu.so` (audit-verified); rebuild sanitized or valgrind. (2) One-run
discriminator: strip (not env-disable) the `e3ddf1583` TRACE instrumentation — crash gone =
instrumentation bug; persists = real corruption. Suspect pool: exact-fit scratch, the
`ggml_compute_params` mirror, the `t_logits` previous-graph write. (3) Boundary-length
validation matrix for the logit gate (from intake-1295#record; the program's defect record is
~all boundary conditions).

## Task 6 — research intake Stage 1: M4 Prefill Engine (intake-1295/1296)

Operator-approved wave; committed `b22fc595`, validator exit 0. Verdict `adopt_patterns`,
credibility 1 (kernel-isolated 3.4-3.7x vs an UNSPECIFIED baseline — confirmed absent from both
primary sources; 5-commit repo, no weights workflow). Transferable: boundary-length correctness
matrix (methodology), masked-tile SKIP vs our DSA-DENSE-MASK, dequant-into-consumer fusion,
INF-67 fusion-thesis corroboration. Expansion 0; contradiction pass clean (bounded, provisional).
Dive recommendation: DECLINE (value extracted at Stage 1; headline unverifiable without Apple
hardware) — operator may overrule by naming the intakes. Peer intake wave's session state
(wave2-stage3-gate, 08-25) preserved under a namespaced key; the JSON reflowed on rewrite
(content verified preserved) — noted.

## Task 7 — AK planner-hypothesis relay (operator-directed)

Distilled 5 hypotheses to the `autokernel-promotion-teardown` session via direct message
(msg `8e00317e…`): H1 causal tile-skip (DSA-DENSE-MASK contrast), H2 dequant-into-consumer
(instrument-first), H3 register glue fusion (with the honest CPU 0-for-3 prior), H4 KV-at-point-
of-use verification, H5 boundary-matrix screen upgrade. All labeled stage1-unverified/planner-
input, gated by AK's own admission flow. No reply requested; uptake visible in its own record.

## Wrap-up notes (2026-09-01)

- Checkbox flips this cycle: 0 — correct (intake pre-Stage-4 writes no handoffs; relays are
  operator-mediated). Derived-actionable dispositions: dive-or-decline carried in the Stage-1
  report + session state (no OP queue row — recommendation is decline, nothing dangles);
  boundary-matrix INF-67 task routed via operator relay (a direct write would breach both the
  intake Stage-3 gate and the live session's lane) — explicit decline of direct filing.
- Wiki sweep: 2 new sources, both INF-67 mid-flight crash-triage churn — compile deferred with
  reason, watermark NOT touched (they compile when the hunt settles; their own precedent).
- OP-11 divergence grew overnight (local ahead 30 / behind 25); epyc-root push still blocked.

## INCIDENT (self-inflicted, found + closed 2026-09-01) — runaway llama-cli: 322 GB + an 11 h region lock

While verifying whether the AutoKernel session was running Qwen3.8-27B numbers (operator question),
a `ps` sweep found MY OWN process from the 08-31 INF-68 Paris sanity check still alive:

- `llama-cli` (pid 1294948), started 2026-08-31 20:37:50, **elapsed 11 h 15 m**. Its generation had
  completed correctly hours earlier; the REPL kept writing `"> "` — with `-no-cnv` AND stdin from
  `/dev/null`, so neither guard stops it.
- It wrote **322,428,757,161 bytes (~300 GiB)** to `scratchpad/inf68-paris2.log`, taking the array
  from 480 G free (post-reclaim) down to **191 G** — silently undoing most of the operator-approved
  OP-31/OP-8 reclaim within hours of it landing.
- Its `region-lock run` wrapper (pid 1294923) held **q0-q3 (cpus 0-95, role bench, tag inf68-paris)
  for the whole 11 h**, which would have blocked or skewed any peer's CPU bench in that window.

Closed: SIGTERM to the captured PID → verified dead (`ps -p`) → wrapper exited and **all four
regions verified free** → runaway log deleted → **disk 191 G → 489 G free**. The committed evidence
copy (20 KB head, `data/inf68-uniform-iq4xs-ab-20260831/paris-uniform-greedy.head.log`) is intact,
so no evidence was lost.

**The real defect is mine and it is a repeat.** The footgun was already documented in progress
2026-08-28 ("llama-cli with closed stdin spins a REPL loop writing '> ' forever — always pipe stdin
or use llama-bench"). On 08-31 I hit it, *noticed* it, wrote it into the hygiene notes, trimmed the
log for evidence — and never checked whether the process was still running. Noting a symptom is not
handling it. Memory filed: `llama-cli-repl-must-be-killed`. Standing correction: every `llama-cli`
launch pairs with an explicit kill+verify, and every task boundary includes a `ps` sweep for my own
long-lived leftovers (`ps -o etime` is the tell).

## Layers 1 + 2 — permanent fix for the runaway-llama-cli class (operator-approved)

**Layer 1 — the defect, fixed and verified.** Root cause is NOT `-no-cnv` being ignored:
`ui::read_input()` (`tools/cli/cli-ui.h:166`) discards the EOF signal that `console::readline()`
returns, so `cli_context::run()`'s `while (true)` loop (`cli-context.cpp:489`) cannot distinguish
"stdin closed" from "empty line" — it re-prompts forever, and `< /dev/null` makes every read return
instantly. Both readline backends agree on an exact invariant: **at EOF the line comes back WITHOUT
a trailing newline, while a real empty line always yields `"\n"`** (`readline_simple` clears the
line; `readline_advanced` skips its `line += '\n'` under `end_of_stream`) — so an empty buffer is a
precise EOF signal that cannot misfire on interactive users.

Patch (19 insertions, 3 files touched → `artifacts/operator/llama-cli-eof-fix-20260901.patch`):
`read_input()` gains an optional `bool * out_eof`; the main loop breaks on EOF; the
model-selection loop (`cli-context.cpp:252`, the SAME bug, second instance) returns on EOF.

Verified in a scratch clone at `7cdd7c97b`, exit code as the assertion:

| test | before | after |
|---|---|---|
| `-p ... -n 8 < /dev/null` (the incident command) | **124** (timeout killed a spinning process) | **0**, one `"> "`, `Exiting...` |
| generation still happens | — | ✅ 304.9 t/s prompt / 109.6 t/s gen |
| piped prompt, no `-p` | — | ✅ exit 0, 1 generation |
| **regression: 2 empty lines then a real prompt** | — | ✅ exit 0, prompt processed — empty lines do NOT exit |

- [ ] Land the patch in the champion lineage (routed to the AutoKernel session, which owns it).
      NOT applicable to frozen production v9, so unpatched binaries persist on this host — which is
      why Layer 2 exists. Worth upstreaming: affects any llama-cli run with redirected/closed stdin.

**Layer 2 — PreToolUse hook (protects today, regardless of binary).**
`scripts/hooks/check_llama_cli_guard.sh` + `llama_cli_guard_scan.py`, wired into the
PreToolUse/Bash group. Blocks an *unbounded* `llama-cli` invocation; passes `timeout <secs>
llama-cli`, an `EPYC_LLAMA_CLI_ACK="why"` escape, and — per the C21 lesson — all TEXT mentions
(quoted strings and heredocs are stripped, so this record, `ls .../llama-cli` and `grep llama-cli`
are unaffected). Fails OPEN if the scanner is missing: this guards a resource burn, not a
correctness violation. Mutation-tested 14/14 scanner cases + 3 end-to-end hook cases, including
wrapper chains (`taskset`/`numactl`) and `region-lock run ... -- ...` handoffs.

Layer 3 (disk-free alarm — `alarm_config.yaml` has no disk check today) NOT implemented: outside
the two layers approved. Filed here so it is a decision, not a silent drop.
