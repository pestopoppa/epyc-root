# TOC-SP-5 standing corpus gates — 2026-11-18

The 62-file BEP sandbox cohort supports neither an exact served-window occupancy rate nor a spill-follow rate. Each metric is **blocked on the TOC-SP-6 artifact build** as detailed below. The predeclared blocker-recording branch of TOC-SP-5 is complete. This read-only analysis used zero inference. Its scope is the standing cohort and its arm and schema gates.

## Corpus and prompt occupancy

The reader found 62 of 62 trajectories, with zero unparsable files and 384 turns. Every rate uses the fixed 62-trajectory denominator, including any missing or unparsable entries as unknown. All 62 contain `coder_escalation` (366 turns), including three with `architect_coding` (18 turns). The files record no `prompt_tokens` or served `n_ctx` on any turn, and the role-to-served-window mapping is unknown. There are 162 turns with `prompt_chars`, across 26 fully covered trajectories. The other 36 have no character counts. The largest recorded count is 12,649 characters.

Each row reports bounds for the share above **each** strict threshold (0.50, 0.60 and 0.85). The bounds assume the logged count covers the full served prompt and its tokenizer produces at most one token per recorded character. Request wrappers, special tokens and character encoding can invalidate that assumption. The exact shares in every row are UNKNOWN, blocked on the TOC-SP-6 artifact build.

| Logged role | Candidate served-window basis | Conditionally excluded | Remaining unknown | Conditional share bound |
| --- | --- | ---: | ---: | ---: |
| `coder_escalation` | :8070, 65,536 tokens per slot | 26/62 | 36/62 | 0–58.06% |
| `coder_escalation` | :8083, 262,144 tokens per request | 26/62 | 36/62 | 0–58.06% |
| `architect_coding` | :8070, 65,536 tokens per slot | 60/62 | 2/62 | 0–3.23% |
| `architect_coding` | :8083, 262,144 tokens per request | 60/62 | 2/62 | 0–3.23% |

The :8083 request cap sits within a 393,216-token shared pool. The 98,304 figure is historical. For `architect_coding`, 59 trajectories contain no turn with that role label and one has complete character coverage. Role absence alone caps the logged-label share at 3/62 (4.84%) under the stipulated full-cohort denominator, even if all three observed-role traces exceeded 0.60. The gate is below 10% for that logged label in this cohort, while served-role/window attribution remains unverified. The `coder_escalation` interval straddles 10% even under the character assumption. This result does not establish a served-role CF-AB-1 skip.

## Spill follows and repeated actions

The scan found zero recognized spill or truncation-pointer headers in 162 recorded prompt tails and zero matching spill-path references in the recorded model output and extracted code. These are text-scan diagnostics. The prompt-tail field has clipped coverage, and the trace format clips raw output and extracted code. There are zero trajectories carrying a structured spill-follow ledger. Creation, executed dereference, and elision history can therefore be missing from the trace.

| Task | Trajectories, both arms | Trajectories ever executing a spill-path peek or grep |
| --- | ---: | --- |
| t1_create_util | 15 | UNKNOWN |
| t2_add_and_use | 13 | UNKNOWN |
| t3_method_and_caller | 13 | UNKNOWN |
| t4_rename_module | 12 | UNKNOWN |
| t5_bugfix | 9 | UNKNOWN |
| All | 62 | UNKNOWN |

- **Spill-follow rate by task and share of tasks ever dereferencing a spill pointer** are blocked on the TOC-SP-6 artifact build. The distinct-task denominator is five, but the numerator is unknown. The trajectory rollup includes all 62 slots.
- **Spill-size deciles and follows per spill in each decile** are blocked on the TOC-SP-6 artifact build. The spill inventory, sizes and corresponding executed follows are unknown, so there is no established per-decile denominator.
- **Same-path re-reads after an elision** are blocked on the TOC-SP-6 artifact build. The recorded fields cannot join elision events to later executed read actions.
- **Same-command re-runs after an elision** are blocked on the TOC-SP-6 artifact build. The recorded fields cannot join elision events to later executed commands with a stable identity.

The corpus supplies no basis to apply the under-10% `query_memory` stop rule.

## Reproduction and custody

```sh
python3 scripts/analysis/toc_sp5_gate.py /mnt/raid0/llm/epyc-orchestrator/data/bep_sandbox
python3 -m pytest -q tests/analysis/test_toc_sp5_gate.py
```

The reader scans the `*/traces/*.jsonl` cohort, refuses a 63rd file, and limits each read to 64 KiB plus one overflow-detection byte. It emits aggregate metrics and hashes, with no raw trace contents. The manifest hash uses canonical JSON of relative path to file SHA-256, with sorted keys and compact separators.

| Evidence | SHA-256 |
| --- | --- |
| Manifest of the 62 trace files | `387e7d829a5a8cd50f4587c178e68565b4cd719aaedbd277be0d3e31e9d2f405` |
| [Reader](../../scripts/analysis/toc_sp5_gate.py) | `7e939946a50ccd2da188322980d6bda0ebb1dc18ad714248c98bed082ff159f1` |
| [Focused tests](../../tests/analysis/test_toc_sp5_gate.py) | `ac3d1b15e6f5b534d06a37cdc51a1c21640f9abb0f9f1a7ef4c2dc22ee48815e` |
| Captured JSON output | `cf4e1ac836588bd12167e83a782a290bec28b0909bbcf18056f2fb2628da7028` |

The captured JSON, including all 62 per-file hashes, is at `/mnt/raid0/llm/tmp/delegation-context-preassembly/sp5/result.json`. The 62 trajectories support this cohort gate assessment only.
