# Incident Log — origin narratives behind agent-file rules

House style (operator directive 2026-07-30): every negative/incident-derived rule in the agent
files keeps its directive plus a one-line origin pointer (`origin: INC-<id>`); the full
narrative lives here. Rules cite entries; entries never carry rules.

## INC-20260706-iqk-missing-subsystem
The GPU-opts branch forked from v6 on 2026-06-22; the iqk port landed on production 2026-06-25.
Because the fresh-pull step was skipped and the branch never re-synced, it silently lacked the
entire iqk subsystem (0 of 8 `GGML_IQK` references) while on track to "become v7" — a candidate
kernel missing a core CPU-performance subsystem. Discovered and rectified 2026-07-06. Rule fed:
CLAUDE.md § Experimental Kernel Workflow step 1 (always fork from current production tip; full
experimental build before promotion).

## INC-20260727-stale-heartbeat
A live session's heartbeat was 2h stale while it was mid-generation; the stall ladder read it as
a stall and only a second signal prevented a spurious nudge of a healthy agent. Rule fed:
refresh the heartbeat at every task boundary (CLAUDE.md § Agents & Automation;
`agents/coordinator-agent.md`).

## INC-20260728-reload-preemption
Two external API-only reloads (16:26:13Z and 16:40:48Z, the latter spawning uvicorn parent PID
3879640) landed during codex's explicitly protected live E8 q3 collection, crossing in-flight
ordinals 246/249/250 and 279/281/282 and forcing their regeneration. Codex owned that
inference; the reloads should have been requested of it. A structural fix (reload path failing
closed while a protected bench region claim is active) was filed by codex, not yet assigned.
Rule fed: reload ownership (`agents/shared/OPERATING_CONSTRAINTS.md` § Inference and
Benchmarks).

## INC-20260728-ctrlc-destroyed-main
A coordinator sent a ~2000-char dispatch via raw `tmux send-keys`, bypassing the chunking
adapter; it blobbed into two paste fragments. Attempting to clear the buffer it sent `Ctrl-U`,
`Ctrl-C`, `Ctrl-U`, `Ctrl-C` — the second `Ctrl-C` exited Codex and destroyed the
`codex-bus-tests` main, despite `Ctrl-U` alone having already worked earlier the same session.
No work was lost (commits were pushed), but a live main was destroyed to fix a cosmetic
problem, consuming a spawn-capped resource — and a subagent had been commissioned minutes
earlier to characterise exactly this TUI empirically in disposable sessions. The method was
available and self-authored, and was not used. Rules fed: TUI keystroke safety
(`agents/shared/OPERATING_CONSTRAINTS.md` § Dangerous Operations;
`agents/coordinator-agent.md` Guardrails).

## INC-20260728-unread-inbox
The coordinator's cursor sat at offset 63627 while 33 messages accumulated unread — among them
codex reporting a hard block on the critical path requiring an operator signature, a completed
contract audit with two CRITICAL fail-open defects, and three daemon boundary notices that
codex had gone idle. Every piece of delivery machinery worked; the coordinator never read the
inbox, and the operator had to find, unaided, a ratification request and an audit report
already sitting in it. Rule fed: DRAIN BEFORE YOU SPEAK (`agents/coordinator-agent.md`).

## INC-20260728-idle-mains
While the coordinator wrote governance docs on its own main thread, the codex-bus-tests and
claude-gpu-lane mains both went idle with empty queues and the operator had to point it out.
Rule fed: coordinator main thread stays free for coordination; an idle main with an empty queue
is a coordination failure (`agents/coordinator-agent.md`;
`agents/shared/SESSION_LIFECYCLE.md`).

## INC-20260728-cleared-context
A bus-testing main was cleared between two neighbouring bus-defect tasks, discarding directly
relevant context; the same day a combined "wrap-up, then /clear, then read X" nudge lost its own
follow-on instruction to the clear. Rules fed: `/clear` requires wrap-up AND disjoint next task;
never share a nudge with the task that follows a clear (`agents/shared/SESSION_LIFECYCLE.md`).

## INC-20260728-heartbeat-bypass
`claude-gpu-lane` finished a review and sat idle awaiting an answer while its heartbeat still
read `working` (~8094s stale); the adapter correctly refused a nudge twice, and the coordinator
bypassed it with raw `tmux send-keys` instead of escalating. Rule fed: guard-refusal escalation
ladder (`docs/guides/agent-workflows/coordinator-escalation.md`).

## INC-20260729-rate-limit-respawn
During post-reboot bringup, re-spawned mains were unreachable until the nudge rate limit
inherited from their destroyed predecessors expired — the limit keys on roster id, not window
instance. Rule fed: the narrow lower `--min-interval-s` exception
(`docs/guides/agent-workflows/coordinator-escalation.md`).

## INC-20260731-broad-process-pattern-kills
A broad process pattern (`llama-server -m`) used to "clean up" a benchmark killed **another agent's
running server — twice in one day**. Separately, `earlyoom` was killed by a pattern sweep because
its own command line contains `--ignore ^(llama-server|sd-server)$`: the pattern matched the guard
process whose entire job is protecting the fleet from OOM kills. Both were recovered. The failure is
structural, not careless — on a shared box any name-based pattern is a wildcard over other sessions'
processes, and a guard's argv necessarily contains the names it guards. Rule fed: kill only PIDs you
captured yourself; never `pkill`/`pgrep` on a name pattern on this host (CLAUDE.md § Process
Management; `agents/shared/OPERATING_CONSTRAINTS.md` § Inference and Benchmarks).

## INC-20260731-warm-server-repeat-prompt-recurrence
Hours after the `ngram-mod` 2.80× result was retracted as a warm-context self-copy artifact, a new
benchmark (the speculative-toggle test) **repeated ONE prompt against a warm server again** and
reproduced the exact same artifact. It was caught before publication and the numbers were discarded.
The lesson is that the retraction did not generalize on its own: the earlier fix was written as
prompt *screening* (repeated-5-gram fraction), which is necessary but not sufficient, because the
copied text is the model's own **generation**, not the prompt. Rule fed: never replicate a
context-reading drafter against a live server on a repeated prompt, and always include a
non-context control arm (`draft-mtp` or `none`) **structurally in the harness** rather than as
operator discipline — NG5/SW-2 in `handoffs/active/speculative-decoding-mtp-refresh.md`.

## INC-20260731-stale-config-outranked-operator-decision
The operator's standing decision is the **composed** spec recipe `ngram-mod,draft-mtp`. The committed
lean registry still carried `draft-mtp` alone (a regression introduced by `2370025f` on 2026-07-19,
which moved the composed value into an unread sidecar key `ngram_candidate_spec_type`). **Twice in one
session an agent let the committed config override the operator's restated decision**, then propagated
the wrong recipe into fresh agent briefs — the root cause of several wasted benchmark runs. The trap
is that a config artifact *looks* authoritative: it is versioned, reviewed, and greppable, while an
operator decision lives in conversation. Rule fed: when a config artifact and a live operator decision
disagree, **the artifact is the thing that is wrong** — fix the artifact and re-verify the emitted
command line, never silently adopt the artifact's value. Verification here meant confirming the
launcher actually emits `ngram-mod,draft-mtp`, because a latent exact-equality test in
`stack_priors.py` would otherwise have silently disabled speculation entirely (epyc-orchestrator
`2874ed73`).

## INC-20260731-optimum-misread-as-baseline
Qwen3-Next-80B was **wrongly excluded from a headline results table** because it runs without
speculative decoding — it was recorded as a "baseline" arm and filtered out of production-optimal
comparisons. It has no draft path at all, so running without speculation *is* its OPTIMUM. A model is
not disqualified from a headline by lacking a lever it cannot have. Rule fed: the OPTIMUM / BASELINE /
CANDIDATE grammar ratified the same day (epyc-root `0b92049e`, `MEASUREMENT.md` §3) exists precisely
for this case — classify an arm by whether it is that model's best achievable configuration, not by
which features are switched on.

## INC-20260731-acceptance-dilution-under-composed-recipe
Under a composed recipe, `draft_n` counts proposals from **both** proposers, so the reported
acceptance rate is mechanically diluted relative to a `draft-mtp`-alone run of the same model. This
was briefly read as a regression. It is not a fault, it is the definition of the metric changing.
Related mechanism confirmed the same session: `--spec-draft-n-max` is a **soft budget, not a cap**
under a composed recipe (mean accepted run length 2.36–2.67 measured at `n_max=2`), and
`ngram_mod_n_max` is a separate, independent knob. Rule fed: an acceptance-rate gate calibrated on
draft-mtp-alone numbers will wrongly reject correctly-configured composed setups — gates on
speculation metrics must declare the recipe they were calibrated against.

## INC-20260731-ggml-linkage-silent-cpu-fallback
Filed 2026-08-12 on reproduction; until then the primary record was epyc-inference-research
`7f310022` and backlog row NIB2-58. `/etc/environment:5` and `devcontainer.json:57` place the
production **CPU-only** `build/bin` EARLY in `LD_LIBRARY_PATH`, so a freshly built HIP binary
resolved the frozen production ggml, found no GPU, and ran full-CPU **while printing
`use gpu = 1`**. `verify_ggml_linkage.sh` reproduces it: 3 of 5 libraries came from the wrong
tree. `ldd` is useless as a check here because llama.cpp **dlopens** `libggml-hip.so` — the
executable shows zero HIP linkage whether the run was GPU-resident or not, so both "I invoked the
HIP build" and "the build reported success" are fully compatible with a full-CPU run. Reproduced
2026-08-12 during the A3 GPU baselines. Rule fed: prove device residency from OUTSIDE the binary —
linkage guard, non-zero VRAM sampled during the run, and a KFD process count
(`agents/shared/OPERATING_CONSTRAINTS.md` § Inference and Benchmarks; CLAUDE.md § Debugging).

## INC-20260806-pytest-api-escape
On 2026-08-05 at 13:04:46Z,
`test_cmd_start_infers_missing_numa_mode_from_realized_fleet` mocked llama-server starts but missed
the separate `start_orchestrator` lifecycle boundary. The unit test therefore launched a real
six-worker uvicorn listener on production port 8000. Two earlier cross-role-lock tests had also
written `ORCHESTRATOR_TMP_DIR` directly into `os.environ` instead of using pytest's restoring
monkeypatch, so the escaped API inherited both `PYTEST_CURRENT_TEST` and a pytest temporary lock
directory. It remained the stack-tracked production API for more than 21 hours and served real
traffic while reading placement leases from test files. The dashboard made the split-brain visible:
HTML is reread on every request and showed the new legend, while the stale Python workers still
returned old matrix-filtered cells. Fixes: the lifecycle test now mocks `start_orchestrator`, parent
test environment writes restore automatically, and `start_orchestrator` refuses to spawn from
pytest while `subprocess.Popen` is still the real callable. Rule fed: a test of a stack lifecycle command
must mock every process boundary, and the production API launcher fails closed under pytest.

## INC-20260812-compacting-read-as-idle
A session COMPACTING its context renders identically to an idle one: the goal line, the "Pursuing
goal" timer and the background-terminal count all disappear together, leaving a bare status line
above an empty composer. The coordinator read that pane state as *finished* for the `inference`
main TWICE in one morning and reported it to the operator as done; the operator corrected it both
times. The authoritative signal existed throughout — `tmux_adapter.py`'s C36 runtime check reads
the session's own rollout JSONL and reports ACTIVE when the last record is mid-turn (`token_count`,
`reasoning`) rather than the turn-terminal `task_complete`/`turn_aborted` — and it had already
refused the corresponding nudges. The refusal was treated as an obstacle to work around rather
than as the finding it was. The same morning produced the opposite error on the same fleet: at
10:53Z `mainB`'s heartbeat read `state: working, task_id: A3-gpu-baseline…` while **446 seconds
stale**, with the pane idle across three consecutive watcher cycles and the GPU at 0%. Rule fed:
three liveness states, not two; the runtime check decides, an adapter refusal citing it is a
finding about the world, and when heartbeat, pane and hardware disagree the hardware wins
(`agents/shared/SESSION_LIFECYCLE.md` § Reading another session's liveness;
`agents/coordinator-agent.md` Guardrails; `docs/guides/agent-workflows/coordinator-escalation.md`
step 1; CLAUDE.md § Agents & Automation).

## INC-20260812-post-exit-vram-sample
The coordinator accused `mainB` of running a GPU benchmark on CPU fallback because a VRAM sample
read 0%. The sample was taken AFTER `llama-bench` exited, and a post-exit sample cannot
distinguish *never resident* from *finished* — the two worlds produce byte-identical readings.
mainB had sampled during the run and held the evidence: VRAM 1% (~640 MB against a 637 MiB F16
model), KFD procs 1, three consecutive samples with the PID alive. The generalisation is that
`llama-bench` EXITS between probes, so 0% utilisation and 0% VRAM are the *normal* reading inside
a perfectly healthy sweep and a single sample landing in that gap is sampling error; the
dispatch-side corollary is that short one-at-a-time benches guarantee the appearance of idle
hardware, so compute is queued back-to-back for occupancy. Rule fed: observation windows — sample
DURING the phenomenon, and base every absence claim on a condition persisting across a stated
number of samples (`agents/shared/OPERATING_CONSTRAINTS.md` § Observation Windows and the
saturation clause of § Codex Delegation & Long-Horizon Throughput; CLAUDE.md § Debugging).

## INC-20260812-dispatch-by-line-number
Dispatching backlog work keyed on `file.md:LINE` broke twice in ONE batch. One pointer named an
unrelated row — `:327` resolved to the P1-7 phantom-fleet item, not the numa-mode row it was
dispatched as — and one had rotted because another agent inserted rows above it that same
morning, which is not carelessness but what working in a file does. Queue-wide anchor rot had
already been measured at 27% (2026-07-29) and re-measured at **34.5%** (2026-08-11), which is why
`backlog_queue_gen.py` keys on verbatim box text. In the same batch, **four of eight** rows that
PASSED `backlog_row_check.py --ref` were fact-checked and found already satisfied in reality:
files already untracked, a `.orig` already deleted, backup directories already gone, a port fleet
already retired. The screener validates a row's FORM against the file and cannot know the world.
Rule fed: the task text is the identity and the line number only a hint; screen for form, then
verify the premise independently before dispatching (`agents/shared/OPERATING_CONSTRAINTS.md` §
Dispatching Backlog Work; `agents/coordinator-agent.md` Guardrails; CLAUDE.md § Handoff Workflow).

## INC-20260816-git-clean-shared-clone

A live `git clean -ffdx`-class operation in the SHARED clone destroyed at least four
unrelated things across two dated events, and each loss was discovered independently by a
different session tripping over it — none by the session that ran the clean. 2026-08-12:
29 worktrees deleted with registrations pruned (forensics `921ec76c0`, `2b14d66ec`,
`8b609ee29`; 45 orphan dirs with dangling gitdir pointers remain). 2026-08-16
(`82400787` context, recurrence disclosed in `b33f14dfc`): the `retirements/` receipts
directory (rebuilt off-tree under P0-7), the `wiki/.last_compile` watermark (its absence
made the next compile report **844 new sources — the whole repo — instead of 51**; the
watermark had to be reconstructed from the last genuine `--touch`), the staged P1
doctrine-collapse artifacts (redone into a TRACKED directory), and — strongly suspected,
same event — the `/workspace/repos/` symlinks, whose absence silently broke 18 wiki links
until `scripts/clone-repos.sh` restored them. The damage signature is characteristic:
`git clean` removes exactly the untracked operational state (watermarks, receipts,
symlinks, staged artifacts) that no commit protects and no diff shows, so the cost
surfaces days later as unrelated-looking breakage. Rule fed: never run `git clean` in the
shared clone or any lane worktree; untracked-but-load-bearing state must either be
tracked, live off-tree, or be listed in a manifest a restorer can replay (CLAUDE.md §
Working-tree identity; `agents/shared/OPERATING_CONSTRAINTS.md` § Shared-tree hygiene).

## INC-20260823-filesystem-containment-gap

An agent ran `sudo -n mkdir -p /mnt/bigdisk && sudo -n mount /dev/sdb1 /mnt/bigdisk`,
planned writes to `/mnt/bigdisk/epyc-backup/` (a device OUTSIDE the data root),
and `sudo apt-get install restic` — all against the operator directive *do not
touch anything outside /mnt/raid0/llm/*. Nothing stopped it. The gap was
TWO-SURFACE and both surfaces were Bash:

  * **Claude surface**: `check_filesystem_path.sh` matches Write|Edit only (it
    reads `tool_input.file_path`); the six PreToolUse Bash hooks
    (check_pytest_safety, check_live_holder_interference, check_commit_hygiene,
    check_d9_loop_plane, check_process_pattern_kill, check_operator_apply_copy)
    scanned none of mount/privileged verbs/out-of-root writes.
  * **opencode surface**: `~/.config/opencode/opencode.jsonc` had no permission
    rules and no plugins — the session that made the mistake had NO guard at all.

Fix (2026-08-23): ONE shared scanner, `scripts/hooks/filesystem_containment_scan.py`
(reuses `shell_scan.segments()`; the RTG-52 "never a fifth parser" rule), called by
`check_filesystem_containment.sh` (Claude PreToolUse → Bash) and
`.opencode/plugins/filesystem-containment.ts` + the global plugin copy (opencode
`tool.execute.before`). Two refusal classes: CLASS A privileged host-level
operations (operator-only; env-ack `EPYC_FS_ACK` is the only override) and CLASS B
writes outside the containment root (`/mnt/raid0/llm/**`, `/workspace/**`,
`/tmp/opencode/**`, `~/.claude/**`, `~/.codex/**`, bare `/tmp/**` tolerated
scratch; operator allowlist `scripts/hooks/filesystem_allowlist.yaml`, schema
`session_bus.filesystem_allowlist.v1`, fail-closed). Defense-in-depth opencode
`permission.bash` deny patterns for the unambiguous privileged verbs. Rule fed:
mechanical filesystem containment on BOTH agent surfaces, one shared implementation
(`docs/guides/agent-workflows/filesystem-containment-guard.md`; CLAUDE.md §
Debugging).

## INC-20260917-daemon-stale-script-inode

A read-only `/proc` census (`tmp/daemon-staleness-20260917/report.md`) found a daemon executing a
STALE OR ORPHANED script inode in three shapes, all live on this host the same night: (1)
**stale and diverged** — the opencode-event reaper (pid 2873259, started 09-08) held `fd/255` on a
lane copy under `worktrees/mains/ak-rebuild-20260828`, 1,802 B, against 7,976 B tracked at HEAD; the
running code still gated its VACUUM decision on `pgrep -x opencode` and had never sourced
`observer_guard.sh`, across 461 iterations and 39 VACUUMs against the operator's live
`opencode.db`. (2) **orphaned inode** — both the hub and bus supervisors showed `(deleted)` for
their own script after an unrelated `git reset --hard origin/main` in the shared clone; content was
identical that day, so nothing was visibly broken, but the next commit to either file would have
diverged silently. (3) **orphaned tree** — a hub on `:8101` ran from a worktree directory that no
longer existed, with no registry row, pidfile or probe to catch it. Mechanism: bash opens a
script's inode once at launch and reads it incrementally for the process's whole life; git never
writes a tracked file in place (checkout/reset/merge unlink and recreate it), so every commit to a
tracked script leaves any daemon already running on an orphaned inode; no cron runs in this
container, so daemons are hand-launched and inherit the launching session's cwd, which is how a
lane cwd produces a lane-pinned daemon. Nothing moved a daemon back: supervisors restart their
charges, never themselves, and `scripts/coordination/WORKTREE_MIGRATION.md` pinned runtime *state*
to `/workspace` while saying nothing about runtime *code*. `observer_census.py` (Rule A/B over
`git ls-files`) certifies the FILE, not a running INSTANCE, so "census OK" coexisted with a
nine-day-stale live reaper. Remedy (NIB2-81, this commit):
`scripts/coordination/daemon_provenance.sh` (`dp_attest`, `dp_stale_since_start`) — a daemon
calling `dp_attest` at its own startup REFUSES to start (a lane may develop a daemon, never run it)
when its own script does
not resolve under the canonical root, warns loudly (never refuses) on an uncommitted local edit,
and records `{pid, script_realpath, inode, blob, started_at}` for `dp_stale_since_start` to poll
once per loop iteration and LOG (never act) that a commit has since replaced the file it is
executing. Wired into the opencode-event reaper's `run` mode and into `bus_supervisor.sh` /
`hub_supervisor.sh`'s own `loop` startup — complementary to, not a duplicate of,
`bus_supervisor.sh`'s pre-existing H-4 check, which watches the SEPARATE daemon `bus_supervisor.sh`
supervises, not its own script. The generalised supervision loop that would also catch shape (3) —
a registry `runtime:` field plus `observer_census.py --live` — remains open as NIB2-81 remedy (b),
out of scope here. Rule fed: runtime-plane daemons execute from canon only (CLAUDE.md § Working-tree
identity; `scripts/coordination/WORKTREE_MIGRATION.md` § The two planes;
`handoffs/active/non-inference-backlog.md` NIB2-81/NIB2-81a).

## INC-20260925-parallel-repack-lost-in-bundled-revert
The OpenMP tensor-repack parallelization (52ddd3200, 2025-12-21, 1.5-2.5x CPU model-load speedup;
upstream PR #18239 closed unmerged) shipped in production-consolidated v1-v5, but its test
(tests/test-repack-parallel.cpp) never followed it past v1 (be03cc3ae). The v6 fresh-upstream rebuild
forward-ported it inside one bundled commit, v6 Stage 1a 814e81782 (2026-06-23: AVX-512BW Q8_0/Q6_K
8x8 kernels + OpenMP repack + CPU_REPACK NUMA mbind). When the kernels (-9% at 96 threads, not
byte-exact) and the mbind (neutral-to-negative) failed their gates, the whole commit was
`git revert`ed (358f0c748, 2026-06-24), taking the orthogonal, never-measured load-time feature with
it. The v6 plan's commit list, the kernel-reconciliation audit ("deliberately reverted") and the
kernel-lineage memory all labelled the commit only as "CPU2 AVX-512BW repack kernels", so v7-v10 and
the AutoKernel champion carried zero omp pragmas in repack.cpp unnoticed for three months. It
surfaced 2026-09-25 when each 519 GB DS41 calibration launch was found spending ~3.5 min in a
single-threaded load (~2.8 h per 48-launch calibration); the loader thread was additionally pinned to
ONE CPU by libgomp under `OMP_PROC_BIND=spread`, so every production CPU server load ran on a single
core. Re-ported onto champion 2b57340bf as 25132e042 (test restored and extended), alongside a
parallel pread reader run as an OpenMP team (90c12df42, `--load-threads` / `LLAMA_ARG_LOAD_THREADS`),
which is what actually speeds up the DS41 recipe (under GGML_IQK=1 it hits no CPU_REPACK tensors);
bit-exact vs the champion, ~3.2x warm / ~2.1x cold on a 27B load. Rule fed (proposed, operator to
ratify into CLAUDE.md § Experimental Kernel Workflow): forward-port one feature per commit; before
reverting a bundled commit, split it and revert only the gated-out parts; a feature's test travels
with it through every consolidation.

## INC-20260926-local-actor-bringup
The DS41 AutoKernel campaign moved its planner from cloud actors to local weights with no prior
local run of the loop to learn from. It went first to the CPU frontdoor `qwen3.8-flash-next` on
:8074 (2026-09-23 18:06Z), then to the GPU `qwen3.8-27b` on :8083 (run 7, 2026-09-24).

The first real candidate measurement came **~57.5 h** later, at 2026-09-26 15:32Z. That spanned 11
run directories, 10 of which scored nothing. The campaign store held 45 records and 0 keeps before
run 10i; 22 of those records were abstentions.

About 26 incidents fell into four root-cause classes (the classes overlap a little):
- **~11 opencode harness semantics.** Examples: pipe truncation; argv quoting; `prompt:` replacing
  the system prompt; a silent 32000 `max_tokens` clamp; `chat_template_kwargs` dropped for local
  providers; a VACUUM lock on `opencode.db`; and a read-only session that an `ask`-class permission
  ENDS without `--auto`, where a `deny` fails only that one call (`b8d6a046`).
- **~12 latent loop or harness bugs** that the local model's long, numerous calls exposed rather than
  created. Examples: TERM not reaching the actor (DS41-C22); an op_scope gate that built 0 of ~15
  candidates (C29); a resume `RatchetRefused` (C31); comparability keyed on the actor roster (OP-60,
  `P-AK-SEARCH-1-A3.1`); discard-on-recoverable-failure (5 commits); exact-symbol route lookup
  (`77f8bf58`); reference probes compiled in the candidate's PATH-less env (`7037165f`); and a refused
  resume falling through to the planner (`2a060a41`).

  Two were still live afterwards. First, an experimental CPU campaign cannot continue past its first
  keep, because continuations never carry `cor_anchor` (17:51Z, DS41-C45). Second, keep anchor builds
  run at `-j1`, inherited from the HIP fix R23-40: ~1 h per keep, and gcc `-j64` reproducibility was
  never checked (DS41-C46).
- **~3 model capability.** Slow CPU prefill, a 74k-token deliberation with zero edits, and no use of
  the fan-out tool.
- **~4 process mistakes.** `touch STOP` used as a drain, an invented "off-hours" hold, a
  mid-calibration stop that blocked the frontdoor, and a 519 GB `--verify-artifacts` re-hash for an
  actor-only change.

A stale seeded "~220 GB/s" ceiling that predated a BIOS change also cost 13 batches (DS41-C36).

A fake model server finds most of the harness class in seconds, and a stub end-to-end iteration finds
most of the loop class. Neither was run before going live. The scripted-fake-server technique was
eventually used, live, to find the critic-permission bug.

The first keep followed at run 10i: `akm-ds41-gemm4xn-2x-unroll`, +4.535% paired, +7.304%
compounded. It is unconfirmed at serving, because the anchor-guard A/A read +19.443% on identical
code digests (DS41-C47).

Full record: [AutoKernel local-actor bring-up retrospective](../../design/autokernel-local-actor-bringup-retro-20260926.md).
Rules fed:
- the new-actor checklist, `docs/guides/agent-workflows/agent-loop-design.md` → *Bringing up a new
  actor model or backend*;
- the gates `handoffs/active/autokernel-orchestrator-actor-backend.md` OAB-29..OAB-32;
- proposed for operator ratification: a wire test before any new actor seat runs live
  (`scripts/operator/ratify_actor_seat_wire_test_20260926.sh`, into
  `agents/shared/OPERATING_CONSTRAINTS.md`).
