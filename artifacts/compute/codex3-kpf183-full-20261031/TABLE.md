| Arm | Case | Route | Prompt | Reply | Child 1 fork/source | Child 2 fork/source | Trunk checkpoints (tokens:pos/pinned) |
|---|---|---|---:|---:|---|---|---|
| champion | raw-holdout-a | /completion | 33 | 8 | unknown; gap unknown | unknown; gap unknown | unknown (field absent) |
| champion | raw-holdout-b | /completion | 38 | 8 | unknown; gap unknown | unknown; gap unknown | unknown (field absent) |
| champion | chat-holdout-a | /v1/chat/completions | 27 | 8 | unknown | unknown | unknown (field absent) |
| champion | chat-holdout-b | /v1/chat/completions | 26 | 8 | unknown | unknown | unknown (field absent) |
| fork-off | raw-holdout-a | /completion | 33 | 8 | unknown; gap unknown | unknown; gap unknown | unknown (field absent) |
| fork-off | raw-holdout-b | /completion | 38 | 8 | unknown; gap unknown | unknown; gap unknown | unknown (field absent) |
| fork-off | chat-holdout-a | /v1/chat/completions | 27 | 8 | unknown | unknown | unknown (field absent) |
| fork-off | chat-holdout-b | /v1/chat/completions | 26 | 8 | unknown | unknown | unknown (field absent) |
| fork-on | raw-holdout-a | /completion | 33 | 8 | 40/end src0; gap 1 | 40/checkpoint src1; gap 1 | 29:28/unpinned, 33:32/pinned |
| fork-on | raw-holdout-b | /completion | 38 | 8 | 45/end src0; gap 1 | 45/checkpoint src1; gap 1 | 34:33/unpinned, 38:37/pinned |
| fork-on | chat-holdout-a | /v1/chat/completions | 27 | 8 | 23/checkpoint src0 | 43/checkpoint src1 | 23:22/unpinned, 27:26/pinned |
| fork-on | chat-holdout-b | /v1/chat/completions | 26 | 8 | 22/checkpoint src0 | 42/checkpoint src1 | 22:21/unpinned, 26:25/pinned |
