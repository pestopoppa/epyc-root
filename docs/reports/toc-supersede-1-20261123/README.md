# TOC-SUPERSEDE-1: offline tool-supersession replay (2026-11-23)

Zero inference, zero model calls. Code: `scripts/analysis/toc_supersede_replay.py`, tests
`tests/analysis/test_toc_supersede_replay.py` (12 pass). Machine-readable results: `summary.json`
(per class, holdout, pooled) and `per_transcript.jsonl` (one row per input, aggregate counts only,
no transcript content). Run: 5 CPU-seconds, full corpus, no sampling except the secondary textual
regret check (stride-capped at 200 evicted outputs per transcript; 919 checked).

## Rule (fixed before the run)

A tool output is superseded by a later call in the same history segment that (a) reads or edits the
same path (`cat/head/tail/sed -n` count as reads), (b) re-runs the same normalized command
(leading `cd X &&` and trailing `2>&1` stripped; Grep/Glob keyed by identical input), (c) is a
SUCCESSFUL build whose targets overlap (a failed build does not supersede: a choice made where the
box text is silent), or (d) is a PASSING re-run of the same normalized test command. A round (one
assistant turn with at least one tool call) is a candidate when all its outputs are superseded and
the 2-round grace has elapsed from the last supersession before the end of the segment. Segments
split at Claude Code compaction boundaries. Tokens are chars/4 estimates; outputs under 40 chars
are never hash-matched.

Primary share = candidate-round output tokens / all history tokens (user text, assistant text, tool
inputs, tool outputs; thinking excluded). Also reported: share of tool-output tokens.

## Inputs and controls

1. Frozen manifest: 139 files, digest `18b94214cde16ba6629070cbdfcba465046da456f6aa8e521f9a4312ccd86c53`
   (sha256 over sorted `path, bytes, sha256` lines; each file read only to its recorded size, so the
   live session transcript cannot move the digest). 78 Claude Code transcripts (`~/.claude/projects/*/*.jsonl`,
   top level only, no subagent files) plus 61 recorded architect-bench bash-loop trajectories
   (`epyc-inference-research/artifacts/architect-bench-gpu-20260814/{agentic,agentic2,agentic4}/trajectories`).
2. Baselines: no eviction (share 0 by definition) and `_clear_stale_tool_outputs` (helpers.py:558)
   simulated per segment: keep the last 2 outputs, 12,000-char gate (its `max_context_tokens=0` path).
3. Per-transcript outputs retained: `per_transcript.jsonl`.
4. Holdout: transcripts whose first record is dated 2026-11-15 or later (23 Claude Code
   worktree/tmp transcripts only; all bench trajectories and all primary Claude Code transcripts
   predate it, so the holdout is almost empty and is NOT an independent confirmation).
5. Complete denominator: all 139 files counted, including 20 with zero tool calls.
6. Rule fixed before the run (this README and the code were committed together; no re-tuning).

## Results (full-history share; `summary.json` has the rest)

| class | files | calls | candidate share of history | share of tool output | dedup repeats | evicted (info-losing) | regret hash / text (sampled) | baseline age-clear share of history, regret |
|---|---|---|---|---|---|---|---|---|
| agentic_bench_bash_loop | 61 | 1,642 | **23.8%** | 43.3% | 717 | 402 (217) | 4.1% / 9.0% | 52.2%, 43.1% |
| claude_code_primary | 17 (2 zero-call) | 33,285 | 0.74% | 2.5% | 1,271 | 769 (720) | 1.0% / 0.4% | 29.2%, 4.0% |
| claude_code_worktree_tmp | 61 (18 zero-call) | 77 | 0.0% | 0.0% | 0 | 0 | n/a | 23.2%, 0.0% |
| pooled | 139 | 35,004 | 1.2% | 4.0% | 1,988 | 1,171 (937) | 1.7% / 2.4% | 29.6%, 5.7% |

Regret = an info-losing evicted output (superseder has a different hash) whose exact content hash
reappears after eviction; the text column is a secondary proxy (distinctive lines of the evicted
output quoted later). Superseded by kind (pooled): shell 957, read 696, edit 287, build 12, test 0.

## Verdict against the 15% gate

The gate is split, not clean. Pooled (token-weighted, dominated by the Claude Code volume) is 1.2%,
below 15%. The only class that is an autonomous tool loop (bench bash loop) is 23.8% of history
(43.3% of tool output), above 15%, so by class the M2 trigger FIRED for that class and did not fire
for Claude Code interactive/worktree use. The bench share is inflated against a real prompt because
the recorded history omits the system and task prompt. Not measured: (1) the orchestrator REPL class
(no recorded REPL transcript with tool-output text exists; consistent with the CF-AKV-0 finding
that `trajectory_artifact` has emitted nothing), (2) the AgentDiet SWE-bench release.

## AgentDiet trajectories

Downloaded `artifact.zip` from figshare (doi 10.6084/m9.figshare.30073654, 46,768,250 bytes, md5
`30e838719cc5dc5a4a64bcb4f55fe572` verified) to `/mnt/raid0/llm/tmp/ak1123-agentdiet/dl/`; the zip
contains `artifact/result/trajs.7z` (46.6 MB), extracted to `ex/`. No 7z tool is installed;
`py7zr` was fetched with `uv pip install --target` to `/mnt/raid0/llm/tmp/ak1123-agentdiet/pylib`.
The extraction script write was refused by the auto-mode classifier and was not retried or routed
around, so the AgentDiet class is NOT replayed. Adapter work remaining after extraction: a parser
for the Trae Agent trajectory format feeding `Segment`/`Call`.
