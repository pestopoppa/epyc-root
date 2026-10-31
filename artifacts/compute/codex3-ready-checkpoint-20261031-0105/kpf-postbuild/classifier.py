import json
def classify(rc, log, output_created):
    lines=log.splitlines()
    prefix="supervisor admission refused: "
    if rc==78 and not output_created and len(lines)==1 and lines[0].startswith(prefix) and len(lines[0])>len(prefix):
        return "RETRYABLE_PRE_NATIVE_ADMISSION_REFUSAL"
    summaries=[]
    for line in lines:
        try: obj=json.loads(line)
        except (json.JSONDecodeError, TypeError): continue
        if isinstance(obj,dict) and obj.get("schema")=="hil15-r11-smoke-supervisor/v1": summaries.append(obj)
    try:
        if (rc==0 and len(summaries)==1 and summaries[0].get("child_rc")==0
            and summaries[0].get("children_drained") is True and summaries[0].get("failure") is None
            and 0<=summaries[0].get("elapsed_s",float("inf"))<=300
            and 0<=summaries[0].get("sampled_peak_tree_rss_bytes",float("inf"))<=8*1024**3):
            return "SUPERVISOR_PASS_REQUIRES_RESULT_VALIDATION"
    except TypeError: pass
    return "HALT_PRESERVE_AND_INSPECT"
