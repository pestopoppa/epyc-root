#!/usr/bin/env python3
"""Private original custody for the bounded PII sub-gate; never a privacy attestation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import uuid

SCHEMA = "epyc.pii.staged_gate.v1"
LIMIT = 1048576
HOOK_DIR = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def load(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate native object member")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def regular(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("capture requires regular original bytes")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
            raise ValueError("capture requires regular original bytes")
        data = source.read()
        after = os.fstat(source.fileno())
    if identity(before) != identity(after) or identity(before) != identity(path.lstat()):
        raise ValueError("original changed while being captured")
    return data


def identity(metadata):
    return {"device": metadata.st_dev, "inode": metadata.st_ino, "size": metadata.st_size,
            "mtime_ns": metadata.st_mtime_ns, "ctime_ns": metadata.st_ctime_ns}


def write(directory, name, data):
    path = directory / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    return {"name": name, "sha256": sha(data)}


def git(repo, *args, index=None, check=True):
    environment = dict(os.environ)
    if index is not None:
        environment["GIT_INDEX_FILE"] = str(index)
        environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(["git", "-C", str(repo), *args], env=environment,
                          check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def head(repo):
    result = git(repo, "rev-parse", "--verify", "HEAD", check=False)
    if result.returncode == 0:
        return result.stdout.decode().strip()
    symbolic = git(repo, "symbolic-ref", "--quiet", "HEAD", check=False)
    if symbolic.returncode == 0:
        reference = symbolic.stdout.decode().strip()
        absent = git(repo, "show-ref", "--verify", "--quiet", reference, check=False)
        if absent.returncode == 1:
            return None
    raise ValueError("original HEAD could not be resolved as a commit or unborn branch")


def trusted_git(repo, *args, input=None, index=None):
    # Current trusted Git only; never execute a captured script or repo config.
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                       GIT_OPTIONAL_LOCKS="0")
    if index is not None:
        environment["GIT_INDEX_FILE"] = str(index)
    try:
        return subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                               "-c", "core.hooksPath=/dev/null", "-c", "diff.renames=false",
                               "-C", str(repo), *args], env=environment, input=input,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.SubprocessError:
        raise ValueError("original Git snapshot unavailable to trusted reader") from None


def comparison_objects(repo, comparison, directory):
    tree = git(repo, "rev-parse", comparison + "^{tree}").stdout.decode().strip()
    descendants = git(repo, "ls-tree", "-r", "-d", "-z", tree).stdout
    trees = {tree}
    for row in descendants.split(b"\0"):
        if row:
            fields, _ = row.split(b"\t", 1)
            trees.add(fields.decode().split()[2])
    result = []
    for number, oid in enumerate(sorted(trees)):
        raw = git(repo, "cat-file", "tree", oid).stdout
        result.append({"oid": oid, "kind": "tree",
                       "artifact": write(directory, f"comparison-tree-{number}.bin", raw)})
    return tree, result


def verify_original_selection(directory, request):
    if not request["supported_index"]:
        return
    with tempfile.TemporaryDirectory(prefix="pii-native-index-reader-") as temporary:
        repo = Path(temporary)
        trusted_git(repo, "init", "--quiet", "--object-format=" + request["object_format"])
        index = directory / request["index"]["name"]
        entries = trusted_git(repo, "ls-files", "--stage", "-z", index=index).stdout
        if entries != regular(directory / request["stage_entries"]["name"]):
            raise ValueError("frozen original index/stage entries refused")
        for item in request["comparison_objects"]:
            raw = regular(directory / item["artifact"]["name"])
            oid = trusted_git(repo, "hash-object", "-w", "-t", item["kind"], "--stdin", input=raw).stdout.decode().strip()
            if oid != item["oid"] or item["kind"] != "tree":
                raise ValueError("original comparison object binding refused")
        if request["head"] is None:
            if request["comparison"] != request["comparison_tree"]:
                raise ValueError("unborn original comparison refused")
        else:
            raw = regular(directory / request["comparison_commit"]["name"])
            oid = trusted_git(repo, "hash-object", "-w", "-t", "commit", "--stdin", input=raw).stdout.decode().strip()
            if (oid != request["head"] or request["comparison"] != request["head"]
                    or raw.splitlines()[0] != b"tree " + request["comparison_tree"].encode()):
                raise ValueError("original HEAD/tree comparison binding refused")
        # Name-only, no rename detection, attributes/textconv/external execution.
        selected = trusted_git(repo, "diff", "--cached", "--no-ext-diff", "--no-textconv",
                               "--no-renames", request["comparison_tree"], "--name-only",
                               "-z", "--diff-filter=ACM", index=index).stdout
        reproducible = selected == regular(directory / request["selection"]["name"])
        if reproducible is not request["selection_reproducible"]:
            raise ValueError("original frozen Git diff membership refused")


def private_directory(path):
    path.mkdir(mode=0o700)
    # mkdir inherits setgid from real shared Git common directories despite
    # its requested access mode. New recorder custody must be exactly 0700.
    path.chmod(0o700, follow_symlinks=False)


def private_parent(common):
    parent = common
    for name in ("epyc-private", "pii-gates"):
        parent = parent / name
        try:
            private_directory(parent)
        except FileExistsError:
            metadata = parent.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise ValueError("private capture parent is not owner-only")
            permission = stat.S_IMODE(metadata.st_mode)
            if permission == 0o2700:
                # Recorder ancestors only: migrate the sole inherited setgid
                # bit. Never normalize any existing original capsule or file.
                parent.chmod(0o700, follow_symlinks=False)
            elif permission != 0o700:
                raise ValueError("private capture parent is not owner-only")
    return parent


def begin(repo):
    repo = repo.resolve()
    started = utc()
    comparison_head = head(repo)
    common = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.decode().strip())
    original_index = Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "index").stdout.decode().strip())
    split = bool(git(repo, "rev-parse", "--shared-index-path").stdout.strip())
    original = regular(original_index)
    directory = private_parent(common) / uuid.uuid4().hex
    private_directory(directory)
    index_pin = write(directory, "original-index", original)
    raw_entries = git(repo, "ls-files", "--stage", "-z").stdout
    entries_pin = write(directory, "original-stage-entries", raw_entries)
    entries = {}
    unmerged = False
    for row in raw_entries.split(b"\0"):
        if not row:
            continue
        metadata, path = row.split(b"\t", 1)
        mode, oid, stage = metadata.decode().split()
        unmerged |= stage != "0"
        if stage == "0":
            entries[path.decode("utf-8", "surrogateescape")] = {"mode": mode, "oid": oid}
    supported = not split and not unmerged
    # An unborn comparison is an explicit empty Git tree, never a later HEAD.
    comparison = comparison_head
    if comparison is None:
        environment = dict(os.environ)
        result = subprocess.run(["git", "-C", str(repo), "hash-object", "-w", "-t", "tree", "--stdin"],
                                env=environment, input=b"", check=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        comparison = result.stdout.decode().strip()
    comparison_tree, comparison_pins = comparison_objects(repo, comparison, directory)
    comparison_commit = (write(directory, "original-head-commit.bin", git(repo, "cat-file", "commit", comparison_head).stdout)
                         if comparison_head is not None else None)
    inputs = []
    changed = b""
    reproducible = False
    if supported:
        frozen = directory / "original-index"
        if git(repo, "ls-files", "--stage", "-z", index=frozen).stdout != raw_entries:
            raise ValueError("original index changed before snapshot binding")
        changed = git(repo, "diff", "--cached", comparison, "--name-only", "-z", "--diff-filter=ACM", index=frozen).stdout
        independent = trusted_git(repo, "diff", "--cached", "--no-ext-diff", "--no-textconv",
                                  "--no-renames", comparison, "--name-only", "-z",
                                  "--diff-filter=ACM", index=frozen).stdout
        reproducible = changed == independent
        names = [p.decode("utf-8", "surrogateescape") for p in changed.split(b"\0") if p]
        oids = sorted({entries[name]["oid"] for name in names})
        checks = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check"],
                                input=("\n".join(oids) + "\n").encode() if oids else b"",
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        headers = {}
        for row in checks.stdout.decode().splitlines():
            oid, kind, size = row.split()
            headers[oid] = (kind, int(size))
        process = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        cached = {}
        try:
            for number, name in enumerate(names):
                item = {"path": name, **entries[name], "artifact": None}
                kind, size = headers[item["oid"]]
                item.update(object_kind=kind, size=size)
                if kind == "blob" and size <= LIMIT:
                    if item["oid"] not in cached:
                        process.stdin.write(item["oid"].encode() + b"\n")
                        process.stdin.flush()
                        response = process.stdout.readline().decode().split()
                        if response != [item["oid"], "blob", str(size)]:
                            raise ValueError("original indexed object header changed")
                        data = process.stdout.read(size)
                        if len(data) != size or process.stdout.read(1) != b"\n":
                            raise ValueError("original indexed object incomplete")
                        cached[item["oid"]] = write(directory, f"input-{number:06d}.bin", data)
                    item["artifact"] = cached[item["oid"]]
                inputs.append(item)
        finally:
            process.stdin.close()
            process.stdout.close()
            process.wait()
    policy = []
    for number, source in enumerate((HOOK_DIR / "pii_precommit.sh", Path(__file__),
                                    HOOK_DIR / "fixture_snapshot_provenance.py",
                                    HOOK_DIR.parent / "ci/native_conformance.py")):
        original_identity = identity(source.lstat())
        raw = regular(source)
        if identity(source.lstat()) != original_identity:
            raise ValueError("policy identity changed during original capture")
        policy.append({"source": str(source), "identity": original_identity,
                       "artifact": write(directory, f"policy-{number}.bin", raw)})
    request = {"schema": SCHEMA, "started_utc": started, "repo": str(repo),
               "head": comparison_head, "comparison": comparison,
               "comparison_tree": comparison_tree, "comparison_objects": comparison_pins,
               "comparison_commit": comparison_commit,
               "object_format": git(repo, "rev-parse", "--show-object-format").stdout.decode().strip(),
               "original_index": str(original_index), "original_index_sha256": sha(original),
               "index": index_pin, "stage_entries_sha256": sha(raw_entries),
               "stage_entries": entries_pin,
               "selection": write(directory, "original-selection", changed),
               "supported_index": supported, "split_index": split, "unmerged": unmerged,
               "selection_reproducible": reproducible,
               "inputs": inputs, "policy": policy,
               "scope": "PII sub-gate ACM selection only; no wrapper/commit outcome or secret-free entire-index claim",
               "transformations": "existing Bash command substitution and echo; scanner text conversion unchanged",
               "excluded_custody": "oversized/unreadable/non-blob inputs are not claimed as scanned original bytes",
               "metric": "pii_staged_policy_check_passed", "metric_direction": "higher_better",
               "category": "CANDIDATE"}
    write(directory, "execution-request.json", canonical(request) + b"\n")
    for name in ("events.nul", "stdout.log", "stderr.log"):
        write(directory, name, b"")
    return directory, comparison, supported


def event(directory, path, status, detail):
    with (directory / "events.nul").open("ab") as output:
        output.write(b"\0".join(os.fsencode(v) for v in (path, status, detail)) + b"\0")


def events_from(data):
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise ValueError("incomplete native event framing")
    fields = data[:-1].split(b"\0")
    if len(fields) % 3:
        raise ValueError("incomplete native event membership")
    return [{"path": os.fsdecode(fields[i]), "status": os.fsdecode(fields[i+1]),
             "detail": os.fsdecode(fields[i+2])} for i in range(0, len(fields), 3)]


def proposition(record):
    result = "true" if record["pii_staged_policy_check_passed"] else "false"
    return ("The captured PII sub-gate criterion evaluated " + result
            + " for original index digest " + record["original_index_sha256"]
            + " under recorded policy digest " + record["policy_digest"]
            + "; original PII exit was " + str(record["exit_code"])
            + ". This is bounded ACM/text-policy behavior, not an entire-index privacy attestation.")


def provenance_module():
    spec = importlib.util.spec_from_file_location("pii_provenance", HOOK_DIR / "fixture_snapshot_provenance.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive_proof(directory, request, events):
    module = provenance_module()
    repo = Path(request["repo"])
    # All provenance membership reads use the same frozen worktree index.
    previous = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(directory / "original-index")
    result = []
    try:
        eligible = set(module.exemptions(repo, request["comparison"]))
        if any(e["path"] not in eligible for e in events if e["status"] == "native-exemption"):
            raise ValueError("native exemption does not match original frozen source binding")
        blobs = module.IndexBlobs(repo, module.index_entries(repo))
        try:
            containers = sorted({str(module.native_container(e["path"])) for e in events
                                 if e["status"] == "native-exemption"})
            for number, value in enumerate(containers):
                container = module.PurePosixPath(value)
                record = module.verified_phase(container, blobs, module.reader())
                target = directory / f"native-proof-{number}"
                private_directory(target)
                pins = [record["request"], record["log"], *[r["artifact"] for r in record["readset"]],
                        *([record["junit"]] if record["junit"] else []),
                        *[r["artifact"] for r in record.get("generated_outputs", [])]]
                write(target, "receipt.json", blobs.read(str(container / "receipt.json")))
                for pin in pins:
                    write(target, pin["name"], blobs.read(str(container / pin["name"])))
                result.append({"container": value, "directory": target.name,
                               "receipt_sha256": sha(regular(target / "receipt.json"))})
        finally:
            blobs.close()
    finally:
        if previous is None:
            os.environ.pop("GIT_INDEX_FILE", None)
        else:
            os.environ["GIT_INDEX_FILE"] = previous
    return result


def verify_proofs(directory, record):
    """Reopen original native custody using current trusted readers only."""
    module = provenance_module()
    outcomes = [e for e in record["events"] if e["status"] == "native-exemption"]
    containers = {str(module.native_container(e["path"])) for e in outcomes}
    proofs = record["proofs"]
    if len(proofs) != len({p["container"] for p in proofs}) or {p["container"] for p in proofs} != containers:
        raise ValueError("original native proof membership refused")
    verified = {}
    for number, proof in enumerate(proofs):
        if proof["directory"] != f"native-proof-{number}" or module.native_container(proof["container"] + "/read-0.bin") is None:
            raise ValueError("original native proof namespace refused")
        original, digest = module.reader()(directory / proof["directory"] / "receipt.json")
        if digest != proof["receipt_sha256"]:
            raise ValueError("original native proof digest refused")
        verified[proof["container"]] = original
    inputs = {i["path"]: i for i in record["inputs"]}
    for outcome in outcomes:
        item = inputs[outcome["path"]]
        if not item["artifact"] or item["mode"] not in module.REGULAR_MODES:
            raise ValueError("exempted original source bytes unavailable")
        digest = item["artifact"]["sha256"]
        sources = [source for source, expected in module.FIXTURES.items() if digest == expected]
        if len(sources) != 1:
            raise ValueError("original native source identity refused")
        source = sources[0]
        original = verified[str(module.native_container(outcome["path"]))]
        repository, revisions = module.SOURCE_BINDINGS[source]
        cwd = module.PurePosixPath(original["cwd"])
        if not cwd.is_absolute() or ".." in cwd.parts or original["repositories"].get(repository) not in revisions:
            raise ValueError("original native repository binding refused")
        pin = {"name": module.PurePosixPath(outcome["path"]).name, "sha256": digest}
        bound = [r for r in original["readset"] if r.get("role") == "declared_read"
                 and r.get("name") == str(cwd / source) and r.get("artifact") == pin]
        if len(bound) != 1:
            raise ValueError("original native readset source binding refused")


def decide(request, events, exit_code, checks):
    diagnostic = []
    if type(exit_code) is not int:
        diagnostic.append("original exit is not an integer")
    required_checks = {"logs_complete", "proofs_valid", "live_index_unchanged",
                       "head_unchanged", "frozen_index_unchanged", "policy_unchanged"}
    if not required_checks <= checks.keys() or not all(type(value) is bool and value for value in checks.values()):
        diagnostic.append("capture/index/HEAD/policy/proof integrity diagnostic")
    paths = [e["path"] for e in events]
    if len(paths) != len(set(paths)) or set(paths) != {i["path"] for i in request["inputs"]}:
        diagnostic.append("incomplete or duplicate outcome membership")
    scanned = [e for e in events if e["status"] == "scanned"]
    if not scanned or not request["supported_index"]:
        diagnostic.append("no executed scans or unsupported split/unmerged index")
    if not request["selection_reproducible"]:
        diagnostic.append("original selection differs from deterministic no-renames crosscheck")
    valid = {"scanned", "path-exemption", "native-exemption", "oversized", "empty"}
    if any(e["status"] not in valid or (e["status"] == "scanned" and e["detail"] not in {"0", "1"}) for e in events):
        diagnostic.append("read or scanner error")
    inputs = {i["path"]: i for i in request["inputs"]}
    for outcome in events:
        item = inputs.get(outcome["path"])
        if item is None:
            continue
        if outcome["status"] == "scanned" and not item["artifact"]:
            diagnostic.append("scanned original bytes missing")
        if outcome["status"] == "oversized" and item["size"] <= LIMIT:
            diagnostic.append("oversize outcome inconsistent")
        if item["object_kind"] != "blob":
            diagnostic.append("non-blob original input")
    blocked = sum(e["detail"] == "1" for e in scanned)
    if exit_code not in (0, 1) or (exit_code == 0) != (blocked == 0):
        diagnostic.append("native exit/outcome disagreement")
    counts = {"selected": len(request["inputs"]), "scanned": len(scanned),
              "blocked": blocked, "excluded": len(events) - len(scanned)}
    return (None if diagnostic else exit_code == 0), "; ".join(diagnostic), counts


def finish(directory, exit_code, logs_complete=True):
    request = load(regular(directory / "execution-request.json"))
    events = events_from(regular(directory / "events.nul"))
    checks = {"logs_complete": bool(logs_complete), "proofs_valid": True}
    try:
        checks["live_index_unchanged"] = sha(regular(Path(request["original_index"]))) == request["original_index_sha256"]
        checks["head_unchanged"] = head(Path(request["repo"])) == request["head"]
        checks["frozen_index_unchanged"] = sha(regular(directory / request["index"]["name"])) == request["index"]["sha256"]
        checks["policy_unchanged"] = all(sha(regular(Path(pin["source"]))) == pin["artifact"]["sha256"]
                                         and identity(Path(pin["source"]).lstat()) == pin["identity"]
                                         for pin in request["policy"])
    except (OSError, ValueError, subprocess.SubprocessError):
        checks["completion_observable"] = False
    proofs = []
    try:
        if request["supported_index"]:
            proofs = archive_proof(directory, request, events)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        checks["proofs_valid"] = False
    value, diagnostic, counts = decide(request, events, exit_code, checks)
    terminal = {"ended_utc": utc(), "exit_code": exit_code, "checks": checks,
                "events_sha256": sha(regular(directory / "events.nul")),
                "request_sha256": sha(regular(directory / "execution-request.json"))}
    terminal_pin = write(directory, "original-terminal.json", canonical(terminal) + b"\n")
    artifacts = []
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            artifacts.append({"name": path.relative_to(directory).as_posix(), "sha256": sha(regular(path))})
    record = {**request, **terminal, "terminal": terminal_pin, "events": events,
              "proofs": proofs, "artifacts": artifacts, "diagnostic": diagnostic,
              "checks": checks, "counts": counts,
              "policy_digest": sha(canonical(request["policy"])),
              "pii_staged_policy_check_passed": value}
    record["decided_proposition"] = proposition(record) if not diagnostic else ""
    record["receipt_sha256"] = sha(canonical(record))
    write(directory, "receipt.json", canonical(record) + b"\n")


def read_receipt(path):
    path = Path(path)
    if (path.name != "receipt.json" or path.parent.is_symlink() or stat.S_IMODE(path.parent.stat().st_mode) != 0o700
            or path.parent.stat().st_uid != os.getuid()):
        raise ValueError("native sensitive custody is not private")
    record = load(regular(path))
    metadata = path.lstat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) not in {0o600, 0o400}:
        raise ValueError("native receipt is not owner-only")
    unsigned = dict(record)
    seal = unsigned.pop("receipt_sha256")
    if record.get("schema") != SCHEMA or sha(canonical(unsigned)) != seal:
        raise ValueError("native gate receipt schema/seal refused")
    names = [pin["name"] for pin in record["artifacts"]]
    members = list(path.parent.rglob("*"))
    if any(p.is_symlink() for p in members):
        raise ValueError("private custody contains a symbolic member")
    if any(p.is_dir() and (stat.S_IMODE(p.stat().st_mode) != 0o700 or p.stat().st_uid != os.getuid()) for p in members):
        raise ValueError("private nested custody is not owner-only")
    actual = {p.relative_to(path.parent).as_posix() for p in members if p.is_file()}
    if len(names) != len(set(names)) or set(names) | {"receipt.json"} != actual:
        raise ValueError("private original custody membership refused")
    for pin in record["artifacts"]:
        name = Path(pin["name"])
        if (not pin["name"] or name == Path(".") or name.is_absolute()
                or ".." in name.parts or name.as_posix() != pin["name"]):
            raise ValueError("nonlocal private artifact")
        if sha(regular(path.parent / name)) != pin["sha256"]:
            raise ValueError("original private artifact changed or missing")
        metadata = (path.parent / name).lstat()
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) not in {0o600, 0o400}:
            raise ValueError("native original is not owner-only")
    request = load(regular(path.parent / "execution-request.json"))
    if any(record.get(key) != value for key, value in request.items()):
        raise ValueError("original request binding refused")
    events = events_from(regular(path.parent / "events.nul"))
    if events != record["events"]:
        raise ValueError("native event binding refused")
    required = [record["terminal"], request["index"], request["stage_entries"], request["selection"],
                *[p["artifact"] for p in request["comparison_objects"]],
                *([request["comparison_commit"]] if request["comparison_commit"] else []),
                *[p["artifact"] for p in request["policy"]],
                *[i["artifact"] for i in request["inputs"] if i["artifact"]]]
    for pin in required:
        if pin not in record["artifacts"]:
            raise ValueError("original request artifact membership refused")
    terminal = load(regular(path.parent / record["terminal"]["name"]))
    if (any(record.get(k) != v for k, v in terminal.items())
            or terminal["events_sha256"] != sha(regular(path.parent / "events.nul"))
            or terminal["request_sha256"] != sha(regular(path.parent / "execution-request.json"))):
        raise ValueError("original terminal outcome/check binding refused")
    if (request["index"]["sha256"] != request["original_index_sha256"]
            or request["stage_entries"]["sha256"] != request["stage_entries_sha256"]):
        raise ValueError("original index identity refused")
    selected = [p.decode("utf-8", "surrogateescape") for p in regular(path.parent / request["selection"]["name"]).split(b"\0") if p]
    if len(selected) != len(set(selected)) or selected != [i["path"] for i in request["inputs"]]:
        raise ValueError("original selection membership refused")
    entries = {}
    for row in regular(path.parent / request["stage_entries"]["name"]).split(b"\0"):
        if row:
            fields, name = row.split(b"\t", 1)
            mode, oid, stage = fields.decode("ascii").split()
            if stage == "0":
                entries[name.decode("utf-8", "surrogateescape")] = (mode, oid)
    if any(entries.get(i["path"]) != (i["mode"], i["oid"]) for i in request["inputs"]):
        raise ValueError("original staged object membership refused")
    if request["policy"][1]["artifact"]["sha256"] != sha(regular(Path(__file__))):
        raise ValueError("unsupported native producer version")
    if record["policy_digest"] != sha(canonical(request["policy"])):
        raise ValueError("original policy identity refused")
    if request["object_format"] not in {"sha1", "sha256"}:
        raise ValueError("unsupported Git object identity")
    if (any(type(request[k]) is not bool for k in ("supported_index", "split_index", "unmerged", "selection_reproducible"))
            or request["supported_index"] != (not request["split_index"] and not request["unmerged"])):
        raise ValueError("original index capability metadata refused")
    verify_original_selection(path.parent, request)
    if (request["metric"], request["metric_direction"], request["category"]) != (
            "pii_staged_policy_check_passed", "higher_better", "CANDIDATE"):
        raise ValueError("native criterion metadata refused")
    start = datetime.fromisoformat(request["started_utc"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(record["ended_utc"].replace("Z", "+00:00"))
    if start.utcoffset() != timezone.utc.utcoffset(start) or end.utcoffset() != timezone.utc.utcoffset(end) or end < start:
        raise ValueError("original UTC interval refused")
    for item in request["inputs"]:
        if item["artifact"]:
            body = regular(path.parent / item["artifact"]["name"])
            git_digest = hashlib.new(request["object_format"], b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            if len(body) != item["size"] or git_digest != item["oid"]:
                raise ValueError("original indexed object binding refused")
    if record["checks"].get("proofs_valid") is True:
        verify_proofs(path.parent, record)
    value = record["pii_staged_policy_check_passed"]
    expected_value, diagnostic, counts = decide(request, events, record["exit_code"], record["checks"])
    if value is not expected_value or record["diagnostic"] != diagnostic or record["counts"] != counts:
        raise ValueError("original bounded outcome rederivation refused")
    if value is None:
        if not record["diagnostic"] or record["decided_proposition"]:
            raise ValueError("diagnostic proposition refused")
    elif type(value) is not bool or record["diagnostic"] or record["decided_proposition"] != proposition(record):
        raise ValueError("original bounded proposition refused")
    return record, sha(regular(path))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("begin", "event", "finish"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("values", nargs="*")
    args = parser.parse_args()
    try:
        if args.command == "begin":
            directory, comparison, supported = begin(args.directory)
            sys.stdout.buffer.write(os.fsencode(directory) + b"\0" + comparison.encode() + b"\0"
                                    + (b"1" if supported else b"0") + b"\0")
        elif args.command == "event":
            event(args.directory, *args.values)
        else:
            finish(args.directory, int(args.values[0]), len(args.values) == 1 or args.values[1] == "1")
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        # Never publish filenames, contents or exception snippets from private input.
        print("PII native capture unavailable; no finding may be inferred", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
