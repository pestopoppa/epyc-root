#!/usr/bin/env python3
"""Launch the pinned research harness with a fresh contained image per trial.

Harness --container/--container-map values must be immutable image IDs. This
adapter is experimental; it does not establish SWE scoring or full isolation.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

from container_backend import IsolatedContainer, run_with_cleanup

parser = argparse.ArgumentParser()
parser.add_argument('--runner', required=True)
parser.add_argument('--runner-sha256', required=True)
parser.add_argument('--sandbox-source-dir', required=True)
parser.add_argument('--sandbox-sha256-json', required=True)
opts, remaining = parser.parse_known_args()
runner = Path(opts.runner)
if hashlib.sha256(runner.read_bytes()).hexdigest() != opts.runner_sha256:
    raise SystemExit('runner source hash mismatch')
hashes = json.loads(Path(opts.sandbox_sha256_json).read_text())
spec = importlib.util.spec_from_file_location('p5_pinned_harness', runner)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
original = types.SimpleNamespace(DockerEnv=module.DockerEnv, TIMEOUT_EXIT=module.TIMEOUT_EXIT,
                                 _timeout_msg=module._timeout_msg)
with contextlib.ExitStack() as stack:
    def make_env(image_id, docker_bin='docker'):
        manager = IsolatedContainer(original, image_id, opts.sandbox_source_dir, hashes, docker_bin)
        env = stack.enter_context(manager)
        env._p5_container = manager
        return env
    original_run_instance = module.run_instance
    def run_instance(client, env, *args, **kwargs):
        return run_with_cleanup(original_run_instance, client, env, *args, **kwargs)
    module.DockerEnv = make_env
    module.run_instance = run_instance
    sys.argv = [str(runner), *remaining]
    raise SystemExit(module.main())
