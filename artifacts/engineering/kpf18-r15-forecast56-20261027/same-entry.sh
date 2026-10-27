#!/bin/bash
set -euo pipefail
source /mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-r15-repair/successor/config.sh
WATCH=/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56
source "$BASE/pf-context.sh"; hsf_pf_context
[[ ! -e "$BASE/forecast56-dryrun" && ! -L "$BASE/forecast56-dryrun" ]] || refuse 'preserve existing forecast proof'
"$PY" -B -I "$BASE/gate/dryrun_check.py" run --id "$ID" --row-file "$WATCH/ROW-56.md" --min-window-s 8700 --launcher "$WATCH/launch.sh" --job "$BASE/job.sh" --engine "$ENGINE" --source-manifest "$WATCH/SOURCE.sha256" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-forecast56/launch.sh"]' --effect native-model-preload --regions "mi210_0,$PF_CPUS" --required-cpus "$PF_CPUS" --allowed-cpus "$PF_CPUS" --cwd "$BASE" --region-lock-shim "$BASE/region-lock-shim.sh" --timeout-s 90 > "$WATCH/SAME-ENTRY.log" 2>&1
box=$("$PY" -B -I - "$WATCH/SAME-ENTRY.log" "$BASE/dryrun" <<'PY'
import json,pathlib,sys
lines=[x.removeprefix('DRYRUN_ENTRY ') for x in pathlib.Path(sys.argv[1]).read_text().splitlines() if x.startswith('DRYRUN_ENTRY ')]
if len(lines)!=1:raise SystemExit('expected one nonce-bound entry')
box=pathlib.Path(json.loads(lines[0])['box']).resolve(strict=True)
if box.parent!=pathlib.Path(sys.argv[2]).resolve(strict=True) or not (box/'pass.json').is_file():raise SystemExit('missing or foreign proof')
print(box)
PY
)
mkdir "$BASE/forecast56-dryrun"
cp -a "$box/." "$BASE/forecast56-dryrun/"
printf 'SAME_ENTRY_PASS actual_model_load=false actual_transport=false actual_GPU_lock=false\n'
