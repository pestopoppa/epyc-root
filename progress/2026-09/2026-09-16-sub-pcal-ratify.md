# 2026-09-16 — sub-pcal-ratify: P-CAL spec-dec contamination ratifier (zero inference)

Operator decision 2026-09-16, option (a): caveat the E7c and EV-4c calibration numbers in P-CAL now.

- **Branch** `sub/pcal-ratify-20260916`, worktree `/mnt/raid0/llm/worktrees/sub-pcal-ratify`, based on
  origin/main `8abf6984`. Not pushed.
  - `22cfd916`: adds the ratifier `scripts/operator/ratify_pcal_specdec_contamination_20260916.sh` and
    `artifacts/operator/pcal-specdec-contamination-20260916.patch`.
    - Pins:
      - patch `2fb3402e…`
      - MEASUREMENT.md, pre `45c7e3a3…`, post `9659d8c3…`
      - quality-eval.md, pre `94a2726f…`, post `dac23d84…`
    - Dry-run by default; `--apply` applies.
    - Writes the section-5 consolidated receipt, the decision receipt, and the keyed index
      `RATIFY-P-CAL-SPECDEC-20260916`.
    - `human_only_paths.yaml` is untouched, so its sha pin needs no change.
  - `83bc4ca5`: caveats outside the trust boundary.
    - The ESC-7 draft caveat block.
    - The wiki `benchmark-methodology.md` EV-4c bullet.
    - The `CURRENT-CAMPAIGN.md` pointer.
    - The ledger: one appended caveat row each for EV-11-math-rebaseline and EV-4-calibration-baseline.
      Status is unchanged; each row adds `flags.calibration_specdec_contaminated`.
- **Amendment content**
  - E7c math: CONTAMINATED and INVALID. The saturation recount is exact: 1528/1684 and 1485/1628 rows at
    confidence ≥ 0.999999.
  - EV-4c code: CONTAMINATED, size unmeasured (0/820, 2/817 rows saturated); demoted-to-prior.
  - Suspended until EV-CONF-2 reports: RLVR code calibration, EV-5/EV-7 verifier promotion, and the math
    ECE stability check.
  - Standing re-baseline rule: spec-off runs only, or placeholder tokens excluded.
  - No historical number is edited; postflight enforces this.
- **Tests**
  - Dry-run in the worktree is clean and writes nothing.
  - Throwaway worktree `/mnt/raid0/llm/tmp/sub-pcal-test` (since removed):
    - `--apply` gave receipt verdict RATIFIED; every section passed: coherence, evidence (4 sidecars
      durable), protocol, state_diff, validation.
    - A re-run printed ALREADY RATIFIED and exited 0.
    - A half-applied state, a moved target and a tampered patch were each refused.
    - `check_ratifier_receipt_contract.sh`, pointed at the throwaway tree, found nothing for this gate.
- **Not edited**
  - The EV-CONF-2 box in `autopilot-decision-plane-audit-2026-07-22.md`: its finding lives in the
    uncommitted `/workspace` copy from sub-evconf2, so editing it here would conflict.
  - `wiki/source_manifest.json`: it only holds a compiled historical title.
- **Operator next**: merge the branch, then run
  `bash /mnt/raid0/llm/epyc-root/scripts/operator/ratify_pcal_specdec_contamination_20260916.sh --apply`.
  Commit the five paths it prints, then tick VB-EVCONF2-CAVEAT.

## Review fixes (Fable MERGE-AFTER-FIX)

- **Rebase and new commits.** Rebased onto origin/main `87109bb2`; the pre-state pins still match, because
  both targets are byte-identical there. Commits: `232824f8` (ratifier), `fbd40fec` (caveats),
  `057c8d09` (review fixes and wrapper).
- **Provenance.** The evidence is now described as "merged 2026-09-16 via d8b915ee/88a2902d".
  - New pins: patch `b3045b69…`, quality-eval.md post-state `ec25a3ea…`.
  - The MEASUREMENT.md post-state pin is unchanged at `9659d8c3…`.
- **Preflight.** It now fetches the orchestrator and requires both evidence commits to be ancestors of
  origin/main (`merge-base --is-ancestor`).
- **Operator wrapper** `scripts/operator/run_pcal_ratify_20260916.sh`. It fetches, creates a fresh
  worktree and branch, shows the dry-run, asks for RATIFY on the tty, runs `--apply`, stages exactly
  five paths, commits with an "Operator-applied by" trailer, and never pushes. Tested in a throwaway
  setup (a shared bare origin plus a no-checkout clone, since removed):
  - a full `--yes` run committed 5 files with the receipt verdict RATIFIED;
  - a re-run without `--resume` was refused;
  - `--resume` after the commit printed "already done";
  - the interactive path with no tty was refused and applied nothing;
  - `--resume` after an uncommitted apply skipped to staging and committed;
  - `--yes` outside test mode and a missing `--operator` were both refused;
  - the real epyc-root was left untouched: no op/ branch and no worktree.
