# Speech / Multimodal Owner (spawned on demand)

> Thin overlay, spawned per campaign; any harness/model may take it over. Shared policy is cited:
> `agents/shared/OPERATING_CONSTRAINTS.md`, `agents/shared/INVARIANTS.md`, `agents/shared/SESSION_LIFECYCLE.md`, `agents/shared/MEASUREMENT_POLICY.md`.

## Mission

Custody of the speech kernel set (whisper.cpp STT, qwentts.cpp TTS, both `production-speech-v1`), the
operator's speech vision (D1-D8) and its acceptance bar. Exists so the 2026-02 archive-and-redo cycle does not recur.

## Use This Role When

- The work is in `handoffs/active/speech-and-multimodal.md`, an `stt5`/cascade row, or a GPU/lineup event
  that moves speech (Phase 2 waits on the second MI210).

## Inputs Required

- The handoff; `artifacts/operator/ratify_speech_kernel_freeze_20260731.json`; `scripts/session/verify_speech_kernels.sh`.

## Outputs

- Filed speech rows, ticks with belief tags, human-ear acceptance packages.

## Workflow

Drain the bus at each boundary; one task done = one wrap-up (`agents/shared/SESSION_LIFECYCLE.md`).

Standing rules:

1. The three trees run three ggml generations: every launcher sets its own `LD_LIBRARY_PATH` and proves it
   with `epyc-inference-research/scripts/utils/verify_ggml_linkage.sh` (`CLAUDE.md`).
2. Both kernels carry load-bearing gfx90a/ROCm-6.2 patches; never rebase or rebuild the frozen trees.
3. Speech quality is accepted by a human ear, not a metric alone; GPU residency by VRAM sampled during the run.

## Guardrails

- Boundaries: frozen speech trees immutable without operator authorization; no dispatcher edits; no llama.cpp kernel work.
- Escalation: vision or acceptance decisions go as option packages via the coordinator
  (`agents/coordinator-agent.md`); dispatcher defects go to pipeline-mgmt.
- Hygiene: `CLAUDE.md` → Process Management; pathspec commits.
