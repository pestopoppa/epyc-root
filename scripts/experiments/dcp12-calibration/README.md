# DCP-12 calibration packet

Prospective contract: [protocol](../../../docs/design/dcp12-calibration-protocol-20261118.md). Prepare with `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -I -B scripts/experiments/dcp12-calibration/prepare.py`; resulting spec is under the DCP-12 scratch packet. The owner publishes and qualifies it; do not treat a queued row as a host-quiet attestation. Analyze an official window with `python3 packet/calibration_analysis.py native/window-...` after completion. No live inference is part of preparation.

Publisher smoke runs the offline calibration tests before starting the private server and preserves their exit code and output in `OFFLINE-TESTS.txt`; failure refuses qualification. Official runs do not run tests.
