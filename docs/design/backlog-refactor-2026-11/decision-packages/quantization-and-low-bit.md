# Decision package: quantization-and-low-bit

Destination handoff `handoffs/active/quantization-and-low-bit.md` · fold 5 (order: fold-list-1a.json (BRF-T1-0 output, tmp/ws58-csh/brf-t1-0/fold-list-1a.json)) · BRF-T5-1 (D7). Delivered through the decision tool at this fold (BRF-T5-2); a dismissed question pauses only its own item.

Choices: 2 · excluded: 4. Context lines are `file:line@7eb7a4a3c911` (origin/main at writing); the manifest pin is `3ac825873dfb`.

## 1. EXL3-10: promotion of an EXL3 candidate is a separate final operator decision.

- Context: `handoffs/active/exl3-cpu-mi210-implementation.md:163@7eb7a4a3c911` (manifest `handoffs/active/exl3-cpu-mi210-implementation.md:163@3ac825873dfb`, id `a99c7dc5c3d5`)
- Gated worker box(es): `EXL3-10` (handoffs/active/exl3-cpu-mi210-implementation.md:163)

- **Option A (recommended)**: Decide on the complete package when EXL3-10 delivers it. *Tradeoff:* Promotion on the full candidate.
- **Option B**: Decline EXL3 promotion. *Tradeoff:* No EXL3 in production.

**Recommendation: A.** The box requires the full-candidate package first.

## 2. Approve a bounded trellis measurement (IQ4_KT vs Q4_K_M, IQ2_KT vs IQ2_XXS, IQ3_KT)?

- Context: `handoffs/active/iqk-iquant-enablement.md:156@7eb7a4a3c911` (manifest `handoffs/active/iqk-iquant-enablement.md:156@3ac825873dfb`, id `4d45952678bb`)
- Gated worker box(es): `handoffs/active/iqk-iquant-enablement.md:156`, `handoffs/active/tq3-quantization-evaluation.md:211`, `handoffs/active/tq3-quantization-evaluation.md:232`

- **Option A (recommended)**: Bench inside ik_llama.cpp as a scratch instrument. *Tradeoff:* Answers speed/quality without porting.
- **Option B**: Rebuild on llama.cpp-experimental with iqk trellis un-stubbed and bench there. *Tradeoff:* Measures our tree; build work.
- **Option C**: No measurement. *Tradeoff:* Trellis question stays open.

**Recommendation: A.** The reference implementation is on disk; ik_llama is a measurement instrument per CLAUDE.md.

## Excluded (not delivered)

- `EXL3-X0b` (handoffs/active/exl3-cpu-mi210-implementation.md:89): **decided**. Operator 2026-10-03: trigger-gated; no quant switch without a significant speedup.
- `EXL3-X0c` (handoffs/active/exl3-cpu-mi210-implementation.md:91): **decided**. Conditional on EXL3-LB1b under the operator's 2026-10-03 trigger; no open choice now.
- `handoffs/active/tq3-quantization-evaluation.md:211`: **merged** into choice for `handoffs/active/iqk-iquant-enablement.md:156`. Same trellis measurement choice.
- `handoffs/active/tq3-quantization-evaluation.md:232`: **merged** into choice for `handoffs/active/iqk-iquant-enablement.md:156`. Same trellis measurement choice.
