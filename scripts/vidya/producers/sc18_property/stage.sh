#!/bin/bash
set -euo pipefail
source_dir=$(cd "$(dirname "$0")" && pwd)
root=$(git -C "$source_dir" rev-parse --show-toplevel)
packet=/mnt/raid0/llm/tmp/vidya-belief-substrate/property-current
store=/mnt/raid0/llm/kernels/builds
experimental=/mnt/raid0/llm/llama.cpp-experimental
research=/workspace/repos/epyc-inference-research
research_commit=6decaeda4481a841b3a85b55b0be87a6963b3042
candidate=cpu-20261024-c72ec82f5-c5
anchor=cpu-20261024-cdb4d8c77-c4
if [[ -e "$packet" ]]; then
  echo "Refusing to overwrite existing packet: $packet" >&2
  exit 1
fi
mkdir -p "$packet"/{candidate/bin,anchor/bin,source,research,scripts}
cp "$source_dir"/{run_property.py,launch.sh,spec.json} "$packet/"
cp "$research/scripts/utils/verify_ggml_linkage.sh" "$packet/"
cp -a "$store/$candidate/bin/test-backend-ops" "$store/$candidate/bin"/libggml*.so* "$packet/candidate/bin/"
cp -a "$store/$anchor/bin/test-backend-ops" "$store/$anchor/bin"/libggml*.so* "$packet/anchor/bin/"
for file in SHA256SUMS PROVENANCE.md; do
  cp "$store/$candidate/$file" "$packet/source/candidate-$file"
  cp "$store/$anchor/$file" "$packet/source/anchor-$file"
done
git -C "$experimental" show c72ec82f5417bb2937310326120f149b665e8400:tests/test-backend-ops.cpp \
  > "$packet/source/c5-test-backend-ops.cpp"
git -C "$research" archive "$research_commit" scripts/kernel_rnd/autokernel scripts/lib/canonical_recipe.py \
  | tar -x -C "$packet/research" --wildcards '*/autokernel/*.py' 'scripts/lib/canonical_recipe.py'
tar -C "$root/scripts" --exclude=__pycache__ --exclude=.pytest_cache -cf - vidya \
  | tar -x -C "$packet/scripts"
cd "$packet"
find candidate anchor source research scripts -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum > PINNED.sha256
sha256sum run_property.py launch.sh spec.json verify_ggml_linkage.sh >> PINNED.sha256
chmod +x launch.sh
/usr/bin/python3 -BI run_property.py verify
