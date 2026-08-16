# GPU Candidates surface — add Qwen3.8-27B as the new stock-27B arm

**Status**: MOSTLY DONE — artifact updated across all sections; SWE agentic rung parked on a devcontainer restart.
**Created**: 2026-08-14
**Priority**: P2 (presentation surface; not evidence authority)
**Effort**: Low — re-populate one candidate row with Qwen3.8-27B data + fill the gaps

## NEXT STEP — top of queue

1. **Commit the harness parser fix (do this first).**
   `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/agentic_swe_harness.py` is modified
   (+43 lines, staged): `_translate_native_tool_calls()` maps Qwen3.x's native
   `<tool_call><function=bash><parameter=command>…` grammar to the harness's `ACTION:` grammar (grep/read/
   edit/done), plus a defensive `_sha256_file()` for early-return instances. **It is staged but NOT committed** —
   the shared research clone is mid-merge from another session (`U` files under
   `scripts/kernel_rnd/autokernel/`), so `git commit` refuses. **Do NOT touch the conflict.** Once the other
   session's merge clears, commit from the research repo (file is already `git add`ed):
   `git -C /mnt/raid0/llm/epyc-inference-research commit -m "agentic_swe_harness: translate native tool-call grammar to ACTION:; defensive _sha256_file"`.
   The fix is safe in the working tree + index and will survive the wait.
2. **Recreate this devcontainer from the host.** Its `/var/run/docker.sock` is an **orphaned bind-mount**
   (inode pinned from Aug 13; the host dockerd unlinked + recreated the socket at 13:58:01 during the
   29.7.1→29.7.2 apt upgrade). Container-local and irreparable from inside — the host docker and all 40
   `sweb.eval.*` containers are healthy and untouched. This is the **only** blocker on the SWE re-run.
3. **Re-run the SWE agentic harness** on the 19 previously-empty instances (parser fix now active):
   swebench `run_evaluation --max_workers 8 --run_id q38-agentic-final` (instances list
   `/tmp/opencode/swe_remaining.txt`, script pattern `/tmp/opencode/q38_agentic3.sh`), merge with the 21
   patches from run 1, re-run FAIL_TO_PASS, and write **SWE-40 = resolved/40** into the artifact's
   coding-ladder cell + verdict card (currently **15/40 = 37.5%, provisional/understated**).

## The artifact

`/mnt/raid0/llm/tmp/claude-artifacts/np_context_v8_decision.html` — *"GPU Candidates — Throughput &
Model-Selection Surface"* (presentation surface only; evidence authority is the research bundles
`epyc-inference-research/artifacts/np_context_study_v8_20260727/` + `np_context_study_20260723/`).
It shows the architect trio (A4 35B-A3B, Stock 27B dense, A1 122B-A10B IQ2) + 27B finetunes + Laguna-S-2.1,
each with the coding ladder (LCB-hard n=53, BCB-hard n=90, SWE-40 n=40), RAG-at-depth, throughput, MTP gate.

## Task

Add **Qwen3.8-27B** as the new "Stock 27B" arm — the direct successor of the `Stock 27B dense`
(= Qwen3.6-27B) row. Same axes, same era-labeling discipline (label the kernel era; never silently re-collect).

## Coding ladder — WAS RUN (supersedes the earlier "deferred")

The operator declined the Qwen3.8→Qwen3.6 quality comparison on 2026-08-14, then later authorized the coding
ladder anyway ("both rungs, proceed"). Full architect bench (v9 `0db32c06e`, seeded temp 0.6, MTP, reasoning
off) landed:

| Rung | Score | |
|---|---|---|
| LCB-hard (n=53) | **52.8%** (28/53) | tops the 27B class |
| BCB-hard (n=90) | **31.1%** (28/90) | ties stock 27B |
| SWE-40 (n=40) | **15/40 = 37.5% (provisional)** | agentic, understated — 19/40 empty from format-mismatch, now fixed |
| humaneval | 96.3% (158/164) | |
| aime25 / gpqa (cot) / gpqa (letter) / mmlu_pro / olympiad_hard | 76.7% / 81.3% / 42.4% / 56.7% / 47.1% | |

## Steps

- [x] **Populate the throughput row** — Qwen3.8-27B flat ~45 t/s MTP decode, pp512 prefill 727 t/s, era v9 `0db32c06e`.
- [x] **Prefill pp512** — `727.29 ± 28.00 t/s` (`llama-bench -ngl 999 -nkvo 1 -p 512 -r 3`).
- [x] **Coding-ladder cell** — populated (LCB 52.8% / BCB 31.1% / SWE 15/40 provisional); SWE finalizes on re-run.
- [x] **RAG-at-depth + MTP workload-gate** — measured: single-stream decode FLAT ~45 t/s (47.6@2k → 45.0@32k);
  peak aggregate 157.3 t/s @np8/2k. (The earlier "37→13.6 decline / MTP reversal" was a synthetic
  random-word-prompt artifact — corrected; real prompts give a flat MTP curve.)
- [x] **Update the verdict prose** — bottom line + verdict card re-read with Qwen3.8-27B as the new 27B coding bar.

## Deps

`INF-60` (qwen38-27b-replace-qwen36.md) — this artifact update is the *presentation* tail of that rollout.

## Completed 2026-08-16

- Artifact updated across ALL sections (header, verdict card, coding/reasoning ladders, RAG heatmap, 24-cell
  GRID, router plan, bottom line) with Qwen3.8-27B.
- np × depth 24-cell sweep done (real olympiadbench prompts).
- SWE images built (40) + containers started; agentic run 1 → 21 patches / 19 empty (format-mismatch).
- Harness parser fixed (native tool-call translation, 20/20 unit tests pass) — staged, awaiting commit.
- SWE-40 = 15/40 (provisional) written to the artifact; re-run parked on the devcontainer restart.
