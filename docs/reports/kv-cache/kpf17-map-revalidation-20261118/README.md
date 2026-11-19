# KPF-17 second-call map revalidation

The official row `vb-kpf17-map-revalidation-20261118` completed its one model-free case at 19:07:41 UTC on CPUs 16–19. The retained validator accepted all five baseline files. After the synchronized in-place overwrite, the second `validate_maps` call refused the changed `libggml.so` with `ValueError: unattested mapped library`. The monotonic barrier orders the baseline acceptance, worker readiness, overwrite, and second call and return. The native receipt records fixture cleanup. The observation covers this private fixture through the second call. [Official result and original attempt bytes](../../../../data/vidya/kpf17-native-20261118/).

The retained publisher job's `complete` check returned zero on the original packet. The current `origin/main` reader at `d734f83b81c09528e2d77df56e61e201c4e8f3c2` ingested the original sidecar through `kv-prefix-fork` into a scratch ledger. It projected one row and three frames with zero refusals, declines, or missing inputs. The ledger chain verified at frontier 3. A direct observation query allowed `clm_kpf17-map-c539c3ecbf4ab11b1bf388ecb6c481486aa61128af86e1cbc00568596c715ce6` at `Judged/Located`. [Strict ingest](../../../../data/vidya/kpf17-native-20261118/review/kpf17-ingest.json) and [observation query](../../../../data/vidya/kpf17-native-20261118/review/direct-query.json).

The original reader returned `ready` for AutoKernel CPU and GPU model targets and the AutoPilot production lineup. Each response reported `no_applicable_claims`, empty claim and tried lists, and zero claims across all tiers. [AutoKernel context](../../../../data/vidya/kpf17-native-20261118/review/autokernel-context.json) and [AutoPilot context](../../../../data/vidya/kpf17-native-20261118/review/autopilot-context.json).

The shared planner reader accepts the standalone target `{"scope":"task","task_id":"VB-KPF17-MAP-REVALIDATION-WIRE"}` for `kvfork.planner`. Local replay strictly projected the retained bytes into three verified scratch frames. The exact task assembled the one native `Judged/Located` observation and its one tried-mechanisms entry. The wrong task, wrong consumer, CPU model, GPU model and production lineup each returned empty claim and tried lists. The task selection policy leaves the original ledger frames unscoped and preserves the observation's second-call fixture limit. [Recorded planning context](planning-context.json) and [replay command](../../../../scripts/vidya/canary/kpf17_task_context.py).

## Replay

The retained `RESULT.json` preserves the original absolute sidecar locator. To verify the byte copy and strictly project its sidecar from a checkout, run the following from the repository root. The dry run checks the original native receipts and seals without executing the fixture.

```bash
package=data/vidya/kpf17-native-20261118
(cd "$package" && sha256sum -c SHA256SUMS)
nonce=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["nonce"])' "$package/RESULT.json")
scratch=$(mktemp -d)
python3 -B scripts/vidya/cli.py --ledger "$scratch/ledger.jsonl" --json \
  ingest kv-prefix-fork --path "$package/attempts/$nonce/belief_measurements.jsonl" \
  --as-of "$(cat "$package/review/as-of.txt")" --dry-run
```

The retained context responses record the two consumer IDs, normalized targets, reader checkout, and verified scratch ledger head. Both came from `loop_beliefs.py prepare` using the scratch ledger and an empty scratch intake index. No inference ran during verification.

To replay the task planning context and its exclusions from a current checkout, pass a fresh output path.

```bash
python3 -B scripts/vidya/canary/kpf17_task_context.py \
  data/vidya/kpf17-native-20261118 "$(mktemp -d)/context"
```

[Original planning answers and focused test output](planning-controls/) retain the exact CLI answer, five exclusions, original strict ingest and scratch-read log. [Verification details](verification.json) record the checks and publisher refusal; the unused allocator packet was retired after refusal.
