# EXP01 official native capture and planner replay

Row `vidya-exp01-proxy-official-native-20261118-r2` completed with allocator
rc=0 at 15:59:16 UTC on 2026-11-18, on CPUs 72–95 with 24 native threads. The
official writer run ID is `324f2a402186442f9efc21f4e65624eb`. Strict replay verified
65 original units across one validity record, 12 independent bench launches,
four scheduled operational looks, and 48 quality launches covering 24 paired
items on Q4_K_M and IQ4_KT.

The [native archive](native-official.tar.gz) preserves 234 original members,
including launch output, source and input identities, fixed items, writer
terminal bytes, and allocator completion receipts. The original grant file had
cycled out by packaging time. The packager restored its exact bytes from the
writer's `RUN.grant.raw` and verified them against the original grant identity.
The [binding](official-completion-binding.json) records that provenance. The
[raw results](results.jsonl) have SHA-256
`1331643fca75e0287ad76ad2a56e985a7c38ddff666955b5d07f512cf740e728`.

The strict adapter projected eight verified `Judged/Located` observations, one
pp512 and one tg128 observation per CPU arm, each with three scored launches.
Ingestion emitted 24 frames in an isolated ledger with zero refusals. All four
matching CPU scopes reached `AgentPlanner.propose`, each with its own two
observations. Each proposal receipt accepted both declared claims, with zero
rejections. All four same-model GPU targets and the unrelated CPU target
returned zero claims. The prompts also rendered stale, scope-blocked history
from a read-only campaign store. The canary intercepted the planner before
backend execution. [Canary receipt](receipt.json) ·
[Rendered context](planner-context.txt) · [Actual planner receipts](planner-receipts.jsonl).

Applicability is limited to the pinned recovered CPU proxy inputs and reference
instrument `c04881fc0f31dae5f8ec59c1d683889f0c9dfa11`. The operational looks and
fixed quality slice are exploratory. The projected observations carry no
protocol citation and supply no decision-gating warrant. The canary receipt's
`original_official_r3_pre_hook` field describes the historical r3 run. This
packet contains the new instrumented official R2 run.

To replay the portable archive, use this directory as `--filing` with
`scripts/vidya/canary/exp01_context.py`. The reader and campaign paths are in
the canary receipt. Supply a fresh scratch directory under
`/mnt/raid0/llm/tmp`.
