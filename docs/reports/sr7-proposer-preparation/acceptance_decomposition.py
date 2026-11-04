"""Descriptive decomposition of aggregate proposer acceptance; no causal inference.

Input counters must come from comparable, already validated independent samples.
This arithmetic does not validate measurement design, source provenance, uncertainty,
or the caller's aggregation of requests. Zero-count proposer rates are undefined.
"""
from fractions import Fraction


def decompose_acceptance(first, second):
    """Split second-minus-first acceptance into symmetric mix/rate components.

    Inputs map the same proposer names to generated_tokens/accepted_tokens counts.
    Each proposer must generate at least one token in each sample. Fractions are
    returned exactly so the two components sum to the overall difference.
    """
    if not isinstance(first, dict) or not isinstance(second, dict) or not first or set(first) != set(second):
        raise ValueError('same nonempty proposer names required')
    if any(not isinstance(name, str) or not name for name in first):
        raise ValueError('nonempty proposer names required')

    def validate(sample):
        for values in sample.values():
            if not isinstance(values, dict):
                raise ValueError('proposer counters required')
            g, a = values.get('generated_tokens'), values.get('accepted_tokens')
            if type(g) is not int or type(a) is not int or g <= 0 or not 0 <= a <= g:
                raise ValueError('positive generated and valid accepted counts required')
        return sum(v['generated_tokens'] for v in sample.values())

    totals = (validate(first), validate(second))
    mix = Fraction(0)
    rate = Fraction(0)
    details = {}
    for name in sorted(first):
        a, b = first[name], second[name]
        w0, w1 = Fraction(a['generated_tokens'], totals[0]), Fraction(b['generated_tokens'], totals[1])
        r0 = Fraction(a['accepted_tokens'], a['generated_tokens'])
        r1 = Fraction(b['accepted_tokens'], b['generated_tokens'])
        dm = (w1 - w0) * (r0 + r1) / 2
        dr = (r1 - r0) * (w0 + w1) / 2
        details[name] = {'mix': dm, 'rate': dr}
        mix += dm
        rate += dr
    delta = (Fraction(sum(v['accepted_tokens'] for v in second.values()), totals[1]) -
             Fraction(sum(v['accepted_tokens'] for v in first.values()), totals[0]))
    assert mix + rate == delta
    return {'delta': delta, 'mix': mix, 'rate': rate, 'proposers': details}
