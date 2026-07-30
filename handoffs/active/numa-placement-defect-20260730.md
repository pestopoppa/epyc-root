# NUMA placement defect — production CPU inference running at ~1/3 speed

**Status**: OPEN — diagnosis COMPLETE and measured; **no production wiring change is authorised**.
Five distinct defects found, three of them in live production wiring (D1–D3), two in the E5
measurement harness (D4–D5). The corrected reference numbers below are observation-grade
(`n=1–2` reps) and are the input to a re-measurement, not a promotion.
**Created**: 2026-07-30
**Priority**: ACTIVE-HIGH — live throughput damage on two production roles (`frontdoor` 8070,
`ingest_long_context` 8085), plus it invalidates 27 of 31 E5 Stage-B cells.
**Spec**: [MEASUREMENT.md](../../MEASUREMENT.md) + [MEASUREMENT_POLICY.md](../../agents/shared/MEASUREMENT_POLICY.md)
(claim grammar, era stamping, region-lock). All measurement below ran under a held
`region-lock` on `q0..q3` as `role='bench'`.
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

> **`numactl --interleave` binds at FIRST TOUCH only.** Against a warm page cache it is a silent
> no-op — visible above as the warm straddle+interleave row landing on the *unpolicied* number
> rather than the cold-interleave number. This is exactly why the defect survived casual
> re-testing: a warm re-test appears to "confirm" the bad figure.

**Instrument validated.** The single-NPS4-node arm measured `8.80` against the
registry-documented `8.90` — a 1% match, so the meter is sound and the defect is in the wiring
under test. Ruled out as causes: a v8 kernel regression (v7 and v8 both measure `9.76`,
identical); iqk (never engages for Q8_0 — gated behind an unset `GGML_IQK_Q8_0`); MTP head
overhead; mmap page-faulting.

**Honesty caveat on the headline number.** `23.43 ± 0.07` is one `llama-bench` invocation of 3
reps with no independent repeat. Arm `F` in `/mnt/raid0/llm/tmp/numa_matrix2.sh` is **mislabelled**
— its comment says "REPEAT of C-winner shape at 4 nodes" but its argv is
`taskset -c 0-47,96-143 numactl --interleave=0,1 … -t 96`, i.e. a repeat of arm **C**, not D. It
returned `15.28 ± 0.33`, which does independently reproduce C's `15.35 ± 0.08`. So the *straddle+
interleave* figure is replicated; the *full-machine* figure is not yet.

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
derivation: `/mnt/raid0/llm/tmp/e5_rederived.md`.

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

Full cell-by-cell verdict table: `/mnt/raid0/llm/tmp/e5_rederived.md` §6b.

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

### `ingest_long_context` — Qwen3-Next-80B-A3B IQ2_M (no MTP head, so raw decode)

Decode tok/s by prompt length:

| arm | 565 tok | 8,749 tok | 28,232 tok |
|---|---:|---:|---:|
| production as-wired (straddle, no policy, warm) | 15.36 | 13.15 | 9.15 |
| same cpuset + `--interleave=0,1` (cold) | 21.12 | 17.28 | 11.29 |
| **full machine `0-95` + `--interleave=all` (cold)** | **25.36** | **20.35** | **12.21** |

Prefill moves the same direction but far less (194 → 274 tok/s at 565; 101 → 107 at 28k) — as
expected, prefill is compute-bound and decode is bandwidth-bound.

> **This resolves a standing confusion.** An earlier claim that this role "decodes at ~11 tok/s"
> came from **long-context eval rows** (26.5k / 17.4k-token prompts). At those lengths 9–12 tok/s
> is correct. At short context the same role does **15–25 tok/s**. The two figures were never in
> conflict; the context length was simply never carried alongside the number. Any future decode
> claim for this role MUST state its prompt length.

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

### Open

- [ ] **T1 — Fix the `stack_numa.py` wiring.** ⚠ **NOT AUTHORISED YET.** Requires the inference
      owner, the three stack gates (pipeline-green ≠ starts ≠ live==config), and a reload executed
      *by the session that owns the inference, at a moment it chooses*. Scope: `frontdoor` idx0
      and `ingest_long_context` idx0 off the straddling `NUMA_NODE0`; rename or retire the
      NPS2-era constants; decide `-t 48` vs `-t 96` per shape (D3).
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
- [ ] **T7 — Replicate the `23.43 ± 0.07` full-machine figure.** It is currently one 3-rep
      `llama-bench` invocation with no independent repeat (the script arm labelled as its repeat
      is mislabelled and actually repeats the straddle+interleave arm). Cheap; do it before any
      figure derived from it is promoted past observation-grade.
- [ ] **T8 — Carry prompt length on every decode claim for `ingest_long_context`**, in the
      registry and in any handoff that quotes a tok/s for it. The 9–12 vs 15–25 split is entirely
      a context-length effect.

---

## Dependencies

```
D1/D2/D3 diagnosis (DONE)
      │
      ├──> T1 fix stack_numa.py ──┐   [BLOCKED: operator + inference owner + 3 stack gates]
      │                            │
      ├──> T2 --no-mmap decision ──┤   [BLOCKED: needs T1's shape decision + a RAM-budget ruling]
      │                            │
      ├──> T5 arm locality gate ───┤   [independent; do FIRST — it is the guard for T3]
      │                            │
      └──> T4 batch-drain fix ─────┤   [independent; harness-only, zero inference]
                                   │
                                   v
                              T3 re-run 27 E5 cells
                                   │
                                   ├──> batched-decode-measurement.md E5 waypoint closes
                                   ├──> within-role-placement-state-machine.md per-instance -np sizing
                                   └──> heterogeneous-slot-fabric-residency.md (N,K) provisioning
```

* **T5 and T4 are zero-inference and unblocked** — land them before T3 so the re-run is guarded
  and interpretable. T5 in particular is what would have caught D2 the first time.
* **T3 must not start before T1 is decided.** If production is re-wired mid-campaign the re-run
  measures two different machines. If T1 is deferred, T3 still proceeds — but on *bench* ports
  with declared policy, and its recommendations then feed T1 rather than the reverse.
* **T7 is a prerequisite for promoting any full-machine figure past observation-grade**, but not
  for starting T3.
* **T6 gates nothing but may widen T1's scope** — run it early so T1 is scoped once.

---

## Cross-cutting concerns

1. **This is live production damage, not only a measurement defect.** `frontdoor` (8070) and
   `ingest_long_context` (8085) are serving today at roughly one third of the throughput the same
   hardware delivers under the canonical recipe. Every downstream number produced through those
   ports since the 2026-04-24 NPS4 reboot — AutoPilot trial wall-times, eval-tower throughput,
   any tok/s in a role-level registry row — carries the penalty. **The AutoPilot
   `median_request_tps` anchor of 35.7 is NOT affected**: that traffic lands on a placement that
   reproduces today's corrected full-machine number, which is precisely why it disagreed with E5.
   The disagreement was the signal.

2. **Renaming or retiring `NUMA_NODE0`/`NUMA_NODE1` is a breaking change to a widely-read
   constant.** It is consumed by `NUMA_CONFIG`, by the placement state machine, and by the E5
   harness's own shape table. Rename and re-wire in one change or not at all — a half-migration
   leaves two meanings of "node" live simultaneously.

3. **`--no-mmap` is already a per-role registry *data* knob, not new code.**
   `src/registry/stack_priors.py::_role_no_mmap_prior` resolves `no_mmap` from a role's config
   (directly or nested under `cache`/`serving`) and `orchestrator_stack.py` emits `--no-mmap`
   accordingly; the current live value is `false` across the board. So T2 is a policy decision
   with a RAM bill, not an implementation task. `stack_numa.py:193` already anticipates it —
   `worker_general`'s interleave is deliberately scoped to idx0 "so `--no-mmap` quarters can
   first-touch local private pages".

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
   confounded by *placement*, and the largest single effect is a 3× wiring defect.

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
  protocol id, an attestation reference and an era stamp. Nothing here currently carries one.
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

### 2026-07-30 measurement artifacts (scratch — promote before relying on them)

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
