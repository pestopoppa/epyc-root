# 2026-10-21 — research intake: open-model backdoors, control-vector projection, Qwen3.8-27B post-train

Lane `intake/backdoor-cvec-20261020` (worktree `/mnt/raid0/llm/worktrees/intake-backdoor-cvec-20261020`),
for main session workspace-f8. Stages 1-2 done; the Stage-3 plan is drafted and NOT applied. No handoff or
index edits were made.

## What was done

- **Stage 1.** Processed an operator-pasted note with three items. Entries intake-2191..2207 cover 8 input
  sources and 9 expansions. Three are X relays (2192, 2194, 2196), read through a public X-mirror API.
  Re-encounter notes were added to intake-1841, intake-1934 and intake-1945. The SparTech article could not
  be located, so no entry was minted for it.
- **Stage 2, wave 1.** 13 dives: 2191, 2193, 2195, 2197, 2199-2207.
- **Stage 2, wave 2 (Stage-2b).** Six dive-surfaced sources were ingested and dived together, as
  intake-2208..2213. Wave 2 surfaced nothing further, so waves 3-4 had nothing to dive.
- **Totals.** 19 dive-verified entries carry 255 anchors, and all 255 were re-found by hash. The second
  reader returned 116 yes, 25 partial and 0 no over 141 claims.

## Key findings

- **Our exec exposure.** Verified at orchestrator 50f7ffbd:
  - `run_shell` allowlists python3.
  - Model-exec children inherit the full API environment.
  - Nothing restricts egress.
  - `HF_HOME` points children at a cache that holds an HF token.
  - The tool-call log lives in memory and records only successful calls.
- **Our artifact exposure.** GGUFs and chat templates are pinned and verified at none of download, launch
  or re-pull.
- **Ownership.** No handoff owns either the exec side or the artifact side. D-RI-CONTAIN covers only the
  opt-in REPL-cell lane.
- **Coder390 post-train.** Its LCB 83→90 headline is very likely a cap or baseline artifact: the official
  base model reports LCB v6 90.3. The "3.9M examples" figure does not appear in any primary source.
- **Control vectors.** v10 control vectors are additive only, and qwen4exp has no `build_cvec` call, so a
  vector loaded on Q38FN silently does nothing. reasoning-compression.md L129/L209 wrongly says qwen35 lacks
  `build_cvec`.
- **SEAL evaluation.** It has no refusal or safety side-effect check.

## Stage-3 plan (draft)

The plan is at `/mnt/raid0/llm/tmp/intake-backdoor-cvec-stage3/PLAN.md`, with `payload.json` and
`session-stage3.json` next to it. `validate_intake.sh --plan-file … --session-file …` exits 0 and
cite-check exits 0. It has 70 recommendations and 24 tasks across seven packets:

- **P1:** new `model-exec-containment.md`, UFH-16.
- **P2:** new `model-artifact-integrity.md`, RTG-59.
- **P3:** reasoning-compression.
- **P4:** iqk NEW-11/10.
- **P5:** architect bench AMSB-C390-0/1.
- **P6:** moe-routing RT-5.1.
- **P7:** frontier-f3 F3-W3-P1.

There are also 27 knowledge-only rows, 13 monitor rows (M1-M9) and 1 decline. Five operator questions are
in plan §11.

## Notes

- The harness intake (intake-2143..2190) landed on main earlier the same day. Its session record is not
  in `.research-session.json`, which holds this session with deepinfer archived under `prior_sessions`.
  When merging, check for a session-file conflict.
- Scratch kept as cited evidence is under `/mnt/raid0/llm/tmp/intake-backdoor-cvec-20261020/`: dive dirs,
  patches + LEDGER.jsonl, sr/, grounding/, briefs/, tools/ and stage1/fx_*.json. Uncited Stage-1 scratch
  was deleted.
