# Vidya Belief-Substrate Program — superseded history through 2026-09-27

> **Historical ledger only; current work lives in [../active/vidya-belief-substrate-program.md](../active/vidya-belief-substrate-program.md).**
> Moved verbatim at the 2026-09-27 wrap-up (session `workspace-8d`): superseded snapshots, not evidence records.

## Superseded 2026-08-26 state snapshot

_Superseded: the P5c verdict became PROMOTE later on 2026-08-26 (see the completed sibling, section "P5c promotion gate"). The snapshot below records the earlier ITERATE state._

**2026-08-26 state:** the read side is now fully wired. `cite-check` gates every commit through
`index_state.py --check` (self-heals a missing ledger by re-ingesting; scoped to changed
handoffs/wiki/docs; blocking = dangling/overturned/conflicted only). The ledger is rebuilt
(gen-2, 12,479 frames, checkpoint committed; gen-1 attestations archived). Every open row below
carries a STATUS + SHARPENED TRIGGER: the open items are named producer events (freeze lift,
autopilot restart, capture flag, successor runs), not open questions. Decisions taken
2026-08-26: SC16 (keep-conservative `uncertain`), SC47 (decline FlashInfer as carrier), SC11/
SC13/SC48/SC6-HAZARD (priced-and-declined), SC32b renumbered SC51. The P5c promotion gate is
executed for the first time (requirement 4 evidence, verdict ITERATE pending requirements 1–2).

## Dependency notes (P1–P5 era, resolved)

V2 blocks P1 (the pilot spec must exist before the engine). P0 can run in parallel with V2 (it is
operator + curation work). P2 depends on P1 (frames must exist). P3–P5 sequence after P1–P2.
R1/R2 are paper-track and independent; R3 deliberately severed; R4/R5 need pilot data.
