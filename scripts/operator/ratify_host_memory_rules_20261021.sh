#!/bin/bash
# ratify_host_memory_rules_20261021.sh — three host-safety rules in agents/shared/OPERATING_CONSTRAINTS.md
# (memory-admitted large CPU loads, detached long-running drivers, no nested region-lock), the
# INC-20261021-earlyoom-session-kills record, and a PRINTED host-side earlyoom reconfiguration.
#
#   Review (default, writes nothing):    bash scripts/operator/ratify_host_memory_rules_20261021.sh
#   Apply + receipts + commit (ONE):     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_host_memory_rules_20261021.sh --apply --attest RATIFY-HOST-MEMORY-RULES-20261021
#   Apply + receipts, no commit:         ... --apply --attest RATIFY-HOST-MEMORY-RULES-20261021 --no-commit
#   Verify the post-state (read-only):   bash scripts/operator/ratify_host_memory_rules_20261021.sh --verify
#
# ratify-targets: agents/shared/OPERATING_CONSTRAINTS.md
#
# OPERATOR DECISION (approved 2026-10-21): "yes, write the rules and prep the earlyoom command".
# An agent (workspace-58) prepared this bundle; only the operator applies it.
#
# WHY. INC-20261021-earlyoom-session-kills: between 15:56:59Z and 15:57:15Z the host earlyoom daemon
# killed 13 processes, three of them `claude` agent sessions (logs/agent_audit-earlyoom.log; forensics in
# /mnt/raid0/llm/tmp/session-crash-20261021/REPORT.md). The DS41-W6.1 drafter A/B was running TWO
# DS41-1017 CPU llama-servers at once. Measured at 16:13Z, each one held RssAnon ~276 GiB (the MXFP4
# `mxfp4_8x8_q8_0` CPU repack copies the experts into anonymous memory) plus RssFile ~463 GiB.
# MemAvailable fell under earlyoom's 20 GiB kill line, and earlyoom, which may not touch a llama-server
# (`--ignore`), killed the largest unprotected processes: the sessions. The DS41-W5 ABA driver died with
# its subagent shell and left an empty log. The same day, `autokernel.loop.calibrate_served_shapes`
# deadlocked for an hour because it was wrapped in an outer `region-lock run` while taking its own claim.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/host-memory-rules-20261021.patch). Additions only:
#   - OPERATING_CONSTRAINTS.md § Inference and Benchmarks: ONE sub-bullet in the "gpu-quiet and region
#     locks" bullet (never nest region-lock around a tool that claims for itself), and TWO new bullets
#     after it (large CPU loads memory-admitted, one at a time; long-running drivers detached with a
#     pidfile and an end flag). No existing line is changed or removed. The heading is unchanged, so
#     the CLAUDE.md link to "Inference and Benchmarks" still resolves.
#   - docs/reference/agent-config/INCIDENT_LOG.md: appends the INC-20261021-earlyoom-session-kills entry.
#     That file is not human-only; it rides in this bundle so the record lands with the rules.
#
# WHAT IT DOES NOT DO. No code, no measurement rule, no other file, nothing on coordination/session-bus/
# human_only_paths.yaml. It starts no process and runs NO host command. The earlyoom change is PRINTED
# (review mode, and again after apply) for you to run on the host; this container cannot see the unit.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                    see PATCH_SHA256
#   OPERATING_CONSTRAINTS.md   pre / post    see OC_PRE_SHA256 / OC_POST_SHA256   (epyc-root origin/main)
#   INCIDENT_LOG.md            pre / post    see IL_PRE_SHA256 / IL_POST_SHA256
#
# The bundle emits the MEASUREMENT.md section-5 consolidated receipt over its own amendment (a doctrine
# amendment anchors in its own target), then the decision receipt and keyed index, and commits exactly
# five paths through a private index seeded from HEAD. Pushing is left to you; the command is printed.
#
# IDEMPOTENT. When both targets are at their post-state pins and all three receipts exist, a re-run
# prints ALREADY RATIFIED and exits 0. Every other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_host_memory_rules_20261021.sh"

GATE_ID="RATIFY-HOST-MEMORY-RULES-20261021"
INC_ID="INC-20261021-earlyoom-session-kills"
PATCH_REL="artifacts/operator/host-memory-rules-20261021.patch"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
IL_REL="docs/reference/agent-config/INCIDENT_LOG.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_host_memory_rules_20261021.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_host_memory_rules_20261021.receipt.json"
COMMIT_PATHS=("$OC_REL" "$IL_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: host memory rules: memory-admitted large CPU loads, detached drivers, no nested region-lock (${INC_ID}, ${GATE_ID})"

# The three rule heads the amendment adds; each must exist exactly once afterwards.
RULE_MEM_HEAD='- **Large CPU model loads are memory-admitted, one at a time.**'
RULE_DRV_HEAD='- **A driver that must outlive the agent that started it runs detached and leaves a trail.**'
RULE_NEST_HEAD='  - **Never wrap a tool that takes its own region-lock claim in another `region-lock run`.**'
INC_HEAD="## $INC_ID"

PATCH_SHA256="97072d8a3b04672024646d66d5f3ddbaccbe2c2d0868332147ee6c32de423741"
OC_PRE_SHA256="e78639e66e9b4e69c7ba85969a352f1735d1ba05a4735047669419b16e0df5bc"
OC_POST_SHA256="9368c66e9b4691f37ea3e3e57f76f87215ef37a5d67803a69214b6a7aa9b2c2c"
IL_PRE_SHA256="d94142594546a3a9abc1ddc5f2c7127948bb08fc6ef06a6ee555c684620ceebd"
IL_POST_SHA256="3faf4c6505eabc5c39ac7e15eb310d78bd5fb5e7ae1caacc00a0845821da20ec"
OC_ADDED_LINES=21
IL_ADDED_LINES=39

MODE="review"; DO_COMMIT=1; ATTEST=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)     MODE="apply" ;;
    --verify)    MODE="verify" ;;
    --no-commit) DO_COMMIT=0 ;;
    --attest)    shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--review | --verify | --apply --attest $GATE_ID [--no-commit]]" >&2; exit 64 ;;
  esac
  shift
done
# The signer is TYPED, never defaulted: unset, system-account (node, root, id -un) and
# agent-id names are refused before anything is written (2026-09-27 governance repair).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
[ "$MODE" != "apply" ] || ratify_require_operator

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

# The host-side earlyoom change. PRINTED ONLY: this bundle never runs a host command.
print_host_block() {
  cat <<'HOSTEOF'

== HOST-SIDE earlyoom reconfiguration (run on the HOST as root; this bundle does NOT run it) ==
earlyoom runs as systemd unit earlyoom.service on the host. Its unit file is not visible in the
container. Live argv today (the unit's MainPID cmdline):
  /usr/local/bin/earlyoom -M 41943040,20971520 -s 100,100 -r 60 --sort-by-rss
    --ignore ^(llama-server|sd-server)$ --prefer ^llama-bench$ -N .../scripts/hooks/earlyoom_audit.sh

Changes: every existing flag is kept. ADD --avoid for the agent sessions, the shells, the tmux server
and the desktop. WIDEN --prefer to the batch llama tools. --ignore STAYS, so llama-servers remain
unkillable by earlyoom. earlyoom matches each regex against /proc/<pid>/comm, which is truncated to
15 bytes. Every name below was read from a live /proc/<pid>/comm on 2026-10-21, or from a copy of the
binary run under its real name:
  claude  codex  opencode  tmux: server  fish  zsh  gnome-shell
  llama-bench  llama-cli  llama-perplexit (llama-perplexity)  llama-quantize  test-backend-op (test-backend-ops)

--- 1. GATE: does THIS binary honour --avoid under --sort-by-rss? (read-only dry run, ~6 s) ---
Upstream changed --avoid/--prefer under --sort-by-rss on 2026-09-14 (cd65016 "fix: --avoid could pick
the avoided process under --sort-by-rss", c33a888 and b335052: the adjustment became +/-0.3 x MemTotal).
The host binary was source-built from master on 2026-06-04. On that build --avoid takes a fixed
3 GiB off VmRSS, and upstream #377 says an avoided process can then still win. Prove it on the live
box before relying on it:

sudo timeout 6 /usr/local/bin/earlyoom --dryrun -d -m 99,99 -s 100,100 -r 2 --sort-by-rss --ignore '^(llama-server|sd-server)$' --avoid '^(claude|codex|opencode|tmux: server|fish|zsh|gnome-shell)$' --prefer '^(llama-bench|llama-cli|llama-perplexit|llama-quantize|test-backend-op)$' 2>&1 | grep -iE 'version|avoid|prefer|ignore|sending|dry'

PASS  the process it would signal ("sending SIGTERM ... dry run") is NOT claude, codex, opencode,
      tmux: server, fish, zsh or gnome-shell. Continue to step 2.
FAIL  it names one of them. Rebuild earlyoom from current upstream master (the recipe is in
      handoffs/completed/earlyoom-oom-protection.md; `make install` lands in /usr/local/bin), then
      re-run this gate before continuing.

--- 2. drop-in (keep every line already in the editor; add these under [Service]) ---
sudo systemctl edit earlyoom

[Service]
ExecStart=
ExecStart=/usr/local/bin/earlyoom -M 41943040,20971520 -s 100,100 -r 60 --sort-by-rss --ignore '^(llama-server|sd-server)$$' --avoid '^(claude|codex|opencode|tmux: server|fish|zsh|gnome-shell)$$' --prefer '^(llama-bench|llama-cli|llama-perplexit|llama-quantize|test-backend-op)$$' -N /mnt/raid0/llm/epyc-root/scripts/hooks/earlyoom_audit.sh

    ($$ is systemd's escape for a literal $; the single quotes keep 'tmux: server' one argument.
     The bare `ExecStart=` clears whatever ExecStart the unit carries (upstream's reads
     /etc/default/earlyoom as `... $EARLYOOM_ARGS`), so this line becomes the whole argv and
     EARLYOOM_ARGS is no longer used.)

--- 3. restart ---
sudo systemctl restart earlyoom

--- 4. verify (expect one argument per line, with the three regexes ending in a single $) ---
cat /proc/$(systemctl show -p MainPID --value earlyoom)/cmdline | tr '\0' '\n'

PROPOSAL, not part of this bundle: extend scripts/hooks/earlyoom_audit.sh so each kill, rate-limited
to one snapshot per burst (13 kills arrived in 16 s), also appends the /proc/meminfo lines MemAvailable,
AnonPages, Mlocked and Cached, plus the top-10 VmRSS read from /proc/*/status, to a
sidecar log. The trigger instant of INC-20261021 left no memory sample anywhere on disk.
HOSTEOF
}

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for f in "$OC_REL" "$IL_REL" "$PATCH_REL" "$CHECKER_REL" scripts/operator/ratification_receipt.py; do
  [ -f "$ROOT/$f" ] || die "$f not found under ROOT=$ROOT"
done

oc_now="$(sha "$ROOT/$OC_REL")"
il_now="$(sha "$ROOT/$IL_REL")"

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$oc_now" = "$OC_POST_SHA256" ] || { say "  FAIL  $OC_REL is ${oc_now:0:12}, expected post-state ${OC_POST_SHA256:0:12}"; ok=0; }
  [ "$il_now" = "$IL_POST_SHA256" ] || { say "  FAIL  $IL_REL is ${il_now:0:12}, expected post-state ${IL_POST_SHA256:0:12}"; ok=0; }
  for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do
    [ -f "$ROOT/$f" ] || { say "  FAIL  $f missing"; ok=0; }
  done
  if [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    v="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("verdict"))' "$ROOT/$CONSOLIDATED_REL")"
    [ "$v" = "RATIFIED" ] || { say "  FAIL  consolidated receipt verdict is $v"; ok=0; }
  fi
  python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT" >/dev/null || { say "  FAIL  $CHECKER_REL does not exit 0"; ok=0; }
  [ "$ok" -eq 1 ] && { say "VERIFIED: $GATE_ID is applied, pinned, receipted, and the checker is clean."; exit 0; }
  if [ "$oc_now" = "$OC_PRE_SHA256" ] && [ "$il_now" = "$IL_PRE_SHA256" ] && [ ! -f "$ROOT/$INDEX_REL" ]; then
    say "NOT YET RATIFIED: both targets are at their pre-state pins and no receipt exists. Apply with:"
    say "    RATIFY_OPERATOR='<your name>' bash $SCRIPT_PATH --apply --attest $GATE_ID"
  fi
  exit 1
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ "$oc_now" = "$OC_POST_SHA256" ] || [ "$il_now" = "$IL_POST_SHA256" ]; then
  if [ "$oc_now" = "$OC_POST_SHA256" ] && [ "$il_now" = "$IL_POST_SHA256" ] \
     && [ -f "$ROOT/$RECEIPT_REL" ] && [ -f "$ROOT/$INDEX_REL" ] && [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    say "ALREADY RATIFIED: both targets are at their post-state pins and all three receipts exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: a target is amended but the other target or a receipt is missing. Resolve by hand."
fi
[ -f "$ROOT/$INDEX_REL" ] && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
for f in "$RECEIPT_REL" "$CONSOLIDATED_REL"; do
  [ -f "$ROOT/$f" ] && die "$f already exists but the targets are not amended. Resolve by hand."
done

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
pin() { # pin <label> <expected> <found>
  if [ "$2" != "$3" ]; then
    printf '  FAIL  %-44s expected %s\n        %-44s found    %s\n' "$1" "$2" "" "$3"; fail=1
  else
    printf '  ok    %-44s (%s)\n' "$1" "${3:0:12}"
  fi
}
pin "patch hash"                              "$PATCH_SHA256"  "$(sha "$ROOT/$PATCH_REL")"
pin "OPERATING_CONSTRAINTS.md pre-state hash" "$OC_PRE_SHA256" "$oc_now"
pin "INCIDENT_LOG.md pre-state hash"          "$IL_PRE_SHA256" "$il_now"
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-44s\n%s\n' "commit paths clean in git" "$dirty"; fail=1
else printf '  ok    %-44s\n' "commit paths clean in git"; fi
if git -C "$ROOT" apply --check "$ROOT/$PATCH_REL" 2>/dev/null; then
  printf '  ok    %-44s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-44s\n' "patch applies cleanly (no fuzz)"; fail=1
fi
if python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT" >/dev/null; then
  printf '  ok    %-44s\n' "receipt checker exits 0 before the amendment"
else
  printf '  FAIL  %-44s\n' "receipt checker exits 0 before the amendment"; fail=1
fi
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main, 2026-10-21). Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff ($PATCH_REL) =="
  cat "$ROOT/$PATCH_REL"
  say ""
  say "REVIEW ONLY: nothing written. Would amend $OC_REL (post-state pin ${OC_POST_SHA256:0:12}) and"
  say "$IL_REL (post-state pin ${IL_POST_SHA256:0:12}), emit the section-5 consolidated receipt, the"
  say "decision receipt and the keyed index, and commit those five paths."
  say "Apply with ONE command:"
  say "    RATIFY_OPERATOR='<your name>' ROOT=$ROOT bash $SCRIPT_PATH --apply --attest $GATE_ID"
  print_host_block
  exit 0
fi

[ "$ATTEST" = "$GATE_ID" ] || die "--apply needs --attest $GATE_ID (the single attestation token). Nothing written."

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$OC_REL" "$TMPD/oc.bak"
cp "$ROOT/$IL_REL" "$TMPD/il.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/oc.bak" "$ROOT/$OC_REL"
  cp "$TMPD/il.bak" "$ROOT/$IL_REL"
  rm -f "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$OC_REL" --state "$IL_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"
# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$ROOT/$PATCH_REL" || { restore; die "git apply failed; targets restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
oc_after="$(sha "$ROOT/$OC_REL")"
il_after="$(sha "$ROOT/$IL_REL")"
if [ "$oc_after" != "$OC_POST_SHA256" ] || [ "$il_after" != "$IL_POST_SHA256" ]; then
  restore; die "post-state hash mismatch (OC ${oc_after:0:12} vs ${OC_POST_SHA256:0:12}, INCIDENT_LOG ${il_after:0:12} vs ${IL_POST_SHA256:0:12}); targets restored. Nothing changed."
fi
printf '  ok    %-44s (%s)\n' "OPERATING_CONSTRAINTS.md post-state hash" "${oc_after:0:12}"
printf '  ok    %-44s (%s)\n' "INCIDENT_LOG.md post-state hash" "${il_after:0:12}"
if python3 - "$TMPD/oc.bak" "$ROOT/$OC_REL" "$TMPD/il.bak" "$ROOT/$IL_REL" \
     "$RULE_MEM_HEAD" "$RULE_DRV_HEAD" "$RULE_NEST_HEAD" "$INC_HEAD" "$INC_ID" \
     "$OC_ADDED_LINES" "$IL_ADDED_LINES" <<'PYEOF'
import difflib, sys
oc_a, oc_b, il_a, il_b = (open(p, encoding="utf-8").read() for p in sys.argv[1:5])
mem, drv, nest, inc_head, inc_id = sys.argv[5:10]
oc_n, il_n = int(sys.argv[10]), int(sys.argv[11])
ok = True
def counts(a, b):
    d = list(difflib.unified_diff(a.split("\n"), b.split("\n"), lineterm="", n=0))
    rem = [l for l in d if l.startswith("-") and not l.startswith("---")]
    add = [l for l in d if l.startswith("+") and not l.startswith("+++")]
    return len(rem), len(add)
for name, a, b, want in (("OPERATING_CONSTRAINTS.md", oc_a, oc_b, oc_n), ("INCIDENT_LOG.md", il_a, il_b, il_n)):
    r, n = counts(a, b)
    if r != 0 or n != want:
        print(f"  FAIL  {name}: expected additions only ({want} lines); {r} removed, {n} added"); ok = False
for needle in (mem, drv, nest, "## Inference and Benchmarks\n"):
    if oc_b.count(needle) != 1:
        print(f"  FAIL  OPERATING_CONSTRAINTS.md: expected exactly one occurrence of {needle.strip()[:80]!r}"); ok = False
# All three rules sit inside "Inference and Benchmarks", before the next section heading.
start = oc_b.find("## Inference and Benchmarks\n")
end = oc_b.find("\n## ", start + 1)
section = oc_b[start:end]
for needle in (mem, drv, nest):
    if needle not in section:
        print(f"  FAIL  rule not inside 'Inference and Benchmarks': {needle.strip()[:70]!r}"); ok = False
if section.count(inc_id) != 3:
    print(f"  FAIL  expected the three rules to cite {inc_id}; found {section.count(inc_id)}"); ok = False
if il_b.count(inc_head + "\n") != 1 or not il_b.startswith(il_a):
    print("  FAIL  INCIDENT_LOG.md: the entry must be appended once, after the unchanged log"); ok = False
if ok:
    print("  ok    additions only; three rules inside Inference and Benchmarks citing the INC; INC entry appended once")
sys.exit(0 if ok else 1)
PYEOF
then :; else restore; die "postflight failed: targets restored. Nothing changed."; fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id OPERATING-CONSTRAINTS-HOST-MEMORY-RULES \
  --anchor "$RULE_MEM_HEAD" \
  --anchor "$RULE_DRV_HEAD" \
  --anchor "$RULE_NEST_HEAD" \
  --anchor "$INC_HEAD" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$RATIFY_OPERATOR" \
  --no-evidence-reason "doctrine amendment, not a measured claim; the incident evidence (logs/agent_audit-earlyoom.log, 13 EARLYOOM_KILL lines 15:56:59-15:57:15Z; /mnt/raid0/llm/tmp/session-crash-20261021/REPORT.md; the 16:13Z RssAnon/RssFile reading) is untracked host state, so it is narrated in the $INC_ID entry this bundle commits rather than cited as durable evidence" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $OC_REL | cut -d' ' -f1)\" = $OC_POST_SHA256" \
  --validation "test \"\$(sha256sum $IL_REL | cut -d' ' -f1)\" = $IL_POST_SHA256" \
  --validation "test \"\$(grep -c '^## Inference and Benchmarks\$' $OC_REL)\" = 1" \
  --validation "test \"\$(grep -c '^## $INC_ID\$' $IL_REL)\" = 1" \
  --out "$ROOT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="$ROOT/${CONSOLIDATED_REL%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$ROOT/$CONSOLIDATED_REL" ] && mv "$ROOT/$CONSOLIDATED_REL" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$ROOT" "$RATIFIED_AT" "$GATE_ID" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" \
     "$RATIFY_OPERATOR" "$PATCH_REL" "$PATCH_SHA256" "$SCRIPT_REL" \
     "$OC_PRE_SHA256" "$OC_POST_SHA256" "$IL_PRE_SHA256" "$IL_POST_SHA256" "$INC_ID" <<'PYEOF'
import json, os, sys
(root, ts, gate, receipt_rel, index_rel, consolidated_rel, operator, patch_rel, patch_sha, script_rel,
 oc_pre, oc_post, il_pre, il_post, inc_id) = sys.argv[1:16]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "HOST-MEMORY-RULES-LARGE-LOADS-ADMITTED-DRIVERS-DETACHED-NO-NESTED-REGION-LOCK",
  "gate_id": gate,
  "operator_decision": "approved 2026-10-21: \"yes, write the rules and prep the earlyoom command\"",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "target": "agents/shared/OPERATING_CONSTRAINTS.md",
  "section": "Inference and Benchmarks",
  "rules": [
    "at most ONE DS41-class CPU server (private-RAM footprint >=200 GiB) on the host at once, across all sessions; before any load expected above ~100 GB of RAM, MemAvailable minus the expected footprint must stay >=100 GiB, else wait; multi-arm A/B briefs state 'one server at a time'",
    "a driver that must outlive the agent that started it (timing drivers, chained launchers) starts with setsid nohup ... </dev/null &, never as a child of a session or subagent shell, and writes a pidfile plus an end flag on success AND failure",
    "never wrap a tool that takes its own region-lock claim in another region-lock run; the nested claim deadlocks until timeout",
  ],
  "origin": inc_id + ": earlyoom killed 13 processes 15:56:59-15:57:15Z on 2026-10-21, three of them claude sessions, while the DS41-W6.1 drafter A/B ran two DS41-1017 CPU servers (each RssAnon ~276 GiB + RssFile ~463 GiB at 16:13Z); the DS41-W5 ABA driver died with its subagent and left an empty log; separately autokernel.loop.calibrate_served_shapes deadlocked an hour under a nested region-lock",
  "incident_record": "docs/reference/agent-config/INCIDENT_LOG.md#" + inc_id.lower(),
  "host_change": "earlyoom.service reconfiguration (add --avoid for sessions/shells/tmux server/desktop, widen --prefer to batch llama tools, --ignore unchanged) is PRINTED by the bundle for the operator to run on the host; it is not applied or attested by this receipt",
  "not_changed": "no code, no measurement rule, no existing doctrine line; section heading unchanged",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {
    "agents/shared/OPERATING_CONSTRAINTS.md": {"sha256_before": oc_pre, "sha256_after": oc_post},
    "docs/reference/agent-config/INCIDENT_LOG.md": {"sha256_before": il_pre, "sha256_after": il_post},
  },
  "consolidated_receipt": consolidated_rel,
  "applied_by": script_rel,
}
with open(os.path.join(root, receipt_rel), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(root, index_rel)), exist_ok=True)
with open(os.path.join(root, index_rel), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify", "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt_rel}")
print(f"  keyed index:      {index_rel}")
PYEOF
then
  restore; rm -f "$ROOT/$CONSOLIDATED_REL"
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these five paths:"
  say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
  say "    git -C $ROOT commit -m '$COMMIT_MSG'     # only if nothing else is staged in this index"
  print_host_block
  exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""
say "== commit on $BRANCH =="
PIDX="$TMPD/private.index"
commit_manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -m '$COMMIT_MSG'"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD \
  || die "could not seed a private index from HEAD. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_oc="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$OC_REL" | sha256sum | awk '{print $1}')"
staged_il="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$IL_REL" | sha256sum | awk '{print $1}')"
[ "$staged_oc" = "$OC_POST_SHA256" ] && [ "$staged_il" = "$IL_POST_SHA256" ] \
  || die "a staged target (OC ${staged_oc:0:12}, INCIDENT_LOG ${staged_il:0:12}) does not match its post-state pin: something edited it after postflight. NOT committed."
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -m "$COMMIT_MSG"; then
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <five paths>' failed; run it by hand so the index matches HEAD."
  say "  committed $(git -C "$ROOT" rev-parse --short HEAD) on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Publish:"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
say ""
say "The doctrine is ratified. The earlyoom change is separate and still yours to run on the host:"
print_host_block
