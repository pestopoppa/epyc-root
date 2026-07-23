---
title: WP-12 — Server-fleet layer (derive backends from the physical fleet, not per-role URL copies)
status: design (implementation deferred — operator-gated to post-measurement-chain)
created: 2026-07-22
owner: within-role-placement-state-machine (WP-12 line item)
kind: design-only  # NO implementation, NO src edits in this handoff
operator_authorization: op-bundle ESC-8 (2026-07-22) — "WP-12 sequencing (a): design doc now, implementation after the measurement chain completes"
constitution: operator-endorsed 2026-07-22 (quoted verbatim below)
predecessors:
  - handoffs/active/within-role-placement-state-machine.md      # WP-8..WP-14, mode-exclusivity contract, DISPATCH-A/A2/A3
  - handoffs/active/wp9-wp10-lineup-event-prep.md               # fleet-shape recert cascade (WP-9/WP-10)
supersedes_on_land:
  - WP-13 (stack_priors alias-ports inheritance) — durable fix + interim Fix-A field delegations + parity drift-guard test
  - WP-14 (runtime-facts phantom-lineup writer) — subsumed by fleet-from-registry (reader hardening still useful standalone)
---

> **CONSTITUTION (operator-endorsed 2026-07-22 — governs every decision below):**
> *"Roles as a remappable logical layer over servers is sound design."*
> Roles keep their per-role SLAs/timeouts, prompts, sampling, priority, and **remappability**
> (worker_math's historical Qwen2.5-Math binding is the canonical ghost — a role that can be
> re-pointed at a different model/server without touching the physical layer). The **physical
> fleet is defined ONCE and referenced**; roles never carry private copies of the wiring.

---

## Executive summary (10 lines)

1. Today each orchestrator role carries an **independent COPY** of its server wiring: a URL-string field in `ServerURLsConfig` (`src/config/models.py`), an independent `ConcurrencyAwareBackend` (CAB) built per-role in `_init_caching_backends` (`src/llm_primitives/backend.py`), and — through those copies — a fragmented view of the same physical endpoints' health, topology idxs, and region-lock identity.
2. Roles that share ONE physical server (registry `server_mode.worker.shared_with:[worker_math,toolrunner]`; frontdoor↔coder_escalation↔worker_summarize) therefore get **N descriptions of one fleet** that silently drift apart.
3. Shipped failures from that drift: worker_math's stale 2-endpoint copy **serialized its EV-11c arm (~4h)**; same-fleet `forced_role_fallback` churned **~90x** (role A's object trips while role B's object for the same server stays "healthy"); WP-10's worker_math has **no region locks at all**; ESC-8's env producer can **clobber the truth** and wire every role to dead full ports.
4. **Design:** split into a **Fleet layer** (defined once from the registry `server_mode` SoT: endpoints + quarter/full shapes + topology idxs + **ONE** health/breaker state per physical endpoint + **ONE** region-lock identity + demotion/alignment machinery) and a **Role layer** (role → fleet reference + per-role policy: SLA/timeout, prompt/template, sampling, priority, optional capacity cap, placement_policy override).
5. **One endpoint's health is one fact:** the breaker/circuit and the region-lock identity live on the fleet's endpoint, not on any role's copy — every role bound to that fleet reads and writes the same circuit and the same lock.
6. **Fallback becomes fleet-aware:** same-fleet fallback (worker_math→worker_general) collapses to a **no-op** (identical physical backend + identical breaker → nothing to retry); cross-fleet fallback (architect_general→coder_escalation, ingest_long_context→architect_general) stays **real**. This kills the `forced_role_fallback` noise class at the root.
7. **Construction flow:** registry `server_mode` → normalize to Fleet objects (one per physical server group, keyed by primary role + `shared_with`) → build **one CAB per fleet** → roles resolve to `(fleet_ref, RolePolicy)`; the logical role is threaded per-call so tap/timeout/prompt/sampling stay role-specific while the physical dispatch state is shared.
8. **Deletes:** the `_LEGACY_SERVER_URL_FALLBACKS` literals, the per-role URL copies + Fix-A field delegations in `ServerURLsConfig`, the per-role CAB instances for shared fleets, and (on land) WP-13's alias-ports fix + its interim parity drift-guard test. **Keeps:** the role fields — now as references — and every legitimate role-layer bit (remappability, SLAs, sampling, capacity policy).
9. **Rollout:** behind `ORCHESTRATOR_FLEET_LAYER=1` (default off), deployed **after** the EV-11c measurement chain completes, sequenced at the same terminal boundary as WP-13's regeneration + the ESC-8 package; WP-12 landing **removes** WP-13's interim, not layers on top of it.
10. **Riskiest decision:** collapse the N per-role CABs into **one CAB per fleet** (vs. keep per-role CABs sharing only a fleet descriptor). Recommendation below: **collapse** — a shared descriptor still leaves N objects with divergent per-instance dispatch state (the exact fragmentation being fixed); thread the logical role per-call to preserve role identity.

---

## 1. Current architecture (the problem, concretely)

### 1.1 Three URL producers feed per-role string copies

`ServerURLsConfig` (`src/config/models.py:597-663`) declares ~20 role fields, each defaulting to `_server_url_default(<name>)`. `_server_url_default` → `_stack_prior_server_urls()` (`models.py:429-452`), which merges, in precedence order:

1. **env/runtime-facts producer** — `_selected_server_url_values(_runtime_or_env_selected_servers())` (`models.py:316-399`). Driven by `ORCHESTRATOR_STACK_NUMA_MODE` or the runtime-facts manifest. **This is the ESC-8 landmine**: when its import path succeeds it lands FIRST and, via `urls.update(...)` before the `setdefault` from stack_priors, clobbers the truth — wiring every hot role to the dead full ports under `STACK_NUMA_MODE=full` on a quarters-only deployment.
2. **stack_priors producer** — `live_stack_serving_url_values(stack_priors.yaml)` (`src/registry/stack_priors.py:439-446`), the intended SoT (`urls.setdefault(...)` — only fills gaps the env producer left).
3. **manifest + hardcoded literal** — `_stack_manifest_server_urls()` (`models.py:402-426`) then, as the last-resort default, `_LEGACY_SERVER_URL_FALLBACKS` (`models.py:265-294`) — a frozen dict of literal `full:...` tuples per role.

Each role field is an independent string. Shared-fleet roles are wired by **delegating the default to the primary** (the interim WP-13 "Fix A"): `worker_math`, `toolrunner`, `worker_summarize`, `coder`, `coder_escalation` all call `_server_url_default("worker_general")` or `_server_url_default("frontdoor")` (`models.py:616-640`). That is a *convention enforced field-by-field in comments* — nothing structural prevents the next drift.

### 1.2 One ConcurrencyAwareBackend built per role — even for shared fleets

`_init_caching_backends` (`src/llm_primitives/backend.py:46-222`) iterates `server_urls` and builds a backend **per role key**. For every `full:`-prefixed multi-instance role it constructs an independent `ConcurrencyAwareBackend`, and independently re-derives, per role:

- `topology_role` via `_infer_topology_role_for_urls` (`backend.py:17-40`) — a **URL-tuple string match** against the set of topology roles. Robust only while every role's copy is byte-identical.
- the full/quarter split, `_port_of`, and the **DISPATCH-A2 demotion** (`backend.py:135-199`): resolve each endpoint's true topology idx by port against `NUMA_CONFIG`; demote a quarter mis-wired as `full:` into the quarters pool. This decision is recomputed per role and can differ across copies of the same fleet.
- per-instance dispatch state inside the CAB: `_session_quarter` affinity, migration counters, `_full_slot_aligned`, `_quarter_topology_idx`. **None of this is shared** between two roles pointed at the same physical fleet.

### 1.3 The breaker is per-endpoint — but reached through divergent copies

`BackendHealthTracker` (`src/api/health_tracker.py`) keys circuits by `backend_url` and is a **shared singleton** on app state (`state.health_tracker`). So at the URL layer, breaker state is *already* per-endpoint. The fragmentation is upstream of it:

- Two roles can disagree on **which endpoints exist** (worker_math's stale copy had 2 of 5 ports) → they exercise different circuits for the same fleet, and the "healthy" subset masks the "open" one.
- The `_FALLBACK_MAP` (`src/roles.py:395-402`) treats same-fleet roles as independent fallback targets: `WORKER_MATH → [WORKER_GENERAL]`, `CODER_ESCALATION → [FRONTDOOR]`. When the shared fleet is loaded/timing-out, `inference.py:401-416` retries the *same physical endpoints under a different role name* — physically a no-op, but it churns (the ~90x). `classify_failure` + the fallback loop have no notion that both roles are one fleet.
- The **region-lock identity** is the `topology_role`; cross-process CPU region locks are keyed by it (`src/runtime/cpu_region_lock.py`). Because `topology_role` is *inferred per role from URL strings*, a drifted copy can land a role on the wrong lock namespace — or, per DISPATCH-A/A2, let a quarter wired as `full:` grab idx-0's ALL-region lock and head-of-line-block the machine.

### 1.4 Net: N descriptions of one fact

For the worker fleet (gemma4, ports 8072 full + 8082/8182/8282/8382 quarters) there are today up to **four** role objects (worker_general, worker_math, toolrunner, worker_summarize is on the frontdoor fleet; coder/coder_escalation/worker_summarize sit on frontdoor's) each independently describing the same servers, each with its own topology resolution, its own CAB dispatch state, its own path to the breaker, and — for worker_math — **no NUMA_CONFIG entry and thus no region locks** (WP-10). The registry already carries the normalized truth (`server_mode` + `shared_with`); nothing consumes it as a single source.

---

## 2. Target architecture — two layers

### 2.1 Fleet layer (defined ONCE, registry `server_mode` is SoT)

A **`ServerFleet`** is the single description of one physical llama-server deployment. One fleet per distinct physical server group. Fields:

| Field | Meaning | Source |
|-------|---------|--------|
| `fleet_id` | Stable identity == the physical topology role (e.g. `worker_general`, `frontdoor`) | registry `server_mode` primary role |
| `endpoints[]` | `(port, topology_idx, cpu_regions, shape, is_full)` per live instance | stack_priors serving ports resolved against `NUMA_CONFIG` by port |
| `full_instance_idx` / `full_port` | The 1×96t/half instance, or **None** when quarters-only | `NUMA_CONFIG[fleet].full_instance_idx`, cross-checked against live endpoints |
| `mode` | `full` \| `quarter` \| `mixed` — the realized serving mode, not the static default | live endpoint set (kills the WP-14 phantom-lineup class) |
| `topology_role` | The **one** region-lock identity for every endpoint in the fleet | `fleet_id` (no per-role inference) |
| `circuits{port→BackendCircuit}` | **ONE** health/breaker state per physical endpoint | shared `BackendHealthTracker`, keyed by the fleet's own endpoint URLs |
| `placement_policy` | `full_disabled` \| `burst_prefer_quarters` \| `solo_prefer_full` \| `queue_only` | `NUMA_CONFIG[fleet].placement_policy` |
| `demotion/alignment` | DISPATCH-A2 misaligned-full demotion + `_full_slot_aligned`, computed **once** at fleet build | port↔`NUMA_CONFIG` resolution |

The fleet owns exactly one `ConcurrencyAwareBackend` (see §7 riskiest decision). The demotion/alignment machinery, the port→topology-idx resolution, and the region-lock identity are computed once per fleet and are therefore impossible to disagree with themselves.

**Construction:** `build_fleets(registry, numa_config, stack_priors) -> dict[fleet_id, ServerFleet]`. Enumerate `server_mode` rows; each row + its `shared_with` collapses to one fleet; resolve live endpoints from stack_priors (the SoT) with `NUMA_CONFIG` supplying shapes/idxs/policy. The env/runtime-facts producer is **not** consulted for fleet identity (this makes the ESC-8 precedence inversion structural rather than a setdefault-ordering accident).

### 2.2 Role layer (reference + policy)

A **`RoleBinding`** is what a role *is* once the physical layer is factored out:

| Field | Meaning | Today's home (preserved) |
|-------|---------|--------------------------|
| `fleet_ref` | Which `ServerFleet` serves this role | replaces the URL-string field |
| `model_binding` | The logical model the role currently maps to (**remappable** — worker_math↔Qwen2.5-Math ghost) | registry `model_role` |
| `timeout` / SLA | Per-role request deadline | `TimeoutsConfig.for_role` (`models.py:666-790`) — unchanged |
| `prompt` / `template` / `use_chat_completions` | Role prompt + `/v1/chat/completions` vs `/completion` | `chat_completions_roles()`, persona/prompt loaders — unchanged |
| `sampling` | temp/seed/top_p/enable_thinking | registry `chat_template_kwargs`, sampling config — unchanged |
| `priority` | Admission/queue priority | request-priority path — unchanged |
| `capacity_cap` (optional) | e.g. `max_quarters_for_this_role` — cap a role's share of a shared fleet | **new**, role-layer only |
| `placement_policy_override` (optional) | Role-scoped override of the fleet default | **new**, role-layer only |

The role's logical identity is threaded into dispatch per-call. `_tap_dispatch_metadata` (`concurrency_aware.py:982-1006`) already emits BOTH `role` (logical) and `topology_role`/`lock_role` (physical) — the design generalizes that: the fleet backend is physical, the call carries the role, so tap/timeout/prompt/sampling remain role-specific over shared physical state.

---

## 3. Breaker-state sharing semantics — "one endpoint's health is one fact"

- **One circuit per (fleet, endpoint port).** The fleet's endpoints are the *only* set of URLs any of its roles ever present to `health_tracker.is_available` / `record_failure` / `record_success`. Because all roles on the fleet resolve to the identical endpoint tuple (structurally, not by convention), the existing URL-keyed singleton becomes authoritative with no ambiguity.
- **A failure observed by any role trips the circuit for all roles on the fleet.** worker_math and worker_general no longer maintain independent "health opinions" about port 8082.
- **Half-open probing is fleet-global.** One probe per endpoint per cooldown, regardless of how many logical roles ride the fleet — no N-fold probe amplification (a contributor to the 90x).
- **The region lock is the same fact in a different dimension:** one `topology_role` per fleet means the cross-process CPU region locks are the physical truth; a role can never acquire a lock namespace that disagrees with its fleet's endpoints. DISPATCH-A2 demotion happens once at fleet build, so the "quarter-impersonating-full holds all-region lock" hazard cannot be re-created per-copy.

Invariant to assert at build + runtime: **for every fleet, `{endpoints seen by each bound role} == fleet.endpoints`** and **`{topology_role of each bound role} == fleet.fleet_id`**. Fail closed on mismatch (this is the structural replacement for WP-13's parity drift-guard *test*).

---

## 4. force_role / fallback interaction

`force_role` selects a **role** (logical); the role resolves to its fleet. Nothing about forcing a role changes — the role still carries its own prompt/timeout/sampling. What changes is fallback:

- **Same-fleet fallback → no-op (elided).** `get_fallback_roles` becomes fleet-aware: a candidate whose `fleet_ref` equals the failing role's `fleet_ref` is dropped, because retrying it hits the identical physical backend and the identical (already-open) circuit. `WORKER_MATH → WORKER_GENERAL` and `CODER_ESCALATION → FRONTDOOR` both collapse to no-ops (worker_math shares worker_general's gemma4 fleet; coder_escalation shares frontdoor's Qwen fleet). **This is the fix for the `forced_role_fallback` noise class** — the ~90x churn was same-fleet fallback masquerading as failover.
- **Cross-fleet fallback → real, unchanged.** `ARCHITECT_GENERAL → CODER_ESCALATION` (122B fleet → frontdoor fleet) and `INGEST_LONG_CONTEXT → ARCHITECT_GENERAL` cross physical fleets → genuine failover, kept. When the *fleet* circuit is open (all endpoints down), cross-fleet fallback is the only fallback that can succeed, and now it's the only one attempted.
- **Rule:** fallback is meaningful **iff** it changes the physical fleet. The fallback map is re-expressed as fleet-adjacency; same-fleet edges are compiled out at load.

---

## 5. Migration path — what gets deleted, what survives

**Deleted (the per-role copy machinery):**

- `_LEGACY_SERVER_URL_FALLBACKS` literal dict (`models.py:265-294`) — fleets come from stack_priors/registry; a literal per-role frozen tuple is exactly the drift vector being removed. (A single degraded-mode literal *per fleet* may survive as the fleet layer's own last resort — see risks.)
- The per-role URL-string fields' **independent defaults** + the Fix-A field delegations in `ServerURLsConfig` (`models.py:616-640`, the `_server_url_default("worker_general")`/`("frontdoor")` chains). Roles stop owning URL strings.
- The **per-role CAB instances for shared fleets** — the N-objects-per-fleet build in `_init_caching_backends`. One CAB per fleet replaces them.
- `_infer_topology_role_for_urls` URL-tuple string matching (`backend.py:17-40`) — topology role is now `fleet_id`, not inferred.
- **On land, WP-13 in full:** the durable `_stack_manifest_info` alias-ports inheritance fix (`stack_priors.py:836-853`, which today gives an alias only its own single port), *and* its interim Fix-A field delegations, *and* the interim parity drift-guard test. WP-12's fleet identity makes alias-port inheritance moot (aliases are role bindings that reference the primary's fleet). **WP-12 landing removes WP-13's interim, it does not stack on it.**
- **On land, most of WP-14:** the runtime-facts phantom-lineup writer's authority over role wiring — the fleet's `mode` is the realized serving mode from live endpoints, not the static full-mode default the writer records. (The two *reader* hardenings in WP-14 — `dashboard_topology.py` and `eval_tower.py` fail-closed type checks — remain worth landing independently as defense-in-depth.)

**Survives (the legitimate role layer):**

- Every role field — **reclassified from a URL copy to a `fleet_ref` + `RolePolicy`**. The role names, `Role` enum, routing, and MCP/`list_roles` surface are unchanged.
- **Remappability** — a role can be re-pointed at a different fleet/model without touching the physical layer (worker_math's Qwen2.5-Math ghost; toolrunner as a logical alias over the gemma4 fleet).
- Per-role **SLAs/timeouts** (`TimeoutsConfig`), **prompts/templates** (`chat_completions_roles`, persona loaders), **sampling** (registry `chat_template_kwargs`), **priority**, and the new optional **capacity cap** / **placement_policy override**.
- The **contention matrix / topology_hash** machinery and the WP-9/WP-10 recert cascade — fleets change *how wiring is described*, not the measured topology. (WP-12 does not itself change any cpuset, so it does not trigger the §H recert cascade; it should land in a window where the topology_hash is already settled.)
- The shared `BackendHealthTracker` singleton — now reached unambiguously.

**Ordering with the in-flight fixes:** ESC-8's precedence inversion (Fix 2) and WP-13's regeneration are the *interim* that make the current per-copy world safe until WP-12 lands. WP-12 is the durable replacement. Sequence: land ESC-8 + WP-13 interim at the EV-11c boundary (already granted); build+gate WP-12 behind its flag; flip WP-12 on and delete the interim in the same change once its acceptance gate passes.

---

## 6. Test / acceptance plan (incident-derived cases first)

Unit + integration, all runnable without live inference (mock backends, synthetic `NUMA_CONFIG`/stack_priors) except the two live gates flagged. **A live eval is running — no API calls from this design work.**

1. **Fleet collapse / parity** — `build_fleets` over the real registry yields one fleet for `{worker_general, worker_math, toolrunner}` and one for `{frontdoor, coder, coder_escalation, worker_summarize}`; assert every bound role resolves to the **identical** endpoint tuple + `topology_role`. (Replaces WP-13's drift-guard test with a structural invariant.)
2. **worker_math 4-wide** (mode-exclusivity contract, WP-8/WP-10) — 4 concurrent worker_math requests land on **4 disjoint busy quarters** of the shared gemma4 fleet, full idle; worker_math now holds real region locks (fixes WP-10). Mirror case: 4 concurrent frontdoor → 4 quarters, half0 idle.
3. **No phantom-full** — a fleet whose live endpoints are quarters-only with the first port mis-marked `full:` demotes that endpoint into the quarters pool **once** at fleet build (DISPATCH-A2), serves no full, and no role acquires idx-0's all-region lock. Assert region locks == physical cores.
4. **Single breaker state** — inject failures on port 8082 via worker_math's dispatch; assert the *fleet* circuit for 8082 opens and worker_general + toolrunner immediately observe `is_available(8082) == False` (one fact). Assert exactly one half-open probe per cooldown across all bound roles.
5. **Same-fleet fallback is a no-op** — force worker_math with the fleet circuit open; assert `get_fallback_roles` yields **no** same-fleet candidate (no worker_general retry), the request fails fast (or waits on the fleet, not on a role-name retry), and the fallback-churn counter stays ~0 (regression bound for the 90x).
6. **Cross-fleet fallback still real** — architect_general with its fleet circuit open falls back to coder_escalation's (distinct) fleet and succeeds.
7. **Mode-exclusivity contract cases** — `burst_prefer_quarters` fleet abandons full the moment a self-role holder exists; `full_disabled` never emits full; `solo_prefer_full` keeps full first at concurrency 1. Reuse the existing `test_concurrency_aware_migration_sm.py` / placement-SM suites against the one-CAB-per-fleet object.
8. **Remappability** — re-point worker_math's `RoleBinding.fleet_ref`/`model_binding` at a synthetic second fleet; assert only worker_math moves, worker_general/toolrunner stay, and no URL literal edit was needed.
9. **ESC-8 non-clobber** — with `ORCHESTRATOR_STACK_NUMA_MODE=full` set but a quarters-only stack_priors, `build_fleets` produces the quarters fleet (env cannot override fleet identity). Regression for the armed-outage class.
10. **Live gate (operator-approved window only):** single-worker API, `ORCHESTRATOR_FLEET_LAYER=1`; replay the ROUTE-A3 J2/J3 migration probe + a worker_math 4-wide burst; confirm committed migrations, 4 busy quarters, one circuit per endpoint, zero same-fleet fallback events.

---

## 7. Riskiest design decision + recommendation

**Decision: one `ConcurrencyAwareBackend` per FLEET (collapse the N per-role CABs) vs. keep N per-role CABs that merely share a read-only fleet *descriptor*.**

- *Shared-descriptor (lighter):* keep today's per-role CAB objects, but have them all read fleet identity/endpoints/policy from one `ServerFleet`. Smaller diff, preserves per-role object identity for tap/session state.
  - **Fatal flaw:** the fragmentation being fixed is *per-instance dispatch state*, not just wiring — `_session_quarter`, migration counters, `_full_slot_aligned`, and (critically) the live region-lock acquisitions live *inside the CAB object*. N CABs sharing a descriptor still hold N independent session-affinity maps and can still race each other for the same physical quarter under two role names. It reduces wiring drift but **not** the runtime-state fragmentation or the lock races.
- *One-CAB-per-fleet (heavier):* the fleet owns a single CAB; roles dispatch through it, threading their logical role per-call. Session affinity, migration state, and lock acquisition become one authoritative object per physical fleet — which is precisely "one endpoint's health/placement is one fact."
  - **Cost:** dispatch must carry the logical role through a physical backend. Mitigated because the plumbing already exists: `_tap_dispatch_metadata` emits logical `role` + physical `topology_role` separately, and timeout/prompt/sampling are already looked up by role name upstream of the backend, not inside it. Session-affinity keys stay per-`session_id` (already role-agnostic in `_session_quarter`).

**Recommendation: collapse to one CAB per fleet.** It is the only option that actually closes the runtime-state and region-lock fragmentation (the shared-descriptor variant leaves the lock races and divergent session state intact, so it would not have prevented the worker_math serialization or the 90x churn). Thread the logical role as a per-call parameter and keep role-specific timeout/prompt/sampling/priority resolution in the role layer above the backend. Gate the whole thing behind `ORCHESTRATOR_FLEET_LAYER=1` so the legacy per-role build remains the instant rollback until the acceptance gate (§6) passes.

---

## 8. Risks

- **Degraded-mode bootstrap:** deleting `_LEGACY_SERVER_URL_FALLBACKS` removes the last-resort wiring when stack_priors is absent (fresh clone, pre-launch API). *Mitigation:* keep exactly one literal fallback **per fleet** inside the fleet layer (not per role), so the degraded path still resolves without re-introducing per-role copies.
- **Per-call role threading regressions:** collapsing CABs means a bug in role-threading could cross a role's prompt/timeout onto another role on the same fleet. *Mitigation:* acceptance cases 2/7/8; keep the flag default-off until green.
- **Hidden per-role divergence that was load-bearing:** some role may today rely on a *deliberately* different endpoint subset (e.g. a capacity carve-out). *Mitigation:* that is exactly what `capacity_cap` in the role layer expresses — audit each shared-fleet role for an intended cap before collapsing; default cap = full fleet.
- **Sequencing collision with the interim fixes:** landing WP-12 without first removing ESC-8/WP-13 interim risks two systems describing wiring. *Mitigation:* the flip and the interim-deletion are one change (§5 ordering).
- **Topology_hash confusion:** WP-12 changes descriptions, not cpusets — but reviewers may expect a recert. *Mitigation:* document explicitly that WP-12 does **not** touch `NUMA_CONFIG` cpusets and does **not** trigger the §H cascade (unlike WP-9/WP-10).

## 9. Explicit non-goals

- **Not** a NUMA/cpuset change — no new topology fingerprint, no contention-matrix re-measure, no §H recert cascade (that is WP-9/WP-10).
- **Not** a change to the placement state machine, KV migration, or the mode-exclusivity contract — WP-12 consumes DISPATCH-A/A2/A3 behavior, it does not redefine it.
- **Not** a change to routing, the `Role` enum, role prompts/sampling/SLAs, or the MCP role surface — those are the *role layer* and are preserved verbatim.
- **Not** cross-server KV sharing or slot multiplexing (KVCOMM / dynamic-stack-concurrency scope).
- **Not** a registry schema change — `server_mode` + `shared_with` already carry the normalized truth; WP-12 *consumes* it, it does not extend it.
- **Not** the ESC-8 env-alignment stack-script change (Fix 1) — WP-12 makes the env non-authoritative for fleet identity, but the launch-site env hygiene is a separate stack-script task.

## 10. Reporting

### Implementation status (2026-07-23, chartered worktree session — NOT landed; flip boundary pending)

Implementation branch: `wp12-fleet-layer-impl` (epyc-orchestrator, worktree
`/mnt/raid0/llm/worktrees/wp12-fleet-layer`, rebased onto
`origin/spec-dec-mtp-refresh-2026-06-22` @ `97ce58b8` — two-test
reconciliation + solo-goes-full seam fix absorbed), head `3c0b4ce4`, pushed;
84-test targeted regression green post-rebase. The live-lock-coupling finding
this session filed was confirmed by the main session, fixed in `97ce58b8`, and
generalized to a filed three-seam-hermeticity task for the whole file
(`5adf81aa`).
Flag `ORCHESTRATOR_FLEET_LAYER` default OFF everywhere; no env wiring into launch
scripts; flag-off behavior verified byte-identical (existing placement/migration/
demotion suites: 130 passed; the 2 failures — frontdoor drift-guard vacuity check +
vision quarter-preference — pre-exist at the base commit, verified by stash-run).

- [x] §2.1 `ServerFleet` build from registry `server_mode` SoT (`src/fleet.py`; env/runtime-facts producers structurally not consulted; port-resolved `is_full`; per-FLEET degraded literal) ✅ 2026-07-23
- [x] §2.2 `RoleBinding` policy layer (fleet_ref + model_binding; `capacity_cap`/`placement_policy_override` carried as data, enforcement deliberately deferred) ✅ 2026-07-23
- [x] §3 one breaker/lock identity per fleet endpoint (CAB `health_tracker` injection, per-dispatched-endpoint recording, circuit-aware SM candidates, all-open fail-fast; §3 parity invariant fails the build closed) ✅ 2026-07-23
- [x] §7 one-CAB-per-fleet collapse (flag-gated `_init_fleet_backends`; logical role threaded per-call; use_chat_completions fleet-consensus-or-fail-closed) ✅ 2026-07-23
- [x] §4 same-fleet fallback compiled to no-ops (`compiled_fleet_fallback_map` + flag-gated `get_fallback_roles`) ✅ 2026-07-23
- [x] §6 acceptance cases 1–9 as offline/mocked tests (33 tests: `test_fleet_layer_build.py` 1/3/8/9+parity+degraded, `test_fleet_layer_dispatch.py` 2/7+flag-off identity, `test_fleet_layer_breaker.py` 4+5-fail-fast, `test_fleet_layer_fallback.py` 5/6) ✅ 2026-07-23
- Explicit decline (2026-07-23): per-request `use_chat_completions` threading through a shared fleet backend is NOT filed as a task — the fleet-consensus-or-fail-closed rule covers every real fleet (all shared-fleet roles agree in the live config, verified offline), and a future disagreement fails loudly to the legacy build rather than mis-routing; revisit only if that CRITICAL log ever fires.

### FLIP BOUNDARY EXECUTED 2026-07-23 (operator-directed; this session held the con; main session stood down per one-deploy-authority)

- [x] Merge `wp12-fleet-layer-impl` (3c0b4ce4) → `spec-dec-mtp-refresh-2026-06-22` = merge commit `4ca6859a` ✅ 2026-07-23
- [x] Acceptance cases 1–9 re-run on the MERGED tree: 33/33 + targeted regression 53/53 ✅ 2026-07-23
- [x] Launch-env wiring: `ORCHESTRATOR_FLEET_LAYER=1` durable `env.setdefault` (`a172d2dd`); rollback = reload with `ORCHESTRATOR_FLEET_LAYER=0` in the shell env ✅ 2026-07-23
- [x] Pre-reload preflight: fleet build from LIVE registry+priors+NUMA = 4 fleets (frontdoor + worker_general quarters-shared, architect single, ingest quarters), §3 parity green, 8 bindings, none degraded ✅ 2026-07-23
- [x] One API-only reload (new PID 3051676) + no-inference attestation: `ORCHESTRATOR_FLEET_LAYER=1` in worker env (attest_orchestrator_workers), API healthy, /health backend probes now group the shared fleet (`coder_escalation/frontdoor/worker_summarize` as one probe) ✅ 2026-07-23
- [x] Both boundary commits pushed to origin ✅ 2026-07-23
- **DELIBERATE SCOPE DEVIATION (flagged in `a172d2dd`)**: the §5 WP-13 interim deletion did NOT execute at this boundary. Reasoning chain: instant-rollback requirement ⇒ the legacy per-role build stays ⇒ Fix-A delegations + generator alias-ports inheritance are its substrate (deleting them breaks rollback after any priors regeneration: toolrunner KeyError degraded, worker_math single-quarter re-serialization) ⇒ their guard tests stay with the code they guard. Fleet-wins-at-runtime resolves the two-descriptions concern the §5 atomicity clause guarded against. The permission classifier independently blocked live-tree test deletion, converging on the same outcome.
- [ ] **Post-soak §5 cleanup (code + tests as ONE change)**: retire the legacy per-role build path — ServerURLsConfig URL ownership, Fix-A delegations, `_LEGACY_SERVER_URL_FALLBACKS`, generator alias-ports inheritance, and their guard tests (4 in `test_full_slot_demotion.py` + convergence test in `test_stack_priors_compiler.py`) — once the fleet layer survives its soak and the operator retires the flag-off rollback
- [x] §6 case 10 live gate — **PASS** ✅ 2026-07-23 (operator inference grant same day; evidence bundle `coordination/inference-batch/bundles/WP12-case10-live-gate/` + terminal ledger row `WP12-case10-live-gate`): worker_math 4-wide burst → **4 disjoint busy quarters** (8082/8182/8282/8382, all four simultaneously decoding, peak /slots sample all-busy), fleet identity on every dispatch (tap `topology_role=worker_general`), zero same-fleet fallback, zero phantom-full, migration counters 0→0. J2/J3 replay executed faithfully (identical params, `--workers 1` API-only reload, 12/12 OK, n_aborted=0) — verdict INCONCLUSIVE is **structurally correct**: both fleets are quarters-only (no full endpoint), so the full↔quarter migration surface is dormant (C10-F2). Two findings, neither a fleet-layer defect:
  - **C10-F1**: `live_warm_worker_slots()` returns `{}` (filters `tier=="warm"`; every live role is `hot`) → `get_role_max_concurrency()==1` for ALL roles → `_acquire_role` `Semaphore(1)` per role **per API worker process**. Within-role concurrency in production exists ONLY via the 6 uvicorn processes (cross-process disjointness from region flocks). On a `--workers 1` API every role serializes fully — the first burst attempt landed 4/4 on port 8082 back-to-back (staircase 19.7/34.9/49.6/64.1s). Also reinterprets the 2026-07-21 J2/J3 pass: its committed migrations (forward=6/reverse=4) are consistent with fully serial traffic (full-idle KV handovers), not overlap-driven displacement.
  - **C10-F2** (wording corrected 2026-07-23 per [stack-lineup-dossier-2026-07-23.md](stack-lineup-dossier-2026-07-23.md) §5.1): WP-3/WP-4 migration surface dormant in the quarters-only **realized/launched** lineup — the full/half instances remain **declared-dormant** in NUMA_CONFIG (worker full 8072 `placement_policy: full_disabled` by DISPATCH-A `99dd6c92`; frontdoor 8070 / ingest 8085 halves undisabled-but-unlaunched since the v7 quarter-mode cutover `ff4b3766`). SM stays unit-verified; the live surface returns only if the operator redeploys a big instance.
  - **C10-F2 CLOSED same day — lineup restored, J2/J3 PASS on it** ✅ 2026-07-23: the operator ruled the launch-contract drop an accidental regression and directed restoration; 8070/8072/8085 redeployed via the new additive `--numa-mode both` promotion path (orchestrator `95dffc88`; three-gates green: pipeline ok + 183-test suite, additive starts with quarters preserved, live affinity verified, solo dispatch → big instances on all three fleets). The J2/J3 replay then ran on the restored lineup under the fleet layer and **PASSED**: forward=6, reverse=1, n_committed=7, n_aborted=0 (`probeD_stdout.json` / `j2j3_restored_lineup_probeD.jsonl` in the case-10 bundle). Case-10 is now complete in its full original sense — committed migrations confirmed live.
- [x] **C10-F1 follow-up — fleet-derived role concurrency LANDED flag-off** ✅ 2026-07-23 (orchestrator `94ab796f`): `ORCHESTRATOR_FLEET_ROLE_CONCURRENCY=1` derives `get_role_max_concurrency` from the role's realized fleet (disjoint-quarter capacity; big instance never adds capacity since it overlaps; fail-open to legacy on fleet unavailability, never wider). **Default OFF — enabling is a deploy decision** (raises in-process within-role concurrency; placement SM + region locks own disjointness; recommend enabling alongside a WP-8-style eval-fanout validation window). Until enabled, eval fan-out concurrency remains 6-process spread × per-process `Semaphore(1)`.

On implementation (post-measurement-chain, per operator sequencing):
1. Flip the WP-12 checkbox in `within-role-placement-state-machine.md` → `- [x] … ✅ <date>`; note the interim (WP-13 Fix-A + drift-guard test) deletion in the same edit.
2. Update `progress/2026-07/2026-07-DD.md`.
3. Cross-reference op-bundle ESC-8 (shared restart surface) and the WP-9/WP-10 lineup event.

> **2026-07-23**: the fleet layer's heterogeneous extension is governed by the OPERATOR-RATIFIED fabric contract (core guiding principle banner in [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md)): policy-data-never-code, the four robustness axioms, the bounded/reversible/measurable/gated conversion rule.
