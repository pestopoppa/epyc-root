# Stack-change package: UFH-12 Phase 0 — embedder placement + `-c 2048`, and stale stack-config text

**Date**: 2026-09-26 · **Skill**: stack-change phases 0–5 (+ change-topology checks) · **Status**: READY FOR OPERATOR SIGNATURE
**Handoff**: `handoffs/active/repl-embedding-retrieval.md`, task **REPL-EMB-0.1**. The handoff says its owner index row is **UFH-12**; the dispatch called it UFH-11, which is the website row. This package uses UFH-12.
**Scope, as approved by the operator**: one package covering (A) the embedder placement defect and (B) stale stack-config text, so there is one signature.

Nothing here has touched a real tree or the live stack. All edits are on lane branches. Live reads were read-only:
`/proc/<pid>/{cmdline,environ,status,task/*/status,numa_maps}`, `numactl -H`, `rocm-smi`, KFD `vram_*`, and
`bench_core_claim.read_bench_claim()`. No process was started, stopped or signalled, and no inference or embedding request was sent.

---

## 0. Intent

```yaml
topology:
  embedder_pool:            # :8090-:8095, BGE-large-en-v1.5 f16. Model UNCHANGED.
    placement: one cpuset per port, SMT siblings, one NPS4 node each, next to a serving model (D1)
    context_tokens: 512 -> 2048          # 512 tokens per slot at -np 4
    no_mmap: true                        # private weights, so the membind is real
  embedder_granite_97m_r2:  # :8096, WARM, stays default-off. Model choice waits for the Phase-2 eval.
    placement: 152-167
text_only:                  # (B) comments and descriptions; no launch argv changes
  - launch_manifest.yaml, stack_topology.yaml  (orchestrator, hand-edited sources)
  - model_registry.yaml MASTER                 (research; the lean copy is derived)
```

## 1. The defect, read from `/proc` (2026-09-26, `affinity-before-live-20260926.txt`)

| Port | PID | argv | OMP team places (per-task `Cpus_allowed_list`) | all other tasks | resident pages on the node the new plan assigns |
|---|---|---|---|---|---|
| 8090 | 2022735 | `-np 4 -c 512 -t 4` | 0,96 · 32,128 · 48,144 · 88,184 | 194 tasks on 0-191 | 28.8% |
| 8091 | 2022949 | same | **same four** | same | 28.9% |
| 8092 | 2023219 | same | **same four** | same | 30.8% |
| 8093 | 2023456 | same | **same four** | same | 30.3% |
| 8094 | 2023679 | same | **same four** | same | 6.0% |
| 8095 | 2023882 | same | **same four** | same | 5.5% |

**Cause**: `role_launch_meta.embedder*: {no_numa: true}` gives an empty spawn prefix (`stack_numa._numa_prefix`,
fallback branch). Then the canonical OMP env (`OMP_PROC_BIND=spread`, `OMP_PLACES=cores`) picks the same 4 core
places in every process. **The pool has one server's compute, and it sits on 4 cores inside frontdoor's 0-95.**
When the pool is busy, those 4 cores carry 6 embedder threads plus a frontdoor OMP thread each, and frontdoor's
barrier waits on them. Per-slot context is 256 tokens (`/props`), below BGE's 512-token window.

## 2. Core map

### Before (live)
| Logical CPUs | Physical | Tenant |
|---|---|---|
| 0-95 | all | frontdoor full :8070 (`-t 96`, interleave=all) and critic :8074 (`-t 96`), which hold region locks, so they alternate |
| 0-47, 96-143 | 0-47 | frontdoor half A :8080 (`-t 48`) |
| 48-95, 144-191 | 48-95 | frontdoor half B :8180 (`-t 48`) |
| 0-23 | 0-23 | whisper :9000 (`-t 24`, declared cpuset) |
| 24-39 | 24-39 | tts :9002 (16 threads, declared cpuset) |
| 184-191 | 88-95 | GPU host lane: :8083 27B, :8086 VL (`-t 8` each) |
| **0/96, 32/128, 48/144, 88/184** | **0, 32, 48, 88** | **all six embedders' compute teams** |

### After (proposed)
| Port | cpuset | NPS4 node | Siblings of physical | Next to (D1) |
|---|---|---|---|---|
| 8090 | 136-139 | 1 | 40-43 | half A :8080 (nodes 0,1) |
| 8091 | 140-143 | 1 | 44-47 | half A :8080 |
| 8092 | 144-147 | 2 | 48-51 | half B :8180 (nodes 2,3) |
| 8093 | 148-151 | 2 | 52-55 | half B :8180 |
| 8094 | 176-179 | 3 | 80-83 | GPU host lane 184-191 (:8083, :8086), and half B |
| 8095 | 180-183 | 3 | 84-87 | GPU host lane, and half B |
| 8096 (warm) | 152-167 | 2 | 56-71 | reserved for the Granite-97M-R2 eval; not launched by `start` |
| — | 168-175 | 3 | 72-79 | left unallocated |

Full :8070 and critic :8074 span all four nodes, so every instance is next to them. Each spawn is
`numactl --membind=<node> -- taskset -c <cpuset> llama-server … -np 4 -c 2048 -t 4 … --no-mmap`.

**Excluded**: 96-119 (siblings of whisper 0-23), 120-135 (siblings of tts 24-39), and 184-191 (the GPU host lane).
whisper.cpp hangs on unmeasured layouts (`launch_manifest.yaml` whisper entry), so nothing is placed on its siblings.

## 3. Where the cores come from: options

No logical CPU on this host lacks a physical sibling in 0-95 (kernel-verified 2026-09-07,
`feedback_pinned_gpu_host_threads_still_degrade_cpu_floor_9x`). So no free cores exist. The only question is who pays, and when.

| Option | Cost to frontdoor/critic decode | Reversible | Verdict |
|---|---|---|---|
| **(a) Carve physical cores out of 0-95** (e.g. `-t 72`) | Paid on **every** decode, even with an idle pool. The nearest measurement: partitioning the LLMs to 40-95 cost them 22–26% (2026-09-24, `docs/reference/speech/cpu-speech-contention-20260924.md`). It also re-shapes `NUMA_FULL`, the halves, the contention matrix, and every piece of full-shape evidence | Costly | **Reject** |
| **(b) SMT siblings, off the speech siblings and the GPU lane** | Paid only while an embedder computes. `KMP_BLOCKTIME=10` releases an idle team after 10 ms. The frontdoor full instance pins physical cores only, and each half's OMP places are `{phys, sibling}` pairs, so an embedder thread shares a core rather than displacing a thread. The size of the cost is **gate G1**, not an assumption | One data block | **Recommend** |
| (c) Siblings of the speech cores (96-135) | Puts the load on the realtime speech path. That path already collapses under a generating `-t 96` LLM, and whisper hangs on unmeasured layouts | — | Reject |
| (d) Status quo | A pool that is one server wide, sitting on 4 frontdoor cores | — | This is the defect |

## 4. Measurement gates (pre-registered, signed with the package)

The driver is `scripts/server/embedder_placement_gate.py` (orchestrator lane). It sends HTTP only.
Run it **before** apply (`--label pre`, old placement) and **after** the embedder reload (`--label post`), both inside
`scripts/region-lock run --cpu-list 0-191 -- …`. Host condition: no `llama-bench`, no autokernel CPU arm, and
autopilot not dispatching (`feedback_host_drifts_3pct…`, ABA alternation built in).

| Gate | Measures | Unit / direction | PASS | needs-operator | ROLLBACK |
|---|---|---|---|---|---|
| **G0 idle cost** | `post` Q-arm decode vs `pre` Q-arm decode on 8070/8080/8180 (pool idle) | tok/s, higher = better | within the larger of the two runs' A/A floors | — | outside the floor on any port |
| **G1 frontdoor decode cost** (required by the dispatch) | `post` median S/Q per port (pool saturated, 24 requests in flight, vs idle) | ratio of tok/s, higher = better | ≥ 0.95 on 8070, 8080 and 8180, **and** not below the same port's `pre` S/Q by more than its A/A floor | 0.90 ≤ S/Q < 0.95: operator picks keep / 4-instance pool / Phase-1 scheduler cap, with the number shown | < 0.90 |
| **G2 pool scaling** | `post` texts/s on the whole pool ÷ texts/s on one port | ratio, higher = better | ≥ 4.0 (expect ~6) and > `pre` ratio | 2.0–4.0 | < 2.0 (no gain) |
| **G3 speech non-regression** | STT RTF and TTS first-packet on the standard clip, pool saturated, frontdoor idle, via the method in `epyc-inference-research/artifacts/speech_cpu_realtime_20260924/README.md` | RTF lower = better; ms lower = better | STT RTF ≤ 0.40 and TTS first packet ≤ 500 ms (quiet baseline 0.20–0.24 / 91–311 ms) | — | above either |

The frontdoor cost is **not claimed anywhere in this package**. It is G1's number, read from `post.json`.
The G1 thresholds (0.95 / 0.90) are my proposal. The operator may change them when signing (§11).

## 5. Patch set (committed on lane branches, not applied)

| # | Patch | Repo · branch · commit | Content |
|---|---|---|---|
| 1 | `patches/orchestrator-01-embedder-placement-ctx2048-stale-text.patch` | epyc-orchestrator · `lane/ufh11-phase0-20260926` · `845950b4` | `launch_manifest.yaml`: `embedding.placement`, `context_tokens 2048`, `no_mmap`, plus the (B) text fixes. `stack_topology.yaml`: (B) text only; `numa_config` is untouched. `stack_manifest.py`: `EmbedderPlacement`, `EMBEDDING_PLACEMENT` and an import-time validator. `orchestrator_stack.py`: `_embedding_spawn_prefix` (refuse, never re-pin) and `--no-mmap`. New read-only proof tool `scripts/server/embedder_affinity_check.py`. New `tests/unit/test_embedding_placement.py` (18 tests); one launch-parity test updated for :8096's placement. `embed_soft_label_dataset.py`: a comment |
| 2 | `patches/orchestrator-02-measurement-gate-driver.patch` | same branch · `05048a66` | `scripts/server/embedder_placement_gate.py` (G0–G2) |
| 3 | `patches/research-01-stale-role-descriptions.patch` | epyc-inference-research · `lane/ufh11-phase0-20260926` · `7640269b` | Master registry, description and comment text only (§8) |

Every patch is rebased on current `origin/main` (orchestrator `228e0a2c`, research `2a060a41`).
`git apply --check` passes against the research shared clone. The orchestrator shared clone's local `main`
(`fb7871ea`) is 6 commits behind `origin/main`, so apply by merging the lane (§9), not by `git apply` onto a stale `main`.

### Surfaces (DERIVATION.md source list)
| Surface | Touched | Why |
|---|---|---|
| research `model_registry.yaml` (master) | text only | (B). No `roles.*`/`server_mode.*` values change, and `candidate_roles` membership is unchanged |
| `stack_topology.yaml` | text only | `numa_config` is unchanged. Embedders are deliberately **not** made NUMA_CONFIG roles: that would pull them into region locks, the contention matrix and the capacity report |
| `stack_numa.py` | no | no new shape. The embedder cpusets are not decode instances and must not enter `_CPU_SHAPES` |
| `launch_manifest.yaml` | yes | the embedder recipe and placement live here, next to the aux services' `cpuset` precedent |
| `src/config/models.py`, `src/roles.py`, `stack_templates/*.yaml` | no | no role, alias or template change |
| `scripts/server/stack_manifest.py`, `orchestrator_stack.py` | yes | a declared cpuset had no load, validate or emit path. These files are not in `scratch.sh`'s source list; the source set is incomplete for launcher features (same finding as the KVU package) |
| kernel store symlink | no | unchanged (`production/cpu → builds/cpu-20260921-ffc1bac82/bin`) |
| derived artifacts | **never hand-edited** | `PREVIEW-derived-after-update.diff` shows what `update` produced in scratch: only source hashes, `repo_commit`, `compiled_at` and the three description strings. Embedders are not in `stack_priors`. **Do not apply the preview**: phase 7 regenerates it, and its paths point at scratch |

## 6. Preflight (one classified list)

`pipeline-check-baseline.txt` (pristine `origin/main`) vs `pipeline-check-candidate.txt` / `pipeline-update-candidate.txt`:

- **fixable-by-transform (all closed by `update`)**: lean/descriptors/priors are stale against the edited sources, and the `source_artifacts.*` hash mismatches (launch_manifest, orchestrator_stack, stack_manifest, stack_topology). After `update` in scratch: `lean_registry ok`, `guard ok`, `guard_strict ok`, `stack_manifest_registry ok`, `q_scorer_priors ok`.
- **scratch artifact, not a violation**: `runtime_attestation` reported every live port as an "unmanaged listener" because the lane worktree has no `logs/orchestrator_state.json`. It must be re-run from the real tree after apply (P8).
- **pre-existing (in the baseline too)**: the descriptor artifact is stale on pristine main. `test_quarter_stack_smoke::test_derived_chat_ports_drop_retired_ports_and_pick_up_live_ones` fails identically on pristine main (`KeyError: 'worker_general'`).
- **needs-measurement**: G0–G3 (§4). They cannot run before signature: they send inference and need a quiet host.
- **needs-operator**: N-1…N-4 (§10).
- `topology_check.py`: PASS (5 roles, 7 instances, 8 shapes), unchanged. Tests: 302 passed across the launcher, manifest, reload, prewarm, numa, simulated-fixture and parallel-embedder suites; ruff clean.

## 7. Capacity
- **Host leg**: no declared model row changes, so the report is unchanged. `--no-mmap` adds about 6 × 0.62 = 3.7 GiB of private weights, minus the 0.62 GiB shared page cache they replace. That fits inside `capacity.host_os_reserve_gib: 64`, which already names the embedder pool. KV is nil: BERT keeps no KV cache.
- **Per-node**: `numactl -H` shows about 0.7–2 GB free per node. The rest is page cache. `--membind` forces reclaim on the target node, the same mechanism `stack_numa_evict.py` relies on. About 1.4 GiB per node is needed, and P5 verifies locality.
- **GPU leg**: unchanged. The MI210 has 1.52 GiB free now (68.70 − 67.07 GB: :8083 42.9 GB, :8086 24.0 GB).
- **Contention matrix**: `topology_hash` 4893e37e is unchanged, because `numa_config` is untouched (pre-commit hook: fresh). The matrix cells were measured with an idle pool. The busy-pool cross-term is exactly what G1 measures, so no recert is required.

## 8. Part B — stale text, each fix verified

| Where | Said | Truth (how verified) |
|---|---|---|
| `launch_manifest.yaml` header + `port_map.frontdoor` | quarters 8080/8180/8280/8380 | halves 8080/8180 (live PIDs 2025603/2028639 `-t 48`; `stack_topology.yaml` frontdoor instances) |
| `launch_manifest.yaml` `port_map.coder_escalation`, `role_launch_meta.architect_general` | Qwen3.6-27B; aliases `[coder_escalation]` | Qwen3.8-27B-Q8_0 since 2026-08-20 (live :8083 argv; research `b376dadd`); `shared_with: [coder_escalation, ingest_long_context]` |
| `launch_manifest.yaml` `port_map.architect_critic`, `role_launch_meta.architect_critic` | "the 122B UD-Q4_K_M" | Qwen3.8-Flash-Next UD-IQ4_XS since 2026-09-22 (live :8074 argv) |
| `stack_topology.yaml` frontdoor header | Qwen3.5-35B-A3B Q4_K_M, 5-instance pre-warm | Qwen3.6-35B-A3B-MTP-Q8_0, 1 full + 2 halves. The old figures are marked not re-attributable |
| `stack_topology.yaml` critic header, ROLE DEFINITION, W1 note (~:170-212) | 122B critic; architect_general "serves Qwen3.6-27B" | Qwen3.8-Flash-Next on :8074 and Qwen3.8-27B on :8083. The history is kept and dated |
| master `roles.worker_general.description` | gemma4-26B-A4B | alias on frontdoor's :8070 Qwen3.6-35B-A3B process (`server_mode.frontdoor.shared_with` includes `worker_general`; gemma4 retired 2026-09-22) |
| master `roles.architect_general.description` | Qwen3.6-27B | Qwen3.8-27B-Q8_0 since 2026-08-20; hosts coder_escalation and ingest_long_context |
| master `qwen38_flash_next_ud_iq4xs_local` description, section comment, `candidate_roles` comment | ingest_long_context is an alias on :8074 | **server_mode is right, the description was wrong.** `server_mode.ingest_long_context.alias_of: architect_general`, `server_mode.architect_general.shared_with` includes it, `src/roles.py:489,509` → ARCHITECT_GENERAL, `src/config/models.py:344` → `http://localhost:8083`, `port_map` → 8083, and `derived/stack_priors.yaml` records "Operator ruling C2 sent ingest_long_context to the GPU 27B" |

Placement: the master registry for (B) descriptions (the lean copy is derived, per `feedback_ledger_goes_in_master_not_compiled_output`).
The hand-edited orchestrator sources for the manifest and topology comments. **No human-only path is touched**
(`coordination/session-bus/human_only_paths.yaml`), so no trust-boundary token is needed. The signature below is the stack-change gate.

## 9. Bring-up (phases 7–8, after signature, by the session that owns the inference)

**Preconditions** (all read-only):
1. No bench on the embedder cores. Run `.venv/bin/python -c "from scripts.server.bench_core_claim import read_bench_claim, decide_placement as d; c=read_bench_claim(); print(c.empty, [d(x,force=False,claim=c)[0] for x in ('136-139','140-143','144-147','148-151','176-179','180-183')])"` and expect `True` and all `proceed`. This read `True` at prep time. Why it matters: `reload embedders` kills all six **before** starting any, so a refusal after the kill leaves the pool down.
2. Quiet window for G1 (no autokernel CPU arm). The DS41 anchor server on :18641 (PID 2697775, 0-95) was live at prep time.
3. Episodic writers idle. While all six embedders are down, `TaskEmbedder` falls back to **hash pseudo-embeddings** (`use_fallback=True`). Reload when autopilot and chat traffic are idle.

```bash
# 7a — pre-change measurement on the CURRENT stack (old placement)
cd /mnt/raid0/llm/epyc-orchestrator && git pull --ff-only
scripts/region-lock run --cpu-list 0-191 -- .venv/bin/python /mnt/raid0/llm/worktrees/ufh11-phase0-orch-20260926/scripts/server/embedder_placement_gate.py --label pre --out /mnt/raid0/llm/epyc-orchestrator/data/embedder_placement/pre-20260926.json
curl -s -X POST localhost:8090/v1/embeddings -H 'Content-Type: application/json' -d '{"input":["pointer, not summary"]}' > /mnt/raid0/llm/tmp/stack-change-ufh12-phase0-20260926/p6-pre.json
# 7b — apply (merge the lanes; never a pathspec sweep)
cd /mnt/raid0/llm/epyc-orchestrator && git fetch -q && git merge --ff-only origin/lane/ufh11-phase0-20260926
cd /mnt/raid0/llm/epyc-inference-research && git fetch -q && git pull --ff-only && git merge --ff-only origin/lane/ufh11-phase0-20260926
cd /mnt/raid0/llm/epyc-orchestrator && .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
.venv/bin/python -m pytest -q tests/unit/test_embedding_placement.py tests/unit/test_build_server_command_helpers.py tests/unit/test_stack_manifest_imports.py
.venv/bin/python scripts/registry/stack_change_pipeline.py check --numa-mode both --run-promotion-gate   # expect only the pre-existing failures named in §6
# 8 — bring up: embedders ONLY. Frontdoor, critic, GPU roles and the API are NOT reloaded.
.venv/bin/python scripts/server/orchestrator_stack.py reload embedders
```
If the orchestrator main moved, replace the ff-merges with a normal merge of the lane.
The API process does not need a reload: it reads embedder ports, not placement.

## 10. Serving proof (report what each returned; `healthy` is not proof)

- **P1–P5** `.venv/bin/python scripts/server/embedder_affinity_check.py` must exit 0. It checks:
  - exe under `kernels/production/cpu`;
  - argv `-c 2048 -np 4 -t 4 --no-mmap`;
  - **every task of every PID** inside its declared cpuset, with the OMP team on 4 disjoint places;
  - no CPU shared between ports;
  - ≥95% of resident pages on the declared node.

  The pre-change run of the same tool is `affinity-before-live-20260926.txt` (rc=1, every check failing).
- **P6** `/props` on each pool port reports `n_ctx` 512 per slot. The same text as `p6-pre.json` is embedded again; require cosine ≥ 0.99999. BERT holds no KV cache, so an input that fit must embed identically.
- **P7** A 400-token input returns an embedding. Before the change it returned an error.
- **P8** `.venv/bin/python scripts/server/orchestrator_stack.py status` shows 6/6 embedders and no attestation drift. `status` also shows the episodic line; there must be no new hash-fallback rows from the reload window (`scripts/maintenance/repair_episodic_embeddings.py` diagnose).
- **P9** G0–G3 `--label post` → `data/embedder_placement/post-20260926.json`. Apply the §4 table.

## 11. Rollback
`git revert 05048a66 845950b4` (orchestrator) and `git revert 7640269b` (research). Then `stack_change_pipeline.py update`
and `orchestrator_stack.py reload embedders`. No symlink, kernel or model changes, and no state migration.
The episodic index is unaffected: same model, same pooling, and inputs that fit embed identically.
**Triggers**: any ROLLBACK cell in §4; P1–P5 non-zero after one retry; P6 cosine below 0.99999.

## 12. needs-operator
- **N-1 Sign the package**: patches 1–3, bring-up §9, gates §4.
- **N-2 The G1 thresholds**: 0.95 PASS / 0.90 ROLLBACK, as proposed. Change them at signing if you want different values.
- **N-3 Timing**: a quiet window with no autokernel CPU arm, episodic writers idle, and bench guard clear (§9 preconditions).
- **N-4 GPU embedder (D1's other half): a separate package, not an optional step here.** Reasons:
  1. Invariant 4 of the handoff says an index belongs to ONE model. A GPU instance must be the same model as the CPU pool, and the model is decided by the Phase-2 eval (Granite-97M-R2 leads). A GPU BGE now means two VRAM migrations.
  2. The MI210 has 1.52 GiB free, below `device_model`'s 2.0 GiB first-execution headroom. Any GPU embedder fails the capacity gate's GPU leg today.
  3. A device move needs `vram_non_kv_gib` re-measured on a real load (`change-topology` phase 3).

  Its gates, pre-registered for that package:
  - KFD VRAM sampled **during** first load and during a saturated batch;
  - capacity GPU leg PASS;
  - :8083/:8086 decode S/Q ≥ 0.97 with the GPU embedder saturated;
  - the same D1 selection rule.

  The second MI210 (~Oct 2026) is the natural home.

## 13. Not in this package (by design)
- **The D1 scheduler rule** ("idle instance anywhere → the instance sharing the requesting model's hardware →
  lexical now, index later") is orchestration-API code: REPL-EMB-1.1.
  - This package supplies the fact it reads: `stack_manifest.EMBEDDING_PLACEMENT[port].numa_node`, derived from the cpuset.
  - The requesting model's node set comes from its `NUMA_CONFIG` cpuset (GPU roles: the host lane, node 3).
- **Belief-kernel wiring, prepared for the owning session**:
  - row for `scripts/vidya/adapters/README.md`: `embedder_placement_gate | epyc-orchestrator data/embedder_placement/*.json | epyc.embedder_placement_gate.v1 | G0–G3 ratios, unit tok/s and texts/s | adapter: TODO`;
  - task `VB-UFH12-PLACEMENT` in `vidya-belief-substrate-program.md`.
- **Index/handoff edits** are prepared, not applied. After signature, tick REPL-EMB-0.1 and set UFH-12's next action to REPL-EMB-0.2.

## 14. The signature (the single operator action)

```bash
/mnt/raid0/llm/epyc-root/artifacts/operator/stack-change-ufh12-phase0-20260926/ratify_ufh12_phase0_20260926.sh --validate-only
/mnt/raid0/llm/epyc-root/artifacts/operator/stack-change-ufh12-phase0-20260926/ratify_ufh12_phase0_20260926.sh --attest RATIFY-UFH12-PHASE0-EMBEDDER-PLACEMENT-20260926
#   optional, to change N-2:  ... --attest <token> --g1-pass 0.95 --g1-rollback 0.90
```
Until `lane/ufh11-phase0-20260926` is merged into epyc-root `main`, run the same script from the lane worktree:
`/mnt/raid0/llm/worktrees/ufh11-phase0-root-20260926/artifacts/operator/stack-change-ufh12-phase0-20260926/ratify_ufh12_phase0_20260926.sh`.
Paths resolve from the script's own location, so the receipt lands in whichever tree it runs from.
The script verifies this file and the three patches against pinned sha256 values. It also verifies that the three
lane commits exist on `origin`. It then writes one receipt, `artifacts/operator/receipts/RATIFY-UFH12-PHASE0-EMBEDDER-PLACEMENT-20260926.json`,
recording the signed thresholds. **It applies nothing and starts nothing.** Phases 7–8 (§9) are run afterwards by the
session that owns the inference, and they begin by checking that the receipt exists.
