"""Explicit diagnostic-only call budget; the native request-budget fraction is retained."""
SCOUT_BUDGET_S = 600.0
REQUEST_TIMEOUT_S = 1800
PER_CALL_TIMEOUT_S = 600.0


def apply(stage):
    if stage.REQUEST_BUDGET_FRACTION != 0.4:
        raise ValueError('unexpected native request-budget policy')
    original = stage.PER_CALL_TIMEOUT_S
    stage.PER_CALL_TIMEOUT_S = PER_CALL_TIMEOUT_S
    return {'schema': 'epyc.kpf26.diagnostic-scout-policy.v1',
            'original_per_call_timeout_s': original,
            'per_call_timeout_s': stage.PER_CALL_TIMEOUT_S,
            'request_timeout_s': REQUEST_TIMEOUT_S,
            'requested_scout_budget_s': SCOUT_BUDGET_S,
            'request_budget_fraction': stage.REQUEST_BUDGET_FRACTION,
            'initial_effective_scout_budget_s': min(SCOUT_BUDGET_S, REQUEST_TIMEOUT_S*stage.REQUEST_BUDGET_FRACTION),
            'scope': 'isolated diagnostic API process only; production policy unchanged'}
