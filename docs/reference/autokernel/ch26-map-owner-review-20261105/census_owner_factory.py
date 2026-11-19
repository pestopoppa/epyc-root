"""Private wiring for the existing C5 request-owner factory; diagnostic only."""
from pathlib import Path
from boundary_witness import Hook
from census_hook import CensusHook

def make_factory(*, out, snapshot, quiet, launch_state, runtime_prepared, hook_type=Hook, census_type=CensusHook):
    if runtime_prepared is None:
        raise ValueError("prepared C5 runtime identity required")
    root = Path(out).resolve()
    def factory(owned, slots, *, request_context):
        ordinal = launch_state['ordinal']
        phase = request_context.get('phase')
        slot = request_context.get('slot_index')
        if type(ordinal) is not int or not 1 <= ordinal <= 48 or phase not in ('warmup', 'measurement') or type(slot) is not int or slot != 0:
            raise ValueError('invalid request identity for census path')
        inner = hook_type(owned, slots, root/'request-boundaries.jsonl', snapshot=snapshot,
                          quiet=quiet, request_context=request_context,
                          launch_ordinal=ordinal, observer_required=True, runtime_prepared=runtime_prepared)
        path = root/'host-census'/f'launch-{ordinal:03d}-{phase}-slot-{slot}.json'
        return census_type(inner, receipt_path=str(path))
    return factory
