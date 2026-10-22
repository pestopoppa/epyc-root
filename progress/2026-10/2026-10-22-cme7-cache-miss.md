# 2026-10-22 CME-7 poker smoke: why the prefix-cache gate missed (3c4ca599)

Analysis of recorded artifacts only; no server, no run. Run dir `/mnt/raid0/llm/tmp/cme7-poker-out/run-20261022T131252Z/`
(server `qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4`: np 4, ctx 786432, MTP, `--ctx-checkpoints 8`, `--cache-ram 16384`, kernel build `gpu-20261020-dd3d9721c`).

## Result

`hit_ratio_reusable` 0.7948 (103,933 cached / 130,762 reusable), gate 0.95, raw cached/input 0.7346. 26,829 reusable tokens were re-prefilled.

| cause | tokens | share | kind |
|---|---:|---:|---|
| Schema instruction attached to the OUTGOING last user message only (`system.py` `_outgoing`), so the previous user message changes at its tail | 14,058 | 52.4% | client layout, fixed |
| Previous call's generated tokens counted as reusable (CME-5 rule) but a hybrid server never reuses them | 11,028 | 41.1% | gate accounting |
| Parse-retry rollback (history rewound after a failed reply, 2 calls) | 1,743 | 6.5% | client, see CME-7T |
| Slot misrouting | 0 | 0% | none observed |

Of the 11,028 generated-token bucket, 4,096 are the two 2048-token failed first replies of runs 0 and 1 (they sit in the retry prompt and are counted reusable).

## Evidence

- Cached-token arithmetic: for every one of the 38 steady-state calls, `cached = previous_input - (380..460)`, i.e. exactly one user message (hand text + 637-char schema instruction, about 150 tokens) is re-prefilled; none is lower, so no call lost its whole slot history.
- Server selection (server.log): 55 requests on 4 slots from 8 concurrent clients (3 runs + 5 baseline instances). Early requests are `selected slot by LCP similarity, sim_best = 0.10..0.35` (log lines 42-250, a mix of runs and baselines), later ones 0.73-0.93 with `f_keep` 0.8-0.96 (lines 386-737). Client sends no `id_slot`; no gated call shows the signature of a wrong slot, so pinning would gain 0 tokens here.
- Mechanism (source `tools/server/server-context.cpp` of the frozen tree, lines ~3560-3720 and 3440-3500): for a recurrent model the slot can only resume from a context checkpoint, made at the last user-message start and at prompt end - 4. The LCP of the next prompt ended inside the previous last user message (instruction suffix gone), so the end-4 checkpoint was past the LCP (`cur.pos_max > pos_next` rejects it) and the user-message-start checkpoint was used. Log level was INFO, so no `restored context checkpoint` line exists; this step is inferred from the arithmetic and the source. CME-7S reruns with `-lv 4` to read it directly.
- Early-prompt variance: none. The first user message is identical across runs (457 / 451 tokens); no timestamps, ids or tool lists precede the hand text.
- Template: the Qwen3.6 GGUF template renders a historic assistant turn without its `<think>\n\n</think>\n\n` block that the generation prompt had, so even with the instruction fixed the divergence is at prompt end - 4, which the end-4 checkpoint covers.
- `--ctx-checkpoints 8`, `--cache-ram 16384` and `checkpoint_min_step` 8192 were not limiting at these lengths (max prompt 7.7k).

## Gate and bar

The 0.95 bar is fine. The CME-5 denominator is not reachable on this model: with a perfect layout the recorded data gives about 0.91 (generated tokens are not reusable). Amended before any rerun (dated here and in `cache_hit_report.py`): the gated basis is `prompt_prefix` (reusable = min(input_k, input_k-1)); the CME-5 ratio is still computed and printed. Recorded smoke: 0.868 on the new basis; projected after the layout fix about 0.99.

## Code (research `08ace05fd`, pushed)

- `system.py`: the schema instruction is appended once to the STORED user message; each request is the previous request plus the reply plus the new turn, byte for byte. Test `test_every_request_extends_the_previous_one_exactly` replaces the old test that pinned the buggy layout.
- `cache_hit_report.py`: `--basis {prompt_prefix,cme5}`, `hit_ratio_prompt_prefix`, `missed_split`. 12 tests pass; the recorded traces reproduce the split above.

A rerun is needed to confirm (CME-7S). Proposed re-arm: the same `s5-cme7-poker-smoke` filler through FILLERS.md and a grant, research >= `08ace05fd`, server with `-lv 4`; the old job file is not edited.

## Belief kernel

No adapter exists for `epyc.clbench_cache_hit.v1`. Filed `VB-CLBENCH-CACHE-WIRE` and a prepared README row.
