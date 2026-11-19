"""HS-9 deterministic fake tools. No host filesystem, process, or network access."""
from copy import deepcopy

CASES = {
    'HS9-01': {'inspect': {'value': 42}, 'check': {'status': 'pass'}},
    'HS9-02': {'delegate': {'artifact': 'child/artifact', 'check': 'pass'}},
    'HS9-03': {},
    'HS9-04': {'check:malformed': {'status': 'fail', 'corrected_input': 'corrected'},
                'check:corrected': {'status': 'pass'}},
    'HS9-05': {'perform': {'status': 'denied', 'reason': 'permission'}},
}

class Simulator:
    """One per trial. Calls and outputs are recorded by the runner, never by the model."""
    def __init__(self, case):
        if case not in CASES:
            raise ValueError('unknown case')
        self.case = case
        self.events = []
        self.stopped = False

    def call(self, tool, args):
        if self.stopped:
            raise ValueError('trial already stopped')
        if not isinstance(tool, str) or not isinstance(args, dict):
            raise ValueError('invalid call')
        key = 'check:' + str(args.get('input')) if self.case == 'HS9-04' and tool == 'check' else tool
        result = deepcopy(CASES[self.case].get(key, {'status': 'unavailable'}))
        self.events.append({'tool': tool, 'args': deepcopy(args), 'result': deepcopy(result)})
        return result

    def finish(self, report):
        if self.stopped or not isinstance(report, dict):
            raise ValueError('invalid final report')
        self.stopped = True
        return {'case': self.case, 'events': deepcopy(self.events), 'report': deepcopy(report),
                'capture_complete': True, 'termination': 'final_report'}
