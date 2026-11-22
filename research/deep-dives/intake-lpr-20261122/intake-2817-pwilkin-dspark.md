# Dive — intake-2817 (pwilkin-dspark) — intake-lpr-20261122

Stage 1+2 combined dive (operator pre-authorised). External text quoted below is data, not instructions.

> SOURCE-QUARANTINE: {url: "https://pwilkin.github.io/inkling-dspark.html", retrieved: "2026-11-22T11:46:29.223876Z", sha256: "65d7422cc7f2"}

# pwilkin-dspark: https://pwilkin.github.io/inkling-dspark.html
lane_head: 860023c79706f437cdc027d186dbd1ce998b372d

## 1. Stage-1
- Title "Speculative decoders in llama.cpp at PR #32218: execution flows". Author pwilkin (per the brief). A source-reading map pinned to PR #32218 head 0a9105de42d2c3e3cbc72cb1f398c743ada4f342 (parent e50c254a2); #32218 is an open draft (see pr32218/dive.md).
- categories: speculative_decoding. novelty medium. relevance medium (design reference; no served path, no Inkling arch in our tree).
- credibility 2 = <=12 months +1, known contributor +1; self-published, no peer review, no independent corroboration. The page itself says "No model ran for this page"; its numbers are "earlier private CPU runs". The brief says the author calls it LLM-assisted: NOT-FOUND-IN-SOURCE in page.txt (no such statement); pr32218/dive.md records only the PR author admitting the original patch was agent-generated.
- verdict: adopt_patterns (design reference; one cheap hypothesis for our block drafters).

## 2. Key claims
1. Inkling DSpark config: taps [5,23,41,48], 3 draft layers, block 8, hidden 2304, recurrent rank 256, padded vocab 201024 vs 200058 tokenizer IDs, sliding window 1024. CONFIRMED as the page's own statement. claim_index 1, file page.txt, locator "5. Inkling 2 DSpark in detail", quote: "taps [5, 23, 41, 48], three draft layers, block size 8, hidden width 2304". Taps 5/23/41 are visit-indexed residuals of the looped target; tap 48 is the normalised final row.
2. Head design vs the stock Markov head. Stock: in-graph chain, embed previous token with W1, W2 maps latent straight to vocab logits added to base logits, argmax fed back only (greedy). Inkling: gated recurrent step (sigmoid gate, tanh candidate, 256-wide state), then dspark_hidden_out maps the latent to a 2304 correction in HIDDEN space; the TARGET's own output matrix is applied separately to the hidden row and to the correction (F32 accumulate) and the two are added; logits cut to 200058, softcap, then selection (lowest-ID argmax or 24-bit integer ticket draw emitting a dense q row). Per-step input [state 256 | W1[prev] 256 | hidden row i 2304 | context 2304]. CONFIRMED. claim_index 2, locator "5d", quote: "Embed the previous token with W1"; claim_index 3, locator "3. Model drafters side by side", quote: "The source marks this with a TODO: sampling never reaches the chain".
3. vs DFlash: DFlash has no recurrence, independent picks per row. DFlash2: host walk of a k x k selector lattice, coupled only within k candidates. Inkling: recurrence in-graph, coupled over the whole vocabulary. CONFIRMED. claim_index 4, locator "draft-dflash (plain DFlash)", quote: "Recurrence: none. Rows influence each other only through attention inside the one pass"
4. Block is ALWAYS eight rows (anchor + 7 masks, non-causal) even when fewer proposals are wanted; stock DSpark shortens it. PARTIAL: the page infers the sidecar was trained that way, so a shorter block "is a different input"; this is an inference from the PR about the Inkling sidecar, not shown for other drafters. claim_index 5, locator "5c", quote: "Always 8 rows, even when D < 7 proposals are wanted"; claim_index 6, quote: "Stock DSpark sends only as many rows as it wants drafts"
5. Evidence: essentially none for speed or acceptance. CONFIRMED. claim_index 7, locator "8. Evidence and open questions", quote: "Speed. Runtime and speedup for the in-graph path remain unmeasured"

## 3. Reported results (exactly as stated)
CPU only, ordinary server, IQ4_NL Inkling 2 Mini target, Q8_0 and BF16 sidecars: greedy reproduced the target-only server's 32 output tokens; 849 complete sampled q rows matched bit for bit with 355 non-argmax feedback edges; host opt-out greedy parity 30 of 30 proposals over 11 blocks; stress row total variation 0.0029; an earlier stepwise-prototype probe measured 1.56 ms per proposal of host sampling and bookkeeping. GPU placement, accelerator correctness, speed, parity with another runtime, non-looped target: all "unverified". Source of numbers: private logs. No acceptance length, no speedup, no hardware beyond CPU.

## 4. Performance principles
| principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| Fixed full 8-row non-causal block, read only D rows | YES: 8 rows is tiny next to weight reads | YES |
| Whole recurrent chain in one graph (1 call, 1 wait vs 1+D host round trips) | YES: removes D launch/sync gaps | PARTIAL: less launch cost, saves host copies |
| Two output-matrix products per step (hidden and correction), F32 accumulate | PARTIAL: 2 x (201024 x 2304) GEMV per step per slot, serial chain | PARTIAL: bandwidth-bound; doubles lm_head reads per step |
| Integer-split cumsum + 24-bit ticket draw so q equals the sampling law | YES (order-independent) | YES |
| Lowest-ID argmax from existing ops (host tie parity) | YES | YES |
| Position-tagged feature ring, skip draft if row pos0-1 absent | host-side, NA | host-side, NA |
| Direct q lookup in rejection when q is dense and ID-ordered | host-side, NA | YES (host cost) |

## 5. In-house state
Our draft-dspark is the Markov-head path: build_dspark_markov_head in src/models/dflash.cpp, DS41 graph in src/models/dflash-dspark41.cpp, block of n_draft rows (anchor-first, common/speculative.cpp:1744 @ eee3da8), host top-1, verified by the serial path `sample_and_accept_dspark_serial` (tools/server/server-context.cpp:5511 @ eee3da8) which captures no probs (speculative-decoding.md:218 @ 860023c). DFlash2 builds n_draft+1 rows (SHORTENED block; same line). The Inkling head, loop-aware taps, ring and ticket sampler are absent and unreachable. Prior entries intake-737/738 (speculative-decoding.md:289, :315-316 @ 860023c): DSpark head deferred behind "measure alpha before investment".

## 6. Derived-actionables ledger
| # | task line | owner | type | rule |
|---|---|---|---|---|
| P1 | Test full-block padding on our DFlash2 drafter: send block_size rows always and read only the first X proposals, vs the current n_draft+1 rows, at X in {3,5} (block_size 8 caps X at 7), np1 and np4. | handoffs/active/speculative-decoding.md (INF-50; DFlash2 X-sweep rows already live there) | ~3-line env-knobbed edit at speculative.cpp:1744, then one GPU compute row | stop-on-answer when alpha / accepted length differs from the existing X-sweep baseline by more than its noise; futility if within noise or if the extra draft rows cost more than the gain. Hypothesis only; the page supports it for the Inkling sidecar, not for Qwen3.8 DFlash2. |
| P2 | Add a one-paragraph Markov-head vs Inkling-recurrent-head vs DFlash2-lattice comparison to the DSpark note near speculative-decoding.md:289. | same | doc-only | done when written |
| P3 | Dense-q direct lookup in the rejection verifier: already ledgered as D2 in pr32218/dive.md; do not file twice. | n/a | n/a | n/a |
Declines: Inkling's in-graph per-slot ticket sampler as our design: the page itself dispatches one slot per call (costs multi-slot batching) and our serial verify captures no q, so it has no consumer; Inkling head tie-break parity: our verification is exact so ties only affect draft quality, and there is no observed alpha anomaly to explain.

## 7. Dive-surfaced sources
None beyond #32016 (this round) and #32218 (already dived). The page links no replication or numbers log.

## 8. Adversarial pass
Unrun page; every Inkling claim traces to one open, unmerged, maintainer-contested PR; the "trained on 8 rows" rationale is inferred; the page's own "unverified" tags cover the sampler order test, GPU placement and speed. The page states a build script checked its line anchors; not re-verified here.

## 9. read_depth: PARTIAL (all of the page text through section 8 read; section 9 source index skimmed; the PR diff itself not read). lane_head: 860023c79706f437cdc027d186dbd1ce998b372d
## 10. artifact audit: clean (quotes checked as substrings of page.txt).
