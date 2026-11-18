#!/bin/bash
# STEP 6: emit ONE ratification package, with a FIXED required key set.
#
# v9's qualification carried relocatable_runtime and rollback_rehearsal. v10's silently
# dropped both -- nothing noticed, because the package was hand-assembled JSON and a
# hand-assembled document cannot be short of a schema it does not have. A fixed schema
# makes a gate impossible to lose: the required set is not a list in this script, it is
# every gate marked `required: true` in ../promotion_gates.yaml, so adding a gate there
# makes every later package fail until it carries one.
#
#   package.sh --candidate <sha> --out <file> --evidence <dir> [--backend cpu|gpu]
#       assemble: derives store/digest/scope/rewind facts, folds in any
#       <evidence>/<gate>.json, then validates. Exits non-zero naming every missing gate.
#   package.sh --check <file> [--backend cpu|gpu]
#       validate a package against the current promotion inputs. Default scope is CPU and GPU.
#
# It never moves a symlink, cuts a branch or edits a verifier. That is step 7, after the
# signature.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATES="$HERE/../promotion_gates.yaml"
[ -f "$GATES" ] || { echo "FAIL: no promotion_gates.yaml beside this script"; exit 1; }
CAND=""; OUT=""; EVID=""; CHECK=""
BACKENDS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --candidate) CAND="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --evidence) EVID="$2"; shift 2 ;;
    --check) CHECK="$2"; shift 2 ;;
    --backend) BACKENDS+=("$2"); shift 2 ;;
    *) echo "FAIL: unknown argument $1"; exit 2 ;;
  esac
done
[ -n "$CHECK" ] || [ -n "$CAND" ] || { echo "FAIL: pass --candidate <sha> or --check <file>"; exit 2; }

GATES="$GATES" CAND="$CAND" OUT="$OUT" EVID="$EVID" CHECK="$CHECK" HERE="$HERE" \
python3 -B - "${BACKENDS[@]}" <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("FAIL: pyyaml not importable; run this under the orchestrator's uv env")

sys.path.insert(0, os.environ["HERE"])
import drafter_selection_receipt as ch17

backends = sys.argv[1:] or list(ch17.BACKENDS)
if len(set(backends)) != len(backends) or not set(backends) <= ch17.BACKENDS.keys():
    sys.exit("FAIL: pass --backend cpu or --backend gpu once each, or omit for both")
orch = Path(os.environ.get("ORCH", "/mnt/raid0/llm/epyc-orchestrator"))

gates_doc = yaml.safe_load(Path(os.environ["GATES"]).read_text())
_gates = {k: v for k, v in (gates_doc.get("gates") or {}).items() if isinstance(v, dict)}
required = sorted(k for k, v in _gates.items() if v.get("required"))
# A gate may have been recorded under another spelling by an earlier promotion (v10 split
# speed/quality per backend). `accepts` is how the schema tolerates that WITHOUT letting a
# gate go missing -- an unlisted spelling still fails.
accepts = {k: list(v.get("accepts") or [k]) for k, v in _gates.items()}
waived = {w.get("gate") for w in (gates_doc.get("waivers") or []) if isinstance(w, dict)}

STORE = Path("/mnt/raid0/llm/kernels/production")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def store_facts() -> dict:
    out = {}
    for backend in ("cpu", "gpu"):
        link = STORE / backend
        if not link.is_symlink():
            continue
        target = link.resolve()
        server = target / "llama-server"
        row = {"resolves_to": str(target)}
        if server.exists():
            row["llama_server_sha256"] = sha256(server)
            try:
                row["version"] = subprocess.run(
                    [str(server), "--version"], capture_output=True, text=True,
                    env={k: v for k, v in os.environ.items() if k != "LD_LIBRARY_PATH"},
                ).stderr.strip().splitlines()[0]
            except Exception as exc:  # noqa: BLE001
                row["version"] = f"<unreadable: {exc}>"
        anchors = sorted((STORE.parent / "archive").glob(f"{backend}-*"))
        row["rollback_anchor"] = str(anchors[-1]) if anchors else None
        row["rewind_command"] = (
            f"ln -sfn {anchors[-1]}/bin {link}" if anchors else None
        )
        out[backend] = row
    return out


def validate(pkg: dict, *, assembling=False) -> list[str]:
    problems = []
    got = pkg.get("gates") or {}
    for gate in required:
        if gate in waived:
            continue
        names = [n for n in accepts.get(gate, [gate]) if n in got]
        value = got.get(names[0]) if names else None
        if value is None:
            problems.append(
                f"missing required gate {gate!r} (promotion_gates.yaml marks it required). "
                "A package short of a gate is not a package; run it or get it waived in "
                "writing."
            )
        else:
            for name in names:
                row = got.get(name)
                if not isinstance(row, dict):
                    continue
                if "status" not in row:
                    problems.append(
                        f"gate {gate!r} (recorded as {name!r}) carries numbers but NO "
                        "`status`. A reader then decides the verdict, which is how a gate "
                        "gets read as passing because it ran.")
                elif row["status"] not in ("pass", "waived"):
                    problems.append(
                        f"gate {gate!r} (recorded as {name!r}) status={row['status']!r}, "
                        "not pass/waived")
    for key in ("candidate", "incumbent", "store", "rollback", "scope"):
        if assembling and key == "store":
            continue
        if not pkg.get(key):
            problems.append(f"missing required section {key!r}")
    rb = pkg.get("rollback") or {}
    if rb and not rb.get("regeneration_command"):
        problems.append(
            "rollback carries no `regeneration_command`. Two ln -sfn and a git checkout "
            "are NOT a rollback: stack_priors.yaml pins the RESOLVED build dir per role, "
            "so a rewound store still launches the new kernel's path until the derived "
            "layer is recompiled."
        )
    return problems


def check_drafter_selection(pkg, *, checking):
    try:
        receipt = pkg["gates"][ch17.GATE]
        if receipt.get("schema") != ch17.SCHEMA or receipt.get("status") != "pass":
            raise ValueError("expected a completed CH-17 receipt")
        scope = ch17.resolve_scope(orch, backends, dict(os.environ))
        if checking and pkg["scope"].get("roles") != scope:
            raise ValueError("packaged scope differs from the currently derived promotion scope")
        if pkg["incumbent"] != gates_doc["incumbent"]:
            raise ValueError("package incumbent differs from promotion_gates.yaml")
        incumbent = ch17.incumbent_pins(gates_doc["incumbent"], backends)
        ch17.validate(receipt, scope, orch, pkg["candidate"]["commit"],
                      incumbent, backends)
        pkg["scope"]["roles"] = scope
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            subprocess.SubprocessError, yaml.YAMLError) as exc:
        return [f"CH-17 drafter selection refused: {exc}"]
    return []


if os.environ.get("CHECK"):
    path = Path(os.environ["CHECK"])
    pkg = ch17.strict_json(path.read_bytes())
    problems = validate(pkg)
    if ch17.GATE in (pkg.get("gates") or {}):
        problems.extend(check_drafter_selection(pkg, checking=True))
    print(f"== checking {path} against {len(required)} required gate(s): {', '.join(required)}")
else:
    pkg = {
        "schema": "epyc.kernel_promotion_package.v1",
        "candidate": {"commit": os.environ["CAND"]},
        "incumbent": gates_doc.get("incumbent"),
        "scope": {"derived_by": (gates_doc.get("scope") or {}).get("derived_by")},
        "gates": {},
        "rollback": {
            "regeneration_command": (
                "cd /mnt/raid0/llm/epyc-orchestrator && uv run python "
                "scripts/registry/stack_change_pipeline.py update --numa-mode <declared>"
            ),
            "regeneration_reason": (
                "stack_priors.yaml pins the RESOLVED binary_dir/binary_path/ld_library_path "
                "PER ROLE, so it goes stale the instant the symlink moves -- in either "
                "direction. A rewind without this step leaves every launcher pointing at the "
                "kernel that was just rolled back out."
            ),
        },
    }
    evid = os.environ.get("EVID")
    if evid:
        for f in sorted(Path(evid).glob("*.json")):
            pkg["gates"][f.stem] = ch17.strict_json(f.read_bytes())
    problems = validate(pkg, assembling=True)
    if not problems:
        problems.extend(check_drafter_selection(pkg, checking=False))
    if not problems:
        store = store_facts()
        pkg["store"] = store
        pkg["rollback"]["anchors"] = {b: r.get("rollback_anchor") for b, r in store.items()}
        pkg["rollback"]["commands"] = {b: r.get("rewind_command") for b, r in store.items()}
        problems = validate(pkg)
    out = os.environ.get("OUT")
    if not problems and out:
        Path(out).write_text(json.dumps(pkg, indent=2) + "\n")
        print(f"package written to {out}")
    elif not problems:
        print(json.dumps(pkg, indent=2))

if problems:
    print(f"\nPACKAGE INCOMPLETE: {len(problems)} problem(s)")
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("\nPACKAGE COMPLETE -- present it for signature; do not move anything yourself")
PY
