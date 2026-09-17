#!/bin/bash
# ratify_v10_episodic_repin_20260917.sh — re-pin the v10 production checkpoint's episodic-memory
# hashes after the operator-approved eval-leak memory purge of 2026-09-17.
#
#   Review (default, writes nothing):  bash scripts/operator/ratify_v10_episodic_repin_20260917.sh
#   Apply + receipts (no commit):      bash scripts/operator/ratify_v10_episodic_repin_20260917.sh --apply
#   Post-state check (read-only):      bash scripts/operator/ratify_v10_episodic_repin_20260917.sh --verify
#   Operator entry point:              scripts/operator/run_v10_episodic_repin_ratify_20260917.sh --operator <name>
#
# WHAT HAPPENED. epyc-orchestrator 41baad2b (scripts/maintenance/purge_eval_leak_memories_20260917.
# {sh,py}), run by the operator with --apply --include-pinned at 2026-09-17T12:16:56Z, deleted the 4
# HumanEval/55 task memories from the pinned production_best checkpoint
# orchestration/autopilot_checkpoints/multitier_v10_20260810 (memories 63925 -> 63921, FAISS
# ntotal 63925 -> 63921). Three checkpoint files changed: episodic.db, embeddings.faiss and
# id_map.npy. The purge never edits a checkpoint meta or a ratified receipt, so it wrote the new
# hashes to /mnt/raid0/llm/backups/episodic-leak-20260917/pinned_repin_proposal.json and stopped.
# Its --verify --include-live --include-pinned run (12:18:37Z) passed: the store is CLEAN and the
# index health checks pass.
#
# WHAT IS NOW FALSE. Every pin on those three files names the pre-purge bytes:
#   1. multitier_v10_20260810/checkpoint_meta.json   file_sha256[episodic.db|embeddings.faiss|
#      id_map.npy] and memory_count (63925; the v10 ratifier computes it as COUNT(*) FROM memories)
#   2. the checkpoint_sha256 derived from that meta (canonical JSON over file_sha256 plus the
#      meta file's own hash; the v10 ratifier's formula)
#   3. epyc-root artifacts/operator/ratify_multitier_baseline_v10_20260810.json
#      production_checkpoint.metadata, which mirrors 1 and carries 2.
#
# WHO CHECKS THESE PINS (grep of both repos for file_sha256 / checkpoint_sha256 / the receipt path):
#   - scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh --verify: the full v10 manifest,
#     the checkpoint_sha256 and the receipt mirror, all at ITS post-state constants. The purge has
#     already broken it (episodic.db no longer matches the manifest). It is not edited here: its
#     sha256 is attested in ratify_checkpoint_prompt_leak_20260916.receipt.json. This script's
#     --verify re-runs every check it made (rules.md 18f8ea01 in all 10 checkpoints, the leak-marker
#     scan, the full manifest, checkpoint_sha256, the receipt mirror) at the chained post-state,
#     and supersedes it as the validation command. The decision receipt records that.
#   - epyc-orchestrator purge_eval_leak_memories_20260917.py: treats a checkpoint as pinned when
#     "episodic.db" is in file_sha256 and requires file_sha256["prompts/rules.md"] == 18f8ea01.
#     Both still hold after the re-pin, so it keeps classifying v10 as pinned.
#   - epyc-orchestrator ratify_and_apply_multitier_baseline_v10.py: writes the meta and the
#     checkpoint_sha256 once, at v10 ratification; it never re-reads them. Its formula is reused.
#   - StructuralLab.restore_checkpoint() and decision_cockpit.read_checkpoint(): verify no hash.
#   - compute_ready / rtg51 / dashboard "checkpoint_sha256": a different contract (bus and
#     AutoKernel checkpoints), unrelated to this one.
#
# WHAT IT DOES
#   preflight (read-only): the v10 files equal the proposal's "after" hashes; the purge backups
#     equal its "before" hashes (and the purge's MANIFEST.json says so); the proposal and the purge
#     receipt agree with the pins, including the deleted ids and the final passing verify; the live
#     memory count is 63921; the orchestrator purge commit is merged; the prior ratification exists;
#     the re-pinned manifest describes every v10 file exactly.
#   --apply:
#   1. durable backup of checkpoint_meta.json and the v10 receipt to $BACKUP_DIR
#      (/mnt/raid0/llm/backups/v10-episodic-repin-20260917), with SHA256SUMS and README.md;
#   2. checkpoint_meta.json: the three file_sha256 entries -> the "after" hashes, memory_count ->
#      63921, plus an amendments entry (gate RATIFY-V10-EPISODIC-REPIN-20260917, kind
#      eval_leak_memory_purge); checkpoint_sha256 recomputed;
#   3. the v10 receipt: production_checkpoint.metadata mirrors the new meta and checkpoint_sha256,
#      plus a top-level amendments entry. Nothing else in it changes;
#   4. the decision receipt, its keyed index and the MEASUREMENT.md section-5 consolidated receipt.
#
# PINS. Any mismatch is refused. If a target moved, regenerate this bundle; never force it.
#   episodic.db        before 24cff0744a4e...  after 8ff84e9d1e6b...
#   embeddings.faiss   before 4537f9179b5a...  after e067815db238...
#   id_map.npy         before d6b791548b1d...  after af4098d88990...
#   v10 checkpoint_meta.json   pre  54224ec7... (the RATIFY-CKPT-PROMPT-LEAK-20260916 post-state)
#   v10 checkpoint_sha256      pre  a604276f...
#   v10 receipt                pre  e6682b2f...
#   v10 checkpoint_meta.json   post 5af445d8...
#   v10 checkpoint_sha256      post 3b457d98...
#   v10 receipt                post 10ea1184...
#   pinned_repin_proposal.json      00aecc87...
#   (full values are the constants in the Python core)
#
# SAFETY. Takes the AutoPilot singleton lock and the trust-boundary lock (non-blocking; refuses if
# AutoPilot runs). Every write is tmp+rename with the original mode kept. Any failure restores
# every original. IDEMPOTENT: at post-state with all receipts present it prints ALREADY RATIFIED
# and exits 0. Any mixed or unknown state is refused. It never touches episodic.db, the FAISS index
# or the id map (it only hashes them and opens the db read-only, immutable), starts no process,
# takes no compute and edits no tracked orchestrator file.
#
# Environment overrides (tests): ROOT (epyc-root checkout; default: the checkout holding this
# script), ORCH, ORCH_GIT (default ORCH), BACKUP_DIR, PURGE_BACKUP, TRUST_LOCK. Only when
# V10_REPIN_TEST_MODE=1: PURGE_COMMIT_OVERRIDE, V10_REPIN_FAIL_AT, V10_REPIN_EVIDENCE_REPO and
# V10_REPIN_TEST_PINS (a JSON file overriding the core's pin constants). Without it those are ignored.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
ORCH_GIT="${ORCH_GIT:-$ORCH}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/raid0/llm/backups/v10-episodic-repin-20260917}"
PURGE_BACKUP="${PURGE_BACKUP:-/mnt/raid0/llm/backups/episodic-leak-20260917}"
TRUST_LOCK="${TRUST_LOCK:-/run/lock/epyc-measurement-trust-boundary.lock}"
CKPT_ROOT="$ORCH/orchestration/autopilot_checkpoints"
AP_LOCK="$ORCH/orchestration/.autopilot.lock"
V10_REPIN_TEST_MODE="${V10_REPIN_TEST_MODE:-0}"
PURGE_COMMIT="41baad2b9e1bc86cd73c4f582c97358934bd8326"
if [ "$V10_REPIN_TEST_MODE" = "1" ]; then
  PURGE_COMMIT="${PURGE_COMMIT_OVERRIDE:-$PURGE_COMMIT}"
else
  unset V10_REPIN_TEST_PINS
fi
export ROOT ORCH ORCH_GIT BACKUP_DIR PURGE_BACKUP TRUST_LOCK CKPT_ROOT AP_LOCK V10_REPIN_TEST_MODE PURGE_COMMIT

GATE_ID="RATIFY-V10-EPISODIC-REPIN-20260917"
PRIOR_GATE="RATIFY-CKPT-PROMPT-LEAK-20260916"
PURGE_GATE="PURGE-EVAL-LEAK-MEMORIES-20260917"
V10_REL="artifacts/operator/ratify_multitier_baseline_v10_20260810.json"
RECEIPT_REL="artifacts/operator/ratify_v10_episodic_repin_20260917.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_v10_episodic_repin_20260917.receipt.json"
PRIOR_INDEX_REL="artifacts/operator/receipts/$PRIOR_GATE.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$V10_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
export GATE_ID PRIOR_GATE PURGE_GATE V10_REL RECEIPT_REL

MODE="dry-run"
case "${1:-}" in
  ""|--dry-run) MODE="dry-run" ;;
  --apply)      MODE="apply" ;;
  --verify)     MODE="verify" ;;
  *) echo "usage: $0 [--dry-run | --apply | --verify]   (default: --dry-run, writes nothing)" >&2; exit 64 ;;
esac
[ $# -le 1 ] || { echo "usage: $0 [--dry-run | --apply | --verify]" >&2; exit 64; }

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
[ -f "$ROOT/$V10_REL" ] || die "$V10_REL not found under ROOT=$ROOT"
[ -d "$CKPT_ROOT" ]     || die "checkpoint root not found: $CKPT_ROOT"
[ -d "$PURGE_BACKUP" ]  || die "purge backup directory not found: $PURGE_BACKUP"
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

TMPD="$(mktemp -d)"
export TMPD
trap 'rm -rf "$TMPD"' EXIT
CORE="$TMPD/core.py"

# ============================================================================ Python core
cat > "$CORE" <<'PYEOF'
"""Core of ratify_v10_episodic_repin_20260917.sh. Commands: state, evidence, plan, apply,
rollback, verify, pins. Reads its paths from the environment the shell exports."""
import difflib, fcntl, hashlib, json, os, shutil, sqlite3, sys
from pathlib import Path

ROOT = Path(os.environ["ROOT"])
CKPT_ROOT = Path(os.environ["CKPT_ROOT"])
BACKUP_DIR = Path(os.environ["BACKUP_DIR"])
PURGE_BACKUP = Path(os.environ["PURGE_BACKUP"])
TMPD = Path(os.environ["TMPD"])
AP_LOCK = Path(os.environ["AP_LOCK"])
TRUST_LOCK = Path(os.environ["TRUST_LOCK"])
GATE_ID = os.environ["GATE_ID"]
PRIOR_GATE = os.environ["PRIOR_GATE"]
PURGE_GATE = os.environ["PURGE_GATE"]
PURGE_COMMIT = os.environ["PURGE_COMMIT"]
V10_RECEIPT = ROOT / os.environ["V10_REL"]
DECISION_REL = os.environ["RECEIPT_REL"]

V10 = "multitier_v10_20260810"
EPI_FILES = ("episodic.db", "embeddings.faiss", "id_map.npy")
RULES_REL = "prompts/rules.md"
LEAK_MARKERS = (b"Aschoff", b"University of Bonn")

# ---- pins ------------------------------------------------------------------------------------
EPI_BEFORE = {
    "embeddings.faiss": "4537f9179b5a318da59ba4e1fc2bb709d0f13335a0ac6295e4f600f3fa09d8d3",
    "episodic.db": "24cff0744a4ea47f316f5ed8781dc35ce8e843ce555234829c21e88f4a0ffa75",
    "id_map.npy": "d6b791548b1d5c88c68a28c97e3cce8bc7f38496aa93cbb9daa98d446ceaffaf",
}
EPI_AFTER = {
    "embeddings.faiss": "e067815db2388fca7537a4d3aba7186c9186097b89ead43c14e575f4c1f06740",
    "episodic.db": "8ff84e9d1e6bc5708ecda62247c05b214789b1c9b65e14935f48d1dba0ae69f5",
    "id_map.npy": "af4098d88990d656bbb4327c08f86bf95947569ce0e15ccf9bdfcefa881ca498",
}
DELETED_IDS = [
    "500740fe-8e32-44ef-bbe5-e9c9d0d946f8",
    "9f75290f-abec-4826-b285-588cd47a2ee8",
    "d2ddc823-bd8a-4b44-809f-c4ed7593323e",
    "e344a27c-111e-4acd-b142-72cf011ba80e",
]
RULES_PIN = "18f8ea018234605002459cd98e59a9aaeddec235d8e022ff59f6ebd67766d607"
MEMCOUNT_BEFORE = 63925
MEMCOUNT_AFTER = 63921
META_PRE = "54224ec71905b7e628284262579dec1f8da59d0c9d63855fada878ec78305746"
CKSUM_PRE = "a604276fcd053e7590bd391f846334f5fd4616f7cd9ebe78196b8f6305f1d218"
RECEIPT_PRE = "e6682b2fe9cbe88d21b9f6f075a40a38a8b2dd23f40641049578f6c496dc9a03"
META_POST = "5af445d8568b08e62085ae7c68354851d36e27043efeb8cbf5760d656ce28b23"
CKSUM_POST = "3b457d981cc42907abf25f47d13d7827e6c08821ce588e2405075bcf8ea73375"
RECEIPT_POST = "10ea11843d28c3bb13d0b31ef33cc4551a28d595d7b8c20647d1bdee32623464"
PROPOSAL_SHA = "00aecc8751c1021b19f66fa7ac43ed20b8c46030000806426bbed04f493ccde2"

if os.environ.get("V10_REPIN_TEST_MODE") == "1" and os.environ.get("V10_REPIN_TEST_PINS"):
    for _k, _v in json.loads(Path(os.environ["V10_REPIN_TEST_PINS"]).read_text()).items():
        if _k not in globals() or _k.startswith("_"):
            raise SystemExit(f"unknown test pin {_k}")
        globals()[_k] = _v


def amendment():
    return {
        "date": "2026-09-17",
        "gate_id": GATE_ID,
        "kind": "eval_leak_memory_purge",
        "files": {f: {"sha256_before": EPI_BEFORE[f], "sha256_after": EPI_AFTER[f]}
                  for f in EPI_FILES},
        "memory_count_before": MEMCOUNT_BEFORE,
        "memory_count_after": MEMCOUNT_AFTER,
        "deleted_memory_ids": list(DELETED_IDS),
        "reason": ("the 4 memories whose context carried the HumanEval/55 problem text were removed "
                   "by the operator-approved eval-leak purge " + PURGE_GATE + " (epyc-orchestrator "
                   + PURGE_COMMIT[:8] + "); only those rows and their FAISS vectors changed"),
        "source_commit": PURGE_COMMIT,
        "source_script": "scripts/maintenance/purge_eval_leak_memories_20260917.py",
        "purge_backup": str(PURGE_BACKUP / backup_key()),
        "decision_receipt": DECISION_REL,
    }


class Refuse(Exception):
    pass


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_path(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(value):  # identical to ratify_and_apply_multitier_baseline_v10._canonical_hash
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def dump_json(doc):  # both files are written as indent=2, sort_keys, trailing newline
    return (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()


def regular_file(p):
    if p.is_symlink() or not p.is_file():
        raise Refuse(f"{p} is missing or not a regular file")
    return p


def v10_dir():
    return CKPT_ROOT / V10


def backup_key():
    # the purge names each backup after the store's resolved path with "/" -> "__"
    return str((v10_dir() / "episodic.db").resolve()).lstrip("/").replace("/", "__")


def checkpoint_sha(meta_raw):
    meta = json.loads(meta_raw)
    hashes = dict(meta["file_sha256"])
    hashes["checkpoint_meta.json"] = sha_bytes(meta_raw)
    return canonical_hash(hashes)


def db_memory_count(path):
    """COUNT(*) FROM memories, as the v10 ratifier computes memory_count. Read-only, immutable:
    no journal, WAL or shm file is created, and no lock is taken."""
    uri = f"file:{path}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        return int(conn.execute('SELECT COUNT(*) FROM "memories"').fetchone()[0])
    finally:
        conn.close()


def epi_on_disk():
    return {f: sha_path(regular_file(v10_dir() / f)) for f in EPI_FILES}


def verify_manifest(meta):
    """Every file in the v10 checkpoint matches `meta`'s manifest; no extra, no missing file."""
    base = v10_dir()
    listed = set(meta["file_sha256"])
    on_disk = {p.relative_to(base).as_posix() for p in base.rglob("*")
               if p.is_file() or p.is_symlink()} - {"checkpoint_meta.json"}
    if listed != on_disk:
        raise Refuse(f"v10 manifest/file-set mismatch: missing={sorted(listed - on_disk)} "
                     f"extra={sorted(on_disk - listed)}")
    if meta["file_sha256"].get(RULES_REL) != RULES_PIN:
        raise Refuse(f"v10 manifest pins rules.md {str(meta['file_sha256'].get(RULES_REL))[:12]}, "
                     f"expected {RULES_PIN[:12]} (is {PRIOR_GATE} applied?)")
    for rel, want in sorted(meta["file_sha256"].items()):
        got = sha_path(regular_file(base / rel))
        if got != want:
            raise Refuse(f"v10 checkpoint file {rel} is {got[:12]}, manifest says {want[:12]}")


def scan_prompt_copies():
    """What the prior ratify's --verify guaranteed: every checkpoint rules.md copy is at the
    patched pin and no checkpoint text copy carries a leak marker (memory stores excluded)."""
    bad = []
    for p in sorted(CKPT_ROOT.glob("*/prompts/rules.md")):
        if p.parent.parent.is_symlink():
            continue
        if sha_path(p) != RULES_PIN:
            bad.append(f"{p.relative_to(CKPT_ROOT)} is not at {RULES_PIN[:12]}")
    for p in sorted(CKPT_ROOT.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        if p.suffix in (".db", ".sqlite", ".faiss", ".npy", ".npz"):
            continue
        data = p.read_bytes()
        if any(m in data for m in LEAK_MARKERS):
            bad.append(f"leak marker in {p.relative_to(CKPT_ROOT)}")
    return bad


def state():
    """Classify the target set as pre, post, or refuse."""
    link = CKPT_ROOT / "production_best"
    if not link.is_symlink() or link.resolve() != v10_dir().resolve():
        raise Refuse(f"production_best does not resolve to {V10}")
    epi = epi_on_disk()
    meta_sha = sha_path(regular_file(v10_dir() / "checkpoint_meta.json"))
    rec_sha = sha_path(regular_file(V10_RECEIPT))
    rows = [(f"{V10}/{f}", h) for f, h in epi.items()]
    rows += [(f"{V10}/checkpoint_meta.json", meta_sha), (str(V10_RECEIPT), rec_sha)]
    detail = "\n".join(f"    {h}  {r}" for r, h in rows)
    if epi == EPI_BEFORE:
        raise Refuse("the v10 episodic files are at their PRE-purge hashes: the purge was not applied "
                     f"or was rolled back. Nothing to re-pin.\n{detail}")
    if epi != EPI_AFTER:
        raise Refuse("the v10 episodic files match neither the purge proposal's before nor its after "
                     f"hashes (drift or a later write). Regenerate the bundle.\n{detail}")
    if meta_sha == META_PRE and rec_sha == RECEIPT_PRE:
        return "pre", rows
    if meta_sha == META_POST and rec_sha == RECEIPT_POST:
        return "post", rows
    raise Refuse("checkpoint_meta.json and the v10 receipt are neither both at the pre-state pins nor "
                 "both at the post-state pins (drift, tampering or a half-applied run). Resolve by "
                 f"hand; originals, if a run started, are in {BACKUP_DIR}.\n{detail}")


def compute_post():
    """Every post-state byte string, derived in memory from the verified pre-state."""
    out = {}
    meta_path = v10_dir() / "checkpoint_meta.json"
    meta_raw = meta_path.read_bytes()
    if sha_bytes(meta_raw) != META_PRE:
        raise Refuse("checkpoint_meta.json is not at the pinned pre-state")
    if checkpoint_sha(meta_raw) != CKSUM_PRE:
        raise Refuse("v10 checkpoint_sha256 recomputed from the current meta is not the pinned pre value")
    meta = json.loads(meta_raw)
    if dump_json(meta) != meta_raw:
        raise Refuse("checkpoint_meta.json is not in canonical form; a rewrite would change more than the pins")
    fs = meta["file_sha256"]
    for f in EPI_FILES:
        if fs.get(f) != EPI_BEFORE[f]:
            raise Refuse(f"meta pins {f} as {str(fs.get(f))[:12]}, expected the pre-purge {EPI_BEFORE[f][:12]}")
    if fs.get(RULES_REL) != RULES_PIN:
        raise Refuse(f"meta pins rules.md {str(fs.get(RULES_REL))[:12]}; {PRIOR_GATE} must be applied first")
    if meta.get("memory_count") != MEMCOUNT_BEFORE:
        raise Refuse(f"meta memory_count is {meta.get('memory_count')}, expected {MEMCOUNT_BEFORE}")
    gates = [a.get("gate_id") for a in meta.get("amendments") or []]
    if GATE_ID in gates:
        raise Refuse(f"meta already carries a {GATE_ID} amendment but is at the pre-state hash")
    if not gates or gates[-1] != PRIOR_GATE:
        raise Refuse(f"meta's last amendment is {gates[-1] if gates else None}, expected {PRIOR_GATE}")
    amend = amendment()
    for f in EPI_FILES:
        fs[f] = EPI_AFTER[f]
    meta["memory_count"] = MEMCOUNT_AFTER
    meta["amendments"] = list(meta.get("amendments") or []) + [amend]
    meta_new = dump_json(meta)
    cksum_new = checkpoint_sha(meta_new)
    out[meta_path] = meta_new

    rec_raw = V10_RECEIPT.read_bytes()
    if sha_bytes(rec_raw) != RECEIPT_PRE:
        raise Refuse("the v10 receipt is not at the pinned pre-state")
    rec = json.loads(rec_raw)
    if dump_json(rec) != rec_raw:
        raise Refuse("the v10 receipt is not in canonical form; a rewrite would change more than the pins")
    pc = rec["production_checkpoint"]
    if Path(pc["path"]).name != V10:
        raise Refuse(f"v10 receipt production_checkpoint.path is {pc['path']}")
    if pc["metadata"] != {**json.loads(meta_raw), "checkpoint_sha256": CKSUM_PRE}:
        raise Refuse("v10 receipt production_checkpoint.metadata does not mirror the checkpoint meta")
    rgates = [a.get("gate_id") for a in rec.get("amendments") or []]
    if GATE_ID in rgates or not rgates or rgates[-1] != PRIOR_GATE:
        raise Refuse(f"v10 receipt amendments are {rgates}; expected the last to be {PRIOR_GATE}")
    pc["metadata"] = {**meta, "checkpoint_sha256": cksum_new}
    rec["amendments"] = list(rec["amendments"]) + [{
        **amend,
        "checkpoint_meta_sha256_before": META_PRE,
        "checkpoint_meta_sha256_after": sha_bytes(meta_new),
        "checkpoint_sha256_before": CKSUM_PRE,
        "checkpoint_sha256_after": cksum_new,
    }]
    out[V10_RECEIPT] = dump_json(rec)
    return out, meta, sha_bytes(meta_new), cksum_new, sha_bytes(out[V10_RECEIPT])


def check_evidence():
    """Read-only proof that the purge happened as proposed and that the backups hold the before-bytes.
    Returns a list of (ok, message)."""
    res = []

    def chk(cond, msg):
        res.append((bool(cond), msg))
        return bool(cond)

    key = backup_key()
    bdir = PURGE_BACKUP / key
    # backups == before
    for f in EPI_FILES:
        p = bdir / f
        got = sha_path(p) if p.is_file() and not p.is_symlink() else None
        chk(got == EPI_BEFORE[f], f"purge backup {f} == before {EPI_BEFORE[f][:12]}"
            + ("" if got == EPI_BEFORE[f] else f" (got {str(got)[:12]})"))
    try:
        man = json.loads((bdir / "MANIFEST.json").read_text())
        chk(man.get("preimage_sha256") == EPI_BEFORE, "purge backup MANIFEST.json preimage == before")
        src_ok = all(Path(man["source"][f]).resolve() == (v10_dir() / f).resolve() for f in EPI_FILES)
        chk(src_ok, "purge backup MANIFEST.json sources are the v10 checkpoint files")
    except Exception as exc:  # noqa: BLE001
        chk(False, f"purge backup MANIFEST.json unreadable ({exc})")
    # proposal
    pp = PURGE_BACKUP / "pinned_repin_proposal.json"
    try:
        raw = pp.read_bytes()
        chk(sha_bytes(raw) == PROPOSAL_SHA, f"proposal sha256 == {PROPOSAL_SHA[:12]}")
        prop = json.loads(raw)
        keys = [Path(k).resolve() for k in prop]
        chk(keys == [v10_dir().resolve()], "proposal names exactly the v10 checkpoint")
        entry = next(iter(prop.values()))
        chk(entry.get("file_sha256_before") == EPI_BEFORE, "proposal before == pinned before")
        chk(entry.get("file_sha256_after") == EPI_AFTER, "proposal after == pinned after")
        chk(PURGE_GATE in str(entry.get("reason")), f"proposal reason cites {PURGE_GATE}")
    except Exception as exc:  # noqa: BLE001
        chk(False, f"proposal {pp} unreadable ({exc})")
    # disk == after
    epi = epi_on_disk()
    for f in EPI_FILES:
        chk(epi[f] == EPI_AFTER[f], f"v10 {f} == after {EPI_AFTER[f][:12]}"
            + ("" if epi[f] == EPI_AFTER[f] else f" (got {epi[f][:12]})"))
    try:
        count = db_memory_count(v10_dir() / "episodic.db")
        chk(count == MEMCOUNT_AFTER, f"v10 episodic.db memories == {MEMCOUNT_AFTER} (read-only count: {count})")
    except Exception as exc:  # noqa: BLE001
        chk(False, f"v10 episodic.db could not be counted read-only ({exc})")
    # purge receipt
    try:
        rcpt = json.loads((PURGE_BACKUP / "receipt.json").read_text())
        chk(rcpt.get("gate_id") == PURGE_GATE, f"purge receipt gate_id == {PURGE_GATE}")
        v10db = str((v10_dir() / "episodic.db").resolve())

        def v10_store(run):
            for s in run.get("stores") or []:
                if str(Path(s.get("store", "")).resolve()) == v10db:
                    return s
            return None

        applied = [(r, v10_store(r)) for r in rcpt.get("runs") or []
                   if r.get("mode") == "apply" and r.get("include_pinned")]
        applied = [(r, s) for r, s in applied if s and s.get("deleted_ids")]
        if chk(len(applied) == 1, f"purge receipt has exactly one pinned apply that purged v10 (found {len(applied)})"):
            r, s = applied[0]
            chk(r.get("exit") == 0, "that apply exited 0")
            chk(sorted(s.get("deleted_ids") or []) == sorted(DELETED_IDS), "deleted ids == the 4 pinned ids")
            chk((s.get("deleted_rows") or {}).get("memories") == MEMCOUNT_BEFORE - MEMCOUNT_AFTER,
                f"deleted memories rows == {MEMCOUNT_BEFORE - MEMCOUNT_AFTER}")
            fa = s.get("faiss") or {}
            chk((fa.get("ntotal_before"), fa.get("ntotal_after")) == (MEMCOUNT_BEFORE, MEMCOUNT_AFTER),
                f"faiss ntotal {fa.get('ntotal_before')} -> {fa.get('ntotal_after')}")
            chk(s.get("preimage_sha256") == EPI_BEFORE, "apply preimage == before")
            chk(s.get("postimage_sha256") == EPI_AFTER, "apply postimage == after")
        runs = rcpt.get("runs") or []
        last = runs[-1] if runs else {}
        chk(last.get("mode") == "verify" and last.get("exit") == 0 and last.get("include_pinned"),
            "the purge receipt's LAST run is a passing verify with --include-pinned")
        ls = v10_store(last) or {}
        chk(ls.get("status") == "CLEAN" and (ls.get("row_counts") or {}).get("memories") == MEMCOUNT_AFTER,
            f"that verify found v10 CLEAN with {MEMCOUNT_AFTER} memories")
        health = last.get("verify_health")
        chk(isinstance(health, list) and health and all(h.get("ok") for h in health),
            "that verify's index health checks passed")
    except Exception as exc:  # noqa: BLE001
        chk(False, f"purge receipt unreadable ({type(exc).__name__}: {exc})")
    return res


def atomic_write(path, data):
    mode = path.stat().st_mode & 0o7777
    tmp = path.with_name(f".{path.name}.v10-repin.{os.getpid()}")
    with open(tmp, "xb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def durable_backup():
    """Copy every original this ratification rewrites to BACKUP_DIR (resume-safe)."""
    sources = [(v10_dir() / "checkpoint_meta.json", f"{V10}/checkpoint_meta.json"),
               (V10_RECEIPT, f"epyc-root/{V10_RECEIPT.name}")]
    lines = []
    for src, rel in sources:
        dst = BACKUP_DIR / rel
        want = sha_path(src)
        if dst.exists():
            if sha_path(dst) != want:
                raise Refuse(f"backup {dst} exists with different content; refusing to overwrite it")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            if sha_path(dst) != want:
                raise Refuse(f"backup copy verification failed: {dst}")
        lines.append(f"{want}  {rel}\n")
    sums = "".join(lines)
    readme = (
        "# v10-episodic-repin-20260917: originals before the v10 episodic re-pin\n\n"
        f"Written by scripts/operator/ratify_v10_episodic_repin_20260917.sh ({GATE_ID}).\n\n"
        "What: byte-exact originals of the two files that ratification rewrites: the\n"
        f"{V10} checkpoint_meta.json (sha256 {META_PRE})\n"
        f"and the epyc-root v10 baseline receipt (sha256 {RECEIPT_PRE}).\n\n"
        f"Why: the operator-approved eval-leak purge {PURGE_GATE} (epyc-orchestrator\n"
        f"{PURGE_COMMIT[:8]}) removed 4 HumanEval/55 memories from the v10 checkpoint, so its\n"
        "episodic.db / embeddings.faiss / id_map.npy pins had to move. The pre-purge store is in\n"
        f"{PURGE_BACKUP / backup_key()}.\n\n"
        "Restore (by hand only; it makes the pins false again unless the store is restored too):\n"
        f"copy {V10}/checkpoint_meta.json back under orchestration/autopilot_checkpoints/ and\n"
        "epyc-root/* back to artifacts/operator/, then `sha256sum -c SHA256SUMS` here.\n"
    )
    for name, text in (("SHA256SUMS", sums), ("README.md", readme)):
        p = BACKUP_DIR / name
        if p.exists():
            if p.read_text() != text:
                raise Refuse(f"{p} exists with different content")
        else:
            p.write_text(text)
    return BACKUP_DIR


def take_locks():
    handles = []
    for path, what in ((AP_LOCK, "AutoPilot is running"), (TRUST_LOCK, "the trust boundary is busy")):
        fh = open(path, "a+")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fh.close()
            raise Refuse(f"{what} ({path} is locked)")
        handles.append(fh)
    return handles


def journal_path():
    return TMPD / "journal.json"


def rollback():
    j = journal_path()
    if not j.exists():
        print("  rollback: nothing was written")
        return 0
    bad = 0
    for row in json.loads(j.read_text()):
        target, saved, want = Path(row["target"]), Path(row["saved"]), row["sha256"]
        if target.exists() and sha_path(target) == want:
            continue
        atomic_write(target, saved.read_bytes())
        if sha_path(target) != want:
            print(f"  ROLLBACK FAILED for {target}; original is in {BACKUP_DIR}")
            bad = 1
        else:
            print(f"  restored {target}")
    return bad


def _inject(point):  # test hook: simulate a failure at a named point
    if os.environ.get("V10_REPIN_TEST_MODE") == "1" and os.environ.get("V10_REPIN_FAIL_AT") == point:
        raise RuntimeError(f"injected failure at {point}")


def cmd_apply():
    locks = take_locks()
    try:
        st, _ = state()
        if st != "pre":
            raise Refuse(f"state is {st}, not pre")
        bad = [m for ok, m in check_evidence() if not ok]
        if bad:
            raise Refuse("evidence check failed: " + "; ".join(bad))
        post, meta_new, meta_post, cksum_post, rec_post = compute_post()
        if (meta_post, cksum_post, rec_post) != (META_POST, CKSUM_POST, RECEIPT_POST):
            raise Refuse("computed post-state differs from the pinned post-state; regenerate the bundle")
        verify_manifest(meta_new)
        print(f"  ok    durable backup -> {durable_backup()}")
        saved_dir = TMPD / "orig"
        journal = []
        for i, target in enumerate(post):
            saved = saved_dir / f"{i:02d}"
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved)
            journal.append({"target": str(target), "saved": str(saved), "sha256": sha_path(saved)})
        journal_path().write_text(json.dumps(journal))
        try:
            for target, data in post.items():
                atomic_write(target, data)
                print(f"  wrote {target}  ({sha_bytes(data)[:12]})")
                _inject("after_first_write")
            cmd_verify(quiet=True)
        except BaseException:
            print("  apply failed; rolling back")
            rollback()
            raise
    finally:
        for fh in locks:
            fh.close()
    return 0


def cmd_verify(quiet=False):
    st, rows = state()
    if st != "post":
        raise Refuse(f"state is {st}, not post")
    meta_raw = (v10_dir() / "checkpoint_meta.json").read_bytes()
    meta = json.loads(meta_raw)
    verify_manifest(meta)
    if {f: meta["file_sha256"][f] for f in EPI_FILES} != EPI_AFTER:
        raise Refuse("meta does not pin the purged episodic files")
    count = db_memory_count(v10_dir() / "episodic.db")
    if meta.get("memory_count") != MEMCOUNT_AFTER or count != MEMCOUNT_AFTER:
        raise Refuse(f"memory_count: meta {meta.get('memory_count')}, db {count}, pin {MEMCOUNT_AFTER}")
    gates = [a.get("gate_id") for a in meta.get("amendments") or []]
    if gates[-2:] != [PRIOR_GATE, GATE_ID]:
        raise Refuse(f"meta amendments end with {gates[-2:]}, expected [{PRIOR_GATE}, {GATE_ID}]")
    if checkpoint_sha(meta_raw) != CKSUM_POST:
        raise Refuse("recomputed checkpoint_sha256 differs from the pin")
    rec = json.loads(V10_RECEIPT.read_text())
    if rec["production_checkpoint"]["metadata"] != {**meta, "checkpoint_sha256": CKSUM_POST}:
        raise Refuse("v10 receipt metadata does not mirror the re-pinned checkpoint meta")
    rgates = [a.get("gate_id") for a in rec.get("amendments") or []]
    if rgates[-2:] != [PRIOR_GATE, GATE_ID]:
        raise Refuse(f"v10 receipt amendments end with {rgates[-2:]}, expected [{PRIOR_GATE}, {GATE_ID}]")
    bad = scan_prompt_copies()
    if bad:
        raise Refuse("prompt-leak post-state no longer holds: " + "; ".join(bad))
    if not quiet:
        for r, h in rows:
            print(f"  ok    {h[:12]}  {r}")
        print(f"  ok    v10 manifest matches every file; memory_count {MEMCOUNT_AFTER}; "
              f"checkpoint_sha256 {CKSUM_POST[:12]}")
        print(f"  ok    amendments end [{PRIOR_GATE}, {GATE_ID}] in the meta and the receipt")
        print(f"  ok    every checkpoint rules.md at {RULES_PIN[:12]}; no leak marker in any text copy")
        print("VERIFIED: post-state holds")
    return 0


def cmd_evidence():
    fail = 0
    for ok, msg in check_evidence():
        print(f"  {'ok  ' if ok else 'FAIL'}  {msg}")
        fail |= not ok
    return 65 if fail else 0


def cmd_plan():
    st, rows = state()
    print(f"  state: {st}")
    for r, h in rows:
        print(f"    {h}  {r}")
    if st != "pre":
        return 0
    post, meta_new, m, c, r = compute_post()
    verify_manifest(meta_new)
    print("  ok    the re-pinned v10 manifest matches every file on disk (incl. the purged store)")
    bad = scan_prompt_copies()
    if bad:
        raise Refuse("prompt-leak post-state of the prior ratification does not hold: " + "; ".join(bad))
    print(f"  ok    every checkpoint rules.md at {RULES_PIN[:12]}; no leak marker in any text copy")
    ok = (m, c, r) == (META_POST, CKSUM_POST, RECEIPT_POST)
    print(f"  {'ok  ' if ok else 'FAIL'}  computed post pins meta {m[:12]} checkpoint {c[:12]} receipt {r[:12]}")
    print(f"  info  checkpoint_sha256 {CKSUM_PRE[:12]} -> {c[:12]}")
    if not ok:
        raise Refuse("computed post-state differs from the pinned post-state")
    for target, data in post.items():
        before = target.read_bytes().decode().split("\n")
        after = data.decode().split("\n")
        print(f"\n  --- diff {target}")
        for line in difflib.unified_diff(before, after, "before", "after", lineterm="", n=1):
            print("  " + line)
    return 0


def cmd_pins():
    post, _, m, c, r = compute_post()
    print(json.dumps({"META_POST": m, "CKSUM_POST": c, "RECEIPT_POST": r,
                      "PROPOSAL_SHA": sha_path(PURGE_BACKUP / "pinned_repin_proposal.json")}))
    return 0


def main():
    cmd = sys.argv[1]
    try:
        if cmd == "state":
            print(state()[0])
            return 0
        if cmd == "pin":
            print(json.dumps(globals()[sys.argv[2]]))
            return 0
        return {"plan": cmd_plan, "apply": cmd_apply, "rollback": rollback, "evidence": cmd_evidence,
                "verify": cmd_verify, "pins": cmd_pins}[cmd]()
    except Refuse as exc:
        print(f"REFUSING: {exc}", file=sys.stderr)
        return 65


if __name__ == "__main__":
    raise SystemExit(main())
PYEOF

core() { python3 "$CORE" "$@"; }

# ============================================================================ verify (read-only)
if [ "$MODE" = "verify" ]; then
  core verify
  exit $?
fi

# ============================================================================ idempotence
st_rc=0
STATE="$(core state)" || st_rc=$?
[ "$st_rc" -eq 0 ] || die "target state check failed (see above). Nothing written."
if [ "$STATE" = "post" ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ] && [ -f "$CONSOLIDATED" ]; then
    core verify >/dev/null || die "targets are at their post-state pins but --verify fails. Resolve by hand."
    say "ALREADY RATIFIED: the v10 meta and receipt are at their post-state pins and $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: the targets are re-pinned, but a receipt is missing (decision $([ -f "$RECEIPT" ] && echo present || echo MISSING), index $([ -f "$INDEX" ] && echo present || echo MISSING), consolidated $([ -f "$CONSOLIDATED" ] && echo present || echo MISSING)). Resolve by hand."
fi
[ -f "$RECEIPT" ]      && die "$RECEIPT_REL already exists, but the targets are not re-pinned. Resolve by hand."
[ -f "$INDEX" ]        && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ============================================================================ preflight
say "== preflight (ROOT=$ROOT, ORCH=$ORCH, mode=$MODE) =="
fail=0
ok()  { printf '  ok    %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*"; fail=1; }

dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then bad "commit paths clean in git"; printf '%s\n' "$dirty"; else ok "commit paths clean in git"; fi

if [ -f "$ROOT/$PRIOR_INDEX_REL" ] && grep -q '"status": "ratified"' "$ROOT/$PRIOR_INDEX_REL"; then
  ok "prior ratification $PRIOR_GATE is on record ($PRIOR_INDEX_REL)"
else
  bad "prior ratification $PRIOR_GATE keyed index missing or not ratified ($PRIOR_INDEX_REL)"
fi

if git -C "$ORCH_GIT" fetch -q origin 2>/dev/null; then
  ok "orchestrator fetch origin"
  if git -C "$ORCH_GIT" merge-base --is-ancestor "$PURGE_COMMIT" origin/main 2>/dev/null; then
    ok "orchestrator ${PURGE_COMMIT:0:8} (the purge) merged in origin/main"
  else
    bad "orchestrator ${PURGE_COMMIT:0:8} (the purge) merged in origin/main"
  fi
else
  bad "orchestrator fetch origin (cannot verify the purge commit is merged)"
fi
changed="$(git -C "$ORCH_GIT" show --format= --name-only "$PURGE_COMMIT" 2>/dev/null | sort | tr '\n' ' ')"
[ "$changed" = "scripts/maintenance/purge_eval_leak_memories_20260917.py scripts/maintenance/purge_eval_leak_memories_20260917.sh " ] \
  && ok "${PURGE_COMMIT:0:8} adds exactly the two purge scripts" || bad "${PURGE_COMMIT:0:8} file set is '$changed'"

say "  -- purge evidence (hashes ~800 MB twice; a few seconds)"
ev_rc=0
core evidence || ev_rc=$?
[ "$ev_rc" -eq 0 ] || fail=1

say "  -- plan"
plan_rc=0
core plan || plan_rc=$?
[ "$plan_rc" -eq 0 ] || fail=1

if [ "$fail" -ne 0 ]; then
  die "preflight failed. Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
fi
say ""
say "  preflight clean"

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "DRY RUN: would back up checkpoint_meta.json and the v10 receipt to $BACKUP_DIR, apply the diffs"
  say "above, then write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL. Nothing written."
  say "Apply with: ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ============================================================================ apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PRE="$TMPD/pre.json"
restore() {
  core rollback || say "ROLLBACK INCOMPLETE: originals are in $BACKUP_DIR (see its README.md)"
  rm -f "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$V10_REL" --out "$PRE" \
  || die "could not snapshot the pre-state; nothing written"
core apply || die "apply failed and was rolled back (see above)."

say ""
say "== postflight =="
core verify || { restore; die "postflight --verify failed; every original restored."; }

# ============================================================================ consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
mkdir -p "$ROOT/artifacts/operator/receipts"
receipt_rc=0
if [ "$V10_REPIN_TEST_MODE" = "1" ] && [ "${V10_REPIN_FAIL_AT:-}" = "receipt" ]; then
  receipt_rc=1
else
  EXTRA_EMIT=()
  if [ "$V10_REPIN_TEST_MODE" = "1" ] && [ -n "${V10_REPIN_EVIDENCE_REPO:-}" ]; then
    EXTRA_EMIT=(--evidence-repo "$V10_REPIN_EVIDENCE_REPO")
  fi
  python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
    --repo-root "$ROOT" ${EXTRA_EMIT[@]+"${EXTRA_EMIT[@]}"} \
    --pre "$PRE" \
    --protocol-id P-QUAL-T1 \
    --ratification-id "$GATE_ID" \
    --script "$SCRIPT_PATH" \
    --evidence "$PURGE_BACKUP/pinned_repin_proposal.json=the purge's before/after hashes for the three v10 files, written for this amendment" \
    --evidence "$PURGE_BACKUP/receipt.json=the purge receipt: the pinned apply (4 ids deleted) and the passing verify with --include-live --include-pinned" \
    --evidence "$BACKUP_DIR=byte-exact originals of checkpoint_meta.json and the v10 receipt, with SHA256SUMS" \
    --validation "bash scripts/operator/ratify_v10_episodic_repin_20260917.sh --verify" \
    --out "$CONSOLIDATED" || receipt_rc=$?
fi
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Every original restored; the receipt, if any, is kept at ${refused#$ROOT/} for reading."
fi

# ============================================================================ decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$CONSOLIDATED_REL" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$(sha256sum "$BACKUP_DIR/SHA256SUMS" | awk '{print $1}')" \
     "$(sha256sum "$PURGE_BACKUP/receipt.json" | awk '{print $1}')" "$(sha256sum "$ROOT/$V10_REL" | awk '{print $1}')" \
     "$CORE" <<'PYEOF'
import sys, json, os, subprocess
(receipt, index, ts, consolidated_rel, operator, sums_sha, purge_receipt_sha, v10_after, core) = sys.argv[1:10]
def pin(name):
    return json.loads(subprocess.check_output([sys.executable, core, "pin", name], text=True))
pinj = pin
gate = os.environ["GATE_ID"]
purge_backup = os.environ["PURGE_BACKUP"]
before, after = pinj("EPI_BEFORE"), pinj("EPI_AFTER")
doc = {
  "schema": "epyc.autopilot.checkpoint_episodic_repin.v1",
  "decision": "V10-EPISODIC-REPIN",
  "gate_id": gate,
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "operator_decision": "2026-09-17: purge the HumanEval/55 eval-leak memories from every store including the pinned production_best (v10), then re-pin v10",
  "purge": {
    "gate_id": os.environ["PURGE_GATE"],
    "orchestrator_commit": os.environ["PURGE_COMMIT"],
    "script": "scripts/maintenance/purge_eval_leak_memories_20260917.{sh,py}",
    "checkpoint": "orchestration/autopilot_checkpoints/multitier_v10_20260810 (production_best)",
    "deleted_memory_ids": pinj("DELETED_IDS"),
    "memory_count": {"before": pin("MEMCOUNT_BEFORE"), "after": pin("MEMCOUNT_AFTER")},
    "backup_dir": purge_backup,
    "proposal": {"path": os.path.join(purge_backup, "pinned_repin_proposal.json"), "sha256": pin("PROPOSAL_SHA")},
    "receipt": {"path": os.path.join(purge_backup, "receipt.json"), "sha256_at_ratification": purge_receipt_sha},
  },
  "equivalence": "Only the 4 HumanEval/55 memories (and their memories_appendonly_legacy rows and FAISS vectors) changed; every other v10 checkpoint file is byte-identical to its existing pin, which the full manifest check proves. rules.md stays at the RATIFY-CKPT-PROMPT-LEAK-20260916 pin.",
  "state": {
    "multitier_v10_20260810 episodic files": {f: {"sha256_before": before[f], "sha256_after": after[f]} for f in sorted(before)},
    "multitier_v10_20260810/checkpoint_meta.json": {"sha256_before": pin("META_PRE"), "sha256_after": pin("META_POST")},
    "multitier_v10_20260810 checkpoint_sha256": {"before": pin("CKSUM_PRE"), "after": pin("CKSUM_POST")},
    "artifacts/operator/ratify_multitier_baseline_v10_20260810.json": {"sha256_before": pin("RECEIPT_PRE"), "sha256_after": v10_after},
  },
  "backup": {"dir": os.environ["BACKUP_DIR"], "sha256sums": sums_sha},
  "pins_and_checkers": {
    "pins": [
      "checkpoint_meta.json file_sha256[episodic.db, embeddings.faiss, id_map.npy] and memory_count",
      "checkpoint_sha256 (canonical JSON over file_sha256 + the meta's own hash)",
      "ratify_multitier_baseline_v10_20260810.json production_checkpoint.metadata (mirror of both)",
    ],
    "checkers": {
      "scripts/operator/ratify_v10_episodic_repin_20260917.sh --verify": "authoritative post-state check from now on",
      "scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh --verify": "SUPERSEDED as a validation command: it pins the pre-purge meta/receipt hashes, and its script hash is attested in its consolidated receipt, so it is not edited. Every check it made is re-run by this gate's --verify.",
      "epyc-orchestrator purge_eval_leak_memories_20260917.py": "classifies v10 as pinned by 'episodic.db' in file_sha256 and requires rules.md 18f8ea01; both still hold",
      "epyc-orchestrator ratify_and_apply_multitier_baseline_v10.py": "writes the pins once at v10 ratification, never re-reads them; its checkpoint_sha256 and memory_count formulas are reused here",
      "StructuralLab.restore_checkpoint / decision_cockpit.read_checkpoint": "verify no hash",
    },
  },
  "consolidated_receipt": consolidated_rel,
  "applied_by": "scripts/operator/ratify_v10_episodic_repin_20260917.sh",
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
rel = os.path.relpath(receipt, os.environ["ROOT"])
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify",
               "receipt": "/workspace/" + rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}")
print(f"  keyed index:      {index}")
PYEOF
then
  restore; rm -f "$CONSOLIDATED"
  die "could not write the decision receipt or keyed index. Every original restored."
fi

say ""
say "APPLIED, NOT STAGED, NOT COMMITTED. checkpoint_meta.json is an untracked orchestrator file and is"
say "already re-pinned in place (original in $BACKUP_DIR). Commit exactly these four paths:"
say ""
say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
say "    git -C $ROOT diff --cached --stat"
say "    git -C $ROOT commit -F <message file>"
