#!/bin/bash
set -euo pipefail
# Apply only to a clean, separately checked out upstream tree.
root=$(cd "$(dirname "$0")" && pwd)
tree=${1:?usage: apply-patches.sh UPSTREAM_CHECKOUT}
expected=21b6668a49a342c843e679cc5ed16081064a5768
[[ $(git -C "$tree" rev-parse HEAD) == "$expected" ]] || { echo 'wrong upstream commit' >&2; exit 1; }
[[ -z $(git -C "$tree" status --porcelain) ]] || { echo 'checkout is not clean' >&2; exit 1; }
for patch in "$root"/patches/*.patch; do
    git -C "$tree" apply --check "$patch"
    git -C "$tree" apply "$patch"
done
git -C "$tree" diff --check
