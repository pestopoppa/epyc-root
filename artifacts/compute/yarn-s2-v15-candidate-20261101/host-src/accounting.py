"""Match full-plan denominator while preserving interrupted exposure."""
def classify(scope,plan,rows,marker_state):
 ids=scope.get("item_ids")
 if not isinstance(ids,list) or len(ids)!=30 or len(set(ids))!=30 or scope.get("nominal_items")!=30 or scope.get("full_campaign_items")!=120:raise ValueError("scope")
 selected=[x for x in plan if x.get("item_id") in ids]
 expected={x["item_id"]:x["prompt_sha256"] for x in selected}
 if len(selected)!=30 or set(expected)!=set(ids):raise ValueError("plan mismatch")
 seen={}
 for r in rows:
  key=(r.get("arm"),r.get("item_id"))
  if key[0] not in ("A0","A1") or key[1] not in expected or key in seen or r.get("prompt_sha256")!=expected[key[1]]:raise ValueError("invalid result identity")
  seen[key]=r
 prior={(x["arm"],x["item_id"]) for x in scope.get("predecessor_unknown",[])}
 counts={"ok":0,"error":0,"unknown":0,"unexposed":0}
 cells=[]
 for arm in ("A0","A1"):
  for item in ids:
   key=(arm,item);r=seen.get(key)
   if key in prior:
    if r is not None:raise ValueError("prior unknown has result")
    status="unknown"
   elif r is not None:
    status=r.get("status")
    if status not in ("ok","error"):raise ValueError("bad terminal status")
   else:
    state=marker_state(arm,item,expected[item])
    if state not in ("unexposed","unknown","responded"):raise ValueError("marker state")
    status="unexposed" if state=="unexposed" else "unknown"
   counts[status]+=1;cells.append({"arm":arm,"item_id":item,"status":status})
 return {"planned_cells":60,"nominal_items":30,"campaign_nominal_items":120,"counts":counts,"cells":cells}
