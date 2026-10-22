"""VB-RTEPFX2-WIRE: RTE-PFX-2 stagger-probe write side, projected into the ``chunk-kv`` carrier.

Reads the probe's ``probe.json`` (schema ``epyc.rte_pfx2.v1``) and the recipe's ``RUN_HEADER.json``
(schema ``epyc.rte_pfx2.header.v1``) and emits, per arm, TWO ``chunk_kv`` rows into
``<out_dir>/chunk_kv.beliefs.jsonl``:

* ``uncached_prompt_tokens`` -- samples = per-trial ``total_uncached_prompt_tokens`` (server
  ``timings.prompt_n`` summed over the trial's requests), lower better.
* ``prefix_hit_share`` -- realised = sum over every sibling request of
  ``min(cache_n, expected_prefix_tokens)``, ideal = siblings x trials x ``expected_prefix_tokens``.
  The cap keeps the share about the declared prefix (cache_n also counts the shared salt/stem).

Arm ``simultaneous`` (what parallel_dispatch does today) is the BASELINE; the hold arms are
CANDIDATE. This module owns NO ladder and NO row format: the strict reader, the self hash and
``claim_tuple.grade()`` are ``chunk_kv``'s. A request whose timings the server did not report
(``prompt_n``/``cache_n`` = -1, the probe's placeholder) REFUSES the write: nothing is invented.

Window and served pin are NOT in the probe output: the caller passes ``window`` (id, region-lock
claim, UTC span) and ``role``; model and kernel come from the header's argv (``-m``, argv[0]).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters import _native_sidecar as ns  # noqa: E402
from adapters import chunk_kv  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

PROBE_SCHEMA = "epyc.rte_pfx2.v1"
HEADER_SCHEMA = "epyc.rte_pfx2.header.v1"
CONTROL_ARM = "simultaneous"
ARMS = ("simultaneous", "hold_first_tok", "hold_first_end")


def _flag(argv: list, name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def served_pin(header: Mapping[str, Any], role: str) -> dict:
    argv = header.get("argv")
    if not isinstance(argv, list) or not argv:
        raise CaptureError("RUN_HEADER.argv missing: cannot name the served model/kernel")
    model, binary = _flag(argv, "-m"), str(argv[0])
    if not model:
        raise CaptureError("RUN_HEADER.argv has no -m: model not recorded")
    mtime = header.get("binary_mtime")
    if not ns.text(mtime):
        raise CaptureError("RUN_HEADER.binary_mtime missing: kernel_ref cannot be pinned")
    return {"role": role, "model": os.path.basename(model),
            "kernel_ref": f"{os.path.realpath(binary)}@{mtime}"}


def measurements(probe: Mapping[str, Any], header: Mapping[str, Any], *, role: str,
                 window: Mapping[str, Any], header_sha256: str) -> list[dict]:
    if probe.get("schema") != PROBE_SCHEMA:
        raise CaptureError(f"probe.json schema must be {PROBE_SCHEMA!r}")
    if header.get("schema") != HEADER_SCHEMA:
        raise CaptureError(f"RUN_HEADER.json schema must be {HEADER_SCHEMA!r}")
    expected = probe.get("expected_prefix_tokens")
    if not (ns.nonneg_int(expected) and expected > 0):
        raise CaptureError("probe.expected_prefix_tokens must be a positive integer")
    pin = served_pin(header, role)
    out = []
    for arm in ARMS:
        trials = [r for r in probe.get("results", []) if r.get("arm") == arm]
        if not trials:
            raise CaptureError(f"arm {arm!r} has no trials")
        totals, hits, n_sib = [], 0, 0
        for t in trials:
            for row in t.get("rows", []):
                if not (ns.nonneg_int(row.get("prompt_n")) and ns.nonneg_int(row.get("cache_n"))):
                    raise CaptureError(f"arm {arm!r} trial {t.get('trial')}: server timings missing "
                                       "(prompt_n/cache_n < 0); refusing to invent counts")
                if row.get("idx", 0) > 0:
                    hits += min(row["cache_n"], expected)
                    n_sib += 1
            totals.append(t["summary"]["total_uncached_prompt_tokens"])
        if n_sib == 0:
            raise CaptureError(f"arm {arm!r} has no sibling requests")
        subject = f"arm={arm} n={probe.get('n')} prefix_sha256={header.get('prefix_sha256')}"
        detail = {"arm": arm, "n_trials": len(trials), "n_siblings_total": n_sib,
                  "siblings_on_cached_prefix": sum(t["summary"]["siblings_on_cached_prefix"] for t in trials),
                  "sibling_cache_n": [r["cache_n"] for t in trials for r in t["rows"] if r["idx"] > 0],
                  "hit_fraction": probe.get("hit_fraction"), "run_header_sha256": header_sha256,
                  "cache_ram_mib": header.get("cache_ram_mib"), "seed": header.get("seed")}
        common = {"source_program": "RTE-PFX-2", "subject": subject, "served_pin": pin,
                  "window": dict(window), "is_control": arm == CONTROL_ARM, "detail": detail}
        out.append({**common, "kind": "uncached_prompt_tokens", "samples": [float(x) for x in totals]})
        out.append({**common, "kind": "prefix_hit_share", "realised_tokens": hits,
                    "ideal_tokens": n_sib * expected})
    return out


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, probe_path: str | Path,
    header_path: str | Path, role: str, window: Mapping[str, Any], emitted_at: str | None = None,
) -> Path:
    """Emit ``chunk_kv.beliefs.jsonl`` next to the probe output. Raises :class:`CaptureError`."""
    probe_path, header_path = Path(probe_path), Path(header_path)
    for p in (probe_path, header_path):
        if not p.is_file():
            raise CaptureError(f"missing: {p}")
    probe, header = json.loads(probe_path.read_text()), json.loads(header_path.read_text())
    ms = measurements(probe, header, role=role, window=window,
                      header_sha256=ns.file_sha256(header_path))
    return chunk_kv.write_belief_measurements(
        out_dir, run_id=run_id, producer=producer, results_path=probe_path, measurements=ms,
        emitted_at=emitted_at)


rows_for_run = chunk_kv.rows_for_run
frames_for_sidecar = chunk_kv.frames_for_sidecar
