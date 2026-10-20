# Stack-change package (DRAFT): EmbeddingGemma 2 BF16 @256 as the REPL embedder-pool model

**Status:** DRAFT 2026-10-20. Stack-change phases 0-5 written down; **not signable**: no patch set exists, no gate has run, and two inputs from other builders are still pending (§6, §7). Nothing was applied, no server was started, no registry/manifest/topology yaml was edited, nothing ran on the stack. Reads were of files, lane worktrees and one GGUF header.
**Owner:** REPL-EMB lane (UFH-12, [`repl-embedding-retrieval.md`](../../handoffs/active/repl-embedding-retrieval.md)); assembled into the v11 kernel-promotion ratification by the promotion session (`kernel-promotion` step 8 hands to `stack-change` phases 7-8).
**Depends on:** [`llama-v11-manifest.md`](../reference/kernel-manifests/llama-v11-manifest.md) rows V11-043 (PEND) and V11-091 (SUPER); the REPL-EMB-2.2 operator decision of 2026-10-20; the `context_search.py` prefix commit (pending, another builder); `scripts/migration/reembed_stores_eg2.py` (pending, another builder); the "trained on BGE vectors" list (pending, another builder).
**Created:** 2026-10-20
**Scratch**: none (doc only)

Sources read: orchestrator lane worktree `/mnt/raid0/llm/worktrees/repl-emb-25-orch-20261020` (HEAD `0b8c69b0`, plus other builders' uncommitted edits to `src/repl_environment/context_search.py`, `src/session/sqlite_store.py`, `src/session/__init__.py`); root lane worktree `/mnt/raid0/llm/worktrees/repl-emb-25-root-20261020` (HEAD `261a718ac`); the candidate tree `/mnt/raid0/llm/worktrees/llama-gemma-embedding2-20261020b` (`63bc737ea`, read only); the research master registry (shared clone, read only).

---

## 0. Posture: what was decided, and what the evidence is

- **Operator decision 2026-10-20 (verbatim, relayed by the coordinator):** "accept the extension-only verdict and adopt EmbeddingGemma 2 BF16 @256, hybrid with grep." It ships with the next production kernel upgrade (v11, which folds the EG2 model support), **together with** the stack change and the store migration. Nothing is promoted piecemeal.
- **The registered arms FAILED the 2.1 kill rule** (hybrid-BGE -0.058, hybrid-Granite +0.055 vs grep, margin 0.10). EG2 @256 hybrid passes only as an **extension-only** arm (+0.139 vs grep, CI [0.087, 0.191], n = 346). This package changes which model the pool serves. It does **not** flip `repl_embedding_pool` or `context_search`, which stay default OFF (REPL-EMB-2.1 rule; no operator order to flip them).
- **Caveat from the operator record, carried unsoftened.** The EG2 gain rests mostly on the synthetic stratum (LLM-written queries, which favour lexical arms, so the bias runs against EG2), and **EG2 hybrid trails BGE and Granite hybrid on probe45 (45 questions)**. A re-check is scheduled for when >= 75 real REPL traces accrue (task REPL-EMB-2.8; the repo has none persisted today).

  | recall@5, primary set (`data/repl_retrieval_eval/repl-emb-22-20261020/analysis.md`) | grep | BGE hybrid | Granite hybrid | EG2 @256 hybrid |
  |---|---|---|---|---|
  | probe45 (n = 45; questions from `intake-1357#03`) | 0.644 | 0.756 | 0.756 | **0.689** (vs grep +0.044, CI [-0.067, +0.156]) |
  | agent_nav (n = 23) | 0.435 | 0.652 | 0.696 | 0.739 (+0.304, CI [+0.087, +0.522]) |
  | synthetic_spill (n = 278) | 0.529 | 0.421 | 0.558 | 0.669 (+0.140, CI [+0.083, +0.201]) |
  | pooled (n = 346) | 0.538 | 0.480 | 0.592 | 0.676 (+0.139, CI [+0.087, +0.191]) |

  Leakage-flagged rows were excluded from the primary set; they lift lexical arms about 21 points (handoff 2.2 result note).
- **What "hybrid" was in the measurement:** the shipped `ContextSearchIndex.search` = BM25 + dense fused with `rrf_fuse` (`FREEZE-RULES.md`: "hybrid (shipped rrf_fuse with BM25)"). `grep` was the lexical baseline L the hybrid was compared against, **not a fusion leg**. See N-4.
- **Measured vs not.** Parity of the EG2 BF16 GGUF against sentence-transformers FP32 is measured (§8). Recall is measured at **800-char chunks only**. Throughput as served by llama-server, decode interference (G1), memory per instance, behaviour at inputs above 459 tokens, and recall at larger chunks are **not measured**. Every such number below is marked.

---

## 1. Intent (phase 0)

```yaml
retire: []                       # BGE is the rollback anchor; deprecating it is refused (retire-model REFUSES)
assign:
  embedder_pool:                 # ports 8090-8095, roles embedder, embedder_1..5 (launch_manifest only; no registry role)
    model: embeddinggemma-2-BF16.gguf        # ggml-org/embeddinggemma-2-GGUF @ 58faf90940886df2d62be555c8765d00dac362c5
    sha256: 68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216
    bytes: 557950176
    served_dim: 256              # server returns 768; client slices to 256 and L2-renormalises
    pooling: mean
    prefix: model-keyed (query / document / code-query), see §4
topology:
  embedding.placement: unchanged # cpusets 136-139 .. 180-183, one NPS4 node each, 4 threads per instance
  embedding.pool_recipe: {context_tokens: 2048 -> 8192, + batch_tokens 2048, ubatch_tokens 2048, + embd_normalize 2, pooling cls -> mean}
stores:
  episodic / skill / strategy / session: 1024-d BGE -> 256-d EG2 via the migration tool, copy-then-swap, .pre-eg2 retained
ships_with: llama.cpp v11 production kernel (one release, one signature)
not_in_this_change: [repl_embedding_pool flag, MI210 GPU embedder (REPL-EMB-0.3, frozen), Granite :8096 warm recipe, any stack_topology.yaml edit]
```

Classification (skills): not a `change-role` shape. Embedders have no `roles.*` or `server_mode.*` row (`launch_manifest.yaml` header and `role_launch_meta` comments), so `classify.py` has no input and none of the alias surfaces (`shared_with`, `model_role`, `port_map` delegation, `_FALLBACK_MAP`) are touched. Not a `change-topology` class either: no cpuset, port, shape or device moves, so `stack_topology.yaml` and `stack_numa.py` are untouched. It is a **recipe + model swap on a launch-manifest-only fleet**, plus a data migration.

---

## 2. Before and after

| Item | v10 live (BGE) | v11 target (EG2) | source of the "before" |
|---|---|---|---|
| model file | `/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf`, 669,603,712 B, sha256 `3379a0e9cea28fc6d7136df8ea7a88ef99ccce5963b9a6f7af9609997be762e3` | `/mnt/raid0/llm/models/embeddinggemma-2-BF16.gguf`, 557,950,176 B, sha256 `68bae29d...f216` (verified here against the downloaded file in `/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/gguf/`) | `launch_manifest.yaml` `models.embedding_model_path`; arm manifest |
| native dim / served dim | 1024 / 1024 | 768 / **256** (slice + L2) | `embedding_pool_policy.yaml` `client.embedding_dim: 1024` |
| pooling | `cls` | `mean`, `--embd-normalize 2` | `embedding.pool_recipe.pooling` |
| `-np` / `-c` / per-slot | 4 / 2048 / 512 tokens | 4 / **8192** / **2048** tokens | `pool_recipe.slots`, `context_tokens` |
| `-b` / `-ub` | not passed (server forces `n_batch = n_ubatch = 512`) | **2048 / 2048** | `_build_embedding_command`; `tools/server/server.cpp:139-144` |
| `-t` | 4, cpuset size 4 (asserted equal at import) | 4 (unchanged) | `stack_manifest._load_embedding_placement` |
| `--flash-attn` | `on` | omitted (server default `auto`; the parity-proven argv had none) | `pool_recipe.flash_attn: true` |
| `--no-mmap` | yes | yes (placement's `--membind` must be real) | `pool_recipe.no_mmap` |
| ports / cpusets | 8090-8095 / `136-139 140-143 144-147 148-151 176-179 180-183` | unchanged | `embedding.placement` |
| `model_id` the pool client reports | `bge-large-en-v1.5-f16.gguf` (`Path(model_path).name`) | `embeddinggemma-2-BF16.gguf` | `src/embedding_pool/topology.py:176` |
| chunk / clip | 800 / 800 chars | **3200 / 3200 chars (proposed, gated)** | `context_search.py` at HEAD `0b8c69b0`, lines 65-67 |
| warm :8096 Granite | `-c 32768 -np 4 -t 16`, cpuset 152-167, default-off | unchanged (not a pool port, so invariant 4 is not touched) | `embedding.extra_recipes` |

Spawn prefix is unchanged: `numactl --membind=<node> -- taskset -c <cpuset>` with the canonical OMP env (A3 was NULL; keep the declared env).

---

## 3. Launch recipe (b)

```
numactl --membind=<node> -- taskset -c <cpuset> \
  <kernels/production/cpu>/llama-server -m /mnt/raid0/llm/models/embeddinggemma-2-BF16.gguf \
  --host 127.0.0.1 --port 809x -np 4 -c 8192 -b 2048 -ub 2048 -t 4 \
  --embeddings --pooling mean --embd-normalize 2 --no-mmap
```

Every number, with its source:

- **`-c 8192` = slots x per-slot tokens = 4 x 2048.** The server gives each slot `n_ctx / n_parallel` tokens; an input over that gets HTTP 400 `exceed_context_size` (`tools/server/server-context.cpp:3642-3660`, candidate tree). The model card says 8,192 tokens; the GGUF header says `context_length = 262144` (same split the 2.5 manifest notes). 8192 total therefore never exceeds the card's limit.
- **No KV memory is bought by `-c`.** `llama_model::create_memory` returns `nullptr` for `LLM_ARCH_GEMMA_EMBEDDING2` (`src/llama-model.cpp:2120-2135`, candidate tree). `-c` is only the per-slot input ceiling. Expect the "n_ctx_seq < n_ctx_train" warning at launch (2048 < 262144); it is not a defect. The saved parity logs ran at low verbosity and do not show whether the warning appeared at `-np 1 -c 8192`, so this expectation is unverified.
- **`-b = -ub = 2048`: a full slot must not be rejected or split.** `-ub` is the hard per-request token limit (`server-context.cpp:3642`, "input ... is too large to process. increase the physical batch size"). For embeddings the server forces `n_batch = n_ubatch` (`server.cpp:139-144`), and the **whole decode batch across all slots** must fit one ubatch (`llama-context.cpp:1736`, `:2082`: "non-causal attention requires n_ubatch >= n_tokens"). A prompt that does not fit the current batch waits for the next pass (`server-context.cpp:3899-3903`). Consequence at 2048: one full 2,048-token slot runs alone; two ~1,000-token chunks co-batch. `-ub 8192` would co-batch four full slots at four times the compute buffer; **not chosen, benefit not measured**. The BGE pool never set either flag, so it ran `n_ubatch = 512`, which is why its 512-token slot just fit.
- **`-np 4`, `-t 4`, `--no-mmap`, cpusets: unchanged.** The cpusets were measured under G0-G3 in Phase 0; `threads == len(cpuset)` is an import-time assertion. EG2 gives no reason to reopen placement.
- **`--pooling mean --embd-normalize 2`.** GGUF `pooling_type = 1`. Explicit flags match the parity-proven launch (`--embedding --pooling mean --embd-normalize 2 -c 8192 -b 2048 -ub 2048 -np 1 --threads 16`; 2.6 execution note). `--embd-normalize` is valid for the server example (`common/arg.cpp:3129-3134`).
- **`--flash-attn` omitted.** The parity-proven argv carried none, so `auto` is what was proven. Whether `auto` resolved to enabled on CPU is not in the saved logs. The v11 parity re-run (G-P1) records it from `/props` or a `-lv 3` log, and uses the **shipped argv verbatim**.
- **Model facts (GGUF header, read only):** 24 layers, `n_embd` 512, `n_ff` 2048, 4 heads, 1-2 KV heads, head dim 512 (global) / 256 (SWA), symmetric sliding window 1024 with every 6th layer global, `embedding_length_out` 768, non-causal, 271M parameters.

**Memory per instance (ESTIMATE, not measured).** Weights 0.520 GiB (557,950,176 B). Compute buffer at `-ub 2048` from the header dimensions: the per-layer-input projection is 512 x 24 x 2048 x 4 B = 100.7 MB and persists across layers; FFN and attention activations add roughly 150-300 MB. Estimate **0.8-0.95 GiB per instance**, **4.8-5.7 GiB for six**, against about 4.0 GiB now (`stack_templates/default.yaml` `ram_gb: 0.67` x 6). That is +0.8 to +1.7 GiB host-wide, inside `capacity.host_os_reserve_gib: 64`, and about 1.6-1.9 GiB per NPS4 node (two instances per node) against 1.4 GiB now; Phase 0 recorded 0.7-2 GB free per node, so a `--membind` allocation can force reclaim. Gate G-M measures `VmRSS`, the log's `compute buffer size` line (needs `-lv 3`) and page locality. The template's `ram_gb` is set from that measurement, not from this estimate.

### Chunk and index constants (`src/repl_environment/context_search.py`)

The comment above `CHUNK_MAX_CHARS` (HEAD `0b8c69b0`, lines 63-64) sizes the 800-char clip against a 512-token slot ("dense JSON/hex ~400 tokens"). The same rule for a 2048-token slot, with a measured density instead of a guess:

- **Measured (saved parity-gate server log, EG2 BF16 GGUF, 211 real project chunks clipped to 800 chars plus the document prefix, 256 tasks incl. 45 queries):** tokens per task min 13, median 211, max 459. For the 211 chunks, chars per token: median 3.43, p5 2.59, **worst 1.73** (a 794-char chunk = 459 tokens). Sample of one corpus (code 80, json/yaml 51, prose 80); not a bound for digit-heavy or base64 content.
- **Rule:** the cap must leave the worst measured density at <= 90% of the slot: 0.9 x (2048 - ~10 prefix tokens) x 1.73 = 3,173 chars, so **3,200**. A full-cap chunk is about 930 tokens at the median density.

| constant | now | proposed | basis | status |
|---|---|---|---|---|
| `CHUNK_MAX_CHARS` | 800 | **3200** | rule above | gated by G-C1 |
| `DENSE_INPUT_MAX_CHARS` | 800 | **3200** | same; clipping stays on the RAW text, before the prefix | gated by G-C1 |
| `INDEX_ASSUMED_TEXTS_PER_S` | 25 | **3.5, provisional** | The 25 was the pool's capped rate (27 texts/s, post-cap G1 load 2026-09-27) of a ~130-token gate text (`EMB_TEXT`), applied to 800-char chunks. In tokens: 27 x ~130 = ~3,500 tok/s. A full-cap chunk is ~940 tokens, so ~3.7 texts/s, rounded down. **Assumes the EG2 pool is no slower than the BGE pool per token.** The ST pilot (BF16 ~3x BGE on documents, below) is a different runtime and is not banked | provisional until G-T1 |
| `MAX_DENSE_CHUNKS` | 4096 | **576** | keeps the module's design of "three searches at the ceiling": 164 s x 3.5 | provisional; the dense ceiling falls from 3.3 MB to 1.8 MB of bundle until G-T1 measures a higher rate |
| `DENSE_BATCH_CHUNKS` | 128 | **16** | progress is kept per finished batch; 128 chunks would be ~37 s at the new rate against a 10-60 s search budget | provisional |
| `QUERY_MAX_CHARS` | 2000 | unchanged | | |

`index_build_timeout_s` keeps its formula `clamp(5 + n / rate, 10, 60)`.

**Fallback that keeps this package independent of the constants:** if G-C1 fails, ship `CHUNK_MAX_CHARS = DENSE_INPUT_MAX_CHARS = 800` and the three index constants unchanged (the measured arm). The pool recipe is identical either way; the unused slot capacity costs nothing (no KV).

**Operator wanted 2048-token chunks.** 3200 chars gives a ~930-token typical full chunk in a slot that admits 2048. A literal ~2048-token typical chunk is ~7,000 chars (median 3.43 chars/token), which overflows the slot for any content denser than ~3.4 chars/token, i.e. a large fraction of code and JSON. Same recipe, different constants; recommended: 3200 first, and revisit with the oversize policy below and G-C1 numbers.

**Oversize policy (code gap, same orchestrator change set).** An input over the slot returns HTTP 400. `PooledEmbeddingClient._run` treats every non-200 as an `_InstanceError`, so one oversize text in a list request fails the whole 4-text request and puts a healthy instance into `failure_backoff_s` (2 s). The 2.2 run already shows the cost: 61 of 582 queries failed at BGE index build because two synthetic bundles held chunks over the 512-token slot. Required: classify an `exceed_context_size` / "too large" reply as a per-text `input_too_long`, retry that text clipped to half, never penalise the instance.

---

## 4. Prefix and dimension seam (c)

**Prefix (other builder, uncommitted at read time; contract as read from the working-tree diff).** `context_search.py` gains `document_text(model_id, text)`, `dense_query_input(model_id, query, code_intent=...)` and `query_text(..., code_intent=False)`, keyed by a lower-cased marker in the pool's `model_id`:

| side | EG2 string | BGE |
|---|---|---|
| query (default) | `task: search result \| query: ` | `Represent this sentence for searching relevant passages: ` |
| query, `code_intent=True` | `task: code retrieval \| query: ` | same as default |
| document (every chunk, applied by `ensure_dense`) | `title: none \| text: ` | identity |
| clip order | raw text clipped to `DENSE_INPUT_MAX_CHARS`, **then** prefixed | prefixed, then clipped (legacy, byte-identical) |

Markers are `embeddinggemma-2` and `egemma2`, matched against `model_id`. **Coupling to this package: the file must be named `embeddinggemma-2-BF16.gguf`** (the name `Path(model_path).name` reports), or the marker misses and EG2 vectors are made with no prefix. The benchmark harness ids (`eg2-gguf-bf16-256#...`) deliberately contain neither marker, so harness adapters keep adding their own prefixes. The 2.2 run pinned the pre-change `context_search.py` sha256 (`6a4b18d6...`); that commit legitimately changes it. The prefix tokens (~10) are inside the 2048 budget in §3.

**Dimension (code that must land in the same orchestrator change set; none of it exists in the lane worktree):**

1. `embedding_pool_policy.yaml`: `client.embedding_dim: 1024 -> 256` plus a new `client.truncate_dim: 256`. `policy.py` rejects unknown keys, so the loader changes with it.
2. `src/embedding_pool/client.py::_run`: `normalise_vector(raw, dim=self._dim)` raises `_DegenerateVector` on `vec.size != dim`, so a 768-d reply would mark every instance failed. Slice to `truncate_dim`, then L2-renormalise, then check dimension. Reuse the definition the harness froze: `scripts/benchmark/repl_emb_arms.py::truncate_renormalise` (keep leading columns, then L2).
3. Three other paths take the raw server vector and L2-normalise it at full size, with **no dimension check**: `orchestration/repl_memory/embedder.py::_generate_embedding_http`, `::_generate_embedding_llama` (subprocess), and `parallel_embedder.py::_embed_single_server`. They feed the 1024-d stores. One shared helper, called from all four paths, or the stores receive 768-d vectors (or fail at `faiss_store`'s dimension check).
4. `TaskEmbedder._generate_embedding_llama` shells out to `DEFAULT_EMBEDDING_BINARY = /mnt/raid0/llm/llama.cpp/build/bin/llama-embedding`, the in-tree v9 build the CLAUDE.md warning describes, which has no `gemma-embedding2`. It must resolve through `kernels/production/cpu/llama-embedding` (present today) with `--pooling mean`, or the fallback must be removed. The v11 candidate must keep `llama-embedding` in its binary set (the 2.6 build produced `llama-server` only; kernel-promotion step 3 binary-set parity covers this, G-B3).
5. `EmbeddingConfig.embedding_dim`, `EmbedderPoolConfig.embedding_dim`, `hash_fallback_embedding(embedding_dim=1024)`, `FAISSEmbeddingStore(dim=1024)` (two defaults), `SkillBank(embedding_dim=1024)` and the literal at `src/api/services/memrl.py:641`: derive from one constant or from `embedding_model.json` (§6), never from a second literal. Hash fallbacks are write-refused and detectable today (`is_hash_fallback_embedding`); the dimension change must not make a 256-d hash vector look valid.

**Stores' own text prefix (open).** `TaskEmbedder` embeds serialized task text with no prefix (symmetric task-to-task similarity). EG2 is asymmetric. The 2.2 eval measured retrieval, not the stores. A prefix choice has to be pinned at write and at query time, and recorded in the sidecar. Recommendation: `task: sentence similarity | query: ` on both sides (the model card's symmetric prompt). Not measured; U-4.

---

## 5. Surfaces (DERIVATION.md source list)

| Surface | Touched | What |
|---|---|---|
| research `orchestration/model_registry.yaml` (master) | yes | **Add** `embedder_embeddinggemma_2_bf16` (tier D, `candidate_roles: [embedder]`, path, bytes, sha256, native 768 / served 256, `server_config`: ports, 4 threads, `context_size` 2048 per slot, `parallel_slots` 4, pooling mean, residency hot). **Keep `embedder_bge_large_en_v1_5` unmodified**: it is the rollback anchor, and `retire-model` refuses to deprecate one. Update the `episodic_memory.embedding` block (model_path, `dim: 1024`, `pooling: cls`, `server_urls` comment); no orchestrator consumer of that block was found by grep, so it is a documentation restatement. The BGE row's `context_size: 512` is already stale against the live `-c 2048`; fix in the same diff |
| orch `orchestration/launch_manifest.yaml` | yes | `models.embedding_model_path`; `embedding.pool_recipe` (`model_name`, `context_tokens 8192`, `pooling mean`, `flash_attn` false, **new keys** `batch_tokens`, `ubatch_tokens`, `embd_normalize`); comments. `placement`, `pool_ports`, `extra_recipes`, `fallback_slots.embedding: 4` unchanged |
| orch `scripts/server/orchestrator_stack.py` | yes | `_build_embedding_command`: emit `-b`, `-ub`, `--embd-normalize` from the recipe; the `recipe is None` fallback dict is a BGE literal (512 ctx), replace or delete |
| orch `scripts/server/stack_manifest.py` | check | recipe keys flow through `**_EMBEDDING["pool_recipe"]`; confirm the new keys need no loader change; `:1901` existence check follows the new path |
| orch `scripts/server/embedder_affinity_check.py` | yes | argv expectations cover only `-c`, `-np`, `-t`, `--no-mmap`; add `-b`, `-ub`, `--pooling`, `--embd-normalize` |
| orch `scripts/server/embedder_placement_gate.py` | yes | G1 text is a fixed ~130-token `EMB_TEXT`; add a text-size option and an `--embedder-ports` option so the gate can drive harness-owned EG2 servers |
| orch `stack_templates/default.yaml` | yes | six embedder entries name `bge-large-en-v1.5-f16`, `quant: f16`, `ram_gb: 0.67`; header comment "6xBGE". This is what `start` reads. Set `ram_gb` from G-M |
| orch `src/embedding_pool/*`, `embedding_pool_policy.yaml` | yes | §4 |
| orch `orchestration/repl_memory/{embedder,parallel_embedder,faiss_store,skill_bank}.py`, `src/api/services/memrl.py`, `src/session/sqlite_store.py` | yes | §4, §6 |
| orch `src/repl_environment/context_search.py` | yes | prefix commit (other builder) + §3 constants |
| orch `stack_topology.yaml`, `stack_numa.py`, `src/config/models.py`, `src/roles.py` | no | no role, alias, shape or cpuset change; embedders are deliberately not NUMA_CONFIG roles |
| kernel store `kernels/production/{cpu,gpu}` | via v11 | repoint belongs to `kernel-promotion` step 7, not this package |
| derived (lean registry, descriptors, priors, procedure enums, `current_stack_summary.md`) | regenerated | never hand-edited. Embedders are not in `stack_priors` (Phase 0 preview), so expect source-hash churn only |
| model file | yes | copy `embeddinggemma-2-BF16.gguf` into `/mnt/raid0/llm/models/`, verify sha256, **no deletion of BGE** |
| docs naming BGE (`orchestration/README.md`, `docs/chapters/{02,04,07,08,09}-*.md`, `MEMRL_DISTILLATION_DESIGN.md`) | text | update at wrap-up |

`scratch.sh`'s source list omits `orchestrator_stack.py`, `stack_manifest.py`, `embedding_pool_policy.yaml`, `context_search.py` and the `repl_memory` files (same finding as the Phase 0 and KVU packages). Build the patch set on lane worktrees, not in `scratch.sh`'s tree.

---

## 6. Store migration and order of operations (d)

**Tool (pending, another builder): `scripts/migration/reembed_stores_eg2.py`** (dry-run, copy-then-swap, rollback; never run on live stores). It did not exist in either lane worktree or in the shared orchestrator clone when this was drafted. This package states **requirements on it**; reconcile with its docstring and actual flags when it lands.

**Stores found (live dir `orchestration/repl_memory/sessions`, file sizes only):**

| store | files | size | rows (derived, not read) |
|---|---|---|---|
| episodic | `episodic.db` (text lives here), `embeddings.faiss`, `id_map.npy` | 539 MB, 264,249,389 B, 2.5 MB | ~64.5k vectors (264,249,389 / 4096 B per 1024-d row, flat index) |
| session | `session_embeddings.npy` | 4,096,128 B | 1,000 x 1024 (this is `(4,096,128 - 128) / 4096`) |
| skill | `skills.db`; `skill_embeddings.faiss` + `skill_id_map.npy` do not exist today (SkillBank flag off) | 90 KB | 0 vectors |
| strategy | `strategy_store.py` (embedding persistence to be confirmed by the tool's author) | | |

The directory is 22 GB, mostly `pre-reseed` / `pre-repair` backups. `reembedded.npz` (1.98 GB) is an old BGE output, not a live store.

**Requirements on the tool and its sidecar.**

1. Dry-run on a **copy** of the live files, before the signature (gate G-S): row counts per store, token-length distribution of the stored texts against the 2048 slot, projected wall time, a sample of re-embedded vectors against a fresh request through the production client path (cosine >= 0.99999; the P6 analogue), and **similarity-score drift**: percentiles of top-k cosines for ~500 sampled queries, BGE vs EG2. Retrieval thresholds were calibrated on BGE (`episodic_memory.retrieval.min_similarity: 0.3`, `confidence_threshold: 0.6` in the master registry; further code-side thresholds are for the owner to enumerate) and **will not carry over** (U-5).
2. Sidecar `embedding_model.json`, written per store dir at swap time. Fields the package needs: `model_id`, GGUF `sha256`, `native_dim`, `served_dim`, `pooling`, `normalise`, `truncation`, `prefix_query`, `prefix_document`, `source_model` (what the store held before), `written_at`, and the tool's `.pre-eg2` path. Actual schema: pending.
3. Absent sidecar means legacy BGE-1024. This is what makes the `.pre-eg2` copies and a rollback self-consistent without editing them.
4. Copy-then-swap under the store's own writer lock (`.episodic_faiss.lock`, the lock `reseed_episodic_store.py` and `repair_*` take), ids and row order preserved, `episodic.db` untouched except for any model-tag column the tool adds.
5. The apply step re-embeds through the **same truncation + prefix code path** the live pool uses, from v11 EG2 servers launched with the production recipe argv.
6. A rollback subcommand that restores `.pre-eg2` and handles rows written after the swap (re-embed them with BGE from `episodic.db`, or export them); otherwise rollback drops them.

**Consumers that must read `embedding_model.json` and refuse a mismatch (no silent hash vector, no silent re-creation).** Confirmed by reading code: `FAISSEmbeddingStore` (`faiss_store.py`, dim defaults at `:98` and `:553`), `EpisodicStore`, `SkillBank` (`skill_embeddings.faiss`, `skill_id_map.npy`) and its constructor call at `src/api/services/memrl.py:641`, `SQLiteSessionStore` (`src/session/sqlite_store.py`, `session_embeddings.npy`; today `_load_embeddings` unlinks a mismatched file, and the refuse-and-keep `SessionEmbeddingsRefused` fix is in the lane worktree, uncommitted), and the writers `TaskEmbedder` and `ParallelEmbedderClient`. Name-grep candidates, owner to confirm: `retriever.py`, `strategy_store.py`, `seed_loader.py`, `replay/*`, `scripts/maintenance/{repair_episodic_embeddings,backfill_skill_embeddings,reseed_episodic_store,verify_episodic_reseed_cosine,check_episodic_integrity}.py`, `scripts/memory/{backfill_faiss_embeddings,migrate_to_faiss,q_scorer_runner,seed_*}.py`, `scripts/graph_router/reembed_episodic_store.py` (hardcodes the BGE path and an in-tree `llama.cpp/build/bin/llama-server`). **Direct pool readers that bypass the stores** and would silently pull full-size EG2 vectors from 8090-8095: `scripts/graph_router/embed_soft_label_dataset.py` (it does guard `!= 1024`) and `scripts/calibration/build_irt_prompt_embeddings.py`. Checked and **not** pool consumers: `src/retrieval/kb_rag.py` (its own ONNX encoder and stored-width check).

**Order of operations.** One maintenance window inside the v11 full-stack apply, run by the session that owns the inference. The stack is going down anyway for the kernel cut, which stops every writer for free; autopilot stops first (CLAUDE.md "Full stack: stop autopilot first").

```
A  before the signature (no real tree touched; harness-owned servers on non-production ports under region claims)
   A1 v11 candidate built with V11-043; strings + linkage + binary set          G-B1..B3
   A2 parity re-run against the candidate, production argv                      G-P1, G-P2
   A3 chunk-constant recall + overflow check on the frozen 2.2 set              G-C1
   A4 EG2 pool G1/G2/throughput on a quiet host, harness EG2 servers co-pinned   G-1, G-2, G-T1, G-M
      to the declared cpusets (idle BGE servers release their OMP teams after 10 ms, so co-pinning
      should not interfere; the A/A spread in G-1 would show it if it does)
   A5 migration dry-run on a copy of the stores                                  G-S
   A6 preflight on the lane trees (stack_change_pipeline check)                  §9
B  OPERATOR SIGNS (inside the v11 kernel-promotion ratification)                 N-1
C  apply
   C0 stack-change-pending set (phase apply)
   C1 read-only preconditions: region claims clear, bench claim empty on 136-183, no autopilot dispatch
   C2 stop autopilot, then stop the stack; verify from /proc that nothing holds the store files
   C3 snapshot every store file to .pre-eg2 (sha256 manifest)
   C4 kernel cut (kernel-promotion step 7)
   C5 merge lanes; stack_change_pipeline update --numa-mode both; check --run-promotion-gate
   C6 copy embeddinggemma-2-BF16.gguf into models root; verify sha256
   C7 migration apply (tool launches v11 EG2 servers from the production argv; stack is down, so the
      full machine is free); writes embedding_model.json per store
   C8 start --numa-mode both; stack-change-pending set --phase bring-up
   C9 serving proof (§11), post-apply G1/G2/G3, then stack-change-pending clear; start autopilot
```

An API-only variant (`reload orchestrator` plus a store lock) is possible but not recommended: the API holds in-memory FAISS handles and is itself a writer.

---

## 7. Things trained on or calibrated to BGE vectors (e): owned follow-ups

The other builder's list is **pending**; once it exists it is referenced from the docstring of `scripts/migration/reembed_stores_eg2.py`. Candidates found by reading code in this lane (not the owner's list):

- `scripts/graph_router/irt_scorer.py` (+ `build_irt_prompt_embeddings.py`): a ridge regressor from 1024-d BGE embeddings to IRT item scores, built from the pool directly.
- Soft-label router dataset: `embed_soft_label_dataset.py` writes `[1024 BGE(prompt) | 5 task_type | 1 norm_ctx_len | 1 has_images]`; `train_graph_router.py` and the MLP router consume it.
- `orchestration/repl_memory/lightweight_gat.py` (`input_dim: 1024`), `routing_graph.py` (DuckDB `embedding DOUBLE[1024]` in three tables).
- Similarity thresholds and Q-value neighbourhoods calibrated on BGE cosines (§6 item 1).

Each is a retrain or a recalibration with its own acceptance test; none is part of this signature, and none may be silently fed 256-d EG2 vectors. Flag every one as an owned follow-up with a task id when the list lands. Until retrained, the guard is the dimension check plus the sidecar refusal.

---

## 8. Gates (g)

Pre-registered here, proposed for signing. Unit and direction are stated. Nothing below has run.

| Gate | Measures | Direction / unit | Band | Status |
|---|---|---|---|---|
| **G-B1** build | v11 candidate contains EG2 | `strings bin/libllama.so \| grep gemma-embedding2` >= 1 hit; library and binary mtimes after the candidate's commit time | present | pending (0 hits in `cpu-20261020-dd3d9721c`; present on the 20261020b rebuild) |
| **G-B2** linkage | no foreign ggml | `verify_ggml_linkage.sh` PASS on the candidate and on a launched pool instance (`/proc/<pid>/maps`; `ldd` cannot prove it) | PASS | pending |
| **G-B3** binary set | `llama-embedding` + `llama-server` in the set | kernel-promotion step 3 parity vs anchor | PASS | pending |
| **G-P1** parity, short inputs | the 2.5 parity gate re-run **against the v11 binary on the shipped argv** (`-np 4 -c 8192 -b 2048 -ub 2048 -t 4`), inputs sent in lists of 4 so slots co-schedule: `epyc-orchestrator/scripts/benchmark/repl_emb_parity_gate.py`; records `flash_attn` resolution | per-item cosine vs ST FP32, higher = better; non-finite count | zero non-finite and min cos >= 0.99 on >= 200 chunks + the 45 probe questions | pending. Measured so far (v10 port and the 20261020b rebuild, `-np 1`): min cos docs 0.999990, queries 0.999997, mean 0.999997; 256-d view docs min 0.999992 (informational) |
| **G-P2** parity, long slot | **new**: >= 20 real inputs of 1,500-2,040 tokens | same | same | pending. **Nothing above 459 tokens has ever been compared**; SWA window 1024 and position handling above ~500 tokens are unproven against ST |
| **G-C1** chunk constants | the 2.2 deciding set re-scored at `CHUNK_MAX_CHARS = DENSE_INPUT_MAX_CHARS = 3200`; plus `/tokenize` of every chunk the frozen corpus produces at that cap (no inference) | recall@5, higher = better; tokens, lower = better | PASS: EG2 @256 hybrid - L >= 0.10 with paired-bootstrap lower bound > 0 (the extension rule), **and** hybrid@3200 not below hybrid@800 (0.676) by more than 0.05 (the 2.1 equivalence margin), **and** max tokens + prefix <= 2048 or the oversize policy (§3) is merged. FAIL: ship 800 | pending; correctness work, any window |
| **G-T1** throughput and request latency | EG2 pool texts/s with a ~3,200-char text, capped (scheduler mode) and uncapped; p99 of a worst-case 4 x ~2,040-token request | texts/s higher = better; seconds lower = better | sets `INDEX_ASSUMED_TEXTS_PER_S`; p99 <= 10 s (2/3 of `request_timeout_s: 15`) | pending. Uncontended window not required (operator ruling 2026-10-20: accuracy work is not performance-sensitive); the **absolute** numbers carry their contention label |
| **G-1** (G1) decode interference | S/Q on :8070, :8080, :8180: median (pool saturated) / (pool idle), decode tok/s, ABA, A/A spread in tok/s as the floor, run with the scheduler's neighbour cap ON, at **three text sizes**: ~130 tokens (comparable with Phase 0), ~1,000, ~2,000 | ratio, higher = better | proposed: **PASS** if each port is >= the BGE post-cap value for that port minus the larger A/A floor (BGE post-cap 0.921 / 0.918 / 0.862, `data/embedder_placement/post-cap-20260927.json`); **needs-operator** if below that but >= 0.86 (lowest value the operator has accepted); **ROLLBACK** below 0.86. Absolute 0.95 / 0.90 reported beside it | pending. **Not claimed anywhere in this package.** A pre-apply run (A4) and a post-apply run (C9) |
| **G-2** (G2) pool scaling | whole pool / one port, texts/s | ratio, higher = better | >= 4.0 (BGE: 4.96) | pending |
| **G-3** (G3) speech | STT RTF, TTS first packet with the pool saturated, frontdoor idle, **warm-up discard pre-registered** | RTF lower = better; ms lower = better | STT RTF <= 0.40, TTS first packet <= 500 ms | pending |
| **G-M** memory | `VmRSS` per instance, log `compute buffer size`, page locality on the declared node | GiB lower = better; % higher = better | <= 1.1 GiB per instance, >= 95% resident on the node (BGE: 97.8-98.9%) | pending; replaces §3's estimate |
| **G-S** migration dry-run | §6 item 1 | cosine; count | rows in = rows out; sample cosine >= 0.99999 | pending (tool pending) |
| **G-X** signature | one operator signature on the v11 ratification | | | N-1 |

**Reference numbers, with their labels (nothing here is a speed claim):**

- Parity: EG2 BF16 GGUF is parity-proven (table row G-P1); Q8_0 min cos 0.999323 docs / 0.999844 queries, not adopted.
- Contended query latency from the 2.2 run, p50: EG2-256 hybrid 16 ms, BGE hybrid 132 ms. **Contended, mixed server recipes, NOT for any speed claim.**
- Pilot ST screen (`artifacts/research/emb-speed-20261020/`): ST BF16 EG2 41.7 chunks/s vs ST FP32 BGE-large 13.0 (48 threads, batch 32, 256-chunk subset), about 3x; ST FP32 EG2 20.7. Different runtime from llama-server, FP32 BGE as the control (not the f16 GGUF), noise floor 4.7%, peers and a GPU queue were running. **The as-served llama-server BGE leg was never run**; the operator dropped the quiet-host speed block.
- Post-cap BGE G1 baseline: 0.921 / 0.918 / 0.862 (< the 0.95 target; kept by operator decision D3).

---

## 9. Phase 3-5 status

- **Preflight (phase 3):** not run. No candidate tree exists. At assembly: `stack_change_pipeline.py check --numa-mode both` on the lane trees, plus `assert_alias_clean.py --all` (must be unchanged), `topology_check.py` and `capacity.sh` (confirmations; nothing moves).
- **Expected classes.** `fixable-by-transform`: lean registry, descriptors and priors stale against the edited sources until `update`; `stack_templates` model names; the launch-manifest source-hash mismatches. `needs-measurement`: G-P1 to G-S. `needs-operator`: N-1 to N-4.
- **Measure (phase 4):** the gate table above. `--allow-known-gaps` is not offered for any of it.
- **Package (phase 5):** this file becomes the narrative section; the patch set, `PROVENANCE.json`, preflight outputs, the ratify script and its receipt are assembled by the promotion session on the lane branches. The package is the complete multi-repo set or it is not a package: research (master registry), orchestrator (all of §5), root (docs, receipts).

---

## 10. Apply and bring-up (draft; phases 7-8)

```bash
# C0
python -m src.runtime.gpu_window_executor stack-change-pending set --change-id stackchg-eg2-embedder-<date> --phase apply
# C5  (after the kernel cut, lanes merged by merge, never a pathspec sweep)
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
.venv/bin/python scripts/registry/stack_change_pipeline.py check --numa-mode both --run-promotion-gate
# C6
sha256sum /mnt/raid0/llm/models/embeddinggemma-2-BF16.gguf    # expect 68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216
# C8
.venv/bin/python scripts/server/orchestrator_stack.py start --numa-mode both
python -m src.runtime.gpu_window_executor stack-change-pending set --change-id stackchg-eg2-embedder-<date> --phase bring-up
# C9 after the serving proof passes
python -m src.runtime.gpu_window_executor stack-change-pending clear
```

If the stack is already up for a reason other than the v11 cut, the embedder-only form is `orchestrator_stack.py reload embedders` (a real component name; it kills all six before starting any, so a bench-guard refusal after the kill leaves the pool down: check `read_bench_claim()` first, as in Phase 0). While all six are down, `TaskEmbedder` falls back to write-refused hash vectors; writers must be idle.

## 11. Serving proof (report what each returned; `healthy` is not proof)

- **P1** per instance: `argv[0]` resolves into `kernels/production/cpu`; argv carries `-c 8192 -np 4 -b 2048 -ub 2048 -t 4 --pooling mean --embd-normalize 2 --no-mmap`; `/proc/<pid>/maps` shows the v11 `libllama.so` and `strings` of that mapped library shows `gemma-embedding2`; `embedder_affinity_check.py` exits 0 (cpuset, disjoint OMP places, node locality).
- **P2** `/props` reports `n_ctx` 8192 (2048 per slot); one 2,000-token input returns a vector (BGE: rejected above 512).
- **P3** real embeddings through the **production client path**: 256-d, unit norm, finite, and cosine >= 0.999 against the saved ST FP32 reference vectors in `parity/probe45` for the same 45 questions.
- **P4** a context.search index build on a real bundle reports `mode: hybrid`, `embedder_model` = `embeddinggemma-2-BF16.gguf`, no `model_mismatch`.
- **P5** every store dir has `embedding_model.json`; every consumer in §6 starts, reads it, and a deliberately mismatched dummy is refused with the store untouched.
- **P6** `orchestrator_stack.py status`: 6/6 embedders, no attestation drift; no new hash-fallback rows from the window (`repair_episodic_embeddings.py` diagnose).
- **P7** G-1, G-2, G-3 `--label post`, bands as in §8.

## 12. Rollback (f)

- **Pool recipe:** `git revert` the orchestrator and research patches (the v10 BGE pool recipe is the committed pre-change `embedding.pool_recipe`: `context_tokens: 2048, threads: 4, slots: 4, pooling: cls, flash_attn: true, no_mmap: true`, model `bge-large-en-v1.5-f16.gguf`), then `update` and `reload embedders`. BGE weights and the BGE registry row are never touched, so nothing needs re-downloading.
- **Stores:** `.pre-eg2` copies are retained (deleting them is the operator's separate confirmed action). Restore via the tool's rollback subcommand, which must also deal with rows written after the swap (§6 item 6). An absent sidecar restores the legacy BGE meaning.
- **Coupling:** v10 cannot load `gemma-embedding2`. A kernel rollback to the v9/v10 anchor therefore **forces** the pool and store rollback in the same step; the reverse is independent (the BGE pool runs on v11). Order a full rollback as stores, then pool, then kernel.
- **EG2 GGUF stays on disk.** The GPU embedder, Granite, and the `repl_embedding_pool` flag are unaffected.
- **Triggers:** any ROLLBACK cell in §8; P1-P6 failing after one retry; G-1 below 0.86 on any port after apply.

## 13. needs-operator

- **N-1 Sign** the v11 ratification with this package attached. Nothing here is signable until the patch set, the migration tool and the retrain list exist.
- **N-2 G1 thresholds for the EG2 pool** (§8): recommended non-inferiority to the accepted BGE post-cap values, hard floor 0.86, absolute 0.95/0.90 reported. Alternative: the Phase 0 bands (0.95 / 0.90), which the incumbent itself does not meet.
- **N-3 Window:** a quiet period with no autokernel CPU arm and no bench claim on 136-183, inside the v11 full-stack window.
- **N-4 "Hybrid with grep".** The measured arm is BM25 + dense (RRF); grep was the baseline. Is that what was meant? If you meant grep hits as the lexical leg, that arm was **not measured**, and one extra offline arm on the frozen set (correctness work, any window) must precede the signature. Default assumed here: the measured arm. This blocks nothing else.
- Chunk size (3200 now, ~7000 for a literal 2048-token chunk) is **not** an operator item: decided by G-C1 with 800 as the fallback.

## 14. Not in this change (h), and the not-measured ledger

- **MI210 GPU timing** (HIP, Vulkan) stays in the frozen REPL-EMB-0.3 package. The GPU embedder, the B+D saturation-guard policy (REPL-EMB-1.4) and any flag flip are not here.
- **Not measured:** EG2 llama-server throughput and latency uncontended; EG2 G1; memory per instance; parity above 459 tokens; recall at 3,200-char chunks; behaviour of the oversize path; the EG2 argv the 2.2 EG2 arms ran on (the deviation file records only the BGE server recipes); `flash_attn` resolution on CPU; the stores' retrieval quality and similarity thresholds on EG2.
- **Belief-kernel wiring (prepared; the owning session applies):** G-1/G-2/G-3 ride the existing `embedder_placement_capture` writer (VB-UFH12-PLACEMENT); G-C1 rides the 2.2 harness writer (VB-UFH12-RETR); G-P1/G-P2 and G-T1 need a write side confirmed (`repl_emb_parity_gate.py` has none that I found). If absent, add a row to `scripts/vidya/adapters/README.md` and a task in `vidya-belief-substrate-program.md` before the first gate runs.
- **Index:** no row proposed. This is a design package under `docs/design/`, not a handoff; `handoffs/active/` would fail `index_state.py --check` (ORPHAN) without a row. If the REPL-EMB owner wants a pointer, the UFH-12 row's next action can name this file; row edits are the owning session's.

## 15. Unknowns (each with the check that closes it)

| # | Unknown | Closes with |
|---|---|---|
| U-1 | Whether 3,200-char chunks hold recall | G-C1 |
| U-2 | EG2 as-served throughput; the true `INDEX_ASSUMED_TEXTS_PER_S` | G-T1 |
| U-3 | EG2 decode interference on frontdoor halves | G-1 |
| U-4 | The stores' text prefix for symmetric task similarity (recommended `task: sentence similarity \| query: `) | migration dry-run neighbour-overlap + the tool's sidecar |
| U-5 | Retrieval thresholds on EG2 cosines | dry-run similarity percentiles; owner recalibrates before the swap |
| U-6 | Parity above 459 tokens | G-P2 |
| U-7 | Migration tool schema, flags, run time (~64.5k episodic rows) | tool lands; G-S |
| U-8 | The retrain / recalibration list | other builder's report |
| U-9 | Whether `strategy_store.py` persists embeddings | tool author |
| U-10 | Digit-heavy and base64 content density under the Gemma tokenizer (worst measured 1.73 chars/token is from one corpus) | G-C1 `/tokenize` pass over the frozen corpus |
