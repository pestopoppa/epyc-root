"""Partial s2 selection; preserve all 60 cells and never replay ambiguous pairs."""
def eligible(scope,summary,arm):
 ids=scope.get("eligible_candidate_pairs"); unknown={x["item_id"] for x in scope.get("predecessor_unknown",[]) if x.get("arm")=="A0"}
 if not isinstance(ids,list) or len(ids)!=26 or len(set(ids))!=26 or len(unknown)!=4 or set(ids)&unknown or set(ids)|unknown!=set(scope["item_ids"]):raise ValueError("invalid candidate accounting")
 cells=summary.get("cells");
 if not isinstance(cells,list) or len(cells)!=60:raise ValueError("invalid 60-cell accounting")
 state={(x["arm"],x["item_id"]):x["status"] for x in cells}
 if len(state)!=60:raise ValueError("duplicate accounting")
 return {i for i in ids if state.get((arm,i))=="unexposed" and (arm=="A0" or (arm=="A1" and state.get(("A0",i))=="ok"))}
def choose(scope,summary):
 for arm in ("A0","A1"):
  if eligible(scope,summary,arm):return arm
 return None
