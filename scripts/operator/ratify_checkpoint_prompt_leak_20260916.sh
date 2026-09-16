#!/bin/bash
# ratify_checkpoint_prompt_leak_20260916.sh — close the eval-leak rewind hole: patch the leaked
# few-shot example out of every AutoPilot checkpoint copy of prompts/rules.md, and re-pin the
# hashes that attest the v10 production checkpoint.
#
#   Review (default, writes nothing):  bash scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh
#   Apply + receipts (no commit):      bash scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh --apply
#   Post-state check (read-only):      bash scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh --verify
#   Operator entry point:              scripts/operator/run_ckpt_leak_ratify_20260916.sh --operator <name>
#
# OPERATOR DECISION 2026-09-16, OPTION A: close the eval-leak rewind hole.
#
# THE LEAK. Eval pool row simpleqa_general_00912 ("At which university did Jurgen Aschoff study
# medicine?" -> "University of Bonn.") was a verbatim few-shot example (Example 4b) in
# epyc-orchestrator orchestration/prompts/rules.md. epyc-orchestrator 09bdb998 (merged to
# origin/main) replaced it with a synthetic entity, "Halvard Oskeberg" / chemistry. That commit
# fixed the TRACKED file only. Every AutoPilot checkpoint carries an untracked copy of
# orchestration/prompts/, and StructuralLab.restore_checkpoint() copies that copy back over the
# live prompts. production_best -> multitier_v10_20260810 is one of them, so a rollback (automatic
# after three consecutive safety failures, or `autopilot.py restore`) would restore the leak.
#
# INVENTORY (every source a rewind reads: CHECKPOINT_FILES, prompts/, classifier_config.yaml,
# autopilot_short_term_memory.md, strategy_store/; scanned 2026-09-16 for "Aschoff", the
# HumanEval/55 solution code, and the 8-token shingles of simpleqa_general_00912/00795 and
# sv_HE-R{,+}_HumanEval/55::sol0-4, template shingles with pool DF>=32 dropped):
#   prompts/rules.md  sha256 b250c227...  in these 10 checkpoints (all byte-identical, and
#   identical to 09bdb998^:orchestration/prompts/rules.md):
#     20260716_062336 20260727_005741 20260727_030219 20260803_120918 20260803_130944
#     20260804_104155 20260804_152401 20260808_184245 20260809_115107 multitier_v10_20260810
#   20260727_053326 has no prompts/ (state + memory only) and no hit.
#   The HumanEval/55 copy (src/prompts/coder_system.txt) is not under orchestration/prompts, so no
#   checkpoint carries it. No hit in any checkpoint's autopilot_state.json,
#   autopilot_short_term_memory.md, classifier_config.yaml, skills.db (0 rows) or strategy store
#   (1428 strategies; it stores no prompt snapshots, content_hashes is empty).
#   Pins on rules.md b250c227: multitier_v10_20260810/checkpoint_meta.json file_sha256 (the only
#   checkpoint with a manifest; the other metas are pre-v2 and carry no hashes), and
#   epyc-root artifacts/operator/ratify_multitier_baseline_v10_20260810.json
#   production_checkpoint.metadata (file_sha256 + checkpoint_sha256).
# OUT OF SCOPE, recorded in the decision receipt:
#   - episodic.db in every checkpoint (and the live one) holds 4 memories whose context carries the
#     HumanEval/55 problem text. That is eval-task routing memory, not a prompt copy; patching a
#     538 MB memory store is a different decision.
#   - orchestration/autopilot_state*.bak* / archived_backups/*: last_traces text mentions Aschoff.
#     Manual operator backups; no code path restores them.
#
# WHAT A REWIND VERIFIES. Nothing: StructuralLab.restore_checkpoint() copies files and checks no
# hash. The pins are ATTESTATION: checkpoint_meta.json file_sha256 and the v10 receipt are what a
# human or an audit uses to prove production_best is the ratified v10 checkpoint. Patching
# rules.md without re-pinning would leave that record false (b250c227 pinned, 18f8ea01 on disk),
# and re-pinning edits a human-ratified receipt. Hence this operator ratification.
#
# WHAT IT DOES
#   1. durable backup of every original to $BACKUP_DIR (/mnt/raid0/llm/backups/ckpt-leak-20260916)
#      with SHA256SUMS and README.md;
#   2. in each of the 10 checkpoint copies, replaces exactly two lines (the Example 4b question and
#      its web_research query) with the 09bdb998 text. The result must hash to 18f8ea01..., which is
#      09bdb998:orchestration/prompts/rules.md byte for byte;
#   3. multitier_v10_20260810/checkpoint_meta.json: file_sha256["prompts/rules.md"] -> 18f8ea01...
#      plus an "amendments" entry. The checkpoint_sha256 is recomputed with the v10 ratifier's own
#      formula (canonical JSON over file_sha256 + the meta file's hash);
#   4. the v10 receipt: production_checkpoint.metadata mirrors the new meta and checkpoint_sha256,
#      plus a top-level "amendments" entry. Nothing else in it changes;
#   5. writes the decision receipt, its keyed index and the MEASUREMENT.md section-5 consolidated
#      receipt.
# EQUIVALENCE. Only the few-shot example changed: the diff is two lines, both inside Example 4b,
# the same structure and token count, and the patched file is byte-identical to production
# (09bdb998) at that snapshot. No other checkpoint byte changes except checkpoint_meta.json.
#
# PINS. Any mismatch is refused. If a target moved, regenerate this bundle; never force it.
#   rules.md                   pre   b250c22770e999d5ef2092a3689247af8725f6cf1d5f01ed37b6296ea568456e
#   rules.md                   post  18f8ea018234605002459cd98e59a9aaeddec235d8e022ff59f6ebd67766d607
#   v10 checkpoint_meta.json   pre   e9d8538560e2a1435d073513e642465d7d384ef0ace7aafb6d636278f2a79ab8
#   v10 checkpoint_sha256      pre   c60364f1295a931a4b4e806d4dffd2138696537f49b15a3a6881c50737c02b19
#   v10 receipt                pre   3e18e7fdd5039f01fc84f7993a4d2a9568fd02a570b8fcac73fd55ba6b44e251
#   (post pins for the meta, checkpoint_sha256 and receipt are the constants in the Python core)
#
# SAFETY. Takes the AutoPilot singleton lock and the trust-boundary lock (non-blocking; refuses if
# AutoPilot runs). Every write is tmp+rename with the original mode kept. Any failure restores
# every original. IDEMPOTENT: at post-state with all receipts present it prints ALREADY RATIFIED
# and exits 0. Any mixed or unknown state is refused. Nothing here starts a process, takes
# compute or edits a tracked orchestrator file.
#
# Environment overrides (tests): ROOT (epyc-root checkout; default: the checkout holding this
# script), ORCH (orchestrator tree holding orchestration/autopilot_checkpoints), ORCH_GIT (the
# orchestrator git repo used for evidence checks; default ORCH), BACKUP_DIR, TRUST_LOCK.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
ORCH="${ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
ORCH_GIT="${ORCH_GIT:-$ORCH}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/raid0/llm/backups/ckpt-leak-20260916}"
TRUST_LOCK="${TRUST_LOCK:-/run/lock/epyc-measurement-trust-boundary.lock}"
CKPT_ROOT="$ORCH/orchestration/autopilot_checkpoints"
AP_LOCK="$ORCH/orchestration/.autopilot.lock"
POOL="/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl"
export ROOT ORCH ORCH_GIT BACKUP_DIR TRUST_LOCK CKPT_ROOT AP_LOCK

FIX_COMMIT="09bdb998f27fd13a13f3a4908f924626f886ef3a"
GATE_ID="RATIFY-CKPT-PROMPT-LEAK-20260916"
V10_REL="artifacts/operator/ratify_multitier_baseline_v10_20260810.json"
RECEIPT_REL="artifacts/operator/ratify_checkpoint_prompt_leak_20260916.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_checkpoint_prompt_leak_20260916.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$V10_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
export GATE_ID FIX_COMMIT V10_REL RECEIPT_REL

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
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"

TMPD="$(mktemp -d)"
export TMPD
trap 'rm -rf "$TMPD"' EXIT
CORE="$TMPD/core.py"

# ============================================================================ Python core
cat > "$CORE" <<'PYEOF'
"""Core of ratify_checkpoint_prompt_leak_20260916.sh. Commands: inventory, plan, apply,
rollback, verify, pins. Reads its paths from the environment the shell exports."""
import difflib, fcntl, hashlib, json, os, shutil, sys
from pathlib import Path

ROOT = Path(os.environ["ROOT"])
CKPT_ROOT = Path(os.environ["CKPT_ROOT"])
BACKUP_DIR = Path(os.environ["BACKUP_DIR"])
TMPD = Path(os.environ["TMPD"])
AP_LOCK = Path(os.environ["AP_LOCK"])
TRUST_LOCK = Path(os.environ["TRUST_LOCK"])
GATE_ID = os.environ["GATE_ID"]
FIX_COMMIT = os.environ["FIX_COMMIT"]
V10_RECEIPT = ROOT / os.environ["V10_REL"]
DECISION_REL = os.environ["RECEIPT_REL"]

RULES_REL = "prompts/rules.md"
RULES_PRE = "b250c22770e999d5ef2092a3689247af8725f6cf1d5f01ed37b6296ea568456e"
RULES_POST = "18f8ea018234605002459cd98e59a9aaeddec235d8e022ff59f6ebd67766d607"
SWAPS = (
    ('Question: "At which university did Jurgen Aschoff study medicine?"\n',
     'Question: "At which university did Halvard Oskeberg study chemistry?"\n'),
    ('results = json.loads(CALL("web_research", query="Jurgen Aschoff study medicine university"))\n',
     'results = json.loads(CALL("web_research", query="Halvard Oskeberg study chemistry university"))\n'),
)
LEAK_MARKERS = (b"Aschoff", b"University of Bonn")
V10 = "multitier_v10_20260810"
CHECKPOINTS = (
    "20260716_062336", "20260727_005741", "20260727_030219", "20260803_120918",
    "20260803_130944", "20260804_104155", "20260804_152401", "20260808_184245",
    "20260809_115107", V10,
)
NO_PROMPTS = ("20260727_053326",)
META_PRE = "e9d8538560e2a1435d073513e642465d7d384ef0ace7aafb6d636278f2a79ab8"
META_POST = "54224ec71905b7e628284262579dec1f8da59d0c9d63855fada878ec78305746"
CKSUM_PRE = "c60364f1295a931a4b4e806d4dffd2138696537f49b15a3a6881c50737c02b19"
CKSUM_POST = "a604276fcd053e7590bd391f846334f5fd4616f7cd9ebe78196b8f6305f1d218"
RECEIPT_PRE = "3e18e7fdd5039f01fc84f7993a4d2a9568fd02a570b8fcac73fd55ba6b44e251"
RECEIPT_POST = "e6682b2fe9cbe88d21b9f6f075a40a38a8b2dd23f40641049578f6c496dc9a03"

AMENDMENT = {
    "date": "2026-09-16",
    "gate_id": GATE_ID,
    "kind": "eval_leak_few_shot_replacement",
    "file": RULES_REL,
    "sha256_before": RULES_PRE,
    "sha256_after": RULES_POST,
    "reason": ("few-shot Example 4b copied eval pool row simpleqa_general_00912 verbatim; "
               "replaced with the synthetic example from epyc-orchestrator " + FIX_COMMIT[:8]
               + " (only the few-shot example changed)"),
    "source_commit": FIX_COMMIT,
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


def swap(text):
    for old, new in SWAPS:
        if text.count(old) != 1:
            raise Refuse(f"expected exactly one occurrence of {old.strip()[:60]!r}")
        text = text.replace(old, new)
    return text


def regular_file(p):
    if p.is_symlink() or not p.is_file():
        raise Refuse(f"{p} is missing or not a regular file")
    return p


def checkpoint_sha(meta_raw):
    meta = json.loads(meta_raw)
    hashes = dict(meta["file_sha256"])
    hashes["checkpoint_meta.json"] = sha_bytes(meta_raw)
    return canonical_hash(hashes)


def verify_manifest(meta_raw, expect_rules):
    """Every file in the v10 checkpoint matches its manifest; no extra, no missing file."""
    meta = json.loads(meta_raw)
    base = CKPT_ROOT / V10
    listed = set(meta["file_sha256"])
    on_disk = {p.relative_to(base).as_posix() for p in base.rglob("*")
               if p.is_file() or p.is_symlink()} - {"checkpoint_meta.json"}
    if listed != on_disk:
        raise Refuse(f"v10 manifest/file-set mismatch: missing={sorted(listed - on_disk)} "
                     f"extra={sorted(on_disk - listed)}")
    if meta["file_sha256"][RULES_REL] != expect_rules:
        raise Refuse(f"v10 manifest pins rules.md {meta['file_sha256'][RULES_REL][:12]}, "
                     f"expected {expect_rules[:12]}")
    for rel, want in sorted(meta["file_sha256"].items()):
        got = sha_path(regular_file(base / rel))
        if got != want:
            raise Refuse(f"v10 checkpoint file {rel} is {got[:12]}, manifest says {want[:12]}")


def scan_leaks():
    """Leak markers anywhere in a checkpoint's text copies (not the memory stores)."""
    hits = []
    for p in sorted(CKPT_ROOT.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue
        if p.suffix in (".db", ".sqlite", ".faiss", ".npy", ".npz"):
            continue
        data = p.read_bytes()
        if any(m in data for m in LEAK_MARKERS):
            hits.append(str(p.relative_to(CKPT_ROOT)))
    return hits


def state():
    """Classify the whole target set as pre, post, or refuse."""
    # Inventory drift: the set of checkpoints carrying prompts/rules.md must be exactly ours.
    found = sorted(p.parent.parent.name for p in CKPT_ROOT.glob("*/prompts/rules.md")
                   if not p.parent.parent.is_symlink())
    if found != sorted(CHECKPOINTS):
        raise Refuse(f"checkpoint inventory drift: found {found}, prepared for {sorted(CHECKPOINTS)}")
    for name in NO_PROMPTS:
        if (CKPT_ROOT / name / "prompts").exists():
            raise Refuse(f"{name} now has a prompts/ directory; regenerate the bundle")
    link = CKPT_ROOT / "production_best"
    if not link.is_symlink() or link.resolve() != (CKPT_ROOT / V10).resolve():
        raise Refuse(f"production_best does not resolve to {V10}")
    rules = {n: sha_path(regular_file(CKPT_ROOT / n / RULES_REL)) for n in CHECKPOINTS}
    meta_sha = sha_path(regular_file(CKPT_ROOT / V10 / "checkpoint_meta.json"))
    rec_sha = sha_path(regular_file(V10_RECEIPT))
    vals = set(rules.values())
    rows = [(f"{n}/{RULES_REL}", h) for n, h in rules.items()]
    rows += [(f"{V10}/checkpoint_meta.json", meta_sha), (str(V10_RECEIPT), rec_sha)]
    if vals == {RULES_PRE} and meta_sha == META_PRE and rec_sha == RECEIPT_PRE:
        return "pre", rows
    if vals == {RULES_POST} and meta_sha == META_POST and rec_sha == RECEIPT_POST:
        return "post", rows
    detail = "\n".join(f"    {h}  {r}" for r, h in rows)
    raise Refuse("targets are neither all at the pre-state pins nor all at the post-state pins "
                 "(drift, tampering or a half-applied run). Resolve by hand; originals, if a run "
                 f"started, are in {BACKUP_DIR}.\n{detail}")


def compute_post():
    """Every post-state byte string, derived in memory from the verified pre-state."""
    out = {}
    pre_text = (CKPT_ROOT / V10 / RULES_REL).read_bytes().decode("utf-8")
    post_rules = swap(pre_text).encode("utf-8")
    if sha_bytes(post_rules) != RULES_POST:
        raise Refuse(f"swapped rules.md hashes {sha_bytes(post_rules)[:12]}, pin is {RULES_POST[:12]}")
    for n in CHECKPOINTS:
        out[CKPT_ROOT / n / RULES_REL] = post_rules
    meta_raw = (CKPT_ROOT / V10 / "checkpoint_meta.json").read_bytes()
    if checkpoint_sha(meta_raw) != CKSUM_PRE:
        raise Refuse("v10 checkpoint_sha256 recomputed from the current meta is not the pinned pre value")
    meta = json.loads(meta_raw)
    if dump_json(meta) != meta_raw:
        raise Refuse("checkpoint_meta.json is not in canonical form; a rewrite would change more than the pins")
    meta["file_sha256"][RULES_REL] = RULES_POST
    meta["amendments"] = list(meta.get("amendments") or []) + [AMENDMENT]
    meta_new = dump_json(meta)
    cksum_new = checkpoint_sha(meta_new)
    out[CKPT_ROOT / V10 / "checkpoint_meta.json"] = meta_new
    rec_raw = V10_RECEIPT.read_bytes()
    rec = json.loads(rec_raw)
    if dump_json(rec) != rec_raw:
        raise Refuse("the v10 receipt is not in canonical form; a rewrite would change more than the pins")
    pc = rec["production_checkpoint"]
    if Path(pc["path"]).name != V10:
        raise Refuse(f"v10 receipt production_checkpoint.path is {pc['path']}")
    if pc["metadata"] != {**json.loads(meta_raw), "checkpoint_sha256": CKSUM_PRE}:
        raise Refuse("v10 receipt production_checkpoint.metadata does not mirror the checkpoint meta")
    pc["metadata"] = {**meta, "checkpoint_sha256": cksum_new}
    rec["amendments"] = list(rec.get("amendments") or []) + [{
        **AMENDMENT,
        "checkpoints_patched": list(CHECKPOINTS),
        "checkpoint_meta_sha256_before": META_PRE,
        "checkpoint_meta_sha256_after": sha_bytes(meta_new),
        "checkpoint_sha256_before": CKSUM_PRE,
        "checkpoint_sha256_after": cksum_new,
    }]
    out[V10_RECEIPT] = dump_json(rec)
    return out, sha_bytes(meta_new), cksum_new, sha_bytes(out[V10_RECEIPT])


def atomic_write(path, data):
    mode = path.stat().st_mode & 0o7777
    tmp = path.with_name(f".{path.name}.ckpt-leak.{os.getpid()}")
    with open(tmp, "xb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def durable_backup():
    """Copy every original to BACKUP_DIR (resume-safe: identical copies are accepted)."""
    sources = [(CKPT_ROOT / n / RULES_REL, f"{n}/{RULES_REL}") for n in CHECKPOINTS]
    sources.append((CKPT_ROOT / V10 / "checkpoint_meta.json", f"{V10}/checkpoint_meta.json"))
    sources.append((V10_RECEIPT, f"epyc-root/{V10_RECEIPT.name}"))
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
        "# ckpt-leak-20260916: originals before the checkpoint prompt-leak repin\n\n"
        f"Written by scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh ({GATE_ID}).\n\n"
        "What: byte-exact originals of every file that ratification rewrites: prompts/rules.md from\n"
        "10 AutoPilot checkpoints (all sha256 " + RULES_PRE + "), the v10\n"
        "checkpoint_meta.json, and the epyc-root v10 baseline receipt.\n\n"
        "Why: those rules.md copies carry eval pool row simpleqa_general_00912 (Jurgen Aschoff /\n"
        "University of Bonn) as few-shot Example 4b. epyc-orchestrator " + FIX_COMMIT[:8] + " replaced it in\n"
        "the tracked file; a checkpoint rewind would have restored it.\n\n"
        "Restore (by hand only, which re-opens the leak): copy each file back over its original path\n"
        "under orchestration/autopilot_checkpoints/ (epyc-root/* goes to artifacts/operator/), then\n"
        "`sha256sum -c SHA256SUMS` here and against the targets.\n"
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


def cmd_apply():
    locks = take_locks()
    try:
        st, _ = state()
        if st != "pre":
            raise Refuse(f"state is {st}, not pre")
        post, meta_post, cksum_post, rec_post = compute_post()
        if (meta_post, cksum_post, rec_post) != (META_POST, CKSUM_POST, RECEIPT_POST):
            raise Refuse("computed post-state differs from the pinned post-state; regenerate the bundle")
        verify_manifest((CKPT_ROOT / V10 / "checkpoint_meta.json").read_bytes(), RULES_PRE)
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
    verify_manifest((CKPT_ROOT / V10 / "checkpoint_meta.json").read_bytes(), RULES_POST)
    rec = json.loads(V10_RECEIPT.read_text())
    meta = json.loads((CKPT_ROOT / V10 / "checkpoint_meta.json").read_text())
    if rec["production_checkpoint"]["metadata"] != {**meta, "checkpoint_sha256": CKSUM_POST}:
        raise Refuse("v10 receipt metadata does not mirror the patched checkpoint meta")
    if checkpoint_sha((CKPT_ROOT / V10 / "checkpoint_meta.json").read_bytes()) != CKSUM_POST:
        raise Refuse("recomputed checkpoint_sha256 differs from the pin")
    leaks = scan_leaks()
    if leaks:
        raise Refuse(f"leak markers still present in: {leaks}")
    if not quiet:
        for r, h in rows:
            print(f"  ok    {h[:12]}  {r}")
        print(f"  ok    v10 manifest matches every file; checkpoint_sha256 {CKSUM_POST[:12]}")
        print("  ok    no leak marker in any checkpoint text copy")
        print("VERIFIED: post-state holds")
    return 0


def cmd_plan():
    st, rows = state()
    print(f"  state: {st}")
    for r, h in rows:
        print(f"    {h}  {r}")
    if st != "pre":
        return 0
    verify_manifest((CKPT_ROOT / V10 / "checkpoint_meta.json").read_bytes(), RULES_PRE)
    print("  ok    v10 manifest matches every file (pre-state)")
    post, m, c, r = compute_post()
    ok = (m, c, r) == (META_POST, CKSUM_POST, RECEIPT_POST)
    print(f"  {'ok  ' if ok else 'FAIL'}  computed post pins meta {m[:12]} checkpoint {c[:12]} receipt {r[:12]}")
    if not ok:
        raise Refuse("computed post-state differs from the pinned post-state")
    shown = set()
    for target, data in post.items():
        key = target.name
        before = target.read_bytes().decode().split("\n")
        after = data.decode().split("\n")
        if key in shown:
            print(f"  (same diff) {target}")
            continue
        shown.add(key)
        print(f"\n  --- diff {target}")
        for line in difflib.unified_diff(before, after, "before", "after", lineterm="", n=1):
            print("  " + line)
    return 0


def cmd_pins():
    post, m, c, r = compute_post()
    print(json.dumps({"META_POST": m, "CKSUM_POST": c, "RECEIPT_POST": r}))
    return 0


def main():
    cmd = sys.argv[1]
    try:
        if cmd == "state":
            print(state()[0])
            return 0
        return {"plan": cmd_plan, "apply": cmd_apply, "rollback": rollback,
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
    say "ALREADY RATIFIED: every target is at its post-state pin and $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: the targets are patched, but a receipt is missing (decision $([ -f "$RECEIPT" ] && echo present || echo MISSING), index $([ -f "$INDEX" ] && echo present || echo MISSING), consolidated $([ -f "$CONSOLIDATED" ] && echo present || echo MISSING)). Resolve by hand."
fi
[ -f "$RECEIPT" ]      && die "$RECEIPT_REL already exists, but the targets are not patched. Resolve by hand."
[ -f "$INDEX" ]        && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ============================================================================ preflight
say "== preflight (ROOT=$ROOT, ORCH=$ORCH, mode=$MODE) =="
fail=0
ok()  { printf '  ok    %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*"; fail=1; }

dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then bad "commit paths clean in git"; printf '%s\n' "$dirty"; else ok "commit paths clean in git"; fi

if git -C "$ORCH_GIT" fetch -q origin 2>/dev/null; then
  ok "orchestrator fetch origin"
  if git -C "$ORCH_GIT" merge-base --is-ancestor "$FIX_COMMIT" origin/main 2>/dev/null; then
    ok "orchestrator ${FIX_COMMIT:0:8} merged in origin/main"
  else
    bad "orchestrator ${FIX_COMMIT:0:8} merged in origin/main"
  fi
else
  bad "orchestrator fetch origin (cannot verify the fix commit is merged)"
fi
blob_sha() { git -C "$ORCH_GIT" show "$1:orchestration/prompts/rules.md" 2>/dev/null | sha256sum | awk '{print $1}'; }
[ "$(blob_sha "${FIX_COMMIT}^")" = "b250c22770e999d5ef2092a3689247af8725f6cf1d5f01ed37b6296ea568456e" ] \
  && ok "${FIX_COMMIT:0:8}^ rules.md == checkpoint copy (b250c227)" || bad "${FIX_COMMIT:0:8}^ rules.md is not b250c227"
[ "$(blob_sha "$FIX_COMMIT")" = "18f8ea018234605002459cd98e59a9aaeddec235d8e022ff59f6ebd67766d607" ] \
  && ok "${FIX_COMMIT:0:8} rules.md == post-state pin (18f8ea01)" || bad "${FIX_COMMIT:0:8} rules.md is not 18f8ea01"
changed="$(git -C "$ORCH_GIT" show --format= --name-only "$FIX_COMMIT" 2>/dev/null | sort | tr '\n' ' ')"
[ "$changed" = "orchestration/prompts/rules.md src/prompt_builders/constants.py src/prompts/coder_system.txt " ] \
  && ok "${FIX_COMMIT:0:8} touches exactly the three prompt files" || bad "${FIX_COMMIT:0:8} file set is '$changed'"
say "  info  origin/main rules.md now: $(blob_sha origin/main | cut -c1-12)"
if [ -f "$POOL" ] && grep -q '"id": "simpleqa_general_00912"' "$POOL" && grep -q 'Jurgen Aschoff study medicine' "$POOL"; then
  ok "pool row simpleqa_general_00912 present in question_pool.jsonl"
else
  bad "pool row simpleqa_general_00912 not found in $POOL"
fi

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
  say "DRY RUN: would back up the originals to $BACKUP_DIR, apply the diffs above in place,"
  say "then write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL. Nothing written."
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
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-QUAL-T1 \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --evidence "benchmarks/prompts/question_pool.jsonl=eval pool; row simpleqa_general_00912 is the leaked few-shot example" \
  --evidence "$BACKUP_DIR=byte-exact originals of every rewritten file, with SHA256SUMS" \
  --validation "bash scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh --verify" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Every original restored; the receipt is kept at ${refused#$ROOT/} for reading."
fi

# ============================================================================ decision receipt + keyed index
INV_JSON="$TMPD/inventory.json"
python3 - "$INV_JSON" <<'PYEOF'
import json, os, sys
from pathlib import Path
ck = Path(os.environ["CKPT_ROOT"])
rows = sorted(str(p.relative_to(ck)) for p in ck.glob("*/prompts/rules.md") if not p.parent.parent.is_symlink())
json.dump(rows, open(sys.argv[1], "w"))
PYEOF
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$CONSOLIDATED_REL" "$INV_JSON" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$(sha256sum "$BACKUP_DIR/SHA256SUMS" | awk '{print $1}')" \
     "$(sha256sum "$POOL" | awk '{print $1}')" "$(sha256sum "$ROOT/$V10_REL" | awk '{print $1}')" <<'PYEOF'
import sys, json, os, re
(receipt, index, ts, consolidated_rel, inv_json, operator, sums_sha, pool_sha, v10_after) = sys.argv[1:10]
core = open(os.path.join(os.environ["TMPD"], "core.py"), encoding="utf-8").read()
pin = lambda name: re.search(rf'^{name} = "([0-9a-f]{{64}})"', core, re.M).group(1)
gate = os.environ["GATE_ID"]
doc = {
  "schema": "epyc.autopilot.checkpoint_prompt_repin.v1",
  "decision": "CKPT-PROMPT-LEAK-REPIN",
  "gate_id": gate,
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "operator_decision": "2026-09-16 option A: close the eval-leak rewind hole",
  "leak": {
    "pool_row": "simpleqa_general_00912",
    "pool_row_text": "At which university did Jurgen Aschoff study medicine? -> University of Bonn.",
    "related_pool_row": "simpleqa_general_00795 (second Aschoff row; no shingle in any checkpoint)",
    "file": "orchestration/prompts/rules.md, Example 4b (question line and web_research query line)",
    "mechanism": "StructuralLab.restore_checkpoint() copies <checkpoint>/prompts/ over the live prompts; production_best -> multitier_v10_20260810 carried the leaked copy, so any rollback re-introduced it",
  },
  "evidence": {
    "orchestrator_commit": os.environ["FIX_COMMIT"],
    "orchestrator_commit_note": "replaced the example in the tracked rules.md and DEFAULT_ROOT_LM_RULES; merged in epyc-orchestrator origin/main (preflight-verified)",
    "question_pool": {"path": "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl", "sha256": pool_sha},
    "backup_dir": os.environ["BACKUP_DIR"],
    "backup_sha256sums": sums_sha,
    "scan": "grep for Aschoff / University of Bonn / HumanEval/55 solution code, plus 8-token shingles (MHS-3 tokenisation, pool DF<32) of simpleqa_general_00912, simpleqa_general_00795 and sv_HE-R{,+}_HumanEval/55::sol0-4 over every checkpoint file and the live strategy store",
  },
  "equivalence": "Only the few-shot example changed. Each patched rules.md differs from its original in exactly two lines, both inside Example 4b (synthetic 'Halvard Oskeberg' / chemistry, same structure and token count), and is byte-identical to epyc-orchestrator 09bdb998:orchestration/prompts/rules.md, i.e. to production at that snapshot with only the example swapped (the checkpoint copies equal 09bdb998^ byte for byte).",
  "state": {
    "checkpoint_rules_md": {"paths": json.load(open(inv_json)), "sha256_before": pin("RULES_PRE"), "sha256_after": pin("RULES_POST")},
    "multitier_v10_20260810/checkpoint_meta.json": {"sha256_before": pin("META_PRE"), "sha256_after": pin("META_POST")},
    "multitier_v10_20260810 checkpoint_sha256": {"before": pin("CKSUM_PRE"), "after": pin("CKSUM_POST")},
    "artifacts/operator/ratify_multitier_baseline_v10_20260810.json": {"sha256_before": pin("RECEIPT_PRE"), "sha256_after": v10_after},
  },
  "rewind_verification": "restore_checkpoint() verifies no hash; the re-pinned manifest and v10 receipt are attestation. Post-state is checked by the ratify script's --verify (full v10 manifest, checkpoint_sha256, receipt mirror, leak scan).",
  "out_of_scope": [
    "episodic.db (every checkpoint and live): 4 memories whose context carries the HumanEval/55 problem text; eval-task routing memory, not a prompt copy",
    "orchestration/autopilot_state*.bak* and archived_backups/*: last_traces mention Aschoff; manual backups that no code path restores",
    "20260727_053326: no prompts/ directory, no hit",
  ],
  "consolidated_receipt": consolidated_rel,
  "applied_by": "scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh",
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
say "APPLIED, NOT STAGED, NOT COMMITTED. The checkpoint copies are untracked orchestrator files and"
say "are already patched in place (originals in $BACKUP_DIR). Commit exactly these four paths:"
say ""
say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
say "    git -C $ROOT diff --cached --stat"
say "    git -C $ROOT commit -m 'RATIFIED: checkpoint prompt copies re-pinned without the simpleqa_general_00912 few-shot leak (2026-09-16, option A)' -- ${COMMIT_PATHS[*]}"
