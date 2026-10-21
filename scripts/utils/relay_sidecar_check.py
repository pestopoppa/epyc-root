#!/usr/bin/env python3
"""relay_sidecar_check.py — SEC-ART-9 relay and sidecar check (handoffs/active/model-artifact-integrity.md).

A community repo that presents itself as a copy of an upstream can be byte-identical on every weight file and
still carry extra files the upstream never shipped: intake-2197#00 found a relay of trusted quants plus one
refusal-direction sidecar. This tool compares the relay's file tree with the claimed upstream's through the HF
tree API (`?recursive=1&expand=1`, read-only metadata, nothing downloaded) and reports:

  matched        files whose content id is the same in both (LFS sha256 oid; git blob oid for non-LFS files)
  changed        the same path in both with a DIFFERENT content id (the relay altered an upstream file)
  relay_only     every file the upstream lacks, each flagged `tensor_like` (weights / control-vector / adapter
                 suffixes or any LFS file) and, when its bytes DO exist upstream under another name, `renamed_from`
  upstream_only  files the relay dropped (informational; a quant subset is normal)

Verdict (exit code): `clean` (0) no relay_only and no changed; `relay_extras` (3) the upstream lacks files the
relay ships; `content_differs` (3) a shared path differs; `no_overlap` (4) NOTHING matched, so byte identity with
the claimed upstream is not established at all (a re-quantised or converted repo looks like this; the file list
is then only an inventory, not a relay verdict). A non-clean verdict never auto-rejects a model: it is the input
to the SEC-ART-3 review, into which the result is recorded (`--review-record FILE` merges it under
`relay_sidecar_check`, creating the file if absent and leaving every other field alone).

`--upstream` may be omitted when the relay's model card names it (`cardData.base_model`); a card with several
bases, or none, refuses with exit 2 rather than guessing. Revisions default to `main` and are resolved to commit
shas first, so both trees are read at one commit each and the result carries the shas it describes.

Tests: tests/test_relay_sidecar_check.py (mocked tree API)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

SCHEMA = "model-relay-check/1"
HF_ENDPOINT = "https://huggingface.co"
HF_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
# Suffixes that carry numeric payload an inference stack may load. Any LFS-tracked file is flagged too.
TENSOR_SUFFIXES = (".gguf", ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".npy", ".npz", ".pkl", ".pickle",
                   ".onnx", ".h5", ".msgpack", ".ot", ".mlmodel", ".tflite")
VERDICT_EXIT = {"clean": 0, "relay_extras": 3, "content_differs": 3, "no_overlap": 4}


def hf_get_json(url: str):
    """GET a HF API URL as JSON (HF_TOKEN honoured, metadata only). Tests pass their own fetch instead."""
    req = urllib.request.Request(url, headers={"User-Agent": "epyc-relay-check/1"})
    if os.environ.get("HF_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['HF_TOKEN']}")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
        return json.load(resp)


def _resolve(repo: str, ref: str, fetch: Callable[[str], Any]) -> str:
    info = fetch(f"{HF_ENDPOINT}/api/models/{repo}/revision/{urllib.parse.quote(ref, safe='')}")
    sha = info.get("sha", "")
    if not SHA40.match(sha):
        raise ValueError(f"HF returned no 40-hex commit sha for {repo}@{ref}: {sha!r}")
    return sha


def _files(repo: str, sha: str, fetch: Callable[[str], Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for e in fetch(f"{HF_ENDPOINT}/api/models/{repo}/tree/{sha}?recursive=1&expand=1"):
        if e.get("type") != "file":
            continue
        lfs = e.get("lfs") or {}
        out[e["path"]] = {"path": e["path"], "id": lfs.get("oid") or e.get("oid"), "lfs": bool(lfs),
                          "size": lfs.get("size", e.get("size"))}
    return out


def claimed_upstream(repo: str, fetch: Callable[[str], Any]) -> str:
    """The single base model the relay's card names, else ValueError (never guess)."""
    info = fetch(f"{HF_ENDPOINT}/api/models/{repo}")
    base = (info.get("cardData") or {}).get("base_model")
    bases = [base] if isinstance(base, str) else list(base or [])
    if len(bases) != 1 or not HF_REPO_RE.match(str(bases[0])):
        raise ValueError(f"{repo} does not name exactly one upstream in cardData.base_model ({bases!r}); pass --upstream")
    return str(bases[0])


def compare(relay_files: dict[str, dict], upstream_files: dict[str, dict]) -> dict[str, Any]:
    up_by_id: dict[str, list[str]] = {}
    for f in upstream_files.values():
        up_by_id.setdefault(str(f["id"]), []).append(f["path"])
    matched, changed, relay_only = [], [], []
    for path, f in sorted(relay_files.items()):
        up = upstream_files.get(path)
        if up is None:
            row = {"path": path, "size": f["size"], "id": f["id"], "lfs": f["lfs"],
                   "tensor_like": f["lfs"] or path.lower().endswith(TENSOR_SUFFIXES)}
            if str(f["id"]) in up_by_id:
                row["renamed_from"] = sorted(up_by_id[str(f["id"])])
            relay_only.append(row)
        elif up["id"] == f["id"]:
            matched.append(path)
        else:
            changed.append({"path": path, "relay_id": f["id"], "upstream_id": up["id"], "lfs": f["lfs"]})
    upstream_only = sorted(set(upstream_files) - set(relay_files))
    if not matched and not any("renamed_from" in r for r in relay_only):
        verdict = "no_overlap"
    elif changed:
        verdict = "content_differs"
    elif any("renamed_from" not in r for r in relay_only):
        verdict = "relay_extras"
    else:
        verdict = "clean"
    return {"verdict": verdict, "matched": matched, "changed": changed, "relay_only": relay_only,
            "upstream_only": upstream_only}


def check(relay: str, upstream: str | None, relay_rev: str = "main", upstream_rev: str = "main",
          fetch: Callable[[str], Any] = hf_get_json) -> dict[str, Any]:
    for r in (relay, upstream):
        if r is not None and not HF_REPO_RE.match(r):
            raise ValueError(f"{r!r} is not ORG/REPO")
    claimed_from = "argument"
    if upstream is None:
        upstream, claimed_from = claimed_upstream(relay, fetch), "cardData.base_model"
    relay_sha, up_sha = _resolve(relay, relay_rev, fetch), _resolve(upstream, upstream_rev, fetch)
    result = compare(_files(relay, relay_sha, fetch), _files(upstream, up_sha, fetch))
    return {"schema": SCHEMA, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "relay": {"hf_repo": relay, "revision": relay_sha}, "upstream": {"hf_repo": upstream, "revision": up_sha,
                                                                              "claimed_from": claimed_from},
            **result}


def merge_into_review(review_path: str | os.PathLike[str], result: dict[str, Any]) -> None:
    """Record `result` under `relay_sidecar_check` in the SEC-ART-3 review record (create if absent, keep the rest)."""
    p = Path(review_path)
    rec = json.loads(p.read_text()) if p.exists() else {}
    if not isinstance(rec, dict):
        raise ValueError(f"{p} is not a JSON object")
    rec["relay_sidecar_check"] = result
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, p)


def render(result: dict[str, Any]) -> list[str]:
    r, u = result["relay"], result["upstream"]
    lines = [f"relay {r['hf_repo']}@{r['revision'][:12]} vs upstream {u['hf_repo']}@{u['revision'][:12]} "
             f"(claimed via {u['claimed_from']}): {result['verdict'].upper()}",
             f"  matched {len(result['matched'])}, changed {len(result['changed'])}, "
             f"relay_only {len(result['relay_only'])}, upstream_only {len(result['upstream_only'])}"]
    for row in result["relay_only"]:
        note = f" (same bytes as upstream {', '.join(row['renamed_from'])})" if "renamed_from" in row else ""
        lines.append(f"  FILE UPSTREAM LACKS: {row['path']} [{'tensor-like' if row['tensor_like'] else 'other'}]{note}")
    for row in result["changed"]:
        lines.append(f"  CHANGED: {row['path']} relay {row['relay_id']} != upstream {row['upstream_id']}")
    if result["verdict"] == "no_overlap":
        lines.append("  no file matched upstream: byte identity is NOT established (re-quantised or converted repo?)")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="compare a relay repo with its claimed upstream (HF tree API only)")
    ap.add_argument("--repo", required=True, help="the relay / community ORG/REPO under review")
    ap.add_argument("--upstream", help="claimed upstream ORG/REPO (default: the relay card's single base_model)")
    ap.add_argument("--repo-revision", default="main")
    ap.add_argument("--upstream-revision", default="main")
    ap.add_argument("--review-record", help="SEC-ART-3 review JSON to merge the result into")
    ap.add_argument("--json", action="store_true", help="print the full JSON result instead of the summary")
    a = ap.parse_args(argv)
    try:
        result = check(a.repo, a.upstream, a.repo_revision, a.upstream_revision, fetch=hf_get_json)
    except Exception as exc:  # noqa: BLE001 - an unreadable comparison is a refusal to conclude, never "clean"
        print(f"REFUSED: cannot complete relay check: {exc}", file=sys.stderr)
        return 2
    if a.review_record:
        merge_into_review(a.review_record, result)
    print(json.dumps(result, indent=2) if a.json else "\n".join(render(result)))
    return VERDICT_EXIT[result["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
