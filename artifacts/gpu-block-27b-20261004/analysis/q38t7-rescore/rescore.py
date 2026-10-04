#!/usr/bin/python3
"""Re-score Q38-T7 (results/q38_t7/20261004T025247Z) from calls.jsonl stored stats. No inference.

Phase A: PAIRED per id, drafted (dflash2) vs nodraft, under v1 and inf70-degeneracy.v2, plus
ground-truth answer checks for the items that finished with an answer inside 200 tokens.
Phase B/C: inf70-degeneracy.v2 from stored (n, uniq, top, run, words, ascii_ok); loop unchecked.
Writes rescore.json. RESCORE.md is written by hand from it.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
import degeneracy as D  # noqa: E402

RUN = Path("/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/q38_t7/20261004T025247Z")
POOL = Path("/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl")
OUT = Path(__file__).resolve().parent / "rescore.json"
RANK = {"OK": 0, "SHORT": 0, "DEGENERATE": 2, "EARLY-EOS": 3, "EMPTY": 3, "HTTP-ERROR": 3}


def grade(text: str, exp: dict, finish: str) -> str | None:
    """Ground truth only where the whole answer is visible (text_head holds 160 chars, so only
    outputs that STOPPED within 160 chars are gradable). None = not gradable."""
    if finish != "stop" or len(text) >= 160 or not exp:
        return None
    m, e = exp.get("scoring_method"), str(exp.get("expected") or "")
    if m == "multiple_choice":
        got = re.findall(r"\b([A-J])\b", text)
        return "correct" if got and got[0] == e else "wrong"
    if m in ("exact_match", "f1"):
        a = re.search(r"<answer>(.*?)</answer>", text, re.S)
        got = (a.group(1) if a else text).strip().lower()
        return "correct" if got == e.strip().lower() else "wrong"
    if m == "programmatic" and "two_responses" in str(exp.get("scoring_config")):
        parts = [p.strip() for p in text.split("******")]
        return "correct" if len(parts) == 2 and all(parts) and parts[0] != parts[1] else "wrong"
    return None


def main() -> None:
    rows = [json.loads(x) for x in (RUN / "calls.jsonl").open()]
    a_ids = [r["id"] for r in rows if r["phase"] == "A" and r["arm"] == "dflash2"]
    pool = {}
    for line in POOL.open():
        d = json.loads(line)
        if d.get("id") in a_ids:
            pool[d["id"]] = d
    paired, regressions = [], []
    for pid in a_ids:
        arm = {r["arm"]: r for r in rows if r["phase"] == "A" and r["id"] == pid}
        rec = {"id": pid}
        for name, r in arm.items():
            c = r["coherence"]
            v2 = D.classify_stats(c)
            rec[name] = {"v1": c["cls"], "v1_reasons": c.get("salad_reasons"), "v2": v2["cls"],
                         "v2_reasons": v2.get("reasons"), "n": c.get("n"),
                         "answer": grade(r["text_head"], pool.get(pid), c.get("finish"))}
        d, n = rec["dflash2"], rec["nodraft"]
        same = all(arm["dflash2"]["coherence"].get(k) == arm["nodraft"]["coherence"].get(k)
                   for k in ("n", "uniq", "top", "run", "words", "ascii_ok")) and \
            arm["dflash2"]["text_head"] == arm["nodraft"]["text_head"]
        rec["stats_and_head_identical"] = same
        rec["expected"] = (pool.get(pid) or {}).get("expected")
        reg = []
        if RANK[d["v2"]] > RANK[n["v2"]]:
            reg.append(f"v2 {n['v2']} -> {d['v2']}")
        if n["answer"] == "correct" and d["answer"] == "wrong":
            reg.append("answer correct -> wrong")
        rec["drafting_regression"] = reg
        if reg:
            regressions.append(pid)
        rec["v1_paired_equal"] = d["v1"] == n["v1"]
        paired.append(rec)

    gen = []
    for r in rows:
        if r["phase"] in ("B", "C") and "coherence" in r:
            v2 = D.classify_stats(r["coherence"])
            gen.append({"phase": r["phase"], "where": r.get("target", r.get("stream")), "rep": r.get("rep"),
                        "n": r["coherence"]["n"], "uniq": r["coherence"]["uniq"], "uniq_floor_v2": v2["uniq_floor"],
                        "top": r["coherence"]["top"], "run": r["coherence"]["run"],
                        "ascii_ok": r["coherence"]["ascii_ok"], "words": r["coherence"]["words"],
                        "v1": r["coherence"]["cls"], "v1_reasons": r["coherence"].get("salad_reasons"),
                        "v2": v2["cls"], "v2_reasons": v2["reasons"], "v2_soft": v2["soft"]})
    needles = [{"target": r["target"], "correct": r["correct"], "answer": r["answer"]}
               for r in rows if r["phase"] == "B" and r.get("variant") == "needle"]
    model_behaviour = [x for x in needles if not x["correct"] and "abstain" in x["answer"]]
    out = {
        "run": str(RUN), "classifier": D.V2_ID,
        "A": {"paired": paired, "drafting_regressions": regressions,
              "v1_classes_equal_per_id": sum(p["v1_paired_equal"] for p in paired),
              "stats_and_head_identical": sum(p["stats_and_head_identical"] for p in paired),
              "v2_fail_drafted": [p["id"] for p in paired if D.fails({"cls": p["dflash2"]["v2"]})],
              "graded": {p["id"]: (p["dflash2"]["answer"], p["nodraft"]["answer"], p["expected"])
                         for p in paired if p["dflash2"]["answer"] or p["nodraft"]["answer"]}},
        "BC": {"rows": gen, "v1_salad": sum(g["v1"] == "SALAD" for g in gen),
               "v2_fail": [g for g in gen if D.fails({"cls": g["v2"]})]},
        "needles": needles,
        "model_behaviour_notes": model_behaviour,
        "verdict": {
            "drafting_correctness_A_paired": "PASS" if not regressions else "FAIL",
            "degeneracy_BC_v2": "PASS (loop trigger unchecked: no token ids stored)"
            if not any(D.fails({"cls": g["v2"]}) for g in gen) else "FAIL",
            "needle": f"{sum(x['correct'] for x in needles)}/{len(needles)} correct; "
                      f"{len(model_behaviour)} model-behaviour abstention(s), unpaired (no n_max 0 needle)",
        },
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(json.dumps(out["verdict"], indent=1))
    print("A regressions:", regressions, "| v1 equal per id:", out["A"]["v1_classes_equal_per_id"],
          "| identical stats+head:", out["A"]["stats_and_head_identical"])
    print("graded:", out["A"]["graded"])
    for g in gen:
        print(g["phase"], g["where"], g["rep"], g["n"], g["uniq"], g["uniq_floor_v2"], g["top"], g["run"], g["v1"], "->", g["v2"], g["v2_soft"])
    for p in paired:
        if not p["stats_and_head_identical"]:
            print("non-identical:", p["id"], p["dflash2"]["v2"], p["nodraft"]["v2"])


if __name__ == "__main__":
    main()
