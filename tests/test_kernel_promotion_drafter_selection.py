"""Socket-free controls for CH-17 package admission."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude/skills/kernel-promotion/scripts"
sys.path.insert(0, str(SCRIPTS))
import drafter_selection_receipt as ch17  # noqa: E402

CANDIDATE = "a" * 40
ANCHOR = "b" * 40
TREE = "c" * 40


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def packet(tmp_path, monkeypatch):
    monkeypatch.setattr(ch17, "production_runtime_dirs", lambda: [])
    orch = tmp_path / "orch"
    stage = tmp_path / "stage"
    image_identity = put(stage / "BUILD-IDENTITY.json", json.dumps({
        "schema": "epyc.build-identity.v1", "source_sha": CANDIDATE, "source_tree": TREE,
        "kind": "cpu", "branch": "llama.cpp-experimental",
    }))
    binary = stage / "bin/llama-server"
    executable = put(binary, "fixture image with distinct candidate bytes")
    binary.chmod(0o500)
    from kernel_promotion_hot_stack import LIBRARIES
    inventory = [f'{executable["sha256"]}  bin/llama-server']
    for name in LIBRARIES:
        lib = put(stage / "bin" / name, name)
        inventory.append(f'{lib["sha256"]}  bin/{name}')
    manifest = put(stage / "SHA256SUMS.fixture", "\n".join(inventory) + "\n")
    incumbent = put(tmp_path / "incumbent/llama-server", "fixture incumbent bytes")
    ratification = put(tmp_path / "ratification.json", json.dumps({
        "production_head": ANCHOR, "production_frozen": True,
        "production_binary_sha256": {"cpu": incumbent["sha256"]},
    }))
    help_ref = put(tmp_path / "candidate.help", "--spec-type none,draft-mtp,draft-dflash    spec list\n")
    topology = {"numa_mode": "both", "drafter_selection": {"critic": "mtp", "vision": "none"}}
    registry = {
        "server_mode": {"critic": {"model_role": "qwen"}, "vision": {}},
        "roles": {
            "qwen": {"drafters": {
                "mtp": {"spec_type": "draft-mtp", "draft_model": "/model/target.gguf"},
                "dflash2": {"spec_type": "draft-dflash", "draft_model": "/model/dflash2.gguf"},
            }},
            "vision": {"drafters": {}},
        },
    }
    pins = {name: put(orch / ch17.INPUTS[name], yaml.safe_dump(doc))["sha256"]
            for name, doc in (("topology", topology), ("registry", registry))}
    priors = {
        "source_artifacts": {
            key: {"path": ch17.INPUTS[name], "sha256": pins[name]}
            for key, name in (("stack_topology", "topology"), ("registry", "registry"))
        },
        "roles": {"critic": {"serving": {"server_role": "critic"}},
                  "vision": {"serving": {"server_role": "vision"}}},
    }
    pins["priors"] = put(orch / ch17.INPUTS["priors"], yaml.safe_dump(priors))["sha256"]
    changed_topology = topology | {"drafter_selection": {"critic": "dflash2", "vision": "none"}}
    proposal = put(tmp_path / "proposed.yaml", yaml.safe_dump(changed_topology))
    scope = {"cpu": [
        {"role": "critic", "model_path": "/model/target.gguf", "binary_path": incumbent["path"],
         "spec_type": "draft-mtp"},
        {"role": "vision", "model_path": "/model/vision.gguf", "binary_path": incumbent["path"],
         "spec_type": None},
    ]}
    roles = []
    evidence = []
    for scope_role, current, selected, choices in (
        (scope["cpu"][0], "mtp", "dflash2", {"mtp": "draft-mtp", "dflash2": "draft-dflash"}),
        (scope["cpu"][1], "none", "none", {"none": "none"}),
    ):
        role = scope_role["role"]
        path = scope_role["model_path"]
        refs = {}
        for choice, spec in choices.items():
            record = {
                "status": "pass",
                "binding": {"backend": "cpu", "role": role, "model_path": path,
                            "choice": choice, "spec_type": spec,
                            "candidate": {"commit": CANDIDATE, "binary_sha256": executable["sha256"]},
                            "anchor": {"commit": ANCHOR, "binary_sha256": incumbent["sha256"]}},
                "workload": "fixed registered workload", "decision_rule": "predeclared criterion",
                "custody": "source result digest and run identity", "quality": "retained quality result",
                "measured_limits": "one pinned context and shape",
            }
            ref_path = tmp_path / f"{role}-{choice}.json"
            refs[choice] = put(ref_path, json.dumps({"arms": [record]})) | {"pointer": "/arms/0"}
            evidence.append((ref_path, record))
        roles.append({
            "backend": "cpu", "role": role, "server_role": role, "model_path": path,
            "current": current, "selected": selected, "decision": "changed" if current != selected else "unchanged",
            "reason": "Reviewed the pinned qualification within its measured limits.", "choices": refs,
        })
    receipt = {
        "schema": ch17.SCHEMA, "status": "pass", "inputs": pins, "proposed_topology": proposal,
        "candidate": {"source_commit": CANDIDATE, "source_tree": TREE, "branch": "llama.cpp-experimental",
                      "images": {"cpu": {
                          "stage": {"root": str(stage), "inventory": "SHA256SUMS.fixture",
                                    "inventory_sha256": manifest["sha256"],
                                    "identity_sha256": image_identity["sha256"]},
                          "binary_sha256": executable["sha256"],
                          "help": help_ref | {"argv": [str(binary), "--help"], "exit_code": 0,
                                              "source_commit": CANDIDATE, "binary_sha256": executable["sha256"]},
                          "supported_spec_types": ["draft-dflash", "draft-mtp", "none"],
                      }}},
        "anchors": {"cpu": {"binary": incumbent["path"], "commit": ANCHOR, "binary_sha256": incumbent["sha256"]}},
        "roles": roles,
    }
    config = {"ratification": "ratification.json", "ratification_sha256": ratification["sha256"],
              "commit": ANCHOR}
    return receipt, scope, orch, evidence, ch17.incumbent_pins(config, ("cpu",), roots=(tmp_path,))


def check(packet, backends=("cpu",)):
    receipt, scope, orch, _, incumbent = packet
    return ch17.validate(receipt, scope, orch, CANDIDATE, incumbent, backends)


def test_changed_and_explicit_no_drafter(packet):
    check(packet)


def test_unchanged_still_requires_both_eligible_choices(packet):
    receipt, *_ = packet
    receipt.pop("proposed_topology")
    receipt["roles"][0].update(selected="mtp", decision="unchanged")
    check(packet)
    receipt["roles"][0]["choices"].pop("dflash2")
    with pytest.raises(ValueError, match="missing or unsupported eligible choice"):
        check(packet)


@pytest.mark.parametrize(("mutate", "error"), [
    (lambda r: r["roles"].pop(), "scope roles differ"),
    (lambda r: r["roles"].append(r["roles"][0] | {"selected": "mtp"}), "duplicate roles"),
    (lambda r: r["roles"][0].update(reason="unknown"), "selection decision"),
    (lambda r: r["candidate"]["images"]["cpu"].update(binary_sha256=None), "executable pin"),
    (lambda r: r["candidate"]["images"]["cpu"]["help"].update(source_commit=ANCHOR), "help witness"),
    (lambda r: r["roles"][0]["choices"]["mtp"].update(path="/missing-qualification.json"), "missing.*evidence"),
    (lambda r: r["roles"][0]["choices"]["mtp"].update(pointer="/arms/1"), "list index"),
    (lambda r: r["roles"][0]["choices"].update(eagle3=r["roles"][0]["choices"]["mtp"]), "unsupported eligible"),
    (lambda r: r.pop("proposed_topology"), "proposed topology"),
    (lambda r: r["anchors"]["cpu"].update(commit=CANDIDATE), "anchor does not match"),
])
def test_refuses_incomplete_or_conflicting_receipt(packet, mutate, error):
    receipt, _, orch, _, _ = packet
    topology = orch / ch17.INPUTS["topology"]
    before = topology.read_bytes()
    mutate(receipt)
    with pytest.raises((ValueError, IndexError), match=error):
        check(packet)
    assert topology.read_bytes() == before


@pytest.mark.parametrize("subject", ["topology", "registry", "priors"])
def test_stale_source_snapshot_refuses(packet, subject):
    _, _, orch, _, _ = packet
    path = orch / ch17.INPUTS[subject]
    path.write_bytes(path.read_bytes() + b"\n# drift\n")
    with pytest.raises(ValueError, match="changed SHA-256 pin"):
        check(packet)


def test_missing_registry_drafters_is_unknown(packet):
    receipt, _, orch, _, _ = packet
    registry_path = orch / ch17.INPUTS["registry"]
    registry = yaml.safe_load(registry_path.read_bytes())
    del registry["roles"]["vision"]["drafters"]
    receipt["inputs"]["registry"] = put(registry_path, yaml.safe_dump(registry))["sha256"]
    priors_path = orch / ch17.INPUTS["priors"]
    priors = yaml.safe_load(priors_path.read_bytes())
    priors["source_artifacts"]["registry"]["sha256"] = receipt["inputs"]["registry"]
    receipt["inputs"]["priors"] = put(priors_path, yaml.safe_dump(priors))["sha256"]
    with pytest.raises(ValueError, match="registry drafter availability is unknown"):
        check(packet)


@pytest.mark.parametrize("field", ["candidate", "anchor"])
def test_evidence_from_wrong_candidate_or_anchor_refuses(packet, field):
    receipt, _, _, evidence, _ = packet
    path, record = evidence[0]
    record["binding"][field]["commit"] = "0" * 40
    receipt["roles"][0]["choices"]["mtp"].update(put(path, json.dumps({"arms": [record]})))
    with pytest.raises(ValueError, match="qualification candidate, anchor"):
        check(packet)


def test_rehashed_incumbent_executable_must_match_ratification(packet):
    receipt, _, _, _, _ = packet
    anchor = receipt["anchors"]["cpu"]
    replacement = put(Path(anchor["binary"]), "different executable at the same store path")
    anchor["binary_sha256"] = replacement["sha256"]
    with pytest.raises(ValueError, match="anchor binary differs from approved ratification"):
        check(packet)


def test_load_only_record_cannot_qualify_choice(packet):
    receipt, _, _, evidence, _ = packet
    path, record = evidence[0]
    record.pop("quality")
    receipt["roles"][0]["choices"]["mtp"].update(put(path, json.dumps({"arms": [record]})))
    with pytest.raises(ValueError, match="qualification lacks known"):
        check(packet)


def test_rejected_alternative_is_evidence_but_selected_choice_requires_pass(packet):
    receipt, _, _, evidence, _ = packet
    path, record = evidence[0]
    record["status"] = "fail"
    receipt["roles"][0]["choices"]["mtp"].update(put(path, json.dumps({"arms": [record]})))
    check(packet)
    path, record = evidence[1]
    record["status"] = "fail"
    receipt["roles"][0]["choices"]["dflash2"].update(put(path, json.dumps({"arms": [record]})))
    with pytest.raises(ValueError, match="selected choice must have passed"):
        check(packet)


def test_unresolved_nested_evidence_refuses(packet):
    receipt, _, _, evidence, _ = packet
    path, record = evidence[0]
    record["quality"] = {"actually_measured": "unknown"}
    receipt["roles"][0]["choices"]["mtp"].update(put(path, json.dumps({"arms": [record]})))
    with pytest.raises(ValueError, match="qualification lacks known"):
        check(packet)


def test_alias_cannot_keep_the_outgoing_drafter_when_shared_server_changes(packet):
    receipt, scope, orch, _, _ = packet
    priors_path = orch / ch17.INPUTS["priors"]
    priors = yaml.safe_load(priors_path.read_bytes())
    priors["roles"]["critic_alias"] = {"serving": {"server_role": "critic"}}
    receipt["inputs"]["priors"] = put(priors_path, yaml.safe_dump(priors))["sha256"]
    scope["cpu"].append(scope["cpu"][0] | {"role": "critic_alias", "spec_type": None})
    receipt["roles"].append(receipt["roles"][0] | {"role": "critic_alias", "selected": "mtp",
                                                 "decision": "unchanged"})
    with pytest.raises(ValueError, match="proposed topology does not carry the selected drafter"):
        check(packet)


def test_required_backends_are_external_to_receipt(packet):
    with pytest.raises(ValueError, match="backend scope"):
        check(packet, backends=("cpu", "gpu"))


@pytest.mark.parametrize("text", ["", "--spec-type none,none", "--spec-type TYPE", "--spec-type none,"])
def test_missing_or_ambiguous_help_fails_closed(text):
    with pytest.raises(ValueError, match="capability"):
        ch17.supported_types(text)


def test_package_refuses_missing_receipt_before_writing(tmp_path):
    config = yaml.safe_load((SCRIPTS.parent / "promotion_gates.yaml").read_bytes())
    evidence = tmp_path / "evidence"
    for gate, spec in config["gates"].items():
        if spec.get("required") and gate != ch17.GATE:
            put(evidence / f"{gate}.json", '{"status": "pass"}')
    output = tmp_path / "package.json"
    result = subprocess.run([
        str(SCRIPTS / "package.sh"), "--candidate", CANDIDATE, "--out", str(output),
        "--evidence", str(evidence), "--backend", "cpu",
    ], capture_output=True, text=True, check=False)
    assert result.returncode == 1, result.stderr
    assert "missing required gate 'drafter_selection'" in result.stdout
    assert not output.exists()
