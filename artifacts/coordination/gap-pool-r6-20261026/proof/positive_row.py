"""Exact synthetic canonical fixture row; no process or filesystem effects."""
def build_positive_row(row_id, private, quarter, pid):
    if quarter not in ('q0', 'q1', 'q2', 'q3'):
        raise ValueError('literal quarter required')
    return [row_id, 'fixture-owner', str(private / 'filler_run11.sh') + ' pid=' + str(pid),
            quarter, '300', '1', str(private / 'STOP'), 'ARMED', 'block-correctness',
            '600 s', '300', 'n', 'y', 'none found (fixture, 2026-10-26)',
            'synthetic exact correctness', 'n/a (correctness fixture)', 'cpu',
            'pool:gap-filler']

def canonical_physical(region):
    aliases={'q0':0,'0-23':0,'q1':1,'24-47':1,
             'q2':2,'48-71':2,'q3':3,'72-95':3}
    if region not in aliases:
        raise ValueError('canonical region must be one literal full quarter')
    lo=aliases[region]*24
    return set(range(lo,lo+24))

def assert_canonical_affinity(actual_cpus, canonical_region):
    actual={c%96 for c in actual_cpus}
    if actual != canonical_physical(canonical_region):
        raise AssertionError('actual affinity differs from canonical granted quarter')
