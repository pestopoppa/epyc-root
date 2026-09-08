# CPU Decode Roofline Program — completed scope through 2026-09-08

**Split out of [`handoffs/active/cpu-decode-roofline-program.md`](../active/cpu-decode-roofline-program.md)
at campaign close-out, 2026-09-08.** These sections are LANDED or VALIDATED and remain as evidence;
they are not live work. Nothing here contains an open checkbox, a blocking gate (G2-CONC, PROD-2,
PROD-3, CHAMP-1, MEAS-1/OP-40/OP-41), a standing rule, or a currently-cited key file — every span was
checked before the move.

**⚠ Numbers in the "Deployable serving speed" section are SUPERSEDED.** The campaign's final measured
figures are in the active file's CURRENT STATE header: champion `ef81196d5` +
`GGML_NOHUGEPAGE_PROCESS=1` at launch, plain 27.893 t/s (2.1857×), served-MTP 43.281 t/s (1.8255×),
unit = LAUNCH. Retained here because superseding a number is not the same as deleting the record of
how it was obtained.

## Ordering

1. ~~**C0 → C5**~~ ✅ done 2026-09-02 (ledger). Every absolute number below reports against **99.1 ms /
   153 GB/s** with the eviction step in the recipe. **C7 (make the placement fix permanent) is the first
   open item**, because without it every later measurement silently regresses to the as-is regime.
2. **B1 + D0** (one session, no new kernels): the per-path GB/s split and the per-node floor, on the C5
   build. These two numbers rank every lever below by ms/token at stake.
3. **Levers by measured ROI**: Axis D (D1–D7) and Axis B (B2–B4) are independent of each other and of
   Axis A; run them in parallel sessions, each against the C5 anchor in the C5 build.
4. **Axis A** continues in its own session against the same anchor (A-GATE).
5. **Axis E** after A–D report their first measured results (E1, the head download, is already done).

If this ordering is overruled, say so in this file with the reason; it is a recommendation with a reason,
not a gate.

## Axis A — finish the fused decoder's viability test (INF-67)

The go/no-go was answered 2026-09-01: the batched `mul_mat` is callable on staged tensors, so the per-row
`vec_dot` in `FusedMM::dot` is a fixable implementation error, not a structural one. INF-67 remains the
design record; this is the live task list.

- [x] **A1 — batched `mul_mat` substitution in `lora_mm`/`FusedMM`.** ✅ implemented 2026-09-02
      (`380278b40`, branch `inf70/fused`, subagent `fused`) — every per-row `vec_dot` loop replaced by
      `ggml_compute_forward_mul_mat` (via `ggml_cpu_extra_compute_forward` first). **Measured at 1T, same
      build (Release + OpenMP, commit `740d0cfea`), same process, same window, uniform artifact,
      clean placement: fused gemv column = 232 ms after the census fix (810 ms before it — 598 ms was the
      un-migrated repacked-down-expert path), against a whole graph token of 195 ms.** The success criterion
      (→ ~300 ms) is met for the column; the census says the residual is structural (4.1× the calls, the
      double MoE), not mechanical — per-call time is ordinary (36.6 µs per 640×2560 expert slice). The pre-A1 per-row path could not
      be timed in the same build: it aborts with `double free or corruption` on its first token — and the
      abort reproduces on the pristine `c035bbf3d` tree in Release, so the heap corruption pre-dates this
      work and was masked by the debug build the INF-67 campaign measured on.
- [x] **A2 — scratch arena.** ✅ implemented 2026-09-02 (`5d2d27510` + `672c5e9e5`) — one arena per
      nesting slot plus one staging buffer for the recurrent state. **Churn measured (replaces the retired
      "~2.5 GB" estimate): 73 `ggml_init`/`ggml_free` pairs per token asking for 3,520 MB/token before A2,
      223.7 MB actually needed, plus 112.6 MB/token of state-staging allocations; after A2 the four arenas
      hold 12.2 MB total.** With both A1 and A2 in, the fused "other" column is still **150.6 ms at 1T —
      77% of the graph's entire 197 ms token** — so the non-gemv machinery of the fused design costs more
      than the whole graph does, at a thread count where the graph pays no barrier at all.
- [x] **A3 — strip the debug I/O.** ✅ 2026-09-02 (`e02ddbdff`) — ~70 `getenv` and ~114 `fprintf`/`fopen`
      sites behind the compile-time `QWEN4EXP_FUSED_DEBUG` (OFF by default); the worst were ~2.5 M
      `getenv` calls per token inside the expert row loops, two of them inside the `FUSED_PROF` gemv window,
      and five `GGML_FUSED_DUMP_GLAYERS` getenv sites in `process_ubatch` that ran on the GRAPH arm of
      every A/B too.
- [x] **A4 — the safety contract.** ✅ 2026-09-02 (`bf56cf94e` + `07d980e5e`) — hook is OPT-IN
      (`GGML_FUSED_DECODE=1`); `supports_fused_decode()` checks CPU-device residency, repack layout and the
      hparams it assumes; a preflight validates the memory context, cache views/types and the logits
      carrier before any work; PLE and GDN recurrent state staged and committed in one pass at
      end-of-token. The logits carrier remains the previous graph's tensor under a checked contract; the
      owned-buffer form (`decode()` taking the fused result's own buffer) is **A4b**, moot unless the gate
      below is overruled. Three fused-path correctness bugs found and fixed on the way: the GDN state
      copy-back read at a byte offset where the state starts at a float offset (`a188b2f70`), repacked
      IQ4_NL hc loras read as plain rows, and F16 `ple_conv1d` read as F32 — 81 KB past the tensor
      (`b1439ce59`). The INF-67 residual (0.684 / 1.7e-2) was measured with all three present.

**⚠ The measurement trap on A1.** With the churn still present, a *perfect* gemv fix reads fused ≈ 300
(gemv) + 215 (other) = **~515 ms at 1T vs the graph's 350** — still 1.5× slower, because the graph's own
1T non-gemv cost is only ~50 ms. A1 and A2 are individually fatal; the design needs both. With both, the
ambition is the weight stream at the machine's rate (~32 ms for 4.16 GB at 130 GB/s, less as Axis B/D4
raise the rate) plus a fused-path overhead that has to be measured — **≈ 25–30 t/s if that overhead is
≤ 10 ms**. That is the ambition to test, not a predicted result. The fused/graph ratio (3.86× at 1T) is
the honest interim metric; it is same-build and roughly stable across thread counts.

- [x] **A-GATE**: fused ≤ graph at 1T on BOTH the gemv column and the other column, same build. ✅ run
      2026-09-02, three iterations in one session, each driven by the call census naming a defect:
      **4.70× → 1.51× → 1.10×.** Final: **fused 214.3 ms/token vs graph 195.1 ms at `-t 1`, steady state
      (steps 2–6; step 1 is the arena first-touch outlier at 316 ms)**, same process, same model load, same
      window, placement proven; commit `06f916224` on branch `inf70/fused` (self-reported build number 1274
      is a shallow-clone artifact; hashes are the ids). Column split: gemv 170.5 ms, other 41.7 ms — both
      inside the graph's own 1T band, but the side-by-side token is 10% slower, so **the gate is not met.**
      What the census removed: (1) 598 ms of an un-migrated hand-rolled path for the 42 CPU_REPACK
      `ffn_down_exps` (2.15 M scalar dots/token) — routed through the dispatcher; (2) a transcription
      error that ran the routed MoE **twice per layer** (attention side and ffn side; the graph runs it
      once at `qwen4exp.cpp:356`) — removed; after it the census matches the ledger exactly (1,440 expert
      calls = 48 × 10 × 3, 1,236 MB vs the ledger's 1,296 MB). **What remains is structural: 2,213
      `mul_mat` calls vs the graph's 941** (one call per expert per lora where the graph issues one
      `mul_mat_id` per layer and fuses the hc streams), at an ordinary 76.9 µs mean — closing it means
      rebuilding `mul_mat_id` inside the fused path. Logit gate still fails by four orders of magnitude
      (max_abs 1.2–2.7, NMSE 4e-2–2.4e-1 per step; greedy agreed 6/6 on every run). **Operator decision
      package** (report §6b): (a) read the columns as within noise of passing → the 48-thread question
      is a project, not a measurement — the path is single-threaded by construction (`ith=0, nth=1` on a
      private pool; arenas, staging and tensor headers assume one caller), so INF-67 Phase 4 threading is
      one to two focused sessions before any 48T number exists; (b) the literal reading: given its batched
      matmuls, its arena, clean instrumentation, a safety contract and two real defects removed, at one
      thread where it has no dispatch disadvantage the design still costs 10% more than the graph while
      failing numerics — close, with this report as the refutation. **Recommendation from the audit: (b)**;
      the diagnosis is complete enough to choose knowingly, which is what the gate was for. The branch
      keeps the safety contract (A4), the debug strip (A3), the batched kernels (A1), the arenas (A2), the
      three bug fixes and the census instrument as the record; A4b (owned logits buffer, call sites in the
      report) precedes any serving exposure if (a) is chosen. Every arm held the bench lock 80–84 s.

## Disk: the artifact rule costs 92 GB per experiment on this model (measured 2026-09-04)

Surfaced by an operator question — *"I'm surprised we only have 151 GB free, I cleaned up last week and freed
~400 GB"*. The answer is that **this campaign consumed it, predictably and by design.** One model directory holds
**547 GB**:

| variant | size | origin |
|---|---|---|
| `IQ4_XS-uniform` | 92 GB | era anchor (pre-existing, OP-32 baseline) |
| `IQ4_XS-uniform-gateup` | 92 GB | **B3, this campaign** |
| `IQ4_XS-uniform-gateup-r16` | 92 GB | **B3-4, this campaign** (current Axis B/D baseline) |
| `IQ4_XS-uniform-b4` | 91 GB | **B4, this campaign** |
| ~~`IQ4_XS-uniform-b4r`~~ | ~~92 GB~~ | **B4** — deleted 2026-09-04 (regenerable) |
| `UD-IQ4_XS` | 88 GB | served file |

Plus 88 GB of worktrees (one build tree per subagent) and 163 GB of cache. **~367 GB of the ~590 GB consumed since
the 2026-08-31 reclaim (743 GB free then) is this campaign's own artifacts.**

**This is the direct cost of the OP-32 artifact rule**: a delta must be measured with the artifact held identical on
both arms, so every quant experiment on a 125B model mints a new 92 GB file rather than mutating one. That is the
right rule — it is what makes the deltas trustworthy — but on this model it means **~92 GB per experiment, and at
~150–240 GB of working headroom we can hold roughly one experiment in flight at a time.**
**Consequence to plan around, not a defect**: B7 will cost another ~92 GB for its output; any future quant
experiment will too. Budget a deletion per experiment, and prefer artifacts whose recipe + byte count are recorded
(hence regenerable, hence reversibly deletable) when choosing what to drop.

## RECLAIM-1 — the post-convergence artifact reclaim (filed 2026-09-04 on operator prompt)

Operator: *"aren't we now converging on the final kernel/model quant? Once we do, we could delete all the other
unnecessary ones."* Correct, and here is the concrete plan so it happens deliberately rather than under pressure.

**Are we converged?** Nearly, on two of three axes:
- **Kernel — effectively settled**: `c51e4dabf` = D8 + D7a + D1 + B3-k + the iqk IQ4_XS repack fix + `ROWEXACT_N`
  + `FA_SPLIT_KV`. Open only on BE-3 (a non-propagating carrier) and the claim-grade ABA.
- **Serving config — SETTLED, ABA-confirmed 2026-09-04**: MTP head `shared-Q8_0`, `--spec-type draft-mtp
  --spec-draft-n-max 4 --spec-draft-p-min 0.5`, `GGML_ROWEXACT_N` unset, **KV f16 (do NOT quantise)**, `-t 48`,
  `-fa on` + `GGML_FA_SPLIT_KV=0`, canonical env + `taskset -c 0-95 numactl --interleave=all`
  → **23.16 t/s, 1.876× plain** (23.62 superseded; see the ABA block).
- **★ STANDING MEASUREMENT RULE earned by this batch — THE HOST DRIFTS ~3% OVER HOURS.** Same config measured
  23.16 at 12:52 and 22.58–22.73 at 15:05–15:55, while repeating to **1.1% WITHIN a window**. Therefore **any
  INF-70 comparison below ~5% must be SAME-WINDOW and ALTERNATING, or it is not evidence.** Both results
  overturned on 2026-09-04 (the 23.62 headline and the depth-beyond-4 gain) were cross-window artefacts of
  exactly this size, and be1-ship's 18 arms ran sequentially over ~4 hours. A sequential arm matrix measures
  drift as if it were the treatment.
- **Depth beyond n-max 4 — CLOSED, does not pay.** A same-window alternating n4-vs-n5 test returned **ratio
  0.9987** (12/20 and 10/20 prompts — coin flips). The earlier cross-window sweep showing n5/n6/n8 ~3% ahead was
  the drift artefact above. p_min 0.5 vs 0.6 is flat. The plateau is real and **no better operating point exists**.
- **KV cache — SHIP f16, do NOT quantise (B9 CLOSED).** Size analysis was right and irrelevant: 12 of 48 layers
  carry KV, 24.0 KiB/token = 2.42% of budget, 45–90 MiB saved. Sign was **wrong for MTP**: plain gains +0.7% to
  +2.1% as predicted, but **MTP LOSES 2.5–3.5% because α falls 0.8274 → 0.8166.** `attn_rot_k/v` DID flip to 1
  (head dim 256) on both the main and DSA indexer caches, and that never-exercised path is **clean** — 96
  quantised-KV requests, zero incoherence, no assert. `LLAMA_ATTN_ROT_DISABLE=1` was not needed as a rescue but
  was decisive as **attribution**: it recovers 1.9% and lifts α to **0.8329, ABOVE f16's 0.8274** — so the
  **Hadamard rotation, not quantisation error, is what costs acceptance**. q8_0 still loses 1.4% with rotation
  off. A KV-quant win on a plain decoder does not transfer to a speculative one.
- **Bandwidth — MTP takes CPU decode OFF the bandwidth wall.** Plain 51.3 GB/s (33.5% of 153). MTP's
  plain-equivalent 96.3 GB/s (62.9%) is not what it moves: the verify batch carries **3.79 tokens per forward**,
  so actual traffic is **1.096 GB/token = 25.4 GB/s (16.6%)**. The roofline argument for CPU decode changes shape
  under speculation — amortising the weight read across accepted tokens is the lever, not raising GB/s.
**⚠ STALE AS WRITTEN (flagged 2026-09-07): the "B7 in flight" sequencing below is spent.** The PLE-precision
B7 **reported NO on 2026-09-04** and RECLAIM-1 **executed the same day** (123 GB → 421 GB free). Read the
paragraphs that follow as the record of how that decision was reached, not as an outstanding trigger. The
live artifact question is now the OP-37 / PROD-3 reconciliation flagged above (`-gateup-r16` vs B4's
`IQ4_XS-uniform-r16` + F16 router), and **"B7" here means the CLOSED PLE item, never INF-71.**

- **Artifact — NOT yet**: `-gateup-r16` is the best measured (12.73 vs 12.61 plain), but **B7 is in flight** and may
  produce a better one (PLE at Q8_0). **The artifact question closes when B7 reports**, and only then.

**✅ RECLAIM-1 / OP-37 EXECUTED 2026-09-04 (operator: "proceed") — 123 GB → 421 GB free.** Deleted, all
reversibly: `IQ4_XS-uniform-gateup` (92 GB), `IQ4_XS-uniform-b4` (91 GB), `IQ4_XS-uniform-pleQ8` (116 GB —
B7's measured loser). Protected and verified present afterwards: `IQ4_XS-uniform` (era anchor),
`-gateup-r16` (current baseline), `UD-IQ4_XS` (served file), `MTP` (head, in the serving config).
**Precondition satisfied first**: `gguf_swap_ple.py`, the pleQ8 artifact's ONLY regeneration recipe, lived
solely in `/mnt/raid0/llm/tmp/` — a scratch path — so it was committed to `scripts/inf70/` BEFORE the
deletion. `gguf_fuse_gate_up.py` was already in git (`inf70/b3` `dd27ec3bb`). A deletion is only reversible
if its recipe is in git; on the filesystem it is not a recipe, it is a coincidence.

**Original plan, retained:**
**What may be deleted once B7 reports — 183 GB, both reversibly:**
| artifact | size | why deletable | how to regenerate |
|---|---|---|---|
| `IQ4_XS-uniform-gateup` | 92 GB | superseded by `-gateup-r16`, which was built from it | `tools/inf70/gguf_fuse_gate_up.py` from the era anchor (branch `inf70/b3`, `dd27ec3bb`) — one pass, no requant |
| `IQ4_XS-uniform-b4` | 91 GB | B4 complete ✅, an experiment arm | B4's `--tensor-type` overrides, one `llama-quantize` pass |
| B7's loser | ~92 GB | whichever of {IQ4_NL, Q8_0-PLE} B7 rejects | the splice tool, or it is the anchor and stays |

**What must NOT be deleted — CORRECTED 2026-09-04 on operator challenge; my first version was wrong:**
I wrote that deleting `IQ4_XS-uniform` "would invalidate the comparison basis for every future delta on this model."
**That is false, and the operator is right: the comparison basis is TRANSITIVE, exactly as autokernel already
operates it.** A champion that was properly benched against the anchor *inherits its provenance*, and future deltas
are measured against the **champion**, not the anchor — that is the champion-of-record model
(`feedback_one_champion_invariant`: one champion aggregates all work between promotions). The anchor's value lives
in the **recorded delta**, not in the file. Ours is recorded: gate-up 10.33 → r16 10.49 ±0.02 (−1.48 ms) at build
10196 with placement proven, and r16 12.73 vs uniform 12.61 on the production mix at the merged tip — same build,
same window, same recipe, SHA-256 and byte counts on both sides. **So r16 can serve as the champion and the anchor
becomes deletable.**
**Three conditions make that sound, and they should be stated rather than assumed:**
1. The champion was measured against the anchor **under the artifact rule** (same build/window/recipe) — r16 was.
2. The chain is **recorded with enough provenance to reconstruct it** — SHA-256, byte counts, build ids, recipe: yes.
3. The anchor is **re-obtainable** if a future re-validation ever needs it. `IQ4_XS-uniform` is an unsloth-published
   quant, so it is a ~92 GB / ~2.8 h re-download rather than an unrecoverable loss. **Verify that specific file is
   still published before deleting it** — that is the only real precondition, and it is a five-minute check.
**Genuinely keep**: `-gateup-r16` (or whatever B7 promotes) as the champion; `UD-IQ4_XS` (88 GB, the served file);
`MTP/` (6.5 GB, the heads earning the 1.89×).
**Revised ceiling: with the anchor also releasable under a promoted champion, the reclaim is ~275 GB rather than
~183 GB**, leaving champion + served + heads ≈ 187 GB.
**Sequencing unchanged: do NOT reclaim before B7 reports** — it needs ~92 GB now, and deleting its comparison inputs
mid-experiment would be self-defeating. **Trigger: B7's verdict.**

## OPERATOR GOAL 2026-09-04 — "run qwen3.8-Next-Flash AS FAST AS POSSIBLE"

Verbatim. This **reorders the campaign's priorities** and is not just a restatement of intent:
- **Speed ranks above losslessness.** The operator already ruled approximate MTP acceptable (decent acceptance +
  no garbage). So where a lossless and an approximate configuration differ in speed, **the faster one wins** —
  losslessness is a bonus, not a requirement, and no task may treat it as a gate.
- **The comparison that decides this has never been run**: lossless and approximate multipliers have only ever been
  measured at DIFFERENT n-max on DIFFERENT prompt sets (approximate: n-max 2/3/4 on 24 production prompts;
  lossless: n-max 2 on 7 gate prompts with `-fa off`). `be1-ship` Phase 2 runs the cross on one prompt set.
- **`-fa off` is a cost, not a free win.** Every lossless result to date depends on it, and its cost has only been
  characterised as "within noise on the gate table" — not measured at production or long context, where flash
  attention actually earns its keep. `be2-fa` measures it; if it is free the decision is trivial, if it is not then
  `-fa on` with accepted non-exactness is a legitimate answer under this goal.
- **Standing ledger of what speed is still available**, so nothing is lost: BIOS 5600 MT/s + the C8 uncore checklist
  (held for the operator's reboot — the DIMMs run at 4800 of 5600 and the uncore caps at ~37% of nominal); the
  dispatch floor (~65% of the token at the best measured point, Axis A / INF-67 fused decoder); B7 PLE precision
  (quality, not speed); and B8's finding that ~20% of the bandwidth gap to the 122B is architectural.

## Deployable serving speed (claim-grade, 2026-09-03)

Single-stream `llama-server` decode of qwen3.8-next-flash, `-np 1 -c 4096 -t 48 --no-mmap`, canonical env,
forcing eviction, placement 23.0 GiB × 4, warmup + 5 × 128-token greedy `/completion` (`server-tps`),
coherence-gated (all 5 reps' greedy text bit-identical).

**Re-anchored on the merged experimental tip `0d2af8194` (b3k slab merged; build 10203, tree-identical to
`inf70/b3k`; slab default ON, `GGML_MMID_SLAB=0` = control), 2026-09-03, one lock hold, in-window
ggml-linkage + placement proven per arm:**

| artifact | slab | decode | ms/token | GB/s (% of 153) |
|---|---|---|---|---|
| uniform IQ4_XS (era anchor) | on (default) | **12.55 t/s** (ABA 12.589 / 12.516 ±0.05) | 79.7 | 52.3 (34.2%) |
| uniform IQ4_XS | off (control) | 12.079 ±0.033 | 82.79 | 50.3 (32.9%) |
| `IQ4_XS-uniform-gateup-r16` (best artifact) | on (default) | **13.06 ±0.01 t/s** | 76.59 | 52.7 (34.5%) |

- **The slab gain reproduces in the server path**: same binary/window, slab on vs off on uniform =
  **+3.9%** (12.55 vs 12.079, −3.35 ms/token) — confirming, and slightly stronger than, the +3.07%
  `llama-bench` proxy delta. All four arms coherent (greedy text bit-identical across 5 reps).
- **Both headlines beat the pre-measurement projection (12.4 / 12.8).** The prior (pre-b3k) merged tip
  `9e75132e3` measured uniform 12.00 / r16 12.38 in an earlier window — consistent with the slab-off
  control here (12.079). r16 vs uniform (both slab-on): +4.1% decode at ~equal GB/s, tracking the −3.0%
  bytes/token.

**RE-ANCHORED 2026-09-03 on the merged tip `42332502c` with PRODUCTION-LENGTH prompts — the gate the first
anchor lacked.** The earlier 12.00/12.38 and 12.55/13.06 figures were withdrawn because every gate behind them used a
12-token prompt while the tree produced garbage above ~32 (the iqk IQ4_XS ≥32-row repack defect, LONG-PROMPT-GARBAGE,
now fixed and merged). They are **replaced, not restored** — the configuration differs (chat-completions path with
thinking disabled, the production serving path, vs the raw `/completion` path before).

| artifact | decode (n=23 timed) | prompt range | correct behaviour | coherence gate |
|---|---|---|---|---|
| uniform IQ4_XS (era anchor) | **12.61 ±0.10 t/s** (12.43–12.93) | 54–682 tok | **27/27** | 23 COHERENT + 4 correct SHORT, **0 SALAD, 0 EARLY-EOS** |
| `IQ4_XS-uniform-gateup-r16` (best artifact) | **12.73 ±0.10 t/s** (12.50–12.97) | 54–682 tok | **27/27** | 23 COHERENT + 4 correct SHORT, **0 SALAD, 0 EARLY-EOS** |

27 production prompts — 8 coding / 8 reasoning / 8 general from `question_pool.jsonl` plus the three P0 prompts —
greedy, `max_tokens` 200, `enable_thinking` false, `-np 1 -c 8192 -t 48 --no-mmap`, canonical env, forced eviction,
**placement proven 23.0–23.1 GB × 4 and resident `libggml-cpu.so` proven to be the merged-tip build in-window on both
arms**. Coherence classified by REASON in the same window as the timing (`classify.py`); the 4 SHORT rows are
multiple-choice/short-answer items answering correctly (`E`, `B`, `<answer>English</answer>`, `B`) at n=2, where the
classifier correctly declines to compute degeneracy statistics rather than mislabelling them. Evidence
`/mnt/raid0/llm/tmp/inf70/reanchor2/`.

**Finding worth carrying: r16's advantage over uniform SHRINKS at production context lengths — +0.9% here (12.73 vs
12.61) against +3.1% at a 12-token prompt.** r16's edge is a bytes/token effect (−3.0%); as context grows, more of
the token's time goes to attention/KV work that the smaller weight stream does not help, diluting it. An artifact
advantage measured at toy prompt length overstates what production sees.

Note the fused-decode gate is opt-**out** (`GGML_FUSED_DECODE_OFF`), confirmed set in every arm's
`/proc/<pid>/environ`; the graph path is active. Ceiling context: the best served point (r16) reaches
**34.5% of the recipe's 153 GB/s** read bandwidth, i.e. ~65% of the token is still dispatch floor; the
bandwidth third also carries the BIOS headroom (DIMMs at 4800 of 5600, uncore-capped at ~37% of nominal),
held for the reboot. Evidence: `/mnt/raid0/llm/tmp/inf70/reanchor/` (per-arm timelines, `numastat`,
linkage proofs, `summary-*.txt`).

