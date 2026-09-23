# 2026-09-23 — main-kernel

Continuation of the v10 promotion session. Three threads: finishing the cap-convergence
measurement the architect quality gate needed, wiring what that measurement produced into the
belief kernel, and closing two structural defects that the session's own friction exposed.

## 1. The quality-gate token cap is not model-neutral — measured, not argued

The v10 qualification ran `mmlu_pro` at the gate's conventional 64-token cap and Flash-Next
scored 0.5650 pooled against the retired Qwen3.5-122B's 0.6450. Read alone that is an 8-point
regression and it would have been reported as one.

The decomposition says otherwise. At that cap Flash-Next truncated **46 of 200** items, 33 of
them with nothing extractable, while the 122B recorded `truncated: 0`. The two models are not
answering the same way: the 122B emits a letter, Flash-Next derives in the visible channel
(`--no-enable-thinking` is set and `reasoning_chars == 0` on every row, so this is not leaked
reasoning). A truncated derivation scores ~0.05 because nothing can be extracted from it, so
pooling truncated rows understates the model rather than measuring it.

The completion-token distribution is bimodal — median 2 tokens, p90 exactly at the cap at both
64 and 512 — which said the tail was finite and would converge. Confirmed by running the cap up:

| cap | truncated |
|---|---|
| 64 | 23.0% (46/200) |
| 512 | 12.6% (partial, n=87) |
| 4096 | 2.5% (5/200) |
| 8192 | **0 / 200 — converged** |

**Correction, retained.** An earlier version of this entry recorded cap 4096 as taking truncation
to zero, extrapolated from the first 56 rows which happened to contain none; the full 200 had five.
A partial count is not a converged one — the same lesson as the pooled-accuracy rule above, one
level up. Kept here rather than quietly edited out, because the mistake is the point.

**FINAL, both suites converged (`pooled == untruncated`, truncation zero):**

| suite | cap | pooled | untruncated | truncated |
|---|---:|---:|---:|---:|
| mmlu_pro | 8192 | **0.7550** | 0.7550 | 0/200 |
| gpqa | 16384 | **0.6513** | 0.6513 | 0/195 |

Against the retired Qwen3.5-122B's gate numbers (0.6450 / 0.5692) Flash-Next is **ahead on both**,
where at the gate's own 64-token cap it appeared behind on both. The verdict was inverted by the
instrument, not by the model.

Raising the cap was legitimate only because the truncated rows were first shown NON-DEGENERATE (top
repeated 60-char shingle = 1): genuine long derivations converge as the cap rises, repetition loops
never do and no cap would reach zero. Check that first or the instruction does not terminate.

Untruncated-only accuracy at the gate cap was 0.714 on mmlu_pro and 0.618 on gpqa, against
pooled 0.565 / 0.544 — the gap is the artifact.

**A pooled accuracy is never the number to report while `truncated.n > 0`**, and the
`performance:` blocks for `architect_critic` and `qwen38_flash_next_ud_iq4xs_local` are prepared
but deliberately unapplied until the 4096 arm finishes all 200.

Filed as **SSU-F6**: `promotion_gates.yaml` `gates.quality` never records `max_tokens`. The 64
was carried into the v9 and v10 qualifications by convention — precisely the failure that file
was created to end — and a cap that silently favours terse models is not a quality gate.

Also found while reading the live process and filed as **SSU-F7**: `:8074` is missing two env
knobs its own registry recipe declares (`GGML_NOHUGEPAGE_PROCESS`, `GGML_FA_SPLIT_KV`). One of
them is the THP shim. The served process is not running its own recipe and nothing detects that.

## 2. Belief kernel — the architect quality gate is wired on the write side and ingested on neither

`v7_quality_gate_runner.py` has emitted producer-authored rows under
`epyc.v7_quality_gate_runner.accuracy.v1` since SC32 wired the GPU control arms (2026-08-26), and
now from the CPU live-serving arms too (SSU-F2, today). There is no `Source(...)` row and no
adapter for either. One adapter covers both; they are one schema. Filed as **VB-ARCH-CPU-QUAL**
with the source row added to `scripts/vidya/adapters/README.md`.

Two cautions are written into the row verbatim because retrofitting them on read is impossible:
`instrument_class` must reach the tuple (the CPU arms are `serving`, the GPU arms an owned bench —
flattening them manufactures the cross-class comparison MEASUREMENT.md forbids), and truncation
must be projected beside accuracy, for the reason in §1.

## 3. SSU-F5 — 11 failing fixtures, fixed by deriving rather than repinning

`test_stack_priors_compiler.py`: **11 failed / 24 passed → 35 passed**, one file, `ruff` clean.
Nine of the eleven were the restated-derivation class — port and role literals copied from
`port_map` / `numa_config` / `shared_with` — and now recompute from those sources. One was a pin
that pinned the wrong thing. One (`test_compile_maps_model_role_server_binding`) had ten
assertions the compiler resolved from the *live* launcher, so each fix revealed the next; its
fixture now declares the launcher world it describes.

The claim that matters is that the fix DERIVES, and it is proven rather than asserted: a pytest
plugin at `/mnt/raid0/llm/tmp/ssuf5/moved_lineup.py` relocates the worker lane a second time onto
`architect_critic`, moving all five surfaces together, and **34 of 35 tests follow the move with
no edit to the test file**. Keep it — it is a standing regression against the next lineup change.

The one failure under that plugin is a deliberate pin failing loudly at a **production** defect:

**SSU-F8** — `src/config/models.py::_LEGACY_SERVER_URL_FALLBACKS` still names the retired `:8072`
fleet for `worker_general`, `worker_math` and `toolrunner`. `_server_url_default()` ends in a bare
subscript of that dict, so in exactly the degraded mode the table exists to serve — priors
unreadable, no runtime facts, fresh checkout, bootstrap — those three roles resolve to a fleet
with nothing listening. It reads correct today only because live runtime facts win.
The remedy filed is *not* to update the three rows: it is to add the table as a sixth surface in
`check_shared_with_derivations.py`, since its absence there is why this rotted while the five
wired surfaces did not.

## 4. SSU-F9 — the push path is not deterministic, and fails silently

Four consecutive failed pushes to land one reviewed commit. Two defects compose:

- `serialized_push.py` derives its lock directory from the git common dir (correct — it is what
  makes five lane worktrees contend for one lease), while the pre-push hook reads
  `<repo>/coordination/push-locks/`. `--acquire` truthfully says *acquired*; the hook truthfully
  says *NOT HELD*. Same key, two directories.
- The hook accepts a push descended from the lock holder, else requires `EPYC_PUSH_LOCK_HOLDER` or
  `AGENT_ID`. Across two tool calls the holder pid is not an ancestor and the wrapper exports
  neither, so the wrapper's own `--push` fails its own guard.

The expensive part is the silence: `--push` ends on `PUSHING as '<agent>' under the push lock ...`
while git's `error: failed to push some refs` surfaces *earlier* on stderr, and `--release` then
reports `(no push lock held)`, which reads like a normal post-push release. Nothing in that
sequence says the push did not happen. **`git cherry origin/main main` is the only thing that
does** — which is exactly why the wrap-up contract requires it, and it is what caught this.

## 5. Process notes

- The first cap-4096 launch died at 26/200 with no exit code — killed when its parent task was
  reaped, not failed. Relaunched under `setsid`; the runner is idempotent on `(id,seed)` and
  resumed rather than restarting.
- `orchestrator_stack.py reload architect_general` correctly **refused** while the CPU bench is
  running (*"this destroyed 1h09m of decision-gating measurement on 2026-07-27"*).
  `--allow-during-bench` was not passed. The `-lv 4` reload for the `:8083` memory accounting runs
  at the gate's boundary.

## Commits

| Commit | Repo | Subject |
|---|---|---|
| `7a34a377` | epyc-root | belief kernel: wire the architect CPU quality gate, and file SSU-F6/F7 |
| `8b1ff4ba` | epyc-root | SSU-F5 done (11 -> 0), and the two things it left: SSU-F8, SSU-F9 |

Both on `origin/main`, `git cherry` empty.

## Open

- ~~cap sweep~~ **DONE**: converged at 8192 / 16384, recorded in the MASTER registry
  (`epyc-inference-research` `58b115ed`) under `performance.general_suite_quality` — deliberately
  NOT in `quality_score`, which means the CRITIC suite on this role and stays null because that
  gate has still never been run.
- **Near-miss worth recording**: the first edit went into
  `epyc-orchestrator/orchestration/model_registry.yaml`, which is AUTO-GENERATED — the compiled
  runtime view, silently overwritten at the next stack start. The master is in
  epyc-inference-research. Reverted from backup; the file header says so and should have been read
  before editing, not after.
- `:8083` reload with `LLAMA_ARG_LOG_VERBOSITY=4`, to convert the 1.802 GiB compute residual from
  a subtraction into a reading. Queued behind the gate by the bench guard, not by a decision.
- SSU-F8 and SSU-F9 in flight.

---

## 6. Late session — the guard that was already installed, and an index defect I caused

### SSU-F9b withdrawn: the premise was false

I filed, and told the operator, that `epyc-orchestrator` and `epyc-inference-research` carry LFS-only
`pre-push` hooks with no serialization guard. **They do not.** Both carry the identical chained hook
installed 2026-08-12, byte-identical to epyc-root's. That was a subagent claim relayed without
verification; `cat` disproved it. Verified the guards actually *function* rather than merely exist, by
feeding each a real ref-update line — both print `PUSH REFUSED` for an unheld lock.

What *was* true is the better finding: each now resolves to its OWN repo's `coordination/push-locks`,
which is what the SSU-F9 fix produces. **Before it, those two repos' pushes would have been refused
always, not intermittently** — the guard read `/workspace/coordination/push-locks` while
`serialized_push.py` took the lock in the repo's own directory. epyc-root's two derivations
coincidentally produced the same string, which is exactly why the breakage was invisible from the repo
where the work happens. So SSU-F9 silently repaired the sub-repos too.

### The stale-shared-index incident — mine, and caught by a peer

A parallel session flagged a stale working-tree copy. Investigating it found something worse and closer
to home: the SHARED index held snapshots of **six of my files**, each of which would have published a
mass deletion of work already on `origin/main`.

| file | staged vs HEAD |
|---|---:|
| `artifacts/operator/vram-gap-27b-20260923.md` | −379 |
| `handoffs/active/model-stack-single-source-update-pipeline.md` | −154 |
| `.claude/skills/kernel-promotion/promotion_gates.yaml` | −43 |
| `progress/2026-09/2026-09-23-main-kernel.md` | −31 |
| `handoffs/active/vidya-belief-substrate-program.md` | −7 |
| `handoffs/active/master-handoff-index.md` | −2 |

**Mechanism.** I commit through a private index seeded from `origin/main` — which is what stopped me
sweeping peers' hunks all day, and is correct. But it never advances the SHARED index, so a stale entry
there stays pinned to old blob content while HEAD moves past it, and the growing gap reads as deletions.
A plain `git commit` from ANY session would have published them.

**Why it was invisible**, three compounding reasons, all checkable:
1. The damage is proportional to how much you have committed since the entry went stale — it starts at
   zero and grows silently. Mine reached −379 lines on one file over a day.
2. `git status` shows `M`/`MM`; `MM` is the tell but renders as ordinary dirt in a clone with dozens of
   dirty paths.
3. `git diff -- <file>` — the command a careful person reaches for — is worktree-vs-INDEX and **cannot
   show this class of damage by construction**. It needs `--cached`, or `git diff HEAD`.

**The remedy already exists in writing.** `agents/commands/wrap-up.md` says: *"After committing,
`git reset -q -- <the same paths>`."* So this is not a missing rule, it is an unenforced one, and the fix
is detection. I ran it after my first two commits and stopped exactly when I switched to
`commit-tree -p origin/main`, because in that shape the shared index is provably irrelevant to what *I*
publish — the entire risk is to OTHER sessions' commits. **The hygiene step that protects peers looks
redundant from inside the very pattern that made you safe from peers.**

Cleared my six with `git reset`; worktree verified intact afterwards. Left the peer's four alone —
checked each first, since `vidya-belief-substrate-program.md`'s staged deletions were mine while
`adapters/README.md`'s was their DS41 row.

I had seen that staged list hours earlier and called it benign without running `--cached`. **Looking is
not checking**, and that gap is the whole incident. Saved as a durable memory; mechanism notes sent to
the investigating session.

### Champion fast-forward — verified, deliberately NOT taken

A peer asked me to fast-forward `ak/champion/llama-cpp-ffc1bac82eec` to `8df1b5cf2` (a new ggml op,
INF-77 DS41-B7). Verified their claim: `ffc1bac82` IS an ancestor (true fast-forward), 406 insertions /
4 deletions, the only deletions being a `ggml-rpc` `GGML_OP_COUNT` assert refresh, and the sole
references to the new op outside ggml core are in its own test file. Consistent with additive.

**Not taken, and not for ownership reasons.** A champion is a commit AND its build. Moving the ref alone
leaves `ak-loop-tree`'s binaries predating their own commit — INF-70 C9 exactly, where `libggml-cpu.so`
predated its own fix by two days and two agents spent two days on a defect that did not exist. It needs
ref-move plus rebuild, together or neither. Tree state for whoever does it: `ak-loop-tree` has the
champion checked out at `ffc1bac82`, no AutoKernel loop resident (checked `/proc`, not a name pattern).
Surfaced to the operator, since it changes what all future kernel work rebases onto.

## Wiki compilation (operator-cadence step)

Delta was 26 sources spanning several sessions' domains. Compiled the **three I had warrant for** and
scoped the watermark touch to exactly those, leaving 23 in the delta for their owners rather than writing
pages about work I do not understand:
- `wiki/benchmark-methodology.md` — the token cap is part of the claim; the four rules; the
  degeneracy precondition; subtraction-as-residual.
- `wiki/inference-serving.md` — the served process does not run its own recipe; the read VRAM
  decomposition; `full_attention_interval` confirmed in the server's own words.
