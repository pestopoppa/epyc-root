# 2026-09-18 — backlog churn, second batch: seven closures, one contract renamed, one daemon class named

Second low-hanging batch of the evening, same rules as the first (`2026-09-17-backlog-churn.md`):
zero inference, unit tests with fake backends, source reads and `/proc` reads. No server was started,
stopped or reloaded; no daemon was signalled. Four implementation subagents on disjoint file sets,
one read-only investigator, the rest in-session. Everything is committed and pushed in both repos
(`git cherry` empty).

## Closed

| Task | Handoff | Commits | What landed |
|---|---|---|---|
| **Index-row hygiene** | (indices) | root `10f6f2b2` | `scripts/handoffs/stale_next_action.py` — reports a row whose `Next action` names ONLY ticked tasks. Seven rows were stale on introduction and were repointed at their handoff's first still-open task: EVL-13 (ETR-4→ETR-1), EVL-29 (ID-2→ID-3, done 08-23), EVL-37 (RTE-Prefix→S4 Omega A/B), EVL-49 (S-01→S-04, 14 days stale), RTG-15 (EPD-3-R5/R6/R8→EPD-1-orig), RTG-42 (WP-9/10→WP-8), RTG-56 (TD-1/TD-2→TD-1d). Documented beside `--check` in `handoff-index-authoring.md`. |
| **`/v1` schema truth** | harness-selection-and-integration | orch `dadad301` | Every request-field description in `src/api/models/openai.py` now states what the seam actually does. Descriptions only; 13 guard tests assert the false phrase is gone AND the real behaviour is named. |
| **HS-OD-3..7 filed** | harness-selection-and-integration | root `93461a81` | Five behaviour defects the description sweep exposed (below). |
| **UTM-P1a.2** | unified-trace-memory-service | orch `7887e7ae`, root `93461a81` | Second and third pairing-key producers: replay harness stamps `harness="review_replay"` + `task_key=rr50-NNN`; delegator stamps its per-step review index as `turn_ordinal`. 8 tests incl. a real temp store where `paired_runs("rr50-001")` returns both harnesses. **UTM-P1a.3** filed; RTG-41 repointed at it. |
| **NI-OC-a** | non-inference-backlog | root `49e85ab7` | OpenCode event reaper adopts `observer_guard.sh` three-state liveness; registry row adopted at contract v1. 15 tests + 1 skip. **NI-OC-a.1** filed (below). |
| **RTG-47** two data-plane items | dashboard-architecture-restructure | orch `75e68b0b`, root `5c832f07` | `InferenceResult.prompt_tokens` threaded from the three llama_server return sites; tap stamps `prompt_tokens_source="server_terminal"`; a completed card renders `↑ N tok` only for that source, the chars fallback stays `prompt Nc`. Topology nodes carry `substrate_source = process \| role-kind \| manifest`; a declared substrate gets its own chip. 11 + 5 tests. |
| **HS-OD-3 + HS-OD-7** | harness-selection-and-integration | orch `2a609f5c`, root `697eab92` | `x_force_role` is the true name; `x_force_model` kept as a deprecated alias; the three override fields validated after normalization against `available_roles() ∪ server_urls` keys — an unservable value is a 422 naming the field. 151-case contract test built from `Role` and the alias maps, not a hand list. Four Hermes skill docs that told authors `x_force_model` "forces a registry model" corrected. |

## Filed, not fixed

- **HS-OD-4** `max_tokens` is not a generation cap in REPL mode (read only as `max_turns = max_tokens // 500`
  clamped 1..5; per-call cap hard-coded 1024). **HS-OD-5** sampling overrides and `max_tokens` dropped on the
  vision path with a 200. **HS-OD-6** `x_disable_repl=true` + `tools` renders `CALL(...)` instructions for an
  executor that is off. Each changes `/v1` behaviour a shell depends on and wants its own before/after test;
  HS-OD-4 needs a decision (honour, refuse, or document the turn derivation as the contract).
- **UTM-P1a.3** — no pairing exists on REAL data yet: replay writes its own trace DB and unlinks a pre-existing
  one under the TM-8 fresh-run rule while `paired_runs()` reads one `db_path`; live tasks carry no corpus id;
  delegator rows are turn-numbered while replay rows are NULL.
- **NI-OC-a.1** — the live reaper daemon must be restarted from the tracked path (operator/owning session).
- **NIB2-81** — the daemon-staleness class (below). Investigation root `2de8f11e`; full census with pids, inodes
  and diffs at `tmp/daemon-staleness-20260917/report.md`.

## The judgement calls worth keeping

**The description sweep found behaviour, not prose.** `336bd170` had fixed one field whose description promised
a cap the seam never applied. Sweeping the rest of the schema for the same shape produced five rows that are
about code, not docs: a description that promises behaviour the code lacks is a silent no-op aimed at
integrators — the HS-1g call-verb trap pointed the other way. HS-OD-1 already set the rule (*a body field
that changes output semantics must be refused, not ignored*); HS-OD-5/7 were unfinished applications of it,
HS-OD-4/6 mode-dependent contradictions of it, HS-OD-3 a name promising a capability the code did not have.
The descriptions were fixed the same night; the behaviour was filed, because each row changes what a shell
observes and deserves its own test rather than a drive-by patch.

**HS-OD-3 — the role is the contract, so rename rather than build.** `x_force_model` was assigned to `role` and
normalized exactly like `x_orchestrator_role`, so a registry model name could only ever miss. The two
options were to build model-name resolution or to name the field for what it does. The operator ruled:
*"the model role is all that's needed. No need to ping models that aren't part of the orchestration
stack."* Every served model already has a role, and `/v1/models` returns roles, so `x_force_role` is the
true name. **Deprecated, not deleted**: `x_force_model` keeps identical behaviour, is marked deprecated in the
schema and logged when set — removing a published field silently is worse than carrying it (the same call as
EVL-42 (d) the night before). Setting both to different values is a 422 naming both, mirroring the existing
`max_tokens`/`max_completion_tokens` double-supply rule. `gpt-*`/`claude-3` stay `model`-field conveniences
and are deliberately NOT legal override values: they name no role and `/v1/models` does not list them. Three
values that `/v1/models` advertised yet died at lookup (`orchestrator`, `architect`, `worker`) now resolve.

**NI-OC-a — `unobservable` withholds VACUUM.** The old gate was `pgrep -x opencode`: two-state, and a drifted
argv reads a LIVE process as ABSENT — the state that *permits* the destructive branch. It failed closed by
luck of the exit codes, which is why it was registered `unadopted`. The consumer mapping now lets only
certainty permit destruction: `present` → withhold; `unobservable` → withhold **plus** an alarm breadcrumb
that clears on the next sighting; `absent` → permit, and only when every channel that could speak agrees.
Two read-only channels, neither a kill target: `proc_scan` matches `"opencode "` *with the trailing space* so
the reaper's own argv and `opencode.db` cannot self-match, and `db_fd` walks `/proc/*/fd` for an open
descriptor on the event DB — argv-independent, and the thing VACUUM actually cares about. A missing DB is
`unavailable`, never `absent`; channel disagreement is `unobservable`, so the unlucky case (stray cmdline,
DB closed) defers the VACUUM by thirty minutes and says so, instead of rewriting the operator's live DB
under an exclusive lock on a guess. A test asserts no bare name probe survives in the file.

**NIB2-81 — the daemon census instrument structurally missed the class.** NI-OC-a landed and "census OK (17
observers)" printed while the live reaper (pid 2873259, started 09-08) was still executing a 1,802-byte lane
copy from `worktrees/mains/ak-rebuild-20260828` — 461 iterations and 39 VACUUMs on the old two-state code.
`observer_census.py` is static by design: Rule A/B over `git ls-files`, and its runtime battery launches a
sandboxed stand-in rather than inspecting a live pid. It certifies the FILE and has no notion of an
INSTANCE, so it cannot disagree with a daemon that predates the file it certifies. The mechanism is
ordinary: bash holds `fd/255` on the script inode for life; git never writes in place, so every commit moves
the PATH to a new inode while the daemon keeps the old one; no cron in the container, so daemons are
hand-launched and inherit the launcher's cwd, and an abandoned lane never advances. Three shapes are live:
stale-and-diverged (the reaper), orphaned inode (hub and bus supervisors show `(deleted)` — the orphaning
event was this session's own `git reset --hard origin/main` at 19:04; identical content today, diverging
silently on the next commit), and orphaned tree (a `:8101` hub from a worktree that no longer exists, with no
registry row, pidfile or probe). The one loop that works is the bus supervisor's H-4 tree-divergence check,
which restarted the coordinator daemon at 23:34 the same night. Recommended shape: startup self-attestation
(own `fd/255` inode vs `HEAD:<relpath>`) plus a registry `runtime:{pidfile,expected_path}` field and an
`observer_census.py --live` `/proc` walk into the existing fleet alarm; generalising H-4 is the proven
follow-through. Nothing was signalled: the rule is kill only PIDs you captured yourself, and none of these
were.

**RTG-47 — the smallest field that expresses the distinction.** A measurement and an estimate had been
rendering identically on the card. Rather than a new source rule, `prompt_tokens_source` on tap records and
`substrate_source` (+ `substrate_declared_by`) on topology nodes follow the existing direction-dependent
rule: the terminal count is the request's own and wins over a retained mid-run total; an unknown role
declares NOTHING rather than guessing (embedder roles have no master row, so they stay on the heuristic as an
honest unknown). Per the plane rule the contracts live with the orchestrator; the hub commit is rendering
only. The live render of a measured arrow on a real card is unverified by construction — it needs a real
request.

**UTM-P1a.2 — only stamp an ordinal you own.** The delegator passes its per-step review iteration index as
`turn_ordinal` because that is the 0-based index it genuinely owns; the RD-10b final-aggregate review and the
parallel step executor are one-shot and stay NULL, because a 0 there would be an invented ordinal, not a
measured one. `seed` stays NULL everywhere (no RNG seed exists on these paths); `task_key` is pass-through
and never derived from `subtask_id`.

## Not ticked, deliberately

- No Phase-0 HS-4 box: that work belongs to other sessions; evidence went into box text.
- TD-1d's ACCEPTED tick (typed-decision-plane) was left standing with the n=4 re-measurement beside it as
  contrary evidence (`2026-09-18-td1d-remeasure.md`, TD-1d.0) — the box belongs to the accepting session.

## Validation

`index_state.py --check` 0 problems; `stale_next_action.py` none after the seven repoints. Orchestrator:
81 (openai_compat), 302 (trace/review/delegation/shadow), 424 (tap/substrate/topology/backend), 203
(override/model/compression) passed; ruff clean throughout. Root: 15 + 1 skip (reaper), 5 (machine
provenance). Observer census OK, 17 registered.
