# Prospective Astropy scorer controls

This packet stages the known-gold and no-op runs for SWE-bench Verified `astropy__astropy-12907` at base commit `d16bfe05a744909de4b27f5875fe0d4ed41ce607`. It requires the original official rebuild receipt from row `vb-p5-astropy-image-rebuild-20261118`. Staging verifies the pinned base, Dockerfile and exact offline build context, checks the original attempt receipt, log, grant, launcher and source-manifest hashes, and seals those bytes with the native scorer sources. Docker preflight requires the receipt's exact derived image ID.

The native runner captures the allocator grant and checked CPU affinity, UTC start and completion, raw reports and test logs, both fresh checkout witnesses, and owned-container cleanup. Each arm must provide all two FAIL_TO_PASS and thirteen PASS_TO_PASS statuses, with agreement between the scorer, official report and test log. A fully recorded control can have a diagnostic FAIL. A source, acquisition, window or cleanup refusal produces an UNKNOWN attempt with available original artifacts and its error. Publisher smoke uses a private result path and official capture uses `official/RESULT.json`.

The existing Astropy publisher smoke completed both historical arms in 15 seconds. The prospective writer has a 270-second ceiling inside the grant and reserves time for cleanup. This captures one functional scorer case without model inference. Software controls exercise the staging, capture and refusal paths with simulated evaluation. The original AST-based software controls run against the copied, byte-identical historical job. [Historical smoke receipt](../../../docs/reports/p5-gold-controls-20261104/smoke-pass.json)

Once the official build row completes, stage into a fresh native directory.

```bash
scratch=/mnt/raid0/llm/tmp/vidya-belief-substrate
packet=data/vidya/p5-astropy-scorer-controls-20261118
native=$scratch/p5-astropy-native-r1-20261118
python3 -I -B "$packet/stage.py" \
  --image-receipt "$scratch/p5-astropy-scorer-r1-20261118/official/RESULT.json" "$native"
bash "$native/preflight.sh"
```

Verify software controls from the repository root.

```bash
python3 -B -m pytest -q data/vidya/p5-astropy-scorer-controls-20261118/test_stage.py
```
