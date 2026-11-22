# nanocode intake (github.com/nanocodexyz), 2026-11-22

Session `pm-intake-nanocode-20261122`, lane head `27d4d126c` (origin/main at dispatch). Entries
intake-2789 (nanocode), intake-2790 (harnesslang), intake-2791 (nanoeval). The submitted URL is an
organization page with 12 repos. Entries were minted only for the three repos with technique content
EPYC could use. The SDK ports (nanocode-ts, -swift, libnanocode), the demos (durable-cloudflare,
durable-vercel), egress, nds and libkrun are packaging of the same runtime. nanocode-ts was read in
Stage-2b as evidence for intake-2789 and was not minted as a separate entry.

All content below is the dive agents' own words. Quotes are in the intake entries' `claim_anchors`.

## nanocode (intake-2789) @ d489c209
- **Durability:** every model and tool call is journaled. An interrupted nested call gets an
  explicit unknown outcome and is never auto-repeated, so delivery is at-most-once, not exactly-once.
- **Code Mode:**
  - Cells run in a QuickJS worker pool, one fresh context per cell, with no fs, net or console.
  - There is a per-tool call cap with a structured, non-retryable `call_limit` refusal.
  - Cell output is cut in the middle, with a token-count marker where the cut is.
  - The exec prompt comes in a compact and a full variant.
  - A first-line `// @exec:` pragma sets the cell's budget.
- **Custom endpoint:** the endpoint is set by `NANOCODE_OPENAI_BASE_URL`, at
  `bin/nanocode/src/custom_endpoint.rs:4-5`. It speaks the OpenAI Responses API only. There is also
  an Anthropic base-URL variable.
- **TOOLS_MARK** is named in the harnesslang docs but is NOT a symbol in nanocode.

## harnesslang (intake-2790) @ f6b132b
- **Effect classes:** tools are none, idempotent or external. The result of an external effect is
  `maybe<T>`, where unknown is one of the cases. Recovery never re-dispatches an external call that
  was left open.
- **Proofs:**
  - What is proved: durable-before-external, finish-once, worst case. The proofs are over a model of
    each target's lowering.
  - What is assumed: the target models and the generated code.
  - Supporting checks: a seeded fault simulator with 12 planted mutations.
  - Platform limits are marked unverified.
- **Code mode replay:** replay checks each step for divergence with `same_step`, and on a mismatch
  ends the cell as unknown.
- **EPYC gap (grep of epyc-orchestrator `src/`):**
  - `tool_registry.py:88-149` has a SideEffect enum, used for approval only.
  - There is no retry-safety axis and no unknown outcome on crash replay.

## nanoeval (intake-2791) @ c2a11dd
- **Outcomes:** each attempt is typed passed, failed or errored, and errored is excluded from pass
  rates.
- **Eval versions** are pinned by digest, and runners claim work with leases.
- **Regression tests:**
  - Per task: a one-sided Fisher exact test.
  - The verdict: an exact test stratified by task, so a single task that is lost is not a
    regression.
- **Harbor:** tasks come in as Harbor and runs go out as Harbor jobs with ATIF-v1.7 trajectories.
- **unsound.json** lists 7 TB2.1 tasks.
- **Installed agents** honor `ANTHROPIC_BASE_URL` and `OPENAI_BASE_URL`.

## Stage-2b wave 1
- **nanocode.xyz/experiments:** the site publishes no Code Mode vs direct-tool numbers. It says it
  withdrew its earlier comparisons for lack of public run records. Its only measured page,
  harness-for-swarms, uses fixed local replies, not models. Nothing on the site is independent.
- **nanocode-ts @ 97df28ca:**
  - It runs in Node 22 or newer, outside Workers.
  - A free-form `endpoint` is applied as the API base URL.
  - The Anthropic `/v1/messages` path is the likely route to llama-server.
  - DECISIONS.md L72 (2026-11-15) is self-reported and unpublished, with no n given. It says direct
    tools beat Code Mode by 6.4 points on their Codex pair in TB2.1, and that a
    `claude_orchestration` switch was added. Treat this as a hypothesis only, not evidence.
- **TB2.1 upstream tracker:**
  - Issue 233 confirms qemu-startup and qemu-alpine-ssh are unsound (verifier apt 404).
  - Issue 240 confirms build-cython-ext is unsound (the reference solution scores 0).
  - PR 247 covers protein-assembly (oracle 0, one-line fix).
  - mcmc-sampling-stan, torch-tensor-parallelism and crack-7z-hash were not found in these items.

Wave cap: one Stage-2b wave was run. Every remaining surfaced source was either the already-dived
nanocode repo at a newer pin, a docs page that restates it, or tempolang, whose URL was not found.
Those were declined and recorded in the entries' `dive_corrections`.

Artifact audit: scratch lives in `/mnt/raid0/llm/tmp/dive-nanocode/`. There are no figures and
nothing in the repo besides this file and the index entries. Result: clean.
