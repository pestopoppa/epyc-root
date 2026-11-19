"""Validate original K35-shaped request pairs and native completion telemetry."""
CAP_KEY = 'speculative.n_max'
CAP = 7


def verify_pairs(items):
    groups = {}
    for item in items:
        groups.setdefault(item['dflash_pair'], []).append(item['request_body'])
    if len(groups) != 4:
        raise ValueError('expected four predeclared cap pairs')
    prompts = set()
    for pair in groups.values():
        if len(pair) != 2 or [body[CAP_KEY] for body in pair] != [0, CAP]:
            raise ValueError('expected cap 0 then cap 7')
        off, on = ({key: value for key, value in body.items() if key != CAP_KEY} for body in pair)
        if off != on or off['prompt'] in prompts:
            raise ValueError('pair bodies differ beyond cap or repeat a prompt')
        prompts.add(off['prompt'])


def verify_response(data, item, recipe):
    body = item['request_body']
    settings = data['generation_settings']
    timings = data['timings']
    cap = body.get(CAP_KEY)
    spec = recipe['speculation']
    types = set(settings['speculative.types'].split(','))
    if spec not in types or types - {'none', spec}:
        raise ValueError('native response misidentified speculation mode')
    if cap is not None and (type(settings.get(CAP_KEY)) is not int or settings[CAP_KEY] != cap):
        raise ValueError('native response cap differs from request')
    # The native timings serializer omits both counts when no drafting occurred.
    drafted = timings.get('draft_n', 0)
    accepted = timings.get('draft_n_accepted', 0)
    if (type(drafted) is not int or type(accepted) is not int or not 0 <= accepted <= drafted
            or (cap and (drafted == 0 or 'draft_n_accepted' not in timings))
            or (not cap and drafted != 0)):
        raise ValueError('native draft counters contradict cap')
    tokens = data['tokens']
    count = timings['predicted_n']
    finish = data['stop_type']
    limit = body['n_predict']
    if (not isinstance(tokens, list) or not tokens
            or any(type(token) is not int or token < 0 for token in tokens)
            or any(type(n) is not int or n != len(tokens) for n in (count, data['tokens_predicted']))
            or not isinstance(data['content'], str) or not data['content'].strip()
            or finish not in ('eos', 'word', 'limit') or count > limit or (finish == 'limit' and count != limit)):
        raise ValueError('native content, token count or finish is inconsistent')
    prompt_n = timings['prompt_n']
    if (type(prompt_n) is not int or not 1 <= prompt_n <= recipe['context_tokens'] - limit
            or data['tokens_evaluated'] != prompt_n or timings['cache_n'] != 0 or data['truncated'] is not False):
        raise ValueError('native response lacks intact cold prefill')
    return {key: timings[key] for key in ('draft_n', 'draft_n_accepted') if key in timings}
