"""Measurement-only Step runner; no model execution occurs on import.

Pinned upstream code runs in private module namespaces with explicit placement.
The caller serializes this runner, prepares inputs before grants, and supplies
a live co-tenant sampler. Non-streaming completion time is never called TTFA.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import types

try:
    from .cs5_step_adapter import run_reference
except ImportError:
    from cs5_step_adapter import run_reference

UPSTREAM = '76e272b56c3917a8d7188f18bbb5a65dfc8a0845'
MODEL_CODE_SHA256 = '82b93db45a4bf37c2877660b321782aea4715e3e0d7be221e91e99e13815cbe3'
PINS = {
    'stepaudio2.py': '9bd85c95a38b2273388ed4cc024d4a5aca9f585b8c51f04c25515078313a81b4',
    'token2wav.py': '37a13e82d7a0cc656d465197f3c7ac61b8029ae85c91e7ca606cb4c6010974c7',
}


class Placement(ast.NodeTransformer):
    """Replace only cuda placement calls, device kwargs and autocast type."""
    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'cuda':
            if node.args or node.keywords:
                raise ValueError('unexpected upstream cuda arguments')
            node.func.attr = 'to'
            node.args = [ast.Name(id='_cs5_device', ctx=ast.Load())]
        for kw in node.keywords:
            if kw.arg == 'device' and isinstance(kw.value, ast.Constant) and kw.value.value == 'cuda':
                kw.value = ast.Name(id='_cs5_device', ctx=ast.Load())
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'autocast':
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'cuda':
                node.args[0] = ast.Attribute(value=ast.Name(id='_cs5_device', ctx=ast.Load()),
                                             attr='type', ctx=ast.Load())
        return node


def placed_code(source, filename, expected_sha256):
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise ValueError(f'upstream source digest mismatch: {filename}')
    tree = Placement().visit(ast.parse(source, filename=filename))
    return compile(ast.fix_missing_locations(tree), filename, 'exec')


def load_models(source_dir, model_dir, device):
    """Load the pinned upstream checkout without editing it or torch globals.

    Use a dedicated row process: upstream absolute imports are process-local.
    CUDA is also PyTorch's ROCm device vocabulary; this asserts no gfx90a proof.
    """
    root = Path(source_dir).resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != UPSTREAM or git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Step checkout must be clean at the pinned upstream commit')
    # Check both sources before importing torch or constructing either model.
    codes = {name: placed_code((root / name).read_bytes(), str(root / name), digest)
             for name, digest in PINS.items()}
    model_code = Path(model_dir) / 'modeling_step_audio_2.py'
    if hashlib.sha256(model_code.read_bytes()).hexdigest() != MODEL_CODE_SHA256:
        raise ValueError('model compatibility source digest mismatch')
    import torch
    placement = torch.device(device)
    sys.path.insert(0, str(root))
    try:
        modules = {}
        for name, code in codes.items():
            module = types.ModuleType('_cs5_' + Path(name).stem)
            module.__file__ = str(root / name)
            module._cs5_device = placement
            exec(code, module.__dict__)
            modules[name] = module
        model = modules['stepaudio2.py'].StepAudio2(str(model_dir))
        vocoder = modules['token2wav.py'].Token2wav(str(Path(model_dir) / 'token2wav'))
    finally:
        sys.path.pop(0)
    def synchronize():
        if placement.type == 'cuda':
            torch.cuda.synchronize(placement)
    return model, vocoder, synchronize


def run_turn(model, vocoder, messages, *, prompt_wav, expects_audio,
             synchronize, sample_co_tenant, harness, generation=None,
             clock=time.perf_counter):
    """One native text/audio turn, retaining errors and timing boundaries.

    Sampler must inspect the actual co-tenant during this row. No default idle
    assertion is supplied. Includes prompt processing, generation and vocoding;
    excludes model loading and final artifact writes. Synchronize both edges.
    """
    synchronize()
    start = clock()
    tenant = sample_co_tenant()
    result = run_reference(model, messages, expects_audio=expects_audio,
                           **(generation or {}))
    audio_tokens = result.pop('audio')
    wav = None
    if result['error'] is None:
        if not audio_tokens:
            result['error'] = 'no_generated_audio_tokens'
        else:
            wav = vocoder(audio_tokens, prompt_wav=prompt_wav)
            if not isinstance(wav, bytes) or not wav:
                raise ValueError('Token2Wav must return nonempty WAV bytes')
    synchronize()
    end = clock()
    runtime = dict(kind='reference', upstream_digest=UPSTREAM + ':' +
                   hashlib.sha256(Path(__file__).read_bytes()).hexdigest() + ':' +
                   hashlib.sha256(Path(__file__).with_name('cs5_step_adapter.py').read_bytes()).hexdigest())
    return dict(schema='epyc.cs5.step_reference.v1', **result,
                audio_tokens=audio_tokens, wav=wav,
                completion_ms=(end - start) * 1000,
                timing_scope='synchronized native generation plus Token2Wav; not TTFA',
                harness={**harness, 'co_tenant': tenant, 'runtime': runtime},
                upstream_commit=UPSTREAM, upstream_files=PINS,
                model_code_sha256=MODEL_CODE_SHA256,
                messages=messages, prompt_wav=str(prompt_wav),
                generation={**(generation or {}), 'use_cache': False})


def write_turn(out_dir, result, *, run_id, subject):
    """Write native output first, then the existing CS-3 writer attests it.

    Failed turns remain native diagnostics and never emit a success latency.
    Fresh output directories prevent accidental replacement of an attestation.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vidya'))
    try:
        from adapters.conversation_stack_measurement import write_belief_measurements
    finally:
        sys.path.pop(0)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    native = dict(result)
    wav = native.pop('wav')
    if wav is not None:
        (out / 'response.wav').write_bytes(wav)
        native['wav_sha256'] = hashlib.sha256(wav).hexdigest()
    path = out / 'native.json'
    path.write_text(json.dumps(native, ensure_ascii=False, indent=2) + '\n')
    if result['error'] is not None:
        return path, None
    sidecar = write_belief_measurements(out, run_id=run_id,
        producer='scripts/speech/cs5_step_reference.py', results_path=path,
        records=[dict(record_kind='generic', subject=subject,
            metric='turn_latency_ms', value=result['completion_ms'], unit='ms',
            metric_direction='lower_better', protocol_id=None, reps=1,
            reps_basis='scored:completed_nonstreaming_turns', harness=result['harness'],
            fields=dict(timing_scope=result['timing_scope'],
                        encoder_calls=result['encoder_calls'],
                        upstream_commit=UPSTREAM, upstream_files=PINS))])
    return path, sidecar
