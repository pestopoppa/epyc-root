#!/usr/bin/env python3
"""Fail closed when resuming a historical CPU-leg slot.

Call run_guarded instead of runner.run. Identity must be captured by the
launcher from verified model/build content and its actual argv. The receipt
must be written by the checkpoint producer; never fabricate one for old slots.
No checkpoint receipt is inferred from a directory name or a timestamp.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

IDENTITY_KEYS = {"model_sha256", "build_sha256", "argv_sha256"}


def _identity(value):
    if not isinstance(value, dict) or set(value) != IDENTITY_KEYS:
        raise ValueError("identity requires model, build and argv digests")
    if any(not isinstance(v, str) or len(v) != 64 or
           any(c not in "0123456789abcdef" for c in v) for v in value.values()):
        raise ValueError("identity values must be SHA-256 hex digests")
    return value


def _atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=".resume-")
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def fresh_state(arm):
    return {"arm": arm, "turn": 0, "depth": 0, "saved_turn": 0,
            "probes_done": [], "short_done": [], "cold_done": False}


def prepare_resume(state_path, slot_path, receipt_path, identity, *, arm="CY2"):
    """Return a decision and persist a safe state before the runner reads it.

    A valid receipt binds the entire saved state and slot bytes to the model,
    build and exact argv. Unsealed or changed inputs always cause re-prefill.
    Preserve the previous state by content digest before replacing it. Leave
    both the slot and every calls/probe/turn record untouched.
    """
    _identity(identity)
    state_path, slot_path, receipt_path = map(Path, (state_path, slot_path, receipt_path))
    if not state_path.exists():
        return {"action": "fresh", "reason": "no prior state", "archive": None}
    raw = state_path.read_bytes()
    state_digest = hashlib.sha256(raw).hexdigest()
    try:
        state = json.loads(raw)
        receipt = json.loads(receipt_path.read_bytes())
        if not isinstance(state, dict) or state.get("arm") != arm:
            raise ValueError("state arm mismatch")
        if not isinstance(receipt, dict) or receipt.get("schema") != "yarn-cpu-checkpoint-v1":
            raise ValueError("checkpoint receipt schema mismatch")
        if receipt.get("identity") != identity or receipt.get("state_sha256") != state_digest:
            raise ValueError("checkpoint identity or saved state mismatch")
        if type(state.get("saved_turn")) is not int or state["saved_turn"] <= 0:
            raise ValueError("no saved turn")
        # Legacy state may contain progress after its last slot save. Such a
        # state cannot establish the saved depth or which probes are reusable.
        if (type(state.get("turn")) is not int or state["turn"] != state["saved_turn"]
                or type(state.get("depth")) is not int or state["depth"] <= 0):
            raise ValueError("state is not at the saved checkpoint")
        if not slot_path.is_file() or slot_path.stat().st_size <= 0:
            raise ValueError("saved slot missing or empty")
        with slot_path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if receipt.get("slot_sha256") != digest:
            raise ValueError("saved slot digest mismatch")
        return {"action": "resume", "reason": "checkpoint identity verified", "archive": None}
    except (OSError, ValueError, TypeError) as exc:
        reason = str(exc)
    archive = state_path.with_name(state_path.name + ".unusable-" + state_digest)
    if archive.exists():
        if archive.read_bytes() != raw:
            raise ValueError("existing state archive differs; refusing overwrite")
    else:
        # O_EXCL preserves history even if a second invocation races this one.
        with archive.open("xb") as stream:
            stream.write(raw)
    _atomic_json(state_path, fresh_state(arm))
    return {"action": "re-prefill", "reason": reason, "archive": str(archive)}


def run_guarded(runner, args, identity, receipt_path):
    """Integrate the check before the legacy run function loads state.json.

    Copy the args: a caller cannot accidentally override this decision with
    force-preflight or an external self-test server. The caller still owns
    keeper admission, process cleanup and native preflight. This adapter is
    not a launcher and does not grant or start any compute on its own.
    """
    if args.arm != "CY2" or getattr(args, "force_preflight", False) or getattr(args, "selftest_external", False):
        raise ValueError("guarded continuation requires CY2 and native preflight")
    state_path = Path(runner.RESULTS) / args.arm / "state.json"
    decision = prepare_resume(state_path, Path(runner.SLOTS) / (args.arm + ".bin"),
                              receipt_path, identity, arm=args.arm)
    _atomic_json(state_path.with_name("resume-decision.json"), decision)
    return runner.run(copy.copy(args))
