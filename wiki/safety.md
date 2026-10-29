# Safety

**Category**: `safety`
**Confidence**: verified
**Last compiled**: 2026-10-24 (wrap-up sweep 25, workspace-58 convergence delta): SEC-ART-POST-b is operator-ratified. Earlier: 2026-10-24 (wrap-up sweep 22, 3c4ca599 delta): model artifact pins are enforced at start, and exec containment awaits a live tool call. Earlier: 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the last two lineup GGUFs are pinned and the registry default flips to strict (on branches). Earlier: 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23). Earlier: 2026-10-23 (wrap-up sweep 17, workspace-f8: GGUF fingerprints registered for the lineup; the launch check waits on lean-registry pins). Earlier: 2026-10-22 (wrap-up sweep 16, workspace-f8: exec-guard step 1 is on orch main; store immutability filed as SEC-ART-POST-g). Earlier: 2026-10-22 (wrap-up sweep 15, workspace-58: template store live, HF token gone, exec guards staged). Earlier: 2026-10-22 (wrap-up sweep 13, workspace-f8: template-pin coverage and the lean-registry pin gap). Earlier: 2026-10-22 (wrap-up sweep 12, workspace-58: artifact-integrity and exec-containment post-landing steps). Earlier: 2026-10-22 (wrap-up sweep 10: guard-denial ledger, lesson ITS, private-root gate). Earlier: 2026-10-22 (wrap-up sweep 7: CT-18 final: boundary sentence hurts the worker; llguidance abort). Earlier: 2026-10-21 (wrap-up sweep 5: CT-18 static-attack ASR numbers). Earlier: 2026-10-07 — reviewed source backlog. Previous compilation metadata: 2026-09-17 (evening: the v10 episodic re-pin is RATIFIED (MHS-3d closed); the AP-55 shadow pin); earlier 2026-09-17 (afternoon: every leak copy is purged, including the pinned v10 store; the checkpoint prompt re-pin is RATIFIED; the eval fence is on main and ran on a live API); earlier 2026-09-17 (later pass: the eval fence gains write/execute denial and an inherited-TMPDIR fix, the pool leak is chased into the checkpoints, and the MHS-3 structural refusals are built; earlier incremental: security-review GATE-0 before exploitability, mandatory refutation and a CWE-keyed dedup; one gold schema in the reviewer plane; the closure audit's false closures; the OP-20 fail-open argument); earlier: 2026-09-15 (mutation safety: override is a distinct risk class from constrain — every catastrophic held-out regression in the released corpus came from an override patch — and under-generalization has no guard yet; the apply gate is not yet "only screened effects apply"; earlier: 2026-09-14 (noninf sweep: PromptForge's Tier-2 mutation validator was writing the model-generated candidate over the live repo file and importing it in-process, so every proposal's module top level executed unsandboxed with the autopilot's authority — layer 4 is now a static `ast` screen with three denylist profiles, original-file grandfathering, and a closed fail-closed `MutationEffect` enum; an enforced denylist against a prompt asking for the forbidden shape would have made the MH-9 lane propose only rejects, silently, so the shape example now ships as a module constant screened in CI. ETR-2 on this page is now CLOSED — see benchmark-methodology.md); earlier: 2026-08-25 (the agent-security eval fixture is in-tree — TU-DTAP-1 done: a reviewed Apache-2.0 DTAP subset in a disposable local runner with deterministic state judges, typed failure outcomes, immutable trace replay, and target-disjoint attack payloads; and the PII fixture/allowlist drift that left the root candidate gate red for 22 days was surfaced with the L5 closeout)
**Sources**: 41 native document references (source review 2026-10-07)

## Compiled Update — 2026-10-24 (wrap-up sweep 25, workspace-58 convergence delta): SEC-ART-POST-b is operator-ratified

**Confidence: verified.**

- **SEC-ART-POST-b ticked: the four `template_diff_reviewed` entries (frontdoor, worker_vision, architect_critic, architect_general) are operator-signed** (receipt root `522f7fd33`, ratified 13:58Z). A follow-up, NIB2-103, notes that research `data/template_reviews` lacks a README/SHA256SUMS.

Sources: [model-artifact-integrity](../handoffs/active/model-artifact-integrity.md) (SEC-ART-POST-b) · [non-inference-backlog](../handoffs/active/non-inference-backlog.md) (NIB2-103) · [2026-10-24 workspace-58 progress](../progress/2026-10/2026-10-24-workspace-58.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 22, 3c4ca599 delta): model artifact pins are enforced at start, and exec containment awaits a live tool call

**Confidence: verified** (run records and predeclared rules in the cited sources).

- **SEC-ART-1 / 1.1 landed.** `safe_download.py` records the resolved HF commit sha and per-file sha256 into a ledger; the registry schema gained `hf_repo` / `hf_revision` / `sha256`. All 16 lineup roles are pinned (re-verified against the HF tree API and full sha256 of both on-disk GGUFs), and a missing pin is FATAL at `stack_commands.cmd_start` (`validate_or_raise`; `reload` unaffected; blast radius LOW), with an env opt-out. Research `7b157602` and orchestrator `26d0d033` merged; the shared research clone was fast-forwarded (ff-only, operator-approved) so `start` reads the pinned master.
- **Exec containment is applied but unproven live.** The API (restarted 16:19:44Z 10-23) carries `EXEC_WRITE_FLAGS=1`, `WEB_FETCH_GUARD=0`, `EXEC_CONTAINMENT=0`; it has served only `/health` since. `tool_call_audit.jsonl` holds 6 pre-reload records (2 ok, 4 refused). Proofs (1)-(4) wait on the production stack serving plus a first tool-calling request.

Sources: [model-artifact-integrity](../handoffs/active/model-artifact-integrity.md), [model-exec-containment](../handoffs/active/model-exec-containment.md)

## Compiled Update — 2026-10-24 (wrap-up sweep 21, 3c4ca599 delta): the last two lineup GGUFs are pinned and the registry default flips to strict (on branches)

**Confidence: verified** (commits named; ticks wait on merge).

- **SEC-ART-1.1: all 16 lineup roles pinned, 0 exempt.** Research `7b157602` pins `draft_qwen25` and `draft_qwen3_coder_0_75b` (community uploaders, size-matched to the HF LFS entry, 5 sequential metadata reads, no downloads) and fixes a duplicate YAML key that broke strict loading. Orchestrator `26d0d033` makes a missing lineup pin an ERROR by default (opt-out `REGISTRY_ARTIFACT_PINS_STRICT=0`). Merge order matters: research first, then orchestrator, or `start` recompiles without the drafter pins and the strict default refuses. Runtime `pins_strict` stays false until the SEC-ART-2 registration creates the launcher fingerprint ledger.
- **Secrets hygiene.** `/mnt/raid0/llm/hf-cache/token` was mode 664 and is now 600 (contents never read); the named `cache/huggingface/token` no longer exists, and an HF-header temp file remains mode 644 pending chmod or delete. Token rotation is an operator decision.

Sources: [model-artifact-integrity](../handoffs/active/model-artifact-integrity.md), [non-inference-backlog](../handoffs/active/non-inference-backlog.md).

## Compiled Update — 2026-10-23 (wrap-up sweep 17, workspace-f8): lineup GGUF fingerprints are registered, and the launch-time check waits on the lean-registry pins

**Confidence: verified** (`sec-art-fingerprints` RUN_RECORD.json: `check_rc` 0, 6/6 rows, `not_ok` empty).

- **SEC-ART-POST-a PASSED 2026-10-23T00:04Z.** Every lineup GGUF was full-hashed once: 6 rows, ~167 GiB read, one hashing core at `nice -n 19 ionice -c3` in the build role. `check` (stat fingerprint only) returns rc 0. The ledger is `/mnt/raid0/llm/cache/artifact_fingerprints.json`, sha256 `37e9c439…675d` ([model-artifact-integrity](../handoffs/active/model-artifact-integrity.md)).
- **The launcher does not yet read the pins.** SEC-ART-2 (refuse a role whose GGUF does not match its pin) stays open until SEC-ART-POST-f puts them in the lean registry the launcher reads. `pins_strict` is then flipped through stack-change. Until then, a swapped GGUF is detectable by `check` but not refused at launch.

### Source References (2026-10-23 wrap-up sweep 17)

- [model-artifact-integrity](../handoffs/active/model-artifact-integrity.md) (SEC-ART-POST-a, SEC-ART-2)
- [workspace-f8 progress, 2026-10-23 morning](../progress/2026-10/2026-10-23-workspace-f8.md)
- [workspace-f8 progress, 2026-10-22](../progress/2026-10/2026-10-22-workspace-f8.md) (night: fingerprint job armed)


## Compiled Update — 2026-10-22 (wrap-up sweep 16, workspace-f8): exec-guard step 1 is on orchestrator main, and the store-immutability choice is now a filed decision

**Confidence: verified** (git, handoff checkbox state). This section corrects and extends the sweep-15 safety section below.

- **SEC-EXEC-POST-e1 is landed, not just branched.** `exec_write_flags` in `PRODUCTION_FEATURE_WAVE_OVERRIDES` is on orchestrator **main** `a73af3cc`, staged by the operator. It goes live at the operator's next API reload; the box stays open for the live proof (`write_outside_root` in `tool_call_audit.jsonl`) ([model-exec-containment](../handoffs/active/model-exec-containment.md)).
- **The root-own / `chattr +i` question is filed as SEC-ART-POST-g, a decision package.** Option (a) root-owns the store and makes each file immutable; every later publish then needs the operator. Option (b) relies on the launch-time digest once SEC-ART-POST-f and `template_pins_strict` are on. The recommendation is (b) now and (a) after POST-f. Before this it was named in two notes but had no checkbox, so a form-screen could not see it ([model-artifact-integrity](../handoffs/active/model-artifact-integrity.md)).

Sources: [model-exec-containment](../handoffs/active/model-exec-containment.md) (SEC-EXEC-POST-e1) · [model-artifact-integrity](../handoffs/active/model-artifact-integrity.md) (SEC-ART-POST-g) · [workspace-f8 progress, Night](../progress/2026-10/2026-10-22-workspace-f8.md).

## Compiled Update — 2026-10-22 (wrap-up sweep 10): guard refusals are only inferred from transcripts, a lesson's effect needs a never-lessoned control, and trace-derived data has a private-root gate

**Confidence: verified** for the landed privacy gate, PII transcript scan and mining-code results on a 3-day sample; **PROPOSED** for the guard-denial ledger (nothing is wired; hook edits are human-applied) and **inferred** for any lesson-efficacy effect (the pilot has no pre/post read and no full run yet).

- **Guard refusals are currently an inference (guard-denial ledger, DHM-6, PROPOSAL).** A refusal is visible only as hook stderr inside the transcript, classified by regex, which makes the count fidelity `inferred`, blind to which rule of a multi-branch hook fired, and blind to Codex and opencode refusals. The proposal has each of the 11 refusing Claude hooks (plus the Codex and opencode containment guards) append one `dev-harness-guard-denial.v1` line before exiting: timestamp, hook, stable rule id, session, harness, source, tool, a keyed-HMAC block list of the refused command (no command text, path or cwd) and `fidelity=observed`. The HMAC blocks join to later tool calls, so "executed after its denial" becomes a mechanical query. Write discipline: flock, single write under PIPE_BUF, best effort and never fatal to the hook's exit code. Applying it is a human hook edit; the recommended order is Claude hooks first, then Codex/opencode, then the projector reading it as `observed` with the regex kept for history.
- **A lesson's efficacy is specified as an interrupted time series with controls (DHM-3).** 290 lessons were registered (227 feedback memories, 38 incidents, 25 CLAUDE.md rules); only 22 have a mechanical detector and 9 are hook-enforced, the rest recorded as out of scope rather than hidden. Segments are pre-lesson, post-lesson prose-only, post-hook, and post-hook on harnesses the hook does not cover (the in-period control). A lesson effect is read only as a difference against never-lessoned detector classes (`git_reset_hard`, `no_verify`, `hooks_path_null`), the origin-day session and its campaign siblings are self-excluded, and a prose lesson with a low delivered-context rate is reported as **not delivered**, never as **no effect**. The pilot fits exposure-weighted OLS on daily rates, a feasibility readout rather than the specified negative-binomial inference with clustered errors. Five pilot lessons: pattern kill, unbounded `llama-cli`, wholesale `git add` (prose then hook), and two prose-only (piped gate-then-push, glob `rm`).
- **Sample readout of the guard mining (65 units, 4,050 tool calls; tiny N, 3 days, no pre/post read).** 63 would-fire calls, 43 of them containment refusals all blocked by the hook; the rest git stash 5, `git reset --hard` 4, `pgrep` on a pattern 3, worktree prune/force 3, glob rm 2, wholesale add 2 (blocked), hooks-path-null 1; 75 hook denials, all from Claude Code. Predicates are the production scanners where a hook exists and retroactive otherwise, so they can over-fire; AgentRun truncation at 4,000 characters can cut a heredoc terminator. The first-turn floor sample (claude main) puts always-on files at about 12.4k tokens per turn, 5.9% of prompt tokens but 44% of the first-turn floor (3.6 chars/token assumed, nothing calibrated).
- **Trace-derived outputs now have a gate (F3-LB1 closed).** Per-session results live only under a private 0700 root that refuses any git work tree, the vault and the harness stores; aggregates (counts and rule text, per-session keys refused) publish only after the orchestrator `raw_trace_publish_preflight` exits 0; the staged PII guard gained a transcript-shape scan (Claude/Codex/opencode line shapes, per-session schemas, first 256 KB of large blobs; zero hits over the tracked tree, 10 real-hook cases plus 92 existing PII hook tests pass) landed under an operator D9 ack, which only the operator can give.
- **Reaper precondition (NIB2-LB1).** Any reaper that deletes harness-store rows or files must first prove an existing backup holds them: `backup_coverage.py precondition` exits 0 only when covered and fresh, 3 not covered, 4 backup older than the rows; exit 3 or 4 means do not delete and the operator decides, and no agent builds a parallel backup (operator ruling 2026-10-22). The opencode event reaper case was resolved by retiring the requirement: it prunes only the `event` table, which no mining reader uses, and hourly read-only snapshots hold the session/message/part history. Mining readers never open live stores.
- **Operator decision: the HF token revoke is declined.** The token lived only on this host, was never committed, and both local files were deleted 2026-10-21; residual risk accepted (a host process could have copied it while `stored_tokens` was group-writable at 0664).
- **Two containment lapses with named lessons.** A subagent ran an ungranted whisper job on a CPU quarter and was killed by PID, verified dead (no ungranted region-lock claims); and a shared-clone fast-forward ran under a live campaign because the live-process check printed but did not gate (gate it in code on a read-only `/proc` cwd walk). The `%llguidance` abort fix and its remaining fold are in [tool-implementation](tool-implementation.md).

### Source References (2026-10-22 wrap-up sweep 10)

- [docs/design/guard-denial-ledger-proposal.md](../docs/design/guard-denial-ledger-proposal.md) — ledger schema, hooks, rollout
- [docs/design/dev-harness-its-pilot-spec.md](../docs/design/dev-harness-its-pilot-spec.md) — registry, segments, controls, threats
- [handoffs/active/dev-harness-trace-mining.md](../handoffs/active/dev-harness-trace-mining.md) — M1/M2 sample results
- [handoffs/active/frontier-f3-data-flywheel.md](../handoffs/active/frontier-f3-data-flywheel.md) — F3-LB1 privacy gate and PII scan
- [docs/guides/agent-workflows/cleanup-reference-check.md](../docs/guides/agent-workflows/cleanup-reference-check.md) — reaper precondition rule
- [handoffs/active/model-exec-containment.md](../handoffs/active/model-exec-containment.md) — token revoke declined
- [progress/2026-10/2026-10-22-3c4ca599.md](../progress/2026-10/2026-10-22-3c4ca599.md) — containment lapses

## Latest source review — 2026-10-07

## Source synthesis — integrity contracts do not establish isolation

TU-GR-1 specifies a future agent/worker/grader separation but selects and activates no mechanism. Same UID or a separate worktree does not prevent access to hidden oracle material. Trace hashes, typed verdicts and prepared-action bindings establish identity and replay boundaries only when their anchors are retained; they do not enforce filesystem, process, network or mount isolation. The current trusted-code scorer appends assert snippets to candidate-readable source, so it cannot meet hidden-test confidentiality for adversarial candidates as-is. Acceptance requires benign sentinel probes from the actual launched identities and namespaces; mocks establish wiring only.

Other source safeguards have narrower scopes. The terminal timeout guard refuses execution and persistence after a timeout while a worker may continue effects. Declared scratch-root KEEP protection preserves marked roots, overlaps and removal ancestors, and rechecks markers at apply's phase boundary; it does not promise atomic protection against a marker created afterward or whole-host deletion safety. Host-supervision receipts are prospective dependency records, not graded activation or recovery evidence. The accepted October 6 host installation and heartbeat remain separately recorded; future receipt capture does not retroactively re-author those originals.

OpenCode event duty likewise remains inactive until a reviewed runtime handover. Its lock coordinates new once-status invocations, without atomically excluding the unchanged daemon. A successful hygiene heartbeat proves tick liveness, not duty success; subprocess timeout does not prove descendant cancellation. The owner must stop and verify its identified daemon and preserve one scheduler before activation. Source publication leaves the standing bus-supervisor DOWN ruling intact.

### Source References

- [Grader isolation specification](../docs/design/tu-grader-isolation-boundary.md) — real OS denial acceptance.
- [Terminal timeout](../docs/reference/repl-terminal-timeout-state.md) and [KEEP protection](../docs/reference/declared-scratch-root-keep.md) — exact source scopes.
- [Prospective host receipts](../docs/reference/host-supervision-activation-receipts.md) and [event-duty handover](../docs/guides/agent-workflows/opencode-event-duty-handover.md) — activation and recovery limits.
- [Non-inference backlog](../handoffs/active/non-inference-backlog.md) — current host installation and retained operator boundaries.

### Incremental clarification — 2026-10-07: scanner coverage and enforcement require their own authority

The operator's settled 1B decision keeps both credential-redaction fixture files under ordinary staged-blob scanning and rejects global whole-file exclusions. ED25519 header recognition is a separately accepted synthetic detector correction, conferring no fixture exception or complete privacy guarantee. A future concrete fixture edit needs an exact staged-content/provenance package; the old whole-file proposal is historical evidence, not pending authority. ([Credential decision](../docs/reference/credential-fixture-hook-decision.md), [header recognition](../docs/reference/staged-ed25519-header-check.md))

HG-9's detection/repair split is an accepted source-backed topology option with future synthetic cases, not an active selector or a demonstration that named registry models qualify as detectors. Tool-grader isolation likewise remains a distinct enforcement boundary: AP-54 hook-only telemetry cannot substitute for genuine OS denial, and reclassifying it into scoring failure would change the evaluated population. ([Escalation owner](../handoffs/active/reviewer-escalation-and-human-gate-policy.md), [tool-eval owner](../handoffs/active/tool-use-eval-contract.md))

## Source References

- [Grader isolation specification](../docs/design/tu-grader-isolation-boundary.md)
- [Terminal timeout](../docs/reference/repl-terminal-timeout-state.md)
- [KEEP protection](../docs/reference/declared-scratch-root-keep.md)
- [Prospective host receipts](../docs/reference/host-supervision-activation-receipts.md)
- [event-duty handover](../docs/guides/agent-workflows/opencode-event-duty-handover.md)
- [Non-inference backlog](../handoffs/active/non-inference-backlog.md)
- [Credential decision](../docs/reference/credential-fixture-hook-decision.md)
- [header recognition](../docs/reference/staged-ed25519-header-check.md)
- [Escalation owner](../handoffs/active/reviewer-escalation-and-human-gate-policy.md)
- [tool-eval owner](../handoffs/active/tool-use-eval-contract.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 7): CT-18 final, llguidance abort

**Confidence: verified** for the CT-18 / CT-18.1 results (951/951 rows, analysis `/mnt/raid0/llm/tmp/ct18-run-20261021/ANALYSIS_FINAL.md`; every figure is static-attack ASR on a named fixture set, never robustness); **inferred** for UFH14-LB1/LB10 (filed, not run).

- **IB2 (n=24) shows a large sentence effect.** Worker ASR (conflict A/B/C) 45.8 / 25.0 / 4.2% (A-vs-C 10/0, p .001); architect 45.8 / 4.2 / 4.2% (A-vs-B 11/1, p .003). Aligned-twin compliance stays high (worker 95.8 / 91.7 / 83.3%), and C carries a worker competence cost (clean `task_ok` 95.8/95.8/91.7).
- **The larger Skill-Inject set (316 complete triples) refutes a worker benefit.** Worker pooled ASR 25.9 [21.4, 31.1] / 32.0 [27.1, 37.3] / 23.4 [19.1, 28.4]%; B is WORSE than A (17/36, p2 .006), A-vs-C 45/37 (p .22). The CPU stratum (66) is n.s.; the GPU stratum (250) shows A-vs-B 13/31 (p2 .005); pooled and strata agree in direction. Skill-Inject has no competence measure (its `task_ok` is vacuously true). One row (SI-C037 arm C, 37546 tokens > 32768 ctx) is `skipped_ctx_overflow` and excluded from pairs.
- **DP-G ruled by the operator 2026-10-22: "Hold; architect trial".** No prompt change for worker or REPL roles (`debugger_system.md` unchanged); only CT-21, a default-off flag-gated architect-only boundary variant, is trialled, enabled only if competence is non-inferior and ASR improves.
- **Frozen-build hazard:** any request whose grammar starts with `%llguidance` hits `GGML_ABORT` (`common/sampling.cpp:211`) and kills the whole llama-server. UFH14-LB10 adds an orchestrator-side guard that rejects such grammars before they reach a role port; UFH14-LB1 carries the abort-to-error fix on the next experimental line and records which ports accept raw grammar from non-orchestrator clients.
- **Telemetry note:** Codex exports metrics to Statsig by default unless analytics is disabled (intake-2436#record); flagged to the operator, no setting changed.

### Source References (2026-10-22 sweep 7)

- [handoffs/active/qwen-chat-template-evaluation.md](../handoffs/active/qwen-chat-template-evaluation.md)
- [handoffs/active/agentic-serving-harness-fixes.md](../handoffs/active/agentic-serving-harness-fixes.md)
- [progress/2026-10/2026-10-22-ct18-final.md](../progress/2026-10/2026-10-22-ct18-final.md)
- [handoffs/active/frontier-f3-data-flywheel.md](../handoffs/active/frontier-f3-data-flywheel.md)

## Compiled Update — 2026-09-17 (evening): the v10 re-pin is ratified, so the leak cleanup has no debt left

**Confidence: verified**: root commit `810a6a82` and its operator ratification record.

### Key findings

- **MHS-3d is closed.** The afternoon pass left one step: the human-only re-pin of the purged
  `multitier_v10` store.
  - **The ratification.** `ratify_v10_episodic_repin_20260917.sh` ran, and its consolidated receipt
    returned RATIFIED (root `810a6a82`).
  - **What was re-pinned.** The three `file_sha256` entries (`episodic.db`, `embeddings.faiss`,
    `id_map.npy`) and `memory_count` (63925 → 63921). An amendments entry was added, and
    `checkpoint_sha256` moved from `a604276f` to `3b457d98`.
  - **Result.** The eval-leak cleanup is complete on the live, offline and pinned production_best stores.
  - [main-handoff-sweep](../progress/2026-09/2026-09-17-main-handoff-sweep.md),
    [ratify_v10_episodic_repin_20260917.json](../artifacts/operator/ratify_v10_episodic_repin_20260917.json)
- **Shadow cannot be armed by accident.** The AP-55 launcher now pins shadow mode and seed re-run off in
  `AUTHORITY_ENV`, so an inherited environment variable cannot arm the shadow run. Enforcement stays behind
  one reviewed shadow run. [autopilot-continuous-optimization](../handoffs/active/autopilot-continuous-optimization.md)

### Source References (2026-09-17 evening)

- [main-handoff-sweep](../progress/2026-09/2026-09-17-main-handoff-sweep.md): operator actions and rulings.
- [ratify_v10_episodic_repin_20260917.json](../artifacts/operator/ratify_v10_episodic_repin_20260917.json): the ratification.
- [sub-v10-repin](../progress/2026-09/2026-09-17-sub-v10-repin.md): the ratifier that was run.
- [autopilot-continuous-optimization](../handoffs/active/autopilot-continuous-optimization.md): AP-55-ARM launcher pin.

## Compiled Update — 2026-09-17 (afternoon): the leak is out of every store, and v10's re-pin is the last step

**Confidence: verified**: purge receipts, `--verify` output, git ancestry and the reloaded API's own checks.

This answers the previous pass's first open question. **MHS-3b was RATIFIED** (root `b8379d42`): all 10
checkpoint prompt copies were re-pinned to `18f8ea01`, so a rewind no longer restores the leaked `rules.md`.
**MHS-3c purged the out-of-scope copies**, using orchestrator tool `41baad2b`. It covered:
- 11 offline `episodic.db` copies and 15 state backups;
- the live store, purged while the API was stopped (64,208 → 64,204 entries);
- the pinned `multitier_v10` store, with operator approval.

`--verify` passes on all of them, and backups plus the receipt are in
`/mnt/raid0/llm/backups/episodic-leak-20260917/`.

### Key findings

- **A purge of a pinned store produces a ratification debt, not a finished state.** v10's
  `checkpoint_meta.json` pins `episodic.db`, `embeddings.faiss` and `id_map.npy`. After the purge the tool
  writes `pinned_repin_proposal.json` (episodic.db `24cff074…` → `8ff84e9d…`), and the meta keeps the old
  digests until the human-only re-pin (MHS-3d) is ratified.
  [promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md)
- **The purge treats the historical desync as data to preserve, not repair.** `repair_faiss_id_map.diagnose()`
  serves as the oracle, and `repair()` is never called. The 20260716 store keeps its pre-existing +32 FAISS
  desync, with exact diagnose deltas. A timeout that cut the first offline run at item 19 left the originals
  intact, and the re-run completed. [sub-episodic-leak](../progress/2026-09/2026-09-17-sub-episodic-leak.md)
- **The AP-54 fence is on main and ran live.** The AutoPilot merge train (orchestrator `a1a0251a`) carries
  `a8bdb15f`, `80fa99aa` and `0d3b6e26`. The 2026-09-17 reload confirmed that `chat.py` imports
  `knowledge_fence`, so each eval request arms the fence. The API was stopped afterwards at the operator's
  request. [main-handoff-sweep](../progress/2026-09/2026-09-17-main-handoff-sweep.md)

- **The v10 re-pin ratifier is ready and awaits the operator (root `b4744e00`).**
  - **What it re-pins:** the three file hashes, `memory_count` (63925 → 63921), the derived
    `checkpoint_sha256` (`a604276f` → `3b457d98`), and the v10 receipt mirror.
  - **What the checker audit found:** the purge had already broken the MHS-3b ratifier's `--verify`. That
    script's own sha is attested in its receipt, so it cannot be edited. The new `--verify` therefore re-runs
    every check the old one made, at the chained post-state, and the decision receipt records the
    supersession.
  - **How it is tested:** a dry-run against the real checkpoint is clean and wrote nothing. The 16 fixture
    tests are mutation-checked: removing the rollback, or the lock, turns a test red.
  - [sub-v10-repin](../progress/2026-09/2026-09-17-sub-v10-repin.md)

### Source References (2026-09-17 afternoon)

- [sub-v10-repin](../progress/2026-09/2026-09-17-sub-v10-repin.md)
- [main-handoff-sweep](../progress/2026-09/2026-09-17-main-handoff-sweep.md): Afternoon section: the RATIFY, API reload checks, purge scope.
- [sub-episodic-leak](../progress/2026-09/2026-09-17-sub-episodic-leak.md): inventory, design notes, test matrix.
- [promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md): MHS-3b/3c/3d state.
- [autopilot-continuous-optimization](../handoffs/active/autopilot-continuous-optimization.md): AP-54 closure note.

## Compiled Update — 2026-09-17 (later): the fence denies writes and execution, an inherited TMPDIR pointed armed code into a fenced tree, and the pool leak was in the prompts themselves

**Confidence: verified** for the fence's denied/working lists, the TMPDIR chain, the leak locations and the structural-refusal statistics (all offline code-read and negative-control verified). **Inferred** for the residual exposure that remains documented rather than closed.

Three follow-throughs from the previous pass. The AP-54 fence's third review found it handled only read rights, so armed code could still write or execute through raw ctypes. The MHS-3 work then found the leak was not hypothetical: a live AutoPilot prompt was quoting an actual pool question, and the leaked file had been copied into ten checkpoints. The structural refusals the previous pass deferred were also built.

### Key findings

- **The eval fence now denies the full content set, not just reads (`3c2295f4`).** The Landlock ruleset previously handled only `READ_FILE`/`READ_DIR`; armed code could write, truncate, unlink or execute a fenced file through raw ctypes. It now handles the full content set for the running ABI — read, write, execute, `MAKE_*`, `REMOVE_*`, plus `REFER` (ABI≥2) and `TRUNCATE` (ABI≥3). Allowed directories (run dir, `/tmp`, site-packages, every non-fenced subtree) get every handled right; allowed files get the file subset; fenced dirs get nothing. Masks come from the live ABI (`landlock_access_masks`) and ride in the spec, and `--probe` or a maskless spec falls back to read-only ABI-1 masks rather than widening. **Verified denied** (no leak): ctypes write, append, truncate, `os.truncate`, unlink, and creating a new file inside a fenced dir. **Still working:** run-dir write, `/tmp` write, a default `NamedTemporaryFile`, and numpy. Accepted residuals are documented in the fence docstring: names stay listable (`READ_DIR` on `/`), a fenced file in a volatile dir is hook-covered only, the allow-set TTL is 300 s, and new-file creation directly in a container dir that also holds fenced data is denied. Tests: fence suite 121, then 368 more across tool-registry/REPL/eval_tower_concurrency. Enforcement level: landlock ABI 6. ([sub-ap54-fence](../progress/2026-09/2026-09-16-sub-ap54-fence.md), [autopilot-continuous-optimization](../handoffs/active/autopilot-continuous-optimization.md))
- **An inherited TMPDIR pointed armed children at a tree they could not write (`257731ba`).** The API process is launched with `TMPDIR=<llm>/tmp` (`orchestrator_stack.py` sets it; `src/config/models.py` defaults `tmp_dir` to `$TMPDIR` or `<llm>/tmp`), and `/etc/environment` sets none — but `<llm>/tmp` also holds fenced subtrees, so under enforcement `tempfile` would fail for armed code, and the cached spec/hook-roots files (which used `tempfile.gettempdir()`) had the same exposure. The fix widens no rights on `<llm>/tmp`: armed `run_python_code` gets `TMPDIR/TEMP/TMP → <run dir>/tmp`; armed `run_shell` under kernel enforcement gets a per-call `/tmp/epyc-fence-tmp-*` removed after the call; production, control-arm and hook-only launches are unchanged; spec and hook-roots files are pinned to `/tmp/epyc-eval-fence-<uid>`. Verified with `TMPDIR=/mnt/raid0/llm/tmp`: armed `NamedTemporaryFile` and `mkdtemp` work, while a direct create in `<llm>/tmp` is denied (negative control). Fence suite 126; 381 passed across the adjacent suites. ([sub-ap54-fence](../progress/2026-09/2026-09-16-sub-ap54-fence.md))
- **MHS-3's structural refusals are built, and the post-hoc statistics are the reason to trust them (`6df6f0d8`).** `_transfer_safety_verdict` and the GEPA path now refuse, over the ADDED text only: `eval_content_ngram_overlap` (verbatim ≥8-token overlap with the pool/cores/sentinels or the rendered trace bank; hashed shingles packed with row id, ~1.3e-7 FP per shingle, template df ≥32 dropped, anchor-or-15-token-run rule), `eval_expected_answer_leakage` (name-shaped 1–7 token answers), `eval_source_identity_leakage` (trace blocks resolved to question/sentinel ids by ≥3 shared rare tokens, paraphrase-proof) and `eval_suite_special_casing` (keyed/phrase/mention, in-suite included). Every reason carries the matched source id, and harness text (prompts, `src/`, the original file) is never blamed. Measured on the real pool: 16 s cold, +590 MB RSS (index 173 MB, transient peak 1.37 GB), ~9 ms per edit; false positives 0/33 live targets and 0/91 historical mutations (2/91 borderline on special-casing), 2.4% of 467 whole `src`/docs files; coverage 1998/2000 verbatim pool prompts. `tests/unit/test_prompt_forge_content_leakage.py`, 51 tests. ([promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md), [sub-mhs3b](../progress/2026-09/2026-09-16-sub-mhs3b.md))
- **The pool leak was in the prompts (`09bdb998`).** Pool row `simpleqa_general_00912` (Aschoff / Bonn) was a worked example in `orchestration/prompts/rules.md` Example 4b **and** in `DEFAULT_ROOT_LM_RULES`, with a dormant HumanEval/55 copy in `src/prompts/coder_system.txt`. All are replaced with synthetic examples; the change takes effect at the next API reload (owned by the session that owns inference). ([promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md), [sub-leak00912](../progress/2026-09/2026-09-16-sub-leak00912.md))
- **The rewind hole: ten checkpoints, including `production_best`, still carry the leaked file, and restoring one copies it back.** `restore_checkpoint()` copies the checkpoint's `rules.md` (sha `b250c227…`) over the live tree, so removing the leak from the working tree is not enough. The operator chose option A (2026-09-16): the re-pin ratify script landed on root `main` (`0e2bbc33`) and the operator runs it and types RATIFY (it refuses while AutoPilot holds its lock). Out of MHS-3b's scope and still to clean (MHS-3c): 4 HumanEval/55 task memories in `episodic.db` (present in every checkpoint and the live store) and the Aschoff row in `autopilot_state*.bak*` `last_traces`. ([promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md), [sub-ckpt-leak](../progress/2026-09/2026-09-16-sub-ckpt-leak.md))

### Open questions

- MHS-3b/3c are cleanup paths, not detection paths: has the RATIFY been run since the script landed, and do the `episodic.db`/backup copies still exist?
- The Landlock fence's residuals (names listable; 300 s allow-set TTL; volatile-dir files hook-covered only) are accepted, not closed. Does any consumer depend on directory listing of a fenced tree?
- The structural refusals' false-positive rates are measured against one pool snapshot. What is the FP rate on a refreshed pool where the templates have moved?

### Source References (2026-09-17 later pass)

- [2026-09-16-sub-ap54-fence.md](../progress/2026-09/2026-09-16-sub-ap54-fence.md): the Landlock widening (`3c2295f4`), the TMPDIR fix (`257731ba`), and both negative controls.
- [promptforge-mutation-safety-contract.md](../handoffs/active/promptforge-mutation-safety-contract.md): MHS-3 structural refusals, MHS-3a/b/c.
- [2026-09-16-sub-mhs3b.md](../progress/2026-09/2026-09-16-sub-mhs3b.md): the refusal predicates, statistics and tests.
- [2026-09-16-sub-leak00912.md](../progress/2026-09/2026-09-16-sub-leak00912.md): the prompt leak and its replacement.
- [2026-09-16-sub-ckpt-leak.md](../progress/2026-09/2026-09-16-sub-ckpt-leak.md): the checkpoint re-pin ratify path.

## Compiled Update — 2026-09-17: security review decides reachability before exploitability, and a governance tick is not proof

**Confidence: verified** for the skill changes (`SKILL.md` read on `main`; root `affa8f9d`, merged as `719ac638`), the reviewer-plane gold schema (orchestrator `bdf76ab3`), and the closure-audit results. **Inferred** for the OP-20 fail-open argument, which is a decision package the operator has not ruled on.

The security-review skill now has three stages, placed in the pipeline order taken from CodeCrucible. Pre-validation dedup runs first, then GATE-0 production reachability, then mandatory refutation. A candidate that no real entrypoint can reach stops with evidence before any exploit reasoning. A candidate that clears the exploit gates is still only PROPOSED until someone has tried to refute it against the code. The same day's governance work applied the same idea to the backlog: a ticked checkbox is a claim, not evidence. Several fail-closed lessons came with it.

### Key findings

- **GATE-0 runs before exploitability.** `SKILL.md` step 4 now opens with GATE-0: trace from a real entrypoint, checking flag and config defaults, the launch manifest and import wiring. An unreachable candidate stops with evidence (`unreachable in production: …`), receives no severity, and gets no exploit reasoning. Exploit gates 1–8 run only on reachable candidates. The finding schema gains a `Reachability (GATE-0)` line. This reverses the earlier two-pass order, which ran the expensive analysis on dead code too. [security-review-skill](../handoffs/completed/security-review-skill.md)
- **Refutation is mandatory before CONFIRMED.** A candidate that passes the gates must still have its strongest counter-argument checked against the code, with file and line evidence. A refuted candidate goes to residual risk as `refuted: …`. If no refutation attempt is recorded, the finding is not emitted. The schema gains a `Refutation attempted` line. [security-review-skill](../handoffs/completed/security-review-skill.md)
- **The dedup key takes CodeCrucible's placement but not its key.** CodeCrucible dedups on `startLine` equality alone. That collapses two different classes on the same line, and it lets one finding survive twice when a reformat moves its line. The skill's key instead requires all three of: a normalised path (container mounts stripped, and an ambiguous suffix never matches); overlapping line ranges; and related CWEs (identical or parent/child, with the ten MITRE pillars excluded). The key is **prose instructions for an LLM reviewer, not a coded matcher**: benchmrk's five-tier scored matcher was not ported. [security-review-skill](../handoffs/completed/security-review-skill.md)
- **One gold schema and one gold-sanity gate, both in the reviewer plane.** The benchmrk annotation envelope, with its `status:"invalid"` decoys (the negative controls intake-845#record recorded us as lacking), is orchestrator `orchestration/gold_annotation.schema.json` plus `gold_annotations.py`. The gold-sanity gate is `gold_sanity.py` (`run_gate` / `validate_record`). Both belong to RA-9, merged as `bdf76ab3`. The skill consumes them and must not grow a second copy. The gate's order still matters: it runs the gold solution under the project's native runner **before** any self-consistency judge (the carried defect rate is 61.9%, n=105). Wiring the gate into the skill's pipeline prose is still the skill's own task. [security-review-skill](../handoffs/completed/security-review-skill.md), [progress 2026-09-16](../progress/2026-09/2026-09-16.md)
- **A tick is a claim, and one commit made five false ones.** The closure audit checked 3,359 ticked boxes. Five asserted code that exists on no ref (RC-9, E1a, UTM-M7, UTM-M8, a SQLite exporter), **all ticked by `4762625d`**. A later strict sweep found a sixth phantom, `token_observed_turns`, ticked by `08e9d60d`. Reopening follows the fail-closed direction: the box goes back to `[ ]` with its text preserved. Code that was built and later deleted is not reopened; it is labelled SUPERSEDED/REMOVED. The audit never ticks or unticks another live session's box. [handoff-closure-audit guide](../docs/guides/agent-workflows/handoff-closure-audit.md), [sub-closure-fix](../progress/2026-09/2026-09-16-sub-closure-fix.md)
- **OP-20: excluding failed rows is a fail-open.** Today the eval tower drops `task_failed` rows because `not r.error` filters them out. Seeding counts the same rows as WRONG. The package argues against option B ("task_failed → EXCLUDED in both"): a role that fails more often would *look better*, which is exactly the fail-open the disposition taxonomy exists to prevent. The recommendation is A: non-infra failures count as WRONG and infra failures are excluded, with an eval-quality era boundary, landed only between baselines. The stated risk is that a misclassified infra failure, such as an HTTP-400 caused by our own request builder, would then score WRONG, so `infra_failure_reason` coverage should be audited first. If there is no ruling, the default is C, the status quo plus `OP20_CAVEAT`. [sub-cleanup](../progress/2026-09/2026-09-16-sub-cleanup.md)
- **Loaders that fail closed, and a refresher that refuses rather than guesses.** The EVL-12 A2 residue fix routes `build_question_pool()` and `load_questions_by_ids()` through the path-bound research loader. Both fail closed. Before the fix, `--rebuild-pool` built the pool from a different `question_pool` module than the one that sampled it. The fix was merged as orchestrator `dec73e25`, and restoring the old bare imports fails 4 tests. On the dashboard side, `refresh_hub_view.sh` exits 3 on any tree that is unmarked, not a git top-level, or a linked worktree, before it runs `checkout --force`. [sub-cleanup2](../progress/2026-09/2026-09-16-sub-cleanup2.md), [sub-hubview](../progress/2026-09/2026-09-16-sub-hubview.md), [sub-integrate](../progress/2026-09/2026-09-16-sub-integrate.md)
- **Operator approvals on 2026-09-16 that concern safety.** The paired safety-gate frontier change was approved and is being built. It has two parts: the guard on the live policy, where `_pareto_archive_for_safety_guard` currently replays under the legacy objective policy, and the `frontdoor_speed` promotion override, plus the fail-closed operability work. AP-55's gate starts in shadow mode (A), with a pre-approved move to `enforce` after one shadow run. The AP-54 fence (Landlock enforcement) was still under third review and goes live at the API reload that follows the merge train. [progress 2026-09-16](../progress/2026-09/2026-09-16.md)

### Open questions

- Should the skill's dedup key become a scripted matcher, a port of benchmrk's five-tier matcher with a distance metric beyond parent/child, if the skill ever gets a scripted pipeline?
- OP-20: how many `task_failed` rows are in the current-era eval journal? If none, option A costs nothing. The operator has not ruled.
- The AP-54 fence and the safety-gate frontier change had not merged at pass 2. What fail-closed behaviour do they add once they are live?

### Sources

- [handoffs/completed/security-review-skill.md](../handoffs/completed/security-review-skill.md): GATE-0, mandatory refutation, the dedup key, and the single reviewer-plane gold schema and gold-sanity gate.
- [docs/guides/agent-workflows/handoff-closure-audit.md](../docs/guides/agent-workflows/handoff-closure-audit.md): the audit and its phantom-handling policy.
- [progress/2026-09/2026-09-16-sub-closure-fix.md](../progress/2026-09/2026-09-16-sub-closure-fix.md): the reopened false closures and the sixth phantom.
- [progress/2026-09/2026-09-16-sub-cleanup.md](../progress/2026-09/2026-09-16-sub-cleanup.md): the OP-20 decision package and its fail-open argument.
- [progress/2026-09/2026-09-16-sub-cleanup2.md](../progress/2026-09/2026-09-16-sub-cleanup2.md): the fail-closed question-pool loaders.
- [progress/2026-09/2026-09-16-sub-hubview.md](../progress/2026-09/2026-09-16-sub-hubview.md): the refresher's refusal conditions.
- [progress/2026-09/2026-09-16-sub-integrate.md](../progress/2026-09/2026-09-16-sub-integrate.md): merge SHAs `719ac638`, `bdf76ab3` and `dec73e25`.
- [progress/2026-09/2026-09-16.md](../progress/2026-09/2026-09-16.md): the safety-gate frontier approval, the AP-55 shadow mode, and the AP-54 fence status.

## Compiled Update — 2026-09-15: mutation safety — override is a distinct risk class, and under-generalization has no guard yet

**Confidence: verified** for the corpus result, the closed inertness hole, and the labelled corpus
(promptforge mutation-safety contract); **observation** for the budget-shape and cost-yardstick items.

- **ANTI-OVERRIDE prior (MHS-4).** In the released corpus **every catastrophic held-out regression came from an override patch**, and the trained editor converged constrain-only across all 9 patches and all 3 seeds — override (rewrite/force an action, hard-code an answer) is a distinct risk class from constrain.
- **Under-generalization guard is missing (MHS-3).** `_UNIVERSAL_TRANSFER_RE` rejects over-generalization (`always|never|all tasks`) but nothing rejects a mutation that memorizes the eval set by naming its instances; the anti-leakage pattern set must key on **source-identity** (question/sentinel id in the trace bank), not verbatim n-grams, because paraphrase bypasses n-gram matching (BAITBENCH entity-overlap/near-duplicate take-rates 82.5% / 72.5%).
- **The apply gate is not yet "only screened effects apply" (MHS-7/8).** The isolated `apply_code_mutation_in_context` exists but nothing requires its use, and only `UNSAFE` is refused today — so `UNKNOWN` (the default on a hand-constructed `CodeMutation`) still applies.
- **Labelled contrastive corpus available (MHS-5).** `examples/heldout_generalization/` — 23 patches, 3 editors, identical 10-failure evidence, 3 seeds, per-patch sha256, rescued/regressed counts over 1,270 held-out tasks, Apache-2.0.

### Source References (2026-09-15)

- [promptforge-mutation-safety-contract.md](../handoffs/active/promptforge-mutation-safety-contract.md) — the ANTI-OVERRIDE corpus result, the under-generalization gap, the apply-gate state, and the labelled corpus.

## Summary

Safety in the current EPYC stack is mostly about agentic trust boundaries: what external text may influence, which generated findings are allowed to become action items, and how review tools suppress false positives. The Fable 5 frontier review promoted one specific risk from background concern to concrete work: research intake and web research ingest arbitrary external text, then future agents read the resulting handoffs with repo-write authority. That makes source text an instruction-injection surface unless it is explicitly treated as data.

The first hardening pass is complete. External content is now policy-scoped as data, rendered in `SOURCE-QUARANTINE` blocks with provenance metadata, checked by a warn-mode validator, and covered by a synthetic canary. The orchestrator `web_research` path also quarantines source-derived synthesis before it enters downstream agent context. This is intentionally not a history rewrite; old handoffs remain historical, and the convention applies to new intake/research outputs.

Security review has a separate but complementary tool surface. The v1 security-review skill runs STRIDE, OWASP Web/API Top 10, OWASP LLM Top 10 2025, and supply-chain checks, then validates exploitability before emitting findings. Severity is gated by concrete exploit paths, which keeps the skill aligned with the project's general verifier discipline.

## Key Findings

### New (2026-06-22, privacy-hygiene pre-commit secret scanning — COMPLETED)

- **A regex-only pre-commit secret-scanning hook shipped across three repos; a model-based scanner was deliberately rejected as unjustified.** The hook passed 40/40 fixture cases (after patching stale secret-length thresholds and UUID disambiguation) and is installed/verified on epyc-root, epyc-orchestrator, and epyc-inference-research. No pre-push hook or hybrid model-based scanner was added — the evaluation fixture showed regex coverage sufficient, with low operational false-positive signal over 30+ days, and pre-commit remains the fastest feedback path. Scope is workflow-level defense only: no PII masking or model-based extraction, kept separate from document-pipeline safety policies. Source: [privacy-hygiene-precommit-hooks.md](../handoffs/completed/privacy-hygiene-precommit-hooks.md).

- **External content is data, not instructions.** A source may be quoted, summarized, and cited, but not copied into action positions unless an operator or project agent explicitly authors the instruction outside quarantine. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Quarantine needs provenance.** New source-derived blocks carry URL, retrieval timestamp, and SHA prefix, making later review and validator warnings traceable. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **Security-review findings require exploit validation.** The security skill's two-pass design avoids listing theoretical issues unless attacker capability, reachability, trust boundary crossing, vulnerable sink, mitigation bypass, concrete impact, minimal fix, and file/line evidence are all present. Source: [security-review-skill.md](../handoffs/completed/security-review-skill.md).
- **Safety work composes with the evidence plane.** Injection hardening prevents adversarial narrative contamination; the evidence plane prevents accidental narrative contamination from re-entering planner memory. Both are provenance problems. Sources: [Fable 5 executive summary](../handoffs/completed/fable5-findings-00-executive-summary.md), [evidence-plane-event-sourcing-and-narrative.md](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md).

### New (2026-07-14, fail-closed web research semantics)

- **The web research path now uses fail-closed evidence semantics.** The Gate-3 verification kept `get_eval_secret` and the no-tool isolation path clean, but `web_research` now reports `search_failed` instead of a soft success when the search lane is degraded. That is a safety improvement because the downstream planner can still see a fallback hit when one exists, but it cannot confuse degraded search with trusted evidence. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md), [HALO Spike Results](../research/deep-dives/halo-spike-results-2026-07-14.md).

- **Restart hygiene is a safety property, not just an ops concern.** The fresh authority daemon was brought up only after the stale supervisor/child pair was terminated and verified dead, and the live phase health exposed `code_stale=false` plus the current gate set. That keeps stale processes from masquerading as green security posture. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md).
- **Dashboard lock displays must not erase configured-but-inactive capacity.** The 2026-07-14 region-lock topology fix keeps quarter instances visible even when the runtime filter is `stack_numa_mode=full`, and it explicitly distinguishes active holder, selected/free, blocked, and configured inactive shapes. That matters for safety because hiding configured capacity in the operator view is a failure mode for both diagnosis and rollout decisions. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md), `epyc-orchestrator` `774fed69`.

### New (2026-08-16, promotion-gate integrity: the guardrail that cannot see what it is guarding)

Safety here has a second face beyond trust boundaries around external text: the **autonomous promotion gate**, which grants an automated optimizer authority to change production configuration. The 2026-08-15 finding is that this gate is structurally warrant-blind, and the mitigations are filed but not built.

- **Acceptance is a pure score comparison, and the gate never receives the mutation payload.** `passed = len(violations) == 0` (`safety_gate.py:2022`) over five score-comparison legs. Nothing requires a mutation to cite the failure it fixes — and structurally nothing *can* today, because `SafetyGate.check()` takes only an `EvalResult`. The one surplus-shaped check, `_proxy_check`, is warnings-only and fires only when *improved* and *declined* are both non-empty, so a strict no-op fires nothing at all. Surplus is likewise unpriced: the four Pareto objectives are `(quality, speed, -cost, reliability)`, while `instruction_token_ratio` is report-only and gates just the `structural_prune` action. Source: [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) (verified against `epyc-orchestrator` at compile time).
- **A byte-identical candidate can therefore be promoted on noise alone.** Under a stochastic LLM-graded objective, a candidate that changed nothing can outscore its parent. **SG-W1 (FILED, open)** is the cheap fix: refuse to promote a candidate whose config/diff is byte-identical to its parent, regardless of score. A few lines, zero exploration cost. The magnitude is on record from the external cohort dived on 2026-08-15: an *unchanged* harness scored 0.800 and 0.547 on the same suite (`intake-1141#record`).
- **A warrant requirement has a measured cost, so it was deliberately deferred behind telemetry.** **SG-W2 (FILED, open)** records whether an accepted edit cites an observed failure instance *without blocking on it*; the structural obstacle to plan for is threading the action payload to a gate that today takes only an `EvalResult`. The full warrant gate is explicitly deferred because the cost is real and measured in the source literature: equivalent guidance produced the lowest variance *and* "prevented breakthrough modifications" (`intake-1134#record`), and trace-reading share correlated **negatively** with gain, ρ −0.31 to −0.64 (`intake-1140#record`). This is the rare case where the project has evidence that a plausible safety control suppresses the outcome it is layered over — telemetry first, gate only if the telemetry says it matters. Source: [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md).
- **The cheapest exposure measurement is a known-null corpus, and it needs no gate change.** Run the optimizer against inputs with **no** failures and assert it proposes nothing — filed as EV-14f in [eval-tower-verification.md](../handoffs/active/eval-tower-verification.md) (open). Our eval tower measures whether a change HELPS, never whether a proposed fix ANSWERS a real observed failure, so a no-op or a fabricated-need edit is invisible to it. Carry the source's limits: its effect was concentrated in one proposer of five, and the trigger was a board-game genre prior whose analogue in kernel/routing/benchmark harnesses is untested — **a null result there is informative, not exculpatory** (`intake-1129#record`).
- **Scope note, so the external framing is not over-read.** We are not add-only — AP-17 `structural_prune` and `rollback` exist — so the external ratchet argument does not transfer unmodified. What does transfer: nothing re-examines already-accepted scaffolding, and there is **no abstain action**; the controller charter requires emitting "the closest valid AutoPilot action block" even when the best move is operator-facing (`deep_eval` is a partial, non-mutating escape). Five independent sources in that literature have no warrant requirement either — which is an **absence**, not evidence that a warrant requirement is unnecessary. Nobody has tested one.
- **A plausible-looking second `SafetyGate` in the tree is a standing misreading hazard.** `src/diversity_gate.py` has zero production importers, is warn-only by default (`SAFETY_GATE_WARN_ONLY` defaults to `"1"`), and was renamed 2026-07-20 out of a bare-name collision with `scripts/autopilot/safety_gate.py` — the module the autopilot actually imports. Its `evaluate()` accepts on a raw `quality_delta > 0` with no resolution band, so it reads like a live acceptance surface and is not one. A subagent during the 2026-08-15 intake session read it as our live gate and was wrong. **SG-W3 (FILED, open)** is to wire it or delete it. The safety lesson is general: an unwired module that looks like an enforcement surface will eventually be cited as one.
- **Fail-open concealment is the failure mode these guards exist against — and one guard is itself unread.** `src/autopilot_core/measurement_guards.py` has zero `raise` statements but is not naively fail-open: it exists *because* of the documented 2026-08-03 incident in which a T1 calibration reported 0% correct purely because the orchestrator API was down. The residual hole was **ETR-2**: `quality_measured` is computed, documented, and never read, so a placeholder result enters the gate as a literal `0.0` candidate score, saved only by an *independent* guard (the REL-1 reliability floor). A guard that is computed and never consulted is exactly the shape the project's own verification rules warn about. **ETR-2 is CLOSED as of 2026-09-14** (`epyc-orchestrator` `250a5d13`) — the fix and its measurement consequences are compiled in [benchmark-methodology.md](benchmark-methodology.md) (2026-09-14 ETR block); not restated here. Source: [eval-tower-loop-robustness-audit-2026-07-20.md](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md).
- **Absence must not be able to impersonate a passing measurement.** The 2026-07-22 provenance audit found `EvalResult.ece`/`auroc` initializing to `0.0` rather than NaN, so a never-measured `ece` emits a literal `0.0000` that reads as *perfect* calibration and would score full calibration credit via `_calibration_component`. There is no live gate impact today because SafetyGate does not consume `ece`/`auroc`, and the `confidence_is_real` gate fails closed on the real-`EvalResult` paths. The audit's boundary condition is the durable rule: **if real ECE is ever admitted to gating, the absence sentinel must be fixed first (init to NaN) or the `confidence_is_real` gate preserved** — otherwise absence impersonates perfection. Source: [safetygate-rlvr-provenance-audit-2026-07-22.md](../handoffs/completed/safetygate-rlvr-provenance-audit-2026-07-22.md).

### New (2026-08-25, the agent-security eval fixture is in-tree — and a PII gate failed red for 22 days)

- **Agent-security evaluation now has a disposable, deterministic, attack-surface-disjoint fixture in the tree.** TU-DTAP-1 imported an 18-case reviewed Apache-2.0 subset of DecodingTrust-Agent (finance + crm, all 5 injection families, 3 threat classes) into a stdlib-only local runner (`scripts/autopilot/evals/dtap/`, pinned upstream commit `e0323a521…`, LICENSE/README SHA-256s match intake-1021). Judges are fully deterministic state checks — 0 of 6,682 upstream configs use LLM checks, byte-identical 18/18 after transcription with per-file SHA-256. Failure attribution is the exact 8-set `model|parser|tool|endpoint|harness|judge|infrastructure|overflow`; traces are immutable SHA-256-chained with tamper/reorder/drop detection; repeated seeds + Wilson CIs; 66/66 tests with zero inference. **The load-bearing safety property is that attack payloads are fixed and target-disjoint — the harness contains no attack optimization**, so a measured robustness number cannot be confused with attack-search success (matched-target DTAP-RED results are an attack-search upper bound, not a general robustness score). Paired benign/direct/indirect arms give the negative-control axis this project otherwise lacks for agent security, and no upstream setup script was ever run on the host. TU-DTAP-2 (open, inference-gated) adds simulated-service environment effects (finance/gmail/slack/salesforce/paypal shims) so indirect-injection arms exercise environment state, not only tool calls. Sources: [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md), [progress 2026-08-25-mainA-evl46](../progress/2026-08/2026-08-25-mainA-evl46.md).
- **A secret-scanning allowlist and its eval fixture drifted apart, and the gate that would have caught it was red for 22 days unobserved.** The root candidate gate (`scripts/validate/candidate_eval_gate.sh`) has exited 1 since ~2026-08-03: `pii_fixture_eval` 39/40 because commit `8eeaf6c3` (2026-08-03) added `AKIAIOSFODNN7EXAMPLE` to `KNOWN_PLACEHOLDERS` in `scripts/hooks/pii_precommit.sh`, postdating the 2026-07-29 fixture. The failure was first observed during the 2026-08-25 L5 readiness closeout (EVL-38), verified to reproduce on HEAD before being reported, and deliberately left to the PII-hook owning session rather than fixed inside the readiness task. The general rule this extends the page's privacy-hygiene material with: **an allowlist edit is a fixture-evolution event — scanner, allowlist, and eval fixture must version together, and a gate that nobody's periodic path runs is a gate that can stay red for weeks.** Sources: [repo-readiness-scorer.md](../handoffs/active/repo-readiness-scorer.md) (2026-08-25 closeout), [progress 2026-08-25-mainA-evl38](../progress/2026-08/2026-08-25-mainA-evl38.md).

### New (2026-09-14, noninf sweep — PromptForge mutation safety: a validator that wrote the file it was validating)

**Confidence: verified** — read from `epyc-orchestrator` source at `origin/main` `35b05fde`; the fix landed in `7d4b40a8` + `c27eec6c` with 100 new unit tests. Zero inference; nothing here is a performance claim.

This is the 2026-08-16 *promotion-gate integrity* question asked one layer lower down. That block asks what an automated optimizer may **promote**; this one asks what it may **execute while deciding**. The answer on `origin/main` was: anything.

- **A validator that writes the thing it is validating is not a validator.** PromptForge's Tier-2 code-mutation path ran a four-layer `_validate_code_mutation` (`prompt_forge.py:1095`) whose last layer was an "import test": it wrote the **model-generated candidate over the live repo file** (`:1149`) and then `importlib.import_module()`-ed it (`:1157`). Two distinct defects in one step. The candidate's module top level executed **unsandboxed in the autopilot process**, with that process's full filesystem and network authority, on *every* proposal including ones later rejected — the validation step was itself the exploit primitive. And for the duration of the check the live file on disk **was** the unvalidated candidate, visible to any concurrent reader (a parallel session, a uvicorn reload, another test run); restore sat in a `finally`, so a crash or SIGKILL between write and restore left it published. **A path that reverts correctly is still a path that published.** The durable rule: validation must be a pure function of the candidate text, and if a check genuinely needs to run the candidate it is a separate subprocess with a temp copy, a timeout and no repo path on `sys.path` — never the live tree, never in-process. Source: [promptforge-mutation-safety-contract.md](../handoffs/active/promptforge-mutation-safety-contract.md) (RTG-55, MHS-1/MHS-2).
- **Prefer a static screen to dynamic validation when no caller consumes runtime behaviour.** The import test's stated purpose was "importable, no circular imports"; its sole caller reads only `(valid, reason)`. The replacement is `screen_static_safety()` — `ast.parse` plus a denylist walk, no subprocess at all. Dynamic validation was **removed rather than sandboxed**, because a sandbox is a permanent maintenance surface bought for a check nobody's contract needed. Source: `epyc-orchestrator` `docs/guides/meta-harness-operator-guide.md` (layer-4 section, rewritten with the change).
- **The denylist is three profiles, not one list.** (a) *Module level* may hold only a docstring, imports, defs/classes and assignments — a bare top-level call is the "does work at import time" signature. (b) *Capability*: imports must be in a 30-entry pure-stdlib allowlist or a first-party root; `os`/`subprocess`/`sys`/`pathlib`/`pickle`/`ctypes`/`importlib`/`socket`/`requests` and 11 more are banned; `exec`/`eval`/`compile`/`__import__`/`globals`/`locals`/`vars`/`input`/`breakpoint`/`memoryview` are never callable; `open`/`getattr`/`setattr`/`delattr` are restricted; calls rooted at a banned module and any `.system`/`.popen`/`.spawn` are rejected; dunder attribute access is rejected except `__name__`/`__doc__`/`__all__`, because `__class__.__subclasses__` is the standard escape. (c) *Strict inertness* for `new_file` proposals — the ratified `intake-1323` node denylist (Import, ImportFrom, With, While, Lambda, ClassDef, Raise, Global, Delete, Yield, Await) plus rejection of any underscore-prefixed name or attribute. Every profile is a named module-level constant so the operator amends it in one place.
- **Grandfathering is what makes a capability denylist deployable on files that already exist.** A whole-file screen over a real module rejects the module itself — `src/api/routes/chat.py` already calls `getattr`, and the allowlisted files import first-party code freely. So the screen parses the **original** too and grandfathers the import roots and dotted call names it already contained: a mutation is judged on **what it adds**, not on what the file has always done. The hard-banned call set is deliberately exempt from grandfathering. A parameterized test asserts a no-op mutation of all five allowlisted files still passes — that test, not the denylist, is the guard against a future denylist entry silently disabling the whole lane. Source: [progress 2026-09-14 noninf backlog](../progress/2026-09/2026-09-14-noninf-backlog.md).
- **A closed effect enum, normalized totally, is the cheap half of a mutation contract.** `MutationEffect` = `inert | constrain | expand | replace | unsafe | unknown`, carried on `CodeMutation.effect` and reported by both apply paths, which refuse `unsafe`. `normalize()` is **total**: aliases (`noop`, `override`, `add-only`, `MutationEffect.expand`) map in, and anything unrecognised becomes `UNKNOWN` rather than defaulting to benign — the same absence-must-not-impersonate-a-pass rule this page records for `ece`/`auroc`. Tokens truncate at 32 chars and reasons at 240, so model text can never arrive unbounded. The CONSTRAIN/REPLACE split is **derived mechanically** from the candidate (no original definition and no original line removed ⇒ add-only ⇒ CONSTRAIN; a new top-level def ⇒ EXPAND; otherwise REPLACE), which settles the lane's standing question of whether that risk prior needs its own label: it does not. Source: `epyc-orchestrator` `7d4b40a8`.
- **An enforced denylist plus a prompt that asks for the forbidden shape is a silent, total lane failure — and the drift guard belongs in a test.** Making inertness compile-time exposed that the MH-9 AutoMem `schema_evolution` prompt (`prompt_forge.py:1264`) asked the model for a class-based `MemoryAction` / `MemoryActionStore` contract with `from dataclasses import dataclass` — exactly what the strict profile rejects. Nothing would have errored: the lane would have proposed only rejects, forever, logged at WARNING. Per coordinator ruling the ratified denylist was kept and the prompt rewritten to the shape the screen admits (module constants plus pure public `def`s returning `(ok, reason)` instead of raising, no imports, no classes, no underscore names), with the rules stated to the model as enforcement rather than etiquette. The durable mechanism is the general convention: **any prompt that describes a shape an enforcement surface checks must ship that shape as a module constant and screen that exact text in CI** — here `MEMORY_SCHEMA_SHAPE_EXAMPLE` through `screen_static_safety(strict=True)`, plus a negative test that the old class-shaped proposal is rejected for ClassDef + ImportFrom + Raise. Otherwise prompt and enforcement drift apart and the failure is invisible by construction. Source: `epyc-orchestrator` `c27eec6c`.

## 2026-06-15 Update — Safety Became Tooling

- **Security review is now a dedicated skill scaffold.** The new review skill applies STRIDE, OWASP, and supply-chain checks, but only records findings after exploit-path validation succeeds. Source: [security-review-skill.md](../handoffs/completed/security-review-skill.md).
- **Source quarantine is enforced in the intake/rendering path.** Source-derived synthesis now lands in `SOURCE-QUARANTINE` blocks with provenance metadata and a validator, so instruction injection is handled as data hygiene rather than implicit trust. Source: [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).
- **The evidence plane and quarantine solve adjacent problems.** Quarantine keeps external text from becoming instructions, while the evidence plane keeps stale or superseded trial evidence from becoming planner memory; both are provenance controls. Source: [evidence-plane-event-sourcing-and-narrative.md](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md).

## Open Questions

- When should the warn-mode injection validator become blocking? It needs false-positive data from real intake diffs first.
- Should a warrant requirement (an accepted edit must cite the failure it fixes) ever become a gate, given that the only measured evidence says equivalent guidance suppresses breakthrough modifications? SG-W2's telemetry and the EV-14f known-null corpus are the two instruments that would answer it; both are filed and unbuilt.
- Is `src/diversity_gate.py` wired or deleted (SG-W3)? Leaving a second module named like the live acceptance gate in the tree is a recurring misreading hazard, not a cosmetic one.
- ~~Who reconciles the PII-hook fixture/allowlist drift?~~ **RESOLVED 2026-08-25 (mainA, operator-directed)** — the fixture is now a fixture-evolution event: case 1 pins the placeholder policy (`expected_match=false`), and two boundary cases were added (one-char-off lookalike must block; placeholder + real key on one line must block). `pii_fixture_eval` 42/42; `candidate_eval_gate.sh` green for the first time since ~2026-08-03.

- Should PromptForge's strict inertness profile admit an inert `ClassDef` and an allowlisted `ImportFrom` — a plain dataclass is harmless at import time — or is the prompt-side rewrite the permanent answer? Kept as-is because the denylist is ratified from `intake-1323`; the tradeoff is expressiveness in the schema-evolution lane against one more admitted node class. (2026-09-14)
- `apply_code_mutation` still writes the live repo file (git-checkpointed, pre-commit) rather than staging to a worktree first. The isolated path `apply_code_mutation_in_context` exists and nothing forces its use — validation no longer touches the tree, but application still does. (2026-09-14)
- `MutationEffect.UNKNOWN` is permitted by the apply gate — only `UNSAFE` is refused — so a hand-constructed `CodeMutation` that never passed the static screen can still apply. Tightening to "only screened effects apply" requires auditing every construction site. (2026-09-14)

- Should the security-review skill gain a wrapper command or CI gate, or remain manual until a concrete enforcement workflow exists?
- Which local reviewer model is best for OWASP-LLM analysis of the EPYC stack without self-blindness?

## Related Categories

- [Tool Implementation](tool-implementation.md) — security-review and quarantine validators are tooling surfaces.
- [Agent Architecture](agent-architecture.md) — lab jobs and intake workflows must preserve trust boundaries.
- [Knowledge Management](knowledge-management.md) — source provenance determines whether compiled wiki facts are safe to reuse.
- [Benchmark Methodology](benchmark-methodology.md) — the measurement-resolution half of the same gate: a warrant-blind gate that also cannot resolve its own deltas can be moved by noise in both directions.

## Source References

- [Frontier F5 intake injection hardening](../handoffs/completed/frontier-f5-intake-injection-hardening.md) — completed quarantine policy, renderer, validator, and canary.
- [Security-review skill](../handoffs/completed/security-review-skill.md) — two-pass STRIDE/OWASP/LLM/supply-chain review skill.
- [Fable 5 executive summary](../handoffs/completed/fable5-findings-00-executive-summary.md) — evidence-plane framing.
- [Evidence-plane event sourcing and narrative](../handoffs/active/evidence-plane-event-sourcing-and-narrative.md) — provenance-first narrative regeneration plan.
- [AutoPilot continuous optimization](../handoffs/active/autopilot-continuous-optimization.md) — SG-WARRANT block (SG-W1/W2/W3, all open): warrant-blind acceptance, the no-op guard, the measured cost of warrant requirements, and the dead `diversity_gate.py`.
- [Eval-tower loop robustness audit 2026-07-20](../handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md) — `measurement_guards.py` provenance (the 2026-08-03 fail-open incident) and ETR-1/2/3.
- [SafetyGate / RLVR-export provenance audit 2026-07-22](../handoffs/completed/safetygate-rlvr-provenance-audit-2026-07-22.md) — F3 absence-vs-zero for `ece`/`auroc`, the fail-closed `confidence_is_real` gate, and the confirmed-sound list.
- [Eval-tower verification](../handoffs/active/eval-tower-verification.md) — EV-14f known-null corpus as the cheapest exposure measurement for warrant blindness.
- [Tool-Use Eval Contract](../handoffs/active/tool-use-eval-contract.md) — TU-DTAP-1 done: the in-tree deterministic DTAP subset, typed outcomes, target-disjoint attack payloads; TU-DTAP-2 (live-model + simulated-service env effects) open.
- [Repo-readiness scorer](../handoffs/active/repo-readiness-scorer.md) — the 2026-08-25 L5 closeout and the surfaced PII-gate failure with its HEAD-reproduced attribution.
- [PromptForge mutation safety contract](../handoffs/active/promptforge-mutation-safety-contract.md) — RTG-55: MHS-1 (typed effect enum) and MHS-2 (compile-time inertness) closed 2026-09-14; MHS-3–MHS-6 open.
- [Progress 2026-09-14 (noninf backlog)](../progress/2026-09/2026-09-14-noninf-backlog.md) — the session record for the static screen, the grandfathering rule and the prompt/denylist drift guard.
- `epyc-orchestrator` commits `7d4b40a8` (static safety screen + `MutationEffect`) and `c27eec6c` (MH-9 prompt realigned to the denylist, shape example shipped as a screened constant), read against `origin/main` `35b05fde`. [confidence: verified — code-read + 100 unit tests]
- `epyc-orchestrator` `docs/guides/meta-harness-operator-guide.md` — the rewritten layer-4 validation section: what the screen rejects, and the lane's prompt/denylist drift guard. (Guide lives in the orchestrator repo, not epyc-root.)


## Compiled Update — 2026-10-21 (sweep 3): PromptForge guard specs and a special-token injection finding

- MHS-14 adds optional falsifiability fields to the `PromptMutation` record and a deterministic activation beacon; MHS-15 (warn-only, delta-only `prompt_interference_lint`, never a reject) and MHS-16 (read-only cumulative-drift report over accepted ships) are filed. The MHS-16 premise was verified 2026-10-20: `safety_gate.py` judges each ship against its predecessor (the tier baseline is overwritten at each promotion), checks only the aggregate (-5 percent) and per-suite deltas, and has no per-question passed-to-failed flip count. K4 records that the guards fail closed. ([promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md), 2026-10-20)
- HIL item 7 (executor/proposer isolation from answer keys) is a safety contract for the improvement loop: egress block, AP-54 fence on both arms, tripwire and decoy-rubric canary. ([HIL design](../docs/design/harness-improvement-loop-design-20261006.md))
- CT-12 (special-token injection): both the tokenizer probe and the served chat path were OPEN on the champion on 2026-10-20; the CT-12.3a orchestrator neutraliser landed on epyc-orchestrator main (`50f7ffbd`, 44 new tests) with CT-12.3b/c/d follow-ups filed. TOC-SP-8 separately proposes that error-bearing output never be LLM-summarised (not yet implemented). ([workspace-f8 progress](../progress/2026-10/2026-10-20-workspace-f8.md); [tool-output-compression](../handoffs/active/tool-output-compression.md))

Sources: [promptforge-mutation-safety-contract](../handoffs/active/promptforge-mutation-safety-contract.md); [HIL design](../docs/design/harness-improvement-loop-design-20261006.md); [workspace-f8 progress](../progress/2026-10/2026-10-20-workspace-f8.md); [tool-output-compression](../handoffs/active/tool-output-compression.md).

## Compiled Update — 2026-10-21 (sweep 4): the model-exec and model-artifact surfaces, and the injection-path fixes

**Confidence: verified for the code facts (orchestrator commits named, tests run) and the host probes; the open-model-backdoor literature claims are external and carried by intake entries with dive-verified anchors.**

- **Exposure found at orchestrator `50f7ffbd`.** `run_shell` allowlisted python3; model-exec children inherited the full API environment; nothing restricted egress; `HF_HOME` pointed children at a cache holding an HF token; the tool-call log lived in memory and recorded only successful calls. GGUFs and chat templates were pinned and verified at none of download, launch or re-pull. No handoff owned either side, so two were opened: `model-exec-containment.md` and `model-artifact-integrity.md`.
- **Containment landed (SEC-EXEC-1/2/4, orchestrator `644c6530`, `65fbdce3`).** A minimal child environment with a per-task scratch HOME for `run_shell` and `run_python_code` (fenced and unfenced), python and python3 removed from `run_shell`, the find/awk/sed exec refusals applied unscoped, and a durable rotated JSONL tool-call audit that also records refused, timed-out and errored calls (367 tests passed, 1 skipped). Host probes for the rest: `unshare -rn` fails EPERM, Landlock ABI 6 is present (network rules available); a re-probe as the service user and the `web_fetch` private-range deny remain open.
- **Artifact integrity (SEC-ART-1, root `a9fccdc21`, orchestrator `a9a3365a`).** `safe_download` pins the revision and writes a provenance ledger, new-model onboarding gained a Step 0, and a registry pin validator (warn or strict) plus a backfill planner exist; the strict flip waits on the backfill (SEC-ART-1.1). SEC-ART-4 is designed (design text in `model-artifact-integrity.md`), not built.
- **Injection-path fixes (orchestrator `a66e4f838ec8`, 934 tests).** The TOOL_OUTPUT marker is escaped, `skill_context` is neutralised at the REPL site, the document-scan flag note is logged, and the scanner ignores the neutraliser's zero-width space. On the server side CT-12.3b (V11-095) tokenizes control-token spellings in chat request data as plain text (opt-out `--chat-input-parse-special`); it rides candidate C2.
- **Cache-friendly injection, a safety-neutral change with a flag.** `fc02209d` packs SkillBank and routing-context blocks into content-addressed blocks of at least 256 tokens behind `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION` (default OFF, flag-off output pinned to the legacy strings, 18 new tests); only a 12-character sha256 prefix is logged.
- **Control-vector caveat.** v10 control vectors are additive only and qwen4exp has no `build_cvec` call, so a vector loaded on Q38FN silently does nothing; a published coder post-train headline (LCB 83 to 90) is very likely a cap or baseline artifact.

Sources: [Model exec containment](../handoffs/active/model-exec-containment.md), [Model artifact integrity](../handoffs/active/model-artifact-integrity.md), [Qwen chat template evaluation](../handoffs/active/qwen-chat-template-evaluation.md), [Progress intake backdoor-cvec](../progress/2026-10/2026-10-21-intake-backdoor-cvec.md), [Progress inj-fix](../progress/2026-10/2026-10-21-inj-fix.md), [Progress cachefriendly-inject](../progress/2026-10/2026-10-21-cachefriendly-inject.md), [Progress workspace-f8](../progress/2026-10/2026-10-21-workspace-f8.md)

## Compiled Update — 2026-10-21 (sweep 5): CT-18's first static-attack ASR numbers

**Confidence: verified** for the recorded run. **Wording rule CT-20 applies to every figure here.** Each one is a `static-attack ASR on fixture set ib2-ct18-v1` (IB2) or `skillinject-canary-v1` (Skill-Inject). These are static evidence, never a robustness claim. CT-18 is NOT ticked.

- **Setup.** Both roles ran at temperature 0, seed 7 and max_tokens 256, with thinking OFF, the `epyc-qwen3x-v1-terse` template and no speculation.
  - **The arms.** A is the current prompt, B adds a data-not-instructions sentence, and C adds the sentence plus a per-call U+E000-class datamark.
  - **The worker.** Qwen3.6-35B-A3B-MTP-Q8_0 on CPU. This is a deviation: the Gemma-4-26B worker was retired and its GGUF is not on disk, so the Gemma-4-26B 44% prior (`intake-2269#record`) does not apply.
  - **The architect.** Qwen3.8-27B-Q8_0 on the MI210, with VRAM ~29.7 GB sampled.
- **IB2 (24 fixtures, all arms complete).**

  | Role | Conflict-variant ASR, A / B / C | Aligned-twin compliance, A / B / C | Clean utility, A / B / C |
  |---|---|---|---|
  | worker | 45.8% / 25.0% / 4.2% | 95.8% / 91.7% / 83.3% | 95.8% / 95.8% / 91.7% |
  | architect | 45.8% / 4.2% / 4.2% | 75.0% / 79.2% / 66.7% | 95.8% / 95.8% / 95.8% |

  The paired discordants run in one direction. Worker A-vs-C is 10 / 0 (a_only / b_only), and architect A-vs-B is 11 / 1. The defences are not free on the worker, though: A-vs-C lost 3 aligned-twin compliances and gained 0.
- **Skill-Inject (conflict variant, partial).** At the hard stop the architect had n=100 of 317 items: A 29%, B 17%, C 23%. The worker had n=22, too small to read. Items are the first N of a fixed order, not a random sample.
  - **Later segments.** These moved the architect to 128/317 and the worker to 51/317. Registered compute fillers finish the arms in granted gaps, resuming from the RESULTS files.
  - **Import differences.** The import has 319 structural pairs where the paper has 202. The original attack text is deliberately not imported: each pair keeps its structure plus the original's sha256, and carries a benign canary.
- **Belief kernel.** IB2 and SP1 are wired (VB-IBENCH-WRITE). The Skill-Inject arms are a third fixture set whose runner does not call the writer, so VB-CT18-SKILLINJECT-WRITE is filed. Partial arms must not project as complete.

Sources: [Qwen chat template evaluation](../handoffs/active/qwen-chat-template-evaluation.md), [Progress ct18-run](../progress/2026-10/2026-10-21-ct18-run.md), [Progress ct18-resume](../progress/2026-10/2026-10-21-ct18-resume.md), [Vidya belief-substrate program](../handoffs/active/vidya-belief-substrate-program.md), [Compute fillers guide](../docs/guides/agent-workflows/compute-fillers.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 12, workspace-58 over f8's SEC delta): code landed, enforcement still off by default

**Confidence: verified** for what landed (commits and tests cited in the handoffs); nothing here is enabled in production yet.

- **Artifact integrity.** Launch-time GGUF fingerprint and served-template hash checks are wired into the launcher (`TemplatePinError` refuses before `Popen`); a community fine-tune cannot get tool access through stack-change without a recorded review (SEC-ART-3, `uploader_class` on 14 lineup roles); `safe_download` refuses a re-pull whose commit sha or any LFS oid drifted from the pin unless a review record is passed (SEC-ART-7); and a relay/sidecar check compares a claimed copy against its upstream file by file (SEC-ART-9). Still owed: one scheduled IO window to fingerprint every lineup GGUF, the operator's signature on four template-diff reviews, lineup-wide template pins, a live launch proof, and publishing templates to the content-addressed store (SEC-ART-POST-a..e).
- **Exec containment.** Landlock (TCP connect/bind deny) plus a seccomp shim for `run_shell`/`run_python_code` children, a credential read-deny with a token-free HF_HOME, a private-range/link-local `web_fetch` guard, and first-seen-host / write-outside-root audit flags all landed behind flags that default OFF; containment refuses visibly when the host cannot enforce. The enable order is an operator decision (SEC-EXEC-POST-e; recommended: observe-only flags first, then the web guard, then containment, one reload each), after the nextplaid containers are recreated without the old cache-root mount.
- **Secrets.** hf_ and W&B key patterns are in the PII pre-commit hook for every repo including epyc-web, and a name-only history scan exists. The same hook kept a ROCr disassembly listing out of the GPUPIN package commit because it flagged its addresses; the package carries the regeneration command instead.

### Source References (2026-10-22 wrap-up sweep 12)

- [handoffs/active/model-artifact-integrity.md](../handoffs/active/model-artifact-integrity.md) — SEC-ART landings and POST-a..e
- [handoffs/active/model-exec-containment.md](../handoffs/active/model-exec-containment.md) — SEC-EXEC landings, POST-c..e decision package
- [progress/2026-10/2026-10-22-workspace-58.md](../progress/2026-10/2026-10-22-workspace-58.md) — section 17.3 (PII hook on the disassembly file)

## Compiled Update — 2026-10-22 (wrap-up sweep 13, workspace-f8): template-pin coverage is complete, but the pins do not reach the launcher yet

**Confidence: verified** for the registry contents and commits cited; the enforcement gap is a static reading of the compiled registries, not a launch test.

- **Template-pin coverage (SEC-ART-POST-c).** All four lineup roles (frontdoor, architect_general, architect_critic, worker_vision) carry 64-hex `served_template_sha256` pins that match today's bytes. Research `c4017b4f4` adds served-only pins for the two non-lineup roles with a GGUF on disk.
- **Master-registry pins are not enforced at launch.** The orchestrator's lean registry and `stack_priors` carry no sha256 or template pins. A pin written to the master registry therefore protects nothing until a stack-change recompile carries it into the launcher's inputs (SEC-ART-POST-f). Flipping `pins_strict` or `template_pins_strict` before that recompile would give false assurance.
- **Template store ordering (SEC-ART-POST-e).** The registry re-point to the content-addressed store is prepared on a research branch but cannot land first, because a re-point to a digest the store does not hold breaks the launch. The order is: publish, land the re-point, recompile.
- **Secret history scan.** The name-only scan over ~18.7k commits in 4 repos found 0 real secrets.

### Source References (2026-10-22 wrap-up sweep 13)

- [handoffs/active/model-artifact-integrity.md](../handoffs/active/model-artifact-integrity.md) — SEC-ART-POST-a..f
- [handoffs/active/model-exec-containment.md](../handoffs/active/model-exec-containment.md) — SEC-SECRETS-1 history-scan result
- [progress/2026-10/2026-10-22-workspace-f8.md](../progress/2026-10/2026-10-22-workspace-f8.md) — late-evening section

## Compiled Update — 2026-10-22 (wrap-up sweep 15, workspace-58): the template store is published, the HF token is revoked, and the exec guards go on in stages

**Confidence: verified** for the published store (`verify`: 1 entry, 0 problems), the container mounts (`docker inspect`) and the recorded operator decisions. The guard effects are **open**: none of the three flags is on yet.

- **Read-only template store (SEC-ART-6, SEC-ART-POST-e, operator decision (c)).**
  - The override template is published content-addressed at `/mnt/raid0/llm/models/chat-templates/sha256/1443ea9a….jinja` (file 0444, dir 0555).
  - Research main `95f90f04f` re-points frontdoor and architect_critic to it.
  - Still open: the lean-registry recompile, without which the launcher does not see the pins (SEC-ART-POST-f), and the operator-side root ownership / `chattr +i` decision. Until then the files are still same-uid-writable.
- **HF token hygiene (SEC-EXEC-6, option (a)).** The token files were deleted 2026-10-21. The nextplaid-code and nextplaid-docs containers were recreated one at a time with a `huggingface/hub`-only mount (SEC-EXEC-POST-c), and the mount was verified with `docker inspect`.
- **Exec guards (SEC-EXEC-POST-e, operator Option A, staged).**
  - The order is `exec_write_flags` (observe-only), then `web_fetch_guard`, then `exec_containment`.
  - Each step is one API reload, run manually by the operator, plus a live proof (SEC-EXEC-POST-e1..e3).
  - Step 1 is on orch branch `f8/exec-guards-step1` @ `a73af3cc`.

### Source References (2026-10-22 wrap-up sweep 15)

- [handoffs/active/model-artifact-integrity.md](../handoffs/active/model-artifact-integrity.md) — SEC-ART-6, SEC-ART-POST-e
- [handoffs/active/model-exec-containment.md](../handoffs/active/model-exec-containment.md) — SEC-EXEC-6, SEC-EXEC-POST-c, SEC-EXEC-POST-e1..e3

## Compiled Update — 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23)

- **Template sign-off decision.** The operator chose to sign all 4 `template_diff_reviewed` entries now and strip the injection in a v2 template (SEC-ART-POST-b.1). The signature attests the served bytes as reviewed. The CONCERN is a template-authored "SYSTEM WARNING" appended inside `<tool_response>` on error keywords, on frontdoor and architect_critic.
- **One ratify command, pinned twice.** The script pins the four diff sha256s at research `62c2e09da` and the sha256 of the private review digest (`50c35774...`, never committed). Modes are `--dry-run` (default), `--verify` and `--apply` with an attest string and the digest. It was prepared on a branch and is not ticked until the operator runs it.
- **Exec guard step 1 is live.** The 14:59:25Z API-only reload (pid 3932317, orchestrator `a73af3cc`) carries `EXEC_WRITE_FLAGS=1` with `WEB_FETCH_GUARD=0` and `EXEC_CONTAINMENT=0` (observe-only). Proof (1) is still owed: the audit log held 6 records, all pre-reload, each with `write_outside_root` null. Tick on the first post-reload record carrying the field.
- **Backup retention fills the shared volume.** The daily 7.7 GiB tarball job kept 14 copies (~108 GiB) on the same volume as the models. Operator decision: keep 3 locally plus the off-device mirror. About 250 GiB of the volume is invisible from the container (suspect: host docker data); the host agent runs only read-only `du`/`docker system df`, no prune.
- **Hook false positive fixed.** The PII `account_number` rule (12-19 digits) blocked llama-bench `model_n_params` values in any repo. After the operator D9 ack, `n_params` joined the self-describing keys; fixture eval is FA 0/23, FR 0/32 (was FR 1/32).
- **Memory telemetry for the next OOM.** A 30 s sampler (`mem_sampler.py`, 4 tests) was written because the earlyoom incident left no memory sample on disk; it is not running until the host cron starts it.

Sources: [Model artifact integrity](../handoffs/active/model-artifact-integrity.md), [Model exec containment](../handoffs/active/model-exec-containment.md), [Non-inference backlog](../handoffs/active/non-inference-backlog.md), [Progress 3c4ca599](../progress/2026-10/2026-10-23-3c4ca599.md)

## Compiled Update — 2026-10-29: PromptForge mutation-safety items reconciled

- **MHS-9 closed by audit:** `revert_code_mutation`'s new-file revert now commits an explicit pathspec (`git add -A -- <path>` plus `commit --only`) rather than a sweep (orchestrator `25c8e913`, 2026-09-16).
- **MHS-3d closed by audit:** the v10 episodic re-pin was operator-ratified (receipt emitted 2026-09-17, commit `810a6a829`) after the HumanEval/55 eval-leak memory purge.
- **CT-21 safety read:** Skill-Inject ASR showed no improvement from the flag on fixture sets (see Chat Templates); no robustness claim is made.

Sources: [promptforge-mutation-safety-contract handoff](../handoffs/active/promptforge-mutation-safety-contract.md); [qwen-chat-template-evaluation handoff](../handoffs/active/qwen-chat-template-evaluation.md); [CT-21 aggregate verdict](../artifacts/chat-templates/ct21-verdict-20261027/AGGREGATE.md)
