# 2026-09-16 — sub-s5-thresholds: pre-registered thresholds for fable5 §5 #1 (MoE half)

Zero-inference analysis subagent. No inference, no benchmarks, no process management, no commit.
Owning box: `handoffs/active/fable5-window2-findings-05-intake-sweep-and-roofline.md` → "§5 measurement #1,
MoE half". This note turns the prep agent's "proposed reading" under that box into a pre-registration.
**Freeze these thresholds before the first launch.** A threshold edited after data exists is post-hoc.

---

## 0. Decision package (per `OPERATING_CONSTRAINTS.md` → Operator Decision Requests)

**Context.** The runner needs pass/fail lines before the sweep runs. The prep agent's draft has three
problems:
- n=3 falls below the policy's ≥5 reps for a ≥5% claim.
- "Does not fall" has no noise band.
- Its FAIL branch treats routing spread as if it were dequant cost.

The operator's only choice here is which threshold set to freeze. Everything else below is already decided.

| Option | What it is | Cost | Main risk |
|---|---|---|---|
| **A (Recommended)** | Two questions with separate triggers. Q-A (Q4_K/Q8_0 format trajectory) is the only kernel trigger. Q-B (MoE/dense scaling ratio) triggers profiling, not a kernel. Band δ = 8%, n=5, with one pre-committed top-up. | ~25 launches (5 files × 5); estimated 1–1.5 h GPU window (unmeasured estimate) | Needs two dense controls in the same window. |
| B | The prep agent's reading as written: PASS if M2 ≥ 0.8 and F does not fall; FAIL if M2 < 0.5. n=3, no band. | ~15 launches, ~40–55 min (estimate) | Violates the reps rule, so it can only ever be an observation. A −1% wobble flips "does not fall". FAIL can fire on routing alone and misdirect kernel work. |
| C | Option A with δ = 12% (the upper CI of the floor) and n=10 at B∈{1,32}. | ~2× A | The INCONCLUSIVE band widens and GPU time doubles. Only worth it if A comes back INCONCLUSIVE. |
| D | Absolute scaling only, no dense controls. GO if K_moe(32) ≥ 8, NO-GO if < 4. | ~9–15 launches | The only comparator is an n=1 llama-bench prior on an 8B model from 2026-08-16. It cannot separate MoE routing from dequant cost. |

**Recommendation: A.**
- It is the only option that can answer the kernel question (is the dequant gap re-opening under batch?)
  without confusing it with the expected, structural MoE penalty.
- Its δ comes from a launch-unit floor that has a stated n.

**Default if no choice is made.** Option A is frozen as written and the runner proceeds. A pending choice
blocks nothing else.

---

## 1. The question the sweep answers

§5 #1, quoted: *"MI210 quantized `-np {1,2,4,8,16,32}` sweep … — does batching close GAP-A for a
*quantized MoE*? This forks the entire 'build a dequant kernel?' question."*

§8, quoted (the pivot this sweep can fire): *"measurement #1 showing quantized MoE *not* amortizing under
batch (→ the gfx90a dequant kernel jumps to high-ROI for throughput too, not just latency)"*.

§4 caveat, quoted: *"MoE batches worse than dense — distinct tokens hit distinct experts, so expert
weight traffic grows with batch."*

The sweep poses two separable questions. The draft merged them.
- **Q-A (kernel ROI).** Does the Q4_K dequant disadvantage *grow* under batch for an MoE? If it does,
  §6.3 (the gfx90a Q4_K kernel) becomes a throughput lever, not only a latency one.
- **Q-B (amortization).** Does MoE decode scale with B comparably to its dense sibling? This checks
  whether §6.1 ("serve batched") transfers to MoE.

**Why Q-B alone cannot trigger a kernel.** Under uniform routing, the number of distinct experts read
per step grows from 8 at B=1 to about:
- 128·(1−(1−8/128)^32) ≈ **112** at B=32 for gemma-26B-A4B (128 experts, top-8), a ≈14× increase;
- 256·(1−(1−8/256)^32) ≈ **163** at B=32 for Qwen3.6-35B-A3B (256 experts, top-8), a ≈20× increase.

This is arithmetic, not a measurement. Dense weight traffic stays flat in B. So M2 < 1 is expected even
with perfect kernels, and a low M2 on its own points to routing, not dequant. Only Q-A holds the model
and the token stream fixed and varies only the quant format, which isolates the dequant path.

## 2. Arms (from the prep spec, unchanged except where noted)

Tool: production `/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-batched-bench`.
- Tree: v9 `0db32c06e`, which contains `llama-batched-bench`.
- Flags: `-ngl 99 -fa on -ctk f16 -ctv f16 -c 16384 -b 2048 -ub 2048 -t 8`, `taskset -c 184-191`,
  `-npp 128 -ntg 128 -npl 1,2,4,8,16,32`.
- **Add `--output-format jsonl`**, which exists in this tree (`common/arg.cpp:3589`).
- Context check: 32·256 = 8192 ≤ 16384.
- Linkage: prove it with `verify_ggml_linkage.sh`, and sample residency DURING each launch.

| Arm | File (all under `/mnt/raid0/llm/models/`) | Role |
|---|---|---|
| G4 | `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` (16.8 GB) | MoE, Q-A numerator and Q-B |
| G8 | `gemma-4-26B-A4B-it-ORIG-Q8_0.gguf` (26.9 GB) | MoE, Q-A denominator |
| Q8m | `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (37.8 GB) | MoE, Q-B |
| Dg4 | `gemma-4-31B-it-Q4_K_M.gguf` (18.7 GB) | dense control for G4 |
| Dq8 | `Qwen3.6-27B-MTP-Q8_0.gguf` (29.0 GB) | dense control for Q8m. **Change from the prep spec:** this is the MTP twin, so both Qwen arms carry the same unused MTP head. `Qwen_Qwen3.6-27B-Q8_0` is the fallback. |

Notes on the arms:
- **G8 has no dense control.** No `gemma-4-31B` Q8_0 is on disk, so G8 enters Q-A only.
- **Load fallback for Q8m.** If v9 refuses to load it, use `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` (36.9 GB) and
  switch Dq8 to the non-MTP 27B, so the pair stays matched. Record the substitution.
- **Order.** Rotate ABA-style across launches, and pair G4/G8 launches adjacently. Each launch runs the
  whole `-npl` list in one process.

## 3. Metrics (all higher-better)

The primary statistic is computed within each launch, then summarised across launches.
- Every B for an arm runs in the same process, so a within-launch ratio cancels launch-level drift.
- The spread across launches of that ratio is its own measured noise.

| Metric | Definition | Direction |
|---|---|---|
| S_TG(B) | `speed_tg` from the jsonl output (= B·128 / t_tg) | ↑ |
| K(B) | S_TG(B) / S_TG(1), within one launch | ↑ |
| **F(B)** — Q-A primary | S_TG,G4(B) / S_TG,G8(B), paired adjacent launches | ↑ (Q4_K advantage) |
| **E = F(32)/F(1)** — Q-A verdict statistic | Erosion of the Q4_K advantage under batch; 1.0 = no erosion | ↑ |
| **M2** — Q-B verdict statistic | K_moe(32) / K_dense(32), family- and quant-matched (G4:Dg4, Q8m:Dq8) | ↑ |

Reporting rules:
- **Every cell reports** its median over launches, n, spread, and min–max.
- **Spread statistic.** Use `p95_dev_pct`, the statistic from `autokernel.loop.serving._spread`, the same
  one the serving floor uses.
- **Unit.** The unit is the **launch**, one fresh `llama-batched-bench` process.
- **B=16 is secondary.** Report E and M2 at B=16 as well, as a within-sweep consistency check.
- **Monotonicity check.** A dense-control S_TG that breaks monotonicity in B marks that cell *suspect*.
  The 2026-08-16 IQ4_XS B=8 cell is the precedent.

## 4. n and the noise floor

**n = 5 launches per arm.** This follows `MEASUREMENT_POLICY.md` ("Reps: ≥5 for ≥5% claims"); every
threshold below sits at an effect of ≥8%. There is one pre-committed top-up: +5 launches at B∈{1,32} only,
and only on INCONCLUSIVE.

**Floor used: δ = 8%.**
- **Source.** The current launch-unit serving floor,
  `autokernel/loop-memory/serving-floor.qwen3.8-27b-q8-gpu-dflash2-np4.json`:
  **7.897% p95_dev, unit `process`, n=24, 95% bootstrap CI [5.520, 11.322]%**, median 160.18 tok/s,
  built on `build-fold-ef81196d5`.
- **Status today.** Per `2026-09-16-sub-gpu-runner.md` §1, this n=24 floor was *already* produced on
  2026-09-15 (INF-66 R23-61a) and was **not** re-run today. The host has not rebooted since 2026-08-13.
  The post-BIOS repeat (R23-61b) waits on the operator's reboot. The older n=10 value (4.581%) lies below
  the new CI and is superseded.
- **Why 8% is used as a borrowed, conservative band.**
  - The floor comes from a different instrument (`llama-server`, spec on, np=4) than this one.
  - np=4 is where the 27B serving spread peaks (3.33% vs 0.44% at np=1, 2026-09-08).
  - Within-launch ratios should be *tighter* than launch-level rates.
  - No A/A band exists for `llama-batched-bench` on MI210: the 2026-08-16 dense ladder is n=1.
- **Rule: δ_eff = max(8%, measured p95_dev of the verdict statistic in this sweep).** If the sweep
  shows a ratio noisier than the borrowed floor, its own spread wins.
- **Validity gate.** A statistic whose measured p95_dev exceeds 2δ (16%) makes that question
  **INVALID**, not INCONCLUSIVE. Fix the instrument; do not top up.

## 5. Pre-registered thresholds (Option A)

### Admissibility, checked before any verdict

Each item is a gate. If any fails, that arm is an observation and has no verdict.
- Residency is `proven` on every launch (VRAM sampled during the run, KFD count ≥1).
- A `verify_ggml_linkage.sh` receipt exists against the running binary.
- `llama-batched-bench` is the v9 binary. Record its sha256 and confirm the tree is clean.
- The sclk clock is recorded, and any non-flat launch is flagged.
- No other KFD process is present during the window.

### Q-A — kernel ROI (the only kernel trigger)

| Verdict | Rule on E = F(32)/F(1) (median over paired launches) | Rationale |
|---|---|---|
| **GO** (batching holds the Q4_K advantage) | E ≥ 1 − δ_eff (≥ 0.92) | Erosion is within noise. Dense prior: F went 1.098 → 1.118 (E = 1.02), Goedel-8B, n=1, llama-bench, 2026-08-16. |
| **NO-GO** (dequant cost grows with batch on MoE) | E < 1 − 2δ_eff (< 0.84) **and** F(32) < 1.0 | Erosion is beyond 2× the floor, and Q4_K ends up *slower* than Q8_0 at batch, so the smaller file stops paying. Both halves are required: erosion from a large B=1 lead that still leaves Q4_K ahead is not a throughput loss. |
| **INCONCLUSIVE** | Everything else: 0.84 ≤ E < 0.92, or E < 0.84 with F(32) ≥ 1.0 | Run the one top-up. If still inside the band, record a **bounded null** ("no erosion beyond 16%") and keep the §6.1 posture. |

### Q-B — MoE amortization (triggers profiling, never a kernel directly)

These thresholds are the prep agent's, kept. They are evaluated per matched pair (G4:Dg4 and Q8m:Dq8), and
both pairs are reported.

| Verdict | Rule on M2 (median) | Rationale |
|---|---|---|
| **PASS** | M2 ≥ 0.80 | MoE keeps ≥80% of dense scaling despite the ≈14–20× growth in expert traffic from §1. §6.1 transfers. |
| **FAIL** | M2 < 0.50 | MoE loses more than half of dense scaling. Given §1, this is *expected-possible* from routing alone. |
| **INCONCLUSIVE** | 0.50 ≤ M2 < 0.80 | Report with spread. No action beyond the record. |

The 0.8/0.5 gap is a 1.6× ratio. That is far outside the compounded ratio noise, even at the CI-upper
floor: √2·11.3% ≈ 16%. So the δ guard is not needed on these lines, **unless** M2 lies within
δ_eff of 0.80 or 0.50. In that case the verdict is INCONCLUSIVE.

## 6. What each outcome triggers

| Q-A | Q-B | Trigger |
|---|---|---|
| GO | PASS | Tick the MoE-half box. §6.1 stands for quantized MoE, and §6.3 stays latency-only and deprioritized. **The §8 pivot does not fire.** Open the serving follow-up (Section 7). |
| GO | FAIL | Batching still beats a dequant kernel, but MoE amortizes poorly for **routing** reasons. Run §5 #2-style profiling of the batched `MUL_MAT_ID` path (expert-gather and occupancy) *before* any kernel work. Candidate levers are expert-grouped dispatch and occupancy, not dequant. |
| NO-GO | any | **The §8 pivot fires.** §6.3 (gfx90a Q4_K dequant/MMQ kernel via GEAK) rises to a throughput lever for MoE. First run §5 #2 (rocprof, VALU/issue-bound vs HBM-saturated) at B=32 on G4. The kernel starts only if that shows it is not HBM-saturated. This routes to `agentic-rocm-kernel-authoring.md` as a research-priority change, not a deploy. |
| INCONCLUSIVE after top-up | any | Record a bounded null. Keep the status-quo ranking (§6.1 > §6.3). Do not re-run without a new hypothesis. |
| INVALID | — | Fix the instrument (spread > 16%, residency, or linkage). This is not an operator item. |

**Stopping rule.** The table in Section 5 is final after n=5 plus at most one top-up.

**Scope of any verdict.** None of these verdicts changes a serving recipe or `np` value.

## 7. What the proxy cannot claim

`llama-batched-bench` is a **proxy**, not a serving rate.

It cannot speculate. Both MoE targets have a draft path: Qwen3.6-35B-A3B-MTP self-drafts, and
`gemma-4-26B-A4B-it-assistant-Q8_0` exists. So every S_TG in this sweep is category **BASELINE**, never
OPTIMUM, and **never a headline**.

Measured serving on champion `ef81196d5`, Qwen3.6-35B-A3B-MTP-Q8_0, MTP on, unit = launch, residency proven,
2026-09-08:
- **np=1**: **112.68 tok/s** (n=6, p95_dev 2.70%, range 110.21–115.71).
- **np=16**: **310.96 tok/s** (n=3, p95_dev 2.53%, range 309.41–318.83), still climbing (+16% from np=12).
- Serving K(16) = 310.96/112.68 = **2.76**.

Caveats on those serving figures:
- **They are not in the champion doc.** They are not in `docs/design/champion-max-performance-20260908.md`,
  which covers only the dense Qwen3.8-27B (79.25 / 179.12). They live in scratch at
  `/mnt/raid0/llm/tmp/maxperf-35b-20260908/`. Research commit `48a6f6f2` promoted only the 27B sweep.
  This is a provenance gap; promoting the 35B raw files to git is a clerical follow-up.
- **They are observations.** They were measured on a champion (non-production) kernel.

How the proxy limits the claim:
1. **Batched-bench K will be much larger than serving K** and must never be compared with it.
   - Spec-dec gains shrink as B grows, which compresses serving K. Batched-bench has no spec, so its B=1
     is slower and its K higher.
   - The verdicts are therefore claims about the **target-model batched decode kernel path** only.
2. **A GO does not say which `np` to serve.** That needs P-BENCH-3 on `llama-server` with MTP on (the
   still-climbing curve above np=16). This is a separate serving question.
3. **Tokens are synthetic.** `get_token_rand()` is `std::rand() % n_vocab`, unseeded, so every launch
   sees the same sequence (`tools/batched-bench/batched-bench.cpp:71`).
   - Random tokens probably route less skewed than real text, which inflates distinct-expert traffic.
   - This biases **Q-B toward FAIL**. That is one more reason Q-B does not trigger a kernel.
   - Q-A is unaffected: G4 and G8 share a vocabulary and so get identical token IDs.
4. **Short, lockstep sequences.** npp=128/ntg=128, and all sequences decode in lockstep. KV cost is
   small and there is no scheduler or ragged batching, so results say nothing about long-context or
   mixed-length serving.
5. **B=1 runs first in each process.** The only warmup is a prompt-only decode (line 110), so any residual
   first-decode cost lands on B=1 and inflates K. It does so equally for the MoE and dense arms, which is
   another reason M2 and E are ratios.
6. **Claim grade.** v9 is a production-named kernel, so a run carrying every P-GPU-1 field could be
   graded. The decision it feeds is a **research-priority ranking** (§6.1 vs §6.3), not
   keep/revert/deploy. Record the full P-GPU-1 fields anyway. **P-BENCH-3 names `{1,2,4,8,16}`; B=32 is an
   extension**, so state that in the receipt.

## 8. Evidence used (nothing new measured)

- **Dense prior.** `artifacts/gpu-aux-baselines/a10_quant_ladder_occupancy_knee_20260816.md`. Goedel-8B,
  n=1 per cell, llama-bench, no A/A band, OBSERVATION.
  - Q4_K_M: K(32) = 1310.8/107.7 = **12.17**.
  - Q8_0: K(32) = 1172.2/98.1 = **11.95**.
  - f16: K(32) = **14.86**.
  - F: 1.098 → 1.118.
  - This is a prior only, never the comparator: a different tool, a different model size, and 31 days
    older than today.
- **Dense 27B serving.** `docs/design/champion-max-performance-20260908.md`: 79.25 at np=1, 179.12 at
  np=8, serving K(8) = 2.26. Dispersion rises with np (0.44% → 3.33%).
- **MoE 35B serving.** Scratch `/mnt/raid0/llm/tmp/maxperf-35b-20260908/{sweep,sweep-hi,sweep-np1-n6}.json`.
- **Floor.** `2026-09-16-sub-gpu-runner.md` §1.
- **Artifact availability.** File sizes come from a directory listing of `/mnt/raid0/llm/models/`.
