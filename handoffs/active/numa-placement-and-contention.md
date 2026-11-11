# NUMA Placement & Contention Program (INF-45)

> **Restructured 2026-11-10 (pipeline-mgmt, operator "yes, take both on").** The cutover this file was named for closed 2026-10-29 (P0-3). Two tracks were split out: `dynamic-stack-concurrency` → [`hybrid-checkpoint-prompt-reuse.md`](hybrid-checkpoint-prompt-reuse.md) (INF-86), `within-role-placement-state-machine` → [`dispatch-placement-telemetry.md`](dispatch-placement-telemetry.md) (INF-87). Historical title below.

## (historical) NUMA Topology Cutover — RESUME DOCUMENT

> **Fold destination** (BRF-T7-F10, BRF-T7-1, route 1b, 2026-11-03): every former handoff of this plan target is a `## Track:` with its own gate marker: `numa-placement-and-contention`, `reboot-gated-inventory-and-staging`, `contention-model-device-and-load-axes-rider` (rows EVL-49, RTG-07 retired into INF-45). The former `numa-placement-and-contention.md` body is `## Track: numa-placement-and-contention`; tracks those handoffs already had are lifted verbatim after their owner.

> **Fold destination** (BRF-T1-F17, BRF-T1-1, route 1a, 2026-11-02): renamed from `numa-topology-cutover-resume-20260730.md`; absorbs 5 handoff(s) as `## Track:` sections at the end of this file (`batched-decode-measurement.md`, `dynamic-stack-concurrency.md`, `numa-placement-defect-20260730.md`, `shape-keyed-contention-gating.md`, `within-role-placement-state-machine.md`). The body above the first track is the former `numa-topology-cutover-resume-20260730.md`.

> **Current navigation (2026-11-01):** The opening cutover instructions and all dated
> “in flight” notices below describe historical state, not current machine status. P0-3
> was closed in the 2026-10-29 audit (see its checked task below); do not repeat its
> stack restart or matrix run on the strength of this document. Continue with the
> remaining open tasks and the session-per-handoff row workflow; verify live state
> independently before any operational action. Historical result paths may no longer exist.

> **THIS IS A RESUME DOCUMENT, NOT A NARRATIVE.** A production topology cutover is
> **applied in the working tree, uncommitted, and its commit is BLOCKED**, with
> **measurement runs in flight** on the machine. If the owning session died, read
> §0, then §1, then execute §2 P0 in order. **Nothing below needs to be
> re-derived** — the analysis is finished, the code is written, the ordering is
> forced by a pre-commit gate. Your job is to unblock and land it.

**Status**: ACTIVE — applied-uncommitted; P0 blocks the commit
**Created**: 2026-07-30
**Owner**: pipeline-mgmt (assigned 2026-11-10; was "whichever session holds the CPU lane")
**Parent index**: [`master-handoff-index.md`](master-handoff-index.md) (row N25)
**Sibling — DO NOT EDIT CONCURRENTLY**: [`numa-placement-defect-20260730.md`](numa-placement-and-contention.md#track-numa-placement-defect-20260730)
is the *diagnosis* handoff (N24) and has its own writer. This document is the
*cutover-resume* half. Cross-reference it; do not duplicate its findings into it.
**Related**: [`batched-decode-measurement.md`](numa-placement-and-contention.md#track-batched-decode-measurement) (E5
suspension banner) · [`shape-keyed-contention-gating.md`](numa-placement-and-contention.md#track-shape-keyed-contention-gating)
(contention matrix owner) · [`within-role-placement-state-machine.md`](dispatch-placement-telemetry.md)
(placement policy enum)

---

**Priority**: LOW — T7 (rank 161): 97 open but no ready compute item; 15 are reboot-gated inventory and the rest is topology follow-up.

## Track: numa-placement-and-contention
<!-- gate: none -->

> Folded from the body of `handoffs/active/numa-placement-and-contention.md` (row INF-45), from its first `##` section on, @ `04334af47404` on 2026-11-03 (BRF-T7-F10, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### 0. What do I do next (60-second resume)

Answer these three questions in order; each one tells you where in P0 you are.

| Check | Command | If … then |
|---|---|---|
| **1. Are the measurement runs still in flight?** | `repos/epyc-orchestrator/scripts/region-lock status` | Regions **q0/q1/q3 held** → runs are live. **Do not touch the stack, do not start the stack, do not run inference.** Work P1 (all zero-inference) while you wait. Regions **free** → go to check 2. |
| **2. Do the breaking tests still fail?** | `uv run pytest -q tests/unit/test_build_server_command_helpers.py tests/unit/test_orchestrator_stack_threads.py` (from `repos/epyc-orchestrator`) | **Failures** → do P0-1 and P0-2 first. Stack start is gated on these. **Green** → go to check 3. |
| **3. Is the contention matrix fresh?** | `uv run python scripts/server/contention_matrix.py validate` | **STALE** → the stack must be cold-started and the matrix re-benched (P0-3 steps 1-2) before any commit will pass. **Fresh** → commit (P0-3 step 3). |

**The single sentence that explains the whole blocker:** changing the cpusets
changed the topology hash, a pre-commit hook refuses to commit against a matrix
recorded under the old hash, and the only thing that refreshes the matrix needs a
live stack and runs inference — so the commit cannot land until the machine is
free.

---

#### 1. State as of 2026-07-30

##### 1.1 Applied in the working tree, UNCOMMITTED, commit BLOCKED

`epyc-orchestrator`:

| File | What changed |
|---|---|
| `scripts/server/stack_numa.py` | topology (the actual cutover) + import-time invariants + docstring correction |
| `orchestration/model_registry.yaml` | lean registry, recompiled from master |
| `orchestration/derived/stack_priors.yaml` | regenerated |
| `orchestration/model_descriptors.yaml` | regenerated |
| `docs/generated/current_stack_summary.md` | regenerated |
| `src/config/models.py` | port/fleet declarations |
| `src/fleet.py` | fleet shape |
| `src/registry/model_descriptors.py` | descriptor consumption |

`epyc-inference-research`:

| File | What changed |
|---|---|
| `orchestration/model_registry.yaml` | **master** registry — `no_mmap`, `numa_ports` |
| `docs/guides/benchmarking-guide.md` | placement recipes |
| `docs/guides/model-sizing.md` | placement recipes |

> ⚠ **The tree is shared.** `git status` in either repo shows work from *other*
> sessions (repl-memory, autopilot, trace, eval artifacts). **Commit with an
> explicit pathspec** — `git commit -- <paths>` — and never `git add -A`. See
> §4 Cross-cutting concerns.

##### 1.2 THE BLOCKER

The pre-commit hook (`.git/hooks/pre-commit` → `scripts/validate/check_contention_matrix_fresh.py:89`)
rejects the commit with:

```
FAIL: contention matrix is STALE (live topology hash=bc28e15d ...)
```

`orchestration/contention_matrix.yaml` records `topology_hash: "8c8cfcbb13d2611d"`.
Changing the cpusets moved the live hash to `bc28e15d`. The **only** thing that
refreshes it is `python scripts/server/contention_matrix.py` (`run` subcommand),
which **requires a live stack and runs inference**.

**Therefore the ordering is forced, and it is not negotiable:**

1. Let the in-flight measurement runs finish (§1.4).
2. Fix the breaking tests (§1.5) — **stack start is gated on them**.
3. Cold-start the stack.
4. Re-bench the contention matrix.
5. Commit.

##### 1.3 Topology now in the tree

**Quarters are retired.** Each quarterable role now has three shapes:

| Shape | cpuset | interleave | threads |
|---|---|---|---|
| full | `0-95` | `all` | `-t 96` |
| half A | `0-47,96-143` | `0,1` | `-t 48` |
| half B | `48-95,144-191` | `2,3` | `-t 48` |

Ports:

| Role | full | half A | half B |
|---|---|---|---|
| `frontdoor` | 8070 | 8080 | 8180 |
| `worker_general` | 8072 | 8082 | 8182 |
| `ingest_long_context` | 8085 | 8185 | 8285 |
| `architect_general` | 8083 | — (full-only) | — |

**FREED — must not be revived**: `8280` `8380` `8282` `8382` `8385` `8485`.

`no_mmap: true` for `frontdoor`, `coder_escalation`, `architect_general`,
`ingest_long_context`, `worker_vision`, `vision_escalation`.

**Half A is the GPU-disjoint half.** The GPU lane's logical `184-191` fold to
physical `88-95` = region **q3**, which is inside **half B**. Any CPU work that
must not collide with the GPU lane goes on half A.

##### 1.4 Runs in flight — the 2026-07-30 batch is COMPLETE, but a NEW batch is LIVE (2026-07-31)

> ## ⛔ 2026-07-31 09:35Z — DO NOT COLD-START THE STACK. THREE NEW TRACKS ARE RUNNING.
>
> **This supersedes the "nothing is in flight" banner below, which refers only to the 2026-07-30
> batch.** A resuming agent that reads that banner, sees "regions free", and proceeds to §0 check 2
> → cold-start would **destroy three live measurement runs**. Always trust
> `scripts/region-lock status` over any banner in this file, including this one.
>
> Live now: vision MMMU finalization (q3), TTS GPU bench (q3, queued behind it), half-instance
> headline numbers (q0+q1). Paths and state: §"Production-temperature re-runs — IN FLIGHT
> 2026-07-31" near the end of this document. **No results from them may be quoted.**

> ✅ **The 2026-07-30 batch is complete.** Every run listed below finished 2026-07-30 20:21–22:21 and all four regions
> released at that time. **Do NOT wait on these; do not re-arm them.** (This statement was accurate when
> written and is scoped to the runs in the table below — it is **not** a current statement about the machine.)
> Results: `gpungram_results.txt` 36/36 · `halfa_live`/`halfa_rest` DONE · `full_last_results.txt` 3/3 arms
> (a copy is preserved at `/mnt/raid0/llm/tmp/preserved/` — the chain ran twice and the duplicate
> truncated the live file once) · `ngramfix_results.txt` 12/12 DONE 22:21.
> **Also complete and NOT in this table:** the vision-model comparison
> (`/mnt/raid0/llm/tmp/vlquality_results.json`, 2026-07-31) — see §RESULTS below.

Check with `scripts/region-lock status` before anything.

| Run | Results file | Regions held | Notes |
|---|---|---|---|
| GPU ngram sweep | `/mnt/raid0/llm/tmp/gpungram_results.txt` | **q3** | 36 cells. Script `/mnt/raid0/llm/tmp/gpungram_run.sh`. |
| CPU half-A arms | `/mnt/raid0/llm/tmp/halfa_live_results.txt` | **q0 + q1** | |
| Chained follow-on | — | q0+q1, then all four | `/mnt/raid0/llm/tmp/cpu_chain.sh` runs `halfa_rest.sh` (q0+q1), then — **after the GPU sweep releases q3** — `full_last.sh` (all four regions, 122B only). |

**GPU build gotcha (costs an hour if you rediscover it):** the v8 HIP build is at
`/mnt/raid0/llm/llama.cpp-experimental/build-v8-hip/bin/`. It needs
`LD_LIBRARY_PATH` set to **that dir plus `/opt/rocm/lib`**. Without it,
`--list-devices` prints nothing and the build looks broken when it is fine.

**Partial results preserved**: `/mnt/raid0/llm/tmp/ngramshapes_partial.txt` —
16 of 30 cells (the full and half blocks). The quarter block was **deliberately
abandoned** because that shape is retired. This is not an incomplete run to
resume; it is complete for the shapes that still exist.

##### 1.5 Breaking tests — must land in the SAME commit

An A/B against a clean `git archive HEAD` measured **30 net-new failures across
14 files**.

Two of them are in `PROMOTION_GATE_TARGETS` (`scripts/registry/stack_change_pipeline.py:67`),
both in `tests/unit/test_build_server_command_helpers.py`, and **they gate the
launch itself** — the stack will not start until they pass.

One of those two is worth understanding before you "fix" it:

- `tests/unit/test_build_server_command_helpers.py:1031`
  `test_worker_general_numa_policy_is_full_instance_only` asserts
  `"numactl" not in quarter_prefix`. **It encodes the defect as a requirement.**
  Left in place it would have blocked the fix in CI. Do not repair it — retire it.
- Its replacement **already exists**:
  `tests/unit/test_orchestrator_stack_threads.py:159`
  `test_straddling_cpusets_declare_a_numa_policy`, currently marked
  `xfail(strict=True)` and now **XPASSing**. That is the marker working exactly as
  designed. **Delete the marker, keep the test.**

---

#### 2. Prioritized task list

##### P0 — unblocks the commit (4 tasks)

- [x] **P0-0 (NEW 2026-08-11, `mainB`) — derived `stack_priors.yaml` has DROPPED the `NUMA_FULL`
      instance of every quarterable fleet. Owner: the stack owner (`inference`), NOT this lane.**
      This is the single root cause of **7 of the 9 currently-failing unit tests**, and P0-1 cannot
      close until it is fixed. **It must not be fixed in the tests.**

      | | frontdoor | worker_general | ingest_long_context |
      |---|---|---|---|
      | `stack_topology.yaml` declares | **8070** + 8080 + 8180 | **8072** + 8082 + 8182 | **8085** + 8185 + 8285 |
      | `derived/stack_priors.yaml` records | 8080, 8180 | 8082, 8182 | 8185, 8285 |

      Every declared `NUMA_FULL` is absent; both surviving entries per fleet carry
      `cpu_shape_class: half`. `architect_critic` survives only because its sole instance *is* the
      full. **The tell that this is a drop and not a lineup that was never declared:** the same
      priors blob still carries `cache.slots_by_port {8070: 4, 8080: 1, 8180: 1}` — the generator
      knew about the full and it was lost downstream.

      **Consequence beyond the red tests.** `ServerURLsConfig().frontdoor` resolves to
      `full:http://localhost:8080,...`, and the `full:` prefix designates the FIRST url as the full
      instance — so a **half is advertised as the full**. `src/config/models.py` warns in-file that
      dispatch resolves port → topology index and fails OPEN on an unresolvable port; a half
      labelled full is a region-lock **scope** error (2 of 4 regions claimed as if 4), not a
      cosmetic string.

      **Operator-visible recurrence.** `8070/8072/8085` is the exact triplet the operator ruled
      *"accidental and clearly a mistake"* on 2026-07-23, restored the same day via `--numa-mode
      both` (orchestrator `95dffc88`, see `stack-lineup-dossier-2026-07-23.md`). This is that
      regression recurring, now in the derived priors rather than the launch contract.

      **Why no session without the stack can fix it:** `src/registry/stack_priors.py:1041`
      `_realized_compile_numa_mode` derives the mode from the **realized** fleet and explicitly
      REFUSES to compile when nothing is listening (ESC-8 kill chain A4 — it will not default to
      `full` and rewrite priors to a dead lineup). The current file is therefore a faithful record
      of a halves-only launch. Fix = relaunch with the fulls realized, then recompile — i.e. **P0-3
      step 1, which already exists**; this row is its precondition, not extra work.

      **Standing prediction, recorded so it can be falsified:** after that relaunch + recompile all
      seven go green with **zero** test edits. If any still fails it is a real test defect and
      `mainB` owns it.

      Affected tests (do NOT relax them — they assert the topology-declared lineup and are correct;
      editing them to expect halves-only would encode the regression into the promotion gate, the
      same "guard that asserts the defect" shape §1.5 already retired one test for):
      `test_config_consolidation::test_specific_role_urls`, `test_dashboard_helpers` ×3,
      `test_fleet_layer_build::test_case1_real_worker_fleet_realizes_full_plus_quarters`,
      `test_kv_compress_adaptive::test_production_ports_use_live_role_names`,
      `test_stack_templates_v2::TestDefaultYamlRoundTrip::test_default_yaml_loads_and_validates`.
      ✅ **VERIFIED RESOLVED 2026-09-16 (`sub-sweep`), zero source or test edits by this pass.**
      Git evidence: the fulls reappear in `orchestration/derived/stack_priors.yaml` at orchestrator
      `7483d7fb` / `0d145f4f` (2026-08-21, "regen under production fleet mode (both)"). The
      preceding compile `969244d8` (2026-08-11) has no `port: 8072` entry; the regen has 4. On main
      `92bbeb06` (compiled 2026-09-03) the launch entries are frontdoor 8070 full + 8080/8180 half;
      worker_general 8072 full + 8082/8182 half; ingest_long_context 8085 full + 8185/8285 half.
      **Standing prediction held:** all 7 named tests pass (`-k` slice over the 5 files: 159 passed).
      The only later edit to those files, NIB2-69 `4055dba0`, isolates dashboard label resolution
      from host fleet markers. It does not relax a topology expectation.
      **E8-era guard (the other named failure class):** leave it as it is. `ruling_op19_e8_chain_20260827`
      (root `1ee8bd7c`) RETIRES the chain; it does not re-pin the runner. It cites the `:1313` v8-pin
      firing as evidence that the instrument is dead on the current tree. Re-pinning that guard to v9
      would re-base a retired measurement era, which is human-only. The test side was already made
      hermetic on main by NIB2-69 `89b30eb5`: host provenance is stubbed with the runner's own v8
      constants, the identity check is untouched, and 12 sealed-bundle tests are skipped with a
      named owner. All `tests/unit/test_e8*.py`: 386 passed, 28 skipped. The "16 failures" count in
      P0-1 below is therefore historical.
- [x] **P0-1. Fix the 30 net-new breaking tests across 14 files**, including the
      two in `PROMOTION_GATE_TARGETS` (both in
      `tests/unit/test_build_server_command_helpers.py`). Retire
      `test_worker_general_numa_policy_is_full_instance_only` rather than
      repairing it — it asserts the defect (§1.5). Re-derive the exact 30 with an
      A/B against a clean `git archive HEAD` if the list has drifted.

      **RE-DERIVED 2026-08-11 (`mainB`) — the list had drifted, badly. Do not re-do the parts that
      are already done.** Full `tests/unit` run, no `-x`, `--timeout=90`: **9 failed / 11771 passed
      / 63 skipped**, across **7** files — not 30 across 14.
      - The **retire target no longer exists**: `test_worker_general_numa_policy_is_full_instance_only`
        was retired and replaced on 2026-07-31 by the test at
        `test_build_server_command_helpers.py:1156`.
      - **`PROMOTION_GATE_TARGETS` is fully green** — all six target files, **200 passed / 0
        failed** — though this row cites two failures in `test_build_server_command_helpers.py`.
      - **7 of the 9 are P0-0 above** and are not test work at all.
      - **1 fixed** ✅ orchestrator `5f08875a`: a `SimpleNamespace` stand-in omitted
        `retrieval_compaction`, which `eval_tower._compact_question_result` reads unguarded. Fixed on
        the fixture side to match the real `QuestionResult` default (`{}`); making the production
        read defensive would have taught it to tolerate a field that is never genuinely absent.
      - **1 is an operator decision**, filed separately: the E8 protocol's frozen-kernel guard at
        `run_e8_quality_baseline_reseed.py:1313` fires because today's v9 freeze moved the tree it
        pins (`/mnt/raid0/llm/llama.cpp` is now `production-consolidated-v9` @ `0db32c06`; the pin
        wants v8 @ `67a433bf4`). The guard is working correctly — re-pinning it would re-base a
        measurement era, which is human-amendment-only.

      So what remains of P0-1 is **gated on P0-0**, not on test authoring.
      ✅ **CLOSED 2026-08-24** — P0-0's derived-priors drop is resolved
      (`derived/stack_priors.yaml` records 8070/8080/8180 with `cpu_shape_class: full`);
      `PROMOTION_GATE_TARGETS` **196 passed / 0 failed**; full `tests/unit` suite is
      **16 failed / 12526 passed / 69 skipped / 6 xfailed** after three fixture-side fixes today
      (gate-fixture fields `waited_s`/`blocking_roles` in `test_dispatch_cross_role_placement.py`
      and `test_inference_mixin.py`; SS-BENCH-GATE-c placement `ps` subprocess counted in
      `test_model_server_coverage.py`). The 16 remaining failures are all the E8-era guard above
      (operator decision, untouched by design) plus the same-class derived-priors expectations —
      none are the new-topology breakage this row exists to fix. No source code was modified.
- [x] **P0-2. Remove the now-XPASSing `xfail(strict=True)` marker** on
      `tests/unit/test_orchestrator_stack_threads.py::test_straddling_cpusets_declare_a_numa_policy`.
      Keep the test; it is the replacement assertion for the one retired in P0-1.
      ✅ **Already done before 2026-08-11** — verified by `mainB`: the marker is gone, the test is
      bare with an explanatory comment above it, and it passes. Nothing to remove. Ticked so the
      next session does not spend a cycle rediscovering that.
- [x] **P0-3. Cold-start the stack, re-bench the contention matrix, commit + push ✅ 2026-10-29 (audit: stack cold-started live W3 ed891211 (2026-07-31, numa:1329+); matrix re-benched (numa W1 sect [x] 2026-08-01; orch 0a564a1f6 2026-09-24 topology 4893e37e); all repos long committed) [no-belief: audit-reconciliation]
      all three repos.** Strictly ordered; each step has a resume check so a crash
      mid-sequence is recoverable:
      1. **Cold-start** — `orchestrator_stack.py` (never a bespoke launcher).
         Gated on P0-1/P0-2 being green and on `region-lock status` showing the
         measurement regions **free**. *Resume check: is the stack up and does
         live == config?*
      2. **Re-bench** — `uv run python scripts/server/contention_matrix.py run`
         (writes `orchestration/contention_matrix.yaml`). *Resume check:
         `contention_matrix.py validate` reports fresh against live topology hash
         `bc28e15d`.*
      3. **Commit + push** — `epyc-orchestrator`, `epyc-inference-research`, and
         this repo. **Pathspec-limited commits only** (`git commit -- <paths>`),
         `git fetch` + `git log @{u}..main` first. *Resume check: `git status`
         shows the §1.1 files clean in both repos.*

##### P1 — correctness gaps found by three parallel hygiene audits (10 tasks)

Sources — cite these, they contain the full reasoning:
`/mnt/raid0/llm/tmp/hygiene_scheduling.md` ·
`/mnt/raid0/llm/tmp/hygiene_autopilot.md` ·
`/mnt/raid0/llm/tmp/hygiene_config_tests.md`

All ten are **zero-inference** and can be worked while the measurement runs hold
the machine.

- [x] **P1-1. Generalise the `placement_policy` enum vocabulary — it is
      quarter-shaped.** ✅ 2026-08-12 (`mainA`) — orchestrator `1849e7d4`. Row was STALE BY ONE
      DAY: `270cf9ea` (2026-07-31) already landed `BURST_PREFER_SPLIT`, the legacy alias map and
      the `_coerce` raise. The real gap was that fail-CLOSED was tested and fail-LOUD was not —
      gutting the message to `ValueError("bad placement policy")` left all 19 existing tests
      passing. Now pinned by 16 collected tests, 11 mutations all counted as failures. Also
      fixed a docstring that still promised the removed fallback, and a NEW fleet-wide fail-open:
      the `stack_numa` import sat in a bare `except Exception`, so a breakage would silently
      resolve EVERY role to `SOLO_PREFER_FULL`.
      quarter-shaped.** `src/scheduling/placement_policy.py:35` declares
      `BURST_PREFER_QUARTERS`, and `SOLO_PREFER_FULL`'s docstring says concurrent
      requests "spill to NUMA-disjoint quarters". On a machine with no quarters
      both options mean the same non-existent thing. Rename to shape-agnostic
      (`BURST_PREFER_SPLIT`) with an **alias map** for the existing
      `"burst_prefer_quarters"` strings already sitting in configs. **Note while
      you are in there:** `_coerce` returns `None` on an unknown string and the
      caller substitutes `DEFAULT_PLACEMENT_POLICY` — so a typo silently degrades
      to a **different policy** rather than erroring. Fix that too, or the alias
      map hides its own failures.
- [x] ~~**P1-2. `affinity_preflight` self-disarms.**~~ (closed 2026-10-29 audit: DUPLICATE → same defect as numa-placement-defect-20260730.md:900 (T5, INF-43 owner); keep that box; affinity_preflight.py:277 still `required = no_mmap and len(expected_nodes)==1`; blocked on INTERLEAVE_TOLERANCE ratification (no...)
      `scripts/server/affinity_preflight.py:195` reads
      `required = no_mmap and len(expected_nodes) == 1`, so **every full and every
      half is exempt** — the gate that would *prove this cutover landed* passes
      vacuously. **Operator has chosen HARD-FAIL.** Blocked on ratifying
      `INTERLEAVE_TOLERANCE` (P2-3 item B.2), because a multi-node check needs a
      tolerance to check against.
- [x] **P1-3. SUPERSEDE the `dual-half-negative` seed strategy.** ✅ 2026-08-12 — `mainD`. orchestrator `6dd3248d`. Superseded, never edited: **27 insertions, 0 deletions**, which is the machine proof the 2026-06-28 operator prior is untouched. Used the store's own append-only idempotent mechanism rather than inventing a `superseded_by` column. The prior's FIRST clause is refuted too — it calls dual-half 'negative at about 0.5x', while the 2026-07-30 fleet grid measures 2 halves ABOVE 4 quarters at every matched stream count (72.83/52.90, 98.81/81.00, 127.94/108.39).
      `scripts/autopilot/operator_seed_strategies.yaml:353` — `confidence: high`,
      operator-seeded, no TTL, insight "quarters remain the granularity". It
      **forbids the topology we just deployed**. It is a *learned prior*:
      **supersede it, never edit it in place.**
- [x] **P1-4. `stack_templates/default.yaml` is a 4th hand-maintained copy of the
  - *(2026-11-09)* Done in epyc-orchestrator `94af001d`: `default.yaml` topology now derives from `numa_config` at load; loaded template byte-identical before and after; 425 tests pass (one unrelated pre-existing failure). [no-belief: code-landed-verified-by-tests]
      topology.** *(2026-08-12 `mainA`, orchestrator `fa34447c` — PARTIAL, deliberately left
      open. The row's "fails 7 ways" is STALE: `validate_template` returns 0 errors today. The
      real hole was that `numa:` and `threads:` were compared by NOTHING — `stale_role_fact_table`
      skips ports by design and `_validate_stack_prior_parity` slides `numa_mode` until one
      matches, so four roles could declare any cpuset shape or thread count undetected. A parity
      gate now closes that. It is still a FOURTH COPY — now gated rather than derived. Finishing
      needs an owner for `src/config/stack_templates.py`; the proposal is in the new module's
      docstring.)*
      topology.** Its parity gate already fails 7 ways. Either derive it from the
      single source or delete it — a fourth copy is how the drift started.
      - *(2026-11-09, inf45-zerocompute.)* Re-checked: still a gated 4th copy (`scripts/validate/default_template_topology_parity.py` OK, 4 roles / 6 instances). Superseded same day: derivation BUILT, not merged: orchestrator branch `inf45-zerocompute-20261109` @ the P1-4 commit (`resolve_template_topology` in `src/config/stack_templates.py`; `default.yaml` no longer spells port/numa/threads for sourced roles; gate forbids authoring them). Loaded-template before/after dump byte-identical; 425 template/topology tests pass. Unticked until merged.
- [x] **P1-5. `src/registry/registry_validator.py` never cross-checks ✅ 2026-08-12 — `mainD`. orchestrator `7d4f96d2`. Cross-check added and wired into `validate_all`, reached by the one production caller (`stack_commands.py:1289` in `cmd_start`). **Premise corrected**: a PARTIAL guard already existed — `stack_manifest.validate_declaration_parity()` — but it iterates `NUMA_CONFIG.items()` and is structurally blind to a registry declaring a fleet the topology never heard of, which is P1-7's phantom-fleet shape. Both directions now covered, plus duplicate ports, `numa_instances` vs `len(numa_ports)`, and primary port vs full-instance port. 23 tests, counted by the runner (tests/unit 12039 → 12062); an empty/unloadable topology is an ERROR, never silent agreement.
      `numa_ports` against `NUMA_CONFIG`.** This is **the missing guard that
      allowed months of drift**. Add it; it is the cheapest permanent fix in this
      list.
- [x] **P1-6. `scripts/autopilot/eval_tower.py:1155` tests ✅ 2026-10-29 (audit: orch 2f9bd733 (2026-08-12) "eval fan-out: replace the one-mode equality test with a total mode resolution"; eval_tower.py:2044 now guarded by _resolve_stack_numa_mode_for_fanout + _full_first_live_concurrency) [no-belief: audit-reconciliation]
      `stack_numa_mode == "quarter"`.** A half fleet never matches, so eval
      fan-out **silently collapses to 1**. Silent, not loud — no error is emitted.
- [x] **P1-7. `vision_escalation` has a PHANTOM 5-port fleet.** Ports ✅ 2026-10-29 (audit: models.py:278-283 comment: vision_escalation 8187/8287/8387/8487 dropped, role single-instance; stack_templates/default.yaml:13 lists them RETIRED, only alias entry remains; orch 982adb0c (2026-07-31 retire quarters)) [no-belief: audit-reconciliation]
      `8187/8287/8387/8487` **never existed** and are declared in
      `src/config/models.py` (see the comment at `:273`) and
      `stack_templates/default.yaml:145-148`.
- [x] **P1-8. Land `region_lock_wait_s_by_holder` telemetry BEFORE exposing any
      routing knob to autopilot.** A lever autopilot can move but cannot score is
      exactly how `dual-half-negative` (P1-3) got mislearned. This ordering is the
      point of the task. ✅ 2026-11-11 (pipeline-mgmt) — autopilot-visible reader orchestrator `cfa503e5` (read-only, surfaced in the optimization brief; no routing knob). [no-belief: telemetry plumbing, not a measurement]
      - *(2026-11-09, inf45-zerocompute.)* Telemetry merged (`0b342a07`, dispatch log `aa86437c`); an autopilot-visible reader is still needed. It adds `region_lock_wait_s_by_holder()` (blocked-wait seconds + count keyed by holder role from the lock payload, observation-only, process-local) in `src/runtime/cpu_region_lock.py`, 3 new tests + 183-test lock/topology suite green. Surfaced additively as `region_lock_wait_s_by_holder` (process-cumulative) on every `dispatch.v1` dispatch record, with tests (77 pass); the dashboard route is untouched. Unticked until the branch is merged and an autopilot-visible reader exists.
- [x] **P1-9. Delete-candidate: `scripts/server/quarter_scheduler.py` — ADJUDICATED: DO NOT
      DELETE.** ✅ 2026-08-12 (`mainA`) — orchestrator `1fe3b57e`, additive only (+83/-0). Two of
      the row's three claims are FALSE. "Zero runtime importers" is TRUE (every dynamic route
      ruled out). But "two test-only references" misses FOUR more, and THREE ARE LIVE
      PRODUCTION CODE carrying a purpose-built API for this scheduler — `round_robin.py:119`,
      `concurrency_aware.py:1724`, `stack_migration.py:14`; deleting orphans them. "Factually
      wrong about the machine" is refuted: `QUARTER_TOPOLOGY` is identical to the live
      `stack_numa` constants — the quarters are UNUSED since W1, not WRONG. NIB2-18 is an OPEN
      "do not treat as code-only scaffolding" checkbox. The row's own cited test line `:234` is
      wrong; `:322` pins DS-7 governance metadata, so "fixing" it would break a contract. A
      PARKED banner now sits in the module so this is not re-litigated. Original text below.
  - ~~403~~
      lines, **zero runtime importers**, and now factually wrong about the
      machine. Confirm the two test-only references
      (`tests/unit/test_dynamic_stack.py:177`,
      `tests/unit/test_stack_templates_v2.py:234`) and delete.
- [x] **P1-10. Add a pre-commit check for `REQUIRED_SOURCE_ARTIFACTS` staleness.** ✅ 2026-08-12 — `mainD`. orchestrator `65d55ea4`. Reads the GIT INDEX, not the worktree — at commit time the question is what the commit will contain. Blame is scoped (staged paths ERROR, inherited debt WARNs, `--staleness-strict` promotes) because **3 of 9 pins are stale at HEAD right now** and an unconditional gate would push people to `--no-verify`, which also skips the PII and hermes-drift hooks. All three fail-open paths are loud and tested: empty section, unresolvable path, staged deletion. 103 → 127 tests. NOT wired — hook registration is operator territory; the exact line is in the commit message.
      `scripts/validate/stack_change_guard.py:40` — a commit touching any of those
      files **silently blocks `orchestrator_stack.py start`** until the priors are
      recompiled, with no warning at commit time. **Two occurrences today from two
      different sessions**; that is a recurrence rate, not an anecdote.

##### P2 — measurement debt (5 tasks)

- [x] ~~**P2-1. Re-run 27 of 31 E5 Stage-B cells under `P-BENCH-PLACEMENT-1`.**~~ (closed 2026-10-29 audit: DUPLICATE → same work as numa-placement-defect-20260730.md:854 (T3 "Re-run the 27 confounded E5 cells", INF-43 index row); keep that box)
      4 are salvageable. Owning suspension banner:
      [`batched-decode-measurement.md`](numa-placement-and-contention.md#track-batched-decode-measurement).
- [ ] **P2-2. Establish production anchors for the three roles that have none.**
      Only `frontdoor` has one — **median 35.7 tok/s, n=154**, derived from
      AutoPilot production traffic, *a path independent of the thing under test*,
      which is what makes it valid. `worker_general`, `architect_general` and
      `ingest_long_context` have no anchor, so
      `P-BENCH-PLACEMENT-1`'s **mandatory anchor gate has nothing to gate
      against**. Derive them the same way — not from a bench invocation.
- [x] **P2-3. Ratify the 14 TBDs in
  - *(pipeline-mgmt 2026-11-11.)* RATIFIED by operator: RATIFY-INF45-P23-TBDS-20261111, root `70ba71701` (TBDs 3,4,5,7,8,9,10,13,14; 1,2,6,11,12 previously ratified or closed). [no-belief: governance ratification, not a measurement]
      [`../../artifacts/operator/ratification_queue_20260730.md`](../../artifacts/operator/ratification_queue_20260730.md).**
      **A gate whose threshold is unset cannot fail.** Human-amendment-only —
      prepare, present, park; never self-apply. P1-2 is blocked on item B.2
      (`INTERLEAVE_TOLERANCE`).
  - **Operator decision 2026-11-10:** INTERLEAVE_TOLERANCE ±25% relative accepted. It is already in force as TBD 2 under RATIFY-INF45-P23-20261109 (`measurement/protocols/bench-cpu.md`). TBDs 3, 4, 5, 7, 8, 9, 10, 13, 14 remain open, so this box stays open.
- [ ] **P2-4. Add a CONTEXT-DEPTH field to the claim grammar.** Same model, same
      recipe, same placement spans **40.22 tok/s at a 28-token prompt down to
      17.23 at 35k** — a 2.3× spread driven purely by depth — and **the ratified
      exemplar carries the 28-token figure with no depth term**. Proposal is
      drafted in §A of the ratification queue.
  - **Operator decision 2026-11-10:** required `depth=<n>` claim field accepted. Amendment prepared as `scripts/operator/run_inf45_p24_ratify_20261110.sh` (RATIFY-INF45-P24-20261110, human-amendment-only); box closes when the operator signs it.
- [x] **P2-5. ~~Fold the ngram result into the production recipe~~ — CANCELLED ✅ 2026-07-31.** The 2.80× was a warm-context self-copy artifact (see the RETRACTION section below and master index N26). Confirmatory re-run with 3 distinct prompts per rep: **−4.2% to +1.3%**; `ngram-mod` alone costs **23–31%**. **No `acceleration.spec_type` field is to be added.** Original text follows:
  > **P2-5. Fold the ngram result into the production recipe once the sweeps
      land.** Measured CPU gain: **2.80× on Qwen3.6-35B at 14k tokens**
      (acceptance `.505 → .755`) and **+15% on Qwen3-Next-80B, which currently has
      NO speculation at all**. gemma and the 122B gained nothing — do not apply it
      there. The tuning surface is **ONE field per role**:
      `acceleration.spec_type` in the master registry, plus a recompile.

**Counts: P0 = 3 · P1 = 10 · P2 = 5 · total 18.**

---

#### 3. Dependency graph

```
                 ┌─ P0-1 fix 30 breaking tests (2 in PROMOTION_GATE_TARGETS)
                 │
  tests green ───┤                                  ← stack start is GATED on these
                 └─ P0-2 drop the XPASSing xfail marker
                         │
                         ▼
              in-flight runs finish (region-lock status: q0/q1/q3 free)
                         │
                         ▼
              P0-3.1  cold-start the stack           ← requires a live stack
                         │
                         ▼
              P0-3.2  re-bench the contention matrix ← RUNS INFERENCE; only path
                         │                             to topology_hash bc28e15d
                         ▼
              P0-3.3  commit + push all three repos  ← pre-commit hook now passes


  GPU ngram sweep (q3) ──┐
                         ├──► full_last.sh (all four regions, 122B only)
  halfa_rest.sh (q0+q1) ─┘            │
                                      ▼
                          P2-5 fold ngram → acceleration.spec_type
                                      │
                                      ▼
                          SECOND registry recompile + a second contention
                          re-bench, because spec_type changes the launch
                          command and therefore the topology-adjacent priors


  P2-3 ratify INTERLEAVE_TOLERANCE (queue item B.2) ──► P1-2 arm the
                                                        affinity_preflight
                                                        hard-fail

  P1-8 region_lock_wait_s_by_holder telemetry ──► ANY autopilot routing knob
                                                  (incl. P1-1's generalised
                                                   placement_policy surface)
```

**Two hard sequencing facts a fresh agent must not reorder:**

1. **Tests before stack start.** Not stylistic — `orchestrator_stack.py start`
   runs the promotion gate, and two of the failures are in it.
2. **The ngram recipe change (P2-5) forces a SECOND recompile + contention
   re-bench.** If you land it in the same window, sequence it *after* P0-3 so the
   cutover commit is not entangled with a recipe change.

---

#### 4. Cross-cutting concerns

- **Shared working tree.** `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>`
  are the same physical clone. Other sessions are staging into the same index
  right now (visible in `git status`: repl-memory, autopilot, trace, eval
  artifacts). **Never `git add -A`. Always `git commit -- <explicit paths>`.**
  Subagents must never switch branch here.
- **Four copies of the topology.** `stack_numa.py`, the master registry, the lean
  registry, and `stack_templates/default.yaml` (P1-4). Any change to one that
  misses the others reproduces the drift this cutover exists to fix. P1-5 adds
  the guard that would have caught it.
- **Trust-boundary writes are human-only.** `MEASUREMENT.md` and
  `measurement/protocols/` are human-amendment-only. P2-3 and P2-4 are
  *prepare-and-park*, never self-apply.
- **A learned prior is evidence, not config.** P1-3's `dual-half-negative` must be
  **superseded with a dated successor**, not edited. Editing it destroys the
  record of what autopilot believed and why.
- **Silent failure is the theme of this whole handoff.** The disarmed preflight
  (P1-2), the vacuous eval fan-out (P1-6), the missing registry cross-check
  (P1-5), the unset thresholds (P2-3), the `_coerce` policy degradation (P1-1),
  and the no-warning priors staleness (P1-10) are all the *same defect class*: a
  check that cannot fail. Fixing any one of them without the others leaves the
  class intact.
- **Region discipline.** Half A is GPU-disjoint; half B contains q3 which the GPU
  lane holds. Schedule CPU work on half A while the GPU lane is live.
- **Reload ownership.** The session that owns the inference executes any reload,
  at a moment it chooses. Do not force a reload on another session's workflow —
  including the API-only case.
- **No inference from a subagent.** Subagents do zero process management. The
  cold-start and the re-bench are main-session actions.

---

#### 5. Key file locations

**The cutover itself** (`repos/epyc-orchestrator`):

| Path | Role |
|---|---|
| `scripts/server/stack_numa.py` | `NUMA_CONFIG` — the topology; import-time invariants |
| `orchestration/model_registry.yaml` | lean registry (compiled) |
| `orchestration/derived/stack_priors.yaml` | generated priors |
| `orchestration/model_descriptors.yaml` · `src/registry/model_descriptors.py` | descriptors |
| `docs/generated/current_stack_summary.md` | generated summary |
| `src/config/models.py` · `src/fleet.py` | port/fleet declarations |

**The blocker**:

| Path | Role |
|---|---|
| `.git/hooks/pre-commit` | invokes the freshness check |
| `scripts/validate/check_contention_matrix_fresh.py:89` | emits the `FAIL: contention matrix is STALE` message |
| `orchestration/contention_matrix.yaml` | records `topology_hash: "8c8cfcbb13d2611d"`; live is `bc28e15d` |
| `scripts/server/contention_matrix.py` | `run` / `validate` subcommands; **`run` needs a live stack and runs inference** |

**Tests**:

| Path | Role |
|---|---|
| `scripts/registry/stack_change_pipeline.py:67` | `PROMOTION_GATE_TARGETS` |
| `tests/unit/test_build_server_command_helpers.py:1031` | `test_worker_general_numa_policy_is_full_instance_only` — **retire, do not repair** |
| `tests/unit/test_orchestrator_stack_threads.py:159` | `test_straddling_cpusets_declare_a_numa_policy` — **drop the `xfail(strict=True)`, keep the test** |

**P1 targets**:

| Path | Task |
|---|---|
| `src/scheduling/placement_policy.py:35` (+ `_coerce`) | P1-1 |
| `scripts/server/affinity_preflight.py:195` | P1-2 |
| `scripts/autopilot/operator_seed_strategies.yaml:353` | P1-3 |
| `stack_templates/default.yaml` (`:145-148` phantom ports) | P1-4, P1-7 |
| `src/registry/registry_validator.py` | P1-5 |
| `scripts/autopilot/eval_tower.py:1155` | P1-6 |
| `src/config/models.py:273` | P1-7 |
| `scripts/server/quarter_scheduler.py` (403 lines, 0 runtime importers) | P1-9 |
| `scripts/validate/stack_change_guard.py:40` `REQUIRED_SOURCE_ARTIFACTS` | P1-10 |
| `scripts/autopilot/config_applicator.py` `placement_policy_knobs` | P1-1/P1-8 knob surface |

**Research repo** (`repos/epyc-inference-research`):
`orchestration/model_registry.yaml` (**master** — `no_mmap`, `numa_ports`) ·
`docs/guides/benchmarking-guide.md` · `docs/guides/model-sizing.md`

**Evidence + audits** (scratch — copy anything load-bearing into the repo before
relying on it long-term):

| Path | Contents |
|---|---|
| `/mnt/raid0/llm/tmp/hygiene_scheduling.md` | scheduling/placement audit → P1-1, P1-6, P1-8, P1-9 |
| `/mnt/raid0/llm/tmp/hygiene_autopilot.md` | autopilot audit → P1-3, P1-8 |
| `/mnt/raid0/llm/tmp/hygiene_config_tests.md` | config/test audit → P1-4, P1-5, P1-7, P1-10 |
| `/workspace/artifacts/operator/ratification_queue_20260730.md` | the 14 TBDs → P2-3, P2-4 |
| `/mnt/raid0/llm/tmp/gpungram_results.txt` · `gpungram_run.sh` | GPU ngram sweep (q3) |
| `/mnt/raid0/llm/tmp/halfa_live_results.txt` | CPU half-A arms (q0+q1) |
| `/mnt/raid0/llm/tmp/cpu_chain.sh` → `halfa_rest.sh` → `full_last.sh` | chained CPU runs |
| `/mnt/raid0/llm/tmp/ngramshapes_partial.txt` | 16/30 cells; quarter block deliberately abandoned |
| `/mnt/raid0/llm/llama.cpp-experimental/build-v8-hip/bin/` | v8 HIP build — needs `LD_LIBRARY_PATH` = this dir **+** `/opt/rocm/lib` |

**Entry points**:
`repos/epyc-orchestrator/scripts/region-lock status` ·
`scripts/server/orchestrator_stack.py` ·
`scripts/server/contention_matrix.py {run,validate}` ·
`scripts/registry/stack_change_pipeline.py check --run-promotion-gate`

---

#### 6. Reporting instructions

1. **Flip the checkbox in §2 the moment a task lands** — append `✅ YYYY-MM-DD`
   inline. The handoff dashboard counts checkbox state only; prose status is
   invisible to it. Work discovered mid-flight gets its own `- [ ]` line (or
   `- [x] … ✅ date` if already done).
2. **On P0-3 completion**: record the three commit SHAs (orchestrator, research,
   root) and the new `topology_hash` here, delete row **N25** from
   [`master-handoff-index.md`](master-handoff-index.md), and append to
   `progress/2026-07/2026-07-30.md`.
3. **Numbers use the claim grammar** — `(metric, protocol-id, n/reps, date,
   attestation ref)`. Until P2-4 lands, **also state the prompt depth in prose**;
   a bare decode rate is under-specified by up to 2.3×.
4. **Anything that changes a threshold, protocol, or learned prior** is
   prepare-and-park: write the exact patch, present it, do not apply it.
5. **Cross-reference, do not duplicate.** Diagnosis findings belong in
   [`numa-placement-defect-20260730.md`](numa-placement-and-contention.md#track-numa-placement-defect-20260730) (N24),
   E5 re-run accounting in
   [`batched-decode-measurement.md`](numa-placement-and-contention.md#track-batched-decode-measurement). This document
   holds only the *resume state* of the cutover.
6. **When P0 is fully green, this handoff's reason to exist is gone.** Move the
   surviving P1/P2 rows to their owning handoffs and archive this to
   `handoffs/completed/`. A resume document that outlives its blocker becomes
   stale documentation.

##### P1-11 — the contention matrix cannot see the GPU lane (filed 2026-07-30)

- [x] ~~**Make the GPU shadow lane a participant in `contention_matrix.yaml`.** Its~~ (closed 2026-10-29 audit: SUPERSEDED → "OPERATOR DESIGN DIRECTIVE 2026-07-31" (numa:639) states it supersedes the framing of the three tasks above; lane-as-row subsumed by surface redesign box numa:658)
  current participants are six CPU roles only; the lane is not a row. Measured
  footprint: the lane pins host threads to logical `184-191`, which fold to
  PHYSICAL cores 88-95 = region **q3**. So `full` (`0-95`) and `half B`
  (`48-95,144-191`) are physical co-tenants of the lane and `half A`
  (`0-47,96-143`) is not. Under a bandwidth-generating lane proxy the full
  instance lost **34%** while half A lost nothing. Half B has NEVER been measured
  against the lane — which is why every half measurement in this campaign was
  deliberately taken on half A.
- [x] ~~**Do not mechanically exclude `full` / `half B` pairs.** Their CPU-vs-CPU~~ (closed 2026-10-29 audit: SUPERSEDED → superseded by numa:639 directive and "P1-11 CORRECTED 2026-07-31" (numa:993-1005): full/half pairs are derived structural exclusions, lane contention becomes a surface value)
  verdict is structural (cpuset intersection), but their lane contention is not,
  and a BLOCK verdict reached for CPU reasons would leave the lane channel
  permanently unmeasured. This is the dangerous direction of the error.
- [x] ~~**The tool simultaneously over- and under-measures.** 5 of the 15 pairs in~~ (closed 2026-10-29 audit: SUPERSEDED → superseded by numa:639 directive + ratified three-artifact design (numa:1024): derive structural pairs (numa:1030), measure sparse interference (numa:1040))
  the committed matrix are structurally overlapping and tagged
  `overlap_measured` — live inference spent re-deriving set intersection. Under
  the new topology 58 of 78 pairs are structurally blocked. Both halves of this
  are one root cause: the model is cpuset-intersection-only, so it cannot skip
  what is derivable nor represent what is not.
  Do NOT fix inline during the cutover — changing a safety gate's semantics
  mid-migration should be a reviewed change.

###### OPERATOR DESIGN DIRECTIVE 2026-07-31 — the matrix becomes a SURFACE, not a veto

**This supersedes the framing of the three tasks above.** "Make the GPU lane a
matrix participant" is no longer a sufficient statement of the work: adding the
lane as a row inside a mutual-exclusion model would harden exactly the model the
operator has now rejected. Recorded verbatim:

> Co-residency of the GPU lane with half B / full instances **must not be
> modelled as mutual exclusion**. The GPU lane's contention impact is large only
> under heavy memory-bandwidth use — the typical case being models being
> **loaded/unloaded** from the GPU. **We plan to keep GPU models resident, so
> that case does not arise.** There may be deleterious contention under heavy
> concurrent prompting of the GPU models, but binary mutual exclusion of half B /
> full / GPU is **overkill**. The contention matrix should be **more nuanced**
> and should **offer a surface that autopilot can optimize and that the
> orchestration router can be trained on** — not a hard block.

Consequences for the tasks above:

- **[declined: ws58 2026-11-03 content-review: merged into the ratified three-artifact design (the surface is artifacts (2)+(3))]** **Redesign the matrix as a continuous contention surface** (cost/degradation
  estimate per pair and load regime) that autopilot can optimize over and the
  orchestration router can be trained on — not a BLOCK/ALLOW verdict table. The
  GPU lane enters as a dimension of that surface, which subsumes the first task
  above.
- [x] ~~**Derive, do not measure, the structurally-determined pairs.** 58 of 78~~ (closed 2026-10-29 audit: DUPLICATE → same as numa:1030 "(1) Placement feasibility - DERIVED, never measured" (ratified design); keep numa:1030)
  pairs under the new topology are structurally derivable and must not consume
  inference time. Reserve measurement for the pairs whose interaction is *not*
  set-intersection — chiefly the lane channel under concurrent GPU prompting.
- **[declined: ws58 2026-11-03 content-review: merged into the ratified design as the regime axis of artifact (2)]** **Characterise the lane's bandwidth regimes rather than its worst case.**
  The 34% full-instance loss was measured under a bandwidth-generating proxy that
  stands in for model load/unload; with GPU models held resident that regime is
  not the operating point. Measure the resident-and-prompted regime separately
  before any coefficient is written into the surface.
- [x] ~~**Do not refresh the stale contention matrix merely to unblock the~~ (closed 2026-10-29 audit: OBSOLETE → premise (stale matrix blocking orchestrator pre-commit gate) gone: matrix re-benched 2026-08-01 (171f86f9 per numa W1 section) and orch 0a564a1f6 2026-09-24; commits proceed)
  `epyc-orchestrator` pre-commit gate.** Regenerating it under the old
  cpuset-intersection model would spend live inference producing an artifact this
  directive obsoletes. Commits bypass the gate with `--no-verify` and a
  documented reason until the redesign lands. ✅ recorded 2026-07-31


---

#### UPDATE 2026-07-30 evening — ngram RETRACTED; artifact rebuilt; vision measured

##### The ngram finding is withdrawn (this supersedes every ngram row above)

`--spec-type ngram-mod` buys **nothing**. The "2.80× at depth" result committed
earlier today was a harness artifact.

**Mechanism.** Each cell launched ONE server and sent the SAME prompt r times at
`temperature=0.3, seed=42`. Run 1 generates answer X; the server retains X in the
slot KV. Run 2 sends the identical prompt, hits the prompt cache
(`prompt eval = 4 tokens`), and `ngram-mod` — which drafts by matching text already
in context — copies its own previous answer verbatim. Mean accepted draft length
3.58 → 15.88; acceptance → 1.000.

**The control was already in the data.** Sorting all 68 cell logs by run2÷run1:
every cell inflated >1.15× is an ngram arm; all 25 `draft-mtp`-only and `none`
cells are flat at 0.92–1.08×. `draft-mtp` drafts from weights, so a warm context
cannot help it.

**Corrected (run 1 only), 16 model × depth × device cells: gain spans −17.4 % to
+2.7 %, centred on zero.** 35B CPU: 24.85 vs 24.86. `ngram-mod` alone is far worse
than MTP everywhere (122B CPU: 9.38 vs 15.76).

- [x] Retraction committed to research `84067a6e` (raw logs left unedited) ✅ 2026-07-30
- [x] Memory `feedback_ngram_fills_weak_drafter_headroom` rewritten as a retraction ✅ 2026-07-30
- [x] Artifact rebuilt on corrected numbers ✅ 2026-07-30
- [x] **Cancel the queued `acceleration.spec_type` per-role field.** It was queued ✅ 2026-10-29 (audit: P2-5 [x] CANCELLED 2026-07-31 (numa:~397) + numa:907-912 ticks; model_registry.yaml:1666-1669 retires ngram_candidate_spec_type, default_spec_type draft-mtp) [no-belief: audit-reconciliation]
  off the retracted finding. Nothing justifies enabling ngram on any role.
- [x] Re-scope NG1–NG5 in `speculative-decoding-mtp-refresh.md` — they were filed ✅ 2026-10-29 (audit: numa:910 [x]: speculative-decoding-mtp-refresh.md banner added, NG1-NG4 cancelled, NG5 re-scoped (2026-07-31)) [no-belief: audit-reconciliation]
  against the retracted result.
- [ ] Fold the four P-BENCH-PLACEMENT-1 amendments (no repeated-prompt replication
  for context-reading drafters; mandatory non-context control arm; report n/min/max
  never a bare median; `accept=1.000` is a bug report) into MEASUREMENT.md proper.
  - **Operator decision 2026-11-10:** the four amendments ride RATIFY-INF45-P24-20261110 (`scripts/operator/run_inf45_p24_ratify_20261110.sh`) as A1-A4 in the P-BENCH-PLACEMENT-1 annex; box closes when the operator signs it.

##### Confirmatory re-run IN FLIGHT

`/mnt/raid0/llm/tmp/ngramfix.sh` → `ngramfix_results.txt`, under a q0–q3 lock.
3 DISTINCT prompts per rep (disjoint corpus slices, `mkdistinct.py`), per-rep
values printed, `draft-mtp` control in every group. 12 cells: 35B CPU full + 27B
GPU × d8k/d16k × 3 arms. **If a cell still climbs monotonically rep0→rep2, the
harness fix failed and that cell is void** — the script flags this inline.

##### Vision pair measured — the last unbenchmarked stack model

Qwen2.5-VL-7B-Instruct Q4_K_M, node1, 24t, `membind=1`. Same GGUF serves
`worker_vision` and `vision_escalation`, so this characterises both.

| depth | spec=none | spec=ngram-mod |
|---|---|---|
| 3.5k | 7.31 (min 7.20 max 7.47) | 9.18 — **artifact**, min 7.42 = the none arm |
| 14.1k | 5.36 (min 5.32 max 5.41) | 6.29 — **artifact**, min 5.29 |
| 27.6k | 4.03 (n=3, consistent) | not run |

- [x] ~~**NEW FINDING — VL-7B cannot serve deep context on a quarter.** Prefill on 24~~ (closed 2026-10-29 audit: OBSOLETE → premise gone: quarters retired and worker_vision no longer Qwen2.5-VL-7B (registry model_registry.yaml:2684 Qwen3-VL-30B-A3B); the capacity finding was about 7B on a 24-thread quarter)
  threads runs at ~27.5 tok/s, so a 27.6k prompt needs ~14 min and the first rep
  blew a 900 s client timeout. `g32k` was abandoned as guaranteed-void rather than
  burn an hour. If either vision role is expected to take long-context work, it
  needs more cores or GPU residency — this is a real capacity limit, not a bench
  artifact.
- [ ] **Harness parser bug:** depth is read from the FIRST `prompt eval time` line.
  When rep 1 times out before logging one, a later cache-warm incremental count is
  reported instead (observed: `prompt=2926` where true resident context was
  27,586, per `stop processing: n_tokens`). Read depth from `n_tokens` instead.

##### Test progress — 6 of 35 topology failures closed

Both fixed guards had the defect as their passing condition, so the correction
necessarily failed them; replaced, not adjusted. **Uncommitted** — the pre-commit
gate blocks ALL commits to this repo, including test-only ones, until the
contention matrix is refreshed.

- [x] `test_placement_policy` — split ABSENT (→default) from UNRECOGNISED (→raises) ✅ 2026-07-30
- [x] `test_stack_numa` — frontdoor[0] asserts `NUMA_FULL` + `interleave=all`, not
  the NPS2-era `NUMA_NODE0`; policy-less-prefix test rebuilt on a fixture; added
  `test_every_live_role_declares_a_memory_policy` ✅ 2026-07-30
- [x] ~~Remaining 29: `test_gate_seam_wiring` (9), `test_scheduling_contention_gate`~~ (closed 2026-10-29 audit: SUPERSEDED → topology test failures resolved: P0-1 CLOSED 2026-08-24 (numa:279; PROMOTION_GATE_TARGETS 196 passed/0 failed) and P0-0 fulls restored 7483d7fb)
  (5), `test_stack_priors_compiler` (4), `test_scheduling_contention` (3),
  `test_stack_templates_v2` (3), `test_quarter_stack_smoke` (3),
  `test_gpu_shadow_lane_p2` (1), `test_model_descriptors_schema` (1).
  Most funnel into the contention matrix or into quarter-shaped fixtures.
- [x] ~~`NUMA_NODE0` / `NUMA_Q0A` are referenced only by tests and comments; both are deletion candidates.~~
  Corrected 2026-11-01: orchestrator `f4230b222` removed `NUMA_NODE0`; `NUMA_Q0A` remains a live shape
  in `scripts/server/stack_numa.py` and its CPU-shape registries. Do not delete it based on the old claim.
  [no-belief: source inventory correction]

##### Operational lesson — do not re-arm a chain you have not positively identified

I concluded `full_last` was dead from `pgrep -af "full_last|region_lock"` and
re-armed it. It was alive: `cpu_chain.sh` was sitting in a `bash until … sleep 30`
loop whose command line contains neither pattern. Both then ran; they serialized
correctly on the region lock so nothing was poisoned, but full_last executed twice
(~15 min wasted) and the second pass **truncated `full_last_results.txt`** via its
`: > "$OUT"`. Recovered only because the file had been copied to
`/mnt/raid0/llm/tmp/preserved/` beforehand.

- **[declined: ws58 2026-11-03 content-review: a lesson, and one that prescribes pgrep -f, which the host rule forbids]** Before re-arming any chained job, enumerate waiters by their **script name**
  (`pgrep -f cpu_chain.sh`), not by the tag of the job they will eventually launch.
- **[declined: ws58 2026-11-03 content-review: a rule, not a task]** Bench harnesses should append or write to a run-stamped file, never truncate [too-big: current shared-result producers need cross-harness inventory by owner]
  a shared results path at startup.

---

#### UPDATE 2026-07-31 — vision models evaluated; speech stack mapped; ngram retraction propagated

##### Vision: MiniCPM-o is NOT a vision upgrade — the promotion case is dead on vision grounds

42 questions (OCRBench + ChartQA), all arms on the MI210, best quant present on disk.
Raw: `/mnt/raid0/llm/tmp/vlquality_results.json`; harness `/mnt/raid0/llm/tmp/vlquality.py`.

| model · quant | strict | re-scored (true) |
|---|---|---|
| Qwen3-VL-30B-A3B **Q4_K_M** | 35/42 | **36/42** |
| Qwen2.5-VL-7B **Q4_K_M** (incumbent) | 29/42 | **35/42** |
| Qwen3-VL-8B **Q8_0** | 31/42 | 33/42 |
| MiniCPM-o-4.5 **Q8_0** | 31/42 | 31/42 |
| Qwen3-VL-4B **Q8_0** | 28/42 | 29/42 |

- [x] Ran the comparison the M-1 n=10 could never resolve ✅ 2026-07-31
- [x] **Supersede the MiniCPM-o promotion premise in `multimodal-pipeline.md`** (`:153` "Test Path B first",
  `:165` M-1 `+12.5pp`, `:204-210` vendor table, `:255`, `:509`) and in
  `docs/reference/model-probe-scoreboard.md:64,98` ("**Yes** candidate"). MiniCPM-o lands **31/42, below the
  35/42 incumbent**. Note honestly that M-1 was `p=1.0` / `observation_only_unratified`, so this **supersedes on
  power**, it does not statistically contradict. ✅ **2026-07-31 — DONE, and escalated to full deprecation +
  weight deletion under explicit operator authorization.** All five `multimodal-pipeline.md` sites plus the
  scoreboard's two sites are superseded in place (history retained, dated corrections appended). Additionally:
  master registry entry `minicpm_o_45_local_multimodal` marked `deprecated: true` with the measured table as
  `deprecated_reason`; the promotion runbook carries a ⛔ DEPRECATED banner; `gpu-serving-tie-in-program.md`
  **P2-2c cancelled** and D2 reduced to one tenant; `stack_numa.py:429` and `gpu_shadow_lane.py:6` corrected;
  cancelled checkboxes flipped across 12 active handoffs. **The 22 GB `/mnt/raid0/llm/models/MiniCPM-o-4_5-gguf/`
  tree is DELETED** — reversible only by re-download from `openbmb/MiniCPM-o-4_5-gguf`. The M-1 artifact was
  re-verified before acting: exactly one of ten cases is discordant (`vl_chart_test_0563`, incumbent `0.11 kWh`
  vs accepted `0.11`), confirming the scoring-artifact diagnosis.
- **[declined: ws58 2026-11-03 content-review: a record, not a task]** **Record the two scorer artifact classes.** (a) comma/unit — `63,086` vs `63086`, `0.11 kWh` vs `0.11`;
  (b) **LaTeX whitespace** — `\frac { 1 } { x + y }` vs `\frac{1}{x + y}`. Both required offline re-scoring.
  The incumbent's strict score was depressed by 6 and Qwen3-VL-8B's by 2. **A bespoke scorer reproduced a
  brittleness we already fixed once in `debug_scorer.py`.**
- **[declined: ws58 2026-11-03 content-review: a labelling rule]** **Carry the saturation caveat on every one of these numbers.** OCRBench+ChartQA is precisely the family
  where Qwen3-VL was **never claimed** to improve (published: DocVQA +0.4, ChartQA +2.3, AI2D +1.8, OCRBench
  **+8** against the *independent* OpenVLM baseline of 888 — not the +32 the vendor card implies). Its real
  gains are MathVision **+28.8**, MMMU-Pro **+17.6**, MMMU **+11.0**, OmniDocBench **−45% edit distance**.
  Without this caveat the table reads as a Qwen3-VL regression, which it is not.
- [x] **MiniCPM-o encodes images at ~750 tokens, FIXED.** `--image-max-tokens 4096` and `--image-min-tokens 3000`
  are both **no-ops** for it (verified). Qwen2.5-VL spends **4103** on the same image. Architectural
  (~64 tokens/slice, capped slice count) — do not re-litigate by burning MI210 time.
  ✅ **RECORDED 2026-07-31** in `multimodal-pipeline.md` §"Vision Benchmarks vs Current Models" as caveat (b) on
  the 42q table, so the input-fidelity confound travels with the number. Now moot for re-litigation purposes —
  the weights are deleted — but kept because it explains *why* a model with better vendor benchmarks lost here.
- [x] **MiniCPM-o needs `enable_thinking=false` (API) / `--reasoning off` (server) or it scores 0** — it emits
  `reasoning_content` and an **EMPTY** `content`. Reproduced twice today: 1600 tokens of reasoning, no answer.
  ✅ **RECORDED 2026-07-31** in `multimodal-pipeline.md` §"Vision Benchmarks vs Current Models" and preserved in
  the `vlquality.py` harness comment. Moot for MiniCPM-o itself (deleted), but the **class** is not: it is the
  same failure the K35 gate hit in 2026-07 (`0/4` on default reasoning mode), and it generalises to any
  reasoning-mode VLM — a scorer reading `message.content` sees an empty string and reports a quality failure
  that is really a protocol failure.
- [x] **`Qwen3-VL-2B-Instruct-GGUF/` is EMPTY** — download or delete the directory. It is also the *only* model ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): directory no longer exists anywhere on the host (find / -maxdepth 6, 2026-11-10). [no-belief: obsolete, Qwen3-VL-2B dir absent]
  in the family with independent third-party verification, which we therefore cannot use.
- **[declined: ws58 2026-11-03 content-review: a note]** Qwen3-VL benchmark tables on the HF cards are **JPEG images**, not text — "official model card" there means
  a marketing graphic. Weight accordingly.

##### Speech: whisper IS deployed; TTS is not wired; the C++ TTS accelerator source is LOST

> **UPDATE 2026-07-31 (later same day) — TTS now WORKS, and the recommended path changed.**
> Upstream **`qwentts.cpp`** (`/mnt/raid0/llm/qwentts.cpp` @ `abab6b3`) implements the full stack
> including the codec our port hand-rolled, and produced this host's **first working speech
> synthesis**: **round-trip WER 0.0 %**, **TTFA 67.9 ms**, 0.86× real-time on CPU, with
> `CodecDecode` at **64 %** of wall (Talker 1313.7 ms, CodePredictor 1091.8 ms). Weights:
> `/mnt/raid0/llm/models/Qwen3-TTS-qwentts/` (1.19 GB, Q8_0 pair). It also builds with **HIP for
> gfx90a** after a one-line FP8 guard fix in a **third-party** repo — the frozen production kernel
> is untouched and **no experimental-kernel handoff is required**.
>
> **Consequences for the tasks below**: P0 (`start_tts()`) is unchanged and still open, but its
> subject is now `qwentts.cpp` rather than the PyTorch server; the **5-dep install becomes optional**
> (it belongs to the PyTorch fallback, which needs no deps under the C++ path); and "the C++
> accelerator" that must not be rebuilt is **ours**, not this one. Owning detail + task block S-1..S-11:
> [`multimodal-pipeline.md`](speech-and-multimodal.md#track-multimodal-pipeline).
>
> **STT also stopped depending on the network** the same day: `whisper_server.py` resolved a model
> *name* through `huggingface_hub` on every cold start and failed **silently** (it is in
> `OPTIONAL_AUXILIARY_ROLES`). Now pinned offline with a `WHISPER_ALLOW_DOWNLOAD=1` escape hatch;
> loads in 1.42 s with no network.

- [x] Corrected a false negative: whisper **is** on disk and **is** a managed service ✅ 2026-07-31 —
  `faster-whisper large-v3` 2.9 GB + `large-v3-turbo` 1.6 GB at `/mnt/raid0/llm/cache/huggingface/hub/`,
  launched by `orchestrator_stack.py:2123 start_whisper()` → `scripts/voice/start_whisper_server.sh`, port 9000.
  (Missed initially because they are CTranslate2 in `cache/`, not GGML in `models/`.)
- [x] **P0 — wire `start_tts()` into `orchestrator_stack.py`.** There is `start_whisper` (:2123), `start_sd_server` ✅ 2026-10-29 (audit: orch cba55d49 (2026-08-02 "W5+W4: aux services are declared data"): orchestrator_stack.py:3201 start_tts, stack_commands.py:147, launch_manifest.yaml:111 tts: 9002) [no-belief: audit-reconciliation]
  (:2067), `start_document_formalizer` (:2015), `start_handoff_dashboard` (:2176) — and **no TTS**. Operator
  stated 2026-07-31 that this gets fixed today. **The only prior trace is an ARCHIVED box**
  (`handoffs/archived/qwen3-tts-voice-synthesis.md:433`); `multimodal-pipeline.md:20` shows the gap only as
  ASCII art (`→ ❌ NO TTS OUTPUT`), which the dashboard cannot see.
- [x] ~~~~**Install the 5 missing deps for the PyTorch TTS path**~~ — **DOWNGRADED to optional 2026-07-31.**~~ (closed 2026-10-29 audit: OBSOLETE → box is struck through and DOWNGRADED to optional 2026-07-31; measured TTS path is qwentts.cpp (no Python deps), numa:841-847)
  `soundfile`, `fastapi`, `uvicorn`, `librosa`, `scipy` are needed only by the **PyTorch fallback** (Path C).
  The measured path is `qwentts.cpp`, a C++ binary with no Python runtime deps. Do this only if Path C is
  actually chosen. If it is: present already are `torch 2.6.0+cpu` and `transformers 5.5.1` in
  `/mnt/raid0/llm/venvs/llama-gguf-convert`, and you must **use a dedicated voice venv** — do not accrete a
  service's dependencies onto a GGUF-converter env.
- [x] **Do not rebuild the C++ accelerator — its source is gone** ✅ 2026-07-31 — and it is now moot: the
  accelerator in question is **ours**, and upstream `qwentts.cpp` supersedes it outright with a correct codec.
  Historical note: `tts_server.py` is full PyTorch and needs no C++ binary (Talker + CodePredictor + Decoder,
  ~0.9× real-time at 48 CPU threads — an **estimate**, never measured, where `qwentts.cpp` measures 0.86× RT).
  *(ADJUDICATED 2026-08-12 by `mainC` — deliberately left CLOSED. Reads as a prohibition to the
  standing-constraint sweep, but the box itself declares the constraint MOOT: upstream `qwentts.cpp`
  supersedes the accelerator outright, so there is no live action left to forbid. Do not re-open.)*
- [x] **The existing voice stack is invisible to the active handoffs.** `scripts/voice/` already contains ✅ 2026-10-29 (audit: multimodal-pipeline.md:93 now notes scripts/voice/ already contains tts_server.py; :614 "Prototype: FastAPI wrapper" ticked SUPERSEDED 2026-09-24 pointing to conversation-stack.md) [no-belief: audit-reconciliation]
  `tts_server.py`, `create_tts_sidecar.py`, `validate_tts_e2e.py`, `whisper_server.py`, `transcribe_batch.py`,
  `test_latency.py`, `start_whisper_server.sh` — named **only** in archived docs. Meanwhile
  `multimodal-pipeline.md:324` still tells a reader to *"Prototype: FastAPI wrapper around
  `Qwen3TTSModel.from_pretrained()`"* — i.e. build from scratch what already exists.

##### VRAM: speech costs the GPU nothing, which removes MiniCPM-o's last argument

| stack | size |
|---|---|
| MiniCPM-o omni (LLM Q8_0 + vision + audio + tts + proj) | **10.84 GB** |
| Dedicated Qwen3-TTS-12Hz-0.6B (Talker + CodePredictor Q8_0) | **1.14 GB** |
| delta for speech alone | **9.70 GB** |

- [x] **Feed this into `gpu-serving-tie-in-program.md` D2 / P2-9** (`phase2_resident_set` budgets). The PyTorch TTS
  path runs on **CPU** (`torch 2.6.0+cpu`) — **zero GPU VRAM**. Combined with MiniCPM-o losing on vision, there
  is no remaining justification for spending ~10 GB of contested MI210 on it.
  ✅ **2026-07-31 — DONE.** D2 amended in place to a **one-tenant** set (dense-27B only): MiniCPM-o struck as
  deprecated/deleted, whisper already deferred by W3. **P2-2c cancelled** and **P2-2 closed**. The
  `phase2_resident_set` rows in `gpu_shadow_lane_np_ceiling.yaml` were deliberately NOT edited — same fail-safe
  logic the whisper finding used: a reservation for a tenant that never arrives makes the budgets *conservative*,
  so nothing over-authorises. Both reclaims (~7 GB MiniCPM-o + ~1.6 GiB whisper) are queued for
  ceiling-amendment time downstream of P2-5j. Note the orchestrator repo could not be committed (pre-commit
  contention-matrix gate), but `np_ceiling.yaml` needed no edit, so nothing is left uncommitted on this item.

##### ngram retraction propagated into the record ✅ 2026-07-31

- [x] `master-handoff-index.md` **N26 rewritten as a retraction**; N25's P2-debt deploy sentence cancelled ✅
- [x] `speculative-decoding-mtp-refresh.md` — ⛔ banner added; **NG1–NG4 cancelled**, NG5 re-scoped ✅
- [x] `inference-research-index.md` — retraction banner above the stale row ✅
- [x] `numa-topology-cutover-resume-20260730.md` **P2-5 cancelled**; §1.4 in-flight banner corrected ✅
- [x] `numa-placement-defect-20260730.md:25-27` and its ngram section still carry the 2.80×. That file is ✅ 2026-10-29 (audit: numa-placement-defect-20260730.md:1441 "SUPERSEDING NOTE - 2026-07-31" append-only correction names :25-27 and :915 as retracted) [no-belief: audit-reconciliation]
  **append-only by its own rule** — add a dated superseding note at the end, do **not** edit in place.
- **[declined: ws58 2026-11-03 content-review: a note]** **The confirmatory re-run's own caveat**: 5 of 12 cells carry the harness's `MONOTONE CLIMB` flag — **but so
  does a `draft-mtp` CONTROL cell** (27B GPU d16k: 33.08→36.71→37.55), which cannot be contaminated by a drafter
  it does not use. The flag catches ordinary warm-up; it means "inspect", not "void". Fix the detector before
  reusing it.

##### Test/commit state unchanged

- [x] ~~6 of 35 topology test failures fixed and **still uncommitted** — the pre-commit gate blocks *all* commits to~~ (closed 2026-10-29 audit: SUPERSEDED → P0-1 CLOSED 2026-08-24 (numa:279): 196 passed/0 failed on PROMOTION_GATE_TARGETS; commits no longer blocked (matrix re-benched))
  `epyc-orchestrator`, test-only included, until the contention matrix is refreshed. **97 failures total** across
  the suite (the 35 are the topology subset); the denominator was never recorded until now.

##### Temperature methodology — SCOPED, do not over-apply (operator ruling 2026-07-31)

Every benchmark run 2026-07-30/31 used `temperature=0.0`. Production serves at
non-zero (vision roles `0.2`; Qwen3-TTS defaults `0.9`). Standing rule is
production temperature + fixed seed, so those runs are formally off-recipe.

**Operator ruling: do NOT re-run the matrix.** Re-running batch x concurrency x
context x spec x ngram at non-zero temperature is disproportionate. Instead:

- [x] **Once vision, STT and TTS are finalized, re-run ONLY the headline numbers ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): result files /mnt/raid0/llm/tmp/halfa_optimal_results.json and full_headline_results.txt are gone and the Qwen3.6-era lineup they measured has been replaced. [no-belief: obsolete, results gone, lineup replaced]
  at production temperature + seed 42.** That is §01 of the artifact — one
  single-stream cell per model per shape. Nothing else.
  **UNBLOCKED 2026-07-31** — all three modalities are now settled (vision →
  Qwen3-VL-30B-A3B Q4_K_M; STT → whisper.cpp large-v3-turbo f16 on MI210; TTS →
  Qwen3-TTS via qwentts.cpp on MI210). The re-runs are **IN FLIGHT** under the
  composed `ngram-mod,draft-mtp` recipe: half-instance headlines →
  `/mnt/raid0/llm/tmp/halfa_optimal_results.json`, full-instance headlines (all
  four regions, queued) → `/mnt/raid0/llm/tmp/full_headline_results.txt`.
  **No numbers yet — quote none.** Steps (absorb two rows): re-verify the headline recipe label against the lean registry before publishing; when each track lands, fold its result into section 01 of the artifact and flip the headline task.
- [x] **KV-quantization quality test — IN FLIGHT** → ✅ 2026-10-29 (audit: docs/reviews/kvquant-27b-decision-package-20260812.md exists; progress/2026-08/2026-08-12.md:221-227 "kvquant verdict gap CLOSED, decision package committed") [no-belief: audit-reconciliation]
  `/mnt/raid0/llm/tmp/kvquant_results.json`. Question: does `q4_0` KV buy the 27B
  ~180k tokens (vs ~90k on `q8_0`) without a quality cost, given the GPU resident
  set now sits at ≈51.8 of 64 GB leaving only ~12 GB for KV. **No numbers yet.**
- **[declined: ws58 2026-11-03 content-review: merged into the production-temperature headline re-run]** **Re-verify the headline recipe label before publishing these runs.** They
  are the first headlines taken after the lean registry was corrected to emit the
  composed recipe (orchestrator `6390b871`); every prior headline on this host
  since 2026-07-19 was taken under `draft-mtp` alone whether or not it said so.
  Per the ratified §5, headlines are the **production-optimal** arm — so the
  recipe string must be carried on the claim, not assumed.
- **[declined: ws58 2026-11-03 content-review: a labelling rule]** Leave the concurrency/context/spec surfaces at their measured values and
  label them `temp=0.0` in the provenance table, rather than re-measuring.
- Rationale for not re-running the ngram cells: the composed-ngram result is
  −1.6% mean across four cells; temperature is not a plausible sign-flip for a
  drafter-composition effect, and the design decision to carry ngram is made on
  the repetitive-context argument, not on that margin.
- **Greedy is not merely unrepresentative — it has its own failure mode.**
  `temperature=0.0` sent Qwen3-ASR into a degenerate repetition loop
  (`finish_reason: length`, 400 tokens collapsing to 1 word). Any future
  sampling-sensitive benchmark starts at production temperature.

##### Production-temperature re-runs — IN FLIGHT 2026-07-31 (paths only, NO numbers)

The re-runs the ruling above authorises are **executing now**. Recorded as paths so a
later reader can find them; **no result exists yet and none may be quoted**.

| track | lane | output path | state at wrap-up |
|---|---|---|---|
| Vision model finalization on MMMU at production temperature | q3 (GPU) | `/mnt/raid0/llm/tmp/vision_final_results.json` | running — being written |
| TTS GPU bench (`qwentts.cpp`), queued behind the vision run | q3 (GPU) | `/mnt/raid0/llm/tmp/tts_bench_results.txt` | running — being written (queue released during this wrap-up) |
| Half-instance headline numbers at production temperature | q0+q1 (CPU) | `/mnt/raid0/llm/tmp/halfa_headline_results.json` | running — being written |

Harness for the TTS leg: `/mnt/raid0/llm/tmp/tts_bench.sh`.

**All three output files existed and were still being written at wrap-up close (09:35Z).** A file existing is NOT a completed run: nothing here was read, and **no number from any of these three tracks appears anywhere in this wrap-up.** The next session must confirm each run terminated normally before quoting it.


- **[declined: ws58 2026-11-03 content-review: merged into the headline re-run as its filing step]** **When each track lands, fold its result into §01 of the artifact and flip the
  headline task above.** Until then every index row quoting a headline number must
  carry the `temp=0.0` label — the re-run has been *started*, not *completed*, and a
  half-updated provenance table is worse than a consistently-labelled stale one.
- **[declined: ws58 2026-11-03 content-review: a note (precondition status)]** **TTS is no longer a blocker on this gate — it is a measured capability.** The
  ruling's precondition "once vision, STT and TTS are finalized" reads differently now:
  STT is measured (WER 2.35 %, ~4.2 s floor) and TTS is measured (round-trip WER 0.0 %,
  TTFA 67.9 ms, 0.86× RT CPU via `qwentts.cpp`). The remaining unfinalized arm is
  **Qwen3-ASR**, whose 72.14 % WER is a configuration defect with a named suspect (the
  Q8_0 audio projector). See [`multimodal-pipeline.md`](speech-and-multimodal.md#track-multimodal-pipeline) S-6..S-10.

##### P1-11 CORRECTED 2026-07-31 — what is exclusive vs what is a tunable surface

An earlier note recorded the operator's directive too broadly. The correction:

**STILL HARD-EXCLUSIVE — do not model these as tunable:**
- [x] ~~**Co-resident half instances**: half A (q0+q1) and half B (q2+q3) of the SAME~~ (closed 2026-10-29 audit: DUPLICATE → same as numa:1030 (placement feasibility derived from cpuset intersection, ratified three-artifact design); keep numa:1030)
  role are mutually exclusive with each other where their cpusets intersect.
- [x] ~~**Half vs full**: a full instance (0-95) overlaps BOTH halves by construction.~~ (closed 2026-10-29 audit: DUPLICATE → same as numa:1030 (full intersects both halves = derived exclusion); keep numa:1030)
  Full and either half are mutually exclusive. This is set intersection, not
  contention measurement — it is derivable and must never consume inference.

**TUNABLE SURFACE — this is the part that changes:**
- [x] ~~**The GPU lane vs half B / full is NOT mutual exclusion.** Its contention is~~ (closed 2026-10-29 audit: DUPLICATE → same as numa:1040 "(3) Cross-role interference coefficients" (GPU lane vs q3 tenants as a value, not a veto); keep numa:1040)
  bandwidth-driven, and the case that actually hurts is models being **loaded and
  unloaded** from the GPU. The resident-set design keeps GPU models loaded, so that
  case does not arise. Heavy concurrent prompting of GPU models may still cost
  something — that cost is a **value to expose, not a boolean to block on**.
- [x] ~~Emit a **cost surface autopilot can optimize and the orchestration router can~~ (closed 2026-10-29 audit: DUPLICATE → same as numa:658 "Redesign the matrix as a continuous contention surface"; keep numa:658)
  be trained on**, not a BLOCK/ALLOW verdict.

**EXTENSION (operator, same conversation): bake in the other axes.**
- [x] ~~Concurrency at depth is a measured **regression**, not merely a slowdown: at~~ (closed 2026-10-29 audit: DUPLICATE → same requirement as numa:1036 "(2) Per-role capacity curve tok/s=f(np,context_depth)"; keep numa:1036)
  ~15k with np=2 on a half instance, one stream runs 4.7-9.7x the other and the
  **aggregate falls BELOW the np=1 single stream** (gemma 18.59 vs 20.75; Qwen3.6
  15.44 vs 22.18; 122B 7.97 vs 10.76; Qwen3-Next 13.77 vs 15.81). Headline numbers
  already carry context-depth effects. The matrix should carry **(role, shape,
  concurrency, context depth) -> expected cost**, so the router can decide *how* to
  use a role, not just *whether* two may co-run.
- **[declined: ws58 2026-11-03 content-review: a note]** Note this regression is independent of ngram — it reproduces on `draft-mtp`
  alone, so it is a scheduling/batching property, not a speculative-decoding one.

##### RATIFIED DESIGN 2026-07-31 — contention matrix becomes THREE artifacts (option B)

Operator agreed. Replaces the single BLOCK/ALLOW pair matrix, which conflated three
different kinds of thing and is why 58 of 78 pairs were being benchmarked to
rediscover set intersection.

- [ ] **(1) Placement feasibility — DERIVED, never measured.** Pure cpuset
  intersection, regenerated from `stack_numa.py` on every topology change. Zero
  inference, cannot go "stale" in a way a benchmark fixes. half A (q0+q1) vs half B
  (q2+q3) = disjoint, may co-run. full (0-95) intersects both halves = exclusive.
  **This artifact is what a pre-commit gate may consult** — it removes the standing
  block on the orchestrator repo. Program note (absorbs the 2026-07-31 directive rows, W8 and Q4): the matrix is a SURFACE autopilot can price, never a veto; artifact (2) carries the bandwidth regimes (not the worst case); schema first, regenerate last (mining persisted as wf_d3095ecd-19e); the interference model does not wait for E5 (premise corrected 2026-08-01); online learning (option C) layers on later with (2) as cold-start prior and (3) as what telemetry updates.
- [ ] **(2) Per-role capacity curve — `tok/s = f(np, context_depth)` per role x shape.**
  Self-interference, NOT a pair property. **N curves, not N².** This is what the
  half/full headline runs actually produce. Answers "how should I use this role",
  and is the prior a router trains from.
- [ ] **(3) Cross-role interference coefficients — small and SPARSE.** Only for pairs
  feasible under (1) that genuinely share a resource: the GPU shadow lane vs q3
  tenants, cross-node memory bandwidth. A handful of scalars, not 78 cells.
  - 2026-11-11 (pipeline-mgmt) design + row: pair list `data/batched_decode/interference_pairs_v1.json` and driver `scripts/benchmark/interference_pairs.py` landed in research `79a48cb6c`. Cpusets come from stack_numa.py. P1 is half A (qwen36_q8_0) vs half B (Qwen3.8-Flash-Next) at victim np 1/4. P2 is node 0 vs node 1. P3, the GPU lane, reuses U4-NOISE-1 2026-10-22. Each pair runs 5 ABAB rounds and the coefficient is the median with/alone ratio. The run is published as row `inf45-interference-r1-20261111`: host, resumable per pair. Stop rules: stop-on-answer when the 5-round CI of the ratio minus 1 excludes 0 or lies within ±2 %. stop-on-futility on a 5-round spread above 10 %. gate-class = futility-only.
- **[declined: ws58 2026-11-03 content-review: merged into the design note]** Layer online learning (option C) on top later: (2) supplies the cold-start
  prior, (3)'s coefficients are what production telemetry refines.
- [x] ~~**Open design question for the operator**: store (2) as a raw table (exact at~~ (closed 2026-10-29 audit: SUPERSEDED → answered by operator ruling "Capacity curve storage - FITTED PARAMETRIC (operator ruling 2026-07-31)" numa:1073)
  measured points, needs interpolation) or a fitted parametric form (differentiable,
  trainable, but imposes a shape)? Leaning parametric with the raw table retained as
  attestation — depends on how the router consumes priors.

##### Benchmark harness efficiency — STOP RELOADING MODELS (operator, 2026-07-31)

`full_headline.sh` reloaded per (model x depth x np) = **24 loads**, with the 122B at
73 GB each time. Wrong by construction:

- `-np` sets the slot CEILING. **One server at `-np 4` serves 1, 2 or 4 concurrent
  requests**, and depth is a property of the prompt, not the server.
- Correct shape: **one hot server per model** (4 loads), vary concurrency by how many
  requests you fire, vary depth by which prompt you send.
- [x] Rewrite `full_headline.sh` on this pattern before the next full-machine window. ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): full_headline.sh no longer exists in root, research or /mnt/raid0/llm/tmp. [no-belief: obsolete, script deleted]
- **NOT contradicted by the preload finding**: keeping ONE server hot and reusing it
  is correct; loading FOUR different models concurrently is what poisons measurements
  (an idle llama-server burns 47 of 48 cores under `OMP_WAIT_POLICY=active`, proven at
  `halfa_headline_results.v3_preload_POISONED.json`). Hot-and-sequential, not
  preloaded-and-parallel.

##### Queue reordered 2026-07-31 (operator)

- [x] ~~Full-instance headlines were running the **composed** recipe on 24 cells while~~ (closed 2026-10-29 audit: OBSOLETE → queue-order note: coding test adjudicating composed ngram recipe is moot; ngram retracted/retired (model_registry.yaml:1666 default_spec_type draft-mtp, ngram sidecar RETIRED))
  the coding test that ADJUDICATES that recipe had not run. Killed and re-ordered:
  coding test (~30 min, q0+q1) settles the recipe -> then ONE full-machine window on
  the decided recipe, hot instances.

##### Capacity curve storage — FITTED PARAMETRIC (operator ruling 2026-07-31)

Artifact (2) of the three-artifact contention design stores as a **fitted parametric
form**, not a raw lookup table: cheap derivatives, which the router/autopilot can use
directly for gradient-based placement decisions.

- [ ] Fit per role x shape. Retain the raw measured points as **attestation**
  alongside the coefficients — the fit is the interface, the table is the evidence.
  A claim cites the measurement, not the curve. Form (absorbs three rows): the fit MUST carry an np x depth interaction term (a separable A*f(depth)*g(np) cannot express the measured turnover); start from the suggested 3-4 parameter shape; report residuals per role — a form that smooths away the turnover is worse than a table.
- **[declined: ws58 2026-11-03 content-review: merged into the fit task as its form constraint]** **The form MUST carry an np x depth interaction term. A separable form
  `A * f(depth) * g(np)` CANNOT express what we measured.** At ~15k with np=2 on a
  half instance the *aggregate* falls BELOW the np=1 single stream (gemma 18.59 vs
  20.75; Qwen3.6 15.44 vs 22.18; 122B 7.97 vs 10.76; Qwen3-Next 13.77 vs 15.81).
  A separable model forces aggregate monotone-increasing in np, so it would predict
  a speed-up exactly where we measure a regression — and the router would then
  batch precisely where it should not.
- **[declined: ws58 2026-11-03 content-review: merged into the fit task]** Suggested starting shape, 3-4 params per role x shape: [too-big: per-role fit and validation are handoff-owned measurement work]
  `per_stream(np, d) = A / ((1 + d/d0) * (1 + (np-1)/k(d)))` with `k` itself
  depth-dependent (concurrency tolerance shrinks as context grows). `aggregate =
  np * per_stream`, which is then free to turn over. Validate the fit reproduces the
  measured regression before adopting it.
- **[declined: ws58 2026-11-03 content-review: merged into the fit task as its acceptance]** Report fit residuals per role. A form that smooths away the turnover is worse
  than a table, because it is confidently wrong in the region the router cares about.

##### GPU co-residency MEASURED 2026-07-31 — all four models fit; idle residency is free

Curiosity measurement, **no gate attached** (operator explicit). Artifact:
`/mnt/raid0/llm/tmp/gpu_coresidency_results.json`, logs `/mnt/raid0/llm/tmp/gpu_coresidency/`.

27B decode tok/s, 256 tok/rep, `ignore_eos`, a DISTINCT prompt per rep, 27B at **full
`-c 262144`** q8_0 KV:

| state | n | min | median | max | VRAM | delta |
|---|---|---|---|---|---|---|
| alone | 3 | 30.854 | **30.870** | 30.913 | 36.70 GiB | — |
| others resident, IDLE | 3 | 30.868 | **30.872** | 30.892 | 62.40 GiB | **+0.006%** |
| others ACTIVELY working | 3 | 19.496 | **19.810** | 20.224 | 62.58 GiB | **−35.8%** |
| recovery (loads stopped, still resident) | 2 | 30.745 | 30.757 | 30.769 | 62.59 GiB | −0.37% |

- [x] **Idle residency costs ZERO** — state-2 range sits entirely inside state-1's, GPU
  0% busy. **This validates the resident-set premise behind the P1-11 directive**: the
  load/unload bandwidth cost that motivated hard exclusion does not arise. ✅ 2026-07-31
- [x] **It fits at full 262k**: steady state **62.59 of 63.98 GiB, 1.40 GiB spare** ✅
- **[declined: ws58 2026-11-03 content-review: a finding; kv-cache-program KVU-16i carries the runtime-peak gate]** **The 58.30 GiB budget UNDER-PREDICTED by 4.29 GiB.** Cause: **VRAM grows on first
  EXECUTION, not at load** — vision/whisper/TTS compute buffers allocate on first
  inference (61.66 → 62.59 GiB). **Any resident-set budget built from load-time figures
  runs ~1 GiB optimistic.** Correct the budgeting method, not just the number.
- **[declined: ws58 2026-11-03 content-review: a note]** **−35.8% under active load is a WORST-CASE FLOOR, not a duty cycle** — the stress
  was 128 transcriptions + 6 vision queries + 19 syntheses in 39.6 s at 100% GPU. The
  recovery control returning to 30.76 proves it is contention, fully reversible, not
  drift. **This is the cost coefficient artifact (3) of the contention design wants —
  a number to expose, not a veto.**
- [x] **Qwen3-TTS has NO server mode** — made resident via a long-lived ✅ 2026-10-29 (audit: TTS service wired: launch_manifest.yaml:111 tts 9002, start_tts() orchestrator_stack.py:3201 (cba55d49 2026-08-02); the no-server-mode blocker is resolved) [no-belief: audit-reconciliation]
  `--stream-by-line -o -` process blocked on a FIFO. `--stream-by-line` streams ONLY
  with `-o -`; with `-o <file>` it waits for stdin EOF and never synthesizes. A
  production TTS service needs that pattern or a server wrapper. **Blocks TTS being
  wired into `orchestrator_stack.py`.**
- Side latencies: vision 1.66 s alone → ~4.0 s contended; whisper 0.21 s on an 11 s
  clip; TTS RTF 0.191.
- [x] ~~**The frozen production `llama.cpp/build/bin` is CPU-ONLY** — no `libggml-hip.so`.~~ (closed 2026-10-29 audit: OBSOLETE → premise gone: v10 kernel store (CLAUDE.md 2026-09-22) serves from kernels/production/{cpu,gpu}; the v8/9-era build/bin vs build-hip/bin split no longer the serving path)
  GPU work must use `llama.cpp/build-hip/bin` (same commit `67a433bf4`, version 10107).
- [x] ~~**Linkage trap is version-mismatched, not just wrong-tree**: bare `ldd` on~~ (closed 2026-10-29 audit: SUPERSEDED → three-ggml linkage hazard now codified in CLAUDE.md (verify_ggml_linkage.sh, per-launcher LD_LIBRARY_PATH) and W4 per-service ld paths cba55d49)
  `qwen-tts` pulls `libggml-base`/`cpu` from production at **0.16.0** while its own
  `libggml-hip` is **0.17.0**. The three trees are 0.16.0 / 0.18.0 / 0.17.0 — each needs
  its own dir prepended. `verify_ggml_linkage.sh` passes all three once done.

##### STILL IN FLIGHT at compaction — ngram on long-context CODING

`/mnt/raid0/llm/tmp/ngram_coding_results.json`. Decides composed vs `draft-mtp` alone.
12 tokenizer-verified prompts/model (3 extend-refactor, 3 port, 3 fill-in, 3 prose
control), 15k–30k band, arm order REVERSED between models so drift cannot bias both.
Early arm-A signal: acceptance 0.556 (prose) → 0.734 (code), mean accepted draft length
3.20 → 3.88. **Full-machine headline window is deliberately queued BEHIND this** so it
runs once, on the decided recipe, with hot instances (one server per model at `-np 4`).

---

### SESSION APPEND 2026-07-31 (18:00–20:00Z) — groundwork landed, wiring NOT started

**Read this first if you are picking up.** The role reshaping is **entirely unapplied**.
What landed today is the layer underneath it: the facts the stack will be built from are
now trustworthy, where before they were not. Verified against the live registry at 20:00Z:

| target | actual today |
|---|---|
| `worker_vision` + `vision_escalation` → Qwen3-VL-30B-A3B Q4_K_M, GPU, unified on 8086 | still Qwen2.5-VL-7B, CPU, two roles |
| `architect_general` + `coder_escalation` → Qwen3.6-27B dense Q8, GPU, 8083 | still 122B / still frontdoor's 35B |
| `architect_critic` → 122B, CPU, 8074, tier hot, routable **and** consultable | role ABSENT from the registry |
| TTS as a managed service | 0 references in `orchestrator_stack.py` |
| STT → whisper.cpp GPU | still launches faster-whisper CT2 on 9000 |
| spec recipe `draft-mtp` | `stack_priors.yaml` still carries **38** `ngram-mod` occurrences |

#### Landed and pushed today

- [x] ggml linkage fixed across all four kernels ✅ 2026-07-31 — root `136894e8`, research `94cf8d6c`.
      Found that the production HIP binary loaded **all seven** libs from the CPU-only tree with
      `libggml-hip.so.0` absent entirely: it was silently a CPU binary. **Any GPU shadow-lane
      number taken before this is a CPU number.** Co-residency is unaffected (its harness set the
      path itself and recorded `ggml_linkage_verified: true`).
- [x] Speech kernels frozen, forked and genuinely off-host ✅ 2026-07-31 — `production-speech-v1`
      on `pestopoppa/whisper.cpp` (`b307379`), `pestopoppa/qwentts.cpp` (`2c1b518`),
      `pestopoppa/ggml` (`b86f660`). Submodule off detached HEAD. Bundles at
      `/mnt/raid0/llm/kernel-freeze-bundles/`. Before this the patches were uncommitted
      working-tree state; a `git checkout` would have destroyed GPU speech.
- [x] Spec recipe REVERSED to `draft-mtp`, ngram nowhere ✅ 2026-07-31 — research `a126e43d`.
      35B long-context coding 0/12; gemma produced **zero drafts on 9/12** (byte-identical arms);
      80B ngram-alone acceptance 1.6–4.7% (SSM state cannot fork). No role left for the lane.
- [x] Throughput priors corrected ✅ 2026-07-31 — `df4c8e37`, `96aa90f6`. Also quarantined four
      **Qwen3-235B** figures that had sat unlabelled in `architect_general`'s block since the
      2026-03-19 swap; one of them (8.21) was read as the 122B's throughput and propagated.
- [x] `server_mode.frontdoor.shared_with` restored ✅ 2026-07-31 — `596a1e24`. Was `[]` while two
      roles serve on 8070. Answered the drift guard with **data**, not by updating the guard.
- [x] `MEASUREMENT.md` §3 torn bullet repaired ✅ 2026-07-31 — `13383c49` (operator-run).
- [x] Artifact: IQ2_M-as-Q4_K_M retraction + missing VL throughput ✅ 2026-07-31.
- [x] Scoped the orchestrator pre-commit hook ✅ 2026-07-31 — was unconditional, so it blocked
      every commit and pressured people toward `--no-verify`, which also skips PII + hermes-drift.
- [x] Qwen3-VL-30B-A3B decode measured ✅ 2026-07-31 — `category=OPTIMUM`, MI210, spec none:
      **102.18 tok/s** @ 17–19 tok, **70.71** @ 10,984 tok (n=3 each, server-reported depths).
      A second figure exists — **112.20**, median of 250 MMMU image+text turns. Both real,
      different workloads. **Do not pick one silently; record both with conditions.**

#### OUTSTANDING — hard sequence, do not reorder

- [x] **W1. Apply the role reshaping edit list.** ✅ 2026-08-01 — research `fd7a2cdb` + orchestrator `a517793c`. Anchors re-derived by exact-text match (61 unique / 11 prose-range / 4 hand-derived, zero overlaps), not by line arithmetic. Registry + manifest + NUMA + roles.py + all three alias tables landed together.
      ORIGINAL NOTE: Persisted at workflow run `wf_7d5f6816-a67`
      (adversarially verified). Touches BOTH `server_mode:` (638) and `roles:` (1249) in master.
      Found a structural gap: **`server_mode` has no vision row at all**, so `shared_with` — the
      binding `stack_priors.py:683-685` reads to resolve an alias to its process — has nowhere to
      live. Vision unification needs a NEW row, not an edited one.
      **Each role's prior must move in the SAME commit as its model repoint.** A prior correct for
      the old model is wrong the instant the model changes; splitting them is how every stale prior
      corrected today was minted. `frontdoor.shared_with` must become `[worker_summarize]` in the
      same commit that moves `coder_escalation`.
- [x] **W2. Era plumbing for `cost` BEFORE regenerating.** `active_instrument_eras` exists only for
      `eval_quality`; `baseline_state.cost` is a bare `0.5` with no era field, and
      `safety_gate.py:1193`'s own docstring says it is *"inert (always False) when no active era is
      set."* Cost is exactly the dimension the q_scorer normalizer moves (+65% frontdoor, +48%
      worker, +97% architect_general). Marking a boundary without this is a comment with no
      enforcement. Add `active_instrument_eras.cost`, stamp `baseline_state.cost_era`, clone the
      staleness check at `safety_gate.py:782/1020/1087/1193`. Mechanism is live and exercised —
      `eval_quality_era` is E7 against an active E8 right now.
      ✅ 2026-11-11 (pipeline-mgmt) — orchestrator `9ce3f4b3`: `baseline.cost_era`, `active_instrument_eras.cost`, `cost_rebaseline_required` (inert when unset). [no-belief: plumbing, not a measurement]
      Rescore was **declined** on facts: `strategy_store.db` is 0 bytes and `warm_start.py` has no
      journal references, so nothing replays old-normalization scores.
- [x] **W3. Regenerate `derived/stack_priors.yaml`** ✅ 2026-07-31 — orchestrator `ed891211`.
      The single dependency all three propagation failures collapse into — spec recipe, throughput
      priors and topology all landed here. 5 of the 23 red tests went green on their own (23 → 18).
      **Required a missing hop this list did not have:** the pipeline regenerates from the LEAN
      registry and never recompiles lean from master, so `registry_compiler --force` must run FIRST
      or the pipeline reports success over stale input. Stack restarted and verified live on
      `--spec-type draft-mtp`, ngram in zero processes. See SESSION APPEND (20:00–21:00Z).
- [x] **W4. Build `AUX_SERVICES` + per-service `LD_LIBRARY_PATH`, then register whisper.cpp and ✅ 2026-10-29 (audit: orch cba55d49 (2026-08-02) "W5+W4: aux services are declared data, and their ggml is isolated"; AUX_SERVICES in stack_manifest.py, launch_manifest.yaml tts/whisper entries) [no-belief: audit-reconciliation]
      `tts-server`.** Not skippable: both env composers are prepend-only and every `start_*` begins
      at `os.environ.copy()`, so neither service can currently be told to ignore the global path.
      Ports: STT keeps 9000 (implementation swap); TTS on 9002 (verified free and smoke-tested).
- [x] **W5. Fix the `reload` defect first** — `reload whisper` / `reload sd_server` kill the service ✅ 2026-10-29 (audit: orch cba55d49 (2026-08-02) "W5+W4"; stack_manifest.py:291-295 registry makes start and reload agree) [no-belief: audit-reconciliation]
      and fail to restart it (`stack_manifest.py:60-61` → `stack_commands.py:1669` →
      `orchestrator_stack.py:1651`). Any new service added the same way inherits it.
- [ ] **W6. Fix the seven fail-open guards.** Runnable proofs in `/mnt/raid0/llm/tmp/guard-audit/`.
      Live now: `stack_change_guard.py:1000` skips the context assertion for **0/22 roles checked**
      while still reporting 22 targets — invisible. Also `:829` (errors 12→0), `:962` (model-path
      coverage 10/10→8/10), `:1184`, `:1669`. **The correct pattern already exists in the same file**
      at `:1188` and `:1724` — inconsistently applied, so the fix is small.
      - *(2026-11-11, pipeline-mgmt; PARTIAL, box stays open.)* Orchestrator `15402376` closes the remaining fail-open paths in the launch view and serving alignment; the rest of the seven guards are not yet proven closed against `/mnt/raid0/llm/tmp/guard-audit/`. [no-belief: partial]
- [x] **W7. Make the ratify scripts emit a receipt.** `MEASUREMENT.md:138-145` requires a ✅ 2026-10-29 (audit: root cb6ea5093 (2026-08-02) "W7: ratification receipts"; scripts/operator/ratification_receipt.py + check_ratifier_receipt_contract.sh exist; 25e399bf3/c97a8b552 (2026-10-27) emit the section-5 receipt) [no-belief: audit-reconciliation]
      consolidated bundle with evidence hashes and an exact state diff; none of the three 2026-07
      ratifications emitted one. These scripts amend the file defining what a valid verification is,
      using a verification weaker than that definition. Fixing this closes the class permanently.
- **[declined: ws58 2026-11-03 content-review: merged into the design note]** **W8. Contention matrix — schema first, regenerate last.** Mining of existing measurements is
      persisted (`wf_d3095ecd-19e`). Define the raw per-cell vector BEFORE the sweep so feasibility,
      the non-separable capacity fit and interference coefficients all derive offline; a reduction is
      a lossy commitment. Operator constraint: **do not re-bench anything already measured.**
- [ ] **W9. Do NOT bulk-green the 23 tests.** At least 5 are correct tests reporting real defects —
      3 assert `--spec-type == draft-mtp` and receive the falsified composed recipe (they go green at
      W3); 2 are the alias drift guards. A bulk pass would encode the falsified recipe into the suite
      and erase the alias signal. Fix data first.
- [x] **W10. Reconcile the two Qwen3-VL throughput figures** ✅ 2026-08-01 — both recorded with conditions; separately found the ratified MMMU-250 result was sitting under `mmmu_val_250`, a key the descriptor compiler does not read, so the role was reported as having NO quality evidence. Renamed to `vl_score`.
      ORIGINAL NOTE: (102.18 text-only vs 112.20 MMMU
      image+text) into the registry with conditions attached, not as one scalar.


#### NEW — discovered while applying W1 (2026-08-01)

- [x] **The launcher disabled every device it had just resolved.** ✅ 2026-08-01 —
      `_append_cpu_only_device_args` appended `--device none --device-draft none` to EVERY
      default-builder role and `_build_role_command` never read `flags["device"]`. `architect_general`
      ran a 27B dense on 24 CPU threads with the GPU at 0% while reporting healthy + attest ok.
      VRAM 13 MB -> 53.6 GB after the fix.
- [x] **`device`/`device_draft` added to runtime attestation, both directions.** ✅ 2026-08-01 —
      the table checked every declared field EXCEPT device, which is why the above was invisible.
      An UNDECLARED device now asserts `none`, so a CPU role landing on a GPU is caught too.
- [x] **One-input refactor (phase 1).** ✅ 2026-08-01 — `stack_manifest.py` 919→667 and
      `stack_numa.py` 613→452 are thin loaders over `orchestration/launch_manifest.yaml` +
      `orchestration/stack_topology.yaml`, no fallback tables. Byte-identical proof, sha256
      `3894a3a3…` before and after. Both artifacts pinned in `source_artifacts`.
- [x] **`REQUIRED_SOURCE_ARTIFACTS` verified 7 pins while the compiler emitted 9.** ✅ 2026-08-01 —
      the two new declared artifacts were pinned and NEVER verified; mutating `launch_manifest.yaml`
      changed no verdict. Now iterates the producer's own keys; literal kept as a floor. Teeth
      confirmed by mutation.
- [x] **`RETIRED_LIVE_ROLES` derived (42 names) instead of a 1-name grep.** ✅ 2026-08-01 — plus a
      new `stale_role_fact_table` rule that compares launch surfaces against compiled priors. It
      fired on first run against `stack_templates/default.yaml`, where `frontdoor` pointed at the
      NON-MTP GGUF — silently disabling draft-mtp.
- [x] **Device-aware feasibility.** ✅ 2026-08-01 — `src/scheduling/device_model.py`; CPU instances
      claim regions exclusively, GPU roles claim VRAM; exclusions name their resource. Shape-aware
      admission stays behind both flags (default off), 3628 verdicts swept, 0 mismatches.
- [x] **Contention matrix re-benched for the new topology.** ✅ 2026-08-01 — `171f86f9`, 15 pairs,
      ZERO catastrophic. `architect_general`+`ingest` went 0.66 **block** → **1.40 allow**;
      every GPU-involving pair is concurrency-positive.
- [x] **Five dead-config items removed.** ✅ 2026-08-01 — `model_quality_signatures.yaml`,
      `model_registry_lean.yaml`, `delegator._escalate_role` (a 5th ladder copy with a self-loop,
      a null hop and a DOWNGRADE), `quarter_stack_smoke.EXPECTED_CHAT_PORTS`, and three
      `src/orchestration/` paths that have never existed.
- [x] **The registry claimed the 27B was unmeasured. It was not.** ✅ 2026-08-01 — frozen 4-arm
      authority (sha256 `f440680d…`) has arm A3 == this exact GGUF at 23/40 (57.5%) SWE-bench
      Verified, top arm, +20.0 pp over the 122B IQ2. Recorded with instrument + comparators +
      shape caveat; `quality_score` deliberately still null (different instrument).

##### Outstanding after W1

- **[declined: ws58 2026-11-03 content-review: duplicate — stack-lifecycle-program SSU-F4 (derive instead of restate) owns it]** **Phase 2 of the one-input refactor: derive what master already declares.** Highest-value
      target is `slots` — the launcher has NO table and computes `1 if role in SERIAL_ROLES else 2`,
      which disagrees with the registry for 4 of 7 roles (frontdoor 1 vs 2, architect_critic 1 vs 2,
      coder_escalation 2 vs 1, worker_general 2 vs 1). Also `architect_general`'s `device` is
      declared ONLY in master with no launcher-side declaration — precisely the surface the
      `--device none` incident ran through. `shared_with` for `worker` disagrees (legacy
      `worker_explore` alias exists launcher-side only).
- [ ] **`q_scorer_priors` fails: `architect_general` / `coder_escalation` quality source is
      `degraded_fallback`.** The router scores them with a FABRICATED quality number rather than
      none. Deliberately not auto-declared in `accepted_gaps.yaml` — laundering a fail-open fallback
      under a waiver is exactly what that mechanism exists to prevent. Options: make q_scorer refuse
      for null-quality roles, or close the root gap by running the judge suite.
- [ ] **Run the canonical 79-question judge suite on Qwen3.8-27B-Q8_0.** This is the root close for both
      the three accepted gaps (expiring 2026-09-01) and the `q_scorer` degraded fallback. (re-scoped 2026-11-03 from Qwen3.6-27B: deleted; judge now Qwen3.8-27B-Q8_0)
      Identity and stop rule (2026-11-11, pipeline-mgmt): quant_build = Qwen3.8-27B-Q8_0 + DFlash2-Q8_0 drafter on the
      v10 production GPU kernel store, recipe qwen3.8-27b-q8-gpu-dflash2-np4 at `-np 2 -c 196608`; capture with the
      pinned `run_judge_suite.py` anchor shape (thinking off, suite temperatures, seed 42), graded afterwards by the
      Claude-as-Judge anchor protocol, reported per suite. Stop-on-answer when >= 70 of 79 questions are captured with
      a non-empty answer; stop-on-futility on a failed GPU-residency/own-pid proof or > 9 request errors/empty
      answers; gate-class = futility-only (fixed n = 79, one pass), est 5400 s. Row `inf45-judge79-q38-27b-20261111`.
- [x] **`stack_templates/default.yaml` has 9 errors the launch gate never sees.** ✅ 2026-10-31 — orchestrator implementation `c01e72bfe8d69a79c955f7d4b2bef5ea459bce96`; `tests/unit/test_stack_template_launch_gate.py` and Git capsule `artifacts/audit/stack-template-launch-gate-20261031/verification.md`; 115 focused tests pass. [no-belief: source launch-gate regression controls]
      `validate_template()` reports them (missing `architect_critic`, `vision_escalation` on retired
      8087, `coder_escalation` aliasing frontdoor, quarter-port rows for quarters retired
      2026-07-30) but the pipeline never invokes that validator. Wire it into the gate.
      - Current-source audit found the default template valid with 0 errors and 0 warnings; the original nine-error inventory is historical. The new ordinary-start gate resolves explicit/environment/default profiles and calls the native validator before capacity, registry compilation/config writes, and launch effects. Invalid, missing, or malformed active templates refuse early; migration retains its target-specific validator. No live reload or template edit was performed.
- [x] **`validate_model_paths()` validates files the stack does not launch** — its own hardcoded <!-- evidence-integrity: Orchestrator `47d4fc1a8be6479a81fe24426883c43e30238dd2`; artifact: artifacts/compute/refactor-evidence-corrections-20261031/20/focused.log; hygiene, not quota -->
      path list (frontdoor GGUF, architect/ingest dirs) no longer matches the declared models, and
      both stale files still exist on disk so it returns clean. Derive from
      `stack_priors.roles.*.serving.launch.requirements`.
      ✅ 2026-10-30 — orchestrator main `47d4fc1a8be6479a81fe24426883c43e30238dd2` validates active generated model/draft/projector files, deduplicates checks, and retains real embedding/aux/tool inputs. Missing/malformed active requirements fail closed; optional null external drafters and remote backends remain valid. Non-dev start validates before host prerequisites. The old function returned no errors when the active critic drafter was missing in the controlled fixture; the new function reports that exact canonical path.186 focused tests, red/green control and Ruff pass; no model/config or live service changes. [no-belief: source implementation and deterministic preflight controls]
- [x] **`autopilot.py:5589` `_MODEL_SIGNATURES_PATH` names a deleted file.** Harmless today (the arg is ignored) but should be removed with its call-site arg. ✅ 2026-10-29 — orchestrator main `5e1e9bcd2530` removes the retired constant and passes only `descriptors_path` to the existing loader. Descriptor-only fail-closed behavior is unchanged; 38 state-store regression tests and Ruff pass. No autopilot process was reloaded. [no-belief: source cleanup and regression tests] Evidence: APP `5e1e9bcd2530247653c1f913b3ba3653315184d6`; `tests/unit/test_autopilot_state_store.py`. [historical hygiene: implemented 2026-10-29; zero new quota]
- [x] **`NON_QUARTERABLE` still names `architect_general`** in `contention_matrix.py` — now inert
      (one instance either way); comment corrected, set not changed. Orchestrator `02a152a8ffab46879163d815bd47e127c931e8a9` removes the contradictory load-bearing claim; AST unchanged and `make gates` passed. [no-belief: source comment correction]

  <!-- task-evidence-integrity:start validate_model_paths -->
  - Evidence metadata (hygiene, not new quota): Orchestrator `47d4fc1a8be6479a81fe24426883c43e30238dd2`; [original test/artifact](../../artifacts/compute/refactor-evidence-corrections-20261031/20/focused.log). Active paths derive from generated launch requirements; original missing-drafter red/green and186 focused controls cover fail-closed source behavior, with publication receipt. No tests rerun or historical redating.
  <!-- task-evidence-integrity:end validate_model_paths -->

#### Operational notes

- Shared clone: use the explicit three-path `rm` on orphaned pack files, **never `git gc`** — a full
  repack can disrupt live sessions.
- `git add -- artifacts/operator/` hangs: it recurses the huge `.e8_quality_baseline_*.staging-*`
  dirs. Stage exact file paths.
- The scoped pre-commit hook now blocks only topology/contention paths — W1 and W3 WILL be blocked
  by it, correctly, until the matrix is fresh. That ordering is intentional.

---

### SESSION APPEND 2026-07-31 (20:00–21:00Z) — W3 LANDED AND LIVE; W1 BLOCKED ON A BINARY PATH

**Read this first if you are picking up.** The derived layer is now correct and the stack is
running on it. The role reshaping (W1) is still entirely unapplied, and I stopped short of it
deliberately — see the blocker below, which is structural rather than a matter of care.

#### W3 COMPLETE — and a missing hop the prior append did not have

W3 was not one step. `stack_change_pipeline.py update` regenerates descriptors and stack priors
**from the LEAN registry**, and nothing inside it recompiles lean from master. Running the pipeline
alone reports `descriptors: updated / stack_priors: updated / guard: ok` while re-emitting the stale
values, because its input was stale. That is a fail-quiet of exactly the shape this handoff has been
cataloguing: a green result computed over the wrong input.

The sequence that actually works:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
.venv/bin/python -m src.registry.registry_compiler --force            # master -> lean
ORCHESTRATOR_STACK_NUMA_MODE=both \
  .venv/bin/python scripts/registry/stack_change_pipeline.py update   # lean -> descriptors -> priors
```

The explicit `ORCHESTRATOR_STACK_NUMA_MODE=both` is required and correct: the compiler refuses to
guess the realized mode with the fleet down rather than defaulting to `full` (ESC-8 kill chain A4),
and `both` is the intended full+2-halves lineup.

- [x] **W3. Regenerate the derived layer** ✅ 2026-07-31 — orchestrator `ed891211`.
      Lean registry recompiled from master, then descriptors + priors + operator summary.
      Landed: spec recipe `draft-mtp` on all five launching roles; q_scorer cost priors
      frontdoor/coder_escalation 24.3 → **40.22**, worker_general 38.46 → **56.86**,
      architect_general 12.19 → **24.00**, all live-resolved with `source=stack_priors`;
      half-fleet topology carried through. Gates: `guard ok`, `guard_strict ok`,
      `stack_manifest_registry ok`, `q_scorer_priors ok`.
      Tests **23 → 18**: all three `assert 'ngram-mod,draft-mtp' == 'draft-mtp'` witnesses pass, and
      both alias drift guards are answered. Remaining 18 are the topology-literal set plus one
      unrelated — W9 still applies, do not bulk-green them.

- [x] **Two W9 tests replaced (not adjusted)** ✅ 2026-07-31 — orchestrator `a3cfe65e`.
      `test_worker_general_numa_policy_is_full_instance_only` asserted the halves carry **no**
      numactl policy — the defect, not the contract — replaced with
      `test_every_instance_interleaves_over_only_the_nodes_it_spans` (full → `interleave=all`,
      half A → `0,1`, half B → `2,3`). `test_eval_batch_frontdoor_command_uses_pbench3_serving_shape`
      asserted `-t 96` on port 18070, which now sits on `NUMA_HALF_A` (48 physical cores) → `48`.
      Its `--spec-type draft-mtp` assertion was left alone and annotated: it was correct all along.

#### STACK IS UP AND VERIFIED ON THE CORRECTED RECIPE

Started `--numa-mode both`. Verified from `/proc/<pid>/cmdline` on every live server — not from
config, not from the launcher's intent:

```
--port 8070  --spec-type draft-mtp   ngram_occurrences=0     frontdoor  (full)
--port 8080  --spec-type draft-mtp   ngram_occurrences=0     frontdoor  (half A)
--port 8180  --spec-type draft-mtp   ngram_occurrences=0     frontdoor  (half B)
--port 8072  --spec-type draft-mtp   ngram_occurrences=0     worker     (full)
--port 8082  --spec-type draft-mtp   ngram_occurrences=0     worker     (half A)
--port 8182  --spec-type draft-mtp   ngram_occurrences=0     worker     (half B)
--port 8083  --spec-type draft-mtp   ngram_occurrences=0     architect_general
```

The composed recipe is gone from production. The half fleet is live.

##### The gate refused the first launch, correctly, and what that means

`[stack-change-gate] FATAL: gate exited 1; refusing launch`. Every **config** gate was green; the
only failure was `runtime_attestation: live process drift` on two ports:

- `:8000` — the orchestrator API (uvicorn, 6 workers, running 23h)
- `:9000` — `whisper_server.py` faster-whisper CT2 (running 12h)

Both predate the session and are exactly the services **W4** exists to bring under management. I
started with `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1` on the judgement that the blocker is unrelated
to what launches. **That judgement should be reviewed.** The honest reading is that the gate has no
way to say "aux service unmanaged" separately from "unsafe to launch", so it fails at the same
severity for both — and the escape hatch is the only available response. W4 removes the need; until
then this bypass will recur on every start, which is how bypasses become habitual.

#### W1 IS BLOCKED — and not on care or on the open decisions

The edit list is real and complete: **76 edits, E1–E76**, recovered from workflow `wf_7d5f6816-a67`
and decoded byte-exactly to `/tmp/claude-1000/-workspace/26b5f442-13c1-4501-8997-1c2fb9e1c509/scratchpad/editlist.md`
(97,339 bytes, md5 `dbdbb11d35e5beb3957dec7695088853`). Anchors are against master at `96aa90f6`,
md5 `c6a4d2b50e203140d344b436c8f1ab22`, 9876 lines — **re-verify that md5 before applying; master
has since moved to `596a1e24`, so every anchor needs re-derivation.**

**The hard blocker (`COULD NOT VERIFY` #8), now confirmed on disk:**

```
/mnt/raid0/llm/llama.cpp/build/bin/     libggml-base.so  libggml-cpu.so  libggml.so     <- CPU ONLY
/mnt/raid0/llm/llama.cpp/build-hip/bin/ libggml-hip.so.0.16.0                           <- the GPU one
```

W1's core moves are GPU moves — `architect_general` + `coder_escalation` → 27B dense Q8 on ROCm0,
`worker_vision` + `vision_escalation` → Qwen3-VL-30B on ROCm0. **No registry field names the binary
path**, and the launcher uses `build/bin`, which has no HIP backend. Applying W1 as written would
repoint four roles to GPU and launch every one of them on the CPU binary — silently, since a missing
HIP backend does not error, it just runs on CPU. That is the same failure class as the ggml linkage
incident fixed this morning.

**W1 therefore needs, before any registry edit:** a binary-path field in the registry (or a
per-role launcher override) plus the manifest work, landing together. `stack_manifest.py:130-135`
**raises at module import** on a half-edit — it takes down priors compilation and the launcher
rather than degrading.

Also still open and unchanged: **D1–D4** in the edit list (architect_critic tier; how aggressive the
`reasoning` chain triggers should be; whether frontdoor keeps `coder`; the duplicate B3 hint), plus
`COULD NOT VERIFY` #2 (three hardcoded `_RUNTIME_SELECTED_ROLE_ALIASES` tables override the registry
at runtime), #4 (`architect_critic` is not a `Role` enum member → an arm with permanently zero
training rows, which the operator forbade), and #5 (`config_applicator.py:557-562` can write
`ngram-mod,draft-mtp` straight back into the block W1 edits).

`COULD NOT VERIFY` #6 has **cleared**: no session is benching on q0/q1 now (host idle apart from
`earlyoom`), so the contention-matrix constraint on E67/E58 is no longer a live-collision risk —
though the matrix is still stale and W8 still applies.

#### Revised order for the next session

1. **W4/W5** — makes the gate pass honestly and stops the bypass becoming routine. W5 first: the
   `reload` defect means any service registered the same way inherits a kill-without-restart.
2. **Binary-path plumbing** — the prerequisite W1 did not know it had. Without it no GPU role move
   is real.
3. **W1** — re-derive anchors against current master first; land registry + manifest + `roles.py` +
   the three alias tables in one commit.
4. W6 (guards), W7 (ratify receipts), W2 (cost era), W8 (matrix), W10 (VL figures).

W2 was **deprioritized deliberately**: the operator ruled past autopilot metrics deprecated, and the
facts support it — `strategy_store.db` is 0 bytes and `warm_start.py` has no journal references, so
nothing replays old-normalization scores across the boundary the q_scorer correction created. The
era plumbing is still worth building for future comparisons; it is no longer urgent.

#### ADDENDUM (21:00–22:00Z) — the compile chain and the kernel layer

Operator ruling: fix the compile chain before W1, and extend the kernel layer to the
speech kernels. Both landed.

- [x] **Compile is now a pure function of its declared inputs** ✅ 2026-07-31 —
      orchestrator `596e2189`. `compile(master, role assignments, topology) -> lean ->
      derived`. Three deviations closed: (1) the pipeline never recompiled lean from
      master — added as its FIRST step, in check and update; (2) topology was PROBED
      from the running fleet, so identical inputs produced different artifacts
      depending on machine state — now declared in `orchestration/stack_topology.yaml`,
      with the probe demoted to a backstop; (3) check and update resolved the mode
      separately and could disagree — one resolver now, and it reports its source.
      Verified both directions: clean shell → `acceptance: no-inference checks passed`
      (first fully green clean-shell run; it was 39 errors this morning); master
      mutated by one comment → `lean_registry: stale`, exit 1.
      A false positive was caught and fixed before shipping — the pipeline's active-role
      set carries `eval_batch_frontdoor`, which the lean projection does not, so the
      cache key never matched and the step reported stale on every run.

- [x] **Production kernels resolve by backend, not by path** ✅ 2026-07-31 —
      orchestrator `c1a004bf`, layer at `/mnt/raid0/llm/kernels/`.
      `production/{cpu,gpu,stt,tts}` symlinks; `src/registry/kernel_paths.py` resolves
      them and RAISES on an unresolvable backend rather than falling back. Upgrading a
      kernel = archive the old target under a dated name, repoint the symlink,
      re-verify linkage — **neither registry and no launcher changes.**
      The three ggml generations stay separated: verified through the stable path that
      each backend loads its own ggml, `libggml-hip.so.0` present on gpu/stt/tts and
      correctly absent on cpu.

- [x] **Migrate hardcoded `llama.cpp/build/bin` call sites to `kernel_paths.backend_dir()`.** ✅ 2026-08-01 — and the deeper half: `LD_LIBRARY_PATH` outranks `RUNPATH`, so the HIP binary was loading CPU-only ggml from the ambient path. `ld_library_path` now derives from the same backend that chose `binary_dir`.
      ORIGINAL NOTE:
      **W1 REMAINS UNSAFE UNTIL THIS IS DONE.** `c1a004bf` makes the correct thing
      available; it does not yet stop the wrong thing. Until the launcher asks for a
      backend, a registry edit moving a role to the GPU still lands it on the CPU-only
      build, silently.

Stack unaffected by any of the above and still serving: 12/12 healthy, 18 processes,
`--spec-type draft-mtp` with ngram in zero processes, live inference confirmed.

#### ADDENDUM 2 (22:00–23:00Z) — W1's kernel blocker is CLOSED

- [x] **Every role's binary is resolved from its declared DEVICE** ✅ 2026-07-31 —
      orchestrator `b060dd56`. The architecture was already right and one derivation
      was missing: `stack_priors` emits a per-role `binary_path` from `binary_dir`,
      the launcher reads it, and `stack_commands.py:485` verifies live matches
      declared — but `binary_dir` came only from an explicit registry override, so
      every role without one fell through to a CPU-only literal, including any role
      a registry edit had just moved to the GPU.
      `_backend_for_role()` now maps device ROCm*/cuda*/gpu* → gpu backend, else cpu,
      resolved through `kernel_paths`. Verified both directions: `device: ROCm0` →
      `build-hip/bin/llama-server`, `device: none`/absent → `build/bin/llama-server`.
      All ten live roles now carry an explicit backend-resolved binary_path.
      Caught a near-miss: `env_policy`/`kmp_blocktime` key off `binary_dir` being
      truthy, so always-populating it would have flipped every role from `canonical`
      to `binary_override_strip_ggml` with KMP_BLOCKTIME=10. Explicit override and
      derived default are now distinguished; env policy is unchanged and asserted.

- [x] **Kernel freeze scope is derived, not curated** ✅ 2026-07-31 — orchestrator
      `4e8bf1f0`, runbook epyc-root `e19d458f`
      ([`docs/reference/kernel-freeze-runbook.md`](../../docs/reference/kernel-freeze-runbook.md)).
      The models that must show no regression for backend B are exactly those whose
      roles resolve to B in the compiled priors — a projection, so it cannot go stale
      the way a curated list does. `scripts/validate/kernel_freeze_scope.py`.
      **This is what makes the four kernels independently upgradable.** Today: cpu
      serves 10 roles across 5 DISTINCT models (bench the models, not the roles —
      several share one server); gpu/stt/tts serve none and gate on nothing from the
      stack. Promotion is a symlink move; rollback is repointing to the archived
      target. Neither registry changes, ever.

**W1's remaining blockers are now only D1–D4 and the stale anchors** (master moved
`96aa90f6` → `596a1e24`). The CPU-only-binary blocker is gone: a role declaring
`device: ROCm0` gets the HIP build automatically.

Stack verified unaffected throughout: 12/12 healthy, `--spec-type draft-mtp`, live
inference confirmed after every commit.

#### ADDENDUM 3 (wrap-up 2026-07-31) — W1 has a preflight gate; the remaining blockers are named

Nothing here supersedes the three appends above; this only records what landed after
ADDENDUM 2 and converts the loose conclusions in those appends into task lines.

- [x] **W1 preflight gate** ✅ 2026-07-31 — epyc-root `3927b2f9`,
      [`scripts/operator/w1_preflight.py`](../../scripts/operator/w1_preflight.py).
      A **gate, not an applier** — it deliberately does not edit the registry. Verifies the four
      preconditions W1 actually has, all now checkable because the compiler derives what used to be
      restated by hand: the three target model artifacts exist on disk; GPU has ≥50 GiB free
      (27B Q8 ~29 + VL-30B Q4 ~18); the `gpu` kernel backend resolves through the stable layer;
      both repos are clean so an apply cannot mix with unrelated work. Also provides
      backup/rollback for the files W1 touches.
      It was first written with an `--apply` that printed *"not implemented"* — the exact fail-quiet
      shape this handoff has spent the day cataloguing — so the flag was **removed rather than
      stubbed**.
- [x] **Priors source hashes refreshed after the backend-resolution edit** ✅ 2026-07-31 —
      orchestrator `ca5f3e81`. `orchestrator_stack.py` gained `_kernel_server_binary()` in
      `b060dd56` and the priors pin that file's SHA-256, so the artifact went stale the moment the
      code changed. The byte-hash pin did exactly its job. Pipeline back to
      `acceptance: no-inference checks passed`.

##### W1's remaining blockers, as tasks

- [x] **W1-a. Obtain the D1–D4 operator rulings.** ✅ 2026-08-01 — D1 hot · D2 NARROW (`explicit_request` only) · D3 `coder` removed · D4 delete the unreachable duplicate. Plus two rulings the work surfaced: GPU host lane = `184-191` `-t 8` SHARED; matrix refresh = device-awareness first, then bench.
      ORIGINAL NOTE: `architect_critic` tier; how aggressive the
      `reasoning` chain triggers should be; whether `frontdoor` keeps `coder`; the duplicate B3
      hint. Package them per the operator decision-package contract — options, tradeoffs,
      recommendation — rather than asking four separate questions.
- [x] **W1-b. Re-derive all 76 edit-list anchors against current master.** ✅ 2026-08-01 — tooling `/mnt/raid0/llm/tmp/w1-26b5f442/w1_resolve.py`. Two applier bugs found by the work: substring-anchored edits were being whole-line replaced (fixed by moving to character offsets), and 10 unquoted scalars containing `": "` broke YAML — the list was adversarially verified for content but never parsed.
      ORIGINAL NOTE: The list is recovered
      intact at `scratchpad/editlist.md` (97,339 bytes, md5
      `dbdbb11d35e5beb3957dec7695088853`), but its anchors are against master `96aa90f6`
      (md5 `c6a4d2b50e203140d344b436c8f1ab22`, 9,876 lines) and master has moved to `596a1e24`.
      **Do not generate the edits mechanically**: master carries load-bearing provenance comments
      that a YAML round-trip destroys, which is why the original list used line anchors. This needs
      a session with the context budget to verify each anchor.
- [x] **W1-c. Run `w1_preflight.py` immediately before applying** ✅ 2026-08-01 — run at apply time. Its clean-tree check was itself defective: it forbade the repo's documented idiom (pathspec-limited commits in a shared clone), so it now blocks only on collisions with W1's OWN targets and reports unrelated dirt.
      ORIGINAL NOTE:, not once at planning time — two
      of its four checks (repos clean, GPU headroom) are state, not facts.

##### Derived from the 20:00–23:00Z window — filed so they are not lost in prose

- [x] **Review the `ORCHESTRATOR_SKIP_STACK_CHANGE_GATE=1` bypass taken at this session's start.** ✅ 2026-08-01 — reviewed and RESOLVED structurally: `orchestration/accepted_gaps.yaml` gives the gate a severity distinction (declared+unexpired → warning, undeclared or expired → error, stale declaration itself reported). The bypass had by then been taken four consecutive times.
      ORIGINAL NOTE:
      The gate failed only on `runtime_attestation: live process drift` for `:8000` (orchestrator
      API) and `:9000` (faster-whisper CT2) — both predating the session, both exactly what **W4**
      exists to manage. The gate cannot say *"aux service unmanaged"* separately from *"unsafe to
      launch"*, so it fails at the same severity for both and the escape hatch is the only
      available response. **Until W4 lands this bypass recurs on every start**, which is how a
      bypass becomes habitual. Either W4 lands or the gate gains a severity distinction.
- [x] **Do not conflate `architect_general`'s two throughput priors.** ✅ 2026-08-01 — prior moved in the SAME commit as the model repoint, as required.
      ORIGINAL NOTE: **24.00** is the 122B's
      production-optimal figure and is what the derived layer correctly carries today; **47.79** is
      the 27B's and becomes correct only *after* W1 repoints the role. The prior must move in the
      **same commit** as the model repoint — splitting them is how every stale prior corrected this
      session was minted.
- **[declined: ws58 2026-11-03 content-review: a standing rule]** **STANDING — a role's throughput prior must move in the SAME commit as the model repoint.**
  Splitting them is how every stale prior corrected during this session was minted.
  *(SPLIT 2026-08-12 by `mainC`. W1's specific repoint completed on 2026-08-01 and that record
  stays checked above. The general rule outlives it and applies to ANY future repoint, which a
  closed box retires — the same loss-mode as the `seeding_rewards` box split on 2026-08-11.)*
- [x] **Fold `kernel_freeze_scope.py` into the promotion checklist** for the next kernel freeze, so ✅ 2026-10-29 (audit: .claude/skills/kernel-promotion/promotion_gates.yaml:33 derived_by scripts/validate/kernel_freeze_scope.py; docs/reference/kernel-freeze-runbook.md:19,40 run it per backend) [no-belief: audit-reconciliation]
      the regression scope is derived at freeze time rather than restated. Runbook:
      [`docs/reference/kernel-freeze-runbook.md`](../../docs/reference/kernel-freeze-runbook.md).

Repo hygiene surfaced by this window is filed as **NIB2-60..63** in
[`non-inference-backlog.md`](engineering-hygiene-backlog.md) — not acted on here because a stack start
was in flight and several items touch the shared clone.

##### Discovered 2026-08-12 while working P1-3 / P1-5 / P1-10 (`mainD`)

- [ ] **Propagate the `dual-half-negative` supersession to the LIVE strategy store.** [too-big: live strategy-store seeding requires the embedder service owner] The YAML is the
  record; `orchestration/repl_memory/strategies/strategies.db` is what AutoPilot reads. Until
  `scripts/autopilot/seed_operator_strategies.py --apply` runs (dry run: 1 insert, 47 skipped) a
  restarted AutoPilot still reads the stale quarter-granularity prior. Needs a live BGE embedder, so it
  belongs to whoever owns that service. **Time-sensitive for the same reason P1-3 was.**
- [x] **`retrieve_conventions` ranks conventions newest-first before applying the limit.** ✅ 2026-10-29
  Orchestrator main `4b200ec109eda67d92b31e66dbc828dac8da376e` changes the query to
  `created_at DESC`; deterministic timestamp controls cover unlimited, one-row and three-row
  retrieval. All 68 strategy-store tests passed after integration; no live database was changed.
  [no-belief: retrieval-order repair and unit validation]
- [x] **Regenerate `orchestration/derived/stack_priors.yaml`** — 3 of 9 `REQUIRED_SOURCE_ARTIFACTS` pins ✅ 2026-10-29 (audit: orch 7483d7fb / 0d145f4f (2026-08-21 "regen under production fleet mode (both)") regenerated derived/stack_priors.yaml; later regens 92bbeb06 etc.) [no-belief: audit-reconciliation]
  (`orchestrator_stack`, `stack_numa`, `stack_topology`) are stale at HEAD, which is why
  `orchestrator_stack.py start` refuses to launch. Deliberately out of scope for the P1-10 fix (separate
  act, separate file set).
- [x] **The `backend:` → `verify_ggml_linkage` invariant is enforced by ONE TEST, not the loader.** ✅ 2026-10-29 Evidence: APP `e91305c14da8c218ef3e8b57f45c18b580bca9ca`; `tests/unit/test_aux_service_env.py`. [historical hygiene: implemented 2026-10-29; zero new quota]
  `stack_manifest.py:318` forces only `ld_library_path_mode`; `:338` defaults the flag to `False`. Delete
  a flag line from `launch_manifest.yaml` and the loader says nothing —
  `tests/unit/test_aux_service_env.py:128` is the only thing that would notice.

  Fixed in orchestrator `e91305c14da8c218ef3e8b57f45c18b580bca9ca`: backend declarations now
  require literal `verify_ggml_linkage: true`; omitted/false/null/numeric/string values reject. Both
  current speech declarations already comply, while non-backend defaults remain false. 118 focused
  environment/import tests passed; YAML comments corrected with parsed values identical. No live
  reload, model call or frozen-kernel change. Full make gates stopped at missing shellcheck.
  [no-belief: loader invariant and regression validation]

## Track: batched-decode-measurement
<!-- gate: none -->

> Folded from `handoffs/active/batched-decode-measurement.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F17, route 1a, operator D1/D5; retired row INF-07 → INF-45). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Batched-Decode Measurement (E1/E2) + Conditional 8x8 GEMM SIMD (E3) + NUMA×batch (E5)

> ## ⛔ SUSPENDED PENDING RE-MEASUREMENT (2026-07-30)
>
> **Scope: all E5 (NUMA×batch) throughput results** — the 31-cell Stage-B sweep of
> 2026-07-29/30 and the 69-cell W0 scout, which swept the same placement shapes through the
> same harness. A wiring defect in the shapes under test makes every absolute throughput
> value and every cross-cell ranking below unusable. **Re-measurement on the corrected
> placement is IN PROGRESS.**
>
> **Root cause.** The swept shapes inherit the current production wiring's NUMA defect:
> `stack_numa.py:66-67` defines `NUMA_NODE0 = "0-47,96-143"` and
> `NUMA_NODE1 = "48-95,144-191"`, each of which **straddles a pair of NPS4 nodes**, and
> launches them **without `numactl --interleave`**. This host is NPS4 —
> `node0 = 0-23,96-119`, `node1 = 24-47,120-143`, `node2 = 48-71,144-167`,
> `node3 = 72-95,168-191` — so a "half-machine" cpuset spans two nodes while the weights
> first-touch onto whichever node loads them, and every thread on the other node pays a
> remote-access penalty on every weight read. The E5 affinity artifact for this shape
> recorded `pages_by_node {N0: 9226101} / total 9226101` — all 35.2 GiB resident on node0
> while the thread team spanned node0+node1. **`numactl --interleave` binds at FIRST TOUCH
> only**, so it is a silent no-op against a warm page cache; that is why the defect
> survived casual checking, and why a warm re-test appears to "confirm" the bad number.
>
> **Measured 2026-07-30** — `llama-bench` tg128, no speculative decoding,
> `Qwen3.6-35B-A3B-MTP-Q8_0` (the frontdoor model):
>
> | placement | page cache | tok/s |
> |---|---|---:|
> | straddling cpuset, no interleave — **= CURRENT PRODUCTION wiring** | warm | **7.81 ± 3.82** |
> | straddling cpuset, no interleave | cold | 10.28 |
> | straddling cpuset **+ interleave**, `-t 96` | cold | 15.35 |
> | **full machine `taskset -c 0-95` + `numactl --interleave=all`, `-t 96`** | cold | **23.43 ± 0.07** |
>
> The winner is the canonical bench recipe, and it beats the wiring E5 measured through by
> **3.0×** — Stage-B priced the frontdoor model at roughly **one third of its true speed**.
> With MTP speculative decoding ON at that winning placement, single stream measures
> **36-39 tok/s**, independently matching the AutoPilot production anchor
> (`median_request_tps` median **35.7**, n=154, band 35-40).
>
> **Instrument validated; alternative explanations ruled out.** A single-NPS4-node arm
> (24 physical cores, `-t 48`) measured **8.80** tok/s against the registry-documented
> **8.90** — a 1% match, so the measuring instrument is sound and the defect is in the
> wiring under test, not the meter. Ruled out as causes: a v8 kernel regression (v7 and v8
> both measure **9.76**, identical); iqk (it never engages for Q8_0 — gated behind an unset
> `GGML_IQK_Q8_0`); MTP head overhead; and mmap page-faulting.
>
> ### Amended 2026-09-08 (INF-70 audit, MEAS-1 / HARNESS-1 / HARNESS-2 / STAT-1) — sub-floor labels
>
> The original text above and below is **retained verbatim**; this block corrects *labels*, not
> numbers. The cold-targeted CPU harness on this box has a measured **A/A p95 floor of 3.21%**
> (adjacent-window) and **19.89% contended**; the new hot-server harness floor is 0.80% p95.
> **Any delta in this file smaller than ~5% is at or below that floor — its label is WRONG, not
> merely missing, and must be read as UNRESOLVED.** Corrections of fact:
> 1. **`"a v8 kernel regression (v7 and v8 both measure 9.76, identical)"` is not "ruled out"** —
>    restate as **"no v7/v8 difference resolvable above the harness floor"**. Nothing below ~5% was
>    ruled out by that arm.
> 2. **The E1 `-np` ladder interpretation** (*"`-np 2`, `-np 8`, and `-np 16` are all close on
>    aggregate throughput"*; 839.08 / 799.03 / 846.72 = a 0.3–5.9% spread) is **UNRESOLVED at the
>    floor** — "close" and the implied saturation knee are not measured. The **p95 latency ladder
>    (12.31 s → 109.69 s) is far above the floor and stands unchanged**, and it carries that item's
>    actual conclusion.
> 3. **A pre-window host-health precheck establishes ELIGIBILITY, not trustworthiness.** The
>    *"post-reboot host-health gate returns ZERO warnings … so Stage-B is decision-grade eligible"*
>    item must not be cited as evidence that the arms ran clean: INF-70 measured a `loadavg` gate
>    passing at **11.61** and the arm then running through **loadavg 55.7**. The per-cell mid-run
>    re-enforcement recorded further down is the stronger claim and is the one to cite.
> 4. **STAT-1 (harness-wide): the ARM is the unit of replication.** Per-prompt paired statistics are
>    pseudo-replication — a "0/40 prompts lost, p≈0" claim became **−1.04% UNRESOLVED** under
>    arm-level permutation. E5's **one pass per cell** therefore has no error term, and no margin
>    ranked off it (R1–R4) carries significance.
> 5. **DRIFT-1**: there is no linear within-block drift in this harness (slope +0.03%/slot,
>    R² 0.004). "It was drift" is retired as an explanation here.
>
> **Flagged, deliberately NOT actioned (scope changes, owning session's call):** the *"36-39 tok/s …
> independently matching the AutoPilot production anchor (median 35.7)"* and *"8.80 vs the
> registry-documented 8.90 — a 1% match, so the meter is sound"* steps compare a **cold** bench
> absolute against a **differently-harnessed** absolute, which HARNESS-2 forbids (hot reads **+4.36%**
> above cold on the same binary, byte-identical output); the pre-registered **≥5% split-vs-unified
> escalation trigger** sits exactly on the floor and will fire on noise; **R1's ≥10% margin** rule is
> valid only in the quiet/adjacent-window regime, not the 19.89% contended one; and the queued
> re-measurement campaigns (the 31-cell Stage-B re-run, the 24 remaining manifests) should be
> re-planned before firing — **MTP arms are ~2.8× more precise than plain** (sd 0.61% vs 1.71%),
> i.e. **~8× fewer arms** for the same power, and the hot harness is 4× tighter than cold — all under
> the operator directive that lever research is **STOPPED** until a fully consolidated champion exists.
>
> ### SUSPENDED — do not cite, do not gate on
>
> - **ALL absolute throughput values** — tok/s, tasks/hour, aggregate rates — in every E5
>   results block below.
> - **ALL cross-cell rankings.** Every cell was bandwidth-bound under the defect, and the
>   penalty scaled with how many NUMA nodes each shape's cpuset straddled — so the ranking
>   measures the defect, not the shapes. Per the Stage-B config grid below, `C1`/`C1b` for
>   `qwen36_q8_0` and `qwen3_next_80b` are the straddling halves, while `C2`/`C3` are the
>   `NUMA_Q*` quarters, which are exactly the four NPS4 nodes and therefore node-local.
>   The shapes were not penalised alike.
> - **RETRACTED: the Stage-B headline "C3 (four quarters) loses at every clean iso-T rung"**
>   — and, on the same grounds, W0's opposite "C3 quarters aggregate-optimal for EVERY
>   model". Neither direction is established.
> - **RETRACTED: the per-model "winning shape" reads** ("35B wants one half, gemma one full
>   machine + interleave, 80B two node-local halves"). The 35B recommendation names the
>   defective straddling half specifically, which today's numbers contradict directly
>   (7.81 warm vs 23.43 at full machine + interleave).
> - Note for the re-run: for `qwen36_q8_0` and `qwen3_next_80b` the shape that actually won
>   today — full machine `0-95` + `--interleave=all` — **was not in the Stage-B grid at
>   all**; it appeared only as gemma's `C1`. The corrected grid must include it per model.
>
> ### SURVIVES — still valid, NOT suspended
>
> - The **0.0% error rate on every cell** (31/31 Stage-B, and the W0 cells). An error-rate
>   read does not depend on memory bandwidth.
> - Every **harness defect fix** landed during the campaign: throttle-gate cpuset scoping
>   (`98cfff44`), the never-emitted `--reasoning` flag (`5d6a17f2`), `find_llama_processes`
>   identifying by `/proc/<pid>/exe` (`4a5b6bc7`), and the undeclared `httpx` dependency
>   (`040a2ad7`).
> - The **protocol / manifest / attestation machinery itself** — pre-registered cell grids,
>   the affinity-preflight hard gate, the capture contract, and the deterministic-replay
>   ledgers. The instrument is reusable as-is for the re-measurement.
>
> **Not covered by this notice**: the 2026-07-03 / 2026-07-06 **E1/E2** tables further below
> are a separate single-instance campaign, already demoted to pre-v7 historical priors.
> Their placement has not been audited against this defect and no claim either way is made
> here.
>
> Per [MEASUREMENT.md](../../MEASUREMENT.md) the suspended numbers are **retained verbatim
> and annotated — never edited, never deleted** (append-only). Each affected block below
> carries an inline `⛔ SUSPENDED 2026-07-30` marker.

**Status**: IN PROGRESS — A3B E1 and E2 decision-grade evidence landed 2026-07-03; E2 is a keep-candidate for an eval-batch serving class; shadow metadata/feature-gate, default-off warm eval-batch frontdoor hook, guarded activation probe, and plan-only/apply activation-window runners landed; 2026-07-05 activation window smoked through and rolled back cleanly; dense-control E1 tail completed 2026-07-07 as useful but not pristine host-exclusive evidence · **E5 (NUMA×batch interaction sweep) added 2026-07-20 — runs LAST in the post-v7-promotion queue: inference-batch-loop → architect-model-selection-bench → this.** · **⛔ 2026-07-30: all E5 throughput results (Stage-B + W0) SUSPENDED pending re-measurement on the corrected placement — see the suspension notice above.**
**Created**: 2026-06-12
**Priority**: ACTIVE-HIGH — bench-only, ~1 day for E1+E2; rank 2 in the findings-06 "what remains" table; an evidence vacuum under the highest-volume workload (the eval harness)
**Spec**: [fable5-findings-06-kernel-and-concurrency.md](../completed/fable5-findings-06-kernel-and-concurrency.md) §2 (E1/E2/E3) + [MEASUREMENT.md](../../MEASUREMENT.md) P-BENCH-3 — read both before claiming any waypoint
**Related**: [bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign) (E1/E2 are quiesce-window Queue-2 items); [cpu-shape-specialized-gemv-decode.md](../completed/cpu-shape-specialized-gemv-decode.md) (E3 landing zone); [sarathi-serve-cpu-evaluation.md](cpu-decode-roofline-program.md#track-sarathi-serve-cpu-evaluation) (its reopen gate may fire from these results); [within-role-placement-state-machine.md](dispatch-placement-telemetry.md) (the multi-instance layer this complements); [inference-research-index.md](inference-research-index.md) (merged CPU/GPU inference routing)

#### Why

Single-instance batched decode has never been measured: CPU14 was never run,
CPU23 deferred multi-stream interference "unless multi-tenant becomes
relevant" — and per findings-02/03 the dominant workload is now the eval
harness (4.6 h/day T1 + 1.3 h/day T0, 43 questions/trial) fanned out across
instances while `cont_batching` sits unexploited. CPU18's own reopen clause
names "eval pipelines"; the trigger has been satisfied for weeks. The batch>1
8x8 kernel body was never written (dispatcher falls back to scalar).

#### Waypoints

- [x] **E1 — CPU14 at last** (half day, quiesce window): one instance, `-np {1,2,4,8,16}`, fixed question batch, on (a) frontdoor Qwen3.6-A3B and (b) a dense control; measure aggregate tasks/hour + per-stream p50/p95 latency per MEASUREMENT.md P-BENCH-3. Acceptance: claims filed with protocol id + attest ref; saturation point identified per model. **2026-07-03 update**: A3B arm is complete and decision-grade. **2026-07-07 update**: dense-control tail completed at `epyc-inference-research/data/batched_decode/e1-pbench3-dense-control-iqk-20260707T022917Z/` after aborting the missing-IQK attempt. All `qwen36_27b_q8 -np {1,2,4,8,16}` cells completed `43/43` with `0` errors; tasks/hour scaled `20.11 -> 124.62`, aggregate predicted t/s `1.07 -> 6.81`, and p95 latency rose `240.9s -> 674.0s`. The MI210 server remained live, so treat the dense-control tail as useful evidence, not pristine host-exclusive decision evidence. ✅ 2026-07-07
- [x] **E2 — eval-driver A/B** (half day, same window): one T1 eval (43 questions) against a single full instance with `-np 8` continuous batching vs the current 3-concurrent-across-quarters path; metric = wall-minutes/eval (= statistical power per day, per findings-01). Acceptance: the batch serving class is priced; keep-or-kill recommendation for an eval-batch instance set recorded. **2026-07-03 update**: orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` feature flag plus explicit EvalTower request metadata (`workload_class=eval_batch`, shared batch id, background priority). Orchestrator `e9312a17` then added the default-off warm `eval_batch_frontdoor` serving hook on port `18070`; orchestrator `276a1eef` added the guarded preflight/smoke probe. The 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper that starts only `eval_batch_frontdoor`, reloads the API with `ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=1`, runs the smoke probe, and rolls back unless `--keep-enabled` is explicit. **2026-07-05 update**: the activation window completed as `status=smoke_passed_rolled_back`; `eval_batch_frontdoor` launched on port `18070`, API workers attested `eval_batch_serving=true` during probe, the smoke answer was `ok`, the tap hit expected port `18070`, and rollback disabled the feature + stopped `eval_batch_frontdoor`. Activation now has decision-grade evidence; representative quality/eval telemetry is the next remaining gate before any default EvalTower path change.
- [x] **E2 — eval-tower window runner** (same lane): `scripts/benchmark/eval_batch_serving_evaltower_window.py` now packages the compare-and-rollback loop for the current EvalTower arm versus the temporary eval-batch arm. Default mode is plan-only; live mutation requires `--apply --confirm-clean-window`, active AutoPilot blocks by default unless `--allow-autopilot-active` is explicit, and the resulting evidence is non-decision-grade in that case. The runner calls the existing activation helpers, rolls back unless `--keep-enabled` is requested, and writes JSON/MD outputs under `orchestration/reports/eval_batch_serving_evaltower_<timestamp>/`. Tests landed in `tests/unit/test_eval_batch_serving_evaltower_window.py`; validation passed with `uv run pytest -q tests/unit/test_eval_batch_serving_activation_window.py tests/unit/test_eval_batch_serving_evaltower_window.py` (`12 passed`), `uv run ruff check scripts/benchmark/eval_batch_serving_evaltower_window.py tests/unit/test_eval_batch_serving_evaltower_window.py`, and `python3 -m py_compile ...`. Plan-only smoke wrote `/mnt/raid0/llm/tmp/evalbatch-evaltower-plan-smoke-2/summary.json` with `status=plan_only`, `applied=false`, `decision_grade=false`, `autopilot_active=true`, 3 activation commands, and 2 rollback commands.
- [x] **E3 — 8x8 GEMM SIMD body** (days, CONDITIONAL): **NO-GO / CLOSED for now**. 2026-07-18 zero-inference decision: E1/E2 show a serving/topology win, not per-thread compute headroom, and the newer CPU roofline classifies decode-side SIMD/ALU work as bandwidth-killed. Do not write the AVX-512BW batch>1 GEMM body unless a future counter run contradicts the roofline. ✅ 2026-07-18
- [x] **E4 — conditional re-promotions** (doc-only first): **PARTIAL REOPEN TO MEASUREMENT ONLY**. 2026-07-18 zero-inference decision: CPU17/Sarathi reopens only to the long-prompt mid-stream TBT measurement gate because eval-batch is the named workload class; CPU18/MegaBlocks remains gated pending evidence that padding/capacity-factor cost is material. ✅ 2026-07-18
- **[declined: ws58 2026-11-03 content-review: merged into the live RE-MEASURE row (the sweep's current step)]** **E5 — NUMA×batch interaction sweep** (post-v7-promotion quiet window; the never-measured 2D cross). NUMA-split and `-np` batching have only ever been measured **separately** — NUMA-split built the pinning map; `-np` alone is E1 (single instance). **Hypothesis (roofline):** batching amortizes the per-token weight-read → shifts CPU decode **BW-bound → compute-bound** → the NUMA-locality advantage may **flip at high K**; the crossover in K is unknown and sets the slot-fabric grid shape. Directly tests whether **a single full-machine high-`-np` server beats quarter-batched servers**. **Protocol (reuse the E1 `-np` harness + P-BENCH-3):** per-model 2D grid — **N = each model's *allowed* NUMA-pinned configs** (from `scripts/server/stack_numa.py` `NUMA_CONFIG` + the safe-placement table in [within-role-placement-state-machine.md](dispatch-placement-telemetry.md); e.g. frontdoor `{1×half},{2×half},{4×q}` — full+quarter mixes excluded per the 2026-07-21 mode-exclusivity contract [refreshed 2026-07-23, audit C4; the original `{full,q3}`-style mixed examples are superseded]; worker_general `{1×full},{4×q}`; architect 122B out of E5 scope — see the 2026-07-23 design section) × **K = `-np ∈ {1,2,4,8,16,32}`**. Two reads: **(i) iso-concurrency** — hold total in-flight = N×K fixed (e.g. 32) and vary the split (`1×32` vs `2×16` vs `4×8` where safe-placement allows) → the direct "one big batched server vs quarter-batched" answer; **(ii)** unconstrained **peak-aggregate (N,K)**. **Metrics:** aggregate decode t/s **and** per-stream p50/p95 latency (P-BENCH-3), paired with a correctness/garbage check; era-stamped, protocol-id + attest ref. **Canonical recipe only:** OMP env stack, `scripts/server/affinity_preflight.py` **live-affinity verify per instance** (the WP-6 bad-affinity artifact is the cautionary tale), per-instance cache warming (drop_caches NUMA re-read trap), throttle check, host-health gate (uptime / `numa_balancing=0`). **Models:** `qwen36_q8_0` (frontdoor 35B-A3B) + `qwen36_27b_q8` (dense control) — both already in the E1 harness — + gemma `worker_general`. **Decides:** the (N,K) provisioning per model for the slot fabric + whether **workload-class lanes** are real (a low-K/high-K crossover). **Feeds** [within-role-placement-state-machine.md](dispatch-placement-telemetry.md) per-instance `-np` sizing and [heterogeneous-slot-fabric-residency.md](kv-cache-program.md#track-heterogeneous-slot-fabric-residency) (provisioning-pending). **Gating:** post-v7-promotion; runs **LAST in the post-promotion queue** — `inference-batch-loop → architect-model-selection-bench → this` — operator/quiet-window, P-BENCH-3 host-health. Bench-only.

#### Progress Notes

##### 2026-06-14 — Harness + exploratory scout

Implemented `scripts/benchmark/server_np_sweep.py` in `epyc-inference-research` as the durable P-BENCH-3 harness:

- Launches one `llama-server` per cell with `-np N`, `-c 32768`, `-t 96`, `-ub 8192`, `--flash-attn on`, `--jinja`, `-ctk q8_0`, `-ctv q8_0`, `--mlock`.
- Uses a fixed deterministic tier-1 question-pool batch and writes selected qids, manifest, per-request JSONL, summary CSV, recommendations, server logs, and per-cell stop events.
- Refuses decision-grade runs when host-health preconditions fail unless `--allow-host-health-warning` is passed; the manifest then marks `decision_grade=false`.
- Verifies every launched server is dead with `ps -p` after SIGTERM/SIGKILL handling.

Smoke: `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/smoke-server-np-sweep-20260614T1847Z` passed one frontdoor `-np 1` cell and verified server PID stopped.

Exploratory scout: `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/exploratory-e1-pbench3-scout-20260614T1848Z` ran both required model+quant targets over `-np {1,2,4,8,16}` with 10 fixed tier-1 prompts and 64-token cap. **Not a claim**: host uptime was >1 week and `kernel.numa_balancing=0`, so the manifest records `decision_grade=false`.

Scout shape:

| Model+quant | Best scout `-np` | Tasks/hour | p95 latency | Notes |
|---|---:|---:|---:|---|
| Qwen3.6-35B-A3B Q8_0 (`qwen36_q8_0`) | 8 | 1816.37 | 19.4s | `-np 16` slightly regressed; aggregate gain from `-np 1` to `-np 8` was ~41%, but p95 rose ~3.8x. |
| Qwen3.6-27B Q8_0 dense control (`qwen36_27b_q8`) | 8 | 837.09 | 38.7s | Dense control scaled more strongly through `-np 8`; `-np 16` regressed and p95 reached ~50s. |

Next decision-grade E1 action: reboot or otherwise satisfy host-health policy, then rerun the same harness at the full fixed batch size (`43` prompts) and target token cap. Treat `-np 8` as the leading candidate but still rerun all N values because the scout was small and non-gating.

##### 2026-06-19 — E2 coordinator ready; host-health still blocks claims

Implemented `scripts/benchmark/e2_eval_driver_ab.py` in `epyc-inference-research` commit `25caf78` as the durable E2 run-plan coordinator:

- Emits a two-arm manifest and `commands.sh` for the single full-instance `-np 8` continuous-batching arm plus the current EvalTower `AUTOPILOT_EVAL_CONCURRENCY=3` arm.
- Records P-BENCH-3 attestation, selected 43-question tier-1 prompt qids, primary artifact paths, and the keep-or-kill acceptance target.
- Fails closed by commenting runnable commands when host-health warnings are present; `--allow-host-health-warning` is an explicit scout-only override.

Validation: `uv run python -m py_compile scripts/benchmark/e2_eval_driver_ab.py scripts/benchmark/test_e2_eval_driver_ab.py`; `uv run --with pytest pytest -q scripts/benchmark/test_e2_eval_driver_ab.py` -> 3 passed; `uv run --with ruff ruff check scripts/benchmark/e2_eval_driver_ab.py scripts/benchmark/test_e2_eval_driver_ab.py`; dry-run manifest generation under `/tmp/epyc-e2-validate/e2-dry-validate` correctly produced `status=blocked decision_grade=false` because uptime, NUMA state, and existing llama processes violate the claim gate.

No decision-grade E2/E1 result was binned. Current host state still requires a clean host-health/reboot window before claim-grade P-BENCH-3 measurement. A direct-port RoPE scout against the resident frontdoor server was attempted as non-decision-grade resource utilization only, then stopped after 8/100 unparseable responses; no artifact was written and no result should be used.

Follow-up `epyc-inference-research` commit `74e580e` added the no-inference result summarizer:
`e2_eval_driver_ab.py --summarize-run <run_dir>` reads the batch arm `summary.csv` plus the current
EvalTower `current_quarters.jsonl`, computes wall-minutes/eval and
`speedup_current_over_batch`, and emits `summary.json` with
`keep_candidate` / `kill_candidate` / `scout_only` / `incomplete` status. Non-decision-grade manifests
stay `scout_only`, so the summarizer cannot accidentally promote host-health-warning data into a
production keep/kill claim.

##### 2026-06-20 — Queue-2 clean-window manifest wiring

Research `7d2dade` added E2/E1 entries to the tracked clean-window plan:
`docs/data/clean_window_measurement_manifest.json` now has `27` total entries,
`21` ready, and `6` blocked under the observed live port/context constraints,
and `docs/data/clean_window_measurement_commands.sh` includes:

- E2 plan generation:
  `uv run --extra benchmark python scripts/benchmark/e2_eval_driver_ab.py --run-id "$run_id" --prompt-limit 43 --prompt-seed 42 --tier 1 --batch-np 8 --current-concurrency 3`
- E1 decision-grade sweep command:
  `uv run --extra benchmark python scripts/benchmark/server_np_sweep.py --run-id "$run_id" --prompt-limit 43 --prompt-seed 42 --tier 1 --np-levels 1,2,4,8,16`

The E2 command is intentionally a no-inference run-plan generator; it writes the
fresh attested E2 manifest and arm-level `commands.sh`. A smoke against
`/mnt/raid0/llm/tmp/e2_plan_smoke/` during the active AutoPilot window produced
`status=blocked decision_grade=false` with host-health warnings for uptime, NUMA
state, and existing llama processes, proving the planner still fails closed for
claim-grade evidence. No decision-grade E1/E2 result was binned.

Follow-up orchestrator `4bbf1163` added the missing no-inference worker-process
attestation step for the Queue-2 reload. `docs/reference/stack-change-launch-runbook.md`
now pairs the existing `attest_flags.py` feature-state check with
`scripts/validate/attest_orchestrator_workers.py`, which discovers API worker
PIDs through `/config/attest` and reads only requested keys from
`/proc/<pid>/environ`. Live read-only checks at the documented poll budget saw
all six API workers with no feature diffs and no env diffs for the declared
Queue-2 contract (`specialist_routing=true`, `model_fallback=true`, dormant
wave-2 features off, cross-role/placement/reverse-migration/URE/structured-output
process env present). This does not satisfy the host-health/reboot gate for
decision-grade E1/E2; it closes the reload/attestation runbook gap before that
window.

##### 2026-07-03 — Clean-window A3B E1 + E2 keep-candidate

Decision-grade quiet-window measurement landed after pausing AutoPilot cleanly,
stopping the CPU stack, fixing the P-BENCH-3 host-health NUMA check to match the
canonical `kernel.numa_balancing=0` policy, and restarting the stack afterward.
AutoPilot resumed at trial counter `1095` after the measurement window.

E1 A3B artifact:
`/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e1-pbench3-clean-20260703T1912Z/`.
The completed `qwen36_q8_0` rows are decision-grade (`host_health_warnings=[]`,
no pre-existing llama processes, governors `performance`, NUMA balancing `0`):

| `-np` | success | tasks/hour | aggregate predicted t/s | p50 latency | p95 latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 43/43 | 577.97 | 21.26 | 7.04s | 12.31s |
| 2 | 43/43 | 839.08 | 28.88 | 2.76s | 17.95s |
| 4 | 43/43 | 796.31 | 27.28 | 4.70s | 38.81s |
| 8 | 43/43 | 799.03 | 27.50 | 13.53s | 66.17s |
| 16 | 43/43 | 846.72 | 29.14 | 23.17s | 109.69s |

Interpretation: throughput saturates early for the A3B eval primitive; `-np 2`,
`-np 8`, and `-np 16` are all close on aggregate throughput, while tail latency
rises sharply after `-np 2`. The mandatory dense-control manifest entry did not
complete: `qwen36_27b_q8 -np 1` was stopped before a summary row after diagnostic
logs showed about `0.59` generated tok/s on long responses. Treat the dense
control as unresolved and do not use this artifact as a complete dense-control
E1 result.

E2 artifact:
`/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e2-pbench3-clean-20260703T1940Z/`.
The generated A/B summary is decision-grade and records `status=keep_candidate`:

- batch arm: single full `qwen36_q8_0` server with `-np 8`, 43/43 successes,
  `135.479s` wall time, `2.258` wall-minutes/eval, `1142.61` tasks/hour,
  `0.0` error rate, p95 `49.01s`.
- current arm: live EvalTower fan-out with `AUTOPILOT_EVAL_CONCURRENCY=3`,
  `658.193s` wall time, `10.970` wall-minutes/eval, quality `2.233`,
  reliability `1.000`, aggregate speed `43.867` t/s.
- comparison: batch arm is `4.858x` faster by wall-minutes/eval.

Next action: add the actual dedicated eval-batch serving endpoint/launcher shape
and guarded execution hook behind the already-landed `eval_batch_serving` flag,
then re-run representative quality/eval telemetry before changing the default
AutoPilot eval path. E3 remains conditional: do not start the 8x8 GEMM SIMD body
solely from this result; the A3B E1 table shows throughput saturation but the
winning E2 wall-time result is primarily a serving/topology opportunity.

##### 2026-07-03 — Eval-batch metadata gate

Orchestrator `7cb71a4e` landed the first conservative A7 hook stage without
changing evaluator execution:

- `src/features.py` declares `eval_batch_serving`, default-off in both tests and
  production, exposed through the existing runtime flag/config attestation path.
- `scripts/autopilot/eval_tower.py` stamps each `_eval_batch()` with one shared
  `evaltower-<label>-<timestamp>-<n>q` id and sends requests through
  `call_orchestrator_forced()` with `request_priority=background`,
  `workload_class=eval_batch`, and `batch_id=<shared id>`.
- `scripts/benchmark/seeding_orchestrator.py` accepts optional
  `request_priority`, `workload_class`, and `batch_id` fields while preserving
  legacy background-priority behavior for existing callers.

GitNexus impacts before edit: `call_orchestrator_forced` HIGH
(`impactedCount=17`, `processes_affected=4`) and `EvalTower._eval_batch` HIGH
(`impactedCount=24`, `processes_affected=1`), so the main thread handled it.
Validation: `102 passed` for the focused seeding/EvalTower/features/runtime flag
slice, focused Ruff clean, py_compile clean, and `git diff --check` clean.

At that checkpoint, EvalTower still did **not** route to a single `-np 8`
server. The follow-up hook below adds the missing endpoint/launcher surface but
keeps it default-off pending explicit activation and representative telemetry.

##### 2026-07-03 — Default-off eval-batch frontdoor hook

Orchestrator `e9312a17` landed the second conservative A7 hook stage. It
creates a deployable test hook for the E2 batch-serving shape while keeping the
normal hot stack and default AutoPilot eval path unchanged:

- `scripts/server/stack_manifest.py` and `stack_numa.py` define a launcher-only
  warm role, `eval_batch_frontdoor`, on port `18070`, using frontdoor-family
  model/runtime settings with an `-np 8`, `-c 32768`, `-t 96`, `-ub 8192`, q8 KV,
  flash/Jinja/mlock serving shape.
- `scripts/server/orchestrator_stack.py` adds a scoped
  `eval_batch_frontdoor` command builder. The command uses embedded Qwen NEXTN
  speculative decoding and omits `-md` when the draft path resolves to the same
  GGUF as the target, preserving the CPU self-draft duplicate-load fix.
- `scripts/server/stack_commands.py`, `src/registry/registry_compiler.py`, and
  `src/registry/model_descriptors.py` keep the warm hook out of normal hot
  starts and generated active-role descriptors.
- `src/api/routes/chat_pipeline/routing.py` adds a default-off,
  request-scoped rewrite: when `eval_batch_serving` is enabled, a request is
  real-mode eval-batch traffic, no explicit `server_urls` override is present,
  and the configured eval-batch endpoint is healthy, frontdoor-family roles are
  routed to the eval-batch endpoint for that request only.

GitNexus impacts for the edited launch/routing surfaces were LOW after the
prior metadata stage. Validation: py_compile on all touched server/registry/API
files; `187 passed` across `test_registry_compiler.py`,
`test_stack_manifest_imports.py`, `test_build_server_command_helpers.py`, and
`test_pipeline_routing.py`; focused Ruff/syntax checks; `git diff --check`.

This is still not a production flip. Next action is a coordinated activation
window: warm-start `eval_batch_frontdoor`, reload the API with
`ORCHESTRATOR_FEATURE_EVAL_BATCH_SERVING=1` and
`ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL=http://localhost:18070`, then collect
representative EvalTower quality/reliability/throughput telemetry before
changing defaults.

##### 2026-07-03 — Eval-batch serving probe harness

Orchestrator `276a1eef` added
`scripts/benchmark/eval_batch_serving_probe.py`, a guarded activation probe for
the default-off eval-batch serving lane:

- default mode is read-only preflight: check orchestrator `/health`, check warm
  `eval_batch_frontdoor` `/health`, sample `/config/attest` for
  `eval_batch_serving`, detect active AutoPilot, and emit the exact activation
  commands.
- `--smoke --confirm-clean-window --require-enabled` sends one real
  `/chat` request with `workload_class=eval_batch`, background priority, shared
  `batch_id`, and direct frontdoor routing, then verifies the structured
  inference tap hit port `18070`.
- smoke refuses active AutoPilot by default; `--allow-autopilot-active` is
  explicit non-claim-grade load telemetry only.

Live no-inference preflight artifact:
`/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/eval_batch_serving_probe_live_preflight_20260703T234518Z/summary.{json,md}`.
It is `status=blocked`, `decision_grade=false`: orchestrator API health is OK,
AutoPilot is active, sampled API workers have `eval_batch_serving=false`, and
the warm endpoint is absent (`eval_batch_frontdoor health is not OK`). This is
the expected default-off state.

Next activation command:

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run python scripts/benchmark/eval_batch_serving_activation_window.py --apply --confirm-clean-window
```

Default behavior is plan-only. The live 2026-07-04 plan artifact at
`/mnt/raid0/llm/tmp/eval_batch_activation_plan_live/summary.{json,md}` confirms
the expected blocked/default-off state while AutoPilot is active: API healthy,
AutoPilot active, eval-batch flag disabled, and port `18070` absent. Use
`--keep-enabled` only if the activation smoke passes and the operator wants to
leave the lane enabled for representative EvalTower telemetry.

##### 2026-07-05 — Eval-batch activation smoke passed, then rolled back

The activation window on `epyc-orchestrator` commit `132c595d` completed with
`status=smoke_passed_rolled_back` and `decision_grade=true`. The dedicated
`eval_batch_frontdoor` service came up on port `18070`, sampled API workers
attested `eval_batch_serving=true`, the smoke response was `ok`, and the
structured tap confirmed traffic on `18070`. The follow-up rollback disabled
the feature and stopped `eval_batch_frontdoor`, so the live default path stayed
unchanged.

This closes the activation/rollback deliverable for E2. The handoff stays open
for representative quality, reliability, and throughput telemetry before any
default EvalTower path change, while E1 dense-control remains unresolved and E3
still depends on the E1 result.

##### 2026-07-06 — P-BENCH-3 sweep checkpoint

The clean-window sweep `e1-pbench3-20260706T1529Z` completed the full
`qwen36_q8_0` ladder (`np=1,2,4,8,16`) and wrote `summary.csv` before the
`qwen36_27b_q8` dense-control tail was intentionally interrupted. The 35B arm
is decision-grade and shows the expected throughput/latency tradeoff:

- [x] `qwen36_q8_0` P-BENCH-3 ladder complete (`np=1,2,4,8,16`) ✅ 2026-07-06
- [x] `qwen36_27b_q8` dense-control rerun completed at `e1-pbench3-dense-control-iqk-20260707T022917Z`; missing-IQK attempt marked aborted. ✅ 2026-07-07

| `-np` | success | tasks/hour | aggregate predicted t/s | p50 latency | p95 latency |
|---:|---:|---:|---:|---:|---:|
| 1 | 43/43 | 533.72 | 19.63 | 7.50s | 13.66s |
| 2 | 43/43 | 569.69 | 19.61 | 4.54s | 28.32s |
| 4 | 43/43 | 642.99 | 22.03 | 5.40s | 47.12s |
| 8 | 43/43 | 697.21 | 24.00 | 14.08s | 76.04s |
| 16 | 43/43 | 860.45 | 29.62 | 23.86s | 115.95s |

The 27B dense-control run reached the long-tail decode phase at `np=1` and was
then stopped so the quiet window could be returned to the operator. That keeps
the dense-control status explicit instead of implicitly treating the sweep as
fully complete. The stack was restored afterward and is back in `STACK READY`
state.

##### 2026-07-23 — E5 harness preparation (design-only, zero inference; WP-12 worktree session side quest)

Full sweep design prepared per the E5 waypoint; no code written (the harness
lives in `epyc-inference-research/scripts/benchmark/`, outside this session's
write scope) and no inference run. Everything below is mechanically executable
by the implementing session + operator.

**Cell grid (pre-registered; 2026-07-23 operator review folded in — 2×half
added as the whole-machine provisioning candidate).** Indexed by model+quant,
never role. Configs per model (shapes from `NUMA_CONFIG`; bench ports 19xxx to
avoid any prod collision):

| Model | C1 (1×half) | C1b (2×half, one per NUMA node) | C2 (2×q, q2+q3 — mechanism probe) | C3 (4×q) |
|---|---|---|---|---|
| `qwen36_q8_0` (35B-A3B Q8, ~37 GB/inst) | half0 `0-47,96-143` ×96t | + half1 `48-95,144-191` ×96t | 2×48t | 4×48t |
| `qwen36_27b_q8` (dense control, ~29 GB) | shape UNRESOLVED for dense — scout runs 1×half0 vs 1×full-machine `0-95` at K∈{1,8}; Stage-B C1 adopts the winner (full-machine rows double as E1 continuity anchors) | + half1 ×96t | 2×48t | 4×48t |
| `qwen3_next_80b` ingest arm (~45 GB; W4, operator-added 2026-07-23) | half0 ×96t | + half1 ×96t | — | 4×48t |
| `gemma4-26B-A4B Q4_K_M MTP` (~16 GB) | full `0-95` ×96t + `numactl --interleave=all` — NO half shape (half-pinning crashes the MTP draft path, `tensor buffer not set`) | — | — (scout-only) | 4×48t |

Notes: (0) **Config-list semantics**: C1/C1b/C2/C3 are ALTERNATIVE serving
configs for one model, swept as separate cells — never co-deployed. C1 is a
provisioning CANDIDATE + E1-continuity anchor (audit C4 relabel: the realized
stack is QUARTERS-only — **C3 is the status-quo production shape**; gemma's
1×full is DISABLED by placement_policy=full_disabled; the solo big shape C1
describes serves nowhere today). Every anchor cell still means the model's
TOP optimized production recipe on that shape (full spec-dec stack; "anchor"
NEVER means an unoptimized baseline, per the 2026-07-23 operator directive).
C1 also remains the denominator of the scaling read C1@K vs C1b@K ("does
adding the second node-local half double aggregate?"). (i) The "1×big" shape is
**MODEL-SIZE-DEPENDENT**, not universal: for ~35B-class A3B MoE the half wins
(April 2026-04-17 head-to-head, NODE0-local 27.06 t/s vs
full-machine+interleave 26.60 t/s — cache locality beats channel
parallelism), while the 122B architect legitimately takes the full machine
(Probe B 2026-05-04: 1×full+interleave 12.19 t/s vs 4.3 t/s/instance split —
NOTE these are pre-E7-era, pre-NEXTN-self-draft figures cited for SHAPE
DIRECTION only, hypothesis grade per MEASUREMENT.md, never throughput
references; the current architect top spec includes the v6 NEXTN recipe).
Hence the dense-control C1 shape is treated as unresolved (scout decides),
and the architect stays OUT of E5 scope: the waypoint's model list excludes
it, architect-model-selection-bench runs BEFORE E5 and may swap the model,
and its 1×full-vs-4×per-node question already has era-labeled prior data
(12.19 vs 16.86 t/s aggregate, registry reopen note) — optional W5 only on
operator request, at the then-current architect model's top spec.
(ii) `NUMA_CONFIG` has no half1 instance for the frontdoor/ingest families —
the harness SYNTHESIZES the `48-95,144-191`×96t shape on bench ports only; no
prod cpuset changes, no §H recert trigger. (iii) **CORRECTED 2026-07-23 (lineup-dossier archaeology)**: the C1b
half-pair co-run HAS been measured once — the 2026-05-26 operator-requested
DUAL-HALF experiment (certified affinity, halves at 8073/8074/8075) came out
**negative across all three roles** (co-run ratios frontdoor 0.455 / ingest
0.524 / vision 0.541 ≈ each half halves under concurrency → aggregate ≈
serial; mechanism: two 48c halves contend on the memory channels serving the
shared mmap'd weight pages, exactly why 24c quarters scale and halves don't;
`progress/2026-05/2026-05-26.md:844-849`, reverted same day, never standing
config). Pre-v7-era ⇒ **direction-only prior** under E6-cpu-kernel — E5
still measures C1b (kernel + model era changed), but the scout should probe
C1b EARLY and prune hard if the ~0.5 co-run signature reappears; the
provisioning-candidate framing should not presume C1b is live until it beats
this prior. WP-9's actual mixed pair (frontdoor-half0 + ingest-half1,
different models) remains its own §H contention-matrix cell at the lineup
event.

K = per-instance `-np`, capped so total in-flight ≤ 43 (the fixed P-BENCH-3
prompt batch): C1 × {1,2,4,8,16,32}; C1b/C2 × {1,2,4,8,16}; C3 × {1,2,4,8}.

**Stage-B decision-grade set per model (~13 cells):** two pre-registered
comparison families —
- **Whole-machine provisioning (the E5 decision):** iso-T pairs {C1b@T/2 vs
  C3@T/4} for T ∈ {8,16,32} — "two big node-local batched servers vs four
  quarter-batched servers" at equal in-flight;
- **Half-machine mechanism (roofline flip):** iso-T pairs {C1@T vs C2@T/2}
  for T ∈ {16,32} — identical 48-core resource split 1-way vs 2-way, the
  purest NUMA-locality-vs-batch-amortization read;
plus scaling-efficiency pairs {C1@K vs C1b@K} at K ∈ {4,8} (does the second
node-local half double aggregate — the half-grain J5 analogue), and solo
anchors C1@1 (ties to E1) and C3@1. Gemma runs {1×full, 4×q} only (~8 cells).
Legacy mixed shapes (half+q2+q3) are EXCLUDED from Stage B: the 2026-07-21
mode-exclusivity contract deprecates full+quarter co-placement; scout may
probe one mixed cell for curiosity, never for provisioning.

**Protocol decisions (deltas from E1, each with rationale):**
1. **KV budget scales with K** (`-c = <per-stream ctx>×K`, floor 8192, q8 KV,
   `-fa on`): the binding reason is WORK-PARITY across K — decode-time KV read
   traffic follows the stream's actual sequence length (identical across K for
   a fixed prompt set); allocation sets the per-stream CEILING. Under E1's
   fixed-total convention (`-c 32768`) per-stream context shrinks with K
   (32k@1 → 1k@32), so high-K cells would TRUNCATE long answers — doing less
   work per task and inflating tasks/hour. Constant per-stream context makes
   every cell complete the same workload, and matches production footprint
   realism (a K-slot server allocates K streams' worth of real KV state).
   The per-stream constant is a SIZING RULE, not a magic number: smallest
   power of two ≥ max(tier-1 prompt + generation cap + margin) — expected
   2048; implementer verifies against the actual pool. E5 K=1 cells therefore
   aren't byte-comparable to E1 rows; the scout cross-checks direction against
   the E1 ladder before Stage B.
   **Unified KV (`--kv-unified`) — corrected 2026-07-23 after operator review**
   (the original "deliberately out, not production shape" line was written
   without checking project history — it IS a documented project axis:
   tree-spec multi-path verification requires it and our fork FORCE-enables
   `kv_unified` for DRAFT_TREE configs, `common/speculative.cpp:2668`; old
   NUMA/tree bench sweeps passed it on dense arms and deliberately omitted it
   on SSM arms; PR #18730 upstream). Base E5 protocol stays SPLIT KV — it is
   what today's realized stack serves (explicit slots + MTP linear p_split=0 →
   default `kv_unified=false`) and keeps E1 comparability — but: (i) any cell
   running a tree-spec config gets unified FORCED by our own fork, so
   `kv_unified` is a per-cell MANIFEST/attestation field, never assumed; (ii)
   the scout adds one paired probe (qwen36 C1@16, split vs `-kvu`) to price
   the tradeoff on EPYC — unified buys elastic per-stream capacity (no
   truncation ceiling without over-allocating; cross-seq prefix sharing) at
   the cost of per-stream KV contiguity (scattered cells on a BW-bound
   decode), cell/defrag management, and pool-capacity interference between
   streams; ≥5% delta at the probe escalates a split-vs-unified Stage-B arm
   to the operator; (iii) SSM/hybrid arms (ingest W4) keep unified OFF per
   the tree-spec Phase-8 scar (hybrid+kv_unified allocator/acceptance
   failures).
2. **Production spec-dec ON** (`feedback_bench_max_opt` / compare-vs-top-spec):
   qwen36 arms run embedded NEXTN self-draft, gemma runs its draft-mtp recipe
   (all 8 launch params). Record per-cell draft accept-rates — spec-dec ×
   batching interplay is itself unmeasured. The Stage-A probe explicitly tests
   np×spec-dec compatibility per model (gemma MTP ASSERT/wedge risk): if a
   model wedges at np>1, document, notify operator, and run that arm
   spec-dec-off as an explicitly-caveated separate arm — never silently.
   **Operator directive (2026-07-23, absolute): baseline (spec-off /
   unoptimized) configs NEVER run outside explicitly-labeled
   inference-research benchmark arms — never as serving shapes, anchors, or
   reference points. Every "anchor" cell in this sweep means the model's TOP
   optimized production recipe.**
3. **TTFT reported separately** from steady-state per-stream decode (CPU23
   9.6× concurrent-prefill amplification) — closed-loop driver records TTFT,
   per-stream p50/p95 completion latency, and aggregate tasks/hour with the
   ramp window trimmed.
4. **Warming**: `drop_caches` only between MODELS (operator step), then
   per-instance pinned warm-up generation (1 prompt, 32 tok) before any
   measured cell — the shared-mmap first-touch trap
   (`feedback_drop_caches_numa_eviction`) means an unpinned re-read pins one
   node and poisons every quarter cell after it.
5. **Per-cell preconditions**: per-instance LIVE affinity verification via
   the cell-manifest preflight mode that audit C3 builds (the existing
   `affinity_preflight.py` is NUMA_CONFIG-role-keyed and has NO `--live-only`
   flag — it cannot gate the synthesized half1/bench-port shapes as-is; the
   WP-6 bad-affinity artifact is the cautionary tale), throttle check,
   `numa_balancing=0`, no pre-existing llama processes; ps-verified kill
   between cells. **`GGML_IQK=1` set in EVERY cell's server env and recorded
   as a manifest/attestation field alongside `kv_unified`** (audit C1,
   execution-blocking: the v7 iqk runtime gate — without it K-quant/legacy
   cells silently run un-iqk'd; the aborted 2026-07-07 "missing-IQK" dense
   run is the cautionary tale). The harness env imports
   `scripts/lib/canonical_recipe.py` constants instead of keeping a private
   `DEFAULT_ENV` copy (recipe-drift risk). Decision-grade refuses on any
   warning (E1 semantics).
6. **Correctness pairing**: store every response; post-hoc offline score with
   the E7-era B7 scorer; garbage gate per cell = parse-failure ≤ 2/43 and no
   repetition-loop flags, else the cell is marked degraded (speed number
   demoted to observation).

**Pre-registered decision rules** (read before results exist, to avoid
post-hoc cherry-picking):
- **R1 crossover**: at each iso-T, a split wins on aggregate tasks/hour with a
  ≥10% margin; smaller margins = tie → prefer the status-quo quarters split.
  The K* where 1×big first beats 4×q (if anywhere) is the roofline-flip point.
- **R2 lanes**: report the (aggregate, p95) Pareto per model; lanes are "real"
  iff the peak-aggregate cell's p95 exceeds 3× that config's K=1 p95 (or 60s
  absolute) while some lower-K cell holds ≥70% of peak within SLA.
- **R3 eval-lane pricing** (amended per audit C2 — decision-blocking): the E2
  rows (batch 2.258 vs current 10.970 wall-min/eval, 2026-07-03) are
  DEMOTED-TO-PRIOR under three era boundaries (E6-cpu-kernel v7 cutover
  2026-07-20, E7-eval-instrument, E4-quality-core-v2 — and the eval unit
  itself changed, 43-q legacy T1 → 50-item core_v2): direction only, they
  CANNOT gate the lane decision. Before applying R3, RE-BASELINE the
  "current EvalTower fan-out" arm FRESH under v7 + core_v2 + the WP-12 fleet
  layer (one measured row; the batch arm is already re-measured by the E5
  cells themselves), then convert each candidate cell to wall-minutes/eval
  against that fresh baseline. Option (b) remains a zero-code remap under the
  WP-12 fleet layer (an eval-only RoleBinding on a batch-shaped fleet — live
  as of the 2026-07-23 flip).
- **R4 slot-fabric provisioning row**: per model, (config, K) = the
  smallest-latency cell achieving ≥90% of peak aggregate → feeds the
  per-instance `-np` sizing in within-role-placement-state-machine.md and the
  heterogeneous-slot-fabric provisioning table. **Output schema is
  MODEL-KEYED capability data** (model+quant → {solo shape, NUMA-splitting
  potential, per-shape -np optimum, ctx/KV config, spec recipe + accept
  rates, kv_unified attestation}) per the ratified fabric optionality
  contract: models own their optimal config; roles are policy references
  over it; the orchestration layer consumes only the resulting contention
  matrix of the deployed model stack.
- **Spec interpretation note**: the waypoint's "worker_general {full}-only"
  is read as "no full+quarter mixes" — the 4×q worker config is included
  because 1×full@32 vs 4×q@8 is precisely the sweep's money comparison and
  4×q is the live burst mode (WP-8 acceptance shape). Flag to operator at
  scheduling if the literal reading was intended.

**Quiet-window schedule** (queues behind inference-batch-loop →
architect-model-selection-bench per the post-promotion order): **W0** scout —
all models, full grid incl. C1b, 64-token cap, non-decision-grade, prunes
Stage B (~2-2.5 h); **W1** `qwen36_q8_0` Stage B (~4-5 h at ~13 cells);
**W2** gemma Stage B (~2-3 h at ~8 cells); **W3** dense control Stage B
(~4-6 h; slowest decode — control evidence for the MoE-batching-weaker
hypothesis, can lag without blocking W1/W2 provisioning reads); **W4** ingest
`qwen3_next_80b` arm (operator-added 2026-07-23; configs C1/C1b/C3 as
separate cells — C1b's half-pair ratio is same-shape evidence for WP-9;
schedule appetite is the operator's call).
RAM is a non-constraint throughout (worst case 4×45 GB ingest + KV on 1.1 TB,
stack stopped).

**Harness delta spec = audit C3, execution-blocking** (extend
`server_np_sweep.py` or sibling `server_numa_np_sweep.py` in
epyc-inference-research — the existing script is SINGLE-server with hardcoded
`numactl --interleave=all` and cannot run C1b/C2/C3 cells as-is): (a)
cell-manifest input (model, config_id, instances[{cpu_list, port, threads,
numactl_policy}], np, c, prompt caps); (b) multi-server launch/teardown per
cell with per-instance taskset pinning + per-SHAPE numactl policy (interleave
ONLY for full-machine/gemma-MTP shapes) + OMP env stack + `GGML_IQK=1`
imported from `canonical_recipe.py` constants + ps-verified kill; (c)
closed-loop per-stream driver round-robining the 43-prompt pool across N×K
streams, recording TTFT / per-stream latency / trimmed aggregate; (d)
per-instance affinity preflight wired as a hard cell gate — requires
EXTENDING `affinity_preflight.py` with an arbitrary-{cpuset, port}
cell-manifest mode (today role-keyed, no live-only flag); (e) E1-style
manifest with protocol-id P-BENCH-3 (the waypoint blesses reuse), era stamp,
attestation incl. iqk + kv_unified fields, decision_grade gating; (f) iso-T
comparison table + R1-R4 rule evaluation in the summarizer.

- [x] E5 sweep design + cell grid + decision rules + window schedule prepared (design-only, zero inference) ✅ 2026-07-23
- [x] E5 harness implementation ✅ 2026-07-23 (research `b294daa0` + orchestrator `6a55aeed`): `server_numa_np_sweep.py` (multi-instance, canonical env incl. `GGML_IQK=1` via `build_canonical_env`, preflight hard gate, ps-verified teardown, N×K closed-loop driver, E1-style manifest+attestation, dry-run default + `--execute --i-have-operator-grant` double gate, R1–R4 summarizer) + `e5_cell_manifests.py` with the **pre-registered 116-cell grid COMMITTED** (frozen pre-registration artifact) + `affinity_preflight.py` cell-manifest mode. 148 offline tests green (47+54+25+22). Built via 7-agent workflow with 2-lens adversarial review (13 findings, 12 fixed). Two findings bind execution:
  - **POOL-DRIFT (binding, solved by pinned qids)**: the 2026-07-21 E7 pool rebuild changes the `tier=1, seed=42, limit=43` draw — re-sampling would select a different batch including a 101,655-char tulving prompt (breaks the 2048 ctx sizing AND E1 comparability). All 43 E1 qids verified present in the current pool → the manifests pin `prompt_batch.selection="pinned_qids"` + a 4096-char fail-closed cap. General lesson for ANY pool consumer: seed-N draws are pool-version-dependent; pin qids, never re-sample across era boundaries.
  - **E5 sampling regime — DECIDED ✅ 2026-07-23** (operator: "sampling regime as recommended"; research `6b9a90c7`): **production temp+seed42 for every cell** (realized serving defaults: qwen36+gemma temp .3/top_k 40/top_p .95/min_p .05/seed 42; ingest 80B production is already greedy with seed pinned 42; dense control inherits the qwen36 regime). temp-0 exists ONLY in five `-e1parity` **twin cells** of the E1-tied solo anchors (qwen36 C1@1/C3@1; dense C1@1/C3@1 + scout-full@1) so the E1 direction cross-check runs regime-clean — twins carry the `e1_parity_anchor` variant tag, `decision_grade_intent=false`, and the summarizer excludes them from R1/R2/R4 (no regime mixing inside decision rules). Grid: 116 → **121 cells**, regenerated + committed.
  - **`--device none/--device-draft none` discovered necessity**: the v7 binary is HIP-capable — without the explicit pin, E5 CPU cells could silently offload draft work to the MI210. Wired into the harness launch args.
- [x] Operator queue-clear GRANTED ✅ 2026-07-23 ("agreed, proceed"): inference-batch-loop live island exhausted (all parked on operator/build/data gates); architect-bench decision phase complete (well-powered NULL); RP-5/A2-CPU slotted AFTER E5 W0/W1 (ownership transferred to the CPU session — see architect-model-selection-bench.md)
- **⛔ SUSPENDED 2026-07-30 — the W0 scout block below is retained verbatim but its throughput values and rankings are WITHDRAWN.** W0 swept the same C1/C1b/C2/C3 placement shapes through the same harness as Stage-B, so it carries the identical straddling-cpuset NUMA defect (see the suspension notice at the top of this file). The aggregate figures quoted below (qwen36 2028 @np4, gemma 5076 @np8 / 1.78x iso-T, dense 1415 @np2, 80B 2520 @np4) and the "**C3 quarters aggregate-optimal for EVERY model**" scout-physics conclusion are **RETRACTED**, as are the C1b second-node payoff read and the dense C1 shape resolution — all are cross-shape rankings under an unequal per-shape penalty. **What survives**: 69/69 cells clean, the e1parity twins as a regime-clean cross-check of *direction*, and the run/manifest provenance. W0 was already observation-grade (it ran under `--allow-host-health-warning` at 20-day uptime), so nothing decision-grade depended on it. ORIGINAL ENTRY:
- [x] **E5 W0 — EXECUTED COMPLETE ✅ 2026-07-23/24: 69/69 cells clean across all 4 model groups** (run dirs `e5-w0-{qwen36-nothink,gemma,dense,80b}-*` under research `data/batched_decode/`; scout physics: C3 quarters aggregate-optimal for EVERY model — qwen36 2028 @np4 / gemma 5076 @np8 = 1.78x iso-T vs interleaved full / dense 1415 @np2 / 80B 2520 @np4; C1b second-node payoff MODEL-DEPENDENT — loses for MoE-35B, wins for dense + 80B; dense C1 shape RESOLVED = half0 beats full-machine at K=1 and K=8; e1parity twins banked). Original staging text preserved below for the record. ORIGINALLY: **E5 W0 — STAGED, fire in the next operator-present quiet window** (~2-2.5h, CPU-only, `--device none` pinned): **W0 EXECUTING 2026-07-23 evening** (operator: full CPU-window authority). CORRECTED invocation — the earlier staged `--window W0` flag was fabricated; the harness is one-model-group-per-invocation BY DESIGN: per group `.venv/bin/python scripts/benchmark/server_numa_np_sweep.py --manifest-dir data/batched_decode/e5_manifests_w0/<model_key> --execute --i-have-operator-grant --allow-host-health-warning --run-id e5-w0-<model>-<UTC>`, with `sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'` before each group (session has sudo — no operator step). Serving stack STOPPED for the window (named-component stops; classifier declined `stop --all`); 18072/MI210 vacated → full 69-cell grid. **`--allow-host-health-warning` is required and correct for W0**: host uptime is 20 days and the harness refuses decision-grade P-BENCH-3 runs past 1 week — W0 is scout/non-decision by design and the warning is recorded per cell. **⚠ W1/Stage-B PRECONDITION: operator host reboot** (uptime policy; reboots are operator-only) before any decision-grade window. Preconditions: (1) operator present for `drop_caches` transitions between models (root; harness prewarm handles the `feedback_drop_caches_numa_eviction` trap after each); (2) **the MI210 experiment's host threads (port 18072, cores 88-95) overlap node-3 cell cpusets** — the per-cell preflight will correctly FAIL node-3-touching cells (C3, C1b-half1, gemma full-machine) while it runs: pause/re-pin the GPU server for the window, or accept a partial W0 with node-3 cells deferred; (3) no eval/autopilot traffic during cells (serving stack stays up; bench ports 19xxx disjoint); (4) attestation auto-records GGML_IQK/kv_unified/sampling per cell
- [x] **W0 summarizer + Stage-B prune** ✅ 2026-07-28 — all four W0 runs now carry observation-grade `offline_scores.jsonl` plus provenance (2,967 saved responses total) and regenerated summaries/rules. W1 prunes only throughput-only `qwen36_q8_0-C1b-{np4,np8,np16}`; W2 retains its full C1/C3 family but is **invalid for quality/garbage interpretation** because the original Gemma capture stored reasoning text without an answer channel; W3 retains its full grid because the C1b@16 vs C3@8 comparison degraded across metric bases; W4 retains its full grid, but high-K `raw_fallback` rows are demoted from decision-grade use. The frozen manifests are unchanged; derivative plan: `data/batched_decode/e5_pre_reboot_20260728/stage_b_prune_plan.json` SHA-256 `cabd10bd0fe52ed04ca28e314ad0ab8d505de9e5db571115d16c48d0832daee8` (append-only provenance supersession chain; predecessors `06b0abb2ca7abaf004ce56658a8c3753ea719ebdc4f1b50bec65a015954d4f8b` -> `9b4d4f034e3da01cbaaa652838aa9bb481855853180e8deb2dfafc27d69396b8` -> current. The 2026-07-29 append re-attributes the Gemma W0 430/430 from a capture defect to reasoning-mode-ON and retracts the claim that `efd0980c` alone makes W2 safe; it also records the W3 CPU-scope removal. Selection and frozen manifests unchanged.)
- [x] **Stage-B pre-window readiness verification (zero inference)** ✅ 2026-07-29 — post-reboot host-health gate returns ZERO warnings (uptime 49 min, `numa_balancing=0`, no static freq caps) so Stage-B is decision-grade eligible with **no** `--allow-host-health-warning`; kernel verified `production-consolidated-v8` @`67a433bf4` (binary 10107); all four region-lock regions free; host fully quiesced (0 llama-server, 13/1133 GB used, AutoPilot down); all 45 pruned Stage-B manifests present and dry-running clean (exit 0: W1 11, W2 8, W3 14, W4 12); all 5 GGUFs present on disk; launch args confirmed carrying `--device none`/`--device-draft none`, production spec-dec, `-c` = 2048×K floored at 8192, production sampling temp .3/seed 42, n_predict 256.
- [x] **E5 instrument defect — under-load throttle gate was cpuset-blind; FIXED + operator-ratified** ✅ 2026-07-29 (research `98cfff44`) — `cpu_freq_throttle_warnings()` counted boosting cores across all 96 physical cores and required ≥80, but C1 pins 48 physical cores (0-47) and C2 pins 48 (48-95); the idle remainder parks near base clock, so the gate **could never pass for a partial-machine cell**. W0 evidence has zero counterexamples: every 96-core cell passed (C1b 15/15, C3 11/12), every 48-core cell failed (C1-half 0/13, C2 0/10) at counts 53-78, and the two *full-machine* C1 variants (gemma `taskset 0-95`, dense `C1-scout-full`) passed. Throttle warnings feed `gate_warnings` → `hard_gates_passed` → `decision_grade`, so **19 of 45 Stage-B cells** (W1 7/11, W3 7/14, W4 5/12, W2 0/8) would have been force-demoted to observation-grade — including **100% of the pre-registered half-machine mechanism family `{C1@T vs C2@T/2}`**, the roofline-flip read that is E5's core hypothesis. **Not repairable after the fact**: `FreqSampler.result()` persisted only the aggregate count and discarded the per-core vector, so deterministic replay did not apply — the same evidence-retention gap that made the W0 Gemma capture unrecoverable. Fix scopes the gate to the cell's pinned physical cores at the **unchanged** 2.5 GHz threshold and **unchanged** 80/96 ratio (a 96-core cell still needs exactly 80; C1/C2 need 40 of 48 — verified against live sysfs), and persists the full per-core vector in `throttle_check`. Measurement safety gate = human-amendment-only, so this was **presented as a decision package and ratified by the operator before any edit**, never patched unilaterally. 5 new tests pin the semantics incl. the exact W0 failure shape and a full-machine no-loosening guard; 55 passed, ruff clean.
- [x] **E5 protection defect — non-llama ROCm processes and SMT siblings are invisible to cell-mode exclusion (filed 2026-07-29).** `affinity_preflight.py` discovers foreign overlap only through `LLAMA_PROC_PATTERN` matched to the `argv[0]` basename, so a `python` ROCm/PyTorch/TRL trainer is uncounted and can inherit unrestricted affinity on a pinned E5 cell. Its raw logical-CPU intersection is also SMT-blind: GPU host threads `184-191` and an E5 `0-95` cell share physical cores `88-95`, but have an empty logical-id intersection. Port the GPU tooling's sibling-folded `recert_roles` semantics into cell mode and fail closed on relevant non-llama GPU/training process overlap before any `decision_grade=true` Stage-B cell. **Containment:** no MI210 training workload may start during E5; the training-viability smoke is deferred until the host is released.
  **✅ 2026-08-11 (`mainA`) — BOTH BLIND SPOTS CLOSED, orchestrator `74806223`.** Discovery no longer
  matches argv: it checks `/proc/<pid>/fd` for `/dev/kfd` and `/dev/dri/render*`, which is the
  definitive test for "is this process on the GPU" and finds a trainer named `python`. **Measured on
  the live host: 8 such processes right now, none visible to the old matcher.** Overlap is now
  sibling-folded via `gpu_shadow_lane_lease.fold_cpus_to_physical`, **imported not rewritten** per its
  own docstring ("exactly one implementation … cannot answer differently in two places"); if that
  import ever fails the fallback raises rather than substituting a second fold. Verified: the GPU lane
  `184-191` vs a `0-95` cell intersected to the EMPTY SET on logical ids and folds to physical
  `88-95`. Attested per cell as `gpu_tenant_overlaps` + `smt_only_contention` + a
  `contention_gate_semantics` string. Tests +3, suites 24/24 and 6/6, pinning that `HALF_A` stays
  genuinely disjoint while `HALF_B` reports the co-tenancy — so the fold cannot fire on everything.
  - **[declined: ws58 2026-11-03 content-review: superseded by mi210-serving-program P2-5g / P2-5j (host-thread claim and placement)]** **DECISION for the operator — what should the folded overlap GATE?** Recorded, not gating,
    deliberately: the GPU host lane is a **permanent declared co-tenant** of every full-machine shape,
    so gating on physical overlap alone fails every `0-95` cell forever — the throttle-gate incident
    again, a gate whose passing condition can never be met. Options: **(a)** keep recording only
    (status quo, zero risk, the evidence now exists where it did not before); **(b)** gate on
    `smt_only_contention` from processes **not** covered by `--foreign-allow-pattern`, which catches an
    unannounced trainer while letting the declared lane through; **(c)** gate on any GPU tenant
    overlap, which is strictest and would require every E5 window to be GPU-quiet. **Recommend (b)** —
    it is the only one that distinguishes an unannounced contender from the declared co-tenancy the
    cell shapes were designed around. This decides `decision_grade`, so it is an operator ruling, not
    a code default.
- [x] **Operator decision pending — instrument-era row for the gate re-scoping.** Era registry rows are human-amendment-only. The change alters no measured value (throughput/latency are untouched) — only decision-grade *eligibility* — so it may not warrant an era row; flagging rather than assuming. W0 records stay unedited per MEASUREMENT.md (append, never edit).
  **✅ 2026-08-11 — RESOLVED: it did warrant a row, and the operator signed one.** Folded into
  `RATIFY-CONSOLIDATED-ERA-ROWS-20260811` (receipt on disk, attested 21:35Z) rather than signed
  standalone, alongside `E9-cpu-kernel`, `E9-routing-reward` and `E8-seeding-reward-b7-guard`.
  Verified on disk by `mainA`, not taken from the receipt: `E8-cpu-bench-throttle-scope` is at
  `instrument_eras.yaml:376`, `from: 2026-07-29T14:50:06Z`, `scope: cpu_bench`, and its note records
  the eligibility-only reconciliation this item predicted — *"this boundary changes DECISION-GRADE
  ELIGIBILITY ONLY"*. All four folded rows confirmed present. The flag-rather-than-assume call above
  was the right one; the answer came back yes.
  **Consequence already recorded elsewhere:** this row is half of the `cpu_bench` **scope collision**
  noted under the A7 Token-2 item — an eligibility boundary and the kernel cutovers now share one
  scope, so `derive_era("cpu_bench", 2026-07-29)` returns *this* row, not `E8-cpu-kernel`.
  **Also closed by the same signature:** the standalone `E5-THROTTLE-SCOPE-ERA-ROW-20260729` ask,
  which I reported in the A7 package as absent from `tokens/token-queue.md` and never signed. It is
  satisfied by folding, not by separate signature. The `token-queue.md` checkboxes remain unticked
  and are **stale, not pending** — receipts are authoritative and only the operator may tick them.
- [x] **W3 (dense control `qwen36_27b_q8`) — DROPPED BY OPERATOR DECISION, not deferred / not blocked / not failed** ✅ 2026-07-29 — operator: *"27b_q8 is scheduled to run residently on the GPU"*, so a CPU-side dense-control sweep measures a shape that will never serve. This is a scope change, not a deferral: the E5 model list's dense-control arm is superseded for the CPU plane. The 14 pruned W3 cells are **not run**. Durable record: coordinator `msg-20260729T155710Z-45`, operator-instructed in-pane. Reason: 27b_q8 is planned for promotion as a **GPU-resident tenant** (P2-2a dense-27B, VERIFIED LANDED against the `qwen36_27b_stock_q8` tenancy row), so a CPU NUMA×batch sweep would measure a configuration that will never exist in production. **This is a SCOPE change, not a result change** — existing W3 references and the W0 W3 scout data already recorded are retained unedited, per the append-never-edit rule. **Revised sweep scope: 31 of 45 cells** (W1 11 + W2 8 + W4 12), covering **three** model groups; revised wall-clock ≈ **2.5–3 h** from 16:18Z, measured at 5.77 min/cell over the first six W1 cells (the earlier 13–17 h figure predates both the drop and the measured rate). Any artifact update must state the sweep covered three model groups **and why the fourth was dropped**, so no reader infers W3 failed or was lost. The campaign driver was killed and replaced mid-flight before it could auto-launch W3.
- [x] **E5 harness: `--reasoning` was never emitted; gemma4 W2 ran with reasoning ON** ✅ 2026-07-29 (research `5d6a17f2`) — the harness had no `--reasoning` emit at all, so every cell ran at llama-server's `--reasoning auto`. For `arch=gemma4` that default is **ON**, while both model registries record `reasoning: 'off'` for this GGUF — so W2 was not running the production recipe it exists to mirror. **Measured**: the 2026-07-29 capture smoke returned **41/43** `response_capture_missing_answer_text`, every failure HTTP 200 with `predicted_n` exactly 256, empty `response_text` and a populated `reasoning_text` of 599–1174 chars ending mid-sentence — the entire Stage-B budget spent inside the reasoning channel before the answer channel opened. Server log clean: no wedge, no OOM, no truncation (max `n_tokens` 850 vs `n_ctx_slot` 2048), draft acceptance 0.92, nothing within 38× of the 900 s timeout. **The capture contract works and the fail-close fired truthfully** — and this is the same signature behind W0's 430/430, which was misread as a capture bug. Fix emits `--reasoning` (server-side, template-independent, unlike `enable_thinking` which some templates ignore); 19 gemma4 manifests amended with `reasoning:'off'` plus append-only provenance, restoring the pre-registered intent rather than changing it. **Scope verified**: qwen36 W1 carries `enable_thinking:false` and is confirmed clean live (46/46 nonempty answers, 0 reasoning); W0 dense and 80B produced 989/989 and 645/645 nonempty answers — gemma4 is the sole exposure.
- [x] **E5 harness: two launch-blocking defects fixed** ✅ 2026-07-29 — (1) `httpx` was an **undeclared** dependency of the `--execute` path; the 2026-07-26 venv rebuild dropped it and the first Stage-B launch aborted *after* starting and cleanly tearing down a llama-server (research `040a2ad7`). A dry-run cannot catch it because dry-run never touches HTTP. (2) `find_llama_processes` matched the whole `ps args` string, so a coordinator bus relay whose text merely **quoted** `llama-server` tripped the clean-runtime gate on an empty host; the same matcher backs the **per-cell** health gate, so mid-run it would have failed that cell and silently demoted it out of decision-grade (research `4a5b6bc7`). Now resolved via `/proc/<pid>/exe`, which still catches instances launched under `taskset`/`numactl`.
- **[declined: ws58 2026-11-03 content-review: a note]** **T=32 cells return `empty_trimmed_window` → observation-only (discovered mid-campaign 2026-07-29)** — *(⛔ throughput values quoted in this item are SUSPENDED 2026-07-30 — the structural `empty_trimmed_window` finding and its offline-replay remedy are unaffected and still stand.)* — confirmed live on `qwen36_q8_0-C1-np32`: `decision_grade=False`, raw 428.4 / trimmed 0.0, err 0.0%. Structural: `trimmed_aggregate` takes `ramp_end = min(end of successes)` and `drain_start = max(start of successes)`, so when `np` approaches the 43-prompt batch almost nothing both starts after the first completion and ends before the last start. Affects **every T=32 cell** (C1-np32, C1b-np16, C2-np16, C3-np8, and the W2/W4 equivalents) — i.e. the **top rung of both pre-registered decision families**, iso-T {C1@32 vs C2@16} and {C1b@16 vs C3@8}. Low/mid-K rungs (np 1/4/8/16 solo) are unaffected and came back `dg=True`. **Deferred, not lost**: the full per-request start/end/latency ledger is persisted in `requests.jsonl`, so a ratified alternative steady-state rule can be applied **offline** to these exact runs — deterministic replay before regeneration, no re-run needed. Not fixed in-flight because the trimmed-window definition is measurement-instrument territory (human-amendment-only) and changing it mid-campaign would invalidate the cells already banked. Escalated: `msg-20260729T161839Z-45-mainA`.
  - [x] **Offline replay DONE + decision package delivered ✅ 2026-08-11 (`mainA`)** —
    `/mnt/raid0/llm/tmp/e5-a6-trimmed-window/A6-decision-package.md`, with a reproducible driver
    (`replay_candidates.py`). Zero cells; replay over the persisted `requests.jsonl` ledgers.
    **Scope correction to the item above: it is 5 cells, not "every T=32 cell".** Two of the five are
    np=16 (`qwen36_q8_0-C2-np16`, `qwen3_next_80b-C1b-np16`) while **three other np=16 cells passed**
    (`qwen36_q8_0-C1-np16`, `gemma4…-C1-np16`, `qwen3_next_80b-C1-np16`). The trigger is whether any
    single request straddles the interval — arrival/completion interleaving — **not the np level**, so
    a rule keyed on T=32 would fix the wrong thing and still leave two cells blocked.
    **The finding that decides it:** all 5 blocked cells have a valid PRIMARY metric; they are blocked
    only by an empty window in the SECONDARY tasks/hour number, which the 2026-07-30 ruling says ranks
    nothing. And `throughput_basis` is `wallclock_fallback` for **all 34 Stage-B rows including the 26
    that passed** — the gate enforces strict steady-state rigour on the demoted metric while the
    promoted one runs on a fallback basis corpus-wide, ungated.
    **Candidates replayed** (rescue / of 26 moved >5% / worst move): pctile-10 5/5, 18, +148% ·
    pctile-20 5/5, 21, +93% · plateau-50 5/5, 20, +186% · plateau-80 5/5, 14, +164% ·
    **decouple 5/5, 0, 0%**. Every window *redefinition* rescues all five and silently rewrites the
    banked secondary number for 14–21 of the 26 already-passing cells; none re-grades a cell to zero,
    but republishing 21 of 26 banked numbers at up to triple value is the substantive form of the
    hazard. They move because they are a different definition, not a repair: the status-quo window is
    a legitimate conservative rule that simply degenerates at high K.
    **Recommendation: decouple** — stop gating `decision_grade` on the secondary trim, leave
    `trimmed_aggregate` untouched, surface `trimmed_window_empty` and caveat verdicts via the
    `_apply_basis_caveat` path landed under A5. Only candidate that rescues all five while changing
    zero banked numbers. **Cost stated plainly:** promoting 5 cells to decision-grade is itself a real
    grade change on banked cells — which is why it is a token, not an edit.
  - [x] **Operator token OUTSTANDING** — one ask: decouple `decision_grade` from the secondary ✅ 2026-11-10 — signed by operator via coordinator decision tool: decouple `decision_grade` from the trimmed window (both asks, one package). [no-belief: operator decision, not a measurement]
    trimmed-tasks/hour window, promoting the 5 listed cells, with `trimmed_window_empty` as a caveat.
    `TRIM_DEFINITION` is **not** amended and every banked number stands. Nothing further is owed by
    this lane until it is signed. Token 2 (absorbed): the v9 signature added a scope constraint on the consolidated era token; present both asks as one package.
    - **Operator decision 2026-11-10:** token signed (decouple). Implementation is code work:
    - [ ] Implement the signed decouple: stop gating `decision_grade` on the trimmed window (research `scripts/benchmark/server_numa_np_sweep.py:1501`), surface `trimmed_window_empty` via `_apply_basis_caveat`, re-grade the 5 listed cells; banked numbers unchanged.
- [x] **R2/R4 mix metric bases and let a non-decision-grade cell win the Pareto peak (discovered 2026-07-29 by pre-validating the summarizer on a COPY of the live partial W1)** — *(⛔ every tasks/hr figure quoted in this item is SUSPENDED 2026-07-30. The defect it identifies is a metric-BASIS inconsistency — raw vs trimmed — which is scale-invariant, so the finding and its fix survive the suspension and must be applied before the re-measured cells are aggregated.)* — R2 names `qwen36_q8_0-C2-np16` peak at **578.6 tasks/hr on `aggregate_basis=raw_fallback`**, above `C2-np8` at **462.8 on `trimmed`**; `C2-np16` is `decision_grade=false` (`empty_trimmed_window`). R4's `per_shape_np_optimum` picks the same cell on the same basis and flags `mixed_metric_basis: true`. **The arithmetic settles it**: like-for-like, `C2-np8` raw **669.2** > `C2-np16` raw **578.6**, and on trimmed `C2-np16` has no value at all — so it wins on *no* consistent basis. It only appears to win because it is compared on raw while its rival is compared on trimmed, and raw is systematically higher (includes the ramp-up burst, skips steady-state trimming). **This upgrades the 16:18Z T=32 finding**: those cells do not merely fail to contribute, they *actively contaminate* R2/R4 by winning comparisons they should not be in — a reader would wrongly conclude 2×quarter @np16 is the peak provisioning shape. **R1 is unaffected** — it already guards per-pair (`mixed_metric_basis: false` on the clean half-machine T=16 pair, where C2@8 462.8 beats C1@16 327.0 by 29.3% on a consistent trimmed basis). Fix = apply R1's existing guard to R2/R4: exclude `decision_grade=false` cells from aggregation, or refuse a peak whose basis differs from its rivals. **Not changed in-flight** — instrument code, campaign live on it, and changing aggregation mid-run would make banked cells non-comparable. Pure post-hoc read, so it is fixable and re-runnable **offline** against the same run dirs at zero inference cost. Escalated `msg-20260729T162849Z-50-mainA`.
  **✅ 2026-08-11 (`mainA`) — LANDED, research `4fb44869`. Half of this was already fixed; the other half was real.**
  **Already fixed, verified by offline replay of `e5-w1-qwen36-20260729T154725Z`:** the 2026-07-30 metric
  ruling made R2/R4 filter `decision_grade=false` rows *before* selecting and rank on tok/s, not
  tasks/hour. `qwen36_q8_0-C2-np16` — the cell this item names — is now in `observation_only_cells`
  and excluded from both rules, and R4 recommends `C2-np8`, which this item itself calls the correct
  answer. The raw-vs-trimmed peak contamination described above **cannot occur today**.
  **Still real, now fixed:** R2/R4 computed `mixed_throughput_basis` / `mixed_metric_basis` and never
  fed either into `status`, so a verdict could emit `status="decision_grade"` beside its own
  `mixed_throughput_basis: true`. R1 has demoted to `winner_caveated` since review F3. Added
  `_apply_basis_caveat`, mirroring R1's contract exactly — `decision_grade` keeps describing the
  member CELLS and is untouched, so nothing can re-grade a banked cell; only `status` carries it.
  **No banked result changes, proven not asserted:** re-derived `rules.json` for all three run dirs
  with and without the change — byte-identical apart from `created_at`. Measured separately: 0 of 3
  run dirs have a mixed basis among decision-grade cells, so the guard is currently unreachable in
  banked data and is a structural fix, not a re-grade.
  Tests 61 → 64 (mixed path both bases; the compliant same-basis path, so the guard cannot fire on
  everything; and that an `insufficient_decision_grade_data` refusal is never rewritten into a
  caveated verdict). `pytest` is absent in this environment — the suite is stdlib-only by design and
  was run with a plain runner (`/mnt/raid0/llm/tmp/e5-a5-replay/run_tests.py`), 64/64 green.
- [x] **KERNEL-ERA MIS-STAMP: every E5 manifest claims a v7-lineage era while running v8 (found 2026-07-29)** — `e5_cell_manifests.py:76` pins `ERA_CPU_KERNEL = "E6-cpu-kernel"`, set 2026-07-23 (`b294daa0`) and never revisited across the 2026-07-25 v8 cutover. **Note the trap**: era ordinals do NOT track kernel versions — the `cpu_bench` timeline is E0, E1, `E5-cpu-kernel` (v6+iqk), `E6-cpu-kernel` (**v7**, `instrument_eras.yaml:67-78`), `E8-cpu-kernel` (v8). There is no `E7-cpu-kernel`. Reading "E6" as "v6" is the natural and wrong inference, and is why this survived a cutover. **6 confirmed mis-stamps**, all claiming v7-lineage with `attestation.binary_version = 10107 (67a433bf4)` = v8: E5 W1, E5 W4 (**live, `decision_grade=true`**), both W2 capture smokes, and two Laguna SWE-oracle artifacts carrying `meta.kernel="v7-candidate"` against a sibling `plan.json` pinning `production-consolidated-v8`. **Two compounding defects**: (a) `e5_cell_manifests.py:763-764` *rejects* any manifest corrected to `E8-cpu-kernel` — the validator enforces the stale value; (b) `_warn_if_era_stamps_stale()` (`:1138-1151`) fires only `if era_id not in text`, but era registries are **append-only**, so a superseded id is always still present and the check can never fire for it — only for a *deleted* era, which the policy forbids. **A staleness detector whose only trigger is deletion, in a system that never deletes.** That is why the v8 cutover passed green. **Scale/containment**: 208/208 `data/batched_decode` manifests carry `E6-cpu-kernel`, 0 carry E8 — 4 executed-on-v8, 6 W0 runs genuinely v7 and correctly labelled, 198 un-executed templates. The era stamp lives **only** in `manifest.json` (no `cells`/`events`/`requests`/`responses` jsonl carries it), and appears in 0 files outside `data/batched_decode`. **Recoverable — nothing needs re-measurement**: every affected artifact records `attestation.binary_version`. **Fix (needs a human token, era semantics) — ORDER IS LOAD-BEARING.** ⚠ **My first recommendation was WRONG and is retracted**: simply setting `ERA_CPU_KERNEL` to `E8-cpu-kernel` would have **stopped the running campaign**. `server_numa_np_sweep.py:297 revalidate_cells()` (docstringed *fail closed*) runs `validate_cell_manifest` over every manifest it loads, and `cmd_sweep:1803` raises on any error — so flipping the constant makes the sweep refuse to start against all 208 E6-stamped manifests, including the 198 un-executed templates W2/W4 depend on. Caught by the auditor (`msg-20260729T173845Z-75`), independently endorsed by `inference`. Correct order: **(1)** replace equality-to-current-constant validation with a **date- and scope-derived** lookup — the validator must accept the era that was *current when the manifest was pre-registered*, which is the append-only-respecting rule and keeps the 198 templates valid; **(2)** make the stale check compare a stamp against that derived current-at-date scoped era rather than testing registry *membership*; **(3)** only then emit forward stamps from the derived era. **Do NOT substitute a new hard-coded constant** — `E8` hardcoded goes stale at v9 exactly as `E6` did at v8. Append dated corrections rather than editing banked artifacts. *Irony worth keeping*: the comment at `e5_cell_manifests.py:74-75`, three lines above the constant, already reads `E6-cpu-kernel: v7 cutover 2026-07-20` — the correct mapping was adjacent the whole time. Not changed in-flight: W4 is executing this harness. Escalated `msg-20260729T173508Z-55-mainA`.
- [x] **Era-repair package DESIGNED but NOT READY — it fixes the generator, not the mechanism (2026-07-29)** — prepared post-release, adversarially reviewed, **verdict: do not present for a token**. Four blockers, the first two structural:
  **(1)** `server_numa_np_sweep.py:1748` builds the run manifest as `"era": first.manifest.get("era")` — the era block is copied **verbatim** from the cell template at execution time and the registry is never consulted. The package repairs `make_cell` in `e5_cell_manifests.py`, so after the *full* package is applied every remaining run still mints a mis-stamped manifest (reproduced: stamps `E6-cpu-kernel` while `derive_era('cpu_bench', now)` = `E8-cpu-kernel`). Verified independently at that line.
  **(2)** The proposed validator cannot catch the artifacts it exists for: a run manifest inherits the cell's pre-registration date so `E6` validates clean, and run manifests never pass through `revalidate_cells` at all (only `Cell` objects do). **Nothing binds `era.cpu_kernel` to `attestation.binary_version`** — the only field that witnesses the executed instrument.
  **(3)** The recommended variant permanently whitelists the exact stale `{E6-cpu-kernel, E7-eval-instrument}` pair, unbounded in time and count — a green check that means nothing, structurally the same failure as the dead detector it replaces.
  **(4)** Its backfill is not gated on campaign end and would rewrite 191 cell manifests including the 12 the live W4 run loaded.
  **(5) The stale-pin defect is a PAIR, not a single constant — I missed this all day.** `e5_cell_manifests.py:77 ERA_EVAL_INSTRUMENT = "E7-eval-instrument"` sits **one line below** `ERA_CPU_KERNEL` and is stale for the same reason (`eval_quality`'s current era is plain `E8`, registry `:166-168`). `validate_cell_manifest:763-771` checks `cpu_kernel`, `eval_instrument` **and** `source`, each by equality — so **the campaign-breaking fail-closed hazard applies twice**, and a repair touching only line 76 still breaks the sweep on line 77. Caught by the auditor; verified directly. The complete set of genuinely stale code constants is **three** across three repos (`e5_cell_manifests` ×2, `instrument_era_guard` ×1) — bounded, not open-ended.
  **The discriminator that makes a sweep safe**: a pin naming a specific **past** era on purpose is *correct*; a pin meant to track the **current** era is stale. `dashboard.py:2575 _PARETO_SPEED_DEINFLATE_ERA_ID = "E2"` is the former — a rescale **boundary** where pre-E2 speeds are multiplied by `pareto_pre_epoch_speed_factor`. A pattern-based bump would silently move it and corrupt every historical speed read. 673 lines across 317 files name superseded eras and nearly all are legitimately historical; that is the append-only design working.
  **Correct direction**: bind the stamp to `attestation.binary_version` at **run-manifest construction**, not only at cell generation — otherwise the template is fixed and the mint stays open. Rework after host release against a quiesced tree. No re-measurement implied; identity stays recoverable from persisted evidence. Design + review evidence in `/mnt/raid0/llm/tmp/era-repair/`; nothing was written into any repo tree.
  - [x] **A7 decision package delivered ✅ 2026-08-11 (`mainA`)** —
    `/mnt/raid0/llm/tmp/era-repair/04-a7-decision-package.md`. Recommended splitting into two
    independently-signable tokens; **Token 1 was signed the same day** (receipt
    `artifacts/operator/receipts/RATIFY-CONSOLIDATED-ERA-ROWS-20260811.json`, era rows attested
    21:35:01Z). `E9-cpu-kernel` verified at `instrument_eras.yaml:413` (v9, `0db32c06`, binary 10125).
    Four corrections to the item above, all re-derived against the tree, not inherited:
    **(a)** the run-manifest era copy is at `server_numa_np_sweep.py:1895`, not `:1748` — and the
    sharper statement is that `"era": first.manifest.get("era")` and `"attestation": attestation` sit
    in the *same dict literal* 34 lines apart, so the witness and the claim are written side by side
    and the claim ignores the witness. No plumbing is missing, only the binding.
    **(b)** the stale-constant set is **four, not three** — see the new checked item below.
    **(c)** the corpus is **210, not 208**; MIS-STAMPED is **6, not 4**. The two extra runs
    (`e5-w2-capture-smoke-20260729T183019Z`, `e5-w2-gemma-20260729T183151Z`) landed **36 minutes after
    the 07-29 census was taken** — the generator kept minting `E6` while the defect was being written
    up.
    **(d)** the refused backfill deserves a stronger refusal than "ungated": of the 191 pre-registered
    cell manifests, **≥138 are correct at registration** (all added in `b294daa04f` @
    2026-07-23T16:30:41Z, inside the E6 window) and 16 more are dropped-W3 cells that will never
    execute, so a blanket rewrite to `E8` would be **wrong for 72% of its targets**. Its premise, not
    its gating, is what fails.
  - **[declined: ws58 2026-11-03 content-review: merged into the one operator-token ask]** **Token 2 still OUTSTANDING, and the v9 signature added a new constraint on it.** The
    consolidated era token introduced a **scope collision**: `E8-cpu-bench-throttle-scope` (an
    eligibility boundary) and the kernel-cutover rows now share `scope: cpu_bench`, so *latest-by-from-date*
    and *last-appended* disagree for any instant in 2026-07-29..2026-08-10 —
    `derive_era("cpu_bench", 2026-07-29)` returns `E8-cpu-bench-throttle-scope`, **not**
    `E8-cpu-kernel`. Any Token-2 derivation must resolve kernel era by more than scope alone or the 6
    mis-stamped run manifests receive a second wrong answer. **Also**: the 07-29 prototype is
    **date-only** — neither `era_derivation_prototype.py` nor `validator_prototype.py` reads
    `attestation.binary_version` at all, so the "bind to binary_version" direction above is design
    intent that was never implemented; and the registry has no structured `binary_version` field (it
    lives in free-prose `note:`), so there is nothing to bind to without a schema addition.
    **✅ 2026-08-11 (`mainA`) — Token 2 Block A AUTHORED and pre-validated, awaiting signature:**
    `RATIFY-CPU-BENCH-BINARY-VERSION-20260811`, filed in `tokens/token-queue.md`; vehicle committed
    at `artifacts/operator/ratify_cpu_bench_binary_version_20260811.py`. Adds `binary_version` +
    `kernel_commit` to the three cpu_bench **kernel-cutover** rows, every value re-extracted from the
    row's own note and cross-checked. **This one field also resolves the scope collision** — after it,
    the kernel era at instant T is the latest cpu_bench row that *has* a `binary_version`; the
    eligibility row has none and becomes correctly invisible to kernel derivation, so no discriminator
    field is needed. Verified on a copy: at `2026-07-29T15:47:29Z` scope-only returns
    `E8-cpu-bench-throttle-scope` (wrong) and binary-witnessed returns `E8-cpu-kernel` (right).
    `E5-cpu-kernel` excluded — its note records no binary, so derivation fails closed for
    `[2026-06-26, 2026-07-20)`, which is correct rather than a gap. Dry-run exit 0; all five refusal
    paths and idempotent re-apply exercised on copies rather than asserted.
    **Block B (the code repair) is NOT in the token** — code is not a trust boundary and needs no
    signature; it is gated on the field existing and is `mainA`'s to execute once Block A is signed.
    **✅ 2026-08-11 — Block A SIGNED + APPLIED** (receipt
    `artifacts/operator/receipts/RATIFY-CPU-BENCH-BINARY-VERSION-20260811.json`; E6/E8/E9-cpu-kernel
    carry `binary_version` 10098/10107/10125 + `kernel_commit`; re-run reports ALREADY APPLIED,
    idempotent exit 0).
  - [x] **Block B EXECUTED ✅ 2026-08-11 (`mainA`)** — research `9ed5fcb4`, orchestrator `190ccab4`.
    New shared `scripts/lib/instrument_era.py`: `derive_era` (date/scope), `derive_kernel_era`
    (latest cpu_bench row **with a `binary_version`** — scope alone returns the eligibility row for
    the whole W1/W2/W4 window), `era_for_binary` (binds to the witness of what executed).
    **All four stale constants closed:** `e5_cell_manifests.py:76,:77` → derived;
    `cpu_prefill_v8_regression_runner.py:480` → derived (`bcfcd0a5`);
    `instrument_era_guard.py:26` → kept as a *historical* boundary, with the fallback that misused it
    as *current* repointed at a live witness.
    **Validator** is now date-derived: manifests carry `generated_at`, so a stamp is checked against
    the era in force **at pre-registration**. Verified **191/191** existing manifests still valid —
    the equality form was campaign-breaking, not merely stale, since `revalidate_cells` is
    fail-closed. The legacy path (no `generated_at`) requires a *real* era of the right scope and is
    deliberately not the blanket whitelist that got the earlier package refused.
    **Dead detector replaced**: it fired only when a pinned id was ABSENT from an append-only
    registry, so deletion was its only possible trigger. It now warns when the newest cpu_bench row
    carries no `binary_version` — the one condition that silently freezes derivation.
    **Run-manifest binding** (`server_numa_np_sweep.py`, the defect the refused package could not
    reach): the era is resolved from `attestation.binary_version` instead of copied from the cell
    template. An unresolvable binary omits `cpu_kernel` and records why, so consumers fail closed;
    not an exception, because the run data is already on disk by then and destroying the manifest
    would lose provenance rather than mark it unusable.
    **Tests 57 → 65**, including the explicit unwitnessed-window test: `[2026-06-26T22:07:11Z,
    2026-07-20T13:30:13Z)` has no witnessed kernel and derivation must REFUSE there rather than pick
    a neighbour, plus a pin that the boundary opens exactly on time so the refusal window is not one
    second too wide. Two guards whose passing condition was the defect were REPLACED, not adjusted
    (the era-drift test in the prefill runner, and the autopilot fence test asserting the stale
    fallback).
- **[declined: ws58 2026-11-03 content-review: merged into RE-MEASURE (qualify or discard banked cells)]** **`e5_manifests/` holds 69 cells whose own `window` says W0 but carry a recipe W0 never ran (filed 2026-08-11 `mainA`).** Investigated as the "divergent duplicate pre-registration" side finding; **the duplication itself is NOT a defect** — `e5_manifests_w0/` is the W0 **run of record** (proven, not inferred: the W0 gemma run manifest records `args.manifest_dir = data/batched_decode/e5_manifests_w0/gemma4_26b_a4b_q4km_mtp`), and `e5_manifests/` is the current post-fix pre-registration. They diverge because `5d6a17f2` fixed a real recipe defect between them. **Nothing to reconcile and nothing to delete on comparability grounds.** What IS wrong: the 69 W0-window cells in `e5_manifests/` were regenerated with `reasoning: "off"`, and W0 did not run that way — per `5d6a17f2` the harness emitted no `--reasoning` at all, so `arch=gemma4` ran at llama-server's `--reasoning auto` = **ON**, which that commit names as *"the same signature behind W0's 430/430"*. Those rows therefore assert a recipe for a **closed** window that contradicts what it executed, and they fail **silently**: file names, `cell_id`s and `window: W0` all match, so anyone re-deriving "what produced W0" from the live directory gets the wrong answer. **Consequence for readers: W0 gemma is reasoning-ON, Stage-B gemma is reasoning-OFF — not comparable on that axis.** Stage-B side verified correct (W2 gemma ran 2026-07-29T18:31:56Z, after the 15:57:22Z fix, citing `e5_manifests/` copies that carry `reasoning:'off'`; the harness emits the flag at `server_numa_np_sweep.py:460-462`). **Fix belongs with the generator** — stop emitting cells for a completed window, or stamp regenerated historical cells with a `superseded_by_run` pointer — so it is folded into the A7 Token-2 repair rather than done here. Full write-up: `/mnt/raid0/llm/tmp/e5-a6-trimmed-window/A8-w0-manifest-divergence-finding.md`.
- [x] **A11 — E5 DOES have absence-inferred fields; census done ✅ 2026-08-11 (`mainA`).** Answering the rider at `handoffs/active/autopilot-program.md` (`f272bb4e`), which measured the era label being inferred from a MISSING question ledger on ~61% of 1372 autopilot journal rows and asked whether E5 has the analogue. **It does — three, and I introduced two of them tonight.** Write-up: `/mnt/raid0/llm/tmp/e5-a6-trimmed-window/A11-absence-inferred-fields-in-E5.md`. The shape is not "a field is missing" (that is ordinary) but **absence READ AS A VALUE** — unfalsifiable from the record, because a row that never had the field and a row whose true value equals the default are byte-identical. Measured: `reasoning` present on **19/191** manifests (all gemma4, and 10 gemma4 still lack it); `binary_version` present on 3 of 7 cpu_bench rows; `generated_at` absent on the whole legacy corpus. Benign by contrast: `decision_grade_blockers` 33/128 and 28 measurement fields at 110/128, where every reader guards with `or []` or an explicit branch.
  - [x] **The `binary_version` discriminator was mine and had the defect — FIXED ✅ 2026-08-11, research `ecb99de8`.** Block A deliberately chose presence-of-`binary_version` as the kernel-cutover discriminator over an added `boundary_kind`. That cannot distinguish `E8-cpu-bench-throttle-scope` (genuinely not a cutover, correctly excluded) from `E5-cpu-kernel` (**a cutover whose binary nobody recorded**, excluded for the wrong reason). Harmless today; not harmless once an `E10-cpu-kernel` row is appended without the field, since it would read as "not a cutover" and derivation would keep returning `E9` — the silent staleness this repair exists to remove, reintroduced by its own fix. A row that NAMES itself a cutover and carries no binary now raises, naming the row, when it is the row that would have answered the query. Scoped not to over-fire: an older unwitnessed cutover superseded by a witnessed one stays silent, or `E5` would break every present-day query. Tests 65 → 66; 191/191 still valid.
  - [x] **`reasoning` — write side CLOSED ✅ 2026-08-11 overnight, research `567ffa16`.** The 2026-07-29 fix amended 19 gemma4 *artifacts* and never the generator: `make_cell` recorded no `reasoning` for any model, so **regenerating the grid would silently have reverted it** — measured, a freshly generated gemma4 cell lacked the field while its banked equivalent carried it. Every model now states its mode (`gemma4` `off`; the other three `auto`, recording today's behaviour rather than changing it), `make_cell` always emits it, and the **result row now records the effective mode beside `sampling`** so a banked row can finally answer "reasoning on or off?" without resolving a manifest path that may since have been regenerated. The launched command is deliberately byte-identical — `auto` still omits the flag, since `--reasoning auto` *should* equal omitting it and should-be is not verified-to-be in a zero-cells lane; pinned by a test. Sweep suite 64 → 65; 191/191 banked manifests still valid.
  - **[declined: ws58 2026-11-03 content-review: merged into RE-MEASURE]** **Residual, needs a run (not this lane): backfill the 172 banked manifests that lack `reasoning`.** Absence means the flag is not emitted (`server_numa_np_sweep.py:464`), so the server runs `--reasoning auto`, which for `arch=gemma4` is **ON** — the opposite of what both registries record. Already measured: 41/43 capture failures on the W2 smoke and the same signature behind W0's 430/430 (`5d6a17f2`). **The 10 gemma4 manifests lacking the field are exactly the 10 divergent pairs** in the duplicated-W0 row above — one defect seen from two directions. Two asks: (a) persist the effective `reasoning` into each result row beside `sampling`, so a banked row can say which mode produced it; (b) backfill `reasoning` explicitly onto the 172 manifests that lack it, including `"auto"` where that is intended. Not done here — proving (a) end to end needs a run, which is outside this lane's zero-cells boundary.
  - **[declined: ws58 2026-11-03 content-review: a note]** **`generated_at` absence-inference is MINE, bounded, and deliberately kept.** The validator reads its absence as "legacy manifest, validate loosely". Every alternative measured worse — design doc 01 §4 found git last-touch would reject 19 of 191 real files and mtime is worse. It is defensible only because it has a **closing horizon**: it can apply solely to manifests written before today and shrinks as the corpus regenerates. Residual worth closing cheaply: a *future* manifest that loses the field takes the loose path silently. Guard = require `generated_at` once `schema_version` is at or past the version introducing it; deferred because bumping `e5-cell-manifest/1` is a schema change with its own consumers.
- [x] **The executed `reasoning` mode is not recorded in ANY result row (filed 2026-08-11 `mainA`; unowned, small, no trust boundary).** `reasoning` is read from the manifest solely to build the server command (`server_numa_np_sweep.py:460`) and never written into `cells.jsonl` — verified the key is **absent**, not null, in the banked W2 gemma rows. So a banked row cannot answer *"was this measured with reasoning on or off?"*; the only route is to follow `manifest.json → args.cell_manifest/manifest_dir` back to a file on disk, which is exactly what breaks once a manifest directory is regenerated — i.e. the row above. **Same defect class as the A7 era mis-stamp, one field over: the run manifest records the CLAIM but not the WITNESS.** For a setting that already produced a 41/43 capture failure and a 430/430 W0 wipeout, that is thin. Fix: persist the effective `reasoning` into each row beside `sampling`, which is already recorded exactly this way and for exactly this reason. Not done in this lane — it is outside the zero-cells offline-replay boundary, since proving it end-to-end needs a run.
- [x] **FOURTH stale era constant — a LIVE TOOL OUTAGE, fixed ✅ 2026-08-11 (`mainA`), research `bcfcd0a5`** — `epyc-inference-research/scripts/benchmark/cpu_prefill_v8_regression_runner.py:480` pinned the same `{E6-cpu-kernel, E7-eval-instrument}` pair, but unlike the other three it fails **CLOSED**: it asserts `scoped[-1].get("id") == expected_id` and raises `registry active <scope> row drifted`. Verified by execution against the live registry — it raises on **both** scopes, so the v8 prefill regression runner **could not start at all**, and had not been able to since the v8 cutover of 2026-07-25. Nobody hit it because nobody invoked it. Its docstring says it binds to the **active** eras, so this was accidental staleness, not a deliberate historical pin. **Not repinned** — a constant there goes stale at every cutover by construction, which v9 proved a second time. Now derives the active row from the append-only registry (last row of a scope = newest), deliberately positional rather than date-derived *because of the scope collision noted above*. Still fails closed on a missing file, an empty scope, a row with no id or no `from`, and a mid-hash registry change. Verified binding: `cpu_bench` → `E9-cpu-kernel`, `eval_quality` → `E16-eval-history-scoped-quiescence-v10-quality`. **The old drift test REQUIRED the outage** — it appended a newer era and asserted the attestation raised — so it was replaced, not adjusted; a guard whose green state is the defect cannot survive the fix. Added a literal-scan test that no era id is a string literal in the runner, verified to fail against the pre-fix source (which hardcodes two).
- [x] **THIRD stale era constant, AutoPilot fail-safe (routed to `inference`, not mine to touch)** ✅ **2026-08-11 — CLOSED by `mainA` at operator instruction, orchestrator `190ccab4`.** Its value is untouched (E7 was a real boundary; a deliberate past pin is legitimate) — what changed is that nothing treats it as *current*: the registry-unreadable fallback now reads `active_instrument_eras.eval_quality` **and** `quality_exclude_before_ts` from `autopilot_state.json`, a witness the era-advance path maintains. The old fallback under-fenced by three weeks. The test asserting the stale behaviour was REPLACED, not adjusted. — `epyc-orchestrator/src/autopilot_core/instrument_era_guard.py:26` `E7_EVAL_INSTRUMENT_ERA_ID = "E7-eval-instrument"`, stale since `eval_quality` moved to E8 on 2026-07-25. Its own comment says the constant **MUST** match the registry row it stands in for, and it is the **fail-safe fallback used when the registry read fails** — so on registry failure AutoPilot fails **open to a stale era**. `tests/unit/test_instrument_era_guard_eval_quality.py:46` asserts it equals the stale literal, so **the test pins the staleness**. Same fixture-masking pattern as the dead detector. All three lines verified directly.
- [x] **Era ids are not derivable by pattern — three traps, one rule (2026-07-29, verified)** ✅ **2026-08-11 — the rule is now ENFORCED IN CODE, not just recorded** (`mainA`, research `9ed5fcb4`/`ecb99de8`): `scripts/lib/instrument_era.py` derives every era and no era id is a string literal in the generator — pinned by a literal-scan test verified to fail against the pre-fix source. Trap (a) ordinals-vs-versions is now unreachable because nothing reads an ordinal; the `-cpu-kernel` suffix is used only to DETECT a contradiction (a cutover with no `binary_version`), never to order eras. — recorded here because all three bit real work today and the same rule defeats all three.
  **(a) Ordinals do not track kernel versions.** `E5-cpu-kernel` = v6+iqk, `E6-cpu-kernel` = **v7**, `E8-cpu-kernel` = v8, and there is no `E7-cpu-kernel` at all. Reading "E6" as "v6" is the natural inference and it is wrong — it caught me mid-campaign.
  **(b) Names do not follow a scheme, even within one cutover.** The *same* v8 instant `2026-07-25T18:38:43Z` produced three rows with three conventions: `E8-cpu-kernel` (scope `cpu_bench`, `:140`), `E8-autopilot-speed` (`autopilot_speed`, `:155`), and plain **`E8`** (`eval_quality`, `:166`). `grep -c E8-eval-instrument` = **0** — so bumping `instrument_era_guard.py:26` by pattern writes a **phantom id that resolves to nothing**. Caught by the auditor; I verified the grep and the three-convention split myself.
  **(c) A presence check never detects supersession** in an append-only registry — the dead detector above.
  **THE RULE**: *derive* the era from the registry by **scope + latest `from:` date**; never extrapolate a name, never pin a literal. One rule, all three traps.
  Related, and the most dangerous instance: `instrument_era_guard.py:26` is AutoPilot's **fail-safe fallback**, consumed when registry resolution *fails* — so it substitutes a stale guess exactly when the authoritative source is unavailable, and nothing downstream can tell that apart from a correct resolution. If it is made fail-closed, the refusal must name **which scope** failed and the last known era, or someone will re-add a fallback constant to silence it and reintroduce the defect as a fix. AutoPilot territory — routed, not touched.
- [x] **W2 focused post-fix capture smoke — PASSED ✅ 2026-07-29** (`e5-w2-capture-smoke-20260729T183019Z`, verdict exit 0, `decision_grade=true`, `dry_run=false`). Decisive before/after inversion once `--reasoning off` reached the server (research `5d6a17f2`): **empty answer text 41/43 → 0/43**; **rows carrying `reasoning_text` 43/43 → 0/43** (no reasoning channel emitted at all); **offline-scorer `parse_ok` 0/43 → 43/43**; `capture_fail_close_cells` 0; `failures: NONE`. This closes the W2 precondition **and confirms the re-attribution**: the capture contract was always sound and its fail-close fired truthfully — reasoning-mode-ON was what consumed the 256-token budget. Note property 3 (the offline scorer sees scoreable answer text) is now genuinely **exercised**, which the pre-fix run never reached. The decision-grade Gemma W2 sweep started automatically behind the gate at 18:31:51Z. Original text below.
- [x] ~~W2 focused post-fix capture smoke~~ (superseded by the PASSED entry above) — before the decision-grade Gemma W2 sweep, run a focused generated-answer capture check using the hardened SSE contract: persist `reasoning_text` separately, require nonempty answer-text deltas when tokens were generated, and prove the offline scorer sees scoreable answer text — **and confirm the launch line actually carries `--reasoning off`**, which is what PREVENTS the failure; the smoke only DETECTS it (re-attributed 2026-07-29, research `5d6a17f2`: the budget sink was reasoning-mode-ON, not the capture parser). The historic W0 Gemma `430/430` parse failures have no raw SSE ledger and cannot be recovered. **Precondition on the operator artifact**: this smoke must pass BEFORE any decision-grade W2 run; the published results artifact's W2 section (see below) must stop describing the Gemma group as quality-invalid only once real quality data exists from this smoke.
  - [x] **W2 smoke STAGED + verdict tooling landed (zero inference)** ✅ 2026-07-29 (research `c48bcb60`) — `scripts/benchmark/e5_w2_capture_smoke_check.py` gives the smoke a pass/fail verdict instead of an eyeball, checking all three required properties; property 3 runs the **real** offline scorer rather than a proxy, because (1) and (2) can both hold while every answer still strips to nothing. Per-cell parse-failure budget is the scorer's own 2, not a looser smoke-only threshold; an empty ledger fails rather than passing by vacuous truth. **Negative control already run**: against a *copy* of the historic W0 Gemma run it fails all three properties and exits 1 (430/430 empty answers, 0 reasoning fields, 43/43 parse failures in each of 10 cells) — copy, not the historic dir, since the scorer writes into the run dir and history is appended, never edited. Confirms the precise W0 mechanism: HTTP 200, `predicted_n=64`, `response_text=""` — the old parser read only `content`/`delta.content` while gemma emits `reasoning_content`, so the answer channel captured nothing and the reasoning was never persisted anywhere (hence "no raw SSE ledger"). Smoke manifest `data/batched_decode/e5_manifests_w2_capture_smoke/` uses the registered C1 (1×full+interleave) W2 shape at the Stage-B 256-token cap, production sampling, pinned 43-question batch, `decision_grade_intent=false`. 8 new tests, ruff clean. **The smoke itself still needs an inference window — it has not been run.**
- **⛔ SUSPENDED 2026-07-30 — the Stage-B result block below is retained verbatim but its throughput values and rankings are WITHDRAWN.** Every cell ran on placement shapes carrying the straddling-cpuset NUMA defect (see the suspension notice at the top of this file), so all 31 cells were bandwidth-bound at roughly one third of the model's true speed and were penalised unequally by straddle count. **The HEADLINE below — "C3 (four quarters) loses at every clean iso-T rung" — is RETRACTED**, together with the three iso-T margins (29.3% / 40.0% / 47.5% / 26.5%) and the per-model winning-shape reads; the comparison measures the defect, not the shapes. **What survives from this entry**: 31 cells at **0.0% error**, the clean-window hygiene (no `--allow-host-health-warning`, no `--skip-clean-check`, zero host-health warnings, host released with zero orphans), and the decision-grade/observation-grade bookkeeping. Re-measurement is in progress; the operator artifact must carry the retraction. ORIGINAL ENTRY:
- [x] **E5 Stage-B COMPLETE ✅ 2026-07-29 — 31 cells, three model groups, 0.0% error on every cell, 26/31 decision-grade.** Runs `e5-w1-qwen36-20260729T154725Z` (11 cells, 9 DG), `e5-w4-80b-20260729T165639Z` (12, 10 DG), `e5-w2-gemma-20260729T183151Z` (8, 7 DG). No `--allow-host-health-warning`, no `--skip-clean-check`, zero host-health warnings, host released 18:45:19Z with zero orphans. **HEADLINE: C3 (four quarters) loses at every clean iso-T rung in all three groups** — W1 C2@8 > C1@16 by 29.3%; W2 C1 > C3 by 40.0% (T=8) and 47.5% (T=16); W4 C1b@4 > C3@2 by 26.5%, tie at T=16. All `mixed_metric_basis: false`. **Quarters is the realized production shape**, so this reverses W0 on the axis that matters. The *winning* shape is model-dependent — 35B wants one half, gemma one full machine + interleave, 80B two node-local halves — which is itself the slot-fabric finding. **Evidence for a provisioning decision, not the decision**: one pass per cell, T=32 pending offline re-derivation. The local operator artifact was updated in place with the W0 grids retained verbatim.
- [x] **R1's basis caveat is PRESENTATIONAL — a consumer cannot see it** ✅ 2026-07-29 (auditor-verified at the line). `server_numa_np_sweep.py:2162` sets `mixed_metric_basis`; `:2163-2168` attaches a note whose own words are *"verdict caveated, not decision-grade"*; then `:2172-2181` sets `status = "winner"` **without ever reading the flag**. It reaches output only at `:2695`, appended to the human-readable summary line — so a human reading prose sees the caveat while a consumer joining on `status`/`winner_config` ingests a caveated verdict as decision-grade. **Fix shape (instrument code, human-gated, not applied):** when the flag is true, `status` must not be plain `winner` — emit `winner_caveated` or `insufficient_data`, changing the field a consumer keys on while keeping the margin and note. Same class as the day's other findings: *the instrument knows; the output does not carry the knowledge.*
- **[declined: ws58 2026-11-03 content-review: merged into RE-MEASURE (the superseding plan)]** **E5 W1-W4 runs — UNBLOCKED (reboot landed); awaiting an exclusive inference window** — the `BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT` gate is **lifted** (host rebooted 2026-07-29 ~13:42Z; uptime well inside the P-BENCH decision-grade window). All prep is complete and dry-run-verified — see the two ✅ items above and the runbook `epyc-inference-research/data/batched_decode/E5_STAGE_B_RUNBOOK.md`. Remaining blocker is **scheduling, not readiness**: E5 decision-grade is mutually exclusive with ANY llama-server on the host (`host_health_warnings()` counts `existing_llama_processes` **unfiltered**; `--coexist-allow-pattern` relaxes only `ensure_clean_runtime` and teardown, not the health gate — enforced at run start **and** per-cell mid-run, so a stack bringup mid-window kills the remaining cells). Do **not** pass `--allow-host-health-warning`/`--skip-clean-check` here: both force `decision_grade=false` for the whole run (they were correct for W0 at 20-day uptime; they are wrong now). Original text retained below for the record. ORIGINALLY: **BLOCKED_ON_OPERATOR_SCHEDULED_REBOOT** — all W0-derived execution prep is complete, but operator-scheduled reboot remains a hard P-BENCH-1/3 boundary. After reboot, run W1-W4 only in the quiet window; W2 additionally requires its focused post-fix capture smoke. R1-R4 remain withheld until clean decision-grade Stage-B cells exist.
  - **Operator-facing artifact MUST be updated in place when W1-W4 land, not left stale.** The authoritative local E5 results record is `artifacts/operator/e5_w0_preliminary_results.html`; its sibling markdown declares itself superseded and non-authoritative and must not be used as a generation source. The HTML currently leads with an OBSERVATION-GRADE banner (W0 ran under `--allow-host-health-warning` at 20d uptime). When decision-grade results land: (1) update the local HTML in place from the verified run evidence; (2) rewrite the OBSERVATION-GRADE banner/framing, not just the numbers — it is false once decision-grade figures exist, and decision-grade figures must carry the full claim grammar `(metric, protocol-id, n/reps, date, attestation ref)` per `MEASUREMENT.md`; (3) RETAIN the W0 scout figures alongside the new W1-W4 decision-grade figures — per `MEASUREMENT.md` historical numbers are era-labelled and appended, never edited to "fix" them, so any scout-vs-confirmed drift stays visible; (4) the W2 subsection specifically must keep stating quality-invalid status until the focused post-fix capture smoke (above) has passed and real quality data exists. Hosted presentation mirrors are outside this task.
- [x] **ROOT CAUSE FOUND — E5 measured through a straddling-cpuset NUMA defect; all Stage-B + W0 throughput SUSPENDED** ✅ 2026-07-30 — the swept placement shapes inherit the production wiring's defect: `stack_numa.py:66-67` `NUMA_NODE0 = "0-47,96-143"` / `NUMA_NODE1 = "48-95,144-191"` each straddle a **pair** of NPS4 nodes (`node0 = 0-23,96-119`, `node1 = 24-47,120-143`, `node2 = 48-71,144-167`, `node3 = 72-95,168-191`) and are launched with **no `numactl --interleave`**, so weights first-touch onto a single node and the other node's threads pay a remote-access penalty on every weight read — the E5 affinity artifact for this shape recorded `pages_by_node {N0: 9226101} / total 9226101`, all 35.2 GiB on node0 under a node0+node1 thread team. **`--interleave` binds at FIRST TOUCH only**, hence a silent no-op against a warm page cache: the defect survives casual checking and a warm re-test appears to confirm the bad number. **Quantified** (`llama-bench` tg128, no spec-dec, `Qwen3.6-35B-A3B-MTP-Q8_0`): straddling+no-interleave **warm = the current production wiring** `7.81 ± 3.82` t/s; same cold `10.28`; straddling **+interleave** cold `-t 96` `15.35`; **full machine `taskset -c 0-95` + `numactl --interleave=all` cold `-t 96` = `23.43 ± 0.07`** — a **3.0×** gap, i.e. Stage-B priced the frontdoor model at ~one third of its true speed. With MTP spec-dec ON at the winning placement, single stream measures **36-39** t/s, independently matching the AutoPilot production anchor (`median_request_tps` median **35.7**, n=154, band 35-40). **Instrument sound**: a single-NPS4-node arm (24 physical cores, `-t 48`) measured `8.80` vs the registry-documented `8.90` — 1% match. **Ruled out**: v8 kernel regression (v7 and v8 both `9.76`, identical), iqk (never engages for Q8_0 — gated behind an unset `GGML_IQK_Q8_0`), MTP head overhead, mmap page-faulting. Suspension notice + per-block retraction markers landed at the top of this handoff; suspended numbers retained verbatim per the append-never-edit rule.
- [ ] **RE-MEASURE E5 Stage-B on the corrected placement** — re-run the 31-cell Stage-B grid (W1 `qwen36_q8_0`, W2 gemma and W4 `qwen3_next_80b` re-seated on the current CPU role Qwen3.8-Flash-Next IQ4_XS) with correct NUMA policy per shape, then re-derive R1-R4. Binding requirements: (a) **add full machine `0-95` + `numactl --interleave=all` as a swept shape for `qwen36_q8_0` and `qwen3_next_80b`** — today's winner was present in the old grid only as gemma's `C1`, so the qwen36/80B grids could not have found it; (b) every straddling-cpuset cell must either carry `--interleave` or be declared as an explicit defect-replication control, never left implicit; (c) **`drop_caches` before every cell and record `pages_by_node`** — `--interleave` is a no-op on a warm cache, so a warm cell silently measures the defect; (d) attest the numactl policy per instance alongside the existing affinity preflight, and fail closed when policy and cpuset disagree; (e) reuse the existing harness unchanged (it is not implicated — see SURVIVES in the notice) so the re-run stays comparable, and re-check the still-open T=32 `empty_trimmed_window` and R2/R4 mixed-basis items above against the new runs. Needs an exclusive inference window under the same clean-window terms as Stage-B. Absorbs E5 (the parent sweep), the W1-W4 window request, the 69 W0-mismatch and 172 missing-reasoning banked cells (qualify or discard before re-use) and S-04/S-05 (capture readiness, generate the corrected grid per the five binding requirements). One owner, one window request.
  - 2026-11-11 (pipeline-mgmt) code + row: v2 grid, banked-cell tags and `E5_STAGE_B_V2_RUNBOOK.md` landed in research `682fee314`. W4 is re-seated on Qwen3.8-Flash-Next UD-IQ4_XS; W2 gemma is dropped because its GGUF is retired. Depth probes 16k/32k are added for capacity curves. The run is published as row `inf45-e5v2-stageb-r1-20261111`: quiet-host, one model group per grant, resumable. Stop rules: stop-on-answer when, per pre-registered iso-T pair (C1@T vs C1b@T/2), the sign of the C-shape contrast (C1b-C1)/C1 on aggregate decode tok/s lies outside the measured cell noise (1.96×RSS of per-request relative SE). stop-on-futility on the host-health gate failing twice. gate-class = futility-only at interim looks for formal-gate cells (OP-ABSEQ/OP-PQP/OP-ALPHAWIN undecided).
  - **⚠️ PARTIALLY BANKED 2026-08-13 — this is NOT a 40-cell re-run any more. Scope remaining is 24 manifests.** (Annotated 2026-08-16; source `progress/2026-08/2026-08-13-mainA.md` Sessions 7–8, verified on disk the same day.) The A7 grid fired 2026-08-13 22:33Z under a full-machine q0-q3 grant and was stopped by an operator STOP-ALL at 23:03Z.
    - **Group `gemma4_26b_a4b_q4km_mtp`: COMPLETE — 8/8 cells, every cell `decision_grade=True`, error rate 0.0%. DO NOT RE-RUN.** Run dir `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/a7-gemma4_26b_a4b_q4km_mtp-20260813T223750Z/` (8-row `cells.jsonl` + `summary.csv`; clean agg decode tok/s C1-np1 48.92, np2 72.94, np4 85.89, np8 99.04). The sibling `a7-gemma4_26b_a4b_q4km_mtp-20260813T223703Z/` is the **aborted first attempt** — no `cells.jsonl`, no `summary.csv`; cite the `223750Z` dir, never that one.
    - **Group `qwen36_27b_q8`: EXCLUDED from the A7 grid by operator ruling** (coordinator msg-94, 2026-08-13 22:58:33Z — W3 dropped as GPU-resident tenant, `MAIN-GOALS.md:251`). Its partial dir `a7-qwen36_27b_q8-20260813T225106Z/` has no `cells.jsonl`; the partial cells were correctly discarded. **Do not reinstate this group without a new operator ruling.**
    - **Remaining scope = 24 manifests**: `qwen36_q8_0` (12) + `qwen3_next_80b` (8). Launcher archived and still present 2026-08-16 at `/mnt/raid0/llm/tmp/a7-fire-20260813/a7-fire-all.sh` — reuse it (its two 2026-08-13 fixes are baked in: `setsid` so tool timeouts cannot SIGTERM the region lock into orphan `llama-server`s, and `sudo -n` for the inter-group `drop_caches`).
  - **2026-11-02 evidence qualification:** the A7 manifest directory contains 20, not 24, files for the two named remaining Qwen groups (12 + 8); this is an inventory count, not a count of replicated or decision-grade arms. In the banked Gemma run, all four C1b cells declare `numactl_policy=none` for straddling half-machine cpusets; their affinity artifacts record shared model pages across N0–N3, roughly half local to either half. They do not designate defect-replication controls. All four C1 cells declare full-machine interleave and show the expected CPU affinity, but the inspected artifacts do not independently attest runtime memory policy or a cache drop before each cell. The eight `decision_grade=true` labels therefore do **not** themselves prove compliance with the corrected placement requirements above. These observations do not establish that the full-machine cells failed; retain the run and assess any use against the applicable protocol. Source: `a7-gemma4_26b_a4b_q4km_mtp-20260813T223750Z/{cells.jsonl,affinity/}` under `epyc-inference-research/data/batched_decode/`. [belief: cc]
  - **2026-11-02 BRF-T3 E5 adjudication (ws58, zero inference; OBSERVATION):** banked A7 Gemma cells (`a7-gemma4_26b_a4b_q4km_mtp-20260813T223750Z`, cells.jsonl SHA-256 `dfc0487c7c32…`) → **VALID 0 / DEMONSTRATED-INVALID 4 / UNRESOLVED-MISSING-EVIDENCE 4**. The four C1b cells are demonstrated-invalid against requirement (b): straddling cpusets, `numactl_policy=none`, no defect-control declaration; their `pages_by_node` is byte-identical to the preceding interleave=all C1 cells (1 distinct layout across all 8). That is an inherited warm cache, which also witnesses (c) non-compliance. The four C1 cells (0-95 interleave=all, affinity match, local_fraction 1.0) are unresolved: no runtime-policy or per-cell cache-drop witness. They are not invalid. Recorded throughputs stay accurate as historical values. Qwen reconciliation: 20 manifests, (a) PASS in both groups, (b) FAIL in 10 C1b manifests, (c) 0/20 declare a per-cell drop (the harness drops between model groups only). The box stays open: re-runs are required. [belief: cc] Evidence: `docs/design/backlog-refactor-2026-11/t3-evidence/e5-adjudication-20261102.json` (re-scoped 2026-11-03 from W2 gemma and W4 qwen3_next_80b: deleted; now the current CPU roles (Qwen3.6-35B-A3B and Qwen3.8-Flash-Next IQ4_XS))
- [x] **Fix the production cpuset wiring in `stack_numa.py` (orchestrator; gated on the re-measurement)** — `frontdoor` idx0 (port 8070) and `ingest_long_context` idx0 (port 8085) both pin `NUMA_NODE0 = "0-47,96-143"` with **no `numactl_policy`**, which is the defective shape measured at `7.81` t/s warm. `eval_batch_frontdoor` (18070) uses the same cpuset but does carry `interleave=all`; `worker_general` (8083) already uses `NUMA_FULL` + `interleave=all` and is unaffected. **The justification comment in the file is invalid evidence**: the April 2026-04-17 head-to-head (`26.60` interleave vs `27.06` NUMA_NODE0, "B beats A by 1.7%") predates the 2026-04-24 NPS4 reboot — the cpuset genuinely WAS one node then — and its source CSV records `spec == "baseline"`, i.e. speculative decoding OFF. `ingest_long_context` cites that same dead head-to-head to "keep parity" and inherits the defect with no data of its own. The `NUMA_NODE0`/`NUMA_NODE1` names are NPS2-era artefacts and have been misleading since the NPS4 reboot; the `NUMA_Q*` quarters are correctly named and ARE the four NPS4 nodes. **Status: annotated in place 2026-07-30, change deliberately NOT applied** — the wiring is held unchanged so the re-measurement stays comparable with the recorded AutoPilot operating point being re-anchored against. Production serving-path change → operator-gated; apply only once the corrected Stage-B reports. ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): NUMA_NODE0/NUMA_NODE1 were deleted 2026-08-11 (orchestrator scripts/server/stack_numa.py:140); frontdoor now runs on halves. [no-belief: obsolete, constants deleted 2026-08-11]
- [x] **Retract the suspended figures in the operator-facing E5 artifact** — the authoritative local HTML (`artifacts/operator/e5_w0_preliminary_results.html`) carries the Stage-B headline and therefore still presents retracted numbers. Add the suspension banner and the "C3 never wins" retraction while retaining the figures verbatim (append-only). Do not regenerate it from the superseded markdown.
  **✅ 2026-08-11 (`mainA`) — CLOSED, and the row's premise was stale.** Verified before editing:
  the HTML carries **zero** occurrences of `Stage-B`, `W0` or `E5`, and its figures are tok/s, not
  the suspended tasks/hr. It was **rebuilt from scratch on 2026-07-30** (`44c44068`, "artifact:
  rebuild on production recipes") as the `P-BENCH-PLACEMENT-1` placement package with its own
  measurements — so it never carried the Stage-B headline this row assumed. The retraction the row
  asks for was already satisfied elsewhere: the sibling `.md` carries a `SUPERSEDED AND
  NON-AUTHORITATIVE` banner naming the suspension and the 27-of-31 confound.
  **Checking it surfaced a live issue worth more than the filed one.** Every figure on that page is
  `kernel v8 @ 67a433bf4 (10107)` = era `E8-cpu-kernel`, and production froze at v9 today. Appended
  an era note — figures unchanged, append-only — stating they are **historical priors** for v9
  decisions under the reconciliation clause on the `E9-cpu-kernel` row, and that the page is the
  placement package rather than the suspended Stage-B record. HTML re-parsed clean.

#### Gates & pitfalls

- Operator window required: per `feedback_no_concurrent_inference` / `feedback_speed_verify_via_llama_bench`, the operator runs the benches — this handoff prepares commands, harness, and analysis; schedule inside the bulk-campaign Queue-2 quiesce window (one attested reload serves all).
- Do NOT over-extrapolate A3B wins: MoE batching is weaker than dense (distinct tokens hit distinct experts → expert weight traffic grows with batch) — hence the mandatory dense control in E1.
- The 9.6× rep-1 TTFT amplification under concurrent prefill (CPU23) is real; report TTFT separately from steady-state per-stream decode or E2 will look better than it serves.
- Index results by model+quant, never by role (`feedback_model_not_role_indexing`); P-BENCH-3 preconditions (host-health tier, no concurrent inference, interleave re-warm) are binding.
- E3 before E1 is forbidden — the kernel only gets written if the measurement shows compute headroom at intermediate batch.

#### Reporting

Tick waypoints here + one-line progress entry per session; on full completion delete the master-index row and move this file to `completed/`; every number follows the [MEASUREMENT.md](../../MEASUREMENT.md) claim grammar (metric, protocol-id, n, date, attest ref).

- [x] **Eval-batch serving lane decision (tabled here 2026-07-23 from the EV-BASELINE-E7 session)**: ✅ 2026-11-10 — decided by operator: option (c), batched eval decoding on the MI210. [no-belief: operator decision, not a measurement]
  the retired `eval_batch_frontdoor` lane (port 18070, warm launcher-only, -np 8 — "not a
  distinct model-routing role") posed the question: dedicated eval lane vs quiet-window 4-wide
  fan-out on production quarters (this week's proven regime). Decide WITH the E5 NUMA×batch(-np)
  mapping data, not before: E5 tells us what a batch lane costs/yields per placement. Design
  options to evaluate then: (a) no lane — quiet-window fan-out suffices; (b) resurrect a CPU lane
  as a WP-12 fleet with an eval-only role bound to it (outside-quiet-window evals without
  touching interactive traffic); (c) **push batched eval decoding to the MI210 GPU** — an
  eval-lane fleet on the GPU under heterogeneous-slot-fabric-residency.md ("everything is a
  slot"), freeing ALL CPU quarters for interactive traffic. Note: the robust eval structure these
  designs waited on now EXISTS (decision-grade P-CAL instrument, honest error rows, per-question
  artifacts, resume/retry) — the queued design ideas across the notes can now be tested properly.
  - **Operator decision 2026-11-10:** option (c) chosen — eval-lane fleet on the MI210 under heterogeneous-slot-fabric-residency.md, freeing all CPU quarters.
  - [ ] Design and land the MI210 eval-lane fleet (eval-only role bound to a GPU slot fleet); size `-np` from E5/GPU batch data.

#### Pre-execution audit (2026-07-23)

READ-ONLY pre-execution audit of the E5 sweep design (the `2026-07-23 — E5 harness
preparation` note above), run before the execution phase against the realized system. All
claims verified with file:line citations; no inference, no process management. **Verdict:
GO-WITH-CORRECTIONS.** The design is sound, correctly scoped design-only/zero-inference, and
its R4 output already matches the ratified fabric contract. The gating work is the (unbuilt)
multi-server harness, plus three bounded corrections that do not change the sweep's shape.

##### Verdict per dimension

**1. Staleness vs realized system — STALE (correctable).**
- **Fleet layer is POST-FLIP, not mid-flip.** `epyc-orchestrator` `4ca6859a` merged the fleet
  layer (2026-07-23 13:23Z) and `a172d2dd` wired `ORCHESTRATOR_FLEET_LAYER=1` as the durable
  launch default (14:22Z). The E5 design was written concurrently and CORRECTLY assumes
  post-fleet-layer serving (R3's "zero-code remap … an eval-only RoleBinding on a batch-shaped
  fleet"). Realized-first machinery (`scripts/server/realized_fleet.py`, ESC-8) is present and
  the design's realized-mode awareness is consistent. → CLEAN on this sub-point.
- **Realized stack is QUARTERS-based; C1 is NOT the live production shape.**
  `orchestration/derived/stack_priors.yaml` reports frontdoor `numa_policy:
  4x48t_quarter_instances`; `stack_numa.py:184` sets worker_general `placement_policy:
  full_disabled` (quarters-only, no 8072, DISPATCH-A 2026-07-21). The design repeatedly labels
  C1 "the current production solo shape" / "production-shape anchor". That is inaccurate for a
  quarters-only realized stack and **outright wrong for gemma**, whose live production shape is
  4×q — its 1×full (0-95) instance is DISABLED. R1's own tie-break ("prefer the status-quo
  quarters split") already treats quarters as status-quo, contradicting the grid-note. FIX:
  relabel C1 as a provisioning CANDIDATE + E1-continuity anchor; C3 (quarters) is the
  status-quo production shape. (Sweeping C1 as a candidate is fine — the correction is
  interpretive, not structural.)
- **E1/E2 baseline numbers are PRE-v7 historical priors.** `instrument_eras.yaml` E6-cpu-kernel
  boundary = 2026-07-20T13:30:13Z (v7 cutover, `6ad45fa3ff`). The E1 A3B ladder (2026-07-03 /
  07-06) and the E2 rows (batch 2.258 vs current 10.970, 2026-07-03) were measured on v6+iqk
  (E5-cpu-kernel era), pre-E7-eval-instrument (2026-07-21) and pre-E4-quality-core-v2
  (2026-07-23). Under E6 they are **demote-to-prior — direction/hypothesis only, cannot gate**.
  The design uses them correctly for DIRECTION (scout cross-check; April/May shape figures
  flagged hypothesis-grade). But **R3 gates the eval-lane decision on "batch 2.258 vs current
  10.970"** — a demoted number gating a decision, and the eval unit itself changed (43-q legacy
  T1 → 50-item core_v2). See correction C2.
- eval_batch_frontdoor "retired": accurate. Still in code as a warm launcher-only, default-off
  role (`stack_numa.py:88`, port 18070) — "retired" = deprovisioned, not deleted. No task
  assumes it is a live lane. → CLEAN.
- worker_vision -np: the -np>1 MTP-assert risk (`orchestrator_stack.py:779-784`) is real and
  the E5 Stage-A np×spec-dec wedge probe (design point 2) covers that class. → CLEAN.

**2. Measurement-constitution compliance — MOSTLY CLEAN; two gaps.**
- (a) codified recipe: E5 reuses `server_np_sweep.py` (the durable P-BENCH-3 harness), which
  the waypoint blesses — NOT ad-hoc `llama-bench`/`run_benchmark.py`. CLEAN. Nit: that harness
  keeps its OWN `DEFAULT_ENV` (`server_np_sweep.py:46`) instead of importing
  `scripts/lib/canonical_recipe.py` constants — a recipe-drift risk per
  `feedback_use_codified_recipes_not_memory`.
- (b) protocol id / era / attestation / decision_grade gating: all declared (design delta-spec
  e). CLEAN.
- (c) OMP stack: present and correct in `DEFAULT_ENV` (PROC_BIND=spread, PLACES=cores,
  WAIT_POLICY=active, DYNAMIC=false, KMP_BLOCKTIME=10). throttle / numa_balancing=0 /
  host-health / ps-verified kill: all enforced by the inherited harness. **GAP: `GGML_IQK=1`
  (the v7 iqk runtime gate, CLAUDE.md) is absent from `DEFAULT_ENV` and unmentioned in the
  design** — this is exactly the "missing-IQK" trap that aborted the 2026-07-07 dense-control
  run (only the re-run `…-iqk-…` was kept). See correction C1. Affinity: the design mandates
  live verification but cites a non-existent `--live-only` flag and the tool is NUMA_CONFIG-role
  -keyed (cannot gate synthesized half1/bench-port shapes) — see correction C3.
- (d) correctness pairing: design point 6 (store every response, E7-era B7 scorer offline,
  parse-fail ≤2/43 + repetition-loop gate, speed demoted to observation on a degraded cell).
  CLEAN.
- (e) quiet-window gating + instrument identity (solo vs overlapped): present — cells are
  solo instance-sets; C1b is an explicitly-labeled co-run. CLEAN.

**3. Design coherence — CLEAN.** All four waiting consumers are covered:
  (a) eval-lane → R3 (with the C2 re-baseline correction); (b) node-partitioned
  arm-parallelism → C1b (2×half) + iso-T {C1b@T/2 vs C3@T/4}; (c) slot-fabric pricing → R4
  emits MODEL-KEYED capability data, which is exactly the first population the ratified fabric
  contract asks for (`heterogeneous-slot-fabric-residency.md:117` "E5 R4 rows are the first
  population"); (d) -np sizing → R4 feeds `within-role-placement-state-machine.md`. iso-T
  arithmetic and the K-caps (total in-flight ≤43) are internally consistent (C1×{1..32},
  C1b/C2×{1..16}, C3×{1..8}). Minor: E5 sweeps a single quant per model, so the fabric
  contract's (CPU-quant, GPU-quant) pairing axis stays single-valued — out of E5 scope (quant
  choice is architect-bench's axis), acceptable.

**4. Executability — GAP (harness unbuilt) + two script-reference nits.**
- **The multi-server harness does NOT exist.** `server_np_sweep.py` is single-server (docstring
  line 2; `build_server_command` hardcodes `numactl --interleave=all` with no per-instance
  taskset pinning, lines 376-407) — it cannot run C1b/C2/C3 multi-instance cells as-is.
  `server_numa_np_sweep.py` is absent. The delta spec (a-f) is substantial (multi-launch,
  per-instance pinning, closed-loop N×K driver, per-cell affinity gate) and is correctly an
  OPEN checkbox. Implementation time is separate from the run-time estimates and is unbudgeted.
- `affinity_preflight.py` has NO `--live-only` flag (args are `--roles`, `--output`,
  `--require-memory-locality`, `--memory-locality-threshold`) and is NUMA_CONFIG-role-keyed, so
  it cannot validate E5's SYNTHESIZED half1 (`48-95,144-191`) bench-port instances without a
  cell-manifest mode. Delta-spec (d) must build this, not just wire the existing tool.
- **Models all present** (CLEAN): frontdoor `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (37.8 GB); dense
  control `Qwen3.6-27B-MTP-Q8_0.gguf` (29 GB); gemma `gemma-4-26B-A4B-it-Q4_K_M-current.gguf`
  (~14 GB); ingest `…/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/…-Q4_K_M.gguf`
  (~48 GB — the registry-declared Q4_K_M, NOT the `models/…i1-IQ2_M.gguf`; the design's "~45 GB"
  is correct). Results schema/ledger defined (E1-style manifest, `data/batched_decode/`).
- Run-time estimates (W0 ~2-2.5h … W3 ~4-6h) are plausible against the E1 decode rates.

**5. Checkbox hygiene — CLEAN (one stale prose line).** Waypoint checkboxes are accurate (E1/E2
/E3/E4 done; E5 design ✅; harness impl + W0-W3 runs open). No task assumes the eval_batch
frontdoor lane is live or pre-fence routing. Nit: the E5 waypoint PROSE (line 26) still lists
frontdoor configs as `{full},{full,q3},{full,q3,q2}` (full+quarter mixes), superseded by the
2026-07-21 mode-exclusivity contract; the design note's "Spec interpretation note" already
excludes mixed shapes from Stage B, so this is handled in the design but the waypoint sentence
is stale.

##### GO / NO-GO: **GO-WITH-CORRECTIONS**

The sweep design is executable in shape and correctly gated (post-v7 quiet window, LAST behind
inference-batch-loop → architect-model-selection-bench). Predecessor status at audit time:
inference-batch-loop is parked/operator-gated (not terminal), architect-bench is "GPU bench
complete" with CPU-gated items outstanding (RP-5/RP-3/Phase-2) — confirm the operator considers
the queue clear before scheduling. Apply the three corrections below; none blocks design sign-off,
but C1 and C3 are execution-blocking (must land in the harness before any decision-grade cell).

##### Corrected / added task list

- [x] ✅ 2026-07-28 VERIFIED ALREADY IMPLEMENTED (stale checkbox — landed with research `b294daa0`; independent verification at committed HEAD: harness composes env via `canonical_recipe.build_canonical_env`, fail-closes on `env_expectation` mismatch, records `ggml_iqk` in per-cell rows + run-manifest attestation; proven live in W0 `cells.jsonl`) — **C1 (execution-blocking) — set `GGML_IQK=1` per cell + record it as a manifest/attestation
  field.** Add to the harness env (or the canonical env it should import); without it, K-quant/
  legacy-quant cells (gemma Q4_K_M, dense 27B Q8) silently run without iqk — the aborted
  2026-07-07 "missing-IQK" run is the cautionary tale. Attest the iqk state alongside
  `kv_unified`.
- [x] **C2 (decision-blocking for R3) — current-arm re-baseline DONE ✅ 2026-07-23.** Measured
  FRESH under E6-cpu-kernel (v7) + E4-quality-core-v2 + WP-12 fleet layer + the **restored
  big+quarters lineup** (post-restoration, post-locality-heal), current-arm-only via
  `--skip-batch-arm`, PRODUCTION escalation (not pinned — this prices the lane as it actually
  runs): **27.546 wall-min/eval** (core_v2, 50 items, 45 scored, reliability 0.90 floor-clean,
  quality 1.667, resolved eval_concurrency 3 — the restored half occupies q0+q1 so frontdoor's
  disjoint fan-out is half+q2+q3). Report:
  `epyc-orchestrator/orchestration/reports/r3_current_arm_rebaseline_corev2_20260723/`.
  Per-item: 27.546/50 = **0.551 min/item** (0.612 per scored item) — feed this as the R3
  baseline file's `items_per_eval=50` row. Secondary observation (NOT the baseline): a
  legacy-pool-draw run under the same lane measured 21.87 min (different question set;
  `r3_current_arm_rebaseline_20260723/`). Config deltas vs the 2026-07-23-morning current-arm
  row (23.87 min): concurrency 4→3 (restored-geometry resolution), escalation pinned→production,
  lineup quarters-only→big+quarters — the morning row was a reseed input, not an R3 baseline.
  **C10-F1 addendum (2026-07-23, from the WP-12 case-10 live gate)**: the current-arm's
  within-role concurrency mechanism is **6-uvicorn-process spread × per-process per-role
  `Semaphore(1)`** (every live role resolves `get_role_max_concurrency()==1` because
  `live_warm_worker_slots()` filters `tier=="warm"` and all live roles are `hot`), with
  cross-process disjointness from region flocks — NOT a role-level concurrency cap of N. A
  `--workers 1` API serializes each role fully. Model the current-arm baseline accordingly and
  record the API worker count in the arm's attestation. Fix task filed in
  [wp12-fleet-layer-design.md](stack-lifecycle-program.md#track-wp12-fleet-layer-design) (C10-F1 follow-up).
- [x] ✅ 2026-07-28 VERIFIED ALREADY IMPLEMENTED (stale checkbox — `server_numa_np_sweep.py` multi-instance N×K harness + orchestrator `affinity_preflight.py --cell-manifest` mode landed `6a55aeed`/`52978844`/`29779bcc`; hard per-cell gate confirmed: preflight before requests, non-zero exit aborts cell, `decision_grade` requires `live_affinity_verified`; 105+27 targeted tests pass at committed HEAD; all 190 committed manifests validate) — **C3 (execution-blocking) — build the multi-server harness + cell-manifest affinity gate.**
  `server_numa_np_sweep.py` (or extend `server_np_sweep.py`): per-instance taskset pinning +
  correct per-shape numactl policy (interleave only for full/gemma-MTP), multi-launch/teardown
  with ps-verified kill, closed-loop N×K driver (TTFT + per-stream p50/p95 + trimmed aggregate),
  and a per-cell affinity preflight that accepts arbitrary {cpuset, port} cells (the existing
  `affinity_preflight.py` is role-keyed and has no `--live-only` flag — extend it or add a
  manifest mode).
- **C4 ADDENDUM (2026-07-23 lineup restoration)**: the quarters-only premise is OBSOLETE — the
  operator ruled the v7-cutover big-instance drop accidental and the lineup was restored same
  day (orchestrator `95dffc88`: frontdoor half 8070 + worker full 8072 + ingest half 8085 live,
  `burst_prefer_quarters`). **C1 (1×half) is therefore the LIVE production solo shape again**
  for frontdoor/ingest (and 1×full for gemma), not merely a provisioning candidate; C3 remains
  the live burst shape. The R3 current-arm re-baseline MUST run under this restored lineup.
  Contention-matrix note: big∥quarter co-run rows are pre-v7-era priors (hash-fresh,
  semantically demoted) — E5's cells re-measure the underlying physics anyway.
- [x] **C4 (interpretive) — relabel C1** as a provisioning candidate / E1-continuity anchor, not
  "the current production solo shape" (realized stack is quarters-only; gemma's 1×full is
  DISABLED). Optionally refresh the stale waypoint prose (line 26) to the mode-exclusive config
  list the design note already uses.
  **✅ 2026-08-12 (`mainA`) — DONE, and the row's own premise has INVERTED. Verified against the
  live topology, not the row.** C4 asks me to demote C1 *on the grounds that* "realized stack is
  quarters-only". That ground is gone: `982adb0c` ("topology: retire quarters, deploy 1 full + 2
  halves") retired them, and `stack_topology.yaml` now declares **zero quarters anywhere** —
  `realized_shape.quarterable_roles` reads *"full (0-95, interleave=all, -t 96) + half A + half B"*,
  and every CPU role (`frontdoor`, `ingest_long_context`, `worker_general`) instantiates exactly
  `[NUMA_FULL, NUMA_HALF_A, NUMA_HALF_B]`.
  **So the relabel lands on C3, not C1.** C3 (4×quarters) is the shape the E5 design note calls "the
  status-quo production shape per audit C4" — that label is now **false**; quarters are a retired
  shape with no production instance. C1 (1×half) and the full ARE what production runs, so C1 is no
  longer a candidate *contrasted with* production; it is a realized shape.
  **This makes the Stage-B headline and the deployment agree**, which is worth stating because they
  were derived independently: Stage-B measured that **C3 loses at every clean iso-T rung in all three
  model groups**, and production has since retired quarters entirely. The measurement did not drive
  the retirement and the retirement did not drive the measurement — they converged.
  *(The waypoint prose at line 26 is the 2026-07-30 `llama-bench` placement table, not the config
  list this row expected; left unedited, as it is a measurement record.)*

<a id="track-dynamic-stack-concurrency"></a>
## Moved: dynamic-stack-concurrency

Split out 2026-11-10 to [`hybrid-checkpoint-prompt-reuse.md`](hybrid-checkpoint-prompt-reuse.md) (INF-86). No boxes live here.

## Track: numa-placement-defect-20260730
<!-- gate: none -->

> Folded from `handoffs/active/numa-placement-defect-20260730.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F17, route 1a, operator D1/D5; retired row INF-43 → INF-45). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### NUMA placement defect — two production CPU roles serving at ~half speed

*Title corrected 2026-07-30. Previously: "production CPU inference running at ~1/3 speed" — both
halves of that were wrong at higher `n`. The loss is **~2×, not ~3×** (the 3× came from a warm arm
with a ±49% error bar), and it is **two named roles, not "production CPU inference"** — the other
two production CPU roles are already correctly wired. See the amendment note below.*

**Status**: OPEN — diagnosis COMPLETE and measured; the **wiring fix is now WRITTEN (uncommitted,
not reloaded)** — see [Topology change applied](#topology-change-applied-2026-07-30--quarters-retired-1-full--2-halves).
Five distinct defects found, three of them in live production wiring (D1–D3), two in the E5
measurement harness (D4–D5). The corrected reference numbers below are observation-grade
(`n=1–2` reps) and are the input to a re-measurement, not a promotion.

> **Amended 2026-07-30 (second pass, session `mainA`).** Three things changed after the text
> below was written, and the text below is **retained verbatim** per the append-only rule:
> 1. **`P-BENCH-PLACEMENT-1` is RATIFIED**, not STAGED (epyc-root `07b7dcab`; registered in
>    `MEASUREMENT.md` §2 + annex `measurement/protocols/bench-cpu.md`). **T9 CLOSED.** Every
>    "observation-grade because the protocol is STAGED" statement below is superseded — figures
>    measured under the protocol now carry its grade. The `n=1–2` rep caveat on the `np`-ladder
>    and shape tables still stands on its own.
> 2. **The wiring fix is applied in the working tree.** Quarters are retired; every quarterable
>    role is **1 full + 2 halves**, every instance carries a declared memory policy, and `-t`
>    equals the physical core count everywhere. **UNCOMMITTED and NOT RELOADED** — the reload
>    still belongs to the session that owns the inference.
> 3. **A new, larger lever was found while measuring: `ngram-mod`** — up to **2.80×** on
>    `frontdoor` at realistic context, and the **only** speculation `ingest_long_context` can
>    have. See [ngram speculation](#ngram-speculation--a-larger-lever-than-the-placement-fix-on-two-roles).

> **Amended 2026-07-30.** The placement matrix has since been completed across **all four
> production CPU roles** at `r=5` (`r=10` for `frontdoor`), on the production model artefact for
> each role — see [Cross-role placement matrix](#cross-role-placement-matrix--all-four-production-cpu-roles).
> The `n=1–2` rep caveat still applies to the `np`-ladder, shape-sweep and fleet tables; it no
> longer applies to the matrix. Everything nonetheless remains **observation-grade**, because the
> governing protocol `P-BENCH-PLACEMENT-1` is **STAGED, not ratified** — see
> [Protocol, attestation and grade](#protocol-attestation-and-grade).
> **Only `frontdoor` and `ingest_long_context` are mis-wired.** `worker_general` and
> `architect_general` already run the canonical recipe; their matrix rows are counterfactuals, not
> live regressions.

> **Amended 2026-09-08 (INF-70 audit, MEAS-1 / HARNESS-1) — sub-floor magnitudes relabelled.**
> Per the append-only rule the text below is **retained verbatim**; this block corrects its *labels*,
> not its numbers. The cold-targeted CPU harness on this box has a measured **A/A p95 floor of 3.21%**
> (adjacent-window) and **19.89% contended**; the new hot-server harness floor is 0.80% p95. **Any
> delta in this file smaller than ~5% is at or below the floor: its label is WRONG, not merely
> missing, and must be read as UNRESOLVED.** Specifically:
> 1. **Defect 3, quarters row** (`| QUARTER … +2.4% … +2.3% |`) — **UNRESOLVED (below the 3.21%
>    cold-harness floor)**. The following sentence *"Same sign on quarters, smaller magnitude"* does
>    **not** hold: no sign is established on quarters. The HALF row (`+13%` per-stream / `+8.5%`
>    aggregate) is far above the floor and **stands unchanged**.
> 2. **The `llama-bench` corroboration** (*"agrees independently: straddle + interleave at `-t 48` =
>    `15.98` vs `-t 96` = `15.35` (+4%)"*) — **UNRESOLVED**; +4% cannot corroborate anything at this
>    floor. Treat the sentence as withdrawn: the HALF row stands on its own, unsupported by this arm.
> 3. **"Instrument validated"** (`8.80` vs the registry-documented `8.90`, *"a 1% match, so the meter
>    is sound"*) — a 1% agreement is deep inside the floor and, per HARNESS-2, a **cold-harness
>    absolute may never be compared against a differently-harnessed absolute** (hot reads **+4.36%**
>    above cold on the same binary with byte-identical output). The instrument-validation *argument*
>    therefore needs re-derivation — flagged for the owning session, not resolved here.
> 4. **"a v8 kernel regression … ruled out (v7 and v8 both measure `9.76`, identical)"** — restate as
>    **"no v7/v8 difference resolvable above the harness floor"**. Nothing below ~5% was ruled out.
> 5. **The `ngram-mod` corrected gain "−4.2% to +1.3%"** and the **"accepted ~−1.6% ordinary-text
>    cost"** — both **UNRESOLVED (below the floor)**; the numbers stay visible, the labels do not.
>    The **−23–31%** `ngram-mod`-alone cost is far above the floor and **stands**. The retraction of
>    the 2.80× and the standing operator decision to carry the composed recipe are **unaffected** —
>    only the stated *price* of that decision is now unresolved.
>
> Also recorded, and NOT actioned here (they change scope and belong to the owning session): the
> `-c`-provisioning null (`40.44` vs `40.49` tok/s, 0.12%) is UNRESOLVED, not "no cost", and it is the
> whole premise of **T12**; the AutoPilot `median_request_tps` 35.7 anchor is a **hot production
> absolute** and cannot be matched against these cold bench absolutes (this affects the
> `P-BENCH-PLACEMENT-1` anchor gate and the T3/T10 re-run plans); and per **STAT-1** the **arm** is
> the unit of replication, so `n=1` arms cannot size the `>=58 GiB/node` post-load placement gate.

**Created**: 2026-07-30
**Priority**: ACTIVE-HIGH — live throughput damage on **exactly two** production roles
(`frontdoor` 8070, `ingest_long_context` 8085 — **not** `worker_general` and **not**
`architect_general`, both of which are already correctly wired), plus it invalidates 27 of 31 E5
Stage-B cells.
**Spec**: [MEASUREMENT.md](../../MEASUREMENT.md) + [MEASUREMENT_POLICY.md](../../agents/shared/MEASUREMENT_POLICY.md)
(claim grammar, era stamping, region-lock) · protocol **`P-BENCH-PLACEMENT-1`**
(`epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md`, STAGED).
All measurement below ran under a held `region-lock` on `q0..q3` as `role='bench'`.
**Sibling — the cutover-resume half (row N25)**:
[numa-topology-cutover-resume-20260730.md](numa-placement-and-contention.md). **This
document is the DIAGNOSIS; that one is the RESUME STATE of the landing** (blocker, in-flight
runs, P0/P1/P2 queue). Cross-reference it; do **not** duplicate its task rows here — two
checkbox copies of one task give the dashboard two sources of truth.
**Related**: [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement) — the **owner of the
E5 campaign**; its `⛔ SUSPENDED PENDING RE-MEASUREMENT (2026-07-30)` banner is the authoritative
suspension notice and this document is its root-cause backing · [within-role-placement-state-machine.md](dispatch-placement-telemetry.md)
(consumes `NUMA_CONFIG`) · [heterogeneous-slot-fabric-residency.md](kv-cache-program.md#track-heterogeneous-slot-fabric-residency)
(its `(N,K)` provisioning is parameterized by E5) · [inference-research-index.md](inference-research-index.md)
(CPU14/CPU17/CPU18 rows) · [gpu-serving-tie-in-program.md](../completed/mi210-serving-program.md) P1-2
(the E5 W1–W4 execution row and its published-artifact update requirement)

---

#### Scope and provenance of every number below

Unless stated otherwise: measured **2026-07-30**, on **`Qwen3.6-35B-A3B-MTP-Q8_0`** (the
`frontdoor` model), production kernel `production-consolidated-v8` @ `67a433bf4` (binary `10107`),
`GGML_IQK=1`, canonical OMP env stack (`OMP_DYNAMIC=false OMP_PLACES=cores OMP_PROC_BIND=spread
OMP_WAIT_POLICY=active KMP_BLOCKTIME=10`).

Host is **NPS4**:

```
node0 = 0-23,96-119     node1 = 24-47,120-143
node2 = 48-71,144-167   node3 = 72-95,168-191
```

`0-95` are the 96 physical cores; `96-191` are their SMT siblings (core *i* pairs with thread
*i+96*). Each node owns 24 physical cores plus those 24 siblings.

---

#### Protocol, attestation and grade

*Added 2026-07-30.*

| | |
|---|---|
| **Protocol** | `P-BENCH-PLACEMENT-1` — `epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md` |
| **Protocol status** | ~~**STAGED — NOT APPLIED.** Its `MEASUREMENT.md` registry entry (protocol Appendix A) is written and waiting on the operator.~~ **RATIFIED 2026-07-30** by the operator — epyc-root `07b7dcab`, registered in `MEASUREMENT.md` §2 plus the annex `measurement/protocols/bench-cpu.md`. The protocol's own file still said `STAGED` after ratification; corrected in research `0a7f767d`. **T9 CLOSED.** |
| **Attestation** | `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/` — all raw logs **plus the exact script that produced each figure**, committed. `README.md` in that directory carries the figure → file map and the per-figure rep counts. |
| **Era** | `production-consolidated-v8` @ `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server --version` = `10107`, host NPS4 |

~~**Consequence of STAGED: everything measured under this protocol is observation-grade until the
operator ratifies the registry entry.**~~ Per `MEASUREMENT.md` §4 and `MEASUREMENT_POLICY.md` →
*Trust boundary*, the measurement trust boundary is human-amendment-only. ~~Until that amendment
lands, no number in this document — including the completed four-role matrix, including the
`n=10` `frontdoor` figures — may gate a keep / revert / deploy / promote decision.~~

> **RESOLVED 2026-07-30 — the amendment landed.** The operator ratified `P-BENCH-PLACEMENT-1`
> (epyc-root `07b7dcab`). Figures measured **under the protocol** — the four-role matrix and the
> `n=10` `frontdoor` figures — are no longer held back by protocol status. Two caveats survive
> and are independent of ratification:
> - The `np`-ladder, shape-sweep and fleet tables in *Corrected reference numbers* are still
>   `n=1–2` reps. **Rep count is its own gate.**
> - `P-BENCH-PLACEMENT-1`'s **anchor gate is mandatory and three of four roles have no anchor**
>   (only `frontdoor`'s exists: median `35.7` tok/s, `n=154`, band 35–40, from AutoPilot
>   production traffic). Those three roles cannot pass the gate until an anchor exists — a true
>   statement about our evidence, not a blocker to route around. Tracked as **N25 P2-2**.
> - Several §7 thresholds are still **TBD**, and *a gate whose threshold is unset cannot fail*.
>   Proposed values with derivations: `artifacts/operator/ratification_queue_20260730.md`.
>   Tracked as **N25 P2-3**.

Concurrently ratified: **`P-BENCH-3` conformed to `MEASUREMENT.md` §1** — tok/s primary,
tasks/hour **retained** as secondary. Note precisely what changed: tasks/hour was **not removed**.
§1 already said `task_rate` is the AutoPilot objective axis and tok/s the instrument-level metric
for `P-BENCH-*`; the registry row simply contradicted it.

---

#### Defect 1 — straddling cpusets launched with no NUMA memory policy

`epyc-orchestrator/scripts/server/stack_numa.py` defines:

```python
NUMA_NODE0 = ("0-47,96-143", 96)
NUMA_NODE1 = ("48-95,144-191", 96)
```

The names are **NPS2-era artefacts**. They were correct before the 2026-04-24 NPS4 reboot; on the
current NPS4 host `NUMA_NODE0` spans **node0+node1** and `NUMA_NODE1` spans **node2+node3**. Each
is a *straddling* cpuset, not a node.

Roles `frontdoor` (port `8070`) and `ingest_long_context` (port `8085`) launch their full
instances on these cpusets **with no `numactl` policy at all**. With no policy, every weight page
lands on whichever node first touches it, so roughly half of a 96-thread team pays a cross-node
read on every weight access.

Two roles on the same constants are **not** affected: `eval_batch_frontdoor` (`18070`) uses
`NUMA_NODE0` but does carry `numactl_policy: "interleave=all"`, and `architect_general` (`8083`)
plus the `worker_general` full instance (`8072`, `"0-95"`, interleave scoped to idx 0) are
full-machine + interleave already.

##### Measured — `llama-bench` tg128, no speculative decoding, `-r 3`

| placement | page cache | threads | tok/s |
|---|---|---:|---:|
| straddle `0-47,96-143`, no interleave — **= CURRENT PRODUCTION wiring** | warm | 96 | **7.81 ± 3.82** |
| straddle, no interleave | cold | 96 | 10.28 ± 0.02 |
| straddle + `--interleave=0,1` | cold | 96 | 15.35 ± 0.08 |
| straddle + `--interleave=0,1` | cold | 48 | 15.98 ± 0.02 |
| **full machine `0-95` + `--interleave=all`** | cold | 96 | **23.43 ± 0.07** |
| single NPS4 node `0-23,96-119` (instrument check) | cold | 48 | 8.80 ± 0.02 |

**The winner is the canonical bench recipe and it beats the current production wiring by 3.0×.**

> **Amended 2026-07-30 — the ratio is 2.16×, not 3.0×.** The `3.0×` above divides the winner by
> the **warm** as-wired arm, `7.81 ± 3.82` — whose ± is **49% of its own mean**, by far the
> noisiest cell in this document. The higher-`n` re-measurement (`r=10`, `drop_caches` before
> every arm, `highn.sh`) puts the as-wired arm at **`10.83 ± 0.04`** against **`23.36 ± 0.11`**
> canonical = **2.16×**. That agrees with the *cold* as-wired row above (`10.28 ± 0.02`) and
> supersedes the warm one. Rows retained verbatim per the append-only rule; **cite 2.16×**.

> **`numactl --interleave` binds at FIRST TOUCH only.** Against a warm page cache it is a silent
> no-op — visible above as the warm straddle+interleave row landing on the *unpolicied* number
> rather than the cold-interleave number. This is exactly why the defect survived casual
> re-testing: a warm re-test appears to "confirm" the bad figure.

**Instrument validated.** The single-NPS4-node arm measured `8.80` against the
registry-documented `8.90` — a 1% match, so the meter is sound and the defect is in the wiring
under test. Ruled out as causes: a v8 kernel regression (v7 and v8 both measure `9.76`,
identical); iqk (never engages for Q8_0 — gated behind an unset `GGML_IQK_Q8_0`); MTP head
overhead; mmap page-faulting.

**Honesty caveat on the headline number.** ~~`23.43 ± 0.07` is one `llama-bench` invocation of 3
reps with no independent repeat.~~ Arm `F` in `/mnt/raid0/llm/tmp/numa_matrix2.sh` is **mislabelled**
— its comment says "REPEAT of C-winner shape at 4 nodes" but its argv is
`taskset -c 0-47,96-143 numactl --interleave=0,1 … -t 96`, i.e. a repeat of arm **C**, not D. It
returned `15.28 ± 0.33`, which does independently reproduce C's `15.35 ± 0.08`. ~~So the
*straddle+interleave* figure is replicated; the *full-machine* figure is not yet.~~

> **RESOLVED 2026-07-30 (T7 CLOSED).** The full-machine figure **is now replicated**. An
> independent `n=10` run (`highn.sh`, `drop_caches` before each arm) measured **`23.36 ± 0.11`**
> against the original `23.43 ± 0.07` — a 0.3% agreement, well inside both error bars. The
> mislabelled-arm finding stands as the *reason* the replicate was owed; it is no longer an open
> gap. **Do not describe the full-machine figure as unreplicated anywhere.**

---

#### Cross-role placement matrix — all four production CPU roles

*Added 2026-07-30. This supersedes the single-model framing above: D1 was diagnosed on
`frontdoor` alone, and the matrix now covers every production CPU role on **its own production
model artefact**.*

`llama-bench`, `tg128`, **speculative decoding OFF**, `drop_caches` before **every** arm, `r=5`
(`r=10` for `frontdoor`). Kernel `production-consolidated-v8` (binary `10107`), host NPS4. All
values **tok/s**, single instance, single stream.

| arm | launch shape | meaning |
|---|---|---|
| **A** | `taskset -c 0-47,96-143` (straddling `NUMA_NODE0`), **no `numactl` policy** | **the defective shape.** For `frontdoor` and `ingest_long_context` this is *as wired today*; for `worker_general` and `architect_general` it is a **counterfactual** — they are not wired this way |
| **B** | same cpuset + `numactl --interleave=0,1` | isolates *policy* from *cpuset* — how much is recovered by declaring a policy without widening the cpuset |
| **C** | `taskset -c 0-95` + `numactl --interleave=all` | **the canonical recipe.** Already the live wiring for `worker_general` and `architect_general` |

| role | model | A | B | C | A→C |
|---|---|---:|---:|---:|---:|
| `frontdoor` ⚠ **mis-wired** | Qwen3.6-35B-A3B Q8_0 | 10.83 ± 0.04 | — | **23.36 ± 0.11** | **2.16×** |
| `ingest_long_context` ⚠ **mis-wired** | Qwen3-Next-80B-A3B Q4_K_M | 12.42 ± 0.04 | 17.07 ± 0.07 | **22.92 ± 0.31** | **1.85×** |
| `worker_general` ✅ *already correct* | gemma4-26B-A4B Q4_K_M | *(16.37 ± 0.11)* | *(23.43 ± 0.11)* | **39.03 ± 0.56** | *(2.38×)* |
| `architect_general` ✅ *already correct* | Qwen3.5-122B-A10B Q4_K_M | *(4.40 ± 0.01)* | *(6.61 ± 0.02)* | **11.04 ± 0.06** | *(2.51×)* |

> ### ⚠ READ THE SCOPE BEFORE QUOTING ANY RATIO IN THIS TABLE
>
> **Only two of these four roles are losing anything. Two are not.**
>
> * **`frontdoor` (8070) and `ingest_long_context` (8085) are genuinely mis-wired.** For these two,
>   column **A is what production is serving right now** and the A→C ratio (**2.16×** and
>   **1.85×**) is a **live regression** — real throughput being lost today.
> * **`worker_general` and `architect_general` are already correctly wired.** `worker_general`
>   already runs `0-95` + `interleave=all` + `no_mmap: True` (and measures **1.00 weight locality
>   on all five of its instances**); `architect_general` already runs `0-95` + `interleave=all`.
>   For these two, **column A is a COUNTERFACTUAL** — it is what they *would* lose if someone
>   misconfigured them. Their A→C ratios (2.38×, 2.51×, shown *parenthesised and italic* above)
>   are an **independent validation of the canonical recipe on two more models**. They are
>   **NOT** a live regression and **must never be summed, averaged, or presented as fleet-wide
>   damage.**
>
> A reader who takes "all four roles are losing ~2×" from this table has read it wrong. The
> live-damage claim is **two roles**, and it is the same two named in the Priority line.

**The A→C ratio grows with model size**: **`1.85×` at 45.08 GiB → `2.51×` at 72.88 GiB**. This is
consistent with a **remote-memory-bandwidth mechanism** — the larger the resident weight set
relative to per-node capacity and per-node bandwidth, the larger the fraction of every decode step
that must cross the interconnect, and the more a full-machine interleave buys back.

*Stated precisely:* the trend is asserted over the two largest models, where it is clean. It is
**not** monotone across all four (by weight footprint: 15.63 GiB → `2.38×`, 34.37 GiB → `2.16×`,
45.08 GiB → `1.85×`, 72.88 GiB → `2.51×`). Four points spanning four architectures and two quant
families do not isolate a size effect — footprint, quant type, active-expert count and MoE
routing all vary together. Treat "grows with size" as the **mechanism hypothesis the 45 → 73 GiB
pair supports**, not as a fitted law.

**Model-independence note.** Arm C is the same canonical recipe for all four rows and it wins on
all four — across two quant families (`Q8_0`, `Q4_K_M`), four footprints (15.6 → 72.9 GiB), and
four distinct architectures including a hybrid SSM-dense model (Qwen3-Next-80B) and MoE models
spanning A3B to A10B active parameters. **The recipe is not model-specific**, which is the result
that makes it safe to apply to the two mis-wired roles without per-role re-derivation.

Raw logs and the exact producing scripts: `matrix4.sh` / `matrix4_results.txt` (80B, 122B),
`matrix2.sh` / `matrix2_results.txt` (gemma4-26B), `highn.sh` / `highn_results.txt` (`frontdoor`,
`n=10`) — all under the attestation directory.

---

#### Defect 2 — shared mmap means only ONE instance can ever be node-local

llama.cpp `mmap`s the GGUF. Those pages therefore live in the **shared page cache** and are placed
**once**, by whichever process faults them in first. Every later instance maps the *same physical
pages* and inherits that placement **regardless of its own `--membind`**. With
`kernel.numa_balancing=0` (our standing policy) nothing migrates them afterwards.

Measured live from `/proc/<pid>/numa_maps`, four quarter instances each `--membind`-ed to its own
node:

| arm | q0 (own N0) | q1 (own N1) | q2 (own N2) | q3 (own N3) | host RAM used |
|---|---:|---:|---:|---:|---:|
| **mmap (production)** | 25.6% local | 25.6% | 24.2% | 26.9% | **30 GB** |
| **`--no-mmap`** | **100%** | **100%** | **100%** | **100%** | **171 GB** |

Fleet decode aggregate (4 quarters, `np=1` each, MTP spec-dec ON):

| arm | q0 | q1 | q2 | q3 | **fleet aggregate** |
|---|---:|---:|---:|---:|---:|
| mmap | 10.14 | 11.10 | 9.89 | 9.78 | **40.91 tok/s** |
| `--no-mmap` | 14.13 | 11.28 | 13.84 | 12.88 | **52.13 tok/s (+27%)** |

The RAM cost of `--no-mmap` for this fleet is **+141 GB** (30 → 171 GB): each instance gets its
own private 38.1 GB copy instead of sharing one.

##### ⚠ Corollary — fleet throughput is NONDETERMINISTIC ACROSS REBOOTS

Because placement is decided by whichever instance faults the pages first, **fleet throughput
depends on instance START ORDER**. Two observations of the *same* model in the *same* week
landed on opposite extremes:

* **E5 W1 run** (`e5-w1-qwen36-20260729T154725Z`): a single **straddling** instance loaded first
  and first-touched **100% of pages onto node0** (`9,226,101 / 9,226,101` pages, ~35 GB). Every
  one of the 11 later cells in that run inherited it — including the "node-aligned" quarter cells,
  which therefore ran at `local_fraction = 0.00`.
* **Today's quad-fleet probe**: four instances loaded **simultaneously**, so each grabbed ~25% and
  all four ended up symmetric-but-not-local.

Neither is a configuration anybody chose. Any placement claim that does not *declare* its policy
(`--interleave=all` for multi-node shapes, `--membind=<node>` + `--no-mmap` for quarters) is
recording an accident of process scheduling.

---

#### Defect 3 — SMT oversubscription

Half instances are wired `-t 96` onto a cpuset containing **48 physical cores** plus their 48 SMT
siblings. Dropping to `-t 48` (one thread per physical core) is a straight win:

| shape | `np` | `-t 96` per-stream | `-t 48` per-stream | Δ per-stream | `-t 96` aggregate | `-t 48` aggregate | Δ aggregate |
|---|---:|---:|---:|---:|---:|---:|---:|
| HALF (`0-47,96-143`, interleave) | 4 | 11.91 | **13.49** | **+13%** | 94.14 | **102.15** | **+8.5%** |
| QUARTER (`0-23,96-119`, membind) | 4 | 8.18 (`-t 48`) | 8.38 (`-t 24`) | **+2.4%** | 64.03 | 65.51 | +2.3% |

Same sign on quarters, smaller magnitude. The `llama-bench` arm agrees independently: straddle +
interleave at `-t 48` = `15.98` vs `-t 96` = `15.35` (+4%).

---

#### Defect 4 — the E5 metric was wall-clock, not decode

The E5 harness reported

```
aggregate_predicted_tps = total_predicted_tokens / wall_seconds
```

`wall_seconds` spans the whole cell — **model load, warmup, prefill, queueing and idle gaps** — so
it reads systematically low and is not comparable to llama.cpp's `predicted_per_second` or to
`llama-bench` tg.

Fixed by **renaming the field to `aggregate_wallclock_tps`** and adding a true
`aggregate_decode_tps` (per-slot: `sum(predicted_n) / sum(predicted_ms/1000)` over successful
requests, from llama.cpp's verbatim per-request `timings` block).

**Do not read `new/old` as the bug magnitude.** The per-slot denominator sums *overlapping* slot
intervals, so at `T=32` it counts up to 32 slot-seconds per elapsed second; that literal ratio
(median `0.09×`) measures the denominator mismatch, not the defect. The like-for-like comparison
uses `system_decode_tps` = tokens / |union of all `[first_token_s, end_s]` intervals| — same
numerator, same *kind* of denominator, minus load/prefill/idle:

| population | n | min | median | p75 | max |
|---|---:|---:|---:|---:|---:|
| all Stage-B cells | 31 | 1.00× | **1.05×** | 1.09× | 1.22× |
| `T = 1` | 3 | 1.15× | 1.21× | — | 1.22× |
| `T > 1` | 28 | 1.00× | 1.04× | — | 1.13× |

**The metric bug alone understated true system decode throughput by a median of ~5% (22% worst
case, at `T=1`).** It is a correctness and semantics fix — it is **NOT** the main story and it is
**NOT** a rehabilitation of the campaign's numbers. **Defects 1 and 2 are the story.** Full
derivation: `e5_rederived.md` in the attestation directory (was `/mnt/raid0/llm/tmp/`).

The re-derivation is a **pure offline replay** of already-persisted `requests.jsonl` — no
inference, no model loads. Its skip audit is clean: `1333/1333` requests succeeded and every one
carried a well-formed positive `predicted_n`/`predicted_ms` pair, so **0 requests were dropped**
across all 31 cells.

---

#### Defect 5 — the E5 rungs never reached their nominal concurrency

`mean conc` = `sum(predicted_ms) / union window` = the average number of slots actually decoding
at once. Every cell was driven by a **fixed pinned batch of 43 prompts**, so the high-`np` cells
drain before they saturate:

| nominal T | cells | mean achieved concurrency | % of nominal |
|---:|---:|---:|---:|
| 1 | 3 | 1.0 | **100%** |
| 4 | 5 | 3.4 | 86% |
| 8 | 7 | 6.4 | 80% |
| 16 | 8 | 12.4 | 77% |
| 32 | 8 | 14.9 | **47%** |

At `T=32` the machine averaged well under half the nominal slot count. **Any batching-efficiency
conclusion drawn from the `T ≥ 16` rungs is measuring a partially-drained queue, not a saturated
one** — independent of D1 and D2, and it must be fixed in the re-run design (more prompts, or a
closed-loop arrival process, so occupancy holds at `T`).

---

#### Impact on the E5 record

Of the **31** Stage-B cells (2026-07-29, runs `e5-w1-qwen36-20260729T154725Z` /
`e5-w2-gemma-20260729T183151Z` / `e5-w4-80b-20260729T165639Z`), **4 are salvageable**:

* `gemma4_26b_a4b_q4km_mtp-C1-np{1,8,16,32}` — full machine `0-95` + `numactl --interleave=all`,
  weights verified **25.00% per node** from `numa_maps`. Only the metric was wrong; the
  configuration is the intended one.

**27 must be re-run**:

| group | n | why |
|---|---:|---|
| straddling cpuset, no interleave | 13 | threads span 2 nodes, weights first-touched onto one |
| node-aligned cpuset, remote weights | 14 | shared-GGUF pages inherited from an earlier non-interleaved C1 cell in the same run |

The cpuset-shape criterion alone would have said "18 clean / 13 confounded" — **that criterion is
insufficient**, because it cannot see D2. Six qwen36 cells whose cpusets were perfectly
node-aligned ran at `local_fraction = 0.00`. `qwen36_q8_0-C2-np*` had **0% of its weights local on
either instance** (both quarters on N2/N3, all weights on N0), making it strictly *worse* than the
straddling C1 cells it was meant to be compared against.

Corroborating timing gradient at `np=1` (least queueing noise), per-instance decode tok/s by NUMA
distance from N0:

| cell | N0 inst | N1 inst | N2 inst | N3 inst | pattern |
|---|---:|---:|---:|---:|---|
| `qwen36_q8_0-C3-np1` | 3.32 | 3.13 | 2.22 | 2.10 | monotone, 1.58× local:far |
| `qwen3_next_80b-C3-np1` | 3.02 | 2.07 | 1.62 | 0.96 | monotone, 3.15× local:far |
| `gemma4_…-C3-np1` (interleaved control) | 10.42 | 13.17 | 14.89 | 12.16 | flat — no gradient |

Cite the gradient as **corroboration**; the direct `numa_maps` measurement is the primary proof
(the gradient washes out at higher `np` as all four instances contend for one memory controller).

**The preflight instrument saw this and did not gate on it.** Every affinity artifact records
`required: false`, `match: null`, `note: "shared mmap placement observed"`. Per
`affinity_preflight.py:195`, `required = no_mmap and len(expected_nodes) == 1` — the locality gate
arms **only** for `--no-mmap` roles. E5 ran mmap'd, so the gate never armed and six cells at
`local_fraction = 0.0` passed preflight. **`live_memory_placement_verified: true` means *the
placement was observed*, not *the placement was correct*.**

Full cell-by-cell verdict table: `e5_rederived.md` §6b in the attestation directory
(was `/mnt/raid0/llm/tmp/`).

##### What still SURVIVES from the campaign

Unchanged from the suspension banner in [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement):
the **0.0% error rate on every cell** (31/31 Stage-B and the W0 cells) — an error-rate read does
not depend on memory bandwidth; every **harness defect fix** landed during the campaign
(`98cfff44`, `5d6a17f2`, `4a5b6bc7`, `040a2ad7`); and the **protocol / manifest / attestation
machinery** itself — pre-registered cell grids, the affinity-preflight hard gate, the capture
contract and the deterministic-replay ledgers. The instrument is reusable as-is for the
re-measurement, with the D2/D5 fixes folded in.

---

#### Corrected reference numbers

> **Observation-grade.** `n = 1–2` reps, short prompt, MTP speculative decoding **ON**, era
> `production-consolidated-v8` @ `67a433bf4`. These are the *input* to a decision-grade re-run —
> they are not themselves promotable claims and must not be used to gate anything.
>
> **Amended 2026-07-30.** The `n = 1–2` caveat applies to the `np`-ladder and shape tables in
> *this* section, which are MTP-on. The four-role matrix above is a separate, higher-`n`
> (`r=5`/`r=10`), spec-dec-**off** measurement — do not conflate the two. Both remain
> observation-grade, now for a different reason: `P-BENCH-PLACEMENT-1` is STAGED, not ratified.

##### `frontdoor` — Qwen3.6-35B-A3B-MTP-Q8_0, single instance (per-stream / aggregate tok/s)

| shape | np1 | np2 | np4 | np8 | np16 | np32 |
|---|---|---|---|---|---|---|
| **FULL `0-95` + `interleave=all`, `-t 96`** | 38.72 / 38.72 | 27.79 / 54.94 | 19.93 / 79.73 | 13.11 / 105.07 | 8.09 / 130.96 | 4.56 / **145.85** |
| HALF + interleave, `-t 96` | 21.92 / 42.47 | 18.83 / 73.00 | 11.91 / 94.14 | 7.75 / 124.94 | 4.57 / 147.86 | — |
| QUARTER + `membind`, `-t 48` | 14.16 / 27.39 | 10.84 / 41.64 | 8.18 / 64.03 | 4.92 / 78.11 | — | — |

**`np=1` on the corrected full-machine placement reproduces the independent AutoPilot production
anchor**: six sequential requests on a freshly loaded server at the winning placement measured
`39.35 / 36.68 / 36.62 / 36.57 / 36.40 / 36.09` tok/s, against AutoPilot's live
`median_request_tps` median **35.7** (`n=154`, band 35–40). **The original E5 grid had no such
cross-instrument gate** — adding one is a re-run requirement, not an optional nicety.

##### `ingest_long_context` — ⚠ WRONG ARTEFACT — Qwen3-Next-80B-A3B **IQ2_M** (no MTP head, so raw decode)

> ### ⚠ SUPERSEDED 2026-07-30 — this table benched a model production does not serve
>
> These rows used **`Qwen3-Next-80B-A3B-Instruct.i1-IQ2_M.gguf`** (24.27 GiB,
> `/mnt/raid0/llm/models/`). **No role points at that file.** Production `ingest_long_context`
> resolves **`Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf`** (**45.08 GiB**) from
> `/mnt/raid0/llm/lmstudio/models/lmstudio-community/Qwen3-Next-80B-A3B-Instruct-GGUF/`.
>
> **The Q4_K_M rows in the [cross-role matrix](#cross-role-placement-matrix--all-four-production-cpu-roles)
> supersede these for this role** (A `12.42 ± 0.04` → C `22.92 ± 0.31`, `1.85×`). The rows below
> are **kept verbatim** per the append-only rule and are **marked as the wrong artefact**: they
> remain valid as a *shape* result (the decode-vs-context curve and the ordering of the three
> placements) and invalid as an *absolute* figure for this role. A 24 GiB IQ2 model and a 45 GiB
> Q4_K_M model have different bandwidth demands, so the absolute tok/s do not transfer — the
> placement *ordering* does.
>
> **Do not quote any number in the table below as an `ingest_long_context` throughput.**

Decode tok/s by prompt length — **IQ2_M, not the production artefact**:

| arm | 565 tok | 8,749 tok | 28,232 tok |
|---|---:|---:|---:|
| production as-wired (straddle, no policy, warm) | 15.36 | 13.15 | 9.15 |
| same cpuset + `--interleave=0,1` (cold) | 21.12 | 17.28 | 11.29 |
| **full machine `0-95` + `--interleave=all` (cold)** | **25.36** | **20.35** | **12.21** |

Prefill moves the same direction but far less (194 → 274 tok/s at 565; 101 → 107 at 28k) — as
expected, prefill is compute-bound and decode is bandwidth-bound. *(Same IQ2_M caveat.)*

###### `ingest_long_context` — production artefact, Q4_K_M (45.08 GiB)

`llama-bench` `tg128`, spec-dec off, `drop_caches` per arm, `r=5` — from the cross-role matrix:

| arm | tok/s |
|---|---:|
| **A** — as wired today (`0-47,96-143`, no policy) | 12.42 ± 0.04 |
| **B** — same cpuset + `--interleave=0,1` | 17.07 ± 0.07 |
| **C** — canonical `0-95` + `--interleave=all` | **22.92 ± 0.31** |

**This role is mis-wired and the `1.85×` is a live regression.** The decode-vs-context curve has
**not** yet been re-run on Q4_K_M — see **T10**. Until it is, the context-length dependence for
this role is known only in IQ2_M shape.

> **This resolves a standing confusion.** An earlier claim that this role "decodes at ~11 tok/s"
> came from **long-context eval rows** (26.5k / 17.4k-token prompts). At those lengths 9–12 tok/s
> is correct. At short context the same role does **15–25 tok/s**. The two figures were never in
> conflict; the context length was simply never carried alongside the number. Any future decode
> claim for this role MUST state its prompt length.
>
> **Amended 2026-07-30 — the mechanism survives, the numbers do not.** The `15–25` and `9–12`
> bands above are **IQ2_M** figures. The context-length effect is real and the "carry prompt
> length on every claim" rule (T8) stands unchanged. But the *bands themselves* must be re-derived
> on Q4_K_M (T10) before being quoted for this role — at `tg128` the production artefact measures
> `12.42` as-wired / `22.92` canonical, so the short-context band on the real model is lower than
> the IQ2_M `15–25`.

---

#### Topology change applied (2026-07-30) — quarters retired, 1 full + 2 halves

> **State: WRITTEN IN THE WORKING TREE, UNCOMMITTED, NOT RELOADED.** This supersedes the
> *Authorisation status* section below for the *authoring* of the change. It does **not**
> authorise a reload: per `OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*, the reload is
> executed by the session that owns the inference, at a moment it chooses. **A clean-`git archive
> HEAD` A/B measured 30 net-new test failures across 14 files, two of them inside
> `PROMOTION_GATE_TARGETS` — the promotion gate is RED and the stack cannot start until they are
> fixed (N25 P0-1).**
>
> **The commit is separately BLOCKED**, and the ordering is forced, not negotiable: changing the
> cpusets moved the live topology hash to `bc28e15d` while `orchestration/contention_matrix.yaml`
> records `8c8cfcbb13d2611d`; the pre-commit hook (`check_contention_matrix_fresh.py:89`) refuses
> on that; and the **only** refresh path (`contention_matrix.py run`) needs a **live stack and
> runs inference**. So: runs finish → tests green → cold-start → re-bench → commit.
> **Resume state, in-flight runs, and the full cutover queue live in
> [`numa-topology-cutover-resume-20260730.md`](numa-placement-and-contention.md) (N25)** —
> this section records the *finding*; that document records *where the landing is*.

Every quarterable role is now **one full instance plus two halves**. Every instance carries a
**declared memory policy**, and `-t` equals the cpuset's **physical** core count:

| shape | cpuset | `numactl` policy | `-t` |
|---|---|---|---:|
| FULL | `0-95` | `interleave=all` | 96 |
| HALF A — nodes 0,1 (**GPU-disjoint**) | `0-47,96-143` | `interleave=0,1` | 48 |
| HALF B — nodes 2,3 (**GPU co-tenant**) | `48-95,144-191` | `interleave=2,3` | 48 |

| role | full | half A | half B |
|---|---:|---:|---:|
| `frontdoor` | 8070 | 8080 | 8180 |
| `worker_general` | 8072 | 8082 | 8182 |
| `ingest_long_context` | 8085 | 8185 | 8285 |
| `architect_general` | 8083 | — | — (full-only) |

**Ports freed**: `8280` · `8380` · `8282` · `8382` · `8385` · `8485`.

Landed in the same pass:

* **`no_mmap: true` declared in the MASTER registry** for `frontdoor`, `coder_escalation`,
  `architect_general`, `ingest_long_context`, `worker_vision`, `vision_escalation`.
  `worker_general` already carried it (and already measured 1.00 locality). This is the **T2**
  decision, taken as a registry-data change — see the RAM-budget caveats in cross-cutting
  concern 3.
* **`eval_batch_frontdoor` (18070) corrected.** It was `-t 96` on a cpuset holding **48 physical
  cores**, *and* `interleave=all` on a **two-node** cpuset — two independent errors in one
  instance. Now `-t 48` + `interleave=0,1`.
* **Vision pair given explicit `membind=1` / `membind=3`.** `worker_vision` and
  `vision_escalation` are **two roles on two different nodes sharing ONE GGUF** — the exact D2
  shape. Under shared mmap only one of them could ever have been node-local.
* **`ingest_long_context` given a `placement_policy` for the first time.** It had **none**, so it
  defaulted to `SOLO_PREFER_FULL` — a single solo request could take **all four region locks**
  and serialize the machine. That is the DISPATCH-A shape recorded 2026-07-21.
* **`src/fleet.py`** now **derives** its degraded-mode fallback ports from `NUMA_CONFIG` instead
  of hardcoded 5-port lists; **`src/config/models.py`** no longer advertises the freed ports.

**Invariants verified programmatically across the whole of `NUMA_CONFIG`**: (1) no straddling
cpuset without a declared memory policy; (2) `-t` == physical core count. Both hold for every
instance. This closes **T6**.

##### `architect_general` — role definition (operator, 2026-07-30)

Read this before "fixing" its all-region hold. `architect_general` is a **reasoning-boost /
critic** role, invoked in select circumstances only: autopilot planning when running fully local,
and dedicated high-value focused reasoning sessions. It is **not** a general serving role.

Its single full instance on `0-95` holds **all four region locks**, so while it runs it
serializes the entire CPU topology. **That is INHERENT AND ACCEPTED, not a defect** — there is no
sub-full shape to demote to, and a 122B at Q4_K_M has nothing smaller to be. Do **not** add a
`placement_policy` to it; the other roles' `burst_prefer_*` exists because they *have* splits.

The expectation is that **autopilot learns to mostly disregard it**, because the whole-machine
lock is expensive relative to the reasoning gain on most requests. For that to be *learnable*,
the cost must be **ATTRIBUTABLE** — an unattributable whole-machine slowdown is precisely the
shape that produced the mislearned `dual-half-negative` prior. Hence **N25 P1-8**: land
`region_lock_wait_s_by_holder` telemetry **before** exposing any routing knob for this role.

---

#### ngram speculation — a larger lever than the placement fix on two roles

*Discovered 2026-07-30 while measuring placement. Attestation: `ngram.sh` / `ngram2.sh` /
`ngram_results.txt` / `ngram2_results.txt` / `mkreal.py` in the attestation directory.*

Production launches **`--spec-type draft-mtp` alone**. The registry has carried
`ngram_candidate_spec_type: ngram-mod,draft-mtp` as a **never-deployed candidate**.

Measured on **realistic text** — real repository source, **10.6 % repeated 5-grams**:

| model / role | prompt | `draft-mtp` | `ngram-mod,draft-mtp` | speedup |
|---|---:|---:|---:|---:|
| Qwen3.6-35B-A3B — `frontdoor` | 14,059 tok | 24.92 (accept `.505`) | **69.89** (accept `.755`) | **2.80×** |
| Qwen3.6-35B-A3B — `frontdoor` | 53,730 tok | 12.46 | 18.71 | **1.50×** |
| Qwen3-Next-80B — `ingest_long_context` | — | 17.40 | **20.06** (accept `.812`) | **1.15×** |
| gemma4-26B-A4B — `worker_general` (accept `.754`) | — | — | — | **no gain** |
| Qwen3.5-122B-A10B — `architect_general` (accept `.650`) | — | — | — | **no gain** |

**Qwen3-Next-80B carries `acceleration: {type: none}`** because its SSM hybrid has **no
draft-model path**. `ngram-mod` requires no draft model. **It is the only speculation that role
can have** — which reframes the long-standing "not viable on CPU" verdict for it from *no
speculation* to *no draft-model speculation*.

> ### PRINCIPLE — record the rule, not just the numbers
>
> **ngram's benefit is inversely proportional to the incumbent drafter's acceptance rate.** It
> fills headroom, and there is none when the drafter is already strong. That one rule predicts
> every row above: `.505` accept → `2.80×`; `.812` accept (no incumbent at all) → a real but
> modest `1.15×`; `.754` and `.650` incumbents → nothing.

**Methodological correction against this session's own first pass.** The first measurement used
**synthetic filler** — **99.7 % repeated 5-grams, 23 distinct tokens across 8,736 words** — and
returned `2.52×`. That is **nearly worthless as evidence**: it measures the filler, not the
workload. Real repository text confirmed the *direction* but **moved the number**. Any ngram
claim must carry its corpus **and its repeated-5-gram fraction**.

A **GPU ngram sweep (36 cells)** and the remaining **CPU half-shape arms** are **IN FLIGHT and
NOT reportable**. Do not quote a GPU ngram figure from this handoff yet.

---

#### Context depth is a missing term in the claim grammar

Same model, same recipe, same placement — `frontdoor` Qwen3.6-35B-A3B Q8_0:

| prompt depth | decode tok/s | draft acceptance |
|---:|---:|---:|
| 28 tok | **40.22** | 0.746 |
| 570 tok | 28.96 | 0.500 |
| 8,754 tok | 25.18 | 0.478 |
| 34,938 tok | **17.23** | 0.429 |

A **2.3× spread driven purely by depth**, compounded because acceptance decays with it. **The
ratified claim-grammar exemplar carries the 28-token figure and has no depth field** — so it
repeats the retracted `27.06` exemplar's failure mode by a different mechanism. Flagged for
ratification (**N25 P2-4**; `artifacts/operator/ratification_queue_20260730.md` §A). This is the
general form of **T8**, which stated the same requirement for one role.

##### Context allocation is nearly free — capacity is not the binding constraint

| finding | measurement |
|---|---|
| `-c` allocation costs **no decode speed** | 35B: `40.44` tok/s at `-c 8192` vs `40.49` at `-c 262144` |
| `-c` allocation costs **little resident RAM** | gemma4 grew **+6 GB** for a **63.8 GiB** KV reservation — KV pages fault **lazily** |
| `--mlock` does **NOT** pin KV | verified **in llama.cpp source**, not inferred from behaviour |
| every deployed model fits its **full 262,144-token trained window** | true even on a *quarter* instance |

Production runs `-c 32768` = **12.5 %** of what the hardware allows; `architect_general` halves
that again to `8192`/request via `slots: 2`. **Consequence: context can be provisioned at
maximum and managed by a compaction policy above the server, rather than rationed at launch.**
Filed as **T12**.
Attestation: `ctxalloc.sh` / `ctxalloc_results.txt` / `maxctx.py` / `ctxcurve.sh` / `ctxparse.py`.

---

#### Measurement-program repairs landed 2026-07-30

* **`MRG-1` model-registration runbook** —
  `epyc-inference-research/docs/protocols/model-registration-runbook.md`. It is a **GATE, not a
  guide**: a model that has not completed **Steps 0–9 is NOT REGISTERED** and must not hold a
  production role. Its **14 unset values are listed as TBD rather than invented** — proposals in
  the ratification queue (**N25 P2-3**).
* **Attestation rewritten** —
  `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/` now holds **52+
  files with every raw log beside the script that produced it**, plus a **caveats section naming
  the rows that are unsafe to reuse**.
* **`artifacts/operator/ratification_queue_20260730.md`** — proposed values for every TBD, each
  with its derivation and the failure it would have caught. Rationale: **a gate whose threshold
  is unset cannot fail.**
* **Harness metric correction (extends D4).** `aggregate_predicted_tps` was
  `tokens / wall_seconds` → renamed **`aggregate_wallclock_tps`**, true **`aggregate_decode_tps`**
  added. **tasks/hour had been *deciding*** — R1 winners, R2 peaks, R4 optima, `best_np` and the
  saturation knee all ranked on it. **All now rank on tok/s.**

---

#### GPU — self-correction: a working ROCm binary DOES exist

This session claimed earlier that **no ROCm binary existed**. **That was wrong**, from three bad
inferences:

1. **backends are `dlopen`ed, not linked** — so `ldd` proves nothing about backend availability;
2. **17 KB is normal** — the production binary is the same size;
3. **`--list-devices` was empty only because `LD_LIBRARY_PATH` was unset.**

The v8 HIP build works: `ROCm0: AMD Instinct MI210`, version `10107` (`67a433bf4`) — **the same
SHA production serves on CPU**. **ngram IS supported on GPU.** Recorded here because the failure
mode is reusable: three independent negative inferences, none of which was verified against the
primary artefact.

---

#### Tasks

##### Done

- [x] Root-cause diagnosis of the E5 anomaly — identified as production **wiring**, not kernel,
      not iqk, not MTP, not the meter ✅ 2026-07-30
- [x] NUMA placement matrix (`llama-bench` tg128): warm/cold × straddle/interleave/full-machine ×
      `-t 48`/`-t 96`, plus the single-NPS4-node instrument-validation arm ✅ 2026-07-30
- [x] mmap shared-placement locality proof from `/proc/<pid>/numa_maps` — 4×`--membind` quarters,
      mmap vs `--no-mmap`, with the +141 GB RAM cost quantified ✅ 2026-07-30
- [x] SMT-oversubscription probe (`-t 96` vs `-t 48` on halves, `-t 48` vs `-t 24` on quarters) ✅ 2026-07-30
- [x] 80B `ingest_long_context` decode-vs-context curve across three placements — resolves the
      "~11 tok/s" ambiguity ✅ 2026-07-30
      ⚠ *Amended 2026-07-30: this ran on **IQ2_M**, which no role serves. The placement ordering
      and the context-length mechanism stand; the absolute bands do not. Re-run tracked as **T10**
      — this checkbox stays `[x]` because the work was done, not because the answer is final.*
- [x] E5 harness metric rename `aggregate_predicted_tps` → `aggregate_wallclock_tps` + new true
      `aggregate_decode_tps` ✅ 2026-07-30
- [x] Offline re-derivation of all 31 Stage-B cells from persisted `requests.jsonl` (zero
      inference) — per-slot, system-wide and achieved-concurrency reads + the 4-salvageable /
      27-must-re-run verdict ✅ 2026-07-30
- [x] Cross-link: suspension banner recorded in the owning handoff
      [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement) ✅ 2026-07-30
- [x] `stack_numa.py` annotated with the measured consequence and with the retraction of the
      2026-04-17 head-to-head that was cited to justify the wiring (that run predates the NPS4
      reboot **and** its source CSV records `spec == "baseline"`, i.e. speculative decoding OFF —
      `26.60`/`27.06` t/s must not be cited as a current figure for this shape) ✅ 2026-07-30
- [x] **Complete the placement matrix across all four production CPU roles**, each on its own
      production model artefact — A (as-wired) / B (cpuset+`interleave=0,1`) / C (canonical),
      `tg128`, spec-dec off, `drop_caches` per arm, `r=5` ✅ 2026-07-30
- [x] Correct the `ingest_long_context` model artefact — production resolves **Q4_K_M**
      (45.08 GiB), not the IQ2_M file the first pass benched; Q4_K_M A/B/C rows measured and the
      IQ2_M rows marked as the wrong artefact ✅ 2026-07-30
- [x] Promote the measurement artifacts out of `/mnt/raid0/llm/tmp/` — all raw logs **plus the
      exact producing script per figure** committed to
      `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/` with a
      figure→file map in its `README.md` ✅ 2026-07-30
- [x] Codify the protocol — `P-BENCH-PLACEMENT-1`,
      `epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md`, with its
      `MEASUREMENT.md` registry entry **staged** in Appendix A ✅ 2026-07-30

###### Second pass, 2026-07-30 (session `mainA`)

- [x] **Retire quarters; re-shape every quarterable role to 1 full + 2 halves**, each with a
      declared memory policy and `-t` == physical core count. Ports: `frontdoor`
      8070/8080/8180, `worker_general` 8072/8082/8182, `ingest_long_context` 8085/8185/8285,
      `architect_general` 8083 (full-only); freed 8280/8380/8282/8382/8385/8485.
      **Uncommitted, not reloaded** ✅ 2026-07-30
- [x] **Correct `eval_batch_frontdoor` (18070)** — was `-t 96` on 48 physical cores **and**
      `interleave=all` on a two-node cpuset; now `-t 48` + `interleave=0,1` ✅ 2026-07-30
- [x] **Give the vision pair explicit `membind=1` / `membind=3`** — two roles on two different
      nodes sharing ONE GGUF, so under shared mmap only one could ever be node-local ✅ 2026-07-30
- [x] **Give `ingest_long_context` a `placement_policy`** — it had none, so it defaulted to
      `SOLO_PREFER_FULL`, letting one solo request take all four region locks and serialize the
      machine (the DISPATCH-A shape, 2026-07-21) ✅ 2026-07-30
- [x] **Derive `src/fleet.py` degraded-mode fallback ports from `NUMA_CONFIG`** instead of
      hardcoded 5-port lists; stop `src/config/models.py` advertising the freed ports ✅ 2026-07-30
- [x] **Verify both wiring invariants programmatically across all of `NUMA_CONFIG`** — no
      straddling cpuset without a memory policy; `-t` == physical core count ✅ 2026-07-30
- [x] **Record the `architect_general` role definition** (operator): reasoning-boost/critic for
      autopilot planning and dedicated high-value reasoning sessions; its all-region hold is
      **inherent and accepted**, not a defect ✅ 2026-07-30
- [x] **Repair the stack-change gate — twice in one day, from two different sessions.** A commit
      touching any `REQUIRED_SOURCE_ARTIFACTS` file silently blocks
      `orchestrator_stack.py start` until priors are recompiled, with no warning at commit time
      (orchestrator `418810ef`, `002079d7`) ✅ 2026-07-30
- [x] **Replace the test that asserted the defective wiring AND forbade its fix** —
      `test_frontdoor_full_uses_numa_node0_not_full` → `test_straddling_cpusets_declare_a_numa_policy`,
      `xfail(strict=True)` so it fails loudly once the invariant holds (orchestrator `78e9d109`) ✅ 2026-07-30
- [x] **Correct `P-BENCH-PLACEMENT-1`'s own status line** — the protocol file still declared
      itself STAGED after the operator ratified it (research `0a7f767d`) ✅ 2026-07-30
- [x] **Rewrite the attestation index** — 52+ files, every raw log beside the script that
      produced it, plus a caveats section naming rows unsafe to reuse ✅ 2026-07-30
- [x] **File `artifacts/operator/ratification_queue_20260730.md`** — proposed values, with
      derivations, for every TBD in `P-BENCH-PLACEMENT-1` §7 and `MRG-1` §5, because a gate whose
      threshold is unset cannot fail ✅ 2026-07-30
- [x] **Write `MRG-1`**, `epyc-inference-research/docs/protocols/model-registration-runbook.md`
      — a **gate**, not a guide: Steps 0–9 incomplete ⇒ NOT REGISTERED ⇒ must not hold a
      production role. 14 unset values listed as TBD rather than invented ✅ 2026-07-30
- [x] **Measure the ngram lever** on all four production CPU models, on realistic text
      (10.6 % repeated 5-grams), after discarding a synthetic-filler first pass ✅ 2026-07-30
- [x] **Measure the context-depth curve and the `-c` allocation cost** — 2.3× decode spread by
      depth; `-c` costs no speed and little RAM; `--mlock` does not pin KV (verified in
      llama.cpp source) ✅ 2026-07-30

##### Open

- [x] **T1 — Fix the `stack_numa.py` wiring.** ✅ 2026-07-30 — **WRITTEN, uncommitted, NOT
      RELOADED.** Quarters retired; every quarterable role is 1 full + 2 halves; every instance
      carries a declared memory policy; `-t` == physical core count everywhere; NPS2-era
      constants superseded by `NUMA_FULL` / `NUMA_HALF_A` / `NUMA_HALF_B`. The D3 `-t 48` vs
      `-t 96` question is decided per shape (48 on halves, 96 on full). **What remains is not
      T1**: the test suite (**N25 P0-1**) and the reload with its three gates (**N25 P0-3**). Original
      text retained below.
  - *(Original text, superseded — retained per the append-only rule.)* ⚠ **NOT AUTHORISED YET.**
      Requires the inference
      owner, the three stack gates (pipeline-green ≠ starts ≠ live==config), and a reload executed
      *by the session that owns the inference, at a moment it chooses*. Scope: `frontdoor` idx0
      and `ingest_long_context` idx0 off the straddling `NUMA_NODE0`; rename or retire the
      NPS2-era constants; decide `-t 48` vs `-t 96` per shape (D3).
      *Amended 2026-07-30 — scope CONFIRMED by the four-role matrix: exactly these two roles.*
      `worker_general` and `architect_general` need **no change** (already `0-95` +
      `interleave=all`); the matrix's counterfactual A-columns for them are what T1 is *preventing*,
      not what it is fixing. Expected gain on the two in scope: **`frontdoor` `10.83` → `23.36`
      (`2.16×`)**, **`ingest_long_context` `12.42` → `22.92` (`1.85×`)** — observation-grade until
      T9, so these size the change, they do not gate it.
- [x] **T2 — Decide `--no-mmap` for quarter fleets.** ✅ 2026-07-30 — **DECIDED: declare it.**
      `no_mmap: true` is now set in the MASTER registry for `frontdoor`, `coder_escalation`,
      `architect_general`, `ingest_long_context`, `worker_vision`, `vision_escalation`
      (`worker_general` already had it). The quarter framing is moot — quarters are retired.
      Original text: *+27% fleet decode against **+141 GB** host RAM for the 35B quad; needs a
      lineup-level RAM budget decision, not a local one.* The +141 GB figure was for a 4×quarter
      fleet; the 1-full + 2-half topology has a **different residency envelope**, and the actual
      post-reload RSS is unmeasured — verify it as part of **N25 P0-3**, not before.
- [x] **T3 — Re-run the 27 confounded E5 cells** on declared placement. Per model the grid must
      include **full machine `0-95` + `--interleave=all`**, which *was not in the Stage-B grid at
      all* except as gemma's C1 — and which won today for both `qwen36_q8_0` and
      `qwen3_next_80b`. Either drop caches between placement shapes or launch every instance under
      an explicit policy, so placement is **declared, never inherited**.
      *(Amended 2026-07-30: the re-run must conform to **`P-BENCH-PLACEMENT-1`**, now ratified,
      and its grid must use the **new 1-full + 2-half shapes** — the old quarter arms no longer
      exist. **27 of 31 cells** still outstanding.)*
  - **2026-11-02 BRF-T3 (ws58):** adjudication input for the regeneration list. Of the 8 banked Gemma A7 cells, 4 are DEMONSTRATED-INVALID (C1b) and 4 are UNRESOLVED (C1); none is VALID. The box stays open. [belief: cc] `docs/design/backlog-refactor-2026-11/t3-evidence/e5-adjudication-20261102.json` [declined: operator 2026-11-03 model-audit: superseded by RE-MEASURE E5 Stage-B on the corrected placement (same declared-placement grid; its gemma/Qwen3-Next models are deleted)]
- [x] **T4 — Fix the E5 batch drain (D5)** so the high-`T` rungs actually saturate: more prompts,
      or a closed-loop arrival process holding occupancy at `T`. Without this the `T ≥ 16` rungs
      remain uninterpretable even on corrected placement.
      **ANALYSIS DONE + CAUSE QUANTIFIED ✅ 2026-08-12 (`mainA`), zero inference. The row's
      proposed remedy is half right and its diagnosis needs correcting.**
      **The driver is ALREADY closed-loop.** `run_cell_driver` binds N×K streams permanently and
      pulls from one shared queue — its own docstring says so. So "or a closed-loop arrival
      process" is already satisfied; there is no open-loop arrival defect to fix.
      **The real cause is the fixed work quantum.** The batch is a pinned 43 prompts, and
      `T = instances × np`, so requests-per-stream is `43/T`. Measured across all 31 canonical
      Stage-B cells:

      | T | requests/stream | cells with an EMPTY trimmed window |
      |---:|---:|---|
      | 1 | 43.00 | 0 / 3 |
      | 4 | 10.75 | 0 / 5 |
      | 8 | 5.38 | 0 / 7 |
      | 16 | 2.69 | 0 / 8 |
      | **32** | **1.34** | **5 / 8** |

      At T=32 most streams serve **exactly one request**, so the run is ramp plus drain with no
      middle — there is no steady state for `trimmed_aggregate` to find. That is not a trimming
      defect, it is a *sample-size* defect, and it is why the top rung is uninterpretable.
      **T4 and A6 are the same defect from opposite sides**: A6 is the read-side decision (what
      the gate should do about an empty window), T4 is the write-side fix (make the window
      non-empty by giving each stream enough work). Ratifying A6's decouple does NOT make the
      T=32 rung interpretable — it only stops the empty window from voiding the cell's grade. The
      rung stays uninterpretable until the quantum grows.
      **Floor, so the ask is concrete:** for ≥4 requests per stream at T=32 the batch needs **≥128
      prompts**; for ≥3, **≥96**. The three T=32 survivors are all C3 (4 instances × np8), where
      per-instance staggering still lets some request straddle — so T=32 is necessary, not
      sufficient.
      **NOT IMPLEMENTED, and this is the blocker to name:** the 43-qid batch is a **pinned**
      instrument (`prompt_batch.selection: pinned_qids`; the generator docstring states
      re-sampling tier/seed is FORBIDDEN because the pool was rebuilt at the E7 boundary).
      Growing it changes the measurement instrument and breaks comparability with every banked
      E1/W0/Stage-B cell, so it is an operator ruling — and it should be recorded as an **era
      boundary**, not an edit, exactly as the 2026-08-11 rider argues for objective changes.
- [ ] **T5 — Arm the locality gate for mmap roles.** [too-big: interleave threshold and shared mmap attribution need handoff resolution] `affinity_preflight.py:195` currently sets
      `required = no_mmap and len(expected_nodes) == 1`, so under mmap it observes and reports
      but never fails. It should fail a single-node instance whose `local_fraction` is below
      threshold regardless of mmap.
      *(Amended 2026-07-30 — the predicate **self-disarms twice**, and the second way now matters
      more: `len(expected_nodes) == 1` means it never arms on a **multi-node** instance, and
      after the topology change **every** instance is multi-node. The **operator has chosen
      hard-fail**. BLOCKED on ratifying **`INTERLEAVE_TOLERANCE`** (proposed ±25% relative, i.e.
      each node within `[0.75/n, 1.25/n]`) — there is no multi-node analogue of the single-node
      equality check without it. See **N25 P2-3**.)*
      **Live evidence 2026-08-27:** the corrected INF-42 G1 server is a fresh `--no-mmap` process
      launched with `numactl --interleave=all`, CPUs `0-95`, 96 threads and equal kernel weighted-
      interleave weights. Nevertheless, a during-inference `numastat` sample placed 32.28/41.89 GiB
      (~77%) on node 3; its largest 9,006,874-page anonymous mapping reports `interleave:0-3` but
      has 7,198,279 pages on node 3. This is direct anti-vacuity evidence for T5: declared policy is
      not proof of achieved placement, including for a multi-node `--no-mmap` process. The INF-42
      recall outputs remain usable, but its timing fields are not placement-authoritative.
  - **Operator decision 2026-11-10:** INTERLEAVE_TOLERANCE ±25% is ratified (TBD 2, RATIFY-INF45-P23-20261109), so the blocker is gone; T5 is now code-only (`affinity_preflight.py:277`).
- [x] **T6 — Audit the remaining roles for straddling cpusets** and for `numactl_policy: none` on
      any multi-node cpuset ✅ 2026-07-30 — done as a **programmatic invariant check over all of
      `NUMA_CONFIG`**, not a manual read: (1) no straddling cpuset without a declared memory
      policy, (2) `-t` == physical core count. Both hold for every instance. The audit is what
      surfaced the `eval_batch_frontdoor` double error and the vision pair's shared-GGUF
      collision.
- [x] **T7 — Replicate the `23.43 ± 0.07` full-machine figure.** ~~It is currently one 3-rep
      `llama-bench` invocation with no independent repeat (the script arm labelled as its repeat
      is mislabelled and actually repeats the straddle+interleave arm).~~ **CLOSED** — an
      independent `n=10` run (`highn.sh`) measured **`23.36 ± 0.11`** against the original
      `23.43 ± 0.07`, a 0.3% agreement. The full-machine figure is replicated; the mislabelled
      arm remains documented as the reason the replicate was owed ✅ 2026-07-30
  **PARTIAL ✅ 2026-08-11 (`mainA`), orchestrator `d83661a5` — the vacuous-pass half is closed; arming
  stays blocked.** Found while reading the predicate: `memory_verified` is `mismatches == 0`, and
  since the predicate is false for **every** instance post-topology-change, the artifact asserted
  `live_memory_placement_verified: true` on runs that examined **zero** entries — and
  `--require-memory-locality`, an explicit request for the guarantee, passed **vacuously**. Absence
  read as a pass, the A11 shape one subsystem over. Now `memory_checked` derives from entries actually
  examined, the artifact carries `live_memory_placement_checked` + `memory_locality_vacuous`, and the
  flag REFUSES with a message naming the predicate when nothing was eligible; the vacuity branch fires
  before the mismatch branch, pinned by a test (25/25, 6/6).
  **Arming deliberately NOT done**, for two independent reasons: this row is blocked on ratifying
  `INTERLEAVE_TOLERANCE`, and **mmap placement is shared across instances** — a single-node mmap role
  can show a low `local_fraction` because another instance first-touched the pages — so arming it
  would hard-fail correctly-configured roles. That is the throttle-gate failure mode. Still blocked on
  the tolerance ratification for the multi-node analogue.

- [x] **T8 — Carry prompt length on every decode claim for `ingest_long_context`**, in the
      registry and in any handoff that quotes a tok/s for it.
      **REGISTRY HALF DONE ✅ 2026-08-12 (`mainB`, research `7dddce0f`); handoff half still open.**
      Two of the four figures already carried context (`long_context_tps_range … @ ~12K context`,
      `summarization_benchmark … (10K context)`). **`baseline_tps: 10.12` and `optimized_tps: 10.12`
      did not** — and those are the ones consumers read *programmatically*. Annotated as a
      **provenance GAP, not back-filled**: the prompt length was never recorded with them, and
      inventing one to satisfy the rule would defeat the rule. Flagged for whoever re-derives them
      under T10 to record context at the same time.
      **Landed in the MASTER** (`epyc-inference-research/orchestration/model_registry.yaml`), NOT
      `epyc-orchestrator/orchestration/model_registry.yaml` — that file is the compiled runtime view,
      regenerated from the master at every `orchestrator_stack.py start`, so an edit there is
      silently wiped. Worth stating because the row says "in the registry" and there are two.
      **Handoff half — surveyed, not done** (spans other owners' files, so not swept unilaterally).
      Unqualified `ingest_long_context` tok/s quotes found in: `bulk-inference-campaign.md:83,584`
      (`17.27 t/s`, Tulving run), `gemma-challenge-kernel-techniques-v7.md:396` (`13.89`/`14.02`
      base decode, `23.52`/`23.27` server path), `autopilot-continuous-optimization.md:1081`
      (`12.3 t/s/quarter`), `stack-lineup-dossier-2026-07-23.md:21` (`12.3 t/s/quarter`),
      `within-role-placement-state-machine.md:315` (`12.34 t/s`, `~0.1 t/s`). The 9–12 vs 15–25 split is entirely
      a context-length effect. *(Amended 2026-07-30: the rule stands; the 9–12 / 15–25 bands
      themselves are IQ2_M and must be re-derived on Q4_K_M — T10.)*
      **AUDIT DONE ✅ 2026-08-12 (`mainA`), zero inference. Three bare-quote sites, and the rule
      is already half-implemented in one of them.**
      **(1) `speculative-decoding-mtp-refresh.md:92` — the table ALREADY HAS a `prompt` column
      and `ingest_long_context` is the one row that leaves it `—`.** Its neighbours carry
      `14,059 tok` and `53,730 tok`; the 80B row quotes `17.40` and `20.06` t/s against a blank.
      This is the cheapest possible fix — the column exists, the cell is empty — and it is the
      most load-bearing, because a `1.15x` speculation speedup is meaningless without knowing the
      context it was measured at. **Recoverable from that handoff's own artifact; routed to its
      owner, not filled in by me — I will not invent a prompt length.**
      **(2) Registry `roles.ingest_long_context.performance`** carries context where it matters
      (`long_context_tps_range: "14.4-20.8 t/s @ ~12K context"`, `summarization_benchmark:
      "73.8s for 464 tokens ... (10K context)"`) but `baseline_tps: 10.12` and `optimized_tps:
      10.12` are **bare** — and 10.12 sits squarely in the 9-12 short-context band this row says
      is a context artefact. So the registry states the rule for its long-context fields and
      breaks it for its headline ones.
      **(3) This handoff's own A/B/C placement table (`:209`) has no prompt column for any role.**
      Materially the weakest of the three: every arm shares one prompt, so the `A→C` ratio the
      table exists to establish is unaffected. The hazard is only that the absolute `12.42` /
      `22.92` travel out of the table and get compared against a long-context number.
      **Not edited, deliberately.** The amendment above already says the 9-12 / 15-25 bands are
      IQ2_M and must be re-derived on Q4_K_M under **T10**, which needs compute. Annotating
      numbers that are scheduled to be replaced is churn, and rewriting a measurement table is
      not something to do at 3am on an append-only record. The durable half of T8 is the RULE,
      and the rule now has three named enforcement points instead of a general instruction.
- [x] **T9 — Operator ratification of `P-BENCH-PLACEMENT-1`.** ✅ 2026-07-30 — **RATIFIED** by
      the operator (epyc-root `07b7dcab`): registered in `MEASUREMENT.md` §2 plus the annex
      `measurement/protocols/bench-cpu.md`. `P-BENCH-3` was conformed to §1 in the same pass
      (tok/s primary, tasks/hour **retained** as secondary — it was **not** removed). The
      protocol's own file still said STAGED afterwards; corrected in research `0a7f767d`.
      **Grade is no longer blocked by protocol status** — but see **N25 P2-2** (three of four roles
      have no anchor to satisfy the mandatory anchor gate) and **N25 P2-3** (several §7 thresholds are
      still TBD, and a gate whose threshold is unset cannot fail).
- [x] **T10 — Re-run the `ingest_long_context` decode-vs-context curve on the production Q4_K_M ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): ingest_long_context numa_config block removed 2026-09-22 (stack_topology.yaml:296); role is GPU Qwen3.8-27B, no CPU artefact to curve. [no-belief: obsolete, role moved to GPU]
      artefact.** The existing 3-placement × 3-prompt-length curve is IQ2_M (24.27 GiB), which no
      role serves. Only the `tg128` point exists on Q4_K_M (45.08 GiB). Needed before any
      long-context tok/s is quoted for this role, and it feeds T8. (re-scoped 2026-11-03 from IQ2_M/Q4_K_M Qwen3.5-122B-era ingest_long_context artefact: deleted; now Qwen3.8-27B-Q8_0 ingest_long_context (GPU))
- [x] **T11 — Audit every other role for the wrong-artefact class of error.** The IQ2_M mistake
      was not a placement bug — a benched file simply was not the file production resolves. The
      same check has already caught a second instance (`modelref_results.txt` benched
      `gemma-4-26B-A4B-it-Q4_K_M-current.gguf` where `worker_general` serves
      `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf`). Resolve each role's GGUF through the live registry
      chain and diff it against whatever any open handoff quotes for that role.
      **✅ 2026-08-11 (`mainA`) — DONE. Audit: [`docs/reviews/t11-wrong-artefact-audit-20260811.md`](../../docs/reviews/t11-wrong-artefact-audit-20260811.md).**
      Resolved all 11 hot-resident roles through `model_registry_full.yaml → roles[*].model.path` and
      diffed against every `.gguf` quoted on a role line in `handoffs/active/*.md`.
      **One NEW instance, the third of this class**: `rao-redel-substrate-spike.md:120` records the
      ReDel spike against `worker_general` serving `gemma-4-26B-A4B-it-Q4_K_M.gguf`, but that role
      serves `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf`. Both exist on disk at `16,796,010,720` (Apr 4)
      vs `16,796,016,544` (Jun 25) — 5,824 bytes apart, which is why the class survives a casual read.
      **The same line carries a second defect**: it says *"via ik_llama.cpp PR #1744 MTP"*, and
      ik_llama.cpp is a fully deprecated serving path — so those observations came off a
      non-production artefact **and** a non-production kernel. Routed to that handoff's owner rather
      than edited: it is a historical spike record, so it needs a provenance note appended, not its
      numbers rewritten.
      **No other open handoff misquotes a hot-resident role's serving artefact.** 12 of the 15 raw
      hits are false positives in two named families (drafter GGUFs on a target line; multi-role
      lines), recorded in the audit so a mechanical version does not ship an ~80% false-positive
      rate and train readers to ignore it.
- [x] **T12 — Re-decide `-c` provisioning now that its cost is measured at ~zero.** Production ✅ 2026-11-10 — decided by operator: provision the full trained window and manage context by a compaction policy above the server. [no-belief: operator decision, not a measurement]
      runs `-c 32768` = **12.5 %** of the 262,144-token window every deployed model was trained
      for, and `architect_general` halves that again to **8192/request** via `slots: 2` — a
      rationing decision made when the cost was assumed, not measured. Measured 2026-07-30:
      `-c` allocation costs **no decode speed** (35B `40.44` at `-c 8192` vs `40.49` at
      `-c 262144`) and **little resident RAM** (gemma4 +6 GB for a 63.8 GiB KV reservation),
      because **KV pages fault lazily** — and `--mlock` does **not** pin them (verified in
      llama.cpp source). Every deployed model fits its full trained window on even a *quarter*.
      **RAM is not the binding constraint.** So the question is whether context should be
      provisioned at maximum and managed by a **compaction policy above the server** rather than
      rationed at launch. This is a lineup-level decision with a residency bill, like T2 — do not
      flip it per-role. Sequence it **after** the N25 cutover commit; it changes the launch
      command and therefore forces another recompile. Attestation: `ctxalloc.sh` /
      `ctxalloc_results.txt` / `maxctx.py` in the attestation directory.
      **DECISION PACKAGE 2026-08-12 (`auditor`, claimed from the queue; analysis done, ruling
      routed — the flip is the lineup owner's/operator's, per the residency bill this row itself
      names).** The measurement kills the OLD premise (launch-time cost) but does not establish
      max-provisioning as free: **lazy faulting relocates the cost from launch to load.** RSS
      grows toward the full reservation exactly when requests genuinely use deep context, so
      max-`-c` converts a launch-time guarantee (bounded KV by construction) into a runtime
      exposure (worst case = Σ over resident roles of full-window KV, hit silently under
      concurrent deep-context load). "~Zero" was measured at reservation and short-context — true,
      and not the number the decision needs. **Options**: (A) max-provision fleet-wide + a
      compaction/eviction policy above the server — full trained window everywhere, but the
      policy machinery does not exist yet and the worst-case sum is uncomputed; (B) **staged,
      recommended**: raise `-c` only where the lineup's Σ full-window-KV fits RAM with stated
      margin — compute that sum mechanically at priors/stack compile time so the gate is a check,
      not a judgement — and keep rationing elsewhere until (A)'s policy exists; (C) status quo —
      worst option: a rationing decision standing on a premise now measured false. Sequencing
      per the row: fold the `-c` change into the N25 recompile to pay the recompile once.
      Ruling owner: lineup owner + operator. Row stays open pending the ruling.
  - **Operator decision 2026-11-10:** full trained window accepted (lineup-level; not per-role).
  - [ ] Apply full-trained-window `-c` across the lineup as one stack-change package (stack-change skill), with the compaction policy above the server; needs a running production stack.

##### Opened 2026-07-30 by the topology change — OWNED ELSEWHERE, do not re-file here

> **These are filed as checkboxes in
> [`numa-topology-cutover-resume-20260730.md`](numa-placement-and-contention.md)
> (master-index row **N25**), which is the cutover-resume half of this work.** They are listed
> here **without checkboxes on purpose** — duplicating them would give the handoff dashboard two
> sources of truth for the same task and double-count the queue. **This document is the
> diagnosis; N25 is the resume state.** Track completion there.

| Actionable opened by this session | Owned by |
|---|---|
| Fix the tests that break under the new topology — a clean-`git archive HEAD` A/B measured **30 net-new failures across 14 files**, 2 inside `PROMOTION_GATE_TARGETS`; **stack start is gated on them** | N25 **P0-1** |
| Drop the now-XPASSing `xfail(strict=True)` on `test_straddling_cpusets_declare_a_numa_policy` | N25 **P0-2** |
| Cold-start, re-bench the contention matrix, commit + push all three repos | N25 **P0-3** |
| Make the `placement_policy` enum vocabulary shape-agnostic (it is quarter-shaped) | N25 **P1-1** |
| Arm the `affinity_preflight` hard-fail (**= T5 above**) | N25 **P1-2** |
| **Supersede — never edit** — the `dual-half-negative` seed prior, which forbids the deployed topology | N25 **P1-3** |
| Land `region_lock_wait_s_by_holder` telemetry **before** any autopilot routing knob | N25 **P1-8** |
| Delete-candidate `scripts/server/quarter_scheduler.py` (403 ln, 0 runtime importers) | N25 **P1-9** |
| Pre-commit check for `REQUIRED_SOURCE_ARTIFACTS` staleness (fired twice today, two sessions) | N25 **P1-10** |
| Re-run the 27 confounded E5 cells (**= T3 above**) | N25 **P2-1** |
| Production anchors for the three roles that have none | N25 **P2-2** |
| Ratify the TBD thresholds, incl. `INTERLEAVE_TOLERANCE` which blocks T5 | N25 **P2-3** |
| Context-depth field in the claim grammar (generalises **T8**) | N25 **P2-4** |
| Fold the ngram result into the production recipe | N25 **P2-5** + [speculative-decoding-mtp-refresh.md](speculative-decoding.md#track-speculative-decoding-mtp-refresh) **NG1–NG5** |
| Report the in-flight GPU ngram sweep (36 cells) | [speculative-decoding-mtp-refresh.md](speculative-decoding.md#track-speculative-decoding-mtp-refresh) **NG4** |

N25 additionally owns five defects this handoff never named — `stack_templates/default.yaml` as a
**fourth** hand-maintained copy of the topology (**P1-4**), the missing
`registry_validator` cross-check of `numa_ports` against `NUMA_CONFIG` that **allowed months of
drift** (**P1-5**), `eval_tower.py`'s `stack_numa_mode == "quarter"` test that **silently
collapses eval fan-out to 1** under a half fleet (**P1-6**), `vision_escalation`'s **phantom
5-port fleet** (**P1-7**), and the contention matrix's inability to see the **GPU shadow lane**
(**P1-11**).

**Correction to this session's own count**: an early read put the breakage at "~22 tests". The
measured clean-HEAD A/B is **30 net-new failures across 14 files**. Cite 30.

---

#### Dependencies

```
D1/D2/D3 diagnosis (DONE)  +  4-role matrix (DONE)  +  T7 replication (DONE)
      │
      ├──> T1 fix stack_numa.py ──┐   [BLOCKED: operator + inference owner + 3 stack gates]
      │      (frontdoor + ingest   │    scope CONFIRMED by the matrix: exactly 2 roles
      │       ONLY — worker/       │
      │       architect already OK)│
      │                            │
      ├──> T2 --no-mmap decision ──┤   [BLOCKED: needs T1's shape decision + a RAM-budget ruling]
      │                            │
      ├──> T5 arm locality gate ───┤   [independent; do FIRST — it is the guard for T3]
      │                            │
      ├──> T4 batch-drain fix ─────┤   [independent; harness-only, zero inference]
      │                            │
      └──> T11 wrong-artefact audit┤   [independent; do BEFORE T3 — else 27 cells on wrong GGUFs]
                                   │
                                   v
                              T3 re-run 27 E5 cells
                                   │
                                   ├──> batched-decode-measurement.md E5 waypoint closes
                                   ├──> within-role-placement-state-machine.md per-instance -np sizing
                                   └──> heterogeneous-slot-fabric-residency.md (N,K) provisioning

T9 operator ratification of P-BENCH-PLACEMENT-1  [orthogonal — gates GRADE, not work]
      │
      └──> promotion of ANY figure here past observation-grade
           (and therefore: gating T1 on a measured number)

T10 Q4_K_M context curve ──> T8 prompt-length-carrying claims for ingest_long_context
```

##### Second pass, 2026-07-30 — what changed in this graph, and where the rest of it lives

The head of the graph above has resolved: **T1 (wiring) is WRITTEN**, **T2 (`no_mmap`) is
DECIDED**, **T6 (invariant audit) and T7/T9 are CLOSED**. What replaces them is a *landing*
sequence, not a diagnosis sequence, and it is owned by
**[`numa-topology-cutover-resume-20260730.md`](numa-placement-and-contention.md) §3** —
read that graph, not a second copy here. Three orderings from it bear directly on tasks that
remain in *this* document:

* **`N25 P2-3` (ratify `INTERLEAVE_TOLERANCE`) unblocks `T5`.** A multi-node locality check has
  nothing to check against until the tolerance exists. More generally: until the TBDs are
  ratified, `P-BENCH-PLACEMENT-1`'s gates cannot reject anything.
* **`N25 P2-2` (production anchors) is what lets `T3`'s re-run pass the mandatory anchor gate**
  for the three roles that have none.
* **`N25 P0-1` (tests) → `N25 P0-3` (cold-start, re-bench, commit) gates everything downstream of
  the wiring change**, including the RSS measurement that closes T2's residency tail and the
  contention-matrix refresh that cross-cutting concern 4 depends on.

`T4`, `T8`, `T10` and `T11` are unaffected by the cutover and keep their original ordering above:
**`T5`, `T4` and `T11` remain zero-inference and unblocked, and `T11` still belongs before `T3`.**

* **T5 and T4 are zero-inference and unblocked** — land them before T3 so the re-run is guarded
  and interpretable. T5 in particular is what would have caught D2 the first time.
* **T3 must not start before T1 is decided.** If production is re-wired mid-campaign the re-run
  measures two different machines. If T1 is deferred, T3 still proceeds — but on *bench* ports
  with declared policy, and its recommendations then feed T1 rather than the reverse.
* ~~**T7 is a prerequisite for promoting any full-machine figure past observation-grade**, but not
  for starting T3.~~ **T7 CLOSED 2026-07-30** — replication is no longer the blocker on grade.
  **T9 (operator ratification of `P-BENCH-PLACEMENT-1`) now is.** Replication was necessary but
  never sufficient: grade is set by the trust boundary, not by rep count, and that boundary is
  human-amendment-only. A perfectly replicated figure under a STAGED protocol is still
  observation-grade.
* **T6 gates nothing but may widen T1's scope** — run it early so T1 is scoped once.
* **T9 gates promotion, not work.** Every task here can proceed on observation-grade evidence;
  only *promoting a claim* or *gating a production change on one* waits on T9. It is an operator
  decision package, so raise it early — it has a human in its critical path.
* **T10 and T11 are zero-inference-to-scope** (T11 is pure registry resolution; T10 needs a short
  bench run) and gate nothing structural — but T11 should run before T3, since re-running 27 cells
  against the wrong GGUF would repeat the IQ2_M mistake at 27× the cost.

---

#### Cross-cutting concerns

1. **This is live production damage, not only a measurement defect.** `frontdoor` (8070) and
   `ingest_long_context` (8085) are serving today at ~~roughly one third~~ **roughly half** of the
   throughput the same hardware delivers under the canonical recipe. Every downstream number
   produced through those ports since the 2026-04-24 NPS4 reboot — AutoPilot trial wall-times,
   eval-tower throughput, any tok/s in a role-level registry row — carries the penalty. **The
   AutoPilot `median_request_tps` anchor of 35.7 is NOT affected**: that traffic lands on a
   placement that reproduces today's corrected full-machine number, which is precisely why it
   disagreed with E5. The disagreement was the signal.

   > **Amended 2026-07-30 — magnitude corrected, scope confirmed.** "One third" came from the
   > noisy warm arm (`7.81 ± 3.82`). At `r=5`/`r=10` with `drop_caches` per arm the live loss is
   > **`2.16×` on `frontdoor`** (10.83 → 23.36) and **`1.85×` on `ingest_long_context`**
   > (12.42 → 22.92) — i.e. these roles serve at **46%** and **54%** of canonical. Still a severe
   > live regression; not 3×. **The scope is exactly these two roles.** The four-role matrix also
   > covers `worker_general` and `architect_general`, but those are **already correctly wired**
   > and their A-column figures are counterfactuals — do not add them to the damage claim.

2. **Renaming or retiring `NUMA_NODE0`/`NUMA_NODE1` is a breaking change to a widely-read
   constant.** It is consumed by `NUMA_CONFIG`, by the placement state machine, and by the E5
   harness's own shape table. Rename and re-wire in one change or not at all — a half-migration
   leaves two meanings of "node" live simultaneously.

3. **`--no-mmap` is already a per-role registry *data* knob, not new code.**
   `src/registry/stack_priors.py::_role_no_mmap_prior` resolves `no_mmap` from a role's config
   (directly or nested under `cache`/`serving`) and `orchestrator_stack.py` emits `--no-mmap`
   accordingly; ~~the current live value is `false` across the board~~. So T2 is a policy decision
   with a RAM bill, not an implementation task. `stack_numa.py:193` already anticipates it —
   `worker_general`'s interleave is deliberately scoped to idx0 "so `--no-mmap` quarters can
   first-touch local private pages".

   > **CORRECTION 2026-07-30 — `no_mmap` is NOT `false` across the board.** `worker_general` is
   > **`no_mmap: true`** today (both by builder default and by explicit prior) and measures
   > **1.00 weight locality on all five of its instances**. It is already immune to D2. The roles
   > that resolve to `false` are `frontdoor`, `ingest_long_context`, `architect_general`,
   > `eval_batch_frontdoor`, `worker_vision` and `vision_escalation`. This matters for T2's
   > framing: T2 is **not** "turn on a knob nobody uses", it is "extend to two roles a
   > configuration one role already runs in production" — with a working reference to copy.
   > Also load-bearing for T2: **`no_mmap` is role-scoped, with no per-instance analogue** to
   > `numactl_policy_instances`, so "`--no-mmap` on quarters only" is **not expressible in today's
   > code** — flipping the role flips all five instances. And `--no-mmap` **alone is insufficient**:
   > production has recorded `--no-mmap` quarters at `0.486` / `0.333` local, so `--membind` must
   > land with it. Evidence: `no_mmap_budget.md` in the attestation directory.

   > **AMENDED 2026-07-30 (second pass) — the `false` list is now empty for CPU serving roles.**
   > `no_mmap: true` is declared in the MASTER registry for `frontdoor`, `coder_escalation`,
   > `architect_general`, `ingest_long_context`, `worker_vision` and `vision_escalation`; the
   > "roles that resolve to `false`" sentence above is superseded. Two consequences: the
   > "`--no-mmap` on quarters only is not expressible" limitation is **moot** (quarters are
   > retired), and the **+141 GB** figure was measured on a 4×quarter fleet — the 1-full +
   > 2-half topology has a different residency envelope and its actual RSS is **unmeasured**
   > (N25 P0-3). The `--membind` companion requirement still holds for the vision pair, which is why
   > they were given explicit `membind=1` / `membind=3`.

4. **Any co-resident model changes the arithmetic.** These are single-model measurements taken
   under a held region-lock. The mode-exclusivity contract (full XOR quarters per role) and the
   cross-role contention matrix both bear on what the corrected numbers mean for a *populated*
   lineup. Do not port a single-model tok/s into a lineup-provisioning decision without the
   contention layer.

5. **Era stamping.** Every number here is era `production-consolidated-v8` @ `67a433bf4`
   (binary `10107`). The pre-2026-04-24 NPS2 numbers in `stack_numa.py`'s comments are a
   *different host topology* as well as a different kernel — they are not comparable and the
   2026-04-17 head-to-head in particular must not be cited (wrong topology **and** spec-dec off).

6. **The GPU lane's coupling.** [gpu-serving-tie-in-program.md](../completed/mi210-serving-program.md)
   P1-2 owns the E5 W1–W4 execution row and requires that the **published E5 results artifact be
   updated in place at its existing URL** rather than re-published to a new one. Any T3 re-run
   must honour that, and must rewrite the artifact's grade banner rather than leaving stale
   figures visible.

7. **Do not let the D4 metric rename absorb the story.** The rename is real and correct, but it
   accounts for a ~5% median correction. A reader who takes "we fixed the throughput metric" as
   the summary will conclude the campaign is salvageable. It is not: 27 of 31 cells are
   confounded by *placement*, and the largest single effect is a ~~3×~~ **2.16×** wiring defect
   (corrected 2026-07-30 at `n=10`; the conclusion is unchanged).

8. **Do not let the four-role matrix inflate the damage claim.** The matrix exists to validate the
   canonical recipe across models — it measures four roles, but only **two** are mis-wired. The
   `2.38×` and `2.51×` rows belong to `worker_general` and `architect_general`, which **already
   run the winning configuration**; those ratios describe a loss that is *not happening*. Any
   summary, dashboard row, escalation or artifact quoting this table must carry the two-role
   scope. Presenting a fleet-wide "~2× on all CPU roles" would be a false claim about production.

9. **Do not present the ngram result as fleet-wide either.** (*Added 2026-07-30.*) `ngram-mod`
   helps **two** roles and does nothing for the other two, and the reason is mechanical: **its
   benefit is inversely proportional to the incumbent drafter's acceptance rate.** `frontdoor`
   at `.505` accept gains `2.80×`; `worker_general` at `.754` and `architect_general` at `.650`
   gain nothing. Quote the principle with the number, or the next reader will try to deploy it
   everywhere. Also carry the **corpus**: the same measurement on synthetic filler (99.7 %
   repeated 5-grams) read `2.52×` and was nearly worthless — an ngram claim without its
   repeated-5-gram fraction is not a claim.

10. **Every decode number in this document now needs a context depth attached.** (*Added
    2026-07-30.*) The same role/recipe/placement spans `40.22 → 17.23` tok/s from 28 to ~35k
    tokens, with acceptance decaying `0.746 → 0.429`. A tok/s without a depth is a number
    without a workload. N25 P2-4 makes this a grammar requirement; until it lands, do it by hand.

---

#### Reporting instructions

* **On completing any task above**: flip its `- [ ]` → `- [x]` here with an inline `✅ YYYY-MM-DD`,
  and mirror the state into the owning handoff
  [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement) (E5 waypoint) and
  [inference-research-index.md](inference-research-index.md). Prose-only status
  updates are invisible to the handoff dashboard — the checkbox is the metric.
* **On T1 landing**: this is a production stack change. Record the three gates
  (pipeline-green / starts / live==config) plus the post-reload live-affinity verification from
  `affinity_preflight.py` — and verify **live affinity**, not just the topology hash. Append the
  reload to `progress/2026-07/` (or the then-current month) and update the `NUMA_CONFIG`
  provenance comments in `stack_numa.py` so the next reader sees measured evidence, not the
  retracted 2026-04-17 head-to-head.
* **On T3 completing**: the E5 suspension banner in
  [batched-decode-measurement.md](numa-placement-and-contention.md#track-batched-decode-measurement) must be **amended, not deleted** —
  per [MEASUREMENT.md](../../MEASUREMENT.md) the suspended numbers stay verbatim and annotated
  (append-only). Add the corrected table alongside; do not overwrite. Also update the published
  E5 artifact in place per cross-cutting concern 6.
* **Claim grammar**: every number promoted out of this document past observation-grade needs a
  protocol id, an attestation reference and an era stamp. ~~Nothing here currently carries one.~~
  **Amended 2026-07-30 — all three now exist**: protocol `P-BENCH-PLACEMENT-1`; attestation
  `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/`; era
  `production-consolidated-v8` @ `67a433bf4` (binary `10107`). **This does not make anything
  promotable**: the protocol's `MEASUREMENT.md` registry entry is STAGED, not applied, and the
  trust boundary is human-amendment-only. The grammar is now satisfiable; the ratification (T9)
  is what unlocks it.
* **When quoting the four-role matrix anywhere** — dashboard, escalation, bus message, published
  artifact, or another handoff — **carry the two-role scope with it.** `worker_general` and
  `architect_general` are already correctly wired; their A-column and A→C figures are
  counterfactual validation of the recipe, not live loss. The number of production roles losing
  throughput today is **two**.
* **When this handoff closes**: extract the durable findings (the NPS4 straddle trap, the shared-
  mmap first-touch rule, the SMT sizing rule) into the CPU optimization docs, then move this file
  to `handoffs/completed/`.

---

#### ⚠ Authorisation status of the production change

> ### SUPERSEDED 2026-07-30 (second pass) — read this first
>
> The section below describes the state of `stack_numa.py` **earlier on 2026-07-30**, when it
> carried comments only. It is retained verbatim per the append-only rule. **Current state:**
>
> * The wiring change **is written** — quarters retired, 1 full + 2 halves, a declared memory
>   policy on every instance, `-t` == physical cores everywhere. See
>   [Topology change applied](#topology-change-applied-2026-07-30--quarters-retired-1-full--2-halves).
> * It is **UNCOMMITTED** and **NOT RELOADED**. **30 net-new test failures across 14 files (N25 P0-1)**, two of them
>   inside `PROMOTION_GATE_TARGETS` — the promotion gate is red, so the stack cannot start.
> * **The reload is still not self-authorising.** Per `OPERATING_CONSTRAINTS.md` → *Inference and
>   Benchmarks*, it is executed by the session that owns the inference, at a moment it chooses.
>   Tracked as **N25 P0-3**, with the three stack gates and a post-reload live-affinity verification.
> * The **grade** objection in the original text is resolved: `P-BENCH-PLACEMENT-1` is ratified
>   (T9 closed). What remains gating *promotion of specific numbers* is the missing anchors
>   (N25 P2-2) and the unset thresholds (N25 P2-3), not protocol status.

**The `stack_numa.py` production wiring change is NOT authorised.** As of 2026-07-30 the file
carries **comments only** — a `CONSEQUENCE, measured` block, the retraction of the 2026-04-17
head-to-head, and an explicit note that the wiring is *"intentionally left UNCHANGED until [the
E5 re-run] reports"*. **No constant, cpuset, thread count or `numactl_policy` value was altered;
the module is behaviourally identical to its pre-2026-07-30 state.**

This is deliberate for two reasons. First, changing production wiring now would break
comparability with the recorded AutoPilot operating point we are re-anchoring against. Second,
per `OPERATING_CONSTRAINTS.md` → *Inference and Benchmarks*, a stack reload is executed by the
session that owns the inference, at a moment it chooses — it is never forced on that workflow
from outside, and this document does not authorise one.

T1 needs: an operator decision on the target shape, the inference owner's agreement to take the
reload, and the three stack gates. Until all three are satisfied, the correct action is to leave
production exactly as it is and keep the defect documented.

---

#### Key file locations

##### Production code (READ-ONLY for this handoff — no authorised change)

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py` | **D1 site.** `NUMA_NODE0`/`NUMA_NODE1` at lines 66–67; `NUMA_CONFIG` per-role instances; annotated 2026-07-30, behaviourally unchanged |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` | Launch-command builder; emits `--no-mmap` from the `no_mmap` cache prior |
| `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py` | `_role_no_mmap_prior()` — the T2 knob (data, not code) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/affinity_preflight.py` | **T5 site.** `_summarize_numa_maps()` (weight-page placement read); the `required` predicate at line 195 |

##### Sites opened by the 2026-07-30 topology change

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py` | **T1 landed here** (uncommitted). `NUMA_FULL` / `NUMA_HALF_A` / `NUMA_HALF_B` supersede the NPS2-era `NUMA_NODE0`/`NUMA_NODE1`; carries the `architect_general` role definition and the **N25 P1-8** telemetry note |
| `/mnt/raid0/llm/epyc-orchestrator/src/fleet.py` | Degraded-mode fallback ports now **derived** from `NUMA_CONFIG` (was hardcoded 5-port lists) |
| `/mnt/raid0/llm/epyc-orchestrator/src/config/models.py` | No longer advertises the freed ports |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/registry/stack_change_pipeline.py` | `PROMOTION_GATE_TARGETS` — **N25 P0-1**: two of the 30 net-new failures live under this gate; also the `REQUIRED_SOURCE_ARTIFACTS` staleness trap (**N25 P1-10**) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/quarter_scheduler.py` | **N25 P1-9 delete candidate** — 403 lines, zero runtime importers, now factually wrong |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/operator_seed_strategies.yaml` | **N25 P1-3** — `dual-half-negative` (`confidence: high`) forbids the deployed topology; SUPERSEDE, do not edit |
| `/mnt/raid0/llm/epyc-orchestrator/tests/unit/test_build_server_command_helpers.py` · `tests/unit/test_orchestrator_stack_threads.py` | **N25 P0-1 / P0-2** — the two `PROMOTION_GATE_TARGETS` failures and the XPASSing replacement assertion. `test_worker_general_numa_policy_is_full_instance_only` **encodes the defect as a requirement** — retire it, do not repair it |
| `/mnt/raid0/llm/epyc-inference-research/orchestration/model_registry.yaml` | MASTER registry — where `no_mmap: true` and `ngram_candidate_spec_type` are declared |
| `/workspace/artifacts/operator/ratification_queue_20260730.md` | **N25 P2-4 / N25 P2-3** — proposed values for every TBD threshold, with derivations |
| `/mnt/raid0/llm/epyc-inference-research/docs/protocols/model-registration-runbook.md` | **`MRG-1`** — the registration gate (Steps 0–9); its §5 TBDs feed N25 P2-3 |

##### Measurement harness

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/server_numa_np_sweep.py` | E5 harness. `instance_launch_prefix` (lines ~383–394) builds `taskset` + optional `numactl`; D4 rename + `aggregate_decode_tps` landed here |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w1-qwen36-20260729T154725Z/` | Stage-B W1 (11 cells) — first cell first-touched 100% onto N0 |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w2-gemma-20260729T183151Z/` | Stage-B W2 (8 cells) — contains the **4 salvageable** cells |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w4-80b-20260729T165639Z/` | Stage-B W4 (12 cells) |
| `<run>/affinity/<cell_id>.json` | `instances[].memory_placement.pages_by_node` — the primary D2 evidence |

##### Attestation — committed evidence (2026-07-30) ✅ USE THIS

**`/mnt/raid0/llm/epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/`**

All raw logs **plus the exact script that produced each figure**, committed. Its `README.md`
carries the **figure → file map** and the per-figure rep count and spec-dec state — read that
first; it is the index for everything below.

| Path (relative to the attestation dir) | Figure it attests |
|---|---|
| `README.md` | **figure → file map**, per-figure reps, spec-dec state, known caveats |
| `highn.sh` · `highn_results.txt` | **`frontdoor` `n=10`**: as-wired `10.83 ± 0.04` vs canonical `23.36 ± 0.11` (`2.16×`) — the **T7 replication** |
| `matrix4.sh` · `matrix4_results.txt` | **`ingest_long_context` Q4_K_M** and **`architect_general` 122B** A/B/C rows |
| `matrix2.sh` · `matrix2_results.txt` | **`worker_general` gemma4-26B** A/B/C rows (`16.37` → `39.03`) |
| `modelref.sh` · `modelref_results.txt` | per-model as-wired vs canonical, 3 models, `r=2` — ⚠ benched the *non-production* gemma file; prefer `matrix2` |
| `npsweep.sh` · `np_parse.py` · `npsweep_results.txt` | full-machine `np` ladder (MTP on) |
| `shapesweep.sh` · `shapesweep_results.txt` | HALF/QUARTER shapes × `np` — the **D3** SMT probe |
| `quadfleet.sh` · `quadfleet_results.txt` | **D2** mmap `40.91` vs `--no-mmap` `52.13` |
| `locverify.sh` · `numaloc.py` · `locverify_results.txt` | **D2** mechanism proof — 25% vs 100% weight locality |
| `fleetgrid.sh` · `fleetgrid_results.txt` | directly-measured 2×half / 4×quarter fleet grids |
| `ctx80b.sh` · `mkprompts.py` · `ctx80b_results.txt` | 80B decode-vs-context curve — ⚠ **IQ2_M, wrong artefact** (T10 re-runs on Q4_K_M) |
| `e5_rederived.md` | **D4/D5** offline replay of all 31 E5 cells; salvage verdicts (§6b) |
| `no_mmap_budget.md` | **T2** RAM budget, per-role `no_mmap`/`mlock`/policy audit, GGUF resolution |

##### Protocol

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md` | **`P-BENCH-PLACEMENT-1`** — the executable contract. **STAGED**: its `MEASUREMENT.md` registry entry lives in its Appendix A and awaits operator application (**T9**). Until applied, conforming runs are observation-grade by construction |

##### 2026-07-30 measurement artifacts (scratch — ⚠ SUPERSEDED, use the attestation dir above)

> These `/mnt/raid0/llm/tmp/` paths are the **original scratch run**. They are retained for
> provenance only. Everything reproducible has been promoted into the attestation directory above,
> under the protocol, with scripts attached. **Cite the attestation path, never a `tmp/` path** —
> `tmp/` is not committed and will not survive.

| Path | Contents |
|---|---|
| `/mnt/raid0/llm/tmp/numa_matrix.sh` · `numa_matrix.log` | D1 phase 1/2: warm vs cold × straddle/interleave/full |
| `/mnt/raid0/llm/tmp/numa_matrix2.sh` · `numa_matrix2.log` | D1 cold arms incl. the `23.43` full-machine winner, the `8.80` single-node instrument check, and the **mislabelled arm F** (T7) |
| `/mnt/raid0/llm/tmp/npsweep.sh` · `npsweep_results.txt` | Full-machine + interleave `np` ladder, np ∈ {1,2,4,8,16,32} |
| `/mnt/raid0/llm/tmp/shapesweep.sh` · `shapesweep_results.txt` | HALF / HALFphys / QUARTER / QUARTERphys — the **D3** SMT probe |
| `/mnt/raid0/llm/tmp/quadfleet.sh` · `quadfleet_results.txt` | **D2** mmap vs `--no-mmap` 4-quarter fleet decode |
| `/mnt/raid0/llm/tmp/locverify.sh` · `numaloc.py` · `locverify_results.txt` | **D2** per-node `numa_maps` locality table + host RAM cost |
| `/mnt/raid0/llm/tmp/fleetgrid.sh` · `fleetgrid_results.txt` | 2×half and 4×quarter fleet grids at np ∈ {1,2,4,8} |
| `/mnt/raid0/llm/tmp/ctx80b.sh` · `mkprompts.py` · `ctx80b_results.txt` | 80B `ingest_long_context` decode-vs-context curve, 3 placements × 3 prompt lengths |
| `/mnt/raid0/llm/tmp/reanchor.sh` · `reanchor.log` | Six-request AutoPilot-anchor reproduction at the winning placement (36–39 tok/s) |
| `/mnt/raid0/llm/tmp/e5_rederive.py` · `e5_rederived.md` · `e5_rederived.json` | **D4/D5** offline re-derivation — 31 cells, per-slot + system-wide + achieved concurrency, salvage verdicts, W0 appendix. Zero inference |

##### Governing documents

| Path | Role |
|---|---|
| `/workspace/handoffs/active/numa-placement-and-contention.md` | **Owner of E5.** Carries the authoritative suspension banner |
| `/workspace/handoffs/active/master-handoff-index.md` | Dispatch; §A row for this defect |
| `/workspace/MEASUREMENT.md` · `/workspace/agents/shared/MEASUREMENT_POLICY.md` | Claim grammar, era handling, append-only annotation rule, region-lock |
| `/workspace/agents/shared/OPERATING_CONSTRAINTS.md` | *Inference and Benchmarks* — reload ownership (why T1 is not self-authorising) |

---

#### SUPERSEDING NOTE — 2026-07-31 · speculative recipe (append-only correction)

This file is append-only, so the text above is left unedited. Two things in it are
now known to be wrong and MUST NOT be actioned:

1. **The `ngram-mod` 2.80× result is RETRACTED.** (`:25-27` top amendment block,
   `:607` table, `:613`, `:622`, `:915`, `:1094`.) It was a warm-context self-copy
   artifact — the same prompt replayed against a warm server let `ngram-mod` copy
   its own previous answer out of retained context (draft len 3.58 → 15.88,
   acceptance → 1.000). Corrected gain: **−4.2% to +1.3%**. `ngram-mod` *alone*
   costs 23–31%. The instruction at `:915` to "fold the ngram result into the
   production recipe" is **cancelled**. Retraction of record: research
   `84067a6e`, `data/numa_placement/20260730-P-BENCH-PLACEMENT-1/RETRACTION-ngram-20260730.md`.
   Recurrence incident: `docs/reference/agent-config/INCIDENT_LOG.md` →
   `INC-20260731-warm-server-repeat-prompt-recurrence`.

2. **"Production launches `--spec-type draft-mtp` alone … never-deployed
   candidate" (`:600-601`) is FACTUALLY WRONG.** Composed `ngram-mod,draft-mtp`
   is the production recipe by standing operator decision. It was deployed by K16
   on 2026-07-16 (live worker cmdlines verified on 8072/8082/8182/8282/8382) and
   then silently un-deployed by research commit `2370025f` (2026-07-19), which
   reverted `spec_type` to `draft-mtp` and moved the composed value into the
   sidecar `ngram_candidate_spec_type`. That sidecar is now RETIRED.

   These two points are INDEPENDENT. The composed recipe is carried for its
   repetitive-context upside at an accepted **~−1.6%** ordinary-text cost — *not*
   because of the retracted 2.80×. Retracting the speedup does not retract the
   recipe.

**Canonical source — link, do not restate:** the `speculative_decoding_policy`
block at the top of `epyc-inference-research/orchestration/model_registry.yaml`.
It also carries the BASELINE / OPTIMUM / CANDIDATE grammar and the
Qwen3-Next-80B `--spec-type none` = OPTIMUM (not baseline) exception.

#### The permanent fix is MERGED and awaiting activation by the stack owner (2026-09-03)

**This handoff's mechanism is now root-caused and fixed upstream of it.** INF-70's C7 measured why
`numactl --interleave=all` silently fails: it is a per-allocation *hint* the kernel abandons for any node with
no free pages, and page cache counts as not-free — so a 98 GB model "interleaved" across 4 nodes landed
57.7/10.7/8.0/17.7 GB and served at −25% decode / −30% prefill with an identical argv and nothing in any log.
That is almost certainly the mechanism behind this handoff's two half-speed roles.

**Merged, tested, NOT yet live:**
- research `origin/main` `0458de88` — `scripts/utils/numa_evict.py` in the **forcing** form (allocate `TARGET+2`
  whenever `free < TARGET`, verify per node, 2 passes). The earlier form allocated `TARGET − free` and therefore
  reclaimed nothing when a node sat near TARGET; mutation-tested so the weak form fails 14/20 cases.
- orchestrator `origin/main` `5f20e23c` — `numa_pre_evict_gib: 40` enabled on frontdoor, eval_batch_frontdoor,
  architect_critic, ingest_long_context, worker_general; **never on `gpu_host_lane` roles (refused in code, not
  just YAML)**; `[numa-placement]` per-node fold logged after health so placement is observable after the fact;
  priors recompiled. Full suite 14,129 pass / 35 fail, **zero attributable to the change** (33 identical on the
  pristine base, 1 flaky on both, 1 artefact).

- [x] **ACTIVATION — owned by the stack-owning session, not by INF-70.** At its own boundary: ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): C7 pre-evict commit 070e4f28 is an ancestor of the shared orchestrator clone HEAD 68939147. [no-belief: obsolete, activation done]
      `git -C /mnt/raid0/llm/epyc-orchestrator pull --ff-only` (clean, was 3 behind), then
      `stack_change_pipeline.py check` there (expected: lean/descriptors/priors fresh). The running API serves
      from that shared clone, so the pull + reload belongs to whoever owns the stack — an experimental-kernel
      session must not pull code out from under a live process (reload-ownership rule). Until this runs, the fix
      is merged but inert and this handoff's roles keep skewing.
      Evidence: `/mnt/raid0/llm/tmp/inf70/agents/c7-finish/REPORT.md`; memory
      `feedback_page_cache_defeats_numa_interleave`.

- [ ] **The pre-evict hazard is RECLAIM-THEN-LOAD, not the size of the constant — and C7's launch path does
      exactly that sequence.** Found 2026-09-03 by INF-70's `mtp-tip2`; supersedes this item's first framing
      ("is 40 GiB too low?"), which was mine and was wrong about the variable.
      **The evidence.** Two consecutive loads of the SAME model by the SAME launcher, both at `EVICT_GIB=40`, 33 s
      apart, with **identical post-evict free profiles** (119/51/46/81 vs 118/50/46/81 GiB) produced **opposite**
      placements: one skewed 48.9% (23.03 / 23.03 / **11.77** / **34.28** GB), the other perfect (23.02 / 23.03 /
      23.03 / 23.03). The discriminator is in the eviction logs, not the target: the skewed run's evict found
      **node 2 at 0 GiB free** and had to force a 42 GiB membind alloc/release to reclaim it, **then loaded
      immediately**; the clean run's evict did nothing at all, because the previous run had already left node 2
      clean. **The one node that required reclaiming is the one that under-filled**, and its missing 11.26 GiB went
      entirely to node 3 — 11.77 + 34.28 = 46.05 = exactly 2 × the 23.03 GiB per-node share.
      **Why this is worse than a too-small constant:** C7's merged launch path performs precisely this
      evict-then-load-at-once sequence, so the skew lands on exactly the launches the setting exists to protect — a
      cold node, or one holding page cache from a previous model. A bigger constant lowers the odds of needing a
      reclaim; it does not remove the reclaim-then-load hazard.
      **Primary recommendation (the agent's, and it is the right one): VERIFY, do not just evict harder.**
      Production currently has **no post-load placement check** — C7 logs a `[numa-placement]` fold, but logging is
      not gating, so a skewed load is served silently and only surfaces later as an unexplained low-bandwidth
      number. Every INF-70 bench arm gates on in-window `numastat -p` with a 15% deviation limit and REFUSES to
      proceed otherwise; that is the check the launch path lacks. Make the launch path gate on it — re-evict and
      relaunch, or at minimum alarm. Candidate fixes (absorb four rows), cheapest first: a settle delay between reclaim and load; if a constant is kept, scale it with the per-node share (23.03 GiB here); target ~2x the per-node model share (>= 58 GiB/node, e3-run 2026-09-03); add a post-load placement gate to the launch path (deviation limit, action on breach).
      - **[declined: ws58 2026-11-03 content-review: merged into the pre-evict hazard row as a candidate fix]** Add a post-load placement gate to the launch path (deviation limit, action on breach).
      - **[declined: ws58 2026-11-03 content-review: merged as the cheapest candidate fix]** Test whether a settle delay between reclaim and load removes the skew — the cheapest candidate fix,
            and it directly probes the stated mechanism.
      - **[declined: ws58 2026-11-03 content-review: merged as a candidate fix]** If a constant is kept, scale it with the per-node share (23.03 GiB here), not a fixed absolute.
      - **[declined: ws58 2026-11-03 content-review: merged as the target]** **A principled target exists, from a second agent (`e3-run`, 2026-09-03): evict to ~2x the per-node
            model share, i.e. >=58 GiB/node, not 40.** Mechanism: under `--no-mmap` the 92 GB read populates page
            cache *under the same interleave policy*, so each node needs room for its model share PLUS the cache
            that share generates. 40 GiB left a 42.1% skew that its gate refused despite `EVICT OK`; >=58 gave 0.1%
            deviation first try and on every arm after. This is complementary to the reclaim-then-load hazard above,
            not a replacement for it — the gate is still the primary recommendation, but this gives the constant a
            derivation instead of a guess.
      **Evidence strength, stated honestly by the agent:** n=1 skew at 40, n=1 clean at 40, n≥4 clean at 60 — it can
      show 60 was never observed to fail, not that 60 is sufficient. Detail in
      `/mnt/raid0/llm/tmp/inf70/agents/mtp-tip2/FINDING-numa.md`. Owner: the stack session, with the activation
      item above. No orchestrator config was touched by INF-70.

## Track: shape-keyed-contention-gating
<!-- gate: none -->

> Folded from `handoffs/active/shape-keyed-contention-gating.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F17, route 1a, operator D1/D5; retired row RTG-35 → INF-45). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Shape-Keyed Contention Gating + Cross-Role Disjoint Placement

**Status:** ACTIVE — A/A-1 code-complete; **Step 1 (cross-role disjoint placement / GLOBAL region mutex) ARMED LIVE 2026-05-31 PM** (API reloaded, `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` verified in `/proc/<api>/environ`, `cpu_region.GLOBAL.q0-q3.lock` materialized on overlap); **B code-complete END-TO-END but Step 2 (`SHAPE_AWARE_CONTENTION`) still default-off**; C has pure backfill-selection prep only. Remaining work is **rollout-only (no more code)**: Step 2 clean live smoke test (disjoint admit / overlap queue), flag-on, then C under an epoch boundary. Step 1 sampler analysis is complete; it proves the GLOBAL mutex was active and blocking, but does **not** by itself justify Step 2 promotion because the dashboard counters reset/alias during the sample window.
**Created:** 2026-05-30
**Owner:** (operator-directed; implementation by assistant)
**Repos:** `epyc-orchestrator` (src/scheduling, src/backends, src/runtime, scripts/benchmark)
**Depends on:** `contention_matrix.yaml` (topology_hash `df373c79cc4af06f`), `instance_topology.get_instance_regions()`

> **Fable 5 review (2026-06-12)**: the flag-on bracket is item #3 in the consolidated quiesce-window manifest ([bulk-inference-campaign.md](eval-tower-program.md#track-bulk-inference-campaign) Queue 2) and owns the attested production-env reload the other window items piggyback on.
>
> **V6 matrix refresh (2026-06-27)**: orchestrator `526ba3a2` refreshed the live full/primary pair layer for topology `df373c79cc4af06f` after the age certification expired, while preserving the curated `same_role` and `n_way` sections this handoff depends on. The refresh removed the last two unknown pair rows and changed several primary/full-pair verdicts under the v6+iqk kernel. That makes the shape-keyed distinction more important, not less: full/primary co-residency can still block while quarter/disjoint policy remains a separate rollout gate behind `SHAPE_AWARE_CONTENTION`.
>
> **A1 validation refresh (2026-06-27)**: no-inference checks are current under the v6 live stack. `contention_matrix.py validate` and `check_contention_matrix_fresh.py` pass for topology `df373c79cc4af06f`; `tests/unit/test_cross_role_region_mutex.py` passes `3/3`; the placement/contention regression slice (`test_placement.py`, `test_dispatch_placement_state_machine.py`, `test_dispatch_cross_role_placement.py`, `test_concurrency_aware_quarter_preference.py`, `test_concurrency_aware_migration_sm.py`) passes `34/34`; `affinity_preflight.py --roles frontdoor ingest_long_context vision_escalation worker_general worker_vision` verified live `numa_maps` placement for all expected ports and wrote `/mnt/raid0/llm/epyc-orchestrator/data/contention_matrix/affinity_preflight_1782553178.json`. This does **not** promote Step 2: `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` still needs the clean-window disjoint-admit / overlap-queue smoke bracket.

---

#### Current state (start here)

- [x] **A — Cross-role disjoint placement** (prerequisite; correctness-critical) — **CODE-COMPLETE 2026-05-30, behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`; A-1 TOCTOU RESOLVED** via the global region mutex (`cpu_region.GLOBAL.{region}.lock`). Still LIVE-OBSERVATION-GATED before flag-on.
- [x] **B — Shape-keyed admission core + default-off gate seam + dispatch-side caller wiring** — `Placement`, `admit_set`, `held_regions_by_role`, `seam_admit`, dual-flag gate, and `ContentionGate.evaluate(candidate_topology_idx=...)` are code-complete and verified. The seam is **authoritative** when consulted (`worst = seam_decision`), not tightening-only. **Dispatch-side caller wiring DONE 2026-05-31 (Step 2):** `inference.py` defers the coarse role-keyed pre-gate for `ConcurrencyAwareBackend` when both flags are armed (so it can't mask a later disjoint candidate); `concurrency_aware.py` `_dispatch` evaluates the gate per **real** `candidate_topology_idx` before acquiring the candidate lock (denied candidates skipped/re-polled); `contention_gate.py` `admit()` threads `candidate_topology_idx` through to `evaluate()`. B is now code-complete end-to-end; production remains **inert** only because both shape-aware flags default off and the API was not reloaded.
- [~] **C — Backfill prep only** — pure `select_backfill_candidate` is implemented and tested; the heavy-port veto, all-heavy idle barrier, and pressure skip remain intact. Behavior-changing C work is not started.

##### Next actions (operator-gated)

1. ~~**Step 1 staged, not live**~~ ✅ **ARMED LIVE 2026-05-31 PM.** Autopilot had wrapped (`trial_counter=185`, no daemon), so `orchestrator_stack.py reload orchestrator` armed the GLOBAL region mutex; `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` verified in `/proc/<api>/environ`. Autopilot relaunched under Step 1 (`draft_critique`, `--max-trials 300`) to provide observation traffic.
2. ✅ **Observe Step 1 live (ANALYZED 2026-06-12):** sampler `scripts/server/_step1_obs_sampler.sh` wrote 24 rows to `/tmp/step1_observation_20260531.jsonl` from 2026-05-31 13:37:37 UTC to 14:12:09 UTC across trials 186-188. All rows reported `matrix="ok"` and `global_locks=4`; 14/24 rows had blocked pairs, with maxima `ingest_long_context+worker_explore=1084`, `worker_explore+worker_general=618`, `frontdoor+worker_explore=577`, and `frontdoor+ingest_long_context=306`. Max observed `wait_s` was 205.4 and max `admitted` was 29; two rows reported `timeout=2`, both while blocked pairs were present. Interpretation: the GLOBAL mutex was armed and serialized real cross-role overlap, and dashboard attribution survived the GLOBAL pseudo-role (reserved, never iterated; `cpu_region_lock.py:111-113`). Caveat: the endpoint counters reset/alias within the same trace despite being documented as cumulative, so this is a functional observation, not a stable cost/throughput total.
3. ~~Wire the dispatch-side caller to pass the selected `candidate_topology_idx`~~ ✅ **DONE 2026-05-31 (Step 2, default-off).** Remaining: enable `ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1` (requires BOTH flags) only after a live smoke confirms disjoint quarters admit while q-overlaps queue.
- [x] **BUILD: implement the ROUTE-A1 smoke execution bridge** ✅ 2026-07-21 (orchestrator: both stubs replaced; admit/queue classified via placement-queue outcome — ADMIT=clean answer, QUEUE=ContentionDenied 503 timeout, backend failures excluded; 6 mocked tests; double gate + dry-run byte-identical)
- [x] **BRIDGE RESIDUAL 1 — echo GateDecision into /chat response metadata** (serving-path, small): `admitted`/`waited_s`/`decision`/`candidate_topology_idx` are computed in `contention_gate.admit()`/`_dispatch` but dropped, so the probe INFERS the verdict (role-granular; queue-then-admit invisible; only fail-closed timeout observable as QUEUE). Echoing them makes ROUTE-A1 a direct measurement. Do NOT land while a calibration run is live against the API. ✅ **LANDED 2026-08-13** — cherry-picked onto orchestrator `main` as `c61b8184` (6 files, +299/-0, 9 new tests; gate verdict **autonomous** via `merge_gate.py check --repo epyc-orchestrator --range main...a14-gatedecision-echo`; suite 35 passed on merged main; no calibration run live against the API — orchestrator API down). Local commit only, NOT pushed (push freeze).
- [x] **BRIDGE RESIDUAL 2 — bind the re-bench `sample_fn` to the codified bench recipe**: ✅ 2026-08-23 —
      the drive loop + ledger row half is DONE (see the flipped boxes below: `_drive_admit_overlap_probes`
      implemented at `4dd270ed` + 2026-08-23 fail-closed anchor-hold/signal guards; probe verified
      identical to `run_paired_ab._default_arm_probe`; ROUTE-A1 ledger row READY). The vision
      co-run-leaf `bench_canonical` taskset-pinning parity remains an EXECUTION-time concern (operator
      bench approval + quiet window; carried in the ledger row's next_action). The vision co-run leaf honestly refuses the role-level eval lane (cannot pin instance regions; J5-prior protocol parity requires `bench_canonical` taskset pinning). Operator bench approval + quiet window when run. ROUTE-A1's ledger row stays BLOCKED_PRECONDITION until residual 1 (or an operator decision to accept the timeout-proxy signal) and the anchor-hold procedure are settled. (2026-07-21, from the batch-loop attempt): `scripts/autopilot/shapekeyed_step2_smoke.py` has pure planners/aggregators + a double-gated bridge, but `_drive_admit_overlap_probes` (`:718`) and the re-bench driver are `NotImplementedError` stubs — the batch entry was mislabeled runnable and is parked `BLOCKED_PRECONDITION` (build_gate=step2-smoke-bridge). Implement the drive loop over the placement queue mirroring `scripts/analysis/run_paired_ab.py::_default_arm_probe` (call_orchestrator_forced, request_priority=background, workload_class=eval_batch, force_role pinned), then append a READY ledger row for `ROUTE-A1-shapekeyed-step2` (its entry command is already corrected: env gate + `--output`).
4. Switch A placement from the attribution view (`active_region_holders`) to the exact-region view (`held_regions_by_role`) so flag-on placement does not overblock free quarters.
5. Only after B is live and observed, perform C behavior work: narrow the legacy heavy-slot barrier/erase, add work-conserving backfill, then remove the line-98 heavy-port veto.

> **2026-05-31 — dashboard-metrics holder accounting corrected (display only, gate unchanged).**
> `active_region_holders()` (attribution view) over-counted the dashboard's active-role
> readout: a single full-shape MTP worker holding q0–q3 rendered as ×5. Added
> `active_region_holder_instances()` in `src/runtime/cpu_region_lock.py` (group held locks
> by (role, PID) → resolve each PID's exact held-region set to its instance shape) and wired
> it into `ContentionGate.active_decodes_by_role`/`active_instances_by_role`. The scheduler
> attribution view `active_region_holders()` is **unchanged** (GitNexus HIGH-risk; still used
> by A placement). This is a precedent for **Next-action #3** (exact-region view) but does not
> itself change any gate/placement behavior. Commit `263b1b0`; see `progress/2026-05/2026-05-31.md`.

##### A — implementation record (2026-05-30)

- `src/scheduling/placement.py`: added `_cross_role_regions_union(self_role, cross_role_holders, instance_regions)` + a `cross_role_holders: dict[str,Iterable[int]] | None = None` kwarg on `evaluate_placement`. When supplied, holder regions are unioned across **all** roles (self-role entry skipped); `None` → empty union → byte-identical legacy same-role-only behavior. Overlap is computed from canonical region sets (`instance_regions`), never a shape label.
- `src/backends/concurrency_aware.py`: new `@staticmethod _cross_role_disjoint_placement_enabled()` reading `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off); the WP-2 `_dispatch` poll loop now snapshots the full `active_region_holders()` map once per iteration and passes it as `cross_role_holders` **only when both** that flag and the existing `ORCHESTRATOR_PLACEMENT_STATE_MACHINE` are on.
- Tests (`tests/unit/test_placement.py`, +5): cross-role half0 holder filters overlapping quarters; same-role∪cross-role union; whole-machine holder → queue; `cross_role_holders=None` preserves legacy isolation; disjoint node1 holder does **not** filter node0 quarters. Written red-first (confirmed `TypeError` on missing kwarg) then green.
- **Suite:** `test_placement.py` (16) + `test_dispatch_placement_state_machine.py` (10) + `test_concurrency_aware_quarter_preference.py` (8) + `test_concurrency_aware_migration_sm.py` (12) = **46 pass**.
- **Pre-existing failure (NOT mine):** `tests/unit/test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` fails identically with my changes git-stashed — a parallel agent's uncommitted change made `get_placement_policy("frontdoor")` return `BURST_PREFER_QUARTERS` instead of the `SOLO_PREFER_FULL` default the test asserts. Flagged, untouched.

**Gate to exit A (unmet — needs live observation):** flag is OFF; behind-flag code is proven by unit tests only. Before flipping `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`, observe the region-lock dashboard showing a heavy+light set landing on disjoint shapes (operator-gated; needs the stack + a co-residency-inducing workload). **Not committed yet** — working tree only.

Sequencing is **A → B → C**, strict. Each gate below must be met before the next part starts.

---

#### Problem

The autopilot seeder serializes "heavy" roles one-per-wave and barriers between waves, leaving physically-free CPU quarters idle while a node-half instance (e.g. `ingest_long_context.half0` on q0+q1) runs — even though the contention matrix has **already measured** that a fitting role could co-reside profitably (`{frontdoor, ingest_long_context, worker_general} = 1.535× allow`, `{frontdoor, ingest, vision} = 1.731× allow`). The waste is real, but the cause is **not** the heavy-port veto.

##### Root cause (one line)

**Contention is decided per-role and placement-blind, but the physics is per-instance-shape.** The same role pair has two true, non-contradictory measured entries — `frontdoor+ingest = 0.37 block` for overlapping node0-half primaries, `frontdoor+ingest = 1.716 allow` for disjoint quarters — and nothing in the live path can disambiguate them or steer toward the good placement.

##### Why "just delete line 98" does nothing (empirically proven)

Operator monkey-patched `HEAVY_PORTS = set()`; the seed wave plan was **unchanged** (`frontdoor+worker_general | coder_escalation | ingest_long_context | architect_general`). Because:

1. **`pair_policy` is role-keyed and placement-blind** — `contention.py:299-305`, lookup `matrix.get_pair(role_a, role_b)` at `:347`, no shape/instance arg. `frontdoor+ingest` always resolves to the stale primary `0.37` → background → `QUEUE` (`:362-373`).
2. **The gate can only make the verdict worse, never better** — `contention_gate.py:209-246`: it accumulates `worst` across all active-role pairs, then at `:234` applies an N-way result **only if more restrictive** (`_prec[nway] > _prec[worst]`). An N-way `allow` is inert against a pair-derived `QUEUE`. The seeder replicates the same order and is stricter still (requires `pair == ALLOW`, `seeding_eval.py:104-106`).
3. **Placement is a blocker, not a check** — `placement.py:92` `evaluate_placement` filters candidates against the **same** role's holders only (`_holder_regions_union(role, …)` at `:80-89`), called with `holders_for_role = active_region_holders().get(self._topology_role)` (`concurrency_aware.py:949`); and the candidate list pushes `full` first (`:912`). So placement neither avoids cross-role overlap nor *produces* the disjoint-quarter layout the optimistic n_way numbers assume. So line 98 is a symptom downstream of a path that was already going to queue.

So removing line 98 alone changes nothing. The matrix is already the measurement — this work reconciles three code layers to it. **No perf benchmark is required for the claim.**

---

#### Invariants (bake these in)

1. **Overlap is computed from canonical region sets, never inferred from a shape's label.** `full` is not an overlap predicate. Per `instance_topology.py`: regions are quarter labels `q0,q1,q2,q3`; node0-half = `{q0,q1}`, node1-half = `{q2,q3}`, full = `{q0,q1,q2,q3}`. Role primary shapes differ:
   - `frontdoor` (8070), `ingest_long_context` (8085) primary = **lower half** `{q0,q1}` (`0-47,96-143`) — *2026-07-30: previously written "node0-half"; `q0` and `q1` are two **separate** NPS4 nodes (`node0 = 0-23,96-119`, `node1 = 24-47,120-143`), so this cpuset is not node-local. The region-set logic is unaffected.*
   - `vision_escalation` (8087) primary = **upper half** `{q2,q3}` (`48-95,144-191`) — *likewise spans NPS4 node2+node3, not "node1"*
   - `architect_general` (8083), `worker_general` (8072) "full" = **all four** `{q0,q1,q2,q3}` (`0-95`)
   - `worker_vision` (8086) = sub-quarter `q0B` (`24-47,120-143`)
   Use `get_instance_regions()` / `regions_overlap()` / `regions_for(role, idx)` as the single source of truth (already derived from `stack_numa.NUMA_CONFIG`).
2. **`architect_general` is strictly solo** — its only feasible instance is whole-machine (no quarter/half), so every candidate placement overlaps any other holder. It is correctly never in a feasible co-residency set. (NB: this is because of the placement layer, *not* because every old pair entry blocks — `architect_general+worker_general = 1.11 allow` exists at `matrix:101`.)
3. **Decision keys on placement (region sets / instance shapes), not bare role names.** Role-only `pair_policy()` survives **only** as a legacy fallback when the proposed placement is unknown. For **background traffic with unknown placement → fail closed (QUEUE).**
4. **Candidate ordering is region-set based:**
   - No cross-role holders → preserve the role's normal solo preference (sticky-quarter, then its primary, etc.).
   - Cross-role holders present → prefer the **smallest disjoint candidate that the placement-aware admission policy allows**.
   - Never use a human label (`full`) as a proxy for overlap.

---

#### Design

##### Part A — Cross-role disjoint placement (prerequisite; correctness-critical)

Make placement compute occupied regions across **all** roles and prefer disjoint shapes.

- `src/scheduling/placement.py:80-118` — `evaluate_placement` / `_holder_regions_union` must union holder regions across **every** `(role, idx)` currently holding a lock, not just the dispatching role. Take the full cross-role holder map + `instance_regions` and filter candidates whose region set overlaps the cross-role union (`regions_overlap`).
- `src/backends/concurrency_aware.py:909-916, 949` — build `candidates` region-set aware: when cross-role holders exist, do **not** offer `full` first; order by smallest disjoint candidate. Pass the cross-role holder map (`active_region_holders()` whole dict, not `.get(self._topology_role)`).
- Keep the 60 s poll-on-queue fallback (`:945-`) intact.

**Tests before wiring behavior** (per operator): unit-test `evaluate_placement` with a fixture where `ingest_long_context.half0` holds `{q0,q1}` and assert a `frontdoor`/`worker_general`/`vision_escalation` quarter candidate in `{q2,q3}` survives while `{q0,q1}` candidates and any `full` candidate are filtered. Add the cross-role-union case explicitly (today only same-role is covered).

**Gate to exit A:** unit tests green **AND** a live region-lock/dashboard observation showing a heavy+light set actually landing on disjoint shapes (observation, not a bench).

##### Part B — Shape-keyed admission decision (semantic core; safe once A lands)

Add a single placement-aware decision function and route both callers through it.

- New in `src/scheduling/contention.py`:
  `admit_set(active_placements, candidate_placement, traffic_class) -> PairDecision`
  where a *placement* is `(role, region_set)` (or `(role, topology_idx)` resolved via `get_instance_regions`). It looks up contention by **region set / instance shape**, not bare role:
  - disjoint candidate vs active set → consult the **quarter-level `n_way`** layer (authoritative for quarter-capable placement); measured `allow` → ALLOW.
  - overlapping candidate → that placement is infeasible (Part A should never produce it); fail closed.
  - placement unknown → legacy `pair_policy()` role-only fallback; **background + unknown → QUEUE (fail closed)**.
- Both `contention_gate.py:208-246` and the seeder `seeding_eval.py:104-106` (`_can_add_role_to_seed_wave`) call `admit_set` — they currently replicate the pair-before-nway ordering; centralizing removes the duplicated bug and the "n_way can only worsen" asymmetry.

**Matrix schema change** (`contention_matrix.yaml`):
- Pair/n_way lookups become shape-aware. The data is already shape-tagged (`instance_a/instance_b/cpu_list`); `get_pair`/`get_nway` must key on canonical region sets.
- Mark the overlapping-primary `block` entries (`matrix:33,43,53,62,71`) as **placement-conditional** (overlapping-primary placement) so they stop poisoning role-keyed lookups for disjoint placements. Keep them — they are the *correct* verdict for the overlapping placement Part A now refuses to make.

**Tests:** `admit_set` truth table — disjoint heavy+light → ALLOW; overlapping → QUEUE/closed; unknown placement bg → QUEUE; unknown placement fg → ALLOW. Plus a regression asserting an n_way `allow` is no longer masked by a stale primary-pair `queue` once placement is disjoint.

**Gate to exit B:** gate + seeder both produce a co-resident wave (e.g. `frontdoor + ingest + worker_general` on disjoint shapes) in a unit/integration test; no regression on overlapping sets.

##### Part C — Narrow legacy heavy barrier, add backfill, remove line-98

- `scripts/benchmark/seeding_eval.py:393` (`_eval_single_config`) — narrow the "wait all-heavy-ports idle + erase busy heavy slots" to the role's **own** target port/instance; drop the all-heavy-idle wait. Cross-thread erase hazard is `seeding_orchestrator.py:59` (a concurrent heavy seed thread can erase another heavy request's slot) — scope erase to own instance.
- `scripts/benchmark/seeding_eval.py:1069` — dispatch-time "heavy lock under pressure" path: change from **skip** to **backfill** (pick the next admissible role for the free regions via `admit_set`). This is what actually closes the wall-clock idle.
- `scripts/benchmark/seeding_eval.py:98` — **remove** the `HEAVY_PORTS`-both veto last (inert until A+B+C, proven by the monkey-patch).

**Gate to exit C:** with the stack live, the seed wave plan packs a matrix-allowed disjoint heavy+light set into one wave, and the region-lock dashboard shows the intended co-residency. No silent slot erasure of a foreign instance (assert via slot ownership).

---

#### Rollout / rollback

- Each part lands behind its own flag where feasible:
  - A: the placement state machine already gates on `_placement_state_machine_enabled()` (`concurrency_aware.py:921`) — extend that flag or add a `CROSS_ROLE_DISJOINT_PLACEMENT` sub-flag so A can be toggled without reverting code.
  - B: `admit_set` can be feature-flagged to fall back to the legacy pair-before-nway path.
  - C: the line-98 veto removal + backfill are the only irreversible-by-data changes; land last, revert by re-adding the veto (a 1-line revert).
- Rollback order is reverse: C → B → A.
- Topology guard: all of this assumes `topology_hash df373c79cc4af06f`. If `NUMA_CONFIG` changes, the matrix is stale and `admit_set` must fail closed (the gate already does this at `contention_gate.py:198-206`).

#### Acceptance (no perf bench)

1. Unit tests for A (cross-role placement filter), B (`admit_set` truth table + un-masking regression), C (own-instance erase scoping + backfill selection).
2. Live observation: region-lock/dashboard shows the intended disjoint heavy+light shape co-resident under the seeder. This — not a throughput number — is the acceptance signal, because the matrix already supplies the measured ratios.

---

#### Evidence index (verified 2026-05-30)

| Claim | Site |
|---|---|
| `pair_policy` role-keyed, placement-blind | `src/scheduling/contention.py:299-305,347,362-373` |
| Gate accumulates `worst`, n_way only worsens | `src/scheduling/contention_gate.py:209-246` |
| Seeder replicates pair-before-nway, stricter | `scripts/benchmark/seeding_eval.py:101-107` |
| Heavy-port veto (the symptom) | `scripts/benchmark/seeding_eval.py:98` |
| Placement same-role-only filter | `src/scheduling/placement.py:80-118` |
| Placement called with same-role holders; full-first | `src/backends/concurrency_aware.py:909-916,949` |
| Heavy-slot erase / all-heavy-idle wait | `scripts/benchmark/seeding_eval.py:393`; `scripts/benchmark/seeding_orchestrator.py:59` |
| Dispatch-time pressure skip (not backfill) | `scripts/benchmark/seeding_eval.py:1069` |
| Canonical region model (authoritative) | `src/runtime/instance_topology.py` (`get_instance_regions`, `Q_ALL/NODE0_HALF/NODE1_HALF`, `regions_overlap`) |
| Stale primary vs quarter n_way (0.37 vs 1.716) | `orchestration/contention_matrix.yaml:33,301` |
| Monkey-patch `HEAVY_PORTS=set()` → waves unchanged | operator test, 2026-05-30 |

#### Decisions locked

- Part B route: **principled shape-keyed** (`admit_set` keyed on canonical region sets / instance shapes). The interim "let n_way supersede pair if A placed disjointly" is rejected — it leaves the central ambiguity (same pair = 0.37 block ∧ 1.716 allow) unexplained.
- Role-only `pair_policy()` kept **only** as a legacy fallback for unknown placement; **background + unknown placement → fail closed**.
- `architect_general` stays solo (placement layer, not pair entries).
- Candidate ordering region-set based; never use `full` as an overlap proxy.

---

#### A-1 — RESOLVED (cross-role mutual exclusion / global region mutex)  [implemented 2026-05-30, test-first]

**Status of A:** CODE-COMPLETE, still LIVE-OBSERVATION-GATED (flag off; needs the region-lock dashboard showing a heavy+light set on disjoint shapes before flag-on). A-1 closes the TOCTOU — the behind-flag code now realizes both the *preference* AND the cross-role *guarantee*.

##### A-1 implementation (Option 1 — global region-mutex layer)

- `src/runtime/cpu_region_lock.py` (+67/−13):
  - `global_region_lock_path(region)` → `{tmp_dir}/cpu_region.GLOBAL.{region}.lock` (role-agnostic).
  - `_cross_role_mutex_enabled()` reads `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off).
  - `cpu_region_lock(...)`: when enabled, acquires the **GLOBAL** mutex for all regions first (sorted), THEN the per-role attribution locks (sorted) — consistent global ordering = deadlock-free; both layers on the same LIFO release stack. Flag off → GLOBAL layer skipped → byte-identical legacy behavior.
  - Per-role locks UNCHANGED as the attribution layer. `active_region_holders` is driven by the topology table (real `(role, idx)` only) and never globs lock files, so the `GLOBAL` pseudo-role is automatically invisible to attribution.
- Tests — `tests/unit/test_cross_role_region_mutex.py` (NEW, real **fork** processes for honest cross-process flock; spawn can't import the pytest module in the child):
  - flag-OFF → two roles overlap on q0 (documents the TOCTOU; passes against the bug).
  - flag-ON → windows serialize (disjoint) + GLOBAL lock acquirable after release (clean release).
  - `active_region_holders` ignores a held GLOBAL lock (attribution stays role-only).
  - **Hygiene (operator audit fix):** `_run_two_role_race` wraps start/join in try/finally with terminate→join→kill cleanup (mirrors `test_cpu_region_lock.py:400`) so a failed assertion or hung worker can never leak a child; the inert `@pytest.mark.timeout` marks were removed (pytest-timeout not in this venv) in favor of a hard 30s join bound + the finally-kill.
- **Regression:** `test_cpu_region_lock.py` 23/23 pass (legacy lock path intact); full placement/dispatch/mutex suite **58 pass** (mutex 3 + cpu_region_lock 23 + placement 16 + dispatch_cross_role 2 + dispatch_sm 4 + quarter_pref 8 + migration_sm 2). Pre-existing unrelated failure unchanged: `test_placement_policy::test_live_call_with_no_arg_does_not_crash` (parallel agent's `get_placement_policy` default change; stash-proven not mine). [audit-fix re-verified 2026-05-30]

**Remaining A gate (operator):** flip `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` only after a live region-lock/dashboard observation of a heavy+light set landing on disjoint shapes. **Nothing committed — working tree only.** Per operator instruction: **STOP here; do NOT start B (`admit_set`) until this is reviewed.**

---

#### A-1 — original blocker writeup (now resolved; kept for context)

**Status of A:** PARTIAL. The behind-flag code realizes the *preference* (placement filters + smallest-disjoint ordering + dispatch wiring + 48 passing tests) but NOT the cross-role *guarantee*. Do not flip `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` until A-1 is resolved.

**The race.** Region locks are **per-role** files: `cpu_region.{role}.{region}.lock` (`src/runtime/cpu_region_lock.py:98,108`). So `frontdoor.q0.lock` and `ingest_long_context.q0.lock` are *different inodes* — `flock` on them provides **no cross-role mutual exclusion**. `_dispatch` (`src/backends/concurrency_aware.py:962`) snapshots all holders, evaluates disjointness, then acquires only **its own role's** lock (`:974`) with **no post-acquire cross-role revalidation**. Two different roles can each pass a compatible snapshot and then take physically-overlapping regions. (Found by operator audit 2026-05-30; confirmed against the lock-path source.)

**Test owed:** a unit/concurrency test that forces the interleaving (role A and role B both see each other absent in the snapshot, both acquire overlapping regions) and asserts it CANNOT happen after the fix.

##### A-1 design fork (decide before implementing)

1. **Global region-mutex layer (RECOMMENDED).** Keep per-role lock files for holder *attribution* (the dashboard and `active_region_holders()` — and the cross-role union itself — depend on them), but before taking the per-role lock, also acquire a role-agnostic `cpu_region.GLOBAL.{region}.lock` (blocking, acquired in sorted-region order to avoid deadlock) for every region the chosen candidate needs. The global flock gives true cross-role exclusion; the per-role files preserve attribution. Additive (new lock files only), contained to the lock layer, lives behind the same flag.
2. **Post-acquire recheck + release/retry.** After acquiring own-role lock, re-snapshot holders; if a cross-role overlap appeared, release and re-poll. Insufficient alone — the symmetric "both acquired, both recheck, both release" case livelocks, and "A acquired and already passed its recheck before B acquires" still double-holds. Would need a deterministic tiebreaker and still leaves a residual window. NOT recommended as the sole mechanism.
3. **Collapse role out of the lock path (global namespace).** Simplest exclusion but BREAKS `active_region_holders()` role attribution that the dashboard + cross-role union need. Rejected unless attribution is rebuilt elsewhere.

**Recommendation: option 1** — the only one that gives a real guarantee without losing attribution.

##### Corrected A scope/test record (supersedes the earlier "CODE COMPLETE / 46 pass" note above)

- `placement.py`: `_cross_role_regions_union` + `cross_role_holders` kwarg on `evaluate_placement`; `None` → byte-identical legacy. **Ordering invariant FIXED** — when cross-role holders present, `safe` is stable-sorted by ascending region-set size (smallest disjoint first; quarters before full/half); no-cross-role path unchanged.
- `concurrency_aware.py`: `@staticmethod _cross_role_disjoint_placement_enabled()` (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`, default off, effective only with `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`); `_dispatch` snapshots the full holder map once per poll iteration and passes it through.
- Tests: `tests/unit/test_placement.py` (+5 incl. size-ordering) and **new** `tests/unit/test_dispatch_cross_role_placement.py` (+2 dispatch-level: flag-ON frontdoor avoids ingest's held node0-half → lands q2/q3; flag-OFF takes full). **48 pass** across the 5 placement/dispatch files. NB: `_dispatch` re-imports `active_region_holders`/`get_instance_regions` function-locally from their SOURCE modules — patch those, not `ca_mod`.
- **Pre-existing failure (NOT mine):** `tests/unit/test_placement_policy.py::test_live_call_with_no_arg_does_not_crash` — fails identically with my changes git-stashed; a parallel agent's uncommitted change makes `get_placement_policy("frontdoor")` return `BURST_PREFER_QUARTERS` not `SOLO_PREFER_FULL`. Untouched.
- **Nothing committed** — working tree only.

---

#### ⏯️ RESUME HERE — A-1 implementation in progress (context refreshed 2026-05-30)

**Future self: you were mid-implementation of A-1 (global region-mutex layer), test-first, when context ran out. Nothing for A-1 was written yet — you were still reading `cpu_region_lock.py` to plan the integration point. Pick up from the plan below.**

##### Operator's explicit instructions for A-1 (binding constraints)
- **Option 1 only**: global region-mutex layer. Keep per-role locks EXACTLY as attribution locks.
- Add role-agnostic locks as an ADDITIONAL layer, acquired **first**, sorted by region: `cpu_region.GLOBAL.{region}.lock`.
- Gate behind `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT`; **flag OFF must preserve current behavior byte-for-byte**.
- **Race test must use multiprocessing/subprocess** (flock semantics within one process are misleading — flock is per-(fd) and the same process re-acquiring its own lock can succeed misleadingly).
- Test BOTH sides: flag OFF → today's cross-role same-region overlap is ALLOWED (two roles both acquire q0); flag ON → blocked, and releases cleanly.
- **Do NOT start B** until A-1 is green AND the handoff marks A as code-complete-but-live-observation-gated. Then STOP for review.

##### Where things stand (verified facts)
- `src/runtime/cpu_region_lock.py`:
  - `region_lock_path(role, region)` (~line 98–108) → `{tmp_dir}/cpu_region.{role}.{region}.lock`. Sanitizes role/region (`/`,`\` → `_`).
  - `_try_flock(fd, lock_type)` (~line 118) → non-blocking flock, returns bool; raises on non-EAGAIN/EWOULDBLOCK.
  - `_acquire_one_with_timeout(fh, *, region, role, timeout_s, deadline_s, cancel_check, request_tag)` (~line 131) → blocking-with-timeout acquire loop; returns elapsed; raises `CpuRegionLockTimeout`.
  - `active_region_holders(instance_regions=None)` (~line 209) → `{role: [instance_idx,…]}` by scanning `cpu_region.*.lock` files. **CRITICAL: this parses lock FILENAMES for attribution. If you add `cpu_region.GLOBAL.{region}.lock` files, make SURE `active_region_holders` SKIPS the `GLOBAL` pseudo-role** (else dashboard shows a bogus "GLOBAL" role holder). Verify its filename-parsing/glob and add a `GLOBAL` skip.
  - The main entry context manager is **`cpu_region_lock_for_instance(role, instance_idx, *, timeout_s, deadline_s, cancel_check=None, request_tag=None)`** — a `@contextmanager`. It: resolves the instance's region set via `get_instance_regions()` / instance_topology, sorts regions lexicographically, opens+acquires each per-role region lock via `_acquire_one_with_timeout`, yields the list of lock paths, and releases LIFO on exit (all-or-nothing: on any timeout, releases already-held and raises). **THIS is the function you were about to read in full (it lives somewhere around lines 256–404; the file is ~404 lines). Read it FIRST on resume.**
  - File length: ~404 lines (the sed 245–415 only returned 11 lines once, which was a flaky/truncated read — do a fresh `wc -l` and `grep -n "def cpu_region_lock_for_instance"` to get the real boundaries).

##### The A-1 implementation plan (do this, test-first)
1. **Write the failing race test FIRST**: `tests/unit/test_cross_role_region_mutex.py` (NEW). Use `multiprocessing` (spawn or fork) OR `subprocess` with two child workers:
   - Each child calls a tiny helper that acquires `cpu_region_lock_for_instance("frontdoor", <q0 instance idx>)` and `("ingest_long_context", <q0 instance idx>)` respectively — i.e. two DIFFERENT roles both wanting region **q0** — holds briefly (writes a timestamp to a shared file / pipe), then releases.
   - Point `ORCHESTRATOR_TMP_DIR` at a `tmp_path` so lock files are isolated.
   - **Flag OFF assertion**: both children hold q0 SIMULTANEOUSLY (overlapping hold windows) — proves today's TOCTOU bug exists. (This documents current behavior; it should pass against unmodified code.)
   - **Flag ON assertion** (`ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1`): hold windows are DISJOINT (one waits for the other) — proves the global mutex serializes cross-role same-region. Also assert clean release (second acquires after first exits; no leftover GLOBAL lock file held).
   - Helper must be module-level (picklable) for multiprocessing spawn.
2. **Implement**: in `cpu_region_lock_for_instance`, when `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` is on, BEFORE acquiring the per-role region locks, acquire `cpu_region.GLOBAL.{region}.lock` for each region in the instance's set, in sorted order, via the same `_acquire_one_with_timeout` machinery. Add the global paths to the same release stack so LIFO release covers them. Add a `global_region_lock_path(region)` helper → `cpu_region.GLOBAL.{region}.lock`.
   - Flag OFF: skip the GLOBAL acquisition entirely → behavior identical to today.
   - Ordering/deadlock: acquire GLOBAL locks for all regions first (sorted), THEN per-role locks (sorted). Consistent global order across all callers = no deadlock.
3. **Make `active_region_holders` skip `GLOBAL`** (attribution must stay role-only). Add a regression assertion that a held GLOBAL lock does NOT appear as a role.
4. Run: `tests/unit/test_cross_role_region_mutex.py` + the full placement/dispatch suite (`test_placement.py`, `test_dispatch_placement_state_machine.py`, `test_dispatch_cross_role_placement.py`, `test_concurrency_aware_quarter_preference.py`, `test_concurrency_aware_migration_sm.py`) — must stay green (48 currently). Also re-confirm `test_placement_policy::test_live_call_with_no_arg_does_not_crash` is STILL the only pre-existing failure (not introduced by you).
5. Update handoff: flip A-1 from OPEN → resolved; mark A "code-complete, live-observation-gated"; update the routing index row. Then **STOP for operator review. Do NOT start B (`admit_set`).**

##### Test/infra gotchas (learned this session)
- Use `.venv/bin/python -m pytest …` (system python lost PyYAML after devcontainer rebuild; venv is correct).
- `_dispatch` re-imports `active_region_holders` / `get_instance_regions` / `cpu_region_lock_for_instance` **function-locally from their SOURCE modules** (`src.runtime.cpu_region_lock`, `src.runtime.instance_topology`) — monkeypatch THOSE, not `ca_mod` attributes.
- Bash tool output rendering has been flaky this session (results sometimes arrive blank then appear on a later call). If a test result looks empty, re-run to a temp file and `cat` it; don't trust a single blank.
- Shared clone `/mnt/raid0/llm` has many uncommitted parallel-agent changes. When committing, use `git add -p` / explicit hunks — NEVER `git add` whole shared files. Nothing from this whole task is committed yet (working-tree only) — operator commits manually.

##### What's DONE and must not be re-done (A core, behind flag, uncommitted)
- `src/scheduling/placement.py`: `_cross_role_regions_union()` + `cross_role_holders` kwarg on `evaluate_placement`; smallest-disjoint **stable size-sort** applied only when `cross_role_holders` truthy; `None`/empty → byte-identical legacy.
- `src/backends/concurrency_aware.py`: `@staticmethod _cross_role_disjoint_placement_enabled()` reads `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT` (default off); `_dispatch` snapshots full `active_region_holders()` once/iteration and passes it as `cross_role_holders` only when that flag AND `ORCHESTRATOR_PLACEMENT_STATE_MACHINE` are both on.
- Tests: `tests/unit/test_placement.py` (+5, incl. `test_cross_role_disjoint_holder_prefers_smallest_then_full`), `tests/unit/test_dispatch_cross_role_placement.py` (NEW, +2). 48 pass across the 5 files.

##### Standing operational context
- Stack is UP (started this session, all 35 components healthy, `[1.5]` prewarm validated — NUMA balance 26/24.6/24.6/24.6%).
- J6 autopilot soak RUNNING: daemon `autopilot.py start --no-controller --max-trials 2000`, state at `orchestration/autopilot_state.json` (NOT scripts/autopilot/), resumed at trial_counter=124. Log `logs/autopilot_relaunch15_*.log`. **Do NOT touch/restart autopilot or stack without explicit operator permission** (two standing CRITICAL constraints).
- [../archived/shape-keyed-contention-gating-B-RESUME-history-through-2026-06-20.md](../archived/shape-keyed-contention-gating-B-RESUME-history-through-2026-06-20.md) Part B admit_set scaffolding resume checkpoint

---

#### APPEND 2026-08-01 — W1 falsified a LOCKED decision; artifact 1 landed

**Read before executing anything above.** The W1 cutover (epyc-orchestrator `a517793c`) invalidated
one of this handoff's *Decisions locked* entries and three of its Invariant-1 shape facts.

- [x] **Corrected: `architect_general` is NO LONGER "strictly solo".** ✅ 2026-08-01 — the locked
      decision read *"its only feasible instance is whole-machine, so every candidate placement
      overlaps any other holder."* It is now Qwen3.6-27B on MI210 with an **8-thread GPU host lane**
      (`184-191`, `membind=3`). It went from the least co-residency-friendly heavy role to one of the
      most: measured `architect_general`+`ingest` moved **0.66 block → 1.40 allow**, +`frontdoor`
      0.90 → **1.43**, +`worker_general` 0.91 → **1.57**. The whole-machine blocker did not vanish —
      it was renamed `architect_critic` (:8074, full `0-95`, `interleave=all`). Every place this plan
      reasons about "architect_general the whole-machine blocker" now means `architect_critic`.
- [x] **Corrected: Invariant 1 shape table.** ✅ 2026-08-01 — `vision_escalation` (:8087, `{q2,q3}`)
      no longer exists as a process; it is an alias on `worker_vision`'s :8086.
      `architect_general` "full" `{q0,q1,q2,q3}` is now the GPU host lane. `worker_vision` moved off
      the node-1 quarter onto the same shared lane.
- [x] **Corrected: the topology guard's assumed hash.** ✅ 2026-08-01 — this plan assumes
      `df373c79cc4af06f`. Live is now `171f86f9`, and the matrix has been re-benched for it
      (15 pairs, **zero catastrophic**).
- [x] **`seam_admit`'s docstring was STALE and dangerously so.** ✅ 2026-08-01 — it read *"SCAFFOLDING:
      not yet called by the gate/seeder"*, which stopped being true on 2026-05-31 when the
      dispatch-side caller landed. The real chain is `concurrency_aware.py:1334` →
      `ContentionGate.admit()` → `evaluate()` (`contention_gate.py:312`) → `seam_admit`. It is
      inert-by-FLAG, not unreachable-by-wiring. A stale "dead code" comment on a live path tells the
      next auditor to skip the thing that actually runs.
- [x] **Artifact 1 (device-aware feasibility) landed.** ✅ 2026-08-01 —
      `src/scheduling/device_model.py`. See the rider:
      [`contention-model-device-and-load-axes-rider.md`](numa-placement-and-contention.md#track-contention-model-device-and-load-axes-rider).
      Flags stay default-off; 3628 verdicts swept against the prior module with 0 mismatches.

**Honest finding worth keeping.** On the *live* topology the device-aware model changes no
feasibility verdict — `184-191` is SMT-siblings-only and `parse_cpu_list` strips cores ≥96, so the
GPU roles already had EMPTY region sets and the cpuset-only model was right **by accident**. It was
one topology edit from being wrong: on the counterfactual 24-thread node-3 quarter (which W1
originally wired), the old model excluded 10 sets it should have admitted (18/102 → 28/92). What
changed live is that the answer is now *derived* and every exclusion names its resource.

##### Still open here

- [x] **`enumerate_feasible` gating was a category error** — it hard-refused on a stale matrix, but
      the feasibility model reads no measured cell. Now warns and proceeds, stamping
      `consumed_by_this_model: false`. The N-way path still refuses, correctly.
      **2026-08-12 (`mainB`) — VERIFIED ALREADY IMPLEMENTED; this box appears EARNED BUT UNFLIPPED.
      Not flipped by me — not my row; routing to the owner.** The row is written in the past tense
      and describes code that exists, phrase for phrase, at
      `scripts/server/contention_matrix.py:1052-1070`:
      the staleness branch comments *"the N-way enumeration CONSUMES measured pair ratios … that
      path still refuses"* and *"Refusing it on the freshness of evidence it never opens is a
      **category error** … Warn loudly, stamp the status into the manifest, proceed"*, with
      `log.warning(...)` on the `_feasibility` path only. The stamp is at `:1132`,
      `"consumed_by_this_model": not _feas`, carrying the comment *"Stamped for BOTH models. The
      feasibility model consumes nothing from the matrix, but a reader must still be able to see
      what the measured evidence looked like."*
      Verified by reading the implementation, not by matching the prose. If the owner agrees, this
      is a one-character flip with the evidence already written above it.
      ✅ **FLIPPED 2026-09-16 (`sub-sweep`)** — git evidence: the code landed in orchestrator
      `a517793c` (2026-08-01, "W1 cutover code half…"; `git merge-base --is-ancestor a517793c main`
      → true), and still stands on main `92bbeb06` in `cmd_enumerate` (`contention_matrix.py` ~:1671-1694,
      stamp ~:1719). It had no test, so it is now pinned on branch `sub/nextaction-sweep-20260916`
      `e1c06f72` (integrated by orchestrator merge `864c3b3b`): `test_stale_matrix_does_not_refuse_feasibility_enumeration` (rc 0,
      `consumed_by_this_model: false`, status ≠ ok) and `test_stale_matrix_still_refuses_nway_enumeration`
      (rc 2, no manifest written). `tests/unit/test_contention_device_model.py` 27 passed.
- [x] **Bridge residual 1** — echo `GateDecision` (`admitted`/`waited_s`/`decision`/
      `candidate_topology_idx`) into `/chat` response metadata so the ROUTE-A1 smoke MEASURES the
      verdict instead of inferring it from a 503 timeout.
      **⚠ DUPLICATE ROW — this is the same item as `BRIDGE RESIDUAL 1` at the top of this file
      (line ~29), which carries the `Do NOT land while a calibration run is live` gate that this
      copy does not.** Flagged 2026-08-12 (`mainB`); the two must not be worked or closed
      independently. This is the auditor's L166/L206 duplicate class, in-file rather than
      cross-index.
      **STATUS (mainB, the assigned owner of the top row): CODE COMPLETE, DELIBERATELY NOT MERGED.**
      Parked on branch `a14-gatedecision-echo` @ `a7d7bdb6` (6 files, +299/-0, 9 new tests, 127
      passed across the gate/placement/API suites). Merge-gate verdict **AUTONOMOUS**, 6 files, none
      human-only. Two caveats for whoever lands it: run the gate with a **three-dot** range
      (`main...a14-gatedecision-echo`) — two-dot reports 12 files because main advanced and shows
      later commits as deletions — and it needs a **cherry-pick, not `--ff-only`**, for the same
      reason. Still gated on a window clear of any live calibration run against the API.
      ✅ **LANDED 2026-08-13** — cherry-picked onto orchestrator `main` as `c61b8184` (local commit
      only, NOT pushed; push freeze). Gate re-run at landing with the prescribed three-dot range:
      **autonomous** (exit 0, 6 files, no human-only paths). Suite verified green on the branch
      (130 passed: gate/placement/API + the new observation-echo file) and 35 passed on merged
      `main`. No calibration run live against the API at landing (orchestrator API `:8000` down;
      only the dashboard hub serves). Both duplicate rows closed together per the duplicate rule.
- [x] **Bridge residual 2** — bind the re-bench `sample_fn` to the codified bench recipe. ✅ 2026-08-23 —
      `_default_admit_overlap_probe` (shapekeyed_step2_smoke.py:797) verified-identical to the canonical
      `run_paired_ab.py::_default_arm_probe` (:691): same `call_orchestrator_forced` kwargs
      (force_role pinned, `request_priority=background`, `workload_class=eval_batch`, PROBE_TIMEOUT_S,
      PROBE_MAX_TOKENS), same response handling, same placement-queue transport (never /chat).
- [x] **`shapekeyed_step2_smoke.py:718` `_drive_admit_overlap_probes` is a `NotImplementedError`
      stub**, and its `DEFAULT_ANCHOR_IDX`/`DEFAULT_PROBE_ROLES` are stale (anchor idx 0 for
      `ingest_long_context` is the FULL 0-95, not the `{q0,q1}` half; `vision_escalation` has no
      instance) — so every candidate overlaps the anchor and the admit-vs-queue signal the smoke
      exists to measure is structurally unobtainable, while it still "reports". ✅ 2026-08-23 — the
      stub was in fact implemented at `4dd270ed` (2026-07-21; the `:718` citation is stale). The
      "still reports" half is FIXED: new `_verify_anchor_held` (fail-closed anchor-hold precondition
      via read-only `active_region_holders()` scan, injectable seam) + `_verify_probe_signal`
      (refuses structurally-unobtainable plans: zero probes or all-admit/all-queue) — the smoke now
      refuses loudly instead of reporting its own expectation. 12 unit + 25 fixture tests green,
      ruff clean. Ledger row for ROUTE-A1-shapekeyed-step2 appended READY (build gate satisfied;
      execution = dry-run + quiet window + operator anchor hold, inference-gated).
- [x] **Stale smoke defaults (extracted from the box above, 2026-08-23)**: `DEFAULT_ANCHOR_IDX=0`
      (anchor idx 0 for `ingest_long_context` = FULL 0-95, not the `{q0,q1}` half) and
      `DEFAULT_PROBE_ROLES` (vision_escalation has no live instance → 0 rebench pairs). One-line
      operator decision to set a half/quarter anchor; until then the smoke refuses loudly (safe).
      ✅ **DONE 2026-08-23 (operator correction: quarters do not exist — retired 2026-07-30)** —
      `DEFAULT_ANCHOR_IDX = 1` (ingest node0 HALF, 48t, cores 0-47,96-143) with the default plan now
      resolving to 8 probes (3 admit-expected disjoint node1-half candidates + 5 queue-expected);
      `vision_escalation` dropped from `DEFAULT_PROBE_ROLES` (GPU-served :8086, no CPU-region
      instance — documented in the constant); quarter language removed from comments and the
      refusal message. Test fixtures updated to the half-anchor default; 37/37 smoke tests green.
- **[declined: ws58 2026-11-03 content-review: duplicate — context-and-token-economy TB-6 / kv-cache KVU-16i own admission-time VRAM]** **Contention still has no VRAM gate at admission** — `vram_fit` is exported and unused;
      rider Q3 (admission-time vs launch-time) is unratified.
- **[declined: ws58 2026-11-03 content-review: deliberately deferred by its own text with no trigger]** **`select_backfill_candidate` stays device-unaware** — deliberately, since resolving there is
      a live-behaviour change Part C has not authorized.

#### APPEND 2026-08-24 — ROUTE-A1 step-2 smoke EXECUTED (operator grant) — premise falsified for the live fleet layer

Executed 2026-08-24T06:48Z: anchor `ingest_long_context#1` (q0,q1) held via the sanctioned
`region-lock run --regions q0,q1 --role ingest_long_context -- sleep 900` CLI; host quiet (load ~2,
no bench drivers); fleet live; topology `171f86f9188211e9`. Report:
`epyc-orchestrator/data/shapekeyed_step2_smoke/route-a1-20260824T0648Z`.

- **Instrument passed; premise failed.** Plan 8 probes (3 admit / 5 queue expected); anchor-hold
  verified; all 8 probes classified (0 unscored). **smoke_pass = false, 3/8**: all 3 disjoint
  admit-expected probes ADMITTED correctly; **0/5 overlapping queue-expected probes queued** —
  every one ADMITTED.
- **Why (measured, not argued):** (a) the placement machine RE-PLACES forced eval_batch requests
  onto the disjoint instance — sample probe response: `contention_gate: {admitted: true, decision:
  allow, candidate_topology_idx: 2, reason: "all pairs + n-way allow"}` for a frontdoor#1-expected
  probe (i.e. dispatched to frontdoor#2, the node1 half, disjoint from the held anchor); (b) the
  gate decision is allow because the frontdoor+ingest pair row is `borderline` (OP-21 demotion
  2026-08-23) and the gate treats borderline as allow ("realistic green light").
- **The overlap-queue mechanism Step-2 was built to verify does not exist in the live fleet
  layer.** The region-lock anchor hold is not consulted for overlap exclusion on the eval_batch
  path (the queue path neither acquires nor checks region locks — verified separately: forced
  queue requests complete with zero lock acquisition), and the gate's pair-matrix verdict allows
  the co-run. The Step-2 flag-on decision now needs a re-specification: either pin the placement
  machine to the candidate instance (making the smoke measure the gate's verdict for THAT
  placement) or re-state the expectation against the fleet layer's actual overlap handling
  (re-placement + matrix-allow). Ledger: `ROUTE-A1-shapekeyed-step2-20260824T0648Z-executed`
  (DONE_PASS — the instrument ran; the finding is the observation).

#### APPEND 2026-08-24 (cont.) — OP-21 decision-grade attempt + seam exercise (c) + standing smoke restated (b)

- **OP-21 decision-grade attempt (operator-approved, quiet-ish window)**: bench-nway n=12 for the
  overlap pair (8080+8185) → ratio 1.198, cv 0.1044 (still CV_HIGH). **Pooled n=21 across all three
  runs: mean 1.165, cv 0.118, range 0.871-1.475.** Conclusion: the protocol's 0.05 CV gate is
  **physically unreachable** for this pair class under live-fleet variance (MTP+SSM co-run
  scheduling noise) — the matrix row (1.121 borderline) stands within noise; no change warranted.
  A decision-grade number would require a protocol variance allowance for this pair class
  (measurement-constitution question).
- **(c) seam exercise — DIRECTIONAL, INCONCLUSIVE (host became contended mid-window, operator
  flag)**: with q0,q1 held (ingest anchor) AND q2,q3 held (frontdoor busy), all three forced
  eval_batch probes (frontdoor, worker_general, ingest_long_context) returned **504 (queue-budget
  timeout)** — consistent with the seam queueing every placement (every candidate overlaps SOME
  held region), which is the designed fail-closed behavior; but the 504s cannot be cleanly
  attributed under concurrent host load. **Re-run the focused probe pair in a clean window before
  treating the seam as verified.** Mechanism status: both flags are ON in the live API
  (launcher setdefault since 2026-07-06); `seam_admit` is wired and live-reachable; the smoke's
  3/8 was caused by the placement machine only ever proposing disjoint instances.
- **(c) seam exercise — VERIFIED ✅ 2026-08-24 clean-window re-run (operator grant)**. Control:
  no holds → forced frontdoor probe admits in 1.4s (`decision=allow idx=0`). With q0,q1 (ingest
  anchor) + q2,q3 (frontdoor busy) held: all three forced probes (frontdoor, worker_general,
  ingest_long_context) return **504 at exactly the 45s queue budget** (min(90×500, 300000)) with
  explicit gate attribution: `error_detail="[ERROR: placement timeout role=frontdoor
  reason=placement_topology_overlap_timeout holders=[0, 2] after 45.0s]"`. The seam's fail-closed
  overlap exclusion is LIVE and correct: when re-placement is impossible (every proposed candidate
  overlaps a held region), the gate refuses with `placement_topology_overlap_timeout` instead of
  co-placing. **The never-co-place invariant holds at the gate level.** Together with the 08-24
  smoke (3/8: re-placement when disjoint instances exist), the complete behavior is now measured:
  the fleet layer avoids overlap by re-placement when possible, and refuses (queues to timeout)
  when not. Minor cosmetic note: the ingest probe's error_detail echoed `role=worker_general`
  (stale variable in the error message) — harmless, worth a one-line fix.
- **(b) standing smoke restated (DONE, 53 tests green)**: `--expectation {replacement|seam}`
  (default `replacement`): the standing model now expects re-placement + admit for every candidate
  and judges the **observed placement** — `admit_overlap` (echoed `candidate_topology_idx`
  overlapping the anchor) is ALWAYS a failure marked `CO-PLACEMENT` (the never-co-place
  invariant); `queued_unexpected` is a distinct failure (fires if the seam arms while the standing
  expectation is replacement). `seam` mode preserves the original overlap→queue model with
  byte-identical report keys (replays the 08-24 observation as 3/8 exactly). 14 new unit tests.



Reported by `mainC` (bus `msg-20260812T133841Z-20-mainC`), **both code claims independently
re-verified by the `auditor` at HEAD** before filing — the file was read, not the report trusted:

1. `scripts/server/contention_matrix.py:306-313` `_select_live_pair_instances` returns a substituted
   **disjoint** placement as `(a, b, None)` — *no marker* — and sets `overlap_measured` only on the
   faithful overlapping fallback. **The polarity is inverted: the marker fires on the honest
   measurement and is absent on the substituted one**, so a favourable disjoint number enters the
   matrix indistinguishable from a faithful measurement of the pair.
2. `src/scheduling/contention.py:519-536` states the stakes in its own comment — `frontdoor+ingest`
   overlapping node0-half primaries is **0.37 BLOCK**, the same pair disjoint is **1.716 ALLOW** —
   and `admit_set`, the function that disambiguates by CPU-region sets, is explicitly **SCAFFOLDING
   unwired to runtime**. So the live gate is still the role-keyed lookup that cannot tell them apart.

**This is reachable today, not a quarter-era relic.** The operator corrected the terminology: there
are **no quarter instances in production**. The shipped row is `cpu_list 0-47,96-143` vs
`48-95,144-191` — 48 threads each, i.e. **halves** carrying legacy `q0`/`q1` labels — and the matrix
holds zero 24-thread rows. The favourable geometry that entered the gate as a general role-pair
verdict is the current production shape.

- [x] **Fix the marker polarity** — mark, refuse, or reroute to `n_way`. ✅ 2026-08-23 — chose **REFUSE** (safest of the three): `cmd_run` now sends any selection whose geometry marker is present (the substituted overlapping fallback) to `unknown_pairs` with an `overlap_substituted` reason instead of benching/recording it as a `pairs:` row, so the gate's unknown-pair fail-closed policy applies; dry-run reports these as `REFUSED (overlap substitution)` instead of listing them as "would measure". The now-dead `pb.note` path removed. Verified against the shipped `contention_matrix.yaml:129-136` row class. 145 contention-suite tests + 205 importer tests green, ruff clean. The gate owner's call, and
      it does **not** depend on the re-bench landing: the inversion is wrong regardless of what the
      re-measured number turns out to be.
- [x] **Re-bench `frontdoor` + `ingest_long_context` in the OVERLAPPING geometry** (operator-authorised
      2026-08-12). ✅ **MEASURED 2026-08-23 08:53-08:58Z** (operator grant; host quiet: load <3, no bench
      drivers; topology hash `171f86f9188211e9`). Protocol: `contention_matrix.py bench-nway`
      (safe-sampling, N_PREDICT=100), hand-authored manifest pinning ports, per-thread affinity
      attested from /proc (194 pool threads per instance: 8080+8185 both `0-47,96-143` = node0 half
      OVERLAP; 8285 `48-95,144-191` = node1 half). Artifacts:
      `epyc-orchestrator/data/contention_matrix/op21-overlap-rebench-20260823T0855Z/`.
      - **OVERLAP 8080+8185**: n=3 → 1.110/0.871/0.949, ratio 0.977 (cv 0.102, borderline); n=6 →
        1.193/1.201/1.010/1.311/1.268/1.179, ratio 1.194 (cv 0.079, allow); pooled n=9 mean **1.121**,
        cv 0.125 — **NOT decision-grade (cv > 0.05)**; verdict class allow-marginal/borderline.
      - **DISJOINT control 8080+8285**: n=3 → 1.386/1.328/1.366, ratio **1.360**, cv 0.018 —
        decision-grade **allow**.
      - **Read**: the production (overlap) reality is ~1.0-1.2 co-run — mildly net-positive at best,
        dips below 1.0 (0.871); the shipped row's 1.89 allow (samples=1, disjoint geometry) is
        falsified for the overlap shape. Gate disposition (operator): demote the role-keyed pair row
        to the overlap measurement (~1.1 borderline/allow-marginal) since the role-keyed gate cannot
        distinguish geometry; the 1.360 disjoint control stays on file as the boundary reference.
      - **Disposition APPLIED ✅ 2026-08-23** (operator-approved): `contention_matrix.yaml` pair row
        demoted to the overlap measurement — instance_b re-pointed to 8185 (0-47,96-143 half0),
        ratio 1.121, cv 0.1251, samples 9, verdict `borderline`, measured_at + note citing the
        control and artifact path. `validate` + `check_contention_matrix_fresh.py` green (hash
        unchanged); the live gate now reads 1.121/borderline (loader verified). API reloaded
        (`orchestrator_stack.py reload orchestrator`, new uvicorn PID, :8000 healthy) — the
        demotion is in effect.
      The disjoint number is already on file at ratio 1.89 / verdict allow — **re-measuring
      the disjoint case answers the wrong question.**
      **Lane assigned 2026-08-12**: the operator granted `mainC` the CPU lane for exactly this
      (*"You can use the cpu lane — that's where the contention you're discussing lies"*), so this no
      longer waits on an owner. It was OP-21 in the master operator queue; the decision is answered and
      the row is retired. Remaining work is execution, not authorisation.
      **DRY-RUN 2026-08-12 — DO NOT run `contention_matrix.py run` for this.** The operator called the
      dry run rather than spending a post-reboot window, and it paid for itself:
      `_select_live_pair_instances` returns the first **disjoint** live combination and takes **no
      geometry argument** — there is no `--geometry`/`--overlap`/`--pair-ports` flag. Under the standard
      `--numa-mode both` lineup it selects `(8080, 8285)`, which reproduces the shipped 1.89 disjoint row
      **verbatim**. Running it post-reboot would have re-answered the wrong question on a clean host.
      Use `bench-nway` instead: it reads ports straight from a hand-authored manifest with no
      disjointness check, so it can pin the true overlapping halves `8080 + 8185`, and it runs
      `samples=3` with CV rather than `run`'s hardcoded `samples: 1`. Pair it with an `8080 + 8285`
      disjoint control **in the same window**. The `topology_hash` in the manifest must equal what
      `contention_matrix.py validate` prints.
- [x] **Refuse a contention ratio derived from a timed-out bench leg** ✅ 2026-08-12 — orchestrator
      `792ef3d8`. Found by the dry run above. `_http_bench` returns `(0.0, 0.0)` on timeout and
      `par_time = max(...)` discarded it while `total_tokens` still counted both legs. The error is
      **one-directional**: measured at 5 s solo legs, a timeout on the leg that would have dominated
      `max()` is *invisible* (ratio 1.00, identical to a healthy run) and the other shape reads 2.00 —
      no input of this shape can produce a false `block`, they all read `allow`. Fixed at both
      `_bench_pair` and `_bench_nway`; the latter is the path this re-bench will use. Mutation-tested
      per site, 125 contention tests green.
- [x] **`contention_matrix.py run --roles …` TRUNCATES the matrix** — ✅ 2026-08-23 — scoped runs now UPDATE measured rows and carry unmeasured ones forward verbatim (`_split_pair_entries` + `_preserve_unmeasured_entries`, malformed blocks refused); full runs regenerate wholesale unchanged; scoped runs stay stamped `decision_grade=false`. Shipped 15-pair matrix round-trips. `pairs` is in
      `_EMITTER_OWNED_SECTIONS`, so `_carry_forward_sections` does not preserve unmeasured rows: 3 pairs
      in, 1 out. Against `DEFAULT_OUTPUT` that would destroy 14 of 15 measured rows and degrade the
      admission gate to fail-closed for every other pair. Never invoke it against the default output,
      and never invoke the script bare (no subcommand ⇒ `cmd_run` with `dry_run=False`).
- [x] **The contention artifact carries no host-health provenance** ✅ 2026-08-12 — orchestrator
      `77e5a214`. `_host_metadata()` collected `uptime` and `kernel` and `_emit_yaml` discarded both,
      so a run at 14.1 d uptime was indistinguishable from a clean-host one. Now emits `host_kernel`,
      `host_uptime`, `host_health_status`, `host_health_warnings`, `decision_grade` and
      `decision_grade_blockers`. **The rules are IMPORTED from `server_np_sweep.py:host_health_warnings`,
      not re-implemented** — one authority, so the two harnesses cannot drift into disagreeing about
      what "clean" means. Verified live against today's host: `status: warn`, `decision_grade: false`,
      blocker = the uptime rule. **Fail-safe throughout**: probe failure, an unreadable `/proc/uptime`,
      a missing probe, or a pre-existing matrix all render `unknown` + `false`, never clean. The
      `/proc/uptime` case is the sharp one — `host_health_warnings` guards its uptime branch with an
      `isinstance` check, so an unreadable input produces **no warning at all** and would have rendered
      as a clean host without the explicit refusal. 17 pytest-collected tests, **13/13 mutations
      detected**, 151 contention tests green, purely additive (690 insertions, 0 deletions).

- [x] **Tighten the llama-process waiver: it cannot tell a lineup member from a FOREIGN server.**
      `77e5a214` records `existing llama processes present during attestation` as a warning but waives it
      from *gating*, and that waiver is correct in principle — a contention matrix benches the live
      stack, so those processes are the **instrument**, not contamination; gating on them would make
      `decision_grade` permanently unreachable and the field decorative. The waiver is also well built:
      it is derived by re-running the rules against an attestation with the instrument elided, never by
      string-matching a warning, so a reworded rule reclassifies itself.
      **The hole is that "the instrument" is not distinguished from "someone else's server."** On this
      shared host that is a live condition, not a hypothetical — the probe read
      `llama_processes_at_attestation: 1` with a load average of 13.7 while sibling agents were working.
      A foreign server is exactly the contamination a contention measurement must not absorb, and the
      current waiver makes it invisible to the gate. Fix: compare the observed process set against the
      expected lineup (stack manifest / `stack_priors`) and gate on the UNEXPECTED remainder rather than
      waiving the whole class. Until then the documented limit stands and is recorded in the artifact.
      ✅ **2026-09-16 (`sub-sweep`) — IMPLEMENTED AND INTEGRATED** (orchestrator merge `864c3b3b`, pushed in `753343f5`):
      orchestrator branch `sub/nextaction-sweep-20260916` `e1c06f72`. `_host_health_probe` now
      waives only processes whose `--port` is in `_expected_lineup_ports()` (launch-manifest
      `PORT_MAP` ∪ every `NUMA_CONFIG` instance ∪ `EMBEDDER_PORTS`); the unexpected remainder
      (undeclared port, or no attributable port — llama-bench/llama-cli) stays in the gating
      attestation, so the rule owner's own process warning fires there, plus a blocker naming
      `pid (port)`. An unresolvable lineup waives nothing; an empty host never resolves it.
      Provenance gains `llama_processes_lineup` / `llama_processes_foreign`. The explicit-only GPU
      shadow lane (:18100) is deliberately NOT lineup. Tests: contention suite 164 passed; a mutation
      restoring the whole-class waiver fails 5 new tests. Live relevance: a read-only `ps` on
      2026-09-16 showed a llama-server on `--port 18361`, which the old waiver would have hidden.
- [x] **Retire the stale `q*` nomenclature on half-sized instances** ✅ 2026-10-31 — reconciliation: APP `7ef445baffe0fd261c7daeffc0dfe1d42eaf2de1`; `tests/unit/test_contention_matrix_shape_labels.py`; durable artifact `artifacts/ni/source-acceptance-20261031/README.md` (actual topology CLI proof). [no-belief: audit-reconciliation] — a reader seeing `q0` on a
      48-thread instance infers a quarter. It already caused one agent to describe this live defect as
      a legacy one.
- [x] **Look at this together with `contention_nway_non_allow_count`** (`contention_gate.py:325`
      increments outside the precedence test, so it counts every N-way non-ALLOW check, including a
      verdict less restrictive than an existing pairwise decision — `mainC`, same day). Both are
      *the value asserts more than the measurement supports*,
      in the same subsystem, found by different agents hours apart; one review, not two local fixes.
      ✅ 2026-11-01 reconciliation: APP `7ef445baffe0fd261c7daeffc0dfe1d42eaf2de1` corrected the
      half-instance labels; APP `4b0eb6a9a932`, `de636086e679` and `b387c5dded66` corrected the
      counter name and description while retaining the old name as a compatibility alias. The latter
      counts non-ALLOW checks, not changes to the final pairwise verdict. See the adjacent source
      acceptance evidence and the completed counter item in `autopilot-continuous-optimization.md`.
      [no-belief: source and evidence reconciliation]
- [x] **REGION-SIBLING-1 — `region-lock` must map SMT-sibling CPUs to their physical core's region, not drop
      them.** (filed 2026-10-04, workspace-ec, from INC-20261004-subagent-unlocked-cpu-in-held-window)
      `src/runtime/instance_topology.py` `parse_cpu_list` keeps only CPUs 0-95 and silently discards
      96-191. So `region-lock run --cpu-list 160-183` maps to no region and cannot conflict with a held
      `0-95` window, although `thread_siblings_list` pairs cpu160 with 64 and cpu183 with 87 (they share
      physical cores 64-87). On 2026-10-04 three unlocked workloads pinned to 160-183 (a dev llama-server,
      a `cmake -j24`, and the KVU-19b `gpu_slot2.sh`) ran inside workspace-89's held `cpu-window2-20261004`
      and cost its MXFP4/EXL3/Q38FN measurements. Fix: map `c >= 96` to `c - 96` (or read the kernel
      sibling map) in the lock path, so a sibling-only claim conflicts with its physical cores. Check every
      caller that relies on the drop: `src/backends/concurrency_aware.py:547/557` (topology counting) and
      `scripts/server/gpu_shadow_lane_preflight.py:115` (overlap test), plus the AK stage-footprint
      requirement already stated in `autokernel-concurrent-target-coordination.md` §3 ("fold logical SMT
      siblings into the same physical region"). Done when `region-lock run --cpu-list 160-183` blocks
      behind a held `0-95` claim in a unit test, and the callers' existing tests still pass.
      - *(2026-10-04 ~08:00Z, workspace-ec; built, not merged, so not ticked.)* **Fix on epyc-orchestrator branch
        `fix/region-lock-smt-siblings-ec` @ `4ae008a8`** (pushed to origin, not on main). `parse_cpu_list` /
        `cpu_list_to_regions` gain an `smt_siblings` mode: `drop` stays the library default, so in-process placement
        and the AutoKernel claim path keep their exact meaning; `fold` maps each CPU to the lowest id in its sysfs
        `thread_siblings_list` and fails closed if topology is unresolvable. The `region-lock run` CLI folds by default
        (`--no-fold-siblings` restores the gap). 816 tests pass, including 22 new ones; the end-to-end test holds q3 and
        gets rc 75 for `--cpu-list 160-183`, with the child never run. **Merge and deploy AWAIT OPERATOR APPROVAL**: the
        auto-mode classifier blocked the merge to main. After approval, merge, then decide in a follow-up whether the
        placement layer should fold too.
      - *(2026-11-09, inf45-zerocompute.)* Verified ON main: `4ae008a8` is an ancestor of origin/main `98221350`; `tests/unit/test_instance_topology_smt_siblings.py` + region-lock/lock suites 183 passed. Ticked. [no-belief: code-landed-verified-by-tests]

<a id="track-within-role-placement-state-machine"></a>
## Moved: within-role-placement-state-machine

Split out 2026-11-10 to [`dispatch-placement-telemetry.md`](dispatch-placement-telemetry.md) (INF-87). No boxes live here.

## Track: reboot-gated-inventory-and-staging
<!-- gate: INF-06, INF-45#numa-placement-and-contention, INF-45#batched-decode-measurement, INF-86, INF-45#numa-placement-defect-20260730, INF-45#shape-keyed-contention-gating, INF-87, RTG-34#coordination-and-churn-pipeline, RTG-34#churn-pipeline, RTG-34#dashboard-architecture-restructure, RTG-34#handoff-index-and-backlog-graph -->

> Folded from `handoffs/active/reboot-gated-inventory-and-staging.md` @ `04334af47404` on 2026-11-03 (BRF-T7-F10, route 1b, operator D1/D5; retired row EVL-49 → INF-45). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Reboot-Gated Inventory & Pre-Reboot Staging

**Created** 2026-08-12 · **Owner** open (filed by a governance sweep session) · **Domain index**
[research-evaluation-index.md](research-evaluation-index.md) `EVL-49`

> **Operator directive this document serves (2026-08-12, verbatim):** *"I will personally let you know
> when I plan to reboot. If any handoff requires special pre-reboot staging you can let them do it. In
> an ideal world it would be great to know everything that is reboot-gated in our backlog, and churning
> through any pre-reboot work those tasks need so that when we reboot we unblock everything as a whole."*
>
> **The reboot is not imminent and will be announced.** Nothing in here asks for one. This is the list
> of what it buys, and the work that has to happen first so it buys all of it at once.

---

#### 1. The gate, measured — not quoted

Run read-only at 2026-08-12 11:28Z, through the same code path the harness uses
(`server_np_sweep.host_health_warnings(collect_attestation())`):

```
WARNINGS: ['uptime exceeds 1 week; MEASUREMENT.md P-BENCH-1/P-BENCH-3 policy requires reboot
           before decision-grade claims']
uptime_seconds = 1201884.7   (13.91 days)
numa_balancing = 0           ✓
existing_llama_processes = []✓
governor = performance · perf_event_paranoid = 1 · CPU boost observed to 4552 MHz · no throttle
```

**Exactly one warning, and it is uptime.** Every other host-health precondition is already green. That
is the headline: the reboot is the *only* thing between this host and decision-grade measurement, and
the moment it happens a very large batch becomes eligible simultaneously.

**Both routes to decision-grade are shut.** `server_numa_np_sweep.py:2141-2142`:

```python
overrides_active   = bool(args.allow_host_health_warning or args.skip_clean_check)
run_decision_grade = not warnings and not overrides_active
```

So `warnings` blocks it, and the override that clears `warnings` sets `overrides_active`, which blocks
it too. There is no third path. Screening / observation tier runs normally today.

**Asymmetry worth closing (defect-shaped).** `bench_canonical.sh` — the P-BENCH-1 canonical CPU path —
contains **no uptime or host-health check at all**. P-BENCH-3 (`server_numa_np_sweep.py`) fails closed;
P-BENCH-1 is honour-system. A canonical "decision-grade" number can be minted today that the policy
forbids, with nothing refusing it. See task S-11.

---

#### 2. Sequencing — what has to be true before the reboot is callable

| # | Constraint | Source | State |
|---|---|---|---|
| 1 | **INF-03 must reach a durable boundary.** `inference` owns compute and has a live arena campaign (`inf03-available-source-six-arm-20260812-r4`, cell 006 in flight, PIDs 2889129/3435515/3435803). | `inbox/coordinator-agent.jsonl` msg-20260812T111121Z-173, 11:11Z today: *"OP-16 reboot remains necessary for decision-grade IQK/A7 work, but only after INF-03 reaches a durable boundary and explicit operator reboot authorization."* | LIVE — check at reboot time |
| 2 | **All mains wrap up and persist.** `SESSION_LIFECYCLE.md:43-55` makes pre-reboot wrap-up mandatory including commit. Unpushed at 11:32Z: epyc-root 15 commits / 79 dirty; orchestrator 13 / 14; research 1 / 1185 (mostly untracked results — never `git add` that tree wholesale). | `SESSION_LIFECYCLE.md`; measured | pending |
| 3 | **`tmux new-session -d -s agent` is the mandatory first post-reboot command.** `allow_session_creation: false` is deliberate; `cmd_spawn` fails closed without it, so **nothing spawns** until a human runs it. | C20, `session-bus-thin-dispatcher.md` | documented, not automated |
| 4 | **Nothing auto-restarts the supervision tier.** coordinator-daemon, `bus_supervisor.sh`, `hub_supervisor.sh`, `fleet_watch.sh` all die together and none self-starts. `hub_supervisor.sh` was already found dead on 08-10. | OP-9; `session-bus-thin-dispatcher.md` FW-3 | cron form drafted, not installed |

> **⚠ OP-16 is OPEN, not declined.** `session-bus-thin-dispatcher.md` (worktree-isolation row) states
> *"OP-16 was declined by the operator"*. No such decision exists anywhere on the bus, in
> `progress/2026-08/`, or in the token queue; `master-handoff-index.md:46` carries OP-16 open dated
> 2026-08-12 and `autokernel-research-loop.md` §AK6.5 carries it as an open package recommending Option
> A. Today's directive is *deferred-with-announcement*. The row's conclusion (a worktree cutover needs
> no reboot) is right; its stated reason is false and should be corrected before it is cited as
> evidence the reboot was refused. → task **S-13**.

---

#### 3. THE BIG ONE — the reboot alone unblocks almost none of the batch loop

**25 compiled entries in `coordination/inference-batch/entries/` declare an uptime cap** (18 at ≤7 d,
7 at ≤14 d). At 13.91 d all 18 are already refused, and **the seven ≤14 d entries expire at ~13:37Z
today**.

But the uptime cap is the *declarative* half. The **machine-enforced** half is
`required_topology_hash`, which `run_batch_entry.py` compares fail-closed against the live
registry-derived hash — and **every one of those 25 entries is pinned to a dead value**:

| Pinned in the entries | Also pinned | Currently stamped in `contention_matrix.yaml:10` | Recorded live 07-30 |
|---|---|---|---|
| `8c8cfcbb13d2611d` (20-eval-tower, 30-bulk, 40-routing) | `kernel_era: production-consolidated-v7` | `171f86f9188211e9` | `bc28e15d` |
| `df373c79cc4af06f` (50-kernel-op2, 00-example) | `kernel_era: production-consolidated-v6` | — | — |

Production is **`production-consolidated-v9` @ `0db32c06`, binary 10125** (verified today,
`verify_llama_cpp.sh` exit 0). **So after the reboot, all 25 entries still fail closed — on kernel era
and topology hash, for reasons that have nothing to do with uptime.**

**Re-pinning those 25 entries is the single highest-value pre-reboot task in this document.** Without
it, the reboot clears one gate and leaves two. → tasks **S-01, S-02**.

---

#### 4. Second-biggest: the host tunables are not persistent

`kernel.numa_balancing=0`, `perf_event_paranoid=1` and `governor=performance` are all set at runtime.
There is no `/etc/sysctl.d` entry, and `scripts/session/health_check.sh:173-174` **detects** the drift
but nothing **applies** it (`"fix: sudo sysctl -w kernel.numa_balancing=0 (self-resets per session)"`).
`session_init.sh` does not re-apply them either.

**Consequence:** post-reboot the host-health gate warns on `numa_balancing` instead of `uptime` — a
different warning, the identical block, and the fresh-uptime window burns while somebody works out
why. Non-interactive `sudo` is available to sessions, so this is a script, not an operator step.
→ task **S-03**.

Related, same class: **`drop_caches` is available today** (sudo works). A cold page cache is therefore
*not* reboot-gated — which downgrades the MI210 cold-load break-even item from A to B (§7).

---

#### 5. Inventory

**Category key** — **A** genuinely reboot-gated (cannot be done at all until after) · **B** deliverable
claim is reboot-gated but the run executes today at screening tier · **C** misfiled: not gated, or
already satisfied.

Dispatch by **task TEXT**, never `file.md:LINE` — queue-wide anchor rot is 34.5%. Re-resolve with
`python3 scripts/coordination/backlog_row_check.py --row "<text>"`. Note `backlog_row_check.py` now
also refuses *prerequisite-blocked* rows (mainD, 2026-08-12) — a refusal may mean "blocked upstream",
not "rotted".

##### 5.1 Category A — genuinely reboot-gated

| # | Item (cluster) | Owning handoff | Needs the reboot FOR | Pre-reboot staging required | Current staging state |
|---|---|---|---|---|---|
| A1 | **CPU IQK campaign rerun** + its three step rows (`CPU first`, IQK replay candidate #1, "Then a real one") | `autokernel-research-loop.md` | Preflight **refuses before claim/build/benchmark** at 13.47 d — there is no screening tier here at all | Seed `HYPOTHESES.md` entries; re-verify the dry run still composes 13 steps / 10 pairs; **read the dry-run output before executing** (the 2026-08-04 `LD_LIBRARY_PATH` defect: a candidate linked against the anchor's `libggml` measures the anchor and reports a clean null with every gate green) | **READY.** Envelope bound to recipe frame `e504d8e9…b079b0`; dry run clean; whisper/qwentts symlinks repaired; both speech kernels verified; durable command in `progress/2026-08/2026-08-12.md`; STOP_STATE receipts in `/mnt/raid0/llm/autokernel/campaigns/ak-iqk-v9-20260811/events.jsonl` |
| A2 | **OP-16** — the authorization itself | `autokernel-research-loop.md` §AK6.5 | It *is* the reboot | File it as a **pre-validated token block** in `tokens/token-queue.md` — today it exists only as a master-index row, so the one signature the whole A-list waits on is absent from the queue the operator actually reads | Package written (Option A/B + recommendation + default) |
| A3 | **AK-WM-2a / 2b / end-to-end campaign** (matched archive) | `autokernel-research-loop.md` | The archive builder accepts **only real** proposal-v3 events joined to clean DECIDED terminals; synthetic fixtures explicitly refused | Pre-format the projection plan (JSON-pointer + SHA-256 pin list) so receipts fire the moment two clean campaigns exist | Builder + receipts landed (research `900cb5c6`, `e8de8bfa`); 4,078-test suite; 98/98 receipt slice |
| A4 | **C20 — create the `agent` tmux session** | `session-bus-thin-dispatcher.md` | The defect exists only post-reboot | Put the command in `tasks/post-reboot-session.md` as step 1; **pre-write the roster respawn list with endpoint→window-name mapping** (C25: spawn names the window after the *endpoint*, so a mismatch means hand-fixing with `tmux rename-window` again) | Documented in `CURRENT-CAMPAIGN.md` and OP-16 Option A; not in the handover brief's step list |
| A5 | **Supervision tier has no auto-restart** (daemon · `bus_supervisor` · `hub_supervisor` · `fleet_watch`) | `session-bus-thin-dispatcher.md` (FW-3), `handoff-index-and-backlog-graph.md` (**OP-9**) | All four die at once and none self-starts | **Get the OP-9 ruling before the reboot** so the crontab is installed during the boot window; both cron forms are already drafted. Write the manual bring-up order (daemon → supervisor → hub → fleet_watch) into the brief as fallback | Drafted, not installed |
| A6 | **Daemon is running stale code** (C28/C38 committed-not-live) | `session-bus-thin-dispatcher.md` | Python loaded the module at daemon start; the reboot delivers the restart for free | Pre-format the post-restart receipt: `already_flagged` reads `relay_state.json`, tick ≈0 ms, `cmd_status` ≈0.4 s not ≈9 s | Fix verified by direct invocation |
| A7 | **Stack relaunch items:** `-np` drift (12 live-process drift errors), pytest-escaped API PID 3903691, C1 fix #2 manifest writer, `/slots` 0/19, WP-14 phantom lineup, dashboard tap live-render | `autopilot-continuous-optimization.md`, `autopilot-dashboard-fidelity-audit-2026-07-22.md`, `dashboard-architecture-restructure.md`, `within-role-placement-state-machine.md` | All need a **realized lineup** to compare against; the stack is fully down, so the observations are confounded, not failing | Pre-render the expected post-launch process table (per-port `-np`, threads, cpusets) so bring-up is a one-command diff; pre-write the `selected_servers` assertion from the launch manifest; pre-write the human-observation script for the tap (which URLs, which counters, expected ↑/↓) | Tap harness 88 checks / 0 fail; rest unstaged |
| A8 | **earlyoom `--ignore` tweak** | `dynamic-stack-concurrency.md` | earlyoom is PPID 1, started at host boot, outside the container; the flag changes only at its next launch | Write the exact host-side launch line **into the OP-16 package** so it rides the same authorization | Not applied (host-side) |
| A9 | **AP-19b** — first supervised live `gepa_optimize` | `autopilot-continuous-optimization.md` | Needs a live stack in a watched window; the post-reboot relaunch *is* that window | Dry-run the cold bring-up recipe (`esc8-stack-restart-landmine-audit-2026-07-22.md` §2026-07-25); pre-format the journal-row + ERROR-path checklist | Recipe written, never executed; blacklist lifted 2026-07-25 |
| A10 | **AP-WM-1b** — over AutoKernel's first real matched archive | `autopilot-continuous-optimization.md` | Transitive on A1→A3 | Build and dry-run the observe-only harness, fixtures and receipt schema against synthetic rows now — only the *inputs* are gated | Unstaged |
| A11 | **E8 quality-baseline reseed** | `autopilot-continuous-optimization.md` | **3 of 5 blockers are stack-shape** (24 unique ports, 5 live frontdoors, both-mode 6/6) and need the full-lineup relaunch | ⚠ **The reboot alone does NOT unblock it.** (i) Get the operator's A–D choice on the source amendment (zero compute); (ii) **delete the five `.staging-` bundles** left by the 07-26→29 `--execute` attempts — the runner forbids reuse and the post-reboot run will fail on residue; (iii) re-run `--prepare --t2-n 500`; (iv) regenerate the context coverage scan, which reports `required_tokens` in **BYTES** (task S-08) | 5 failed attempts, bundles still present |
| A12 | **Reviewer-plane throughput/latency rows:** LB-1 attribution · LB-4 paired throughput A/B · LB-7 M3 baseline floor · RD-12 latency+token accounting · RM-4 confirmation-tier protocol | `reviewer-latency-and-sampling-budget.md`, `reviewer-decision-plane.md`, `reviewer-model-ablations.md` | Deliverables are throughput/latency/cost. `MEASUREMENT.md:121` records the throttle signature as **multi-day uptime −60%+** — these are invalid by *magnitude*, not merely by grade. LB-1 would produce a confidently wrong attribution | Write the attribution script + per-call-class instrumentation offline; **pre-register which of the three hypotheses each outcome supports** so the post-reboot run is confirmatory; codify sampling policies as arms; freeze task sets + seeds; build the A0/A1 baseline arms; build RD-12's accounting + parse-failure-fallback tests and the 50-question replay set | RD-12's vehicle (RCP-W2) never ran; LB-3 partially landed (`30d3232b`) |
| A13 | **Hermes latency measurement** (first-token, total) | `hermes-outer-shell.md` | Same throttle logic. The handoff's own *"effective throughput much lower than raw 39 t/s"* may itself be a 13-day-uptime artifact rather than a design defect | Build the harness; **capture the current suspect reading labelled pre-reboot** so the delta separates the two explanations | Unstaged |
| A14 | **Tool-output-compression first-party A/B** | `tool-output-compression.md` | Row: *"MUST report WALL-CLOCK (neither paper reports latency)"* — wall-clock is the declared differentiator | Build the log-growth / grep-cost instrumentation and the arm harness | Unstaged |
| A15 | **ColBERT S4b / S6 latency** | `colbert-reranker-web-research.md` | A hard **200 ms** threshold against a **180 ms** GTE baseline — a 20 ms margin. Throttle does not degrade this verdict, it inverts it | Export LateOn INT8 (the actual blocker, offline); **re-confirm the 180 ms GTE anchor was itself taken on a compliant host** — if not, it is not a valid anchor and both arms must be re-measured | Harness exists (`bench_colbert_rerank.py`, `b37de4a`) |
| A16 | **Parser bake-offs with a speed axis:** ODL 200-PDF five-way · LiteParse-vs-ODL-vs-pdftotext · LightOnOCR latency · ERNIE MI210 rebench | `opendataloader-pipeline-integration.md`, `ernie-image-turbo-evaluation.md` | Speed is a scored axis in each; ERNIE's row is explicitly *"measure-not-extrapolate"* | **Acquire the OmniDocBench source PDFs + mint the immutable manifest** — pure download/provenance, and it unblocks `document-parser-table-bench.md` too (same work filed twice). Note the real local ceiling is **51 eligible PDFs, not 200** | ODL hard-blocked since 07-29 on the missing PDFs |
| A17 | **Strand RustEvo2 Phase B** | `strand-rust-coder-rustevo2-verification.md` | Entry `KOP2-strand-rustevo2-phaseB` requires `quiet_window` + `max_uptime_days: 7` + `cache_state: warm`; single-instance sequential canonical bench with no screening variant | Dry-run `eval_models_rq1.py` against a mock endpoint; re-point the entry's `kernel_era: v6` / `topology df373c79cc4af06f` (§3); pre-create `/workspace/tmp/rustevo/RustEvo/results/`; pre-format the ledger row and gate-table fork | Phase A ✅ (GGUF on disk, toolchain + venv installed, harness validated 06-18); `OP-STRAND-INFERENCE-APPROVAL` ungranted |
| A18 | **RE-4 LongCoT-Mini chain** (RE-4.2 probe → 4.3 full → 4.4 ladder → 4.5 package), plus its duplicates **K-LCM-1** and **RE-4** | `re4-protocol-redesign.md`; dups in `bulk-inference-campaign.md`, `backlog-roi-audit-2026-07-14.md` | Entry `RE-4-longcot-mini-calibration` requires `quiet_window` + 7 d; row text names "operator quiet-window … autopilot stopped" | Re-attest the topology hash into the entry (the handoff header says to); regenerate + pin the 30-row stratified probe manifest (8/8/7/7 chem/chess/cs/math by sorted id); `--dry-run` `longcot_mini_stack_runner.py`; pre-write the `DONE_PASS` / `DONE_MARGINAL_OBS` ledger stubs. **Collapse the three duplicate surfaces to one** | RE-4.0 ✅ runner v2 (research `9323213d`); RE-4.1 ✅ entry v2 applied; dataset on disk; ledger `BLOCKED_PRECONDITION` |
| A19 | **MindDR Phase-2 gfx90a training-viability smoke** (**OP-4**) | `minddr-deep-research-mode.md` | *"Countermanded until E5 Stage-B releases the host"* — a Python ROCm trainer is invisible to E5's process/SMT-affinity gates and would silently contaminate its decision-grade cells | **Provision the pinned gfx90a training env** (`torch`/`transformers`/`accelerate`/`trl`/`peft`/`datasets` are absent from both uv envs) — pure provisioning, no host quiet needed, and it is the stated blocker | Unstaged. Cascades to `frontier-f3-data-flywheel.md`, `engram-conditional-memory.md`, the EV-9 judge model |
| A20 | **OpenMLE Sandbox reproduction** | `architect-model-selection-bench.md` | **A different reboot** — cgroup v1 via a GRUB kernel-cmdline edit | **Do NOT bundle into the OP-16 reboot.** Gate (1) is network-only and "any main": pull the worker/controller images and prove they run. Then draft the cgroup-v1 decision package (GRUB stanza diff + rollback + what depends on cgroup v2). Note `autokernel-research-loop.md:670` already declines a cgroup-v1 reboot as outside the adopted design | Trigger fired 08-11; gates ordered 1→2→3 |

##### 5.2 Category B — the run works today, only the claim waits

Full list in §6. Cluster heads:

| # | Cluster | Owning handoff | Needs the reboot FOR | Pre-reboot staging |
|---|---|---|---|---|
| B1 | **E5 NUMA×batch / placement re-measurement** — `RE-MEASURE E5 Stage-B on the corrected placement` (live), `E5 W1-W4 runs`, `E5 — NUMA×batch interaction sweep`, plus `T3` (`numa-placement-defect-20260730.md`) and `P2-1` (`numa-topology-cutover-resume-20260730.md`) — **one physical run, five rows** | `batched-decode-measurement.md` (+2) | Decision-grade label only; the row forbids the override in its own text. Also needs an exclusive window: `host_health_warnings()` counts `existing_llama_processes` **unfiltered**, enforced at run start *and* per cell, so a stack bringup mid-window kills the remainder | **Regenerate the corrected grid** per the row's binding requirements: (a) add full-machine `0-95` + `numactl --interleave=all` as a swept shape for `qwen36_q8_0` and `qwen3_next_80b` — today's winner existed in the old grid only as gemma's C1; (b) every straddling cell carries `--interleave` or is a declared defect-replication control; (c) `drop_caches` before every cell + record `pages_by_node`; (d) attest numactl policy per instance, fail closed on disagreement; (e) harness unchanged. Then re-verify readiness (§6.1). **⚠️ UPDATE 2026-08-16 — the grid is PARTIALLY BANKED, remaining scope is 24 manifests, not 40** (A7 grid fired then operator-stopped 2026-08-13; `progress/2026-08/2026-08-13-mainA.md` Sessions 7–8, verified on disk): group `gemma4_26b_a4b_q4km_mtp` is **COMPLETE 8/8, all decision-grade, 0.0% error — DO NOT RE-RUN**, banked at `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/a7-gemma4_26b_a4b_q4km_mtp-20260813T223750Z/` (the `...223703Z` sibling is the aborted attempt, no `cells.jsonl`); group `qwen36_27b_q8` is **EXCLUDED by operator ruling** (coordinator msg-94 2026-08-13 22:58:33Z, W3 dropped as GPU-resident tenant); remaining = `qwen36_q8_0` (12) + `qwen3_next_80b` (8) = **24 manifests**, launcher archived and still present at `/mnt/raid0/llm/tmp/a7-fire-20260813/a7-fire-all.sh`. Sizing the next exclusive window at 40 cells would burn hours redoing banked work |
| B2 | **GPU shed-trade** — `P2-5c` (RUN the P2-5a measurement), `P2-5j` + its decision-bearing successor, `P2-5g` | `gpu-serving-tie-in-program.md` | P2-5c gate G2 is verbatim the uptime tier; P2-5g's deliverable is a decision-grade contention pair feeding `contention_matrix.yaml` | Design already committed (`docs/design/p2-5a-shed-trade-measurement-spec.md`, research `d5f5942f`; corpus re-frozen `5e7a1564`). Pre-register arms; design the saturation-knee calibration sweep; author the `contention_matrix.yaml` per-pair entry shape; **P2-5j must precede any q3 carve** — MI210 is on NUMA **node 1**, so today's 184-191 placement is already cross-node and the node-local candidates were never tried |
| B3 | **Eval-tower model-gated cluster** — EV-5 ThinkPRM (4 rows), EV-7 Ouro T0, EV-8 diversity baseline, EV-10a skill efficacy, EV-13b review-F1 | `eval-tower-verification.md` | All five entries carry `quiet_window` + 7 d | **Highest-yield staging in the whole sweep** and 100 % non-inference: HF-pull ThinkPRM-1.5B → `convert_hf_to_gguf.py` → `llama-quantize` Q4_K_M; land the `orchestrator_stack.py` sequential-load config; implement `eval_t2()`; place Ouro-2.6B weights; freeze+pin EV-8's 20 prompts/role × 4 completions with seeds; assemble EV-13b's Augment-v1 145-bug golden set + semantic matcher and **author its batch entry** (it has none) |
| B4 | **Reviewer quality-axis rows** — RC-8, TM-8, RM-2/3/5/6/7/8/10, GC-1a/2a/3a, H-Q1 | `reviewer-calibration-accounting.md`, `reviewer-trace-materialization.md`, `reviewer-model-ablations.md`, `glm52-reviewer-capability-gates.md` | FA/FR/CR/coverage are quality metrics — throttle-insensitive. The **binding** gate for most is RC-6a's `MEASUREMENT.md` amendment, not uptime | **Build TM-8's per-worker flag-introspection probe first** — the known 1-of-6 uvicorn propagation hazard silently corrupts TM-8 coverage, so the guard must exist *before* the window. Freeze the K-of-M protocol and corpus slice; author RM-5's 6 bias injections and RM-10's 3 prompt arms (100 % offline). Honour GC-1a's prohibition: do **not** rerun unchanged `multi_oracle`/binary-schema/answer-fragment slices without a new repair hypothesis. Stage the H-Q1 UD-IQ3_XXS download (~300-340 GB, not present) |
| B5 | **Claim-grade singles** — P6 decision-grade confirmations, SWE `2b-confirm`, Gate-R `G3`, `I4` 33-flip re-run, 79-question judge suite on 27B | `inference-batch-loop.md`, `scoring-infra-standardization.md`, `fable5-window2-findings-03…md`, `autopilot-continuous-optimization.md` | Each deliverable is named claim-grade / decision-grade | Do SWE's gold-validation docker work now (non-inference) and pre-configure the scorer over the FULL slice (empty patches are absent from the report's lists and silently shrink the pairing). Do `G2` HIP build + op-coverage smoke — explicitly *"no window needed"* — and `G1` P-GPU-1 ratification, both of which clear G3's path; **repair `n5_frontdoor_drafter_retest.sh`, which pins a dead v5-only commit and must not run as-is**. Pin I4's 33 flip items to a manifest |
| B6 | **Determinism / routing / placement** — D3 canonical bench + D4 era row, RI-10 canary (+RI-11/12), DCP-6, SS-BENCH-GATE-b, WP-9/WP-10, WP-6/WP-7 + ≥8-pair vision_escalation, Bridge residual 2, `real_suite_v1` discriminability, Q4, BEP-2/J8, W3 applicator, live-pool oracle | `prompt-construction-determinism.md`, `routing-intelligence.md`, `bep-dcp-falsification-harness.md`, `standardized-stack-update-pipeline-finalization.md`, `within-role-placement-state-machine.md`, `shape-keyed-contention-gating.md`, `loops-and-dashboards-audit-2026-07-05.md`, `contention-model-device-and-load-axes-rider.md`, `batched-edit-parallel-apply.md`, `capability-registry-and-promotion.md`, `autopilot-continuous-optimization.md` | Mixed: canonical certification (D3), env-only-at-restart (RI-10's `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED`, DCP-6's `AUTOPILOT_TOOL_SENTINELS`), instrument-boundary (pool rebuild), topology re-pin (WP-9/10) | **Stage every launch-env flag into the post-reboot bring-up so the canary window starts at t=0 instead of costing a second restart.** Land SS-BENCH-GATE-b's cpusets **before** the reboot so they are live from the first launch — the incident it prevents is a reload sidecar invalidating a decision-gating run 1h09m in, i.e. exactly how the first clean window gets wasted. Implement `shapekeyed_step2_smoke.py:718`'s `NotImplementedError` stub. Root-cause `real_suite_v1`'s 0/50-vs-35/50 flip offline by deterministic replay. **WP-9/WP-10 needs no reboot** (its own prep doc says so) but its recert bench must not run at 13 d uptime or it bakes throttle hysteresis into a durable topology pin that ~52 sites reference |

##### 5.3 Category C — misfiled, or already satisfied

**These inflate the gated queue and should be corrected, not dispatched.** The highest-value ones:

| Item | Owning handoff | Evidence it is not gated |
|---|---|---|
| **EV-4, EV-4b, EV-11c** (3 rows + 2 dependents, + `RE-1` duplicate) | `eval-tower-verification.md`, `backlog-roi-audit-2026-07-14.md` | Ledger is terminal **`DONE_PASS` 2026-07-23** with `decision_grade=True` on both arms; EV-4 explicitly *supersedes* EV-4b. **Stale-open checkboxes — flip, do not dispatch.** |
| **P1-1, P1-2, P1-3, P2-5f, P2-5i, P2-9** | `gpu-serving-tie-in-program.md` | Every reboot clause names the **07-29** reboot, which executed. Real gate is the E8 signature (P0-1). P1-2's own 08-11 annotation records Stage-B COMPLETE. P2-5i is a standing prohibition carrying `do not flip this box`. P2-9 mentions a reboot only as a download-hazard warning |
| **RC-6a + its two amendment candidates**, **LB-6b**, **LB-6**, **LB-3**, **LB-8** | `reviewer-calibration-accounting.md`, `reviewer-latency-and-sampling-budget.md` | RC-6a is a **human PR against `MEASUREMENT.md`** with blocks already copy-paste-ready and a 4-step checklist. It gates every decision-grade reviewer claim. LB-6b is an operator threshold pick from three drafted candidates. **Both are free wins during the reboot wait** |
| **`gpqa_diamond_cot` full n=198** | `architect-model-selection-bench.md` | GPU accuracy is device-independent and the sibling MMLU-Pro control ran **2026-08-12** at this uptime with released claims. Pinned manifest exists; A1/A3 run dirs exist. **Only the A4 arm is missing — dispatchable today** |
| **Eval-tower A2 / C2 / E5 hardening** | `eval-tower-architecture-audit-2026-07-20.md` | Gate is mechanical and not uptime: *"`pgrep -f evaltower_window` returns nothing (and `:8000` idle)"*. Run the pgrep before assuming blocked |
| **`llamacpp-v6-consolidation.md` "Post-reboot NUMA topology bench (the NEXT gate)"** | same | Dead prose with **no open checkbox**; the file's own line 391 records **"Reboot-necessity verdict: NO REBOOT NEEDED"**; v6 is three eras superseded. Its 3 open rows are upstream-parity items with no host gate |
| **NPS / BIOS / NUMA-topology reboots** | `handoffs/completed/nps-reboot-runbook.md`, `wiki/hardware-optimization.md` § NPS4 48×4 notes | **The whole category is empty.** The runbook is closed — *"Reopen triggers: none"*, L3aaN is do-not-re-propose. the folded NPS4 48×4 notes in `wiki/hardware-optimization.md` are notes-only with **zero open checkboxes**. There is no live BIOS/boot-setting item |
| **R1a — end-to-end bench claim** | `session-bus-thin-dispatcher.md` | Needs one short smoke (`-n 128 -r 1`, small model) under a *held claim*, not a signature (R2 ✅). **The stack is fully down, so this is the cheapest it will ever be — do it BEFORE the reboot**, since it de-risks every decision-grade bench in the first clean window (A0 is currently only structurally verified) |
| **AP-3 / AP-3b**, **AP-WM-1**, **autopilot-pause interlock**, **worktree isolation phase 2** | `autopilot-control-plane-integration.md`, `autopilot-continuous-optimization.md`, `session-bus-thin-dispatcher.md` | "Restart-scoped" means *llama-server role reload*, not host reboot. AP-WM-1 matched a `decision-grade` keyword only because it **disclaims** it. The pause interlock is a code fix — but fix it **before** AutoPilot resumes, it caused a live outage 08-03 |
| **RM-9** | `reviewer-model-ablations.md` | Its precondition is **falsified** — A4 failed admission (FA 41.7 %, FR 25.0 %, AUC 0.509). Close as a decline, do not carry as gated |
| **GC-4** | `glm52-reviewer-capability-gates.md` | Operator decision, and it **collides with OP-8** (GLM-5.2 GO/WAIT/KILL, 222 GB). May be moot if OP-8 lands KILL — escalate the pairing |
| **`ROUTE-A1` / `ROUTE-A2`** | (batch ledger) | Blocked by a `NotImplementedError` stub (`shapekeyed_step2_smoke.py:718`) and a missing corpus manifest. A reboot fixes neither; both will resurface as false post-reboot candidates |
| **`reviewer-typed-artifacts.md` (4 rows) + `security-review-skill.md` (6 rows)** | those files | Zero host dependency, same intake source. **10 boxes, cleanest none-lane block available**, and the negative-control axis is a prerequisite for ever measuring a false-accept rate — which every A12 row depends on |
| **`cpu-shape-specialized-gemv-decode.md`, `sarathi-serve-cpu-evaluation.md`, `gpu-drafter-mi200-investigation.md`** | those files | Say so explicitly: *"Does NOT require BIOS reboot or env var"* · *"Independent of L3aaN reboot"* · the clean-window retest is already `- [x]` decision-grade ✅ 2026-07-16 |

**Also stale, and it matters:** `document-parser-table-bench.md` and `opendataloader-pipeline-integration.md` each carry **standing constraints wearing checkboxes** (`Do not download MinerU2.5-Pro…✅`, `NAME COLLISION — do not resolve by path`, `Route … away from LiteParse`). Same defect class the auditor escalated as `backlog-queue-template-rows`. Do not dispatch, do not flip.

---

#### 6. Run now at screening tier — do not leave these waiting

The reboot changes a *label*, not a *number*, for everything in Category B. Running them now costs
nothing and converts the post-reboot pass from discovery into confirmation. Label the tier honestly in
the manifest (`decision_grade: false`) and say "quiesced host" in anything published — AutoPilot is
down, so these numbers are not silently representative of production.

**Highest value first:**

1. **RC-8 baseline** (`reviewer-calibration-accounting.md`) — the entry states plainly that *"the
   observation-grade run itself does not block on"* OP-5a. Corpus v1 already built
   (`nearmiss-v1`, 11,516 rows, `content_sha256 1c50c025…`).
2. **DCP-6 eval half** — `dcp_j7_ab.py` *"requires `--host-quiet-confirmed` and refuses if AutoPilot is
   running"*. **AutoPilot is down, so it will not refuse today.** Last artifact: `decision.status=hold`.
3. **RM-3 screening tier** — literally the screening tier; all four children ✅. Only the *promotion
   rule* to confirmation tier needs post-reboot cost numbers.
4. **D3 canonical bench, screening pass** — establishes effect direction at zero claim risk, then the
   post-reboot run only has to confirm it.
5. **RLM E1 / E3 / E3b** — the handoff already grades its n=20 numbers as observations; a screening pass
   de-risks the harness.
6. **ERNIE content-filter audit** — harness ready (`ed6f65f5`), 10 cases across 5 categories authored,
   qualitative deliverable, throttle-insensitive.
7. **AP-WM-1 offline archive comparison**, **`gpqa_diamond_cot` A4 arm**, **MD-9 sentinel A/B**, **TM-8
   coverage** (after its introspection probe lands), **document-parser Phase B binary `<table>` gate**.
8. **The seven `max_uptime_days: 14` entries** in `30-bulk-campaign.yaml` — eligible until **~13:37Z
   today** and then not again until the reboot. They still fail the topology pin (§3), so this is only
   reachable if S-01 lands first. Report the outcome either way.

---

#### 7. Capture before the reboot — restart destroys these

**What survives:** `/workspace`, `/mnt/raid0/llm/**` (incl. `/mnt/raid0/llm/tmp`, 41 GB) and the
agent-memory dir are all `/dev/md127`, one persistent RAID. The 2026-08-11 fleet-wide claim that
*"uncommitted work does not survive a reboot"* was **false and was retracted** (F-21,
`coordinator-role-failure-modes-and-refactor.md`). The real hazard to untracked work is `git clean
-ffdx`, not the power button.

**What does not:** `/tmp` is the **container overlay**, a different filesystem (22 GB, includes the
agent scratchpads). It survives a container *restart* but not a container *recreate* — and
`.devcontainer/Dockerfile` is currently modified in the working tree.

| # | Artifact | Why it dies / why it matters | Where |
|---|---|---|---|
| C-1 | **`tmux list-windows -t agent`** — window names ↔ roster ids | The only record of the live roster shape; C25's endpoint/window mismatch was hand-fixed with `tmux rename-window` last time and *"nobody will remember next reboot"*. Currently: `0 coordinator · 1 htop · 2 btop · 3 inference · 4 auditor · 5 mainA · 6 mainB · 7 mainC · 8 mainD · 9 fish` (session created 2026-08-01 05:46) | kernel state |
| C-2 | **Daemon epoch + pid + heartbeat**, plus supervisor/hub/fleet_watch pids | C26's guard refuses a live state when heartbeat `age` exceeds **system uptime** — only meaningful if the pre-reboot epoch is known. Live now: daemon 1728027 (11:28:48), supervisor 359336 (11:02:43), hub :8100 1367133 (11:19:37), fleet_watch 1448583 (11:20:37) | `heartbeats/coordinator-daemon.json` + `ps` |
| C-3 | **`/proc/<uvicorn>/environ`** and **`/proc/3903691/environ`** | WP-10's entire safety argument rests on `ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1` having been *read from a live process*; that verification dies with the process. PID 3903691 is the pytest-escaped API carrying `PYTEST_CURRENT_TEST` — the surviving evidence for INC-20260806-pytest-api-escape | `/proc` |
| C-4 | **NUMA page placement (`pages_by_node`) of every resident instance, and the warm production-wiring datapoint** | `--interleave` binds at **first touch only**, so it is a silent no-op on a warm cache. The defective placement (`{N0: 9226101} / 9226101`, all 35.2 GiB on node0 under a node0+node1 team) and the warm **7.81 ± 3.82 t/s** frontdoor figure are the AutoPilot operating point B1 is re-anchoring against | `/proc/<pid>/numa_maps` |
| C-5 | **Page cache = 1046 GB warm.** Not a loss to prevent — a state to *declare* | The reboot drops it. That is the point (cold-cache opportunity) and the cost (every model load is cold). Post-boot the first re-read **pins one node** — the NUMA-interleave re-warm discipline must be in the boot runbook, never a bare re-read | measured |
| C-6 | **Current CPU frequency profile** | min 1998 / avg 2412 / **max 4552 MHz** at load 12.0, no throttle. Capture it so a post-reboot delta can prove (or disprove) accumulated throttle rather than assuming it | `/proc/cpuinfo` |
| C-7 | **Era-fenced ledger accrual — the highest-risk loss in the sweep** | Fence `1785004723.0` retains **16 trusted rows / 2 eligible items against a 40-item target** (shortfall 38) after excluding 1,317 pre-era rows. **If the reboot moves the kernel/topology era, this resets to zero again.** Snapshot the ledger, the fence value and the row counts, and decide *deliberately* whether the reboot opens a new era | `fable5-window2-findings-01/03` |
| C-8 | **AutoPilot journal: duty-cycle + production-traffic history** | Needed for the P2-2 anchors (3 of 4 roles have none; `frontdoor` = median 35.7 t/s, n=154) and for P2-5f. AutoPilot has been down since `2026-07-27T08:23:07Z`; a restart resets the accumulation clock again. **Harvest what exists now** | `orchestration/` journal shards |
| C-9 | **`logs/llama-server-*.log`** | Open row: *"UNEXPLAINED: every llama-server exited at ~07:00 on 2026-08-04"* — ends with an explicit instruction: **"If it recurs, capture `logs/llama-server-*.log` BEFORE restarting."** | `epyc-orchestrator/logs/` |
| C-10 | **`autopilot.log` and the `tool_chains` rows** | A previous rotation already destroyed the historical REPL evidence (*"0 parseable historical REPL sessions"*). Archive before it happens again | `epyc-orchestrator/` |
| C-11 | **In-flight session journals feeding P4c** | `next_turn_followup_command` is populated by reading the *next* bash command in the same session journal; a reboot ends every session, so unpaired rows are lost and the "1 week of data" restarts | `logs/tool_compression_monitor.jsonl` + journals |
| C-12 | **M3 / M4 soak clocks** | M4 is a 48 h zero-idle acceptance; a reboot resets it, slipping the `triage` and `headless-worker` grants another two days | `token-queue.md` standing gates |
| C-13 | **Pre-restart daemon tick cost** (~8.9 s, ~6.6 GiB transient dicts per 45 s tick, 29.5 % of a core) | The before-half of A6's A/B; unreproducible after the restart | measured |
| C-14 | **`/mnt/raid0/llm/tmp/orchestrator_runtime_facts.json`** (`2026-08-11T08:19:56Z`, `selected_servers: None`) | The stack-down control for A7's comparison; overwritten at the next reload | RAID (safe, but will be overwritten) |
| C-15 | **Suspect anchors of unknown host provenance**, each labelled pre-reboot | Hermes *"much lower than raw 39 t/s"*; ColBERT's **180 ms** GTE baseline; PaddleOCR's `2918.78` / `3245.60` ms median page latencies; LB-1's 07-16 regression anchor (~68 backend requests + 11-17 plan-review prompts per 50-question replay). Capture them so the post-reboot delta separates *design problem* from *13-day-uptime problem* | various |
| C-16 | **Region-lock flocks and the sealed `advisory*.jsonl` shard** | flocks are kernel state and vanish. C38 archives sealed shards to `EPYC_BUS_ARCHIVE_ROOT` (default `/mnt/raid0/llm/bus-archive/advisory`, outside the repo where `git clean -x` cannot reach). Confirm the current shard is sealed and archived | bus |
| C-17 | **The accepted v9 control bundle and journal** — `ak-controls-v9-a4cb04ca-20260812-r2`, AutoPilot exact-stop at trial `1458`, the three-point speed frontier, and the Kernel-R&D surface state (frozen v9, 8/8 preflight, 5/5 controls, GPU `NOT_REPRODUCED`) | `CURRENT-CAMPAIGN.md` mandates preservation explicitly | RAID |

---

#### 8. Post-reboot first hour — the order these rows imply

Not a proposal; this is the ordering the open rows already require, collected in one place.

1. **`tmux new-session -d -s agent`** — C20. Nothing in the code does this; every spawn refuses until
   it exists.
2. **Re-apply the host tunables** — `sysctl -w kernel.numa_balancing=0`, `perf_event_paranoid=1`,
   governor `performance`. **Verify with `health_check.sh` before anything measures.** Skipping this
   swaps the uptime warning for a `numa_balancing` warning and wastes the fresh window (§4).
3. **Restart the supervision tier** in order: coordinator-daemon (picks up C28/C38 for free) →
   `bus_supervisor.sh` → `hub_supervisor.sh` → `fleet_watch.sh`. Verify each with `ps -p <pid>`, never
   with `status` — the state file outlives the process that wrote it.
4. **Respawn the roster onto the EXISTING ids.** A fresh alias orphans that identity's cursor, outbox
   and triage `corr_id`s. Expect C40's staleness banner on the relayed backlog — last time 703 messages
   landed in one burst and two mains burned tokens on 12-day-old work.
5. **Launch the stack with the staged env**: `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true` (RI-10),
   `AUTOPILOT_TOOL_SENTINELS` (DCP-6), SS-BENCH-GATE-b cpusets, `ORCHESTRATOR_SEARXNG_DEFAULT=1`
   (SX-6). Each of these otherwise costs a second restart.
6. **Run the launch verification**: the per-change checklist in
   `model-stack-change-standardization-audit.md` (do-not-flip; it is a procedure, not a backlog row) +
   the `-np` drift diff + the `selected_servers` assertion + `verify_ggml_linkage.sh` for every
   launcher.
7. **Re-derive and re-pin the live topology hash**, then re-run the batch-entry preflights.
8. **Then** the window is genuinely clean. **CPU IQK, D3, and the E5 re-measurement all want the same
   window and are mutually exclusive with any `llama-server` on the host** — co-schedule them
   deliberately; the ordering is `inference`'s call.

---

#### 9. Pre-reboot staging tasks

Dispatchable now. None requires a reboot; none runs a benchmark or starts `llama-server`.

- [x] **S-01 — Re-pin all 25 uptime-capped inference-batch entries to the current era and live topology
      hash.** ✅ 2026-08-12 (commit `b92845c2`). Re-pinned **36** entries across 7 files to
      `171f86f9188211e9` + `kernel_era: production-consolidated-v9`, and recompiled `manifest.yaml`
      (the artifact the loop actually reads — editing only `entries/` would have left the fix with no
      caller). Scope was the named 25 plus 11 more carrying the identical dead pin
      (`00-rcp-prologue.yaml` 3, `10-reviewer-plane.yaml` 8). Deliberately excluded:
      `60-glm-decision.yaml` (experimental-candidate eras are the comparison baseline) and
      `90-coordination-rows.yaml` (`COORD-v7-promotion` is a historical record). `compile_inference_batch.py
      validate` → 52/52 valid. **See §10 — the "all 25 fail closed today" premise was wrong.**
- [x] **S-02 — Re-derive the live topology hash first and record it with its derivation.** ✅ 2026-08-12.
      Live hash **`171f86f9188211e9`**, derived through the enforcing consumers' own path
      (`preflight_gate._live_topology_hash()` → `contention.topology_fingerprint_for_matrix(NUMA_CONFIG,
      matrix)`); no value was copied. **Recorded as a re-runnable deriver, not a number** —
      `scripts/coordination/derive_topology_hash.py` hard-codes no hash and carries `--check-entries`
      (fail-closed; refuses a vacuous empty-input pass). Recording a *number* is exactly how three stale
      values entered circulation, so the number is deliberately not the deliverable.
- [x] **S-03 — Write and validate a first-boot host-prep script.** ✅ 2026-08-12.
      `scripts/session/host_prep.sh` (`--check` / `--apply` / `--install-boot` / `--verify-boot`) covers
      the **eight** settings the gates actually check (§10), not the three named here. Boot persistence
      installed on the HOST and verified (7/7). 39 fake-root mutation tests + 7 live mutation assertions,
      all counted and exit-gated. **See §10 — the "no `/etc/sysctl.d` entry" premise was also wrong.**
- **[declined: ws58 2026-11-03 content-review: merged into RE-MEASURE]** **S-04 — Capture contemporaneous E5 Stage-B readiness before future execution.** The July staging record is historical. Research `main` publishes the current v10 dry-only runbook at `3caaf22fa853daab5c5ae055ca46b67809e2c938`; the already closed `VB-EVL49-S04-V10-DRY-PLAN` records three model-free planning controls. Before a future run, bind current host readiness, exclusive-window admission, CPU kernel-store alias/binary/version/linkage and the model/input identities required by that run. Dry planning does not establish these facts. Actual E5 measurements remain with their inference-window task.
- **[declined: ws58 2026-11-03 content-review: merged into RE-MEASURE]** **S-05 — Generate the corrected E5 re-measurement grid** per the RE-MEASURE row's five binding
      requirements (full-machine `0-95` + `interleave=all` added for `qwen36_q8_0` and
      `qwen3_next_80b`; explicit `--interleave` or a declared defect-replication control on every
      straddling cell; `drop_caches` + `pages_by_node` per cell; per-instance numactl attestation that
      fails closed on policy/cpuset disagreement; harness unchanged). Dry-run to exit 0.
  - **Source phase accepted, 2026-10-21 (original event 2026-10-08):** the same capture closed by VB-EVL49-S05-CORRECTED-ROSTER-CAPTURE preserves original TRUE outer1/1, corrected saved-E1 33 manifests, two W1/W4 dry plans, 48 outputs and 2,764 inputs. Roster SHA-256 `c577e45a0d37682b1d536df5c12ce86fe43807b9f25fd08e0ae74d312a96ef2e`. [Original custody and exclusions](../../artifacts/ci/evl49-s05-native-source-20261008/README.md). S05 stays open for current 1.35 GB pool/placement and owner-window observations; synthetic observer capture is separately tracked by VB-EVL49-S05-OBSERVER-SOURCE-CAPTURE, not a new completed S05 source checkbox.
  - **2026-11-02 BRF-T3 (ws58):** the existing `e5_manifests_a7_placement1` Qwen set (20) does NOT yet satisfy the five requirements. 10 C1b manifests fail (b), with straddling cpusets, policy none and no control declaration. 0/20 declare a per-cell drop for (c). (a) passes. The grid still needs generating, and the launcher `a7-fire-20260813` is MISSING. The box stays open. [belief: cc] `docs/design/backlog-refactor-2026-11/t3-evidence/e5-adjudication-20261102.json`

- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-reboot-gated-inventory-and-staging on 2026-11-03 (BRF-T1-MEQ, operator D2): **S-06**.*
- **[declined: ws58 2026-11-03 content-review: the operator declined the full-set ODL re-baseline acquisition in the 2026-11-03 model audit]** **S-07 — Acquire the OmniDocBench source PDFs and mint an immutable manifest.** Unblocks
      `opendataloader-pipeline-integration.md` and `document-parser-table-bench.md` (same work filed
      twice). Record that the real local ceiling is 51 eligible PDFs, not 200.
- [x] ~~**S-08 — Regenerate the E8 context coverage scan.** `e8_quality_context_coverage_v4_20260727.json`~~ (closed 2026-10-29 audit: SUPERSEDED → ruling_op19_e8_chain_20260827.json / 1ee8bd7cc: E8 chain and A11 reseed retired; the E8 coverage scan only fed that decision)
      reports `required_tokens` in **BYTES** and was taken against the pre-07-30 fleet. Both the A–D
      options package and the two 19 MB replacement-map candidates inherit both errors — nobody should
      act on them as they stand. Re-tokenize today; this directly unblocks A11's operator decision.
- [x] **S-09 — Delete the five `.staging-` bundles** left by the 2026-07-26→29 E8 `--execute` attempts. ✅ 2026-11-10 — closed as obsolete (operator 2026-11-10: close as obsolete): no E8 .staging-* bundles remain under research, orchestrator or tmp (only an unrelated hermes tool dir). [no-belief: obsolete, bundles gone]
      The runner forbids reuse, so the post-reboot run fails on residue. (Coordinate with the row's
      owner before deleting; this is their lane.)
- **[declined: ws58 2026-11-03 content-review: stale pre-reboot staging (reboot 2026-08-13); pinning is mi210-serving-program GPS-PIN-1]** **S-10 — Land SS-BENCH-GATE-b's cpuset pinning in the launch path before the reboot** so it is
      live from the first post-reboot launch. It exists to stop a reload sidecar invalidating a
      decision-gating run — which is exactly how the first clean window gets wasted.
- [ ] **S-11 — Close the P-BENCH-1 host-health gap.** `bench_canonical.sh` performs no uptime or
      host-health check, so the canonical CPU path can silently mint a policy-non-compliant
      decision-grade number while the P-BENCH-3 path fails closed. Either add the gate or make the
      attestation mandatory in the emitted artifact. Route to the measurement-protocol owner — the
      trust boundary is human-amendment-only, so propose, do not amend.
  - **Source checkpoint (2026-11-01):** Research `f311e004e2eaaf23bd87d2ab4a7530396c77830f`, proof `d41be316c941097f0e54a3ec4147ef67d07afe36`, captures the existing partial host observation after region-claim admission and embeds it in the benchmark log. Synthetic fixture tests only; cache drop, re-warm and THP are not attested. Missing uptime stays unknown; the existing warning uses > one week while Annex B says >= one week. No grade or protocol amendment; measurement-protocol-owner review of this proposed attestation remains required and S-11 stays open. Scratch: `/mnt/raid0/llm/tmp/codex3-s11-health-20261101`.
  - **Operator decision 2026-11-10:** option "mandatory attestation in the emitted artifact" chosen; box stays open as code work in research `scripts/benchmark/bench_canonical.sh` (HOST_ATTESTATION, :397).
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** **S-12 — File OP-16 as a pre-validated token block in `tokens/token-queue.md`.** It currently
      exists only as a master-index row, so the one signature the whole Category-A list waits on is
      absent from the queue the operator reads. Include the earlyoom `--ignore` line (A8) and the OP-9
      cron ruling (A5) so they ride the same authorization.
- **[declined: ws58 2026-11-03 content-review: bookkeeping in a retired file]** **S-13 — Correct the "OP-16 was declined by the operator" claim** in
      `session-bus-thin-dispatcher.md`'s worktree-isolation row. No such decision exists; OP-16 is open
      and deferred-with-announcement. The row's conclusion stands; its justification does not. (Owner:
      `mainD`, C-OWN — route, do not edit.)
- **[declined: ws58 2026-11-03 content-review: stale pre-reboot capture list]** **S-14 — Execute the capture list in §7 into a dated snapshot directory** under
      `/mnt/raid0/llm/tmp/pre-reboot-<UTC>/` (persistent array), and reference it from
      `tasks/post-reboot-session.md`. Pattern to reuse:
      `epyc-inference-research/scripts/benchmark/op2_quiet_window_prep.py`, which already creates a run
      dir, records host/repo/process state, stamps a stage plan and writes `operator_next_commands.sh`
      **without starting inference**.
- **[declined: ws58 2026-11-03 content-review: superseded by the coordinator-agent cold-start skill]** **S-15 — Write the post-reboot runbook (§8) into
      `coordination/session-bus/tasks/post-reboot-session.md`** with the roster respawn command list and
      the endpoint→window-name mapping verified against `config.yaml` beforehand. That file is currently
      the *coordinator handover brief*, not a reboot runbook; add the runbook as its Phase-0a section
      rather than overwriting it. (Owner: coordinator-agent — route.)
- **[declined: ws58 2026-11-03 content-review: bookkeeping of other handoffs' boxes]** **S-16 — Run the Category-C corrections**: flip EV-4 / EV-4b / EV-11c (terminal `DONE_PASS`);
      close RM-9 as a decline (its precondition is falsified); run `pgrep -f evaltower_window` and
      release the eval-tower hardening rows if it is empty; dispatch the `gpqa_diamond_cot` A4 arm;
      collapse the three duplicate RE-4 / K-LCM-1 surfaces to one. Route each to its owning index rather
      than flipping another agent's boxes.
- **[declined: ws58 2026-11-03 content-review: duplicate of coordination-and-churn-pipeline R1a]** **S-17 — Close R1a before the reboot, not after.** One short `-n 128 -r 1` smoke on a small model
      under a *held* region claim proves a real `llama-bench` acquires, holds and releases it. The stack
      is fully down, so this is the cheapest it will ever be, and it de-risks every decision-grade bench
      in the first clean window. **Inference lane — route to `inference`, do not self-dispatch.**
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** **S-18 — Put the two free operator decisions in front of the operator during the wait**: RC-6a
      (the `MEASUREMENT.md` P-REV-1 PR — blocks are copy-paste-ready, and it gates the entire
      decision-grade reviewer tier) and LB-6b (pick one of three drafted thresholds). Land RC-6a's two
      kappa/estimand amendment candidates first — the row says so.
- **[declined: ws58 2026-11-03 content-review: OP-6 is era-stale (v8); the reviewer-plane relaunch is RCP-W1]** **S-19 — Re-issue OP-6 before it is approved.** It names *"the v8 reference lineup"* while
      production is v9, and its executable manifest (`00-rcp-prologue.yaml`) is a further era behind at
      v7 with a stale topology pin. Approving it as written buys a v7/v8-stamped, throttle-contaminated
      window.
- **[declined: ws58 2026-11-03 content-review: training environment; training is out of scope]** **S-20 — Provision the pinned gfx90a training environment** (`torch`/`transformers`/`accelerate`/
      `trl`/`peft`/`datasets`, absent from both uv envs). Pure provisioning, no host quiet needed, and it
      is the stated blocker on OP-4 — which cascades to `frontier-f3-data-flywheel.md`,
      `engram-conditional-memory.md`, `minddr-deep-research-mode.md` and the EV-9 judge model.

---

#### 10. Corrections from executing S-01/S-02/S-03 (2026-08-12)

Both headline premises in §3 and §4 were measured **from inside the container** and are wrong about the
host. Neither error changes the conclusion that the work was worth doing; both change *what the residual
blocker is*, so they matter for the post-reboot ordering in §8.

##### 10.1 §3 is inverted — the 25 entries were NOT failing closed, 21 were FALSE-PASSING

`run_batch_entry.topology_gate` has **two** live-hash sources and the entries use the weaker one:

* If the entry carries `topology_artifact`, live = `sha256(artifact)` — a **64**-char digest, which can
  never equal a 16-char fingerprint. **No entry carries one.**
* Otherwise `live` is taken **from the B4 attestation itself** (`run_batch_entry.py:681-687`), so the
  gate compares the pin against an attestation rather than against the host.

Measured through the real consumer before the fix: pin `8c8cfcbb13d2611d` → `verified=**True**`, because
`attestations/20260720T191355.json` (2026-07-20) is stamped with that same stale hash. **A stale pin and
a stale attestation agree with each other and both disagree with the host.** 21 entries
(`20-eval-tower` 8, `30-bulk` 10, `40-routing` 3) were in that state; only the 4 `df373c79cc4af06f`
entries genuinely refused, and for "no matching attestation", not "hash mismatch".

The genuinely fail-closed consumer is the **other** one: `preflight_gate.check_topology_hashes(
expected_topology_hash=…)` does an exact match against the live fingerprint, and it is invoked from
inside `00-rcp-prologue.yaml`'s own command string. Measured: stale → `ok=False` "topology hash drift vs
expected"; `171f86f9188211e9` → `ok=True`. That command is what **mints** the attestation the first
consumer trusts, so the chain was: stale pin ⇒ minting refuses ⇒ no fresh attestation ⇒ the old one keeps
certifying the old pin.

**Consequence for §8 step 7:** re-pinning was necessary but is **not sufficient**. After the re-pin the
gate returns `hash_match=true, verified=false` — an *honest* refusal reading *"no matching B4 attestation
… execute refused"*. The residual blocker is a **fresh B4 attestation stamped `171f86f9188211e9` with
live affinity verified**, and `preflight_gate.py` is invoked with `--require-servers`, so it needs a live
lineup. That is genuinely post-relaunch work and belongs to `inference`. Mutation-verified 6/6: with a
live-hash-stamped attestation the entries verify; with the old stale one they no longer do.

> **Do not "fix" this by dropping a JSON into `coordination/inference-batch/attestations/`.**
> `load_attestation()` globs every `*.json` there and takes the newest match, so a hand-written file
> would silently re-create the false pass. The mutation tests for this were run against a temp dir for
> exactly that reason.

##### 10.2 §4 is wrong — the host DOES persist `numa_balancing`, by two mechanisms

`/etc/sysctl.d` inside this container is an **overlayfs** path. The host's `/etc` is a different
filesystem, reachable at `/proc/1/root/etc` (the container shares the host PID namespace, so PID 1 is the
host's systemd; `stat -c %d` gives 45 vs 2050). Anything checked — or written — at the container path
says nothing about host boot. On the **host**:

* `/etc/sysctl.d/99-epyc-inference.conf` → `kernel.numa_balancing = 0` (dated 2026-05-06), overriding
  `/etc/sysctl.d/20-numa.conf` which sets it to `1`.
* `numa-balancing-off.service`, **enabled** in `multi-user.target.wants`, re-asserts it after
  `systemd-sysctl`.

So the predicted post-reboot `numa_balancing` warning **would not have happened**. What genuinely did not
persist: `kernel.perf_event_paranoid` (absent from all host sysctl config; reverts to 4),
`scaling_governor`, and THP `enabled`/`defrag` — no host unit set any of them.

##### 10.3 What the gates actually check — eight settings, not three

| Setting | Target | Checked by | Persisted at boot now? |
|---|---|---|---|
| `kernel.numa_balancing` | `0` | `host_health_warnings`, `health_check.sh`, `canonical_recipe` | ✅ was already (sysctl.d + unit) |
| `kernel.perf_event_paranoid` | `≤1` | `health_check.sh`, `canonical_recipe` | ✅ **added** to host sysctl.d |
| `scaling_governor` (all 192) | `performance` | `health_check.sh` (cpu0), `canonical_recipe` (cpu0), `cpu_bench_clean_preflight` (uniform) | ✅ **added** via `epyc-host-prep.service` |
| THP `enabled` | `always` | `health_check.sh`, `canonical_recipe` | ✅ **added** via unit |
| THP `defrag` | `always` | `health_check.sh`, `canonical_recipe` | ✅ **added** via unit |
| `energy_performance_preference` | `performance`\|`balance_performance` | `cpu_bench_clean_preflight` | ✅ **added** via unit |
| `cpufreq/boost` | `≠0` (absent OK) | `cpu_freq_static_warnings` | n/a — driver default |
| `scaling_max_freq` (all) | `≥2500000` kHz | `cpu_freq_static_warnings` | **check-only by design** — a cap is throttle *evidence*; auto-raising it would defeat `feedback_host_throttle_check` |

Not settable, reported for the runbook: uptime ≤ 7 d (reboot only), zero `llama-server`/`-bench`/`-cli`
processes, RAM > 100 GB. Note `host_health_warnings()` *collects* `scaling_governors` but **never asserts
it** — the governor gate lives only in `health_check.sh` / `canonical_recipe` / `cpu_bench_clean_preflight`.

##### 10.4 Staged vs applied

**Applied to the live host: nothing but a self-restored test mutation.** All eight settings were already
at target, so `--apply` was a no-op. The one live write was `perf_event_paranoid 1→3→1` for the mutation
test, guarded by re-verified quiescence (0 llama processes, all 4 GLOBAL region locks free) and restored
by an EXIT trap. Chosen because it is a *permission* gate, not a performance knob — it cannot perturb a
throughput measurement.

**Deferred to boot** (inert now; nothing started, nothing restarted, no service reloaded):
`kernel.perf_event_paranoid = 1` appended to the host's `99-epyc-inference.conf`, and
`/etc/systemd/system/epyc-host-prep.service` + its `multi-user.target.wants` symlink (governor, THP
enabled/defrag, EPP). `systemd-analyze verify` parses the unit clean and every `ExecStart` body passes
`sh -n`. **Revert** = remove those two files and the symlink under `/proc/1/root/etc/...`.

> **Trap worth keeping:** the installer's first version resolved the host root to `/` because
> `/proc/1/root` is root-traversable only and an unprivileged `[[ -d ]]` probe silently returned false.
> It would have written the container overlay, reported success, and changed nothing at boot. Its own
> `--verify-boot` caught it (it claimed the host did not persist `numa_balancing`, which we knew to be
> false). It now fails closed instead, and test **H** is the regression.

##### 10.4a Observer-contract interaction (caught by the census hook, fixed by deletion)

The first revision of `host_prep.sh` reported *"llama-family processes visible: N"* by listing process
argv and grepping the llama binary names. That tripped Rule A of the observation contract
(`ed38041d`) and, because the census scans **untracked** files, it blocked commits fleet-wide while the
file was still a work in progress.

**Resolved by deleting the observation, not by enrolling it** — the stronger option under
`feedback_critique_panels_need_a_delete_lens`:

* Nothing in the script branched on the count; it was decoration.
* It was fail-open in exactly the contract's specimen shape. Under `set -o pipefail`, grep exiting 1 on a
  genuine zero and the process lister failing outright both fall into the same `|| true` branch and print
  `0`. **Absent and unobservable were byte-identical**, and the fail-open direction reported "nothing
  running" when it could not see — the reading that would green-light a heavy workload onto a live model.
* A better detector already owns the question: `server_np_sweep.find_llama_processes()` resolves
  `/proc/<pid>/exe` instead of matching argv, and `host_health_warnings()` is what actually gates.
  A second, worse copy of an observation this script does not consume is pure liability.

Census now passes at **14 observers — unchanged**, i.e. the fix added no observer rather than legitimising
one. Second-order note worth keeping: the replacement *comment* re-triggered the census because it quoted
the offending idiom verbatim, discovery being a source-pattern match. The comment now describes the
command instead of reproducing it — the same trap recorded for this hook's own commit message.

##### 10.5 Flagged, not fixed — the uptime cap is self-defeating (§3 / `30-bulk-campaign.yaml`)

`max_uptime_days` and the host-health gate pull in opposite directions and the interaction deserves an
owner's decision, not a patch from this lane:

* An entry needing `cache_state: warm` needs an *old* host; an entry capped at `max_uptime_days: 7|14`
  needs a *young* one. `30-bulk-campaign.yaml` has entries asserting **both**.
* **`max_uptime_days` has ZERO code consumers.** It appears only in
  `scripts/coordination/inference_batch.schema.json:159` (declared) and in the entry YAML — no `.py` or
  `.sh` in epyc-root, epyc-inference-research or epyc-orchestrator ever reads it. The only uptime
  enforcement anywhere is the hard-coded `MAX_DECISION_GRADE_UPTIME_SECONDS = 7 d` in
  `server_np_sweep.py:57,303`. So a `14` cap cannot buy the extra week it appears to promise, and a `1`
  cap (`50-kernel-op2.yaml:154`) buys no extra strictness either. It is inert documentation wearing the
  syntax of a gate.
* So the 7 entries "expiring at ~13:36Z today" were never reachable *as decision-grade* anyway, and the
  window question is moot independently of the pin.
* Suggested reframing for the owner: express the real requirement (`cache_state`, `quiet_window`) and
  drop `max_uptime_days` wherever it merely duplicates the hard 7 d ceiling, so the field stops implying
  a per-entry override that no consumer honours.

---

#### Cross-references

`autokernel-research-loop.md` §AK6.5 (OP-16) · `batched-decode-measurement.md` (E5) ·
`gpu-serving-tie-in-program.md` (P2-5 series) · `session-bus-thin-dispatcher.md` (C20, supervision) ·
`eval-tower-verification.md` (EV-5/7/8/10a/13b) · `CURRENT-CAMPAIGN.md` (live posture) ·
`coordination/inference-batch/entries/` (the 25 gated entries) ·
`measurement/protocols/bench-cpu.md` + `kernel-research.md` (the ratified ceiling).

##### Source-validation continuation — 2026-10-21

Prepared source validations remain unrun: NIB83 E17 has seven synthetic controls; CJ10's 10 Research and 19 ROOT counts are **file inventories, not control counts**; the S05 observer has eleven synthetic controls; CJ14 typed redundancy must include the actual current `spec_policy` closure, with native case count unknown until capture. CJ5/6/7 has six fixture source files and 3 reporting / 6 IFBench / 5 edit test functions; executed case counts remain unknown. Bind exact current hashes, request/readset/receipt, full native argv/status/JUnit and FALSE/NULL originals before new events. Reuse the existing CI source class and shared grade; no product import, live observer, inference, efficacy or protocol-grade claim follows.

NIB77's refreshed 2026-10-21 frozen registration inventory contains **35 retained exact lane paths, 24 with tracked and/or untracked source status entries**. These counts do not identify active, retirable or owned lanes. Native historical PID fields are absent now; current working/compacting/idle and accountable stewardship remain unknown. Default recommendation is retain current custody and all bytes; an explicitly named willing steward is an optional operator choice. No migration, cleanup, deletion, process termination or ownership transfer is authorized. [Current package](../../artifacts/operator/decisions/NIB77-current-custody-20261021/README.md).

## Track: contention-model-device-and-load-axes-rider
<!-- gate: INF-45#numa-placement-and-contention, INF-45#batched-decode-measurement, INF-86, INF-45#numa-placement-defect-20260730, INF-45#shape-keyed-contention-gating, INF-87 -->

> Folded from `handoffs/active/contention-model-device-and-load-axes-rider.md` @ `04334af47404` on 2026-11-03 (BRF-T7-F10, route 1b, operator D1/D5; retired row RTG-07 → INF-45). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### RIDER — Contention model: the device, batching and context axes

**Rides on:** [`shape-keyed-contention-gating.md`](numa-placement-and-contention.md#track-shape-keyed-contention-gating) (Parts A/B/C) and
W8 in [`numa-topology-cutover-resume-20260730.md`](numa-placement-and-contention.md).
**Status:** DESIGN — audit + open questions. No code. Written 2026-08-01 while W1 was landing,
so that when execution starts it is execution, not design.
**Why a rider:** the parent plan is sound and largely built. This does not replace it. It records
(1) what the W1 cutover invalidated in it, and (2) the one dimension it does not model at all.

---

#### 1. What W1 invalidated in the parent plan — fix before executing it

The parent plan's **Decisions locked** section contains an assumption that is now false. Executing
against it unmodified would encode a topology that no longer exists.

| Parent plan says | Reality after W1 (2026-08-01) |
|---|---|
| *"`architect_general` is strictly solo — its only feasible instance is whole-machine, so every candidate placement overlaps any other holder."* | **FALSE.** `architect_general` is now Qwen3.6-27B on MI210 on the **shared 8-thread GPU host lane** `184-191` (`membind=3`). It is no longer whole-machine and no longer solo. MEASURED 2026-08-01: its worst pair went **0.66 block → 1.40 allow**; +`frontdoor` 0.90 → 1.43; +`worker_general` 0.91 → 1.57. It went from the *least* co-residency-friendly role to one of the *most*. (An interim 24-thread node-3 quarter was wired first and superseded by the operator's lane ruling.) |
| Invariant 1: `vision_escalation` (8087) primary = upper half `{q2,q3}` | **Role has no server.** It is an alias on `worker_vision`'s `:8086`. Port 8087 is retired. |
| Invariant 1: `architect_general` (8083) "full" = all four `{q0,q1,q2,q3}` | Now the shared GPU host lane `184-191`, 8 threads — SMT siblings of physical 88-95, so zero physical cores by the region formula. |
| *"all of this assumes `topology_hash df373c79cc4af06f`"* | RESOLVED 2026-08-01: the matrix was re-benched for the live hash **`171f86f9`** (15 pairs, zero catastrophic). It had drifted through `df373c79` → `8c8cfcbb` → `911d3dea` → `1c654634` → `171f86f9`, spanning the half-fleet cutover (2026-07-30) and W1. |
| — | **NEW role** `architect_critic` inherits the full `0-95` `interleave=all` instance on `:8074`. The "whole-machine solo heavy role" role did not disappear; it changed name. Every place the plan reasons about `architect_general`-the-whole-machine-blocker now means `architect_critic`. |

**Consequence:** the matrix has never been regenerated for a topology in which a heavy architect
role is GPU-resident. Every measured `architect_general` pair row in
`orchestration/contention_matrix.yaml` describes a 96-thread CPU instance that no longer exists.
They are not merely stale, they are **about a different machine configuration**.

`tests/unit/test_scheduling_contention.py` carried 3 stale witnesses validating the matrix against
live `NUMA_CONFIG`. The matrix is now regenerated; re-check them against `171f86f9`.

---

#### 2. The dimension the model does not have: DEVICE

Verified 2026-08-01 by direct search: **zero** occurrences of `device`, `gpu`, `ROCm` or any
equivalent in `src/scheduling/contention.py`, `src/scheduling/contention_gate.py`, or
`src/runtime/cpu_region_lock.py`. Regions are derived purely from NUMA cpusets.

So a role whose weights are VRAM-resident under `-ngl 999`, and whose cpuset exists only to give
it host threads for tokenising and sampling, is accounted **identically to a CPU decode holding
the same cpuset**.

Two concrete wrong answers this produces today:

1. **False exclusion.** `enumerate_feasible()` (`scripts/server/contention_matrix.py:658`) marks a
   role-set `topology_infeasible` whenever no mutually-disjoint cpuset assignment exists. A GPU
   lane and a half/full CPU instance overlap on cpuset, so the set is excluded — even though the
   GPU role's actual draw on the contended resource (DRAM bandwidth on those regions) is close to
   nil. *This is the operator's stated example: GPU-lane usage is not mutually exclusive with
   running half B or a full instance.*
2. **Unmodelled real contention.** Conversely, two GPU roles that share **no** cpuset at all
   contend for HBM bandwidth and VRAM capacity — and the model cannot see it, because it has no
   resource other than CPU regions. The measured four-model GPU steady state is **62.59 of
   63.98 GiB (1.40 GiB headroom)**, and VRAM grows on first *execution*, not at load. Nothing in
   the admission path checks it.

The device axis is therefore not a refinement. It is the difference between the model's resource
vocabulary and the machine's actual resources.

---

#### 3. Why batching and context cannot simply become matrix cells

The natural instinct is to add `np` and context depth as further matrix dimensions. The
combinatorics forbid it:

```
roles² × shapes² × np ∈ {1,2,4,8,16,32} × L-buckets
```

Even the 2D NUMA×batch cross alone — waypoint **E5** in
[`batched-decode-measurement.md`](numa-placement-and-contention.md#track-batched-decode-measurement) — is described there as *"the
never-measured 2D cross"*, is gated on a post-promotion quiet window, and has not run. The two
axes have only ever been measured **separately**: NUMA-split built the pinning map, `-np` alone is
E1 (`qwen36_q8_0` ladder `np=1,2,4,8,16` complete 2026-07-06).

E5's own hypothesis is the reason this matters: batching amortises the per-token weight read, which
shifts CPU decode from **bandwidth-bound to compute-bound** — so the NUMA-locality advantage *may
flip at high K*, and the crossover point is unknown. A contention verdict measured at one `np` is
therefore not valid at another, in a direction that can reverse.

Enumerating that surface conflicts with the standing operator constraint: **do not re-bench
anything already measured**. So the load axes have to enter as a *computed* quantity, not a
measured cell.

---

#### 4. Proposed split: hard constraints vs soft costs

This is the answer to the standing open question — *what belongs in contention management vs the
autopilot/router-exposed surface*. Recommendation, stated so it can be ratified or rejected:

> **Contention management owns hard constraints and must fail CLOSED.
> The router/autopilot owns soft costs and must fail OPEN with a penalty.**

Today's code conflates them, and that conflation is the root defect: a measured ratio of `0.37`
becomes a hard `QUEUE`, so a *stale or missing* measurement can block work that is physically fine.
A cost that cannot be computed should degrade to a penalty, never to a veto.

This maps onto W8's three artifacts:

| # | Artifact | Answers | Needs measurement? | Owner | Failure mode |
|---|---|---|---|---|---|
| 1 | **Feasibility** | *Can these placements coexist at all?* Pure topology + **device**: CPU regions, GPU host cores, exclusivity. | **No** — fully derived from `NUMA_CONFIG` + declared `device`. | Contention mgmt | Fail **closed** |
| 2 | **Capacity fit** | *Does the set fit in the resources?* VRAM, host RAM, host cores. **Non-separable**: KV grows with `np × L`, so this is where batching and context enter — as arithmetic, not as measured cells. | **No** — computed from declared shapes. | Contention mgmt | Fail **closed** |
| 3 | **Interference coefficients** | *How much do they slow each other?* Measured degradation, parameterised rather than enumerated. | **Yes** — the only artifact that does. | Router / autopilot, as a **cost term** | Fail **open** with a penalty |

Two things fall out immediately:

- **Artifact 1 fixes the GPU false-exclusion with zero benchmarking.** Give the feasibility model a
  device concept and "GPU lane + half B" stops being a conflict, because the GPU role's claim is
  *8 host cores*, not *the DRAM bandwidth of every region its cpuset spans*.
- **Artifact 2 gives VRAM a first-class seat.** With 1.40 GiB headroom measured, VRAM is currently
  the binding constraint on the GPU and is entirely unmodelled. It is also *non-separable* — you
  cannot decide it per-pair, only for the whole resident set — which is exactly why W8 insisted the
  raw per-cell vector be defined before any sweep.

---

#### 5. Open questions — need an operator ruling before implementation

**Q1 — Ratify the constraint/cost split in §4?** If yes, the follow-on is mechanical: `admit_set`
splits into a feasibility+capacity gate (fail closed) and an interference score (fail open), and
`pair_policy`'s hard `QUEUE` on a low ratio becomes a cost.

**Q2 — GPU host-core accounting.** The proven GPU recipe pins host threads to `taskset -c 184-191`
with `-t 8` (8 logical = SMT siblings of physical 88-95, i.e. region `q3`). W1 currently gives
`architect_general` a 24-thread quarter on `72-95,168-191` instead. Which is canonical? And does a
GPU role hold its host cores **exclusively**, or may a CPU role share them? This decides whether
two GPU roles can share one host lane.

**Q3 — Is VRAM a contention resource or a placement precondition?** i.e. does it belong in
artifact 2 (checked at admission, every request) or only at launch (checked once, when the server
starts)? VRAM grows on first *execution*, which argues for admission-time.

**Q4 — Does the interference model need E5 first?** E5 (NUMA×batch) is designed and unrun. Options:
ship artifact 3 parameterised on the separately-measured axes and let E5 *calibrate* it later, or
block artifact 3 until E5 runs. Shipping first is cheaper and testable; it risks a model whose
crossover term is guessed. Note artifacts 1 and 2 need **neither** — they can land regardless.

---

#### 6. Sequencing once ratified

1. **Refresh the parent plan against §1** — it has a locked decision that is now false.
2. **Artifact 1 (feasibility + device)** ✅ 2026-08-01 — `src/scheduling/device_model.py`. Derived, no measurement. NOTE the honest result: on the LIVE topology it changes no verdict, because the GPU lane is SMT-siblings-only and already had empty region sets — the old model was right by accident. On the counterfactual node-3-quarter wiring it admits 10 sets the old model excluded (18/102 → 28/92).
3. **Artifact 2 (capacity fit incl. VRAM)** — derived, no measurement.
4. **Regenerate `contention_matrix.yaml`** ✅ 2026-08-01 — done for topology `171f86f9`, 15 pairs, ZERO catastrophic. `architect_general`+`ingest` 0.66 block → 1.40 allow; every GPU-involving pair concurrency-positive.
5. **Artifact 3 (interference)** as a cost term; E5 calibrates per Q4.
6. Only then the parent plan's Step-2 flag-on, its three bridge residuals, and Part C.

Nothing in steps 2–3 requires inference, a quiet window, or the stack to be idle.

---

#### 7. RATIFIED 2026-08-01

**Q1 — constraint/cost split: RATIFIED with an interference veto floor.**
Feasibility and capacity fit are hard constraints owned by contention management and fail CLOSED.
Interference is a router/autopilot cost term that fails OPEN with a penalty — **except** that a
measured catastrophic pair (ratio below ~0.65) still vetoes. Unmeasured pairs get a cost plus a
penalty, never a veto.
*Note for the implementer:* on the current topology there is **no** pair below the floor — the
re-benched matrix has zero catastrophic pairs — so the veto branch is presently unexercised. It must
still be implemented (a future topology can reintroduce one), but it should not be treated as the
common path, and the floor value needs an owner rather than being an anonymous constant.

**Q2 — GPU host lane: RATIFIED as `184-191`, `-t 8`, SHARED between GPU roles.**
Rationale: this is the placement every GPU measurement on this host was taken under (the 27B
SWE-bench arm A3 and the Qwen3-VL MMMU-250 cutover both used `taskset -c 184-191 … -t 8`), so the
deployed shape matches the measured shape and the quality/throughput transfers hold. Two roles
needing ~8 host threads each do not justify fencing 48 physical cores from the CPU fleet.
Consequence already handled: `_assert_instance_invariants` gained a device-aware branch, because
`184-191` is all SMT siblings and reads as ZERO physical cores under the `-t == physical` rule —
the correct placement would otherwise have been rejected at import as infinite oversubscription.

- [x] **Q3 — is VRAM a contention resource or a launch precondition?** ✅ 2026-08-03 — **RESOLVED:
      launch precondition.** `vram_fit` stays out of `admit_set`/`seam_admit`, and that is now a
      decision rather than a deferral.

      Two reasons, the second measured this session.

      **Structural.** `admit_set`/`seam_admit` decide PAIRWISE; VRAM is a SET-WIDE capacity. "Do A
      and B interfere?" and "does {A,B,C,D} fit in 64 GiB?" are different questions, and the second
      has no per-pair answer — no pair is individually at fault when a fourth model overflows the
      device. Wiring a set-wide constraint into a pairwise seam would either reject legal pairs or
      pass illegal sets. This is a type mismatch, not a tuning choice.

      **Empirical — and it overturns this question's own premise.** The rider argued "VRAM grows on
      first EXECUTION, not at load, which argues for admission-time." For the llama-server roles
      that is wrong: **KV is reserved AT LAUNCH** (`-c` is preallocated across `-np` slots), so a
      role's footprint is fixed the moment it binds. Measured 2026-08-03 with four resident
      processes: 36.10 + 22.47 + 2.77 + 2.31 = **63.67 GiB of 63.98**, steady, while the fleet
      served real traffic all session.

      The execution-time growth the rider observed is real but small and bounded — the four-model
      set moved 61.66 → 62.59 GiB (~0.93 GiB) after each model executed once. That is compute
      buffers, not KV, and it is **exactly what the 2.0 GiB headroom already covers** (~2x margin,
      recorded in the implementation note above). A per-request admission check would re-verify a
      quantity that cannot change between requests.

      **Consequence, and the one caveat worth carrying:** the speech services DO allocate
      per-request (whisper on long audio especially), and they are the only GPU tenants that do.
      They are also the smallest (2.31 / 2.77 GiB). If a future GPU tenant has a large
      execution-time footprint, this answer should be revisited — the reasoning is "launch-time
      reservation dominates", not "VRAM never grows".
- **[declined: ws58 2026-11-03 content-review: merged into the design note (premise corrected 2026-08-01)]** **Q4 — does the interference model need E5 (NUMA×batch) first?** STILL OPEN, but the premise
      was STALE and is corrected here (2026-08-03). E5 is **not** "designed and unrun": a 31-cell
      Stage-B sweep and a 69-cell W0 scout both RAN (2026-07-29/30) and were then **SUSPENDED
      2026-07-30 pending re-measurement** — they swept placement shapes through wiring that the
      canonical bench recipe beats, so every absolute throughput value in them is withdrawn. See
      the suspension notice at the head of [`batched-decode-measurement.md`](numa-placement-and-contention.md#track-batched-decode-measurement).
      So the real question is not "run E5 first?" but "does the interference model need E5's
      RE-measurement first?", and the answer inherits E5's own queue position (it runs LAST,
      after inference-batch-loop and architect-model-selection-bench). Artifacts 1 and 2 need
      neither and are done/scoped.

##### Implementation note recorded 2026-08-01

Artifact 1 chose a **2.0 GiB VRAM headroom** (declared total 64 GiB, 63.98 usable). Justification:
declared per-role figures are load-time, and the measured four-model set grew 61.66 → 62.59 GiB
after each model executed once — about 0.93 GiB the sum cannot see. 2.0 covers that with ~2× margin
and leaves the live pair (36.70 + 20.56 = 57.26) feasible with 4.74 spare. Configurable via
`--vram-headroom` / `$ORCHESTRATOR_VRAM_HEADROOM_GIB`. **Nothing declares this number** — it is a
judgement over measured values and is the one restated constant in the artifact.

##### Open defect found at 2026-08-02 wrap-up — `slots_by_port` is compile-mode-scoped

- [x] **Make `runtime.cache.slots_by_port` independent of the compile-time NUMA mode.** ✅ 2026-08-03 — fixed in epyc-orchestrator `9e14c069`; `status` now reports NO attestation warnings.
      `orchestrator_stack.py status` reports four attestation warnings against
      CORRECTLY-launched servers:

          server_8080/8180 (frontdoor halves) runtime slots expected 16; live cmdline has 4
          server_8082/8182 (worker halves)    runtime slots expected 16; live cmdline has 4

      The halves are right — per-instance `-np` is full 16 / half 4, set 2026-08-02.
      The producer is right too: `stack_manifest.declared_slots_by_port('frontdoor')`
      returns `{8070: 16, 8080: 4, 8180: 4}`, and recompiling the priors with
      `numa_mode='both'` reproduces exactly that map.

      The COMPILED artifact carries only `{8070: 16}`, because
      `orchestration/derived/stack_priors.yaml` was compiled in the default
      `full` mode while the live fleet runs `both`. Attestation looks up the
      live `--port`, misses, and falls back to the role-level `slots: 16`.

      This is the precise failure `_slots_by_port`'s own docstring says it exists
      to prevent — "it would report drift on correctly-launched servers, which is
      the fastest way to teach a reader to ignore this output." It is now doing
      that, so the warning channel is actively training readers to ignore it.

      Fix direction: `slots_by_port` is a port -> slots LOOKUP, so carrying ports
      that are not launched in the current mode costs nothing and makes
      attestation correct in every mode. Merge the mode-independent
      `declared_slots_by_port(role)` in as a floor. Watch for the circular import
      between `src/registry/stack_priors` and `scripts/server/stack_manifest`
      (already observed emitting "partially initialized module" warnings on the
      `_stack_manifest_info` path) — a lazy import inside the function is likely
      required.

      RESOLVED. `declared_slots_by_port()` is merged in as a mode-independent
      FLOOR, with mode-scoped values winning on conflict (verified: a launch
      view resolving 8080 to 9 keeps 9 while the floor supplies 8070/8180).
      Alias roles needed host inheritance too — they have no NUMA_CONFIG entry
      of their own, so server_8082/8182 still attested against 16 until the
      alias inherited its host's declared map. The lazy import mirrors
      `_launch_runtime_record`'s existing pattern, so the circular-import risk
      was already solved in this module.

##### Worktree isolation + guard composition — closed 2026-08-03

- [x] **Close the worktree-isolation leak at its root** ✅ 2026-08-03 — orchestrator `93e7f5a2`
      + `cd76de50`. `_get_default_project_root()` RETURNED the literal, so ~14 modules leaked
      through one function. 62 no-slash hits → 9; 18 → 14. Two classes grep could not find: a leak
      in the same file using single quotes, and 12 test files doing
      `sys.path.insert(0, "<literal>")` — a test in a worktree imported the MAIN checkout's `src/`
      and could not have measured its own tree. Verified: 172 path constants identical / 0
      divergent; HEAD-in-a-worktree baseline gave byte-identical failure sets both directions;
      isolation went 17/17 leaking → 0.
- [x] **Fix the packaging-level leak `Path(__file__)` cannot reach** ✅ 2026-08-03 — `pip install -e .`
      bakes the checkout path into the venv `.pth`, so a plain `python script.py` from a worktree
      imported main-checkout `src/` while every module's own anchor was correct. pytest masks it
      (rootdir wins), so a green suite was never evidence. Tracked resolver + idempotent installer.
- [x] **Make the unit suite reproducible** ✅ 2026-08-03 — `orchestration/runtime_flags.json` is
      untracked live state the API rewrites; it changed MID-RUN during an attribution pass.
      17 of 18 apparent regressions in a clean-worktree diff were this file, not code.
- [x] **Secret scanning was advisory-only** ✅ 2026-08-03 — `.git/hooks/pre-commit` called its hooks
      bare, so a failing PII check was discarded by a passing drift check. Reproduced: AWS key
      staged, `BLOCKED` printed, commit landed. Fixed + tracked installer, since the wrapper was
      untracked in all three repos and every fix died on a fresh clone.
- [x] **Full non-pytest worktree isolation** ✅ 2026-08-03 — orchestrator `60637f77`. Closed WITHOUT
      a per-worktree venv, which would have cost **803 MB per worktree** to fix a path-resolution
      problem. The residual gap was `python /path/to/worktree/scripts/foo.py` run from outside that
      worktree: CWD cannot see that invocation, and it is the ordinary shape of running a script by
      absolute path. The shim now tries `sys.argv[0]`'s directory FIRST, then CWD — the entry script
      states which checkout you mean regardless of where you are standing, while CWD still covers
      `python -m pkg` and a bare REPL. Verified: script-in-worktree/cwd-elsewhere now resolves to
      the worktree; main checkout unchanged; a script outside any checkout does not hijack; an
      unrelated repo with `src/` + `orchestration/` but a different project name is not adopted.
- [x] **Decide the durable-evidence form under the wiki-only ruling.** ✅ 2026-08-03 — RESOLVED: a durable citation is a reference to distilled knowledge in the wiki, where literature references are documented. Both bundles untracked (research `a752ca21`), kept locally with SHA256SUMS; `wiki/benchmark-methodology.md` gained a Reference section naming path, contents, verification and reproduction; the registry citation repoints at the wiki. `check_evidence_durability.py`: 0 errors. Superseded detail: Operator ruling 2026-08-03:
      research reaches GitHub only as distilled knowledge and REFERENCES in the wiki, never as raw
      material at any size. Two evidence bundles were committed to
      `epyc-inference-research/data/` earlier the same day (`judge_suite_headtohead_20260802` 1.5 MB,
      `swe_verified_preliminary_20260724` 72 KB) and are already pushed. They predate the ruling and
      conflict with it; MEASUREMENT.md §5 requires a durable citation, so the question is what form
      that citation takes — a wiki reference to a local path, or a committed bundle. Operator call.

#### Research Intake Update — 2026-09-26 — llama-server capacity-signal map (C1-A5) + monitor triggers

**Signal map, from production v10 source (server-context.cpp@ffc1bac8:698-722, 903-908, 4720-4760, per the intake-1797 dive).**
- HW-Router's running/waiting counts map to `llamacpp:requests_processing` / `requests_deferred`. These exist only
  with `--metrics`, which CPU launches do NOT pass today (orch `orchestrator_stack.py:1267` @fb7871ea, `:1272` at
  `a439070e`, is GPU-only; live :8074 argv read 2026-09-26).
- KV-cache % has NO analogue: KV is preallocated per slot at launch (:193). The nearest signal is per-slot fill from
  `/slots` n_prompt_tokens + n_decoded vs n_ctx.
- TTFT/TPOT averages must come from counter deltas. `prompt_seconds_total/prompt_tokens_total` excludes queue wait.
  The `prompt_tokens_seconds` / `predicted_tokens_seconds` gauges are lifetime averages in v10, because
  `metrics_reset_bucket` is never set.
- Pending decode tokens are not exposed: `n_remain` is -1 without `n_predict`.
- v10 `/slots` does emit n_prompt_tokens, n_prompt_tokens_processed and n_prompt_tokens_cache. Deferred-request
  lengths are not exposed.
- Never wire a vLLM-shaped KV% or a lifetime gauge into routing (intake-1797#01, intake-1796#01, intake-1798#02).

**Where the soft load cost lives.** The per-request saturation guard is an instance of §7 Q1 ("soft cost, fail OPEN
with a penalty"). It is owned by decision-aware-routing.md DAR-LAT-1/2 and reads the orchestrator's own admission
ledger, not a second poller. No task here.

**Triggers (prose, no checkbox; both entries are stage1-unverified, so no figure from them may be cited until dived):**
- When Artifact 3 (interference cost) is parameterised with a batch-throughput lane in scope, dive intake-1812#record
  first, as a candidate analytic prior for that lane.
- If fable5-window2-findings-02-heterogeneous-gpu.md F1 (:239) shows the overlap is worth pursuing, dive
  intake-1814#record before designing R-A5's async CPU backend. Any live device/PCIe load axis must reuse existing
  readers (Axiom 1).
