#!/bin/bash
# Snapshot and verify inputs before the owner publishes this finite row.
set -euo pipefail
umask 077
P="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$P" rev-parse --show-toplevel)"
D="${1:?absolute run directory}"
U="${2:?AdaMAST checkout}"
REV=3c83d81c85937f5e8911fd96daa2ca38c1ad2585
MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
MODEL_SHA=a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348
SERVER=/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/llama-server
TEMPLATE=/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
CLAUDE="${FM2_CLAUDE_ROOT:-/home/node/.claude/projects/-workspace}"
CODEX="${FM2_CODEX_ROOT:-/home/node/.codex/sessions}"
[[ "$D" == /* && "$D" =~ ^[a-zA-Z0-9_/.-]+$ ]]
[[ ! -e "$D/SOURCE.sha256" ]]
mkdir -p "$D/code" "$D/inputs"
chmod 700 "$D"
model_stat="$(stat -Lc '%d:%i:%s:%Y:%Z' "$MODEL")"
if [ ! -s "$D/model.sha256" ]; then
  ionice -c3 nice -n 19 /usr/bin/sha256sum "$MODEL" > "$D/model.sha256.part"
  mv "$D/model.sha256.part" "$D/model.sha256"
fi
[[ "$(cat "$D/model.sha256")" == "$MODEL_SHA  $MODEL" ]]
[[ "$(stat -Lc '%d:%i:%s:%Y:%Z' "$MODEL")" == "$model_stat" ]]
git -C "$U" archive "$REV" adamast LICENSE | tar -x -C "$D/code"
(cd "$D/code" && git apply "$P/adamast_local.patch")
cp "$P/"{job.sh,precond.sh,pilot.py,fm2_transport.py,own_port_proof.py,mast_fseries_crosswalk.json,adamast_local.patch} "$D/code/"
cp /mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/qwen_thinking_lib.sh "$D/code/"
cp /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/code/"
cp "$REPO/scripts/coordination/"{adamast_normalize,delegation_accounting}.py "$D/code/"
sed "s|@RUN_DIR@|$D|g" "$P/launch.sh" > "$D/code/launch.sh"
sed "s|@RUN_DIR@|$D|g" "$P/spec.json" > "$D/spec.json"
cat > "$D/code/model.env" <<PINS
FM2_SERVER_BIN=$SERVER
FM2_MODEL_GGUF=$MODEL
FM2_MODEL_STAT=$model_stat
FM2_TEMPLATE=$TEMPLATE
FM2_PY=$PY
PINS
SERVER_DIR="$(dirname "$SERVER")"
cat > "$D/KERNEL.sha256" <<PINS
4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c  $SERVER
64817c163bf7efdd4eb6cd46ca97749199d299949131970a9a49c36dcfd3ef57  $SERVER_DIR/libllama-server-impl.so
1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551  $TEMPLATE
PINS
if [ ! -s "$D/inputs/manifest.json" ]; then
  /usr/bin/python3 -I -B "$D/code/adamast_normalize.py" sample --claude-root "$CLAUDE" --codex-root "$CODEX" \
    --per-stratum 3 --seed fm2-adamast-20261118 --manifest "$D/inputs/manifest.json.part"
  mv "$D/inputs/manifest.json.part" "$D/inputs/manifest.json"
fi
if [ ! -s "$D/inputs/index.jsonl" ]; then
  /usr/bin/python3 -I -B "$D/code/adamast_normalize.py" normalize --check \
    --manifest "$D/inputs/manifest.json" --out-dir "$D/inputs"
fi
(
  cd "$D/code"
  "$PY" -B - "$REV" "$MODEL_SHA" <<'PY'
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import httpx
import openai
from adamast.core.trace_formats import load_trace_bundle
from adamast.judges.contract import _prepare_taxonomy

inputs = Path("../inputs")
manifest = json.loads((inputs / "manifest.json").read_text())
traces = []
for path in sorted((inputs / "traces").glob("*.jsonl")):
    trace = load_trace_bundle(path).traces[0]
    original = json.loads(path.read_bytes())
    assert trace["problem_id"] == path.stem == original["problem_id"]
    assert set(original) == {"problem_id", "task", "raw_trajectory", "metadata"}
    traces.append(original)
assert len(traces) == len(manifest["entries"])
assert {trace["metadata"]["harness"] for trace in traces} == {"claude", "codex"}
assert {trace["metadata"]["harness"] for trace in traces if trace["metadata"]["kind"] == "subagent"} == {"claude", "codex"}
taxonomy_path = Path("adamast/core/mast.json")
_, codes = _prepare_taxonomy(taxonomy_path, allow_review_required=False)
assert {code["id"] for code in codes} == {f"MAST-{i}" for i in range(1, 15)}
crosswalk = Path("mast_fseries_crosswalk.json")
assert {entry["mast"] for entry in json.loads(crosswalk.read_text())["mappings"]} == {code["id"] for code in codes}
smoke = min((trace for trace in traces if trace["task"]), key=lambda trace: len(trace["raw_trajectory"]))
pins = {
    "prepared_at": datetime.now(timezone.utc).isoformat(),
    "adamast_commit": sys.argv[1], "model_sha256": sys.argv[2],
    "model_bytes": 29047086048, "kernel_version": "10303 (ffc1bac82)",
    "kernel_manifest_sha256": sha256(Path("../KERNEL.sha256").read_bytes()).hexdigest(),
    "package_patch_sha256": sha256(Path("adamast_local.patch").read_bytes()).hexdigest(),
    "taxonomy_sha256": sha256(taxonomy_path.read_bytes()).hexdigest(),
    "crosswalk_sha256": sha256(crosswalk.read_bytes()).hexdigest(),
    "sample_manifest_sha256": manifest["manifest_sha256"],
    "sample_size": len(traces), "sample_strata": dict(Counter(t["metadata"]["stratum"] for t in traces)),
    "openai_sdk": openai.__version__, "httpx": httpx.__version__,
    "smoke_unit": smoke["problem_id"],
}
Path("pins.json").write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n")
PY
  "$PY" -B -m adamast judge --help >/dev/null
)
(cd "$D" && find code inputs -type f -print0 | sort -z | xargs -0 /usr/bin/sha256sum > SOURCE.sha256.part)
(cd "$D" && /usr/bin/sha256sum KERNEL.sha256 model.sha256 >> SOURCE.sha256.part && mv SOURCE.sha256.part SOURCE.sha256)
chmod 700 "$D/code/"*.sh
/bin/bash "$D/code/precond.sh"
