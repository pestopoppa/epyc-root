# FlyDSL: Expert GPU Kernel Development with the Ease of MLIR Python Native DSL on AMD GPUs

- **Intake**: intake-2736 (`intake-2736#record`)
- **Source**: https://rocm.blogs.amd.com/software-tools-optimization/flydsl-python-native/README.html
- **Verification**: dive-verified · read depth FULL
- **Disposition**: knowledge_only; handoffs: rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Positioning blog only; it says nothing about gfx90a support. Cite nothing numeric from it.

## Key claims (anchored)

0. FlyDSL targets thread-level and IR-level control for expert developers, complementary to block-level Triton.
   - Section 3: "thread-level and IR-level control for expert developers seeking roofline performance"
1. FlyDSL operators have entered early production adoption, claimed competitive with CK, with no numbers given.
   - Current Status: "FlyDSL-based high-performance operators have entered early production adoption"
2. The roadmap lists MFMA, Atom and additional intrinsic support; the pip package supports Python 3.10+; no GPU target is named.
   - Roadmap: "MFMA, Atom, and additional intrinsic support"
   - Install: "The pip package (flydsl) supports Python 3.10+"

## Dive record

2026-11-20 Stage-2b dive (sonnet; full read). Launch post (Feb 2026, updated Mar 2026); names no gfx target, MI model or ROCm version; performance claims qualitative. Vocabulary and positioning only; the architecture facts are in the FlyDSL docs entry. lane_head b5c5fe7b4e63
