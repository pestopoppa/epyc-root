"""Install only the lane-owned AM changes into a clean pinned scratch worktree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN = "c9f2e34cea7a0e9ddac5ad7b2088bf06b56ee1db"
HERE = Path(__file__).resolve().parent


def install(source, check=False):
    source = Path(source).resolve()

    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], text=True).strip()

    if git("rev-parse", "HEAD") != PIN:
        raise ValueError("AM integration requires the pinned experimental source commit")
    # Require a real detached worktree, never the frozen serving checkout.
    if not (source / ".git").is_file() or git("branch", "--show-current"):
        raise ValueError("AM integration requires a detached scratch git worktree")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ValueError("AM integration requires a clean scratch worktree")
    patch = HERE / "integration.patch"
    git("apply", "--check", str(patch))
    owned = [patch, HERE / "native_carrier.h", HERE / "native_runtime.h"]
    if not check:
        git("apply", str(patch))
        for path in owned[1:]:
            (source / "src" / path.name).write_bytes(path.read_bytes())
    return {
        "schema": "epyc.am.integration-install.v1", "source_commit": PIN,
        "source": str(source), "check_only": check,
        "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in owned},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(install(args.source, args.check), indent=2))
