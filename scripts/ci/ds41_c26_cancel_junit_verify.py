#!/usr/bin/env python3
"""Exact source-AST, parameter-product and JUnit verifier; stdlib/Git data only."""
import ast
from collections import Counter
import hashlib
import itertools
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

TEST_PATHS = (
    "scripts/kernel_rnd/autokernel/loop/test_initial_serving_floor.py",
    "scripts/kernel_rnd/autokernel/loop/test_serving.py",
)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args], stderr=subprocess.PIPE)

def ast_digest(node):
    return sha(ast.dump(node, include_attributes=False).encode())

def body_digest(node):
    return ast_digest(ast.Module(body=node.body, type_ignores=[]))

def parameters_from_source(fn):
    dimensions = []
    # Function decorator marks are applied bottom-up; exact IDs retain that order.
    for decorator in reversed(fn.decorator_list):
        if not isinstance(decorator, ast.Call) or not ast.unparse(decorator.func).endswith("parametrize"):
            continue
        names = ast.literal_eval(decorator.args[0])
        names = [names] if isinstance(names, str) else list(names)
        raw_values = ast.literal_eval(decorator.args[1])
        values = [[value] if len(names) == 1 else list(value) for value in raw_values]
        if any(len(row) != len(names) for row in values):
            raise ValueError("parametrize row arity differs from names")
        dimensions.append({"names": names, "values": values})
    return dimensions

def testcase_identity_map(parsed_by_path):
    found = {}
    for path, parsed in parsed_by_path.items():
        module = path[:-3].replace("/", ".")
        if path == TEST_PATHS[0]:
            for node in parsed.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    dims = parameters_from_source(node)
                    if not dims:
                        raise ValueError("startup source no longer carries literal dimensions")
                    for values in itertools.product(*(dimension["values"] for dimension in dims)):
                        params = {}; id_parts = []
                        for dimension, row in zip(dims, values):
                            params.update(zip(dimension["names"], row)); id_parts.extend(str(value) for value in row)
                        name = node.name + "[" + "-".join(id_parts) + "]"
                        found[(module, name)] = (path, node, params)
        else:
            for cls in parsed.body:
                if isinstance(cls, ast.ClassDef):
                    for node in cls.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                            found[(module + "." + cls.name, node.name)] = (path, node, {})
    return found

def verify(source: Path, manifest_path: Path, junit_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_bytes())
    source_pin = manifest["source_pin"]
    if git(source, "rev-parse", "HEAD").decode().strip() != source_pin:
        raise ValueError("source checkout does not match case-manifest pin")
    parsed_by_path = {}
    file_records = manifest["source_files"]
    if set(file_records) != set(TEST_PATHS):
        raise ValueError("manifest's whole-module file set differs")
    for path, expected in file_records.items():
        raw = git(source, "show", f"{source_pin}:{path}")
        row = git(source, "ls-tree", source_pin, "--", path).decode().split()
        if row[0] != expected["mode"] or row[2] != expected["blob"]:
            raise ValueError("test file Git blob/mode differs: " + path)
        if len(raw) != expected["bytes"] or sha(raw) != expected["sha256"]:
            raise ValueError("test file bytes/SHA differs: " + path)
        parsed = ast.parse(raw.decode("utf-8"), filename=path)
        if ast_digest(parsed) != expected["ast_sha256"]:
            raise ValueError("whole module AST differs: " + path)
        parsed_by_path[path] = parsed
    startup = next(n for n in parsed_by_path[TEST_PATHS[0]].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "test_selected_startup_prepares_only_missing_exact_floor")
    dims = parameters_from_source(startup)
    recorded_dims = manifest["parameter_dimensions"].get(TEST_PATHS[0])
    if recorded_dims != dims:
        raise ValueError("literal parameter dimensions differ from frozen manifest")
    source_items = testcase_identity_map(parsed_by_path)
    actual_records = {}
    for row in manifest["testcases"]:
        identity = (row["classname"], row["name"])
        if identity in actual_records:
            raise ValueError("manifest duplicates an expected JUnit identity")
        actual_records[identity] = row
    if len(source_items) != 46 or len(actual_records) != 46 or set(source_items) != set(actual_records):
        raise ValueError("source-derived cases and exact manifest are not the same 46 identities")
    for identity, (path, node, params) in source_items.items():
        row = actual_records[identity]
        if row["source_path"] != path or row["parameters"] != params:
            raise ValueError("case source path or literal parameters differ: " + repr(identity))
        if row["definition_ast_sha256"] != ast_digest(node) or row["body_ast_sha256"] != body_digest(node):
            raise ValueError("original complete test definition/body AST differs: " + repr(identity))
    junit_root = ET.parse(junit_path).getroot()
    actual = []
    for node in junit_root.iter("testcase"):
        identity = (node.attrib.get("classname", ""), node.attrib.get("name", ""))
        if not all(identity):
            raise ValueError("JUnit testcase is missing classname/name")
        if any(node.find(tag) is not None for tag in ("failure", "error", "skipped")):
            raise ValueError("JUnit contains a nonpassing, skipped or failed case: " + repr(identity))
        actual.append(identity)
    if Counter(actual) != Counter(actual_records.keys()):
        raise ValueError("JUnit exact classname/name multiset differs from all source-derived identities")
    return {"result": "PASS", "source_pin": source_pin, "whole_modules": list(TEST_PATHS), "parametrized_cases": sum(1 for row in actual_records.values() if row["parameters"]), "ordinary_test_methods": sum(1 for row in actual_records.values() if not row["parameters"]), "expected_and_actual": len(actual), "source_definition_body_hashes_checked": len(actual_records), "duplicate_or_missing": False}
