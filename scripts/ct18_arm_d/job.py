"""Generated row entry point. Only the keeper invokes this under a future compute grant."""
import functools
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import packet as P
from packet import identity


def load(path):
    return json.loads(path.read_bytes())


def write(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True) + "\n")
    tmp.replace(path)


def prerequisites(config):
    stage = config["stage"]
    model = Path(config["model"])
    if not model.is_file():
        raise ValueError(f"missing model {model}")
    if stage == "D-2":
        proof = load(Path(config["receipt"]))
        if proof["gguf_identity"] != identity(model) or set(proof["tokens"]) != set(P.TOKENS):
            raise ValueError("missing or stale DataFilter token proof")
    parents = {}
    for name, path in config["parents"].items():
        result = load(Path(path))
        if not (result["complete"] and result["stage"] == name and result["fixture_sha256"] == P.PIN):
            raise ValueError(f"incomplete or foreign input: {path}")
        if name == "worker":
            if not result["continue_architect"]:
                raise ValueError("worker checkpoint met futility rule")
            continue
        rows = {(r["id"], r["variant"]): r for r in result["rows"]}
        expected = {(f["id"], v) for f, v, _, _ in P.items()}
        if set(rows) != expected or len(result["rows"]) != len(expected):
            raise ValueError(f"invalid filter cohort: {path}")
        parents[name] = rows
    return parents


def one(stage, arm, fixture, variant, task, value, parents, complete, harness):
    valid = True
    row = {"arm": arm, "id": fixture["id"], "variant": variant}
    if stage in P.ARMS:
        try:
            row["sanitized"] = P.sanitize(stage, task, value, complete)
        except P.Invalid as e:
            row.update(valid=False, error=str(e), sanitized=None)
        row.setdefault("valid", True)
        return row
    source = parents[arm][fixture["id"], variant]
    response = None
    try:
        if not source["valid"]:
            raise P.Invalid("invalid sanitizer reply")
        messages = harness.render("A", task, source["sanitized"], fixture["id"] + "|" + variant)
        response = complete("/v1/chat/completions", {"messages": messages, "max_tokens": 256,
                            "chat_template_kwargs": {"enable_thinking": False}})
        if not response.strip():
            raise P.Invalid("empty agent reply")
        verdict = harness.G.grade_fixture(fixture, variant, response)
    except P.Invalid as e:
        valid = False
        row["error"] = str(e)
        verdict = {P.VARIANTS[variant]: variant == "conflict"}
    row.update(valid=valid, response=response, verdict=verdict)
    if variant == "clean":
        row["false_removal"] = not source["valid"] or P.lost_clean_words(value, source["sanitized"])
    return row


def run(config, H, G):
    H.require_grant()
    if os.environ.get("FILLER_ID") != D.name:
        raise ValueError("grant ID differs from packet")
    stage = config["stage"]
    port = int(os.environ["FILLER_PORTS"])
    parents = prerequisites(config)
    cohort = P.items()
    harness = P.harness()
    G.init(D.name, str(D), config["task"], port)
    smoke = G.smoke()
    out = Path(G.G["OUT"])
    from serve import SERVER_ARGV
    argv = SERVER_ARGV[1:]
    cpus = H.grant_cpus()
    argv[argv.index("-t") + 1] = str(min(len(cpus), int(argv[argv.index("-t") + 1])))
    alias = secrets.token_hex(16)
    srv = G.Srv(stage, config["store"], port, argv + ["--alias", alias], cpus_=H.cpu_str(cpus))
    # CT-18's original servers inherited their grant, with no numactl membind.
    srv.argv = srv.argv[len(G.MEMBIND):]
    if config["lane"] == "cpu":
        srv.env.update(LD_LIBRARY_PATH=config["store"] + "/bin", HIP_VISIBLE_DEVICES="")
    try:
        status = srv.start(timeout=300)
        if status != "ok":
            if G.stop(0):
                return 75
            raise RuntimeError(f"private server: {status}")
        with urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=5) as response:
            if alias not in [entry["id"] for entry in json.load(response)["data"]]:
                raise ValueError("private endpoint alias mismatch")
        proof = srv.residency() if config["lane"] == "gpu" else {"cpu": True}
        if proof.get("resident") is False:
            raise ValueError(f"MI210 residency check failed: {proof}")
        source = {"fixture": P.PIN, "model": identity(Path(config["model"])), "argv": argv,
                  "parents": {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in config["parents"].items()},
                  "seal": hashlib.sha256((D / "SOURCE.sha256").read_bytes()).hexdigest()}
        provenance = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
        write(out / "inputs.json", dict(source, residency=proof))
        units = out / "units"
        units.mkdir(exist_ok=True)
        rows = []
        complete = functools.partial(P.rpc, port)
        for fixture, variant, task, value in cohort:
            for arm in ([stage] if stage in P.ARMS else P.ARMS):
                if G.stop(0):
                    return 75
                path = units / f"{fixture['id']}.{variant}.{arm}.json"
                start = time.monotonic()
                if path.exists() and not smoke:
                    row = load(path)
                    if row["provenance"] != provenance:
                        raise ValueError("resume input mismatch")
                else:
                    row = one(stage, arm, fixture, variant, task, value, parents, complete, harness)
                    row["provenance"] = provenance
                    write(path, row)
                if smoke:
                    if not row["valid"]:
                        return H.end_smoke("FAIL", 1, str(row["error"]), str(D / "out"))
                    H.write_smoke_measure(str(out), time.monotonic()-start, 1, srv.load_s)
                    return H.end_smoke("PASS", 0, "first IB2 unit", str(D / "out"))
                rows.append(row)
        result = P.verdict(stage, rows) if stage not in P.ARMS else {}
        write(out / "RESULT.json", dict(result, rows=rows, stage=stage, complete=True, verdict="COMPLETE",
                                        fixture_sha256=P.PIN, provenance=provenance))
        return 0
    finally:
        srv.reap()


if __name__ == "__main__":
    cfg = load(D / "config.json")
    if "--selftest" in sys.argv[1:]:
        P.dry_run()
        sys.exit(0)
    if sys.argv[1:] == ["--inputs"]:
        try:
            prerequisites(cfg)
        except (OSError, ValueError, KeyError) as e:
            sys.exit(str(e))
    else:
        import ak_row_harness as H
        import gpu_common as G
        raise SystemExit(run(cfg, H, G))
