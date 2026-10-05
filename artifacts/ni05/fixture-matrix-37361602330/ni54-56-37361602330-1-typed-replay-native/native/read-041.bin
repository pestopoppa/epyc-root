"""Resolve production kernel binaries by BACKEND, never by build path.

A backend is a capability ("run this on the GPU"), not a location. Naming a build
directory in a registry or a launcher couples the orchestration apparatus to how a
kernel happened to be built, which is why moving a role to the GPU by registry edit
alone would previously have launched it on the CPU-only build — silently, because a
missing ggml backend does not raise, it simply is not used.

The stable layer lives at ``/mnt/raid0/llm/kernels/production/<backend>/`` and is a
symlink per backend. Freezing a new kernel repoints the symlink and archives the old
one; nothing here or in either registry changes. See that directory's README.md.

The three trees run three different ggml generations, so every launcher must set
``LD_LIBRARY_PATH`` to the backend directory this module returns — inheriting another
tree's ggml runs silently wrong rather than failing.
"""

from __future__ import annotations

import os
from pathlib import Path

KERNEL_ROOT = Path("/mnt/raid0/llm/kernels")
PRODUCTION_ROOT = KERNEL_ROOT / "production"

# backend -> the server binary that backend provides
BACKEND_BINARIES: dict[str, str] = {
    "cpu": "llama-server",
    "gpu": "llama-server",
    "stt": "whisper-server",
    "tts": "tts-server",
}

VALID_BACKENDS = frozenset(BACKEND_BINARIES)

# Backends whose binaries need a vendor runtime on LD_LIBRARY_PATH in addition to
# their own ggml. Data, not a branch: a future cuda/vulkan backend joins the map.
# stt and tts are HIP builds too (both trees ship libggml-hip.so), so both need
# the ROCm runtime alongside their own ggml.
BACKEND_VENDOR_LIB_DIRS: dict[str, tuple[Path, ...]] = {
    "gpu": (Path(os.environ.get("ROCM_PATH", "/opt/rocm")) / "lib",),
    "stt": (Path(os.environ.get("ROCM_PATH", "/opt/rocm")) / "lib",),
    "tts": (Path(os.environ.get("ROCM_PATH", "/opt/rocm")) / "lib",),
}

# The ONE backend that needs no prepend, and the reason why: the ambient
# environment already resolves to the CPU tree, so adding a path there would
# change every CPU role's environment for no benefit.
#
# Everything else must lead with its OWN directory. This used to be derived from
# "has vendor dirs?", which silently returned [] for stt and tts — the two
# backends whose ggml generation differs MOST from the ambient one (0.18.0 and
# 0.17.0 vs the CPU tree's 0.16.0). Deriving "needs no prepend" from "needs no
# vendor runtime" conflated two unrelated properties and produced exactly the
# silent-wrong-ggml launch this module exists to prevent.
_BACKENDS_NEEDING_NO_PREPEND = frozenset({"cpu"})


class KernelPathError(RuntimeError):
    """Raised when a backend cannot be resolved.

    Deliberately fatal. Returning a fallback path here would reintroduce exactly the
    defect this module exists to prevent: a GPU request quietly satisfied by a CPU
    build. An unresolvable backend is a third outcome, not a success.
    """


def backend_dir(backend: str) -> Path:
    """Return the directory for ``backend``, or raise.

    Also the value a launcher must put on ``LD_LIBRARY_PATH``.
    """
    if backend not in VALID_BACKENDS:
        raise KernelPathError(
            f"unknown kernel backend {backend!r}; valid: {sorted(VALID_BACKENDS)}"
        )
    path = PRODUCTION_ROOT / backend
    if not path.is_dir():
        raise KernelPathError(
            f"kernel backend {backend!r} does not resolve: {path} is missing or dangling. "
            f"Repoint it with: ln -sfn <build dir> {path}"
        )
    return path.resolve()


def backend_ld_library_path(backend: str) -> list[str]:
    """Return the ``LD_LIBRARY_PATH`` entries a launcher must PREPEND for ``backend``.

    Setting this is not optional for an accelerated backend, and the failure mode is
    silent. ``build-hip/bin/llama-server`` has ``RUNPATH=$ORIGIN:/opt/rocm/lib``, but
    ``LD_LIBRARY_PATH`` outranks ``RUNPATH`` in the loader's search order — so an
    ambient ``LD_LIBRARY_PATH`` containing the CPU tree (which this host's shell
    profile sets) makes the HIP binary load the CPU-only ``libggml.so`` from
    ``build/bin``. No ROCm device is then registered and ``--device ROCm0`` is
    rejected outright with ``invalid device: ROCm0`` (observed 2026-08-01 on
    worker_vision:8086). A role that does NOT name a device fails quieter still: it
    launches, serves, and runs entirely on the CPU.

    Returns ``[]`` for backends that need no prepend (``cpu``): the CPU tree is what
    the ambient environment already resolves to, and adding a path there would change
    every CPU role's environment for no benefit.

    Every OTHER backend leads with its own directory, whether or not it also needs a
    vendor runtime. ``stt`` and ``tts`` returned ``[]`` until 2026-08-02 because the
    emptiness test was "no vendor dirs" rather than "is the ambient tree" — see
    ``_BACKENDS_NEEDING_NO_PREPEND``.
    """
    if backend not in VALID_BACKENDS:
        raise KernelPathError(
            f"unknown kernel backend {backend!r}; valid: {sorted(VALID_BACKENDS)}"
        )
    if backend in _BACKENDS_NEEDING_NO_PREPEND:
        return []
    vendor_dirs = BACKEND_VENDOR_LIB_DIRS.get(backend, ())
    return [str(backend_dir(backend)), *(str(path) for path in vendor_dirs)]


def server_binary(backend: str) -> Path:
    """Return the executable server binary for ``backend``, or raise."""
    directory = backend_dir(backend)
    binary = directory / BACKEND_BINARIES[backend]
    if not binary.is_file():
        raise KernelPathError(
            f"kernel backend {backend!r} resolves to {directory}, but "
            f"{BACKEND_BINARIES[backend]!r} is not present there"
        )
    return binary


def describe() -> dict[str, dict[str, str]]:
    """Report every backend and where it currently points.

    Provenance, not decoration: a binary launched from the wrong backend is otherwise
    indistinguishable from one launched from the right one.
    """
    out: dict[str, dict[str, str]] = {}
    for backend in sorted(VALID_BACKENDS):
        entry: dict[str, str] = {"binary_name": BACKEND_BINARIES[backend]}
        try:
            resolved = backend_dir(backend)
            entry["resolves_to"] = str(resolved)
            entry["binary_present"] = str((resolved / BACKEND_BINARIES[backend]).is_file())
        except KernelPathError as exc:
            entry["error"] = str(exc)
        out[backend] = entry
    return out
