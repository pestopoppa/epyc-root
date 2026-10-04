#!/mnt/raid0/llm/epyc-inference-research/.venv/bin/python
"""False-positive / recall check of inf70-degeneracy.v2 vs v1 on known-coherent corpora (prefixes of
200..2000 tokens) and on synthetic degenerate streams. No inference. Writes calibrate_v2.json."""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, "/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import degeneracy as D  # noqa: E402
from length_bias import TOK, corpora  # noqa: E402

LENS = [200, 500, 1000, 1500, 2000]


def main() -> None:
    c = corpora()
    out = {"coherent": {}, "fp_examples": []}
    print(f"{'corpus':10} {'n':>5} {'docs':>4} {'v1 SALAD':>8} {'v2 DEGEN':>8}  v2 reasons")
    for name, docs in c.items():
        for n in LENS:
            v1 = v2 = tot = 0
            reasons = collections.Counter()
            for doc, s in docs:
                if len(s) < n:
                    continue
                toks = s[:n]
                text = TOK.decode(toks)
                tot += 1
                a = D.classify_v1(text, toks, "length")
                b = D.classify(text, toks, "length")
                v1 += a["cls"] == "SALAD"
                if D.fails(b):
                    v2 += 1
                    reasons.update(b["reasons"])
                    out["fp_examples"].append({"corpus": name, "doc": doc, "n": n, "reasons": b["reasons"],
                                               "loop": b["loop"], "top": b["top"], "run": b["run"]})
            if tot:
                out["coherent"][f"{name}@{n}"] = {"docs": tot, "v1_salad": v1, "v2_fail": v2, "v2_reasons": dict(reasons)}
                print(f"{name:10} {n:>5} {tot:>4} {v1:>8} {v2:>8}  {dict(reasons)}")
    Path(__file__).with_suffix(".json").write_text(json.dumps(out, indent=1))
    for e in out["fp_examples"][:15]:
        print("FP", e)


if __name__ == "__main__":
    main()
