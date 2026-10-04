#!/usr/bin/env python3
"""report.md generator for one gpu-slot-ak-20261004 results dir (re-runnable; reads only the artifacts).

Usage: slot_report.py /mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/<ts>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p3_kvu_probe_slot as P3  # noqa: E402  (a1_summary, P3V1, EXPECT, V1_REF)

KVU_LABELS = ["kvu_on_b2048", "kvu_off_b2048", "kvu_on_b512"]
ORIG = Path("/mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/kvu16b/20261004T032520Z/report.json")
# root-cause REPORT.md §1 table (v10, skip absent, -b 2048): s per 2048-token chunk by occupied cells
ORIG_CHUNK = {0: 3.81, 40000: 5.67, 80000: 7.92, 120000: 9.84, 160000: 13.21, 200000: 14.91, 240000: 17.13, 280000: 18.87}


def jl(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def f(x, nd=2, suf=""):
    if x is None:
        return "-"
    if isinstance(x, float):
        return f"{round(x, nd)}{suf}"
    return f"{x}{suf}"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    R = Path(sys.argv[1])
    run = jl(R / "slot_run.json") or {}
    arms = {lb: {"arm": jl(R / lb / "arm.json"), "rep": jl(R / lb / "replay" / "report.json"),
                 "it": jl(R / lb / "replay" / "iterations.json")} for lb in KVU_LABELS}
    L = [f"# GPU slot gpu-slot-ak-20261004: KVU-16b replay (fixed predicate) + P3v2, KVU-19a+19b build", "",
         "> **Attribution tag: every skip-ON arm is `19a+19b-combined (incl. commit 2)` (build c7f5ac9ad).** Commit 2 (WMMA seq tiles) is NOT in the KVU-19 fold (19a + commit 1 only) and regresses aligned 4x8 verify ~14%; do not attribute skip-ON numbers to the fold. Skip-OFF arms (MASK_SKIP=0 SEQ_ROWS=0) are the production-equivalent v10 path and carry the `-b 512` stack-change evidence.", "",
         f"Results `{R}`. Build dir `{run.get('bin')}`; scratch port :{run.get('port')}; budget {run.get('budget_min')} min; "
         f"value order `{run.get('order')}`; started {run.get('started_at')}, finished {run.get('finished_at')} "
         f"({run.get('elapsed_min')} min).", ""]
    a0 = next((v["arm"] for v in arms.values() if v["arm"]), None)
    if a0:
        L += [f"- server build_info `{a0.get('build_info')}`; argv source {a0.get('argv_source')}",
              f"- argv transforms: {'; '.join(a0.get('argv_transforms') or [])}", ""]
    L += ["## Timeline (value order, caps)", "", "| item | status | verdict | rc | wall min | replay cap min | note |",
          "|---|---|---|---|---|---|---|"]
    for it in run.get("items", []):
        L.append(f"| {it.get('label')} | {it.get('status')} | {f(it.get('verdict'))} | {f(it.get('rc'))} | "
                 f"{f(it.get('wall_min'))} | {f(it.get('replay_cap_min'))} | "
                 f"{it.get('reason') or ('HARD TIMEOUT' if it.get('hard_timeout_hit') else '')} |")

    # ---------------- KVU-16b summary
    L += ["", "## KVU-16b replay: 4 x ~80k staggered, fixed decoding predicate", "",
          "| metric | original (v10, no skip, b2048, broken predicate) | " + " | ".join(KVU_LABELS) + " |",
          "|---" * (len(KVU_LABELS) + 2) + "|"]
    orig = jl(ORIG) or {}

    def row(name, ov, fn):
        L.append(f"| {name} | {ov} | " + " | ".join(fn(arms[lb]) for lb in KVU_LABELS) + " |")
    row("env / -b -ub", "v10 / 2048 2048", lambda a: f"skip {(a['arm'] or {}).get('skip')} / {(a['arm'] or {}).get('b')} "
                                                   f"{(a['arm'] or {}).get('ub')}" if a["arm"] else "-")
    row("live knobs", "-", lambda a: f"{(a['arm'] or {}).get('live_env', {})}".replace("|", "/") if a["arm"] else "-")
    row("verdict", f"{orig.get('verdict')} (invalid)", lambda a: f((a["rep"] or {}).get("verdict")))
    row("wall s (capped?)", f(orig.get("wall_s")), lambda a: f"{f((a['rep'] or {}).get('wall_s'))} ({(a['rep'] or {}).get('capped')})")
    row("TTFT own-send s, req 0..3", "181.4, 343.6, 544.6, never", lambda a: f((a["rep"] or {}).get("ttft_own_send_s")))
    row("first token since t0 s", f(orig.get("first_token_s")), lambda a: f((a["rep"] or {}).get("first_token_since_t0_s")))
    row("max requests decoding at once", "3 (true; reported 4)", lambda a: f((a["rep"] or {}).get("max_requests_decoding")))
    row("max resident tokens", f(orig.get("max_resident_tokens")), lambda a: f((a["rep"] or {}).get("max_resident_tokens")))
    row("max resident while all 4 decode", "- (invalid)", lambda a: f((a["rep"] or {}).get("max_resident_with_all_decoding")))
    row("decode tok/s per req, all decoding", f(orig.get("decode_tps_per_slot_all_decoding")),
        lambda a: f((a["rep"] or {}).get("decode_tps_per_request_all_decoding")))
    row("KFD peak GiB (replay sampler)", f((orig.get("vram") or {}).get("kfd_peak_gib")),
        lambda a: f(((a["rep"] or {}).get("vram") or {}).get("kfd_peak_gib")))
    row("KFD own peak GiB (arm, 1 Hz, load..teardown)", "-", lambda a: f(((a["arm"] or {}).get("vram") or {}).get("own_pid_peak_vram_gib")))
    row("KFD own at healthy / after replay GiB", "51.69 / 58.88",
        lambda a: f"{f((a['arm'] or {}).get('kfd_at_healthy_gib'))} / {f((a['arm'] or {}).get('kfd_after_replay_gib'))}")
    row("bad log lines", f(orig.get("bad_line_counts")), lambda a: f((a["rep"] or {}).get("bad_line_counts")))
    row("request -> slot/task (log agrees?)", "i0:s1 i1:s2 i2:s3 i3:s0",
        lambda a: " ".join(f"i{m['req']}:s{m['server_slot']}/t{m['task']}{'' if m.get('agree') else '(!)'}"
                           for m in (a["rep"] or {}).get("request_slot_task_map", [])) or "-")
    row("coherence sha", "-", lambda a: f(((a["arm"] or {}).get("coherence") or {}).get("text_sha")))

    # ---------------- per-iteration seconds vs occupied cells
    L += ["", "## Seconds per server iteration (one prefill chunk) vs occupied cells", "",
          "Median s/iteration [mean chunk tokens, mean decoders] per 40k bucket of occupied cells D (prefilling slot's "
          "processed + every decoding request's prompt + generated), from the per-iteration prompt_progress events; "
          "`s/2048` normalises the chunk to 2048 tokens. Original = REPORT.md §1 (v10, no skip, b2048).", "",
          "| D (k cells) | original s/2048 | " + " | ".join(f"{lb} s/iter [chunk, dec] | {lb} s/2048" for lb in KVU_LABELS) + " |",
          "|---" * (2 + 2 * len(KVU_LABELS)) + "|"]
    bk = {}
    for lb in KVU_LABELS:
        for b in ((arms[lb]["it"] or {}).get("by_occupied") or []):
            bk.setdefault(b["occupied_lo"], {})[lb] = b
    for lo in sorted(set(bk) | set(ORIG_CHUNK)):
        cells = []
        for lb in KVU_LABELS:
            b = bk.get(lo, {}).get(lb)
            cells += [f"{b['median_s_iter']} [{b['mean_chunk']:.0f}, {b['mean_decoders']}]" if b else "-",
                      f(b["median_s_per_2048"]) if b else "-"]
        L.append(f"| {lo // 1000}-{lo // 1000 + 40} | {f(ORIG_CHUNK.get(lo))} | " + " | ".join(cells) + " |")
    L += ["", "Per-decoder decode tok/s inside each bucket (decode tokens / iteration seconds / decoders):", "",
          "| D (k cells) | " + " | ".join(KVU_LABELS) + " |", "|---" * (1 + len(KVU_LABELS)) + "|"]
    for lo in sorted(bk):
        L.append(f"| {lo // 1000}-{lo // 1000 + 40} | " + " | ".join(
            f(bk[lo][lb].get("decode_tps_per_decoder"), 3) if lb in bk[lo] else "-" for lb in KVU_LABELS) + " |")

    # ---------------- decode while a prefill runs
    L += ["", "## Per-request decode tok/s while each prefill runs (window: prefill's first progress -> its first token)", "",
          "| arm | prefilling req | window s | iterations | prefill tok/s | median s/iter | decode tok/s per decoding req | sum |",
          "|---|---|---|---|---|---|---|---|"]
    for lb in KVU_LABELS:
        for p in ((arms[lb]["it"] or {}).get("per_prefill") or []):
            L.append(f"| {lb} | i={p['req']}{'' if p.get('completed') else ' (cut by cap)'} | {p['window_s']} | {p['iterations']} | "
                     f"{p['prefill_tps']} | {f(p.get('median_s_iter'))} | "
                     f"{', '.join(f'i{k}: {v}' for k, v in (p.get('decode_tps_while_prefilling') or {}).items()) or '-'} | "
                     f"{f(p.get('decode_tps_sum'), 3)} |")
    L.append("")
    L.append("Original (v10, no skip, b2048; REPORT.md §1): decoders summed 0.46 (i=1 prefill), 0.54 (i=2), 0.56 tok/s (i=3); "
             "prefill 440/232/146/115 tok/s for i=0..3.")

    # ---------------- ratios vs the root-cause predictions
    def last_common(l1, l2):
        b1 = {b["occupied_lo"]: b for b in ((arms[l1]["it"] or {}).get("by_occupied") or [])}
        b2 = {b["occupied_lo"]: b for b in ((arms[l2]["it"] or {}).get("by_occupied") or [])}
        com = sorted(set(b1) & set(b2))
        return (com[-1], b1[com[-1]], b2[com[-1]]) if com else None
    L += ["", "## Against the root-cause predictions (REPORT.md §4)", ""]
    c = last_common("kvu_off_b2048", "kvu_on_b2048")
    if c:
        lo, off, on = c
        L.append(f"- skip OFF/ON s per 2048 at D {lo // 1000}-{lo // 1000 + 40}k: {off['median_s_per_2048']} / "
                 f"{on['median_s_per_2048']} = {off['median_s_per_2048'] / max(1e-9, on['median_s_per_2048']):.2f}x "
                 "(predicted ~3.5x for KVU-19a alone at the i=3 end state)")
    c = last_common("kvu_on_b2048", "kvu_on_b512")
    if c:
        lo, b2, b5 = c
        L.append(f"- ON b2048 vs ON b512 s/iteration at D {lo // 1000}-{lo // 1000 + 40}k: {b2['median_s_iter']} / "
                 f"{b5['median_s_iter']} = {b2['median_s_iter'] / max(1e-9, b5['median_s_iter']):.2f}x shorter iterations; "
                 f"decode per decoder {b2.get('decode_tps_per_decoder')} vs {b5.get('decode_tps_per_decoder')} tok/s "
                 "(predicted ~4x decode while prefilling from -b 512; prefill rate roughly unchanged at depth)")
    for lb in KVU_LABELS:
        pp = {p["req"]: p for p in ((arms[lb]["it"] or {}).get("per_prefill") or [])}
        if 3 in pp:
            L.append(f"- {lb}: decode sum while i=3 prefills {pp[3].get('decode_tps_sum')} tok/s (original 0.56)")
    L.append("- VRAM: the original grew from 51.69 GiB at load to 58.88 under concurrent prefill+decode (REPORT.md §3); "
             "compare 'KFD own at healthy / after replay' and 'KFD own peak' above, and the -lv 4 breakdown below.")

    # ---------------- memory
    L += ["", "## Memory (-lv 4): load-time buffers and the exit breakdown", ""]
    for lb in KVU_LABELS:
        a = arms[lb]["arm"]
        if not a:
            continue
        m = a.get("memory_lines") or {}
        L += [f"### {lb}", "", "```"] + [ln.split(" ", 1)[-1] for ln in (m.get("breakdown") or [])[:16]] + \
             [f"(load lines {len(m.get('load') or [])}; growth/pool debug lines {m.get('growth_debug_total')})", "```", ""]

    # ---------------- coherence
    L += ["## Coherence spot-checks (greedy, enable_thinking=false; text saved, no classifier)", "",
          "| launch | sha | finish | tokens | text (first 160 chars) |", "|---|---|---|---|---|"]
    cohs = sorted(R.glob("*/coherence.json")) + sorted(R.glob("p3v2/*/coherence.json"))
    shas = {}
    for p in cohs:
        cj = jl(p) or {}
        lab = str(p.parent.relative_to(R))
        shas.setdefault(cj.get("text_sha"), []).append(lab)
        txt = (cj.get("content_text") or cj.get("error") or "").replace("\n", " ").replace("|", "/")[:160]
        L.append(f"| {lab} | {cj.get('text_sha')} | {cj.get('finish')} | {cj.get('predicted_n')} | {txt} |")
    L += ["", f"- identical-text groups: {json.dumps({k: v for k, v in shas.items()})}", ""]

    # ---------------- P3v2
    pdirs = sorted((R / "p3v2").glob("pair*_*")) if (R / "p3v2").exists() else []
    L += ["## P3v2 A1 (L0_base -> L3 ~355k with 3 parked neighbours -> L0_after), ON vs OFF", ""]
    if not pdirs:
        L.append("- not run (budget) — see the timeline.")
    else:
        cols = [("v1 (v10 ffc1bac82)", P3.a1_summary(P3.P3V1 / "a1.json"))] + \
               [(d.name, P3.a1_summary(d / "a1.json")) for d in pdirs]
        L += ["| metric | " + " | ".join(c[0] for c in cols) + " |", "|---" * (len(cols) + 1) + "|"]

        def prow(lab, fn):
            L.append(f"| {lab} | " + " | ".join(fn(c[1] or {}) for c in cols) + " |")
        prow("status / build", lambda a: f"{a.get('status')} / {a.get('build')}")
        prow("L3 fill tokens", lambda a: f(a.get("fill_L3")))
        for v in ("drafted", "nodraft"):
            prow(f"L0 base {v} tok/s", lambda a, v=v: f(a.get(f"base.{v}")))
            prow(f"**L3 {v} tok/s**", lambda a, v=v: f((a.get("tab") or {}).get(f"L3.{v}")))
            prow(f"L3 loss vs L0 {v}", lambda a, v=v: f(a.get(f"loss_L3.{v}"), suf="%"))
            prow(f"ABA drift {v}", lambda a, v=v: f(a.get(f"aba.{v}"), suf="%"))
        prow("L3 nodraft text sha", lambda a: f((a.get("tab") or {}).get("L3.nodraft.sha")))
        prow("VRAM own peak GiB", lambda a: f(a.get("vram_own_peak_gib")))
        prow("live knobs", lambda a: f"{a.get('live_env')}".replace("|", "/"))
        on = [c[1] for c in cols[1:] if c[0].endswith("_on") and c[1]]
        off = [c[1] for c in cols[1:] if c[0].endswith("_off") and c[1]]
        for v in ("nodraft", "drafted"):
            xo = [(a.get("tab") or {}).get(f"L3.{v}") for a in on]
            xf = [(a.get("tab") or {}).get(f"L3.{v}") for a in off]
            xo, xf = [x for x in xo if x], [x for x in xf if x]
            if xo and xf:
                L.append(f"- L3 {v}: ON mean {sum(xo) / len(xo):.2f} vs OFF mean {sum(xf) / len(xf):.2f} tok/s = "
                         f"{(sum(xo) / len(xo)) / (sum(xf) / len(xf)):.2f}x (expect ON >= {P3.EXPECT.get('L3_' + v + '_min')}; "
                         f"v1 {P3.V1_REF.get('L3_' + v)}; KVU-19b target: L3 loss < 10%)")
    (R / "report.md").write_text("\n".join(L) + "\n")
    print(f"wrote {R / 'report.md'} ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
