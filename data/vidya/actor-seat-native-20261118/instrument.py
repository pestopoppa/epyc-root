"""One bounded actor-seat variable call, against a row-owned local actor endpoint."""
from pathlib import Path
import os
import shutil
import sys
from urllib.parse import urlsplit

from autokernel.loop import actor_context, actor_metrics, actors

from opencode_v2 import metrics_export


class PrivateOpenCode(actors.Backend):
    def argv(self, *args, **kwargs):
        command = super().argv(*args, **kwargs)
        return [command[0], "--standalone", *(arg.removesuffix("#default") for arg in command[1:])]


def main():
    workspace = Path(sys.argv[1]).resolve(strict=True)
    port = int(sys.argv[2])
    # OpenCode v2 consults PWD independently of the kernel process cwd.
    os.chdir(workspace)
    os.environ["PWD"] = str(workspace)
    actor_metrics.parse_export = lambda path: metrics_export(path, actor_metrics.parse_export_data)
    backend = PrivateOpenCode("opencode", "vidya-seat/vidya-seat", "default", actors.OPENCODE)
    endpoint = actors._provider_base_url(backend.model)
    if urlsplit(endpoint or "").geturl() != f"http://127.0.0.1:{port}/v1":
        raise ValueError("private OpenCode provider does not name the owned loopback server")
    if os.environ.get("AK_VIDYA_CAMPAIGN_CAPTURE") != "1":
        raise ValueError("native prospective writer must be enabled")
    with actors._scratch_scope(workspace).scope("call", "actor-seat-instrument") as scope:
        bundle = actor_context.materialize(
            "## Selected target (original launch, model, requests and build)\nA read-only source-capture control. No repository operation.\n",
            workspace.parent / actor_context.BUNDLE_DIR, role="critic", scope=scope,
        )
        prompt = ("Reply with this JSON object and stop: "
                  '{"accepted":true,"reason":"instrument"}\n\n' + bundle.index)

        bundle.seal(prompt)
        (workspace.parent / "prompt.txt").write_text(prompt, encoding="utf-8")
        shutil.copytree(bundle.directory, workspace.parent / "offered-context",
                        ignore=shutil.ignore_patterns(".scratch-owner.json"))
        result = actors._run_agent(
            prompt, workspace=workspace, timeout_s=90, backend=backend, read_only=True,
            schema=actors.REVIEW_SCHEMA,
            env={actors.SEAT_ENV_ARM: "plain" + actor_context.ARM_SUFFIX,
                 actors.SEAT_ENV_BUNDLE_MANIFEST: str(bundle.directory / "manifest.json"),
                 "OPENCODE_DISABLE_MODELS_FETCH": "true", "OPENCODE_DISABLE_AUTOUPDATE": "true"},
        )
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
