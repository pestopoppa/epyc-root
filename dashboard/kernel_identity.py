"""Offline read-only freeze/ELF identity checks; never part of hub health.

Expected identities come from the ratified manifest. No kernel is executed or changed.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import re
import stat
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from dashboard import panels
REPO = Path(__file__).resolve().parents[1]
_REPO_ROOT = REPO
PRODUCTION_KERNEL_ATTESTATION = Path(os.environ.get(
    "PRODUCTION_KERNEL_ATTESTATION",
    str(REPO / "artifacts/operator/ratify_v10_final_freeze_20260922.json")))


PRODUCTION_KERNEL_REPO = Path(os.environ.get(
    "PRODUCTION_KERNEL_REPO",
    "/mnt/raid0/llm/llama.cpp"))


SPEECH_KERNEL_ATTESTATION = Path(os.environ.get(
    "SPEECH_KERNEL_ATTESTATION",
    str(REPO / "artifacts/operator/ratify_speech_kernel_freeze_20260731.json")))


PRODUCTION_LLAMA_BINARIES = {
    "cpu": Path(os.environ.get("PRODUCTION_LLAMA_CPU_BINARY",
                               "/mnt/raid0/llm/kernels/production/cpu/llama-server")),
    "hip": Path(os.environ.get("PRODUCTION_LLAMA_HIP_BINARY",
                               "/mnt/raid0/llm/kernels/production/gpu/llama-server")),
}


_MAX_HASHED_BINARY_BYTES = 512 * 1024 * 1024


PRODUCTION_STABLE_LINK_ROOT = Path(os.environ.get(
    "PRODUCTION_STABLE_LINK_ROOT", "/mnt/raid0/llm/kernels/production"))


PRODUCTION_STABLE_LINKS = {
    "cpu": (None, "llama-server"),
    "gpu": (None, "llama-server"),
    "stt": ("/mnt/raid0/llm/whisper.cpp/build/bin", "whisper-server"),
    "tts": ("/mnt/raid0/llm/qwentts.cpp/build", "tts-server"),
}


_GGML_FAMILY = ("libggml", "libwhisper", "libllama", "libmtmd")


def _read_json_object(path: Path, what: str) -> tuple:
    """``(artifact_present, data_or_None, reader_error_or_None)`` for one artifact.

    ONE reader for all four file-backed panels, so the absent/corrupt distinction
    cannot be right in one of them and wrong in the other three.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, None, None
    except OSError as exc:
        return path.exists(), None, f"{what} unreadable: {exc}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return True, None, f"{what} unreadable: {exc}"
    if not isinstance(data, dict):
        return True, None, f"{what} malformed (not an object)"
    return True, data, None


def _production_kernel_summary(attestation_path: Path,
                               production_repo: Path) -> dict:
    """Read the operator freeze attestation and compare the canonical checkout."""
    present, data, err = _read_json_object(attestation_path,
                                           "production kernel attestation")
    if data is None:
        if err is None:
            # D-1 residual (KRD-AUDIT-20260812). `_read_json_object` returns err=None
            # for a simply-absent file, and this function used to pass that straight
            # through — so the panel could only say "attestation not found" with no
            # reason. The render was made loud earlier; the REASON was still missing,
            # and the same synthesised-sentence pattern already existed one function
            # away in `_read_kernel_contract`. Asymmetry closed.
            err = (f"production kernel freeze attestation not exported — nothing has "
                   f"written {attestation_path}. The production kernel identity is "
                   f"UNPROVEN; do not read this page as confirming which kernel is live.")
        return {"available": False, "artifact_present": present,
                "evidence": str(attestation_path), "error": err}
    observed_branch = observed_head = checkout_error = None
    try:
        proc = subprocess.run(
            ["git", "-C", str(production_repo), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        head = subprocess.run(
            ["git", "-C", str(production_repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        if proc.returncode == 0:
            observed_branch = proc.stdout.strip() or None
        else:
            checkout_error = (proc.stderr.strip()
                              or f"git symbolic-ref exited {proc.returncode}")
        if head.returncode == 0:
            observed_head = head.stdout.strip() or None
        elif checkout_error is None:
            checkout_error = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        checkout_error = str(exc)
    expected_branch = data.get("production_branch")
    expected_head = data.get("production_head")
    working_tree = _working_tree_state(production_repo)
    return {
        "available": True,
        "decision": data.get("decision"),
        "status": data.get("status"),
        "frozen": data.get("production_frozen"),
        "branch": expected_branch,
        "head": expected_head,
        "version": data.get("production_version"),
        "binary_sha256": data.get("production_binary_sha256") or {},
        "ggml": data.get("ggml"),
        "ratified_at": data.get("ratified_at"),
        "scope": data.get("scope"),
        "evidence": str(attestation_path),
        "checkout": {
            "path": str(production_repo),
            "branch": observed_branch,
            "head": observed_head,
            "matches_attestation": (
                observed_branch == expected_branch and observed_head == expected_head
                if observed_branch and observed_head and expected_branch and expected_head
                else None),
            "error": checkout_error,
            **working_tree,
        },
    }


def _sha256_file(path: Path) -> tuple:
    """``(digest_or_None, error_or_None)``. Absence is not an error here — the caller
    distinguishes *missing binary* from *unreadable binary*, and both must stay loud."""
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"unreadable: {exc}"
    if size > _MAX_HASHED_BINARY_BYTES:
        return None, f"refusing to hash {size} bytes (> {_MAX_HASHED_BINARY_BYTES})"
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        return None, f"unreadable: {exc}"
    return digest.hexdigest(), None


def _binary_identity(label: str, path: Path, expected_sha256: str | None) -> dict:
    """One attested binary, compared live.

    THREE-VALUED ON PURPOSE, because two of the states are the ones that hurt:
    ``matches`` True (identity proven), False (DRIFT — something rebuilt or replaced a
    frozen binary), or None (*unknown* — the file is missing, unreadable, or the
    attestation carries no digest to compare against). A missing binary must never
    read as a passing one, which a boolean would force it to.
    """
    observed, error = _sha256_file(path)
    present = observed is not None
    if expected_sha256 and observed:
        matches = observed == expected_sha256
    else:
        matches = None
    if error is None and not present:
        error = "binary absent — the freeze attests a file that is not on disk"
    elif matches is False:
        error = ("BINARY DRIFT — on-disk digest does not match the operator "
                 "attestation; a frozen binary was rebuilt or replaced")
    elif expected_sha256 is None and present:
        error = "attestation carries no digest for this binary — identity unverifiable"
    return {"label": label, "path": str(path), "present": present,
            "expected_sha256": expected_sha256, "observed_sha256": observed,
            "matches": matches, "error": error}


def _working_tree_state(repo: Path) -> dict:
    """Three-valued working-tree cleanliness, including untracked paths."""
    try:
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain=v1",
             "--untracked-files=all"], capture_output=True, text=True,
            timeout=5.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"clean": None, "dirty_count": None, "dirty_paths": [],
                "status_error": str(exc)}
    if status.returncode != 0:
        return {"clean": None, "dirty_count": None, "dirty_paths": [],
                "status_error": (status.stderr.strip()
                                 or f"git status exited {status.returncode}")}
    rows = [row for row in status.stdout.splitlines() if row]
    return {"clean": not rows, "dirty_count": len(rows),
            "dirty_paths": rows[:20], "status_error": None}


def _checkout_identity(repo: Path, expected_branch: str | None,
                       expected_head: str | None) -> dict:
    """Live branch/head of a kernel tree vs what the attestation froze."""
    observed_branch = observed_head = error = None
    try:
        branch = subprocess.run(
            ["git", "-C", str(repo), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5.0, check=False)
        if branch.returncode == 0:
            observed_branch = branch.stdout.strip() or None
        else:
            error = branch.stderr.strip() or f"git symbolic-ref exited {branch.returncode}"
        if head.returncode == 0:
            observed_head = head.stdout.strip() or None
        elif error is None:
            error = head.stderr.strip() or f"git rev-parse exited {head.returncode}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = str(exc)
    if observed_branch is None and observed_head is None and error is None:
        error = "kernel tree unreadable — no branch or head could be resolved"
    matches = None
    if observed_branch is not None and observed_head is not None:
        matches = (observed_branch == expected_branch and observed_head == expected_head)
    return {"path": str(repo), "branch": observed_branch, "head": observed_head,
            "expected_branch": expected_branch, "expected_head": expected_head,
            "matches_attestation": matches, "error": error,
            **_working_tree_state(repo)}


def _ggml_generation_identity(repo: Path, expected: str | None) -> dict:
    """Compare attested ggml generation with the checked-out tree metadata."""
    cmake = repo / "ggml" / "CMakeLists.txt"
    try:
        source = cmake.read_text(encoding="utf-8")
    except OSError as exc:
        return {"expected": expected, "observed": None, "matches": None,
                "evidence": str(cmake), "error": f"ggml generation unverifiable: {exc}"}
    fields = {}
    for name in ("MAJOR", "MINOR", "PATCH"):
        match = re.search(rf"set\(GGML_VERSION_{name}\s+([0-9]+)\)", source)
        if match:
            fields[name] = match.group(1)
    observed = ".".join(fields.get(name, "") for name in ("MAJOR", "MINOR", "PATCH"))
    if not observed or ".." in observed:
        return {"expected": expected, "observed": None, "matches": None,
                "evidence": str(cmake),
                "error": "ggml generation unverifiable — version fields incomplete"}
    if not expected:
        return {"expected": None, "observed": observed, "matches": None,
                "evidence": str(cmake),
                "error": "ggml generation observed but not attested"}
    matches = observed == expected
    return {"expected": expected, "observed": observed, "matches": matches,
            "evidence": str(cmake),
            "error": None if matches else "GGML GENERATION DRIFT — tree differs from attestation"}


def _speech_kernel_summary(attestation_path: Path | None = None) -> dict:
    """whisper.cpp and qwentts.cpp — the two thirds of the freeze nobody was showing.

    WHY THIS EXISTS (KRD-AUDIT-20260812). The freeze covers a production KERNEL SET —
    llama.cpp `production-consolidated-v9` plus whisper.cpp and qwentts.cpp at
    `production-speech-v1` — and the dashboard projected only llama. Measured on the
    live surface before this change: the strings `whisper`, `qwentts`, `speech` and
    `ggml` appeared ZERO times anywhere in `autokernel_current_state()`. Two of three
    frozen kernels could drift, be rebuilt, or vanish and no panel would say so.

    THE STALE-SOURCE TRAP, and it is why llama is NOT read from here. This attestation
    also carries a `kernels.llama_cpp` block — pinned at **v8** (`67a433bf`, binary
    10107) and labelled in its own text *"unchanged by this ratification; recorded for
    completeness"*. It was accurate on 2026-07-31 and was superseded by the v9 freeze
    on 08-11. Folding the set from this one file would therefore project a **stale
    llama identity that still looks internally consistent** — the failure this audit
    was commissioned to find, not to reproduce. llama comes from the v9 attestation;
    this function deliberately ignores its own llama block.

    ggml GENERATION IS PROJECTED because it is load-bearing, not decorative: the three
    trees run three different ggml generations (0.18.0 / 0.17.0 / v9's own), and
    `CLAUDE.md` records that a binary inheriting another tree's ggml *runs silently
    wrong*. A number that must match and is shown nowhere is exactly the class of fact
    this dashboard exists to surface.
    """
    attestation_path = attestation_path or SPEECH_KERNEL_ATTESTATION
    present, data, err = _read_json_object(attestation_path, "speech kernel attestation")
    if data is None:
        if err is None:
            err = (f"speech kernel freeze attestation not exported — nothing has "
                   f"written {attestation_path}. Two of the three frozen kernels "
                   f"(whisper.cpp, qwentts.cpp) are therefore UNVERIFIED here.")
        return {"available": False, "artifact_present": present,
                "evidence": str(attestation_path), "error": err, "kernels": []}
    kernels = []
    for key, title in (("whisper_cpp", "whisper.cpp (STT)"),
                       ("qwentts_cpp", "qwentts.cpp (TTS)")):
        spec = data.get("kernels", {}).get(key)
        if not isinstance(spec, dict):
            kernels.append({"key": key, "title": title, "available": False,
                            "error": f"attestation carries no `{key}` block"})
            continue
        binary = spec.get("binary")
        kernels.append({
            "key": key, "title": title, "available": True,
            "tree": spec.get("tree"), "branch": spec.get("branch"),
            "head": spec.get("commit"), "ggml": spec.get("ggml"),
            "load_bearing_patch": spec.get("load_bearing_patch"),
            "checkout": _checkout_identity(Path(spec.get("tree") or "/nonexistent"),
                                           spec.get("branch"), spec.get("commit")),
            "binary": _binary_identity(title, Path(binary), spec.get("binary_sha256"))
            if binary else {"label": title, "present": False, "matches": None,
                            "error": "attestation names no binary for this kernel"},
        })
    return {"available": True, "ratification": data.get("ratification"),
            "ratified_at": data.get("date_utc"), "scope": data.get("scope"),
            "evidence": str(attestation_path), "error": None, "kernels": kernels}


def _elf_dynamic(path: Path) -> tuple:
    """``(needed, runpath_entries, error)`` from the ELF dynamic section.

    READ-ONLY AND NON-EXECUTING, deliberately. The research contract
    (`verify_ggml_linkage.sh`) uses `ldd`, which invokes the dynamic loader; the
    follow-up brief forbids executing the production binary, so this parses
    `readelf -d` instead. Strictly weaker than `ldd` — it cannot see dlopened
    backends — and that limit is reported rather than hidden.
    """
    try:
        proc = subprocess.run(["readelf", "-d", str(path)],
                              capture_output=True, text=True, timeout=10.0, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], [], f"readelf unavailable: {exc}"
    if proc.returncode != 0:
        return [], [], (proc.stderr.strip() or f"readelf exited {proc.returncode}")
    needed, runpath = [], []
    for line in proc.stdout.splitlines():
        if "(NEEDED)" in line and "[" in line:
            needed.append(line.split("[", 1)[1].rstrip("]").strip())
        elif ("(RUNPATH)" in line or "(RPATH)" in line) and "[" in line:
            raw = line.split("[", 1)[1].rstrip("]").strip()
            runpath.extend([e for e in raw.split(":") if e])
    return needed, runpath, None


def _ambient_foreign_ggml_dirs() -> dict:
    """Entries on the SERVER PROCESS's ``LD_LIBRARY_PATH`` that carry a libggml.

    WHY THIS IS THE FIRST THING CHECKED. `LD_LIBRARY_PATH` is consulted BEFORE a
    binary's own `DT_RUNPATH`, so a single ggml-bearing directory on it overrides
    every tree-local guarantee the binaries carry. That is not hypothetical:
    INC-20260731-ggml-linkage-silent-cpu-fallback is exactly this — a HIP-built
    whisper-cli loaded the production CPU-only ggml, found no GPU, and ran full-CPU
    while printing `use gpu = 1`. The run completes, the output is well-formed, and
    only the throughput is quietly wrong.

    SCOPE, STATED because it is easy to overclaim: this observes the environment of
    the DASHBOARD PROCESS, not of any launcher. A clean reading here does not prove a
    launcher is clean, and a dirty reading does not prove a specific measurement was
    contaminated — it proves the host handed THIS process a contaminated path, which
    is evidence about the environment sessions inherit. The durable config
    (`/etc/environment`, devcontainer) is the authority on whether the incident fix is
    still applied; a stale shell can carry removed entries until it is restarted.
    """
    raw = os.environ.get("LD_LIBRARY_PATH", "")
    entries, carriers = [e for e in raw.split(":") if e], []
    for entry in entries:
        try:
            if any(f.name.startswith("libggml") for f in Path(entry).iterdir()):
                carriers.append(entry)
        except OSError:
            continue
    return {"ld_library_path": entries, "ggml_bearing_entries": carriers,
            "clean": not carriers,
            "note": ("observed for the DASHBOARD PROCESS only — this is evidence about "
                     "the environment sessions inherit, not proof about any launcher")}


def _linkage_evidence(binary: Path, tree_root: Path) -> dict:
    """Does this binary's ggml family resolve inside its OWN tree?"""
    needed, runpath, error = _elf_dynamic(binary)
    if error:
        return {"binary": str(binary), "tree_root": str(tree_root), "error": error,
                "verified": None, "runpath": [], "ggml_libs": []}
    origin = binary.parent
    resolved_runpath = [str(origin) if e == "$ORIGIN" else e.replace("$ORIGIN", str(origin))
                        for e in runpath]
    # One transitive hop: llama-server NEEDs only its impl .so, and the ggml family
    # arrives through that. Stopping at the direct NEEDED set would report "no ggml
    # libraries" for the two llama binaries — an absence that is an artifact of where
    # we stopped looking, not a property of the binary.
    frontier = list(needed)
    for name in list(needed):
        if name.startswith("libllama-server-impl"):
            child = origin / name
            if child.exists():
                more, _, child_err = _elf_dynamic(child)
                if not child_err:
                    frontier.extend(more)
    libs, foreign, unresolved = [], [], []
    for name in sorted(set(frontier)):
        if not name.startswith(_GGML_FAMILY):
            continue
        where = None
        for candidate_dir in resolved_runpath or [str(origin)]:
            if (Path(candidate_dir) / name).exists():
                where = str(Path(candidate_dir) / name)
                break
        inside = bool(where) and Path(where).resolve().is_relative_to(tree_root.resolve())
        if where is None:
            unresolved.append(name)
        elif not inside:
            foreign.append({"lib": name, "resolved": where})
        libs.append({"lib": name, "resolved": where, "inside_tree": inside if where else None})
    verified = (not foreign and not unresolved and bool(libs))
    return {
        "binary": str(binary), "tree_root": str(tree_root),
        "runpath": resolved_runpath, "ggml_libs": libs,
        "foreign": foreign, "unresolved": unresolved,
        "verified": verified if libs else None,
        "error": (None if libs else
                  "no ggml-family library found in the ELF dynamic section — linkage "
                  "unverifiable from a static read (backends may be dlopened)"),
        "method": "readelf -d (non-executing); weaker than ldd — cannot see dlopened backends",
    }


def _stable_link_projection() -> list:
    """The four stable production links, and what they actually resolve to."""
    out = []
    for name, (expected_dir, binary_name) in production_link_targets().items():
        link = PRODUCTION_STABLE_LINK_ROOT / name
        entry = {"name": name, "link": str(link), "expected_target": expected_dir,
                 "binary_name": binary_name}
        try:
            is_link = link.is_symlink()
            target = str(link.resolve()) if link.exists() else None
        except OSError as exc:
            entry.update({"present": False, "is_symlink": False, "target": None,
                          "matches_expected": None, "binary_present": None,
                          "error": f"unreadable: {exc}"})
            out.append(entry)
            continue
        matches = (target == expected_dir) if target else None
        binary_present = bool(target) and (Path(target) / binary_name).is_file()
        error = None
        if target is None:
            error = ("stable link absent or dangling — launchers that follow the "
                     "runbook would resolve nothing")
        elif not matches:
            error = f"stable link repointed: resolves to {target}, expected {expected_dir}"
        elif not binary_present:
            error = f"stable link resolves, but {binary_name} is not inside its target"
        entry.update({"present": target is not None, "is_symlink": is_link,
                      "target": target, "matches_expected": matches,
                      "binary_present": binary_present, "error": error})
        out.append(entry)
    return out


def production_kernel_set(attestation_path: Path | None = None,
                          production_repo: Path | None = None,
                          speech_attestation_path: Path | None = None) -> dict:
    """The COMPLETE frozen kernel set, folded to one honest verdict.

    Three kernels, four binaries. `production_kernel` (llama only) is left untouched
    beside this for existing consumers; this is the set-level view, and it is one
    panel rather than a second llama panel — the audit brief explicitly warned against
    duplicating what already renders.

    THE FOLD IS DELIBERATELY PESSIMISTIC. `intact` is True only when every kernel and
    every binary is proven — any drift, absence, unreadable tree or missing digest
    makes it False, and `unverified` records how many facts could not be established
    at all. A set-level green that can be produced by a kernel we failed to read is
    the same absence-tolerance that let incident 8 render a dead loop as a clean page.
    """
    llama = _production_kernel_summary(attestation_path or PRODUCTION_KERNEL_ATTESTATION,
                                       production_repo or PRODUCTION_KERNEL_REPO)
    speech = _speech_kernel_summary(speech_attestation_path)

    binaries = []
    llama_digests = llama.get("binary_sha256") or {}
    for slot, path in PRODUCTION_LLAMA_BINARIES.items():
        binaries.append(_binary_identity(f"llama.cpp {slot.upper()}", path,
                                         llama_digests.get(slot)))
    for kernel in speech.get("kernels", []):
        if kernel.get("binary"):
            binaries.append(kernel["binary"])

    members, alarms = [], []
    llama_ck = llama.get("checkout") or {}
    llama_generation = _ggml_generation_identity(
        production_repo or PRODUCTION_KERNEL_REPO, llama.get("ggml"))
    members.append({"key": "llama_cpp", "title": "llama.cpp",
                    "available": llama.get("available"),
                    "branch": llama.get("branch"), "head": llama.get("head"),
                    "version": llama.get("version"), "ggml": llama.get("ggml"),
                    "ggml_generation": llama_generation,
                    "matches_attestation": llama_ck.get("matches_attestation"),
                    "working_tree_clean": llama_ck.get("clean"),
                    "dirty_count": llama_ck.get("dirty_count"),
                    "dirty_paths": llama_ck.get("dirty_paths") or [],
                    "error": llama.get("error") or llama_ck.get("error")})
    for kernel in speech.get("kernels", []):
        tree = Path(kernel.get("tree") or "/nonexistent")
        members.append({
            "key": kernel.get("key"), "title": kernel.get("title"),
            "available": kernel.get("available"),
            "branch": kernel.get("branch"), "head": kernel.get("head"),
            "version": None, "ggml": kernel.get("ggml"),
            "ggml_generation": _ggml_generation_identity(tree, kernel.get("ggml")),
            "matches_attestation": (kernel.get("checkout") or {}).get("matches_attestation"),
            "working_tree_clean": (kernel.get("checkout") or {}).get("clean"),
            "dirty_count": (kernel.get("checkout") or {}).get("dirty_count"),
            "dirty_paths": (kernel.get("checkout") or {}).get("dirty_paths") or [],
            "error": kernel.get("error") or (kernel.get("checkout") or {}).get("error")})

    if not llama.get("available"):
        alarms.append("llama.cpp freeze attestation unavailable — production identity unproven")
    if not speech.get("available"):
        alarms.append("speech kernel freeze attestation unavailable — whisper.cpp and "
                      "qwentts.cpp identities unproven")
    for member in members:
        if member.get("matches_attestation") is False:
            alarms.append(f"{member['title']}: tree does NOT match attestation (drift)")
        elif member.get("available") and member.get("matches_attestation") is None:
            alarms.append(f"{member['title']}: tree identity could not be established")
        if member.get("working_tree_clean") is False:
            alarms.append(
                f"{member['title']}: frozen working tree is DIRTY "
                f"({member.get('dirty_count')} paths; no mutation performed by dashboard)")
        elif member.get("available") and member.get("working_tree_clean") is None:
            alarms.append(f"{member['title']}: working-tree cleanliness unverified")
        generation = member.get("ggml_generation") or {}
        if generation.get("matches") is False:
            alarms.append(f"{member['title']}: GGML GENERATION DRIFT")
        elif generation.get("matches") is None:
            alarms.append(f"{member['title']}: ggml generation unverified")
    for binary in binaries:
        if binary.get("matches") is False:
            alarms.append(f"{binary['label']}: BINARY DRIFT vs operator attestation")
        elif not binary.get("present"):
            alarms.append(f"{binary['label']}: attested binary absent from disk")

    # --- stable links + tree-local linkage (KRD-AUDIT-20260812 follow-up) ---
    stable_links = _stable_link_projection()
    for link in stable_links:
        if link.get("error"):
            alarms.append(f"stable link `{link['name']}`: {link['error']}")

    ambient = _ambient_foreign_ggml_dirs()
    if not ambient["clean"]:
        alarms.append(
            "LD_LIBRARY_PATH carries ggml-bearing directories "
            f"({', '.join(ambient['ggml_bearing_entries'])}) — it is consulted BEFORE "
            "each binary's RUNPATH, so a speech kernel launched from this environment "
            "can silently load llama's ggml and run wrong while reporting success "
            "(INC-20260731). Observed for the dashboard process; check the launcher.")

    linkage = []
    for name, (expected_dir, binary_name) in production_link_targets().items():
        tree_root = Path(expected_dir)
        # The tree that owns the libraries: for llama both build dirs live under the
        # one clone, so the ROOT is the tree, not the build dir.
        for anchor in ("/mnt/raid0/llm/llama.cpp", "/mnt/raid0/llm/whisper.cpp",
                       "/mnt/raid0/llm/qwentts.cpp"):
            if expected_dir.startswith(anchor):
                tree_root = Path(anchor)
                break
        evidence = _linkage_evidence(Path(expected_dir) / binary_name, tree_root)
        evidence["link"] = name
        linkage.append(evidence)
        if evidence.get("foreign"):
            alarms.append(f"{name}: ggml resolves OUTSIDE its own tree — "
                          + ", ".join(f"{f['lib']} -> {f['resolved']}" for f in evidence["foreign"]))
        elif evidence.get("verified") is None:
            alarms.append(f"{name}: tree-local linkage UNVERIFIABLE "
                          f"({evidence.get('error') or 'no evidence'})")

    links_ok = sum(1 for l in stable_links
                   if l.get("matches_expected") and l.get("binary_present"))
    linkage_ok = sum(1 for e in linkage if e.get("verified") is True)

    proven = sum(1 for b in binaries if b.get("matches") is True)
    unverified = sum(1 for b in binaries if b.get("matches") is None)
    trees_proven = sum(1 for m in members if m.get("matches_attestation") is True)
    generations_proven = sum(
        1 for member in members
        if (member.get("ggml_generation") or {}).get("matches") is True)
    return {
        "schema": "epyc.production_kernel_set.v1",
        "expected_kernels": 3,
        "expected_binaries": len(PRODUCTION_LLAMA_BINARIES) + 2,
        "kernels_present": len(members),
        "trees_matching": trees_proven,
        "binaries_proven": proven,
        "binaries_unverified": unverified,
        "stable_links": stable_links,
        "stable_links_ok": links_ok,
        "linkage": linkage,
        "linkage_verified": linkage_ok,
        "ggml_generations_proven": generations_proven,
        "ambient_library_path": ambient,
        # PESSIMISTIC, and now over five independent facts rather than two: the
        # attestations, the trees, the binary digests, the stable links launchers
        # actually follow, and proof each binary's ggml comes from its own tree. A set
        # that is byte-identical but reachable only through a repointed link, or whose
        # libraries resolve into another tree, is not intact in any sense a measurement
        # can rely on.
        "intact": (llama.get("available") is True and speech.get("available") is True
                   and trees_proven == len(members) == 3
                   and all(m.get("working_tree_clean") is True for m in members)
                   and proven == len(binaries) == 4
                   and links_ok == len(stable_links) == 4
                   and linkage_ok == len(linkage) == 4
                   and generations_proven == len(members) == 3
                   and ambient["clean"]),
        "alarms": alarms,
        "members": members,
        "binaries": binaries,
        "llama": llama,
        "speech": speech,
        "evidence": [str(attestation_path or PRODUCTION_KERNEL_ATTESTATION),
                     str(speech_attestation_path or SPEECH_KERNEL_ATTESTATION)],
    }


def production_link_targets() -> dict:
    """Resolve store targets declared by the ratification, with no import-time I/O."""
    links = dict(PRODUCTION_STABLE_LINKS)
    _, manifest, _ = _read_json_object(PRODUCTION_KERNEL_ATTESTATION, "freeze manifest")
    for slot, name in (("cpu", "cpu"), ("gpu", "hip")):
        if links.get(slot, (None,))[0] is not None:
            continue
        declared = (manifest or {}).get("binary_location", {}).get(slot, "")
        target = declared.split(" -> ", 1)[-1].split(" (", 1)[0] if " -> " in declared else ""
        # The manifest records targets relative to kernels/.
        expected = str(PRODUCTION_STABLE_LINK_ROOT.parent / target) if target else "/unverified-store-target"
        links[slot] = (expected, "llama-server")
    return links
