import json,os,pathlib,time
r=json.loads(pathlib.Path(os.environ['QUAL_RESULT']).read_text());b=r['boundary'];stop=pathlib.Path(b['stop']);assert r['status']=='PROBED' and r['cleanup_actual']=='PASS' and r['progress']==5 and r['exact_marker_safe'] is True and len(r['tests'])==4 and not stop.exists() and time.time()<b['end']
