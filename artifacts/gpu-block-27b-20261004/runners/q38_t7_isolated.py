"""Prospective Q38 paired-arm coordinator; requires a separately reviewed runtime adapter.

No CLI or subprocess/network implementation is provided. The injected runtime owns server
identity verification, launch, captured cleanup, native receipts and STOP propagation.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol


class InvalidRun(RuntimeError):
    pass


class Runtime(Protocol):
    def start(self, arm: str, recipe: dict) -> Any: ...
    def verify(self, server: Any, arm: str, recipe: dict) -> None: ...
    def request(self, server: Any, body: dict, kind: str) -> dict: ...
    def stop(self, server: Any) -> bool: ...
    def stopping(self) -> bool: ...


@dataclass(frozen=True)
class Pair:
    key: str
    body: dict
    warm_body: dict | None = None
    min_cached_tokens: int | None = None


def _reject_override(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'speculative' or key.startswith('speculative.'):
                raise InvalidRun('request speculative overrides are forbidden')
            _reject_override(child)
    elif isinstance(value, list):
        for child in value:
            _reject_override(child)


def _body_bytes(body: dict) -> bytes:
    _reject_override(body)
    return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _same_warmed_prefix(warm: dict, measured: dict) -> bool:
    """Support the historical Q38 chat shape and the original plain prompt fixture."""
    if 'prompt' in warm and 'prompt' in measured:
        prefix, prompt = warm['prompt'], measured['prompt']
        return isinstance(prefix, str) and bool(prefix) and isinstance(prompt, str) and prompt.startswith(prefix)
    wm, mm = warm.get('messages'), measured.get('messages')
    if not isinstance(wm, list) or not isinstance(mm, list) or not wm or len(wm) != len(mm):
        return False
    if wm[:-1] != mm[:-1] or not isinstance(wm[-1], dict) or not isinstance(mm[-1], dict):
        return False
    left, right = dict(wm[-1]), dict(mm[-1])
    prefix, prompt = left.pop('content', None), right.pop('content', None)
    return (left == right and isinstance(prefix, str) and bool(prefix)
            and isinstance(prompt, str) and prompt.startswith(prefix))


def _validate_recipes(recipes: dict) -> None:
    if set(recipes) != {'drafted', 'nodraft'}:
        raise InvalidRun('exactly drafted and nodraft recipes required')
    d, n = recipes['drafted'], recipes['nodraft']
    # Explicit fields avoid trying to infer a server's mode from a free-form argv.
    required = {'binary', 'model', 'shape', 'draft_model', 'draft_options'}
    if set(d) != required or set(n) != required:
        raise InvalidRun('recipe schema mismatch')
    if not d['draft_model'] or not d['draft_options']:
        raise InvalidRun('drafted recipe must declare draft model and options')
    if n['draft_model'] is not None or n['draft_options']:
        raise InvalidRun('nodraft recipe must omit draft model and options')
    if any(not d[k] or d[k] != n[k] for k in ('binary', 'model', 'shape')):
        raise InvalidRun('server baseline recipe differs')


def run_pairs(runtime: Runtime, recipes: dict, pairs: list[Pair]) -> dict:
    """Sequential arms, presealed matching bodies, independently warmed per arm.

    Returns partial on failure and exposes all completed native responses. A real runtime
    must enforce identity, no-redraw and durable writes before this can be scheduled.
    """
    _validate_recipes(recipes)
    if not pairs or len({p.key for p in pairs}) != len(pairs) or any(not p.key for p in pairs):
        raise InvalidRun('nonempty unique pair keys required')
    sealed = []
    for pair in pairs:
        body = _body_bytes(pair.body)
        if pair.warm_body is None:
            if pair.min_cached_tokens is not None:
                raise InvalidRun('cache threshold requires warm request')
            warm = None
        else:
            warm = _body_bytes(pair.warm_body)
            if not _same_warmed_prefix(pair.warm_body, pair.body):
                raise InvalidRun('measured prompt must begin with the warm prefix')
            if type(pair.min_cached_tokens) is not int or pair.min_cached_tokens <= 0:
                raise InvalidRun('positive native cache threshold required')
        sealed.append((pair.key, body, warm, pair.min_cached_tokens))
    records, cleanup, failure = [], {}, None
    for arm in ('drafted', 'nodraft'):
        server = None
        try:
            if runtime.stopping():
                raise InvalidRun('STOP before launch')
            server = runtime.start(arm, copy.deepcopy(recipes[arm]))
            runtime.verify(server, arm, copy.deepcopy(recipes[arm]))
            for key, body, warm, threshold in sealed:
                if runtime.stopping():
                    raise InvalidRun('STOP before request')
                if warm is not None:
                    response = runtime.request(server, json.loads(warm), 'warm')
                    records.append({'arm': arm, 'key': key, 'kind': 'warm', 'response': response,
                                    'body_sha256': hashlib.sha256(warm).hexdigest()})
                    if not isinstance(response, dict) or response.get('http_status') != 200:
                        raise InvalidRun('warm request failed')
                if runtime.stopping():
                    raise InvalidRun('STOP before measured request')
                response = runtime.request(server, json.loads(body), 'measure')
                records.append({'arm': arm, 'key': key, 'kind': 'measure', 'response': response,
                                'body_sha256': hashlib.sha256(body).hexdigest()})
                if not isinstance(response, dict) or response.get('http_status') != 200:
                    raise InvalidRun('measured request failed')
                if threshold is not None:
                    timings = response.get('timings')
                    cache = timings.get('cache_n') if isinstance(timings, dict) else None
                    if type(cache) is not int or cache < threshold:
                        raise InvalidRun('cache witness missing or insufficient')
        except Exception as exc:
            failure = f'{type(exc).__name__}: {exc}'
        finally:
            if server is not None:
                try:
                    cleanup[arm] = runtime.stop(server) is True
                except Exception:
                    cleanup[arm] = False
                if not cleanup[arm]:
                    failure = failure or 'cleanup unverified'
        if failure:
            break
    return {'partial': failure is not None, 'error': failure, 'records': records, 'cleanup': cleanup}
