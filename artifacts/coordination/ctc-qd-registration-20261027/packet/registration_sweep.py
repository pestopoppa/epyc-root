#!/usr/bin/env python3
"""PROPOSED read-only registration sweep; no resource, lease or mutation authority.

Only explicitly bound native records supply load/server/anchor identity. Legacy
rows lacking metadata are UNKNOWN, never a shared null load. This checks a
projection of native records, not their full native validity or live residency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import validate_fillers as vf

SCHEMA = "epyc.registration_sweep.v1"
RECIPE = "epyc.autokernel.canonical_launch.v1"
LAUNCH = "epyc.stack.server_launch.v1"
PLANS = {"epyc.autokernel.experiment_plan.v1", "epyc.autokernel.experiment_plan.v2"}
MAX_BYTES = 2 * 1024 * 1024


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def text(value):
    require(isinstance(value, str) and bool(value.strip()), "nonempty text required")
    return value


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value), "invalid SHA256")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_regular(path):
    """Bound reads and refuse final symlinks/special files before any read.

    Parent symlink aliases remain valid. Nonblocking open prevents a FIFO from
    waiting for its writer; fstat then rejects it, directories and devices.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode), "regular file required")
        require(info.st_size <= MAX_BYTES, "record too large")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "record too large")
        return raw
    finally:
        os.close(fd)


def reject_constant(value):
    raise Invalid("nonfinite JSON constant: " + value)


def load_json(path):
    raw = read_regular(path)
    return json.loads(raw, object_pairs_hook=unique_object,
                      parse_constant=reject_constant), hashlib.sha256(raw).hexdigest()


def record(ref):
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "invalid record reference")
    require(Path(text(ref["path"])).is_absolute(), "record path must be absolute")
    value, actual = load_json(ref["path"])
    require(actual == sha(ref["sha256"]), "source record changed: " + ref["path"])
    require(isinstance(value, dict), "source record must be object")
    return value


def artifact(value, role):
    require(isinstance(value, dict), "artifact must be object")
    # The enclosing canonical snapshot binds roles/paths as well as content.
    require(value.get("schema") == "epyc.autokernel.launch_artifact.v1", "unsupported artifact domain")
    require(value["role"] == role, "artifact role mismatch")
    require(Path(text(value["path"])).is_absolute(), "artifact path must be absolute")
    return sha(value["sha256"])


def anchors(refs):
    require(isinstance(refs, list) and 0 < len(refs) <= 32, "native anchors required")
    result = []
    for ref in refs:
        plan = record(ref)
        require(plan.get("schema") in PLANS, "unsupported anchor record domain")
        identity = plan.get("anchor_identity")
        require(isinstance(identity, dict) and bool(identity), "missing native anchor_identity")
        result.append((ref["path"], ref["sha256"], digest(identity)))
    require(len(set(result)) == len(result), "duplicate anchor reference")
    return tuple(sorted(result))


def project(meta, cells, col):
    require(isinstance(meta, dict), "metadata must be object")
    require(sha(meta["row_sha256"]) == digest(cells), "stale row binding")
    if "non_model" in meta:
        require(set(meta) == {"row_sha256", "non_model"}, "non-model metadata conflicts")
        text(meta["non_model"])
        require(cells[col["ds41-class y/n"]] == "n", "DS41 row cannot be non-model")
        return {"non_model": True}
    recipe = record(meta["recipe"])
    require(recipe.get("schema") == RECIPE, "unsupported recipe domain")
    body = {k: v for k, v in recipe.items() if k not in {"schema", "snapshot_digest", "execution_digest"}}
    require(sha(recipe["snapshot_digest"]) == digest(body), "canonical snapshot checksum differs")
    sha(recipe["execution_digest"])  # Native normalized execution domain; NOT an argv hash.
    argv = recipe["argv"]
    require(isinstance(argv, list) and bool(argv) and all(isinstance(x, str) and "\0" not in x for x in argv),
            "invalid exact argv")
    require(isinstance(recipe["dsos"], list) and bool(recipe["dsos"]), "sealed DSO set required")
    model = artifact(recipe["model"], "model")
    drafter = artifact(recipe["drafter"], "drafter") if recipe.get("drafter") is not None else None
    exe = artifact(recipe["executable"], "executable")
    dsos = tuple(sorted((text(x["role"]), artifact(x, "dso")) for x in recipe["dsos"]))
    require(len(set(dsos)) == len(dsos), "duplicate DSO")
    for name in ("launch_env", "relevant_environment"):
        require(isinstance(recipe[name], dict), "missing environment projection")
    require(isinstance(recipe["absent_environment"], list), "absent_environment must be list")
    raw_argv = hashlib.sha256("\0".join(argv).encode()).hexdigest()
    shape = (model, drafter, exe, dsos, "sha256:nul-joined-utf8-argv/v1", raw_argv)
    load = digest([shape, recipe["launch_env"], recipe["relevant_environment"], recipe["absent_environment"]])
    session = meta["session"]
    session_id = text(session["id"])
    require(sha(session["load_sha256"]) == load, "session shared-load binding differs")
    native_anchors = anchors(session["anchors"])
    server = None
    if "server" in meta:
        launch = record(meta["server"])
        require(launch.get("schema") == LAUNCH, "unsupported server record domain")
        require(launch.get("argv") == argv and launch.get("argv_sha256") == raw_argv,
                "server argv/domain differs from exact recipe")
        server = (text(launch["launch_id"]), text(launch["launched_at"]),
                  text(launch["binary_realpath"]), text(launch["model_path"]), raw_argv)
    require(cells[col["ds41-class y/n"]] != "y" or server is not None,
            "DS41 candidate needs native server reference")
    return {"shape": shape, "load": load, "session": session_id, "anchors": native_anchors,
            "server": server, "ds41": cells[col["ds41-class y/n"]] == "y",
            "sources": {k: meta[k] for k in ("recipe", "server") if k in meta}}


def rows(path):
    raw = read_regular(path)
    col, parsed, _ = vf.parse_table(raw.decode("utf-8"))
    result = {}
    for _, cells in parsed:
        require(len(cells) == len(vf.COLUMNS), "malformed 18-cell row")
        rid = text(cells[0])
        require(rid not in result, "duplicate filler-id: " + rid)
        result[rid] = cells
    return col, result, hashlib.sha256(raw).hexdigest()


def sweep(existing, candidate, col, catalog):
    require(isinstance(catalog, dict) and catalog.get("schema") == SCHEMA, "unsupported catalog")
    metadata = catalog["rows"]
    require(isinstance(metadata, dict), "catalog rows must be object")
    rid = candidate[0]
    require(candidate[col["status"]] not in vf.TERMINAL, "terminal candidate")
    own = project(metadata[rid], candidate, col)
    matches, unknown, problems = [], [], []
    resolutions = metadata[rid].get("resolutions", {})
    require(isinstance(resolutions, dict), "resolutions must be object")
    for peer_id, cells in sorted(existing.items()):
        if peer_id == rid or cells[col["status"]] in vf.TERMINAL:
            continue
        try:
            peer = project(metadata[peer_id], cells, col)
        except (Invalid, KeyError, TypeError, OSError, ValueError) as exc:
            unknown.append({"row": peer_id, "reason": str(exc)})
            continue
        if own.get("non_model") or peer.get("non_model"):
            continue
        kinds = []
        if own["shape"] == peer["shape"]:
            kinds.append("same-model-build-argv")
        if own["ds41"] and peer["ds41"] and own["server"] == peer["server"]:
            kinds.append("same-DS41-server")
        if not kinds:
            continue
        match = {"row": peer_id, "kinds": kinds, "session": peer["session"],
                 "shared_load_sha256": peer["load"], "anchors": peer["anchors"], "sources": peer["sources"]}
        matches.append(match)
        resolution = resolutions.get(peer_id, {})
        require(isinstance(resolution, dict), "resolution must be object")
        action = resolution.get("action")
        if action == "separate" and isinstance(resolution.get("reason"), str) and resolution["reason"].strip():
            match["resolution"] = resolution
        elif (action == "join" and own["session"] == peer["session"] == resolution.get("session")
              and own["load"] == peer["load"] == resolution.get("shared_load_sha256")
              and own["anchors"] == peer["anchors"]
              and own["server"] == peer["server"]
              and resolution.get("anchor_refs") == [list(x) for x in peer["anchors"]]):
            match["resolution"] = resolution
        else:
            problems.append(peer_id + ": join compatible session/load/anchors or state a separate reason")
    return {"schema": SCHEMA, "candidate": rid, "allowed": not problems, "matches": matches,
            "unknown_legacy": unknown, "exhaustive": not unknown, "problems": problems,
            "candidate_sources": own.get("sources", {}),
            "candidate_anchors": own.get("anchors", []),
            "owner_adopted": False, "all_producers_bound": False}


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", required=True)
    ap.add_argument("--candidate-row", required=True)
    ap.add_argument("--candidate-id", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--for-registration", action="store_true")
    a = ap.parse_args(argv)
    try:
        col, existing, queue_sha = rows(a.file)
        candidate_col, candidate_rows, candidate_sha = rows(a.candidate_row)
        require(candidate_col == col and set(candidate_rows) == {a.candidate_id}, "one exact candidate row required")
        catalog, catalog_sha = load_json(a.catalog)
        result = sweep(existing, candidate_rows[a.candidate_id], col, catalog)
        result["input_sha256"] = {"queue": queue_sha,
                                  "candidate": candidate_sha,
                                  "catalog": catalog_sha}
        print(json.dumps(result, sort_keys=True))
        return 2 if a.for_registration and not result["allowed"] else 0
    except (Invalid, vf.Malformed, KeyError, TypeError, OSError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "error": str(exc), "allowed": False}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(run())
