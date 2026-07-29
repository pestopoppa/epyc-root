# POST-REBOOT SESSION BRIEF

Read this first if you are a freshly-spawned session on a host that just rebooted and you have
zero context. It was commissioned before the reboot and is written to be self-contained — but it
is a pointer document, not a restatement of the underlying handoffs. Go read those when a section
tells you to.

Authoritative sources, cited rather than duplicated below:
- `handoffs/active/gpu-serving-tie-in-program.md` — the GPU-lane program spine (Phase 0-3).
- `handoffs/active/batched-decode-measurement.md` — the E5 NUMA×batch sweep (§ "E5 — NUMA×batch
  interaction sweep" and its W0-W4 sub-bullets).
- `handoffs/active/session-bus-thin-dispatcher.md` — bus/dispatcher defect ledger; see the
  `POST-REBOOT HANDOVER — claude-gpu-lane` block (~line 670) and the C-series items.
- `progress/2026-07/2026-07-29.md` — claude-main's handover, "Deferred / open" section (OD-A,
  OD-D, OD-E).

Nothing is mid-write. **Every session was closed by the operator before the reboot** (2026-07-29
~13:30Z): `codex`, `claude-gpu-lane`, `fable-auditor`, `codex-bus-tests`, `claude-main` — all
wrapped, committed and pushed first, then closed; `coordinator-agent` last. So expect an **empty
`agent` tmux session** and zero live mains on arrival. That is the intended shape, not a fault, and
it means the spawn plan you present is the whole fleet rather than a gap-fill.

**Branch state at close — five branches remain unmerged and are yours to reconcile.** A
wrap-up promotion sweep on 2026-07-29 merged every branch that merged cleanly and carried real
content. What is left is *only* the conflicting set, deliberately not auto-resolved:

| Repo | Branch | Why it did not land |
|---|---|---|
| epyc-root | `codex-wrapup-precompact-20260729` | doc conflict in `master-handoff-index.md` + `progress/2026-07/2026-07-29.md` |
| epyc-orchestrator | `codex/e8-consolidated-wrapper-20260728` (9 commits) | code conflict |
| epyc-orchestrator | `codex/e8-abort-terminal-seals-20260729` (3) | code conflict |
| epyc-orchestrator | `codex/e8-typed-provenance-20260729` | code conflict |
| epyc-orchestrator | `e8-v5-runtime-root-20260727` (7) | code conflict |
| epyc-orchestrator | `tierc-10d-crash-window-durability` | code conflict |

All five are E8-harness or E8-adjacent, i.e. the same repair chain codex left mid-sequence — so
reconcile them **in codex's stated order** (scorer isolation → replay successor → dual binding),
not by branch date. Three epyc-root `codex/e8-*` ratifier branches merged cleanly but produced a
**zero-byte diff** (duplicate commits already on main) and were therefore *not* pushed — treat them
as already landed and delete rather than re-merge. `spec-dec-mtp-refresh-2026-06-22` is fully
merged (0 unique, 307 behind); it is a stale label, not pending work. Five orchestrator
`dependabot/uv/*` branches are open and untouched by this sweep.

**All three repos were at `0` unpushed at close.** `epyc-root` main tip `b998b0b5` (plus the
operator-signed `MEASUREMENT.md` amendment `e6b84496`), `epyc-orchestrator` main `f7a02d94`,
`epyc-inference-research` untouched.

---

## 1. Bringup — do this before anything else

**Nothing survives a reboot automatically. In this order:**

1. **`tmux new-session -d -s agent`** — after reboot, nothing creates the `agent` tmux session,
   and `cmd_spawn` in `tmux_adapter.py` fails closed without it (bus defect **C20**,
   `handoffs/active/session-bus-thin-dispatcher.md` ~line 1096). This is **not** a defect when you
   hit the refusal — it is correct fail-closed behavior on a missing session — and it is **not
   optional**: nothing spawns until this command has run. `tmux.allow_session_creation: false`
   means the adapter will never create the session itself; every main is a window in this one
   session, an explicit 2026-07-27 operator requirement.
2. **Restart the coordinator-daemon.** It is a process, not persisted state — it was at epoch 9
   pre-reboot and does not resume itself.
3. Expect every heartbeat to read stale and no window to be live immediately after restart, so
   routed bus messages to not-yet-restarted mains will emit "LOOKS DEAD" advisories. That is bus
   defect **C18**'s warning working as designed (deduped per message/recipient, so it cannot
   flood) — not a fault. It quiets as mains come back up.
4. **Do not "fix" an unreadable tmux session by treating it as zero live mains.** That is the
   **C14 polarity error** (`handoffs/active/session-bus-thin-dispatcher.md` line 907 and the
   C14/C18 polarity note at line 710): a roster row whose window cannot be matched must NOT be
   read as "not running" — doing so hands out occupied slots. Derive liveness from what is
   observable; never assume absence from a field nobody is maintaining.

**Also verify, in the same bringup pass:**
- `scripts/session/verify_llama_cpp.sh` — confirms the production kernel branch is still
  `production-consolidated-v8` and untouched.
- `region-lock status` — confirm all regions read free (nothing should still be held from
  pre-reboot claims; q3 was held by `bench-e8-quality` pre-reboot per
  `gpu-serving-tie-in-program.md` P2-5c gate G1 — that hold does not survive the reboot, but
  verify rather than assume).
- Serving stack is up (`orchestrator_stack.py status` or equivalent) and matches the intended
  lineup.
- AutoPilot state — it was DOWN pre-reboot (no process; last journal activity
  `2026-07-27T08:23:07Z`), resume gated on the E8 signature per P1-3 below. Check current state,
  don't assume it auto-resumed.
- **Confirm uptime has freshly reset.** The P-BENCH host-health tier is uptime-gated
  (≤1-week = decision-grade eligible); pre-reboot uptime was multi-day and had lapsed the
  decision-grade window (`gpu-serving-tie-in-program.md` P2-5c gate G2, lapsing
  ~2026-07-31). The reboot is what reopens this window — verify it actually did (`uptime`) before
  treating any decision-grade run as clear to fire.

---

## 2. The work queued for this session, with gating stated

Do not run anything below out of order relative to its stated gate.

### E5 W1-W4 (NUMA×batch sweep) — `handoffs/active/batched-decode-measurement.md`
- **W0 is complete** (69/69 cells, all four model groups; see the "E5 W0 — EXECUTED COMPLETE"
  entry). W1-W4 were `BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT` — that block is now lifted by this
  reboot.
- **W2 has a hard precondition: run its focused post-fix capture smoke FIRST**, before any
  decision-grade W2 (Gemma) sweep. Reason: the historic W0 Gemma capture had 430/430 parse
  failures with **no raw SSE ledger** — those are unrecoverable, not re-scoreable. The smoke must
  persist `reasoning_text` separately, require nonempty answer-text deltas when tokens were
  generated, and prove the offline scorer can see scoreable answer text. It must pass before the
  decision-grade W2 run, and the published artifact's W2 section (below) stays quality-invalid
  until it does.
- **R1-R4 (the summarizer reads that turn W1-W4 into decisions) are withheld until clean
  decision-grade Stage-B cells exist.** Do not run them early against partial or scout data.
- This is P1-2 in the GPU program's Phase 1 (`gpu-serving-tie-in-program.md`): "fresh-uptime,
  quiet-window per protocol, no deadline — the reboot resets the window."

### E8 quality baseline — codex's handover, and the critical path

**Everything downstream is parked behind this.** P0-1 (the E8 baseline signature) gates AutoPilot
resume (P1-3), which gates the P2-5f duty-cycle measurement, which gates the shed-batch decision
rule. codex owned it and closed with the tail unfinished. Its verbatim handover, in its stated
order — **do not reorder these three**:

1. **Integrate scorer isolation first.**
2. **Replay the successor second.**
3. **Fix the historical-receipt / runtime-helper dual binding**, and only then rerun the audit.

State at close: 279 rows clean, sidecar
`bd89f9e4d7e0a114518a7a0a729b5ea6322ea21e02728f9fc6795db40992a424`. **Incomplete** — no
deterministic completion, no finalizer inference, no baseline application, and no publication
occurred. Race rows 97 / 203 / 279 remain retained for race-only retry and must never be silently
promoted to clean rows. Failed evidence is immutable; nothing was applied.

Before rerunning anything, read `fable-auditor`'s static contract audit findings in
`coordination/session-bus/outbox/fable-auditor.jsonl` (task `e8-harness-contract-audit`) — six
tier-A fail-open contracts, the two CRITICAL ones verified closed at pinned commit `182ccef6`.
The point of that audit was to replace codex's serial run-discover-fix loop with one static pass;
re-running before reading it re-enters the loop the audit exists to end.

### P1-3 — AutoPilot resume (`gpu-serving-tie-in-program.md` Phase 1)
- Gated on **P0-1, the E8 baseline signature**. Preconditions are already fixed and merged
  (tiny-n hard-gate guard `4d329002`, kv_compaction per-role skip `24fa1399`). Fresh-reseeded
  routing memory learns from scratch once resumed; F1 real-task grounding applies.

### P2-5f — GPU-lane shed-batch duty-cycle measurement (`gpu-serving-tie-in-program.md`)
- **POST-REBOOT ONLY. Do not start early.** The dependency chain: P0-1 (E8 signature) → AutoPilot
  resume (P1-3) → duty cycle becomes measurable → complexity threshold becomes settable → the
  P2-5 shed-batch decision rule becomes executable. Sampling duty cycle against a freshly-rebooted
  or still-quiesced host returns a near-zero value and would **wrongly close class 3 (shed-batch)
  on a measurement artifact, not a finding** — this is the exact trap the item exists to warn
  against. Wait for AutoPilot to be running representatively, not just running.

---

### Wiki compilation — DONE 2026-07-29, with one policy gap left open

All 7 queued sources were compiled at the pre-reboot wrap-up on operator instruction (`total_new`
now `0`). Four pages updated: `inference-serving`, `hardware-optimization`,
`benchmark-methodology`, `agent-architecture`, each with a dated *Compiled Update* section.

**Read this before trusting those pages**: three of the campaigns they describe are incomplete, and
the pages say so rather than smoothing it — E8 has **no baseline signature** (numeric half complete
at exact-stop 16/16/0, quality half T1-terminal only; every 07-27→07-29 landing is instrument
repair, and the ratification wrapper's own verdict is *FIX-FIRST — do not sign as pushed*); the GPU
lane is **built, inert, not activated**; E5 W1-W4 are unrun, so every carried-forward number is
observation-grade.

**`requires_human_or_measured_review` — DECIDED, convention suffices (operator, 2026-07-29).**
The manifest's `writer_evidence_policy` sets it `true`, and the four pages compiled on 2026-07-29
are model-compiled without that review; no per-section review-flag banners were added, matching
what recent passes on the same pages did. The operator was presented the choice — add the banners,
or record that convention suffices — and chose **convention**. So this is settled, not pending: do
not re-open it as a defect, do not retrofit banners to these pages, and do not treat the absent
review as blocking any downstream use of them. If the policy field itself should change to match
practice, that is a separate proposal against the manifest, not a fix to these four pages.

## 3. Artifact-update obligation when E5 W1-W4 land

When decision-grade W1-W4 results are ready, the operator-facing results artifact must be
**updated in place, never replaced**. Full requirement text is in
`handoffs/active/batched-decode-measurement.md` under the "E5 W1-W4 runs" task — point future
readers there. The one detail fatal to lose: pass the existing URL explicitly —

```
url: https://claude.ai/code/artifact/b0a7785f-d618-436a-a3e2-46f2fef393aa
```

— when calling the Artifact tool to republish. Omitting `url` mints a brand-new URL and breaks
the operator's existing link. Also required, per the linked handoff:
- Replace the OBSERVATION-GRADE banner/framing — it becomes false once decision-grade figures
  exist.
- Apply the full `MEASUREMENT.md` claim grammar `(metric, protocol-id, n/reps, date,
  attestation ref)` to the new decision-grade figures.
- **Retain the W0 scout numbers alongside** the new figures rather than overwriting them —
  historical numbers are era-labelled and appended per `MEASUREMENT.md`, never edited to "fix,"
  so scout-vs-confirmed drift stays visible.
- The W2 subsection specifically stays quality-invalid in the artifact until the W2 capture smoke
  (§2 above) has passed and real quality data exists.

Source markdown/HTML: `artifacts/operator/e5_w0_preliminary_results.md` /
`.html`.

---

## 4. GPU lane activation — DECIDED (operator, 2026-07-29)

The GPU shadow lane is built (`gpu-serving-tie-in-program.md` P2-6 landed, P2-4 review done) but
**not switched on**. Remaining before any activation:
- **P2-2** — tenants land. **RESCOPED to two tenants by operator decision W3 (2026-07-29)**:
  dense-27B (stock first) + MiniCPM-o (parked promotion runbook §Steps 1-6). **Whisper is no longer
  part of P2-2** — it was refiled as **P2-9**, downstream of the bake-off, with W1 recommended and
  W2 explicitly ruled out (no clone, no HIP build, no GGUF download). Current state: **P2-2a
  dense-27B VERIFIED LANDED**; **P2-2b** MiniCPM-o artifacts verified and its Step-1 proposal
  pre-validated; **P2-2c** (MiniCPM-o Steps 1-6) is the **sole open task**, post-reboot by the
  runbook's own P7 rule, and still needs the runbook **P1 operator grant**. P2-2 is **NOT closed**.
- Activation choreography, Steps 0-7 (`docs/gpu-shadow-lane.md`), operator-gated.
- **Phase 3** — P3-1 shadow bake-off (stock-27B vs FF, scored separately per duty), P3-2 tenancy
  decision package to the operator, **P3-3** operator three-gates sign-off — required before any
  production traffic reaches the lane.

**But before any of that: P2-5j must run first.** It sweeps host-thread placement *including
device-local candidates* — the MI210 is `numa_node=1`, yet the only placements ever compared for
its 8 host threads were `184-191` (SMT siblings of physical `88-95`, inside q3) vs `88-95` itself
— **both cross-node from the GPU's own NUMA node**. Device-local placements (node-1 SMT, e.g.
within `120-143`/`136-143` over Q0B) have **never been tried**. If a device-local placement wins,
the entire q3 entanglement dissolves and any carve happens on Q0B instead, with untested upside on
lane throughput. Activating on the current q3 assumption without running this sweep risks baking
in a wrong placement and invalidating the measured serving-shape lineage that everything else
(ceiling tables, P2-5c shed-batch arms) is built on. **Sequencing: do not carve q3, and do not
flip the activation switch, before P2-5j runs.**

**DECIDED: HYBRID — option C, "sign-off last."** Chosen by the operator 2026-07-29 via
AskUserQuestion in the `fable-auditor` session, from the options package filed on bus task_id
`lane-activation-decision-package`. The full option text with costs, risks and reversibility is
reconstructible from that bus record. Decided sequence:

1. **P2-2 tenant landing first** — non-contending (disk + VRAM work), and a prerequisite of every
   measurement path since the sweep needs a tenant to serve.
2. **Steps 0–7 activation choreography.**
3. **P3-1/P3-2 shadow bake-off starts immediately on the INCUMBENT 184-191 placement** — tenant
   selection is placement-relative and transfers; the P3-2 decision package must carry a
   **placement-pending caveat on absolute latency and token-economics numbers**.
4. **P2-5j placement sweep folds into the P2-5c campaign** as already filed.
5. **Placement + carve (O2+O1 default per the standing topology package) + residency decided
   TOGETHER at the verdict.**
6. **P3-3 production sign-off LAST**, on the final placement — production never inherits a moving
   placement.

Optional early-warning attachment: a 2-arm mini-probe (incumbent vs one node-1 candidate, one
shape, estimated 2–4h).

Two clarifications from the package that correct earlier framing in this section:
- Activating on the current placement does **not** invalidate the measured serving-shape
  lineage — it **uses** it. Re-derivation cost triggers only if the sweep later moves the threads,
  and it triggers then regardless of whether activation came first. What activation-first actually
  risks is narrower: bake-off absolute numbers and production sign-off minted on a
  possibly-suboptimal placement, raising the procedural price of moving later.
- P2-5g (finer-region minting) does **not** change sequencing. Every carve variant is downstream
  of the sweep by P2-5j's own gate, and carve economics matter only at residency-verdict time. It
  blocks neither activation nor bake-off.

The tension narrative above (P2-5j never having compared device-local placements, and the risk of
baking in a wrong placement) remains valid background for *why* the sequence above is what it
is — it is no longer an open question. Do not activate the lane, carve q3, or advance past
P2-2/Steps 0-7 outside the decided sequence above.

---

## 5. Known bus defects and conventions you inherit

- **C20** — reboot spawn blocker, covered in full in §1 above.
- **C11** — `handoffs/active/session-bus-thin-dispatcher.md` line 888: C9 (the `live_mains` /
  `resolve_spawn_cap` / `cmd_spawn` change) landed and was committed (`8cbe50c0`) by the same
  session that had just reviewed C6, on direct operator instruction — but the independent review
  C9's own filing called for is still unpaid. Not urgent (the change is fail-closed on every
  branch it cannot evaluate, both suites green) but a second pair of eyes is cheap now and
  expensive later. This is a coordinator-daemon-owned call, not something to self-resolve.
- **C-OWN — the C-series is UNOWNED.** `claude-gpu-lane` was re-tasked off it and then closed, so
  C6/C9/C10/C14/C16/C18/C21 and all of `tmux_adapter.py` have no owner. Filed as `C-OWN` in
  `handoffs/active/session-bus-thin-dispatcher.md` (~line 678). **Re-assigning this is the first
  bus-side thing a new coordinator should put in a spawn plan** — the delivery plane you depend on
  to do your own job is currently maintained by nobody.
- **C22** — `roster_window_names()` is dead code still carrying the last-writer-wins idiom
  (handoff ~line 682). The reviewer's residual from the C6 fix.
- **C23** — triage disposition has no bulk-clear granularity, so N routed items produce N identical
  payloads (handoff ~line 687). Protocol shape, not a send bug — do not "fix" it in the adapter.
- **C11** review debt (below) and **C22/C23** are all cheap now and expensive later; they are the
  natural first assignment for whoever takes C-OWN.
- **C18a** — `codex-bus-tests` is still listed with `role: main` and no session. Non-urgent: the
  liveness check works correctly regardless of whether this roster field is maintained, but it's
  stale bookkeeping worth fixing when convenient.
- **BUS-GATE convention** for new operator scripts: header comment `# BUS-GATE: <id>`; on apply,
  write `<name>.receipt.json`; when a successor script is minted, mark the old one
  `<name>.superseded`.
- **Operator actions route over the bus as pre-validated token-requests, never pane-only.** Do not
  hand the operator a raw command outside this path.
- **Reload ownership**: the session holding inference executes its own API/stack reloads, at a
  moment it chooses — never reload another session's held inference out from under it.

---

## 6. Open handovers — already actioned, do not redo

From `progress/2026-07/2026-07-29.md` ("Deferred / open"), claude-main's handover:
- **OD-A (KTransformers)** — the simulator-scoped kill in `fable5-window2-findings-02` never
  reached the runtime. Transferable delta is Expert Deferral (async CPU-GPU MoE overlap, ≤0.5%
  accuracy drop), which is NOT AMX-dependent. Operator flagged as a research thread — still open,
  no action taken yet, pick up if prioritized.
- **OD-D (Q5_0)** — the enabling rationale was retracted: the Q4_K_M A/B that motivated it was CPU
  (2026-05-07, pre-MI210), while upstream #1385 is ROCm — the mechanism cannot explain the result.
  Effectively closed as a dead lead; no further action implied.
- [x] **OD-E** — audited `intake-915` (the only non-dived KB entry) for the intake-926 fabrication mode. ✅ 2026-07-29 — core source claims verified; narrowly overstated scope was corrected; `verification` promoted to `dive-verified`. Completion record: `intake-derived-work-2026-07-25.md` ID-10e.

**Explicitly do NOT redo**: claude-main's final message asked for the E5 `stage_b_prune_plan`
provenance repair to be re-assigned, but that request was **stale when written** — the repair is
already **COMPLETE**, landed as research commit `d61e4e8c` and root commit `dd1d0b4b` (see
`coordination/session-bus/outbox/codex-bus-tests.jsonl` task `e5-stage-b-plan-provenance-repair`,
and `artifacts/operator/e5_w0_preliminary_results.md` line 134 / `.html` line 296). Do not
re-open or re-run this.

---

## Bus drain reminder

Per `CLAUDE.md` bus protocol: at your first task boundary in this session, run
`scripts/coordination/session_bus.py drain --agent <your-roster-id>` and act on any pending
assignments/nudges, then refresh your heartbeat
(`session_bus.py append --agent <id> --target heartbeat --json '{"state":"working","task_id":"<id>"}'`).
Given the C18 "LOOKS DEAD" advisories expected right after bringup (§1.3), this is doubly
important now — it is how you stop being counted as dead.
