#!/bin/bash
set -euo pipefail
# Static review guard: removal needs fresh source pins and owner review.
echo 'REFUSED: KPF181 qualification/production integration is not enabled' >&2
exit 78
# No unreachable legacy dispatch is retained in this isolated copy.
