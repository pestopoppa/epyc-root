"""Opt-in real Docker/tool/gates contract for NI05 off-host validation."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("EPYC_RUN_DEVCONTAINER_GATES") != "1",
    reason="set EPYC_RUN_DEVCONTAINER_GATES=1 in the isolated off-host job",
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
