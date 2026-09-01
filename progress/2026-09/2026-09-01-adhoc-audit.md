# 2026-09-01 — ad-hoc audit session (workspace-62), day 2

Continuation of the 2026-08-31 session (audit → INF-68 → OP-33 (renumbered OP-33 at the 2026-09-01 reconciliation)/OP-8 executions; see
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
  OP-33/OP-8 reclaim within hours of it landing.
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

## Task 8 — qwen38-mtp community submission: measured, and submitted as PR #70

Operator-approved public submission to `github.com/sudoingX/qwen38-mtp` (Qwen3.8-27B MTP results
collection). Three MI210 seams granted and released by the AutoKernel session (device owner);
attested binary `/mnt/raid0/llm/tmp/build-champ-tip-clean/bin`, champion tip `9e18beb0`, whose
`libggml-hip.so` code-section digest is byte-equal to guard-verified `anchor-gen-011`.

**Measured** (Qwen3.8-27B Q8_0 unsloth, f16 KV, `-c 32768`, `-np 1`, unmodified `probe.py` @
`431bf8a821`, 3 prompts x 3 runs, thinking off):

| arm | P1 py | P2 prose | P3 bash | median | mean | acceptance | mean len | VRAM |
|---|---|---|---|---|---|---|---|---|
| baseline | 30.4 | 30.5 | 30.3 | **30.4** | 30.4 | — | — | 28.65 GiB |
| MTP n-max 2 | 42.0 | 32.0 | 40.3 | 40.3 | 37.5 | 0.880 | 2.76 | — |
| MTP n-max 8 | 74.6 | 30.5 | 46.8 | **46.8** (+54.0%) | 52.0 | 0.375 | 3.99 | 30.90 GiB |
| DFlash n-max 8 | 93.4 | 39.6 | 61.1 | **61.1** (2.0x) | 64.6 | 0.537 | 4.75 | 33.92 GiB |

Findings, all novel against that repo's 63-row corpus:
- **n-max 8 is the optimum here (+16% over n-max 2)** — against the table's trend, where n-max 8 is
  recorded as a loser everywhere it was swept (5090 NVFP4 "confirmed worst", b10680 "turns down",
  A5000 declined it on spread). Extends their rule 1 tiering onto datacenter silicon.
- **Prompt dependence is extreme and grows with depth**: at n8, python +145%, bash +54%,
  **prose +0% (30.5 vs a 30.5 baseline)**. A single-prompt headline would mislead either way.
- Acceptance as vanity metric confirmed: 0.880 → 0.375 while mean accepted length 2.76 → 3.99 and
  throughput rises. Deep drafting wins on tokens-per-verify, not on being more often right.

**Submitted**: PR #70 — one table row (30.4 → 46.8, n-max 8, 0.375), a footnote carrying the
n-max 2 arm, the full per-run spread (P3 `[58.2, 46.8, 45.9]`, one ~25% excursion, disclosed
because the A5000 declined n-max 8 on spread grounds), non-stock-fork disclosure per their rule 6,
the gfx90a `-funsafe-math-optimizations` greedy-argmax warning, and a new `sweeps/instinct-cdna.md`.
DFlash included as a labelled non-MTP path with AK's required parity caveat verbatim. No internal
figures cited.

## Task 9 — two false alarms of mine, both corrected same-day

1. **"DFlash2 is 3.1x slower than baseline / the config is broken."** WRONG. I copied the flags off
   AK's running server and assumed they were the DFlash arm; they were the `draft-simple` CONTROL
   arm, deliberately wrong-on-purpose. 9.7 t/s at acceptance 0.126 is that control behaving as
   designed. The load warnings I cited as a fault signature appear identically in healthy 70 t/s
   runs. **Lesson: argv tells you WHAT is running, never WHY** — one question to the owner would
   have cost a message and saved an investigation. (AK accepted the warnings-are-a-trap point as a
   real finding and filed a champion-lineage cleanup to demote/annotate them.)
2. Correct arm is `--spec-type draft-dflash` (not `dflash2`, which was the arm's internal name).

## Task 10 — six hypotheses relayed to the AutoKernel planner

Sent (msg `2fa07724`), each with a falsifier, framed as planner input under AK's own admission flow:
**H1** the loop's objective may measure a shape production never runs (champion +16.180% on
llama-bench tg, which is source-proven unable to express `ne11>1`; measured transfer to the DFlash
serving cell was **+0.57%**) · **H2** the seed space may inherit the same blind spot · **H3**
serving config may move acceptance more than kernels move throughput (0.537 vs 0.371 on identical
prompts/model/drafter) · **H4** per-request decay in one config (`[67.3, 52.6, 46.7]` monotonic)
would make request index a hidden variable in every multi-request benchmark · **H5** the ~13%
server-vs-client instrument gap may be a calibratable constant · **H6** kernel ranking may be
prompt-class dependent.

Provenance stated in the message: H1 rests on AK's figures and note, not on anything I measured;
H4 rests on three runs.

## Wrap-up notes (task 8-10 cycle)

- Checkbox flips: 0 in `handoffs/` — correct. This cycle's work is an external submission plus
  cross-session relays; no handoff-tracked task was completed. The one handoff-adjacent item
  (Layer 1 llama-cli patch) already carries its own `- [ ]` from the earlier commit.
- Derived-actionables dispositions: **6 filed with AK** (the hypotheses — AK's planner owns them,
  it confirmed filing H3/H4-class items as a one-factor sweep and the instrument gap into INF-22
  P3-4); **2 explicit declines** — (a) I did NOT add my numbers to INF-61's surface
  (`gpu-candidates-surface-qwen38-update.md`) because the GPU/AK lane owns that comparison and has
  already filed the instrument gap itself; writing into it would duplicate a record its owner
  maintains. (b) I did NOT open an operator-queue row for H1 despite its significance — it is a
  hypothesis for AK to test, not a decision only the operator can make; if it survives its
  falsifier it becomes one, and AK owns raising it then.
- Device hygiene: three seams, all released on time; every `llama-server` killed by captured PID
  and verified dead; all four regions free at each release. Contrast with yesterday's 11h runaway —
  the difference was killing by captured PID inside the harness rather than trusting a flag.

## Task 11 — OP-11 resolved: the push backlog is cleared (merge `21cefca5` on origin/main)

Operator directive: "let's resolve OP-11 so the push backlog clears."

**The blocker's premise was stale, and that is the finding.** OP-11 (open since 2026-08-16) read
*"90 ahead / 111 behind, 103 files changed on BOTH sides, so `-s ours` would silently revert
origin's half; real three-way merge in flight; D9-ack needed."* Measured at resolution time:
**42 ahead / 30 behind, FOUR both-sides files**, merge-base `e56c1d68` (2026-08-30) — the
2026-08-30 reconciliation had already collapsed the divergence. The option its owning handoff
rejected as ~78 hand-resolved conflicts cost **two**, both disjoint appends. No `-s ours`, no
force-push, nothing discarded. I had re-reported this blocker verbatim in four consecutive
wrap-ups without re-measuring it.

Conflicts and resolutions (all "keep both", never "pick a side"):

| file | conflict | resolution |
|---|---|---|
| `wiki/hardware-optimization.md` | both lanes appended compiled updates | kept all five (3 origin, 2 mine) |
| `handoffs/active/master-handoff-index.md` | **duplicate OP-ID collision** | origin's OP-30/31 keep their numbers (published first); mine renumbered **OP-32** (uniform IQ4_XS) / **OP-33** (disk reclaim), references updated in 3 progress files + the owning handoff |
| same file, generated block | both regenerated | took origin's, regenerated after the merge |
| `wiki/source_manifest.json` | my regen was SMALLER | took origin's — a generated file must never regress on a merge |

**Two deliberate deletions preserved against the merge's instinct to resurrect them**: OP-8 (mine —
GLM-5.2 ruled KILL, artifact deleted, handoff completed) and OP-28 (origin's — the autokernel lane
resolved its own bundle). A naive "union" resolution would have re-opened both.

Verification before commit: origin-only and mine-only markers both present post-merge; no tracked
file regressed in size vs `origin/main`; `--diff-filter=U` empty.

**Push mechanics — two refusals, both correct, neither bypassed.** (1) The pre-push guard wants the
**push** lock, which is a *different lease* from the wrap-up lease I held. (2) Holding it was still
not enough: the guard requires the pusher to *prove* ownership, since a lock file alone does not
show the pushing process belongs to the holder — resolved with `AGENT_ID=adhoc-audit`, the
sanctioned path, NOT `EPYC_ALLOW_UNSERIALIZED_PUSH`.

**Pushed from the isolated merge worktree, deliberately.** The shared clone still holds the
fused-decoder session's uncommitted work; advancing its branch pointer under them would have made
their next commit revert origin's changes. Their tree was never touched. Local `main` is now simply
behind and fast-forwards whenever each session chooses.

Result: **everything from both lanes is on `origin/main`** — two days of audit, INF-68, the
OP-31/OP-8 executions, the llama-cli fix and guard, the wiki compiles, and the MI210 submission
record. The only local-only commit is the fused-decoder session's `7bdd6376`, theirs to push.

- [x] OP-11 resolved and the row removed from the operator queue ✅ 2026-09-01
- [ ] Fleet follow-up: local `main` in the shared clone is 31 behind `origin/main` and holds one
      unpushed peer commit — each session fast-forwards at its own boundary; not mine to force.
