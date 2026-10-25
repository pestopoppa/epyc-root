# Codex NI checkpoint — 2026-10-25 23:10Z

**Snapshot boundary:** 2026-10-25 23:10Z. This note records accepted receipts and owner-confirmed scheduling state at that time; it is not a live ledger. Root baseline reviewed from `origin/main` `a1bc17fbc72d82921f987c8425cb6c1804042f8b`.

## Accepted results and limits

- UFH12 Request A source publication: `epyc-orchestrator` commit `46f03ecc596a566bb68b0f0311e73f7b6c2089fe`, remote-equal, 109 accepted tests (`/mnt/raid0/llm/tmp/codex-ni-20261025-ufh12-publication/result/publication.txt`). Actual EG2 BF16 copy, R1–R5 live proof, and Request B remain open. No ROOT promotion or runtime reload is implied.
- GNX native R2 resource-control fixtures: PASS, rc 0, CPUs 72–95, SQL threads 1, observed native DB task cap 6 (`/mnt/raid0/llm/tmp/codex-ni-20261025-gnx-native-cap-fix/r2/result/attempt-2/RESULT.json`). This did not run a fresh index, write an installed package, or publish source. GNX source publication still awaited mandatory model-free make gates and job revision against private pinned tools; the previous 75-old-path check is superseded and no source publication had occurred at this boundary.
- RTG57 continuation source publication: commit `53a029764a28a54fd7570b002ec4f0881bba47bd`, remote-equal, normal hooks and exit 0 (`/mnt/raid0/llm/tmp/codex-ni-20261025-rtg57/publication-continuation-v1/results/publication.txt`, `status.json`). The 22-test result is source-only; full native capture remains open. Preserve the earlier v1 whole-MAIN-drift failure and clean lease release.
- Prior root receipt `6d7ff38908ec475e8ba8ece4b11675c717a320a` already covers exactly CME7T and INF64. Do not recount those closures. No committed-conclusion belief capture or main promotion is claimed for that receipt.

## Scheduling and open work

- `gap-ni08-ingest-20261025` (poller 662457, watcher 662458) passed admission at 23:08:21Z and is locally ARMED. It was sent under notice `f9506526`; owner ACK/registration/book was pending. This is one locally ready row, not the 6–10-row pool target. The full 162-case canonical-config preflight passed at 23:01:57Z; it is preflight evidence only.
- AKX job 4113131 / watcher 4113227 and V11 job 4113334 / watcher 4113368 are booked to the night writer after EB, expected 2026-10-26 around 22:00Z; full runs are not complete. HPR golden v3 is booked 2026-10-26 03:30Z, q1.
- INF78 R10 failed after 103 unit cases because Claude returned the legitimate refusal `Cannot write to <path> while in plan mode.` R11 passed 106 preflight cases; capture-all-15 plus strict-cleanup is prepared but unarmed pending MAIN review of the native packet. Native 15 are not PASS.
- INF73 source-first actual run had 40 pass / 1 fail because `/usr/bin/python3` resolved via symlink differently from platform-resolved Python 3.13. Continuation using resolved 3.13 passed one preflight case, but remained ready=false and unarmed. No materialization/native/GPU approval.
- Gap-pool policy controls passed 27 cases and three documentation-surface proposals existed, but operational policy adoption was not established. The owner’s q3 fold rule applies block-correctness-only while an open GPU grant names CPUs 184–191; it did not change the current writer. Five model-free AK test-debt groups were accepted and deconflicted, but no group fix had been dispatched.
- The original INF62 memo remained reviewable analysis only; target/checkpoint/trainer recipe was unverified. The original DF2-QWOPUS parent remained open; future K1/training work stays preserved.

## Belief and checkbox handling

These source publications and software/test results do not invent measurement tuples. Reuse existing native source/task extensions where applicable; record a committed-conclusion OBSERVATION only after its actual commit, path, and line exist. No new source class or grading ladder, ingestion, retroactive tuple, parent tick, or checkbox change is proposed here.
