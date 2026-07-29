# M-2 Path-B TTS Decision: Pinned CLI Interface

**Decision requested:** choose how to resolve the still-open M-2 Path-B
text-to-speech observation for MiniCPM-o/CosyVoice2.

## Context

The read-only feasibility probe reached a terminal result at the exact
`llama.cpp-omni` `feat/web-demo` pin
`5202b7b2f4d11f50b9f996161e7a2f8b8571b890`:
`blocked-by-pinned-interface`. The built `llama-omni-cli` has no text/prompt
argument or output-WAV-path contract. Its `--test <audio-prefix> <n>` consumes
numbered WAV fixtures and writes through its own nested output path, so it
cannot produce the M-2 required deterministic `text -> $RUN/output.wav`
observation. This is not a model-asset, v8, or MI210 serving failure.

The source evidence is
[M2_OMNI_FEASIBILITY_PROBE.md](/mnt/raid0/llm/epyc-inference-research/artifacts/minicpm-o-phase1-v8-20260726/M2_OMNI_FEASIBILITY_PROBE.md).
No option authorizes a production integration, a lineup change, or a claim
that TTS is supported on MI210. Any authorized derivative work starts only
after the current 27B GPU phase boundary and must not delay evidence already
running. A3/A4 confirmation remains separately gated by the clean-CPU boundary.

## Options

### 1. Authorize a minimal detached derivative contract adapter (Recommended)

Authorize a narrowly scoped source change **only** in the independent detached
`/mnt/raid0/llm/llama.cpp-omni-experimental` worktree. Add the smallest
deterministic CLI surface needed to accept exact text and write an explicitly
selected WAV path, then record the resulting full source commit as a new,
immutable derivative pin. Run the M-2 observation only against that derivative;
keep any HIP/MI210 probe separately scoped and explicitly unproven until it is
tested.

| Dimension | Tradeoff |
| --- | --- |
| Scope | A small CLI/API adapter plus a derivative-pinned runner contract; no mainline `llama.cpp`, orchestrator, registry, or production v8 edit. |
| Risk | Medium: the adapter may expose a different decoder path or reveal upstream TTS defects; isolation prevents production contamination. |
| Time | Bounded engineering and review work, then an operator-approved test window; longer than holding but not dependent on upstream timing. |
| Evidence quality | High for the actual M-2 question because the test has deterministic text input and a captured WAV output; it is evidence for the derivative only, not upstream or MI210 support. |
| Reversibility | High: abandon the detached worktree/derivative pin and retain v8 unchanged. |

**Required acceptance boundaries:** preserve the original pin as the parent;
publish the derivative commit SHA and a concise patch rationale before any
measurement; retain the exact input text, output-WAV hash/path, command, and
runtime identity; and fail the run if the output contract cannot be met. A new
derivative pin is mandatory before build or test use.

### 2. Wait for an upstream pin with the required documented interface

Keep M-2 blocked and monitor upstream for a commit that supplies both text
input and an explicit output-WAV contract. Re-run the read-only interface audit
on a newly resolved detached pin before authorizing the test.

| Dimension | Tradeoff |
| --- | --- |
| Scope | No local source change; only a future detached-pin audit and test approval. |
| Risk | Lowest implementation risk; schedule and interface stability depend on upstream. |
| Time | Unbounded. |
| Evidence quality | Highest provenance for upstream behavior, provided the new interface passes the same deterministic-contract audit. |
| Reversibility | Immediate: remain blocked or later choose Option 1. |

### 3. Decline Path-B TTS and close it as unavailable for the current pinned path

Do not adapt the fork and do not substitute fixture-audio response, mainline
OuteTTS, or another TTS implementation as an M-2 result. Record Path-B as
unavailable at this pin and direct any future TTS work to a separately approved
alternative path with its own test plan.

| Dimension | Tradeoff |
| --- | --- |
| Scope | No source or runtime work for this fork. |
| Risk | Lowest operational risk, but loses the opportunity to determine whether built-in CosyVoice2 can eliminate the Qwen3-TTS port. |
| Time | Immediate decision closure; no Path-B evidence is produced. |
| Evidence quality | None for the Path-B quality/latency hypothesis; accurately preserves the pinned-interface finding. |
| Reversibility | High: reopen later through Option 1 or 2 with a new authorization. |

## Recommendation

Choose **Option 1**. The blocker is a narrow, observable contract mismatch,
not missing weights, and a minimal derivative can answer M-2 without touching
the frozen production kernel. The derivative pin and recorded I/O contract
make its evidence auditable while avoiding the invalid substitution of an
audio-fixture response for text-to-speech. This does not authorize HIP/MI210
support, service integration, or production promotion.

## Fail-Closed Default

Without explicit operator selection, M-2 remains **blocked-by-pinned-interface**.
Do not build or alter `llama.cpp-omni`; do not run a substitute TTS experiment;
do not modify frozen `production-consolidated-v8` at
`67a433bf45a8a091d83b4ea0b32ff0735fd51800`; and do not update the model
registry, orchestrator, or lineup. The unchecked M-2 TTS test stays open.

## Resolution (operator, 2026-07-27)

**Selected: Option 1 (minimal detached derivative adapter) + a standing Option-2
upstream watch.** Authorize the smallest deterministic `text -> $RUN/output.wav`
CLI/API surface **only** in the detached `/mnt/raid0/llm/llama.cpp-omni-experimental`
worktree, recorded as a new immutable derivative pin, and run the M-2 observation
against that derivative. In parallel, **monitor `llama.cpp-omni` upstream** for an
official commit that documents both text input and an explicit output-WAV contract;
if one lands, re-audit it and migrate the M-2 observation onto the upstream pin
(Option 2), retiring the local derivative.

The Option-1 acceptance boundaries stand in full: preserve the original pin
(`5202b7b2f4d11f50b9f996161e7a2f8b8571b890`) as parent; publish the derivative
commit SHA + patch rationale before any measurement; retain exact input text,
output-WAV hash/path, command, and runtime identity; fail-closed if the output
contract cannot be met. **Still NOT authorized:** HIP/MI210 TTS support, service
integration, model-registry/orchestrator/lineup change, or any production promotion.

**Execution gate:** per this doc's Context, derivative work starts **only after the
current 27B GPU phase boundary** (the FF/TC np_context_study_v8 grid is live on the
MI210) and must not delay running evidence. The adapter build/audit is CPU-side and
can be prepared without the GPU; the M-2 observation itself queues behind GPU-free.
Owning session for execution: the Codex long-horizon workflow (relay required).

## Immutable Derivative Pin (2026-07-27)

The authorized detached derivative is now pinned at
`c86781a93fa07b396ec3613fb79e7a22ab30d8f8` in
`/mnt/raid0/llm/llama.cpp-omni-experimental`. Its exact ancestry is:

- required upstream parent:
  `5202b7b2f4d11f50b9f996161e7a2f8b8571b890`;
- minimal contract adapter:
  `af555ed6cb3b2a135b43f614a9e03c9df4d77825`;
- audited repair and terminal derivative pin:
  `c86781a93fa07b396ec3613fb79e7a22ab30d8f8`.

Patch rationale: add a strict CPU-only CLI path for exact text input and a
fresh private run directory, then publish exactly `output.wav` by validating
and joining the backend's complete consecutive PCM WAV chunk set. Strict mode
disables fallback/device ambiguity and fails closed on missing prerequisites,
unsafe paths, incomplete output, or publication conflicts. Legacy callers keep
their prior behavior when strict mode is disabled. The run-directory contract
assumes a trusted parent and excludes concurrent mutation by another process
using the same account.

Independent audit identified and the terminal pin fixes three acceptance
blockers: stale completion-marker indices in real retained output, an
unintended legacy CPU-routing change, and umask-dependent run-directory
permissions. The terminal pin also bounds WAV format allocation and moves
run-directory creation after prerequisite preflight.

CPU validation ran under the `q1` region lock against the terminal pin:

- CMake Release build of `llama-omni-cli` and
  `test-omni-tts-run-contract`: passed;
- `test-omni-tts-run-contract`: passed;
- `test-omni-cli-contract`: passed;
- focused CTest result: `2/2` passed, `0` failed.

No M-2 derivative measurement had run when this pin was published. The
observation remains queued behind the FF/TC MI210 grid and must retain its
exact input text, command, runtime identity, output path, and WAV SHA-256.

The standing upstream watch checked `origin/master` at
`74699a53df6ca0f4947ff37066f851532c20b12d`. That revision still lacks a
documented deterministic text-input plus explicit single-output-WAV contract,
so no migration from the local derivative is available yet.
