# Native-v3 row proposals, not READY

| ID | Backend | Actual production scope | D1 terminal result | Qualification first event |
|---|---|---|---|---|
| `codex-ni-inf12-gate2-triton36-v3-20261101` | `transformers-hf-inprocess` | Original MemoryAgentBench full matrix: 22 sources × two arms, 3,671 QA records per arm; three actual QA work units admitted per 1,800-second window, resume until complete | `inf12/outputs/RESULT.json` | Official `eventqa_65536` question (67,283 input tokens), followed in normal fixture by actual `eventqa_full` (258,333 input tokens) |
| `codex-ni-specgram3-llg101-cpu-r3-20261101` | `llama.cpp-in-process` | Original 48 native real-logit component cells + eight greedy prompt pairs + 5,450-call/seven-cell replay; 21,600-second requested window | `specgram3/out/RESULT.json` | First successful script-0 `llama_decode` in the pinned native benchmark |

There is no 18-cell task in the cited original SPEC-GRAM.3 request or its pinned request manifest: both specify **48** component cells. An 18-cell row would drop required work and is not proposed. The 48-cell component rate projects 4,267 seconds; greedy/replay time remains unknown.

`owner-bootstrap-dry.json` checks both exact draft IDs against the uninstalled owner map and pinned v3 verifier using an isolated module substitution; it validates `bound_files` including absolute source manifests and calibrated-rate evidence. The live owner installer reports `ready_to_apply=false` because the P0 qual-v2 link is not installed. Neither manifest is published to READY.
