"""Project original GFX captures through the shared measurement carrier.

The producer reader reopens source, allocator, workload and raw-counter custody.
Only its original declared measurements are projected; UNKNOWN captures decline.
"""

from claim_tuple import register
from producers.gfx_observation.reader import ADAPTER_ID, native_rows, project as _project

AUTHORITY = "measurement"


@register("ak-gfx-observation")
def project(row):
    return _project(row)
