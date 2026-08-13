# mainB — repl-turn-efficiency backlog batch (4 rows, one file)

**You are mainB** (roster id `mainB`, lanes `[gpu, none]`). Bootstrap: `drain --agent mainB --triage`, then execute.

All four rows live in `handoffs/active/repl-turn-efficiency.md` — work them as ONE batch (one file, one writer). Each is small (~0.5h), `lane: none`, no compute. Verify each premise against the file before acting; a screened row can already be satisfied.

1. **L101** — S4 Omega A/B candidate: adopt the turn-floor + mandated-procedure shape from
   `MULTIPAPER_CHILD_SYSTEM_PROMPT` as the intervention arm (this handoff previously had none).
2. **L102** — Only if an evidence-retrieval suite is separately justified: plumb HotpotQA's
   already-loaded-but-DISCARDED `supporting_facts` (`dataset_adapters.py:1524`) into the emitted
   record to create the first span-level GT, and write the interval metric with a robust matcher.
3. **L117** — Record the zero-sub-LLM result: on Oolong synth-with-labels the RLM scored perfectly at
   every context length using **regex over the context variable**, zero sub-LLM calls.
4. **L120** — Provenance fixes: neither intake-537 nor intake-803 references this handoff (both cite
   `completed/` targets; `rlm-orchestrator-roadmap.md` archived 2026-03-29). Fix the cross-refs.

## Constraints

- lanes `[gpu, none]`: no compute, no region claims.
- **Push policy (operator 2026-08-13): docs/handoffs pushes PERMITTED** — commit and push your
  handoff/progress edits at wrap-up. Hold kernel/orchestrator code pushes.
- Wrap up at the boundary: flip `- [ ]`→`- [x]` for anything you record done, commit, push the
  handoff edits.
