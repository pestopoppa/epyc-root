"""SC49: strict read side (plus the G1 write-side manifest contract) for the
research-intake compute-gated sweeps G1–G4 (intake-1274/1276/1277/1279).

The four sweeps specified by the 2026-08-21 Stage-2b wave emit measurements that
must land in the belief kernel BEFORE the first run — never reconstructed on read
(the DF2-4 / ``benchmarks/results`` precedent). This module is that hook:

* **G1** — the #27442 greedy long-prefill boundary sweep (``g1_27442_boundary_sweep.sh``,
  protocol ``epyc.g1_27442.boundary_sweep.v1``): per-trial prompt token count,
  prompt class, **first sampled token id**, stop reason, at five target lengths on
  the frozen-v9 CPU path. The runner writes ONE JSONL row per trial (EXACTLY the
  seven contract fields) plus ``run_manifest.json`` — the attestation. The read
  side validates the manifest self-hash, re-hashes ``trials.jsonl`` against the
  manifest's ``trials_sha256``, validates every row, and only then projects.
* **G2** — the redesigned DF2-5 concurrency grid: per-slot acceptance, mean
  accepted length, drafter arm, ``--kv-unified`` state.
* **G3** — the MI210 quantized-KV verify probe: which FA kernel the verify batch
  lands in, at each ``draft_max``.
* **G4** — post-restore prompt-reuse rate per migration.

Doctrine, following the strict-reader family (SC19 / SC37 / SC21 / SC45):

* **Project, never grade.** Each projection is registered under the shared
  registry; ``claim_tuple.grade()`` decides. No new grading rule anywhere.
* **The caveats are load-bearing and ride IN every tuple, verbatim and enforced.**
  (a) G1 is a CORRECTNESS observation, not a throughput claim; (b) the
  repeated-pangram arm is a NEGATIVE CONTROL whose result must never be projected
  as a model-quality claim — the reader REFUSES any row that omits ``prompt_class``
  and the claim states the class's clause verbatim, so no tuple can be emitted
  without it; (c) G2's acceptance ratio is NOT comparable across
  ``--spec-draft-n-max`` values — a G2 row lacking ``n_max`` is refused, and every
  G2 tuple carries ``n_max`` and the mean accepted length together.
* **Direction is recorded, never invented.** Token ids, stop reasons and kernel
  names have no polarity, and ``ClaimTuple`` has no direction-less path (its
  validator rejects anything outside ``higher_better``/``lower_better``), so the
  house precedent applies (contention_gate / contention_matrix): the tuple's
  metric/value pair is the quantity whose polarity the PRODUCER's own gate
  declares — G1 ``first_sampled_token_is_eog`` with the class-gated meaning of
  higher (exposure signal on the meaningful arm, degenerate-input behaviour on
  the filler arm) stated in the claim; G3's kernel selection is a categorical
  observation whose direction label is nominal, stated as such in the claim.
* **Attestation is collect-time and the level is honest.** The G1 artifact is the
  run directory (manifest + trials bound by ``trials_sha256``). When the run sits
  inside a git tree whose HEAD equals the recorded ``research_commit`` the
  artifact is pin-verifiable (``Witnessed/Attested``); out-of-tree or off-pin is
  honest ``Witnessed/Anchored``. A recomputed hash that disagrees with the
  recorded one is tampering, not decay: the whole run is refused (fail closed).
  G2–G4 runners do not exist yet; their rows carry a locator only (no manifest
  contract), so those tuples honestly land at ``Witnessed/Anchored`` until their
  manifests are defined — the G1 manifest is the template.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.research_sweeps/v1"
AUTHORITY = "measurement"

# ── G1: #27442 boundary sweep ────────────────────────────────────────────────
G1_MANIFEST_SCHEMA = "epyc.g1_27442.run_manifest.v1"
G1_PROTOCOL_ID = "epyc.g1_27442.boundary_sweep.v1"
G1_SOURCE_KIND = "g1-boundary-sweep-measurement"
G1_TRIAL_FILE = "trials.jsonl"
G1_TRIAL_FIELDS = frozenset({
    "prompt_length_target", "prompt_length_actual", "prompt_class",
    "first_sampled_token_id", "stop_reason", "seed", "trial_ts_utc",
})
PROMPT_CLASSES = frozenset({"pangram", "meaningful"})
STOP_REASONS = frozenset({"eog", "completed"})

CORRECTNESS_CAVEAT = (
    "CORRECTNESS OBSERVATION, not a throughput claim: this trial records which token "
    "the model sampled FIRST after a cold full prefill with cache_prompt=false; it says "
    "nothing about speed, throughput, or latency."
)
NEGATIVE_CONTROL_CAVEAT = (
    "NEGATIVE CONTROL: this trial used a repeated-pangram filler prompt; its result is "
    "degenerate-input behaviour and must never be projected as a model-quality claim."
)

# ── G2: DF2-5 concurrency grid ────────────────────────────────────────────────
G2_SCHEMA = "epyc.g2_df25_draft_grid.v1"
G2_SOURCE_KIND = "g2-df25-draft-grid-measurement"
G2_CAVEAT = (
    "Draft acceptance is NOT comparable across --spec-draft-n-max values; this tuple "
    "carries n_max and the mean accepted length together, so the number is only "
    "interpretable at the recorded n_max."
)
G2_CATEGORIES = frozenset({"BASELINE", "CANDIDATE"})

# ── G3: MI210 quantized-KV verify probe ───────────────────────────────────────
G3_SCHEMA = "epyc.g3_miqk_fa_kernel_probe.v1"
G3_SOURCE_KIND = "g3-miqk-fa-kernel-measurement"

# ── G4: post-restore prompt-reuse rate ────────────────────────────────────────
G4_SCHEMA = "epyc.g4_prompt_reuse_rate.v1"
G4_SOURCE_KIND = "g4-prompt-reuse-measurement"

SWEEP_SCHEMAS = frozenset({G2_SCHEMA, G3_SCHEMA, G4_SCHEMA})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


class CaptureError(ValueError):
    """The G1 write contract was asked for a manifest the run did not produce."""


# ── shared vocabulary helpers (one definition of well-formed) ────────────────


def content_hash(value: Any) -> str:
    """Canonical sha256 — the exact form the G1 runner mirrors byte-for-byte.

    ``json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`` with
    no trailing newline; the manifest file BYTES are this string, so the file
    digest and the self-hash are the same number (the eval-tower-band precedent).
    """
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(directory: Path) -> str | None:
    """HEAD of the git tree containing ``directory``, else None (no exceptions)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    head = out.stdout.strip()
    return head if _SHA256.match(head) else None


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _pos_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 1


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) \
        and math.isfinite(value)


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


# ── G1: validation (shared by the write contract and the reader) ─────────────


def validate_trial(row: Any) -> list[str]:
    """Every structural problem in one G1 trial row. Empty list == producer-authored.

    The SC49 contract: a row carries EXACTLY these seven fields — no more, no
    fewer — so a row that omits ``prompt_class`` (or anything else) is refused,
    which is how "refuse a projection that omits it" is enforced.
    """
    if not isinstance(row, dict):
        return ["trial row is not a JSON object"]
    p: list[str] = []
    extra = set(row) - G1_TRIAL_FIELDS
    if extra:
        p.append(f"trial row carries non-contract fields: {sorted(extra)}")
    missing = G1_TRIAL_FIELDS - set(row)
    if missing:
        p.append(f"trial row omits contract fields: {sorted(missing)}")
    if not _pos_int(row.get("prompt_length_target")):
        p.append("prompt_length_target must be a positive integer")
    if not _pos_int(row.get("prompt_length_actual")):
        p.append("prompt_length_actual must be a positive integer")
    if row.get("prompt_class") not in PROMPT_CLASSES:
        p.append(f"prompt_class must be one of {sorted(PROMPT_CLASSES)}")
    fid = row.get("first_sampled_token_id")
    if fid is not None and not _nonneg_int(fid):
        p.append("first_sampled_token_id must be a non-negative integer or null")
    if row.get("stop_reason") not in STOP_REASONS:
        p.append(f"stop_reason must be one of {sorted(STOP_REASONS)}")
    if not _nonneg_int(row.get("seed")):
        p.append("seed must be a non-negative integer")
    if not _utc_timestamp(row.get("trial_ts_utc")):
        p.append("trial_ts_utc must be a UTC timestamp")
    return p


def validate_manifest(manifest: Any) -> list[str]:
    """Every structural problem in one G1 run manifest. Empty list == well-formed."""
    if not isinstance(manifest, dict):
        return ["run_manifest.json is not a JSON object"]
    p: list[str] = []
    if manifest.get("schema") != G1_MANIFEST_SCHEMA:
        p.append(f"schema must be {G1_MANIFEST_SCHEMA!r}")
    if manifest.get("protocol_id") != G1_PROTOCOL_ID:
        p.append(f"protocol_id must be {G1_PROTOCOL_ID!r}")
    for key in ("binary_path", "model_path", "date"):
        if not _text(manifest.get(key)):
            p.append(f"{key} must be a non-empty string")
    for key in ("binary_sha256", "model_sha256", "trials_sha256", "manifest_sha256"):
        if not _SHA256.match(str(manifest.get(key, ""))):
            p.append(f"{key} must be a 64-hex digest")
    if not _SHA1.match(str(manifest.get("research_commit", ""))):
        p.append("research_commit must be a 40-hex git revision (the pin)")
    launch = manifest.get("launch")
    if not isinstance(launch, dict):
        p.append("launch must be an object (the effective protocol flags)")
    else:
        if launch.get("n_predict") != 1:
            p.append("launch.n_predict must be 1 (the sweep samples ONE token per trial)")
        if launch.get("temp") != 0:
            p.append("launch.temp must be 0 (greedy, the G1 protocol)")
        if launch.get("cache_prompt") is not False:
            p.append("launch.cache_prompt must be false (cold prefill, the G1 protocol)")
        if launch.get("n_parallel") != 1:
            p.append("launch.n_parallel must be 1 (the G1 protocol)")
        if launch.get("conversation_mode") is not False:
            p.append("launch.conversation_mode must be false (raw prompt, no chat template)")
    if manifest.get("trials_file") != G1_TRIAL_FILE:
        p.append(f"trials_file must be {G1_TRIAL_FILE!r}")
    sha = str(manifest.get("manifest_sha256", ""))
    if _SHA256.match(sha):
        try:
            if content_hash({k: v for k, v in manifest.items()
                             if k != "manifest_sha256"}) != sha:
                p.append("manifest_sha256 does not bind the manifest content "
                         "(tampered or non-canonical serialization)")
        except (ValueError, TypeError):
            p.append("manifest content is not canonically hashable")
    return p


def validate_sweep_row(row: Any) -> list[str]:
    """Structural problems in a G2/G3/G4 native row (schema-tagged)."""
    if not isinstance(row, dict):
        return ["sweep row is not a JSON object"]
    schema = row.get("schema")
    p: list[str] = []
    if schema not in SWEEP_SCHEMAS:
        p.append(f"schema must be one of {sorted(SWEEP_SCHEMAS)}")
        return p
    if not _text(row.get("run_id")):
        p.append("run_id must be a non-empty string")
    if not _utc_timestamp(row.get("trial_ts_utc")):
        p.append("trial_ts_utc must be a UTC timestamp")
    if schema == G2_SCHEMA:
        if not _pos_int(row.get("n_max")):
            # Load-bearing: acceptance is not comparable across n_max, so a row
            # lacking it is uninterpretable and is refused (SC49 clause).
            p.append("n_max (--spec-draft-n-max) is REQUIRED for a G2 row — acceptance "
                     "is not comparable without it")
        if not _nonneg_int(row.get("slot_index")):
            p.append("slot_index must be a non-negative integer")
        if not _text(row.get("drafter_arm")):
            p.append("drafter_arm must be a non-empty string")
        if not isinstance(row.get("kv_unified"), bool):
            p.append("kv_unified must be a boolean (the --kv-unified state)")
        if not isinstance(row.get("accepted"), bool):
            p.append("accepted must be a boolean (per-slot acceptance)")
        if not _finite(row.get("mean_accepted_length")):
            p.append("mean_accepted_length must be a finite number")
        elif row["mean_accepted_length"] < 0:
            p.append("mean_accepted_length must be >= 0")
    elif schema == G3_SCHEMA:
        if not _nonneg_int(row.get("draft_max")):
            p.append("draft_max must be a non-negative integer")
        if not _text(row.get("selected_fa_kernel")):
            p.append("selected_fa_kernel must be a non-empty string")
    elif schema == G4_SCHEMA:
        if not _text(row.get("migration_id")):
            p.append("migration_id must be a non-empty string")
        if not _finite(row.get("reuse_fraction")):
            p.append("reuse_fraction must be a finite number")
        elif not 0.0 <= row["reuse_fraction"] <= 1.0:
            p.append("reuse_fraction must lie in [0, 1] (a fraction)")
    return p


# ── G1 read side ─────────────────────────────────────────────────────────────


def _load_run(run_dir: Path) -> tuple[dict, list[dict]] | None:
    """(manifest, trial rows) for one run directory, or None when inadmissible."""
    manifest_path = run_dir / "run_manifest.json"
    trials_path = run_dir / G1_TRIAL_FILE
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if validate_manifest(manifest):
        return None
    if not trials_path.is_file():
        return None
    try:
        recomputed = _file_sha256(trials_path)
    except OSError:
        return None
    if recomputed != manifest["trials_sha256"]:
        return None
    rows: list[dict] = []
    try:
        lines = trials_path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if validate_trial(row):
            return None
        rows.append(row)
    if not rows:
        return None
    return manifest, rows


def refusal_reason(run_dir: str | Path) -> str | None:
    """Why a run directory yields zero rows: ``"no emissions"`` / ``"malformed: ..."`` /
    ``"tampered: ..."``, else None."""
    path = Path(run_dir)
    manifest_path = path / "run_manifest.json"
    trials_path = path / G1_TRIAL_FILE
    if not path.is_dir():
        return "no emissions"
    if not manifest_path.is_file():
        return "no emissions"  # the manifest is written only when the run is complete
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return f"malformed: unreadable run_manifest.json ({exc})"
    problems = validate_manifest(manifest)
    if any("manifest_sha256 does not bind" in p for p in problems):
        return ("tampered: run_manifest.json no longer matches its own manifest_sha256 "
                "(the attestation the adapter sha256s) — fail closed, zero rows")
    if problems:
        return "malformed: " + "; ".join(problems)
    if not trials_path.is_file():
        return "malformed: attested trials file missing — the run is incomplete"
    try:
        recomputed = _file_sha256(trials_path)
    except OSError as exc:
        return f"malformed: unreadable trials.jsonl ({exc})"
    if recomputed != manifest["trials_sha256"]:
        return (f"tampered: trials.jsonl no longer matches the manifest's trials_sha256 "
                f"(recorded {manifest['trials_sha256'][:12]}…, recomputed {recomputed[:12]}…) "
                "— fail closed, zero rows")
    for lineno, line in enumerate(trials_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            return f"malformed: non-JSON line {lineno} ({exc})"
        row_problems = validate_trial(row)
        if row_problems:
            return f"malformed: line {lineno}: " + "; ".join(row_problems)
    return None


def native_rows(run_dir: str | Path) -> tuple[dict, ...]:
    """Admissible G1 trial rows from one run directory. Missing/incomplete/tampered
    -> zero rows (fail closed: the run is ONE artifact, not N files)."""
    path = Path(run_dir)
    loaded = _load_run(path)
    if loaded is None:
        return ()
    manifest, rows = loaded
    run_name = path.name
    pinned = False
    head = _git_head(path)
    if head is not None and head == manifest.get("research_commit"):
        pinned = True
    trials_path = path / G1_TRIAL_FILE
    trials_sha = _file_sha256(trials_path)
    manifest_sha = _file_sha256(path / "run_manifest.json")
    return tuple({
        "run_dir": str(path),
        "run_name": run_name,
        "manifest": manifest,
        "row": row,
        "trial_index": index,
        "manifest_sha256_recomputed": manifest_sha,
        "trials_sha256_recomputed": trials_sha,
        "git_pinned": pinned,
    } for index, row in enumerate(rows))


def _g1_claim(*, row: dict, run_name: str, git_pinned: bool) -> str:
    target = row["prompt_length_target"]
    actual = row["prompt_length_actual"]
    cls = row["prompt_class"]
    fid = row["first_sampled_token_id"]
    stop = row["stop_reason"]
    seed = row["seed"]
    parts = [
        f"G1 #27442 boundary trial {run_name} ({cls} arm, seed {seed}): at target "
        f"{target} prompt tokens the frozen-v9 CPU path cold-prefilled {actual} tokens "
        f"and the first sampled token id was {fid if fid is not None else 'null (extraction failed)'} "
        f"(stop_reason {stop}).",
        f"first_sampled_token_is_eog={str(stop == 'eog').lower()} — on the meaningful "
        "arm this is the exposure signal the gate escalates on (valid EOS as first "
        "token after a cold long prefill); the direction label is recorded from that "
        "gate, never inferred.",
        CORRECTNESS_CAVEAT,
    ]
    if cls == "pangram":
        parts.append(NEGATIVE_CONTROL_CAVEAT)
    if not git_pinned:
        parts.append("Attestation: run directory is out-of-tree or off-pin — "
                     "re-derivable, not pinned (Witnessed/Anchored).")
    return " ".join(parts)


@register(G1_SOURCE_KIND)
def project_g1(native: Any) -> ClaimTuple:
    """Projection only. One claim per trial; the run directory is the artifact."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("G1 native row must retain the trial row")
    row = native["row"]
    problems = validate_trial(row)
    if problems:
        raise ProjectionError("G1 trial row is not a producer-authored SC49 row: "
                              + "; ".join(problems))
    manifest = native.get("manifest")
    if validate_manifest(manifest):
        raise ProjectionError("G1 native row must retain a valid run manifest "
                              "(callers cannot bypass native_rows)")
    run_name = str(native.get("run_name") or "")
    if not run_name:
        raise ProjectionError("G1 native row must retain the run name "
                              "(callers cannot bypass native_rows)")
    pinned = bool(native.get("git_pinned"))
    cls = row["prompt_class"]
    return ClaimTuple(
        measurement_id=f"g1_{run_name}_{row['prompt_length_target']}_{cls}",
        metric="first_sampled_token_is_eog",
        value=row["stop_reason"] == "eog",
        date=str(row["trial_ts_utc"])[:10],
        # The sweep OBSERVES the frozen production kernel's actual first-token
        # behaviour — the baseline the gate reads, never a proposal under test.
        category="BASELINE",
        claim=_g1_claim(row=row, run_name=run_name, git_pinned=pinned),
        # Polarity of the producer's own gate (exposure on meaningful, degenerate
        # input on filler) — stated per class in the claim, never inferred.
        metric_direction="higher_better",
        protocol_id=G1_PROTOCOL_ID,
        reps=1,
        reps_basis="trials (one cold greedy run per target×class cell)",
        unit="eog_first_bool",
        attestation_path=str(Path(str(native.get("run_dir", ""))) / "run_manifest.json"),
        # The manifest is the attestation the adapter sha256s; the recorded
        # self-hash equals the recomputed file digest by canonical serialization.
        attestation_sha256=manifest["manifest_sha256"],
        attestation_locator=(
            f"g1-27442:{run_name}:{row['prompt_length_target']}:{cls}:"
            f"{row['trial_ts_utc']}"),
        # Presence/pin decided here, not by the ladder's containment root: in-git
        # at the recorded research_commit -> True (Attested), else honest Anchored.
        attestation_present=pinned,
        source_kind=G1_SOURCE_KIND,
        extra={
            "schema": G1_MANIFEST_SCHEMA,
            "protocol_id": G1_PROTOCOL_ID,
            "run_dir": str(native.get("run_dir", "")),
            "run_name": run_name,
            "trial_index": native.get("trial_index"),
            "prompt_length_target": row["prompt_length_target"],
            "prompt_length_actual": row["prompt_length_actual"],
            "prompt_class": cls,
            "first_sampled_token_id": row["first_sampled_token_id"],
            "stop_reason": row["stop_reason"],
            "seed": row["seed"],
            "trial_ts_utc": row["trial_ts_utc"],
            "launch": manifest.get("launch"),
            "binary_path": manifest.get("binary_path"),
            "binary_sha256": manifest.get("binary_sha256"),
            "model_path": manifest.get("model_path"),
            "model_sha256": manifest.get("model_sha256"),
            "research_commit": manifest.get("research_commit"),
            "manifest_sha256": manifest["manifest_sha256"],
            "manifest_sha256_recomputed": native.get("manifest_sha256_recomputed"),
            "trials_sha256_recomputed": native.get("trials_sha256_recomputed"),
            "git_pinned": pinned,
            "correctness_caveat": CORRECTNESS_CAVEAT,
            "negative_control_caveat": NEGATIVE_CONTROL_CAVEAT,
        },
    )


def frames_for_run_dir(run_dir: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (``claim_tuple.to_frames``)."""
    frames: list[dict] = []
    for native in native_rows(run_dir):
        frames.extend(to_frames(project_g1(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


# ── G2/G3/G4 read side (their runners' rows; no manifest contract yet) ───────


def _load_sweep_file(path: Path) -> list[dict] | None:
    if not path.is_file():
        return None
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    rows: list[dict] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return None
        if validate_sweep_row(row):
            return None
        rows.append(row)
    return rows or None


def native_rows_file(jsonl_path: str | Path) -> tuple[dict, ...]:
    """Admissible G2/G3/G4 native rows from one schema-tagged JSONL file.
    Missing/empty/malformed -> zero rows."""
    path = Path(jsonl_path)
    rows = _load_sweep_file(path)
    if not rows:
        return ()
    return tuple({
        "row": row,
        "row_path": str(path),
        "row_index": index,
    } for index, row in enumerate(rows))


def refusal_reason_file(jsonl_path: str | Path) -> str | None:
    """Why a G2/G3/G4 JSONL file yields zero rows, else None."""
    path = Path(jsonl_path)
    if not path.is_file():
        return "no emissions"
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return f"malformed: unreadable file ({exc})"
    if not any(line.strip() for line in lines):
        return "no emissions"
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            return f"malformed: non-JSON line {lineno} ({exc})"
        problems = validate_sweep_row(row)
        if problems:
            return f"malformed: line {lineno}: " + "; ".join(problems)
    return None


def _sweep_claim(row: dict) -> str:
    schema = row["schema"]
    if schema == G2_SCHEMA:
        return (
            f"DF2-5 draft-grid slot {row['slot_index']} of run {row['run_id']}: "
            f"drafter arm {row['drafter_arm']!r}, --kv-unified={str(row['kv_unified']).lower()}, "
            f"--spec-draft-n-max={row['n_max']}, accepted={str(row['accepted']).lower()}, "
            f"mean accepted length {row['mean_accepted_length']:.3f}. {G2_CAVEAT}"
        )
    if schema == G3_SCHEMA:
        return (
            f"MI210 quantized-KV verify probe, run {row['run_id']}: at draft_max="
            f"{row['draft_max']} the verify batch selected the FA kernel "
            f"{row['selected_fa_kernel']!r}. Categorical selection observation — the "
            "metric direction label is nominal (recorded, never used for ranking); "
            "the probe's verify question is WHICH kernel executes, not how well."
        )
    return (
        f"Post-restore prompt-reuse probe, run {row['run_id']}, migration "
        f"{row['migration_id']!r}: prompt reuse fraction {row['reuse_fraction']:.4f} "
        "of prefilled tokens (reuse preserved across the restore is the goal of the "
        "dynamic-stack migration; higher is better)."
    )


@register(G2_SOURCE_KIND)
def project_g2(native: Any) -> ClaimTuple:
    """Projection only. One claim per SLOT — a slot observation is one witness."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("G2 native row must retain the slot row")
    row = native["row"]
    problems = validate_sweep_row(row)
    if problems:
        raise ProjectionError("G2 slot row is not a producer-authored DF2-5 row: "
                              + "; ".join(problems))
    if row.get("schema") != G2_SCHEMA:
        raise ProjectionError(f"project_g2 only projects {G2_SCHEMA!r} rows")
    # Arm rule: the DF2-5 baseline arm IS the reference the candidate arms are
    # measured against, so a baseline drafter arm is BASELINE and any other arm
    # is CANDIDATE (the pareval arm-rule precedent).
    category = "BASELINE" if row["drafter_arm"] == "baseline" else "CANDIDATE"
    return ClaimTuple(
        measurement_id=f"g2_{row['run_id']}_slot{row['slot_index']}",
        metric="mean_accepted_length",
        value=row["mean_accepted_length"],
        date=str(row["trial_ts_utc"])[:10],
        category=category,
        claim=_sweep_claim(row),
        # Longer accepted draft runs are the campaign's declared polarity; the
        # n_max caveat in the claim keeps the number from being compared across
        # --spec-draft-n-max values (SC49 clause, enforced by validate_sweep_row).
        metric_direction="higher_better",
        protocol_id=G2_SCHEMA,
        reps=1,
        reps_basis="slots (one slot observation per row)",
        unit="tokens",
        attestation_path="",
        attestation_sha256="",
        attestation_locator=str(native.get("row_path", "")),
        attestation_present=False,
        source_kind=G2_SOURCE_KIND,
        extra={
            "schema": G2_SCHEMA,
            "run_id": row["run_id"],
            "slot_index": row["slot_index"],
            "drafter_arm": row["drafter_arm"],
            "n_max": row["n_max"],
            "kv_unified": row["kv_unified"],
            "accepted": row["accepted"],
            "mean_accepted_length": row["mean_accepted_length"],
            "trial_ts_utc": row["trial_ts_utc"],
            "row_path": native.get("row_path"),
            "row_index": native.get("row_index"),
            "caveat": G2_CAVEAT,
        },
    )


@register(G3_SOURCE_KIND)
def project_g3(native: Any) -> ClaimTuple:
    """Projection only. One claim per (run, draft_max) selection observation."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("G3 native row must retain the probe row")
    row = native["row"]
    problems = validate_sweep_row(row)
    if problems:
        raise ProjectionError("G3 probe row is not a producer-authored MI210 probe row: "
                              + "; ".join(problems))
    if row.get("schema") != G3_SCHEMA:
        raise ProjectionError(f"project_g3 only projects {G3_SCHEMA!r} rows")
    return ClaimTuple(
        measurement_id=f"g3_{row['run_id']}_dm{row['draft_max']}",
        metric="selected_fa_kernel",
        value=row["selected_fa_kernel"],
        date=str(row["trial_ts_utc"])[:10],
        category="BASELINE",
        claim=_sweep_claim(row),
        # No polarity exists on a kernel name; the label is recorded nominally and
        # the claim says so (the contention_gate precedent for categorical verdicts).
        metric_direction="higher_better",
        protocol_id=G3_SCHEMA,
        reps=1,
        reps_basis="probes (one kernel-selection observation per draft_max)",
        unit="kernel_name",
        attestation_path="",
        attestation_sha256="",
        attestation_locator=str(native.get("row_path", "")),
        attestation_present=False,
        source_kind=G3_SOURCE_KIND,
        extra={
            "schema": G3_SCHEMA,
            "run_id": row["run_id"],
            "draft_max": row["draft_max"],
            "selected_fa_kernel": row["selected_fa_kernel"],
            "trial_ts_utc": row["trial_ts_utc"],
            "row_path": native.get("row_path"),
            "row_index": native.get("row_index"),
            "direction_note": "nominal label, never a ranking",
        },
    )


@register(G4_SOURCE_KIND)
def project_g4(native: Any) -> ClaimTuple:
    """Projection only. One claim per migration."""
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("G4 native row must retain the reuse row")
    row = native["row"]
    problems = validate_sweep_row(row)
    if problems:
        raise ProjectionError("G4 reuse row is not a producer-authored reuse row: "
                              + "; ".join(problems))
    if row.get("schema") != G4_SCHEMA:
        raise ProjectionError(f"project_g4 only projects {G4_SCHEMA!r} rows")
    return ClaimTuple(
        measurement_id=f"g4_{row['run_id']}_{row['migration_id']}",
        metric="prompt_reuse_fraction",
        value=row["reuse_fraction"],
        date=str(row["trial_ts_utc"])[:10],
        category="BASELINE",
        claim=_sweep_claim(row),
        metric_direction="higher_better",
        protocol_id=G4_SCHEMA,
        reps=1,
        reps_basis="migrations (one reuse observation per migration)",
        unit="fraction_0_1",
        attestation_path="",
        attestation_sha256="",
        attestation_locator=str(native.get("row_path", "")),
        attestation_present=False,
        source_kind=G4_SOURCE_KIND,
        extra={
            "schema": G4_SCHEMA,
            "run_id": row["run_id"],
            "migration_id": row["migration_id"],
            "reuse_fraction": row["reuse_fraction"],
            "trial_ts_utc": row["trial_ts_utc"],
            "row_path": native.get("row_path"),
            "row_index": native.get("row_index"),
        },
    )


def frames_for_sweep_file(jsonl_path: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission for G2/G3/G4 JSONL files (shared carrier)."""
    frames: list[dict] = []
    for native in native_rows_file(jsonl_path):
        schema = native["row"]["schema"]
        if schema == G2_SCHEMA:
            tup = project_g2(native)
        elif schema == G3_SCHEMA:
            tup = project_g3(native)
        else:
            tup = project_g4(native)
        frames.extend(to_frames(tup, as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


# ── the G1 write-side manifest contract (mirrored byte-for-byte by the runner) ─


def build_run_manifest(
    run_dir: str | Path,
    *,
    trials_sha256: str,
    binary_path: str,
    binary_sha256: str,
    model_path: str,
    model_sha256: str,
    research_commit: str,
    launch: dict[str, Any],
    date: str | None = None,
    protocol_id: str = G1_PROTOCOL_ID,
) -> Path:
    """Emit ``run_manifest.json`` for a completed G1 run — the SC49 write contract.

    The runner calls this AFTER the last trial (or mirrors the canonical form
    exactly: ``json.dumps(sort_keys, separators=(",", ":"), ensure_ascii=False)``,
    no trailing newline — the file bytes ARE the content hash, so the self-hash
    and the collect-time file digest are the same number). Refuses to emit when
    the trials file is missing or the digests are not 64-hex.
    """
    out = Path(run_dir)
    if not out.is_dir():
        raise CaptureError(f"run directory missing: {out}")
    trials_path = out / G1_TRIAL_FILE
    if not trials_path.is_file():
        raise CaptureError(f"no {G1_TRIAL_FILE} at {out} — call this AFTER the trials")
    if not _SHA256.match(trials_sha256):
        raise CaptureError("trials_sha256 must be a 64-hex digest over trials.jsonl")
    for label, digest in (("binary_sha256", binary_sha256), ("model_sha256", model_sha256)):
        if not _SHA256.match(digest):
            raise CaptureError(f"{label} must be a 64-hex digest")
    if not _SHA1.match(research_commit):
        raise CaptureError("research_commit must be a 40-hex git revision")
    if not isinstance(launch, dict) or launch.get("n_predict") != 1 \
            or launch.get("temp") != 0 or launch.get("cache_prompt") is not False:
        raise CaptureError("launch must declare the G1 protocol (n_predict=1, temp=0, "
                           "cache_prompt=false) — the manifest attests what ran")
    manifest = {
        "schema": G1_MANIFEST_SCHEMA,
        "protocol_id": protocol_id,
        "date": date or datetime.now(timezone.utc).strftime("%Y%m%dT%H%MZ"),
        "binary_path": binary_path,
        "binary_sha256": binary_sha256,
        "model_path": model_path,
        "model_sha256": model_sha256,
        "research_commit": research_commit,
        "launch": launch,
        "trials_file": G1_TRIAL_FILE,
        "trials_sha256": trials_sha256,
    }
    manifest["manifest_sha256"] = content_hash(
        {k: v for k, v in manifest.items() if k != "manifest_sha256"})
    problems = validate_manifest(manifest)
    if problems:
        raise CaptureError("refusing to emit an invalid run manifest: "
                           + "; ".join(problems))
    tmp = out / "run_manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False), encoding="utf-8")
    tmp.replace(out / "run_manifest.json")
    return out / "run_manifest.json"


__all__ = [
    "ADAPTER_ID", "AUTHORITY",
    "G1_MANIFEST_SCHEMA", "G1_PROTOCOL_ID", "G1_SOURCE_KIND", "G1_TRIAL_FILE",
    "G1_TRIAL_FIELDS", "PROMPT_CLASSES", "STOP_REASONS",
    "CORRECTNESS_CAVEAT", "NEGATIVE_CONTROL_CAVEAT",
    "G2_SCHEMA", "G2_SOURCE_KIND", "G2_CAVEAT",
    "G3_SCHEMA", "G3_SOURCE_KIND", "G4_SCHEMA", "G4_SOURCE_KIND",
    "CaptureError", "content_hash", "validate_trial", "validate_manifest",
    "validate_sweep_row", "refusal_reason", "native_rows", "project_g1",
    "frames_for_run_dir", "native_rows_file", "refusal_reason_file",
    "project_g2", "project_g3", "project_g4", "frames_for_sweep_file",
    "build_run_manifest",
]
