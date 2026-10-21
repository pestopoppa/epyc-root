#!/usr/bin/env python3
"""ECR-EB-1 slice builder. Applies SELECTION_RULE.md exactly (committed first). Zero compute: parses local copies of the
EdgeBench card, tasks.jsonl, task shards and the paper HTML. Usage: build_slice.py <outdir>"""
import csv, glob, hashlib, html, json, os, re, sys
D1 = "/mnt/raid0/llm/tmp/dive-dpf-1361"
SH = "/mnt/raid0/llm/tmp/dive-dpfw2-edgebench-shards/shards"
MODELS = ["Opus 4.8", "GPT-5.5", "GPT-5.4", "GLM-5.1", "DS-V4-Pro"]
GPU_REQ = re.compile(r"(requires?|needs?|must use|use an?|uses?)\s+(an?\s+)?(nvidia\s+)?(gpu|cuda)\b", re.I)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
log = {"sha256": {k: sha(os.path.join(D1, k)) for k in ("README.md", "tasks.jsonl", "paper.html")}}

# card
card = {}
for line in open(os.path.join(D1, "README.md"), encoding="utf8"):
    if not line.startswith("| ") or "/" not in line:
        continue
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) != 7 or not re.match(r"^[a-z0-9_]+$", c[0]):
        continue
    card[c[0]] = {}
    for m, cell in zip(MODELS, c[2:]):
        v = [None if x.strip() == "—" else float(x) for x in cell.split("/")]
        if len(v) == 6:
            card[c[0]][m] = v
log["card_tasks"] = len(card)
tasks = {json.loads(l)["task_id"]: json.loads(l) for l in open(os.path.join(D1, "tasks.jsonl"))}
log["tasks_jsonl"] = len(tasks)

# paper
h = open(os.path.join(D1, "paper.html"), encoding="utf8").read()
seg = h[h.find('id="A7.T8'):]
paper = {}
for r in re.findall(r"<tr\b.*?</tr>", seg, re.S):
    x = re.sub(r"<annotation.*?</annotation>", "", r, flags=re.S)
    x = html.unescape(re.sub(r"<[^>]+>", "|", x))
    toks = [t.strip() for t in x.split("|") if t.strip()]
    if not toks or not re.match(r"^[a-z0-9_]+$", toks[0]):
        continue
    name, rest = toks[0], toks[1:]
    cells, i = [], 0
    while i < len(rest) and len(cells) < 5:
        if rest[i] == "—":
            cells.append((None, None, False)); i += 1; continue
        try:
            mean = float(rest[i])
        except ValueError:
            break
        i += 1; star = False
        if i < len(rest) and rest[i] == "*":
            star = True; i += 1
        sd = None
        if i < len(rest) and rest[i] == "±":
            sd = float(rest[i + 1]); i += 2
        cells.append((mean, sd, star))
    if len(cells) == 5:
        paper[name] = dict(zip(MODELS, cells))
log["paper_task_rows"] = len(paper)
mism = 0; chk = 0
for t, p in paper.items():
    for m in MODELS:
        if t in card and m in card[t] and p[m][0] is not None and card[t][m][5] is not None:
            chk += 1; mism += abs(p[m][0] - card[t][m][5]) > 0.051
log["paper_vs_card_12h_cells_checked"] = chk; log["paper_vs_card_12h_mismatch"] = mism

stages = {}
rows = []
all_ids = sorted(set(card) | set(tasks))
joined = [t for t in all_ids if t in card and t in tasks and t in paper]
stages["join_card_tasks_paper"] = len(joined); stages["dropped_unmatched"] = sorted(set(all_ids) - set(joined))
surv = [t for t in joined if tasks[t]["language"] in ("Python", "C++")]; stages["lang_python_cpp"] = len(surv)
surv = [t for t in surv if tasks[t]["internet"] is False]; stages["internet_false"] = len(surv)
def cpu_only(t):
    p = os.path.join(SH, t + ".json")
    return os.path.exists(p) and not GPU_REQ.search(open(p, encoding="utf8").read())
surv = [t for t in surv if cpu_only(t)]; stages["cpu_only"] = len(surv)
def s2max(t): return max([v[0] for v in card[t].values() if v[0] is not None], default=None)
surv = [t for t in surv if s2max(t) is not None and s2max(t) < 90.0]; stages["nonsaturated_2h_lt90"] = len(surv)
def head(t):
    d = [v[5] - v[0] for v in card[t].values() if v[0] is not None and v[5] is not None]
    return (sum(d) / len(d), len(d)) if d else (None, 0)
surv = [t for t in surv if head(t)[1] >= 3 and head(t)[0] > 0]; stages["headroom_pos"] = len(surv)
def sd(t, m): return paper[t][m][1]
excl = [t for t in surv if any(sd(t, m) is not None and sd(t, m) > 15.0 for m in ("GLM-5.1", "DS-V4-Pro"))]
surv2 = [t for t in surv if t not in excl]; stages["sd_gt15_excluded"] = excl; stages["after_sd_exclusion"] = len(surv2)
rank = sorted(surv2, key=lambda t: (-head(t)[0], t))[:8]
cols = ["rank", "task_id", "language", "category", "metric", "mean_headroom_2h_to_12h", "n_models_headroom", "max_score_2h", "mean_score_2h", "mean_score_12h",
        "glm51_12h_mean", "glm51_12h_sd", "dsv4pro_12h_mean", "dsv4pro_12h_sd", "sd_flag", "internet", "cpu_only", "score_direction_note"]
with open(os.path.join(out, "edgebench_slice.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols)
    for i, t in enumerate(rank, 1):
        hh, n = head(t)
        s2 = [v[0] for v in card[t].values() if v[0] is not None]; s12 = [v[5] for v in card[t].values() if v[5] is not None]
        g, d = paper[t]["GLM-5.1"], paper[t]["DS-V4-Pro"]
        flag = "sd_missing" if (g[1] is None or d[1] is None) else ("fewer_than_3_runs" if (g[2] or d[2]) else "ok")
        w.writerow([i, t, tasks[t]["language"], tasks[t]["category"], tasks[t]["metric"], round(hh, 2), n, max(s2), round(sum(s2) / len(s2), 2), round(sum(s12) / len(s12), 2),
                    g[0], g[1], d[0], d[1], flag, tasks[t]["internet"], True, "card scores are rescaled 0-100 (higher better); raw direction field not used"])
# full audit table of every joined task with its stage outcome
with open(os.path.join(out, "edgebench_all_joined_audit.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["task_id", "language", "internet", "cpu_only", "max_score_2h", "mean_headroom", "n_models", "glm_sd", "ds_sd", "outcome"])
    for t in joined:
        hh, n = head(t); g, d = paper[t]["GLM-5.1"], paper[t]["DS-V4-Pro"]
        o = ("selected" if t in rank else "sd_excluded" if t in excl else "below_top8" if t in surv2 else
             "language" if tasks[t]["language"] not in ("Python", "C++") else "internet" if tasks[t]["internet"] else "gpu_or_no_shard" if not cpu_only(t) else
             "saturated_2h" if not (s2max(t) is not None and s2max(t) < 90) else "headroom")
        w.writerow([t, tasks[t]["language"], tasks[t]["internet"], cpu_only(t), s2max(t), None if hh is None else round(hh, 2), n, g[1], d[1], o])
log["stages"] = stages; log["selected"] = rank
json.dump(log, open(os.path.join(out, "build_log.json"), "w"), indent=1)
print(json.dumps(log, indent=1))
