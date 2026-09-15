# 2026-09-15 — research-intake: Dogacel/auto-gpu-kernel and the MLSys 2026 FlashInfer contest loops

**Session**: `/research-intake https://github.com/Dogacel/auto-gpu-kernel` (operator-spawned, shared clone, no lane).
**Operator prerogative (verbatim)**: *"My main prerogative with this research-intake session is distilling what (if
anything) this repo is doing better than our autokernel loop and learn from it."*
**Branch**: `intake/agk-20260915` in worktree `/mnt/raid0/llm/worktrees/intake-agk-20260915`, off `origin/main`
`50ee3656`, merged forward to `dd955d72` during wrap-up, then pushed and promoted to `main`.

## Stages

- **Stage 1** — 1 submitted URL + 5 expansion entries, all `stage1-unverified`. Expansion cap 10, used 5.
- **Stage 2** — operator selected all 5 recommended dives.
- **Stage 2b** — operator selected all 4 recommended dive-surfaced sources; every other surfaced source declined and
  recorded on the bearing entry.
- **Stage 3** — plan approved (`~/.claude/plans/tranquil-booping-flask.md`).
- **Stage 4** — this record.

## ID renumbering (the one execution deviation)

The shared clone `/workspace` was **357 commits behind `origin/main`** (local main `d372c953`, 2026-09-09), and
`origin/main`'s intake index already ran to **intake-1424**. The session's provisional block intake-1367..1376
collided with real upstream entries. Stage 4 therefore ran in a fresh worktree off `origin/main`, and the ten entries
were renumbered to **IDs 1425..1434**, with every in-entry cross-reference remapped (165 prefixed + 2 bare refs,
0 leftovers; all cross-reference ids resolve). Each entry records the renumbering in `dive_corrections`. Dedup was
re-run against `origin/main`: no collision for any of the ten sources. Credit: `workspace-55` warned about the stale
base before anything was staged.

| new id | source | verification |
|---|---|---|
| intake-1425#record | Dogacel/auto-gpu-kernel (kopt+kbench, Full-Agent DSA #1) | dive-verified |
| intake-1426#record | arXiv 2608.14560 Houmao multi-agent | dive-verified (placement claim overturned) |
| intake-1427#record | syhya/mlsys26-flashinfer-contest (LLM-CUDA / LoongFlow) | dive-verified |
| intake-1428#record | arXiv 2607.16831 MSInfer GDN | dive-overturned |
| intake-1429#record | Dogacel/DeepSeek-Sparse-Attention-Kernels (companion) | stage1, knowledge-only |
| intake-1430#record | romitjain/kachua-mlsys (GDN AA #1) | dive-verified |
| intake-1431#record | flashinfer-ai/mlsys26-contest writeup archive | dive-verified |
| intake-1432#record | kamahori/mlsys-contest-syfi-fully-agent (GDN FA #1) | dive-verified |
| intake-1433#record | mit-han-lab/mlsys2026-flashinfer-contest (HAN Lab KDA) | dive-verified |
| intake-1434#record | arXiv 2406.06484 + FLA reference kernels | dive-verified |

## The answer to the prerogative

Full synthesis: [`research/deep-dives/mlsys26-contest-loops-vs-autokernel.md`](../../research/deep-dives/mlsys26-contest-loops-vs-autokernel.md).

None of the contest loops beats ours on measurement, evaluator integrity, outcome logging or critic discipline. What
they expose is **our own hardened checks sitting unwired in the live loop**, plus the absence of any stall reflex:

1. `--autokernel-harden` + receipt check exist; `loop/bench.py:219-221` runs plain `llama-bench`, on a
   candidate-built binary, with the critic seeing only declared paths (R24-1, R24-2).
2. `check_no_fallback_dispatch_proof` (`evaluator/correctness.py:3047`) and `fold2_gates.py` G4 exist; `loop/run.py`
   imports neither (R24-4).
3. The critic runs `--dangerously-skip-permissions` in the lane worktree under a "make edits directly" note, with no
   re-hash before the gate (R24-3).
4. `gates.deterministic` compares return codes, never outputs, and has no caller (R24-5).
5. No keep-drought diagnostician (R24-7) and no no-measurement/keep-rate alarm (R24-8) — our runs 18/24/9 droughts
   were all caught by the operator.

Corrections the dives forced on the sources: auto-gpu-kernel's winning runs used neither kopt nor fresh sessions and
its report swaps the trace counts; 34.93x is an organizer arithmetic mean of ratios, not reproducible; Houmao never
won (1.68x is the #2 self-report); MSInfer's central prefill claim is contradicted by its own tagged artifact; SyFI's
full-agent prefill is a 0.981-similar copy of its human-steered kernel; HAN Lab's MoE #1 runs at 0.65x of baseline;
Kachua's Split-WY core is reference FLA practice, not a contest invention.

## Filed (16 new `- [ ]`, 0 checkbox flips)

- `autokernel-rebuild-program.md` → new **§ R24** with R24-1..11 plus a dated declined block.
- `rocm-verify-profile-backend.md` → **RVP-C6-26** (within-pair content-memo hole in the hardened bench).
- `log-linear-gated-deltanet-readiness.md` → **G16a**, **G16b**, plus an in-place correction to G16's 2e-7 attribution.
- `mi210-big-model-and-acceleration-roadmap.md` → **G15a**, plus the G15 wording fix
  (`GGML_CUDA_DELTANET_MIN_BLOCKS_PER_SM` is a compile-time macro; as an env var it silently does nothing, which would
  have measured the recurrent kernel twice and reported a tie).
- `autokernel-unified-surface-program.md` → P1b chunked-GDN sub-bullet (two-tier reference-restoring prepass, gated on
  a dispatch-proven A/B). §8 untouched, as it forbids new checkboxes.
- 36 ledger rows declined, each with a reason on its entry or in the R24 declined block.

## Verification

- `validate_intake.sh` exit 0 (1430 entries).
- `index_state.py --check` exit 0, including cite-check clean (126 citations across 5 documents; bare entry-level
  citations of entries carrying an overturned claim were converted to `#record`).
- No index rows needed: INF-66, INF-48, INF-73, INF-33, INF-34 already own these handoffs.
- No GPU, no inference, no builds this session.

## Wrap-up notes

- **Index pruning screen:** `index_state.py` prune signal returned **0 candidates**, so nothing was archived.
- **Wiki sweep:** content-hash drift showed 23 sources (8 added, 15 changed). I compiled only the two this session
  authored — the deep-dive and this progress note — into `wiki/autonomous-research.md`, and deliberately did **not**
  run `--touch`: advancing the shared watermark past the other 21 sources (other sessions' autokernel-hardening,
  disk-sweep, ROI-dispatch and AP50 work) would silently mark them compiled when no page was written for them.
  The watermark stays where it was, so the next sweep still sees them.
- **Agent logging** was not active for this session; `agent_log.sh` was never sourced, so there were no open tasks to
  close. Recorded rather than back-filled, since a retroactive audit line would assert a trail that does not exist.
- **Shared clone:** my provisional entries were truncated out of `/workspace`'s `research/intake_index.yaml`, and
  `.research-session.json` there holds this session's state (uncommitted, not carried into this branch — that tracked
  file belongs to whichever intake session last wrote it upstream).
