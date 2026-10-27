# UFH-12 G-S source installation and owner canary

Do not arm either row until the reviewed root patch is merged, the installed-root canary below passes, and enrollment validates. The pre-existing `defba...` runtime is superseded by this guarded successor. The two successor rows share ports/results and must be scheduled sequentially. Each needs an explicit `regions=24-47` grant, 1200 seconds, 900-second minimum, 8 GiB RAM. Exit 75 means resumable partial work, not PASS or a code-fix hold.

Use a real claimed correctness window for Python/canary execution. Set `GS_ROOT` to the resolved installed ROOT checkout containing the merged patch; set `GS_B` to `/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-gs-rehearsal/wiring`. A unique output directory is mandatory:

```bash
GS_ROOT=$(readlink -f /mnt/raid0/llm/views/epyc-root-main)
GS_B=/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-gs-rehearsal/wiring
GS_CANARY="$GS_B/canary-installed-$(date -u +%Y%m%dT%H%M%SZ)"
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python "$GS_ROOT/scripts/vidya/ufh12_gs_canary.py" --runtime-seal "$GS_B/SOURCE.sha256" --out "$GS_CANARY"
cp "$GS_CANARY/canary-receipt.json" "$GS_B/INSTALL-RECEIPT.json"
/usr/bin/python3 -B "$GS_B/enrollment.py" "$GS_B/INSTALL-RECEIPT.json" "$GS_B/SOURCE.sha256"
```

A successful canary prints its receipt path; enrollment prints the exact resolved installed root. Receipt schema is JSON containing `source_family=VB-UFH12-GS`, `status=passed`, `planning_context=visible`, `synthetic=true`, `installed_root`, SHA-256 fields for adapter, helper, producer, registry, shared carrier, canary and runtime source seal, and `evidence_path` / `evidence_sha256`. Its isolated ledger and fixture explicitly use `synthetic-fixture.gguf`; the canary requires both coverage values 1 records to appear in planning context. They are never real measurements and must not enter the live ledger. Runtime enrollment checks each hash, checks the reviewed fixed hashes in `INSTALLED-PINS.json`, validates the current registry loads this exact adapter, and checks canary evidence. Any source update invalidates the receipt. Generate a fresh installed receipt; never reuse the private-tree receipt.

Once reviewed and installed, use the exact rows in `ROW-DRAFT.md` and `ROW-TOKENS-DRAFT.md` (one writer applies them); swap the original unarmed rows for these successor launchers and preserve their completed T1 proof paths. `REVIEWED.sha256` must contain the reviewed final SOURCE.sha256 file hash and its absolute path. Do not change the source, binary, GGUF, lib pins, receipt, sample manifest or checkpoints after acceptance. On execution, the job refuses stale receipts, wrong grant, HOLD, wrong affinity and concurrent facets; it emits prospective coverage and descriptive raw records. Completion requires all records and verified owned-process cleanup. G-S and R5 stay open until actual evidence and subsequent threshold sweeps exist.

After installing and validating the receipt, the exact pollers are `bash "$GS_B/poller.sh" scores` and `bash "$GS_B/poller.sh" tokens`. Register and schedule them sequentially; they wait for their own grants. Source pins: adapter `5f8e33960eb23fd82ac9a21d4a1c80df6849ba48ff277dd9f94394540b886a1b`; helper `96449344de985296deb73b05fec2f476cc28d1f41eaa025d8e08b3e9220fa96e`; producer `de2c315743e827367493a2810ec54fe54dfe1420026b43197b2d634d3dd5933d`; shared carrier `405e9fe8fa536029886580070eb6c8c6838e1eab8309cc33c94956ee260a23d2`; canary `79e73351e104c9c1b287123a2985748f8380307caeb0f28983db28b6d5b76514`. The installed registry hash is captured by the canary and checked against the actual registry, because integration can legitimately change that shared file.
