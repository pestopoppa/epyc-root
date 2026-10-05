"""Opt-in real Docker/tool/gates contract for NI05 off-host validation."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("EPYC_RUN_DEVCONTAINER_GATES") != "1",
    reason="set EPYC_RUN_DEVCONTAINER_GATES=1 in the isolated off-host job",
)

SHELL_FORMAT_FILES = (
    "scripts/lib/env.sh",
    "scripts/diffusion/start_sd_server.sh",
    "scripts/benchmark/package_a_instrumented_eval.sh",
    "scripts/benchmark/operator_candidates/collect_e8_quality_baseline_v5.sh",
    "scripts/benchmark/operator_candidates/ratify_and_apply_e8_quality_baseline_v5.sh",
    "scripts/benchmark/operator_candidates/prepare_e8_quality_baseline_v5_candidate.sh",
    "scripts/setup/install_editable_pth.sh",
    "scripts/voice/build_nprocs_shim.sh",
    "scripts/autopilot/operator_candidates/ratify_and_apply_resource_lanes_v2.sh",
)


@pytest.fixture(scope="session")
def devcontainer_image(tmp_path_factory: pytest.TempPathFactory) -> str:
    image_root = Path(os.environ["NI05_IMAGE_ROOT"]).resolve()
    dockerfile = image_root / ".devcontainer" / "Dockerfile"
    image = "ni05-devcontainer:validation"
    empty_context = tmp_path_factory.mktemp("ni05-empty-build-context")

    subprocess.run(
        [
            "docker",
            "buildx",
            "build",
            "--build-arg",
            "TZ=UTC",
            "--progress=plain",
            "--load",
            "--file",
            str(dockerfile),
            "--tag",
            image,
            str(empty_context),
        ],
        check=True,
        timeout=20 * 60,
    )
    return image


def test_devcontainer_installs_pinned_linter_versions(devcontainer_image: str) -> None:
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "bash",
            devcontainer_image,
            "-euo",
            "pipefail",
            "-c",
            " && ".join(
                [
                    "test \"$(dpkg-query -W -f='${Version}' shellcheck)\" = '0.10.0-1'",
                    "test \"$(dpkg-query -W -f='${Version}' shfmt)\" = '3.8.0-1'",
                    "test \"$(markdownlint --version)\" = '0.49.1'",
                ]
            ),
        ],
        check=True,
        timeout=5 * 60,
    )


def test_offhost_shfmt_patch_preserves_shell_ast(devcontainer_image: str, tmp_path: Path) -> None:
    """Format copies only, and retain a diff plus normalized AST evidence."""
    orchestrator = Path(os.environ["NI05_ORCHESTRATOR"]).resolve()
    artifacts = Path(os.environ["NI05_ARTIFACTS"]).resolve() / "shfmt-remediation"
    artifacts.mkdir(parents=True, exist_ok=True)
    copied = tmp_path / "orchestrator-copy"
    copied.mkdir()
    for relative in SHELL_FORMAT_FILES:
        target = copied / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(orchestrator / relative, target)

    files = [f"/work/{relative}" for relative in SHELL_FORMAT_FILES]
    script = "\n".join(
        [
            "set -euo pipefail",
            "shfmt --version",
            *[
                f"bash -n {path} && shfmt --to-json --filename {path} < {path} > {path}.before.json"
                for path in files
            ],
            "shfmt -w -i 2 -ci " + " ".join(files),
            *[
                f"bash -n {path} && shfmt --to-json --filename {path} < {path} > {path}.after.json"
                for path in files
            ],
        ]
    )
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--volume",
            f"{copied}:/work:rw",
            "--workdir",
            "/work",
            "--entrypoint",
            "bash",
            devcontainer_image,
            "-euo",
            "pipefail",
            "-c",
            script,
        ],
        check=True,
        timeout=10 * 60,
    )

    def normalized_ast(path: Path) -> object:
        ast = json.loads(path.read_text())

        def without_positions(node: object) -> object:
            # mvdan/sh v3.8.0 syntax/typedjson encodes syntax.Pos as exactly
            # {"Offset": uint, "Line": uint, "Col": uint}; this also covers
            # the derived Pos/End fields and named position fields on AST nodes.
            if (
                isinstance(node, dict)
                and set(node) == {"Offset", "Line", "Col"}
                and all(
                    isinstance(value, int) and not isinstance(value, bool)
                    for value in node.values()
                )
            ):
                return {"__syntax_position__": True}
            if isinstance(node, dict):
                return {
                    key: without_positions(value)
                    for key, value in node.items()
                }
            if isinstance(node, list):
                return [without_positions(value) for value in node]
            return node

        return without_positions(ast)

    diff_lines: list[str] = []
    records = []
    for relative in SHELL_FORMAT_FILES:
        original = orchestrator / relative
        formatted = copied / relative
        before_ast = normalized_ast(Path(f"{formatted}.before.json"))
        after_ast = normalized_ast(Path(f"{formatted}.after.json"))
        assert before_ast == after_ast, f"shell AST changed for {relative}"
        normalized_ast_bytes = json.dumps(
            before_ast, sort_keys=True, separators=(",", ":")
        ).encode()
        before_text = original.read_text().splitlines(keepends=True)
        after_text = formatted.read_text().splitlines(keepends=True)
        diff_lines.extend(
            difflib.unified_diff(
                before_text,
                after_text,
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
        records.append(
            {
                "path": relative,
                "before_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
                "after_sha256": hashlib.sha256(formatted.read_bytes()).hexdigest(),
                "before_lines": len(before_text),
                "after_lines": len(after_text),
                "line_delta": len(after_text) - len(before_text),
                "normalized_ast_equal": True,
                "normalized_ast_sha256": hashlib.sha256(
                    normalized_ast_bytes
                ).hexdigest(),
                "bash_n_before_after": True,
            }
        )

    patch = "".join(diff_lines)
    patch_path = artifacts / "format.patch"
    patch_path.write_text(patch)
    summary = {
        "formatter": "shfmt 3.8.0 (Debian package 3.8.0-1)",
        "arguments": ["-w", "-i", "2", "-ci"],
        "ast_position_encoding": {"Offset": "uint", "Line": "uint", "Col": "uint"},
        "ast_position_source": "mvdan/sh v3.8.0 syntax/typedjson/json.go",
        "source_checkout_modified": False,
        "files": records,
        "patch_bytes": len(patch.encode()),
        "added_lines": sum(
            line.startswith("+") and not line.startswith("+++")
            for line in patch.splitlines()
        ),
        "removed_lines": sum(
            line.startswith("-") and not line.startswith("---")
            for line in patch.splitlines()
        ),
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }
    (artifacts / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def test_independent_markdownlint_gate(devcontainer_image: str) -> None:
    """Run markdownlint independently even when the ordered gate chain stops early."""
    orchestrator = Path(os.environ["NI05_ORCHESTRATOR"]).resolve()
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{orchestrator}:/workspace:ro",
            "--workdir",
            "/workspace",
            "--entrypoint",
            "bash",
            devcontainer_image,
            "-euo",
            "pipefail",
            "-c",
            "make mdlint",
        ],
        check=True,
        timeout=10 * 60,
    )


def test_actual_static_make_gates(devcontainer_image: str) -> None:
    orchestrator = Path(os.environ["NI05_ORCHESTRATOR"]).resolve()
    research = Path(os.environ["NI05_RESEARCH"]).resolve()
    expected_overrides = {
        "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN": "/fixture/llama-server",
        "ORCHESTRATOR_PATHS_LLAMA_MTMD": "/fixture/llama-mtmd-cli",
        "ORCHESTRATOR_PATHS_LLAMA_SERVER": "/fixture/llama-server",
    }
    for name, expected in expected_overrides.items():
        assert os.environ.get(name) == expected, f"unexpected explicit fixture override {name}"

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--volume",
            f"{orchestrator}:/workspace:ro",
            "--volume",
            f"{research}:/mnt/raid0/llm/epyc-inference-research:ro",
            "--workdir",
            "/workspace",
            "--env",
            "CI=",
            "--env",
            "ORCHESTRATOR_PATHS_LLAMA_CPP_BIN",
            "--env",
            "ORCHESTRATOR_PATHS_LLAMA_MTMD",
            "--env",
            "ORCHESTRATOR_PATHS_LLAMA_SERVER",
            "--entrypoint",
            "bash",
            devcontainer_image,
            "-euo",
            "pipefail",
            "-c",
            "make gates CI=",
        ],
        check=True,
        timeout=20 * 60,
    )
