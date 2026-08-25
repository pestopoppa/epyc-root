#!/bin/bash
# Ratify: create MEASUREMENT.md Annex D (determinism / output-parity protocols).
#
# WHY THIS IS A SCRIPT YOU RUN AND NOT A COMMIT I MADE
# ----------------------------------------------------
# MEASUREMENT.md:4 and section 5 make amendments HUMAN-ONLY, PR-reviewed, append-or-version,
# and state that the protocols/ annexes "carry the SAME trust boundary and amendment rules
# as this file". Creating a sixth annex is the same class of change as the 2026-08-03
# Annex-S creation. The research-intake Stage-4 applier refuses every path under
# measurement/ by construction, so this bundle was held rather than committed.
#
# WHAT IT DOES  (row H22 of the approved wave-2 plan)
#   1. creates measurement/protocols/determinism-parity.md  -- Annex D, 115 lines
#   2. MEASUREMENT.md layout sentence      "five annexes" -> "six annexes"
#   3. MEASUREMENT.md annex key            adds  **D** = determinism-parity.md
#   4. MEASUREMENT.md section 2 registry   adds P-PARITY-1 and P-NONDET-1, both STAGED
#   5. MEASUREMENT.md CHANGELOG            prepends the 2026-08-23 amendment entry
#   6. writes artifacts/operator/ratify_measurement_annex_d_20260823.json
#
# SCOPE. This ratifies the ANNEX. The two protocols land as "list staged", NOT ratified
# (MEASUREMENT.md section 2 legend: check = ratified, clipboard = staged/operator-apply;
# precedent P-PAIRED, staged 2026-07-23). No measurement has been taken under either, so
# neither may be quoted as ratified until one has. Nothing here starts a process, touches
# a kernel tree, or takes compute.
#
# ALL OR NOTHING. A registry row pointing at a missing annex, or an annex with no registry
# row, is worse than neither -- so preflight refuses the whole bundle on any single
# mismatch, and the apply stage restores from backup if postflight fails.
#
# Usage:
#   bash scripts/operator/ratify_measurement_annex_d_20260823.sh --dry-run   # preflight only
#   bash scripts/operator/ratify_measurement_annex_d_20260823.sh             # apply
#   bash scripts/operator/ratify_measurement_annex_d_20260823.sh --commit    # apply + commit
#
# Idempotent: a second run detects the annex is already present and exits 0 without writing.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
MEAS="$ROOT/MEASUREMENT.md"
ANNEX="$ROOT/measurement/protocols/determinism-parity.md"
RECEIPT="$ROOT/artifacts/operator/ratify_measurement_annex_d_20260823.json"
VENVPY="${VENVPY:-$ROOT/repos/epyc-orchestrator/.venv/bin/python}"
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

DRY_RUN=0; DO_COMMIT=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --commit)  DO_COMMIT=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }

[ -f "$MEAS" ] || die "MEASUREMENT.md not found at $MEAS"
[ -x "$VENVPY" ] || die "python not found at $VENVPY"

# ---------------------------------------------------------------- idempotence
if [ -f "$ANNEX" ] && grep -qF 'determinism-parity.md' "$MEAS"; then
  say "ALREADY RATIFIED: $ANNEX exists and MEASUREMENT.md references it. Nothing to do."
  exit 0
fi
[ -f "$ANNEX" ] && die "$ANNEX exists but MEASUREMENT.md does not reference it -- half-applied state, resolve by hand"
grep -qF 'determinism-parity.md' "$MEAS" && die "MEASUREMENT.md references the annex but the file is missing -- half-applied state, resolve by hand"

# ---------------------------------------------------------------- preflight
say "== preflight =="
fail=0
chk() { # chk <expected-count> <label> <needle>
  local want="$1" label="$2" needle="$3" got
  got="$(grep -cF -- "$needle" "$MEAS" || true)"
  if [ "$got" != "$want" ]; then printf '  FAIL  %-46s expected %s, found %s\n' "$label" "$want" "$got"; fail=1
  else printf '  ok    %-46s (%s)\n' "$label" "$got"; fi
}
chk 1 "layout sentence (five annexes)"  'five annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this'
chk 1 "annex key line (S)"              '**S** = `measurement/protocols/speech.md`.'
chk 1 "section-2 anchor row (P-TTS-REL-1)" '| P-TTS-REL-1 | qwentts_tts release decision rule | verdict — **not a claim** | ✅ 2026-08-03 | S |'
chk 1 "CHANGELOG anchor (Annex S entry)" '- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created'
chk 0 "annex letter D not already in use" '**D** = `measurement/protocols/'

n_annex="$(find "$ROOT/measurement/protocols" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [ "$n_annex" != "5" ]; then printf '  FAIL  %-46s expected 5, found %s\n' "annex files on disk" "$n_annex"; fail=1
else printf '  ok    %-46s (5)\n' "annex files on disk"; fi

if [ "$fail" -ne 0 ]; then
  die "preflight failed -- MEASUREMENT.md is not in the state this bundle was prepared against. Nothing written."
fi
say "  preflight clean"

if [ "$DRY_RUN" -eq 1 ]; then
  say ""
  say "DRY RUN -- would create $ANNEX (115 lines) and apply 4 edits to MEASUREMENT.md."
  exit 0
fi

# ---------------------------------------------------------------- apply
BACKUP="$(mktemp)"; cp "$MEAS" "$BACKUP"
restore() { cp "$BACKUP" "$MEAS"; rm -f "$ANNEX"; }

say ""
say "== apply =="
mkdir -p "$(dirname "$ANNEX")" "$(dirname "$RECEIPT")"

cat > "$ANNEX" <<'EOF_ANNEX_D'
<!-- RATIFIED __RATIFIED_AT__ by operator ratification (scripts/operator/ratify_measurement_annex_d_20260823.sh).
     Annex D of MEASUREMENT.md (same trust boundary, same amendment rules).
     Determinism / output-parity protocol family.
     SCOPE OF THIS RATIFICATION: the ANNEX is created. Its two protocols are registered
     in MEASUREMENT.md section 2 as STAGED, not ratified -- no measurement has yet been
     taken under either, and none may be quoted as ratified until one has. -->

# Annex D — Determinism & output-parity protocols

Two protocols. `P-PARITY-1` answers *"do these two decode configurations produce the same tokens?"*
`P-NONDET-1` answers the prior question *"does either of them produce the same tokens as itself?"* —
which must be settled first, because a harness that never repeats a call cannot tell a real
divergence from run-to-run noise.

Both emit a **verdict**, not a rate. Neither is a speed protocol and neither may be quoted beside a
throughput figure.

## P-PARITY-1 — Greedy-output parity between two decode configurations

**Scope.** Any claim of the form "configuration A produces the same output as configuration B" where
the factor under test is a decode-path change: a speculative-decoding type or depth, a KV cache
type, a kernel route, a drafter, a batching mode. **Not** for comparing two different models, two
different weight quantizations, or two prompts.

**Metric.** Per-prompt `PASS` / `FAIL`, plus the **index of the first differing generation token** on
every `FAIL`. **Direction: not applicable — this is a verdict, not a scalar.** An aggregate pass
rate is **not** the metric and MUST NOT be reported as one (see *Reporting*).

### Instrument

- **n >= 5 prompts, minimum, non-negotiable.** A single-prompt parity check returns a false clean
  sheet at a measured rate near 50%: the same upstream reporter went 1/5, then 0/5, then 4/5
  depending on prompt and patch, and one arm was byte-identical on one workload and divergent on the
  other. **A 1-prompt parity result is not a P-PARITY-1 result and may not be labelled as one.**
- **Greedy only.** `temperature 0`, fixed seed, sampling otherwise held identical across arms.
- **Two independent comparison keys, both reported:**
  1. **Stripped-output MD5** — hash of the generated text with the startup banner and the prompt
     echo removed. Removing them is part of the instrument; a hash over unstripped output compares
     the banner.
  2. **Normalized-identity SHA-256** over the tuple `{content, reasoning_content, token_ids}`. This
     catches a divergence that renders to identical text — the case a text hash cannot see.
- **First-divergent-generation-token index** via `llama-tokenize` **on the same vocabulary as the
  run**. It is the *generation* token index — not a character offset, not a prompt-inclusive index.
  A character offset is not comparable across arms.

### Preconditions

- **Fresh process per phase.** Measured: **1/5 divergences with a reused server versus 4/5 with a
  fresh process per phase**, *despite* `cache_prompt=false`. `cache_prompt=false` is **not** a
  substitute for a fresh process and must not be cited as one.
- **ABBA ordering.** Run A, B, B, A. Order effects and process-lifetime effects are both real here;
  ABBA separates them from the factor under test.
- **Explicit rerun-for-determinism.** Before comparing arms, each arm is run under `P-NONDET-1`
  below. **An arm that is not self-identical cannot be compared to anything**, and a parity failure
  measured against a non-deterministic arm is uninterpretable.
- **Confound control — quantized KV.** Run at `-ctk f16 -ctv f16` by default. Quantized KV **alone**
  moves greedy output with the factor under test disabled, so **any quantized-KV arm requires its
  own factor-disabled f16-vs-quantized baseline first**, or non-parity is unattributable.
- **Local-patch route capture (this fork specifically).** Frozen production carries EPYC-local commit
  `a6b4b5263` (`ggml/src/ggml-cuda/mmvq.cu:341-344`), which deliberately routes Q8_0 to a different
  kernel at `ne11 >= 2` and whose own commit message says it is *"numerically-valid (not
  bit-exact)"*. Capture `GGML_CUDA_LOG_MMVQ_ROUTE=1` on **every** arm (a runtime env var,
  `ggml-cuda.cu:1812-1814`, so no rebuild is needed) and report which kernel each batch actually
  took. **A reference arm that takes the same route as the arm under test is not a reference.** Note
  that the equivalent `N==1` vs `N>1` split exists on both CPU paths (`llamafile_sgemm`'s `mnpack`
  register blocking; iqk's `funcs[ny-1]` dispatch), so **batch invariance is not a property any of
  our three compute planes holds** — never assume it.

### Reporting

- **Per prompt: PASS/FAIL, both hashes, and the first-differing-generation-token index on a FAIL.**
- **NEVER an aggregate verdict.** "4/5 passed" is not a result; it is five results, and *which*
  prompt failed is the load-bearing part. An aggregate hides the prompt-dependence that makes n=1
  unsafe in the first place.
- Report the MMVQ route per arm alongside the verdict.
- A parity claim cites `[P-PARITY-1, n=<prompts>, <date>, attest <path>]` per MEASUREMENT.md §3.

### Decision rule

`PASS` on **all** prompts means parity holds **for those prompts, that model, that KV type and that
route** — a durable negative of exactly that scope and no wider. Any `FAIL` is **not** automatically
a defect in the factor under test: attribute it only after the reference arm, the KV baseline and
the route capture together exclude the alternatives. A `FAIL` whose reference arm took the same
kernel route is **unattributable** and is reported as such, not as a divergence.

## P-NONDET-1 — Run-to-run non-determinism detector

**Scope.** Establishing that a single configuration is self-identical, before it is compared to
anything.

**Metric.** Bit-identical / not, plus `max abs Δ` across the N repeats (**lower-better**;
bit-identical is the only passing value when used as a parity precondition).

### Instrument

- **Repeat the identical call N times inside ONE process** (N >= 10). Compare all N outputs to each
  other, not to a stored expectation.
- **A one-shape-per-fresh-process harness cannot run this protocol.** That harness sees a clean first
  call and clears a broken kernel — it is structurally blind to the phenomenon. Measured instance:
  ten identical backward calls in one process returned ten different answers, absmax compounding
  0.40 to 252.88, while the forward pass stayed bit-identical throughout.
- Where a numeric tensor is available, report `max abs Δ` across repeats; where only text is
  available, report the count of distinct outputs among the N.

### Decision rule

Not bit-identical across N means the configuration is **non-deterministic**, and **no parity,
regression or A/B claim may be built on it** until the source is found. Bit-identical across N means
the configuration is admissible as a `P-PARITY-1` arm, for that shape.

**Provenance.** Both protocols generalise the comparison methods and failure modes documented in
llama.cpp issues #27407 and #25618, plus the fla #1156 non-determinism case; adopted as our own
instrument by the wave-2 research-intake plan (row H22) and first consumed by
`handoffs/active/dflash2-block-drafter-experimental-build.md` DF2-6.
EOF_ANNEX_D
"$VENVPY" - "$ANNEX" "$RATIFIED_AT" <<'PYEOF'
import sys, pathlib
p, ts = pathlib.Path(sys.argv[1]), sys.argv[2]
t = p.read_text()
assert '__RATIFIED_AT__' in t, 'annex timestamp placeholder missing'
p.write_text(t.replace('__RATIFIED_AT__', ts))
PYEOF
say "  created $ANNEX"

"$VENVPY" - "$MEAS" <<'PYEOF' || { echo "edit stage failed"; exit 70; }
import sys, pathlib
p = pathlib.Path(sys.argv[1]); t = p.read_text()
EDITS = [
 ("layout sentence",
  "five annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this",
  "six annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this"),
 ("annex key",
  "**S** = `measurement/protocols/speech.md`.",
  "**S** = `measurement/protocols/speech.md`,\n**D** = `measurement/protocols/determinism-parity.md`."),
 ("section-2 rows",
  "| P-TTS-REL-1 | qwentts_tts release decision rule | verdict — **not a claim** | ✅ 2026-08-03 | S |",
  "| P-TTS-REL-1 | qwentts_tts release decision rule | verdict — **not a claim** | ✅ 2026-08-03 | S |\n"
  "| P-PARITY-1 | Greedy-output parity between two decode configurations (spec-dec type/depth, KV type, kernel route, drafter, batching mode) | per-prompt PASS/FAIL + first-differing generation-token index — **not a claim** below n=5 prompts, and **never** an aggregate pass rate | \U0001F4CB staged 2026-08-23 | D |\n"
  "| P-NONDET-1 | Run-to-run non-determinism detector (N >= 10 identical calls in ONE process) | bit-identical / not; max abs Δ across repeats (↓) | \U0001F4CB staged 2026-08-23 | D |"),
 ("CHANGELOG",
  "- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created",
  "- **2026-08-23 (v2.x)** — AMENDMENT: **Annex D**\n"
  "  (`measurement/protocols/determinism-parity.md`) created as a **sixth** annex, filed by instrument\n"
  "  class, holding `P-PARITY-1` (greedy-output parity between two decode configurations) and\n"
  "  `P-NONDET-1` (run-to-run non-determinism detector). These are the first protocols of any kind for\n"
  "  output identity; every parity check in the repo until now was ad hoc. Supersedes the layout\n"
  "  sentence (`five` → `six`) and the annex key line; §2 gains two rows, both staged. Load-bearing\n"
  "  content: n >= 5 prompts (a 1-prompt check false-clears at a measured rate near 50%), fresh process\n"
  "  per phase (1/5 vs 4/5 measured, despite `cache_prompt=false`), per-prompt reporting with the\n"
  "  first-differing-generation-token index and **never** an aggregate, an f16-KV confound control, and\n"
  "  `GGML_CUDA_LOG_MMVQ_ROUTE=1` route capture because EPYC-local `a6b4b5263` is explicitly\n"
  "  \"numerically-valid (not bit-exact)\" at `ne11 >= 2`. Filed by research-intake wave-2 plan row H22.\n\n"
  "- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S** (`measurement/protocols/speech.md`) created"),
]
for label, old, new in EDITS:
    n = t.count(old)
    if n != 1:
        sys.exit(f"edit '{label}': anchor occurs {n}x, expected 1 -- aborting")
    t = t.replace(old, new, 1)
p.write_text(t)
print("  applied 4 edits to MEASUREMENT.md")
PYEOF

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
pchk() { local want="$1" label="$2" needle="$3" got
  got="$(grep -cF -- "$needle" "$MEAS" || true)"
  if [ "$got" != "$want" ]; then printf '  FAIL  %-46s expected %s, found %s\n' "$label" "$want" "$got"; pf=1
  else printf '  ok    %-46s (%s)\n' "$label" "$got"; fi
}
pchk 1 "layout says six annexes"       'six annexes in `measurement/protocols/`'
pchk 0 "layout no longer says five"    'five annexes in `measurement/protocols/`'
pchk 1 "annex key registers D"         '**D** = `measurement/protocols/determinism-parity.md`.'
pchk 1 "P-PARITY-1 registered"         '| P-PARITY-1 |'
pchk 1 "P-NONDET-1 registered"         '| P-NONDET-1 |'
pchk 1 "CHANGELOG entry present"       '2026-08-23 (v2.x)'
pchk 1 "Annex S CHANGELOG preserved"   '- **2026-08-03 (v2.x)** — AMENDMENT: **Annex S**'
pchk 1 "P-TTS-REL-1 row preserved"     '| P-TTS-REL-1 |'

grep -q '^# Annex D — Determinism & output-parity protocols$' "$ANNEX" \
  && printf '  ok    %-46s\n' "annex heading present" \
  || { printf '  FAIL  %-46s\n' "annex heading present"; pf=1; }
grep -q 'RATIFIED '"$RATIFIED_AT" "$ANNEX" \
  && printf '  ok    %-46s\n' "annex timestamp stamped" \
  || { printf '  FAIL  %-46s\n' "annex timestamp stamped"; pf=1; }
grep -q '__RATIFIED_AT__' "$ANNEX" && { printf '  FAIL  %-46s\n' "no unsubstituted placeholder"; pf=1; } \
  || printf '  ok    %-46s\n' "no unsubstituted placeholder"

n_after="$(find "$ROOT/measurement/protocols" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [ "$n_after" != "6" ]; then printf '  FAIL  %-46s expected 6, found %s\n' "annex files on disk" "$n_after"; pf=1
else printf '  ok    %-46s (6)\n' "annex files on disk"; fi

if [ "$pf" -ne 0 ]; then
  restore
  die "postflight failed -- MEASUREMENT.md restored from backup and the annex removed. Nothing changed."
fi
rm -f "$BACKUP"
say "  postflight clean"

# ---------------------------------------------------------------- receipt
"$VENVPY" - "$RECEIPT" "$RATIFIED_AT" "$ANNEX" <<'PYEOF'
import sys, json, hashlib, pathlib
receipt, ts, annex = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
json.dump({
  "schema": "epyc.measurement.annex_creation.v1",
  "decision": "CREATE-ANNEX-D",
  "ratified_at": ts,
  "status": "ratified",
  "annex_letter": "D",
  "annex_path": "measurement/protocols/determinism-parity.md",
  "annex_sha256": hashlib.sha256(annex.read_bytes()).hexdigest(),
  "protocols_registered": [
    {"id": "P-PARITY-1", "status": "staged",
     "emits": "per-prompt PASS/FAIL + first-differing generation-token index"},
    {"id": "P-NONDET-1", "status": "staged",
     "emits": "bit-identical / not; max abs delta across repeats"}],
  "scope": ("The ANNEX is created under operator authority. Both protocols are registered STAGED, "
            "not ratified: no measurement has been taken under either, and neither may be quoted "
            "as ratified until one has."),
  "measurement_md_edits": ["layout five->six", "annex key +D",
                           "section-2 +P-PARITY-1 +P-NONDET-1", "CHANGELOG 2026-08-23 entry"],
  "provenance": ("research-intake wave-2 plan row H22; methods generalised from llama.cpp #27407 "
                 "and #25618 and the fla #1156 non-determinism case; first consumer DF2-6"),
  "applied_by": "scripts/operator/ratify_measurement_annex_d_20260823.sh",
}, open(receipt, "w"), indent=2)
print(f"  receipt written: {receipt}")
PYEOF

# ---------------------------------------------------------------- commit
if [ "$DO_COMMIT" -eq 1 ]; then
  say ""
  say "== commit =="
  cd "$ROOT"
  git fetch --quiet || true
  GI="$(mktemp)"; rm -f "$GI"
  GIT_INDEX_FILE="$GI" git read-tree HEAD
  GIT_INDEX_FILE="$GI" git add MEASUREMENT.md "$ANNEX" "$RECEIPT"
  GIT_INDEX_FILE="$GI" git diff --cached --stat
  GIT_INDEX_FILE="$GI" git commit -F - <<'EOF_MSG'
MEASUREMENT: create Annex D (determinism / output-parity protocols)

Sixth annex, filed by instrument class. Holds P-PARITY-1 (greedy-output parity
between two decode configurations) and P-NONDET-1 (run-to-run non-determinism
detector). These are the first protocols of any kind for output identity; every
parity check in the repo until now was ad hoc.

Both land STAGED, not ratified. No measurement has been taken under either.

Load-bearing content, each element traceable to a measured failure: n >= 5
prompts, because a single-prompt parity check false-clears at a rate near 50%;
a fresh process per phase, because the same harness measured 1/5 reused vs 4/5
fresh despite cache_prompt=false; per-prompt reporting with the first-differing
generation-token index and never an aggregate; an f16-KV confound control,
because quantized KV alone moves greedy output; and route capture, because the
EPYC-local commit a6b4b5263 is explicitly "numerically-valid (not bit-exact)"
at ne11 >= 2, so a non-parity result on MI210 is not automatically upstream.

The measurement trust boundary is human-amendment-only, so this was prepared by
research-intake wave 2 (plan row H22) and applied by operator ratification via
scripts/operator/ratify_measurement_annex_d_20260823.sh, never by the agent
session. Receipt: artifacts/operator/ratify_measurement_annex_d_20260823.json
EOF_MSG
  rm -f "$GI"
  say "  committed"
else
  say ""
  say "NOT COMMITTED. Review, then:"
  say "    git add MEASUREMENT.md measurement/protocols/determinism-parity.md \\"
  say "            artifacts/operator/ratify_measurement_annex_d_20260823.json"
  say "    git commit"
  say "  (or re-run this script with --commit)"
fi

say ""
say "DONE. Annex D created; P-PARITY-1 and P-NONDET-1 registered as STAGED."
