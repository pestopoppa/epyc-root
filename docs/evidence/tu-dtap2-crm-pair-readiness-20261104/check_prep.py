#!/usr/bin/env python3
import json
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/live-pair-20261104')
x=json.loads((D/'input.json').read_bytes())
expected={'model':'c159d1518f16bc42533d9a09f034eb598b670341adc2b08b9a9751614aea71eb',
          'server':'4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c',
          'template':'87a2728cb8dc9fe424d624542f6060ec05a1d285ebbec578bb078900e33396b5'}
observed={k:x[k]['sha256'] for k in expected}
if x.get('source_commit')!='ec063054d2d7e2e801b130d124fec18683a96a15' or observed!=expected:
    raise SystemExit('preflight/source identity mismatch: '+json.dumps({'source_commit':x.get('source_commit'),'observed':observed},sort_keys=True))
print('prepared inputs match source, model, production CPU kernel, and template pins')
