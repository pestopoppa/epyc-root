# GPU-ZOS-2.3 atomic r5 — accepted preparation capsule (2026-10-31)

Publication: `codex-ni-gpu-zos23-c5-concurrent-r5-20261031`, published 2026-10-31T08:01:51.708231Z. Exact READY manifest SHA-256 `61af3a542f136d7d31b4d401f9a3366b051eace480ba387f69f0b1224880d627`; exact row SHA-256 `074dcfc0cb8802e177b1eb450dfe265b1ecebd25d1a44c24c0cbc8e1f2f0e5c7`. Publication receipt included as `READY-PUBLISHED.json`.

## Diagnostic scope and findings

- Original independent-chat A/A was 24/24 mismatch. The conditional serial correctness tier passed, but that does not permit reuse of old timing.
- Slot-pinned/barrier independent chat remained 4/4 mismatched. Atomic native prompt-array enqueue with exact server-rendered token arrays/settings matched 4/4 across two fresh C5 loads at 256 tokens. This changes entry transport; it does not satisfy or close the original independent-chat adoption gate and gives no causal model-level conclusion.
- The new payload captures fresh paired arms. Original numeric bands are diagnostic references only; no old timings were reused. Analysis is unconditionally `ATOMIC_DIAGNOSTIC`; `ship_authorized=false`, `original_parent_complete=false`, and the original independent-chat parent stays open.
- Feasibility estimate was 5531.8 s against an 8400 s window. Final normal smoke completed in 77.2041 s; actual full A1 cutoff at 75 s returned 75/partial at 76.9383 s and server/KFD drain was confirmed. Validator, grant admission, actual PID, dual-output, ready-to-armed and dead-PID refusal controls passed. A failed first pilot accidentally folded q3/empty grant state; it is retained. Final controls used proper R7 without folding and GPU-only.
- No production, kernel store, source tree, or build was modified. The accepted packet is diagnostic preparation only; no deployment or adoption.

## Source evidence and custody

Full records remain at `/mnt/raid0/llm/tmp/codex-ni-zos23-concurrent-successor-20261031/`. Retention reported no missing referenced or actual scratch files; five future paths are explicitly tracked. `SOURCES.sha256` records the exact manifest/row and selected raw proof inputs. Binaries and large wave/result records are not copied.

Files: `READY.json` and `READY.row.md` are exact staged/published payload bytes. `READY-PUBLISHED.json` records the publication receipt; `DECISION-AUDIT.md` preserves the original §9 boundary. This capsule summarizes and points to native evidence; it does not replace the source records.
