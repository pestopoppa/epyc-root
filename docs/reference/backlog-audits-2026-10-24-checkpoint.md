# 2026-10-24 accepted diagnostic findings checkpoint

This checkpoint preserves three owner-accepted static/source audits from the workspace-58
delegation packet. They are diagnostics and implementation guidance, not new measurements, live
service evidence, or completed code changes. The detailed accepted reports remain in the protected
task packet at `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/tasks-from-ws58/`; this document
copies the decision-relevant evidence and its limits so the next owner does not have to reconstruct
the conversation.

## GNX-SEGV-1 — incremental GitNexus analyze crashed

**Accepted finding:** the orchestrator's incremental `gitnexus analyze` exited with signal 11 after
it logged the expanded write set (`changed=80`, `added=19`, then `+1063 importer(s) added to writable
set`). Available output does not identify the failing function or native frame. A LadybugDB/native
binding fault is plausible, not established.

Static evidence places the crash after importer expansion and within the incremental write-back
window. `.gitnexus/meta.json` was changed and retained `incrementalInProgress` (`toWriteCount: 99`);
the active database was 511,283,200 bytes versus 435,286,016 bytes in the verified pre-run backup,
and the WAL and parse cache had post-start mtimes. Those facts prove writes happened, not row-level
damage or database inconsistency. No core/backtrace was captured; the inspected source and run log
cannot narrow the native frame. The 19 additions and 80 changed files inspected were valid UTF-8,
had no NUL bytes, and had maximum line lengths of 235 and 374 characters; oversized files were
already skipped. Peak RAM was not measured.

**Owner action and current state (corrected at 2026-10-24 16:47Z):** the owner moved the untrusted
partial index aside and restored the verified backup at `fd1a894`. The suggested full rebuild was
then **refused before execution** (rc 64: `GLOBAL/q0 lacks one granted ancestor write flock`); no
analyze ran. A one-shot wrapper `--force` waiter was rebooked for the whole-host window after the
quiet chain, ending by 21:58Z. Do not report that job as running or the crash as repaired. Existing
coverage is `NIB2-GNX-1` in `handoffs/active/non-inference-backlog.md` and `VB-GNX-REINDEX-1` in
`handoffs/active/vidya-belief-substrate-program.md` / the adapter source table; no duplicate task or
ClaimTuple ladder is needed. The source table correctly classifies the receipt as dependency
evidence.

The accepted recovery recommendation remains: keep the partial index untrusted, retain the
verified backup, and use the existing wrapper's full `--force` path only after the whole-host
writer/CPU grant is available. This is a risk-reduction proposal, not proof of root cause or
guaranteed recovery. Do not query the partial database.

## HSF-5P-G4-LOG-1 — G4 enable line was filtered

**Accepted finding:** the 15:44Z G4 result stays **INCONCLUSIVE**. The campaign's server verbosity
was 3 (the default); `common/log.cpp` maps the mirror's `LLAMA_LOG_INFO` line to
verbosity 4, and the callback drops messages above the configured threshold. Thus the B server log
can omit the `HSF-5.P kv host mirror ON` evidence even when the code path emits it. The log's
verbosity line is 3, with zero ` I llama_` lines; the verdict's G4 gate requires `enabled_line`, so
the inconclusive result matches the filter.

The proposed harness amendment appends `--log-verbosity 4` to **every arm's** generated argv,
preserving within-run symmetry. It admits INFO and TRACE output while still excluding DEBUG at 5.
Inspected logger call sites did not show per-token TRACE logging, but this does not prove zero timing
overhead: extra formatting, queue work, and I/O are possible. Treat a future run as a separate
measurement under an owner-reviewed new pin. The source patch, amendment, launcher digest, and
predeclaration remain proposals until the owner applies and pins them. No dry-run, test, build, or
campaign was run as part of this checkpoint.

The owner accepted the direction and requires the amendment to say G1 is evaluated with all arms at
verbosity 4. The GPU rerun is still blocked on its separate grant after the quiet chain. Existing
coverage is the open end-to-end `HSF-5.P` acceptance task in
`handoffs/active/heterogeneous-slot-fabric-residency.md`, plus the already-filed
`VB-HSF5P-WRITE` native writer/reader. No result is promoted and no new belief ladder is proposed.

## HPR-B-SIM-DISAGREE-1 — generated suffix missing from simulator prefix state

**Accepted explanation:** the simulator retains generated-output *counts* but not the token IDs in
the simulated slot prefix. For the 64k dense wave-0 `extend_1` request, its prior rendered-input LCP
is 65,318 and its newest usable checkpoint is 65,314; the server slot held 65,333 tokens after
generation. The difference is 19 tokens: 4 tokens after the simulator's selected checkpoint in the
old prompt plus 15 generated tokens retained by the server. Therefore simulator prompt length was
2,818 while the log's prompt length was 2,799. The server's logged 65,333 prefix is direct evidence
of its cached length, but saved request artifacts omit the generated token IDs; the exact 15-token
identity and an independent replay are unavailable. The 8k dense wave-0 and 64k dense wave-1 cells
agree with their final checkpoints, so a count-only fix would incorrectly extend those cases.

The narrow proposed correction is to capture/persist prompt and generated token IDs, retain the
server's actual token sequence across simulated requests, and calculate LCP against that sequence.
Use the server's retained boundary (`n_total + generated - 1` here), not every returned token. A
non-tautological regression requires token-ID fixtures from a new predeclared run; current artifacts
cannot reproduce this exact case. The 64k disagreement remains `INVALID_SIM_DISAGREES`; the owner
accepted the explanation and explicitly forbade re-grading the old run. A corrected simulator needs
a new predeclared run and grant.

**Coverage audit:** the KVU adapter source entry already covers native `requests.jsonl` rows but
explicitly does not read decision-input `cells.jsonl` rows. The parent `VB-KVU-1` source and the
open HPR-B holdout in `handoffs/active/kv-unified-stack-rollout.md` are the right owner paths. This
checkpoint is a source audit, not a ClaimTuple-producing measurement. Do not create a second source
class or grading ladder; if the owner accepts the simulator fix, extend the existing producer's
native capture and its existing source task before the next run. The owner offered
`HPR-B-SIM-FIX-2` as an optional follow-up; exact draft text for the owning main is below.

## Owning-session application draft

The following child checkbox is a concrete derived action from the accepted HPR diagnosis. It was
not applied here because the handoff is owner-maintained:

```markdown
- [ ] **HPR-B-SIM-FIX-2 — model the server-retained generated-token suffix in KVU-12.1 checkpoint simulation.** Extend the existing KVU-12.1 producer to capture prompt and generated token IDs, preserve the server's retained token boundary (`n_total + generated - 1`), and compute the next LCP over that full sequence. Add (1) a clearly synthetic token-ID fixture that exercises the known 65,333 cached-prefix / 2,799 prompt-token arithmetic, and (2) a separate capture fixture from a new predeclared run that independently validates the retained generated suffix; preserve the agreeing 8k and 64k wave-1 controls. Do not claim the synthetic fixture reconstructs the old run's absent token IDs. Existing run remains `INVALID_SIM_DISAGREES`; do not re-grade it. New predeclaration and grant required before rerun. Evidence: `docs/reference/backlog-audits-2026-10-24-checkpoint.md`, HPR-B-SIM-DISAGREE-1.
```

No separate checkbox draft is proposed for GNX (existing NIB2-GNX-1 covers the rerun) or HSF
(existing HSF-5.P is the end-to-end acceptance task; the amendment remains a concrete proposal
inside that task). The HSF and GNX accepted reports are already durably represented by this focused
document and their existing handoff/source entries.
