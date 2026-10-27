#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/t96/packet
[ "$(awk '/Cpus_allowed_list/{print $2}' /proc/self/status)" = 72-73 ] || exit 70
bash -n "$D/launch.sh" "$D/job.sh"
/usr/bin/python3 -B -c 'import ast, pathlib; ast.parse(pathlib.Path("/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/t96/packet/driver.py").read_text()); print("driver syntax PASS")'
/usr/bin/python3 -B "$D/deps/dryrun_check.py" run --id rtg57-c5-vkq-t96 --row-file "$D/ROW.md" --min-window-s 5100 --launcher "$D/launch.sh" --job "$D/job.sh" --engine "$D/deps/filler_run12.sh" --source-manifest "$D/SOURCES.sha256" --scoped-pf --entry-json '["/bin/bash","/mnt/raid0/llm/tmp/codex-ni-20261027-rtg57-f32-completion/t96/packet/launch.sh"]' --effect first-model-load --regions 72-73 --required-cpus 72-73 --allowed-cpus 72-73 --cwd "$D" --region-lock-shim "$D/pf-shim.sh" --timeout-s 90
