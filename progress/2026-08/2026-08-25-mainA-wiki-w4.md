# 2026-08-25 — mainA — wiki compile sweep w4 (kernel pages)

## Task

Wrap-up wiki sweep, worker w4. Pages owned: `wiki/hardware-optimization.md`,
`wiki/kv-cache.md`, `wiki/quantization.md`, `wiki/speculative-decoding.md`,
`wiki/ssm-hybrid.md`, `wiki/memory-augmented.md`. Prepare exact markdown in
`/tmp/wiki-w4.md`; the main thread applies. No wiki edits, no commits.

## Method

Followed the project-wiki Operation 3 contract (SKILL.md): read all six pages fully
(hardware-optimization 3672 lines, kv-cache 748, quantization 611, speculative-decoding 1495,
ssm-hybrid 537, memory-augmented 532), then read every drifted source and diffed against
each page's "Last compiled" date. Where the page's own newest sections cited the source with
locators, the source was treated as compiled.

## Outcome

- **5 of 6 pages: no new sections.** The 2026-08-23 evening/wave-2 sweeps on
  hardware-optimization, kv-cache, quantization, speculative-decoding and ssm-hybrid already
  compile everything the drifted sources contain through 2026-08-23; hardware-optimization
  additionally carries a 2026-08-25 NUMA section. Verified source-by-source (§3 of
  /tmp/wiki-w4.md) with the specific compiled section named for each.
- **ssm-hybrid.md: correction proposed, no new section.** The live (undated) Summary, Key
  Findings, Actionable and Open Questions still carry the pre-retraction Log-Linear GDN
  "4–10× smaller state" claim, contradicting the page's own 2026-08-12 RETRACTED section
  (measured ≈15× larger vs the released checkpoint). Surgical replacements prepared that
  point at the retraction and the 2026-08-22/23 additions.
- **memory-augmented.md: one new section.** Its Last compiled (2026-08-08) predates the
  RAO/ReDel substrate spike's episodic-store content: the 5-sub-decision labelling axis
  (landed 2026-05-19, column/index/backfill + 29 tests, **zero producers** per the 2026-08-03
  audit) and the SkyRL rollout-tree accounting design (scoped 2026-07-29, independent review
  required, no code change). Header update + full section + page-level source entries
  prepared, ≥3 source references.

## Excluded (deliberately)

halo-rlm-trace-loop-integration.md (predates compile; compiled on Agent Architecture);
RAO/RLM cluster depth-gate content (compiled as Routing Intelligence N17); large-MoE EP
ledger details and Kimi addendum (compiled on moe-optimization/local-inference);
repl-turn-efficiency ledger (context-management/agent-architecture).

## Deliverables

- `/tmp/wiki-w4.md` — full prepared markdown (headers + new section + corrections + per-page
  no-change evidence).
- `logs/agent_audit-mainA.log` — task start/end entries.

## Compliance

No file under `/workspace/wiki/` touched; no commits; `wiki/agent-architecture.md` and
`wiki/knowledge-management.md` untouched.
