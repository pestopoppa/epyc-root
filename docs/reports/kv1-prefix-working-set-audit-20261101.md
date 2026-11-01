# KV-1 prefix working-set audit (2026-11-01)

## Scope and source

This is a zero-inference, read-only count for KV-1. The canonical source was
`/mnt/raid0/llm/epyc-orchestrator/logs/serving_calls/serving_calls.jsonl`, SHA-256
`3b6627275bb1abec5f945320167557a579de8422d98f71b471f2a65a99cfea9f`. It contains 130
records; all record IDs are unique and each `record_sha256` re-derives. A second independent
read reproduced the digest and record counts. Source code was read from epyc-orchestrator
`origin/main` at `25d4bc71351437b45d400c36e986b502d94c3c5c`.

Of the 130 records, 125 were dispatched and carried a prefix fingerprint. Ninety-eight include
the `c2048` depth; 27 are shorter than that depth, and five undispatched records have no
fingerprint. No `coder_primary` traffic appears in this log. The complete traffic window is
2026-10-03 05:00:13Z through 2026-10-29 17:34:25Z.

## Method

The candidate count groups dispatched records with a valid `ts_start`, integer server port, and
`request.prefix_fp.c2048`. It sorts by `ts_start` and calculates the maximum number of distinct
`c2048` hashes in any trailing 3,600-second window, by role, by launch identity when available,
and by recorded port. A launch identity uses `(server.launch_id, server.base_url,
provenance.host)`. Rows missing `launch_id` remain unresolved `(port, base_url, host)` groups and
are not treated as confirmed physical-server groups. Slot ceilings used for comparison were the
handoff's production value of two, and one for `coder_primary` / `coder_escalation` role
declarations. No prompt text or hash identifiers are included here.

## Candidate maxima by role and server

These are upper bounds on the number of distinct PrefixRouter keys, not exact router-key counts;
the truncated 16-hex-character SHA-256 values are treated as collision-free at this sample size.
`eligible` is the number of dispatched records with a `c2048` fingerprint. The repeated column
counts distinct `c2048` hashes that recur at least twice in the peak window.

| Role | Port | Dispatched / eligible | Max distinct `c2048` | Repeated distinct | Calls in peak window | Slot ceiling |
|---|---:|---:|---:|---:|---:|---:|
| architect_critic | 8083 | 8 / 4 | 3 | 1 | 4 | 2 |
| coder_escalation | 8083 | 6 / 3 | 1 | 1 | 2 | 1 |
| frontdoor | 8199 | 28 / 9 | 1 | 1 | 2 | 2 |
| coder_escalation | 18283 | 26 / 26 | 1 | 1 | 2 | 1 |
| architect_general | 18973 | 6 / 6 | 2 | 2 | 4 | 2 |
| coder_escalation | 18973 | 8 / 8 | 2 | 2 | 4 | 1 |
| frontdoor | 18973 | 42 / 42 | 2 | 2 | 18 | 2 |
| worker_general | 19198 | 1 / 0 | — | — | 1 | 2 |

## Candidate maxima by recorded port

Ports are endpoint labels, not proof of one physical server or process across a full window.
These combined port maxima are candidates only; see launch-identity results below.

| Port | Dispatched / eligible | Max distinct `c2048` | Repeated distinct | Slot ceiling | Peak window endpoint (UTC) |
|---:|---:|---:|---:|---:|---|
| 8083 | 14 / 7 | 4 | 1 | 2 | 2026-10-04 02:51:30Z |
| 8199 | 28 / 9 | 1 | 1 | 2 | 2026-10-29 09:26:49Z |
| 18283 | 26 / 26 | 1 | 1 | 2 | 2026-10-23 00:43:53Z |
| 18973 | 56 / 56 | 2 | 2 | 2 | 2026-10-22 11:22:44Z |
| 19198 | 1 / 0 | — | — | 2 | no fingerprinted window |

## Candidate maxima by role and launch identity

Distinct counts remain `c2048` upper bounds, not exact PrefixRouter-key counts. Launch IDs are
shown with a short prefix only.

| Role | Launch ID / identity state | Port | Max distinct `c2048` | Peak-window end (UTC) | Slot ceiling |
|---|---|---:|---:|---|---:|
| architect_critic | `f4f50d…` | 8083 | 3 | 2026-10-04 02:50:39.652Z | 2 |
| architect_general | launch ID missing | 18973 | 2 | 2026-10-22 11:25:12.729Z | 2 |
| coder_escalation | `3d2361…` | 8083 | 1 | — | 1 |
| coder_escalation | `f4f50d…` | 8083 | 1 | 2026-10-04 02:51:30.662Z | 1 |
| coder_escalation | launch ID missing | 18283 | 1 | — | 1 |
| coder_escalation | launch ID missing | 18973 | 2 | 2026-10-22 11:24:49.529Z | 1 |
| frontdoor | launch ID missing | 8199 | 1 | — | 2 |
| frontdoor | launch ID missing | 18973 | 2 | 2026-10-22 11:22:08.429Z | 2 |

Launch `f4f50d…` is the one shared identity observed across roles; its combined distinct
`c2048` upper bound is 4 in a rolling 60-minute window ending 2026-10-04 02:51:30.662Z. On port
8083 across the full dataset, 14 records include two missing launch IDs and five distinct
non-missing launch IDs. Every record on ports 8199 (28), 18283 (26), 18973 (56), and 19198 (1)
lacks a launch ID; ports 8070 (2) and 8074 (3) also have no launch IDs and no c2048-eligible
traffic. The launch identity needed for physical-server grouping is therefore unavailable for
most calls.

## Limitation and next action

`PrefixRouter` canonicalizes the prompt then hashes its first 256 characters (`prefix_length=256`).
The serving record's `c2048` hash is computed over the first 2,048 caller-wire characters and
does not use that canonicalization or prompt rendering. Distinct `c2048` hashes therefore give
only an upper bound on distinct router keys: different long fingerprints may share the router's
first 256 canonical characters. Calls shorter than 2,048 characters also lack this fingerprint.
The shared launch `f4f50d…` has a candidate upper bound of four versus two configured slots, but
the exact router-key count is unknown. Port 8083's full-window aggregate also spans multiple
launches, and most other ports have no launch ID, so the log cannot establish physical-server
working sets for every endpoint. No exact-key or exact-server conclusion is claimed.

Next: emit a privacy-preserving hash of the exact canonical 256-character PrefixRouter input and
an immutable server launch identity with each serving record (with tests proving the hash shares
the router's canonicalization path and identity survives sidecar rollover). Then repeat the
role/server rolling-window count over a complete window. Do not log raw prompt text or canonical
keys. No models, inference, server, or production process were used or changed.
