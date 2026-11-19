"""Prepare actual inputs once; install referenced successors, never launch compute."""
import hashlib
import json
from pathlib import Path
import shlex
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install
import execution_binding
import publisher_provider

ROW = 'kvu-kpf18-native-lifecycle-r1-20261119'
BIN = Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin')
R15 = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15')
R7 = Path('/mnt/raid0/llm/tmp/codex-ni-kpf18-native-segfault-r7-20261030')
ENGINE = Path(publisher_provider.ENGINE)


def sha(path):
    if path.suffix.lower() == '.gguf':
        raise ValueError('model weights forbidden')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root):
    if root != install.SCRATCH / ROW or root.exists():
        raise ValueError('new fixed lifecycle scratch root required')
    artifacts = {'python': Path('/proc/self/exe').resolve(), 'shell': Path('/bin/bash').resolve(),
                 'flock': Path('/usr/bin/flock').resolve(), 'server': BIN / 'llama-server'}
    for role, name in {'ggml': 'libggml.so', 'ggml_base': 'libggml-base.so',
                       'ggml_cpu': 'libggml-cpu.so', 'ggml_hip': 'libggml-hip.so',
                       'server_impl': 'libllama-server-impl.so', 'llama': 'libllama.so',
                       'llama_common': 'libllama-common.so', 'mtmd': 'libmtmd.so'}.items():
        artifacts[role] = (BIN / name).resolve()
    framing = {'framing_result': R7 / 'cpu-replay/attempts/1793382000-1793385600/RESULT.json',
               'complete_marker': R7 / 'cpu-replay/COMPLETE',
               'source_manifest': R7 / 'cpu-replay/SOURCES.sha256',
               'root_source_manifest': R7 / 'SOURCES.sha256'}
    for key, path in framing.items():
        if sha(path) != execution_binding.R7_PINS[key]:
            raise ValueError('retained R7 identity mismatch')
    canonical = R15 / 'canonical-export-root'
    for name, pin in execution_binding.PROJECTION.items():
        if sha(canonical / name) != pin:
            raise ValueError('canonical projection mismatch')
    prepared = {'argv': '/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt',
                'prompts': '/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl'}
    provider_sources = {str(publisher_provider.ORCHESTRATOR / name):
                        sha(publisher_provider.ORCHESTRATOR / name) for name in publisher_provider.SOURCES}
    common = [*artifacts.values(), *framing.values(), *(canonical / name for name in execution_binding.PROJECTION),
              *(Path(name) for name in prepared.values()), R15 / 'out/PRELOAD-MODEL-IDENTITY.json',
              install.RETAINED / 'ORIGINAL-MODELS.json',
              HERE / 'lifecycle.py', HERE / 'prepare_lifecycle.py', publisher_provider.LEGACY]
    sources = {str(path): sha(path) for path in common}
    sources.update(provider_sources)
    # Reuse the accepted receipt and live stat tuples; never read model bytes.
    sys.path.insert(0, str(install.RETAINED))
    from preload_integration import load_preload_models
    load_preload_models(R15 / 'out/PRELOAD-MODEL-IDENTITY.json', install.RETAINED / 'ORIGINAL-MODELS.json')
    root.mkdir(); (root / 'out').mkdir()
    for mode, provider in [('official', publisher_provider.LEGACY),
                           ('publisher-smoke', HERE / 'publisher_provider.py')]:
        inventory = dict(sources, **{str(provider): sha(provider)})
        execution = {'mode': mode, 'row_id': ROW, 'window_s': 9000,
                     'stop_file': str(root / 'STOP') if mode == 'official' else
                                  str(Path('/mnt/raid0/llm/tmp/compute-flags/dryrun') / ROW / 'stop'),
                     'output_root': str(root / 'out'),
                     'artifacts': {key: str(path) for key, path in artifacts.items()},
                     'provider': str(provider), 'provider_sources': provider_sources,
                     'prepared': prepared, 'preload_receipt': str(R15 / 'out/PRELOAD-MODEL-IDENTITY.json'),
                     'enrollment': {'framing_mode': 'retained-r7-v1',
                                    'canonical_export': str(canonical),
                                    **{key: str(path) for key, path in framing.items()}},
                     'sources': inventory}
        install.install(root / mode, execution=execution, binding_revision=install.REVISION,
                        guard_revision='current-guard-v3')
    command = lambda action: shlex.join([str(artifacts['python']), '-I', '-B', str(HERE / 'lifecycle.py'), action, str(root)])
    args = ['bash', str(ENGINE), '--id', ROW, '--class', 'gpu', '--role', 'bench',
            '--gpu-quiet', 'exclusive', '--claim-cpus', '184-191', '--min-window', '8700',
            '--stop', str(root / 'STOP'), '--workdir', str(root),
            '--precond-cmd', command('check'), '--complete-cmd', command('complete'), '--cmd', command('run')]
    (root / 'launch.sh').write_text('#!/bin/bash\nset -euo pipefail\nexec ' + shlex.join(args) + '\n')
    spec = {'id': ROW, 'owner': 'kvu', 'launcher': str(root / 'launch.sh'), 'lane': 'gpu',
            'regions': 'mi210_0,184-191', 'result_path': str(root / 'out/RESULT.json'),
            'result_format': 'json', 'dryrun_native_result': True, 'kind': 'compute',
            'decision_rule': 'Agent: require rc0, owned_cleanup_returned, native conformance verdict; preserve INVALID or refusal; no parent closure.',
            'verdict_by': 'agent', 'estimate_s': 7250, 'priority_rank': 1,
            'handoff_task': 'handoffs/active/kv-cache-program.md:KPF-18.0d',
            'scratch_root': str(root), 'first_progress_s': 300,
            'lineage': 'kvu-kpf18-current-native-lifecycle',
            'notes': 'Actual retained R7 enrollment; original a1f0c8cf9/build10348. Smoke = native request plus own VRAM, mappings and cleanup. Full = existing group3 recipe; stop on verdict, refusal, STOP, deadline or exhaustion. No model hashing.'}
    (root / 'spec.json').write_text(json.dumps(spec, indent=2) + '\n')
    return root / 'spec.json'


if __name__ == '__main__':
    print(prepare(Path(sys.argv[1])))
