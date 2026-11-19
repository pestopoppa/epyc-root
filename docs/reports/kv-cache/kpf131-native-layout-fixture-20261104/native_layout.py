"""Fail-closed decoder for captured KV debug grids (synthetic-fixture scope).

This parses textual allocator diagnostics. It does NOT decode a physical cache
ABI or prove that a log span belongs to a particular live request. Callers must
provide explicit capture bindings; missing evidence yields UNKNOWN.
"""
from __future__ import annotations

import hashlib
import json
import re


class InvalidLayout(ValueError):
    """Observed bytes/metadata contradict the declared debug-grid format."""


class UnknownLayout(ValueError):
    """Required witness is absent or cannot safely be attributed."""


_MAX_SUPPORTED_GRID = 262144  # local safety cap, not a proven historical cache size


def parse_grid(owners_text: str, positions_text: str, size: int) -> dict:
    if type(size) is not int or size <= 0:
        raise InvalidLayout("invalid grid size")
    if size > _MAX_SUPPORTED_GRID:
        raise UnknownLayout("grid exceeds local parser bound; historical geometry is unproven")
    if not isinstance(owners_text, str) or not isinstance(positions_text, str):
        raise InvalidLayout("grid tables must be text")
    owners = re.sub(r"[\s*]", "", owners_text)
    if len(owners) != size or any(c not in ".0123456789M" for c in owners):
        raise InvalidLayout("bad or ambiguous ownership grid")
    words = positions_text.replace("*", " ").split()
    if len(words) != size or any(not re.fullmatch(r"\.|-?\d+", w) for w in words):
        raise InvalidLayout("bad position grid")
    positions = [None if w == "." else int(w) for w in words]
    if any(p is not None and p < 0 for p in positions):
        raise InvalidLayout("occupied positions must be nonnegative")
    if any((o == ".") != (p is None) for o, p in zip(owners, positions)):
        raise InvalidLayout("grid occupancy mismatch")
    return {"owners": owners, "positions": positions, "size": size}


_HEADER = re.compile(
    r"find_slot: stream\[(\d+)\], n =\s*(\d+), used =\s*(\d+), "
    r"head =\s*(\d+), size =\s*(\d+), n_swa =\s*(\d+)"
)


def first_debug_grid(lines) -> dict:
    """Parse first complete known text grid; reject incomplete framing."""
    if not isinstance(lines, (list, tuple)) or any(not isinstance(x, str) for x in lines):
        raise InvalidLayout("log lines must be a sequence of text")
    for i, line in enumerate(lines):
        match = _HEADER.search(line)
        if not match:
            continue
        stream, used_max_p1, used, head, size, n_swa = map(int, match.groups())
        if size > _MAX_SUPPORTED_GRID:
            raise UnknownLayout("grid exceeds local parser bound; historical geometry is unproven")
        if (size <= 0 or head > size or used_max_p1 > size
                or used > used_max_p1 or n_swa < 0):
            raise InvalidLayout("malformed allocator header ABI")
        blocks, chunk = [], []
        for next_line in lines[i + 1:]:
            row = next_line.strip()
            if _HEADER.search(row) or row.startswith("find_slot: stream["):
                break
            if row.startswith("find_slot:") and "min[" in row:
                break
            if not row:
                if chunk:
                    blocks.append("\n".join(chunk)); chunk = []
                    if len(blocks) == 2:
                        break
                continue
            chunk.append(row)
        if chunk and len(blocks) < 2:
            blocks.append("\n".join(chunk))
        if len(blocks) != 2:
            raise UnknownLayout("incomplete or unknown native grid framing")
        grid = parse_grid(blocks[0], blocks[1], size)
        occupied_indices = [i for i, owner in enumerate(grid["owners"]) if owner != "."]
        observed_used = len(occupied_indices)
        observed_used_max_p1 = occupied_indices[-1] + 1 if occupied_indices else 0
        if used != observed_used:
            raise InvalidLayout("header used count differs from occupied grid cells")
        if used_max_p1 != observed_used_max_p1:
            raise InvalidLayout("header used_max_p1 differs from last occupied grid index")
        grid.update(stream=stream, used_max_p1=used_max_p1, used=used,
                    head=head, n_swa=n_swa)
        return grid
    raise UnknownLayout("no native find_slot grid in request scope")


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_BINDING_KEYS = {
    "request_id", "task_id", "slot", "pid", "image_sha256", "binary_sha256",
    "mappings", "event_start", "event_end",
}
_MAPPING_KEYS = {"path", "device", "inode", "sha256"}


def _validate_binding(binding) -> None:
    if not isinstance(binding, dict):
        raise UnknownLayout("capture binding absent")
    if not _BINDING_KEYS.issubset(binding):
        raise UnknownLayout("capture binding incomplete")
    if (not isinstance(binding["request_id"], str) or not binding["request_id"]
            or type(binding["task_id"]) is not int or binding["task_id"] < 0
            or type(binding["slot"]) is not int or not 0 <= binding["slot"] <= 9
            or type(binding["pid"]) is not int or binding["pid"] <= 0
            or type(binding["event_start"]) is not int or binding["event_start"] < 0
            or type(binding["event_end"]) is not int or binding["event_end"] <= binding["event_start"]):
        raise InvalidLayout("malformed capture identity or event span")
    for key in ("image_sha256", "binary_sha256"):
        if not isinstance(binding[key], str) or not _HEX64.fullmatch(binding[key]):
            raise InvalidLayout("malformed image/binary digest")
    mappings = binding["mappings"]
    if not isinstance(mappings, list) or not mappings:
        raise UnknownLayout("mapped-library custody absent")
    seen = set()
    for mapping in mappings:
        if not isinstance(mapping, dict) or not _MAPPING_KEYS.issubset(mapping):
            raise UnknownLayout("mapped-library identity incomplete")
        if (not isinstance(mapping["path"], str) or not mapping["path"].startswith("/")
                or not isinstance(mapping["device"], str) or not mapping["device"]
                or type(mapping["inode"]) is not int or mapping["inode"] <= 0
                or not isinstance(mapping["sha256"], str) or not _HEX64.fullmatch(mapping["sha256"])):
            raise InvalidLayout("malformed mapped-library identity")
        identity = (mapping["path"], mapping["device"], mapping["inode"])
        if identity in seen:
            raise InvalidLayout("duplicate mapped-library identity")
        seen.add(identity)


def _compare_grids(fork, control, *, child_slot, control_slot, fork_receipt,
                   prefix, batch_partition_fork, batch_partition_control):
    if (not isinstance(fork, dict) or not isinstance(control, dict)
            or not {"owners", "positions", "size"}.issubset(fork)
            or not {"owners", "positions", "size"}.issubset(control)):
        raise UnknownLayout("decoded grid absent")
    numeric = ("size", "used", "used_max_p1", "head", "n_swa", "stream")
    for grid in (fork, control):
        if any(key not in grid for key in numeric):
            raise UnknownLayout("allocator metadata incomplete")
        if any(type(grid[key]) is not int for key in numeric):
            raise InvalidLayout("allocator metadata must be integers")
        if grid["size"] > _MAX_SUPPORTED_GRID:
            raise UnknownLayout("grid exceeds local parser bound; historical geometry is unproven")
        if (grid["size"] <= 0 or grid["used"] < 0 or grid["used_max_p1"] < 0
                or grid["head"] < 0 or grid["head"] > grid["size"]
                or grid["used_max_p1"] > grid["size"] or grid["n_swa"] < 0
                or grid["stream"] < 0):
            raise InvalidLayout("allocator metadata outside supported bounds")
        if (not isinstance(grid["owners"], str)
                or not isinstance(grid["positions"], list)
                or len(grid["owners"]) != grid["size"]
                or len(grid["positions"]) != grid["size"]):
            raise InvalidLayout("decoded grid shape is malformed")
        if any(owner not in ".0123456789M" for owner in grid["owners"]):
            raise InvalidLayout("decoded grid contains invalid owner")
        if any((owner == ".") != (pos is None) or
               (pos is not None and type(pos) is not int)
               for owner, pos in zip(grid["owners"], grid["positions"])):
            raise InvalidLayout("decoded grid occupancy is malformed")
        if any(pos is not None and pos < 0 for pos in grid["positions"]):
            raise InvalidLayout("occupied positions must be nonnegative")
        occupied = [i for i, owner in enumerate(grid["owners"]) if owner != "."]
        expected_max = occupied[-1] + 1 if occupied else 0
        if grid["used"] != len(occupied):
            raise InvalidLayout("allocator used count differs from grid occupancy")
        if grid["used_max_p1"] != expected_max:
            raise InvalidLayout("allocator used_max_p1 differs from grid high-water index")
    if type(prefix) is not int or prefix <= 0:
        raise InvalidLayout("invalid prefix")
    if type(child_slot) is not int or type(control_slot) is not int or not (
            0 <= child_slot <= 9 and 0 <= control_slot <= 9 and child_slot != control_slot):
        raise InvalidLayout("slot identity invalid")
    if fork["size"] != control["size"] or fork["positions"] != control["positions"]:
        raise InvalidLayout("native positions/occupancy differ")
    metadata = ("stream", "used_max_p1", "used", "head", "n_swa")
    if any(key not in fork or key not in control for key in metadata):
        raise UnknownLayout("allocator metadata incomplete")
    if any(fork[key] != control[key] for key in metadata):
        raise InvalidLayout("native allocator metadata differs")
    if not batch_partition_fork or not batch_partition_control:
        raise UnknownLayout("batch partition evidence absent")
    if batch_partition_fork != batch_partition_control:
        raise InvalidLayout("batch partition differs")
    if not isinstance(fork_receipt, dict):
        raise UnknownLayout("fork receipt absent")
    required_receipt = {"http", "n_fork_tokens", "fork_src_slot", "task_id", "request_id"}
    if not required_receipt.issubset(fork_receipt):
        raise UnknownLayout("fork receipt incomplete")
    if fork_receipt.get("http") != 200 or fork_receipt.get("n_fork_tokens") != prefix:
        raise InvalidLayout("fork receipt does not bind requested prefix")
    if fork_receipt.get("fork_src_slot") not in (0, 3):
        raise UnknownLayout("fork source slot is absent or unsupported")
    wanted = set(range(prefix))
    fpos, cpos = set(), set()
    for owner, pos in zip(fork["owners"], fork["positions"]):
        if owner == "M" and pos in wanted:
            raise UnknownLayout("multi-owner cells cannot be attributed by this decoder")
        if owner == str(child_slot) and pos in wanted:
            fpos.add(pos)
    for owner, pos in zip(control["owners"], control["positions"]):
        if owner == str(control_slot) and pos in wanted:
            cpos.add(pos)
    if fpos != wanted or cpos != wanted:
        raise UnknownLayout("requested prefix cells not completely attributable")
    for i, pos in enumerate(fork["positions"]):
        if pos in wanted and (fork["owners"][i] != str(child_slot)
                              or control["owners"][i] != str(control_slot)):
            raise InvalidLayout("relevant cells differ or ownership is ambiguous")
    return True


def compare_bound(fork, control, *, child_slot, control_slot, fork_receipt, prefix,
                  batch_partition_fork, batch_partition_control,
                  fork_binding, control_binding) -> dict:
    """Return MATCHED only when grid, identity, mappings and fork receipt bind.

    Missing witnesses are UNKNOWN; contradictory observed evidence is INVALID.
    Neither state includes a layout digest that could be mistaken for a proof.
    """
    try:
        _validate_binding(fork_binding)
        _validate_binding(control_binding)
        if not isinstance(fork_receipt, dict):
            raise UnknownLayout("fork receipt absent")
        required_receipt = {"http", "n_fork_tokens", "fork_src_slot", "task_id", "request_id"}
        if not required_receipt.issubset(fork_receipt):
            raise UnknownLayout("fork receipt incomplete")
        if fork_binding["slot"] != child_slot or control_binding["slot"] != control_slot:
            raise InvalidLayout("capture slot differs from requested slot")
        if fork_binding["task_id"] != fork_receipt.get("task_id"):
            raise InvalidLayout("fork task identity mismatch")
        if fork_binding["request_id"] != fork_receipt.get("request_id"):
            raise InvalidLayout("fork request identity mismatch")
        if fork_binding["request_id"] == control_binding["request_id"]:
            raise InvalidLayout("fork and control request identities collide")
        for key in ("pid", "image_sha256", "binary_sha256", "mappings"):
            if fork_binding[key] != control_binding[key]:
                raise InvalidLayout("fork/control capture custody differs: " + key)
        _compare_grids(fork, control, child_slot=child_slot,
                       control_slot=control_slot, fork_receipt=fork_receipt,
                       prefix=prefix, batch_partition_fork=batch_partition_fork,
                       batch_partition_control=batch_partition_control)
    except UnknownLayout as error:
        return {"status": "UNKNOWN", "reason": str(error)}
    except (InvalidLayout, AttributeError, KeyError, TypeError) as error:
        return {"status": "INVALID", "reason": str(error)}
    payload = {"positions": fork["positions"], "prefix": prefix,
               "batch_partition": batch_partition_fork,
               "fork_request_id": fork_binding["request_id"],
               "control_request_id": control_binding["request_id"]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()
    return {"status": "MATCHED", "layout_sha256": digest,
            "batch_partition_equal": True, "method": "text KV debug grid plus bound receipts"}
