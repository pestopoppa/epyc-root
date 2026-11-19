"""Parse a single isolated v10 speculative statistics snapshot.

The caller must provide one complete trace emitted after a single request on a
fresh server. The parser cannot establish that lifecycle from text alone.
"""
import re

LINE = re.compile(
    r"statistics\s+(?P<name>[\w-]+):\s+#calls\(b,g,a\)\s*=\s*"
    r"(?P<begin>\d+)\s+(?P<draft_calls>\d+)\s+(?P<accept_calls>\d+),\s*"
    r"#gen drafts\s*=\s*(?P<generated_drafts>\d+),\s*"
    r"#acc drafts\s*=\s*(?P<accepted_drafts>\d+),\s*"
    r"#gen tokens\s*=\s*(?P<generated_tokens>\d+),\s*"
    r"#acc tokens\s*=\s*(?P<accepted_tokens>\d+)"
)


def parse_proposer_stats(text, expected_names, response_generated, response_accepted):
    """Return proposer counts and rates, rejecting incomplete or inconsistent logs."""
    expected = set(expected_names)
    if len(expected) != len(expected_names) or not expected:
        raise ValueError('expected proposer names must be nonempty and unique')
    if type(response_generated) is not int or type(response_accepted) is not int:
        raise ValueError('response counters must be integers')
    if response_generated <= 0 or not 0 <= response_accepted <= response_generated:
        raise ValueError('invalid response counters')
    found = {}
    for line in text.splitlines():
        if 'statistics' not in line or '#gen drafts' not in line:
            continue
        match = LINE.search(line)
        if not match:
            raise ValueError('malformed statistics line')
        name = match['name']
        if name in found or name not in expected:
            raise ValueError('duplicate or unexpected proposer')
        counts = {key: int(value) for key, value in match.groupdict().items() if key != 'name'}
        if (counts['accepted_tokens'] > counts['generated_tokens'] or
                counts['accepted_drafts'] > counts['generated_drafts'] or
                counts['accepted_drafts'] > counts['accept_calls']):
            raise ValueError('inconsistent proposer counters')
        found[name] = counts
    if set(found) != expected:
        raise ValueError('missing proposer statistics')
    total_generated = sum(x['generated_tokens'] for x in found.values())
    total_accepted = sum(x['accepted_tokens'] for x in found.values())
    if (total_generated, total_accepted) != (response_generated, response_accepted):
        raise ValueError('proposer totals do not match response counters')
    for counts in found.values():
        generated = counts['generated_tokens']
        counts['token_share'] = generated / total_generated
        counts['acceptance'] = counts['accepted_tokens'] / generated if generated else None
    return {'proposers': found, 'acceptance': total_accepted / total_generated}
