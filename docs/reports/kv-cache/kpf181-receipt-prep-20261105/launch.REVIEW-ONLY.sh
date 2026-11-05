#!/bin/bash
set -euo pipefail
# This fixed guard makes the candidate non-runnable, even if invoked manually.
echo 'REFUSED: unqualified KPF181 migration draft; no target execution' >&2
exit 78
# No unreachable legacy dispatch is retained in this isolated copy.
