"""Validate the evidence references and topology decision carried by CH-17."""

import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "scripts/benchmark"))
from kernel_promotion_hot_stack import (  # noqa: E402
    check_pin,
    is_hash,
    production_runtime_dirs,
    require,
    unique_keys,
    verify_stage,
)

GATE = "drafter_selection"
SCHEMA = "epyc.kernel_promotion_drafter_selection.v1"
BACKENDS = {"cpu": "cpu", "gpu": "hip"}
INPUTS = {
    "topology": "orchestration/stack_topology.yaml",
    "registry": "orchestration/model_registry.yaml",
    "priors": "orchestration/derived/stack_priors.yaml",
}
QUALIFICATION_FIELDS = ("workload", "decision_rule", "custody", "quality", "measured_limits")
UNKNOWN = {"unknown", "unresolved", "missing", "inconclusive", "unobserved", "pending",
           "partial", "error", "refuted"}
SPEC_OPTION = re.compile(r"^[ \t]*--spec-type[ \t]+([a-z0-9,-]+)(?:[ \t]{2,}.*|[ \t]*)$", re.MULTILINE)


def known(value):
    return bool(value) and (not isinstance(value, str) or value.strip().lower() not in UNKNOWN | {""})


def recorded(value):
    if isinstance(value, dict):
        value = list(value.values())
    if isinstance(value, list):
        return bool(value) and all(recorded(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return value is not None and (not isinstance(value, str) or known(value))


def pinned_bytes(path, expected):
    data = path.read_bytes()
    require(is_hash(expected) and hashlib.sha256(data).hexdigest() == expected,
            f"invalid or changed SHA-256 pin: {path}")
    return data


def reference(ref):
    path = Path(ref["path"])
    require(path.is_absolute() and path.is_file(), f"missing or non-absolute evidence reference: {path}")
    return pinned_bytes(path, ref["sha256"])


def strict_json(data):
    return json.loads(data, object_pairs_hook=unique_keys)


def supported_types(help_text):
    options = SPEC_OPTION.findall(help_text)
    require(len(options) == 1, "candidate --spec-type capability is unknown")
    types = options[0].split(",")
    require(all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item) for item in types)
            and len(types) == len(set(types)), "malformed candidate --spec-type capability")
    return set(types)


def resolve_scope(orch, backends, env):
    """Use the regular scope entry point, including its incumbent store checks."""
    scope = {}
    with tempfile.TemporaryDirectory(prefix="ch17-scope-") as tmp:
        for backend in backends:
            path = Path(tmp) / f"{backend}.json"
            result = subprocess.run([str(HERE / "scope.sh"), "--backend", backend, "--json", str(path)],
                                    capture_output=True, text=True, check=False, timeout=60,
                                    env=env | {"ORCH": str(orch)})
            require(result.returncode == 0, f"cannot derive {backend} promotion scope: "
                    f"{result.stdout.strip()} {result.stderr.strip()}")
            scope.update(strict_json(path.read_bytes()))
    return scope


def source_inputs(receipt, orch):
    require(receipt["inputs"].keys() == INPUTS.keys(), "topology, registry and compiled priors pins are required")
    docs = {name: yaml.safe_load(pinned_bytes(orch / path, receipt["inputs"][name]))
            for name, path in INPUTS.items()}
    sources = docs["priors"]["source_artifacts"]
    for name, key in (("topology", "stack_topology"), ("registry", "registry")):
        require(sources[key]["path"] == INPUTS[name] and sources[key]["sha256"] == receipt["inputs"][name],
                f"compiled scope has a stale {name} input")
    return docs


def incumbent_pins(config, backends, roots=(ROOT, Path("/workspace"))):
    """Read the configured incumbent's frozen executable digests from its attestation."""
    relative = Path(config["ratification"])
    candidates = [root / relative for root in roots]
    path = next((path for path in candidates if path.is_file()), candidates[0])
    attestation = strict_json(pinned_bytes(path, config["ratification_sha256"]))
    require(attestation["production_head"] == config["commit"] and attestation["production_frozen"] is True,
            "incumbent ratification does not bind the configured frozen commit")
    binaries = {backend: attestation["production_binary_sha256"][BACKENDS[backend]] for backend in backends}
    require(all(is_hash(sha) for sha in binaries.values()), "ratification lacks frozen executable digests")
    return {"commit": config["commit"], "binaries": binaries}


def image_bindings(receipt, scope, commit, incumbent):
    candidate = receipt["candidate"]
    require(is_hash(commit, 40) and candidate["source_commit"] == commit
            and is_hash(candidate["source_tree"], 40) and known(candidate["branch"]),
            "candidate source commit, tree and branch are required")
    require(candidate["images"].keys() == scope.keys() == receipt["anchors"].keys(),
            "candidate images and anchors must cover each promoted backend")
    production = production_runtime_dirs()
    bindings = {}
    for backend, scope_rows in scope.items():
        image = candidate["images"][backend]
        stage = verify_stage(image["stage"], candidate, BACKENDS[backend], production)
        binary = stage["binary"]
        require(stage["binary_sha256"] == image["binary_sha256"], f"{backend}: candidate executable pin differs")
        witness = image["help"]
        require(witness["argv"] == [binary, "--help"] and witness["exit_code"] == 0
                and witness["binary_sha256"] == stage["binary_sha256"]
                and witness["source_commit"] == commit, f"{backend}: help witness differs from candidate")
        types = supported_types(reference(witness).decode())
        require(image["supported_spec_types"] == sorted(types), f"{backend}: reported spec types differ from help")
        anchor = receipt["anchors"][backend]
        incumbent_binaries = {row["binary_path"] for row in scope_rows}
        require(incumbent_binaries == {anchor["binary"]} and anchor["commit"] == incumbent["commit"],
                f"{backend}: anchor does not match the incumbent scope")
        approved = incumbent["binaries"][backend]
        require(anchor["binary_sha256"] == approved, f"{backend}: anchor binary differs from approved ratification")
        check_pin(Path(anchor["binary"]), approved)
        bindings[backend] = ({"commit": commit, "binary_sha256": stage["binary_sha256"]},
                             {"commit": incumbent["commit"], "binary_sha256": approved}, types)
    return bindings


def evidence_record(ref, binding, *, selected):
    """Check custody and applicability of a cited record. Human ratification reviews the judgment."""
    value = strict_json(reference(ref))
    pointer = ref["pointer"]
    require(isinstance(pointer, str) and (pointer == "" or pointer.startswith("/")),
            "qualification reference needs a JSON pointer")
    if pointer:
        for token in pointer[1:].split("/"):
            require(not re.search(r"~(?![01])", token), "invalid qualification JSON pointer")
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None,
                        "invalid qualification array index")
                value = value[int(token)]
            else:
                value = value[token]
    require(isinstance(value, dict) and value["binding"] == binding,
            "qualification candidate, anchor, role, model or choice binding differs")
    require(all(recorded(value.get(field)) for field in QUALIFICATION_FIELDS),
            "qualification lacks known workload, decision rule, custody, quality or measured limits")
    status = value.get("status")
    require(status in ("pass", "fail") and (not selected or status == "pass"),
            "choice needs a resolved qualification verdict; selected choice must have passed")


def selection_inputs(docs, receipt):
    topology = docs["topology"]
    selections = topology.get("drafter_selection", {})
    require(isinstance(selections, dict) and all(isinstance(v, str) and v for v in selections.values()),
            "current topology drafter_selection is malformed")
    proposed = receipt.get("proposed_topology")
    if proposed is None:
        return selections, selections
    proposed_doc = yaml.safe_load(reference(proposed))
    require({k: v for k, v in topology.items() if k != "drafter_selection"}
            == {k: v for k, v in proposed_doc.items() if k != "drafter_selection"},
            "proposed topology includes changes outside drafter_selection")
    proposed_selections = proposed_doc["drafter_selection"]
    require(isinstance(proposed_selections, dict), "proposed drafter_selection is malformed")
    return selections, proposed_selections


def role_decision(scope_row, decision, backend, docs, selections, proposed, binding):
    role = scope_row["role"]
    label = f"{backend}/{role}"
    model_path = scope_row["model_path"]
    require(known(model_path) and decision["model_path"] == model_path, f"{label}: target model differs from scope")
    serving = docs["priors"]["roles"][role]["serving"]
    server = serving["server_role"]
    require(known(server) and decision["server_role"] == server, f"{label}: launching server differs from priors")
    registry = docs["registry"]
    model_role = registry["server_mode"][server].get("model_role", server)
    drafters = registry["roles"][model_role].get("drafters")
    require(isinstance(drafters, dict), f"{label}: registry drafter availability is unknown; declare drafters explicitly")
    declared = {}
    for name, recipe in drafters.items():
        require(isinstance(name, str) and known(name) and name != "none" and isinstance(recipe, dict)
                and isinstance(recipe.get("spec_type"), str) and known(recipe["spec_type"])
                and recipe["spec_type"] != "none" and isinstance(recipe.get("draft_model"), str)
                and known(recipe["draft_model"]), f"{label}: malformed registered drafter {name!r}")
        declared[name] = recipe["spec_type"]
    current = selections.get(server)
    if current is None and len(declared) == 1:
        current = next(iter(declared))
    require(current in declared or current == "none", f"{label}: current drafter selection is unknown")
    # Aliases use the launching server's resolved drafter. Scope can omit their flags.
    if server == role:
        require((scope_row["spec_type"] or "none") == (declared.get(current) or "none"),
                f"{label}: incumbent compiled speculation differs from topology/registry")
    candidate, anchor, supported = binding
    eligible = {name: spec for name, spec in declared.items() if spec in supported}
    selected = decision["selected"]
    if selected == "none" or current == "none":
        require("none" in supported, f"{label}: candidate does not advertise the no-drafter type")
        eligible["none"] = "none"
    require(eligible and decision["choices"].keys() == eligible.keys(),
            f"{label}: missing or unsupported eligible choice; expected {sorted(eligible)}")
    reason = decision["reason"]
    require(decision["current"] == current and selected in eligible and isinstance(reason, str) and known(reason),
            f"{label}: missing, unresolved or unsupported selection decision")
    changed = current != selected
    require(decision["decision"] == ("changed" if changed else "unchanged"), f"{label}: incorrect decision kind")
    require(proposed.get(server, current) == selected and (not changed or server in proposed),
            f"{label}: proposed topology does not carry the selected drafter")
    for name, spec in eligible.items():
        evidence_record(decision["choices"][name], {
            "backend": backend, "role": role, "model_path": model_path,
            "choice": name, "spec_type": spec, "candidate": candidate, "anchor": anchor,
        }, selected=name == selected)
    return server, current, selected


def validate(receipt, scope, orch, commit, incumbent, backends):
    require(receipt["schema"] == SCHEMA and receipt["status"] == "pass", "expected a completed CH-17 receipt")
    require(scope.keys() == set(backends) and all(scope.values()), "promoted backend scope is missing or empty")
    docs = source_inputs(receipt, orch)
    bindings = image_bindings(receipt, scope, commit, incumbent)
    selections, proposed = selection_inputs(docs, receipt)
    expected = {(backend, row["role"]): row for backend, rows in scope.items() for row in rows}
    require(len(expected) == sum(map(len, scope.values())), "duplicate role in derived promotion scope")
    decisions = {(row["backend"], row["role"]): row for row in receipt["roles"]}
    require(len(decisions) == len(receipt["roles"]) and expected.keys() == decisions.keys(),
            f"CH-17 scope roles differ: missing {sorted(expected.keys() - decisions.keys())}; "
            f"unexpected {sorted(decisions.keys() - expected.keys())}; duplicate roles are forbidden")
    process_choices = {}
    changes = {}
    for (backend, role), row in expected.items():
        server, current, selected = role_decision(
            row, decisions[backend, role], backend, docs, selections, proposed, bindings[backend])
        require(process_choices.setdefault(server, selected) == selected,
                f"conflicting decisions for shared server {server}")
        if current != selected:
            changes[server] = selected
    changed_keys = {key for key in selections.keys() | proposed.keys() if selections.get(key) != proposed.get(key)}
    require(changed_keys == changes.keys(), "reviewed topology changes differ from the in-scope drafter decisions")
    for name, path in INPUTS.items():
        check_pin(orch / path, receipt["inputs"][name])
