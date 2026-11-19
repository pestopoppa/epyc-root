"""Read source-pinned, offline input receipts without rehashing model weights."""
import json
from pathlib import Path


def file_identity(path):
    stat = Path(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def model_pin(path, expected_sha, receipt_path):
    receipt = json.loads(Path(receipt_path).read_text())
    identity = file_identity(path)
    if (receipt.get("schema") != "hil15-prepared-model/v1"
            or receipt.get("path") != str(Path(path).resolve())
            or receipt.get("sha256") != expected_sha
            or receipt.get("identity") != list(identity)):
        raise ValueError("model differs from offline content-verified input receipt")
    return identity


def runtime_pin(receipt_path):
    record = json.loads(Path(receipt_path).read_text())
    if record.get("schema") != "hil15-python-runtime/v1" or not record.get("metadata"):
        raise ValueError("invalid prepared runtime receipt")
    return record
