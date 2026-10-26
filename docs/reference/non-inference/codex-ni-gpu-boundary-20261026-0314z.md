# Codex NI GPU boundary — 2026-10-26 03:14Z snapshot

This record preserves the reviewed boundary from 02:30Z through the 03:14Z receipt readback. It does not merge or change worker-owned handoffs, registration tables, source tables, intake entries, or checkboxes. Later material is labeled with its observation time.

## CME-7T wrapper publication

The explicit candidate system-prompt wrapper was published to the review branch `codex/ni-cme7t-prompt-plumbing-20261026` at commit `6f9799a933741fb0ae2dd267cfa29b39987b6165`; the captured local and remote commit IDs matched. The change is one wrapper file (`scripts/benchmark/run_clbench_epyc_local.sh`, source SHA-256 `a267204bdac72c3faf1e575ec6ec1b38959c92b3b7d02fe3e5840d2830aadfec`). It adds optional direct/file prompt input, mutual exclusion, UTF-8/NUL and overwrite guards, plus prompt and source hash metadata. The publication receipt reports `stage=published-exact-one-wrapper`, `rc=0`, at `2026-10-26T02:56:24Z`; graph impact is `UNKNOWN` and model efficacy remains `OPEN`. This code publication does not show model efficacy or close the parent CME task.

## GAP R6 private synthetic replay

The private combined current9 + EVL10 + GAP quarter replay returned `PASS` for its synthetic HOLD-refusal, owned-child-drain, and affinity proposition using native EVL ended fields. The exact verdict at `/mnt/raid0/llm/tmp/codex-ni-20261026-gap-pool-engine/r6/official-quarter/results/VERDICT.json` records `synthetic=true`, `private_hold_only=true`, `canonical_adoption=false`, quarter `q1`, canonical region `24-47`, and actual/child affinity `24..47`. This is not operational adoption or a production claim.

## GPU correctness rows at 03:14Z

- Matmul row `ni-gpu-pool-matmul-20261026-v1` proposes 571 generated artifact-specific ROCm `MUL_MAT`/`MUL_MAT_ID` cases against the CPU reference, correctness only. The local armed row is `/mnt/raid0/llm/tmp/codex-ni-20261026-gpu-pool-matmul/ROW-ARMED.md`.
- Attention row `ni-gpu-pool-attention-20261026-v1` proposes 1063 generated cases (ROPE 328, SOFT_MAX 207, FLASH_ATTN_EXT 528), correctness only. The local armed row is `/mnt/raid0/llm/tmp/codex-ni-20261026-gpu-pool-attention/ROW-ARMED.md`.
- The device is `mi210_0`; `184-191` are host CPU affinity threads, not GPU IDs. Both rows request 1800 seconds with 1500 seconds minimum, 8 GiB, and a separately reserved q3 envelope.
- Matmul request receipt `3c78219d-ebfd-416a-a04a-c3a52b233cf6` and attention request receipt `ff7c8e8d-7f00-4306-9f26-9114932cdfb2` each report `socket_sent` and pending recipient confirmation. The requests are not owner ACKs, bookings, official canonical grants, or results. Each local own-row grant check is an admission self-test only and does not grant the canonical row.
- MAIN-to-WS58 source-enrollment request `44c5963d` asks for owner application to existing SC18/SC88 before the first GPU grant; it is not a worker-applied source-table change. Neither GPU workload may launch before the enrollment evidence and canonical grant are present.
- Both candidates are non-store binary `c463f601b`; source/build provenance is `UNKNOWN`, and the recreated shim/source mismatch is disclosed. Any result would be binary-specific synthetic correctness only. Production and kernel store were untouched.

## Other research proposals at the boundary

HSF5P source audit was sent; no phase-2 row existed in the 03:14Z snapshot. GNX R2 packet SHA-256 is `c07a5a0194e876dd206a938a1a1c791e1f89574b2bec0c10896381bb0743e678`; the concrete `A ptrace event-admission` proposal was reviewed and sent to WS58 as message `77db43a8`. Seven fake preflight fixtures do not establish native status; native status was unknown and there was no row.

## 03:17Z addendum — elementwise arming approval

MAIN's `MAIN-APPROVED-FINAL-PACKET` receipt approves arming the exact sealed elementwise packet, digest `5a33ba2982e94a427ae16cdea635f905b9d158676412399ef2a87559eafd2b0a`. The local launcher log records official GPU filler8 launcher PID `2258057` up at `2026-10-26T03:17:06Z`. This is an armed poller only: no canonical grant or native result is established here. The proposed device remains `mi210_0`, with `184-191` host CPU affinity threads; the operator reservation is q3. No result claim is made.

## Claim and publication limits

Do not combine fixture controls, fake preflight passes, own-row admission checks, source publication, or private synthetic GAP verdicts into native GPU results or completed-task counts. CME model efficacy remains open; GAP adoption remains false; no native GPU result is claimed. No worker-authored handoff/index/source-table/intake changes, index regeneration, wiki compilation, inference, or main promotion are part of this checkpoint. MAIN’s source row and SC18 child application is owner state recorded in the addendum; this checkpoint changes no owner checkbox. Source receipts are evidence anchors only; no committed-conclusion ingestion or new measurement warrant is claimed.

## 03:14:48Z–03:20Z owner-state addendum

- MAIN independently read ROOT `origin/main` at `26f28d3397009c97a497bce20d6c39fb9eadb5f0` (commit time 03:14:48Z; read back by MAIN during the 03:20 boundary) and confirmed the GPU source-table row plus the SC18 child were applied. The pinned source-table file `scripts/vidya/adapters/README.md` has SHA-256 `73f48f4157c0d91233c8c0e85aa2948738b6be49eef191b27f7868bfa79f23fb`; `handoffs/active/vidya-belief-substrate-program.md` has SHA-256 `bd628c4ff94a00097aabb62001374c4f2ad4fed2b16677bf1d198101d8927940`. This closes the enrollment prerequisite, not booking or a canonical GPU grant.
- Elementwise row `ni-gpu-pool-elementwise-20261026-v1` is now ARMED. MAIN approved exact seal `5a33ba2982e94a427ae16cdea635f905b9d158676412399ef2a87559eafd2b0a`; official GPU filler8 launcher `2258057` and distinct watcher `2258059` are separately live. Its own-row admission self-test returned exit 0 against real RAM/process/window data; registration request UUID `76542d1a-fc48-441e-a4f7-13c249929aef` is `socket_sent` with owner confirmation pending. No canonical grant or native GPU result exists.
- A subsequent MAIN notice (`1b2ec68e`) requests a precise correction to the attention row's record carrier: `provenance.json` is the enrollment carrier; `results.json` is the results array. This is an owner-facing carrier-description correction, not an additional task or a native-result receipt. Keep the enrollment carrier and result array distinct.
- The 03:14Z snapshot above remains as recorded; the dated addenda supersede only the specific owner-state fields that changed.
