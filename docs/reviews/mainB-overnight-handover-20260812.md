# `mainB` — overnight handover, 2026-08-11 → 2026-08-12

**Lane**: orchestrator correctness (sequential). **Compute used: none** — no inference, no benchmarks,
no model servers, no region claims, no signing vehicle. Unit tests and file/git reads only.
**Written**: 03:2xZ, blocked on the merge, not idle.
**Not written to**: the three frozen paths (`progress/2026-08/2026-08-12.md`,
`handoffs/active/tool-output-compression.md`, `handoffs/active/intake-derived-work-2026-07-25.md`).

---

## 1. Finished — verifiable list

Every hash below was read back from `git log`, not from memory. Repo in brackets.

| Hash | Repo | What |
|---|---|---|
| `a4e398fc` | orch | **HS-OD-2**: `/v1/chat/completions` returned backend failures as HTTP 200 assistant text. Every eval fan-out through `:8000` had been scoring outages as low-quality generations. Now 502 / propagated `HTTPException` / propagated `ContentionDenied`; streaming path fixed too (3 further sites the finding never named). |
| `f8479a72` | root | HS-OD-2 closed with scope note. |
| `2c421c1c` | orch | **`start --validate-only` was declared and never read** — a documented dry-run flag that launched production instead. Wired, before dispatch. |
| `2821937c` | orch | Hoisted `--validate-only` above the bench guard (residual found by `mainA`). |
| `f2ad030e` | orch | **SEQ-A detector fixed**: it compared a JOINT verdict against a single-axis threshold and reported the mismatch as staleness. Now attributes per axis: 6 quality-refuted, 3 rate-refuted-only, **0 unexplained**. |
| `43108014` | orch | SEQ-A0 — refuted-stickiness as an explicit policy flag, **default OFF**, seq-v1 byte-for-byte. |
| `46f9eacd` | orch | REL-1 measurement guards unified into one module (equivalence proved by AST **before** the move). |
| `48a685f0` | orch | `expected_stack_services` fail-open made LOUD (both silent paths were `logger.debug`). |
| `98ed5c5f` | orch | E8-PANELS-a — frontier-rerun counters kept current on the OPEN marker. |
| `f4230b22` | orch | Deleted `NUMA_NODE0`/`NUMA_NODE1` — a shape that could not be used correctly (import-time `AssertionError` was its only reachable effect). |
| `5f08875a` | orch | `retrieval_compaction` fixture drift. |
| `78257261` | orch | 12.19 t/s record re-attributed to `architect_critic`, append-only. |
| `7dddce0f` | research | `ingest_long_context` baseline/optimized tps recorded as carrying **no** context length — a provenance gap stated, not back-filled. |
| `6af15249` | root | **`docs/guides/agent-workflows/verification-failure-catalogue.md`** — eight measured ways a check passes for the wrong reason. |
| `3c7edafc` | root | **P0-0 filed** — the dropped-full-instances defect, which existed only in bus traffic until then. |
| `7f840404` | root | E8-PANELS-c — the hub surfaces existed; the guard protecting them was vacuous. |
| `d060df9e`, `cd01cb5d` | root | A11 §5 precondition verified FALSE (row parked); residual filed out of scope with reasons. |
| `b57cef39` | root | SC19 — belief-kernel write-side wiring filed against my own A14 change. |
| `17fc2e1b` | root | Shared-file class as one durable note. |

**Merge (P0)**: seven paths resolved by union and staged, then `progress/2026-08/2026-08-12.md`
unioned and staged (2020 lines, 0 markers). Verified at content level three times, against three
different planes — working tree, index, and commit `66f40eeb`. Zero lines lost from either side.

**Parked, not landed**: **A14** (`GateDecision` echo) on branch `a14-gatedecision-echo` @ `a7d7bdb6`
— merge-gate verdict AUTONOMOUS, 6 files, +299/-0, 9 tests. **Cherry-pick, not `--ff-only`** (main
advanced past the branch point), and run the gate with a **three-dot** range.

---

## 2. Found without being asked — the most valuable output

1. **`start --validate-only` launched production.** Filed by `mainA`, fixed by me. Not a stale flag —
   an *anti-guard*: a documented dry-run affordance that did the opposite of what it advertised, so
   it manufactured the confidence to run the command. `mainA` was about to run it under lane `none`.
2. **The SEQ-A "sticky refuted label" finding was an artifact**, and an operator decision (Horn A) had
   already been taken on it. The detector compared a joint verdict to a single-axis threshold; the
   rate axis refutes for essentially every candidate (`E_rate` max 1.11 vs `budget_min_e` 2.0). I
   refused to implement, and the corrected detector shows **0 unexplained** across 393 trials. Doing
   as instructed would have silently answered SEQ-B1, a *different* human-amendment-only question.
3. **P0-0** — derived `stack_priors.yaml` had dropped the `NUMA_FULL` instance of **every**
   quarterable fleet (8070/8072/8085), so a HALF is advertised as the full instance: a region-lock
   *scope* error. Same triplet the operator ruled "accidental and clearly a mistake" on 2026-07-23.
4. **Nine distinct ways a check passes for the wrong reason**, from five agents in one night, now one
   citable artifact. Probably the most reusable thing produced. (The ninth is mine and was caught by
   the `auditor` in this very handover: my hash-verification pass resolved root hashes against the
   orchestrator repo — right key, wrong universe — and reported eight valid commits as BAD.)
5. **Two rows were confounded, not defects** — the manifest "empty lineup" and the priors state were
   *faithful records of a degraded reality*, indistinguishable from corruption unless you check what
   was running when they were written. Several pre-reboot rows may be describing the outage.
6. **Stale claims were invisible locks.** A 14-day-old claim from a dead session blocked a row in my
   own lane; flagging it led `mainC` to ship claim-age marking and `inference` to release five.

---

## 3. What I got wrong, and who caught it

Preserved deliberately: **four mains and the coordinator each made a real error tonight, and every
one was caught by someone else.** That is the finding.

| My error | Caught by | Mechanism |
|---|---|---|
| Merge union built from a **stale snapshot** — would have dropped 31 sections including six of my own | `mainA`, who warned **twice** | Worktree HEAD was main *at worktree creation*; mains kept committing. |
| The verification of that union was **vacuous and passed** | myself, on an absurd number | Read `:3` after `git add`, which collapses stages → empty side → every set/substring test trivially true. |
| Re-derived the refused-row set from the schema; empty allow-set flagged **all 220** rows | myself, on the absurd number again | Same family, second instance in one night. |
| Wrote a **circular** test — simulated the dispatch branch instead of exercising `main()` | myself, before commit | Would have passed against the broken build. |
| `aa03f0e0`'s message described a handoff note its edit had **not applied** | myself, next read | Edit and announcement written in the same breath; the announcement lands even if the edit fails. |
| Index line said "eight faces" while the entry edit failed on a stale anchor | myself, on the assertion | Same shape, third instance. |
| Recorded `mainA`'s third sign with the **wrong mechanism** | the `auditor`'s own retraction | I wrote "the fix landed 34s earlier"; truth was they grepped my *uncommitted* work — the fix wasn't committed for another 20s. |
| My batch-8 section filed under `mainA`'s heading | `mainA`'s finding, applied to myself | `cat >>` at EOF re-parents to whoever wrote a `##` last. |
| Attributed a heading-count disclosure to `mainD` | `mainD` asked me to check | Checked; it was the coordinator's. Their instinct was right even though the finding was negative. |

**The pattern worth keeping:** every one of these was silent-by-construction. None failed loudly; all
were caught by someone reading the *artifact* rather than the *report*, or by a number too clean to
be true. That is why the catalogue is keyed on the diff rather than on intent.

---

## 4. Open in my lane, with the specific next action

| Item | State | Next action | Owner |
|---|---|---|---|
| **A4** — E8 frozen-kernel pin | Blocked on ONE command | `git -C /mnt/raid0/llm/llama.cpp worktree add --detach /mnt/raid0/llm/llama.cpp-v8-e8 67a433bf45a8a091d83b4ea0b32ff0735fd51800`, then ~10 min of mine (one constant at `run_e8_quality_baseline_reseed.py:81` + era note) | `inference` / operator |
| **A14** — GateDecision echo | Coded, tested, parked | **Cherry-pick `a7d7bdb6`** (NOT `--ff-only`); needs a window clear of any live calibration run. Land the SC19 write-side hook *with* it — unmerged is the only cheap moment | coordinator + `inference` |
| **P0-0** — priors dropped every full | Filed, compute-blocked | Relaunch `--numa-mode both`, recompile priors. **Standing prediction: all 7 red tests go green with ZERO test edits**; if any still fails it is a real test defect and mine | `inference` |
| **T8** — handoff half | Registry half done | 7 unqualified `ingest_long_context` tok/s quotes across 5 other owners' handoffs, listed on the row. Route to them or authorise me | coordinator |
| **W4** — `migration_status` field | Sized, not applied | One word from the coordinator and I apply it to `stack_change_surface_manifest.yaml` | coordinator |
| Deferred progress append | Held in scratch | `scratchpad/mainB-DEFERRED-progress-append.md` — insert under my own `##`, container-check, diff-check, then verify with `git show <sha>:<path>` | me, on freeze lift |

**Declined with reasons — do not re-issue without new information:** `vram_fit` admission gate
(unratified rider Q3); C1 fix #2 (confounded by a down stack — *may now be checkable*); C1 fix #3 and
E8-PANELS-b (other owners); session-bus schema alignment (`mainD`); `debug_scorer` pre-B7
(human-amendment-only); `model-stack:628` (the tool now correctly refuses it).

---

## 5. NEEDS THE OPERATOR

Flagged for the single package. Nothing here is actionable by an agent.

1. **A4 worktree command** (above). A sandbox classifier refuses it to me because it targets the
   frozen production kernel tree — correctly. It creates a *new* directory and a detached checkout;
   it does not modify, rebase, build, commit to, or move the branch of the v9 tree, and nine
   worktrees already exist off that repo. **Blocks the E8 provenance guard, which is currently red
   for the right reason and must not be closed by loosening it.**
2. **SEQ-B1 — joint gate vs quality-primary.** The real question behind SEQ-A. Its own text: *"under a
   joint gate, a candidate that buys quality with throughput can never be promoted — which may be
   exactly what you want."* Three candidates (`70902e4b` E=11.55, `dd793a6e` 8.70, `85c3dcf2` 2.74)
   are **the entire population** of that case: 6 others fail on quality and would be excluded under
   any policy, and **0** are excluded by mistake. Human-amendment-only.
3. **E8 frozen-kernel era** — Option A already chosen (pin E8 to a v8 worktree). Needs (1) to execute.
   Re-pinning to v9 instead would re-base a measurement era.
   **⚠ Disambiguation (flagged by the `auditor`, and worth doing before the package is assembled):**
   this is **not** the same as their morning-note "E8 final-c1" item, which is about retiring the
   unspent 2026-07-27 quality-baseline **apply token**. Two different E8 items, adjacent names,
   different decisions — mine is an *instrument pin*, theirs is a *token retirement*. Do not merge
   them into one line.
4. **P0-0 is a recurrence**, not a fresh bug: 8070/8072/8085 is the exact triplet ruled on 2026-07-23.
   Worth knowing it came back.

---

## 6. One process note

`mainC` observed a loop worth keeping: I flagged a claim-hygiene issue → `mainC` swept and shipped
age-marking → `inference` released five stale claims → I worked the row that freed. **Four steps,
under an hour, no operator involvement.** The fleet self-corrected faster than it escalated, and
every error in §3 was caught the same way.
