#!/bin/bash
# Offline validation: each successor job.py's verified_coverage() against its predecessor's sealed analyze logs,
# then with one synthetic genuine skip line appended (must FAIL), then with a heap skip that is not whitespace-only (must FAIL).
set -uo pipefail
T=/mnt/raid0/llm/tmp; R=$T/kpf-coverage-fix-20261105/replay.py; H=$T/heterogeneous-slot-fabric-residency
pairs=("$T/kvu/kpf131-impact-r5-20261105|$T/kvu/kpf131-impact-r4-20261105"
       "$T/kvfork/kpf17-oracle-impact-8952-20261105-r2|$T/kvfork/kpf17-oracle-impact-8952-20261105"
       "$H/kpf182-component-impact-8952-20261105-r3|$H/kpf182-component-impact-8952-20261105-r2")
for i in kpf26-attestation-impact-8682-20261105 kpf27d-impact-326f-successor-20261105 kpf625-server-impact-8952-20261105 kpf191-drafter-impact-8952-20261105; do pairs+=("$H/$i-r2|$H/$i"); done
for p in "${pairs[@]}"; do
  n=${p%%|*}; o=${p##*|}
  echo "== $(basename $n)"
  echo -n "  real logs:        "; out=$(python3 $R $n/job.py $o/out < /dev/null) || true; printf "%s\n" "${out:0:220}"
  echo -n "  +real skip line:  "; out=$(python3 $R $n/job.py $o/out "Skipping 3 files: unsupported grammar" < /dev/null) || true; printf "%s\n" "${out:0:160}"
  echo -n "  +heap cpp skip=2: "; out=$(python3 $R $n/job.py $o/out "$(printf '[gitnexus-heap] sr-extract-start used_mb=1 rss_mb=1 lang=cpp files=5\n[gitnexus-heap] sr-extract-end used_mb=1 rss_mb=1 lang=cpp parsedFiles=3 preExtractedHits=3 skipped=2')" < /dev/null) || true; printf "%s\n" "${out:0:160}"
done
