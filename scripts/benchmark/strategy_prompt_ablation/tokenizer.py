"""Three-arm serving-tokenizer measurement for a keeper-supervised runner.

This helper does not start a server, establish ownership, or grant a window.
The caller must verify the actual binary/model, exclusive listener and grant;
callbacks below are assertions by that caller, not independent proofs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ARMS = ('baseline', 'strategy_short', 'strategy_long')


def capture_strategy_prompt_tokens(prompt_dir: Path, *, tokenize, check_window, witness, identity: dict) -> dict:
    """Count pinned whole prompts; record native token counts, never sum fragments.

    tokenize receives UTF-8 text and must call the witnessed server with
    add_special=False and parse_special=True; it returns the native token list.
    No output is written; the runner must retain the result and its provenance.
    """
    if not all(callable(f) for f in (tokenize, check_window, witness)):
        raise TypeError('tokenize, check_window and witness callbacks required')
    if not isinstance(identity, dict) or any(not identity.get(k) for k in ('binary_sha256', 'model_sha256', 'template_sha256')):
        raise ValueError('binary, model and template identity required')
    raw = (prompt_dir / 'manifest.json').read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != 'epyc.strategy_prompt_ablation.preparation.v1' or set(manifest.get('arms', {})) != set(ARMS):
        raise ValueError('invalid strategy prompt manifest')
    prompts = {}
    for arm in ARMS:
        spec = manifest['arms'][arm]
        if not isinstance(spec, dict) or spec.get('file') != arm + '.txt':
            raise ValueError('unexpected prompt filename')
        data = (prompt_dir / spec['file']).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if not data or digest != spec.get('sha256') or len(data) != spec.get('bytes'):
            raise ValueError('prompt digest mismatch')
        prompts[arm] = (data.decode('utf-8'), digest)
    if len({digest for _, digest in prompts.values()}) != len(ARMS):
        raise ValueError('duplicate prompt arms')
    if check_window() is not True:
        raise RuntimeError('keeper window not active')
    before = witness()
    if not isinstance(before, dict) or any(not before.get(k) for k in ('pid', 'birth', 'port', 'listener_inodes')):
        raise RuntimeError('incomplete listener witness')
    counts = {}
    for arm, (prompt, digest) in prompts.items():
        if check_window() is not True:
            raise RuntimeError('keeper window ended')
        tokens = tokenize(prompt, add_special=False, parse_special=True)
        if not isinstance(tokens, list) or not tokens or any(type(t) is not int or t < 0 for t in tokens):
            raise ValueError('invalid native token array')
        counts[arm] = {'sha256': digest, 'tokens': len(tokens)}
    after = witness()
    if before != after or check_window() is not True:
        raise RuntimeError('listener or keeper window changed')
    return {'schema': 'epyc.strategy_prompt_ablation.tokenizer.v1',
            'manifest_sha256': hashlib.sha256(raw).hexdigest(), 'counts': counts,
            'tokenizer_flags': {'add_special': False, 'parse_special': True},
            'scope': 'whole prompt byte strings; chat-template overhead excluded',
            'identity_asserted': dict(identity), 'listener_asserted': before,
            'limitations': 'Caller must verify listener, source identity, grant and tokenize callback.'}
