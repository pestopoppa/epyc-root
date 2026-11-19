#!/usr/bin/env python3
"""Read-only SR-6 prompt audit; passing is scoped to the supplied inventories.

Manifest: {"prompts": [{"id", "class", "window", "seed", "prompt",
"rendered_prompt", "rendered_token_ids", "source", "source_kind"}]}; source_kind
must be "non_model". History: {"prompts": [{"prompt": ...}, ...]} or
{"prompt_sha256": [hex, ...]}; exposure: {"prompt_sha256": [hex, ...]}.
The caller must independently establish inventory completeness and tokenization
provenance. This tool cannot establish either or detect copied generations.
"""
import argparse
from collections import Counter
import hashlib
import json
import sys
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    raw = Path(path).read_bytes()
    return json.loads(raw), sha(raw)


def hashes(inventory):
    if not isinstance(inventory, dict):
        raise ValueError("inventory must be an object")
    out = set()
    if "prompts" in inventory:
        if not isinstance(inventory["prompts"], list):
            raise ValueError("invalid prompts inventory")
        for p in inventory["prompts"]:
            if not isinstance(p, dict) or not isinstance(p.get("prompt"), str):
                raise ValueError("invalid historical prompt")
            out.add(sha(p["prompt"].encode("utf-8")))
    if "prompt_sha256" in inventory:
        values = inventory["prompt_sha256"]
        if not isinstance(values, list) or any(not isinstance(x, str) or len(x) != 64 or any(c not in '0123456789abcdef' for c in x) for x in values):
            raise ValueError("invalid SHA-256 inventory")
        out.update(values)
    if not {"prompts", "prompt_sha256"} & inventory.keys():
        raise ValueError("inventory has no recognized hash source")
    return out


def repeated_5grams(tokens):
    grams = [tuple(tokens[i:i+5]) for i in range(max(0, len(tokens)-4))]
    counts = Counter(grams)
    # Count occurrences beyond the first, not all occurrences of repeated types.
    numerator = sum(n - 1 for n in counts.values())
    denominator = len(grams)
    return {"numerator": numerator, "denominator": denominator,
            "fraction": numerator / denominator if denominator else None,
            "definition": "occurrences beyond first / all 5-gram occurrences"}


def audit(manifest, prior, exposed):
    rows = manifest.get("prompts") if isinstance(manifest, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("manifest must contain nonempty prompts list")
    seen_ids, seen_seeds, seen_hashes, windows, classes = set(), set(), set(), set(), set()
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("prompt entry must be an object")
        for key in ("id", "class", "window", "prompt", "rendered_prompt", "source"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"missing or empty {key}")
        if row["class"] not in ("code", "rag", "prose"):
            raise ValueError("unknown class")
        if row.get("source_kind") != "non_model":
            raise ValueError("source_kind must assert non_model")
        seed, tokens = row.get("seed"), row.get("rendered_token_ids")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        if not isinstance(tokens, list) or len(tokens) < 5 or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in tokens):
            raise ValueError("rendered_token_ids must contain at least five nonnegative integers")
        digest = sha(row["prompt"].encode("utf-8"))
        if row["id"] in seen_ids or seed in seen_seeds or digest in seen_hashes:
            raise ValueError("duplicate id, seed or prompt")
        if digest in prior or digest in exposed:
            raise ValueError("prompt matches supplied historical or exposure inventory")
        seen_ids.add(row["id"]); seen_seeds.add(seed); seen_hashes.add(digest)
        windows.add(row["window"]); classes.add(row["class"])
        result.append({"id": row["id"], "window": row["window"], "class": row["class"],
                       "prompt_sha256": digest,
                       "rendered_prompt_sha256": sha(row["rendered_prompt"].encode("utf-8")),
                       "token_ids_sha256": sha(json.dumps(tokens, separators=(',', ':')).encode()),
                       "repeated_5gram": repeated_5grams(tokens)})
    if len(windows) < 3 or classes != {"code", "rag", "prose"}:
        raise ValueError("need at least three windows and all three classes")
    return {"status": "SCOPED_PASS_NOT_PUBLICATION_AUTHORITY", "prompts": result,
            "limitations": ["Disjointness is only against supplied inventories; completeness is not proven.",
                            "Source and tokenizer provenance are assertions, not verified.",
                            "No semantic near-duplicate or copied-generation detection."]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifest"); p.add_argument("--history", required=True, action="append")
    p.add_argument("--exposure", required=True)
    a = p.parse_args()
    try:
        manifest, manifest_sha = read_json(a.manifest)
        prior = set(); inventory_shas = []
        for path in a.history:
            data, digest = read_json(path); prior.update(hashes(data)); inventory_shas.append({"path": path, "sha256": digest})
        data, exposure_sha = read_json(a.exposure)
        result = audit(manifest, prior, hashes(data))
        result.update({"manifest_sha256": manifest_sha, "history": inventory_shas,
                       "exposure": {"path": a.exposure, "sha256": exposure_sha}})
        print(json.dumps(result, indent=2)); return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "UNKNOWN", "reason": str(exc)}), file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main())
