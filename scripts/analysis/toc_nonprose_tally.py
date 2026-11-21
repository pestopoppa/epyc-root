#!/usr/bin/env python3
"""TOC-CMP-NONPROSE-TALLY: prose vs non-prose share of context tokens introduced, per role.

Input: retained epyc.orchestrator.trajectory_event.v1 artifacts (hashes/lengths/counts only, no text).
Context tokens INTRODUCED over a trajectory, per role of the emitting turn:
  initial   = first turn's prompt_tokens (system + task + tools: PROSE/instruction)
  model     = sum completion_tokens (model-authored reasoning + code: counted as PROSE-side, not tool output)
  obs       = sum tool_output_chars / (prompt_chars/prompt_tokens of that turn)  (observation text, tokens)
Classifier rule for obs (counts only, because text is not retained in the event):
  turn with execution calls only            -> non-prose (file / shell / SQL / test output from REPL execution)
  turn with retrieval calls only            -> prose (retrieved documents / web results)
  mixed                                     -> apportioned by call count
  turn with zero recorded calls but output  -> non-prose (REPL print output with no tool-call tally; labelled `untallied`)
Duplicate files (identical sha256) are counted once.
"""
import collections, hashlib, json, sys

files = [l.strip() for l in open(sys.argv[1]) if l.strip()]
base = "/mnt/raid0/llm/"
seen, per, ntraj = set(), collections.defaultdict(lambda: collections.Counter()), collections.Counter()
for f in files:
    try:
        raw = open(base + f, "rb").read()
    except OSError:
        continue
    h = hashlib.sha256(raw).hexdigest()
    if h in seen:
        continue
    seen.add(h)
    first = {}
    for line in raw.decode(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("event") != "turn" or not e.get("prompt_tokens") or not e.get("prompt_chars"):
            continue
        role = e.get("role") or "unknown"
        first.setdefault(role, True)
        c = per[role]
        if first[role] is True:
            c["initial"] += e["prompt_tokens"]; c["traj"] += 0; ntraj[role] += 1; first[role] = False
        c["turns"] += 1
        c["model"] += e.get("completion_tokens") or 0
        tpc = e["prompt_chars"] / e["prompt_tokens"]
        obs = (e.get("tool_output_chars") or 0) / tpc
        tc = e.get("tool_calls") or {}
        ex, rt = tc.get("execution", 0), tc.get("retrieval", 0)
        if ex + rt == 0:
            c["obs_nonprose"] += obs; c["obs_untallied"] += obs
        else:
            c["obs_nonprose"] += obs * ex / (ex + rt); c["obs_prose"] += obs * rt / (ex + rt)
out = {"unique_files": len(seen), "roles": {}}
for role, c in sorted(per.items()):
    prose = c["initial"] + c["model"] + c["obs_prose"]
    tot = prose + c["obs_nonprose"]
    out["roles"][role] = {"trajectories": ntraj[role], "turns": c["turns"], "tokens_introduced": round(tot),
                          "prose_side_share": round(prose / tot, 3), "nonprose_share": round(c["obs_nonprose"] / tot, 3),
                          "of_which_untallied_obs": round(c["obs_untallied"] / tot, 3),
                          "initial": round(c["initial"]), "model": round(c["model"]),
                          "obs_nonprose": round(c["obs_nonprose"]), "obs_prose": round(c["obs_prose"])}
print(json.dumps(out, indent=1))
