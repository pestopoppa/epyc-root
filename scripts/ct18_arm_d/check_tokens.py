"""Check the released tokenizer IDs and decoded token bytes with the CPU vocab-only CLI."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from packet import TOKENS, identity

BIN = Path("/mnt/raid0/llm/kernels/builds/cpu-20261020-dd3d9721c/bin")


def token_ids(tokenizer):
    added = json.loads(tokenizer.read_bytes())["added_tokens"]
    ids = {entry["content"]: entry["id"] for entry in added if entry["special"] and entry["content"] in TOKENS}
    if set(ids) != set(TOKENS) or len(set(ids.values())) != len(TOKENS):
        raise ValueError(f"{tokenizer}: missing or aliased DataFilter special token")
    return ids


def token_check(gguf, tokenizer, expected_sha256):
    before = identity(gguf)
    ids = token_ids(tokenizer)
    with gguf.open("rb") as f:
        if f.read(4) != b"GGUF":
            raise ValueError(f"{gguf}: invalid GGUF magic")
        f.seek(0)
        if hashlib.file_digest(f, "sha256").hexdigest() != expected_sha256:
            raise ValueError("converted GGUF differs from the supplied conversion digest")
    for token, expected in ids.items():
        result = subprocess.run([str(BIN / "llama-tokenize"), "-m", str(gguf), "--no-bos",
                                 "--parse-special", "-p", token], check=True, capture_output=True,
                                text=True, env=dict(os.environ, LD_LIBRARY_PATH=str(BIN)))
        pieces = re.findall(r"^\s*(\d+) -> '(.*)'$", result.stdout, re.M)
        if pieces != [(str(expected), token)]:
            raise ValueError(f"{token}: expected one token {expected} decoding to itself, saw {pieces}")
    if identity(gguf) != before:
        raise ValueError("GGUF changed during verification")
    return {"gguf_identity": before, "gguf_sha256": expected_sha256, "tokens": ids,
            "tokenizer_sha256": hashlib.sha256(tokenizer.read_bytes()).hexdigest()}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("gguf", type=Path)
    p.add_argument("tokenizer", type=Path, help="released DataFilter tokenizer.json")
    p.add_argument("gguf_sha256", help="digest recorded at conversion")
    args = p.parse_args()
    print(json.dumps(token_check(args.gguf, args.tokenizer, args.gguf_sha256), indent=2))
