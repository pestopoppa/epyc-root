"""DeepDive question-only projection; no gold is sent to either arm."""
def project(row):
 q=row.get("question") if isinstance(row,dict) else None
 if not isinstance(q,str) or not q: raise ValueError("invalid question")
 return q
