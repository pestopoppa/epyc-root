# MOAT: Migration Orchestration via Automated Translation (AMD-Ecosystem/moat)

- **Intake**: intake-2746 (`intake-2746#record`)
- **Source**: https://github.com/AMD-Ecosystem/moat
- **Verification**: dive-verified · read depth PARTIAL
- **Disposition**: integrated; handoffs: autokernel-loop.md, rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Adopt the evidence-discipline patterns (ISA-identity carry-forward, blocked-vs-failed, base control). Do not adopt the port/PR tooling; Moat is not a performance search loop.

## Key claims (anchored)

0. Moat runs five agents in sequence that hand over through a state file; the reviewer and validator can send work back to the porter.
   - README How it works: "Five agents run in sequence, and each hands over through a state file rather than a conversation"
   - README How it works: "The reviewer and the validator can both send it back to the porter."
1. Validation is gated on real-GPU test runs per wavefront gate; a compile or CPU-only smoketest is not evidence.
   - README maintainer section: "A compile is not evidence and does not count."
   - README Scope and honesty: "A CPU-only build smoketest proves compilation only; correctness is gated on real-GPU test runs."
   - README gates: "Coverage is expressed as gates -- wave64, wave32, windows"
2. Decisions that need a person are enforced by tooling and bound to a commit and its text.
   - README What a person decides: "Each is enforced by the tooling rather than by an instruction an agent is asked to remember"
   - README What a person decides: "their approval is bound to that commit and that text"
3. Moat names silent 32-lane assumptions as the most common way a CUDA port breaks on AMD.
   - README gate note: "Code that silently assumes 32 is the single most common way a CUDA port breaks on AMD"

## Dive record

2026-11-20 Stage-2b wave-2 dive (sonnet; PARTIAL: README, AGENTS.md, validator.md, reviewer.md, heads of codeobj_diff.py and changeclass.py read @ 86968a5e896a). Moat is a port gate-and-provenance workflow, not a performance search. Transferable to our loop: evidence bound to an exact commit with re-derivation on head move; carry-forward without a GPU re-run only when exported symbols and normalized device ISA are identical (indeterminate treated as differ); a 'blocked (host fact) vs failed (code fact)' distinction when no GPU is present; a base-control pattern (rebuild the pre-fix source and show the gate still passes) to prove a gate is blind; 'assertion count is a lower bound' and 'read what the checker compares'. Our loop is already stronger on gaming controls (autokernel-loop.md §8.6 L2007-L2023 @901b3fe). All Moat measurements are ROCm 7.x. Licence/fork/upstream machinery not applicable. CONTRIBUTING.md declined. lane_head 901b3fe44a30
