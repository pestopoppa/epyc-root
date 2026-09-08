# CPU Decode Roofline Program — history through 2026-09-08

**Split out of [`handoffs/active/cpu-decode-roofline-program.md`](../active/cpu-decode-roofline-program.md)
at campaign close-out, 2026-09-08.** A day-1 correction trail with no forward-looking content.
**Historical: verify against actual code before trusting any description here.**

## Audit log — 2026-09-02

Audit of the 2026-09-02 draft against primary records (`progress/2026-08/2026-08-28.md`, the INF-67/INF-68
records, the artifact's tensor table, the fusion tree's `ggml-cpu.c`, and the bandwidth tool's source).
Corrections applied in this file:

1. **425 GB/s retired** — `bench_stream3.cpp` divides 4 GiB by the copy time of a 2 GiB array (read+write
   already counted, standard STREAM); its "traffic" column doubles again. Measured copy is 212 GB/s at an
   unrecorded thread count without the OMP stack; read-only bandwidth under the recipe was never measured
   → **C0**. The DGX-Spark comparison is withdrawn until C0 exists.
2. **"5.6–17 GB/s expert path" retired** — the same record retracts it (`2026-08-28.md:170,190`): the
   per-op profiler was contaminated by cross-node waits; in-function timing gives 68–88 µs/call,
   ~100–130 GB/s. Axis B rebuilt on the fixed-cost hypothesis with a discriminating test (B2).
3. **Bytes per token corrected** from "2.8–3.4 GB" (another model's 2026-05-28 figure) to ≈ 4.16 GB from
   the artifact's tensor table; the F32 router, the Q6_K lm_head and the Q5_1 down-experts surfaced (B4).
4. **"28 ms gemv" retired as a measured number** — its constants are in no committed profiler record
   (INF-68 audit); the in-function medians are the sourced equivalents. "27% of roofline" fell with it.
5. **Node count corrected** to the measured 7,906 / 6,887 (INF-67's ~5,850 / ~6,800 are unsourced).
6. **B3 (prefetch at router time) rewritten** — the router reads the post-attention state
   (`qwen4exp.cpp:314-360`); no in-layer window exists, and `madvise(WILLNEED)` is inapplicable under
   `--no-mmap`. **B4 (expert locality) demoted to B6** — experts are contiguous slabs.
7. **Axis D added** — the dispatch floor was the largest term in every accounting and had no tasks: the
   profiler that produced "5–8 µs/node" cannot see barrier wait, and the tree's barrier, internal
   matmul barriers, absent elision, THP and runtime choice were never examined.
8. **Axis E added** (operator direction): MTP restoration, sequenced last. Rewritten the same day once
   unsloth's published heads were found (2026-09-01 upload): no FP8 download, no converter run; the work
   is porting the `qwen4exp` MTP graph and borrowing from `unslothai/llama.cpp#144`.
9. Recipe made explicit (the `canonical_recipe.py` prefix + OMP stack; INF-68 used it, the 08-28 bandwidth
   run did not), C5 gained the OMP on/off arm and the box-state capture, C6 wires the belief kernel.
10. INF-68 path fixed (`../completed/`), INF-67 given a pointer to this task list, wiki
    `benchmark-methodology.md` correction 1 rewritten as the fifth correction.
11. **Measured the same day (operator granted the CPU):** C0 read bandwidth 67–77 GB/s as-is vs 153/166 GB/s
    after per-node eviction; C5 anchor 10.14 / 10.09 t/s at t48 (as-is 7.65), t1 5.04; barrier primitive
    1.9 µs at 48T; tiny-node cost 3.7 µs at 48T; 100% THP when memory is free. The **placement mechanism**
    (page-cache-full nodes defeat `--interleave=all`) explains the 08-28→08-31 −32% and became task C7.
12. SMBIOS read: 12 × Samsung 96 GB DDR5-5600 RDIMMs configured at 4800 MT/s (one per channel); the BIOS
    change to 5600 is queued by the operator for the next reboot — re-run C0/C5 after it.
13. Operator direction folded in: unsloth heads downloaded (E1 ✅); no DFlash2 drafter exists for this
    model; EXL3 weights exist with a fused VNNI CPU decode → INF-71.
14. Follow-up arms: UD under clean placement 9.18 t/s (13.46 retired for good); C0-c four node-local
    streams total 171 GB/s with each node dropping from 66 to ~40 → a global uncore cap → task C8 (BIOS
    checklist for the operator's reboot: 5600 MT/s, UCLK 1:1, APBDIS/DF P0, DF C-states, power-down).

### Research-intake follow-up 2026-09-07 — CLOSED on arrival

- [x] **Reconcile INF-70 main vs `lane/inf70-audit-20260902`** ✅ 2026-09-07 — closed by this merge: main now
  carries the audited copy, so the superseded ≈ 100–130 GB/s expert-path figures are gone and 61.8 GB/s at
  proven placement is the only number here. Filed by the 2026-09-07 research-intake wave (`intake-1318#record`).
