import json, sqlite3, time
p='/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db'
c=sqlite3.connect('file:'+p+'?mode=ro',uri=True)
result=c.execute("SELECT count(*), coalesce(sum(update_count),0) FROM memories WHERE instr(context,?)>0", ('What is 17 * 3?',)).fetchone()
print(json.dumps({'db_path':p,'observed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'matched_rows':result[0],'matched_update_count_sum':result[1],'meaning':'literal substring only; traffic provenance unknown'}))
