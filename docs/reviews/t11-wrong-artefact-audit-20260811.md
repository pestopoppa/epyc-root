# T11 — wrong-artefact audit across every serving role

**Author** `mainA`, 2026-08-11. **Row** `handoffs/active/numa-placement-defect-20260730.md` T11.
**Method** resolve each role's GGUF through the live registry chain
(`orchestration/model_registry_full.yaml` → `roles[<role>].model.path`, hot-resident set from
`model_registry.yaml → process_layout.hot_resident`), then diff against every `.gguf` quoted on a
role line in `handoffs/active/*.md`. Zero inference; pure registry resolution.

## Live resolution — the 11 hot-resident roles

| role | serves |
|---|---|
| `frontdoor` | `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` |
| `worker_summarize` | `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` |
| `architect_general` | `Qwen3.6-27B-MTP-Q8_0.gguf` |
| `coder_escalation` | `Qwen3.6-27B-MTP-Q8_0.gguf` |
| `architect_critic` | `Qwen3.5-122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` |
| `worker_general` | `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` |
| `worker_math` | `Qwen2.5-Math-7B-Instruct-Q4_K_M.gguf` |
| `toolrunner` | `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf` |
| `ingest_long_context` | `Qwen3-Next-80B-A3B-Instruct-Q4_K_M.gguf` |
| `worker_vision` | `Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf` |
| `vision_escalation` | `Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf` |

171 of 180 registry roles resolve to a GGUF; the 9 that do not are non-local backends and
placeholders.

## Result: one NEW instance of the wrong-artefact class

**`handoffs/active/rao-redel-substrate-spike.md:120`** records the ReDel substrate spike running
against `worker_general` and states it was serving
`/mnt/raid0/llm/models/gemma-4-26B-A4B-it-Q4_K_M.gguf`. **`worker_general` serves
`gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf`.** Both files exist on disk and are nearly the same size —
`16,796,010,720` (Apr 4) versus `16,796,016,544` (Jun 25), a difference of 5,824 bytes — which is
precisely why this class survives a casual read: the names differ by one token and the sizes differ
by less than a page per gigabyte.

**The same line carries a second defect.** It says the model was served *"via ik_llama.cpp PR #1744
MTP"*. Per `CLAUDE.md`, **ik_llama.cpp is fully deprecated as a serving path** — the tree on disk is
a reference/measurement instrument only. So the spike's observations came off both a non-production
artefact and a non-production kernel.

This is the **third** instance of the class, after the IQ2_M placement error and the
`modelref_results.txt` case named in the row itself. That the check keeps finding more is the
argument for making it mechanical rather than periodic.

## False-positive classes, recorded so the next audit does not re-chase them

The raw diff reported 15 hits on hot-resident roles. Twelve are not defects, in two families:

1. **Drafter GGUFs on a target-model line.** `gpu-drafter-mi200-investigation.md` quotes
   `Qwen3.5-0.8B-Q8_0.frontdoor-specials.gguf` and `…frontdoor-mtp-specials.gguf` on lines naming
   `frontdoor`. Those are the *draft* models for that role, not competing target resolutions — a
   speculative-decoding role legitimately names two GGUFs.
2. **Multi-role lines.** `gpu-cot-scaffold-sidecar.md:334` names `frontdoor` and `coder_escalation`
   in one sentence alongside a third role's GGUF, so a line-scoped matcher attributes it to both.

The remaining hit, `numa-placement-defect-20260730.md:888`, is the T11 row's own prose describing the
already-known `modelref_results.txt` instance. Expected, not new.

**Implication for automating this:** a line-scoped role↔GGUF matcher has a false-positive rate near
80% on this corpus. Any mechanical version needs to (a) exclude `mmproj-*` and known drafter
artefacts, and (b) attribute to a single role per line or refuse the line. Reporting raw matches
would train readers to ignore it — the failure mode that makes a check worse than none.

## Disposition

- The `rao-redel-substrate-spike.md` finding is **routed to that handoff's owner, not edited here**:
  it is a historical spike record, and per `MEASUREMENT.md` such records are appended to, never
  rewritten. What it needs is a provenance note, not a correction of its numbers.
- No other open handoff misquotes a hot-resident role's serving artefact.
