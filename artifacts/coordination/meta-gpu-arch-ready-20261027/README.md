# META qwen4exp native GPU diagnostic — owner handoff

MAIN approved source seal `f00a79b8c94fa399232a9dd7325b689b09d223b87b80297828805518e19ec5cc`. The operational packet is `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/packet`; this directory records its reviewed source and owner-only prepared rows. This is an unarmed synthetic qwen4exp Meta MoE fixture only. No GPU, model, or inference has run in this preparation; C5 a0 and all other full gates remain open. Original build outer rc70 and unproven drain remain historical facts; independent recovered artifacts are bound by the source seal and `actual-bindings.sha256`.

T1: `packet/dryrun/6d64662f37d82504887fb7c0b0fb819ac5c6f093c7a51bfe/pass.json`. Normal synthetic admission and reaped poller: `packet/final-admit/`; engine failure/stale-marker controls: `../engine-controls5/admitted-command.log`. Adapter suite and synthetic history canary: `../existing-suite-final/admitted-command.log` and `../canary-synthetic-history/prepare.json` under `/mnt/raid0/llm/tmp/codex-ni-20261027-meta-gpu-arch-ready/`. These are synthetic controls, not GPU acceptance or proof that a production loop is wired.

Owner installs the reviewed adapter from this commit into the clean `/mnt/raid0/llm/views/epyc-root-main` view and verifies SHA-256 `fb5386bb2cf650898f28ae712caffc7280cb98948a28969ef11f1436b2c73fb0`. Run the installed-byte synthetic context canary on an admitted model-free CPU window:

```sh
/mnt/raid0/llm/tmp/refactor-01a16fc3/ci/phase-b-candidate-venv/bin/python -I -B /mnt/raid0/llm/views/epyc-root-main/artifacts/coordination/meta-gpu-arch-ready-20261027/installed-source-canary.py
```

Then owner applies the source table/task draft in `PREPARED-ROWS.md` and writes `packet/BK-ENROLLMENT-APPLIED.txt` with `adapter-sha256=<digest>`, `installed-root=/mnt/raid0/llm/views/epyc-root-main`, and `planning-canary=passed` only after the owner accepts the applicable canary. The existing shared-loop historical/do-not-repeat canary remains required before calling the production loop wired. The packet also requires MAIN's bound acceptance receipt and a separate real GPU grant, actual ancestor lock, time/hold/RSS/disk checks, and PCI/DRM/KFD during-run residency. Champion owner alone decides integration after real gates.
