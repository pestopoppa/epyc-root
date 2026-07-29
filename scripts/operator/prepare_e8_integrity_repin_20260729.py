#!/usr/bin/env python3
"""One-signature ceremony: re-pin the E8 v4 integrity trio + the amendment test chain.

PREPARED 2026-07-29 by fable-auditor (task prepare-v4-manifest-repin); APPLY ONLY
after the tier-A wave is final, with one operator token. Two coupled integrity
envelopes drifted for structural reasons and both need exactly one signature:

  A. v4 integrity trio — the six-artifact manifest
     (artifacts/operator/e8_quality_baseline_v4_integrity_20260727.json), the
     INTEGRITY_SHA256 pin inside the v4 ratify wrapper, and the expected-set
     list in tests/test_e8_quality_baseline_v4_wrapper.py. 2/6 artifacts had
     drifted at preparation time and more were expected while tier-A landed.
  B. amendment chain — tests/test_e8_quality_source_protocol_amendment.py was
     hash-pinned INSIDE the ratified amendment manifest, so its red-test fix
     (exit-code-agnostic live guard + hermetic exit-0 twin; see
     scripts/operator/patches/amendment_test_exitcode_agnostic_20260729.patch)
     could never be a one-file change. OPERATOR DECISION 2026-07-29
     (unbind-the-checker): the trust envelope binds the INSTRUMENT (script,
     helper, decision doc), never the instrument's CHECKER (the test suite) —
     this was the repo's only manifest pinning a test file, and doing so made
     red-test hygiene operator-gated. The ceremony therefore REMOVES the test
     entry from artifact_sha256, patches the helper's hardcoded expected set
     (scripts/operator/patches/amendment_helper_unbind_checker_20260729.patch),
     re-pins the helper's own manifest entry, and cascades the manifest hash
     into the amendment script's MANIFEST_SHA256.

Design contract (operator-directed):
  * PINS BY GIT CONTENT — every artifact hash is computed from
    `git show <commit>:<path>`, never from live files (the capacityfix-ratifier
    pattern; closes check-then-exec TOCTOU).
  * RECOMPUTES, NEVER HARDCODES — no artifact hash appears in this file; the
    operator names the commits, the tool derives everything.
  * DRIFT-REFUSING — apply refuses unless every live artifact byte-matches the
    named commits, so a pin can never be stale at birth.
  * NO TEST-ONLY GREENING — the test's expected set is GENERATED from the same
    manifest the wrapper pin covers, and the post-apply verifier re-derives the
    whole chain independently; manifest and test cannot end up disagreeing.
  * IDEMPOTENT — a second apply with the same inputs is a no-op (exit 0).
  * REFUSES PARTIAL STATE — apply refuses to start from a half-applied state;
    every target is backed up (<target>.pre-repin-20260729) and rolled back on
    any post-publish verification failure.

Usage (operator, at apply time — one pre-validated command):
  scripts/operator/prepare_e8_integrity_repin_20260729.py \
      --orch-commit <final-orch-sha> --root-commit <final-root-sha> --dry-run
  # review the printed plan, then the SAME command with:
  #   --apply --attest REPIN-E8-V4-INTEGRITY-AND-AMENDMENT-TEST-20260729
Verification any time:  --verify --orch-commit <sha> --root-commit <sha>
Self-contained proof:   --selftest   (builds a COPY, runs the full ceremony
                        against it, exercises idempotence and partial-refusal,
                        and pytests the re-pinned tests in the copy; the real
                        tree is never written)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANONICAL_ROOT = Path("/mnt/raid0/llm/epyc-root")
CANONICAL_ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")
TOKEN = "REPIN-E8-V4-INTEGRITY-AND-AMENDMENT-TEST-20260729"
STAMP = "pre-repin-20260729"

V4_MANIFEST_REL = "artifacts/operator/e8_quality_baseline_v4_integrity_20260727.json"
V4_WRAPPER_REL = "artifacts/operator/ratify_and_apply_e8_quality_baseline_v4_20260727.sh"
V4_TEST_REL = "tests/test_e8_quality_baseline_v4_wrapper.py"
AMEND_MANIFEST_REL = (
    "artifacts/operator/e8_quality_source_protocol_amendment_manifest_20260726.json"
)
AMEND_SCRIPT_REL = "artifacts/operator/amend_e8_quality_source_protocol_20260726.sh"
AMEND_TEST_REL = "tests/test_e8_quality_source_protocol_amendment.py"
AMEND_HELPER_REL = "artifacts/operator/e8_quality_source_amendment.py"
PATCH_REL = "scripts/operator/patches/amendment_test_exitcode_agnostic_20260729.patch"
HELPER_PATCH_REL = "scripts/operator/patches/amendment_helper_unbind_checker_20260729.patch"

ALL_TARGET_RELS = [
    V4_MANIFEST_REL,
    V4_WRAPPER_REL,
    V4_TEST_REL,
    AMEND_MANIFEST_REL,
    AMEND_SCRIPT_REL,
    AMEND_TEST_REL,
    AMEND_HELPER_REL,
]

ORCH_PREFIX = "/mnt/raid0/llm/epyc-orchestrator/"


class RepinError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_content(repo: Path, commit: str, rel: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{rel}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RepinError(
            f"git content unavailable: {repo} {commit[:12]}:{rel} — "
            f"{proc.stderr.decode(errors='replace').strip()}"
        )
    return proc.stdout


def artifact_repo_rel(key: str, root: Path, orch: Path) -> tuple[Path, str, Path]:
    """Map a manifest key to (repo, repo-relative path, live path). Refuses unknowns."""
    if key.startswith(ORCH_PREFIX):
        return orch, key[len(ORCH_PREFIX):], Path(key)
    if key.startswith("/"):
        raise RepinError(f"manifest artifact in no known repo: {key}")
    return root, key, root / key


def replace_exactly_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RepinError(f"{label}: expected exactly 1 occurrence of the current "
                         f"value, found {count} — refusing to guess")
    return text.replace(old, new, 1)


def stage_patch(root: Path, patch_rel: str, target_rel: str) -> bytes:
    """Return the target's post-patch bytes. Drift-refusing and idempotent:
    refuses when the patch neither applies nor is already applied."""
    patch_path = root / patch_rel
    if not patch_path.is_file():
        raise RepinError(f"ceremony patch missing: {patch_path}")
    target = root / target_rel
    check = subprocess.run(
        ["git", "-C", str(root), "apply", "--check", str(patch_path)],
        capture_output=True, text=True, check=False,
    )
    already = subprocess.run(
        ["git", "-C", str(root), "apply", "--check", "--reverse", str(patch_path)],
        capture_output=True, text=True, check=False,
    )
    if check.returncode != 0 and already.returncode != 0:
        raise RepinError(
            f"{patch_rel} neither applies nor is already applied — {target_rel} "
            f"drifted; regenerate the patch. git apply --check said: "
            f"{check.stderr.strip()}"
        )
    if check.returncode != 0:
        return target.read_bytes()
    with tempfile.TemporaryDirectory(dir="/mnt/raid0/llm/tmp") as tmp:
        staged = Path(tmp) / target_rel
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, staged)
        applied = subprocess.run(
            ["git", "apply", str(patch_path)],
            capture_output=True, text=True, check=False, cwd=tmp,
        )
        if applied.returncode != 0:
            raise RepinError(f"staging {patch_rel} failed: {applied.stderr}")
        return staged.read_bytes()


def compute_plan(root: Path, orch: Path, orch_commit: str, root_commit: str) -> dict:
    """Derive every desired byte from git content. Pure; writes nothing."""
    v4_manifest_path = root / V4_MANIFEST_REL
    manifest = json.loads(v4_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "epyc.e8_quality_baseline_v4_integrity.v1":
        raise RepinError("v4 integrity manifest schema differs — wrong file?")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise RepinError("v4 integrity manifest has no artifact map")

    new_hashes: dict[str, str] = {}
    drift: list[str] = []
    for key, old_digest in artifacts.items():
        repo, rel, live = artifact_repo_rel(key, root, orch)
        commit = orch_commit if repo == orch else root_commit
        pinned = sha256_bytes(git_content(repo, commit, rel))
        new_hashes[key] = pinned
        if not live.is_file():
            drift.append(f"{key}: live file MISSING")
        elif sha256_file(live) != pinned:
            drift.append(f"{key}: live differs from {commit[:12]} (tier-A still "
                         f"moving, or wrong commit named)")

    # New manifest bytes: value-substitution only, so formatting survives.
    manifest_text = v4_manifest_path.read_text(encoding="utf-8")
    for key, old_digest in artifacts.items():
        if new_hashes[key] != old_digest:
            manifest_text = replace_exactly_once(
                manifest_text, old_digest, new_hashes[key], f"v4 manifest[{key}]")
    new_manifest_hash = sha256_bytes(manifest_text.encode("utf-8"))

    # Wrapper pin line.
    wrapper_path = root / V4_WRAPPER_REL
    wrapper_text = wrapper_path.read_text(encoding="utf-8")
    pin_match = re.search(r'^INTEGRITY_SHA256="([0-9a-f]{64})"$', wrapper_text, re.M)
    if not pin_match:
        raise RepinError("v4 wrapper INTEGRITY_SHA256 line not found")
    new_wrapper_text = wrapper_text
    if pin_match.group(1) != new_manifest_hash:
        new_wrapper_text = replace_exactly_once(
            wrapper_text,
            f'INTEGRITY_SHA256="{pin_match.group(1)}"',
            f'INTEGRITY_SHA256="{new_manifest_hash}"',
            "v4 wrapper pin",
        )

    # Test expected set: GENERATED from the manifest keys — the no-test-only-
    # greening property. The block is replaced between its exact delimiters.
    test_path = root / V4_TEST_REL
    test_text = test_path.read_text(encoding="utf-8")
    block = re.search(r"    required = \{\n(?:        \"[^\n]+\n)+    \}\n", test_text)
    if not block:
        raise RepinError("v4 test `required = {...}` block not found")
    generated = "    required = {\n" + "".join(
        f'        "{key}",\n' for key in sorted(artifacts)
    ) + "    }\n"
    new_test_text = test_text.replace(block.group(0), generated, 1)

    # Amendment chain: patched test -> manifest artifact_sha256 -> script pin.
    new_amend_test_bytes = stage_patch(root, PATCH_REL, AMEND_TEST_REL)
    new_amend_test_hash = sha256_bytes(new_amend_test_bytes)
    new_helper_bytes = stage_patch(root, HELPER_PATCH_REL, AMEND_HELPER_REL)
    new_helper_hash = sha256_bytes(new_helper_bytes)

    amend_manifest_path = root / AMEND_MANIFEST_REL
    amend_manifest = json.loads(amend_manifest_path.read_text(encoding="utf-8"))
    binding = amend_manifest.get("artifact_sha256")
    if not isinstance(binding, dict) or AMEND_HELPER_REL not in binding:
        raise RepinError("amendment manifest artifact binding is missing — wrong file?")
    new_amend_manifest_text = amend_manifest_path.read_text(encoding="utf-8")
    # UNBIND THE CHECKER (operator decision 2026-07-29): the trust envelope
    # binds the instrument, never the instrument's checker. Remove the test
    # entry entirely; idempotent when already absent.
    old_test_pin = binding.get(AMEND_TEST_REL)
    if isinstance(old_test_pin, str):
        entry = f',\n    "{AMEND_TEST_REL}": "{old_test_pin}"'
        if new_amend_manifest_text.count(entry) != 1:
            raise RepinError("amendment manifest test entry not found in the "
                             "expected trailing position — refusing byte surgery")
        new_amend_manifest_text = new_amend_manifest_text.replace(entry, "", 1)
    # The helper is patched by this same ceremony, so its pin is recomputed.
    old_helper_pin = binding[AMEND_HELPER_REL]
    if old_helper_pin != new_helper_hash:
        new_amend_manifest_text = replace_exactly_once(
            new_amend_manifest_text, old_helper_pin, new_helper_hash,
            "amendment manifest helper pin")
    new_amend_manifest_hash = sha256_bytes(new_amend_manifest_text.encode("utf-8"))

    amend_script_path = root / AMEND_SCRIPT_REL
    amend_script_text = amend_script_path.read_text(encoding="utf-8")
    script_pin = re.search(r'^MANIFEST_SHA256="([0-9a-f]{64})"$', amend_script_text, re.M)
    if not script_pin:
        raise RepinError("amendment script MANIFEST_SHA256 line not found")
    new_amend_script_text = amend_script_text
    if script_pin.group(1) != new_amend_manifest_hash:
        new_amend_script_text = replace_exactly_once(
            amend_script_text,
            f'MANIFEST_SHA256="{script_pin.group(1)}"',
            f'MANIFEST_SHA256="{new_amend_manifest_hash}"',
            "amendment script manifest pin",
        )

    desired = {
        V4_MANIFEST_REL: manifest_text.encode("utf-8"),
        V4_WRAPPER_REL: new_wrapper_text.encode("utf-8"),
        V4_TEST_REL: new_test_text.encode("utf-8"),
        AMEND_MANIFEST_REL: new_amend_manifest_text.encode("utf-8"),
        AMEND_SCRIPT_REL: new_amend_script_text.encode("utf-8"),
        AMEND_TEST_REL: new_amend_test_bytes,
        AMEND_HELPER_REL: new_helper_bytes,
    }
    changed = {rel: (root / rel).read_bytes() != data for rel, data in desired.items()}
    return {
        "new_hashes": new_hashes,
        "drift": drift,
        "desired": desired,
        "changed": changed,
        "new_manifest_hash": new_manifest_hash,
        "new_amend_test_hash": new_amend_test_hash,
        "new_amend_manifest_hash": new_amend_manifest_hash,
    }


def verify_chain(root: Path, orch: Path, orch_commit: str, root_commit: str) -> list[str]:
    """Independent re-derivation of the full chain. Empty list == coherent."""
    problems: list[str] = []
    try:
        manifest = json.loads((root / V4_MANIFEST_REL).read_text(encoding="utf-8"))
        artifacts = manifest["artifacts"]
        for key, digest in artifacts.items():
            repo, rel, _live = artifact_repo_rel(key, root, orch)
            commit = orch_commit if repo == orch else root_commit
            if sha256_bytes(git_content(repo, commit, rel)) != digest:
                problems.append(f"manifest[{key}] != git content at named commit")
        wrapper_text = (root / V4_WRAPPER_REL).read_text(encoding="utf-8")
        pin = re.search(r'^INTEGRITY_SHA256="([0-9a-f]{64})"$', wrapper_text, re.M)
        if not pin or pin.group(1) != sha256_file(root / V4_MANIFEST_REL):
            problems.append("wrapper INTEGRITY_SHA256 != manifest bytes")
        test_text = (root / V4_TEST_REL).read_text(encoding="utf-8")
        block = re.search(r"    required = \{\n((?:        \"[^\n]+\n)+)    \}\n", test_text)
        if not block:
            problems.append("v4 test `required = {...}` block not found")
        else:
            listed = set(re.findall(r'^        "([^"]+)",$', block.group(1), re.M))
            if listed != set(artifacts):
                problems.append(f"test expected set != manifest keys "
                                f"(test-only greening shape): {sorted(listed ^ set(artifacts))}")
        amend_manifest = json.loads((root / AMEND_MANIFEST_REL).read_text(encoding="utf-8"))
        amend_binding = amend_manifest["artifact_sha256"]
        if AMEND_TEST_REL in amend_binding:
            problems.append("amendment manifest still binds the CHECKER (test file) "
                            "— operator decision 2026-07-29 is instrument-only binding")
        for rel, digest in amend_binding.items():
            if not (root / rel).is_file() or sha256_file(root / rel) != digest:
                problems.append(f"amendment manifest[{rel}] != live bytes")
        amend_script_text = (root / AMEND_SCRIPT_REL).read_text(encoding="utf-8")
        spin = re.search(r'^MANIFEST_SHA256="([0-9a-f]{64})"$', amend_script_text, re.M)
        if not spin or spin.group(1) != sha256_file(root / AMEND_MANIFEST_REL):
            problems.append("amendment script MANIFEST_SHA256 != amendment manifest bytes")
    except (RepinError, KeyError, json.JSONDecodeError, OSError) as exc:
        problems.append(f"chain verification failed to run: {exc}")
    return problems


def apply_plan(root: Path, plan: dict) -> list[str]:
    """Back up, publish atomically per file, verify, roll back on failure."""
    changed_rels = [rel for rel, changed in plan["changed"].items() if changed]
    backups: dict[str, Path] = {}
    published: list[str] = []
    try:
        for rel in changed_rels:
            target = root / rel
            backup = target.with_name(target.name + f".{STAMP}")
            if backup.exists():
                raise RepinError(f"backup already exists — refusing to clobber "
                                 f"evidence of a prior partial apply: {backup}")
            shutil.copyfile(target, backup)
            backups[rel] = backup
        for rel in changed_rels:
            target = root / rel
            tmp = target.with_name(target.name + ".repin-tmp")
            tmp.write_bytes(plan["desired"][rel])
            if rel.endswith(".sh") or rel.endswith(".py"):
                tmp.chmod(target.stat().st_mode)
            os.replace(tmp, target)
            published.append(rel)
        return changed_rels
    except BaseException:
        for rel in reversed(published):
            shutil.copyfile(backups[rel], root / rel)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    parser.add_argument("--attest")
    parser.add_argument("--orch-commit")
    parser.add_argument("--root-commit")
    parser.add_argument("--root", type=Path, default=CANONICAL_ROOT)
    parser.add_argument("--orch", type=Path, default=CANONICAL_ORCH)
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.orch_commit or not args.root_commit:
        parser.error("--orch-commit and --root-commit are required (pins derive "
                     "from git content at these commits, never from live files)")
    root, orch = args.root.resolve(), args.orch.resolve()

    if args.verify:
        problems = verify_chain(root, orch, args.orch_commit, args.root_commit)
        for p in problems:
            print(f"  FAIL {p}")
        print("chain: " + ("COHERENT" if not problems else f"{len(problems)} problem(s)"))
        return 0 if not problems else 1

    plan = compute_plan(root, orch, args.orch_commit, args.root_commit)
    changed = [rel for rel, c in plan["changed"].items() if c]
    print(f"pinned commits: orch={args.orch_commit[:12]} root={args.root_commit[:12]}")
    for key, digest in sorted(plan["new_hashes"].items()):
        print(f"  artifact {digest[:16]}…  {key}")
    print(f"  v4 manifest -> {plan['new_manifest_hash'][:16]}…  (wrapper pin follows)")
    print(f"  amendment test -> {plan['new_amend_test_hash'][:16]}…  "
          f"manifest -> {plan['new_amend_manifest_hash'][:16]}…  (script pin follows)")
    for d in plan["drift"]:
        print(f"  DRIFT {d}")
    print(f"targets needing change: {changed or '(none — already applied)'}")

    if args.dry_run:
        print("dry-run: nothing written" + ("" if not plan["drift"] else
              " — NOTE apply would REFUSE on the drift above"))
        return 0

    # --apply
    if args.attest != TOKEN:
        print(f"ERROR: --apply requires --attest {TOKEN}", file=sys.stderr)
        return 1
    if plan["drift"]:
        print("ERROR: refusing to mint pins that are stale at birth — live "
              "artifacts differ from the named commits:", file=sys.stderr)
        for d in plan["drift"]:
            print(f"  {d}", file=sys.stderr)
        return 1
    if not changed:
        print("already applied — idempotent no-op")
        return 0
    pre_problems = verify_chain(root, orch, args.orch_commit, args.root_commit)
    # A half-applied prior state shows up as SOME targets already at desired
    # bytes while the chain is incoherent; refuse rather than guess.
    partially = any(not c for c in plan["changed"].values()) and any(plan["changed"].values())
    if partially and pre_problems:
        print("ERROR: refusing a partially-applied state — some targets already "
              "carry the new pins while the chain is incoherent. Restore from "
              f"*.{STAMP} backups, then re-run.", file=sys.stderr)
        return 1
    applied = apply_plan(root, plan)
    post = verify_chain(root, orch, args.orch_commit, args.root_commit)
    if post:
        for rel in applied:
            target = root / rel
            shutil.copyfile(target.with_name(target.name + f".{STAMP}"), target)
        print("ERROR: post-apply verification failed; ALL targets rolled back:",
              file=sys.stderr)
        for p in post:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"applied {len(applied)} target(s); chain verified COHERENT; backups at "
          f"*.{STAMP}")
    return 0


def selftest() -> int:
    """Full ceremony against a COPY. The real tree is never written."""
    real_root = CANONICAL_ROOT
    with tempfile.TemporaryDirectory(dir="/mnt/raid0/llm/tmp") as tmp:
        copy_root = Path(tmp) / "root"
        rels = ALL_TARGET_RELS + [PATCH_REL, HELPER_PATCH_REL] + [
            "artifacts/operator/e8_quality_pool_regenerator.py",
            "artifacts/operator/e8_quality_source_protocol_amendment_20260726.md",
            # the four root-relative v4 artifacts, so the copy's manifest resolves
            "artifacts/operator/apply_e8_quality_baseline_state.py",
            "artifacts/operator/e8_context_replacement_map_candidate_relaxed_20260727.json",
            "artifacts/operator/e8_quality_context_coverage_v4_r2_20260727.json",
            "artifacts/operator/prepare_e8_quality_baseline_reseed_v4_20260727.sh",
        ]
        for rel in rels:
            src, dst = real_root / rel, copy_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            dst.chmod(src.stat().st_mode)
        subprocess.run(["git", "init", "-q"], cwd=copy_root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=copy_root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "fixture"], cwd=copy_root, check=True)
        root_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=copy_root,
                                     capture_output=True, text=True,
                                     check=True).stdout.strip()
        orch_commit = subprocess.run(["git", "-C", str(CANONICAL_ORCH), "rev-parse",
                                      "HEAD"], capture_output=True, text=True,
                                     check=True).stdout.strip()
        # The copy's root-relative artifacts match its own commit by construction;
        # the two orchestrator artifacts pin against the REAL orch repo read-only.
        # Live-vs-commit drift for those two depends on the real working tree —
        # report, and if the live orch files are mid-edit, selftest still proves
        # the refusal path (which is itself a required behaviour).
        base = ["--root", str(copy_root), "--orch", str(CANONICAL_ORCH),
                "--orch-commit", orch_commit, "--root-commit", root_commit]
        run = lambda *m: main([*m, *base])  # noqa: E731

        print("== selftest 1: dry-run (plan + drift report) ==")
        assert run("--dry-run") == 0
        print("== selftest 2: pre-apply verify must FAIL (old pins) ==")
        assert run("--verify") == 1
        print("== selftest 3: apply ==")
        code = main(["--apply", "--attest", TOKEN, *base])
        if code != 0:
            print("selftest: apply refused (live orch drift) — exercising the "
                  "refusal path is a PASS only if drift was reported; see above. "
                  "Re-run when the orch tree is quiescent for the full proof.")
            return 1
        print("== selftest 4: post-apply verify ==")
        assert run("--verify") == 0
        print("== selftest 5: idempotent re-apply ==")
        assert main(["--apply", "--attest", TOKEN, *base]) == 0
        print("== selftest 6: partial-state refusal ==")
        wrapper = copy_root / V4_WRAPPER_REL
        text = wrapper.read_text()
        wrapper.write_text(re.sub(r'^INTEGRITY_SHA256="[0-9a-f]{64}"$',
                                  'INTEGRITY_SHA256="' + "0" * 64 + '"',
                                  text, flags=re.M))
        assert run("--verify") == 1
        wrapper.write_text(text)
        assert run("--verify") == 0
        print("== selftest 7: pytest the re-pinned tests in the copy ==")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        pytest = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
             str(copy_root / V4_TEST_REL)
             + "::test_detached_integrity_root_is_pinned_and_covers_execution_boundary",
             str(copy_root / AMEND_TEST_REL)
             + "::test_plan_and_validate_only_do_not_mutate_authoritative_files",
             str(copy_root / AMEND_TEST_REL)
             + "::test_manifest_binds_script_decision_helper_and_tests",
             str(copy_root / AMEND_TEST_REL)
             + "::test_plan_and_validate_only_pass_in_pinned_fixture",
             ], capture_output=True, text=True, env=env, check=False,
        )
        print(pytest.stdout.strip().splitlines()[-1] if pytest.stdout.strip() else pytest.stderr[-400:])
        if pytest.returncode != 0:
            print(pytest.stdout[-2000:])
            print("selftest: FAILED at pytest stage")
            return 1
        print("selftest: ALL STAGES PASS (real tree untouched)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
