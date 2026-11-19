#!/usr/bin/env python3
"""Rank the local-launch matrix and write ANALYSIS.md."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    data = json.loads((ROOT / "summary.json").read_text())
    rows = [r for r in data["rows"] if r.get("ok") and r.get("mean_tok_s")]
    lines = [
        "# Local launch matrix — analysis",
        "",
        f"Generated: {data.get('generated_utc')}",
        "",
        "> `cpu_code_*_28k` arms are invalid for throughput: the concatenated code prompt "
        "ended at a boundary that made the model emit EOS on the first token "
        "(`predicted_n=1`, 1e6 sentinel). They remain in `SUMMARY.md`/raw `runs/` but are "
        "excluded from the ranking below.",
        "",
    ]
    for phase in ("cpu", "gpu"):
        pr = [r for r in rows if r["phase"] == phase]
        pr.sort(key=lambda r: r["mean_tok_s"], reverse=True)
        if not pr:
            continue
        lines += [f"## {phase.upper()}", "", "| rank | arm | np | ctx | thr | KV | unified | spec | prompt_n | tok/s | mean | accept | NUMA dev% |", "|---:|---|---:|---:|---:|---|---|---|---:|---|---:|---:|---:|"]
        for i, r in enumerate(pr, 1):
            acc = (r.get("acceptance") or {}).get("alpha")
            lines.append(
                f"| {i} | {r['arm']} | {r['np']} | {r['ctx']} | {r['threads']} | {r['ctk']} | "
                f"{r['kv_unified']} | {r['spec']}"
                f"{(' n' + str(r['draft_n_max'])) if r.get('draft_n_max') else ''} | "
                f"{r['prompt_n']} | {r['tok_s']} | {r['mean_tok_s']} | {acc if acc is not None else ''} | "
                f"{r['numastat_max_dev_pct']} |"
            )
        lines.append("")
        best = pr[0]
        lines.append(
            f"Raw max (not a cross-prompt/context comparison): **{best['arm']}** at "
            f"**{best['mean_tok_s']} tok/s**. The 8k, 28k prose, 55k prose and code-prompt "
            "rows are different workloads; use the progress entry for the like-for-like calls."
        )
        lines.append("")
    (ROOT / "ANALYSIS.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
