#!/bin/bash
# run_devc_add_gdb_20261112.sh -- add gdb to the devcontainer apt install line (operator decision tool 2026-11-11,
# "Grant r6 + add gdb"; autokernel row r6 needs gdb for crash backtraces and fails FUTILITY_NO_GDB without it).
#
# WHAT IT EDITS (only these two files; .devc/ is NOT a hook-protected path, but this script is the sole editor)
#   .devc/Dockerfile.patch      adds "+    gdb \" after the pciutils line, and keeps the unified-diff hunk counts
#                               and later hunk start offsets consistent (hunk 2 grows by one line)
#   .devcontainer/Dockerfile    adds "    gdb \" after pciutils (the file the container build actually reads)
#
#   Review (default; read-only, shows the diff and self-checks the patch arithmetic in a scratch dir):
#     bash scripts/operator/run_devc_add_gdb_20261112.sh
#   Apply (OPERATOR, on a TTY; edits the two files in place, then prints the rebuild command):
#     bash /workspace/scripts/operator/run_devc_add_gdb_20261112.sh --apply
#   Verify AFTER the rebuild, inside the new container:
#     bash /workspace/scripts/operator/run_devc_add_gdb_20261112.sh --verify
#
# REBUILD: this repo has no written rebuild procedure. The only documented entry point is the `devc` host CLI
# (scripts/nightshift/claude_via_devc.sh: "run 'devc /mnt/raid0/llm/epyc-root'"); this script prints
# `devc rebuild /mnt/raid0/llm/epyc-root`, which is the claude-code-devcontainer rebuild subcommand. Run it on the HOST,
# not in this container. The operator owns host/container restarts. A rebuild wipes ~/.local; see OBS-11 in handoffs.
# Idempotent. ROLLBACK: git checkout -- .devc/Dockerfile.patch .devcontainer/Dockerfile (or revert the commit).
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

ROOT="/workspace"
PATCH="$ROOT/.devc/Dockerfile.patch"
DOCKERFILE="$ROOT/.devcontainer/Dockerfile"
SCRATCH_PARENT="/mnt/raid0/llm/tmp"
HOST_PROJECT="/mnt/raid0/llm/epyc-root"

MODE="review"
case "${1:-}" in
  "") ;;
  --review|--dry-run) MODE="review" ;;
  --apply) MODE="apply" ;;
  --verify) MODE="verify" ;;
  *) echo "usage: $0 [--review | --apply | --verify]" >&2; exit 64 ;;
esac
die() { printf '\nREFUSING: %s\n' "$*" >&2; exit 65; }

if [ "$MODE" = "verify" ]; then
  if command -v gdb >/dev/null 2>&1; then
    echo "OK: gdb present: $(command -v gdb) ($(gdb --version | head -1))"
    exit 0
  fi
  echo "FAIL: gdb not found on PATH; the container was not rebuilt from the edited Dockerfile" >&2
  exit 1
fi

[ -f "$PATCH" ] && [ -f "$DOCKERFILE" ] || die "patch or Dockerfile missing"
command -v python3 >/dev/null && command -v patch >/dev/null || die "python3 and patch are required"
S="$(mktemp -d "$SCRATCH_PARENT/devc-add-gdb.XXXXXX")"
trap 'rm -rf "$S"' EXIT

python3 - "$PATCH" "$DOCKERFILE" "$S" <<'PY'
import re, sys, pathlib
patch_p, df_p, s = map(pathlib.Path, sys.argv[1:4])
pl = patch_p.read_text().split("\n")
dl = df_p.read_text().split("\n")

# --- Dockerfile: insert after the pciutils package line (inside the apt-get install block)
if any(l.strip() == "gdb \\" for l in dl):
    new_dl = dl
else:
    idx = [i for i, l in enumerate(dl) if l == "    pciutils \\"]
    assert len(idx) == 1, "expected exactly one pciutils line in Dockerfile"
    new_dl = dl[:idx[0] + 1] + ["    gdb \\"] + dl[idx[0] + 1:]

# --- patch: add the '+' line, bump that hunk's new-count and every later hunk's new-start
if any(l == "+    gdb \\" for l in pl):
    new_pl = pl
else:
    idx = [i for i, l in enumerate(pl) if l == "+    pciutils \\"]
    assert len(idx) == 1, "expected exactly one +pciutils line in patch"
    new_pl = pl[:idx[0] + 1] + ["+    gdb \\"] + pl[idx[0] + 1:]
    hdr = re.compile(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)$")
    hunk_of_line = None
    out, cur = [], 0
    for i, l in enumerate(new_pl):
        m = hdr.match(l)
        if m:
            cur += 1
            a, b, c, d, rest = m.groups()
            if i < idx[0] + 1 and True:
                pass
            out.append((i, cur, m))
        # no-op collecting
    # the hunk containing the new line is the last header before it
    target = max(h for h in out if h[0] < idx[0] + 1)[1]
    for i, k, m in out:
        a, b, c, d, rest = m.groups()
        c, d = int(c), int(d)
        if k == target:
            d += 1
        elif k > target:
            c += 1
        new_pl[i] = "@@ -%s,%s +%d,%d @@%s" % (a, b, c, d, rest)
(s / "patch.new").write_text("\n".join(new_pl))
(s / "Dockerfile.new").write_text("\n".join(new_dl))
PY

# self-check: reverse-apply the CURRENT patch to the current Dockerfile to recover the base, then the NEW patch on
# that base must reproduce the NEW Dockerfile byte for byte.
cp "$DOCKERFILE" "$S/base"
patch -s -R "$S/base" < "$PATCH" || die "current patch does not reverse-apply to the current Dockerfile (they already disagree before this change)"
cp "$S/base" "$S/rebuilt"
patch -s "$S/rebuilt" < "$S/patch.new" || die "new patch does not apply to the base (hunk arithmetic wrong)"
cmp -s "$S/rebuilt" "$S/Dockerfile.new" || die "new patch applied to base does not reproduce the new Dockerfile"
echo "self-check ok: base -> new patch -> new Dockerfile reproduces byte for byte"

echo; echo "== diff .devc/Dockerfile.patch =="; diff -u "$PATCH" "$S/patch.new" || true
echo; echo "== diff .devcontainer/Dockerfile =="; diff -u "$DOCKERFILE" "$S/Dockerfile.new" || true

if [ "$MODE" = "review" ]; then
  echo; echo "review only; nothing written. Apply with: bash $ROOT/scripts/operator/run_devc_add_gdb_20261112.sh --apply"
  exit 0
fi

[ -r /dev/tty ] && [ -t 0 ] || die "run --apply from a terminal"
cp "$S/patch.new" "$PATCH"
cp "$S/Dockerfile.new" "$DOCKERFILE"
echo; echo "APPLIED. Commit the two files (git add -- .devc/Dockerfile.patch .devcontainer/Dockerfile), then on the HOST run:"
echo
echo "    devc rebuild $HOST_PROJECT"
echo
echo "After the rebuild, inside the new container:"
echo "    bash $ROOT/scripts/operator/run_devc_add_gdb_20261112.sh --verify"
