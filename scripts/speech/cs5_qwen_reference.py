"""Measurement-only Qwen3-Omni audio/text runner; imports no model on import."""
import hashlib
import importlib.metadata
import io
from pathlib import Path
import subprocess
import time

try:
    from .cs5_step_reference import write_turn as _write_turn
except ImportError:
    from cs5_step_reference import write_turn as _write_turn

UPSTREAM = 'e4235853125589c789f06a2dd83e9f4126df5e9d'
PINS = {'README.md': '013dbbd14768e7767a05d6a5da8dffecd0b8f36938eedaa6a5000c26484f4603'}


def verify_sources(source_dir, environment):
    """Require prospective package/source pins; never hash model weights here."""
    root = Path(source_dir).resolve()
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
    if git('rev-parse', 'HEAD') != UPSTREAM or git('status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Qwen checkout must be clean at the pinned upstream commit')
    for name, digest in PINS.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Qwen upstream source digest mismatch')
    for name in ('torch', 'transformers', 'qwen-omni-utils'):
        if importlib.metadata.version(name) != environment['versions'][name]:
            raise ValueError(f'environment version mismatch: {name}')
    # Source files are relative to installed distributions, preventing arbitrary
    # caller paths from masquerading as the implementation being loaded.
    for package, relative in (
        ('transformers', 'transformers/models/qwen3_omni_moe/modeling_qwen3_omni_moe.py'),
        ('transformers', 'transformers/models/qwen3_omni_moe/processing_qwen3_omni_moe.py'),
        ('qwen-omni-utils', 'qwen_omni_utils/__init__.py'),
    ):
        path = Path(importlib.metadata.distribution(package).locate_file(relative))
        if hashlib.sha256(path.read_bytes()).hexdigest() != environment['sources'][relative]:
            raise ValueError(f'environment source mismatch: {relative}')


def load_models(source_dir, model_dir, device, *, environment):
    verify_sources(source_dir, environment)
    import torch
    from transformers import Qwen3OmniMoeForConditionalGeneration, Qwen3OmniMoeProcessor
    from qwen_omni_utils import process_mm_info
    model = Qwen3OmniMoeForConditionalGeneration.from_pretrained(
        str(model_dir), dtype='auto', device_map=str(device),
        attn_implementation='sdpa', local_files_only=True)
    model.eval()
    processor = Qwen3OmniMoeProcessor.from_pretrained(str(model_dir), local_files_only=True)
    def synchronize():
        if torch.device(device).type == 'cuda':
            torch.cuda.synchronize(device)
    return model, processor, process_mm_info, synchronize


def _check_messages(messages, expects_audio):
    count = 0
    for message in messages:
        content = message['content']
        if isinstance(content, str):
            continue
        for item in content:
            if item['type'] == 'audio':
                if not Path(item['audio']).is_file():
                    raise ValueError('audio must be a prepared local file')
                count += 1
            elif item['type'] != 'text':
                raise ValueError('this reference runner accepts text and local audio only')
    if expects_audio and not count:
        raise ValueError('expected an audio input')


def _wav_bytes(audio):
    import soundfile
    samples = audio.reshape(-1).detach().cpu().numpy()
    if not samples.size:
        raise ValueError('empty generated audio')
    import numpy as np
    if not np.isfinite(samples).all():
        raise ValueError('nonfinite generated audio')
    out = io.BytesIO()
    soundfile.write(out, samples, 24000, format='WAV', subtype='FLOAT')
    return out.getvalue()


def run_turn(model, processor, messages, *, process_mm_info, expects_audio,
             synchronize, sample_co_tenant, harness, environment, generation=None,
             clock=time.perf_counter):
    """Native prompt/processing/generation timing, with observed audio features.

    Generation must return both thinker tokens and talker audio. Timed scope ends
    after synchronized generation; WAV serialization is excluded. Not TTFA.
    """
    _check_messages(messages, expects_audio)
    settings = dict(generation or {})
    reserved = {'return_audio', 'thinker_return_dict_in_generate', 'use_audio_in_video'}
    if reserved.intersection(settings):
        raise ValueError('generation cannot override audio/output contract')
    synchronize()
    start = clock()
    tenant = sample_co_tenant()
    text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    audios, images, videos = process_mm_info(messages, use_audio_in_video=False)
    inputs = processor(text=text, audio=audios, images=images, videos=videos,
                       return_tensors='pt', padding=True, use_audio_in_video=False)
    features = inputs.get('input_features')
    observed = features is not None and features.numel() > 0
    if expects_audio and not observed:
        raise ValueError('audio preprocessing produced no features')
    inputs = inputs.to(model.device).to(model.dtype)
    tokens, audio = model.generate(**inputs, **settings, return_audio=True,
        thinker_return_dict_in_generate=True, use_audio_in_video=False)
    synchronize()
    end = clock()
    response = tokens.sequences[:, inputs['input_ids'].shape[1]:]
    raw = processor.batch_decode(response, skip_special_tokens=False,
                                 clean_up_tokenization_spaces=False)[0]
    cleaned = processor.batch_decode(response, skip_special_tokens=True,
                                     clean_up_tokenization_spaces=False)[0]
    wav = None if audio is None else _wav_bytes(audio)
    runtime = dict(kind='reference', upstream_digest=UPSTREAM + ':' +
                   hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    return dict(schema='epyc.cs5.qwen_reference.v1', error=None if wav else 'no_generated_audio',
        tokens=response.tolist(), raw_text=raw, text=cleaned, wav=wav,
        input_audio_features_present=observed, generation=settings,
        environment=environment, messages=messages, upstream_commit=UPSTREAM,
        upstream_files=PINS, producer='scripts/speech/cs5_qwen_reference.py',
        completion_ms=(end-start)*1000,
        timing_scope='synchronized native prompt, processing and generation; excludes WAV serialization; not TTFA',
        harness={**harness, 'runtime': runtime, 'co_tenant': tenant})


def write_turn(out_dir, result, *, run_id, subject):
    return _write_turn(out_dir, result, run_id=run_id, subject=subject)
