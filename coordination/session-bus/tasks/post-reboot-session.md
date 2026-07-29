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

If any of the above is mid-write by another live agent when you go to read it, note that and move
on rather than blocking on it — other sessions may still be active across the reboot boundary.

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
- **P2-2** — tenants land: dense-27B (stock first) + MiniCPM-o (parked promotion runbook
  §Steps 1-6) + whisper.
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
- **OD-E** — audit `intake-915` (the only non-dived KB entry) for the intake-926 fabrication mode.
  Still open.

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
