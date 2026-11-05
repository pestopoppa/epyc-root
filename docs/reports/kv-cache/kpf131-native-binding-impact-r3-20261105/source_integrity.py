"""Small model-free source-tree custody helpers for the impact runner."""
import subprocess


def untracked_index_affecting_paths(tree):
    """List untracked non-ignored files; GitNexus private metadata stays excluded."""
    raw = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=tree,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    return [path.decode("utf-8", errors="surrogateescape") for path in raw.split(b"\0") if path]
