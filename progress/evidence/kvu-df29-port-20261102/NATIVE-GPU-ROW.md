# V11-FA-2b native GPU validation row (proposal only)

## Scope and readiness

This row validates the original DF2-9 server reproducer on the six exact historical arms, with the private port-successor source. It makes no code/build changes and records no new claim until executed. The existing binaries and all three required model/template files were present at preparation time; recheck their hashes, build provenance, linkage, host admission, and free VRAM at the run boundary. A present path is not a freshness or approval proof.

Source bundle: `/mnt/raid0/llm/worktrees/mains/h-kvu/progress/evidence/kvu-df29-port-20261102/source/`
Patch proposal: `/mnt/raid0/llm/worktrees/mains/h-kvu/progress/evidence/kvu-df29-port-20261102/port-selector.patch`
Historical source pins: `.../final/artifacts/engineering/df29-port-source-20261031/ORIGINAL-SOURCE-PINS.json`.

## Arms (all required; do not substitute the superseded D build)

| Arm | Exact arm directory | Role |
|---|---|---|
| A | `/mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-A` | ROCm WMMA on |
| B | `/mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-B` | ROCm WMMA off, baseline |
| C | `/mnt/raid0/llm/kernels/builds/gpu-20261004-5026470c6-C` | B + #27870 + #28576 |
| D | `/mnt/raid0/llm/kernels/builds/gpu-20261004-fa5ebc0c8-D` | C + CDNA D=256 tuning (current D, not 2e0f9dd06) |
| E | `/mnt/raid0/llm/kernels/builds/gpu-20261004-e9b3b04df-E` | B + #27870 |
| M | `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/build-master-11fe02151` | upstream master comparison |

Pinned inputs inherited unchanged from the historical DF2-9 kit:
- target `/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf`
- drafter `/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf`
- template `/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja`
- prompt JSON is the byte-pinned `prompts/server_prompts.json` in the source bundle.

## Execution contract

Run only in an admitted exclusive MI210 GPU window with the normal region/CPU placement and linkage controls. Reverify all arm `bin/llama-server` identities against approved manifests and the linkage verifier immediately before launch. Require the existing helper preflight (at least 38 GiB free VRAM), no other GPU tenant, and capture per-arm binary/hash/linkage evidence. Do not stop any process except PIDs captured and owned by this runner.

Use the successor runner directly so it selects a bindable loopback port per invocation; do not pass `--port` (explicit busy ports must refuse). Each arm runs both original configs with the historical defaults and cap:

```bash
KIT=/mnt/raid0/llm/tmp/refactor-01a16fc3/df29-port-private-20261031/final/scripts/benchmark/df29
OUT=/mnt/raid0/llm/tmp/df29-port-native-slot-<UTC timestamp>
mkdir -p "$OUT"
for spec in \
  A:/mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-A \
  B:/mnt/raid0/llm/kernels/builds/gpu-20261004-90c12df42-B \
  C:/mnt/raid0/llm/kernels/builds/gpu-20261004-5026470c6-C \
  D:/mnt/raid0/llm/kernels/builds/gpu-20261004-fa5ebc0c8-D \
  E:/mnt/raid0/llm/kernels/builds/gpu-20261004-e9b3b04df-E \
  M:/mnt/raid0/llm/tmp/v11-fa-ab-20261004/build-master-11fe02151; do
  arm=${spec%%:*}; build=${spec#*:}
  timeout 340 "$KIT/df29_server.sh" "$build" "$OUT/$arm" --arm "$arm" --configs orig,prod --cap 300 \
    >"$OUT/$arm.console" 2>&1
  rc=$?
  printf 'arm=%s rc=%s\n' "$arm" "$rc" >> "$OUT/launcher-status.txt"
done
grep -h '^DF29 ' "$OUT"/*/verdicts.txt
```

The executing wrapper must preserve per-arm nonzero exit codes while continuing to collect all arm verdicts, and must write `ERROR` for missing verdicts. A slot is complete only with both `orig` and `prod` verdict lines for each of A/B/C/D/E/M (12 total), plus per-arm provenance/linkage and cleanup evidence. PASS/FAIL/ERROR/INCOMPLETE remain separate; no aggregation may silently drop errors. Arm A is the positive control. The actual server verdict is the required native evidence; `--select-port-only` and mock tests do not count.

Estimated wall envelope: six arms × 300 s cap plus 40 s outer guard each = 34 min maximum, excluding admission/setup. Budget >= 40 min of exclusive slot recommended.

## Current evidence (offline only)

- Six model-free port/ownership tests pass with real loopback sockets: 6/6.
- Proposed shell files pass `bash -n`.
- No GPU server or inference was started; no native verdict exists yet.
