import json, sys, numpy as np
P = sys.argv[1]
R = json.load(open(f"{P}/RESULT.json"))
def load(arm, role, n):
    return [np.load(f"{P}/{arm}-{role}-{i:03d}.npy") for i in range(n)]
out = {}
for fam in ("mirror", "upstream"):
    a, b = f"{fam}_fp32", f"{fam}_int8"
    S = {}
    for arm in (a, b):
        Q = load(arm, "k7", 70); D = load(arm, "document", 200)
        S[arm] = np.array([[float((q @ d.T).max(axis=1).sum()) for d in D] for q in Q])
    rec = [t for t in R["top1"] if t["pair"] == f"{a}__{b}"][0]
    ids = [d["query_id"] for d in rec["details"]]
    t1a, t1b = S[a].argmax(1), S[b].argmax(1)
    stored = [(d["top1"][a], d["top1"][b]) for d in rec["details"]]
    recomputed_matches_stored = all((int(x), int(y)) == s for x, y, s in zip(t1a, t1b, stored))
    dis = []
    for i in range(70):
        if t1a[i] != t1b[i]:
            order = np.argsort(-S[a][i])
            rank_b_in_a = int(np.where(order == t1b[i])[0][0]) + 1
            m = S[a][i]; top = m[order[0]]
            dis.append({"query_id": ids[i], "fp32_top1": int(t1a[i]), "int8_top1": int(t1b[i]),
                        "int8_top1_rank_in_fp32": rank_b_in_a,
                        "fp32_rel_gap_top1_vs_int8pick": float((top - m[t1b[i]]) / abs(top)),
                        "fp32_rel_top2_margin": float((top - m[order[1]]) / abs(top))})
    agree_margins = [float((np.sort(S[a][i])[-1] - np.sort(S[a][i])[-2]) / abs(np.sort(S[a][i])[-1])) for i in range(70) if t1a[i] == t1b[i]]
    out[f"{a}__{b}"] = {"agreement": f"{70-len(dis)}/70", "recomputed_matches_stored": recomputed_matches_stored,
        "disagreements": dis,
        "disagree_int8pick_rank_counts": {str(r): sum(1 for d in dis if d["int8_top1_rank_in_fp32"] == r) for r in sorted({d["int8_top1_rank_in_fp32"] for d in dis})},
        "disagree_fp32_rel_margin_median": float(np.median([d["fp32_rel_top2_margin"] for d in dis])) if dis else None,
        "agree_fp32_rel_margin_median": float(np.median(agree_margins))}
same = []
print(json.dumps(out, indent=1))
