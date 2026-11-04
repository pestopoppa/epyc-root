# IFBench CJ-6a row readiness

This packet preserves the single-arm row specification, pinned model and source/input manifest, runner and offline-scoring wrapper. The model is Qwen3.8-27B Q8_0; the corpus is the 300-prompt official root file at IFBench commit `1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d`. Runtime source uses a detached Git worktree backed by shared Git objects, not a copied checkout. The dataset archive and pre-run outcome/uncertainty contract are [retained separately](../../../data/benchmarks/ifbench-1c40f0c/README.md).

The full run captures one immutable exposure per prompt with model, server, decoding, source, prompt and grant bindings; an unresolved exposure is UNKNOWN and stops continuation without redraw. Official strict and loose scores require an exact 300/300 prompt join; no paired delta or suite adoption follows from one arm.

The publisher smoke uses the actual pinned 27B target and production CPU kernel with one non-cohort engineering prompt, four CPUs, and isolated dry-run output. It must not write to the full cohort's run directory. Its outcome is an engineering qualification only, not an IFBench score. The 14,400-second estimate is a provisional window budget, not a completion guarantee.

The detached source worktree is load-bearing until scoring and original input evidence are preserved. The future result filer must remove that worktree with `git worktree remove <source>` before issuing the `FILED` receipt that permits scratch reclamation.
