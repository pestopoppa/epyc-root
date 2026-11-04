"""Refuse a modified packet or source-bound plan before launching a server."""
import hashlib,json
from pathlib import Path
def verify_packet_pin(pin_path):
    pin_path=Path(pin_path); data=json.loads(pin_path.read_text())
    if hashlib.sha256((pin_path.parent/'plan.json').read_bytes()).hexdigest()!=data['plan_sha256']:
        raise ValueError('plan identity changed')
    files=data['files']
    if not files or not any(Path(p).name=='token-ids.json' for p in files):
        raise ValueError('token fixture pin absent')
    for p,h in files.items():
        if not Path(p).is_absolute() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:
            raise ValueError('packet identity changed: '+p)
