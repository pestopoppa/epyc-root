"""Replay the four-token boundary fixture through the frozen CPU llama sampler."""

import ctypes as c
import hashlib
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE = Path("/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82")
FIXTURE = HERE.parent / "spec-filter-ties-20261126/SPEC-FILTER-TIES.json"
SEED = 3
PARAMS = {"top_k": 2, "top_p": 0.5, "min_p": 0.05, "temp": 1.0}
CHAINS = [[], ["top_k"], ["top_p"], ["min_p"], list(PARAMS),
          ["temp", "min_p", "top_p", "top_k"]]


class Token(c.Structure):
    _fields_ = [("id", c.c_int32), ("logit", c.c_float), ("p", c.c_float)]


class Candidates(c.Structure):
    _fields_ = [("data", c.POINTER(Token)), ("size", c.c_size_t),
                ("selected", c.c_int64), ("sorted", c.c_bool)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Native:
    def __init__(self):
        self.lib = c.CDLL(str(STORE / "bin/libllama.so"))
        for name, signature in {
            "greedy": [], "dist": [c.c_uint32], "top_k": [c.c_int32],
            "top_p": [c.c_float, c.c_size_t], "min_p": [c.c_float, c.c_size_t],
            "temp": [c.c_float],
        }.items():
            ctor = getattr(self.lib, "llama_sampler_init_" + name)
            ctor.argtypes, ctor.restype = signature, c.c_void_p
        self.lib.llama_sampler_apply.argtypes = [c.c_void_p, c.POINTER(Candidates)]
        self.lib.llama_sampler_free.argtypes = [c.c_void_p]
        self.lib.llama_sampler_apply.restype = self.lib.llama_sampler_free.restype = None

    def apply(self, rows, chain, selector):
        backing = (Token * len(rows))(*(Token(t, v, 0) for t, v in rows))
        cur = Candidates(backing, len(rows), -1, False)
        for op in [*chain, selector]:
            args = [PARAMS[op]] if op in PARAMS else []
            if op in ("top_p", "min_p"):
                args.append(1)
            if op == "dist":
                args.append(SEED)
            sampler = getattr(self.lib, "llama_sampler_init_" + op)(*args)
            try:
                self.lib.llama_sampler_apply(sampler, c.byref(cur))
            finally:
                self.lib.llama_sampler_free(sampler)
        assert 0 <= cur.selected < cur.size
        return [cur.data[i].id for i in range(cur.size)], cur.data[cur.selected].id, cur.data[cur.selected].p


def mass(logits, ids):
    return sum(math.exp(logits[i]) for i in ids)


def whole_tie(logits, order, chain):
    ids = list(order)
    for op in chain:
        descending = sorted(ids, key=logits.__getitem__, reverse=True)
        if op == "top_k":
            cutoff = logits[descending[min(len(ids), PARAMS[op]) - 1]]
        elif op == "top_p":
            threshold = PARAMS[op] * mass(logits, ids)
            cumulative = 0.0
            for tok in descending:
                cutoff = logits[tok]
                cumulative += math.exp(cutoff)
                if cumulative >= threshold:
                    break
        elif op == "min_p":
            cutoff = logits[descending[0]] + math.log(PARAMS[op])
        else:
            assert op == "temp" and PARAMS[op] == 1
            continue
        ids = [i for i in ids if logits[i] >= cutoff]
    return sorted(ids)


def run():
    fixture = json.loads(FIXTURE.read_text())
    probs = fixture["row"]["input_probabilities"]
    assert probs == {str(i): 0.25 for i in range(4)}
    assert SEED == fixture["key"]["fixture_rng_seed"]
    native = Native()
    mapped = {Path(line.split()[-1]) for line in Path("/proc/self/maps").read_text().splitlines()
              if "/libllama.so" in line or "/libggml" in line}
    assert len(mapped) >= 3
    expected = dict(line.split()[::-1] for line in (STORE / "SHA256SUMS").read_text().splitlines())
    hashes = {}
    for path in sorted(mapped):
        rel = str(path.relative_to(STORE))
        hashes[rel] = digest(path)
        assert hashes[rel] == expected[rel]
    cases = {
        "uniform_pit_fixture": [math.log(p) for p in probs.values()],
        "one_ulp_gap": [1, 1 + 2**-23, -2, -3],
        "wide_gap": [-1, 3, 0, -2],
        "masked_tie": [0, 0, -math.inf, -math.inf],
    }
    out = []
    for case, values in cases.items():
        logits = [c.c_float(v).value for v in values]
        for order in [[0, 1, 2, 3], [2, 1, 3, 0]]:
            rows = [(i, logits[i]) for i in order]
            greedy = native.apply(rows, [], "greedy")[1]
            assert greedy == max(order, key=logits.__getitem__)
            for chain in CHAINS:
                support, token, p = native.apply(rows, chain, "dist")
                assert (support, token, p) == native.apply(rows, chain, "dist")
                denom = mass(logits, support)
                logp = logits[token] - math.log(denom)
                assert abs(math.exp(logp) - p) < 1e-6
                reference = whole_tie(logits, order, chain)
                out.append(dict(row=case, order=order, logits=[v if math.isfinite(v) else "-inf" for v in logits],
                                filter_order=chain, raw_greedy=greedy, key={"seed": SEED, "draw_offset": 0},
                                support=support, whole_tie_reference=reference, same_support=sorted(support) == reference,
                                token=token, full_mass=mass(logits, order), retained_mass=denom,
                                full_logprob=logits[token] - math.log(mass(logits, order)), retained_logprob=logp))
    return dict(fixture_sha=digest(FIXTURE), original_test_sha=fixture["fixture_sha"]["value"],
                library_sha256=hashes, parameters=PARAMS, cases=out)


if __name__ == "__main__":
    if os.environ.get("LD_LIBRARY_PATH") != str(STORE / "bin"):
        raise SystemExit("Set LD_LIBRARY_PATH to " + str(STORE / "bin"))
    print(json.dumps(run(), indent=2, allow_nan=False))
