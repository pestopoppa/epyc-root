"""No index compute: fail-closed P3 scan driver configuration."""
def analysis_env(inherited):
    env = dict(inherited)
    env.update({"GITNEXUS_WORKER_POOL_SIZE": "1",
                "GITNEXUS_PARSE_CHUNK_CONCURRENCY": "1",
                "GITNEXUS_WORKER_SUB_BATCH_TIMEOUT_MS": "120000",
                "GITNEXUS_WORKER_MAX_CUMULATIVE_TIMEOUT_MS": "600000",
                "GITNEXUS_WORKER_SUB_BATCH_MAX_BYTES": "131072"})
    return env

def impact_args(tree, symbol, source):
    return ["gitnexus", "impact", symbol, "--repo", str(tree),
            "--direction", "upstream", "--file", source]

def validate_impact(symbol, data):
    if not isinstance(data, dict) or data.get("error") or data.get("status") in ("ambiguous", "not_found") or data.get("partial") or data.get("truncated") or data.get("risk") not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        raise ValueError(f"unresolved or incomplete impact for {symbol}: {data}")
