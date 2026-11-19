"""Check the one-device KFD inventory against the prepared MI210 identity."""

import json
from pathlib import Path


PIN = Path(__file__).resolve().parent / 'device-pin.json'
TOPOLOGY = Path('/sys/class/kfd/kfd/topology/nodes')
FIELDS = ('unique_id', 'vendor_id', 'device_id', 'domain', 'location_id',
          'drm_render_minor', 'gfx_target_version')


def device():
    gpu_nodes = [(p.parent, int(p.read_text())) for p in sorted(TOPOLOGY.glob('*/gpu_id'))]
    (node, gpu_id), = [(node, gpu_id) for node, gpu_id in gpu_nodes if gpu_id]
    properties = dict(line.split() for line in (node / 'properties').read_text().splitlines())
    return {
        'node': int(node.name),
        'gpu_id': gpu_id,
        'name': (node / 'name').read_text().strip(),
        'pci': {key: int(properties[key]) for key in FIELDS},
    }


def verify():
    live = device()
    if live != json.loads(PIN.read_bytes()):
        raise ValueError('the singleton KFD device differs from the prepared MI210 pin')
    return live


if __name__ == '__main__':
    verify()
