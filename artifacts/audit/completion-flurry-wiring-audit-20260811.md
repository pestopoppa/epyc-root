# Completion-Flurry Wiring Audit — 2026-08-11

**Auditor:** `auditor` (Fable 5, xhigh) · **Assigned:** coordinator-agent on direct operator
instruction · **Task:** `auditor-completion-flurry-wiring-audit`
**Scope:** the 2026-07-29 completion set, audited for MISSED WIRING — the standing question is
not "was it done" but "is it wired in, and is it live". Four states per item: (1) committed and
live · (2) committed, not live · (3) claimed, not committed · (4) live but wired to the wrong
thing.

**Status: COMPLETE** — all four sections done, verified, and filed on the bus.

## Executive summary (running)

- **D:** Two of the three "pending" operator tokens are ALREADY SPENT — operator-ratified
  2026-07-29 pre-reboot; receipts on disk. The third (E9 era row) is a dead command over a live
  need. The queue presents all three as pending because the delivery plane treats bus-message
  state as world state.
- **A:** 8 of 11 completions fully committed-and-live. `repl-turn-efficiency-ready-batch` is
  claimed-NOT-committed (wiped by the 17:30Z tree-restore `2053b758`, never re-applied);
  `utm-m5` instrument is committed-not-live (zero runs, zero consumers). The E8-ratified retry
  NEVER executed (writer abort 11:33Z, 9 min post-ratification). New defect: the token relay is
  receipt-blind and regenerates spent tokens as pending on every daemon restart.
- **C:** Two operator-signature items — no cpu_bench era row exists for v9 (every CPU bench
  since the freeze inherits a wrong era), and ratified Annex G still pins P-GPU-1 to
  "currently v8" while AutoKernel is mid-rollout. Consolidated era-row token is now a four-item
  package. `verify_llama_cpp.sh` correctly enforces v9; no phantom era ids in live code.
- **B:** The queue decayed further while frozen: TOP-40 dispatchable 1→0 (one 07-29 "verified"
  claim was false when written), anchor rot 27%→51%, and **79.5% of the queue's READY surface
  is invalid**. Template corruption confirmed and under-reported at least twice; ONE standing
  constraint is still wrongly `[x]` right now — it survived mainC's repair because the guard
  tool reads a box-scoped banner as section-scoped (the un-enumerated seventh box). 19 template
  steps still offered as READY.

---

## D. The three "pending" operator tokens — VERDICT: 2 spent, 1 dead-command/live-need

Priority item, re-validated first at coordinator request. Headline: **the token queue is
presenting two tokens the operator already signed 13 days ago.** The post-reboot fleet rebuilt
its worldview from 12-day-old undelivered bus messages and never checked for receipts on disk.

### D1. `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` — SPENT (ratified 2026-07-29 10:59Z)

- Receipt: `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json`,
  `status: ratified`, `reviewed_at: 2026-07-29T10:59:11Z` — 41 min after the token request
  (10:18:27Z).
- Transaction journal:
  `artifacts/operator/pbench4_fg4b_affinity_transactions/.pbench4-affinity-20260729T105911Z.m40lby_o/COMPLETE`
  = `{"state": "committed"}`.
- Amendment landed as commit `e6b84496` (2026-07-29 13:14Z, operator-authored,
  "measurement: P-BENCH-4 affinity-witness superseding amendment (FG-4b)"), MEASUREMENT.md +31
  lines, CHANGELOG +2 — all **pre-reboot** (reboot ~14:15Z).
- The literal marker heading was later dropped by the **v2 constitution rewrite** (`a9647a7a`,
  2026-07-30, operator-authored), but the substance was carried forward: current
  `MEASUREMENT.md:57` protocol-table row `P-BENCH-4 … ✅ (+affinity superseding amend)` and annex
  `measurement/protocols/bench-cpu.md:116` (§ P-BENCH-4). **Not a wiring loss** — a
  restructure that preserved the ratified content.
- Dry-run today: exit 1, `ERROR: runner worktree is not at the pinned commit`. Irrelevant — by
  design (duplicate-marker refusal + preimage-hash pins) this token can never validly run twice.
- **Action: DO NOT PRESENT. Queue row is stale** (`tokens/token-queue.md:134`, unchecked).

### D2. `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729` — SPENT (ratified 2026-07-29 11:24Z)

- Receipt: `artifacts/operator/ratify_e8_final_c1_retry_capacityfix_20260729.json`,
  `status: ratified`, `ratified_at: 2026-07-29T11:24:32Z` — 8 min after the token request
  (11:16:38Z). Script sha on disk today matches the receipt's recorded pin (`d7e3161e…`):
  self-consistent.
- Dry-run today: exit 1, the ratifier's own guard —
  `ERROR: final-c1 capacity-fix ratifier receipt already exists`. That refusal **is** the
  spent-token proof.
- Correction to the queue/resume-brief framing: `inference-e8-resume-20260729.md:57` claims the
  script "pins root main `300ed404` → will refuse on drift". It does not — it pins orchestrator
  `182ccef6` + file hashes; the operative refusal is receipt-exists.
- **Execution answer (Section A follow-through): the ratified work NEVER executed.** The retry
  writer aborted at 11:33:14Z — nine minutes after ratification — with
  `status: terminal_aborted_no_admission`, `error_type: builtins.ValueError`
  (`artifacts/operator/e8_quality_baseline_v5_partial_r2_final_c1_capacityfix_20260729T112433Z/writer_abort.json`,
  verified directly). The two `"outcome": "clean"` rows in the same namespace are copied-forward
  pointers to pre-existing race-row sidecars (413-byte file, no response text, sidecar hash for
  ordinal 279 identical to the pre-retry handover note), not fresh generation. Nothing has run
  since: repair-chain work continued to 07-30 11:52Z, then the fleet went dark;
  `gpu-serving-tie-in-program.md:48` `P0-1` is still `- [ ]` as of its newest commit **today**
  (`abf1a905`), and `inference` is currently on `autokernel-completion`, not E8. Executing now
  would run under the **v9** kernel (10125) against a v8/E8-era baseline — cross-era. This needs
  a fresh operator decision package (owner: inference), not this token. P0-1 still gates
  AutoPilot resume (P1-3) and everything downstream.
- **Action: DO NOT PRESENT. Queue row is stale** (`tokens/token-queue.md:144`, unchecked).

### D3. `RATIFY-E9-ROUTING-REWARD-ERA-20260729` — DEAD COMMAND, LIVE NEED

- The command pins `sha256(orchestration/instrument_eras.yaml) = 6aedacad…`; current is
  `3ebfa6cf…` → the assert refuses (verified read-only, no state touched).
- Cause of drift: **autopilot has been sealing eras into that same file autonomously** —
  E14/E15/E16 landed since 07-29 (`git log`: "autopilot: seal E14/E15/E16 …").
- The need survives: `id: E9-routing-reward` is **absent** from the yaml; the reward-saturation
  repair boundary (2026-07-21T15:27:04Z, scope `routing_reward`) is still unrecorded.
- Re-authoring hazard: the token appends the row as the FINAL `eras[]` entry
  (`assert d['eras'][-1]['id']=='E9-routing-reward'`). With E11–E16 now sealed, a naive re-pin
  appends a `from: 2026-07-21` row after rows that post-date it — out of chronological order.
  The insertion point must be re-derived by the owner.
- **Action: re-author (owner: mainB's successor), then re-present. Not currently presentable.**

### D4. Consolidation finding — still applies, STRENGTHENED

The 07-29 finding `THREE-tokens-would-race-on-instrument_eras.yaml`
(`msg-20260729T162119Z-56-auditor`) named E9-routing-reward, mainA's `e5-era-row-token`
(token-request undelivered ~305 h, daemon-escalated), and the seeding-scorer era label. All
remain unfulfilled. Strengthened because autopilot's autonomous era-sealing means **any
whole-file sha pin on `instrument_eras.yaml` rots within hours** — a static pre-validated
command over that file is dead on arrival. Recommendation to coordinator: consolidate all owed
era-row insertions into ONE token, authored (and sha-pinned) at presentation time.

### D5. Root cause of the phantom-pending state (wiring class: state 4 — wired to the wrong thing)

`tokens/token-queue.md` presents all three tokens as unchecked-pending with "pre-validated,
dry-run exit 0". The queue was rebuilt from stale undelivered outbox messages;
`inference-e8-resume-20260729.md` §3 asserts "neither was signed", which durable receipts
refute. The delivery plane treated *message-not-delivered* as *decision-not-made*. **The receipt
on disk, not the bus message, is the source of truth for whether a token is spent** — the queue
rebuild consumed the wrong source. Queue rows D1/D2 are stale; the queue owner (mainC per
current dispatch) flips them — this audit touches no checkbox.

Residual: artifacts cannot prove WHO typed `--attest`. Everything is consistent with
operator-run attestation pre-reboot (operator-authored amendment commit 13:14Z same morning).
If the operator does not recall signing on the morning of 07-29, that becomes an incident-grade
question. Flagged to coordinator (`msg-20260811T090716Z-138-auditor`).

---

## A. The 2026-07-29 completion set — four-state wiring test

All eleven completions resolved. Subagent evidence reviewed; every load-bearing negative was
independently re-verified on my thread (noted inline). States: **1** committed+live · **2**
committed, not live · **3** claimed, not committed · **4** live, wired to the wrong thing.

| # | From / task | State | One-line verdict |
|---|---|---|---|
| 1 | auditor `c-own-round-2` (12 commits) | **1** (10/12); C32 latent | All on main; C24/C25/C26/P1b/C27a/b/c/C33 observably executing TODAY. C32 committed+wired, fail-closed, but zero live invocations ever (no roster row uses an index endpoint). |
| 2 | auditor `c36-runtime-liveness` | **1** | Call chain `resolve_stuck_agents → _tmux_nudge → tmux_adapter nudge → probe() → runtime_liveness()` traced end-to-end. The Claude-liveness source decision (`msg-20260729T165422Z-397`) remains genuinely unanswered — matches the completion's own disclosure. |
| 3 | auditor `p2-5l-stack-numa-doc-debt` (`ae40ee8b`, orch) | **1** | Corrected NPS4 header still live and accurate. Context obsolesced within 24 h (quarter retirement `982adb0c` 07-31; the 07-30 ~2× NUMA placement defect in the same file) — not a defect of this narrow-scoped commit. |
| 4 | auditor `stale-open-audit-extension` (`5c10b466`) | **1**, artifact since retired | The index file it edited was deleted in the legitimate 08-10 restructure (`b208d9ce`); the substance it certified (B1–B5, E2/E3 boxes at owner handoffs) is still true at HEAD. |
| 5 | codex-bus-tests `e5-stage-b-plan-provenance-repair` (`d61e4e8c`) | **1** | Provenance chain `06b0abb2 → 9b4d4f03 → cabd10bd0f` intact; handoff-cited hash equals `git show HEAD` hash exactly. Doc/provenance artifact — no runtime consumer exists to mis-wire. |
| 6 | codex-bus-tests `bus-c6-verification-followup` (`73d31568`) | **1** | Overlay-tolerant predicate present at HEAD (+19 stacked commits, unreverted); imported by the daemon that started TODAY 08:48Z (pid 496387) — verified on my thread. |
| 7 | inference `utm-m5-per-window-store-instrument` (`05e0b8bf`, orch) | **2** | The C27 shape. On main, tests pass, UTM-M5 box reconciled `[x]` — but **zero callers, zero runs ever, zero output anywhere on the filesystem**. The question it was built to answer (per-window success decay) remains unanswered. Also missing its belief-kernel write-side wiring row (see A-w below). |
| 8 | mainC `dsa-legacy-scope-audit` (`c2ff1f80`) | **1** | Confirmatory stale-pointer closure; content correctly superseded into `inference-research-index.md` INF-31 → owner doc still states the MOOT/#23346 facts. |
| 9 | mainC `opendataloader-pageindex-consumer-probe` | **1 by accident / 3 for evidence** | mainC's original commit was **wiped by the tree-restore** `2053b758` (dangling blob `2045dd32` proves it existed) and coincidentally re-authored next day by an unrelated bulk commit. The cited evidence doc `docs/reviews/opendataloader-pipeline-none-lane-20260729.md` is **untracked to this day** — never committed on any ref (re-verified on my thread). The exact untracked-looks-committed trap. |
| 10 | mainC `skyrl-rollout-tree-accounting-design` (cited `HEAD`) | **1** | Dangling citation resolves cleanly to `d7c8dbdb` (4 s before the bus post); design content verbatim at HEAD; "no code change" claim correct. Defect is citation practice only — a moving ref in a completion record. |
| 11 | mainC `repl-turn-efficiency-ready-batch` (4 rows) | **3** | All four closures (L101/L102/L117/L120) **wiped by the tree-restore and never re-applied**. Re-verified on my thread: all four `- [ ]` at HEAD, `git blame` → `2053b758`. Bus claim is currently false against git; queue rows still `READY` (accurate — the work is genuinely undone); anchors not rotted, cleanly re-dispatchable. |

### A-w. New wiring defects surfaced by the sweep (not in the 07-29 claims)

1. **Token relay is receipt-blind (state 4 — live, wired to the wrong source of truth).** C27a
   (`relay_token_blocks`) and C33 work exactly as committed — and that is the problem: on
   today's 08:48Z daemon restart they regenerated the two SPENT tokens (D1/D2) as pending queue
   blocks (+246 uncommitted lines in `token-queue.md`, mtime 08:48:11), and the C33
   prevalidation defect notice re-fires **every tick** on mainA's 12-day-old
   `E5-THROTTLE-SCOPE-ERA-ROW-20260729` request (advisory rows 09:17:43Z, 09:18:10Z, …).
   Deleting the stale queue rows will not stick — the relay recreates them on the next restart
   unless it learns to check for a receipt/spent state before presenting a token block. Routed
   to mainD (C-OWN owner).
   **CLOSED same day as C39** (`fd0fdd6e` receipt-aware relay, annotate-never-suppress;
   `917badee` drift check; `41c20ef5` scope-honest all-clear) plus the auditor-side class
   closure (`ebce92a2`: static conformance check, 3 signed-but-unindexed gates indexed,
   authoring contract at `receipts/README.md`). Sole remaining step: coordinator-agent
   restarts the daemon so the fixed relay goes live. Residual `ratify_and_apply_e8_quality_
   baseline_v4_20260727.sh` stays with inference (retire-or-repin), named by the check.
2. **Advisory-store bloat**: `status` reports ~3.0M advisory rows; C34's dedup covers
   schema-invalid rows but not per-tick `would-assign`/re-fired notices. Routed to mainD as an
   observation.
3. **UTM-M5 instrument has no belief-kernel write-side hook**: no row in
   `scripts/vidya/adapters/README.md`, no task in the vidya program handoff — the exact
   `benchmarks/results` failure shape (4,562 files, no write hook, 0 usable claim tuples). Routed
   to inference (instrument owner) with `action_required`; not edited directly because the
   handoff tree is dirty under parallel writers today.

### A-rc. Cross-cutting root causes

- **RC1 — the 17:30Z tree-restore silently destroyed same-day work.** `2053b758` ("fix: restore
  full tree after malformed isolated index", 1,955 files) reset the tree to a stale snapshot,
  wiping the ~15:00Z commit window. Casualties: item 11 (still lost at HEAD), item 9's original
  commit (recovered only by coincidence). **No INCIDENT_LOG entry exists for this event**
  (grep verified 0 hits) — a restore that discards committed same-day work is exactly what the
  incident log is for. Routed to coordinator; the log file is dirty under another writer, so I
  did not add the entry myself.
- **RC2 — bus-message state treated as world state.** One failure family across D and A: the
  token queue rebuilt from undelivered messages without receipt checks (D5); the resume brief
  asserting "neither was signed" against on-disk receipts; C27a/C33 replaying 12-day-old
  requests as live. The delivery plane needs a rule: **artifacts on disk (receipts, checkbox
  state at HEAD) outrank any bus message when they disagree.**

## B. Dispatch-queue corruption, re-derived against today's tree

Full re-derivation over the queue's TOP-40 sample, its replacement list, all 73 unique
runner-up refs, AND all 1,080 BY-HANDOFF rows (an extension beyond the 07-29 audit). Pinned to
09:25Z; mainC landed repair commits (`e43c8c27`, `001c06da`) at 09:21–09:22Z **mid-audit** —
figures below are post-repair unless stated. Surviving-corruption claims re-verified on my
thread after mainC's commits.

### B-1. Decay since 07-29 — the queue was frozen while its targets moved

Exactly ONE commit touched the queue in 13 days (`eb92b4c9`, 08-10 — five string renames, zero
rows, zero boxes), while 40 of its 182 target handoffs were edited under it. Re-derived
classifications:

| bench | 07-29 | today |
|---|---|---|
| TOP-40 examined rows: dispatchable | 1 of 9 | **0 of 9** (row #37 was already closed *when the audit ran*; row #35 was flipped **14 min after** the audit certified it) |
| "VERIFIED-DISPATCHABLE" replacement list (header claims 100%) | — | **2 of 13** (three entries closed 2, 5, and 14 min after the audit commit) |
| Straight-swap-in list (header: "verified still open") | 0 of 8 | **0 of 8** (composition shifted: 4 closed / 4 anchor-rot; entries 1 and 3 are standing PROHIBITIONS offered as work) |
| 73 unique refs: anchor rot | 27% | **51%** (34/73 refs now point at a different KIND of line than 13 days ago — measured by diff, not inferred) |
| 73 unique refs: dispatchable | 19% | **4–10%** (substantive vs strict anchor rule) |
| All 1,080 rows: READY surface (`blocker = -`, 244 rows) | — | **79.5% invalid** (50.8% rot · 28.3% already-closed — rot rate independently reproduces the 73-ref sample's 50.7%) |
| Counts-table headline | "open boxes falling" | **inverted** — unchecked tasks grew 1,082 → 1,261 (+16.5%); 54% of section headers carry wrong open-box counts |

The 07-29 numbers were a *starting hypothesis*; today's are strictly worse, and two of the
07-29 "verified" claims were false at the moment of writing. **Line-number refs are
structurally unmaintainable at this churn rate** — the queue's own caveat ("line numbers are a
hint, task text is the identity") is defeated by its own `blocker` column, which is what a
coordinator screens on.

### B-2. Template-row corruption — confirmed, under-reported at least twice, ONE still live

Git history proves the corruption class directly: `72d27f39` flipped "Run GEAK-family
freshness sweep **at each audit**" to `[x]` — *deleting the words "at each audit" in the same
hunk*; `3e82267e` breached an already-banner-guarded checklist 1 h 54 m after the guard was
placed; four `model-stack-change` boxes flipped **2026-07-14** (pre-dating the sweep entirely)
were found only today; each successive pass found more than the last.

**Surviving corruption, verified on my thread at ~09:30Z, post-repair:**
`handoffs/active/model-stack-single-source-update-pipeline.md` § Outstanding Work — the
`- [x] Treat scripts.benchmark.seeding_rewards, … as re-audited surfaces … Do not churn them
unless a concrete duplicated live fact reappears. ✅ 2026-07-29` box is **still flipped**. It
is a continuous imperative plus a standing condition — the exact tell the section's own banner
defines. It survived because the banner enumerates "THESE SIX BOXES" and this is the
un-enumerated SEVENTH standing constraint; mainC's repair tooling (`section_is_guarded`) reads
the box-scoped banner as section-scoped and exempted it — **a guard passed by the very thing
it was built to catch** ("can I pass this guard by deleting/not-being what it inspects" —
yes: by not being enumerated). Compounding: queue row L1039 annotates this constraint
"**CLOSED 2026-07-29**" — a standing keep-unchurned rule cannot be closed. The banner's own
queue-row citations (`:353`/`:355`) are also rotted (actual: `:350`/`:352`).

Second surviving case, different failure mode: `agentic-rocm-kernel-authoring.md`'s
GEAK-freshness template box was **consumed, not restored** — the standing step survives only
as prose (L148) with no checkbox tracking; the queue's TOP-40 #8 anchor is dead.

**CORRECTED 09:53Z by mainD's C41 fix** (`msg-20260811T095317Z-184-mainD`), accepted: my
"un-enumerated seventh box" mechanism was WRONG — the banner's count is right (the section
holds exactly SIX open boxes, all enumerated, plus THREE closed: L339/357/361). L339 was not
exempted by a banner-enumeration gap; it is a **checkbox-state question on a closed box**,
owned by the file owner (mainC), which the synthesis below already covers. The guard-scope
defect itself was real and is FIXED (`section_is_guarded` → `box_is_guarded`, 45 tests, corpus
43→39 guarded with nothing newly guarded). What survives of my claim: a standing constraint
inside a `[x]` box is invisible as an active rule — that loss-mode stands regardless of guard
semantics.

**Loss-mode now mechanically detectable (10:00Z):** mainD added
`backlog_row_check.py --audit-guards` (`a17ba974`, 54 tests) — any `[x]` under a DO-NOT-FLIP
banner prints as a review prompt, closing the blind spot that `box_is_guarded` (a dispatch
check) can only ever speak about open boxes. Verified on my thread: 3 hits corpus-wide, L339
first, framed as REVIEW not verdict. Adjudication of the hits remains with mainC.

**Adjudication conflict, recorded 09:23Z** (`msg-20260811T092254Z-131-mainC`): mainC, as
repairing owner, adjudicated the `:339` box a *legitimate completed task* (the re-audit half
did complete). My refined position, sent to mainC: **both halves are real** — the box records
a genuine completed re-audit AND carries a standing constraint ("Do not churn them unless…")
that a `[x]` renders invisible as an active rule, the same loss-mode as the consumed
GEAK box. Recommended synthesis, owner's call: keep the `[x]` completion record but extract
the do-not-churn constraint into its own unchecked constraint line (or add it to the banner's
enumeration, which currently stops at six and is why every tool pass exempts it). The queue
row L1039 marking the standing constraint "CLOSED" is wrong under either reading.

### B-3. The queue still offers 19 template steps as READY

34 rows point into banner-guarded template sections; **19 carry `blocker = -`**; only ONE
carries the `TEMPLATE — DO NOT DISPATCH` annotation that `msg-20260729T160627Z` requested
13 days ago — including the exact row that message named (`model-stack-change-…:230`). The
tell inverts in both directions: benign heading over standing constraints
(`model-stack-single-source`), and warning heading over rows whose blocker COLUMN still reads
READY (`integration-test-coverage`).

### B-4. Backlog leak found during re-derivation

`routing-and-optimization-index.md:652-653` went out-of-range in the 08-10 index restructure;
the P1 successor work survives **only as prose** in `learned-routing-controller.md:1464-1466`
with no open checkbox owning it anywhere. Routed to coordinator for ownership assignment.

### B-5. Caveats (carried from evidence, not resolved)

The tree moved during measurement (mainC's 09:22Z commits); anchor-vs-substantive tie-break
for prose-under-`[x]` reported both ways; `repo-readiness-scorer.md:415` BLOCKED is a
judgment call (blocker is the v9 freeze contract, not row text); true ALREADY-CLOSED share is
a lower bound (prose-completions not audited); 7 queue rows belonging to two
moved-to-completed handoffs not traced into successors.

## C. Stale-by-v9 sweep

Sweep of all three repos for surfaces still assuming v8 (`67a433bf4`, binary 10107) as CURRENT
after the 08-11 v9 freeze (`0db32c06e`, 10125). v8-as-rollback references excluded by design.
Load-bearing claims re-verified on my thread (era state, Annex G, verifier, shadow-lane
constants, cert registry).

### C-1. OPERATOR-SIGNATURE ITEMS — surfaced immediately, bypass the saturation gate

> **RESOLVED INTO TOKENS 2026-08-11 (coordinator assignment `consolidated-era-and-annexg-token`):**
> both items are now authored, pre-validated, unsigned amendment vehicles committed as `75a722c6`
> — `ratify_consolidated_era_rows_20260811.sh` (four era rows, per-row strike, 59/59 suite
> evidence) and `ratify_annexg_v9_currency_20260811.sh` (two parentheticals, sha-pinned).
> Token blocks: `msg-20260811T094705Z-154/-155-auditor`. Awaiting operator signature.

1. **No cpu_bench era row exists for v9.** `orchestration/autopilot_state.json`
   `active_instrument_eras.cpu_bench = "E8-cpu-kernel"` (verified) while production has run v9
   since today's freeze — the era registry (`instrument_eras.yaml`, 31 ids, newest E16 dated
   08-10) was never advanced for the kernel cutover. **Every CPU bench stamped since the freeze
   inherits a wrong era** — the exact `ERA_CPU_KERNEL=E6` manifest failure shape, recurring at
   fleet scale, and the single highest-leverage upstream cause of the v8-pin debt below. This
   folds into the consolidated era-row token (D4), which is now a FOUR-item package:
   v9 cpu-kernel row · `E9-routing-reward` · mainA's `E5-THROTTLE-SCOPE-ERA-ROW-20260729` ·
   the seeding-scorer era label.
2. **Ratified Annex G pins "currently v8".** `measurement/protocols/gpu-cross-device.md:17-18`
   (ratified 20260730T103218Z, amended `759843d8`): P-GPU-1 decision-grade claims "MAY ONLY be
   produced on a production-named kernel (`production-consolidated-vN`; currently v8
   `67a433bf4`)". Human-amendment-only. While the parenthetical is stale, the P-GPU-1 claim
   class on v9 is formally ambiguous — **urgent because AutoKernel is mid-rollout and P-GPU-1
   gates its claim class.**

### C-2. Gates/constants that would reject or mis-handle the v9 binary (owner triage)

- **gpu_shadow_lane family** (orch): `gpu_shadow_lane.py:51-52` pins `10107`/`67a433bf4`
  (verified); consumed as hard preflight blockers in `gpu_shadow_lane_preflight.py:357,360` and
  `gpu_shadow_lane_stage0.py:332-333`; `gpu_shadow_lane_tenancy.yaml:48-50` pins the same.
  Feature-flagged off today, blocks on first enable under v9.
- **`reasoning_effort_certifications.yaml:4`** `active_kernel_era: production-consolidated-v8`
  (verified). Dormant only because `role_certifications: {}` is empty — the first cert recorded
  under v9 mismatches via `validate/reasoning_effort_certifications.py:147`.
- **Reusable research runners fail-closed on v8** (research repo): `laguna_q4_cpu_bench_runner.py:57-59`,
  `laguna_iq2_mi210_kv_sweep.py:36,38`, `fg4b_a4_cpu_evidence_importer.py:33-34`,
  `fg4b_a4_cpu_optimized_reanchor.py:58-59`; `validate_model_tensors.sh:37` defaults
  `PROD_VERSION=10107` and **silently prefers** a v8 build when both exist (mis-prefer, not
  crash).
- **Ambiguous-status, owner must retire-or-repin** (flagged, not judged closed):
  `run_e8_quality_baseline_reseed.py` (still named by SS-BENCH-GATE; likely superseded by the
  08-10 v10 multi-tier baseline path but never marked retired), `rearm_e8_autopilot_20260726.sh`
  (no receipt → unexecuted; AutoPilot since restarted by other means), the two DFlash
  observation runners (DFlash now ships IN v9; pre-promotion tools plausibly moot).

### C-3. Live docs / open next-actions instructing "start from v8"

Following any of these literally now violates the four-step kernel workflow (step 1: pull
*current* production tip): `cpu-shape-specialized-gemv-decode.md:735` (open box),
`qwen-mtp-llamacpp-port.md:47,91-92` ("Current state" section feeding open P6b/P7 items),
`numa-topology-cutover-resume-20260730.md:1006-1007` (open box),
`docs/reference/architect-bench-runbook.md:47` (SOP worked example),
`docs/reference/model-probe-scoreboard.md:1,4-5` (self-described "living scoreboard" asserting
v8 as current).

### C-4. Known / report-only

- `e5_cell_manifests.py:76` `ERA_CPU_KERNEL = "E6-cpu-kernel"` — confirmed still present, now
  TWO generations stale (E6=v7 → E8=v8 → v9 unrowed), 208/208 manifests carry it,
  `validate_cell_manifest` rejects hand-corrections. NOT repaired, per standing instruction.
- Sibling `e5_cell_manifests.py:77` `ERA_EVAL_INSTRUMENT = "E7-eval-instrument"` — same
  append-only-drift pattern, but semantically tracks pool/scorer identity and no later era
  describes a pool rebuild, so staleness is NOT asserted; owner awareness only.

### C-5. Verified clean (absence evidenced, not assumed)

`scripts/session/verify_llama_cpp.sh` **enforces v9** (branch/commit/version-line pins verified
on my thread — the gate the brief worried about is correct). `verify_speech_kernels.sh`
independent of the llama freeze, correct. `MEASUREMENT.md` core, `agents/**`, `scripts/nightshift/`,
protocol annexes other than Annex G: zero stale hits. **Phantom era ids: none in live code** —
`E8-eval-instrument` has 0 code occurrences (prose-about-the-trap and one synthetic test fixture
only); no invented era id in either repo diffs against the 31 authoritative registry ids.
AutoKernel already self-defends: its harness refused a stale-instrument receipt post-freeze
(`data/autokernel_controls_3pct_20260811_v9_hardened_instrument_receipt_refused/`).

---

## FINAL RECONCILIATION — 2026-08-11 22:30Z (post-restart; sections B and D closed)

**D — decision package for the last open item (authored 23:10Z, unowned since inference's
hand-off; for operator via coordinator):** *What to do with the never-executed E8 final-c1
retry (P0-1).* Evidence: the ratified retry aborted `no_admission` 9 min post-signature and
never ran; its own instrument pins REFUSE v9 (`FROZEN_V8` asserts); the v10 multitier baseline
(ratified 08-10, E16 rows sealed, autopilot state advanced) already superseded the E8 baseline
as AutoPilot's gate; race rows are retained immutable. **Option A (recommended) — RETIRE:**
close P0-1 as superseded-by-v10-multitier; mark the E8 record terminal-partial by design;
retire `run_e8_quality_baseline_reseed.py`, `ratify_and_apply_e8_quality_baseline_v4` (the
conformance check's standing residual), and `rearm_e8_autopilot` as superseded artifacts. Cost:
E8 baseline stays documented-incomplete. **Option B — deterministic completion only:** no
inference, finalize from persisted outputs; already known-blocked (the scoring-replay validator
rejects the historical judge trace, inference 07-30). **Option C — re-run under v9 as a new
protocol:** cross-era by construction, duplicates multitier, spends compute inference owns.
A over B over C.

**D — every token thread terminal:** P-BENCH-4-affinity and E8-capacityfix SPENT (07-29);
E9-ROUTING-REWARD and E5-THROTTLE satisfied by FOLDING into the consolidated token (signed
21:35Z); Annex G signed 21:34Z; era-advance signed 22:15Z and its consumer chain verified
(state field E9, receipt sha match, dashboard reads per-request — live-on-next-request, no
process caches it). **Sole remaining D item, now UNOWNED and routed to coordinator:** the E8
final-c1 cross-era decision package (and the e8-v4 ratifier retire-or-repin) — inference
handed both off ("unrelated to current AutoKernel scope"); they need an owner assigned.

**B — queue story terminal:** `BACKLOG-DISPATCH-QUEUE.md` carries a SUPERSEDED / DO-NOT-DISPATCH
banner; `backlog_queue_gen.py --generate` (text-keyed) is the replacement — the structural
recommendation adopted and built same-day. L339 resolved by its owner (`8ec84f67`, banner
SEVEN); queue row L1039 is **moot** (a row in a superseded file). `--audit-guards` covers the
flipped-constraint class going forward. C18(a) is a packaged one-word operator decision
sitting in the thin-dispatcher (§L800-802), coordinator's to present.

**Daemon restart verification (pid 496387 → 921178 at 22:18:12Z) — all five gaps LIVE, proven
by consumers not files:** C39 fired five `looks-spent` defect notices into the coordinator
inbox at 22:18:14 — one per receipted gate in the queue, including the era-advance signed
three minutes earlier; no gate re-appended (1 block each). C28/C38: `relay_state.json` EXISTS
(the mirror of mainD's absence-proof), fresh mtime, 641 flagged / 8 delivered and growing.
R1 (autonomous wake path) live by the same restart. **CORRECTION (22:45Z, from the
tonight-commits audit): R2's daemon-side check is NOT live** — `48ad4dfb` landed 22:21:25Z,
three minutes AFTER the restart, so pid 921178 predates it. Four gaps live, not five; R2
enforces as CLI (returns CLEAN, correctly) and its tick-path half awaits the next restart.
No false claim by mainD (its wrap-up worded the verification as repo-state, not
daemon-state); the over-claim was mine and is corrected here.

### Tonight-commits audit (22 root + 1 orchestrator since 22:00Z) — folded 22:45Z

20 of 23 verified state 1, including: the operator's "26 green stale-override tests"
reconciled exactly; mainD's archive-sweep recovery verified **byte-exact zero-loss** (the
aborted commit's snapshot of every live outbox is an exact prefix of the current file; the
"13 swept files" premise corrects to 14 unrelated live-file diffs over the same 24 archives);
mainA's Token 2 Block A queued additive and unsigned; every sha in mainB's progress entry
resolves. Findings:

1. **`48ad4dfb` state 2** — R2 daemon-side check committed post-restart (above).
2. **`b41af9d7` mislabeled / `c384c4a8` dangling citation** — the R1 nudge-guard fix landed
   under a verbatim copy of an UNRELATED commit's message ("A16+A18 gepa framing") after an
   amend, with 31 index-regeneration files riding along; the handoff and progress log cite
   `b1222b6e`, which is a **dangling commit unreachable from any clone**. The fix is real;
   the audit trail is broken in both directions (cited sha unresolvable; real sha's subject
   describes different work). Third sweep-class incident today, same root (`--amend` on a
   shared index). Repair routed to mainD: correct the two citations b1222b6e→b41af9d7 with
   an explanatory note — history is pushed, so a documentary correction, not a rewrite.
3. `43108014` (mainB, orch) — "75 passed across every consumer" not reconstructable (41
   narrow / 131 broad); code and 8/8 new tests verified real. Citation-precision note
   routed.

## Self-referential closure

The audit standard applies to the auditor: the 07-29 auditor session's own deliverables —
`artifacts/audit/checkbox-flips-20260729.md` and `artifacts/audit/c-series-code-audit-20260729.md` —
were **untracked** (state 3, never committed on any ref) until this audit's commit, the same
defect flagged against mainC's evidence doc in Section A. Both are committed alongside this
report. (`artifacts/audit/gpu-activation-critical-path.md` and `untracked-backup-20260729/`
remain untracked deliberately — not auditor lineage, ownership unestablished; flagged to
coordinator rather than committed.)

## Post-signature verification addendum — 2026-08-11 ~21:45Z (operator standing directive)

**Both tokens signed at 21:34:50Z (Annex G) and 21:35:01Z (era rows), directly from the 09:47
token blocks.** The coordinator's P0 "deliver both commands" reprioritize (21:34:22Z) crossed
the signing by ~30 seconds — stood down with receipts as evidence (receipts-on-disk outrank
bus messages, the D5 rule applied live; `msg-…-167-auditor`).

### Signature integrity — all verified

- Both keyed receipt indexes exist with `indexed_by: "attest"` — written by the ratifiers'
  own attest paths. **The C39 authoring contract worked on its first live use.**
- Era token: all FOUR rows applied, none struck; live `instrument_eras.yaml` sha256 is
  **byte-identical** to the receipt's `target_sha256_after` (`08a1b93b…`) — applied exactly as
  validated, no churn since.
- Annex G: both currency sites (line 17-18 and 167-168) read `currently v9 0db32c06e`;
  amended file sha equals the pre-validated candidate `d60f4129…` exactly. **P-GPU-1
  decision-grade claim class on v9 is textually unambiguous as of 21:34:50Z.** D-series items
  D3/D4 and C-1 items 1–2: **CLOSED.**

### Consumer states (the "is it live" half)

| Consumer | State | Note |
|---|---|---|
| Registry-deriving readers (newest `from` ≤ now per scope) | **LIVE** | derive `E9-cpu-kernel` from the amended file directly |
| `autopilot_state.json` `active_instrument_eras.cpu_bench` | **STILL `E8-cpu-kernel` — mechanism gap CONFIRMED** | **Nothing is wired to advance it.** v8 precedent (`ratify_v8_era_fence_20260725.sh`) wrote registry+state atomically; no v9 analogue exists; the v10 multitier seal passes `cpu_bench` through unchanged (`dict(...)` shallow copy); no code derives cpu_bench from the registry at runtime. Downstream: dashboard Pareto endpoint (`dashboard.py:~5539`) reports E8 against a signed registry saying E9. **Closure authored**: `ratify_v9_cpu_bench_era_advance_20260811.sh` (`e31fba9f`, dry-run exit 0, single-field, receipt-chained) — token block `msg-…-168-auditor`, awaiting signature |
| AutoKernel interim output (freeze → 21:34:50Z) | re-stampable | coordinator's interim posture lifts; re-stamp action sits with inference |
| `e5_cell_manifests.py` `ERA_CPU_KERNEL`/validator | unchanged by design | mainA Token 2 territory (schema + four-constant repair, gated) |

### Known property handed forward (mainA, 22:07Z): cpu_bench scope collision

The signed consolidated token records an ELIGIBILITY boundary (`E8-cpu-bench-throttle-scope`)
in the same scope as the kernel-cutover rows — so `derive_era(cpu_bench, t)` for
t ∈ 2026-07-29..2026-08-10 returns the throttle row, not `E8-cpu-kernel`. Not an authoring
defect (the row was always `scope: cpu_bench` per the 07-29 operator ruling that gate semantics
are part of the instrument) but a semantic property every future cpu_bench derivation must
handle: kernel-identity queries must filter by row kind, not scope alone. Owned by mainA's
Token 2 (structured `binary_version`/kind schema); recorded in
`batched-decode-measurement.md` and the A7 package banner. My era-advance ratifier is
unaffected (literal field write, no derivation).

### Item 4 — C39 re-presentation check

Structural: **no duplicate gate blocks** in `token-queue.md` (string-dedupe held even pre-C39).
Live annotation: **blocked on the daemon restart** — pid 496387 unchanged since 08:48, so the
queue currently presents FIVE unchecked gates of which **all five are phantoms**: two spent
07-29, two signed tonight, and `RATIFY-E9-ROUTING-REWARD-ERA-20260729` **superseded** by the
consolidated token (its row content landed inside it). The superseded one has no keyed receipt,
so even post-restart C39 cannot annotate it — the queue owner (mainC) should mark it
SUPERSEDED-BY `RATIFY-CONSOLIDATED-ERA-ROWS-20260811`; suggestion filed to mainD for a
`status: superseded` index form.

### Signed-but-untracked closure (found during item 1)

Both operator-signed amendments sat **applied but uncommitted** — the exact tree-restore loss
class this audit documented this morning. Closed: root signature artifacts committed as
`cd58ba75` (annex + 2 receipts + 2 keyed indexes), orchestrator registry amendment as
`53fc3250` (live sha verified = receipt `target_sha256_after` before committing).

### Item 3 — same-day commit audit (29 root + 4 orchestrator)

**Orchestrator (4 commits, all verified state 1):** `78257261` (stack_topology re-attribution,
comment-only, claim==diff), `872bc851` (stack_numa rationale correction; claimed 19 tests
re-run by the auditing agent: 19 passed exact), `f4230b22` (NUMA_NODE0/1 deletion; AST-verified
**zero code references remain**, all survivors prose; no running process to be stale against),
`5f08875a` (test fixture; claimed 76 tests re-run: 76 passed exact). The
`test_specific_role_urls` failure is **confirmed pre-existing and disjoint** from today's
commits — root cause is `stack_priors.yaml` regenerated at 01:36Z faithfully recording a
halves-only launch with no frontdoor `:8070` full instance (the 2026-07-23 dropped-ports
regression class, independently reproduced by mainB, already filed). Also noted: **no**
autopilot/instrument commit exists today in orchestrator — the era amendment was signed
tonight and committed by this audit (`53fc3250`); and `scripts/autopilot/system_card.md` is
stale on BOTH era fields (generated artifact, regeneration → autopilot resume checklist).

**Root (48 commits — the day ran past the brief's 29; 12 landed during the audit itself):**
45 verified state 1 (including test-count claims *re-run*, orchestrator cross-citations
resolved, and the operator's freeze-sha byte-checked). Findings:

1. **HEADLINE — `2e01d5dd` + `b763112e` (C28/C38): undisclosed committed-not-live on the
   daemon tick path.** `load_relay_state`/`save_relay_state` called at
   `session_bus_coordinator.py:2449/2604` inside the relay tick; daemon pid 496387 unrestarted
   since 08:48. Unlike the same author's exemplary C39 disclosure, **no "NOT YET LIVE" caveat
   exists anywhere** (verified: one such string in the whole handoff, C39's), and the C28 box is
   `[x]` closed with before/after numbers while the live daemon still burns ~29.5% of a core
   re-parsing 1 GB of advisory.jsonl per 45 s tick and remains C28-vulnerable. The exact
   pattern this audit was commissioned to find. Routed to mainD (annotate, owner flips);
   restart urgency to coordinator now covers C39 **and** C28/C38.
2. **My own `ebce92a2` was 3-adjacent** — three receipt-index pointers asserted `ratified`
   over receipts that existed only on disk (untracked since 07-29); my conformance check
   only stat'ed the filesystem. **Closed**: receipts committed (`ea2c8381`), check extended to
   verify git-tracking of every index target (`2b60bbba`). Filesystem presence is not
   provenance.
3. `a17ba974` (mainD) claims "54 tests"; actual collected count is **47** (sequence 37→45→47
   reconstructed; feature itself real and wired). Citation defect routed to mainD for the
   handoff record.
4. **L339 finally resolved my way, by its owner**: `8ec84f67` (mainC, 21:49Z) reversed its
   own adjudication ("C41's docstring had it right"), restored the box to open, and corrected
   the banner SIX→SEVEN — the banner was the document defect after all. The loss-mode claim
   survived every layer of this exchange; the two-step correction trail above stands as
   history, not error.
5. `c629b33b` broke "Parent index" links across ~34 handoffs (bad global replace);
   self-corrected one minute later by `1317060a`; clean at HEAD. Recorded as an instance of
   the author-side-unvalidated-change class, no action.

## Bus filings

- Item D findings → coordinator-agent: `msg-20260811T090716Z-138-auditor`
  (`action_required: true`, `needs_routing_to: ["coordinator-agent"]`).
- Triage dispositions (mainA NUMA retraction + VOID R1-R4): `msg-20260811T090739Z-139-auditor`,
  `msg-20260811T090739Z-140-auditor`.
- Section A findings → coordinator/mainD/mainC/inference: `msg-20260811T092037Z-141-auditor`.
- Section C findings incl. the two operator-signature items → coordinator/inference:
  `msg-20260811T092219Z-142-auditor`.
- Section B findings + audit completion → coordinator/mainC (incl. the live surviving
  template corruption): `msg-20260811T093054Z-143-auditor`.
