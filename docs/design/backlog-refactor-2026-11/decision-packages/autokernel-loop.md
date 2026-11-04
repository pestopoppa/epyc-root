# Decision package: autokernel-loop

Destination handoff `handoffs/active/autokernel-loop.md` · fold 12 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 9 · excluded: 5. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. OAB-15 / OP-59: opencode store, (a) global `snapshot:false`? (b) a retention policy?

- Context: `handoffs/active/autokernel-orchestrator-actor-backend.md:527@7eb7a4a3c911` (manifest `handoffs/active/autokernel-orchestrator-actor-backend.md:527@3ac825873dfb`, id `3aacc295f9de`)
- Gated worker box(es): `OAB-15` (handoffs/active/autokernel-orchestrator-actor-backend.md:527)

- **Option A (recommended)**: (a) per-call only + (b) age out headless-actor sessions older than N days. *Tradeoff:* Keeps TUI undo; bounds the 10.8 GB store + 10.9 GB WAL.
- **Option B**: (a) global + (b) age out. *Tradeoff:* Simpler config; disables TUI undo.
- **Option C**: No change. *Tradeoff:* Store keeps growing; VACUUM cannot shrink it.

**Recommendation: A.** This is the package's own recommendation; only retention can shrink the store.

## 2. R23-1: file the llama-cli EOF fix upstream?

- Context: `handoffs/active/autokernel-rebuild-program.md:1154@7eb7a4a3c911` (manifest `handoffs/active/autokernel-rebuild-program.md:1154@3ac825873dfb`, id `75820b54fd88`)
- Gated worker box(es): `R23-1` (handoffs/active/autokernel-rebuild-program.md:1154)

- **Option A (recommended)**: File upstream. *Tradeoff:* Helps every non-interactive llama-cli user; a small PR to maintain.
- **Option B**: Keep it local. *Tradeoff:* No upstream effort; the defect stays in upstream.

**Recommendation: A.** The fix is small and correctness-only; open-source upstreaming fits policy.

## 3. Ratify the P-KLD divergence-protocol annex (OP-38, `ratify_p_kld_divergence_protocol_20260915.sh`)?

- Context: `handoffs/active/autokernel-rebuild-program.md:1771@7eb7a4a3c911` (manifest `handoffs/active/autokernel-rebuild-program.md:1771@3ac825873dfb`, id `0c4189186da6`)
- Gated worker box(es): `R23-47` (handoffs/active/autokernel-rebuild-program.md:1771)

- **Option A (recommended)**: Ratify. *Tradeoff:* Gives KLD/PPL claims a protocol (route-pinned MoE cells, fp64, cluster bootstrap); INF-70 KLD needs a re-read under it.
- **Option B**: Ratify with edits. *Tradeoff:* Same, after a revision round.
- **Option C**: Decline. *Tradeoff:* No divergence protocol; KLD numbers stay observation-grade.

**Recommendation: A.** MEASUREMENT.md has zero divergence terms and the package is prepared; only `bash -n` was run, so the operator run is the test.

## 4. R23-29: spend the 3 h Q4_K floor calibration, or run the ~15 min ungated llama-bench A/B first?

- Context: `handoffs/active/autokernel-rebuild-program.md:2639@7eb7a4a3c911` (manifest `handoffs/active/autokernel-rebuild-program.md:2639@3ac825873dfb`, id `f134678f1b81`)
- Gated worker box(es): `R23-29` (handoffs/active/autokernel-rebuild-program.md:2639)

- **Option A (recommended)**: Ungated A/B first, calibrate only if it shows a signal. *Tradeoff:* ~15 min GPU; not claim-grade.
- **Option B**: Full 3 h A/A floor calibration now. *Tradeoff:* Claim-grade; 3 h GPU for a target no one has chosen.

**Recommendation: A.** The box recommends the cheap signal first; no Q4_K GPU target exists yet.

## 5. Sign off P4 exit (rebuild the loop): run 11 met the bar by the letter?

- Context: `handoffs/active/autokernel-rebuild-program.md:511@7eb7a4a3c911` (manifest `handoffs/active/autokernel-rebuild-program.md:511@3ac825873dfb`, id `82d844cf7518`)
- Gated worker box(es): `handoffs/active/autokernel-rebuild-program.md:511`

- **Option A (recommended)**: Sign off and tick P4. *Tradeoff:* Closes P4 on recorded evidence (10 iterations, 8 measurements, 2 champion commits).
- **Option B**: Require a second qualifying run. *Tradeoff:* Stronger evidence; one more loop run.

**Recommendation: A.** The exit bar was pre-declared and met; the box stays open only for the signature.

## 6. AK-PM-7: add a PORTABILITY class to registry entries?

- Context: `handoffs/active/autokernel-research-loop.md:5398@7eb7a4a3c911` (manifest `handoffs/active/autokernel-research-loop.md:5398@3ac825873dfb`, id `5e87a51fb354`)
- Gated worker box(es): `AK-PM-7` (handoffs/active/autokernel-research-loop.md:5398)

- **Option A**: Add a portability field. *Tradeoff:* Records what survives a hardware move; schema change.
- **Option B (recommended)**: Record the decision not to. *Tradeoff:* No schema change; the source ships no ablation or code.

**Recommendation: B.** Reading-and-design only and blocked on AK-PM-4; nothing may be adopted on the paper alone.

## 7. Push (fast-forward) research main to `eaf1ac36` (lane `lane/research-park-20260927`, fixed `window_ab.sh`)?

- Context: `handoffs/active/autokernel-research-loop.md:5610@7eb7a4a3c911` (manifest `handoffs/active/autokernel-research-loop.md:5610@3ac825873dfb`, id `79906437ff6e`)
- Gated worker box(es): `AK-MMQ-H10a` (handoffs/active/autokernel-research-loop.md:5610), `AK-MMQ-H10b` (handoffs/active/autokernel-research-loop.md:5616)

- **Option A (recommended)**: Approve the push. *Tradeoff:* Per-kernel timing and per-arm failure isolation land; covers AK-MMQ-H10a and H10b.
- **Option B**: Hold. *Tradeoff:* The fixed script stays on a lane; no MMQ timing CSV can be produced from main.

**Recommendation: A.** Both H10a and H10b wait on this push; the change is a measurement script.

## 8. Approve the additional HIGH validator event for AKU-07j (OP-AKU-HELD)?

- Context: `handoffs/active/autokernel-unified-surface-program.md:3269@7eb7a4a3c911` (manifest `handoffs/active/autokernel-unified-surface-program.md:3269@3ac825873dfb`, id `0298a9723b4c`)
- Gated worker box(es): `AKU-07j` (handoffs/active/autokernel-unified-surface-program.md:3269)

- **Option A (recommended)**: Approve. *Tradeoff:* Persisted held-cost settlement can be validated across restarts.
- **Option B**: Decline. *Tradeoff:* AKU-07j stops at the low-risk independent work.

**Recommendation: A.** The box separates it from the approved descendant capture; the validator is what proves restart settlement.

## 9. S3-AKU-11: launch the strategy-only ablation once costed (~255 attempts/arm, ~31 GPU-h/arm)?

- Context: `handoffs/active/autokernel-unified-surface-program.md:4043@7eb7a4a3c911` (manifest `handoffs/active/autokernel-unified-surface-program.md:4043@3ac825873dfb`, id `60281b648049`)
- Gated worker box(es): `S3-AKU-11` (handoffs/active/autokernel-unified-surface-program.md:4043)

- **Option A (recommended)**: Keep launch gated; deliver the costed design only. *Tradeoff:* No GPU cost now.
- **Option B**: Approve a launch on the GPU screen surface. *Tradeoff:* Answers whether the critic matters; ~62-93 GPU-h.

**Recommendation: A.** The deliverable is a design with no launch; the cost is large and CPU is infeasible.

## Excluded (not delivered)

- `R23-49` (handoffs/active/autokernel-rebuild-program.md:1803): **merged** into choice for `handoffs/active/cpu-decode-roofline-program.md:1021`. Same tradeoff as MEAS-1 (OP-41: serialise builds vs CPU arms).
- `AK-PM-4` (handoffs/active/autokernel-research-loop.md:5347): **decided**. Operator ratified 2026-08-21 (AK-PM-11 option (a)): do not build yet; sequence SkillBank A/B -> AK-PM-11 -> build decision.
- `AK-PM-11` (handoffs/active/autokernel-research-loop.md:5443): **decided**. OPERATOR-RATIFIED 2026-08-21 option (a): do not build cross-run memory until the ablation returns.
- `AK-MMQ-H10b` (handoffs/active/autokernel-research-loop.md:5616): **merged** into choice for `AK-MMQ-H10a`. Waits on the same research push as AK-MMQ-H10a.
- `VB-AK-HISTORY` (handoffs/active/autokernel-research-loop.md:5698): **decided**. DONE 2026-10-24 by operator decision (3c4ca599); landed as two research commits.
