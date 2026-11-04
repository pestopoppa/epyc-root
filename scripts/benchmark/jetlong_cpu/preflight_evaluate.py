"""Offline evaluator for a future no-cache numeric /completion prompt-count probe."""
def evaluate(response, expected):
    if type(expected) is not int or expected <= 0 or not isinstance(response, dict):
        raise ValueError('invalid preflight input')
    timings = response.get('timings')
    if not isinstance(timings, dict):
        return {'verdict': 'INVALID', 'reason': 'missing timings'}
    count, cache = timings.get('prompt_n'), timings.get('cache_n')
    evaluated, truncated = response.get('tokens_evaluated'), response.get('truncated')
    if any(type(x) is not int for x in (count, cache, evaluated)) or type(truncated) is not bool:
        return {'verdict': 'INVALID', 'reason': 'missing or invalid count, cache or truncation field'}
    if truncated or cache != 0 or count != expected or evaluated != expected:
        return {'verdict': 'FAIL', 'expected': expected, 'prompt_n': count, 'cache_n': cache,
                'tokens_evaluated': evaluated, 'truncated': truncated}
    return {'verdict': 'PASS', 'expected': expected, 'prompt_n': count,
            'cache_n': cache, 'tokens_evaluated': evaluated, 'truncated': truncated}
