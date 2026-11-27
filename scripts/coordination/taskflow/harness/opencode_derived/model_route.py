"""Bind explicit Taskflow aliases to approved native model and template evidence."""
import hashlib
import json
from pathlib import Path
import re
import stat

from .case_snapshot import digest
from .transport import DEFAULT_MODEL, Model


_SHA256 = re.compile(r"[0-9a-f]{64}")
_SHARD = re.compile(r"(.*)-(\d{5})-of-(\d{5})\.gguf")


def approved_json(path, sha256, description):
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != sha256:
        raise ValueError(f"approved {description} bytes changed")
    return json.loads(content)


def job_model(job):
    if "model" not in job:
        return DEFAULT_MODEL
    config = job["model"]
    return Model(config["id"], config["name"])


def _files(entries, role):
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"model manifest must name every {role} file")
    files = []
    seen_inodes = set()
    for entry in entries:
        path = Path(entry["path"])
        if not path.is_absolute() or path != path.resolve() or path.suffix != ".gguf":
            raise ValueError(f"model manifest requires an exact canonical GGUF path: {path}")
        info = path.stat()
        identity = (info.st_dev, info.st_ino)
        observed = (info.st_size, *identity, info.st_mtime_ns, info.st_ctime_ns)
        expected = tuple(entry[key] for key in ("bytes", "device", "inode", "mtime_ns", "ctime_ns"))
        if (any(type(value) is not int for value in expected)
                or observed != expected or not stat.S_ISREG(info.st_mode)
                or info.st_size <= 0 or not _SHA256.fullmatch(entry["sha256"])):
            raise ValueError(f"{role} file differs from its content-verified identity: {path}")
        if identity in seen_inodes:
            raise ValueError(f"duplicate {role} file in model manifest: {path}")
        seen_inodes.add(identity)
        files.append(path)
    shard = _SHARD.fullmatch(files[0].name)
    if shard is None:
        if len(files) != 1:
            raise ValueError(f"{role} file manifest does not name a single model or GGUF split")
    else:
        prefix, first, total = shard.groups()
        if first != "00001" or len(files) != int(total) or any(
            path != files[0].with_name(f"{prefix}-{index:05d}-of-{total}.gguf")
            for index, path in enumerate(files, 1)
        ):
            raise ValueError(f"model manifest must contain the complete ordered {role} GGUF split")
    return tuple(files)


def _value(argv, *names):
    matches = [index for index, arg in enumerate(argv) if arg in names]
    if not matches:
        return None
    if len(matches) != 1 or matches[0] + 1 == len(argv) or not argv[matches[0] + 1]:
        raise ValueError(f"native argument must appear once with a value: {names[0]!r}")
    return argv[matches[0] + 1]


def verify_model(job, model, proof, argv, model_path):
    """Verify content-custodied files again by identity without rereading model weights."""
    if "model" not in job:
        if _SHARD.fullmatch(model_path.name):
            raise ValueError("split GGUF requires an explicit complete model manifest")
        return None
    config = job["model"]
    manifest_sha = config["manifest_sha256"]
    manifest = approved_json(config["manifest"], manifest_sha, "model manifest")
    template_sha = manifest["template_sha256"]
    if not _SHA256.fullmatch(template_sha):
        raise ValueError("invalid model template digest")
    expected = {
        "model_id": model.id, "model_manifest_sha256": manifest_sha, "template_sha256": template_sha,
    }
    if manifest["model_id"] != model.id or any(proof.get(key) != value for key, value in expected.items()):
        raise ValueError("model, template or manifest differs from the approved native serving receipt")
    if _value(argv, b"--alias") != model.id.encode():
        raise ValueError("live native model alias differs from the approved model ID")
    target = _files(manifest["target_files"], "target")
    live_target = _value(argv, b"-m", b"--model")
    if Path(live_target.decode()).resolve() != target[0] or target[0] != model_path:
        raise ValueError("live target model is not the first manifest file")
    draft = _files(manifest["draft_files"], "draft") if "draft_files" in manifest else ()
    draft_arg = _value(argv, b"-md", b"--model-draft", b"--draft-model")
    if (Path(draft_arg.decode()).resolve() if draft_arg else None) != (draft[0] if draft else None):
        raise ValueError("live draft model differs from the approved manifest")
    if set(draft) & set(target):
        raise ValueError("target files cannot also be counted as draft files")
    if _value(argv, b"--chat-template") is not None:
        raise ValueError("inline template override cannot be bound to the approved template file")
    template_arg = _value(argv, b"--chat-template-file")
    template_path = manifest.get("template_path")
    if bool(template_arg) != bool(template_path) or (
        template_path and (Path(template_arg.decode()).resolve() != Path(template_path)
                           or digest(Path(template_path)) != template_sha)
    ):
        raise ValueError("live template override differs from the approved template")
    return target


def verify_thinking(job, model, proof):
    """Require a qualifying ON/OFF and preservation observation for CPU thinking."""
    if job["backend"] != "cpu" or not job.get("thinking"):
        return False
    spec = job.get("thinking_qualification")
    if model.id == DEFAULT_MODEL.id or "model" not in job or not spec:
        raise ValueError("CPU thinking requires an explicit qualified model and template")
    qualified = approved_json(spec["path"], spec["sha256"], "thinking qualification")
    same = {
        "backend": "cpu",
        "pid": proof["pid"],
        "model_id": model.id,
        "model_manifest_sha256": proof["model_manifest_sha256"],
        "template_sha256": proof["template_sha256"],
    }
    if any(qualified.get(key) != value for key, value in same.items()) or not all(
        qualified.get(key) is True for key in ("enable_thinking_on", "enable_thinking_off", "preserve_thinking")
    ):
        raise ValueError("CPU thinking qualification does not bind this live model and template")
    return True
