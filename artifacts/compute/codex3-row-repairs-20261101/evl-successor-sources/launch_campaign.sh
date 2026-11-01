#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-row-repairs-20261101/evl-successor
# The literal catalog digest pins every member before any host entry executes.
EXPECTED_CATALOG_SHA256=0815be1a48d142890e09fffe5777b553dbdbc15a218e5715df03485214b67ba3
[[ $(sha256sum "$D/CAMPAIGN-SOURCES.sha256" | cut -d' ' -f1) == "$EXPECTED_CATALOG_SHA256" ]] || { echo 'source catalog digest mismatch' >&2; exit 78; }
sha256sum --quiet -c "$D/CAMPAIGN-SOURCES.sha256" || { echo 'source catalog member mismatch' >&2; exit 78; }
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1
cd "$D"
: "${EVL34_EXTRA_HEADROOM_BYTES:=0}"
export EVL34_EXTRA_HEADROOM_BYTES
EVL34_REQUIREMENTS_FREEZE=/mnt/micron/codex3-lanes/root/artifacts/compute/codex3-row-repairs-20261101/requirements-freeze.txt
export EVL34_REQUIREMENTS_FREEZE
host=(sudo -n --preserve-env=HOME,FILLER_ID,FILLER_CPUS,FILLER_THREADS,FILLER_NEEDGPU,FILLER_END,FILLER_DEADLINE,FILLER_PIDFILE,EVL34_EXTRA_HEADROOM_BYTES,EVL34_PREFLIGHT_LOG,EVL34_REQUIREMENTS_FREEZE /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/host-entry.sh")
# Disabled until the canonical LOOP49 engine and approved qualification exist.
echo 'UNQUALIFIED: canonical LOOP49 engine and qualification required' >&2
exit 78
