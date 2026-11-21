# Slipstream repo (intake-2779) - Stage-2b dive
Source: github.com/chenzhuofu/slipstream pinned 05d48f4ddf4fbab146f95b49f802db26e303e6f4 (cloned to extra/slipstream/repo); read_depth PARTIAL (README full; judge.py and summarizing.py accept/reject sections; not the rest of summarizing.py, tests, upstream base). lane_head ac1347f5d3218531bb369c286837630bf842ff74. Bears on intake-2770 (2605.08580v1/dive.md read first).

## Verdict
Code is released, MIT (inherited mini-swe-agent LICENSE.md), anonymous double-blind artifact. Runnable for SWE-bench Verified only.

## Verified facts
- Engine: vLLM server per run via SLURM; pyproject pins vllm==0.11.2 (paper reports 0.19.1 - mismatch to note). Models: Qwen3.5-9B (TP1), Seed-OSS-36B (TP2). Judge client is AsyncOpenAI against a base_url.
- Judge prompts present: V2-Fast (alignment + non-contradiction, score=min, 0-10, guided_choice '0'..'10', max_tokens 8, thinking off) and V2-Slow (JSON with reasoning).
- Reject path: async summary discarded, _do_summary re-run synchronously on pre-spec+spec context (docstring). This overturns the earlier dive's "targeted update" wording. Threshold is config speculation_threshold, not hardcoded.
- Gaps: BrowseComp harness not bundled; placeholder PROJECT_ROOT paths; Docker-free grading needs Apptainer images.

## llama.cpp server wiring
Feasible. Judge needs only chat completions with a 0-10 constrained output: llama-server GBNF/json_schema replaces vLLM guided_choice; enable_thinking via chat_template_kwargs; base_url/api_base configurable. Agent side needs two concurrent sequences sharing the pre-compaction prefix (slot + seq_cp; kv-prefix-fork P1 per prior dive). Cost M; MI210 has HBM headroom, CPU overlap contends for DRAM bandwidth (unmeasured).

## Principles
See dive.yaml (concurrent compactor on shared prefix + next-k validation: M; constrained one-integer judge: S).

## Adversarial
Anonymous artifact; no independent replication; README numbers (+8.8 pp, -39.7%) restate the paper, no variance. Prior dive's concern stands.

## Actionables
A1 task: llama-server judge shim (TOC-CMP-3g). A2 task: run repo vs llama-server api_base on a SWE-bench Verified subset (TOC-CMP-4). A3 decline: BrowseComp (not bundled).

## Dive-surfaced
mini-swe-agent upstream: decline (known, MIT).

artifact audit: clean
