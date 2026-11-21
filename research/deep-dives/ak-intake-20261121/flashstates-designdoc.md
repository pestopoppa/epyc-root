# Stage-2b (wave 3) dive: FlashStates vLLM fork design doc "Hybrid State Checkpoints" (intake-2787)

- **Source read:** `FutureMLS-Lab/vllm` `docs/design/hybrid_state_checkpoints.md` @ `3cfd432cd83a54a5e538cad7b090e56c27a870f9`, raw sha256 `1321566c5d21…`. `flashstates-designdoc/extracted.txt` (25,332 bytes) is the anchor text.
- **read_depth: FULL.** Every section was read: options table, Motivation, Design principles, Recovery units, Frontier keys, Frontier checkpoints, Decode-boundary states, Session leaves, Indexer rings, In-chunk state export, Export kernels, GDS eviction, Prefill cost model, KV connectors, Speculative decoding, Compact state layout, Metrics, Requirements and Testing. The doc links to code (`export.py`, the vendored FlashInfer GDN kernel). That code was not re-read in this wave; the intake-2772 dive read `export.py`.
- **lane_head:** 4b428f15153d0a32b37e6302849691b2212a49ab. In-house code cites are the C17 `ed5d94969` copies in `extra/` (`c17_server_context.cpp`, `c17_gdn.cu`).
- **Bearing dives read first:** `flashstates-repo/dive.md` (intake-2772), `2611.26020v1/dive.md` (FrontierReplay, intake-2758), `pr31669/dive.md`. Plan boxes read: RS-REPLAY-PORT/-GATE, KPF-64-CUTS, KPF-64-SNAPSLOT-READ, FR-UFH14-DIVERGE, and the M2 monitor (`ak-intake-20261121-plan.md` L147-204, L395-397).

## Verdict
**dive-verified.** This is the primary mechanism text behind intake-2772. The facts the plan relies on hold:
- export is single-target per request per step;
- export offsets are grid-aligned;
- export is SM100-only;
- bit-identity is defined by two invariants.

The doc adds three things the plan did not yet use:
1. **The exact export pipeline.** The scheduler picks one position, which travels through the KV manager → `SchedulerOutput` → attention metadata → the kernel. The kernel writes to a per-sequence workspace row, and a second step copies that row into the cache block.
2. **The speculative-decoding rules for resolving an exact state from per-position verify columns.** This is the vLLM analogue of our K-snapshot slots, and it bears directly on KPF-64-SNAPSLOT-READ.
3. **Refusal conditions.** Frontier publication is refused when the device state runs past the kept tokens, for example a stop string inside accepted drafts. Export is refused under ubatching.

## How targets are chosen and exported mid-prefill (settled)

| Question | Answer in the doc |
|---|---|
| Which positions are targets | In `align` mode, the positions where a state *must* be cached: "a block boundary after a mid-block start, the last cacheable block boundary, or a shared-prefix junction" (Motivation item 2). Frontiers (exact request end) are captured at request free, not by export. |
| Grain | At most one must-cache position per non-final chunk (`export.plan_export`). If the backend can write the first one (`is_mamba_prefill_checkpoint_valid`), the chunk runs past it, and ends at the second one if there is one. Otherwise it ends at the first, as without export. **One position per request per step.** |
| Alignment | The layer declares it: **64 tokens for GDN, 16 for FlashKDA**. The scheduler places offsets on the prefix-cache grid (`get_mamba_prefill_checkpoint_grid`). A filler chunk that the block-aligned split cannot schedule "may instead end on a 64-token boundary when that leaves at least 1024 tokens". |
| Per-request offsets | Upstream FlashInfer checkpoints at one stride for every sequence in the call, the gcd of the batch's offsets. The fork instead assigns one workspace row per exporting sequence (`plan_gdn_export_rows`), and a vendored kernel writes each sequence's state at its own offset. |
| Scheduler interaction | `MambaManager` reserves and re-keys the checkpoint block. The position then flows `SchedulerOutput.prefill_checkpoint_positions` → `CommonAttentionMetadata.prefill_checkpoint_positions` → `compute_mamba_prefill_checkpoints`. "A later cap on the chunk that moves the position out of it drops the export." |
| Memory layout | Kernel → workspace row → `MambaPrefillCheckpointExporter` copies the rows into cache blocks. This is two-stage, not an in-place write. FlashKDA stores the checkpoint and the final state from registers. When few sequences leave SMs idle, the GDN kernel splits a (seq, value head) pair into two half-row tiles run as one 2-CTA cluster. |
| Route cost | An exporting long single sequence is forced onto FlashInfer's non-context-parallel route, "which can be slower". |
| Eviction | GreedyDual-Size over recovery units: a state plus the attention pages only it needs. Score = L + gain/size, where gain is the prefill seconds from the unit's fallback, using a cost model with d per token plus e per token per 100k of context. Only e/d matters. Optional leaf-last tiers, and pins for the first 256 waiting requests. |
| Refusals | Export is refused with EAGLE block drop, **ubatching** and context parallelism. The kernels act only on compute capability 10.0. Frontiers are refused with ReplaySSM, KV events and CP. Under spec decoding, frontiers need `truncate_acceptance_at_stop`. |

## Claim verification (Stage-1 claims carried by intake-2772 and the plan)

| # | Claim | Status | Evidence |
|---|---|---|---|
| 0 | Export lets a chunk run past one cache position per request per step, and the kernel writes the state there | CONFIRMED | "contains at most one position where a state must be cached"; "one position per request per step" |
| 1 | Grain is 64 tokens for GDN and 16 for KDA, on the prefix-cache grid | CONFIRMED (as the scheduler-side alignment the layer declares). The release PDF (intake-2788 App. H) says the GDN *kernel* supports 16-aligned offsets inside its 64-token tiles. The two are consistent: the doc's 64 is the serving configuration at 3cfd432. | invariant 4 |
| 2 | Exported state is bit-identical to the cut-at-offset state, and output/final state are unchanged | CONFIRMED | invariant 1 (both halves) |
| 3 | SM100-only; other GPUs keep upstream checkpoint paths | CONFIRMED | Requirements + Export kernels |
| 4 | Export avoids extra prefill passes ("the chunk is not cut") | CONFIRMED, NARROWED | It removes the early chunk stop, but a long single sequence loses the CP route. No overhead number is given anywhere in the doc. |
| 5 | (plan KPF-64-SNAPSLOT-READ premise) An exact state can be taken from a per-position spec column instead of a cut | SUPPORTED BY PRECEDENT | The fork resolves frontiers from "the column of the last accepted draft". It gathers a later column into the first with `MambaStateGather` before anything reads it, and takes decode-boundary states from the verify column at a crossed boundary. |

## Mapping onto llama.cpp (C17 `ed5d94969`) and our GDN kernels

- **Target positions are known before the batch is built.** `c17_server_context.cpp` fill_prompt L5297-5333 breaks the slot's batch at four kinds of position:
  - user-message starts (`spans.is_ckpt_start`, with a min-step rule);
  - reorder junctions (`kv_reorder_junctions`);
  - n−(4+n_ubatch) and n−4 (`checkpoint_offsets[] = {4 + n_ubatch, 4}`).

  The checkpoint is created **before** `llama_decode` of the next batch (L5406-5410), so it captures the state at the cut. This is the same "a non-final chunk must end at every position where a state has to be cached" constraint that vLLM's export removes (doc Motivation item 2).
- **What a cut actually costs here (our analysis, not measured).** A cut stops only *this slot's* contribution to the shared batch; other slots keep filling it (`break` exits the per-slot loop).
  - The **n−4** cut on its own adds a server iteration but **no extra ubatch** when n_batch ≥ n_ubatch+4. After the n−(4+n_ubatch) cut, the remaining ub+4 tokens split into ubatches of ub and 4 whether or not the batch breaks at n−4.
  - The extra *partial ubatch* comes from the **n−(4+n_ubatch)** cut and from user-message-start or junction cuts, which end a batch off the ubatch grid.

  This matters for pricing. KPF-64-CUTS currently counts "extra ubatches (prefill cuts)" as one thing, and KPF-64-SNAPSLOT-READ removes only the n−4 cut.
- **The fork rejects export under ubatching.** llama.cpp *always* ubatches, so an export op input must be per ubatch: the offset is relative to the ubatch that contains the target. The vLLM "one position per request per step" rule becomes "one offset per sequence per GDN op call", and the ubatch splitter routes it.
- **Our K-snapshot op is the per-position layout.** In `c17_gdn.cu`, the snapshot slot mapping is "slot 0 = most recent state, slot s = s tokens back" for the last K tokens of the op (L718-731). The C8-6 chunked kernel processes those K tokens as single-token chunks "so every per-token snapshot the cache keeps is materialised exactly" (L37-38). That is the doc's `per_position` layout restricted to the tail of a call. An export-offset input generalises it from "last K positions" to "one arbitrary offset".
- **Chunked-kernel export cost (C8-6, chunk `GDN_CH_C` = 64).**
  - A 64-aligned offset relative to the call start is the inter-chunk state the scan already holds, so it costs one extra state store.
  - An interior offset has two options:
    - **(a)** End a chunk at c, a variable-length chunk, as keep_rs already does. This is cheap, but it shifts the chunk grid after c, so output and final state differ in fp32 rounding from the no-export call. That breaks the doc's invariant 1, first half.
    - **(b)** The FlashStates bounded prefix update from the tile's own intermediates (intake-2788 App. H). This keeps the main recurrence untouched.

  Upstream vLLM's Mamba-2 path reportedly does (a) ("ends a logical chunk at the cache boundary"; search result, see dive-surfaced). The recurrent HIP kernel and the CPU op are token-granular, so any offset is one store there.
- **Wave64 / LDS.** The export adds global stores of an already-resident state shard: no cross-lane change, no `__ballot`, no LDS growth. The 2-CTA cluster split has no gfx90a analogue and is not needed: it addresses SM idling with few sequences on SM100, and at np ≤ 4 our grid is H × n_seqs × column blocks.
- **Speculative frontier rules map onto PFXC-A1.**
  - C17 `checkpoint_after_generation` (L3383-3401) checkpoints only when `pos_max + 1 == n_tokens`, i.e. no pending draft positions. That is the analogue of the doc's "state after the kept tokens".
  - The doc's extra refusal (scheduler kept fewer tokens than the device sampled, e.g. a stop string inside accepted drafts) has no explicit counterpart in C17. If the slot's cached tokens run past the text the client keeps, the post-generation checkpoint lies past the next prompt's divergence. It is then never usable, and the restore silently falls back to an earlier checkpoint.
  - This is a hit-rate loss, not a correctness bug: the restore only accepts `pos_max` within the matched prefix (L5082-5097). It belongs in FR-UFH14-DIVERGE's classification.
- **GDS eviction.** Not applicable now. llama.cpp checkpoints are per-slot host-RAM byte vectors (32 per slot, `create_checkpoint` L3325-3378), and KPF-64 found the pool not binding at 4 sessions on 4 slots. This is unchanged from the intake-2772 decline.

## Principles

| Principle | Source evidence | MI210 gfx90a | Zen 5 CPU | Port cost | EPYC consumer |
|---|---|---|---|---|---|
| Plan the chunk so it holds ≤ 1 must-cache position; run past it and export instead of stopping | §In-chunk state export | Server-side: per-ubatch offset routed by the splitter | same | S (server) | M2 export clause; KPF-64-CUTS |
| One offset per sequence written into a per-sequence row, copied to the cache block afterwards | §Export kernels (GDN) | Write into an extra output region, then the existing checkpoint host copy | same | M (op input + 3 kernels) | M2 export clause |
| Bit-identity contract: output and final state equal the no-export call; export equals the cut-at-offset state; offset 0 writes nothing; no-offset calls run the original kernel | invariants 1-3 | C8-6 interior offsets need the prefix-update form to keep the first half | CPU per-token loop meets both trivially | S (tests) | M2 export clause gate |
| Resolve an exact state from a per-position verify column, and refuse when the device ran past the kept tokens | §Speculative decoding | Our K-snapshot slots are the per-position columns | same | S (code read) | KPF-64-SNAPSLOT-READ; FR-UFH14-DIVERGE |
| Evict a state together with its exclusive pages by prefill-saved per freed block | §GDS | host-RAM pool only | same | S | decline (pool not binding) |

## Grounding vs current EPYC state
- **Checkpoint cut positions:** `extra/c17_server_context.cpp` L5297-5333 and L5346-5410 (C17 `ed5d94969` copy). **Post-generation checkpoint:** L3380-3401. **Checkpoint pool and min-step thinning:** L3325-3358.
- **K-snapshot slot layout:** `extra/c17_gdn.cu` L718-731. **C8-6 keep_rs tail chunks:** L37-38. **K as an op param:** L1300-1302.
- **No export-offset input exists.** Searched `c17_gdn.cu` for snapshot/offset parameters: only K and the tree parent input (src[6]).
- **Plan boxes this bears on:**
  - KPF-64-CUTS (plan L190-196);
  - KPF-64-SNAPSLOT-READ (L198-204);
  - FR-UFH14-DIVERGE (L182-188);
  - the M2 monitor export clause (L395-397).

## Adversarial pass (2 queries, shared with intake-2788)
- "FlashStates Arbitrary State Checkpointing hybrid vLLM" found one aggregator page restating the README numbers (restatement). There is no replication or criticism.
- "vLLM mamba_prefill_export … checkpoint_every_n_tokens" found:
  - FlashInfer's docs: upstream `checkpoint_every_n_tokens` must be a multiple of the 64-token chunk size. This independently confirms the gcd-stride and 64-grain constraint the fork works around.
  - vLLM docs: upstream `compute_mamba_prefill_checkpoints` exists for align mode.
  - A Nemotron 3.5 report (arXiv 2610.38095, search snippet only): upstream vLLM PR #57329 gives Mamba-2 in-forward prefill checkpoints by ending a logical chunk at the cache boundary.

  So in-forward checkpoint export is also an **upstream vLLM direction**, not only FlashStates. The chunk-split variant has a production precedent.
- Internal caveats:
  - The doc gives no export overhead numbers.
  - Its tests check bit-identity only on SM100.
  - The CP-route loss is acknowledged but not quantified.

## Plan impact (explicit)
1. **Changed box text: KPF-64-CUTS** (done-when). Proposed:
   > · done when: a per-recipe table split by cut kind (user-message start, reorder junction, n-(4+n_ubatch), n-4) giving cuts per request, extra partial ubatches per request, extra server iterations per request, their wall ms and share of prefill wall time is filed under KPF-64 with the verdict: material if the extra-ubatch time is >= 3% of prefill wall time on any served recipe

   Why: by the C17 batch-fill code the n−4 cut adds an iteration but no ubatch, while the others add a partial ubatch. Export removes ubatches; the snapshot read removes only the n−4 iteration.
2. **Changed box text: KPF-64-SNAPSLOT-READ** (append to done-when):
   > ; the note also states what removing the n-4 cut saves on the served recipes (with n_batch >= n_ubatch + 4 the n-4 break adds a server iteration but no ubatch) and cites the FlashStates fork's per-position spec-column resolution as precedent (intake-2787#record)
3. **Monitor change: M2 export clause.** Exact text is in the intake-2788 dive. It must say that the export route needs no RS-REPLAY-PORT, that the offset is per ubatch, and that the gate is invariants 1-3.
4. **FR-UFH14-DIVERGE:** the coverage refinement is given in the intake-2788 dive (one combined change).
5. No new box.

## Derived-actionables ledger

| id | action | owner | bears on | disposition |
|---|---|---|---|---|
| flashstates-designdoc-A1 | Split KPF-64-CUTS by cut kind and report extra ubatches separately from extra iterations (text above) | handoffs/active/kv-cache-program.md | KPF-64-CUTS | task (box text change) |
| flashstates-designdoc-A2 | KPF-64-SNAPSLOT-READ: price the n−4 cut removal and cite the per-position column precedent | handoffs/active/kv-cache-program.md | KPF-64-SNAPSLOT-READ | task (box text change) |
| flashstates-designdoc-A3 | Export op contract: one offset per sequence per GDN call, relative to the containing ubatch, routed by the ubatch splitter; invariants 1-3 as the test set | handoffs/active/kv-cache-program.md | M2 | monitor text change (fires with KPF-64-CUTS) |
| flashstates-designdoc-A4 | Port the 2-CTA half-row split | — | — | decline: it solves SM100 SM idling with few sequences; gfx90a has no clusters and our np ≤ 4 grid is not SM-starved by this |
| flashstates-designdoc-A5 | GDS / leaf-last eviction, Mooncake hooks | — | 2611.26020v1-A4 | decline: KPF-64 shows the host-RAM checkpoint pool is not binding at our load |

## Dive-surfaced sources
- **vLLM PR #57329** (Mamba-2 in-forward prefill checkpoint by ending a logical chunk at the cache boundary; seen as a search snippet citing arXiv 2610.38095). It would settle the cost and identity behaviour of the chunk-split variant on a production engine. **decline now:** re-surface only when the M2 export trigger fires (KPF-64-CUTS material).
- **vLLM RFC #55697** "Application-Directed Prefix Checkpoints for Hybrid GDN/Mamba" (discuss.vllm.ai; search result). **decline:** llama.cpp already has application-directed targets (`message_spans`, `kv_reorder_junctions`). The RFC's L40S numbers are a forum post.

artifact audit: clean
