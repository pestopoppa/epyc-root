#!/bin/bash
# The change-topology checker as it will be once the DFLASH2 package's ROOT patch lands
# (it teaches topology_check.py that `device: none` is the launcher's CPU spelling). That
# root patch still `git apply --check`s on /workspace, i.e. it was never applied; until it
# is, the checker fails on worker_vision for BOTH base and candidate. Scratch copy only.
set -uo pipefail
PKG=/mnt/raid0/llm/tmp/stack-change-kvpool-20261003
RS="$PKG/root-scratch"
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
rm -rf "$RS"; mkdir -p "$RS/.claude/skills/change-topology/scripts"
cp -p /workspace/.claude/skills/change-topology/scripts/topology_check.py "$RS/.claude/skills/change-topology/scripts/"
(cd "$RS" && git apply /mnt/raid0/llm/tmp/stack-change-dflash2-20261003/patches/root/stackchg-dflash2-20261003.root.patch)
for t in base pristine; do
  echo "== $t (DFLASH2 root patch applied to a scratch copy of topology_check.py)"
  "$PY" "$RS/.claude/skills/change-topology/scripts/topology_check.py" --orchestrator "$PKG/sandbox-$t/orchestrator" \
    --intent "$PKG/intent.yaml" 2>&1 | tail -3
  echo "rc=${PIPESTATUS[0]}"
done
