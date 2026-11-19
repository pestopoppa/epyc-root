# PRB-T4 isolated CPU preparation pilot

The pilot tests whether a four-core allocator window can capture and cost the baseline, static and token-unit TALE-EP interventions on the frontdoor weight and v10 CPU build. It records whether the TALE answer plus its estimator costs more or less than the paired baseline and static answers. Lower token and wall cost is favorable. One item per suite provides no estimate of sampling error, suite effect, confidence interval or adoption decision.

## Questions and interventions

Select the first registered ID for each of math, olympiadbench, mmlu_pro and livecodebench from the original 1,600-ID seed-42 SAMPLE.json, SHA-256 0eacc3d95f0a69072ec2f6f5efdf936ad254f7ba6c8b50305962df7bbe51743f. Before inference, stream and verify the original refreshed question pool against SHA-256 3c3b498a483f4131bbe397fdd316f6833f0d169db709d1539489bc46941bfb6c and retain the exact four rows. The suite order comes from the PRB predeclaration.

| Suite | Registered ID | Source scorer |
|---|---|---|
| math | gsm8k_01029 | Exact match with the registered extraction rule |
| olympiadbench | olympiadbench_algebra_2501 | Registered gold substring, sensitive to formatting |
| mmlu_pro | mmlu_pro_chemistry_03738 | Registered ten-choice scorer |
| livecodebench | leetcode_flip-game | Registered tests in the existing confined scorer |

The pinned PRB-T4 research driver supplies the prompt text, static preset by suite with its general fallback, estimator parser and token-unit TALE answer suffix. Send one baseline answer, one static answer, one estimator and one TALE answer per question, in that order. The estimator is capped at 32 generated tokens. Its parsed β is clamped to [10, 4096] tokens, with fallback 100 on unparseable text. The separate [10, 500] clamp belongs to the legacy word-unit prompt. β is an instruction in the prompt. The HTTP completion limit is 512 tokens for every answer arm, an instrument bound below the full campaign’s 8,192.

Both the estimator and each answer record native prompt, completion and total tokens plus measured request wall time. The TALE answer has answer-only costs, estimator-inclusive costs and estimator-inclusive deltas against baseline. The report retains completion-only deltas alongside total-token deltas for historical comparison. Native length results are recorded and sent to the source scorer when available. Empty or unavailable scoring is UNKNOWN. LiveCodeBench uses the retained cgroup/Landlock/seccomp scorer. If the confined scorer cannot establish a verdict, the capture retains UNKNOWN and still reports valid native token and wall costs. Generated code requires confinement.

## Serving custody and stop conditions

Use the DCP-12 prior weight receipt for Qwen3.6-35B-A3B-MTP-Q8_0.gguf. File identity is checked before and after every native request. The instrument uses the isolated DCP-12 CPU launch shape with four granted physical cores, private loopback port 19392, split KV and CPU-only v10 ffc1bac82 build 10303. It checks the binary, loaded libraries, template, models, props, slots, affinity and captured listener PID. Build-manifest and binary digests establish freshness. The raw requests use the pinned registry's frontdoor generation default temperature 0.3, seed 42, Jinja with enable_thinking=false, server reasoning off and prompt caching disabled. Only user messages are sent, matching the benchmark's direct request pattern. Four-core latency describes this isolated shape.

Allocator smoke uses the same launcher and native path with the first frozen baseline control. The predicate requires fresh raw request, HTTP and response bytes with native usage plus linkage, owned server and captured-PID/port teardown. Smoke qualifies the instrument for that one request. The official cap is one attempt at 16 requests and 2,400 seconds of runner wall time, with startup limited to 160 seconds, each answer to 150 seconds and each estimator to 45 seconds. Stop after the last scheduled request or at the first STOP, exhausted grant/deadline, transport, response-schema, serving custody or cleanup failure. Preserve existing files, the first failed cell, and the unsent cells as UNKNOWN. Completion means captured diagnostic coverage with teardown. The full PRB-T4 cohort and its decision rule remain separate.

The native report is the prospective source for the existing TALE measurement adapter. The adapter must bind the immutable cohort and served identity, request and response, native costs, partial outcomes and cleanup before projecting through the existing carrier. The strict reader and planning-context canary belong to VB-PRB-T4-CPU-PILOT-WIRE.
