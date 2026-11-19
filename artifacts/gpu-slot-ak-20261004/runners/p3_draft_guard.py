"""Validate no-draft server identity before a benchmark sends any request."""
from __future__ import annotations
DRAFT_VALUE_FLAGS = frozenset({'-md', '--model-draft', '--model-draft-voc', '-mdv', '--spec-type', '--draft-max', '--draft-min', '--draft-p-split', '--draft-p-min', '--draft-p0', '-ngld', '--gpu-layers-draft', '-cd', '--ctx-size-draft', '-td', '--threads-draft', '-tbd', '--threads-batch-draft', '--spec-draft-n-max', '--spec-draft-n-min', '--device-draft', '-devd'})
DRAFT_MODEL_FLAGS = frozenset({'-md', '--model-draft', '-mdv', '--model-draft-voc'})

def has_drafter(argv: list[str]) -> bool:
    return any(arg.split('=', 1)[0] in DRAFT_VALUE_FLAGS for arg in argv)

def dedicated_no_draft_argv(argv: list[str]) -> list[str]:
    """Remove drafter configuration and reject missing option values."""
    out = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        flag = arg.split('=', 1)[0]
        if flag in DRAFT_VALUE_FLAGS:
            if '=' not in arg:
                i += 1
                if i >= len(argv) or argv[i].startswith('-'):
                    raise ValueError(f'missing value for {flag}')
        else:
            out.append(arg)
        i += 1
    if has_drafter(out):
        raise ValueError('no-draft argv retains a drafter')
    return out

def validate_request(argv: list[str], body: dict) -> None:
    """Fail before HTTP I/O for zero-draft traffic on a drafted launch."""
    zero = body.get('speculative.n_max') == 0
    nested = body.get('speculative')
    zero = zero or (isinstance(nested, dict) and nested.get('n_max') == 0)
    if zero and has_drafter(argv):
        raise ValueError('n_max=0 requires a dedicated server launched without a drafter')
