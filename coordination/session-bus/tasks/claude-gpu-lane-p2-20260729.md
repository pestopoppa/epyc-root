# TASK BRIEF — claude-gpu-lane — P2-5j sweep protocol, then P2-2c

**Roster id:** `claude-gpu-lane` · **Lane:** gpu / none · **Assigned by:** coordinator-agent,
2026-07-29

You wrapped and closed cleanly pre-reboot; everything below is your own filed state, picked back
up. Owning handoff: `handoffs/active/gpu-serving-tie-in-program.md`.

## 0. Start here — the work that needs nothing from anyone (do this FIRST)

**Design the P2-5j host-thread placement sweep protocol.** Zero inference, zero gates, so it does
not wait on the stack or on an operator signature.

The finding that makes it necessary, restated because it decides the design: **the MI210 is
`numa_node=1`, yet the only placements ever compared for its 8 host threads are `184-191` (SMT
siblings of physical `88-95`, inside q3) and `88-95` itself — and both are cross-node from the
GPU's own NUMA node.** Device-local placements (node-1 SMT, e.g. within `120-143` / `136-143` over
Q0B) have **never been tried**. If a device-local placement wins, the entire q3 entanglement
dissolves and any carve happens on Q0B instead, with untested upside on lane throughput.

Protocol must state, per `MEASUREMENT.md` claim grammar: the arms (incumbent `184-191`, `88-95`,
and at least one device-local node-1 candidate), n/reps, the shape(s) held fixed, the codified
recipe it invokes, and what would falsify a win. Import recipe constants from
`bench_canonical.sh` / `canonical_recipe.py` — do not retype remembered values. **P2-5j folds into
the P2-5c campaign** as already filed.

Optional, if you judge it worth proposing: the **2-arm mini-probe** early-warning attachment
(incumbent vs one node-1 candidate, one shape, est. 2–4h).

## 1. Then P2-2c — MiniCPM-o promotion Steps 1–6

**P2-2 is NOT closed** and you were right to refuse to mark it so. State you filed:
- **P2-2a dense-27B — VERIFIED LANDED** (28,665,067,072 B, sha256 `5927dc06…43897b2a`, re-hashed on
  disk against the `qwen36_27b_stock_q8` tenancy row).
- **P2-2b MiniCPM-o — artifacts verified**, both P4 hashes re-verified against the bytes, Step-1
  registry anchors re-validated exact (lines 4072-4138, line 249 verbatim, block still State A).
  **The runbook block IS the proposal diff — no re-derivation needed.** NOT APPLIED.
- **P2-2c — Steps 1–6, the sole open task.**

**Two preconditions, neither of which is yours to grant:**
1. **Fleet up.** The runbook's own P7 rule blocked this pre-reboot: no fleet port was listening,
   and Step 2 explicitly **forbids a manual mode override** in exactly that case. `codex` is the
   inference owner and is bringing the stack up now — **wait for its confirmation, then re-run P7
   yourself rather than assuming.**
2. **The runbook P1 operator grant**, plus its Step-4/6 inference authorisation. Coordinator-agent
   is presenting this; do not start Steps 1–6 without it.

**Whisper is no longer part of P2-2** — refiled as **P2-9**, downstream of the bake-off, W1
recommended, W2 explicitly ruled out (no clone, no HIP build, no GGUF download). Your fail-safe
banner at the head of `orchestration/gpu_shadow_lane_np_ceiling.yaml` (orchestrator `66165717`)
stands: those `phase2_resident_set` rows are **conservative, not wrong**, and reclaiming whisper's
1.6 GiB is a ceiling amendment gated downstream of P2-5j like every carve variant.

## 2. The decided activation sequence — do not deviate

**DECIDED by the operator 2026-07-29: HYBRID, option C, "sign-off last."** Filed on bus task_id
`lane-activation-decision-package`. The sequence:

1. **P2-2 tenant landing first** — non-contending (disk + VRAM), and a prerequisite of every
   measurement path, since the sweep needs a tenant to serve.
2. **Steps 0–7 activation choreography** (`docs/gpu-shadow-lane.md`), operator-gated.
3. **P3-1/P3-2 shadow bake-off starts immediately on the INCUMBENT `184-191` placement** — tenant
   selection is placement-relative and transfers. The P3-2 decision package **must carry a
   placement-pending caveat on absolute latency and token-economics numbers.**
4. **P2-5j folds into P2-5c.**
5. **Placement + carve (O2+O1 default per the standing topology package) + residency decided
   TOGETHER at the verdict.**
6. **P3-3 production sign-off LAST**, on the final placement — production never inherits a moving
   placement.

**Do not carve q3 and do not flip the activation switch before P2-5j runs.** Two corrections from
the decision package that supersede earlier framing: activating on the current placement does
**not** invalidate the measured serving-shape lineage — it *uses* it; and **P2-5g (finer-region
minting) does not change sequencing** — it blocks neither activation nor bake-off.

## 3. Host state as of 14:12Z (verified)

- `verify_llama_cpp.sh` **PASS** — `production-consolidated-v8` @ `67a433bf4`, CPU **and** HIP
  servers both `10107`.
- **region-lock: q0/q1/q2/q3 all free** — the pre-reboot q3 hold did not survive.
- Uptime ~30 min; the P-BENCH decision-grade window is **reopened**.
- 🔴 **AutoPilot DOWN.** It is the representative production load generator. **Do not sample GPU
  shed-batch duty cycle now** — P2-5f is explicitly POST-REBOOT-ONLY *and* downstream of AutoPilot
  running **representatively, not merely running**. Sampling against a quiesced host returns a
  near-zero value and would wrongly close class 3 (shed-batch) **on a measurement artifact, not a
  finding**. This is the exact trap the item exists to warn against.

## 4. Constraints with live reasons

- **`codex` owns the inference and the stack.** Only the owning session reloads the orchestrator
  API or the stack. Route any reload request to coordinator-agent — never run one around codex's
  protected runs (fabric axiom 4; origin 2026-07-28, two external API-only reloads forced
  regeneration of in-flight ordinals mid-collection).
- **The CPU is busy**: codex on E8, `claude-main` on E5, concurrently by operator decision. You are
  gpu/none — **acquire** region claims via `region-lock`, never infer a region is free by observing
  it (TOCTOU).
- **MI210 host threads**: current incumbent is `taskset 184-191` (SMT siblings), and the server
  stays resident per MODEL. That incumbent is what P2-5j exists to test — do not treat it as
  settled while designing the sweep.
- Trust boundaries are human-only. Never sign, never flip a checkbox you do not own.
- **Bus hygiene, your own filed lesson**: *a repeated payload across N corr_ids is bus noise by
  construction.* 19 byte-identical `triage-disposition-post-standdown` messages are still sitting
  in the coordinator's triage queue (defect C23, protocol shape, not a send bug). Keep payloads
  terse and item-specific.

## 5. Bus discipline

At every task boundary:

```bash
python3 scripts/coordination/session_bus.py drain --agent claude-gpu-lane --triage
python3 scripts/coordination/session_bus.py append --agent claude-gpu-lane \
  --target heartbeat --json '{"state":"working","task_id":"<current>"}'
```

Report to coordinator-agent on task_id `p2-5j-protocol` (then `P2-2-tenant-landing`). Anything
needing an operator signature goes out immediately, not batched into a wrap-up. Checkbox
discipline: flip `- [ ]` → `- [x]` with an inline `✅ 2026-07-29`; prose status is invisible to the
dashboard.
