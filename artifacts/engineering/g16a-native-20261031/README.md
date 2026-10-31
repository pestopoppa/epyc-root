# G16a native completion - MAIN accepted, scoped

The original diagnostic completed under actual R7 gpu-quiet exclusive with host affinity184-185, no CPU-quarter claim and no idle GPU lock. Exact candidate af90102c7c3659c78b4e4c87698e258525c77000 is v10 ffc1bac82 plus the original two-file C3 G16a patch. Native source/image custody is in SOURCE-HANDOFF.json, PROVENANCE.json and IMAGE-SHA256SUMS. All original records are preserved; this directory copies the raw eight-case logs and receipts for filing.

| T | Sequences | Exact raw case | Chunk trace | Live KFD samples | Post-dispatch samples |
|---|---|---|---|---|---|
| 64 | 1 | 1/1 OK | recurrent control | 2 | n/a |
| 256 | 1 | 1/1 OK | recurrent control | 2 | n/a |
| 2048 | 1 | 1/1 OK | recurrent control | 2 | n/a |
| 4096 | 1 | 1/1 OK | recurrent control | 2 | n/a |
| 8192 | 1 | 1/1 OK | recurrent control | 2 | n/a |
| 2048 | 2 | 1/1 OK | 512 / floor312 | 7 | 5 |
| 4096 | 2 | 1/1 OK | 512 / floor312 | 12 | 10 |
| 8192 | 2 | 1/1 OK | 512 / floor312 | 17 | 15 |

Each raw case contains exactly one matching supported GATED_DELTA_NET(...): OK,1/1 tests passed and Backend ROCm0: OK. All three long two-sequence stderr logs contain their own exact chunked dispatch. The pinned test subclass has no error/tolerance override: inherited err() calls nmse(), max_err(backend) calls max_nmse_err(backend), and ROCm retains1e-7. The runtime comparison uses that tolerance and fails above it. The raw logs do not expose numerical NMSE magnitudes; no such value or deterministic seed is reconstructed.

Every case's live process maps identify the exact HIP image SHA2c944080746d671414d0cf80fa17e60aca3082e7706a26a973751395d7eb2b56. All46 retained residency samples bind the same PID/birth to positive own-process KFD VRAM while it is live; the three traced cases have post-dispatch samples. Total window16.343459523s, partial=false, rc0 and zero live descendants. Watcher/public/native terminals all completed and no watcher remains.

MAIN accepts G16a completion only. G16 greedy A/B, keep-rs, speed and champion integration/promotion are not cleared. No dispatch-proven numerical miss occurred, so G16b is not triggered. No duplicate READY or rerun is warranted. Source/build/native packet is retained with KEEP through greedy A/B and coordinated integration. C3 owns active champion lanes; integration must preserve its existing opt-in gate and validate the full combined candidate, with no production/store modification implied by this result.

This finding is suitable for committed-conclusion OBSERVATION filing ([belief: cc]); no retrospective measurement ClaimTuple is invented. Prospective write-side projection is separately requested in BELIEF-WIRING-DRAFT.md.
