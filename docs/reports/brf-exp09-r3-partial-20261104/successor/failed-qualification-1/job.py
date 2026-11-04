#!/usr/bin/env python3
"""BRF-T4-EXP09 expanded replay (24-log target; answer budget 1024): spill / evidence retention.

Arms (predeclared order: control arm over all manifest logs first -> paired readout -> interventions per log):
  control       the CURRENT REPLEnvironment._spill_output path, executed unchanged from the pinned orchestrator
                snapshot (fresh REPLEnvironment per log = first-spill path; worker llm_call role=worker n_tokens=512
                on the last 4,000 chars). Only the transport differs: llm_primitives is an adapter that sends
                prompt + "\n\n" + context_slice (LLMPrimitives' own concatenation) to OUR llama-server.
  verified_quote same 4,000-char tail input; worker returns JSON {status, quotes[], summary}; every quote is
                byte-verified against the FULL spill, status must agree with the log's exit status, a fail log needs
                failure evidence INSIDE a verified quote, summary non-empty and shorter than the span; any rejection
                fails open to the static head/tail fallback (the control's own step 3).
  shape_header  deterministic, no LLM: header + pytest summary line + FAILED/ERROR lines + first E-lines + pointer.
  pointer_only  header + pointer footer, no summary.
Each cell then runs ONE fixed answer prompt over the arm's view (the evidence selection) and is scored against gold
facts extracted from the FULL log (corpus/MANIFEST.json). Units: one JSON line per (item, arm) in out/results.jsonl,
plus preflight / paired_readout / stop records. Resume by (item, arm) identity; dry-run cells are moved aside.
Stop rules: STOP file, FILLER_DEADLINE, own cap (EXP09_CAP_S, 2700 s), validity abort (control code sha mismatch,
planted-mismatch never rejected, linkage outside the kernel store), futility (operational early stop; verified_quote cannot reach the
control's accuracy total even if every remaining log scores 1.0). Exploratory/decision-support: an early stop is an
operational decision, never a gate result.
"""
import hashlib, inspect, json, os, re, signal, subprocess, sys, time, urllib.request, uuid
from summary_flags import completion_flags, completion_record, duplicate_cell_keys, exact_failed_id_recall

B = os.environ.get("EXP09_WORKDIR", "/mnt/raid0/llm/tmp/brf-exp09-resume-r4")
OUT = f"{B}/out"
RES = f"{OUT}/results.jsonl"
SEED_RES = f"{OUT}/results.r3-native.jsonl"
DRY_RES = f"{OUT}/results.dryrun.r4.jsonl"
IDENT = json.load(open(f"{B}/identity.json"))
MAN = json.load(open(f"{B}/corpus/MANIFEST.json"))
PORT = int(IDENT["port"])
ARMS = ["control", "verified_quote", "shape_header", "pointer_only"]
EXEC_ID = uuid.uuid4().hex[:12]
DRY = os.environ.get("FILLER_DRYRUN") == "1"
T0 = time.time()
CAP = int(os.environ.get("EXP09_CAP_S", "2700"))
sys.path.insert(0, f"{B}/orch")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def emit(rec):
    rec.update(exec_id=EXEC_ID, dryrun=DRY, t=round(time.time() - T0, 1), ts=time.strftime("%FT%TZ", time.gmtime()))
    if rec.get("kind") != "cell":
        destination = f"{OUT}/run-events.r4.jsonl"
    elif DRY:
        destination = DRY_RES
    else:
        destination = RES
    with open(destination, "a") as f:
        f.write(json.dumps(rec) + "\n")
        f.flush()
        os.fsync(f.fileno())


def stop_reason():
    sf = os.environ.get("FILLER_STOPFILE", f"{B}/STOP")
    if os.path.exists(sf) or os.path.exists(f"{B}/STOP"):
        return "stopfile"
    dl = os.environ.get("FILLER_DEADLINE")
    if dl and time.time() >= int(dl):
        return "deadline"
    if time.time() - T0 >= CAP:
        return "cap"
    return None


def check():
    """Offline identity preflight: pins copied corpus, source control rows and engine inputs."""
    errs = []
    pins = json.load(open(f"{OUT}/seed-pins.json"))
    if sha(open(f"{B}/corpus/MANIFEST.json", "rb").read()) != IDENT["corpus_manifest_sha256"]:
        errs.append("corpus manifest drift")
    if sha(open(f"{B}/corpus/MANIFEST.json", "rb").read()) != pins["corpus_manifest_sha256"]:
        errs.append("seed corpus manifest drift")
    for it in MAN["items"]:
        local_sha = sha(open(it["file"], "rb").read())
        if local_sha != it["sha256"]:
            errs.append(f"corpus {it['id']} sha drift")
        if pins["control_item_sha256"].get(it["id"]) != local_sha:
            errs.append(f"seed control identity drift: {it['id']}")
    if MAN.get("corpus_sha256") != pins["preflight"].get("corpus_sha256"):
        errs.append("aggregate corpus hash differs from R3 preflight")
    seed_path = f"{OUT}/results.r3-native.jsonl"
    if sha(open(seed_path, "rb").read()) != pins["sha256"]:
        errs.append("R3 native seed sha drift")
    if os.path.exists(RES) and os.path.getsize(RES) > 0:
        errs.append("R4 treatment result_path is not empty before launch")
    if sha(open(f"{B}/orch/src/repl_environment/environment.py", "rb").read()) != IDENT["environment_py_sha256"]:
        errs.append("environment.py snapshot drift")
    if sha(open(IDENT["server_bin"], "rb").read()) != IDENT["server_bin_sha256"]:
        errs.append("llama-server binary drift")
    st = os.stat(IDENT["model"])
    if st.st_size != IDENT["model_size"]:
        errs.append("model size drift")
    if errs:
        print("CHECK FAIL: " + "; ".join(errs)); sys.exit(1)
    print("CHECK OK")


# ---------------------------------------------------------------- server
SERVER = None


def start_server():
    global SERVER
    cpus = os.environ.get("FILLER_CPUS", "0-3")
    thr = os.environ.get("FILLER_THREADS", "4")
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.path.dirname(IDENT["server_bin"])  # own ggml generation only
    env.update(IDENT["omp_env"])
    log = open(f"{OUT}/server-{EXEC_ID}.log", "w")
    cmd = ["taskset", "-c", cpus, IDENT["server_bin"], "-m", IDENT["model"], "--port", str(PORT), "--host",
           "127.0.0.1", "-t", thr, "-c", "16384", "-np", "1", "--jinja", "--chat-template-file",
           IDENT["chat_template_file"], "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--temp", "0",
           "--no-warmup"]
    SERVER = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    if os.environ.get("FILLER_PIDFILE"):
        open(os.environ["FILLER_PIDFILE"], "a").write(f"{SERVER.pid}\n")
    lib = os.environ.get("FILLER_LIB", "/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_lib.sh")
    r = subprocess.run(["bash", "-c", f'source "{lib}"; fl_wait_own_port {PORT} {SERVER.pid} 900'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("server not healthy: " + r.stdout[-300:])
    maps = open(f"/proc/{SERVER.pid}/maps").read()
    libs = sorted({l.split()[-1] for l in maps.splitlines() if "libggml" in l or "libllama" in l})
    store = os.path.realpath(os.path.dirname(IDENT["server_bin"]))
    bad = [l for l in libs if not os.path.realpath(l).startswith(store)]
    return {"pid": SERVER.pid, "cpus": cpus, "threads": thr, "cmd": cmd, "ggml_libs": libs, "linkage_ok": not bad,
            "foreign_libs": bad}


def stop_server():
    if SERVER and SERVER.poll() is None:
        SERVER.terminate()
        try:
            SERVER.wait(30)
        except subprocess.TimeoutExpired:
            SERVER.kill(); SERVER.wait(10)


def chat(text, n_tokens):
    body = json.dumps({"messages": [{"role": "user", "content": text}], "max_tokens": n_tokens, "temperature": 0,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    t = time.time()
    d = json.loads(urllib.request.urlopen(req, timeout=900).read())
    return d["choices"][0]["message"]["content"] or "", {"latency_s": round(time.time() - t, 2),
                                                          "usage": d.get("usage"), "timings": d.get("timings")}


class Adapter:  # transport only; the control's prompt/context/n_tokens come from _spill_output itself
    def __init__(self):
        self.calls = []

    def llm_call(self, prompt, context_slice="", role=None, n_tokens=512, skip_suffix=False, **kw):
        txt, meta = chat(prompt + "\n\n" + context_slice if context_slice else prompt, n_tokens)
        self.calls.append({"role": role, "n_tokens": n_tokens, "skip_suffix": skip_suffix,
                           "context_chars": len(context_slice), "prompt": prompt, **meta, "raw": txt})
        return txt


# ---------------------------------------------------------------- arms
def control_view(text, item):
    from src.repl_environment import REPLConfig, REPLEnvironment
    ad = Adapter()
    r = REPLEnvironment(context="exp09", config=REPLConfig(spill_dir=f"{OUT}/spill/{item}"), llm_primitives=ad)
    view = r._spill_output(text)
    return view, {"worker_calls": ad.calls, "fell_back": not ad.calls or ad.calls[-1]["raw"] not in view}


def head_footer(text, item):
    p = f"{OUT}/spill/{item}/full.txt"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(text)
    head = f"[Output: {len(text)} chars, {len(text.splitlines())} lines → {p}]"
    foot = f'Use peek(2000, file_path="{p}") or grep("<pattern>", file_path="{p}") to inspect.'
    return head, foot


def static_fallback(text, head, foot):
    lines = text.splitlines(); n = len(lines)
    parts = [head, "\n".join(lines[:15])]
    if n > 20:
        parts += [f"...\n[lines {n - 4}–{n}]", "\n".join(lines[-5:])]
    return "\n".join(parts + [foot])


FAILURE_EV = re.compile(r"FAILED|ERROR|Error|Exception|Traceback|assert|failed")
VQ_PROMPT = ("Summarize this program output for an agent that cannot see it. Reply with ONLY a JSON object: "
             '{"status": "pass" or "fail", "quotes": [up to 8 lines copied VERBATIM, character for character, from '
             'the output, choosing the lines that carry the result: failing test ids, error messages, final counts], '
             '"summary": "at most 5 lines"}.')


def verify_quotes(text, quotes, status, exit_status):
    ver = [q for q in quotes if isinstance(q, str) and q.strip() and q in text]
    reasons = []
    if not quotes:
        reasons.append("no-quotes")
    if len(ver) != len(quotes):
        reasons.append(f"unverified-quotes:{len(quotes) - len(ver)}")
    if status != exit_status:
        reasons.append(f"status-disagree:{status}!={exit_status}")
    if exit_status == "fail" and not any(FAILURE_EV.search(q) for q in ver):
        reasons.append("no-failure-evidence-in-quotes")
    return ver, reasons


def vq_view(text, item, gold):
    head, foot = head_footer(text, item)
    raw, meta = chat(VQ_PROMPT + "\n\n" + text[-4000:], 512)
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        obj = json.loads(m.group(0)) if m else {}
    except Exception:
        obj = {}
    quotes = obj.get("quotes") or []
    quotes = quotes if isinstance(quotes, list) else []
    summ = str(obj.get("summary") or "")
    ver, reasons = verify_quotes(text, quotes, str(obj.get("status", "")).lower(), gold["exit_status"])
    if not obj:
        reasons.append("unparseable")
    body = "Verified quotes:\n" + "\n".join(ver) + "\nSummary: " + summ
    if not summ.strip() or len(body) >= len(text):
        reasons.append("summary-empty-or-not-shorter")
    # planted mismatch: one real FAILED line with one byte flipped must be rejected by the same verifier
    real = next((l for l in text.splitlines() if l.startswith("FAILED ")), text.splitlines()[-1])
    planted = real[:-1] + ("X" if real[-1:] != "X" else "Y")
    _, p_reasons = verify_quotes(text, [planted], gold["exit_status"], gold["exit_status"])
    accepted = not reasons
    view = f"{head}\n{body}\n{foot}" if accepted else static_fallback(text, head, foot)
    return view, {"worker_calls": [{**meta, "raw": raw, "n_tokens": 512}], "quotes": quotes, "verified": ver,
                  "quote_verification_rate": round(len(ver) / len(quotes), 3) if quotes else None,
                  "reject_reasons": reasons, "accepted": accepted, "fell_back": not accepted,
                  "planted_mismatch_rejected": any(r.startswith("unverified") for r in p_reasons)}


def shape_view(text, item):
    head, foot = head_footer(text, item)
    lines = text.splitlines()
    summ = [l for l in lines if re.match(r"^=+ .*\b(failed|passed|error)", l)][-1:]
    fails = [l for l in lines if l.startswith(("FAILED ", "ERROR "))][:15]
    elines = [l for l in lines if re.match(r"^E\s+\S", l)][:6]
    body = ["[shape: pytest log]", *summ, f"[{len(fails)} FAILED/ERROR lines shown]", *fails,
            "[first E-lines]", *elines]
    return f"{head}\n" + "\n".join(body) + f"\n{foot}", {"fell_back": False, "selected_lines": len(body)}


def pointer_view(text, item):
    head, foot = head_footer(text, item)
    return f"{head}\n{foot}", {"fell_back": False}


ANSWER_PROMPT = ("You are an agent. A tool produced a long output; you only see the observation below. Answer from it. "
                 'Reply with ONLY a JSON object: {"exit_status": "pass" or "fail", "n_failed": integer or null, '
                 '"failed_ids": [failing test ids], "first_exception": "exception class name" or null, '
                 '"need_fetch": null, or a grep pattern you would run on the spill file if the observation is not '
                 'enough to answer}.\n\nObservation:\n')


def score(ans, gold, view):
    m = re.search(r"\{.*\}", ans, re.S)
    try:
        a = json.loads(m.group(0)) if m else {}
    except Exception:
        a = {}
    facts = {"exit_status": float(str(a.get("exit_status", "")).lower() == gold["exit_status"]),
             "n_failed": float(a.get("n_failed") == gold["n_failed"])}
    ids = [str(x) for x in (a.get("failed_ids") or []) if x]
    facts["failed_ids_recall"] = round(sum(any(g in i or i in g for i in ids) for g in gold["failed_ids"])
                                       / len(gold["failed_ids"]), 3)
    if gold["first_exception"]:
        facts["first_exception"] = float(gold["first_exception"].split(".")[-1]
                                         in str(a.get("first_exception") or ""))
    ret = {"n_failed": float(f"{gold['n_failed']} failed" in view),
           "failed_ids": round(sum(g in view for g in gold["failed_ids"]) / len(gold["failed_ids"]), 3)}
    if gold["first_exception"]:
        ret["first_exception"] = float(gold["first_exception"] in view)
    return {"parsed": bool(a), "facts": facts, "accuracy": round(sum(facts.values()) / len(facts), 3),
            "retention": ret, "retention_mean": round(sum(ret.values()) / len(ret), 3),
            "refetch_requested": bool(a.get("need_fetch")), "answer": a}


def run_cell(it, arm, text):
    gold = it["gold"]
    t = time.time()
    if arm == "control":
        view, ev = control_view(text, it["id"])
    elif arm == "verified_quote":
        view, ev = vq_view(text, it["id"], gold)
    elif arm == "shape_header":
        view, ev = shape_view(text, it["id"])
    else:
        view, ev = pointer_view(text, it["id"])
    t_view = time.time() - t
    ans, meta = chat(ANSWER_PROMPT + view, 1024)
    sc = score(ans, gold, view)
    exact_id_report = exact_failed_id_recall(sc.get("answer"), gold.get("failed_ids"))
    rec = {"kind": "cell", "item": it["id"], "item_sha256": it["sha256"], "arm": arm, "view": view,
           "view_chars": len(view), "evidence": ev, "view_latency_s": round(t_view, 2), "answer_raw": ans,
           "answer_meta": meta, **sc, **exact_id_report}
    emit(rec)
    # emit adds execution metadata in-place; return the same complete record so final
    # completeness/mechanism checks see the evidence that was persisted to JSONL.
    return rec


def done_cells():
    seed_sha = sha(open(SEED_RES, "rb").read())
    pins = json.load(open(f"{OUT}/seed-pins.json"))
    if seed_sha != pins["sha256"]:
        raise RuntimeError("R3 native seed sha mismatch")
    got = {}
    rows = []
    seed_controls = []
    malformed = []
    for source in (SEED_RES, RES):
        if not os.path.exists(source):
            continue
        with open(source) as stream:
            for line_no, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                except Exception:
                    malformed.append(f"{source}:{line_no}")
                    continue
                if not isinstance(row, dict):
                    malformed.append(f"{source}:{line_no}")
                    continue
                if row.get("kind") == "cell" and not row.get("dryrun"):
                    rows.append(row)
                    got[(row["item"], row["arm"])] = row
                    if source == SEED_RES and row.get("arm") == "control":
                        seed_controls.append(row)
    if len(seed_controls) != 24:
        raise RuntimeError("expected 24 pinned R3 native controls")
    for row in seed_controls:
        if pins["control_item_sha256"].get(row.get("item")) != row.get("item_sha256"):
            raise RuntimeError("seed control identity mismatch: " + str(row.get("item")))
    if sha(open(f"{B}/corpus/MANIFEST.json", "rb").read()) != pins["corpus_manifest_sha256"]:
        raise RuntimeError("seed corpus manifest changed")
    return got, duplicate_cell_keys(rows), malformed


def main():
    os.makedirs(OUT, exist_ok=True)
    if DRY and os.path.exists(DRY_RES):
        os.unlink(DRY_RES)  # each smoke starts with a fresh qualification stream
    if not DRY and os.path.exists(f"{OUT}/COMPLETE"):
        os.unlink(f"{OUT}/COMPLETE")
    got, duplicates, malformed = done_cells()
    if malformed:
        emit({"kind": "validity-abort", "reason": "malformed-native-results",
              "line_numbers": malformed,
              "decision": "REVISE (native result JSONL is not fully parseable)"})
        return 3
    if duplicates:
        emit({"kind": "validity-abort", "reason": "duplicate-native-cells", "duplicates": duplicates,
              "decision": "REVISE (duplicate cell identities in native results)"})
        return 3
    from src.repl_environment import REPLEnvironment
    import src.features as F
    fn_sha = sha(inspect.getsource(REPLEnvironment._spill_output))
    code_ok = fn_sha == IDENT["spill_output_fn_sha256"] and F.features().context_arm_ab is not True \
        and os.environ.get("ORCHESTRATOR_REPL_SPILL_ERROR_PRESERVE") != "1"
    signal.signal(signal.SIGTERM, lambda *a: (stop_server(), sys.exit(143)))
    rc = 0
    try:
        srv = start_server()
        probe, pm = chat("Reply with the single word: ready", 4)
        emit({"kind": "preflight", "control_fn_sha256": fn_sha, "control_code_unchanged": code_ok,
              "orch_pin": IDENT["orch_pin"], "server": srv, "probe": probe, "probe_meta": pm,
              "corpus_sha256": MAN["corpus_sha256"], "n_items": len(MAN["items"]), "cap_s": CAP})
        if not code_ok or not srv["linkage_ok"]:
            emit({"kind": "stop", "reason": "validity-abort", "control_code_unchanged": code_ok,
                  "linkage_ok": srv["linkage_ok"], "decision": "REVISE (control not executed unchanged)"})
            return 3
        items = MAN["items"]
        texts = {it["id"]: open(it["file"]).read() for it in items}
        plan = ([(items[0], "verified_quote")] if DRY else
                [(it, "control") for it in items] + [(it, a) for it in items for a in ARMS[1:]])
        readout_done = False
        for it, arm in plan:
            if arm != "control" and not DRY and not readout_done:
                ctrl = [got[(i["id"], "control")]["accuracy"] for i in items if (i["id"], "control") in got]
                emit({"kind": "paired_readout", "control_cells": len(ctrl),
                      "control_accuracy_mean": round(sum(ctrl) / len(ctrl), 3) if ctrl else None})
                readout_done = True
            if (it["id"], arm) in got:
                continue
            why = stop_reason()
            if why:
                emit({"kind": "stop", "reason": why, "cells_done": len(got)}); return 0
            got[(it["id"], arm)] = run_cell(it, arm, texts[it["id"]])
            if arm == "verified_quote":  # futility look after every verified_quote cell
                c_tot = sum(got[(i["id"], "control")]["accuracy"] for i in items if (i["id"], "control") in got)
                vq = [got[(i["id"], "verified_quote")]["accuracy"] for i in items if (i["id"], "verified_quote") in got]
                if len(vq) >= 4 and sum(vq) + (len(items) - len(vq)) < c_tot:
                    emit({"kind": "stop", "reason": "futility", "label": "operational decision, not a gate result",
                          "vq_sum": sum(vq), "control_total": c_tot, "vq_cells": len(vq)})
                    return 0
        summary_kind, summary = completion_record(
            got, [it["id"] for it in items], ARMS, answer_cap=1024
        )
        valid = summary_kind == "pass_complete"
        if not valid:
            emit({"kind": "validation_incomplete", **summary})
            emit({"kind": "validity-abort", "reason": "invalid-pass-completion",
                  "details": summary["validation_reasons"],
                  "decision": "REVISE (full valid comparison not captured)"})
            return 3
        fired = summary["mechanism_fired"]
        capture_complete = summary["capture_complete"]
        emit({"kind": "pass_complete", **summary})
        if not DRY:
            open(f"{OUT}/COMPLETE", "w").write(
                f"{EXEC_ID} cells={len(got)} mechanism_fired={fired} capture_complete={capture_complete}\n")
    except Exception as e:  # noqa: BLE001 - recorded, rc non-zero
        emit({"kind": "error", "error": repr(e)[:500]}); rc = 2
    finally:
        stop_server()
    return rc


if __name__ == "__main__":
    if "--check" in sys.argv:
        check(); sys.exit(0)
    sys.exit(main())
