"""Parse only explicit resolved Flash Attention messages, never the requested auto value."""
import re

PATTERN = re.compile(r'^.*\bresolve_fused_ops: Flash Attention (enabled|not supported, set to disabled)\s*$', re.MULTILINE)
REQUESTED = re.compile(r'^.*\bllama_context: flash_attn\s*=\s*(auto|enabled|disabled)\s*$', re.MULTILINE)

def resolve(log):
    if set(REQUESTED.findall(log)) != {'auto'}:
        raise ValueError('flash attention requested mode absent, ambiguous or not auto')
    states = {'on' if m == 'enabled' else 'off' for m in PATTERN.findall(log)}
    if len(states) != 1:
        raise ValueError('flash attention resolution absent or ambiguous')
    return states.pop()
