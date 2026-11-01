# DF2-12.1 frontdoor 96-thread calibration-first booking

## Separate keeper-owned qualification resource claim before HARD target qualification

`codex-ni-df2-12-1-frontdoor-cal96-20261101` | keeper/ws58 owner | distinct **pregrant qualification calibration** exposure | CPU regions `0-95` (all four quarters, physical only) | no GPU claim | memory cap 120 GiB | 1800 s bounded window | scratch `/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101/calibration-live` | scratch port 18770 | disk floor 150 GiB. This is a resource request to the keeper owner, **not a FILLERS/READY row or official science grant**. A command-type FILLER would itself need HARD qualification and would be circular. ws58 issues a distinct limited calibration authority and claims the free whole host with region-lock. Current active correctness grants cover 0-95, so this claim waits for a serialized owner boundary; NI does not steal their CPUs.

## Owner-bound launch template

The executable owner entry is `owner_pregrant.sh calibrate cpu --authority "$WS58_CPU_CAL_AUTHORITY"` and `owner_pregrant.sh calibrate gpu --authority "$WS58_GPU_CAL_AUTHORITY"`. It pins both binary paths, role geometry, production-thread affinity, exact prompt SHA, scratch ports and output paths; ws58 supplies only its bounded authority path/time. The expanded CPU command below records the underlying region-lock form. The GPU command is generated directly by the same wrapper, so no owner needs to reconstruct it from prose.

Fill `EXPERIMENTAL_CPU_SERVER` and `PROOF_DIR` from the same-image build/test receipts, `PROMPT_SHA` from frozen `PROMPTS.json`, and `CAL_AUTHORITY` from a keeper-owned, bounded pregrant calibration authority file. Start only in that resource window. The keeper records authority-file SHA, actual region-lock claim log, process birth/RSS/time, and pre/post live roles. The `FILLER_*` variables below are **local PIDfile/affinity wiring only**, and convey no FILLERS enrollment, keeper nonce, or official grant. The runner refuses missing identity/affinity/PIDfile/state, mismatched image proof, changed manifest SHA, unexpected target shape, or failed own-PID drain.

The authority JSON contract for this packet is `{kind:"ws58.pregrant.calibration.v1",id:<CAL_ID>,regions:"0-95",host_cpus:"0-95",manifest_sha256:<PROMPT_SHA>,binary_sha256:<exact scratch server SHA>,start_epoch:<number>,end_epoch:<number>}`. ws58 owns creation and records its custody; NI only reads it. The command below must run under the actual region-lock claim, not merely with the environment variables set. `region-lock --timeout-s 60` bounds claim acquisition, while `run_role.py` sets its native deadline to the authority's `end_epoch` and drains 30 seconds before it. The owner sets an 1800-second authority window and its separate watchdog.

```bash
CAL_ID=codex-ni-df2-12-1-frontdoor-cal96-20261101
CAL_ROOT=/mnt/raid0/llm/tmp/codex-ni-df2-12-1-prep-20261101
CAL_STATE="$CAL_ROOT/calibration-live/state"
mkdir -p "$CAL_STATE"
WS58_CALIBRATION_AUTHORITY="$CAL_AUTHORITY" \
FILLER_ID="$CAL_ID" FILLER_CPUS=0-95 FILLER_STATE_DIR="$CAL_STATE" \
FILLER_PIDFILE="$CAL_STATE/$CAL_ID.pids" \
/workspace/repos/epyc-orchestrator/scripts/region-lock run \
  --cpu-list 0-95 --role bench-cpu --timeout-s 60 --tag "$CAL_ID" -- \
  /usr/bin/python3 "$CAL_ROOT/run_role.py" \
  --shape frontdoor_mtp --binary "$EXPERIMENTAL_CPU_SERVER" --port 18770 \
  --manifest "$CAL_ROOT/PROMPTS.json" --manifest-sha "$PROMPT_SHA" \
  --proof-dir "$PROOF_DIR" --out "$CAL_ROOT/calibration-live/run" --calibrate-only
```

The command is a staged template, not an executed claim. `run_role.py` preserves exact saved frontdoor argv: `-t 96 -np 4 -c 262144 --spec-type draft-mtp --spec-draft-n-max 4`, CPU backend, physical `taskset 0-95`; it launches one target completion only after same-image rollback PASS and template/tokenizer preflight. `calibrate_rate.py` writes `FIRST-REQUEST-INTENT.json` before `/completion`, then raw request/response/status/error before JSON parse, followed by attempt and ACCEPTED or UNKNOWN disposition. The intent binds exact body, rendered/tokenized maximum, manifest, image, argv, recipe, authority and observed server identity. `CALIBRATION-RATE.json` records output rate `generated_tokens/wall_s` under actual 96-CPU affinity. After verified own-server drain the runner seals `CALIBRATION-RATE-SEALED.json` with full argv, binary, image/rollback, raw HTTP, server log and drain hashes. Its `production_threads:96` and `measured_tok_s` can be used as v14 `rate_basis.evidence` **only after ws58 binds the authority, actual claim and first-request source receipts and the keeper's forecast accepts it**. No calibration has run; the original frozen rollback test fails from a proven test-oracle error, and the corrected test has not yet passed on a final own measurement image. NI may build/test that D2 scratch image under standing smoke rules without champion-owner acknowledgment; the actual 96-thread calibration remains a separate ws58-owned resource window. The estimate would be one recipe-bound sample, not a throughput distribution or science outcome.

The target READY `prompt_tokens_required` is separately computed as the exact maximum rendered/template token count from the accepted image before keeper nonce. Its value is unknown now; raw GGUF-vocab salted prompts were 95 tokens and are not that value. The calibration output's `prompt_tokens` must equal the READY declaration or the row is revised before qualification; no historical October log is used as a 96-thread rate claim.

## Architect GPU production-thread counterpart

The GPU science shape also needs a matching **eight-thread** rate. ws58 issues a separate bounded pregrant qualification-calibration authority for `codex-ni-df2-12-1-architect-cal8-20261101`: `regions:"mi210_0"`, `host_cpus:"184-191"`, exact GPU scratch-server SHA and same manifest SHA, 1800 s, GPU-quiet exclusive, scratch port 18783, 120 GiB RAM cap and 150 GiB disk floor. It claims **GPU quiet only** in region-lock and tasksets 184-191 inside the runner, avoiding inadvertent q3 folding; ws58 must prove the host threads and GPU are actually free. With `WS58_CALIBRATION_GPU_HELD=1` set only inside that owner-held claim, use the same `run_role.py --calibrate-only` template above with `--shape architect_dflash --binary "$EXPERIMENTAL_GPU_SERVER" --port 18783 --out "$CAL_ROOT/calibration-live-gpu/run"`, `FILLER_CPUS=184-191`, an isolated GPU state/PIDFILE, and `region-lock run --gpu-quiet exclusive --role bench-gpu --timeout-s 60`. The target code checks MI210 KFD membership and nonzero VRAM during compute; `calibrate_rate.py` requires actual unified KV, `-t8 -np4 -c393216 --spec-type draft-dflash --spec-draft-n-max7`, and eight-CPU client affinity. This is a distinct calibration exposure, never a FILLERS grant or DF2-12.1 science result.
