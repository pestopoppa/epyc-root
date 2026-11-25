# RSL-R5 planning-context canary (2026-11-24)

Evidence for boxes RSL-R2 (INBOX-AUTOMATION), RSL-R5 (WIRED + BELIEF) and VB-AK-BW-CENSUS-WIRE.
No compute, no inference: a copy of the live census, a scratch store, a scratch journal. The live
census and journal were checked byte-unchanged afterwards (`live census/journal unchanged: True`).

## Research commit it ran on

The canary ran 2026-11-24 22:33 UTC from a research worktree carrying the RSL-R5 gap fixes
(planner-only inbox on the GPU path, shape_class derived from the BWS seed), which research
committed as `f491243fd` (22:33:46 UTC) on top of `56ff8846d` (census_inbox, RSL-R2) and
`520824d99` (census_update coverage + family_rank). The worktree HEAD was not recorded in the
run output, so the pin is by commit time and content, not by a captured `rev-parse`. To re-run on
any later research origin/main (all three commits are ancestors of it):
`cd <worktree>/scripts/kernel_rnd/autokernel && nice -n 19 taskset -c 84-87 python3 -s -B canary-r5fix.py <outdir>`.

## Files

| File | What it shows |
|---|---|
| `canary-r5fix.py` | The canary script (copy of the one that ran). Steps a-d below. |
| `canary-output.txt` | Its stdout. [a] census_update.run writes coverage + family_rank, 25 surfaces all carry family, 11 family ranks. [b] census_inbox.sync writes 5 BWS stubs into a scratch inbox beside 25 copied committed seeds (RSL-R2: stubs installed). [c-cpu]/[c-gpu] the assembled planner_only context contains BWS ids (5 each) and the family-rank block. [d] a cand.json carries `shape_class`; the build and op-perf stages run on it (rc 0). |
| `context-cpu.txt`, `context-gpu.txt` | The full rendered planner_only context for the CPU and GPU lanes (about 216 KB each), untrimmed. Search for `BWS-` to find the census-derived seeds, and `Family rank` for the family block. |
| `cand.json` | Candidate record derived from BWS-27B-DF2-GPU-LM-HEAD-248320X5120: `shape_class = {op_family: MUL_MAT, dims: {k: [5120], m: [248320]}}`. |

## Size

447 KB total, under the 2 MB limit. Nothing was trimmed: the two context files are kept whole so the
BWS ids and the family-rank block can be checked in place.

## Limits (what this canary does not show)

- `[c-fullloop]` is STATIC: `loop/run.py` `_build_context` needs a live run state, so the full-loop
  assembly is cited by line, not executed.
- The op-perf stage verdict is `FUTILITY_SCREEN_ONLY_NO_KEEP`: it proves the candidate reaches the
  stage with a shape_class, not that op-perf can decide (see audit N1/N2/N3).
- Script paths in `canary-output.txt` point at the original scratchpad; the content is what is cited.
