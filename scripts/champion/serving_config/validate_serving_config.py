#!/usr/bin/env python3
"""validate_serving_config.py - validator for the champion serving-config artifact (CHAMPION-SERVING-CONFIG-1).

Schema id: epyc.champion.serving_config.v1
Policy:    docs/reference/kernel-manifests/README.md, "Champion serving config".
Artifact:  docs/reference/kernel-manifests/serving-configs/<champion>.serving-config.json

Document shape (all keys required unless marked optional):
  schema            "epyc.champion.serving_config.v1"
  champion          e.g. "C22"
  generated_utc     ISO-8601 UTC
  notes             optional str
  servers[]         one per served model + role
    server_mode     registry key under server_mode.* (e.g. "architect_critic")
    port            int
    model           served model id
    device          str
    registry_serving_shape   dict: the registry serving_shape the argv deltas are taken against
    registry_runtime         dict {slots, ctx_checkpoints, cache_ram}: the server_mode record's own runtime knobs
                             (not in serving_shape), compared against config.np / ctx_checkpoints / cache_ram_mib
                             (required for a measured optimal; drift-checked under --registry)
    optimal         {status, provenance, ...}
        status "measured": config{}, argv_delta[], screen_state, provenance{}
        status "pending" : pending_reason, row_id (or needs_row), NO result_sha256, NO numbers
    alternates[]    0..3 named configs, same entry shape plus name (a "measured" optimal needs >= 2).
                    argv_delta rows are {flag, value, reason}: a flag in BARE_FLAGS carries no value, every other
                    flag REQUIRES one (typed per flag; `|` and whitespace are rejected; a temperature flag is 0-1.0,
                    operator 2026-11-24: no high-temperature testing). A pending entry's intended_delta may list
                    sweep arms as a list value.
    tradeoffs[]     rows {id, config, throughput_tok_s, itl_p50_ms, itl_p95_ms, temperature, acceptance,
                    memory_gib, unmeasured{field: reason}, provenance{}}; a null metric needs a reason
    evidence[]      optional rows that informed a pending entry: {row_id, result_json, result_sha256, verdict}

Provenance (non-pending): row_id, result_json (absolute path), result_sha256 (64 hex), store (path).
If the result_json exists on this host its sha256 is recomputed and must match (a mismatch is an error;
a missing file is a warning, or an error under --strict-files; every programmatic caller -- package.sh and
serving_config_registry.py -- validates with strict_files=True, so a missing RESULT.json fails a promotion). An entry whose row has no filed RESULT.json
must be "pending"; pending entries carry the row id and never a sha or a metric (no invented numbers).

Exit 0 = valid, 1 = invalid, 2 = usage/IO error.

Usage:
  python3 -I scripts/champion/serving_config/validate_serving_config.py [--strict-files] [--registry PATH] FILE...
"""
import argparse
import hashlib
import json
import os
import re
import sys

SCHEMA = "epyc.champion.serving_config.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CONFIG_KEYS = ("n_ctx", "np", "batch", "ubatch", "kv_k", "kv_v", "kv_unified", "ctx_checkpoints",
               "cache_ram_mib", "drafter", "sampling")
DRAFTER_KEYS = ("spec_type", "model", "n_max")
SAMPLING_KEYS = ("temperature", "top_p", "top_k")
TRADEOFF_METRICS = ("throughput_tok_s", "itl_p50_ms", "itl_p95_ms", "temperature", "acceptance", "memory_gib")
STATUSES = ("measured", "pending")
# registry serving_shape field -> (config key, argv flags that may legitimately override it in argv_delta)
SHAPE_MAP = {
    "n_ctx": ("n_ctx", ("-c", "--ctx-size")),
    "batch": ("batch", ("-b", "--batch-size")),
    "ubatch": ("ubatch", ("-ub", "--ubatch-size")),
    "kv_unified": ("kv_unified", ("--kv-unified", "--no-kv-unified")),
}
# server_mode.<role> record fields that are NOT in serving_shape but are still compared (the registry diff
# writes them: np -> slots, ctx_checkpoints, cache_ram_mib -> cache_ram). The artifact carries a snapshot of
# them as `registry_runtime`; with --registry that snapshot is drift-checked against the live record.
# registry runtime field -> (config key, argv flags that may legitimately override it)
RUNTIME_MAP = {
    "slots": ("np", ("-np", "--parallel")),
    "ctx_checkpoints": ("ctx_checkpoints", ("--ctx-checkpoints", "-ctxcp")),
    "cache_ram": ("cache_ram_mib", ("--cache-ram", "-cram")),
}
# argv_delta flag classes. A flag is a bare switch only if listed in BARE_FLAGS; every other flag takes a
# value, so an unknown flag fails closed (an argv_delta without its value is a signable no-op or a
# silently-true knob). Keep in sync with the orchestrator's src/registry/serving_alternates.py
# (parity-tested there).
BARE_FLAGS = frozenset((
    "--kv-unified", "-kvu", "--no-kv-unified", "--no-warmup", "--no-mmap", "--mlock", "--cont-batching",
    "--no-cont-batching", "--jinja", "--no-context-shift", "--swa-full", "-nkvo", "--no-kv-offload"))
INT_FLAGS = frozenset((
    "-c", "--ctx-size", "-b", "--batch-size", "-ub", "--ubatch-size", "-np", "--parallel",
    "--ctx-checkpoints", "-ctxcp", "--cache-ram", "-cram", "-t", "--threads", "-ngl", "--n-gpu-layers",
    "--draft-max", "--draft-min", "--spec-draft-n-max", "-n", "--predict", "--top-k"))
FLOAT_FLAGS = frozenset(("--temp", "--temperature", "--top-p", "--min-p"))
TEMP_FLAGS = frozenset(("--temp", "--temperature"))
#: operator 2026-11-24: no high-temperature testing; the temperature alternate is low-temperature, T 0-0.6.
MAX_TEMPERATURE = 1.0


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, where, msg):
        self.errors.append("%s: %s" % (where, msg))

    def warn(self, where, msg):
        self.warnings.append("%s: %s" % (where, msg))


def check_provenance(p, where, rep, strict_files, require_store=True):
    if not isinstance(p, dict):
        rep.err(where, "provenance must be an object")
        return
    for k in ("row_id", "result_json", "result_sha256") + (("store",) if require_store else ()):
        if not isinstance(p.get(k), str) or not p.get(k):
            rep.err(where, "provenance.%s required (non-empty string)" % k)
    sha, path = p.get("result_sha256"), p.get("result_json")
    if isinstance(sha, str) and not HEX64.match(sha):
        rep.err(where, "provenance.result_sha256 is not 64 lowercase hex")
    if isinstance(path, str) and path:
        if not os.path.isabs(path) or not path.endswith("RESULT.json"):
            rep.err(where, "provenance.result_json must be an absolute path ending in RESULT.json")
        elif os.path.isfile(path):
            if isinstance(sha, str) and HEX64.match(sha) and sha256_file(path) != sha:
                rep.err(where, "provenance.result_sha256 does not match the file on disk: " + path)
        else:
            (rep.err if strict_files else rep.warn)(where, "result_json not present on this host: " + path)


def check_pending(e, where, rep):
    if e.get("status") != "pending":
        return
    if not (isinstance(e.get("row_id"), str) and e.get("row_id")) and not (
            e.get("row_id") is None and isinstance(e.get("needs_row"), str) and e.get("needs_row")):
        rep.err(where, "pending entry needs row_id, or row_id null plus a needs_row explanation")
    if not isinstance(e.get("pending_reason"), str) or not e.get("pending_reason"):
        rep.err(where, "pending entry needs pending_reason")
    for k in ("result_sha256", "result_json", "config", "provenance") + TRADEOFF_METRICS:
        if k in e:
            rep.err(where, "pending entry must not carry '%s' (no RESULT.json filed, nothing measured)" % k)


def check_config(c, where, rep):
    if not isinstance(c, dict):
        rep.err(where, "config must be an object")
        return
    for k in CONFIG_KEYS:
        if k not in c:
            rep.err(where, "config.%s required" % k)
    for k in ("n_ctx", "np", "batch", "ubatch", "ctx_checkpoints", "cache_ram_mib"):
        if k in c and not (isinstance(c[k], int) and not isinstance(c[k], bool) and c[k] > 0):
            rep.err(where, "config.%s must be a positive integer" % k)
    if "kv_unified" in c and not isinstance(c["kv_unified"], bool):
        rep.err(where, "config.kv_unified must be boolean")
    for k in ("kv_k", "kv_v"):
        if k in c and not isinstance(c[k], str):
            rep.err(where, "config.%s must be a string (e.g. q8_0)" % k)
    d = c.get("drafter")
    if isinstance(d, dict):
        for k in DRAFTER_KEYS:
            if k not in d:
                rep.err(where, "config.drafter.%s required (null when no drafter)" % k)
    elif "drafter" in c:
        rep.err(where, "config.drafter must be an object")
    s = c.get("sampling")
    if isinstance(s, dict):
        for k in SAMPLING_KEYS:
            if not _num(s.get(k)):
                rep.err(where, "config.sampling.%s must be a number" % k)
    elif "sampling" in c:
        rep.err(where, "config.sampling must be an object")


def _token_problem(v):
    """Why a string cannot be one argv token (`|` is sweep notation, whitespace splits a token), or None."""
    if "|" in v:
        return "contains '|' (a sweep is not a value: use a list under intended_delta, or one entry per arm)"
    if any(c.isspace() for c in v):
        return "contains whitespace (an argv value is a single token)"
    return None


def check_flag_value(flag, d, where, rep, allow_list=False):
    """A value-taking flag requires a value of its type; a bare switch carries none (or `true`)."""
    has = "value" in d
    v = d.get("value")
    if flag in BARE_FLAGS:
        if has and v is not True:
            rep.err(where, "%s is a bare switch: omit 'value' (or use true), got %r" % (flag, v))
        return
    if not has or v is None or isinstance(v, bool):
        rep.err(where, "%s takes a value: 'value' is required (got %s)" % (flag, "none" if not has else repr(v)))
        return
    vals = v if isinstance(v, list) else [v]
    if isinstance(v, list) and (not allow_list or not v):
        rep.err(where, "%s value must be a scalar (a list of sweep arms is allowed only in intended_delta)" % flag)
        return
    for x in vals:
        if isinstance(x, bool) or x is None or not isinstance(x, (str, int, float)):
            rep.err(where, "%s value %r must be a number or a string token" % (flag, x))
            continue
        if isinstance(x, str):
            bad = _token_problem(x)
            if bad:
                rep.err(where, "%s value %r %s" % (flag, x, bad))
                continue
            if not x:
                rep.err(where, "%s value must not be empty" % flag)
                continue
        if flag in INT_FLAGS:
            ok = (isinstance(x, int) or (isinstance(x, str) and re.fullmatch(r"-?[0-9]+", x))) and int(x) >= (
                -1 if flag in ("-ngl", "--n-gpu-layers") else 0)
            if not ok:
                rep.err(where, "%s value %r must be an integer" % (flag, x))
        elif flag in FLOAT_FLAGS:
            try:
                f = float(x)
            except (TypeError, ValueError):
                rep.err(where, "%s value %r must be a number" % (flag, x))
                continue
            if flag in TEMP_FLAGS and not 0 <= f <= MAX_TEMPERATURE:
                rep.err(where, "%s value %r outside 0-%s (no high-temperature testing, operator 2026-11-24)"
                        % (flag, x, MAX_TEMPERATURE))
            elif f < 0:
                rep.err(where, "%s value %r must be non-negative" % (flag, x))


def check_argv_delta(delta, where, rep, allow_list=False):
    if not isinstance(delta, list):
        rep.err(where, "argv_delta must be a list (empty when identical to the registry)")
        return
    for i, d in enumerate(delta):
        if not isinstance(d, dict) or not isinstance(d.get("flag"), str) or not d["flag"].startswith("-"):
            rep.err(where, "argv_delta[%d] needs a 'flag' starting with '-'" % i)
            continue
        w = "%s[%d](%s)" % (where, i, d["flag"])
        if "reason" not in d:
            rep.err(where, "argv_delta[%d] (%s) needs a reason" % (i, d.get("flag")))
        if _token_problem(d["flag"]):
            rep.err(w, "flag %s" % _token_problem(d["flag"]))
            continue
        check_flag_value(d["flag"], d, w, rep, allow_list=allow_list)


def check_against_shape(entry, shape, where, rep, runtime=None):
    """Config fields that differ from the registry serving_shape (or, for np / ctx_checkpoints / cache_ram,
    from the registry runtime record) must be explained by an argv_delta flag."""
    cfg, delta = entry.get("config") or {}, entry.get("argv_delta") or []
    flags = {d.get("flag") for d in delta if isinstance(d, dict)}
    for skey, (ckey, fl) in SHAPE_MAP.items():
        if skey in shape and ckey in cfg and shape[skey] != cfg[ckey] and not (flags & set(fl)):
            rep.err(where, "config.%s=%r differs from registry serving_shape.%s=%r with no argv_delta flag %s"
                    % (ckey, cfg[ckey], skey, shape[skey], "/".join(fl)))
    for rkey, (ckey, fl) in RUNTIME_MAP.items():
        if isinstance(runtime, dict) and rkey in runtime and ckey in cfg and runtime[rkey] != cfg[ckey] \
                and not (flags & set(fl)):
            rep.err(where, "config.%s=%r differs from registry runtime %s=%r with no argv_delta flag %s"
                    % (ckey, cfg[ckey], rkey, runtime[rkey], "/".join(fl)))
    kq = (shape or {}).get("kv_quant") or {}
    for side, flag in (("k", "-ctk"), ("v", "-ctv")):
        if side in kq and ("kv_" + side) in cfg and kq[side] != cfg["kv_" + side] and flag not in flags:
            rep.err(where, "config.kv_%s=%r differs from registry serving_shape.kv_quant.%s=%r with no %s delta"
                    % (side, cfg["kv_" + side], side, kq[side], flag))


def check_entry(e, where, rep, shape, strict_files, alt=False, runtime=None):
    if not isinstance(e, dict):
        rep.err(where, "entry must be an object")
        return
    if e.get("status") not in STATUSES:
        rep.err(where, "status must be one of %s" % (STATUSES,))
        return
    if alt and not (isinstance(e.get("name"), str) and e.get("name")):
        rep.err(where, "alternate needs a name")
    if e["status"] == "pending":
        check_pending(e, where, rep)
        if "intended_delta" in e:
            check_argv_delta(e["intended_delta"], where + ".intended_delta", rep, allow_list=True)
        return
    check_config(e.get("config"), where, rep)
    check_argv_delta(e.get("argv_delta"), where, rep)
    if isinstance(shape, dict) and isinstance(e.get("config"), dict):
        check_against_shape(e, shape, where, rep, runtime)
    check_provenance(e.get("provenance"), where, rep, strict_files)


def check_tradeoff(t, where, rep, names, strict_files):
    if not isinstance(t, dict):
        rep.err(where, "tradeoff row must be an object")
        return
    if not isinstance(t.get("id"), str):
        rep.err(where, "tradeoff row needs an id")
    cref = t.get("config")
    if not isinstance(cref, str) or not (cref in names or cref.startswith("evidence:")):
        rep.err(where, "tradeoff.config %r must be 'optimal', an alternate name, or 'evidence:<label>'" % (cref,))
    elif cref in names and names[cref] != "measured":
        rep.err(where, "tradeoff row references pending config %r (no numbers for a pending entry)" % cref)
    unm = t.get("unmeasured") or {}
    for m in TRADEOFF_METRICS:
        if m not in t:
            rep.err(where, "tradeoff.%s required (number, or null with an unmeasured reason)" % m)
            continue
        v = t[m]
        if v is None:
            if not (isinstance(unm.get(m), str) and unm[m]):
                rep.err(where, "tradeoff.%s is null without an unmeasured['%s'] reason" % (m, m))
        elif not _num(v) or v < 0:
            rep.err(where, "tradeoff.%s must be a non-negative number or null" % m)
    a = t.get("acceptance")
    if _num(a) and a > 1:
        rep.err(where, "tradeoff.acceptance must be in [0, 1]")
    check_provenance(t.get("provenance"), where, rep, strict_files)


def validate(doc, strict_files=False, registry=None):
    rep = Report()
    if not isinstance(doc, dict):
        rep.err("$", "document must be an object")
        return rep
    if doc.get("schema") != SCHEMA:
        rep.err("$", "schema must be %r" % SCHEMA)
    for k in ("champion", "generated_utc"):
        if not isinstance(doc.get(k), str) or not doc.get(k):
            rep.err("$", "%s required" % k)
    servers = doc.get("servers")
    if not isinstance(servers, list) or not servers:
        rep.err("$", "servers must be a non-empty list")
        return rep
    seen = set()
    for i, s in enumerate(servers):
        w = "servers[%d]" % i
        if not isinstance(s, dict):
            rep.err(w, "must be an object")
            continue
        w = "servers[%d](%s)" % (i, s.get("server_mode"))
        for k in ("server_mode", "model", "device"):
            if not isinstance(s.get(k), str) or not s.get(k):
                rep.err(w, "%s required" % k)
        if not isinstance(s.get("port"), int):
            rep.err(w, "port must be an integer")
        key = (s.get("server_mode"), s.get("port"))
        if key in seen:
            rep.err(w, "duplicate (server_mode, port)")
        seen.add(key)
        shape = s.get("registry_serving_shape")
        if not isinstance(shape, dict):
            rep.err(w, "registry_serving_shape (object) required")
            shape = None
        elif registry is not None:
            live = (registry.get("server_mode") or {}).get(s.get("server_mode"), {}).get("serving_shape")
            if live is None:
                rep.err(w, "registry has no server_mode.%s.serving_shape" % s.get("server_mode"))
            elif live != shape:
                rep.err(w, "registry_serving_shape drifted from the live registry serving_shape")
        opt = s.get("optimal")
        measured = isinstance(opt, dict) and opt.get("status") == "measured"
        runtime = s.get("registry_runtime")
        if runtime is None:
            if measured:
                rep.err(w, "registry_runtime (object: slots, ctx_checkpoints, cache_ram) required for a measured "
                           "optimal: np / ctx_checkpoints / cache_ram are compared against it")
        elif not isinstance(runtime, dict) or any(
                not (isinstance(runtime.get(k), int) and not isinstance(runtime.get(k), bool) and runtime[k] >= 0)
                for k in RUNTIME_MAP):
            rep.err(w, "registry_runtime must be an object with non-negative integers %s" % (sorted(RUNTIME_MAP),))
            runtime = None
        elif registry is not None:
            rec = (registry.get("server_mode") or {}).get(s.get("server_mode"), {})
            for k in RUNTIME_MAP:
                if rec.get(k) != runtime[k]:
                    rep.err(w, "registry_runtime.%s=%r drifted from the live registry server_mode.%s.%s=%r"
                            % (k, runtime[k], s.get("server_mode"), k, rec.get(k)))
        check_entry(opt, w + ".optimal", rep, shape, strict_files, runtime=runtime)
        names = {"optimal": opt.get("status") if isinstance(opt, dict) else None}
        alts = s.get("alternates")
        if not isinstance(alts, list):
            rep.err(w, "alternates must be a list")
            alts = []
        if len(alts) > 3:
            rep.err(w, "at most 3 alternates")
        if isinstance(opt, dict) and opt.get("status") == "measured" and len(alts) < 2:
            rep.err(w, "a measured optimal needs 2-3 named alternates (latency, throughput, low-temperature)")
        for j, a in enumerate(alts):
            check_entry(a, "%s.alternates[%d]" % (w, j), rep, shape, strict_files, alt=True, runtime=runtime)
            if isinstance(a, dict):
                n = a.get("name")
                if n in names or n == "optimal":
                    rep.err(w, "duplicate alternate name %r" % n)
                names[n] = a.get("status")
        tos = s.get("tradeoffs")
        if not isinstance(tos, list):
            rep.err(w, "tradeoffs must be a list")
            tos = []
        if isinstance(opt, dict) and opt.get("status") == "measured" and not tos:
            rep.err(w, "a measured optimal needs at least one tradeoffs row")
        tids = set()
        for j, t in enumerate(tos):
            check_tradeoff(t, "%s.tradeoffs[%d]" % (w, j), rep, names, strict_files)
            if isinstance(t, dict):
                if t.get("id") in tids:
                    rep.err(w, "duplicate tradeoff id %r" % t.get("id"))
                tids.add(t.get("id"))
        for j, ev in enumerate(s.get("evidence") or []):
            check_provenance(ev, "%s.evidence[%d]" % (w, j), rep, strict_files, require_store=False)
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--strict-files", action="store_true", help="a missing RESULT.json on this host is an error")
    ap.add_argument("--registry", help="orchestrator model_registry.yaml: also check registry_serving_shape for drift")
    a = ap.parse_args(argv)
    registry = None
    if a.registry:
        try:
            import yaml
            with open(a.registry) as f:
                registry = yaml.safe_load(f)
        except Exception as ex:  # noqa: BLE001
            print("cannot load registry %s: %s" % (a.registry, ex), file=sys.stderr)
            return 2
    rc = 0
    for p in a.files:
        try:
            with open(p) as f:
                doc = json.load(f)
        except (OSError, ValueError) as ex:
            print("%s: cannot read/parse: %s" % (p, ex), file=sys.stderr)
            return 2
        rep = validate(doc, a.strict_files, registry)
        for m in rep.warnings:
            print("WARN  %s: %s" % (p, m))
        for m in rep.errors:
            print("ERROR %s: %s" % (p, m))
        print("%s: %s (%d error(s), %d warning(s))" % (p, "INVALID" if rep.errors else "OK", len(rep.errors), len(rep.warnings)))
        if rep.errors:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
