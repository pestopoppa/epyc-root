# NUMA placement defect — two production CPU roles serving at ~half speed

*Title corrected 2026-07-30. Previously: "production CPU inference running at ~1/3 speed" — both
halves of that were wrong at higher `n`. The loss is **~2×, not ~3×** (the 3× came from a warm arm
with a ±49% error bar), and it is **two named roles, not "production CPU inference"** — the other
two production CPU roles are already correctly wired. See the amendment note below.*

**Status**: OPEN — diagnosis COMPLETE and measured; **no production wiring change is authorised**.
Five distinct defects found, three of them in live production wiring (D1–D3), two in the E5
measurement harness (D4–D5). The corrected reference numbers below are observation-grade
(`n=1–2` reps) and are the input to a re-measurement, not a promotion.

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

**Created**: 2026-07-30
**Priority**: ACTIVE-HIGH — live throughput damage on **exactly two** production roles
(`frontdoor` 8070, `ingest_long_context` 8085 — **not** `worker_general` and **not**
`architect_general`, both of which are already correctly wired), plus it invalidates 27 of 31 E5
Stage-B cells.
**Spec**: [MEASUREMENT.md](../../MEASUREMENT.md) + [MEASUREMENT_POLICY.md](../../agents/shared/MEASUREMENT_POLICY.md)
(claim grammar, era stamping, region-lock) · protocol **`P-BENCH-PLACEMENT-1`**
(`epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md`, STAGED).
All measurement below ran under a held `region-lock` on `q0..q3` as `role='bench'`.
**Related**: [batched-decode-measurement.md](batched-decode-measurement.md) — the **owner of the
E5 campaign**; its `⛔ SUSPENDED PENDING RE-MEASUREMENT (2026-07-30)` banner is the authoritative
suspension notice and this document is its root-cause backing · [within-role-placement-state-machine.md](within-role-placement-state-machine.md)
(consumes `NUMA_CONFIG`) · [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md)
(its `(N,K)` provisioning is parameterized by E5) · [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md)
(CPU14/CPU17/CPU18 rows) · [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md) P1-2
(the E5 W1–W4 execution row and its published-artifact update requirement)

---

## Scope and provenance of every number below

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

## Protocol, attestation and grade

*Added 2026-07-30.*

| | |
|---|---|
| **Protocol** | `P-BENCH-PLACEMENT-1` — `epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md` |
| **Protocol status** | **STAGED — NOT APPLIED.** Its `MEASUREMENT.md` registry entry (protocol Appendix A) is written and waiting on the operator. |
| **Attestation** | `epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/` — all raw logs **plus the exact script that produced each figure**, committed. `README.md` in that directory carries the figure → file map and the per-figure rep counts. |
| **Era** | `production-consolidated-v8` @ `67a433bf45a8a091d83b4ea0b32ff0735fd51800`, `llama-server --version` = `10107`, host NPS4 |

**Consequence of STAGED: everything measured under this protocol is observation-grade until the
operator ratifies the registry entry.** Per `MEASUREMENT.md` §4 and `MEASUREMENT_POLICY.md` →
*Trust boundary*, the measurement trust boundary is human-amendment-only. Until that amendment
lands, no number in this document — including the completed four-role matrix, including the
`n=10` `frontdoor` figures — may gate a keep / revert / deploy / promote decision. They may inform
design, scoping and prioritisation, which is exactly what they are used for here.

---

## Defect 1 — straddling cpusets launched with no NUMA memory policy

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

### Measured — `llama-bench` tg128, no speculative decoding, `-r 3`

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

## Cross-role placement matrix — all four production CPU roles

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

## Defect 2 — shared mmap means only ONE instance can ever be node-local

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

### ⚠ Corollary — fleet throughput is NONDETERMINISTIC ACROSS REBOOTS

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

## Defect 3 — SMT oversubscription

Half instances are wired `-t 96` onto a cpuset containing **48 physical cores** plus their 48 SMT
siblings. Dropping to `-t 48` (one thread per physical core) is a straight win:

| shape | `np` | `-t 96` per-stream | `-t 48` per-stream | Δ per-stream | `-t 96` aggregate | `-t 48` aggregate | Δ aggregate |
|---|---:|---:|---:|---:|---:|---:|---:|
| HALF (`0-47,96-143`, interleave) | 4 | 11.91 | **13.49** | **+13%** | 94.14 | **102.15** | **+8.5%** |
| QUARTER (`0-23,96-119`, membind) | 4 | 8.18 (`-t 48`) | 8.38 (`-t 24`) | **+2.4%** | 64.03 | 65.51 | +2.3% |

Same sign on quarters, smaller magnitude. The `llama-bench` arm agrees independently: straddle +
interleave at `-t 48` = `15.98` vs `-t 96` = `15.35` (+4%).

---

## Defect 4 — the E5 metric was wall-clock, not decode

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

## Defect 5 — the E5 rungs never reached their nominal concurrency

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

## Impact on the E5 record

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

### What still SURVIVES from the campaign

Unchanged from the suspension banner in [batched-decode-measurement.md](batched-decode-measurement.md):
the **0.0% error rate on every cell** (31/31 Stage-B and the W0 cells) — an error-rate read does
not depend on memory bandwidth; every **harness defect fix** landed during the campaign
(`98cfff44`, `5d6a17f2`, `4a5b6bc7`, `040a2ad7`); and the **protocol / manifest / attestation
machinery** itself — pre-registered cell grids, the affinity-preflight hard gate, the capture
contract and the deterministic-replay ledgers. The instrument is reusable as-is for the
re-measurement, with the D2/D5 fixes folded in.

---

## Corrected reference numbers

> **Observation-grade.** `n = 1–2` reps, short prompt, MTP speculative decoding **ON**, era
> `production-consolidated-v8` @ `67a433bf4`. These are the *input* to a decision-grade re-run —
> they are not themselves promotable claims and must not be used to gate anything.
>
> **Amended 2026-07-30.** The `n = 1–2` caveat applies to the `np`-ladder and shape tables in
> *this* section, which are MTP-on. The four-role matrix above is a separate, higher-`n`
> (`r=5`/`r=10`), spec-dec-**off** measurement — do not conflate the two. Both remain
> observation-grade, now for a different reason: `P-BENCH-PLACEMENT-1` is STAGED, not ratified.

### `frontdoor` — Qwen3.6-35B-A3B-MTP-Q8_0, single instance (per-stream / aggregate tok/s)

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

### `ingest_long_context` — ⚠ WRONG ARTEFACT — Qwen3-Next-80B-A3B **IQ2_M** (no MTP head, so raw decode)

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

#### `ingest_long_context` — production artefact, Q4_K_M (45.08 GiB)

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

## Tasks

### Done

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
      [batched-decode-measurement.md](batched-decode-measurement.md) ✅ 2026-07-30
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

### Open

- [ ] **T1 — Fix the `stack_numa.py` wiring.** ⚠ **NOT AUTHORISED YET.** Requires the inference
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
- [ ] **T2 — Decide `--no-mmap` for quarter fleets.** +27% fleet decode against **+141 GB** host
      RAM for the 35B quad. Needs a lineup-level RAM budget decision, not a local one — a
      role-by-role `no_mmap` flip changes the whole machine's residency envelope.
- [ ] **T3 — Re-run the 27 confounded E5 cells** on declared placement. Per model the grid must
      include **full machine `0-95` + `--interleave=all`**, which *was not in the Stage-B grid at
      all* except as gemma's C1 — and which won today for both `qwen36_q8_0` and
      `qwen3_next_80b`. Either drop caches between placement shapes or launch every instance under
      an explicit policy, so placement is **declared, never inherited**.
- [ ] **T4 — Fix the E5 batch drain (D5)** so the high-`T` rungs actually saturate: more prompts,
      or a closed-loop arrival process holding occupancy at `T`. Without this the `T ≥ 16` rungs
      remain uninterpretable even on corrected placement.
- [ ] **T5 — Arm the locality gate for mmap roles.** `affinity_preflight.py:195` currently sets
      `required = no_mmap and len(expected_nodes) == 1`, so under mmap it observes and reports
      but never fails. It should fail a single-node instance whose `local_fraction` is below
      threshold regardless of mmap.
- [ ] **T6 — Audit the remaining roles for straddling cpusets** and for `numactl_policy: none` on
      any multi-node cpuset. `NUMA_NODE0`/`NUMA_NODE1` are referenced from more than the two roles
      named here; every reference needs the NPS4 re-reading.
- [x] **T7 — Replicate the `23.43 ± 0.07` full-machine figure.** ~~It is currently one 3-rep
      `llama-bench` invocation with no independent repeat (the script arm labelled as its repeat
      is mislabelled and actually repeats the straddle+interleave arm).~~ **CLOSED** — an
      independent `n=10` run (`highn.sh`) measured **`23.36 ± 0.11`** against the original
      `23.43 ± 0.07`, a 0.3% agreement. The full-machine figure is replicated; the mislabelled
      arm remains documented as the reason the replicate was owed ✅ 2026-07-30
- [ ] **T8 — Carry prompt length on every decode claim for `ingest_long_context`**, in the
      registry and in any handoff that quotes a tok/s for it. The 9–12 vs 15–25 split is entirely
      a context-length effect. *(Amended 2026-07-30: the rule stands; the 9–12 / 15–25 bands
      themselves are IQ2_M and must be re-derived on Q4_K_M — T10.)*
- [ ] **T9 — Operator ratification of `P-BENCH-PLACEMENT-1`.** The protocol is written and its
      `MEASUREMENT.md` registry entry is **STAGED in the protocol's Appendix A, not applied**. The
      measurement trust boundary is human-amendment-only, so until the operator applies it,
      **every figure in this document is observation-grade by construction** and cannot gate a
      keep / revert / deploy / promote decision — including T1. Present the registry entry as a
      decision package; do not self-apply.
- [ ] **T10 — Re-run the `ingest_long_context` decode-vs-context curve on the production Q4_K_M
      artefact.** The existing 3-placement × 3-prompt-length curve is IQ2_M (24.27 GiB), which no
      role serves. Only the `tg128` point exists on Q4_K_M (45.08 GiB). Needed before any
      long-context tok/s is quoted for this role, and it feeds T8.
- [ ] **T11 — Audit every other role for the wrong-artefact class of error.** The IQ2_M mistake
      was not a placement bug — a benched file simply was not the file production resolves. The
      same check has already caught a second instance (`modelref_results.txt` benched
      `gemma-4-26B-A4B-it-Q4_K_M-current.gguf` where `worker_general` serves
      `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf`). Resolve each role's GGUF through the live registry
      chain and diff it against whatever any open handoff quotes for that role.

---

## Dependencies

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

## Cross-cutting concerns

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

4. **Any co-resident model changes the arithmetic.** These are single-model measurements taken
   under a held region-lock. The mode-exclusivity contract (full XOR quarters per role) and the
   cross-role contention matrix both bear on what the corrected numbers mean for a *populated*
   lineup. Do not port a single-model tok/s into a lineup-provisioning decision without the
   contention layer.

5. **Era stamping.** Every number here is era `production-consolidated-v8` @ `67a433bf4`
   (binary `10107`). The pre-2026-04-24 NPS2 numbers in `stack_numa.py`'s comments are a
   *different host topology* as well as a different kernel — they are not comparable and the
   2026-04-17 head-to-head in particular must not be cited (wrong topology **and** spec-dec off).

6. **The GPU lane's coupling.** [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md)
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

---

## Reporting instructions

* **On completing any task above**: flip its `- [ ]` → `- [x]` here with an inline `✅ YYYY-MM-DD`,
  and mirror the state into the owning handoff
  [batched-decode-measurement.md](batched-decode-measurement.md) (E5 waypoint) and
  [cpu-inference-optimization-index.md](cpu-inference-optimization-index.md). Prose-only status
  updates are invisible to the handoff dashboard — the checkbox is the metric.
* **On T1 landing**: this is a production stack change. Record the three gates
  (pipeline-green / starts / live==config) plus the post-reload live-affinity verification from
  `affinity_preflight.py` — and verify **live affinity**, not just the topology hash. Append the
  reload to `progress/2026-07/` (or the then-current month) and update the `NUMA_CONFIG`
  provenance comments in `stack_numa.py` so the next reader sees measured evidence, not the
  retracted 2026-04-17 head-to-head.
* **On T3 completing**: the E5 suspension banner in
  [batched-decode-measurement.md](batched-decode-measurement.md) must be **amended, not deleted** —
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

## ⚠ Authorisation status of the production change

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

## Key file locations

### Production code (READ-ONLY for this handoff — no authorised change)

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/stack_numa.py` | **D1 site.** `NUMA_NODE0`/`NUMA_NODE1` at lines 66–67; `NUMA_CONFIG` per-role instances; annotated 2026-07-30, behaviourally unchanged |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` | Launch-command builder; emits `--no-mmap` from the `no_mmap` cache prior |
| `/mnt/raid0/llm/epyc-orchestrator/src/registry/stack_priors.py` | `_role_no_mmap_prior()` — the T2 knob (data, not code) |
| `/mnt/raid0/llm/epyc-orchestrator/scripts/server/affinity_preflight.py` | **T5 site.** `_summarize_numa_maps()` (weight-page placement read); the `required` predicate at line 195 |

### Measurement harness

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/server_numa_np_sweep.py` | E5 harness. `instance_launch_prefix` (lines ~383–394) builds `taskset` + optional `numactl`; D4 rename + `aggregate_decode_tps` landed here |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w1-qwen36-20260729T154725Z/` | Stage-B W1 (11 cells) — first cell first-touched 100% onto N0 |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w2-gemma-20260729T183151Z/` | Stage-B W2 (8 cells) — contains the **4 salvageable** cells |
| `/mnt/raid0/llm/epyc-inference-research/data/batched_decode/e5-w4-80b-20260729T165639Z/` | Stage-B W4 (12 cells) |
| `<run>/affinity/<cell_id>.json` | `instances[].memory_placement.pages_by_node` — the primary D2 evidence |

### Attestation — committed evidence (2026-07-30) ✅ USE THIS

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

### Protocol

| Path | Role |
|---|---|
| `/mnt/raid0/llm/epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md` | **`P-BENCH-PLACEMENT-1`** — the executable contract. **STAGED**: its `MEASUREMENT.md` registry entry lives in its Appendix A and awaits operator application (**T9**). Until applied, conforming runs are observation-grade by construction |

### 2026-07-30 measurement artifacts (scratch — ⚠ SUPERSEDED, use the attestation dir above)

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

### Governing documents

| Path | Role |
|---|---|
| `/workspace/handoffs/active/batched-decode-measurement.md` | **Owner of E5.** Carries the authoritative suspension banner |
| `/workspace/handoffs/active/master-handoff-index.md` | Dispatch; §A row for this defect |
| `/workspace/MEASUREMENT.md` · `/workspace/agents/shared/MEASUREMENT_POLICY.md` | Claim grammar, era handling, append-only annotation rule, region-lock |
| `/workspace/agents/shared/OPERATING_CONSTRAINTS.md` | *Inference and Benchmarks* — reload ownership (why T1 is not self-authorising) |
