#!/usr/bin/env python3
"""RTG-ASK-1: ask-calibration from logs only (no inference).

Reads the orchestrator progress JSONL logs (read-only), writes a results JSON.
Stdlib only.  Usage:
    python3 rtg_ask1_log_replay.py <progress_dir> <out_json>
"""
import hashlib
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict

TYPES = ("task_started", "routing_decision", "task_completed", "task_failed",
         "escalation_triggered", "plan_reviewed")
TOP = ("architect",)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(pdir):
    eps = defaultdict(lambda: {"esc": [], "plan": 0})
    files = sorted(x for x in os.listdir(pdir) if x.endswith(".jsonl"))
    manifest = []
    for fn in files:
        p = os.path.join(pdir, fn)
        manifest.append({"file": fn, "bytes": os.path.getsize(p), "sha256": sha(p)})
        with open(p, errors="replace") as f:
            for line in f:
                if not any(('"%s"' % t) in line[:40] for t in TYPES):
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                et, tid = r.get("event_type"), r.get("task_id")
                if et not in TYPES or not tid:
                    continue
                e = eps[tid]
                d = r.get("data") or {}
                ts = r.get("timestamp")
                if et == "task_started":
                    e["start"] = e.get("start") or ts
                    e["prompt_chars"] = len(d.get("objective") or "")
                elif et == "routing_decision" and "route" not in e:
                    e["route"] = (d.get("routing") or [None])[0]
                    e["risk"] = d.get("factual_risk_score")
                    e["band"] = d.get("factual_risk_band")
                    e["diff"] = d.get("difficulty_score")
                    e["start"] = e.get("start") or ts
                elif et in ("task_completed", "task_failed"):
                    ans = ((d.get("work") or {}).get("answer")) or ""
                    e["end_ts"] = ts
                    e["outcome"] = r.get("outcome") if et == "task_completed" else "failure"
                    e["infra"] = ans.startswith("[ERROR:")
                    e["tokens"] = d.get("tokens_generated") or 0
                    e["gen_ms"] = d.get("generation_ms") or 0.0
                    e["ans_chars"] = d.get("answer_chars") or 0
                    e["prod_role"] = d.get("producer_role")
                elif et == "escalation_triggered":
                    e["esc"].append(d.get("reason") or "")
                    e["esc_to"] = d.get("to_tier")
                    e["esc_from"] = d.get("from_tier")
                    e["start"] = e.get("start") or ts
                elif et == "plan_reviewed":
                    e["plan"] += 1
    return eps, manifest


def auroc(y, s):
    pos = [v for v, l in zip(s, y) if l == 1]
    neg = [v for v, l in zip(s, y) if l == 0]
    if not pos or not neg:
        return None
    pairs = sorted([(v, l) for v, l in zip(s, y)])
    rank, i, rsum = 1, 0, 0.0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg = (rank + rank + (j - i) - 1) / 2
        rsum += avg * sum(1 for k in range(i, j) if pairs[k][1] == 1)
        rank += j - i
        i = j
    return (rsum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def boot_ci(y, s, n=300, seed=7):
    rnd = random.Random(seed)
    idx = list(range(len(y)))
    vals = []
    for _ in range(n):
        b = [rnd.choice(idx) for _ in idx]
        a = auroc([y[i] for i in b], [s[i] for i in b])
        if a is not None:
            vals.append(a)
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]]


def fit_logistic(X, y, epochs=300, lr=0.1, l2=1e-3):
    m = len(X[0])
    mu = [sum(r[j] for r in X) / len(X) for j in range(m)]
    sd = [max(1e-9, (sum((r[j] - mu[j]) ** 2 for r in X) / len(X)) ** 0.5) for j in range(m)]
    Z = [[(r[j] - mu[j]) / sd[j] for j in range(m)] for r in X]
    w, b = [0.0] * m, 0.0
    for _ in range(epochs):
        gw, gb = [l2 * v for v in w], 0.0
        for z, t in zip(Z, y):
            p = 1 / (1 + math.exp(-max(-30, min(30, b + sum(a * c for a, c in zip(w, z))))))
            for j in range(m):
                gw[j] += (p - t) * z[j] / len(Z)
            gb += (p - t) / len(Z)
        w = [a - lr * g for a, g in zip(w, gw)]
        b -= lr * gb
    return lambda r: b + sum(w[j] * (r[j] - mu[j]) / sd[j] for j in range(m))


def main():
    pdir, out = sys.argv[1], sys.argv[2]
    eps, manifest = load(pdir)
    digest = hashlib.sha256("".join(m["sha256"] for m in manifest).encode()).hexdigest()
    res = {"manifest_files": len(manifest), "manifest_digest": digest,
           "manifest_range": [manifest[0]["file"], manifest[-1]["file"]],
           "episodes_total": len(eps)}

    # ---- (a) counts
    all_esc = [(t, e) for t, e in eps.items() if e["esc"]]
    reasons = Counter()
    model_init = 0
    for _, e in all_esc:
        for r in e["esc"]:
            if r.startswith("Model-initiated"):
                model_init += 1
            reasons["nudges" if "nudge" in r else "failures" if "failure" in r else "other"] += 1
    per_role = defaultdict(lambda: {"policy_escalations": 0, "model_initiated_escalate": 0,
                                    "plan_review_consults": 0, "episodes": 0})
    for t, e in eps.items():
        role = e.get("route") or e.get("esc_from") or "unknown"
        pr = per_role[role]
        pr["episodes"] += 1
        pr["plan_review_consults"] += e["plan"]
        for r in e["esc"]:
            pr["policy_escalations"] += 1
            if r.startswith("Model-initiated"):
                pr["model_initiated_escalate"] += 1
    res["a_counts"] = {"escalation_events": sum(len(e["esc"]) for _, e in all_esc),
                       "episodes_with_escalation": len(all_esc),
                       "model_initiated_escalate_calls": model_init,
                       "escalation_reason_kinds": dict(reasons),
                       "plan_reviewed_consults_total": sum(e["plan"] for e in eps.values()),
                       "per_role": per_role,
                       "note": "escalation_triggered here = rule-policy failures/nudges; zero carry the 'Model-initiated:' prefix "
                               "that graph/nodes.py would write for escalate(). Consults are not tapped as distinct events; "
                               "plan_reviewed (architect plan review) is the only per-task consult-like record."}

    # ---- eligible episodes
    elig = [(t, e) for t, e in eps.items()
            if e.get("route") and "outcome" in e and not any(e["route"].startswith(x) for x in TOP)]
    elig.sort(key=lambda te: te[1].get("start") or "")
    res["eligible_episodes"] = len(elig)
    res["eligible_escalated"] = sum(1 for _, e in elig if e["esc"])
    if len(elig) < 200:
        res["stop"] = "fewer than 200 escalation-eligible episodes; counts only"
        json.dump(res, open(out, "w"), indent=1, default=dict)
        return

    # ---- (b) probe
    noninfra = [(t, e) for t, e in elig if not e["esc"] and not e["infra"]]
    res["probe_pool"] = {"non_escalated_non_infra": len(noninfra),
                         "excluded_infra": sum(1 for _, e in elig if not e["esc"] and e["infra"]),
                         "excluded_escalated": res["eligible_escalated"]}
    roles = ["frontdoor", "coder_escalation", "worker_general"]

    def feat(e, full):
        f = [e.get("risk") or 0.0, e.get("diff") or 0.0, math.log1p(e.get("prompt_chars") or 0)]
        f += [1.0 if (e.get("route") == r) else 0.0 for r in roles]
        if full:
            f += [math.log1p(e["tokens"]), math.log1p(e["ans_chars"]),
                  e["gen_ms"] / max(1, e["tokens"])]
        return f

    y = [0 if e["outcome"] == "success" else 1 for _, e in noninfra]
    cut = int(0.7 * len(noninfra))
    res["probe_split"] = {"train_n": cut, "holdout_n": len(noninfra) - cut,
                          "train_range": [noninfra[0][1]["start"], noninfra[cut - 1][1]["start"]],
                          "holdout_range": [noninfra[cut][1]["start"], noninfra[-1][1]["start"]],
                          "train_fail_rate": sum(y[:cut]) / cut,
                          "holdout_fail_rate": sum(y[cut:]) / (len(y) - cut)}
    res["entropy_only_baseline"] = {"n_episodes_with_logged_entropy": 0,
                                    "status": "UNAVAILABLE: generation_monitor entropy is not written to progress logs or the "
                                              "inference tap (0 entropy/logprob fields); no entropy-only AUROC can be computed "
                                              "without inference. Holdout AUROC for entropy-only = n/a."}
    ho = {}
    for name, full in (("probe_prompt_time_features", False), ("probe_with_post_gen_features", True)):
        X = [feat(e, full) for _, e in noninfra]
        if len(set(y[:cut])) < 2 or len(set(y[cut:])) < 2:
            ho[name] = {"auroc": None, "note": "single-class split"}
            continue
        sc = fit_logistic(X[:cut], y[:cut])
        s = [sc(r) for r in X[cut:]]
        yh = y[cut:]
        ho[name] = {"holdout_auroc": auroc(yh, s), "bootstrap95": boot_ci(yh, s), "n": len(yh)}
    # single-feature references (NOT the entropy baseline)
    yh = y[cut:]
    ho["ref_difficulty_score_only"] = {"holdout_auroc": auroc(yh, [(e.get("diff") or 0) for _, e in noninfra[cut:]])}
    ho["ref_factual_risk_only"] = {"holdout_auroc": auroc(yh, [(e.get("risk") or 0) for _, e in noninfra[cut:]])}
    ho["leakage_warning"] = ("post-gen features (tokens, answer_chars, ms/token) are outcome-correlated "
                             "(failed/empty answers are short) and are not available at ask time; only "
                             "probe_prompt_time_features is a valid ask-time probe.")
    res["b_holdout"] = ho
    res["m4_fired"] = False
    res["m4_reason"] = "not evaluable: entropy-only baseline has 0 logged samples; the >=0.05 margin cannot be established."

    # ---- (c) budget-priced penalty replay
    cells = defaultdict(lambda: {"esc": [0, 0], "no": [0, 0], "n": 0, "n_esc_events": 0})
    for _, e in elig:
        if e["infra"]:
            continue
        c = cells[(e["route"], e.get("band") or "none")]
        k = "esc" if e["esc"] else "no"
        c[k][0] += 1 if e["outcome"] == "success" else 0
        c[k][1] += 1
        c["n"] += 1
        c["n_esc_events"] += len(e["esc"])
    total = sum(c["n"] for c in cells.values())
    budget = sum(1 for _, e in elig if e["esc"] and not e["infra"]) / total
    rows = []
    for k, c in cells.items():
        if c["esc"][1] >= 5 and c["no"][1] >= 5:
            u = c["esc"][0] / c["esc"][1] - c["no"][0] / c["no"][1]
        else:
            u = None
        rows.append({"cell": "%s|%s" % k, "n": c["n"], "n_esc": c["esc"][1], "n_no": c["no"][1], "uplift": u})
    for r in rows:
        r["n_esc_events_cell"] = r["n_esc"]
    usable = sorted([r for r in rows if r["uplift"] is not None], key=lambda r: -r["uplift"])
    fixed = 0.15
    obs_vol = sum(r["n_esc"] for r in usable)
    priced = {}
    for frac in (1.0, 0.5, 0.25):
        cap, cov, lam, inc = frac * obs_vol, 0, None, set()
        for r in usable:
            if cov + r["n_esc"] > cap:
                break
            cov += r["n_esc"]
            lam = r["uplift"]
            inc.add(r["cell"])
        changed = [r for r in usable if (r["uplift"] > fixed) != (r["cell"] in inc)]
        priced["budget_%.2fx_observed_consults" % frac] = {
            "priced_lambda": lam, "cells_escalating": len(inc),
            "cells_with_decision_change_vs_fixed_0.15": len(changed),
            "episodes_in_changed_cells": sum(r["n"] for r in changed),
            "escalations_in_changed_cells": sum(r["n_esc"] for r in changed)}
    res["c_replay"] = {"budget_escalation_rate_observed": budget, "usable_cells": len(usable),
                       "cells_total": len(rows), "fixed_penalty": fixed,
                       "cells_escalating_under_fixed_0.15": sum(1 for r in usable if r["uplift"] > fixed),
                       "priced": priced,
                       "episodes_in_usable_cells": sum(r["n"] for r in usable),
                       "cells": usable,
                       "caveat": "uplift is observational (escalated episodes are selected by failure), so it is biased low; "
                                 "treat as a replay of rule decisions, not a causal price."}
    json.dump(res, open(out, "w"), indent=1, default=dict)


main()
