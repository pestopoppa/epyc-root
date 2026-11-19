#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
import json, sys
p=json.load(open(sys.argv[1]))
if p.get('schema') not in ('dtap.crm_posthash.v1','dtap.crm_posthash_fixture.v1'): raise SystemExit(1)
if p.get('capture_kind') not in ('live','fixture'): raise SystemExit(1)
