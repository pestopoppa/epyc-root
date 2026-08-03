#!/bin/bash
# apply_ratification.sh — OPERATOR-RUN apply for AutoKernel attestation 1a.
#
# Performs the human-only writes an agent cannot: the MEASUREMENT.md core-file deltas,
# the Annex B / Annex G appends, the new Annex K file, the MEASUREMENT_POLICY.md digest
# bullet, and the human_only_paths.yaml conceptual entries + .sha256 re-pin.
#
# DEFAULT IS DRY-RUN. Nothing is written without --apply.
#   Read artifacts/operator/autokernel-policy-draft/RATIFICATION_PACKAGE.md first.
#
# Usage:
#   apply_ratification.sh                       # dry run, full diff preview, writes nothing
#   apply_ratification.sh --apply               # apply every item
#   apply_ratification.sh --only 1,2,3,5,8      # apply only these items (struck items omitted)
#   apply_ratification.sh --apply --only 4,5
#   apply_ratification.sh --verify              # post-apply verification only
#
# Guarantees:
#   * idempotent — re-running after a partial apply detects what landed and skips it
#   * fail-closed — every edit site is checked for expected content BEFORE anything is written
#   * never force, never delete, never touch a production kernel branch
#   * backups taken before every write; nothing is destroyed (prime directive)
set -euo pipefail

ROOT="${EPYC_ROOT:-/workspace}"
BUNDLE="$ROOT/artifacts/operator/autokernel-policy-draft"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
APPLY_DATE="$(date -u +%Y-%m-%d)"
BACKUP_DIR="$ROOT/artifacts/operator/autokernel-1a-backup-$TS"

APPLY=0
VERIFY_ONLY=0
ONLY_RAW=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)  APPLY=1; shift ;;
    --verify) VERIFY_ONLY=1; shift ;;
    --only)   ONLY_RAW="${2:-}"; shift 2 ;;
    --only=*) ONLY_RAW="${1#--only=}"; shift ;;
    -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "FATAL: unknown argument '$1' (see --help)" >&2; exit 2 ;;
  esac
done

ALL_ITEMS="1 2 3 4 5 6 7 8"
SELECTED="$ALL_ITEMS"
if [[ -n "$ONLY_RAW" ]]; then
  SELECTED="$(printf '%s' "$ONLY_RAW" | tr ',' ' ')"
  for i in $SELECTED; do
    case " $ALL_ITEMS " in
      *" $i "*) ;;
      *) echo "FATAL: --only names unknown item '$i' (valid: 1..8)" >&2; exit 2 ;;
    esac
  done
fi

want() { case " $SELECTED " in *" $1 "*) return 0 ;; *) return 1 ;; esac; }

# --- couplings (RATIFICATION_PACKAGE.md §B) --------------------------------
# These are MEASUREMENT.md:116-118 requirements, not preferences. Item 2 narrows a
# clause whose text lives in Annex G; item 3 is the record of that narrowing. A landed
# 2 without 3 is a silent edit. A landed 3 without 2 points at a protocol that does
# not exist. Item 2 without item 1 has no annex to live in.
check_couplings() {
  local bad=0
  if want 2 && ! want 1; then
    echo "FATAL: item 2 (P-AK-SEARCH-1) requires item 1 (Annex K container) — it has no home without it." >&2; bad=1
  fi
  if want 2 && ! want 3; then
    echo "FATAL: item 2 requires item 3 (Annex G cross-reference). Landing 2 without 3 changes what" >&2
    echo "       gpu-cross-device.md:16-21 MEANS while leaving its TEXT untouched — the silent edit" >&2
    echo "       MEASUREMENT.md:116-118 forbids by name." >&2; bad=1
  fi
  if want 3 && ! want 2; then
    echo "FATAL: item 3 requires item 2. A cross-reference to a protocol that does not exist is as" >&2
    echo "       wrong as an unqualified absolute a protocol has quietly narrowed." >&2; bad=1
  fi
  [[ $bad -eq 0 ]] || exit 2
}

# --- output helpers --------------------------------------------------------
say()   { printf '%s\n' "$*"; }
head1() { printf '\n=== %s ===\n' "$*"; }
skip()  { printf '  SKIP  %s\n' "$*"; }
plan()  { printf '  PLAN  %s\n' "$*"; }
done_() { printf '  DONE  %s\n' "$*"; }

# preview_replace <file> <old> <new> — print a unified diff of a one-shot replacement
preview_replace() {
  local f="$1" old="$2" new="$3" tmp
  tmp="$(mktemp)"
  OLD="$old" NEW="$new" python3 - "$f" "$tmp" <<'PY'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding='utf-8').read()
open(dst, 'w', encoding='utf-8').write(s.replace(os.environ['OLD'], os.environ['NEW'], 1))
PY
  diff -u --label "a/${f#$ROOT/}" --label "b/${f#$ROOT/}" "$f" "$tmp" || true
  rm -f "$tmp"
}

# preview_append <file> <text>
preview_append() {
  local f="$1" text="$2" tmp
  tmp="$(mktemp)"
  cp "$f" "$tmp"
  printf '%s' "$text" >> "$tmp"
  diff -u --label "a/${f#$ROOT/}" --label "b/${f#$ROOT/}" "$f" "$tmp" || true
  rm -f "$tmp"
}

# do_replace <file> <old> <new> — exact, single-occurrence, asserted
do_replace() {
  local f="$1" old="$2" new="$3"
  OLD="$old" NEW="$new" python3 - "$f" <<'PY'
import os, sys
p = sys.argv[1]
old, new = os.environ['OLD'], os.environ['NEW']
s = open(p, encoding='utf-8').read()
n = s.count(old)
assert n == 1, f'anchor found {n} times in {p} (expected exactly 1) — file drifted, STOP'
open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
PY
}

do_append() { printf '%s' "$2" >> "$1"; }

backup() {
  [[ $APPLY -eq 1 ]] || return 0
  mkdir -p "$BACKUP_DIR"
  local f="$1"
  [[ -f "$f" ]] || return 0
  cp -a "$f" "$BACKUP_DIR/$(printf '%s' "${f#$ROOT/}" | tr '/' '_')"
}

# ==========================================================================
# Anchors and payloads — every one is quoted from RATIFICATION_PACKAGE.md §E
# ==========================================================================
MEAS="$ROOT/MEASUREMENT.md"
BENCH="$ROOT/measurement/protocols/bench-cpu.md"
GPU="$ROOT/measurement/protocols/gpu-cross-device.md"
ANNEXK="$ROOT/measurement/protocols/kernel-research.md"
DIGEST="$ROOT/agents/shared/MEASUREMENT_POLICY.md"
HOP="$ROOT/coordination/session-bus/human_only_paths.yaml"
HOP_PIN="$ROOT/coordination/session-bus/human_only_paths.sha256"

# --- E.1 layout paragraph (item 1) ----------------------------------------
E1_OLD='three annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
file — they are the constitution, filed by family, not commentary on it.'
E1_NEW='four annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
file — they are the constitution, filed by family or instrument class, not commentary on it.'

# --- E.2 annex key line (item 1) ------------------------------------------
E2_OLD='`measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`.'
E2_NEW='`measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
**K** = `measurement/protocols/kernel-research.md`.'

# --- E.3 registry row (item 2) --------------------------------------------
E3_ANCHOR='| P-DFLASH-LINEUP-1 | DFlash lineup enablement (per-lane) | acceptance + t/s ratio (↑) | ✅ 2026-07-25 | G |'
E3_NEW="$E3_ANCHOR
| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend | search verdict — **not a claim**; direction carried per record | ✅ $APPLY_DATE | K |"

# --- E.4 Annex G cross-reference (item 3) ---------------------------------
E4_ANCHOR='MUST NOT gate any keep / revert / deploy / promote / buy / close decision and MUST NOT be
consumed by AutoPilot or any automated optimizer.'
E4_NEW="$E4_ANCHOR

*Narrowed for in-worktree candidate search only by \`P-AK-SEARCH-1\` (Annex K, ratified $APPLY_DATE).
The decision-grade clause above is unchanged, and the consumption clause continues to bind every
consumer other than the AutoKernel controller that produced the record, within the campaign that
produced it.*"

# --- E.6 digest bullet (item 4) -------------------------------------------
E6_OLD='≥1wk → reboot required); `pgrep` zombie check.'
E6_NEW='≥1wk → reboot required); no-concurrent-inference precondition per Annex B §E — `WITNESS` (claim + own-scope + residual-load witness) or `LEGACY`; **never a name-pattern process read** (`CLAUDE.md:84`).'

# --- E.8 §6 cross-reference (item 6) --------------------------------------
E8_ANCHOR='call, not contamination.'
E8_NEW="$E8_ANCHOR Autonomous-loop reclamation of the enumerated expirable
classes is governed by §5 *\"Evidence retention and reclamation\"*; this list is otherwise closed and
confers no authority beyond its own enumeration."

# --- E.9 §6b row (item 7) -------------------------------------------------
E9_ANCHOR='| Agent memory | 49/108 files carry numbers | Pointers, not claims; sessions re-verify per memory-recall caveat | |'
E9_NEW="$E9_ANCHOR
| Kernel-research strategy store (\`scripts/kernel_rnd/kernel_store.py\` SQLite; rows written before $APPLY_DATE) | pre-ratification rows | demote-to-prior (:180-182) + quarantine | Narrows the \`Strategy store / STM / planner narrative\` ruling above for these rows only — their evaluator never gated on coherence, so correctness labels were emitted without an anchor comparison and are not verdicts. Quarantined from every correct-only frontier and readiness computation; a lineage decision resting only on them gets a re-measure ticket (:164-166). Rows of that corpus written by the routing planner or the STM are NOT affected. |"

# --- E.11 gate-list conceptual entries (item 8) ---------------------------
E11_ANCHOR='  - "privileged system-wide changes affecting stability"'
E11_NEW="$E11_ANCHOR
  - \"AutoKernel evaluator immutability against non-agent writes — the PreToolUse layer sees agent tool calls only, so a daemon or a candidate subprocess bypasses it entirely; the enforcing layer is OS-level (separate uid or read-only bind mount), and no glob can express it\"
  - \"glob: entries in the paths: block above were DECLARATIVE ONLY until 2026-08-03: the matcher in scripts/hooks/check_trust_boundary_edit.sh quoted its right-hand side, which disables bash pattern matching, so measurement/protocols/*.md matched nothing and Annexes B/Q/G were agent-writable through Write/Edit while the guard reported success. Literal entries were unaffected and always blocked, which is why the defect survived every prior test. REPAIRED in epyc-root 6f1c4a8b (RHS unquoted) with scripts/hooks/test_check_trust_boundary_edit.sh asserting both directions against the live gate list. A future editor must not re-quote it\""

# ==========================================================================
# Preconditions
# ==========================================================================
preconditions() {
  head1 "PRECONDITIONS"
  local fail=0

  # 0. the bundle exists and is readable
  for f in RATIFICATION_PACKAGE.md RATIFICATION_LEDGER.md \
           Annex-K-container.draft.md P-AK-SEARCH-1.draft.md \
           preflight-substitute.draft.md evidence-retention.draft.md \
           human-only-paths-delta.draft.md; do
    if [[ -f "$BUNDLE/$f" ]]; then say "  ok    bundle file present: $f"
    else say "  FAIL  missing bundle file: $f"; fail=1; fi
  done

  # 1. bundle tracked in git (MEASUREMENT.md:146-156 — evidence must be durable)
  local untracked
  untracked="$(cd "$ROOT" && git ls-files --others --exclude-standard -- artifacts/operator/autokernel-policy-draft/ || true)"
  if [[ -n "$untracked" ]]; then
    say "  WARN  bundle files are UNTRACKED in git — commit before signing:"
    printf '          %s\n' $untracked
    say "        git commit -- artifacts/operator/autokernel-policy-draft/"
    say "        (a working-tree file in a shared clone is one 'git checkout' from gone)"
  else
    say "  ok    every bundle file is tracked in git"
  fi

  # 2. clean working tree for the TARGET paths only (shared clone: never check globally)
  local dirty
  dirty="$(cd "$ROOT" && git status --porcelain -- \
            MEASUREMENT.md measurement/protocols agents/shared/MEASUREMENT_POLICY.md \
            coordination/session-bus/human_only_paths.yaml \
            coordination/session-bus/human_only_paths.sha256 || true)"
  if [[ -n "$dirty" ]]; then
    say "  FAIL  target paths have uncommitted changes — commit or stash them first:"
    printf '          %s\n' "$dirty"
    fail=1
  else
    say "  ok    target paths are clean in git"
  fi

  # 3. human_only_paths pin matches its file BEFORE we touch anything
  if [[ -f "$HOP" && -f "$HOP_PIN" ]]; then
    local live pinned
    live="$(sha256sum "$HOP" | awk '{print $1}')"
    pinned="$(tr -d '[:space:]' < "$HOP_PIN")"
    if [[ "$live" == "$pinned" ]]; then
      say "  ok    human_only_paths pin matches (${live:0:12}…)"
    else
      say "  FAIL  human_only_paths PIN MISMATCH before any edit — pre-existing drift."
      say "        live=${live:0:12}… pinned=${pinned:0:12}…"
      say "        Resolve deliberately; do not absorb pre-existing drift into this amendment."
      fail=1
    fi
  else
    say "  FAIL  human_only_paths.yaml or its .sha256 is missing"; fail=1
  fi

  # 4. expected content present at every edit site we intend to touch
  # Exact SUBSTRING occurrence count, not a line-oriented grep: several anchors span
  # more than one line, and `grep -F` splits a multi-line pattern into one pattern per
  # line, which counts matches that are not occurrences of the anchor at all.
  count_occurrences() { # <file> <needle> -> prints an integer
    NEEDLE="$2" python3 - "$1" <<'PY'
import os, sys
try:
    s = open(sys.argv[1], encoding='utf-8').read()
except OSError:
    print(-1); raise SystemExit
print(s.count(os.environ['NEEDLE']))
PY
  }

  check_anchor() { # <label> <file> <needle>
    if [[ ! -f "$2" ]]; then say "  FAIL  missing file: ${2#$ROOT/}"; return 1; fi
    local n; n="$(count_occurrences "$2" "$3")"
    if [[ "$n" == "1" ]]; then say "  ok    anchor present ($1)"; return 0; fi
    if [[ "$n" == "0" ]]; then say "  FAIL  EXPECTED CONTENT NOT FOUND ($1) in ${2#$ROOT/} — file drifted since authoring"; return 1; fi
    say "  FAIL  anchor ambiguous ($1): $n occurrences in ${2#$ROOT/} — refusing to guess"; return 1
  }

  want 1 && { landed_1 || { check_anchor "E.1 layout"      "$MEAS"  "$E1_OLD" || fail=1
                            check_anchor "E.2 key line"    "$MEAS"  "$E2_OLD" || fail=1; }; }
  want 2 && { landed_2 || check_anchor "E.3 registry"      "$MEAS"  "$E3_ANCHOR" || fail=1; }
  want 3 && { landed_3 || check_anchor "E.4 annex G"       "$GPU"   "$E4_ANCHOR" || fail=1; }
  # Item 4 has TWO independent edit sites — the Annex B append (transcribed by the
  # operator) and the digest bullet (applied here). They can land separately, so each
  # is probed separately; a shared probe would report a false drift after a partial apply.
  want 4 && { landed_4_digest || check_anchor "E.6 digest"  "$DIGEST" "$E6_OLD" || fail=1; }
  want 6 && { landed_6 || check_anchor "E.8 dump list"     "$MEAS"  "$E8_ANCHOR" || fail=1; }
  want 7 && { landed_7 || check_anchor "E.9 6b table"      "$MEAS"  "$E9_ANCHOR" || fail=1; }
  want 8 && { landed_8 || check_anchor "E.11 gate list"    "$HOP"   "$E11_ANCHOR" || fail=1; }

  # 5. production kernel safety — we never touch it, and we prove we did not
  if [[ -d /mnt/raid0/llm/llama.cpp/.git ]]; then
    local br; br="$(git -C /mnt/raid0/llm/llama.cpp rev-parse --abbrev-ref HEAD 2>/dev/null || echo UNKNOWN)"
    say "  note  production kernel branch is '$br' — this script never reads, writes or references it"
  fi

  if [[ $fail -ne 0 ]]; then
    head1 "PRECONDITIONS FAILED — nothing was written"
    say "Re-present the SAME apply token with updated hashes (MEASUREMENT.md:143-144),"
    say "never a restarted chain."
    exit 1
  fi
  say "  --> all preconditions satisfied"
}

# ==========================================================================
# Idempotence probes — 'has this item already landed?'
# ==========================================================================
landed_1() { grep -qF 'four annexes in `measurement/protocols/`' "$MEAS" 2>/dev/null; }
landed_2() { grep -qF '| P-AK-SEARCH-1 |' "$MEAS" 2>/dev/null; }
landed_3() { grep -qF 'Narrowed for in-worktree candidate search only' "$GPU" 2>/dev/null; }
landed_4() { grep -qF '§E — Exclusion preconditions' "$BENCH" 2>/dev/null; }
landed_4_digest() { grep -qF 'no-concurrent-inference precondition per Annex B §E' "$DIGEST" 2>/dev/null; }
# NB: probe on a string unique to the CLAUSE, not on its title — item 6's appended
# sentence quotes the title, so a title probe reports item 5 landed when only item 6 did.
landed_5() { grep -qF 'epyc.autokernel.tombstone.v1' "$MEAS" 2>/dev/null; }
landed_6() { grep -qF 'Autonomous-loop reclamation of the enumerated expirable' "$MEAS" 2>/dev/null; }
landed_7() { grep -qF 'Kernel-research strategy store' "$MEAS" 2>/dev/null; }
landed_8() { grep -qF 'REPAIRED in epyc-root 6f1c4a8b' "$HOP" 2>/dev/null; }

# ==========================================================================
# Items
# ==========================================================================
item_1() {
  head1 "ITEM 1 — Annex K container + core-file layout/key-line deltas"
  if landed_1; then skip "layout paragraph already reads 'four annexes' — item 1 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT.md — layout paragraph (E.1)"; preview_replace "$MEAS" "$E1_OLD" "$E1_NEW"
    plan "MEASUREMENT.md — annex key line (E.2)";   preview_replace "$MEAS" "$E2_OLD" "$E2_NEW"
    plan "CREATE measurement/protocols/kernel-research.md (header + Remit)"
    plan "MEASUREMENT.md — CHANGELOG bullet (E.10, first bullet)"
    say  "  NOTE  the annex Remit body is transcribed by the operator from"
    say  "        Annex-K-container.draft.md §2 and §5; this script creates the file with its"
    say  "        header and a transcription marker, and never invents normative text."
    return 0
  fi
  backup "$MEAS"
  do_replace "$MEAS" "$E1_OLD" "$E1_NEW";  done_ "layout paragraph -> four annexes / instrument class"
  do_replace "$MEAS" "$E2_OLD" "$E2_NEW";  done_ "annex key line gains K"
  if [[ ! -f "$ANNEXK" ]]; then
    mkdir -p "$(dirname "$ANNEXK")"
    cat > "$ANNEXK" <<EOF
<!-- RATIFIED $TS. Annex K of MEASUREMENT.md (same trust boundary, same
     amendment rules). Kernel research and release protocol family. Remit and admission
     test below are normative. -->

# Annex K — Kernel research & release protocols

<!-- TRANSCRIBE, THEN DELETE THIS COMMENT: the Remit block from
     artifacts/operator/autokernel-policy-draft/Annex-K-container.draft.md §2,
     then (if item 2 landed) the P-AK-SEARCH-1 normative text from
     artifacts/operator/autokernel-policy-draft/P-AK-SEARCH-1.draft.md §2.
     Substitute <APPLY_DATE> = $APPLY_DATE. This script does not invent normative text.
     This comment contains the literal token on purpose: verification step G.4 fails
     while it is here, so an un-transcribed annex cannot be mistaken for a finished one. -->
EOF
    done_ "created ${ANNEXK#$ROOT/}"
  else
    skip "${ANNEXK#$ROOT/} already exists — left untouched"
  fi
}

item_2() {
  head1 "ITEM 2 — P-AK-SEARCH-1 registry row + normative text"
  if landed_2; then skip "registry row already present — item 2 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT.md §2 — append P-AK-SEARCH-1 row (E.3)"
    preview_replace "$MEAS" "$E3_ANCHOR" "$E3_NEW"
    plan "measurement/protocols/kernel-research.md — append P-AK-SEARCH-1 normative text"
    say  "  NOTE  normative text is transcribed by the operator from P-AK-SEARCH-1.draft.md §2."
    return 0
  fi
  backup "$MEAS"
  do_replace "$MEAS" "$E3_ANCHOR" "$E3_NEW"; done_ "registry row appended (Status ✅ $APPLY_DATE)"
  say "  ACTION REQUIRED: transcribe P-AK-SEARCH-1.draft.md §2 into ${ANNEXK#$ROOT/}"
}

item_3() {
  head1 "ITEM 3 — Annex G cross-reference (coupled to item 2)"
  if landed_3; then skip "cross-reference already present — item 3 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "gpu-cross-device.md — append narrowing cross-reference (E.4)"
    preview_replace "$GPU" "$E4_ANCHOR" "$E4_NEW"
    return 0
  fi
  backup "$GPU"
  do_replace "$GPU" "$E4_ANCHOR" "$E4_NEW"; done_ "Annex G records the narrowing"
}

item_4() {
  head1 "ITEM 4 — Annex B §E exclusion preconditions + digest bullet"
  if landed_4; then skip "§E already present in bench-cpu.md — item 4 already applied"
  else
    if [[ $APPLY -eq 0 ]]; then
      plan "bench-cpu.md — APPEND §E (full text: preflight-substitute.draft.md §3 blockquote)"
      say  "  NOTE  §E is ~200 lines of normative text; it is transcribed by the operator, not"
      say  "        generated here. This script verifies the append landed and never fabricates"
      say  "        constitutional text."
    else
      backup "$BENCH"
      say "  ACTION REQUIRED: append preflight-substitute.draft.md §3 blockquote to ${BENCH#$ROOT/}"
      say "                   substituting <APPLY_DATE> = $APPLY_DATE"
    fi
  fi
  if landed_4_digest; then
    skip "MEASUREMENT_POLICY.md:38 digest bullet already updated"
  elif [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT_POLICY.md — digest bullet (E.6)"; preview_replace "$DIGEST" "$E6_OLD" "$E6_NEW"
  else
    backup "$DIGEST"
    do_replace "$DIGEST" "$E6_OLD" "$E6_NEW"; done_ "digest bullet: pgrep zombie check -> Annex B §E"
  fi
}

item_5() {
  head1 "ITEM 5 — Evidence retention and reclamation (MEASUREMENT.md §5)"
  if landed_5; then skip "retention clause already present — item 5 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT.md §5 — APPEND retention bullet after the 2026-08-02 durability clause"
    say  "  NOTE  full text: evidence-retention.draft.md §3 blockquote (~90 lines), transcribed by"
    say  "        the operator with <APPLY_DATE> = $APPLY_DATE. Not generated here."
    return 0
  fi
  backup "$MEAS"
  say "  ACTION REQUIRED: append evidence-retention.draft.md §3 blockquote to MEASUREMENT.md §5,"
  say "                   immediately after the 2026-08-02 durability bullet"
}

item_6() {
  head1 "ITEM 6 — §6 dump-list cross-reference (optional, one sentence)"
  if landed_6; then skip "cross-reference already present — item 6 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT.md §6 — append one sentence to the explicit dump list (E.8)"
    preview_replace "$MEAS" "$E8_ANCHOR" "$E8_NEW"
    return 0
  fi
  backup "$MEAS"
  do_replace "$MEAS" "$E8_ANCHOR" "$E8_NEW"; done_ "§6 points at §5's retention rule"
}

item_7() {
  head1 "ITEM 7 — §6b strategy-store narrowing (optional)"
  if landed_7; then skip "§6b row already present — item 7 already applied"; return 0; fi
  if [[ $APPLY -eq 0 ]]; then
    plan "MEASUREMENT.md §6b — append per-corpus row (E.9)"
    preview_replace "$MEAS" "$E9_ANCHOR" "$E9_NEW"
    return 0
  fi
  backup "$MEAS"
  do_replace "$MEAS" "$E9_ANCHOR" "$E9_NEW"; done_ "§6b narrows :216 for kernel-research rows only"
}

item_8() {
  head1 "ITEM 8 — human_only_paths conceptual entries + pin rewrite (ATOMIC)"
  if landed_8; then skip "conceptual entries already present — item 8 already applied"
  else
    if [[ $APPLY -eq 0 ]]; then
      plan "human_only_paths.yaml — append two conceptual: entries (E.11)"
      preview_replace "$HOP" "$E11_ANCHOR" "$E11_NEW"
      plan "human_only_paths.sha256 — rewrite pin (LAST action, after the final byte)"
      return 0
    fi
    backup "$HOP"; backup "$HOP_PIN"
    do_replace "$HOP" "$E11_ANCHOR" "$E11_NEW"; done_ "two conceptual: entries appended"
  fi
  if [[ $APPLY -eq 1 ]]; then
    # The pin MUST be the last action. Recomputing unconditionally is correct and
    # idempotent: if the YAML did not change, the pin does not change either.
    sha256sum "$HOP" | awk '{print $1}' > "$HOP_PIN"
    done_ "pin rewritten -> $(cut -c1-12 < "$HOP_PIN")…"
  fi
}

# ==========================================================================
# Verification (RATIFICATION_PACKAGE.md §G)
# ==========================================================================
verify() {
  head1 "VERIFICATION"
  local rc=0

  say "-- G.1 trust-boundary pin"
  if [[ -f "$HOP" && -f "$HOP_PIN" ]]; then
    local live pinned
    live="$(sha256sum "$HOP" | awk '{print $1}')"
    pinned="$(tr -d '[:space:]' < "$HOP_PIN")"
    if [[ "$live" == "$pinned" ]]; then say "  ok    pin matches (${live:0:12}…)"
    else say "  FAIL  PIN DRIFT: live=${live:0:12}… pinned=${pinned:0:12}…"; rc=1; fi
  fi
  if [[ -f "$ROOT/scripts/coordination/session_bus.py" ]]; then
    if python3 "$ROOT/scripts/coordination/session_bus.py" validate >/dev/null 2>&1; then
      say "  ok    session_bus.py validate: trust boundary intact"
    else
      say "  FAIL  session_bus.py validate reported drift (exit non-zero)"; rc=1
    fi
  fi
  say "  NOTE  this checks the PIN, not whether the listed paths are enforced. See G.2."

  say "-- G.2 hook enforcement probe (records reality, does not gate)"
  local hook="$ROOT/scripts/hooks/check_trust_boundary_edit.sh"
  if [[ -x "$hook" || -f "$hook" ]]; then
    for t in "$ROOT/MEASUREMENT.md" "$BENCH" "$ANNEXK"; do
      local ec=0
      printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$t" \
        | CLAUDE_PROJECT_DIR="$ROOT" bash "$hook" >/dev/null 2>&1 || ec=$?
      printf '  exit %s  %s\n' "$ec" "${t#$ROOT/}"
    done
    say "  expect 2 for MEASUREMENT.md (literal entry). 0 for the annexes is the known,"
    say "  disclosed layer-1 glob-matcher defect (deferred item D5) — not a failure of this apply."
  fi

  say "-- G.3 deltas landed"
  for probe in \
    "four annexes in \`measurement/protocols/\`:$MEAS:item 1 layout" \
    "kernel-research.md:$MEAS:item 1 key line" \
    "| P-AK-SEARCH-1 |:$MEAS:item 2 registry row" \
    "Narrowed for in-worktree candidate search:$GPU:item 3" \
    "§E — Exclusion preconditions:$BENCH:item 4" \
    "epyc.autokernel.tombstone.v1:$MEAS:item 5 retention clause" \
    "storage_floor_bytes_free:$MEAS:item 5 floor" \
    "Autonomous-loop reclamation of the enumerated expirable:$MEAS:item 6" \
    "Kernel-research strategy store:$MEAS:item 7" \
    "DECLARATIVE ONLY:$HOP:item 8" ; do
    local needle file label
    needle="${probe%%:*}"; local rest="${probe#*:}"; file="${rest%%:*}"; label="${rest#*:}"
    if grep -qF -- "$needle" "$file" 2>/dev/null; then say "  ok    $label"
    else say "  --    $label (absent — struck, or not applied)"; fi
  done

  say "-- G.4 no placeholder survived into the constitution"
  local hits
  hits="$(grep -nE '<DATE>|<APPLY_DATE>|<APPLY_TS>|BLOCKED-ON|\bTBD\b' \
          "$MEAS" "$ROOT"/measurement/protocols/*.md 2>/dev/null || true)"
  if [[ -z "$hits" ]]; then say "  ok    no unfilled token in MEASUREMENT.md or any annex"
  else say "  FAIL  placeholder transcribed into the constitution:"; printf '        %s\n' "$hits"; rc=1; fi

  say "-- G.6 production kernels untouched"
  if [[ -d /mnt/raid0/llm/llama.cpp/.git ]]; then
    local st; st="$(git -C /mnt/raid0/llm/llama.cpp status --porcelain 2>/dev/null | head -5 || true)"
    if [[ -z "$st" ]]; then say "  ok    production kernel tree clean"
    else say "  WARN  production kernel tree is dirty (NOT caused by this script):"; printf '        %s\n' "$st"; fi
  fi

  head1 "VERIFICATION $( [[ $rc -eq 0 ]] && echo PASSED || echo 'REPORTED FAILURES' )"
  return $rc
}

# ==========================================================================
# Main
# ==========================================================================
head1 "AutoKernel attestation 1a — $( [[ $APPLY -eq 1 ]] && echo 'APPLY' || echo 'DRY RUN (writes nothing)' )"
say "root       : $ROOT"
say "items      : $SELECTED"
say "apply date : $APPLY_DATE"
say "package    : artifacts/operator/autokernel-policy-draft/RATIFICATION_PACKAGE.md"
[[ $APPLY -eq 1 ]] && say "backups    : $BACKUP_DIR"

if [[ $VERIFY_ONLY -eq 1 ]]; then
  verify
  exit $?
fi

check_couplings
preconditions

for i in $ALL_ITEMS; do
  if want "$i"; then "item_$i"; else head1 "ITEM $i — STRUCK (not applied)"; fi
done

if [[ $APPLY -eq 1 ]]; then
  head1 "APPLY COMPLETE"
  say "backup: $BACKUP_DIR"
  say ""
  say "Remaining operator steps (RATIFICATION_PACKAGE.md §F):"
  say "  1. transcribe the normative blockquotes flagged ACTION REQUIRED above"
  say "  2. add the CHANGELOG bullets (package §E.10) for the items that landed"
  say "  3. python3 scripts/operator/ratification_receipt.py emit --pre <snapshot>"
  say "  4. record preimage/receipt hashes in RATIFICATION_LEDGER.md §0 and §8"
  say "  5. re-run this script with --verify"
  say "  6. commit, pathspec-limited (package §F step 6)"
else
  head1 "DRY RUN COMPLETE — nothing was written"
  say "Re-run with --apply to execute, or --only <n,...> to omit struck items."
fi
