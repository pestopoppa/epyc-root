"""SC4: ingest sealed measurement manifests — the corpus that can actually reach Q4 Witnessed.

**This adapter exists because a prior conclusion in this program was wrong.** The 2026-08-11 ceiling
measurement scanned `progress/` markdown, found 2.2% of stated results cited anything durable, and
concluded the organisation records its measurements as prose. That measured the NARRATION layer and
generalized it to the measurement layer — the wrong-sample error, committed by the very session
cataloguing it.

The measurement layer is highly attested and already constitution-compliant. A sealed manifest
carries more provenance than an intake entry ever will:

| MEASUREMENT_POLICY.md § The claim rule | sealed manifest field |
|---|---|
| protocol-id      | `schema_version` / `capture_schema_version` |
| n/reps           | `arms.*.counts` |
| date             | `observational_provenance.sealed_at_utc` |
| attestation ref  | `runner_sha256`, `hashes_json_sha256`, `authority/*.sha256` |

So Q4 `Witnessed` was never unreachable in principle. It was unreachable because nothing read this
directory.

Two refusals are deliberate. A manifest that is not `SEALED_*` is a run in progress, not a result.
And a manifest whose named artifacts are absent from disk grades DOWN rather than being skipped —
a hash over a file that no longer exists proves nothing, and silently dropping it would hide the
decay this substrate exists to surface.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple  # noqa: E402
from claim_tuple import grade as _grade  # noqa: E402
from frames import make_frame  # noqa: E402

ADAPTER_ID = "vidya.adapters.sealed_manifest/v1"
AUTHORITY = "measurement"
RESEARCH_ROOT = Path("/workspace/repos/epyc-inference-research")

FT_SOURCE = "epyc.vidya/frame/source_observed/v1"
FT_CLAIM = "epyc.vidya/frame/claim_proposed/v1"
FT_SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"

_SHA = re.compile(r"^[0-9a-f]{64}$")


def is_sealed(manifest: dict) -> bool:
    """Only a sealed manifest is a result. Anything else is a run someone is still doing."""
    return str(manifest.get("status", "")).upper().startswith("SEALED")


def protocol_id(manifest: dict) -> str | None:
    for key in ("capture_schema_version", "schema_version"):
        val = manifest.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def attestations(manifest: dict) -> dict[str, str]:
    """Every 64-hex digest the manifest carries, keyed by the field that held it."""
    out: dict[str, str] = {}
    for key, val in manifest.items():
        if isinstance(val, str) and _SHA.match(val):
            out[key] = val
    authority = manifest.get("authority")
    if isinstance(authority, dict):
        for name, meta in authority.items():
            if isinstance(meta, dict) and _SHA.match(str(meta.get("sha256", ""))):
                out[f"authority/{name}"] = meta["sha256"]
    return out


def reps(manifest: dict) -> int | None:
    arms = manifest.get("arms")
    if not isinstance(arms, dict):
        return None
    total = 0
    for arm in arms.values():
        counts = (arm or {}).get("counts") if isinstance(arm, dict) else None
        if isinstance(counts, dict):
            total += sum(v for v in counts.values() if isinstance(v, int))
    return total or None


def sealed_at(manifest: dict) -> str | None:
    prov = manifest.get("observational_provenance")
    if isinstance(prov, dict):
        for key in ("sealed_at_utc", "sealed_at", "captured_at"):
            val = prov.get(key)
            if isinstance(val, str) and val.strip():
                return val[:10]
    return None


def project(manifest: dict, *, run_id: str = "run", locator: str = "",
            artifacts_present: bool = True) -> ClaimTuple:
    """Map a sealed manifest into the canonical claim tuple. Projection only — no grading.

    `artifacts_present` is threaded into the tuple as a synthetic path rather than being graded
    here, because presence is a property of the artifact and the ladder is the ladder's business.
    """
    atts = attestations(manifest)
    digest = next(iter(sorted(atts.values())), "")
    return ClaimTuple(
        measurement_id=f"seal_{run_id}",
        metric="sealed_measurement_run",
        value=str(manifest.get("status") or ""),
        date=sealed_at(manifest) or "",
        # A sealed scoring run is the ratified record for its scope, not a proposal under test.
        category="BASELINE",
        claim=(f"Sealed measurement run {run_id}: {manifest.get('status')} under "
               f"{protocol_id(manifest)}"),
        protocol_id=protocol_id(manifest) or "",
        reps=reps(manifest),
        reps_basis="scored:arms.counts" if reps(manifest) else "",
        attestation_sha256=digest,
        attestation_locator=locator or (f"manifest:{run_id}" if digest else ""),
        # Presence is decided by the projector: a sealed manifest attests to its `authority/*`
        # files, not to itself, so the ladder cannot derive it from a path.
        attestation_present=artifacts_present,
        source_kind="sealed-measurement",
        extra={"attestations": sorted(atts)},
    )


def grade(manifest: dict, *, artifacts_present: bool) -> tuple[str, str, list[str]]:
    """Kept as a thin shim over the single ladder in `claim_tuple`.

    This function used to carry its OWN copy of the constitution's rule, and on 2026-08-10 it was
    caught disagreeing with `measurement_record.grade()` on the same input (Judged/Located vs
    Judged/T0 for a protocol-less, attestation-less record). Two implementations of one rule become
    two dialects of it; the divergence then shows up as unexplainable grade differences between
    corpora. Delegating is the fix, and this docstring is the reason it must stay delegated.
    """
    return _grade(project(manifest, artifacts_present=artifacts_present))


def _artifacts_present(manifest_path: Path, manifest: dict) -> bool:
    authority = manifest.get("authority")
    if not isinstance(authority, dict) or not authority:
        return False
    base = manifest_path.parent
    return all((base / "authority" / name).is_file() or (base / name).is_file()
               for name in authority)


def frames_for_manifest(manifest_path: Path, *, as_of: str) -> list[dict]:
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(manifest, dict) or not is_sealed(manifest):
        return []

    # Identity from the path RELATIVE TO the artifacts root, not the basename. Basenames collide
    # hard here: `sealed_package` names two different runs and `input` names three different ARMS
    # of one run, so a basename key merged distinct measurements into one claim -- the fake-identity
    # failure this substrate exists to detect, produced by its own adapter.
    try:
        rel_dir = manifest_path.parent.relative_to(RESEARCH_ROOT / "artifacts")
    except ValueError:
        rel_dir = manifest_path.parent
    run_id = str(rel_dir)
    ident = re.sub(r"[^a-z0-9]+", "_", run_id.lower()).strip("_")
    source_id = f"src_seal_{ident}"
    claim_id = f"clm_seal_{ident}"
    q, t, reasons = grade(manifest, artifacts_present=_artifacts_present(manifest_path, manifest))
    atts = attestations(manifest)

    scope = manifest.get("scope") or manifest.get("conversion_policy") or ""
    claim_text = (
        f"Sealed measurement run {run_id}: {manifest.get('status')} under "
        f"{protocol_id(manifest)}"
        + (f"; scope: {str(scope)[:120]}" if scope else "")
    )

    rel = str(manifest_path)
    return [
        make_frame(
            frame_type=FT_SOURCE,
            assertion={
                "source_id": source_id,
                "locator": rel,
                "source_kind": "sealed-measurement",
                "title": run_id,
                "revision_observed": sealed_at(manifest),
            },
            provenance={"method": ADAPTER_ID, "about": run_id, "retrofit": False},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
        make_frame(
            frame_type=FT_CLAIM,
            assertion={"claim_id": claim_id, "display_text": claim_text,
                       "source_id": source_id},
            provenance={"method": ADAPTER_ID, "derived_from": source_id, "about": run_id},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
        make_frame(
            frame_type=FT_SUPPORT,
            assertion={
                "claim_id": claim_id,
                "evidence_id": f"evd_seal_{ident}",
                "grade": {"Q": q, "T": t},
                "source_id": source_id,
                "protocol_id": protocol_id(manifest),
                "reps": reps(manifest),
                "attestation_count": len(atts),
            },
            provenance={"evidence": f"evd_seal_{ident}", "about": claim_id,
                        "method": ADAPTER_ID, "grade_reasons": reasons,
                        "attestations": sorted(atts)},
            actor=ADAPTER_ID, authority_scope=AUTHORITY, created_at=as_of,
        ),
    ]


def discover(root: Path = RESEARCH_ROOT, *, limit: int | None = None) -> Iterable[Path]:
    found = sorted(root.glob("artifacts/**/manifest.json"))
    return found[:limit] if limit else found
