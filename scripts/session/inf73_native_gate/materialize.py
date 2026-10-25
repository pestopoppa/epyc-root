#!/usr/bin/env python3
"""PROPOSED granted-only materializer. Shared source is read-only.
Future owner grant permits a new private local clone and exact sparse checkout.
"""
import hashlib
import re
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runner import Refused, read_tree, verify_materialized

def private_clone(repository, commit, tree_text, readset_text, destination, run=subprocess.run):
    destination = Path(destination).absolute()
    if destination.exists():
        raise Refused("private clone destination exists")
    complete = read_tree(tree_text, regular_only=False)
    selected = read_tree(readset_text)
    if any(complete.get(path) != identity for path, identity in selected.items()):
        raise Refused("private clone readset differs from sealed complete tree")
    if not Path(repository).is_absolute() or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise Refused("only exact local repository/commit identities are allowed")
    run(["git", "clone", "--shared", "--no-hardlinks", "--no-checkout", "--", str(repository), str(destination)], check=True)
    # Object alternates are private clone metadata; canonical clone stays read-only.
    patterns = "\n".join("/" + path for path in selected) + "\n"
    run(["git", "-C", str(destination), "sparse-checkout", "set", "--no-cone", "--stdin"], input=patterns, text=True, check=True)
    run(["git", "-C", str(destination), "checkout", "--detach", commit], check=True)
    verify_materialized(destination, selected)
    return len(selected)

def copy_runtime(closure, source_root, destination):
    """Copy only sealed package files; system stdlib/ELF references stay readonly."""
    destination = Path(destination)
    if destination.exists():
        raise Refused("private runtime destination exists")
    destination.mkdir(parents=True)
    source_root = Path(source_root)
    for original, expected in closure["files"].items():
        source = Path(original)
        if not source.is_relative_to(source_root):
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise Refused("runtime package drift before copy")
        target = destination / source.relative_to(source_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(source.read_bytes())
        target.chmod(source.stat().st_mode & 0o777)
    for original in closure["symlinks"]:
        if Path(original).is_relative_to(source_root):
            raise Refused("package symlink requires explicit materialization review")

def materialize(repository, commit, tree_text, readset_text, destination, git=subprocess.check_output):
    destination = Path(destination)
    if destination.exists():
        raise Refused("destination exists; no overwrite")
    complete = read_tree(tree_text, regular_only=False)
    readset = read_tree(readset_text)
    if any(complete.get(path) != identity for path, identity in readset.items()):
        raise Refused("readset is not exact subset of approved commit")
    actual = git(["git", "-C", str(repository), "ls-tree", "-r", commit], text=True)
    if actual != tree_text:
        raise Refused("actual immutable Git tree differs from sealed commit map")
    destination.mkdir(parents=True)
    # Failed partial materializations are retained for diagnosis and never accepted/reused.
    for relative, (mode, blob) in readset.items():
        body = git(["git", "-C", str(repository), "cat-file", "blob", blob])
        if hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest() != blob:
            raise Refused("Git transport returned different blob bytes")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as output:
            output.write(body)
        target.chmod(0o755 if mode == "100755" else 0o644)
    verify_materialized(destination, readset)
    return len(readset)

# Only prepare.py may invoke these library functions, after its canonical grant checks.
if __name__ == "__main__":
    raise SystemExit("REFUSED: library-only materializer; use the canonical granted prepare job")
