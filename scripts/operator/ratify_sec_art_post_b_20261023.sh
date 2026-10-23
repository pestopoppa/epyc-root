#!/bin/bash
# ratify_sec_art_post_b_20261023.sh -- operator sign-off of the four SEC-ART-5 chat-template diff reviews
# (SEC-ART-POST-b, handoffs/active/model-artifact-integrity.md).
#
#   Review / dry run (default; writes nothing durable, pushes nothing):
#     bash scripts/operator/ratify_sec_art_post_b_20261023.sh --dry-run
#   Sign and land (the OPERATOR runs this, e.g. as ONE `!` command in Claude Code):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_sec_art_post_b_20261023.sh \
#         --apply --attest RATIFY-SEC-ART-POST-B-20261023 --digest-sha256 <sha256 of the review digest>
#     optional: --roles worker_vision,architect_general   (sign a subset; default = all four)
#   Verify the post-state (read-only):
#     bash scripts/operator/ratify_sec_art_post_b_20261023.sh --verify
#
# WHAT IS SIGNED. The human review of data/template_reviews/<role>.diff (upstream -> served chat template) for
# frontdoor, worker_vision, architect_critic and architect_general. Read the PRIVATE review digest first (its
# path and sha256 are pinned below; it is never committed), then spot-check the raw diffs it points at.
#
# WHERE THE SIGNATURE LIVES. NOT in epyc-root: in epyc-inference-research orchestration/model_registry.yaml, field
# server_mode.<role>.chat_template.template_diff_reviewed. This script lives in root and edits THAT repo's file.
# validate_model_registry.py Check 6 requires the provenance fields (upstream/served sha256 + template_diff) but
# does NOT read template_diff_reviewed, and no code defines a signed-line format, so this script defines it
# (new-model Step 1.5 asks for "who read data/template_reviews/<role>.diff, date"; this adds the bytes reviewed):
#   SIGNED reviewed_by="<NAME>" reviewed_on=<YYYY-MM-DD> diff=data/template_reviews/<role>.diff
#     diff_sha256=<64hex> upstream_sha256_12=<12hex> served_sha256_12=<12hex> review_digest_sha256=<64hex>
#     gate=RATIFY-SEC-ART-POST-B-20261023                                                   (one line)
# --verify is the check of that format; a green validator alone does not prove a sign-off.
#
# WHAT --apply DOES, in order, each step refusing on any mismatch:
#   1. signer: typed --attest token, RATIFY_OPERATOR a human name (scripts/operator/lib/ratify_operator.sh), and
#      --digest-sha256 equal to the pinned digest sha256 AND to the digest file on disk;
#   2. pins at research origin/main: each diff's sha256, each role's upstream/served template sha256 and
#      template_diff path; each template_diff_reviewed still reads the exact "sign-off pending" text;
#   3. the served template bytes on disk still hash to the pin (store file, or a header-only GGUF read);
#   4. a detached scratch worktree of research at a FRESH origin/main: replace exactly those lines (re-parse
#      proof: the YAML document equals the original with only those values changed), run
#      validate_model_registry.py (no SEC-ART-5 error, no error that the unedited tree lacks) and
#      scripts/test_validate_model_registry_templates.py;
#   5. commit + push research (fast-forward of origin/main, under scripts/coordination/serialized_push.py's lock);
#   6. a detached scratch worktree of root at a fresh origin/main: this script, the receipt
#      artifacts/operator/ratify_sec_art_post_b_20261023.json and its keyed index
#      artifacts/operator/receipts/RATIFY-SEC-ART-POST-B-20261023.json in ONE commit, pushed under the lock.
#
# WHAT IT DOES NOT DO: reload, start or stop any process; touch any served template, GGUF or store file; edit
# the lean orchestrator registry (template_diff_reviewed is not compiled into it; SEC-ART-POST-f owns that).
#
# IDEMPOTENT / RESUMABLE: roles already signed with this gate are skipped; research landed but no receipt ->
# only the root step runs; everything landed -> "ALREADY RATIFIED", exit 0. A rejected push stops the run;
# re-run to resume.
#
# ROLLBACK: `git revert` the research commit named in the receipt (restores the "pending" text).
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
SRC_ROOT="${SRC_ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"   # the root checkout holding this script

GATE_ID="RATIFY-SEC-ART-POST-B-20261023"
SCRIPT_REL="scripts/operator/ratify_sec_art_post_b_20261023.sh"
RECEIPT_REL="artifacts/operator/ratify_sec_art_post_b_20261023.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"

RESEARCH_REPO="${RESEARCH_REPO:-/mnt/raid0/llm/epyc-inference-research}"
ORCH_REPO="${ORCH_REPO:-/mnt/raid0/llm/epyc-orchestrator}"
ROOT_REPO="${ROOT_REPO:-/mnt/raid0/llm/epyc-root}"
RESEARCH_PY="${RESEARCH_PY:-/mnt/raid0/llm/epyc-inference-research/.venv/bin/python}"
ORCH_PY="${ORCH_PY:-/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python}"
SYS_PY="/usr/bin/python3"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-sec-art-post-b"
REGISTRY_REL="orchestration/model_registry.yaml"
VALIDATOR_REL="scripts/validate_model_registry.py"
VALIDATOR_TEST_REL="scripts/test_validate_model_registry_templates.py"

# ---- pins (filled by the preparing agent; the operator verifies by reading them) ----
DIGEST_PATH="/mnt/raid0/llm/private/sec-art-post-b/TEMPLATE_REVIEW_DIGEST.md"   # PRIVATE, never committed
DIGEST_SHA256_PIN="50c357749c54064da46aa8f9a0e49f9fd0d63f4cb08924469d8a6767b29e2516"
PENDING_TEXT="generated 2026-10-21 by the SEC-ART-5 lane (diff upstream -> served); human review sign-off pending"
STORE_TEMPLATE="/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja"
VISION_GGUF="/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf"
GENERAL_GGUF="/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
# role | diff sha256 (content at research origin/main) | upstream_template_sha256 | served_template_sha256 | served source
ROLE_PINS=(
  "frontdoor|98b0d55c261f388bf11b919be59e0ce2eb7971f89117d716414fa136388715df|e84f32a23fdda27689f868aa4a1a5621f41133e51a48d7f3efcbea2839574259|1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551|file:$STORE_TEMPLATE"
  "worker_vision|05bdf611f26c4ad4af4a966400c697eb527ed5acb6d03fd01595d3101ea12bac|3636d0f0bd6bef02654cdffdc447b79cb2cef8ab02cc75267345946291a489e4|3636d0f0bd6bef02654cdffdc447b79cb2cef8ab02cc75267345946291a489e4|gguf:$VISION_GGUF"
  "architect_critic|cfdc36542b761d30ece2d0c65fc33be67cbbf776b833cb39a0b7b251162d6cbc|c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041|1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551|file:$STORE_TEMPLATE"
  "architect_general|3f80812a214ada4967559cdc49edd473063d7b6cafc98ce2d936c5e9bd1659cd|c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041|12827f24b742ea4e80cdc12dbcf9622227056b9f797252a3149263d4f9aaadce|gguf:$GENERAL_GGUF"
)
ALL_ROLES="frontdoor,worker_vision,architect_critic,architect_general"
SEC_ART5_CODES="MISSING_TEMPLATE_PROVENANCE BAD_TEMPLATE_PIN TEMPLATE_PIN_PREFIX_MISMATCH TEMPLATE_DIFF_MISSING"

MODE="review"; ATTEST=""; TYPED_DIGEST=""; ROLES_CSV="$ALL_ROLES"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)  MODE="apply" ;;
    --verify) MODE="verify" ;;
    --attest) shift; ATTEST="${1:-}" ;;
    --digest-sha256) shift; TYPED_DIGEST="${1:-}" ;;
    --roles) shift; ROLES_CSV="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --attest $GATE_ID --digest-sha256 <sha256>] [--roles r1,r2]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
g() { local repo="$1"; shift; git -c safe.directory='*' -C "$repo" "$@"; }
sha_of() { sha256sum -- "$1" | awk '{print $1}'; }
sha_at() { g "$1" show "$2:$3" | sha256sum | awk '{print $1}'; }   # content sha256 of a file at a commit

for tool in git sha256sum awk "$SYS_PY" "$RESEARCH_PY" "$ORCH_PY"; do
  command -v "$tool" >/dev/null || die "$tool not available"
done
PUSHER="$ROOT_REPO/scripts/coordination/serialized_push.py"
[ -f "$PUSHER" ] || die "$PUSHER not found"
case "$DIGEST_SHA256_PIN ${ROLE_PINS[*]}" in *@@*) die "script was not finalised (unfilled pin)";; esac

# role selection (subset of the four, no duplicates)
ROLES=()
IFS=',' read -r -a _req <<<"$ROLES_CSV"
for r in "${_req[@]}"; do
  case ",$ALL_ROLES," in *",$r,"*) ;; *) die "--roles: unknown role '$r' (allowed: $ALL_ROLES)";; esac
  for s in "${ROLES[@]+"${ROLES[@]}"}"; do [ "$s" = "$r" ] && die "--roles: duplicate '$r'"; done
  ROLES+=("$r")
done
[ "${#ROLES[@]}" -gt 0 ] || die "--roles is empty"
pin_of() { local p; for p in "${ROLE_PINS[@]}"; do [ "${p%%|*}" = "$1" ] && { printf '%s\n' "$p"; return; }; done; die "no pin for $1"; }

# ---------------------------------------------------------------- read-only state of research + root
g "$RESEARCH_REPO" fetch -q origin main || die "cannot fetch origin main in $RESEARCH_REPO"
g "$ROOT_REPO" fetch -q origin main || die "cannot fetch origin main in $ROOT_REPO"
RES_MAIN="$(g "$RESEARCH_REPO" rev-parse origin/main)"

# Per-role state of template_diff_reviewed at research origin/main: pending | signed (this gate, valid) | other.
role_states() { # repo rev roles... -> lines "role state value"
  local repo="$1" rev="$2"; shift 2
  g "$repo" show "$rev:$REGISTRY_REL" | GATE_ID="$GATE_ID" PENDING="$PENDING_TEXT" "$RESEARCH_PY" -I -c '
import json, os, re, sys, yaml
doc = yaml.safe_load(sys.stdin)
rx = re.compile(r"^SIGNED reviewed_by=\"([^\"\\\x00-\x1f]+)\" reviewed_on=(\d{4}-\d{2}-\d{2}) "
                r"diff=(data/template_reviews/[a-z_]+\.diff) diff_sha256=([0-9a-f]{64}) "
                r"upstream_sha256_12=([0-9a-f]{12}) served_sha256_12=([0-9a-f]{12}) "
                r"review_digest_sha256=([0-9a-f]{64}) gate=(" + re.escape(os.environ["GATE_ID"]) + r")$")
for role in sys.argv[1:]:
    ct = ((doc.get("server_mode") or {}).get(role) or {}).get("chat_template") or {}
    v = ct.get("template_diff_reviewed")
    state = "pending" if v == os.environ["PENDING"] else ("signed" if isinstance(v, str) and rx.match(v) else "other")
    print(role, state, json.dumps(v))
' "$@"
}

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  INDEX_LANDED=no; g "$ROOT_REPO" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && INDEX_LANDED=yes
  if [ "$INDEX_LANDED" = yes ]; then
    mapfile -t SIGNED_ROLES < <(g "$ROOT_REPO" show "origin/main:$RECEIPT_REL" | "$SYS_PY" -I -c 'import json,sys; print("\n".join(json.load(sys.stdin)["signed_roles"]))') \
      || die "receipt $RECEIPT_REL unreadable on root origin/main"
    say "  receipt on root origin/main: $RECEIPT_REL (signed roles: ${SIGNED_ROLES[*]})"
  else
    SIGNED_ROLES=("${ROLES[@]}"); say "  FAIL  $INDEX_REL is not on root origin/main"; ok=0
  fi
  seen=0
  while read -r role state value; do
    seen=$((seen + 1))
    pin="$(pin_of "$role")"; IFS='|' read -r _ dsha usha ssha _src <<<"$pin"
    if [ "$state" != signed ]; then say "  FAIL  $role: template_diff_reviewed is $state: $value"; ok=0; continue; fi
    have_diff="$(sha_at "$RESEARCH_REPO" origin/main "data/template_reviews/$role.diff")"
    line="$(printf '%s' "$value" | "$SYS_PY" -I -c 'import json,sys; print(json.loads(sys.stdin.read()))')"
    want_tail="diff=data/template_reviews/$role.diff diff_sha256=$have_diff upstream_sha256_12=${usha:0:12} served_sha256_12=${ssha:0:12} review_digest_sha256=$DIGEST_SHA256_PIN gate=$GATE_ID"
    case "$line" in *" $want_tail") say "  ok    $role: $line" ;;
      *) say "  FAIL  $role: signed line does not bind the current diff/pins/digest: $line"; ok=0 ;; esac
  done < <(role_states "$RESEARCH_REPO" origin/main "${SIGNED_ROLES[@]}")
  [ "$seen" -eq "${#SIGNED_ROLES[@]}" ] || { say "  FAIL  read $seen of ${#SIGNED_ROLES[@]} registry entries (registry unreadable?)"; ok=0; }
  [ "$ok" -eq 1 ] && { say "VERIFIED: $GATE_ID -- ${#SIGNED_ROLES[@]} template_diff_reviewed line(s) signed on research origin/main, receipt on root origin/main."; exit 0; }
  exit 1
fi

# ---------------------------------------------------------------- 1. signer + digest
if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply requires the typed confirmation --attest $GATE_ID"
  # shellcheck source=/dev/null
  source "$SRC_ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator   # exits 65 on an unset/default/system/login/agent name
  case "$RATIFY_OPERATOR" in *'"'*|*'\'*) die "RATIFY_OPERATOR must not contain a double quote or backslash";; esac
  [ "$(printf '%s' "$RATIFY_OPERATOR" | tr -d '[:cntrl:]')" = "$RATIFY_OPERATOR" ] || die "RATIFY_OPERATOR contains control characters"
  [ -n "$TYPED_DIGEST" ] || die "--apply requires --digest-sha256 <sha256 of $DIGEST_PATH> (the digest you read)"
  SIGNER="$RATIFY_OPERATOR"
  say "signer: $SIGNER"
else
  SIGNER="${RATIFY_OPERATOR:-<operator>}"
  say "dry run: signer shown as '$SIGNER' (no name check outside --apply)"
fi
say "== review digest =="
[ -f "$DIGEST_PATH" ] || die "review digest $DIGEST_PATH is missing (it is private and lives only on this host)"
DIGEST_HAVE="$(sha_of "$DIGEST_PATH")"
[ "$DIGEST_HAVE" = "$DIGEST_SHA256_PIN" ] || die "digest on disk sha256 $DIGEST_HAVE != pinned $DIGEST_SHA256_PIN (edited after preparation)"
if [ -n "$TYPED_DIGEST" ]; then
  [ "$TYPED_DIGEST" = "$DIGEST_SHA256_PIN" ] || die "--digest-sha256 $TYPED_DIGEST != pinned digest $DIGEST_SHA256_PIN"
  say "  ok  typed digest sha256 = pinned = on disk ($DIGEST_HAVE)"
else
  say "  ok  digest on disk = pinned ($DIGEST_HAVE); --apply will also require it typed"
fi
SCRIPT_SHA="$(sha_of "$SCRIPT_PATH")"
say "  this script sha256 $SCRIPT_SHA (recorded in the receipt)"

# ---------------------------------------------------------------- 2. state + pins at research origin/main
say "== research origin/main $RES_MAIN =="
TO_SIGN=(); ALREADY=()
while read -r role state value; do
  case "$state" in
    pending) TO_SIGN+=("$role") ;;
    signed)  ALREADY+=("$role"); say "  ok  $role already signed with $GATE_ID (skipped)" ;;
    *) die "$role: template_diff_reviewed is neither the pending text nor a $GATE_ID signature: $value (changed after preparation)" ;;
  esac
done < <(role_states "$RESEARCH_REPO" origin/main "${ROLES[@]}")
[ "$(( ${#TO_SIGN[@]} + ${#ALREADY[@]} ))" -eq "${#ROLES[@]}" ] || die "could not read template_diff_reviewed for every role (registry unreadable?)"
INDEX_LANDED=no; g "$ROOT_REPO" cat-file -e "origin/main:$INDEX_REL" 2>/dev/null && INDEX_LANDED=yes
if [ "${#TO_SIGN[@]}" -eq 0 ] && [ "$INDEX_LANDED" = yes ]; then
  say "ALREADY RATIFIED: ${ROLES[*]} signed on research origin/main and $INDEX_REL is on root origin/main. Nothing to do."; exit 0
fi
[ "$INDEX_LANDED" = no ] || die "$INDEX_REL is on root origin/main but ${TO_SIGN[*]} still pending (token spent for a different subset?). Resolve by hand."

for role in "${ROLES[@]}"; do
  pin="$(pin_of "$role")"; IFS='|' read -r _ dsha usha ssha _src <<<"$pin"
  have="$(sha_at "$RESEARCH_REPO" origin/main "data/template_reviews/$role.diff")"
  [ "$have" = "$dsha" ] || die "STALE: data/template_reviews/$role.diff on origin/main is $have, the reviewed diff was $dsha. A new diff needs a new review."
  g "$RESEARCH_REPO" show "origin/main:$REGISTRY_REL" | ROLE="$role" U="$usha" S="$ssha" "$RESEARCH_PY" -I -c '
import os, sys, yaml
ct = yaml.safe_load(sys.stdin)["server_mode"][os.environ["ROLE"]]["chat_template"]
want = {"upstream_template_sha256": os.environ["U"], "served_template_sha256": os.environ["S"],
        "template_diff": "data/template_reviews/%s.diff" % os.environ["ROLE"]}
bad = {k: ct.get(k) for k, v in want.items() if ct.get(k) != v}
sys.exit("registry pins differ: %r" % bad if bad else 0)
' || die "$role: registry chat_template pins changed after preparation"
  say "  ok  $role: diff sha256 $dsha; registry upstream ${usha:0:12} served ${ssha:0:12}"
done

# ---------------------------------------------------------------- 3. served bytes on disk still match
say "== served templates on disk =="
AI_MOD="$(mktemp "$STAGE_PARENT/sec-art-post-b-ai.XXXXXX.py")"
g "$ORCH_REPO" show "origin/main:src/registry/artifact_integrity.py" >"$AI_MOD" || die "cannot read orchestrator artifact_integrity.py"
for role in "${ROLES[@]}"; do
  pin="$(pin_of "$role")"; IFS='|' read -r _ _ _ ssha src <<<"$pin"
  case "$src" in
    file:*) have="$(sha_of "${src#file:}")" ;;
    gguf:*) have="$(AI_MOD="$AI_MOD" "$ORCH_PY" -I -c '
import hashlib, importlib.util, os, sys
spec = importlib.util.spec_from_file_location("ai_mod", os.environ["AI_MOD"]); m = importlib.util.module_from_spec(spec)
sys.modules["ai_mod"] = m; spec.loader.exec_module(m)
b = m.read_gguf_chat_template(sys.argv[1]); print(hashlib.sha256(b).hexdigest() if b is not None else "absent")
' "${src#gguf:}")" ;;
  esac
  [ "$have" = "$ssha" ] || { rm -f -- "$AI_MOD"; die "$role: served template now hashes to $have, pinned $ssha ($src)"; }
  say "  ok  $role: $have (${src%%:*}, header/text read only)"
done
rm -f -- "$AI_MOD"

# ---------------------------------------------------------------- push locks free (read-only)
for r in "$RESEARCH_REPO" "$ROOT_REPO"; do
  st="$("$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$r" --lock-name push --status 2>&1 || true)"
  case "$st" in *FREE*) say "  ok  push lock FREE for $r" ;; *) die "push lock for $r is not free: $st" ;; esac
done

# ---------------------------------------------------------------- 4. stage the edit in a scratch worktree
STAGE="$(mktemp -d "$STAGE_PARENT/sec-art-post-b.XXXXXX")"
RES_WT="$STAGE/research"; ROOT_WT="$STAGE/root"
WT_ADDED=(); ROOT_COPIED=()
cleanup() {
  local wt repo path rel
  for wt in "${WT_ADDED[@]+"${WT_ADDED[@]}"}"; do
    repo="${wt%%|*}"; path="${wt#*|}"
    [ -d "$path" ] || continue
    if [ "$path" = "$RES_WT" ]; then
      g "$path" checkout -q -- "$REGISTRY_REL" >/dev/null 2>&1 || true          # drop OUR uncommitted edit only
    else
      g "$path" reset -q >/dev/null 2>&1 || true
      for rel in "${ROOT_COPIED[@]+"${ROOT_COPIED[@]}"}"; do
        g "$path" ls-files --error-unmatch -- "$rel" >/dev/null 2>&1 || rm -f -- "$path/$rel"
      done
    fi
    g "$repo" worktree remove "$path" >/dev/null 2>&1 || say "NOTE: scratch worktree left at $path (inspect, then: git -C $repo worktree remove $path)"
  done
  rm -f -- "$STAGE"/*.txt "$STAGE"/*.json
  rmdir "$STAGE" 2>/dev/null || true
}
trap cleanup EXIT

say "== staging (research scratch worktree at origin/main) =="
g "$RESEARCH_REPO" worktree add -q --detach "$RES_WT" "$RES_MAIN" || die "research: cannot add a scratch worktree"
WT_ADDED+=("$RESEARCH_REPO|$RES_WT")

run_validator() { # out-file -> rc
  local rc=0
  (cd "$RES_WT" && nice -n 19 "$RESEARCH_PY" "$VALIDATOR_REL" "$REGISTRY_REL") >"$1" 2>&1 || rc=$?
  echo "$rc"
}
BASE_RC="$(run_validator "$STAGE/validator.base.txt")"
say "  validator on UNEDITED origin/main: rc=$BASE_RC, $(tail -1 "$STAGE/validator.base.txt")"

TODAY="$(date -u +%Y-%m-%d)"
SIGNED_JSON="$STAGE/signed.json"
if [ "${#TO_SIGN[@]}" -gt 0 ]; then
  SPEC=""
  for role in "${TO_SIGN[@]}"; do
    pin="$(pin_of "$role")"; IFS='|' read -r _ dsha usha ssha _src <<<"$pin"
    SPEC="$SPEC$role|$dsha|${usha:0:12}|${ssha:0:12}"$'\n'
  done
  REG="$RES_WT/$REGISTRY_REL" SPEC="$SPEC" NAME="$SIGNER" DAY="$TODAY" DIGEST="$DIGEST_SHA256_PIN" GATE_ID="$GATE_ID" \
  PENDING="$PENDING_TEXT" OUT="$SIGNED_JSON" "$RESEARCH_PY" -I - <<'PY' || die "registry edit refused (see message above)"
import copy, json, os, sys, yaml
e = os.environ
path = e["REG"]
text = open(path, encoding="utf-8").read()
orig = yaml.safe_load(text)
lines = text.split("\n")

def block(lo, hi, indent, key):
    """(start, end) of the child `key:` at `indent` spaces within lines[lo:hi]."""
    pre = " " * indent + key + ":"
    for i in range(lo, hi):
        if lines[i] == pre or lines[i].startswith(pre + " "):
            j = i + 1
            while j < hi and (not lines[j].strip() or lines[j].startswith(" " * (indent + 1)) or lines[j].lstrip().startswith("#")):
                j += 1
            return i, j
    sys.exit(f"{key!r} not found at indent {indent}")

sm = block(0, len(lines), 0, "server_mode")
signed, expected = {}, copy.deepcopy(orig)
for row in filter(None, e["SPEC"].split("\n")):
    role, dsha, u12, s12 = row.split("|")
    rr = block(sm[0] + 1, sm[1], 2, role)
    cr = block(rr[0] + 1, rr[1], 4, "chat_template")
    old = "      template_diff_reviewed: " + e["PENDING"]
    hits = [i for i in range(cr[0] + 1, cr[1]) if lines[i] == old]
    if len(hits) != 1:
        sys.exit(f"{role}: expected exactly one pending template_diff_reviewed line, found {len(hits)}")
    value = (f'SIGNED reviewed_by="{e["NAME"]}" reviewed_on={e["DAY"]} diff=data/template_reviews/{role}.diff '
             f"diff_sha256={dsha} upstream_sha256_12={u12} served_sha256_12={s12} "
             f'review_digest_sha256={e["DIGEST"]} gate={e["GATE_ID"]}')
    lines[hits[0]] = "      template_diff_reviewed: " + json.dumps(value, ensure_ascii=False)
    expected["server_mode"][role]["chat_template"]["template_diff_reviewed"] = value
    signed[role] = value
new = "\n".join(lines)
if yaml.safe_load(new) != expected:
    sys.exit("post-edit document differs from original + the signed values; refusing to write")
open(path, "w", encoding="utf-8").write(new)
json.dump(signed, open(e["OUT"], "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"  ok  {len(signed)} line(s) replaced; re-parse proof: document == original + signed values only")
PY
  CHANGED="$(g "$RES_WT" diff --name-only)"
  [ "$CHANGED" = "$REGISTRY_REL" ] || die "staged edit touches more than $REGISTRY_REL: $CHANGED"
  NUMSTAT="$(g "$RES_WT" diff --numstat -- "$REGISTRY_REL" | awk '{print $1" "$2}')"
  [ "$NUMSTAT" = "${#TO_SIGN[@]} ${#TO_SIGN[@]}" ] || die "staged edit changed '$NUMSTAT' lines, expected ${#TO_SIGN[@]} replaced"
else
  printf '{}\n' >"$SIGNED_JSON"
  say "  nothing to sign in research (resuming the root step)"
fi

NEW_RC="$(run_validator "$STAGE/validator.new.txt")"
say "  validator on STAGED tree: rc=$NEW_RC, $(tail -1 "$STAGE/validator.new.txt")"
for code in $SEC_ART5_CODES; do
  grep -q "\[$code\]" "$STAGE/validator.new.txt" && { grep "\[$code\]" "$STAGE/validator.new.txt" >&2; die "validator reports a SEC-ART-5 (Check 6) error on the staged tree"; }
done
NEW_ERRS="$(grep -F '  ERROR   [' "$STAGE/validator.new.txt" | sort -u | comm -23 - <(grep -F '  ERROR   [' "$STAGE/validator.base.txt" | sort -u) || true)"
[ -z "$NEW_ERRS" ] || { printf '%s\n' "$NEW_ERRS" >&2; die "the edit introduces validator errors the unedited tree does not have"; }
if [ "$NEW_RC" -ne 0 ]; then
  say "  NOTE validator rc=$NEW_RC on the staged tree, identical to the unedited origin/main (pre-existing, not from this edit):"
  grep -F '  ERROR   [' "$STAGE/validator.new.txt" | sed 's/^/        /'
fi
say "  ok  Check 6 clean; no new validator error"
(cd "$RES_WT" && nice -n 19 timeout 600 "$RESEARCH_PY" -m pytest -q -p no:cacheprovider "$VALIDATOR_TEST_REL") >"$STAGE/tests.txt" 2>&1 \
  || { tail -20 "$STAGE/tests.txt" >&2; die "$VALIDATOR_TEST_REL failed on the staged tree"; }
say "  ok  $VALIDATOR_TEST_REL: $(tail -1 "$STAGE/tests.txt")"

if [ "$MODE" = "review" ]; then
  say ""
  say "== the staged registry change (signer shown as '$SIGNER', date $TODAY) =="
  g "$RES_WT" diff -U0 -- "$REGISTRY_REL" | sed -n '/^@@/,$p'
  say ""
  say "DRY RUN -- nothing was committed or pushed, no receipt was written. --apply would:"
  [ "${#TO_SIGN[@]}" -eq 0 ] || say "  1. commit the ${#TO_SIGN[@]} signed line(s) (${TO_SIGN[*]}) on fresh research origin/main and push it under the push lock"
  say "  2. commit this script + $RECEIPT_REL + $INDEX_REL on fresh root origin/main and push it under the push lock"
  say "  It reloads NOTHING. The scratch worktrees are removed on exit."
  say "DRY-RUN OK: $GATE_ID -- all preconditions hold."
  exit 0
fi

# ---------------------------------------------------------------- 5-6. land (apply)
push_locked() { # name repo-for-lock worktree
  local name="$1" repo="$2" wt="$3" tokdir tok rc=0
  tokdir="$(mktemp -d "$STAGE_PARENT/sec-art-post-b-push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || { rmdir "$tokdir" 2>/dev/null; die "$name: could not take the push lock"; }
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" git -c safe.directory='*' -C "$wt" push origin HEAD:refs/heads/main || rc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$repo" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: $name push lock release failed -- check serialized_push.py --status"
  rm -f "$tok"; rmdir "$tokdir" 2>/dev/null || true
  [ "$rc" -eq 0 ] || die "$name: git push rejected (rc=$rc; origin/main probably moved). Nothing after this was pushed; re-run to resume."
  say "  pushed $name $(g "$wt" rev-parse --short HEAD) -> origin/main"
}
say ""; say "== landing =="
RES_COMMIT="(signed before this run; see research origin/main log)"
if [ "${#TO_SIGN[@]}" -gt 0 ]; then
  g "$RES_WT" add -- "$REGISTRY_REL"
  g "$RES_WT" commit -q -m "SEC-ART-POST-b: operator sign-off of template_diff_reviewed (${TO_SIGN[*]}) -- signed by $SIGNER" \
    -m "Gate $GATE_ID. Each line binds the reviewed diff sha256, the upstream/served template pins and the review digest sha256 $DIGEST_SHA256_PIN. Receipt: epyc-root $RECEIPT_REL." \
    || die "research: commit failed (a pre-commit hook refused it?)"
  RES_COMMIT="$(g "$RES_WT" rev-parse HEAD)"
  push_locked research "$RESEARCH_REPO" "$RES_WT"
  g "$RESEARCH_REPO" fetch -q origin main
  g "$RESEARCH_REPO" merge-base --is-ancestor "$RES_COMMIT" origin/main || die "research commit $RES_COMMIT is not on origin/main after the push"
fi

g "$ROOT_REPO" worktree add -q --detach "$ROOT_WT" origin/main || die "root: cannot add a scratch worktree"
WT_ADDED+=("$ROOT_REPO|$ROOT_WT")
for rel in "$RECEIPT_REL" "$INDEX_REL"; do [ ! -e "$ROOT_WT/$rel" ] || die "$rel already exists on root origin/main (token spent)"; done
if [ -e "$ROOT_WT/$SCRIPT_REL" ]; then
  [ "$(sha_of "$ROOT_WT/$SCRIPT_REL")" = "$SCRIPT_SHA" ] || die "root origin/main already has a DIFFERENT $SCRIPT_REL; refusing to overwrite it"
else
  mkdir -p "$(dirname "$ROOT_WT/$SCRIPT_REL")"; cp -- "$SCRIPT_PATH" "$ROOT_WT/$SCRIPT_REL"; ROOT_COPIED+=("$SCRIPT_REL")
  [ "$(sha_of "$ROOT_WT/$SCRIPT_REL")" = "$SCRIPT_SHA" ] || die "root: script changed during the copy"
fi
ROOT_COPIED+=("$RECEIPT_REL" "$INDEX_REL")
mkdir -p "$ROOT_WT/artifacts/operator/receipts"
PINS="$(printf '%s\n' "${ROLE_PINS[@]}")" RECEIPT_ABS="$ROOT_WT/$RECEIPT_REL" INDEX_ABS="$ROOT_WT/$INDEX_REL" \
RECEIPT_TARGET="$ROOT_REPO/$RECEIPT_REL" GATE_ID="$GATE_ID" OPERATOR="$SIGNER" RES_COMMIT="$RES_COMMIT" RES_BASE="$RES_MAIN" \
SCRIPT_SHA="$SCRIPT_SHA" DIGEST="$DIGEST_SHA256_PIN" DIGEST_PATH="$DIGEST_PATH" SIGNED_JSON="$SIGNED_JSON" \
ROLES="${ROLES[*]}" ALREADY="${ALREADY[*]+"${ALREADY[*]}"}" BASE_RC="$BASE_RC" NEW_RC="$NEW_RC" \
TESTS="$(tail -1 "$STAGE/tests.txt")" "$SYS_PY" -I - <<'PY'
import datetime, json, os
e = os.environ
pins = {}
for line in e["PINS"].splitlines():
    if line.strip():
        role, dsha, usha, ssha, src = line.split("|", 4)
        pins[role] = {"diff": f"data/template_reviews/{role}.diff", "diff_sha256": dsha,
                      "upstream_template_sha256": usha, "served_template_sha256": ssha, "served_source": src}
roles = e["ROLES"].split()
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": e["GATE_ID"],
    "status": "ratified",
    "human_attestation": e["GATE_ID"],
    "signed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "signed_by": e["OPERATOR"],
    "signed_by_uid": os.getuid(),
    "signature_channel": "operator-run script (--attest typed confirmation + typed review-digest sha256)",
    "decision": ("SEC-ART-POST-b: the operator read the upstream -> served chat-template diffs and the agent-prepared "
                 "security review digest, and signs server_mode.<role>.chat_template.template_diff_reviewed for the "
                 "roles below (handoffs/active/model-artifact-integrity.md)."),
    "signed_roles": roles,
    "already_signed_before_this_run": e["ALREADY"].split(),
    "review_digest": {"path": e["DIGEST_PATH"], "sha256": e["DIGEST"],
                      "note": "private, never committed; the sha256 binds what was read"},
    "pinned": {r: pins[r] for r in roles},
    "signed_lines": json.load(open(e["SIGNED_JSON"], encoding="utf-8")),
    "validation": {"validate_model_registry_rc_unedited": int(e["BASE_RC"]), "validate_model_registry_rc_staged": int(e["NEW_RC"]),
                   "check6_errors_staged": 0, "new_errors_staged": 0, "test_validate_model_registry_templates": e["TESTS"]},
    "landed": {"epyc-inference-research": {"commit": e["RES_COMMIT"], "base": e["RES_BASE"], "ref": "origin/main",
                                           "path": "orchestration/model_registry.yaml"},
               "epyc-root": {"commit": "the commit carrying this receipt", "ref": "origin/main"}},
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "reloads_performed": [],
}
with open(e["RECEIPT_ABS"], "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, sort_keys=True, ensure_ascii=False); fh.write("\n")
index = {"gate_id": e["GATE_ID"], "indexed_by": "attest", "receipt": e["RECEIPT_TARGET"],
         "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}
with open(e["INDEX_ABS"], "x", encoding="utf-8") as fh:
    json.dump(index, fh, indent=2, sort_keys=True); fh.write("\n")
PY
ROOT_PATHS=("$RECEIPT_REL" "$INDEX_REL")
g "$ROOT_WT" ls-files --error-unmatch -- "$SCRIPT_REL" >/dev/null 2>&1 || ROOT_PATHS+=("$SCRIPT_REL")
g "$ROOT_WT" add -- "${ROOT_PATHS[@]}"
g "$ROOT_WT" commit -q -m "RATIFIED $GATE_ID: SEC-ART-POST-b template-diff reviews signed (${ROLES[*]}) by $SIGNER" \
  -m "Research ${RES_COMMIT:0:12} carries the signed template_diff_reviewed lines; receipt $RECEIPT_REL, index $INDEX_REL. Reloads: none." \
  || die "root: commit failed (a pre-commit hook refused it?); research is landed, re-run to resume the root step"
push_locked root "$ROOT_REPO" "$ROOT_WT"

cat <<EOF

RATIFIED $GATE_ID by $SIGNER.
  research: $RES_COMMIT  (orchestration/model_registry.yaml, template_diff_reviewed for: ${ROLES[*]})
  root:     $RECEIPT_REL + $INDEX_REL (in the pushed root commit)
NOTHING WAS RELOADED.
Next: bash $SCRIPT_REL --verify ; then the owning session ticks SEC-ART-POST-b in
handoffs/active/model-artifact-integrity.md (cite this receipt).
EOF
