"""Stand-alone matched C8 long-prompt comparison; not wired into a keep gate.

The caller owns GPU admission and output retention.  This adapter refuses a floor
from any other request set, recipe, or anchor execution; it never treats an
uncalibrated comparison as evidence.  Workload/tokenizer validation belongs to
``longctx_c8`` and happens before any server is launched.
"""
from pathlib import Path

from . import longctx_c8, serving


def _validated(anchor, manifest, proof, texts, encode, tokenizer_sha256, pairs):
    if anchor.backend != "gpu" or anchor.template.np != 8:
        raise ValueError("long-context C8 comparison requires a GPU np=8 launch")
    if type(pairs) is not int or not 1 <= pairs <= 64:
        raise ValueError("matched pair count must be in 1..64")
    identity = anchor.execution_digest
    if (not isinstance(identity, str) or len(identity) != 64
            or any(c not in "0123456789abcdef" for c in identity)):
        raise ValueError("anchor execution identity is missing")
    frozen = longctx_c8.validate_manifest(anchor.template, manifest, proof, texts,
                                           encode, tokenizer_sha256)
    requests = frozen.requests(tuple(p.prompt_id for p in frozen.prompts), anchor.template)
    return requests, identity


def _store(root, anchor, identity):
    return Path(root) / "longctx-c8-floors" / anchor.template.recipe_hash / identity


def calibrate(root, anchor, manifest, proof, texts, encode, tokenizer_sha256, *, pairs,
              samples=serving.MATCHED_CALIBRATION_PAIRS):
    """Record an explicit matched A/A floor for the validated workload and anchor."""
    requests, identity = _validated(anchor, manifest, proof, texts, encode,
                                    tokenizer_sha256, pairs)
    store = _store(root, anchor, identity)
    path = serving.floor_path(store, anchor.template, frozen_requests=requests,
                             instrument=serving.MATCHED_INSTRUMENT, pairs=pairs)
    if path.exists():
        raise serving.ServingFloorMismatch("refusing to overwrite an existing C8 floor")
    row = serving.calibrate_floor(anchor.template, Path(anchor.build_dir), samples=samples,
                                  port=anchor.port, resolved_recipe=anchor,
                                  frozen_requests=requests,
                                  instrument=serving.MATCHED_INSTRUMENT, pairs=pairs)
    serving._validate_matched_floor(row, anchor.template, requests, pairs, resolved=anchor)
    baseline = row.get("baseline_resolved_recipe")
    if not isinstance(baseline, dict) or baseline.get("execution_digest") != identity:
        raise serving.ServingFloorMismatch("C8 calibration anchor identity differs")
    return serving.write_floor(store, anchor.template, row, frozen_requests=requests,
                               unit=serving.CALIBRATION_UNIT,
                               instrument=serving.MATCHED_INSTRUMENT, pairs=pairs)


def compare(root, anchor, candidate, manifest, proof, texts, encode, tokenizer_sha256, *, pairs):
    """Compare fresh server processes in recorded randomized order, against its own floor."""
    requests, identity = _validated(anchor, manifest, proof, texts, encode,
                                    tokenizer_sha256, pairs)
    if candidate.backend != "gpu" or candidate.template.np != 8:
        raise ValueError("candidate must use a GPU np=8 launch")
    store = _store(root, anchor, identity)
    reading = serving.load_floor(store, anchor.template, frozen_requests=requests,
                                 instrument=serving.MATCHED_INSTRUMENT, pairs=pairs)
    if not reading.verified or reading.floor_pct is None:
        raise serving.ServingFloorMismatch("C8 comparison requires its own calibrated floor")
    serving._validate_matched_floor(reading.row, anchor.template, requests, pairs, resolved=anchor)
    baseline = reading.row.get("baseline_resolved_recipe")
    if not isinstance(baseline, dict) or baseline.get("execution_digest") != identity:
        raise serving.ServingFloorMismatch("C8 floor anchor execution identity differs")
    return serving.compare(anchor.template, Path(anchor.build_dir), Path(candidate.build_dir),
                           pairs=pairs, floor_pct=reading.floor_pct, floor_unit=reading.unit,
                           port=anchor.port, anchor_resolved_recipe=anchor,
                           candidate_resolved_recipe=candidate, frozen_requests=requests,
                           floor_request_digest=reading.request_digest,
                           instrument=serving.MATCHED_INSTRUMENT, floor_record=reading.row)
