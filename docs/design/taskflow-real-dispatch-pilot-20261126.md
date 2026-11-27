# A3B real-task dispatch pilot — 2026-11-26

> Follow-up evidence: [November 27 full-tools C22 revalidation and task comparison](../reports/a3b-full-tools-canary-20261127.md). That study qualifies the replacement harness and evaluates independent execution, deterministic feedback, paid guidance and main-only effort. The pilot figures below retain their original restricted-harness scope.

- **A3B-REAL-DISPATCH-PILOT — REPAIRS_VALIDATED_CANDIDATE_ONLY.** Six bounded tasks are complete and their reviewed outputs are published. No initial attempt closed a task unchanged. One corrected A3B test was accepted with an identical functional AST; three drafts needed human repairs and two tasks were completed independently. Source and test-intent errors were observed under a restricted, changing harness; they do not establish an intrinsic model ceiling. Historical interrupted/resumed outcomes retain their specific harness qualifications. Automated reviewer acceptance remains advisory.

## Harness-scope correction — 2026-11-26

The prior pilot did **not** provide the best available OpenCode-derived harness. Its custom configuration exposed seven direct tools, disabled execution through Code Mode and other useful capabilities, imposed read/turn restrictions, and retained a stock instruction referring to `tools.opencode.session_move` without exposing the required `execute` tool. A model-free wire audit of the installed, published OpenCode 2.2.5 executable instead observes twelve direct tools: edit, glob, grep, question, read, shell, skill, subagent, webfetch, websearch, write and execute. The installed executable SHA-256 is `8d060e1d2fbb9bb44cf09ae6ed1f3f6a7cff070b5227e2f90970132b23a92050`.

The published outcomes and token records remain historical evidence for that restricted configuration. They cannot establish whether these tasks require a stronger model after a fully repaired, useful harness is supplied. Software-unit checks and offline reasoning-template controls also did not prove native end-to-end qualification. Real-task comparisons are held until the replacement harness passes model-free and native tool, budget, isolation and continuity checks. The target is a reliable OpenCode-derived configuration, with deterministic error feedback and adequate budgets, rather than stock configuration purity.

Audit receipts: `artifacts/analysis/taskflow-real-pilot-20261126/stock-structural.json`; full historical wire references and current qualification work remain KEEP-retained under `/mnt/raid0/llm/tmp/ws58-a3b-revalidate-20261126/` and `/mnt/raid0/llm/tmp/ws58-a3b-frozen-revalidation-20261126/`. No new model-quality result is claimed by this correction.

## Scope and serving identity

This follows the [completed canary](taskflow-stage1-canary-findings.md), rather than replacing its enrolled workload or verdict. The pilot used fresh, still-needed documentation/design and constrained-test briefs, exclusive task claims, pinned inputs, trusted acceptance checks and independent main review before landing. Existing completed work was reused: GREP-HISTORY's four tests and DS41-W-44's 47 tests passed and their stale backlog rows were reconciled without duplicate model implementation runs.

Both servers used **C22 composite**, source `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, version 10748, and Qwen3.6-35B-A3B-MTP-Q8_0. CPU and GPU each offered four slots with 131072 context per slot. CPU serving used the whole host and overlapped GPU control CPUs as requested. Thinking was enabled for GPU worker tasks and disabled for CPU work. Retained forwarded requests and nonempty assistant reasoning fields verify actual thinking, beyond the launch configuration. Review calls were nonthinking.

The pilot has **six logical tasks, 17 scheduling attempts and 252 request records: 67 CPU and 185 GPU**. One request was a native wire control. Forty records belong to harness-affected attempts; that is an attempt classification, not forty individual transport failures. This is diagnostic serving evidence under different workloads and changing overlap conditions, not a CPU/GPU benchmark or a new model-ranking experiment.

## Independent outcomes

| Task | Native worker mode | Published outcome |
|---|---|---|
| PAW-5 | GPU thinking | Model correction retained a prerequisite error. Main repaired status/citations and filed one coherent shadow-classifier proposal. Root `ad6ab8638c6d`. |
| NARIQ-LIBTRELLIS-MAP-1 | CPU nonthinking, then GPU thinking | Delivered drafts conflated memory spaces, formats and coverage and retained incorrect MFMA/LDS statements. Independently prepared replacement design: research `9a4e7dd4b433`. No kernel or device-qualification claim. |
| DS41-W-75 | GPU thinking | Stray helper correctly rejected. Main excluded it and repaired the seed disposition note. Root `ad6ab8638c6d`. |
| PFXC-A3 | CPU nonthinking | Model correction repaired arithmetic/geometry errors; main repaired extraction and source attribution. Research `8b6bc70f2242`; exact extractor reproduces all 41 historical values and recipe bytes are unchanged. |
| DS41-W-66 | GPU thinking | Original worker made no edit in 30 turns. The guided attempt was interrupted by a shortened wall envelope and resumed with older reasoning omitted by the template default. Its combined no-edit outcome remains confounded. Main repaired the actual receipt fixture; two independent integration checks pass. Research `ae08f0a58a77`. |
| UTM-B2-VERBATIM-WITH-COMPACTION | GPU thinking | Initial test forced compaction and bypassed required behavior. Corrected worker test passes 62 tests and detects five planted regressions. Formatting/comment cleanup preserves its exact AST. Orchestrator `af947afe843b`. |

The [main audit](../../artifacts/analysis/taskflow-real-pilot-20261126/audit.json) binds full publication commits, dispositions, raw performance hashes and all 17 attempt identities. Raw Taskflow `verified` states are preserved separately from these independent outcomes.

## Observed harness repairs

- **Pinned packaging and provenance:** archive the full pinned scripts tree, preflight the real packet path, and bind immutable loaded-source manifests before model work. Custom proxy plumbing that failed the real wire path was replaced with the proven proxy and checked through OpenCode.
- **Reference delivery:** canonical commit `0a5f725a2ff0` validates and hashes external inputs before creating a lane, copies them read-only, protects them from edits, and verifies them before and after acceptance tests. Symlink cleanup no longer chmods through a replaced reference.
- **Truthful command recovery:** the same commit suggests only exact configured commands and runners, preserves quoted whitespace, and distinguishes cwd-relative file paths from an explicitly approved absolute runner. Real OpenCode replay recovered from the observed denial without wider permissions.
- **Output and wall budgets:** the row driver binds actual OpenCode and proxy output ceilings; a 2048-token document-write failure received a bounded 8192-token recovery. Approved wall envelopes survive baseline budget calculations and still respect resource deadlines. The earlier 660-second interruption remains recorded rather than attributed solely to the model.
- **Trusted checks:** versioned controls repair observed PAW heading/provenance false rejections and a PFXC multi-budget sentence false rejection. Stronger source checks reject the NARIQ hallucinations. The VERBATIM oracle now tests normal compaction, the actual session writer, ownership and both existing registration/conflict guards. Old graders and outputs remain available.
- **Resume continuity:** ordinary tool continuation already retained reasoning. A same-task OpenCode resume appended a new user turn, causing the default template to omit earlier reasoning. The post-run repair opts approved same-task thinking resumes into preservation and records that policy in the manifest. Five wire cases, three provenance cases and offline rendering of the actual GGUF template pass: PAW 0/8 to 8/8 and W66 0/22 to 22/22 prior reasoning entries. This repair used no new native inference and does not change historical model outcomes.
- **Reporting:** aggregate and per-stream views now include all observed requests, with harness-affected requests and controls identified separately. Missing native timings and the unreported reasoning-token breakdown remain unknown; reported zero reasoning tokens are not interpreted as absence of thinking.

The canonical Taskflow suite passed **239 tests**; the final policy subset passed **79**. The orchestrator's required `make gates` passed after two pre-existing shell-format discrepancies were normalized; minified shell output is byte-identical before and after. The reviewed test also passed Ruff checks. These software controls establish the repairs, not model capability or a new performance warrant.

## Performance, retention and cleanup

The [reconciled thinking-token audit](../../artifacts/analysis/taskflow-real-pilot-20261126/token-audit/REPORT.md) records 91,108 generated tokens across 179 thinking-worker requests, including reasoning, answers and tool-call text. A reasoning-only split is unavailable. The earlier paired CPU audit accepted 3/5 in each mode; its thinking arm generated 40,322 tokens versus 27,207 without thinking. Different caps and budgets prevent attributing those cost or elapsed-time differences solely to the switch. The pilot and earlier C22 runs likewise establish no clean causal quality advantage; the planned matched replays address that question.

[Performance tables](/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/runtime/PERFORMANCE.md) and [complete JSON](/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/runtime/PERFORMANCE.json) retain per-task and per-stream latency, upstream and delivered TTFT, native prefill/decode speeds, approximate aggregate phase speeds, token/cache/MTP totals, resource samples and failure details. Aggregates use estimated active intervals; CPU OpenMP spinning is distinguished from useful inference. CPU was quiesced after its last task, and later GPU samples retain that changed condition.

The [source-and-evidence archive](/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/runtime/reproducibility/taskflow-a3b-pilot-20261126T161856Z.tar.gz) has SHA-256 `3b63f1a91fbe74ec0bd1c9d6830f006f8e3d2ff265c570506096b981b2961cdb`. It contains immutable native snapshots, controls, pinned inputs, raw patches and reports. The entire pilot root is KEEP-leased through 2027-01-25 16:23:19 UTC. The [cleanup receipt](/mnt/raid0/llm/tmp/ws58-a3b-pilot-20261126/runtime/FINAL-CLEANUP.json) verifies owned servers/workers/controllers exited, KFD emptied and compute claims released.

The global dispatcher stayed under its standing hold; its legacy coordinator relay was absent and the bounded pilot used direct owner claims. The parent TASKFLOW-STAGE1 dated one-week comparison remains a separate open task. This heterogeneous pilot supplies no replacement verdict for that comparison or for a paired 35B/27B experiment.

Next: codex-a3b-pilot qualifies the repaired OpenCode-derived harness before matched task replays and measured guidance versus main-only comparisons.
