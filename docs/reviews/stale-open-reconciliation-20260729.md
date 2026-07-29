# Stale-open reconciliation — 2026-07-29

## Method and result

Three independent read-only sweeps covered the active handoffs alphabetically
(`0`–`fable5`, `gemma`–`pipeline`, and `qwen`–`yarn`). The integrator also scanned
all unchecked lines carrying completion markers. A checkbox was changed only where a
reachable commit plus a named file, artifact, or regression test proved the exact
deliverable. This pass made **12 checkbox flips**.

| Handoff | Flips | Proof |
|---|---:|---|
| `context-folding-progressive.md` | 2 | orchestrator `921f71d1` + `tests/unit/test_session_summary.py`; root `2102c0f05` |
| `gpu-serving-tie-in-program.md` | 1 | root `724130a2`; `heterogeneous-slot-fabric-residency.md:114-135` |
| `gpu-acceleration-path.md` | 2 | root `c942728e` + `progress/2026-07/2026-07-25.md`; root `683f70de` + `research/intake_index.yaml` |
| `internal-kb-rag.md` | 7 | Stage-2a evidence recorded by root `c942728e` (five findings) and `683f70de` (two corrections) |

The flips distinguish completed analysis/recording from later execution. For example,
the GPU-host-thread gap is recorded, but the separate fabric-slot implementation is
still open; K-eval is re-scoped, but still requires a region claim.

## Needs owner confirmation — do not flip

These items appeared partially complete or superseded, but the exact requested
deliverable was not proven. They remain unchecked.

- `ernie-image-turbo-evaluation.md:139`: result exists elsewhere, not in the
  explicitly required deep-dive.
- `autopilot-continuous-optimization.md:517` (AP-27): scaffolding exists, but the
  required Ouro integration does not.
- `evidence-plane-event-sourcing-and-narrative.md:80,83` (W3/W6): implementation
  exists but consumer/acceptance work remains.
- `eval-tower-verification.md:413-414` (EV-10a/b): scaffolds landed, deployment and
  producer wiring remain.
- `document-parser-table-bench.md:71,144`: architecture pre-check does not prove
  the conditional parser work is complete.
- `harness-selection-and-integration.md:134,136,142-148`: findings exist, but the
  named matrix/index/policy outputs are absent or future-facing.
- `internal-kb-rag.md:222-223`: standing future-use directions, not completed
  deliverables.
- `opendataloader-pipeline-integration.md:629`: source review is complete; the
  requested ODL-to-PageIndex probe was not run.
- `gpu-serving-tie-in-program.md:144-145` (P2-5l/P2-5m): rationale is documented,
  but the file-owner comment correction and P-SHED reporting change are absent.

The broader stale-open audit also identifies parked, superseded, and gate-frozen
work. Those states are deliberately not counted as complete in this reconciliation.
