#!/bin/bash
set -euo pipefail
script=$(cd "$(dirname "$0")/../.." && pwd)/scripts/safety/path_identity.sh
base=$(mktemp -d /tmp/path-identity.XXXXXXXX)
trap 'rm -rf "$base"' EXIT
mkdir -p "$base/bin" "$base/mount/a" "$base/mount/b"
printf data > "$base/mount/a/object"
ln "$base/mount/a/object" "$base/mount/b/alias"
[[ $(stat -c %d "$base/mount") != $(stat -c %d /mnt/raid0/llm/tmp) ]] || { echo 'fixture needs two devices' >&2; exit 1; }
cat > "$base/bin/findmnt" <<'MOCK'
#!/bin/bash
if [[ $1 == -T ]]; then printf '%s\n' "$IDENTITY_TEST_MOUNT test ext4"; exit 0; fi
if [[ $1 == -rn && $2 == -o && $3 == TARGET ]]; then printf '%s\n' "$IDENTITY_TEST_MOUNT" /mnt/raid0/llm/tmp; exit 0; fi
# Typical non-raw tree formatting cannot be consumed as a path.
printf '├─%s\n└─/mnt/raid0/llm/tmp\n' "$IDENTITY_TEST_MOUNT"
MOCK
cat > "$base/bin/find" <<'MOCK'
#!/bin/bash
printf '%s\n' "$1" >> "$IDENTITY_TEST_FIND_LOG"
[[ ${IDENTITY_TEST_FAIL_FIND:-0} != 1 ]] || { echo 'simulated traversal failure' >&2; exit 9; }
exec /usr/bin/find "$@"
MOCK
chmod +x "$base/bin/findmnt" "$base/bin/find"
export PATH="$base/bin:$PATH" IDENTITY_TEST_MOUNT="$base/mount" IDENTITY_TEST_FIND_LOG="$base/find.log"
bash "$script" "$base/mount/a/object" > "$base/out"
grep -F "ALIAS: $base/mount/a/object" "$base/out" >/dev/null
grep -F "ALIAS: $base/mount/b/alias" "$base/out" >/dev/null
[[ $(wc -l < "$base/find.log") == 1 ]]
! grep -Fx /mnt/raid0/llm/tmp "$base/find.log" >/dev/null
if IDENTITY_TEST_FAIL_FIND=1 bash "$script" "$base/mount/a/object" > "$base/fail-out" 2>&1; then
    echo 'failed traversal incorrectly succeeded' >&2; exit 1
fi
grep -F 'Alias traversal failed' "$base/fail-out" >/dev/null
printf 'path identity fixture PASS\n'
