# Vidya sync hook installation

Both Git hooks resolved by `/workspace` contain one Vidya sync block. `receipt.json` records the installation, byte preservation, shell syntax and repeat-install checks.

Keep VB-SYNC-HOOK-INSTALL open until a genuine update of `/workspace` main changes `research/intake_index.yaml`. Once that update is visible at `origin/main` and the detached hook has finished, record the triggering commit and confirm lag 0 using `python3 scripts/vidya/cli.py sync --check` without a manual sync. A push to remote main alone does not invoke these local hooks.
