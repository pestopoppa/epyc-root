def validate_verdict(verdict):
    return isinstance(verdict, dict) and set(verdict) == {'P1', 'P2', 'P3'} and all(verdict[k] is True for k in ('P1', 'P2', 'P3'))
