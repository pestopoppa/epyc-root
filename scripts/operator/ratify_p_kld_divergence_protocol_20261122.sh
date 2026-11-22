#!/bin/bash
# ratify_p_kld_divergence_protocol_20261122.sh — P-KLD-1: create MEASUREMENT.md Annex V
# (measurement/protocols/divergence.md, distribution-divergence protocol), with its section-2
# registry row, annex-key line, layout sentence and CHANGELOG entry.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_p_kld_divergence_protocol_20261122.sh
#   Apply + receipts + commit (ONE):    RATIFY_OPERATOR=<name> bash scripts/operator/ratify_p_kld_divergence_protocol_20261122.sh --apply
#   Apply + receipts, no commit:        RATIFY_OPERATOR=<name> bash ... --apply --no-commit
#   Verify the post-state (read-only):  bash scripts/operator/ratify_p_kld_divergence_protocol_20261122.sh --verify
#
# --apply asks you to type RATIFY on the terminal before it writes anything (the operator ack).
#
# Operator queue OP-38 · autokernel-rebuild R23-47 · research intake rtx6kpro-20260907 item 4.5.
# Decision package: artifacts/operator/op38-pkld-decision-20260915.md.
# REBUILT 2026-11-22 from the 2026-09-15 package (branch sub/op38-pkld-package,
# artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh), which pinned a MEASUREMENT.md
# pre-state (45c7e3a3...) that no longer exists and was only ever `bash -n` checked. Changes:
#   - MEASUREMENT.md pre-state re-pinned to origin/main as of 2026-11-22 (92199cbb...);
#   - registry row appended at the END of the section-2 table (after P-SERVE-1), date 2026-11-22;
#   - CHANGELOG entry prepended above the newest entry (2026-11-19 P-SERVE-1);
#   - annex text unchanged except its header comment and a new §V11 that reconciles it with
#     Annex K P-AK-SEARCH-1-A5 (graph-fusion KLD keep gate, ratified 2026-11-09, after the draft);
#   - modern ratifier conventions: typed operator (lib/ratify_operator.sh), --review/--apply/--verify,
#     consolidated receipt beside the decision receipt, private-index commit, post-state pins.
#
# WHY IT NEEDS YOU. MEASUREMENT.md and measurement/protocols/*.md are human-amendment-only
# (coordination/session-bus/human_only_paths.yaml; invariant 15). An agent prepared this bundle and
# apply-tested it in a throwaway worktree. Only the operator applies it.
#
# SCOPE. Protocol TEXT only. No measurement is taken, re-labelled or edited; no threshold, gate or
# code changes. Earlier divergence numbers become demote-to-prior through Annex V §V10; their primary
# records are never touched. No process, compute or network.
#
# PINS (refuse on any mismatch; if a target moved, REGENERATE the bundle, never force or fuzz):
#   staged annex                 1b407e27d5aa4a8769af9df17f034988cf6320fd60945032895774a81f54bdc6
#   MEASUREMENT.md pre-state     92199cbbfa3500da8a41cd6803fe7ba99165365f96b4a5b15183a16a2f580152
#   MEASUREMENT.md post-state    see MEAS_POST_SHA256 below
#   distillation source          rtx6kpro@44e817b kld/README.md
#                                sha256 b1501772150998a3546a0d864726f19eaa0cb880f7d7db51c1f93df43c803346
#
# ALL OR NOTHING. If postflight or the receipt fails, apply restores MEASUREMENT.md and removes the
# annex and receipts. IDEMPOTENT: a re-run on the ratified state prints ALREADY RATIFIED.
# ROOT defaults to the checkout this script lives in.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_p_kld_divergence_protocol_20261122.sh"

STAGED_REL="artifacts/operator/staged/p-kld-annex-20261122.md"
STAGED="$ROOT/$STAGED_REL"
MEAS_REL="MEASUREMENT.md"
MEAS="$ROOT/$MEAS_REL"
PROTO_DIR="$ROOT/measurement/protocols"
ANNEX_REL="measurement/protocols/divergence.md"
ANNEX="$ROOT/$ANNEX_REL"
GATE_ID="RATIFY-P-KLD-1-20261122"
RECEIPT_REL="artifacts/operator/ratify_p_kld_divergence_protocol_20261122.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_p_kld_divergence_protocol_20261122.receipt.json"
RECEIPT="$ROOT/$RECEIPT_REL"; INDEX="$ROOT/$INDEX_REL"; CONSOLIDATED="$ROOT/$CONSOLIDATED_REL"
COMMIT_PATHS=("$MEAS_REL" "$ANNEX_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_SUBJECT="RATIFIED: P-KLD-1 — MEASUREMENT.md Annex V, distribution-divergence protocol (OP-38, 2026-11-22)"

ANNEX_SHA256="1b407e27d5aa4a8769af9df17f034988cf6320fd60945032895774a81f54bdc6"
MEAS_PRE_SHA256="92199cbbfa3500da8a41cd6803fe7ba99165365f96b4a5b15183a16a2f580152"
MEAS_POST_SHA256="258147f7ee517dce04e338797ac4962134ea1be8a891aacd6e994263242b926a"
SOURCE_README_SHA256="b1501772150998a3546a0d864726f19eaa0cb880f7d7db51c1f93df43c803346"
ROW_PREFIX='| P-KLD-1 |'
KEY_LINE='**V** = `measurement/protocols/divergence.md`.'
CHANGELOG_ANCHOR='- **2026-11-22 (v2.x)** — AMENDMENT: **Annex V** (`measurement/protocols/divergence.md`) created as a'

MODE="review"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --review|--dry-run) MODE="review" ;;
    --apply)            MODE="apply" ;;
    --verify)           MODE="verify" ;;
    --no-commit)        DO_COMMIT=0 ;;
    -h|--help)          sed -n '2,45p' "$SCRIPT_PATH"; exit 0 ;;
    *) echo "usage: $0 [--review | --apply [--no-commit] | --verify]   (default: --review, writes nothing)" >&2; exit 64 ;;
  esac
done
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
[ "$MODE" != "apply" ] || ratify_require_operator
if [ "$DO_COMMIT" -eq 0 ] && [ "$MODE" != "apply" ]; then echo "usage: --no-commit only makes sense with --apply" >&2; exit 64; fi

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3 >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git >/dev/null || die "git not on PATH"
[ -f "$MEAS" ] || die "MEASUREMENT.md not found under ROOT=$ROOT"
[ -d "$PROTO_DIR" ] || die "annex directory not found at $PROTO_DIR"
[ -f "$ROOT/scripts/operator/ratification_receipt.py" ] || die "section-5 receipt tool missing at $ROOT/scripts/operator/ratification_receipt.py"
[ -f "$STAGED" ] || die "staged annex not found at $STAGED"
got="$(sha "$STAGED")"
[ "$got" = "$ANNEX_SHA256" ] || die "staged annex hash mismatch: expected $ANNEX_SHA256, found $got. The text you reviewed is not the text that would be installed."

# The four MEASUREMENT.md edits. Each anchor must occur exactly once. Used by apply and review.
apply_edits() { # apply_edits <in> <out>
  python3 - "$1" "$2" <<'PYEOF'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding="utf-8").read()
L = t.split("\n")
serve = [i for i, l in enumerate(L) if l.startswith("| P-SERVE-1 |")]
if len(serve) != 1:
    sys.exit(f"edit 'section-2 row': P-SERVE-1 row occurs {len(serve)}x, expected 1")
L.insert(serve[0] + 1,
  "| P-KLD-1 | Teacher-forced next-token distribution divergence between a named reference R and candidate Q of the same model (quantization/codec, precision swap, kernel/route, KV type, graph change); on a MoE, codec attribution requires a route-pinned R×Q cell | mean KL(R‖Q) nats (↓) with a source-cluster bootstrap CI; ln PPL ratio and top-1 agreement secondary — **not a claim** without a declared estimand, and **never** against a universal band | ✅ 2026-11-22 | V |")
t = "\n".join(L)
EDITS = [
 ("layout sentence",
  "six annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this",
  "seven annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this"),
 ("annex key",
  "**D** = `measurement/protocols/determinism-parity.md`.",
  "**D** = `measurement/protocols/determinism-parity.md`,\n**V** = `measurement/protocols/divergence.md`."),
 ("CHANGELOG",
  "- **2026-11-19 (v2.x)** — AMENDMENT (Annex K, new protocol `P-SERVE-1`): the kernel-champion serving",
  "- **2026-11-22 (v2.x)** — AMENDMENT: **Annex V** (`measurement/protocols/divergence.md`) created as a\n"
  "  **seventh** annex holding `P-KLD-1`, the protocol for any KL-divergence, perplexity or top-1\n"
  "  agreement number used to compare two artifacts, kernels, routes or configurations of one model.\n"
  "  Supersedes the layout sentence (`six` → `seven`) and the annex key line; §2 gains one row. Load-bearing\n"
  "  content: full-vocabulary only, with `llama-perplexity --kl-divergence` declared a lossy, truncated\n"
  "  instrument (`uint16` base window of 16 nats, reference entries below −16 nats dropped); FP64 summary\n"
  "  sums; a declared estimand before capture; a source-document-cluster bootstrap, never the tool's\n"
  "  per-token `±` or a σ multiple built from it; no model-independent bands; a fail-closed runner and a\n"
  "  durable receipt; and, on a MoE, no attribution to the codec without a route-pinned `R×Q` cell.\n"
  "  Defines how PPL, top-1 agreement, coherence and speculative `α` relate to KLD (none substitutes for\n"
  "  it) and demotes earlier divergence numbers to prior unless their receipts prove every field. §V11\n"
  "  leaves Annex K `P-AK-SEARCH-1-A5` (graph-fusion KLD keep gate) operative as a search verdict.\n"
  "  Distilled from `local-inference-lab/rtx6kpro@44e817b` `kld/README.md` (research intake\n"
  "  2026-09-07, item 4.5; autokernel-rebuild R23-47; operator queue OP-38).\n\n"
  "- **2026-11-19 (v2.x)** — AMENDMENT (Annex K, new protocol `P-SERVE-1`): the kernel-champion serving"),
]
for label, old, new in EDITS:
    n = t.count(old)
    if n != 1:
        sys.exit(f"edit '{label}': anchor occurs {n}x, expected 1")
    t = t.replace(old, new, 1)
open(dst, "w", encoding="utf-8").write(t)
PYEOF
}

check_landed() { # check_landed <MEASUREMENT.md> <annex>
  local f=0 n
  for pair in "1|seven annexes in \`measurement/protocols/\`" "0|six annexes in \`measurement/protocols/\`" \
              "1|$KEY_LINE" "1|**D** = \`measurement/protocols/determinism-parity.md\`," \
              "1|$ROW_PREFIX" "1|| P-SERVE-1 |" "1|| P-NONDET-1 |" "1|$CHANGELOG_ANCHOR"; do
    want="${pair%%|*}"; needle="${pair#*|}"
    n="$(grep -cF -- "$needle" "$1" || true)"
    if [ "$n" != "$want" ]; then printf '  FAIL  %-55s expected %s found %s\n' "${needle:0:55}" "$want" "$n"; f=1; fi
  done
  [ "$(sha "$2")" = "$ANNEX_SHA256" ] || { printf '  FAIL  annex not at pinned hash\n'; f=1; }
  [ "$f" -eq 0 ] && printf '  ok    %-55s\n' "annex installed, key/row/layout/CHANGELOG present once"
  return "$f"
}

meas_now="$(sha "$MEAS")"

# ---------------------------------------------------------------- --verify (read-only)
if [ "$MODE" = "verify" ]; then
  say "== verify (ROOT=$ROOT, read-only) =="
  vf=0
  if [ "$meas_now" = "$MEAS_POST_SHA256" ]; then printf '  ok    %-55s (%s)\n' "MEASUREMENT.md post-state hash" "${meas_now:0:12}"
  else printf '  FAIL  MEASUREMENT.md post-state hash expected %s found %s\n' "$MEAS_POST_SHA256" "$meas_now"; vf=1; fi
  [ -f "$ANNEX" ] && { check_landed "$MEAS" "$ANNEX" || vf=1; } || { say "  FAIL  $ANNEX_REL missing"; vf=1; }
  for f in "$RECEIPT" "$INDEX" "$CONSOLIDATED"; do
    if [ -f "$f" ]; then printf '  ok    present: %s\n' "${f#"$ROOT"/}"; else printf '  FAIL  missing: %s\n' "${f#"$ROOT"/}"; vf=1; fi
  done
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ] && [ -f "$CONSOLIDATED" ]; then
    python3 - "$RECEIPT" "$INDEX" "$CONSOLIDATED" "$GATE_ID" "$RECEIPT_REL" "$ANNEX_SHA256" "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" <<'PYEOF' || vf=1
import json, sys
rp, ip, cp, gate, rrel, asha, mpre, mpost = sys.argv[1:9]
r = json.load(open(rp)); i = json.load(open(ip)); c = json.load(open(cp)); ok = True
def bad(m):
    global ok; ok = False; print("  FAIL  " + m)
if r.get("status") != "ratified" or r.get("gate_id") != gate or r.get("protocol_id") != "P-KLD-1": bad("decision receipt status/gate/protocol")
if not r.get("operator") or not r.get("applied_at"): bad("decision receipt operator/applied_at")
if r.get("annex_sha256") != asha: bad("decision receipt annex sha")
if r.get("state", {}).get("MEASUREMENT.md") != {"sha256_before": mpre, "sha256_after": mpost}: bad("decision receipt MEASUREMENT.md hashes")
if i.get("gate_id") != gate or i.get("status") != "ratified" or not str(i.get("receipt", "")).endswith(rrel): bad("keyed index")
if c.get("verdict") != "RATIFIED" or c.get("protocol_id") != "P-KLD-1" or c.get("ratification_id") != gate: bad(f"consolidated receipt verdict={c.get('verdict')!r}")
if ok: print("  ok    decision receipt, keyed index and consolidated receipt agree with the pins")
sys.exit(0 if ok else 1)
PYEOF
  fi
  dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo GIT-STATUS-FAILED)"
  if [ -n "$dirty" ]; then printf '  FAIL  five paths committed and clean at HEAD\n%s\n' "$dirty"; vf=1
  else printf '  ok    %-55s (%s)\n' "five paths committed and clean at HEAD" "$(git -C "$ROOT" rev-parse --short HEAD)"; fi
  [ "$vf" -eq 0 ] || { say "VERIFY FAILED: P-KLD-1 is not (fully) ratified in $ROOT."; exit 1; }
  say "VERIFIED: P-KLD-1 is ratified, receipted and committed in $ROOT."; exit 0
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ -f "$ANNEX" ]; then
  [ "$(sha "$ANNEX")" = "$ANNEX_SHA256" ] || die "$ANNEX_REL exists but not at the pinned hash; something else occupies Annex V. Resolve by hand."
  if [ "$meas_now" = "$MEAS_POST_SHA256" ] && [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: annex installed, MEASUREMENT.md at its post-state pin, receipts present. Nothing to do."
    say "Check it with: ROOT=$ROOT bash $SCRIPT_PATH --verify"; exit 0
  fi
  die "half-applied state: annex installed but MEASUREMENT.md/receipts are not in the ratified state. Resolve by hand."
fi
grep -qF -- "$ROW_PREFIX" "$MEAS" && die "half-applied state: MEASUREMENT.md registers P-KLD-1 but $ANNEX_REL is missing. Resolve by hand."
[ -f "$RECEIPT" ] && die "$RECEIPT_REL exists but the annex is missing. Resolve by hand."
[ -f "$INDEX" ] && die "keyed index $INDEX_REL already exists: this gate is already spent. Double-signing is refused."
[ -f "$CONSOLIDATED" ] && die "$CONSOLIDATED_REL already exists. Resolve by hand."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
printf '  ok    %-55s (%s)\n' "staged annex hash" "${ANNEX_SHA256:0:12}"
if [ "$meas_now" != "$MEAS_PRE_SHA256" ]; then
  printf '  FAIL  MEASUREMENT.md pre-state hash expected %s\n        found %s\n' "$MEAS_PRE_SHA256" "$meas_now"; fail=1
else printf '  ok    %-55s (%s)\n' "MEASUREMENT.md pre-state hash" "${meas_now:0:12}"; fi
n_annex="$(find "$PROTO_DIR" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [ "$n_annex" != "6" ]; then printf '  FAIL  annex files on disk expected 6, found %s\n' "$n_annex"; fail=1
else printf '  ok    %-55s (6)\n' "annex files on disk"; fi
if grep -qF 'divergence.md' "$MEAS"; then printf '  FAIL  divergence.md already referenced in MEASUREMENT.md\n'; fail=1
else printf '  ok    %-55s\n' "divergence.md not yet referenced"; fi
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo GIT-STATUS-FAILED)"
if [ -n "$dirty" ]; then printf '  FAIL  commit paths clean in git\n%s\n' "$dirty"; fail=1
else printf '  ok    %-55s\n' "commit paths clean in git"; fi
TMPD="$(mktemp -d)"; trap 'rm -rf "$TMPD"' EXIT
if apply_edits "$MEAS" "$TMPD/MEASUREMENT.md.new" && [ "$(sha "$TMPD/MEASUREMENT.md.new")" = "$MEAS_POST_SHA256" ]; then
  printf '  ok    %-55s (%s)\n' "edits reproduce the post-state pin" "${MEAS_POST_SHA256:0:12}"
else printf '  FAIL  edits do not reproduce the post-state pin %s\n' "$MEAS_POST_SHA256"; fail=1; fi
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main, 2026-11-22). Stale checkout: fast-forward it first. Moved constitution: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""; say "== MEASUREMENT.md diff =="
  diff -u "$MEAS" "$TMPD/MEASUREMENT.md.new" | sed "s#$TMPD/MEASUREMENT.md.new#MEASUREMENT.md (amended)#" || true
  say ""; say "== new annex: $ANNEX_REL (= $STAGED_REL, $(wc -l < "$STAGED") lines; read it there) =="
  say ""
  say "REVIEW ONLY: would install $ANNEX_REL, apply the diff above, write $RECEIPT_REL,"
  say "$INDEX_REL and $CONSOLIDATED_REL, and commit those five paths. Nothing written."
  say "Apply with: RATIFY_OPERATOR=<your-name> ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- operator ack
if [ "${PKLD_RATIFY_TEST_YES:-0}" = "1" ] && [ "${PKLD_RATIFY_TEST:-0}" = "1" ]; then
  say "(test mode: ack prompt skipped)"
else
  [ -r /dev/tty ] || die "no terminal to read the RATIFY ack from; run this interactively"
  printf '\nThis installs Annex V and amends MEASUREMENT.md in %s as operator "%s".\nType RATIFY to apply: ' "$ROOT" "$RATIFY_OPERATOR"
  IFS= read -r answer < /dev/tty || die "could not read from the terminal"
  [ "$answer" = "RATIFY" ] || die "ack was '$answer', not RATIFY. Nothing written."
fi

# ---------------------------------------------------------------- apply
APPLIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR="$RATIFY_OPERATOR"
cp "$MEAS" "$TMPD/MEASUREMENT.md.bak"
PRE="$TMPD/pre.json"
restore() { cp "$TMPD/MEASUREMENT.md.bak" "$MEAS"; rm -f "$ANNEX" "$RECEIPT" "$INDEX"; }
say ""; say "== apply =="
python3 "$ROOT"/scripts/operator/ratification_receipt.py capture --repo-root "$ROOT" \
  --state "$MEAS_REL" --out "$PRE" || die "could not snapshot the pre-amendment state; nothing written"
cp "$STAGED" "$ANNEX"
cp "$TMPD/MEASUREMENT.md.new" "$MEAS"
say "  installed $ANNEX_REL and amended $MEAS_REL"

# ---------------------------------------------------------------- postflight
say ""; say "== postflight =="
pf=0
[ "$(sha "$MEAS")" = "$MEAS_POST_SHA256" ] && printf '  ok    %-55s\n' "MEASUREMENT.md post-state hash" || { say "  FAIL  MEASUREMENT.md post-state hash"; pf=1; }
check_landed "$MEAS" "$ANNEX" || pf=1
n_after="$(find "$PROTO_DIR" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
[ "$n_after" = "7" ] && printf '  ok    %-55s (7)\n' "annex files on disk" || { say "  FAIL  annex files on disk: $n_after"; pf=1; }
if python3 - "$TMPD/MEASUREMENT.md.bak" "$MEAS" <<'PYEOF'
import sys, difflib
a = open(sys.argv[1], encoding="utf-8").read().split("\n"); b = open(sys.argv[2], encoding="utf-8").read().split("\n")
removed = [l[1:] for l in difflib.unified_diff(a, b, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
allowed = ("**D** = `measurement/protocols/determinism-parity.md`.", "six annexes in `measurement/protocols/`")
bad = [l for l in removed if not any(x in l for x in allowed)]
ok = not bad and len(removed) <= 2
for l in bad: print(f"  FAIL  unexpected removed line: {l[:90]!r}")
if ok: print(f"  ok    additions-only diff (+{len(b)-len(a)} net, {len(removed)} rewritten in place)")
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi
[ "$pf" -eq 0 ] || { restore; die "postflight failed: MEASUREMENT.md restored and annex removed. Nothing changed."; }
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""; say "== section-5 consolidated receipt =="
mkdir -p "$ROOT/artifacts/operator/receipts"
receipt_rc=0
python3 "$ROOT"/scripts/operator/ratification_receipt.py emit \
  --repo-root "$ROOT" --pre "$PRE" \
  --protocol-id P-KLD-1 --protocol-new \
  --anchor "$KEY_LINE" --anchor "$CHANGELOG_ANCHOR" \
  --ratification-id "$GATE_ID" --script "$SCRIPT_PATH" --operator "$OPERATOR" \
  --no-evidence-reason "protocol-text adoption; no new measurement. Distilled from local-inference-lab/rtx6kpro@44e817b kld/README.md (sha256 $SOURCE_README_SHA256) via docs/research-intake/rtx6kpro-20260907.md item 4.5; annex sha256 $ANNEX_SHA256" \
  --validation "bash scripts/validate/check_claims_grammar.sh --files $ANNEX_REL" \
  --out "$CONSOLIDATED" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="${CONSOLIDATED%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$CONSOLIDATED" ] && mv "$CONSOLIDATED" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/}."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$APPLIED_AT" "$GATE_ID" "$CONSOLIDATED_REL" "$RECEIPT_REL" "$OPERATOR" \
     "$ANNEX_SHA256" "$MEAS_PRE_SHA256" "$MEAS_POST_SHA256" "$SOURCE_README_SHA256" "$SCRIPT_REL" "$(sha "$SCRIPT_PATH")" "$STAGED_REL" <<'PYEOF'
import sys, json, os
(receipt, index, ts, gate, cons_rel, rrel, operator, annex_sha, pre, post, src_sha, script_rel, script_sha, staged_rel) = sys.argv[1:15]
doc = {
  "schema": "epyc.measurement.annex_creation.v1", "decision": "CREATE-ANNEX-V", "gate_id": gate,
  "ratified_at": ts, "applied_at": ts, "operator": operator, "status": "ratified",
  "protocol_id": "P-KLD-1", "annex_letter": "V", "annex_path": "measurement/protocols/divergence.md",
  "annex_sha256": annex_sha, "staged_text": {"path": staged_rel, "sha256": annex_sha},
  "state": {"MEASUREMENT.md": {"sha256_before": pre, "sha256_after": post}},
  "measurement_md_edits": ["layout six->seven", "annex key +V", "section-2 +P-KLD-1 (end of table)", "CHANGELOG 2026-11-22 entry"],
  "scope": "Protocol text only. No measurement is taken, relabelled or edited. Pre-annex divergence numbers are demote-to-prior under Annex V V10 unless their receipts prove every V9 field. V11 leaves Annex K P-AK-SEARCH-1-A5 operative.",
  "consolidated_receipt": cons_rel,
  "provenance": {"source": "local-inference-lab/rtx6kpro@44e817b kld/README.md", "source_sha256": src_sha,
    "intake": "docs/research-intake/rtx6kpro-20260907.md item 4.5", "handoff": "autokernel-rebuild R23-47",
    "operator_queue": "OP-38", "decision_package": "artifacts/operator/op38-pkld-decision-20260915.md",
    "rebuilt_from": "artifacts/operator/ratify_p_kld_divergence_protocol_20260915.sh (branch sub/op38-pkld-package)"},
  "applied_by": {"path": script_rel, "sha256": script_sha},
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify", "receipt": "/workspace/" + rrel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}\n  keyed index:      {index}")
PYEOF
then restore; rm -f "$CONSOLIDATED"; die "could not write the decision receipt or keyed index. Amendment rolled back."; fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""; say "APPLIED, NOT COMMITTED (--no-commit). Commit exactly: ${COMMIT_PATHS[*]}"
  say "Then: ROOT=$ROOT bash $SCRIPT_PATH --verify"; exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""; say "== commit on $BRANCH =="
PIDX="$TMPD/private.index"; MSGF="$TMPD/commit_msg.txt"
cat > "$MSGF" <<EOF
$COMMIT_SUBJECT

Seventh annex (measurement/protocols/divergence.md), the protocol for any
KL-divergence, perplexity or top-1 agreement number comparing two artifacts,
kernels, routes or configurations of one model. Full-vocabulary only, with
llama-perplexity --kl-divergence declared a lossy truncated instrument; FP64
sums; an estimand declared before capture; a source-cluster bootstrap, never
the tool's per-token "±"; no model-independent bands; fail-closed runner and
durable receipts; on a MoE, no codec attribution without a route-pinned RxQ
cell. Earlier divergence numbers are demote-to-prior (V10). V11 leaves Annex K
P-AK-SEARCH-1-A5 operative as a search verdict. No measurement, threshold, gate
or code changes.

Applied through $SCRIPT_REL; all pins verified and the section-5 consolidated
receipt returned RATIFIED. Receipts: $RECEIPT_REL,
$CONSOLIDATED_REL, $INDEX_REL.

Operator-applied by $OPERATOR
EOF
manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -F <message>"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD || die "could not seed a private index. Amendment IS applied (not rolled back). Commit by hand: $manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" || die "could not stage. Amendment IS applied. Commit by hand: $manual"
staged_meas="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$MEAS_REL" | sha256sum | awk '{print $1}')"
staged_annex="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$ANNEX_REL" | sha256sum | awk '{print $1}')"
[ "$staged_meas" = "$MEAS_POST_SHA256" ] && [ "$staged_annex" = "$ANNEX_SHA256" ] \
  || die "a staged target does not match its pin; NOT committed (amendment applied in the working tree)."
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
[ "$staged_list" = "$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)" ] || die "private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -F "$MSGF"; then
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" || say "  WARNING: run 'git reset -q -- <five paths>' by hand"
  say "  committed $(git -C "$ROOT" rev-parse --short HEAD) on $BRANCH"
else
  die "the commit failed (hook output above). The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $manual"
fi
say ""; say "RATIFIED and committed. Not pushed. Check: ROOT=$ROOT bash $SCRIPT_PATH --verify"
say "Then push $BRANCH and land it on main (a session can do this)."
say "Then the owning session ticks R23-47 and removes OP-38 from the operator queue."
