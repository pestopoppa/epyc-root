# 2026-09-15 — non-CPU-inference ROI sweep: dispatch + integration

Session without a lane (ad-hoc, shared clone). All work done in private worktrees off origin/main; this file lands
with the integration branch `sub/integrate-20260915`.

**Environment finding:** the shared `/workspace` clone was 332 commits behind origin/main (local `main` @ 2026-09-09).
The first ROI overview was verified against that stale tree, so several "open" items were already closed upstream
(M-12e `dcb769c1`, SC67 `baaa6741`, MHS-1, SEQ-B2). Every later agent read handoffs from origin/main.

## Landed (branches, unpushed at time of writing)
- **Stale-row cleanup** (`sub/stale-row-cleanup-20260915`): 8 index rows re-pointed, OP-22 retired (container PID 1
  2026-08-13, after `136894e8`), NIB2-64 + NI-IO ticked, RTG-49 status fixed, RE-1 note.
- **RECLAIM-2 / OP-37 resolved** (same branch): operator kept `UD-IQ4_XS` (INF-67 megakernel benchmark artifact) and
  `IQ4_XS-uniform` (recipe pin, re-hashed `4bfb9849…` OK). Deleted `-gateup-r16`, `-uniform-r16`, and the recipe-REJECTED
  self-contained MTP head. Record in `cpu-decode-roofline-program.md`.
- **R23-61a** GPU serving floor, PRE-BIOS: 7.897% p95_dev, process unit, n=24, CI [5.520, 11.322]%, recipe-hash
  verified, residency 24/24. R23-61b post-BIOS repeat filed. CI code: research `sub/r23-61a-floor-n-ci` `a25aaf1f`.
- **NIB2-69** (orchestrator `sub/nib2-69-strict-gate`): check-mode artifact root-caused; one NUMA mode per `check`;
  unit failures 33 → 0.
- **OBS-8 / OBS-6** (`sub/obs-8-obs-6`): port gate refuses when blind or occupied; health check scores unreadable as UNKNOWN.
- **DF2-QWOPUS scoping** (`sub/df2-qwopus-scoping`): don't train yet; K1 gate first (`docs/design/df2-qwopus-scoping-20260915.md`).
- **OP-38 P-KLD package** (`sub/op38-pkld-package`): annex + ratify script (never run) + decision package.
- **CME-2 + SC68 done, CME-1 partial** (research `sub/cme-1-beam-adapter`, root `sub/sc68-beam-write-side`). BEAM data licence is CC BY-SA 4.0.
- **AP-50 cockpit** (orchestrator `sub/ap-50-decision-cockpit`, root `sub/ap-50-cockpit-page`): built and tested offline; not deployed.
- **AutoKernel disk sweep** (`sub/autokernel-disk-sweep`): DRY-RUN manifest (607 GB scanned; REMOVE 34.8 GB, KEEP-dirty
  369.9 GB), plus design review `docs/design/autokernel-disk-hygiene-20260915.md`. `--apply` only after operator review.
- **Disk:** ~195 GiB reclaimed (r16 ×2, rejected MTP head, NIB2-65/66 partials); `/mnt/raid0` 156 → 336 GB free.

## Open, needs operator (as of the end of this session)
- **OP-43a — the runaway `llama-cli`** (24 GB/h, not our PID). The one time-sensitive item. → NIB2-72.
- **OP-43b — AutoKernel sweep apply or decline** (34.8 GB safe; 370 GB dirty trees; 187 lane worktrees on the frozen
  clone). → NIB2-77.
- NIB2-73: the 12 broken evidence citations blocking the master-registry ledger.
- NIB2-65: `Qwen3-4B-Thinking-2507-GGUF` rationale conflict (an active handoff uses it as a control arm).
  NIB2-66: dirty `k28-prototype` tree.
- OP-38 ratification (package ready, script never run); OP-38 → OP-46 renumbering proposal.
- Whether :8100 should serve `/cockpit` too (needs that session's tree synced, or OP-9's supervisor restored).
- RESOLVED this session: EVL-25 (7B stand-in, operator), AP-50 deploy (option A, operator), OP-37 (keep both
  artifacts, operator), OP-22 (verified resolved).

## Later in the session (post-push)

- **Pushed** (3 repos): epyc-root `0fa74299 → d143152f`, epyc-orchestrator `34e27fdf → 92bbeb06`,
  epyc-inference-research `a146fe28 → 5af2e801`. Root pushes ran under the `push` lease (acquire → push → release).
- **OP-37 RESOLVED (operator).** Keep `UD-IQ4_XS` — it is the artifact the INF-67 CPU fused-decoder megakernel was
  developed and benched against (`progress/2026-08/2026-08-28.md:259`, `cpu-fused-decoder-blocks.md:31`) — AND keep
  `IQ4_XS-uniform` (recipe-pinned champion artifact; sha256 re-verified `4bfb9849…c9f8957` == the PROD-1 pin). The
  earlier verification had proposed uniform alone as the keeper; the operator's correction is recorded as RECLAIM-2.
- **Deleted, operator-directed:** `-gateup-r16` + `-uniform-r16` (183 GiB, regenerable from the keeper via fork
  `experimental-inf70-b3` `dd27ec3bb` / `-b4` `49a1255` / `-b4r2` `a0907a8bc`) and the recipe-REJECTED self-contained
  MTP head (3.9 GiB, on HF). With the earlier NIB2-65/66 partials: **~195 GiB reclaimed**, 156 → 337 GB free.
- **OPERATOR RULE ADOPTED MID-SESSION:** every deletion needs manual confirmation before it executes, even when the
  operator has already said "delete the others" and verification passed. Saved to memory
  (`feedback_manual_confirm_before_deletion`). Origin: this session deleted the two r16 artifacts in the same turn the
  verification landed, and the verification had picked the wrong keeper.
- **A regression this session caused and fixed.** The NIB2-65 ledger was written into the COMPILED lean registry
  (`epyc-orchestrator/orchestration/model_registry.yaml`) instead of the MASTER — the exact defect
  `feedback_ledger_goes_in_master_not_compiled_output` records. It broke the priors' registry hash pin, and the
  now-strict stack-change gate (NIB2-69, landed hours earlier) refused the launch. Reverted on orchestrator
  `92bbeb06`; `stack_change_pipeline.py check` is green end-to-end (incl. `runtime_attestation`). The gate caught a
  real drift on its first live run. Re-filing the ledger against master is blocked → NIB2-73.
  Also undone: a `--dry-run` start still RECOMPILED the lean registry in the shared clone (dry-run is not read-only
  on that path) — the file was restored to HEAD content.
- **AP-50 DEPLOYED** (operator option A, cockpit only): API started via `orchestrator_stack.py reload orchestrator`
  (pid 2096743, `/health` 200; AutoPilot left STOPPED, zero model servers), `/dashboard/api/decision_cockpit` 200 +
  its probe `ok`, page served from a SECOND hub on **:8101** out of a fresh origin/main checkout. :8100 belongs to
  the `autokernel-unified` lane session and was left untouched (still `/health` 200); it will not serve `/cockpit`
  until its own tree syncs, because `hub_supervisor.sh` (OP-9) is not running.
- **EVL-25 answered on the 7B stand-in** (operator chose the stand-in over a ~19 GB download): bf16 LoRA fits with
  ~22% headroom extrapolated to 9B → 4-bit QLoRA retired for the ~2k-token/step shape, NOT for longer context.
  The handoff's "~22-25 GB" estimate was low: the non-weight term alone is ~24.7 GB.
- **Runaway found (NIB2-72 / OP-43a):** a coverage-harness `llama-cli` stuck in interactive mode, 58.4 GB of `>`
  prompts at a measured 24 GB/h, 96 threads since 19:50Z. **I first mis-attributed a 48 GB drop in under an hour to
  normal background growth by quoting a DAILY rate (8-24 GB/day) against an hourly observation — the mismatch was
  itself the signal.** Not our PID; the kill is the operator's or the Codex session's.
- **Worktrees:** 16 of this session's 20 `sub-*` worktrees removed after verifying clean + contained in origin/main +
  no process inside (one had leftover regen output, restored to HEAD first, so nothing was force-removed). Kept:
  `sub-integrate-root` (serves :8101), `sub-master-ledger` (blocked ledger fix), `sub-r2361a`, `sub-evl25`.
- **Wrap-up gates:** README freshness clean; wiki scan `has_drift: false` (no compile needed); prune candidates 0;
  `index_state.py --check` 0 problems. Agent logging was never started this session (`agent_session_start` not
  called), so there are no open `agent_task_*` spans to close.

## Evidence-durability pass (NIB2-73 family)

- **NIB2-73 closed** (research `d4de5535`): the 8 deleted models are ledgered in the MASTER registry, where a recompile
  cannot erase them. The first attempt put them in the COMPILED lean file — the defect
  `feedback_ledger_goes_in_master_not_compiled_output` already records — which broke the priors' hash pin and was
  caught by the strict gate NIB2-69 landed hours earlier. Reverted as orchestrator `92bbeb06`.
- **NIB2-73a closed** (research `041ecb1d`): 8 of 9 cited artifacts carried into git with per-campaign README +
  SHA256SUMS, every sha256 verified against the origin. The 22.4 MB campaign was carried at **1.54%** — the distilled
  results and provenance chain, not the raw capture, verbose logs, VRAM telemetry or SWE-bench patch bodies, which also
  keeps upstream authors' emails out of the tree. The 9th was already correctly WITHHELD (third-party receipt PII).
  Side effect: both dflash2-challenger ratification hashes now verify against artifacts in git; until then they hashed
  untracked files, so they asserted nothing in any checkout but one.
- **NIB2-73c closed**: the gate could not distinguish DELIBERATELY WITHHELD from LOST. A `<file>.WITHHELD.sha256`
  sibling now resolves a citation as verdict WITHHELD — info severity, never folded into OK, never escalated by `-W`.
- **HYG-3 closed** (root `7b72bf64`): epyc-root's commit-hygiene hook read a `2>&1` redirection as a pathspec, blocking
  the most common git idiom on this host. It fired against me three times today, including on the commit recording its
  own fix (the active hook comes from the stale shared clone).
- **NIB2-73d closed** (research `6575c33c`): the 11 undocumented campaign directories now carry provenance READMEs +
  SHA256SUMS, written from git history / registry citations / progress logs / handoffs, with `UNVERIFIED` wherever a
  fact could not be established. 3,782 files sealed, `sha256sum -c` clean, missing-docs list now EMPTY.
  **Three premises I handed the agents were wrong and were corrected in the writing** — bonsai_current_v7 is the
  speed-rerun evidence, not the quality rejection's; numa_placement is the shared attestation dir disambiguated by arm;
  the glm52 native-MTP 185837Z pair is not a completed A/B. Sourcing each claim is what caught them.
- **Filed, not fixed:** NIB2-73e (the gate scans the registry only, so cited-but-untracked evidence in docs/handoffs is
  invisible — with 4 concrete instances), NIB2-73f (the operator's own email in a tracked audit file — his call).
