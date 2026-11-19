"""Model-free Step-Audio2 compatibility seam for the CS-5 reference harness.

Call a pinned upstream StepAudio2 instance, which owns its native prompt format.
No model loading, placement, timing, CS-3 certification or serving changes here.
"""
from contextlib import contextmanager
import re


def prepare_audio_inputs(input_ids, attention_mask=None, wavs=None, wav_lens=None,
                         **kwargs):
    """Keep full IDs and audio at EVERY step, including an empty DynamicCache."""
    return dict(input_ids=input_ids, attention_mask=attention_mask,
                wavs=wavs, wav_lens=wav_lens)


def clean_language_prefix(text):
    """Strip one initial Chinese language tag; preserve the raw output separately."""
    if not isinstance(text, str):
        raise TypeError('native text must be a string')
    return re.sub(r'\A<[一-鿿]+>', '', text, count=1)


@contextmanager
def audio_preparation(llm):
    """Install per-instance audio handling and a scoped encoder witness.

    Restores the instance dictionary exactly, even on generation errors. The
    caller must serialize requests to this instance; unrelated instances and
    the upstream class are untouched.
    """
    name = 'prepare_inputs_for_generation'
    owned = name in vars(llm)
    original = vars(llm).get(name)
    calls = {'encoder_calls': 0}

    def count(_module, _inputs):
        calls['encoder_calls'] += 1

    handle = llm.encoder.register_forward_pre_hook(count)
    try:
        setattr(llm, name, prepare_audio_inputs)
        yield calls
    finally:
        try:
            if owned:
                setattr(llm, name, original)
            else:
                delattr(llm, name)
        finally:
            handle.remove()


def run_reference(model, messages, *, expects_audio, **generation):
    """Return native/raw evidence, refusing silent audio bypass.

    Use upstream StepAudio2.__call__ so its StepFun prompt format is retained.
    Cache is disabled in the generation config as well as in prepared inputs.
    A zero encoder count is returned as an explicit engineering failure, never
    a coherent audio result. Raw native tokens/text are kept without scoring.
    """
    if type(expects_audio) is not bool:
        raise TypeError('expects_audio must be boolean')
    if generation.get('use_cache', False) is not False:
        raise ValueError('Step reference requires use_cache=False')
    generation['use_cache'] = False
    with audio_preparation(model.llm) as witness:
        tokens, raw_text, audio = model(messages, **generation)
    text = clean_language_prefix(raw_text)
    audio_ran = witness['encoder_calls'] > 0
    return dict(tokens=tokens, raw_text=raw_text, text=text, audio=audio,
                encoder_calls=witness['encoder_calls'], expects_audio=expects_audio,
                audio_path_ok=not expects_audio or audio_ran,
                error='audio_path_never_ran' if expects_audio and not audio_ran else None)
