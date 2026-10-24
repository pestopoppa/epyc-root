# 2026-10-24 — cold_vision_failfast

## S-20 cold vision refusal source fix

- Root cause in fresh `epyc-orchestrator` source: `_handle_vision_request` awaited optional OCR before trying the selected VL server. In explicit server-only mode, a cold endpoint therefore did not fail until after OCR; the two configured vision roles can also resolve to the same server URL.
- Implemented a 250 ms shared-deadline TCP-connect preflight only for explicit `ORCHESTRATOR_VISION_VL_BACKEND=server`. It uses the selected endpoints (respecting `force_server`), deduplicates aliases, and refuses through the existing `All vision paths failed` error before OCR, structured analysis, or legacy HTTP fallback when none accepts a connection. Healthy server-only requests retain OCR and VL inference; other backend modes do not preflight.
- Published the two source files as orchestrator commit `846783d109ea014fa3fdcc6c02ac13b49d3bf592` and promoted it to `main` as `84f6f6f15f713d21098dbad2b153d32f8cc13624`. The promoted diff changes only `src/api/routes/chat_vision.py` and `tests/unit/test_chat_vision.py`; source blobs match tested candidate `5fc97a54c65d1022ae780f74fd34476e2501c623`.
- Official focused validation used the project Python 3.11 environment and the immutable launcher pinned to `5fc97a54`. Result: 16 passed, 40 deselected, one warning, 1.31 s; JUnit XML gate passed with all seven required new test IDs and no failures, errors, or skips. Evidence: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/s20-coldvision/test.log`, `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/s20-coldvision/status.json`, and `/mnt/raid0/llm/tmp/codex-ni-20261024-coldvision/runs/s20-coldvision-5fc97a54-20261024T165515Z-64444.xml`.
- The tests use mocked endpoints and assert the source timing bound. The original 27.9 s live observation remains historical; no live API request, server probe, service reload, or model call was made, so no measured live latency reduction is claimed.

## Handoff closure draft for main review

Proposed S-20 checkbox text is in `handoffs/active/multimodal-pipeline.md` in this ROOT docs worktree. This is a draft for the owning main to review and apply. The existing `INF41-S20-SOURCE` text is left unchanged; no domain-index or master-index edits are included.
