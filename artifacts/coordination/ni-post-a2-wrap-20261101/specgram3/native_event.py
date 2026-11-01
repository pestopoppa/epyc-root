import hashlib
import re

_PREFIX = re.compile(r'real logits ([a-z0-9-]+) script (\d+): prefix (\d+) \+ script (\d+) tokens')
_SUMMARY = re.compile(r'real logits computed in ([0-9]+(?:\.[0-9]+)?) s')

def parse_first_native_decode(log_text: str, expected_prompt_tokens: int) -> dict:
    lines=log_text.splitlines()
    vocab=next((line for line in lines if line.startswith('vocab ') and 'full load: real logits' in line),None)
    prefix_line=next((line for line in lines if _PREFIX.fullmatch(line.strip())),None)
    summary_line=next((line for line in lines if _SUMMARY.fullmatch(line.strip())),None)
    if not vocab or not prefix_line or not summary_line:
        raise ValueError('native full-load, decoded-prefix and post-decode summary lines are all required')
    if lines.index(prefix_line)>lines.index(summary_line):
        raise ValueError('native prefix event must precede post-decode summary')
    prefix_match=_PREFIX.fullmatch(prefix_line.strip());summary_match=_SUMMARY.fullmatch(summary_line.strip())
    kind, script, prompt, forced=prefix_match.groups();elapsed=float(summary_match.group(1))
    event={'kind':kind,'script':int(script),'prefix_tokens':int(prompt),'script_tokens':int(forced),
           'post_decode_elapsed_s':elapsed,
           'prefix_line_sha256':hashlib.sha256(prefix_line.encode()).hexdigest(),
           'summary_line_sha256':hashlib.sha256(summary_line.encode()).hexdigest(),
           'summary_line':summary_line.strip(),'prefix_line':prefix_line.strip(),
           'vocab_line_sha256':hashlib.sha256(vocab.encode()).hexdigest()}
    if event['kind'] != 'toolcall-eager' or event['script'] != 0:
        raise ValueError('native event is not the declared first toolcall-eager input')
    if event['prefix_tokens'] != expected_prompt_tokens or event['script_tokens'] <= 0 or elapsed<=0:
        raise ValueError('native event token counts differ from the declared first input')
    return event
