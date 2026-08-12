# Ratification package — coordinator-seat refactor, 2026-08-12

**One package, at the end, as directed.** Everything below needs the operator's own hand, either
because it sits behind the human-amendment-only trust boundary, or because it is a judgement about
evidence that an agent should not make for you. Nothing here has been applied.

Each item states: what it is, what it costs, what happens if you do nothing.

The work that did NOT need your signature is already landed and is summarised at the end for
context, not for approval.

---

## A. Trust-boundary amendments (2)

Full text, exact YAML, and apply commands are in
[`OPERATOR-SIGNATURE-PACKAGE-20260812.md`](OPERATOR-SIGNATURE-PACKAGE-20260812.md); summarised here
so you can decide from one page.

### A1 — Gate the auto-loaded instruction surfaces (AUD-15)

Add `CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md`, `agents/shared/*.md` to
`coordination/session-bus/human_only_paths.yaml`, then rewrite the `.sha256` pin.

- **Why**: those files load into *every* session at startup. `CLAUDE.md` already requires operator
  approval for sub-agent edits and **nothing enforces it** — eight `Write|Edit` hooks are
  registered and not one guards them as an instruction surface. On 2026-08-12 commit `2f787163`
  edited both with no ask, no token, no receipt. A wrong premise there becomes five sessions' truth
  at once (F-21 is the proof: a false claim about reboot durability is the stated reason one main
  committed another agent's work).
- **Cost**: every policy edit then needs your signature. Note honestly that this is a **speed bump,
  not containment** — Layer 2 of the hook fails OPEN if the gate list cannot be parsed, by design.
  As scoped, `agents/coordinator-agent.md` stays ungated (it is a role overlay, not `agents/shared/`).
  Adding `agents/*.md` would gate role files too, at more friction.
- **If you do nothing**: the gap stays open and F-19 recurs the next time a subagent is pointed at
  an instruction surface.

### A2 — P-GPU-1 field 3: name the verifier-produced linkage receipt

One clause added to `measurement/protocols/gpu-cross-device.md` field 3: the `LD_LIBRARY_PATH` /
backend evidence is satisfied **only** by a verifier-produced receipt captured against the running
binary (verifier id, inspected library set with per-library path and sha256, verdict) — never by a
recorded environment string alone, and a receipt that inspected nothing is vacuous.

- **Why**: llama.cpp *dlopens* `libggml-hip.so`, so a "HIP" run can execute entirely on CPU while
  `ldd` shows nothing. A hand-recorded env string cannot distinguish the two.
- **Cost**: none operationally — the Phase-5 launcher gates produce this artifact automatically, and
  the receipt schema already exists twice in the codebase.
- **If you do nothing**: the mechanisms still ship; the constitution keeps permitting a
  hand-recorded string, so the INC-20260731 class stays formally possible.
- **Do not apply retroactively**: §B below was dispositioned under the *current* text.

---

## B. Measurement judgements (2)

Evidence: [`docs/reviews/gpu-linkage-retro-certification-20260812.md`](../../docs/reviews/gpu-linkage-retro-certification-20260812.md).

**The headline is good news**: the **v9 freeze evidence SURVIVES certification.** The production-v9
cert run banked `LD_LIBRARY_PATH` as a single-entry override, so the stale container path could not
participate in resolution — immune by construction. The CLAUDE.md-level freeze rests on evidence
that holds. Two artifacts certifiable, five observation-grade, and **nothing in the audit shows any
measured number to be wrong** — the vision harnesses defeated the hazard, they just failed to bank
the proof.

### B1 — The vision-cutover numbers: split decision

| Number | Verdict | Reasoning |
|---|---|---|
| Accuracy (`+11.2 pp`, McNemar `p=0.0011`) | **No re-run needed** | Accuracy is invariant to which device executed the tokens; `harness.py:242` *prepends* the HIP build dir so the precondition never held; sampled VRAM scaled monotonically with model size |
| Throughput / VRAM (`decode 112.20 vs 214.54 t/s`, `vram_mb_total 21061`) | **Re-run before they gate anything further** | Quoted in `model_registry.yaml:2231-2238`; exactly the class the hazard corrupts |

**Decide**: re-run the throughput/VRAM pair now, or leave them observation-grade and simply stop
citing them in decisions until someone needs them.

### B2 — The sharper problem: `model_registry.yaml:2478`

The registry attests `architect_general` `baseline_tps: 30.87` / `contended_tps: 19.81` to
`gpu_coresidency_20260731` — an **experimental-kernel** artifact with no `LD_LIBRARY_PATH`, no
commit, `n=3` against a −35.8% claim, whose own title reads *"GPU co-residency curiosity measurement
(no gate)"*. It feeds `q_scorer` baselines.

**Decide**: relabel the registry entry to observation-grade (cheap, immediate, and honest), or
schedule a governed re-measurement, or accept it explicitly with the limitation recorded.

---

## C. Row edits an agent must not make (Phase 7 §7, items 1–7)

Listed in full in the audit note's §7; item 8 is already closed. They include a `model_registry`
relabel and **four stale `multimodal-pipeline.md` rows** — S-16 is still `- [ ]` for a promotion that
shipped in orchestrator `a517793c` on 2026-08-01, and `:492` states `worker_vision` stays on
Qwen2.5-VL, which **contradicts the live registry**. These are index/handoff edits, which need your
approval by standing rule.

**Decide**: approve the batch, or nominate which to apply.

---

## D. Host-level items (2) — need root or ownership I do not have

### D1 — `worktree.useRelativePaths=true` is still in `/etc/gitconfig`

This is the **system-level root cause** of the worktree destruction. With it set, git writes gitdir
pointers that resolve only at the depth they were written for; from the other path depth of the bind
mount the same live worktrees read *prunable*, and a `git worktree prune` — or the `git gc` that runs
one — deletes their admin data. That is what destroyed all five lane worktrees on 2026-08-12.
Repo-local `false` protects this repo only; every other clone on the host is still exposed.

```bash
sudo git config --system --unset worktree.useRelativePaths
```

### D2 — A Python venv was created into `/workspace` itself

`pyvenv.cfg` reads `command = /home/node/.local/bin/python3.12 -m venv /workspace`, with `bin/`,
`lib/`, `lib64` as its skeleton. Untracked **and** un-ignored, so it is exposed to any `git add -A`
or `git clean -x`. I did not touch it in case a session is using it. It should be relocated by
whoever owns it.

---

## E. Disposals awaiting your call (2)

1. **25 orphan worktree directories** under `/mnt/raid0/llm/worktrees/mains/*.orphan-20260812T1035Z`
   and `/mnt/raid0/llm/autokernel/worktrees/`. **The hazard is already neutralised** — the five
   `mains/*` backups still pointed at the LIVE lanes' admin dirs (a stray `git add` inside a backup
   would have landed in a working lane's index), so each `.git` was renamed to
   `.git.disabled-20260812`: content preserved, inert to git, reversible. Whether to delete the
   directories is yours. **`git worktree prune` must never be the tool** — they are unregistered,
   and prune is what caused this.
2. **`stash@{0}` in `epyc-inference-research`** — 6 superseded predecessor files kept as evidence
   during the reconciliation. Droppable once you are satisfied.

---

## E2. Two dispatch items with named blockers (routed, not decided)

Both were found while making the tick actually able to fire. Neither is a
judgement call — they are work someone must do — but they are listed here because
they gate the loop doing anything useful on day one.

1. **11 `opendataloader-pipeline-integration--*` queue rows are unrecoverable by
   machine.** Every anchor has rotted (`:405` is now a tree-diagram branch) and the
   rows carry no `task_text` to recover from, so nothing can re-derive what they
   were. They need a human to re-anchor them BY TEXT. This is the exact case
   C50b measured as "11 of 11 rows".
2. **`mainC` asks for ~2 minutes of quiet host** to convert today's scout-grade
   cells into bankable decision-grade numbers. Uptime now passes; the last failing
   preflight leg was `tripwire_bench`, contended by the migration. Purely a
   scheduling call.

## F. One expectation to set before the daemon comes up

Not a decision — a thing that will otherwise look like a bug on first contact.

The tick now **refuses to auto-dispatch a row lacking `screened_by` or `expected_occupancy`**. That
is the intended fail-closed posture — an autonomous dispatcher acting on a stale or shallow row is
the failure this exists to prevent — and hand-dispatch is unaffected throughout.

Intake now writes both receipts, and the live queue was backfilled where it could be done honestly:
8 rows gained `screened_by`, 4 gained occupancy, 8 gained `task_text`. **15 of 19 live rows remain
hand-dispatch-only**, 11 of them because they are the unrecoverable rows in §E2 above. So expect the
first tick to dispatch little and *say why* for each refusal, rather than to dispatch nothing
silently.

Two things had to be fixed before any of that could hold, and both are worth knowing because each
would have produced the same symptom — a loop that never fires — from a different direction:

- **`fold_queue` is last-write-wins**, and all eight row-rewrite sites dropped the new fields. A row
  born screened and estimated would have lost both on its first status change and been refused
  forever.
- **`STALE_REQUEUED` was a black hole.** The stall ladder writes it when a lease expires with
  attempts remaining (and `INFRA_BLOCKED` when they are exhausted, which is where the retry bound
  lives), but nothing converted it back to `READY` and eligibility demanded `READY`. **17 of 19 live
  rows sat there, unassignable regardless of receipts.** Now assignable, pinned by a test over the
  status tuple rather than a spelling.

**An unestimated row is a row a human dispatches — not a row to invent a number for.** The intake
rules deliberately emit *no* occupancy field rather than a zero or a guess for any `cpu`/`gpu` row
without a stated duration, because a fabricated number there is precisely the F-14 harm, and a `0.0`
reads downstream as an answered question rather than an open one.

Likewise: on first bringup the supervisor will read the daemon's source-tree marker as **UNKNOWN**
until the daemon has started once under the new code, and will correctly refuse to restart it.
Cannot-determine never justifies a kill. Start the daemon first, then the supervisor.

---

## What landed without needing you

For context only. 8 phases, ~32 commits this session on top of the 139-commit batch push.

| Your complaint | What changed |
|---|---|
| *"it can't nudge the mains"* | Submit **and** discard now measured working (`space + settle + key`; bare keys and `Escape` do nothing); failed deliveries actually roll back instead of stranding text that re-arms the refusal loop; a main whose subagents redraw its pane is reachable via the doorbell instead of looking unreachable-but-idle |
| *"its inbox cries wolf"* | 310 standing triage items → **45 MUST-ACT + 265 FYI**. Multi-recipient `action_required` is refused at the point of writing, with the compliant rewrite in the error text |
| *"resources sit idle"* | Dispatch rows are typed: `task_text` is the identity, `screened_by` and `expected_occupancy` are required for auto-dispatch, deeper work wins between equals, and `drain` reports queue depth and in-flight occupancy so "is the fleet loaded?" is a reading |
| *"wrap-ups collide"* | Per-main lane worktrees, per-agent progress files, and an O_EXCL lease — proven by a concurrent-wrap-up test with a negative control, and live on the real lanes (mainD refused 5×, acquired 2.16s later) |
| *"it reports wrong things"* | The role no longer reads instruments at all (AUD-1). It relays receipts carrying `source_msg_id` or `receipt_path`, or it does not send the figure |
| *"the watchdog kills healthy daemons"* | mtime predicate replaced by a committed-tree SHA marker; restarts rate-limited to one per 15 min then ALARM. 7/7 mutants killed including a vacuity mutant |

Three failure-mode rows closed by **deletion rather than construction** (R-12/R-14/R-15 collapse into
AUD-1's subtraction) — the delete-lens the audit asked for and rarely gets.
