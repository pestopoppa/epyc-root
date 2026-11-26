"""Remove or move untracked files inside one Taskflow worker's Git worktree."""

import os
import stat
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path


DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
RESERVED_PARTS = {"..", ".git", ".taskflow-refs"}


def git_output(lane: Path, *args: str) -> bytes:
    # Always inspect the lane's own index and HEAD, including in linked worktrees.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    return subprocess.run(["git", "--literal-pathspecs", "-C", str(lane), *args], env=env,
                          capture_output=True, check=True).stdout


def require_untracked(lane: Path, paths: list[Path]) -> None:
    for path in paths:
        if (git_output(lane, "ls-files", "--cached", "-z", "--", str(path))
                or git_output(lane, "ls-tree", "-z", "HEAD", "--", str(path))):
            raise ValueError(f"tracked path: {str(path)!r}")


def relative_file(cwd: Path, operand: str) -> Path:
    path = Path(operand)
    parts = cwd.parts + path.parts
    if (not operand or path.is_absolute() or operand.startswith("-")
            or any(part.casefold() in RESERVED_PARTS for part in parts)):
        raise ValueError(f"expected a worktree-relative scratch path: {operand!r}")
    return cwd / path


def mode_at(parent_fd: int, name: str) -> int:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False).st_mode
    except FileNotFoundError:
        return 0


def open_directory(root_fd: int, directory: Path, stack: ExitStack) -> int:
    fd = root_fd
    for part in directory.parts:
        fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
        stack.callback(os.close, fd)
        if mode_at(fd, ".git"):
            raise ValueError(f"nested Git worktree: {str(directory)!r}")
    return fd


def clean_scratch(lane: Path, cwd: Path, operation: str, operands: list[str]) -> None:
    if operation not in {"rm", "mv"} or not operands or (operation == "mv" and len(operands) != 2):
        raise ValueError("use taskflow-scratch rm <file> [...] or taskflow-scratch mv <source> <destination>")
    lane = lane.resolve(strict=True)
    cwd = cwd.resolve(strict=True).relative_to(lane)
    if git_output(lane, "rev-parse", "--show-prefix").strip():
        raise ValueError("scratch root must be a Git worktree root")
    paths = [relative_file(cwd, operand) for operand in operands]
    with ExitStack() as stack:
        root_fd = os.open(lane, DIRECTORY_FLAGS)
        stack.callback(os.close, root_fd)
        sources = list(dict.fromkeys(paths if operation == "rm" else paths[:1]))
        require_untracked(lane, sources)
        source_fds = [open_directory(root_fd, path.parent, stack) for path in sources]
        for path, fd in zip(sources, source_fds):
            mode = mode_at(fd, path.name)
            if not mode or stat.S_ISDIR(mode):
                raise ValueError(f"expected an existing scratch file: {str(path)!r}")

        if operation == "rm":
            for path, fd in zip(sources, source_fds):
                os.unlink(path.name, dir_fd=fd)
            return

        source, dest = paths
        dest_fd = open_directory(root_fd, dest.parent, stack)
        if not dest.parts or stat.S_ISDIR(mode_at(dest_fd, dest.name)):
            dest_fd = open_directory(root_fd, dest, stack)
            dest /= source.name
        require_untracked(lane, [dest])
        if stat.S_ISLNK(mode_at(dest_fd, dest.name)):
            raise ValueError(f"move destination is a symbolic link: {str(dest)!r}")
        os.replace(source.name, dest.name, src_dir_fd=source_fds[0], dst_dir_fd=dest_fd)


def main() -> int:
    try:
        lane, operation, *operands = sys.argv[1:]
        clean_scratch(Path(lane), Path.cwd(), operation, operands)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"taskflow-scratch: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
