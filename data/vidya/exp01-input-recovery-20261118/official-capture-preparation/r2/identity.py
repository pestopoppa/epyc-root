#!/usr/bin/env python3
"""EXP-01 validity unit: identity of every arm GGUF (size, mtime, pinned sha, arch, tensor-type histogram),
instrument support for the arch, ggml linkage rc, KT kernel strings. No weight hashing here (pinned at publish)."""
import json, os, re, subprocess, sys
from collections import Counter

modelset, ik, link_rc, kt_syms = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
sys.path.insert(0, os.path.join(ik, "gguf-py"))
env = {}
for line in open(modelset):
    m = re.match(r"\s*(?:export\s+)?([A-Z0-9_]+)=(.*)", line)
    if m:
        env[m.group(1)] = m.group(2).strip().strip('"\'')
libllama = os.path.join(ik, "build/src/libllama.so")
lib_strings = subprocess.run(["strings", libllama], capture_output=True, text=True).stdout
arms, ok, why = {}, True, []
required = env.get("REQUIRE", "Q4KM IQ4KT IQ2XXS IQ2KT").split()
for arm in ("Q4KM", "IQ4KT", "IQ2XXS", "IQ2KT"):
    p = env.get(arm, "")
    if arm not in required and not p:
        arms[arm] = {"required": False}; continue
    a = {"path": p, "sha256_pinned": env.get(arm + "_SHA", "")}
    if not p or not os.path.exists(p):
        a["exists"] = False; arms[arm] = a; ok = False; why.append(f"{arm} missing"); continue
    st = os.stat(p); a.update(exists=True, size=st.st_size, mtime=int(st.st_mtime))
    try:
        from gguf import GGUFReader
        r = GGUFReader(p)
        f = r.fields["general.architecture"]
        a["arch"] = bytes(f.parts[f.data[0]]).decode()
        a["types"] = dict(Counter(t.tensor_type.name for t in r.tensors).most_common(6))
    except Exception as x:
        a["read_error"] = str(x)[:200]; ok = False; why.append(f"{arm} unreadable")
    arch = a.get("arch")
    a["arch_supported_by_instrument"] = bool(arch) and (f"\x00{arch}\x00" in lib_strings or arch in lib_strings.split("\n"))
    if arch and not a["arch_supported_by_instrument"]:
        ok = False; why.append(f"{arm} arch {arch} unknown to instrument")
    want = {"IQ4KT": "IQ4_KT", "IQ2KT": "IQ2_KT"}.get(arm)
    if want and want not in a.get("types", {}):
        ok = False; why.append(f"{arm} has no {want} tensors (mechanism cannot fire)")
    arms[arm] = a
if link_rc != 0:
    ok = False; why.append(f"verify_ggml_linkage rc={link_rc}")
if kt_syms == 0:
    ok = False; why.append("no IQ*_KT kernel strings in instrument libggml")
commit = subprocess.run(["git", "-C", ik, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", ik, "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip()
print(json.dumps({"unit": "validity", "ok": ok, "why": why, "arms": arms, "instrument": {
    "tree": ik, "commit": commit, "tracked_dirty": bool(dirty), "linkage_rc": link_rc, "kt_kernel_strings": kt_syms,
    "fixture": env.get("FIXTURE", "0") == "1"}}))
