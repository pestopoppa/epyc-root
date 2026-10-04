# RTG-58 P2 — orchestrator prefix index (revived radix tree): design, blast radius, prepared handoff text

Prepared 2026-10-04 by a subagent for the owning sessions (ak-ds41-main keeps the handoff and index row;
workspace-ec owns P2 execution as stack owner). **Nothing here is applied to the handoff.** Section 4 is the
exact text to paste into `handoffs/active/kv-prefix-fork-and-paged-attention.md` under `### P2`, section 5 is
the lessons note. Code: `epyc-orchestrator` branches `feat/rtg58-p2-prefix-index` (LOW-risk half) and
`feat/rtg58-p2-prefix-index-gate` (stacked; the HIGH-risk gate half) in worktree
`/mnt/raid0/llm/worktrees/orch-radix-revival`; not pushed, API not reloaded.

## 1. Design (Phase 1)

### 1.1 Audit of the January 2026 `radix_cache.py` (recovered from `2db54487^`)

| Item | Verdict | Why |
|---|---|---|
| `insert` / `find_longest_prefix` / "deepest node with a holder" match | **keep (semantics)** | Correct LPM shape; reused as `RadixTree.insert/match`. |
| `insert` stamps `slot_id` on every node of the path; `_remove_prefix` clears only the leaf | **fix** | The stale-slot bug: shared interior nodes keep naming a slot that was evicted or reassigned; re-inserting an explicit `slot_id` never removed the slot's old path, so two paths claimed one slot. Fixed with per-node holder sets + one recorded path per entry; insert REPLACES, remove walks the whole path and prunes. Regression test `test_stale_slot_regression_from_the_january_radix_cache`. |
| One dict node per token, docstring claiming path compression | **fix** | 60k-token trunk = 60k Python objects per slot. Now path-compressed edges over chained 512-char block hashes (~500 per 60k tokens). |
| `_allocate_slot` / `_evict_lru` (client allocates slots; returns slot 0 when empty) | **drop** | The server picks slots (LCP + `--cache-ram`); a client allocator is the UFH14-B4 failure. |
| `TokenizedRadixCache` (client tokenizer) | **drop** | Client tokens ≠ what the server tokenizes after the chat template. Keys are wire bytes; token counts come from the server's own `timings`. |
| Hot-prefix persistence, hit counter for any ≥1-token match, `time.time()` LRU | **drop / fix** | Persistence is the dead slot-save path (UFH14-B4h). Matches below a threshold never count; monotonic clock injected. |
| Server reconciliation, concurrency, per-server scoping | **add** | Absent before; see 1.3-1.5. |

### 1.2 Composition with `PrefixRouter`

Neither replace nor wrap. `PrefixRouter` stays the legacy opt-in pin (`ORCHESTRATOR_PREFIX_ROUTER_PIN_SLOTS=1`).
The index (`src/inference/prefix_index.py`) is a separate structure, **one per physical server** (keyed
`host_port` like the long-prefill lease, so roles sharing :8083 share one index — KV-0b, stronger than the
per-construction `_router_for` map). It is driven from two places that every dispatch lane already crosses:
the KV pool gate (`SharedKVPoolAdmission.acquire`: primitives, passthrough, scouts) and the serving record
(`serving_calls.recorded_call`, `passthrough.write_serving_record`). `CachingBackend` consults it only for
pin policy `idle`.

### 1.3 Data model

- Key = the text the serving record already fingerprints (`serving_calls._prompt_text_for_fingerprint`):
  `/completion` prompt verbatim; chat lane single user message (rendered = HEAD + content + TAIL, so content
  prefixes are rendered prefixes: `key_kind=exact`); `tools`+`messages` JSON for chat payloads / passthrough
  (`approx`: prefix relation at message granularity). No canonicalization (a canonical key invents matches).
- Tree: path-compressed trie over chained block hashes `h_i = H(h_{i-1} || block_i)` (`ORCHESTRATOR_PREFIX_INDEX_BLOCK_CHARS`, default 512).
  Matches err LOW by < 1 block (~170 tokens), never high.
- Entries: `slot` (server-verified), `pending` (served, not yet bound), `served` (slot unknown after 30 s:
  ordering only, never credit), `inflight` (SGLang `lock_ref`: admitted request's trunk, with text for an
  exact junction, prefill deadline and prefilled flag).
- Token estimates use the entry's measured `prompt_tokens/chars`, else 4 chars/token for prefixes and
  3 chars/token for suffixes (the gate's conservative estimator).

### 1.4 Eviction and staleness (server = source of truth)

- Binding: after a served call, the entry is bound to slot S and S's `/slots` `id_task` when S is idle and
  holds `prompt_n + cache_n + predicted_n` ± 4 tokens. `/completion` names S (`id_slot`: origin `exact`);
  the chat lane does not, so S is inferred and **only when exactly one idle slot matches** (never guessed).
- Drop when `/slots` shows: different `id_task` (foreign task ran there), `n_prompt_tokens` 0 (cleared /
  idle-slot purge) or below what we left, slot missing, or a different server launch id.
- Reconcile runs at every gate poll from the resolver's cached `/slots` (no extra HTTP).
- Eviction: slot entries are replaced by the next observation on that slot; `served` capped at 32 LRU;
  `pending` expires at 30 s; `inflight` ends at `release`.

### 1.5 Concurrency

One `threading.Lock` per index, a leaf lock (gate `_cond` → index lock is the only nesting). Six uvicorn
workers: verified `slot` entries are shared through `{tmp_dir}/kv_prefix_index.{host}_{port}.json` (atomic
rewrite under flock, newest-wins per slot, drop markers propagate; hashes only, never text;
`ORCHESTRATOR_PREFIX_INDEX_HOST_WIDE`). `pending`/`inflight` stay per process: trunk-first and LPM see
same-worker siblings (scouts, delegate waves originate in one worker); passthrough fan-outs spread over workers
see each other only through verified slots. Host-wide in-flight is a follow-up if KPF-26 shows misses.

### 1.6 What it drives (all behind the flag)

(c) and the record observation are on branch A; (a), (b), (d), (e) and the `prefix_index` credit are on
the gate branch B (see section 2).

| | Mechanism | Default with flag on |
|---|---|---|
| (a) trunk-first | Gate holds a request whose ≥`TRUNK_MIN_TOKENS` (4096) trunk an EARLIER in-flight sibling is still prefilling, until `prefill_done`, `/slots` shows no prefill, the floor-rate deadline, or `TRUNK_HOLD_S` (120 s). Others pass a trunk-held waiter with its reservation counted. Central, so every fan-out site gets it. | **off** unless `ORCHESTRATOR_PREFIX_INDEX_FORK=1` (holding only pays once P1 shares a busy slot's cells) |
| (b) LPM | A waiter with a reusable prefix ≥ `LPM_MIN_TOKENS` (2048) that fits now is admitted ahead of lower-score waiters that do not; each waiter is passed at most `LPM_MAX_SKIPS` (1) times. Queue bound 8 makes DFS-weight ≡ LPM, so DFS-weight is not separate. | on |
| (c) pinning | `ORCHESTRATOR_PREFIX_INDEX_PIN=idle`: pin only a VERIFIED IDLE slot (≤ 2 s old) holding the longest prefix ≥ 2048 tokens; never busy, never chat lane, caller slot wins. UFH14-B4's failure (256-char hash → one slot → server defers) cannot occur. | off |
| (d) unique cells | `unique_cells()` = union vs sum of slot+inflight prefixes (`shareable_tokens_est` = what P1 saves), recorded per admission. With fork on, a request whose source is a busy slot/in-flight sibling reserves `want − shared` (`fork_credit_tokens`); idle sources are never credited (their cells are not counted anywhere). New credit source `cache_credit_source: "prefix_index"` for the long-prefill rule (verified idle slot, exact to the block; best-of with `fp_history`/`slots_text`). | credit on; fork credit only with fork |
| (e) fork plan | Admission record `prefix_index.fork_plan = {source, slot_id, junction_chars}` (exact junction by text compare for in-flight siblings). Not sent on the wire until P1's interface exists. | recorded only with fork |

### 1.7 Metrics

Per server (`get_status()[url]["prefix_index"]`, only with the flag on): entries by kind, nodes, verified
slots; `lookups`, `matches{source}`, `bound_exact/inferred`, `verify_timeouts`, `stale_drops{reason}`,
**prediction error** (`predicted_cache_tokens` vs the server's `timings.cache_n`: abs error, over/under) and
**slot prediction hits** (vs `id_slot`), `trunk_holds/_s_total/_timeouts`, `lpm_passes`, `pins`,
`fork_credit_tokens`, ledger reads/writes/errors, `unique_cells`. Per call: `kv_admission.prefix_index` in
the serving record (match, predicted cache tokens/slot, verdict, fork plan) — so the offline report can
grade the index against the server without new plumbing.

### 1.8 Flags (all default OFF / inert unless the master flag is on)

`ORCHESTRATOR_PREFIX_INDEX` (master), `_FORK`, `_PIN` (`off|idle`), `_LPM` (on), `_LPM_MIN_TOKENS`,
`_LPM_MAX_SKIPS`, `_TRUNK_MIN_TOKENS`, `_TRUNK_HOLD_S`, `_PIN_MIN_TOKENS`, `_PIN_FRESH_S`, `_BLOCK_CHARS`,
`_HOST_WIDE`. Flag off: no index object, no file, no key computed, admission record/status keys identical.

### 1.9 Test plan

- Done (offline, this branch): tree split/prune/union, the stale-slot regression, binding exact/inferred/
  ambiguous, each stale-drop reason, relaunch, verify timeout, fork lookups, trunk owner + exact junction,
  pin rules, unique cells, host-wide ledger across two workers, prediction-error hook; admission credit, LPM
  bounded reorder, trunk hold + release + timeout, fork credit on the reservation; **wiring**: passthrough
  route (TestClient → gate → fake llama-server → record → index → second call predicted slot) and the `/chat`
  backend half (`llm_call` → `_real_call` → gate → `CachingBackend` → `LlamaServerBackend` → SSE
  `/completion`); **flag off**: index construction raises, callers compute no key, legacy record/status key
  sets, wire payload == `_build_payload` output, passthrough forwards the client's raw bytes, no ledger file.
- Live (KPF-26, workspace-ec, needs P1 for a/d/e): shadow window with the flag on and FORK off on :8083 —
  read `prediction_abs_err_tokens/predictions`, `slot_prediction_hits/slot_predictions`, stale-drop mix;
  then the P2 gate replay with FORK on against the P1 build.

## 2. Blast radius (GitNexus + grep)

Fresh index of the worktree (`scripts/gitnexus-analyze.sh /mnt/raid0/llm/worktrees/orch-radix-revival`,
74k nodes; the main-clone index is stale at `f72d1d5` and the 2026-09-27 worktree indexes predate
`serving_calls`). `impact --direction upstream`:

| Symbol touched | Impacted | Risk | Notes (grep-backed) |
|---|---|---|---|
| `PrefixRouter` (class) | 0 | LOW | not edited; constructed in `llm_primitives/backend.py` `_router_for` + fleet `_mk` (member path GitNexus misses) |
| `PrefixRouter.get_slot_for_prompt` | 3 | LOW | not edited |
| `CachingBackend.infer` / `infer_stream_text` (pin branch) | 1 / 0 | LOW | GitNexus misses member calls: grep finds `_call_caching_backend`, `ConcurrencyAwareBackend`, `RoundRobinBackend`, fleet backends |
| `serving_calls.recorded_call` (observe hook) | 0 | LOW | decorates `LlamaServerBackend.infer` and `.infer_stream_text`: every primitives call; hook is a flag check |
| `serving_calls.remember_served` (neighbour) | 1 | LOW | |
| `passthrough.write_serving_record` | 4 | LOW | 1 process |
| `passthrough._passthrough` / `_Call` | 2 / 0 | LOW | |
| `context_limits.parse_slots` | 4 | LOW | also `embedding_pool/busy.py` |
| `context_limits.SlotState` (+ `id_task`, compare=False, default None) | 34 | MEDIUM | additive field; equality unchanged |
| `_call_caching_backend` (prefix_key kwarg) | 4 | LOW | |
| `passthrough.gate`, scout `complete` (prefix_key kwarg) | ≤3 | LOW | |
| **`SharedKVPoolAdmission.acquire`** | 6 (2 processes, 14 flows) | **HIGH** | callers: `_call_caching_backend`, `passthrough.gate`, scout pool gate (member call GitNexus misses) — every dispatch to a shared-pool server |
| **`SharedKVPoolAdmission._admissible`** | 5 | **HIGH** | |
| **`SharedKVPoolAdmission.release`** | 17 | **HIGH** | |
| `prefill_done` / `get_status` | 7 / 0 | LOW | |

**Decision taken on the HIGH rows (CLAUDE.md "STOP and warn"; the dispatch said stop on HIGH):** the code was
written before the fresh index finished (the stale 2026-09-27 index rated `SharedKVPoolAdmission` LOW, which
the RTG-58 GitNexus note already warns is not evidence). On the fresh HIGH, the work was split:
- `feat/rtg58-p2-prefix-index` (the requested branch) carries ONLY the LOW/MEDIUM edits: the index, the
  serving-record observation, the `idle` pin, `SlotState.id_task`.
- `feat/rtg58-p2-prefix-index-gate` (stacked) carries the gate wiring (credit, LPM, trunk hold, fork credit,
  fork plan) and must not land until the stack owner (workspace-ec) acknowledges the HIGH rating, as P1 does for
  KPF-12/13. Both are flag-OFF and byte-identical with the flag off (tests).

## 3. Questions for the server (for workspace-ec's INTERFACE.md; designed against today's v10 `/slots`)

1. **Slot content identity.** v10 `/slots` gives `id_task`, `n_prompt_tokens`, `is_processing`,
   `n_decoded` only; content identity is inferred from "same id_task, same token count". Can `/slots`
   expose a per-slot **content epoch** that increments on every `prompt_clear`, `seq_rm`, `--cache-ram`
   load, idle-slot purge and fork-into, plus a cheap **prefix hash ladder** (e.g. a hash of the token ids at
   each checkpoint position)? With an epoch the index never mis-binds; with hashes it could verify without
   trusting its own observations.
2. **`id_slot` / `id_task` on the OAI endpoints.** `/v1/chat/completions` and `/v1/responses` bodies carry
   neither, so chat-lane binding is inferred. Please add both to `timings` (next to KPF-16's
   `n_fork_tokens`, `fork_src_slot`, `fork_src_kind`), streamed and non-streamed, including non-streamed
   `/v1/responses` (today it has no `timings` at all).
3. **Checkpoint positions.** Per slot: the list of context-checkpoint token positions (and which are
   `pinned` via `checkpoint_at`), so the index can predict the fork position `p` = largest checkpoint ≤ LCP
   instead of assuming the full LCP. Update semantics: rewritten on every create/erase.
4. **`checkpoint_at` units.** Token positions require the orchestrator to tokenize the RENDERED template.
   Can the field also accept `{"message": k}` (checkpoint at the start/end of message k after templating) or a
   byte offset into the rendered prompt? Message granularity is exactly what fan-out trunks need.
5. **Fork capability discovery.** Expose `slot_fork_min_tokens` (0 = off) in `/props` so the orchestrator
   can set its FORK mode from the server rather than an env var.
6. **Unique cells.** KPF-16's pool unique-cells figure: in `/slots` (per slot private/shared) and a pool
   total in `/props` or `/metrics`, refreshed per batch, so `_fits` can read real sharing.
7. **Busy-slot fork source.** When the fork source is busy and mid-decode, is `n_prompt_tokens` of the
   source still the shared prefix, or does it advance with decode? (The index treats a busy slot's verified
   content as its bound prompt, not its decode tail.)
8. **Purge/forks and `id_task`.** After a fork INTO slot D, does D's `id_task` change (new task) and does the
   source's `id_task` stay? The staleness rule assumes "source unchanged, destination changed".

## 4. Prepared task text for RTG-58 (paste under `### P2`, after KPF-20; do not apply from a subagent)

```markdown
- [ ] **KPF-27: revived prefix index (radix tree) — orchestrator side, behind `ORCHESTRATOR_PREFIX_INDEX`
  (default OFF).** Branches `feat/rtg58-p2-prefix-index` (commit 2833e3a2: index, record observation, `idle`
  pin) and stacked `feat/rtg58-p2-prefix-index-gate` (commit d63f7aa9: KV pool gate wiring — GitNexus HIGH on
  `SharedKVPoolAdmission.acquire/_admissible/release`, lands only after workspace-ec acknowledges); review +
  land by the owning session; no API reload from the branch. Module `src/inference/prefix_index.py`: one index per
  physical server, path-compressed trie over chained 512-char block hashes, entries `slot` (bound to `/slots`
  `id_task`), `pending`, `served`, `inflight`; reconciled with `/slots` at every gate poll; verified slots
  shared host-wide via `{tmp_dir}/kv_prefix_index.{host}_{port}.json`. Design and server questions:
  `/mnt/raid0/llm/tmp/orch-radix-revival-20261004/RTG58-P2-prepared.md`.
  - [x] KPF-27a: audit of the January `radix_cache.py` (keep LPM semantics; fix stale-slot bug and missing
    path compression; drop client slot allocation and client tokenizer). Regression test for the stale-slot bug.
  - [x] KPF-27b: wiring — serving-record observation (`recorded_call`, `passthrough.write_serving_record`),
    `CachingBackend` pin policy `idle` (branch A); KV pool gate (`prefix_key` on primitives, passthrough,
    scouts; credit, LPM, trunk hold, fork credit, fork plan) on branch B.
  - [ ] KPF-27b-ack: workspace-ec acknowledges the HIGH blast radius of branch B (acquire/_admissible/release)
    before it lands, as for KPF-12/13.
  - [x] KPF-27c: flag-off proof (`tests/unit/test_prefix_index_flag_off.py`) and wiring tests through the
    passthrough route and `llm_call` → `/completion`.
  - [ ] KPF-27d: land on main (owning session), then a **shadow window** on :8083 with the flag on and
    `_FORK` off: record `prediction_abs_err_tokens/predictions`, `slot_prediction_hits/slot_predictions` and
    the `stale_drops` mix from `get_status()`; done when two windows are recorded (VB-KVU-PF).
  - [ ] KPF-27e: when P1's INTERFACE.md lands, map its fields (content epoch, `id_slot`/`id_task` on OAI
    timings, checkpoint positions, `/props` fork capability, unique cells) into `reconcile`/`lookup`, and send
    `checkpoint_at` from the trunk-first path (KPF-21).
- KPF-21 note: trunk-first is implemented centrally in the gate (`ORCHESTRATOR_PREFIX_INDEX_FORK=1`), not per
  fan-out site; KPF-21 stays open for the prefill-only trunk request with `checkpoint_at` (needs KPF-15).
- KPF-22 note: the bounded LPM bypass is implemented in KPF-27 (`_prefix_index_admissible`, at most
  `ORCHESTRATOR_PREFIX_INDEX_LPM_MAX_SKIPS` passes per waiter). KVU-6's and INF-05 KV-3's owners record the
  overlap; KPF-22 closes after KPF-26 measures it.
- KPF-23 note: decision recorded in `prefix_cache.py`'s docstring — `PrefixRouter` kept as the legacy opt-in;
  index pin policy `idle` pins only verified idle slots; hash routing retires after the KPF-27d shadow metric.
- KPF-24 note: `cache_credit_source: "prefix_index"` added; fork credit on the reservation behind `_FORK`;
  switch from the client estimate to the server's unique-cell figure once KPF-16 publishes it.
```

## 5. Prepared lessons note (append to "Lessons: the orchestrator already had a radix router once")

```markdown
- **2026-10-04 revival (KPF-27).** The radix tree came back in a different role: an index that records where
  prefixes are and lets the gate act on it (credit, LPM, trunk hold, fork plan), never a cache model and
  never a slot allocator. Three rules made it safe to revive: (1) the server is the source of truth — every
  slot entry is bound to `/slots` `id_task` and dropped the moment the server disagrees; (2) a client key is
  the WIRE text, not a canonicalized or client-tokenized one; (3) it is wired into paths every request
  already crosses (the KV pool gate and the serving record), with a flag-off test that proves nothing else
  changed — the January module failed on exactly that last point.
```

## 6. Test results (single pytest process, `nice -n 19 taskset -c 190-191`)

- Branch A `2833e3a2` (clean detached checkout): 237 passed — `test_prefix_index{,_wiring,_flag_off}.py`,
  `test_prefix_cache.py`, `test_serving_calls{,_prefix_fp}.py`, `test_passthrough_route.py`,
  `test_inference_mixin.py`, `test_context_limits_model_cap.py`, `test_kv_prefix_history.py`.
- Branch B `d63f7aa9`: 350 passed — the above index tests + `test_prefix_index_admission.py`,
  `test_kv_pool_long_prefill.py`, `test_kv_pool_cross_process_lease.py`, `test_kv_prefix_history.py`,
  `test_context_overflow_handling.py`, `test_oab8_scouts.py`, `test_passthrough_route.py`,
  `test_inference_mixin.py`, `test_inference_tap.py`.
- Wider A+B run (489 items incl. `tests/integration/test_cache_{hits,integration}.py`): 482 passed, 6 skipped,
  1 failed = `test_cache_hits.py::test_canonicalization_throughput` (316 prompts/s vs a 5000/s floor). It fails
  identically on untouched `main` f8c9c0a3 under the same 2-CPU niced run: environmental, not this change.
- Logs: `/mnt/raid0/llm/tmp/orch-radix-revival-20261004/tests-{A,B}.log`, `related-tests.log`.
