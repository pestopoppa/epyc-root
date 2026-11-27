"""Select, seal and independently verify repeat evidence. Offline filesystem operations only."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
from tempfile import TemporaryDirectory

SCHEMA = "taskflow.model-repeat-archive.v1"
MAX_SHARD = 16 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
GROUPS = {"runtime", "native", "cases", "baseline", "source", "protocol", "performance", "review"}
SAFE_FILE = re.compile(r"[a-z]+-[0-9]{3}\.tar\.gz\Z")
DENIED_DIRS = {".git", "__pycache__", ".cache", ".venv", "node_modules", "py312-deps", "site-packages",
               "slot-cache", "lane", "grade-lane", "work", "session", "s", "rootfs",
               "venv", "vendor", "dependencies", "stock", ".taskflow-refs"}
DENIED_FILES = {"auth.json", "credentials.json", "id_rsa", "id_ed25519"}
TYPES = {".json", ".jsonl", ".log", ".txt", ".md", ".py", ".jinja", ".patch", ".sha256", ".csv", ".tsv",
         ".out", ".stderr", ".stdout", ".yaml", ".yml", ".toml", ".sh", ".cpp", ".js", ".mjs"}
PROC_FILES = {"maps", "numa_maps", "status", "stat"}
SCOPE = (
    "Archived members preserve exact supplied source bytes. Selected frozen case baseline maps include read-only inputs. "
    "Native and review evidence includes wire bodies, request ledgers, exported terminal sessions and recorded usage. "
    "Container filesystems, unfiltered work directories, session databases, weights, and dependency trees are excluded. "
    "Native readiness receipts, later metadata rechecks, checker outcomes, and owner acceptance retain distinct provenance. "
    "Slot lock files preserve path custody alongside owner receipts; file bytes do not encode held flock state."
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def safe_relative(name):
    path = PurePosixPath(name)
    if not path.parts or path.is_absolute() or ".." in path.parts or path.as_posix() != name or "\n" in name:
        raise ValueError(f"invalid relative evidence path {name!r}")
    return path


def regular(path):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError(f"evidence must be a regular file: {path}")
    if st.st_size > MAX_FILE:
        raise ValueError(f"individual evidence file exceeds the archival limit: {path}")
    return st


def consider(path):
    return (path.name not in DENIED_FILES and not path.name.startswith(".env")
            and (path.suffix in TYPES or path.name in PROC_FILES or path.name in {"KEEP", "STOP", "SHA256SUMS"}
                 or path.name.endswith((".json.gz", ".jsonl.gz", ".log.gz", ".patch.gz", ".txt.gz"))))


class Selection:
    def __init__(self):
        self.files = {}

    def add(self, source, group, original, expected=None, *, size=None, executable=None):
        safe_relative(original)
        if group not in GROUPS:
            raise ValueError(f"unknown evidence group: {group}")
        if (source.suffix.lower() in {".gguf", ".safetensors", ".so", ".sqlite"}
                or source.suffix.lower() == ".bin" and group != "baseline"):
            raise ValueError(f"binary model/runtime internals outside evidence scope: {source}")
        if source.name in DENIED_FILES or source.name.startswith(".env"):
            raise ValueError(f"credential or environment file outside evidence scope: {source}")
        # Permit established repository symlinks in ancestors, never in the actual selected object.
        st = regular(source)
        key = f"{group}/{original}"
        value = {"source": str(source.resolve(strict=True)), "group": group, "original": original,
                 "sha256": file_sha(source), "bytes": st.st_size, "executable": bool(st.st_mode & 0o111)}
        if expected is not None and value["sha256"] != expected:
            raise ValueError(f"evidence differs from source lock: {source}")
        if size is not None and value["bytes"] != size or executable is not None and value["executable"] is not executable:
            raise ValueError(f"baseline size or mode differs from source lock: {source}")
        if key in self.files and self.files[key] != value:
            raise ValueError(f"two files claim the same evidence name: {key}")
        self.files[key] = value

    def walk(self, root, group, prefix, *, extra_denied=()):
        if not root.is_dir():
            raise ValueError(f"missing evidence directory: {root}")
        denied = DENIED_DIRS.union(extra_denied)
        for current, dirs, files in os.walk(root, followlinks=False):
            here = Path(current)
            dirs[:] = sorted(name for name in dirs if name not in denied and not (here / name).is_symlink())
            for name in sorted(files):
                path = here / name
                slot_lock = here.name == "slot-locks" and re.fullmatch(r"(cpu|gpu)-[0-3]\.lock", name)
                if (consider(path) or slot_lock) and not path.is_symlink():
                    self.add(path, group, f"{prefix}/{path.relative_to(root).as_posix()}")


def select_cases(selection, matrix):
    aliases = {}
    baselines = {}
    for key, case_ref in sorted(matrix["cases"].items()):
        spec = case_ref["case_spec"]
        source = Path(spec["path"])
        packet = source.parent
        selection.add(source, "cases", f"{key}/case.json", spec["sha256"])
        prompt = case_ref["initial_prompt"]
        selection.add(Path(prompt["path"]), "cases", f"{key}/prompt.md", prompt["sha256"])
        case = read(source)
        for field in ("independent_acceptance", "preservation_check"):
            checker = case_ref.get(field)
            if checker is None:
                continue
            refs = [checker["entry"], *checker["support"], *checker["qualification_receipts"]]
            for index, ref in enumerate(refs, 1):
                artifact = Path(ref["path"])
                selection.add(artifact, "cases", f"{key}/{field}/{index:02d}-{artifact.name}", ref["sha256"])
        selection.walk(packet, "cases", key, extra_denied={"baseline"})
        selection.add(packet / "oracle.py", "cases", f"{key}/oracle.py", case["oracle_sha256"])
        tree = case["baseline_files"]
        fingerprint = digest(json_bytes(tree))
        already_archived = fingerprint in baselines
        if not already_archived:
            baselines[fingerprint] = f"tree-{len(baselines) + 1:02d}"
        baseline = packet.resolve(strict=True) / "baseline"
        for name, meta in sorted(tree.items()):
            path = baseline / safe_relative(name)
            if path.resolve(strict=True) != path:
                raise ValueError(f"baseline path has a symlink: {path}")
            if already_archived:
                evidence_data(dict(meta, source=str(path)))
            else:
                selection.add(path, "baseline", f"{baselines[fingerprint]}/{name}", meta["sha256"],
                              size=meta["bytes"], executable=meta["executable"])
        aliases[key] = {"baseline": baselines[fingerprint], "file_map_sha256": fingerprint, "files": len(tree),
                        "original_baseline": str(packet / "baseline"), "case_sha256": spec["sha256"]}
    return aliases


def cpu_custody(root):
    route = root / "runtime/epoch-02/ROUTE-cpu.json"
    if not route.is_file():
        return None
    value = read(route)
    dispatch_ref = value["serving_receipt"]
    dispatch = Path(dispatch_ref["path"])
    native_ref = value["native_qualification"]
    native_pass = Path(native_ref["path"])
    initial = dispatch.parent / "LIVE.json"
    original = read(initial)
    adapted = read(dispatch)
    if file_sha(dispatch) != dispatch_ref["sha256"] or file_sha(native_pass) != native_ref["sha256"]:
        raise ValueError("CPU serving or qualification artifact disagrees with route lock")
    if any(adapted.get(key) != val for key, val in original.items()):
        raise ValueError("CPU dispatch metadata replaced a native qualification value")
    ready_path = root / "runtime/epoch-02/READY-cpu.json"
    ready = read(ready_path)
    identity = ready["identity"]
    if (adapted["port"], adapted["pid"], adapted["pid_start_ticks"]) != (
            ready["port"], identity["pid"], identity["start_ticks"]):
        raise ValueError("CPU metadata recheck disagrees with the owner PID, birth, or listener")
    return {
        "kind": "main-owned read-only live metadata recheck for dispatch",
        "scope": "Qualification executed against original native LIVE and PASS. Main's later SERVING projection adapted metadata only.",
        "paths": {label: {"path": str(path), "sha256": file_sha(path)} for label, path in (
            ("original_live", initial), ("native_qualification_pass", native_pass),
            ("later_dispatch_serving_recheck", dispatch), ("owner_ready", ready_path), ("dispatch_route", route))},
        "additional_fields": sorted(set(adapted).difference(original)),
        "recorded_adaptation": adapted.get("adaptation"),
        "executed_qualifier_source_claim": False,
    }


def planned(root, repo, args):
    selection = Selection()
    runtime = root / "runtime"
    usage_snapshots = {path.name for pattern in ("manager-usage-*", "perf-checkpoint-*", "perf-final*", "quality-checkpoint-*", "quality-final*", "report-data-checkpoint-*", "report-data-final*") for path in runtime.glob(pattern) if path.is_dir()}
    selection.walk(runtime, "runtime", "runtime",
                   extra_denied={"perf-control-current", "perf-control-epoch01", *usage_snapshots})
    for prep in sorted(p for p in root.iterdir() if p.name.startswith(("gpu-prep", "cpu-prep")) and p.is_dir()):
        selection.walk(prep, "native", prep.name)
    setup = root / "task-prep"
    selection.walk(setup, "protocol", "task-prep")
    selection.add(root / "KEEP.md", "protocol", "KEEP.md")
    protocol = repo / "docs/design/27b-q38fn-full-tools-repeat-20261127.md"
    selection.add(protocol, "protocol", protocol.relative_to(repo).as_posix())
    for path, expected in sorted(read(setup / "DRIVER-SOURCE-LOCK.json")["files"].items()):
        source = Path(path)
        selection.add(source, "source", f"driver/{source.relative_to(repo).as_posix()}", expected)
    review_lock = root / "runtime/REVIEW-CODE-LOCK.json"
    if review_lock.is_file():
        for index, (path, expected) in enumerate(sorted(read(review_lock)["files"].items()), 1):
            source = Path(path)
            selection.add(source, "source", f"review/{index:02d}-{source.name}", expected)
    prior_export = Path("/mnt/raid0/llm/tmp/ws58-a3b-revalidate-20261126/performance/collect_perf.py")
    selection.add(prior_export, "source", "performance/collect_perf.py",
                  "33ebc3be0ce33906a71182bdf93c9c4fb8b9c08ce720312360792ccf52dfa92c")
    baseline_aliases = select_cases(selection, read(setup / "MATRIX.json"))
    cpu = read(root / "cpu-prep/CONFIG-cpu.json")
    gpu = read(root / "gpu-prep-v2/CONFIG-gpu.json")
    for name, store in (("cpu", next(Path(x) for x in cpu["argv"] if x.endswith("/llama-server")).parent.parent),
                        ("gpu", Path(gpu["build_identity"]).parent)):
        for file in ("BUILD-IDENTITY.json", "BUILD-OK.json", "SHA256SUMS"):
            selection.add(store / file, "source", f"kernel/{name}/{file}")
    selection.add(Path(gpu["recipe_path"]), "source", "serving/gpu-recipe.json", gpu["recipe_sha256"])
    cpu_recipe = next(rec for rec in cpu["source_identity"] if rec["path"].endswith("_recipe.py"))
    selection.add(Path(cpu_recipe["path"]), "source", "serving/cpu-recipe.py", cpu_recipe["sha256"])
    for suffix in ("performance", "review"):
        for spec in getattr(args, suffix):
            folder = Path(spec).resolve(strict=True)
            selection.walk(folder, suffix, folder.name)
    if getattr(args, "manager_usage", None):
        folder = args.manager_usage.resolve(strict=True)
        summary = folder / "SUMMARY.json"
        events = folder / "EVENTS.jsonl"
        record = read(summary)
        if (record.get("schema") != "taskflow.repeat-manager-token-usage.v1"
                or len(events.read_bytes().splitlines()) != record.get("responses")):
            raise ValueError("sanitized manager-usage snapshot has an inconsistent ledger")
        selection.add(summary, "performance", "manager-usage/SUMMARY.json")
        selection.add(events, "performance", "manager-usage/EVENTS.jsonl")
    for path in args.bound_file:
        source = Path(path).resolve(strict=True)
        if not consider(source):
            raise ValueError(f"unsupported explicit evidence file: {source}")
        selection.add(source, "source", f"additional/{source.parent.name}/{source.name}")
    return {"schema": SCHEMA, "files": [selection.files[k] for k in sorted(selection.files)],
            "baseline_aliases": baseline_aliases, "custody": {"cpu_dispatch_adapter": cpu_custody(root)},
            "scope": SCOPE}


def chunk_rows(rows):
    shard = []
    size = 0
    group = None
    for row in rows:
        if shard and (row["group"] != group or size + row["bytes"] > MAX_SHARD):
            yield group, shard
            shard, size = [], 0
        group = row["group"]
        shard.append(row)
        size += row["bytes"]
    if shard:
        yield group, shard


def evidence_data(row):
    source = Path(row["source"])
    st = regular(source)
    if st.st_size != row["bytes"] or bool(st.st_mode & 0o111) is not row["executable"]:
        raise ValueError(f"file changed after selection: {source}")
    data = source.read_bytes()
    if digest(data) != row["sha256"]:
        raise ValueError(f"digest changed after selection: {source}")
    return data


def decoded_gzip_sha(path):
    with gzip.open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_archive(stage, spec, selection_sha256):
    if spec["schema"] != SCHEMA or not spec["files"]:
        raise ValueError("unknown or empty evidence selection")
    names = {(row["group"], row["original"]) for row in spec["files"]}
    if len(names) != len(spec["files"]):
        raise ValueError("duplicate original member name in selection")
    members, shards, indexes = [], [], {}
    ordered = sorted(spec["files"], key=lambda row: (row["group"], row["original"]))
    for group, rows in chunk_rows(ordered):
        if group not in GROUPS:
            raise ValueError(f"unknown evidence group: {group}")
        indexes[group] = indexes.get(group, 0) + 1
        shard = f"{group}-{indexes[group]:03d}.tar.gz"
        if not SAFE_FILE.fullmatch(shard):
            raise ValueError(f"archive exceeds supported shard count: {shard}")
        target = stage / shard
        with target.open("xb") as out, gzip.GzipFile(filename="", mode="wb", fileobj=out, mtime=0) as zipped:
            with tarfile.open(mode="w|", fileobj=zipped, format=tarfile.USTAR_FORMAT) as bundle:
                for index, row in enumerate(rows, 1):
                    safe_relative(row["original"])
                    data = evidence_data(row)
                    member = tarfile.TarInfo(f"member-{index:06d}")
                    member.size = len(data)
                    member.mode = 0o755 if row["executable"] else 0o644
                    bundle.addfile(member, io.BytesIO(data))
                    enclosed = row["original"].endswith(".gz")
                    members.append({**row, "archive": shard, "member": member.name,
                                    "inner_encoding": "gzip" if enclosed else "raw",
                                    "decoded_sha256": digest(gzip.decompress(data)) if enclosed else row["sha256"]})
        shards.append({"archive": shard, "stored_sha256": file_sha(target), "stored_bytes": target.stat().st_size,
                       "decoded_tar_sha256": decoded_gzip_sha(target)})
    layout = {key: value for key, value in spec.items() if key != "files"}
    layout.update({"selection_sha256": selection_sha256, "shards": shards, "members": members})
    (stage / "ARCHIVE-LAYOUT.json.gz").write_bytes(gzip.compress(json_bytes(layout), mtime=0))
    (stage / "README.md").write_text("# Repeat evidence archive\n\n" + layout["scope"] + "\n\n"
                                    "The compressed layout maps numbered archive members to original paths and raw file digests. "
                                    "Original gzip wire bodies remain byte-for-byte inside the outer archives.\n\n"
                                    "Use `gzip -dc ARCHIVE-LAYOUT.json.gz` to find an original path, then "
                                    "`tar -xOzf SHARD MEMBER` to write the selected source bytes to standard output.\n\n"
                                    "Run `python3 package.py verify --archive .` to check the stored and decoded hashes.\n")
    (stage / "package.py").write_bytes(Path(__file__).read_bytes())
    for row in ordered:
        evidence_data(row)


def verify(root, *, checksum=True):
    layout_path = root / "ARCHIVE-LAYOUT.json.gz"
    layout = json.loads(gzip.decompress(layout_path.read_bytes()))
    if layout["schema"] != SCHEMA:
        raise ValueError("unknown archive layout")
    grouped = {}
    originals = set()
    for row in layout["members"]:
        safe_relative(row["original"])
        key = (row["group"], row["original"])
        if key in originals:
            raise ValueError(f"duplicate original in layout: {key}")
        originals.add(key)
        group = row["group"]
        if group not in GROUPS or not row["archive"].startswith(f"{group}-"):
            raise ValueError(f"evidence group disagrees with archive shard: {key}")
        member = row["member"]
        if not re.fullmatch(r"member-[0-9]{6}", member):
            raise ValueError(f"invalid member name: {member}")
        bucket = grouped.setdefault(row["archive"], {})
        if member in bucket:
            raise ValueError(f"duplicate archive member name: {row['archive']}/{member}")
        bucket[member] = row
    archives = {entry["archive"] for entry in layout["shards"]}
    if archives != set(grouped) or len(layout["shards"]) != len(archives):
        raise ValueError("shard membership disagreement")
    count = 0
    for shard in layout["shards"]:
        name = shard["archive"]
        if not SAFE_FILE.fullmatch(name):
            raise ValueError(f"invalid shard name: {name}")
        path = root / name
        if path.is_symlink() or path.stat().st_size != shard["stored_bytes"] or file_sha(path) != shard["stored_sha256"]:
            raise ValueError(f"stored archive hash or size mismatch: {name}")
        if decoded_gzip_sha(path) != shard["decoded_tar_sha256"]:
            raise ValueError(f"decoded tar hash mismatch: {name}")
        remaining = dict(grouped[name])
        with tarfile.open(path, "r|gz") as bundle:
            for member in bundle:
                if member.name not in remaining or not member.isfile():
                    raise ValueError(f"unexpected archive member: {name}/{member.name}")
                row = remaining.pop(member.name)
                if member.size != row["bytes"] or member.mode != (0o755 if row["executable"] else 0o644):
                    raise ValueError(f"member size or mode mismatch: {name}/{member.name}")
                with bundle.extractfile(member) as source:
                    data = source.read()
                if digest(data) != row["sha256"]:
                    raise ValueError(f"source byte hash mismatch: {name}/{member.name}")
                inner = gzip.decompress(data) if row["inner_encoding"] == "gzip" else data
                if digest(inner) != row["decoded_sha256"]:
                    raise ValueError(f"inner payload hash mismatch: {name}/{member.name}")
                count += 1
        if remaining:
            raise ValueError(f"archive members missing: {name}")
    if checksum:
        included = archives | {"ARCHIVE-LAYOUT.json.gz", "ARCHIVE-VALIDATION.json", "README.md", "package.py"}
        checksums = root / "ARTIFACTS.sha256"
        if ({p.name for p in root.iterdir()} != included | {checksums.name}
                or any(p.is_symlink() or not p.is_file() for p in root.iterdir())):
            raise ValueError("archive contains extra or missing stored files")
        expected = "".join(f"{file_sha(root / name)}  {name}\n" for name in sorted(included))
        if checksums.read_text() != expected:
            raise ValueError("whole archive checksum manifest mismatch")
    return {"schema": SCHEMA, "decoded_source_files_verified": count, "shards_verified": len(archives),
            "stored_shards_bytes": sum(x["stored_bytes"] for x in layout["shards"]),
            "layout_sha256": file_sha(layout_path), "selection_sha256": layout["selection_sha256"],
            "native_calls": 0}


def pack(selection_path, expected, dest):
    data = selection_path.read_bytes()
    if digest(data) != expected:
        raise ValueError("evidence selection digest differs from approval")
    if dest.exists():
        raise FileExistsError(f"evidence destination already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".archive-", dir=dest.parent) as staging:
        stage = Path(staging) / "publication"
        stage.mkdir()
        write_archive(stage, json.loads(data), expected)
        receipt = verify(stage, checksum=False)
        (stage / "ARCHIVE-VALIDATION.json").write_bytes(json_bytes(receipt))
        stored = sorted(stage.iterdir(), key=lambda x: x.name)
        (stage / "ARTIFACTS.sha256").write_text("".join(f"{file_sha(p)}  {p.name}\n" for p in stored))
        verify(stage)
        if dest.exists():
            raise FileExistsError(f"evidence destination already exists: {dest}")
        stage.rename(dest)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--root", type=Path, required=True)
    plan.add_argument("--repo", type=Path, required=True)
    plan.add_argument("--out", type=Path, required=True)
    plan.add_argument("--manager-usage", type=Path, help="One sanitized manager-usage snapshot for the final cutoff")
    for field in ("performance", "review", "bound-file"):
        plan.add_argument("--" + field, action="append", default=[])
    build = commands.add_parser("pack")
    build.add_argument("--selection", type=Path, required=True)
    build.add_argument("--selection-sha256", required=True)
    build.add_argument("--out", type=Path, required=True)
    confirm = commands.add_parser("verify")
    confirm.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        spec = planned(args.root.resolve(strict=True), args.repo.resolve(strict=True), args)
        with args.out.open("xb") as stream:
            stream.write(json_bytes(spec))
        result = {"selection": str(args.out), "sha256": file_sha(args.out), "files": len(spec["files"])}
    elif args.command == "pack":
        result = pack(args.selection, args.selection_sha256, args.out)
    else:
        result = verify(args.archive)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
