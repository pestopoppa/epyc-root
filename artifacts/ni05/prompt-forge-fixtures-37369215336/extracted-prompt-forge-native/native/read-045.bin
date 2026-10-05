"""Stable identity helpers for autopilot actions.

These helpers are intentionally pure so runtime autopilot, dashboard
reconstruction, and offline reports cluster the same behavioral action in the
same way.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Free-text / per-trial narrative keys that describe an action but do not
# determine the deployed config. Anything that changes behavior must stay out
# of this set.
EPHEMERAL_ACTION_KEYS = frozenset({
    "description",
    "hypothesis",
    "reasoning",
    "expected_mechanism",
    # Recovery metadata describes the configuration that preceded a staged
    # candidate; it is not part of the deployed candidate's behavior.
    "_multitier_restore_preimage",
    "_multitier_restore_flags",
})


def action_signature(action: Any) -> str:
    """Stable text signature for repeat-detection across a run."""
    try:
        return json.dumps(action, sort_keys=True, default=str)
    except Exception:
        return str(action)


def canonical_action(action: Any) -> Any:
    """Drop narrative-only keys from an action mapping."""
    if not isinstance(action, dict):
        return action
    return {
        key: value
        for key, value in action.items()
        if key not in EPHEMERAL_ACTION_KEYS
    }


def config_fingerprint(action: Any) -> str:
    """Stable identity of the deployed config measured by an action."""
    basis = action_signature(canonical_action(action))
    return hashlib.sha1(basis.encode()).hexdigest()[:16]


def action_from_journal_row(row: dict[str, Any]) -> Any:
    """Extract the journaled action from a row.

    Current rows store it in ``config_snapshot``; older rows may only have the
    action JSON in ``reasoning``.
    """
    cfg = row.get("config_snapshot")
    if cfg:
        return cfg
    try:
        return json.loads(row.get("reasoning") or "{}")
    except Exception:
        return {}


def config_fingerprint_from_row(row: dict[str, Any]) -> str:
    """Config fingerprint for a journal row."""
    return config_fingerprint(action_from_journal_row(row))


# ── Served-config identity (gate-frontier re-review B1 + operator decision, 2026-09-16) ──
#
# ``config_fingerprint`` hashes the ACTION dict. For most action types that is not the
# served configuration: ``{"type": "seed_batch", "n_questions": 10}`` hashes identically
# across a month of config changes (one fingerprint covers 394 journal rows), and
# ``{"type": "prompt_mutation", "file": ..., "mutation": "targeted_fix"}`` names a request,
# not the text it produced. Clustering those as "reproductions of one config" makes
# reproduction evidence vacuous. A row identifies what was served only through:
#
# * an explicit config delta on the action — a structural experiment's ``flags`` or a
#   numeric trial's resolved ``params``; or
# * for prompt / code / GEPA mutations (operator decision 2026-09-16), the sha256 of the
#   mutated file content that was actually SERVED, recorded on the row at eval time as
#   ``eval_details.served_content = {"files": {path: sha256}}`` — never copied from a
#   stored action, so a forced re-run is identified by what it served.
#
# The regime part is the AP-55 fingerprint WITHOUT the orchestrator commit component
# (``infra_regime_digest``): an unrelated orchestrator commit must not split a cluster,
# while a kernel / model / recipe / host / evaluator change does. Everything else has NO
# identity and never counts as a reproduction. The identity lives on eval_details, never
# on the action, so ``config_fingerprint`` / ``action_signature`` (archive representative
# keys, repeat detection) are unchanged for every row, old or new.
CONFIG_IDENTIFYING_ACTION_FIELDS = {
    "structural_experiment": "flags",
    "numeric_trial": "params",
}
CONTENT_IDENTIFIED_ACTION_TYPES = frozenset({"prompt_mutation", "code_mutation", "gepa_optimize"})
SERVED_CONTENT_KEY = "served_content"
INFRA_REGIME_DIGEST_KEY = "infra_regime_digest"
_SHA256_HEX = frozenset("0123456789abcdef")


def served_content_files(value: Any) -> dict[str, str] | None:
    """Validated ``{path: sha256}`` from a served_content record, or None."""
    if not isinstance(value, dict):
        return None
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        return None
    out: dict[str, str] = {}
    for path, sha in files.items():
        if not isinstance(path, str) or not path or not isinstance(sha, str):
            return None
        digest = sha.strip().lower()
        if len(digest) != 64 or not set(digest) <= _SHA256_HEX:
            return None
        out[path] = digest
    return dict(sorted(out.items()))


def action_config_identity(
    action: Any, infra_digest: str = "", served_content: Any = None
) -> str | None:
    """Served-config identity of an action, or None when nothing identifies what was served."""
    if not isinstance(action, dict):
        return None
    action_type = str(action.get("type") or "")
    if action_type in CONTENT_IDENTIFIED_ACTION_TYPES:
        files = served_content_files(served_content)
        if files is None:
            return None
        payload = json.dumps({"served_files": sorted(files.items())}, sort_keys=True)
        base = "content:" + hashlib.sha1(payload.encode()).hexdigest()[:16]
    else:
        field = CONFIG_IDENTIFYING_ACTION_FIELDS.get(action_type)
        if field is None:
            return None
        delta = action.get(field)
        if not isinstance(delta, dict) or not delta:
            return None
        base = config_fingerprint(action)
    return f"{base}@{infra_digest}" if infra_digest else base


def row_regime_digest(row: dict[str, Any]) -> str:
    """The row's non-orchestrator AP-55 regime digest ("" when it has none)."""
    details = row.get("eval_details") if isinstance(row, dict) else None
    if isinstance(details, dict) and details.get(INFRA_REGIME_DIGEST_KEY):
        return str(details[INFRA_REGIME_DIGEST_KEY])
    fingerprint = row.get("infra_fingerprint") if isinstance(row, dict) else None
    if isinstance(fingerprint, dict) and fingerprint.get("component_digests"):
        from src.autopilot_core.infra_fingerprint import regime_digest

        return regime_digest(fingerprint)
    return ""


def row_config_identity(row: dict[str, Any]) -> str | None:
    """Served-config identity of a journal row (see ``action_config_identity``)."""
    details = row.get("eval_details") if isinstance(row, dict) else None
    served = details.get(SERVED_CONTENT_KEY) if isinstance(details, dict) else None
    return action_config_identity(action_from_journal_row(row), row_regime_digest(row), served)
