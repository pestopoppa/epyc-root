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
#   package.sh --candidate <sha> --out <file> [--evidence <dir>]
#               --serving-config <file> [--master-registry <file>] [--no-dry-run]
#       assemble: derives store/digest/scope/rewind facts, folds in any
#       <evidence>/<gate>.json, then validates. Exits non-zero naming every missing gate.
#   package.sh --check <file>
#       validate an existing package (or a previous promotion's qualification artifact).
#
# SERVING CONFIG (operator 2026-11-24, PROMOTION-REGISTRY-SERVING-1): the promotion carries the
# champion serving-config artifact (docs/reference/kernel-manifests/serving-configs/
# <champion>.serving-config.json). A package without it is INCOMPLETE -- both on assemble and on
# --check (the artifact must exist at its recorded path and still match its recorded sha256).
# Assembling with it emits three sections into the package:
#   serving_config     path + sha256 + champion of the artifact
#   registry_diff      the master-registry edits (serving_shape knobs + alternates) it implies
#   registry_dry_run   the diff applied to a COPY of the master in a scratch dir, then
#                      `stack_change_pipeline.py update` + `check` on that copy; must be `pass`
# The registry logic lives in the orchestrator (scripts/registry/serving_config_registry.py);
# EPYC_ORCH (default /mnt/raid0/llm/epyc-orchestrator) and EPYC_ORCH_PY pick the checkout and its
# interpreter. Without --master-registry the master is research origin/main. The live registry is
# never written: step 8 applies the signed diff; this script only emits and rehearses it.
#
# It never moves a symlink, cuts a branch or edits a verifier. That is step 7, after the
# signature.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATES="$HERE/../promotion_gates.yaml"
[ -f "$GATES" ] || { echo "FAIL: no promotion_gates.yaml beside this script"; exit 1; }
CAND=""; OUT=""; EVID=""; CHECK=""; SERVCFG=""; MASTER=""; NODRY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --candidate) CAND="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --evidence) EVID="$2"; shift 2 ;;
    --check) CHECK="$2"; shift 2 ;;
    --serving-config) SERVCFG="$2"; shift 2 ;;
    --master-registry) MASTER="$2"; shift 2 ;;
    --no-dry-run) NODRY=1; shift ;;
    *) echo "FAIL: unknown argument $1"; exit 2 ;;
  esac
done
[ -n "$CHECK" ] || [ -n "$CAND" ] || { echo "FAIL: pass --candidate <sha> or --check <file>"; exit 2; }

ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
ORCH_PY="${EPYC_ORCH_PY:-$ORCH/.venv/bin/python}"
GATES="$GATES" CAND="$CAND" OUT="$OUT" EVID="$EVID" CHECK="$CHECK" \
SERVCFG="$SERVCFG" MASTER="$MASTER" NODRY="$NODRY" ORCH="$ORCH" ORCH_PY="$ORCH_PY" \
ROOT="$(cd "$HERE/../../../.." && pwd)" \
python3 - <<'PY'
import hashlib, json, os, subprocess, sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("FAIL: pyyaml not importable; run this under the orchestrator's uv env")

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


ROOT = Path(os.environ["ROOT"])
DIFF_SCHEMA = "epyc.registry_serving_diff.v1"


def _artifact_path(raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else ROOT / p


def validate_serving(pkg: dict) -> list[str]:
    """The package must carry the champion serving config, its registry diff and a passing dry-run."""
    problems = []
    sc = pkg.get("serving_config")
    sc_sha = None
    if not isinstance(sc, dict) or not sc.get("path"):
        problems.append(
            "missing the champion serving-config artifact (serving_config.path). A promotion "
            "carries its serving config -- docs/reference/kernel-manifests/serving-configs/"
            "<champion>.serving-config.json -- so a package without it is incomplete "
            "(SKILL.md step 8; pass --serving-config)."
        )
    else:
        art = _artifact_path(sc["path"])
        if not art.is_file():
            problems.append(f"serving-config artifact {sc['path']!r} does not exist")
        else:
            sc_sha = sha256(art)
            if sc.get("sha256") != sc_sha:
                problems.append(
                    f"serving-config artifact {sc['path']!r} changed since the package recorded "
                    f"it (recorded sha256 {str(sc.get('sha256'))[:12]}, now {sc_sha[:12]}); "
                    "re-assemble so the signature covers what will be applied"
                )
    diff = pkg.get("registry_diff")
    if not isinstance(diff, dict) or diff.get("schema") != DIFF_SCHEMA or not isinstance(diff.get("ops"), list):
        problems.append(
            f"missing registry_diff ({DIFF_SCHEMA}): the package must show the registry edits "
            "the signature covers (serving_shape knobs and alternates)"
        )
    elif sc_sha and diff.get("serving_config_sha256") != sc_sha:
        problems.append("registry_diff was not derived from the recorded serving-config artifact")
    dry = pkg.get("registry_dry_run")
    if not isinstance(dry, dict):
        problems.append(
            "missing registry_dry_run: the diff must be applied to a COPY of the registry and "
            "stack_change_pipeline check run on it before the operator signs"
        )
    elif dry.get("status") != "pass":
        problems.append(
            f"registry_dry_run status={dry.get('status')!r}, not pass"
            + (f" ({dry['error']})" if dry.get("error") else "")
        )
    return problems


def validate(pkg: dict) -> list[str]:
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
    problems.extend(validate_serving(pkg))
    for key in ("candidate", "incumbent", "store", "rollback", "scope"):
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


if os.environ.get("CHECK"):
    path = Path(os.environ["CHECK"])
    pkg = json.loads(path.read_text())
    problems = validate(pkg)
    print(f"== checking {path} against {len(required)} required gate(s): {', '.join(required)}")
else:
    store = store_facts()
    pkg = {
        "schema": "epyc.kernel_promotion_package.v1",
        "candidate": {"commit": os.environ["CAND"]},
        "incumbent": gates_doc.get("incumbent"),
        "store": store,
        "scope": {"derived_by": (gates_doc.get("scope") or {}).get("derived_by"),
                  "note": "run scripts/scope.sh --json <file> and attach it"},
        "gates": {},
        "rollback": {
            "anchors": {b: r.get("rollback_anchor") for b, r in store.items()},
            "commands": {b: r.get("rewind_command") for b, r in store.items()},
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
            pkg["gates"][f.stem] = json.loads(f.read_text())
    servcfg = os.environ.get("SERVCFG")
    if servcfg:
        cfg_path = Path(servcfg)
        try:
            shown = str(cfg_path.resolve().relative_to(ROOT))
        except ValueError:
            shown = str(cfg_path.resolve())
        if not cfg_path.is_file():
            # recorded as given; validate_serving() reports the missing file by name
            pkg["serving_config"] = {"path": shown, "sha256": None}
        else:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                sect_out = Path(td) / "sections.json"
                cmd = [os.environ["ORCH_PY"],
                       str(Path(os.environ["ORCH"]) / "scripts/registry/serving_config_registry.py"),
                       "section", "--config", str(cfg_path), "--out", str(sect_out)]
                if os.environ.get("MASTER"):
                    cmd += ["--master", os.environ["MASTER"]]
                if os.environ.get("NODRY"):
                    cmd += ["--no-dry-run"]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0 or not sect_out.exists():
                    print("FAIL: serving-config registry sections could not be built:\n"
                          + (res.stderr or res.stdout).strip()[-1500:])
                    sys.exit(1)
                sections = json.loads(sect_out.read_text())
            sections["serving_config"]["path"] = shown
            pkg.update(sections)
    problems = validate(pkg)
    out = os.environ.get("OUT")
    if out:
        Path(out).write_text(json.dumps(pkg, indent=2) + "\n")
        print(f"package written to {out}")
    else:
        print(json.dumps(pkg, indent=2))

if problems:
    print(f"\nPACKAGE INCOMPLETE: {len(problems)} problem(s)")
    for p in problems:
        print("  " + p)
    sys.exit(1)
print("\nPACKAGE COMPLETE -- present it for signature; do not move anything yourself")
PY
