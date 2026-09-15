#!/bin/bash
# Ratify: create MEASUREMENT.md Annex V (distribution-divergence protocol P-KLD-1).
# Operator queue OP-38 · autokernel-rebuild-program.md R23-47 · intake rtx6kpro-20260907 item 4.5.
#
# WHY THIS IS A SCRIPT YOU RUN AND NOT A COMMIT AN AGENT MADE
# ----------------------------------------------------------
# MEASUREMENT.md:4 and section 5 make amendments HUMAN-ONLY, PR-reviewed, append-or-version.
# The protocols/ annexes "carry the SAME trust boundary and amendment rules as this file", and
# coordination/session-bus/human_only_paths.yaml lists both MEASUREMENT.md and
# measurement/protocols/*.md. Creating a seventh annex is the same class of change as the
# 2026-08-23 Annex D creation (scripts/operator/ratify_measurement_annex_d_20260823.sh).
# This script copies that structure.
#
# THE GAP IT CLOSES
# -----------------
# MEASUREMENT.md section 2 has no divergence protocol of any kind. Two campaigns nonetheless quote
# KLD / PPL / top-1 numbers as gate evidence. The INF-70 B7 and B4 quality gates both rest on
# llama-perplexity's per-token "±" and on sigma multiples built from it, on a MoE, with no route
# control. Section 1 of the decision package lists every affected claim:
# artifacts/operator/op38-pkld-decision-20260915.md.
#
# WHAT IT DOES
#   1. installs artifacts/operator/staged/p-kld-annex-20260915.md, BYTE-IDENTICAL, as
#      measurement/protocols/divergence.md (Annex V, 392 lines). SHA-256 is pinned below and
#      verified both before and after the copy.
#   2. MEASUREMENT.md layout sentence      "six annexes" -> "seven annexes"
#   3. MEASUREMENT.md annex key            adds  **V** = measurement/protocols/divergence.md
#   4. MEASUREMENT.md section-2 registry   adds the P-KLD-1 row, RATIFIED
#   5. MEASUREMENT.md CHANGELOG            prepends the 2026-09-15 amendment entry
#   6. emits the section-5 consolidated receipt (scripts/operator/ratification_receipt.py), plus
#      the decision receipt artifacts/operator/ratify_p_kld_divergence_protocol_20260915.json and
#      its keyed index artifacts/operator/receipts/RATIFY-P-KLD-1-20260915.json
#
# SCOPE. This ratifies protocol TEXT. No measurement is taken, re-labelled or edited, and no
# threshold, gate or code changes. Pre-existing divergence numbers become demote-to-prior through
# Annex V section V10. Their primary records are never touched. Nothing here starts a process,
# touches a kernel tree or takes compute.
#
# PINS: refuse on any mismatch.
#   annex (staged and installed)  094c6c19651be15bb193d29f828224846b325bd76eb5468e1a0d2f2563d5136f
#   MEASUREMENT.md pre-state      45c7e3a31ccc7c453d66b00124011a5bbbf9f44eaa90510d4cb3f75a1ae49dec
#                                 (origin/main as of 0fa742992; last touched by b05c4433 on 2026-09-08)
#   distillation source           rtx6kpro@44e817b kld/README.md
#                                 sha256 b1501772150998a3546a0d864726f19eaa0cb880f7d7db51c1f93df43c803346
# If MEASUREMENT.md has moved, this bundle is REGENERATED, never forced or fuzzed.
# A stale checkout (the /workspace shared clone lagged origin/main by 340 commits on
# 2026-09-15, without the 2026-09-08 blocks) is refused for the same reason.
#
# ALL OR NOTHING. Two half-applied states are worse than no change: a registry row pointing at a
# missing annex, and an annex with no registry row. Preflight refuses the whole bundle on any
# single mismatch. If postflight or the receipt fails, apply restores MEASUREMENT.md from backup
# and removes the annex.
#
# Usage (ROOT = an epyc-root checkout whose MEASUREMENT.md matches the pin; default /workspace):
#   bash artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh --dry-run   # preflight only, writes nothing
#   bash artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh --apply     # apply + receipts, no commit
#   bash artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh --commit    # apply + receipts + commit
#   ROOT=/mnt/raid0/llm/worktrees/sub-pkld bash <this script> --commit              # on the package branch
#
# Idempotent: when the annex is installed at the pinned hash, the row is registered and the
# receipt exists, a re-run prints ALREADY RATIFIED and exits 0 without writing.
# No process probes, no process management, no network.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

ROOT="${ROOT:-/workspace}"
MEAS="$ROOT/MEASUREMENT.md"
PROTO_DIR="$ROOT/measurement/protocols"
ANNEX="$PROTO_DIR/divergence.md"
ANNEX_REL="measurement/protocols/divergence.md"
STAGED="${STAGED:-$SCRIPT_DIR/staged/p-kld-annex-20260915.md}"
GATE_ID="RATIFY-P-KLD-1-20260915"
RECEIPT_REL="artifacts/operator/ratify_p_kld_divergence_protocol_20260915.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
INDEX="$ROOT/$INDEX_REL"
CONSOLIDATED_REL="artifacts/operator/receipts/ratify-p-kld-1-20260915.receipt.json"
CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"

ANNEX_SHA256="094c6c19651be15bb193d29f828224846b325bd76eb5468e1a0d2f2563d5136f"
MEAS_PRE_SHA256="45c7e3a31ccc7c453d66b00124011a5bbbf9f44eaa90510d4cb3f75a1ae49dec"
SOURCE_README_SHA256="b1501772150998a3546a0d864726f19eaa0cb880f7d7db51c1f93df43c803346"
ROW_NEEDLE='| P-KLD-1 | Teacher-forced next-token distribution divergence'

MODE=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply)   MODE="apply" ;;
    --commit)  MODE="commit" ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done
if [ -z "$MODE" ]; then
  echo "usage: $0 --dry-run | --apply | --commit   (no default: choose explicitly)" >&2
  exit 64
fi

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
[ -f "$MEAS" ]   || die "MEASUREMENT.md not found at $MEAS"
[ -d "$PROTO_DIR" ] || die "annex directory not found at $PROTO_DIR"
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] \
  || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py; a ratification without the consolidated receipt is refused"

# ---------------------------------------------------------------- staged annex pin
[ -f "$STAGED" ] || die "staged annex not found at $STAGED"
got="$(sha "$STAGED")"
[ "$got" = "$ANNEX_SHA256" ] || die "staged annex hash mismatch: expected $ANNEX_SHA256, found $got. The text you reviewed is not the text that would be installed."

# ---------------------------------------------------------------- idempotence
row_present=0; grep -qF -- "$ROW_NEEDLE" "$MEAS" && row_present=1
if [ -f "$ANNEX" ]; then
  inst="$(sha "$ANNEX")"
  [ "$inst" = "$ANNEX_SHA256" ] || die "$ANNEX exists with hash $inst, not the pinned $ANNEX_SHA256. Something else occupies Annex V; resolve by hand."
  if [ "$row_present" -eq 1 ] && [ -f "$RECEIPT" ]; then
    say "ALREADY RATIFIED: $ANNEX_REL is installed at the pinned hash, P-KLD-1 is registered and $RECEIPT_REL exists. Nothing to do."
    exit 0
  fi
  die "half-applied state: annex installed (row_present=$row_present, receipt_present=$([ -f "$RECEIPT" ] && echo 1 || echo 0)). Resolve by hand."
fi
[ "$row_present" -eq 1 ] && die "half-applied state: MEASUREMENT.md registers P-KLD-1 but $ANNEX_REL is missing. Resolve by hand."
[ -f "$RECEIPT" ] && die "half-applied state: $RECEIPT_REL exists but the annex is missing. Resolve by hand."
[ -f "$INDEX" ]   && die "keyed index $INDEX_REL already exists: this gate is already spent. Double-signing is refused."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT) =="
fail=0
meas_pre="$(sha "$MEAS")"
if [ "$meas_pre" != "$MEAS_PRE_SHA256" ]; then
  printf '  FAIL  %-50s expected %s\n        %-50s found    %s\n' "MEASUREMENT.md pre-state hash" "$MEAS_PRE_SHA256" "" "$meas_pre"
  fail=1
else
  printf '  ok    %-50s (%s)\n' "MEASUREMENT.md pre-state hash" "${meas_pre:0:12}"
fi
chk() { # chk <expected-count> <label> <needle>
  local want="$1" label="$2" needle="$3" got
  got="$(grep -cF -- "$needle" "$MEAS" || true)"
  if [ "$got" != "$want" ]; then printf '  FAIL  %-50s expected %s, found %s\n' "$label" "$want" "$got"; fail=1
  else printf '  ok    %-50s (%s)\n' "$label" "$got"; fi
}
chk 1 "layout sentence (six annexes)"        'six annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this'
chk 1 "annex key line (D, terminal)"         '**D** = `measurement/protocols/determinism-parity.md`.'
chk 1 "section-2 anchor row (P-NONDET-1)"    '| P-NONDET-1 | Run-to-run non-determinism detector (N >= 10 identical calls in ONE process) |'
chk 1 "CHANGELOG anchor (2026-09-08 entry)"  '- **2026-09-08 (v2.x)** — AMENDMENT: three appendix blocks ratified as ONE decision out of the'
chk 1 "BOUNDED-NULL-1 block (cited by annex)" '## BOUNDED-NULL-1 — a null needs its power and its fired-knob control'
chk 0 "annex letter V not already in use"    '**V** = `measurement/protocols/'
chk 0 "divergence.md not already referenced" 'divergence.md'

n_annex="$(find "$PROTO_DIR" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [ "$n_annex" != "6" ]; then printf '  FAIL  %-50s expected 6, found %s\n' "annex files on disk" "$n_annex"; fail=1
else printf '  ok    %-50s (6)\n' "annex files on disk"; fi

# Targets must carry no unrelated edits. Otherwise a commit would sweep a peer session's hunk
# into this amendment (shared-clone hazard).
dirty="$(git -C "$ROOT" status --porcelain -- MEASUREMENT.md "$ANNEX_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-50s\n%s\n' "targets clean in git" "$dirty"; fail=1
else printf '  ok    %-50s\n' "targets clean in git"; fi

if [ "$fail" -ne 0 ]; then
  die "preflight failed: $ROOT is not in the state this bundle was prepared against (origin/main 0fa742992). Stale checkout: fast-forward it first. Moved constitution: regenerate the bundle. Nothing written."
fi
say "  preflight clean"

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "DRY RUN: would install $ANNEX_REL (pinned ${ANNEX_SHA256:0:12}), apply 4 edits to MEASUREMENT.md,"
  say "and write $RECEIPT_REL, $INDEX_REL and $CONSOLIDATED_REL. Nothing written."
  exit 0
fi

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BACKUP="$(mktemp)"; cp "$MEAS" "$BACKUP"
PRE="$(mktemp)"
restore() {
  cp "$BACKUP" "$MEAS"
  rm -f "$ANNEX" "$RECEIPT" "$INDEX"
}

say ""
say "== apply =="
python3 "$ROOT"/scripts/operator/ratification_receipt.py capture --repo-root "$ROOT" \
  --state MEASUREMENT.md --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"

cp "$STAGED" "$ANNEX"
inst="$(sha "$ANNEX")"
if [ "$inst" != "$ANNEX_SHA256" ]; then
  restore; die "installed annex hash $inst != pinned $ANNEX_SHA256; removed. Nothing changed."
fi
say "  installed $ANNEX_REL (${inst:0:12})"

if ! python3 - "$MEAS" <<'PYEOF'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text(encoding="utf-8")
EDITS = [
 ("layout sentence",
  "six annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this",
  "seven annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this"),
 ("annex key",
  "**D** = `measurement/protocols/determinism-parity.md`.",
  "**D** = `measurement/protocols/determinism-parity.md`,\n**V** = `measurement/protocols/divergence.md`."),
 ("section-2 row",
  "| P-NONDET-1 | Run-to-run non-determinism detector (N >= 10 identical calls in ONE process) | bit-identical / not; max abs Δ across repeats (↓) | \U0001F4CB staged 2026-08-23 | D |",
  "| P-NONDET-1 | Run-to-run non-determinism detector (N >= 10 identical calls in ONE process) | bit-identical / not; max abs Δ across repeats (↓) | \U0001F4CB staged 2026-08-23 | D |\n"
  "| P-KLD-1 | Teacher-forced next-token distribution divergence between a named reference R and candidate Q of the same model (quantization/codec, precision swap, kernel/route, KV type); on a MoE, codec attribution requires a route-pinned R×Q cell | mean KL(R‖Q) nats (↓) with a source-cluster bootstrap CI; ln PPL ratio and top-1 agreement secondary — **not a claim** without a declared estimand, and **never** against a universal band | ✅ 2026-09-15 | V |"),
 ("CHANGELOG",
  "- **2026-09-08 (v2.x)** — AMENDMENT: three appendix blocks ratified as ONE decision out of the",
  "- **2026-09-15 (v2.x)** — AMENDMENT: **Annex V** (`measurement/protocols/divergence.md`) created as a\n"
  "  **seventh** annex holding `P-KLD-1`, the first protocol for any KL-divergence, perplexity or top-1\n"
  "  agreement number; until now two campaigns quoted divergence numbers with no protocol behind them.\n"
  "  Supersedes the layout sentence (`six` → `seven`) and the annex key line; §2 gains one row. Load-bearing\n"
  "  content: full-vocabulary only, with `llama-perplexity --kl-divergence` declared a lossy, truncated\n"
  "  instrument (`uint16` base window of 16 nats, reference entries below −16 nats dropped); FP64 summary\n"
  "  sums; a declared estimand before capture; a source-document-cluster bootstrap, never the tool's\n"
  "  per-token `±` or a σ multiple built from it; no model-independent bands; a fail-closed runner and a\n"
  "  durable receipt; and, on a MoE, no attribution to the codec without a route-pinned `R×Q` cell.\n"
  "  Defines how PPL, top-1 agreement, coherence and speculative `α` relate to KLD (none substitutes for\n"
  "  it) and demotes earlier divergence numbers to prior unless their receipts prove every field.\n"
  "  Distilled from `local-inference-lab/rtx6kpro@44e817b` `kld/README.md` (research intake\n"
  "  2026-09-07, item 4.5; autokernel-rebuild R23-47; operator queue OP-38).\n\n"
  "- **2026-09-08 (v2.x)** — AMENDMENT: three appendix blocks ratified as ONE decision out of the"),
]
for label, old, new in EDITS:
    n = t.count(old)
    if n != 1:
        sys.exit(f"edit '{label}': anchor occurs {n}x, expected 1 -- aborting")
    t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print(f"  applied {len(EDITS)} edits to MEASUREMENT.md")
PYEOF
then
  restore; die "edit stage failed; MEASUREMENT.md restored and annex removed. Nothing changed."
fi

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pchk() { local want="$1" label="$2" needle="$3" got
  got="$(grep -cF -- "$needle" "$MEAS" || true)"
  if [ "$got" != "$want" ]; then printf '  FAIL  %-50s expected %s, found %s\n' "$label" "$want" "$got"; pf=1
  else printf '  ok    %-50s (%s)\n' "$label" "$got"; fi
}
pchk 1 "layout says seven annexes"        'seven annexes in `measurement/protocols/`'
pchk 0 "layout no longer says six"        'six annexes in `measurement/protocols/`'
pchk 1 "annex key registers V"            '**V** = `measurement/protocols/divergence.md`.'
pchk 1 "annex key keeps D"                '**D** = `measurement/protocols/determinism-parity.md`,'
pchk 1 "P-KLD-1 registered once"          '| P-KLD-1 |'
pchk 1 "P-NONDET-1 row preserved"         '| P-NONDET-1 |'
pchk 1 "CHANGELOG entry present"          '- **2026-09-15 (v2.x)** — AMENDMENT: **Annex V**'
pchk 1 "2026-09-08 CHANGELOG preserved"   '- **2026-09-08 (v2.x)** — AMENDMENT: three appendix blocks'

[ "$(sha "$ANNEX")" = "$ANNEX_SHA256" ] \
  && printf '  ok    %-50s\n' "annex still at pinned hash" \
  || { printf '  FAIL  %-50s\n' "annex still at pinned hash"; pf=1; }

n_after="$(find "$PROTO_DIR" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [ "$n_after" != "7" ]; then printf '  FAIL  %-50s expected 7, found %s\n' "annex files on disk" "$n_after"; pf=1
else printf '  ok    %-50s (7)\n' "annex files on disk"; fi

# Additions only, except the two lines rewritten in place. Line-count delta is invariant: +16.
if python3 - "$BACKUP" "$MEAS" <<'PYEOF'
import sys, difflib
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
removed = [l[1:] for l in difflib.unified_diff(a, b, lineterm="", n=0)
           if l.startswith("-") and not l.startswith("---")]
expected_removed = {
    "**D** = `measurement/protocols/determinism-parity.md`.",
}
ok = True
if len(b) - len(a) != 16:
    print(f"  FAIL  line delta expected +16, found {len(b) - len(a):+d}"); ok = False
for line in removed:
    if line not in expected_removed and "six annexes in `measurement/protocols/`" not in line:
        print(f"  FAIL  unexpected removed line: {line[:90]!r}"); ok = False
if len(removed) > 2:
    print(f"  FAIL  {len(removed)} lines removed, at most 2 expected"); ok = False
if ok:
    print(f"  ok    additions-only diff (+{len(b) - len(a)} net, {len(removed)} rewritten in place)")
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi

if [ "$pf" -ne 0 ]; then
  restore
  die "postflight failed: MEASUREMENT.md restored from backup and annex removed. Nothing changed."
fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
mkdir -p "$ROOT/artifacts/operator/receipts"
receipt_rc=0
python3 "$ROOT"/scripts/operator/ratification_receipt.py emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id P-KLD-1 --protocol-new \
  --anchor '**V** = `measurement/protocols/divergence.md`.' \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --no-evidence-reason "protocol-text adoption; no new measurement. Distilled from local-inference-lab/rtx6kpro@44e817b kld/README.md (sha256 $SOURCE_README_SHA256) via docs/research-intake/rtx6kpro-20260907.md item 4.5; annex sha256 $ANNEX_SHA256" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $ANNEX_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#$ROOT/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
MEAS_POST_SHA256="$(sha "$MEAS")"
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$ANNEX_SHA256" "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" \
     "$SOURCE_README_SHA256" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" "${RATIFY_OPERATOR:-${USER:-unknown}}" <<'PYEOF'
import sys, json, os
(receipt, index, ts, annex_sha, pre_sha, post_sha, src_sha, gate, consolidated_rel,
 receipt_rel, operator) = sys.argv[1:12]
doc = {
  "schema": "epyc.measurement.annex_creation.v1",
  "decision": "CREATE-ANNEX-V",
  "gate_id": gate,
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "annex_letter": "V",
  "annex_path": "measurement/protocols/divergence.md",
  "annex_sha256": annex_sha,
  "measurement_md_sha256_before": pre_sha,
  "measurement_md_sha256_after": post_sha,
  "protocols_registered": [
    {"id": "P-KLD-1", "status": "ratified",
     "emits": "mean KL(R||Q) nats (lower-better) with a source-cluster bootstrap CI; ln PPL ratio and top-1 agreement secondary"}],
  "scope": ("Protocol text only. No measurement is taken, relabelled or edited. Divergence numbers "
            "recorded before this annex are demote-to-prior under Annex V section V10 unless their "
            "receipts prove every V9 field."),
  "measurement_md_edits": ["layout six->seven", "annex key +V", "section-2 +P-KLD-1",
                           "CHANGELOG 2026-09-15 entry"],
  "consolidated_receipt": consolidated_rel,
  "provenance": {
    "source": "local-inference-lab/rtx6kpro@44e817b kld/README.md",
    "source_sha256": src_sha,
    "intake": "docs/research-intake/rtx6kpro-20260907.md item 4.5",
    "handoff": "handoffs/active/autokernel-rebuild-program.md R23-47",
    "operator_queue": "OP-38",
    "decision_package": "artifacts/operator/op38-pkld-decision-20260915.md",
  },
  "applied_by": "artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh",
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify",
               "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}")
print(f"  keyed index:      {index}")
PYEOF
then
  restore; rm -f "$CONSOLIDATED"
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi
rm -f "$BACKUP" "$PRE"

COMMIT_PATHS=(MEASUREMENT.md "$ANNEX_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")

# ---------------------------------------------------------------- commit
if [ "$MODE" = "commit" ]; then
  say ""
  say "== commit =="
  MSG="$(mktemp)"
  cat > "$MSG" <<'EOF_MSG'
RATIFIED: P-KLD-1 — MEASUREMENT.md Annex V, distribution-divergence protocol (OP-38, 2026-09-15)

Seventh annex (measurement/protocols/divergence.md). It is the first protocol for any KL-divergence,
perplexity or top-1 agreement number. Two campaigns had been quoting such numbers as gate evidence
with no protocol behind them.

Load-bearing content:
- full-vocabulary only, with llama-perplexity --kl-divergence declared a lossy, truncated instrument:
  uint16 16-nat base window, reference entries below -16 nats dropped;
- FP64 summary sums;
- an estimand declared before capture;
- a source-document-cluster bootstrap, never the tool's per-token "±" or a sigma multiple built
  from it;
- no model-independent bands;
- a fail-closed runner with durable receipts;
- on a MoE, no attribution to the codec without a route-pinned RxQ cell.

The annex also defines how PPL, top-1 agreement, coherence and speculative alpha relate to KLD, and
demotes earlier divergence numbers to prior unless their receipts prove every field.

No measurement, threshold, gate or code changes.
Distilled from local-inference-lab/rtx6kpro@44e817b kld/README.md (research intake 2026-09-07, item
4.5; autokernel-rebuild R23-47). Applied by operator ratification via
artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh; the annex is installed at its pinned
SHA-256. Receipts: artifacts/operator/ratify_p_kld_divergence_protocol_20260915.json and
artifacts/operator/receipts/ratify-p-kld-1-20260915.receipt.json.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF_MSG
  # Commit from a private index seeded from HEAD, so nothing another session staged rides along.
  GI="$(mktemp -u)"
  if ! { GIT_INDEX_FILE="$GI" git -C "$ROOT" read-tree HEAD \
         && GIT_INDEX_FILE="$GI" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
         && GIT_INDEX_FILE="$GI" git -C "$ROOT" diff --cached --stat \
         && GIT_INDEX_FILE="$GI" git -C "$ROOT" commit -q -F "$MSG"; }; then
    rm -f "$GI" "$MSG"
    say "COMMIT REFUSED (hook or git error, shown above). The amendment is APPLIED and NOT committed."
    say "Nothing was rolled back. Read the refusal, then commit the paths below by hand or re-run nothing:"
    printf '    %s\n' "${COMMIT_PATHS[@]}"
    exit 1
  fi
  rm -f "$GI" "$MSG"
  # The shared index still holds the pre-amendment blobs for these paths; left alone, a later
  # commit from that index would silently REVERT this ratification. Re-sync exactly these paths.
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}"
  say "  committed $(git -C "$ROOT" rev-parse --short HEAD) (not pushed)"
else
  say ""
  say "APPLIED, NOT COMMITTED. Review the diff and the receipts, then either re-run nothing and:"
  say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
  say "    git -C $ROOT commit"
  say "  (the targets were verified clean in preflight, so adding them whole takes no peer hunk)"
fi

say ""
say "DONE. Annex V created; P-KLD-1 registered RATIFIED. Next: tick R23-47 in"
say "handoffs/active/autokernel-rebuild-program.md and remove the OP-38 row from the operator queue."
