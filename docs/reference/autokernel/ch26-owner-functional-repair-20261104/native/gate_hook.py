"""Install a request-scoped CH-26 observer in the DS41 gate's measurement owner.

Requires serving-ch26-prototype.patch on the exact reviewed serving source.
Creates one diagnostic capture per warmup/measurement request and requires every
capture to finish before the launch can return. This does not admit a floor.
"""
from owner_hook import RequestCapture


def install_in_gate(gate, factory):
    if not callable(factory): raise ValueError('capture factory required')
    original = gate.install_measure_wrapper
    if not callable(original) or getattr(original, '_ch26_injected', False):
        raise ValueError('gate wrapper missing or already instrumented')
    def install(serving, *args, **kwargs):
        returned = original(serving, *args, **kwargs)
        current = serving._measure_once
        # The existing gate wrapper accepts **kwargs; enforce the reviewed patched
        # owner via an explicit marker at installation rather than relying on Python
        # wrapper signatures that may erase the underlying signature.
        if getattr(serving, '_ch26_owner_patch', None) != 'prototype-v2':
            raise ValueError('unbound CH-26 serving prototype')
        if getattr(current, '_ch26_injected', False): raise ValueError('duplicate CH-26 wrapper')
        def measured(*a, **kw):
            if 'ch26_capture_factory' in kw: raise ValueError('caller cannot replace owned capture factory')
            captures = []
            def create(target_pid, request_context):
                cap = factory(target_pid, request_context)
                if not isinstance(cap, RequestCapture): raise ValueError('owned request capture required')
                captures.append(cap)
                return cap
            try:
                result = current(*a, **dict(kw, ch26_capture_factory=create))
                recipe = a[0] if a else None
                expected = 2 * getattr(recipe, 'np', -1)
                if expected <= 0 or len(captures) != expected:
                    raise ValueError('CH-26 per-request capture count differs')
                if any(cap.state != 'finished' or cap.receipt is None for cap in captures):
                    raise ValueError('CH-26 request observer receipt incomplete')
                return result
            finally:
                for cap in captures:
                    if cap.state != 'finished': cap.abort()
        measured._ch26_injected = True
        serving._measure_once = measured
        return returned
    install._ch26_injected = True
    gate.install_measure_wrapper = install
