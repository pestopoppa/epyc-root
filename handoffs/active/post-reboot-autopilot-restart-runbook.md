# ⚡ POST-REBOOT RUNBOOK — restart AutoPilot with authority LIVE

**Status**: ARMED — execute immediately on the first session after the host reboot (2026-06-28). Do this **before** other work.
**Priority**: P0 (the stack + autopilot are down across the reboot; authority is staged and waiting for this restart to go live).
**Created**: 2026-06-28
**Related**: [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) · [evidence-plane-ledger-and-sequential-verdicts.md](evidence-plane-ledger-and-sequential-verdicts.md) · [autopilot-authority-autoenable-proposal.md](autopilot-authority-autoenable-proposal.md)

## Why this exists
Before the reboot: operator killed AutoPilot, then **enabled planner authority** for the first time (gates all green — `restart_ready=True`, W6 alarm cleared after the calibrated rule `d4eae8b9`). The enablement is **staged**, not live — it activates only when AutoPilot restarts with the correct env. This runbook makes that restart deterministic.

## State staged pre-reboot (verify these survived the reboot — they're on-disk, so they should)
- `orchestration/autopilot_state.json` → `baseline_ledger_authority_enabled: true` (operator-authorized 2026-06-28).
- `orchestration/authority_consent.json` (gitignored, operator-owned) → grants `baseline_ledger: allow`. **Baseline authority is fail-closed behind this file** (code `e03c9f41`): if it's missing/denied, authority stays OFF.
- Revert path if needed: backup at `/mnt/raid0/llm/tmp/autopilot_state.bak-before-authority-enable-1782683463.json`; or set the flag false; or set consent ≠ "allow".

## Runbook (in order)

- [ ] **1. Host health.** Confirm CPU freq scaling is normal post-reboot (reboot resolves the multi-day throttle per `feedback_host_throttle_check`). No `drop_caches` needed on a fresh boot.
- [ ] **2. Bring up the stack** (canonical lifecycle — never manual): from `/mnt/raid0/llm/epyc-orchestrator`:
  ```
  python3 scripts/server/orchestrator_stack.py start
  ```
  This launches llama servers + the orchestrator API with the mandatory OMP/NUMA env and page-cache prewarm, and serves the dashboard (now incl. the optimization-brief panel + the authority-consent code). Wait for `[OK] ... ready` / `/health` 200.
- [ ] **3. Lock the consent file** (so no same-uid agent can grant authority without you). With sudo:
  ```
  sudo chown root:root /mnt/raid0/llm/epyc-orchestrator/orchestration/authority_consent.json
  sudo chmod 0444       /mnt/raid0/llm/epyc-orchestrator/orchestration/authority_consent.json
  sudo chattr +i        /mnt/raid0/llm/epyc-orchestrator/orchestration/authority_consent.json   # hardened: blocks rm too
  ```
  (To change later: `sudo chattr -i …`, edit, re-lock. Skipping this leaves authority working but not agent-proof.)
- [ ] **4. Confirm authority reads enabled** (flag + consent):
  ```
  python3 -c "import json; from src.autopilot_core.baseline_ledger import baseline_ledger_authority_enabled; print(baseline_ledger_authority_enabled(json.load(open('orchestration/autopilot_state.json'))))"
  ```
  Expect `True`. If `False`, the consent file is missing/denied — fix before continuing.
- [ ] **5. Restart AutoPilot** with the exact W4/W6 + hints recipe (the missing env is what caused the trial-1004 bad restart — do not omit any):
  ```
  cd /mnt/raid0/llm/epyc-orchestrator
  AUTOPILOT_SEQ_VERDICT=1 \
  AUTOPILOT_W6_AUDIT_BLOCK=1 \
  AUTOPILOT_W6_AUDIT_N=10 \
  AUTOPILOT_W6_AUDIT_EVERY_N_TRIALS=1 \
  AUTOPILOT_W6_AUDIT_SHADOW_ONLY=1 \
  AUTOPILOT_PLANNER_TIMEOUT=600 \
  AUTOPILOT_PLANNER_HINTS=1 \
  setsid .venv/bin/python3 scripts/autopilot/autopilot.py start --max-trials 2000 \
    > /mnt/raid0/llm/tmp/autopilot_postreboot_$(date -u +%Y%m%dT%H%M%SZ).log 2>&1 &
  ```
  `AUTOPILOT_SEQ_VERDICT=1` is what makes sequential-verdict authority live (it's env-gated, not a state flag).
- [ ] **6. Verify live** (a few minutes in):
  - process up; phase advancing (`/mnt/raid0/llm/tmp/autopilot_phase.json` trial id climbing).
  - `python3 scripts/autopilot/restart_readiness_report.py --json --strict --require-seq-cutover --require-w6-audit` → `restart_ready: True`, blockers `[]`.
  - brief endpoint: `curl -s 127.0.0.1:8000/dashboard/api/optimization_brief` → `authority.decision_grade_possible` should be **true** ONCE the banner fix below lands; until then it still shows observations (see Known gap).
  - `/health` green; no `autopilot_killed_mid_trial` churn.

## Banner fix — DONE (landed `8fe19f62`, activates on the step-2 stack start)
- [x] **Optimization-brief banner now reflects real authority.** `authority_banner()` derives baseline from the consent-gated `baseline_ledger_authority_enabled(state)` and sequential from the live autopilot's `AUTOPILOT_SEQ_VERDICT` env (read from `/proc`, fail-safe off). It will flip to "Authority ENABLED … decision-grade" automatically once step 5 brings autopilot up with the SEQ_VERDICT env. No action needed beyond the normal step-2 stack start (which reloads the module).

## Reversibility / safety
- Disable authority any time: change consent to non-"allow" (or `sudo chattr -i` + delete), or set the state flag false. Fail-closed = the conservative direction.
- Do **not** re-enable across a future kernel/instrument era boundary without re-accruing current-era evidence (the gates enforce this via `pareto_exclude_before_ts`).
