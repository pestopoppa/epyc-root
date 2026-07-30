<!-- STAGED OVERLAY (epyc-root, AFC-P6.20) — bake into llama.cpp-experimental BEFORE the next
     kernel promotion so the vNEXT production tree ships this file at its root. It cannot be
     added to the frozen v8 tree: HEAD is pinned by verify_llama_cpp.sh + the ratification SHA.
     At promotion: copy over the upstream 1-line CLAUDE.md; leave upstream AGENTS.md in place
     (this file scopes it). -->

# llama.cpp production tree — EPYC project overlay

**THIS TREE IS THE FROZEN PRODUCTION KERNEL** (`production-consolidated-vN`; check
`git branch --show-current`). It serves the live inference stack.

- **Never build, edit, rebase, or commit here** without explicit operator authorization. All
  kernel/feature/benchmark work happens in the `llama.cpp-experimental` worktree — we version
  past production, never patch it in place. Workflow:
  `/mnt/raid0/llm/epyc-root/CLAUDE.md` § Experimental Kernel Workflow.
- `scripts/session/verify_llama_cpp.sh` (epyc-root) enforces the expected branch/commit/binary
  of this tree; any commit here breaks that attestation chain.
- The upstream `AGENTS.md` in this tree is ggml-org's contribution policy — it applies ONLY
  when preparing an upstream PR from a clean experimental branch. Its build instructions,
  commit-trailer rules (`Assisted-by:`), and ASCII-only style do NOT govern EPYC project work;
  project policy lives in epyc-root (private-fork exemption).
- Project governance, measurement policy, and session rules:
  `/mnt/raid0/llm/epyc-root/CLAUDE.md` (also reachable as `/workspace/CLAUDE.md`).
