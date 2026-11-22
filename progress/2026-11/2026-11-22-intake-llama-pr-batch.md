# 2026-11-22 — research intake: llama.cpp PR batch + Inkling 2 Mini (intake-lpr-20261122)

- Ran the research-intake skill on 9 operator-submitted sources (llama.cpp PRs #32741, #32774, #32775, #30846,
  #32456, #32740, #32771, #32758 and the HF Inkling 2 Mini blog). The operator pre-authorised all dives and up to
  four Stage-2b waves.
- Minted intake-2792..intake-2823: 9 submitted, plus 23 Stage-2b entries over 4 waves. All 32 are dive-verified,
  with 233 script-written anchor marks. The wave cap was reached; remaining surfaced sources are declined in the
  bearing entries' dive_corrections. intake-2598 (#28019) got a re-encounter note.
- Dives are in `research/deep-dives/intake-lpr-20261122/` (31 Markdown files).
- The Stage-3 plan is `research/deep-dives/intake-lpr-20261122/stage3-plan.md`: 7 packets, 10 proposed boxes,
  7 monitors and 2 knowledge-only items. The v2 payload validates. It is awaiting operator approval, so no handoff
  edits have been made.
- No compute used. Pre-existing (not from this run): `--check-anchors` reports 26 mark mismatches on
  intake-2678..2690.

Next: operator approves or edits the Stage-3 plan; then Stage 4 files the 10 boxes (owner: the research-intake lane).

## Stage 4 (operator-approved 2026-11-22 with three edits)
- Seven boxes filed:
  - speculative-decoding.md: SPEC-STALE-1.
  - harness-program.md: PFXC-SAVE-1.
  - autokernel-loop.md: AK-ISA-FAMILIES and GDN-VERIFY-BASE.
  - kernel-champion-and-promotion.md: FOLD-GUARD-H12 and FOLD-CENSUS-1 (FOLD-CENSUS-1 also asks, per upstream change, whether we gain from adopting it or our path is faster).
  - model-evaluation-queue.md: INK2-MINI-1, reframed to the 35B-A3B replacement role.
- H12 band, H12 union and Q8_0 two-stream screens are AutoKernel seed hypotheses: epyc-inference-research
  `scripts/kernel_rnd/autokernel/loop/seeds/hypotheses/20-intake-lpr-h12-band-union-q8-2stream-20261122.md`.
- Monitor and knowledge prose (M1-M7, K1-K3) placed in the owner handoffs. Dispositions are on all 32 entries.
- No index rows needed. validate_intake --plan-file and index_state.py --check both exit 0.
