#!/usr/bin/env python3
"""Real verifier progress: native ingest and planner assembly completed, regardless of visibility verdict."""
import json,os,sys
from pathlib import Path
try:
    d=json.loads(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).read_text())
    ok=(d.get('schema')=='epyc.vb.akwire.planning_canary.v1' and d.get('prepare_status')=='ready'
        and d.get('rows_projected')==31 and d.get('ingest_refused')==0
        and isinstance(d.get('proposition_visible'),bool)
        and len(d.get('native_final_sha256',''))==64 and d.get('model_backend_calls')==0)
except (OSError,ValueError,KeyError): ok=False
sys.exit(0 if ok else 1)
