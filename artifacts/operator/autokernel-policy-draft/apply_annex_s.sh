#!/bin/bash
# apply_annex_s.sh — ratify Annex S (speech protocols) into the measurement constitution.
#
# Follows the apply_ratification.sh precedent: DRY-RUN BY DEFAULT.
#
#   ./apply_annex_s.sh                # dry run: check every precondition, change nothing
#   ./apply_annex_s.sh --apply        # apply
#   ./apply_annex_s.sh --verify       # verify a landed apply
#
# Every edit is precondition-checked against the EXACT current bytes. If any target
# file has drifted since the deltas were computed, the script REFUSES rather than
# applying a fuzzy match — a governance file edited by a near-miss is worse than one
# not edited at all.
#
# NOT INCLUDED, deliberately:
#   D7 — the speech freeze receipt's WER misattribution. It is a human-only amendment
#        to a ratified receipt and needs a SUPERSEDING receipt, never an in-place edit
#        (MEASUREMENT.md:116-118, :174-175). See the report. Independent of D1-D6.
#   The missing 2026-08-03 MEASUREMENT.md CHANGELOG bullets for the FIVE ratifications
#        that landed that day without them. That is a separate deferral from the
#        Annex K apply (apply_ratification.sh:573), not an Annex S delta.

set -euo pipefail

ROOT="/workspace"
STAGE="${ROOT}/artifacts/operator/autokernel-policy-draft"
ANNEX_SRC="${STAGE}/speech.ANNEX-S-TRANSCRIBED.txt"
ANNEX_DST="${ROOT}/measurement/protocols/speech.md"
CORE="${ROOT}/MEASUREMENT.md"
ROOTLOG="${ROOT}/CHANGELOG.md"
ANNEXK="${ROOT}/measurement/protocols/kernel-research.md"

MODE="dry"
case "${1:-}" in
  --apply)  MODE="apply" ;;
  --verify) MODE="verify" ;;
  "")       MODE="dry" ;;
  *) echo "FATAL: unknown argument '$1' (use --apply, --verify, or nothing for a dry run)" >&2; exit 2 ;;
esac

say() { printf '%s\n' "$*"; }
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$*"; }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$*"; }

say "=== Annex S apply — mode: ${MODE} ==="
say ""

# ---------------------------------------------------------------- preconditions
PRE_FAIL=0

check_file() {
  if [[ -f "$1" ]]; then ok "$2 present"; else fail "$2 MISSING: $1"; PRE_FAIL=1; fi
}

check_contains() {
  # $1 file, $2 literal string, $3 label
  if grep -qF -- "$2" "$1"; then ok "$3"; else fail "$3 — anchor text not found in $1"; PRE_FAIL=1; fi
}

check_absent() {
  if grep -qF -- "$2" "$1"; then fail "$3 — already present in $1 (already applied?)"; PRE_FAIL=1; else ok "$3"; fi
}

say "Preconditions:"
check_file "$ANNEX_SRC" "transcription"
check_file "$CORE"      "MEASUREMENT.md"
check_file "$ROOTLOG"   "CHANGELOG.md"
check_file "$ANNEXK"    "Annex K"

if [[ "$MODE" != "verify" ]]; then
  if [[ -e "$ANNEX_DST" ]]; then fail "destination already exists: $ANNEX_DST"; PRE_FAIL=1; else ok "destination is free"; fi
  check_contains "$CORE" "four annexes in \`measurement/protocols/\`" "D1 anchor (layout says 'four')"
  check_contains "$CORE" "**K** = \`measurement/protocols/kernel-research.md\`." "D2 anchor (annex key line)"
  check_contains "$CORE" "| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees" "D3 anchor (registry tail row)"
  check_absent   "$CORE" "measurement/protocols/speech.md" "D2/D3 not yet applied"
  check_absent   "$ROOTLOG" "Annex S created" "D5 not yet applied"
  check_absent   "$ANNEXK"  "owning-annex set extended" "D6 not yet applied"
fi

# The transcription must be clean. This is the gate that stops a draft becoming law.
for bad in "DRAFT" "NOT RATIFIED" ".draft.md"; do
  if grep -qF -- "$bad" "$ANNEX_SRC"; then fail "transcription still contains '$bad'"; PRE_FAIL=1; fi
done
[[ $PRE_FAIL -eq 0 ]] && ok "transcription carries no draft markers"

if [[ $PRE_FAIL -ne 0 ]]; then
  say ""
  say "REFUSING: preconditions failed. Nothing was changed."
  exit 1
fi

# ---------------------------------------------------------------------- verify
if [[ "$MODE" == "verify" ]]; then
  say ""
  say "Post-apply verification:"
  V=0
  [[ -f "$ANNEX_DST" ]] && ok "Annex S is in place" || { fail "Annex S missing"; V=1; }
  grep -qF "five annexes in \`measurement/protocols/\`" "$CORE" && ok "D1 layout says 'five'" || { fail "D1"; V=1; }
  grep -qF "**S** = \`measurement/protocols/speech.md\`." "$CORE" && ok "D2 annex key lists S" || { fail "D2"; V=1; }
  [[ $(grep -c "| P-STT-\|| P-TTS-" "$CORE") -eq 8 ]] && ok "D3 eight registry rows" || { fail "D3 row count"; V=1; }
  grep -qF "Annex S" "$ROOTLOG" && ok "D5 root changelog" || { fail "D5"; V=1; }
  grep -qF "owning-annex set extended" "$ANNEXK" && ok "D6 Annex K cross-reference" || { fail "D6"; V=1; }
  say ""
  [[ $V -eq 0 ]] && say "VERIFIED." || { say "VERIFICATION FAILED."; exit 1; }
  exit 0
fi

# ------------------------------------------------------------------- dry / apply
say ""
say "Planned changes:"
say "  0. cp  ${ANNEX_SRC}"
say "     ->  ${ANNEX_DST}   ($(wc -l < "$ANNEX_SRC") lines)"
say "  D1. MEASUREMENT.md layout paragraph: 'four annexes' -> 'five annexes'  (one word)"
say "  D2. MEASUREMENT.md annex key line:   add '**S** = measurement/protocols/speech.md.'  (+1 line)"
say "  D3. MEASUREMENT.md section 2 registry: append 8 rows (4 P-STT-*, 4 P-TTS-*)"
say "  D4. MEASUREMENT.md CHANGELOG: prepend the Annex S amendment bullet"
say "  D5. CHANGELOG.md: append one line at EOF"
say "  D6. kernel-research.md: append the owning-annex-set cross-reference"
say ""

if [[ "$MODE" == "dry" ]]; then
  say "DRY RUN — nothing was changed."
  say "Re-run with --apply to execute, then --verify to check."
  exit 0
fi

# ------------------------------------------------------------------------ apply
say "Applying..."

cp "$ANNEX_SRC" "$ANNEX_DST"
ok "0. Annex S written to ${ANNEX_DST}"

python3 - "$CORE" "$ROOTLOG" "$ANNEXK" "$STAGE" <<'PYEOF'
import pathlib, sys, re

core, rootlog, annexk, stage = (pathlib.Path(p) for p in sys.argv[1:5])

# ---- D1: layout paragraph, one word ----------------------------------------
t = core.read_text()
before = "four annexes in `measurement/protocols/`"
assert t.count(before) == 1, f"D1: expected exactly 1 match, found {t.count(before)}"
t = t.replace(before, "five annexes in `measurement/protocols/`", 1)
print("  OK    D1 'four' -> 'five'")

# ---- D2: annex key line, +1 line -------------------------------------------
before = "**K** = `measurement/protocols/kernel-research.md`.\n"
assert t.count(before) == 1, f"D2: expected exactly 1 match, found {t.count(before)}"
after = ("**K** = `measurement/protocols/kernel-research.md`,\n"
         "**S** = `measurement/protocols/speech.md`.\n")
t = t.replace(before, after, 1)
print("  OK    D2 annex key line now lists S")

# ---- D3: eight registry rows ------------------------------------------------
anchor = ("| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend "
          "| search verdict — **not a claim**; direction carried per record | ✅ 2026-08-03 | K |\n")
assert t.count(anchor) == 1, f"D3: registry anchor row not found exactly once ({t.count(anchor)})"
rows = "".join(f"| {pid} | {desc} | {metric} | ✅ 2026-08-03 | S |\n" for pid, desc, metric in [
    ("P-STT-1",     "STT transcription correctness: corpus, normalization, match rule",
                    "WER % (↓) — **not a claim** without its owning release protocol"),
    ("P-STT-2",     "STT speed: real-time factor, latency, throughput",
                    "RTF (↓), first-token latency ms (↓), throughput (↑)"),
    ("P-STT-3",     "Speech memory stability and audio-input identity (backend-agnostic)",
                    "verdict — **not a claim**"),
    ("P-STT-REL-1", "whisper_stt release decision rule",
                    "verdict — **not a claim**"),
    ("P-TTS-1",     "TTS text/audio identity, deterministic and numerical checks",
                    "verdict — **not a claim**"),
    ("P-TTS-2",     "TTS intelligibility/quality proxy with a human-independent floor",
                    "round-trip WER % (↓)"),
    ("P-TTS-3",     "TTS speed: first-audio latency, RTF, throughput",
                    "first-audio ms (↓), RTF (↓), throughput (↑)"),
    ("P-TTS-REL-1", "qwentts_tts release decision rule",
                    "verdict — **not a claim**"),
])
t = t.replace(anchor, anchor + rows, 1)
print("  OK    D3 eight registry rows appended")

# ---- D4: MEASUREMENT.md CHANGELOG bullet ------------------------------------
head = "## CHANGELOG\n\n"
assert t.count(head) == 1, "D4: '## CHANGELOG' heading not found exactly once"
bullet = (
    "- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created\n"
    "  as a **fifth** annex, filed by modality, holding the STT (`P-STT-1`, `P-STT-2`, `P-STT-3`,\n"
    "  `P-STT-REL-1`) and TTS (`P-TTS-1`, `P-TTS-2`, `P-TTS-3`, `P-TTS-REL-1`) protocol families —\n"
    "  the first measurement protocols of any kind for the `whisper_stt` and `qwentts_tts`\n"
    "  backends. Supersedes the layout sentence (`four` → `five`) and the annex key line; §2 gains\n"
    "  eight rows. `P-AK-SEARCH-1`'s owning-annex set is extended to \"B, Q, G or S\".\n\n")
t = t.replace(head, head + bullet, 1)
print("  OK    D4 CHANGELOG bullet prepended")

core.write_text(t)

# ---- D5: root CHANGELOG ------------------------------------------------------
r = rootlog.read_text()
line = ("- 2026-08-03: Annex S created (measurement/protocols/speech.md) — STT (P-STT-1..3, "
        "P-STT-REL-1) and TTS (P-TTS-1..3, P-TTS-REL-1) protocol families ratified; first "
        "measurement protocols for the whisper_stt and qwentts_tts backends; P-AK-SEARCH-1's "
        "owning-annex set extended to \"B, Q, G or S\".\n")
if not r.endswith("\n"):
    r += "\n"
rootlog.write_text(r + line)
print("  OK    D5 root CHANGELOG line appended")

# ---- D6: Annex K cross-reference --------------------------------------------
k = annexk.read_text()
xref = (
    "\n\n## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)\n\n"
    "`P-AK-SEARCH-1`'s scope clause requires a search record presented on a durable surface to be\n"
    "re-measured under *\"its owning protocol in Annex B, Q or G\"*. Annex S\n"
    "(`measurement/protocols/speech.md`, ratified 2026-08-03) creates the owning protocols for the\n"
    "`whisper_stt` and `qwentts_tts` backends, which had none when this protocol was ratified. That\n"
    "set now reads **B, Q, G or S**.\n\n"
    "This narrows nothing and lifts nothing. It records that the re-measurement route this protocol\n"
    "requires now EXISTS for the two speech backends; before Annex S it did not, which made the\n"
    "requirement unsatisfiable for them rather than strict.\n")
if not k.endswith("\n"):
    k += "\n"
annexk.write_text(k + xref)
print("  OK    D6 Annex K cross-reference appended")
PYEOF

say ""
say "APPLIED. Now run:  $0 --verify"
say ""
say "Then commit — measurement/ is a human-only path, so this commit is yours:"
say "  cd ${ROOT} && git add MEASUREMENT.md CHANGELOG.md measurement/protocols/speech.md measurement/protocols/kernel-research.md && git commit"
