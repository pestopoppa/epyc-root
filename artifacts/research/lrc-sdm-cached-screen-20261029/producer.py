#!/usr/bin/env python3
"""One prospective P4.5 grouped diagnostic. prepare and run are separate immutable phases.

No serving quality floor is configured. The unconstrained choices in this screen
are descriptive diagnostics, not decisions or a candidate serving policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.graph_router.train_routing_classifier_kl import _train_arm  # noqa: E402

DATA = Path(
    "/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p45_soft_labels/soft_labels_embedded.npz"
)
LABELS = DATA.with_name("soft_labels.jsonl")
POOL = Path(
    "/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/pool_rebuild_a3_20260721/question_pool.PRE-A3-BACKUP-20260628-build.jsonl"
)
DATA_HASH = "eb456857e6e667bb87aaa791ba55e765ca231e0fdee58976006d7673a12351cd"
LABEL_HASH = "39e3fc21acee3f356e4ece6d5fd1baa4a01dfc546d5fc0394635e76d2a1b7112"
ROLES = [
    "frontdoor",
    "coder_escalation",
    "worker_general",
    "architect_general",
    "ingest_long_context",
    "worker_vision",
]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    with path.open("x") as f:
        json.dump(value, f, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")


def spec(path):
    return {"path": str(path), "sha256": digest(path)}


def prepare(out):
    import sklearn

    if digest(DATA) != DATA_HASH or digest(LABELS) != LABEL_HASH:
        raise ValueError("frozen cache digest mismatch")
    with np.load(DATA, allow_pickle=True) as data:
        qids = list(map(str, data["qids"]))
        suites = list(map(str, data["suites"]))
        roles = [str(row[1]) for row in data["label_map"]]
    if len(qids) != 540 or len(set(qids)) != len(qids) or roles != ROLES:
        raise ValueError("qid/semantic role inventory mismatch")
    wanted = set(qids)
    prompts = {}
    with POOL.open() as f:
        for line in f:
            item = json.loads(line)
            suite, prompt = item.get("suite"), item.get("prompt")
            if not suite or not prompt:
                continue
            qid = hashlib.sha1(f"{suite}\0{prompt}".encode("utf-8", errors="replace")).hexdigest()[
                :16
            ]
            if qid in wanted:
                if qid in prompts and prompts[qid] != prompt:
                    raise ValueError("qid collision")
                prompts[qid] = prompt
    if set(prompts) != wanted:
        raise ValueError("all qid prompts must resolve before split")
    # Near duplicates: normalized first 4096 characters; five-token shingles,
    # Jaccard >= .85; connected components across suites. Frozen without labels.
    shingles = []
    for qid in qids:
        tokens = re.findall(r"\w+", prompts[qid][:4096].lower())
        shingles.append(
            set(zip(*(tokens[i:] for i in range(5)))) if len(tokens) >= 5 else {tuple(tokens)}
        )
    parent = list(range(len(qids)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(qids)):
        for j in range(i):
            a, b = shingles[i], shingles[j]
            if min(len(a), len(b)) < 0.85 * max(len(a), len(b)):
                continue
            if len(a & b) / max(1, len(a | b)) >= 0.85:
                parent[find(i)] = find(j)
    components = defaultdict(list)
    for i in range(len(qids)):
        components[find(i)].append(i)
    by_suite = defaultdict(list)
    for rows in components.values():
        group_id = min(qids[i] for i in rows)
        stratum = min(suites[i] for i in rows)
        by_suite[stratum].append((group_id, rows))
    rng = np.random.default_rng(42)
    partition = {}
    for suite in sorted(by_suite):
        groups = sorted(by_suite[suite])
        order = rng.permutation(len(groups))
        n = len(groups)
        n_train, n_cal = int(round(0.6 * n)), int(round(0.2 * n))
        for pos, idx in enumerate(order):
            group_id, rows = groups[idx]
            part = "train" if pos < n_train else "calibration" if pos < n_train + n_cal else "test"
            for i in rows:
                partition[qids[i]] = {"group": group_id, "suite": suites[i], "split": part}
    out.mkdir(parents=True, exist_ok=False)
    sources = {
        "producer.py": Path(__file__),
        "mlp_training.py": ROOT / "scripts/graph_router/train_routing_classifier_kl.py",
        "classifier.py": ROOT / "orchestration/repl_memory/routing_classifier.py",
        "action_scorer.py": ROOT / "orchestration/repl_memory/action_outcome_scorer.py",
    }
    for name, source in sources.items():
        with (out / name).open("xb") as target:
            target.write(source.read_bytes())
    save(out / "partition.json", partition)
    save(out / "roles.json", ROLES)
    recipe = {
        "grouping": "normalized first 4096 chars; word 5-shingle Jaccard >=0.85, connected components; missing text refused; cross-suite group assigned lexicographically first suite",
        "split": "seed 42, 60/20/20 group counts within stratum, rounded",
        "mlp": {
            "epochs": 300,
            "lr": 0.01,
            "patience": 40,
            "batch_size": 64,
            "seed": 42,
            "arm": "historical P4.5 hard-label comparator",
        },
        "hgb": {
            "loss": "squared_error",
            "max_iter": 100,
            "max_leaf_nodes": 7,
            "min_samples_leaf": 20,
            "l2_regularization": 1,
            "early_stopping": False,
            "random_state": 42,
        },
        "controls": "train-only role means and observed-target shuffle seed 43",
        "support": "at least 20 observed training and 10 calibration groups per role",
        "floor": None,
        "floor_reason": "no configured serving quality-rate floor found; unconstrained argmax is descriptive only; policy abstains",
        "decision": "historical diagnostic only without a quality floor; no pilot without >=30 paired groups, >=90% outcome coverage, >=2pp gain and positive group-bootstrap 95% lower bound",
        "interval_budget": "at 30 groups worst-case independent Bernoulli 95% half-width ~17.9pp; at 108 groups ~9.4pp; a 2pp gain cannot be established with useful precision absent favorable pairing",
        "seed": 42,
        "numpy": np.__version__,
        "sklearn": sklearn.__version__,
        "python": sys.version,
        "pool_sha256": digest(POOL),
        "cache_sha256": DATA_HASH,
        "labels_sha256": LABEL_HASH,
        "source_sha256": digest(Path(__file__)),
        "scorer_sha256": digest(ROOT / "orchestration/repl_memory/action_outcome_scorer.py"),
        "mlp_source_sha256": digest(ROOT / "scripts/graph_router/train_routing_classifier_kl.py"),
        "classifier_source_sha256": digest(
            ROOT / "orchestration/repl_memory/routing_classifier.py"
        ),
    }
    staged = ROOT / "orchestration/repl_memory/routing_classifier_weights.npz"
    recipe["historical_weights_sha256"] = digest(staged) if staged.exists() else None
    save(out / "recipe.json", recipe)
    save(
        out / "manifest.json",
        {
            "cache": spec(DATA),
            "labels": spec(LABELS),
            "pool": spec(POOL),
            "partition": spec(out / "partition.json"),
            "recipe": spec(out / "recipe.json"),
            "roles": spec(out / "roles.json"),
            **{name: spec(out / name) for name in sources},
        },
    )
    print(
        "frozen",
        {
            split: sum(v["split"] == split for v in partition.values())
            for split in ("train", "calibration", "test")
        },
        "groups",
        len(components),
    )


def run(out):
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.metrics import mean_squared_error
    import sklearn

    if (out / "FIT_STARTED").exists() or (out / "TEST_OPENED").exists():
        raise ValueError("screen already started; repeat is forbidden")
    manifest = json.loads((out / "manifest.json").read_text())
    for record in manifest.values():
        if digest(Path(record["path"])) != record["sha256"]:
            raise ValueError("frozen manifest changed")
    recipe = json.loads((out / "recipe.json").read_text())
    if (
        digest(Path(__file__)) != recipe["source_sha256"]
        or sklearn.__version__ != recipe["sklearn"]
        or np.__version__ != recipe["numpy"]
        or sys.version != recipe["python"]
    ):
        raise ValueError("frozen producer or runtime changed")
    for filename, key in (
        ("scripts/graph_router/train_routing_classifier_kl.py", "mlp_source_sha256"),
        ("orchestration/repl_memory/routing_classifier.py", "classifier_source_sha256"),
        ("orchestration/repl_memory/action_outcome_scorer.py", "scorer_sha256"),
    ):
        if digest(ROOT / filename) != recipe[key]:
            raise ValueError("frozen training source changed")
    partition = json.loads((out / "partition.json").read_text())
    with np.load(DATA, allow_pickle=True) as data:
        qids = list(map(str, data["qids"]))
        suites = list(map(str, data["suites"]))
        x = np.asarray(data["X"], dtype=np.float32)
        hard = np.asarray(data["hard_labels"], dtype=int)
        roles = [str(row[1]) for row in data["label_map"]]
    if roles != ROLES or set(qids) != set(partition):
        raise ValueError("frozen mapping mismatch")
    valid = np.zeros(len(qids), dtype=bool)
    indices = {
        name: np.array(
            [i for i, qid in enumerate(qids) if partition[qid]["split"] == name], dtype=int
        )
        for name in ("train", "calibration", "test")
    }
    pretest = np.concatenate([indices["train"], indices["calibration"]])
    valid[pretest] = np.isfinite(x[pretest]).all(axis=1) & (
        np.linalg.norm(x[pretest, :1024], axis=1) > 0
    )
    train = indices["train"][valid[indices["train"]]]
    cal = indices["calibration"][valid[indices["calibration"]]]
    records = {}
    with LABELS.open() as f:
        for line in f:
            # Identify the partition without decoding held-out outcome fields.
            match = re.search(r'"qid"\s*:\s*"([^"]+)"', line)
            if not match:
                raise ValueError("missing qid")
            qid = match.group(1)
            if qid in records or qid not in partition:
                raise ValueError("duplicate or unmatched qid")
            records[qid] = line
    if set(records) != set(qids):
        raise ValueError("qid join incomplete")

    def outcomes(rows):
        y = np.full((len(rows), len(roles)), np.nan)
        mask = np.zeros_like(y, dtype=bool)
        for n, i in enumerate(rows):
            rec = json.loads(records[qids[i]])
            if rec["qid"] != qids[i]:
                raise ValueError("qid join mismatch")
            if rec["suite"] != suites[i] or "roles_seen" not in rec:
                raise ValueError("suite mismatch or missing observation mask")
            seen = rec["roles_seen"]
            if (
                len(seen) != len(set(seen))
                or set(seen) != set(rec["role_correctness"])
                or set(seen) - set(roles)
            ):
                raise ValueError("observation identity mismatch")
            for role in seen:
                k = roles.index(role)
                y[n, k] = float(rec["role_correctness"][role])
                if not np.isfinite(y[n, k]) or not 0 <= y[n, k] <= 1:
                    raise ValueError("invalid observed rate")
                mask[n, k] = True
        return y, mask

    train_y, train_seen = outcomes(train)
    cal_y, cal_seen = outcomes(cal)
    if not train_seen.any():
        raise ValueError("no observed training cells")
    eye = np.eye(len(roles), dtype=np.float32)

    def expand(xx, yy, mm):
        row, role = np.nonzero(mm)
        return np.concatenate([xx[row], eye[role]], axis=1), yy[row, role], 1 / mm.sum(axis=1)[row]

    xt, yt, wt = expand(x[train], train_y, train_seen)
    onehot = np.eye(len(roles), dtype=np.float32)
    with (out / "FIT_STARTED").open("x") as marker:
        marker.write("single fit; repeat prohibited\n")
    begin = time.monotonic()
    clf, history = _train_arm(
        x[train],
        onehot[hard[train]],
        x[cal],
        onehot[hard[cal]],
        n_actions=len(roles),
        label_map=dict(enumerate(roles)),
        epochs=300,
        lr=0.01,
        patience=40,
        batch_size=64,
        seed=42,
        arm_name="historical_p45_hard",
    )
    hgb = HistGradientBoostingRegressor(**recipe["hgb"]).fit(xt, yt, sample_weight=wt)
    shuffle = np.random.default_rng(43).permutation(yt)
    negative = HistGradientBoostingRegressor(**recipe["hgb"]).fit(xt, shuffle, sample_weight=wt)
    means = np.array(
        [np.nanmean(train_y[:, i]) if train_seen[:, i].any() else np.nan for i in range(len(roles))]
    )
    support = []
    for k in range(len(roles)):
        t = {partition[qids[train[i]]]["group"] for i in np.flatnonzero(train_seen[:, k])}
        c = {partition[qids[cal[i]]]["group"] for i in np.flatnonzero(cal_seen[:, k])}
        support.append(
            {
                "train_groups": len(t),
                "calibration_groups": len(c),
                "minimum_evidence_met": len(t) >= 20 and len(c) >= 10,
            }
        )
    cal_x, cal_target, _ = expand(x[cal], cal_y, cal_seen)
    cal_rmse = (
        float(np.sqrt(mean_squared_error(cal_target, hgb.predict(cal_x))))
        if len(cal_target)
        else None
    )
    save(
        out / "fitted.json",
        {
            "support": dict(zip(roles, support)),
            "calibration_hgb_observed_rmse": cal_rmse,
            "threshold": None,
            "quality_floor": None,
            "reason": recipe["floor_reason"],
            "mlp_epochs": len(history),
            "training_seconds": time.monotonic() - begin,
        },
    )
    # The original collection writer is fixed in source before any test outcome access.
    # Exclusive creation makes every second test opening a hard error.
    with (out / "TEST_OPENED").open("x") as marker:
        marker.write("single opening; no retuning or repeat permitted\n")
    test = indices["test"]
    valid[test] = np.isfinite(x[test]).all(axis=1) & (np.linalg.norm(x[test, :1024], axis=1) > 0)
    test_y, test_seen = outcomes(test)
    with np.load(DATA, allow_pickle=True) as cache:
        original = np.asarray(cache["correctness"], dtype=float)
    for part in (train, cal, test):
        values, observed = outcomes(part)
        if not np.allclose(original[part][observed], values[observed], atol=1e-6, rtol=0):
            raise ValueError("cache and JSONL observed correctness disagree")
    rows = []
    errors = defaultdict(list)
    for n, idx in enumerate(test):
        qid = qids[idx]
        row = {
            "item_id": qid,
            "qid": qid,
            "group_id": partition[qid]["group"],
            "suite": suites[idx],
            "status": "invalid" if not valid[idx] else "scored",
            "decisions": {},
            "observed_roles": {
                roles[j]: float(test_y[n, j]) for j in range(len(roles)) if test_seen[n, j]
            },
            "menu": [roles[j] for j, item in enumerate(support) if item["minimum_evidence_met"]],
            "costs": None,
        }
        if valid[idx]:
            flat = np.concatenate([np.repeat(x[idx][None, :], len(roles), axis=0), eye], axis=1)
            mlp = clf.forward(x[idx : idx + 1])[0][0]
            hgb_rates = hgb.predict(flat)
            neg_rates = negative.predict(flat)
            preds = {"mlp": mlp, "hgb": hgb_rates, "role_mean": means, "shuffled": neg_rates}
        else:
            preds = {
                name: np.full(len(roles), np.nan)
                for name in ("mlp", "hgb", "role_mean", "shuffled")
            }
        for name, estimates in preds.items():
            admissible = np.isfinite(estimates)
            if name in ("hgb", "shuffled"):
                admissible &= (
                    np.array([v["minimum_evidence_met"] for v in support])
                    & (estimates >= 0)
                    & (estimates <= 1)
                )
            if name == "role_mean":
                admissible &= np.array([v["minimum_evidence_met"] for v in support])
            k = (
                int(np.argmax(np.where(admissible, estimates, -np.inf)))
                if admissible.any()
                else None
            )
            observed = bool(k is not None and test_seen[n, k])
            row["decisions"][name] = {
                "role": roles[k] if k is not None else None,
                "observed": observed,
                "minimum_evidence_met": bool(k is not None and support[k]["minimum_evidence_met"]),
                "policy_supported": False,  # No declared calibration quality floor.
                "outcome": float(test_y[n, k]) if observed else None,
                "scores": [float(v) if np.isfinite(v) else None for v in estimates],
                "diagnostic_only": True,
                "policy_action": "incumbent_fallback",
            }
            if name in ("hgb", "role_mean", "shuffled"):
                for j in range(len(roles)):
                    if test_seen[n, j] and np.isfinite(estimates[j]):
                        errors[name].append((float(estimates[j]) - float(test_y[n, j])) ** 2)
        rows.append(row)
    raw = out / "decisions.jsonl"
    with raw.open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    summaries = {}
    for name in ("mlp", "hgb", "role_mean", "shuffled"):
        decisions = [r["decisions"][name] for r in rows]
        seen = [d["outcome"] for d in decisions if d["observed"]]
        summaries[name] = {
            "selected_observed": len(seen),
            "mean_selected_observed": float(np.mean(seen)) if seen else None,
            "unobserved_selected": sum(
                d["role"] is not None and not d["observed"] for d in decisions
            ),
            "abstentions": sum(d["role"] is None for d in decisions),
            "unsupported_selections": sum(
                d["role"] is not None and not d["minimum_evidence_met"] for d in decisions
            ),
            "policy_unsupported_selections": sum(
                d["role"] is not None and not d["policy_supported"] for d in decisions
            ),
        }
    pairs = [
        r for r in rows if r["decisions"]["mlp"]["observed"] and r["decisions"]["hgb"]["observed"]
    ]
    grouped = defaultdict(list)
    for row in pairs:
        grouped[row["group_id"]].append(
            row["decisions"]["hgb"]["outcome"] - row["decisions"]["mlp"]["outcome"]
        )
    groups = np.array([np.mean(v) for v in grouped.values()])
    rng = np.random.default_rng(44)
    boot = (
        np.array([rng.choice(groups, size=len(groups), replace=True).mean() for _ in range(10000)])
        if len(groups)
        else np.array([])
    )
    report = {
        "test_questions": len(rows),
        "invalid_embeddings": sum(r["status"] == "invalid" for r in rows),
        "arms": summaries,
        "raw_observed_cell_rmse": {
            name: float(np.sqrt(np.mean(errors[name]))) if errors[name] else None
            for name in ("hgb", "role_mean", "shuffled")
        },
        "raw_observed_cell_counts": {
            name: len(errors[name]) for name in ("hgb", "role_mean", "shuffled")
        },
        "mlp_rate_error": None,  # Softmax class confidence is not a correctness rate.
        "paired_questions": len(pairs),
        "paired_coverage": len(pairs) / len(rows) if rows else None,
        "paired_groups": len(groups),
        "paired_group_mean_gain": float(groups.mean()) if len(groups) else None,
        "paired_group_bootstrap_95_lower": float(np.quantile(boot, 0.025)) if len(boot) else None,
        "policy": "all challenger routes abstain; no configured rate floor",
        "disposition": "descriptive_only_no_serving_quality_floor",
    }
    save(out / "report.json", report)
    print(json.dumps(report, sort_keys=True))
    sys.path.insert(0, "/workspace/scripts/vidya")
    from adapters import research_screen
    from claim_tuple import grade
    from datetime import datetime, timezone

    raw_spec = {**spec(raw), "row_count": len(rows)}
    n_invalid = report["invalid_embeddings"]
    body = {
        "schema": research_screen.SCHEMA,
        "receipt_id": "lrc-sdm-screen-20261029",
        "run_id": "lrc-sdm-screen-20261029",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": {"kind": "historical_observed_outcome_routing", "revision": DATA_HASH},
        "producer": {"name": "screen_observed_outcomes.py", "revision": recipe["source_sha256"]},
        "input_manifest": spec(out / "manifest.json"),
        "baseline": {
            "id": "historical_p45_refit_hard_label",
            "revision": recipe["mlp_source_sha256"],
        },
        "raw_outputs": raw_spec,
        "window": {"kind": "holdout", "id": "frozen_group_test_seed42", "reason": ""},
        "counts": {
            "eligible": len(rows),
            "scored": len(rows) - n_invalid,
            "failure": 0,
            "invalid": n_invalid,
            "abstention": 0,
        },
        "rule": {
            "id": "historical_diagnostic",
            "revision": spec(out / "recipe.json")["sha256"],
            "statement": recipe["decision"],
        },
        "disposition": {"decision": "descriptive_only", "reason": recipe["floor_reason"]},
        "claim": {
            "class": "benchmark_performance",
            "metric": "paired_observed_questions",
            "value": report["paired_questions"],
            "unit": "questions",
            "direction": "higher_better",
            "category": "CANDIDATE",
            "protocol_id": "",
            "text": "Number of historical questions with both selected outcomes observed",
            "reps_basis": "valid historical test questions",
        },
        "profile": {
            "kind": "observed_outcome_routing",
            "cache": spec(DATA),
            "labels": spec(LABELS),
            "partition": spec(out / "partition.json"),
            "recipe": spec(out / "recipe.json"),
            "role_mapping": spec(out / "roles.json"),
            "raw_decisions": raw_spec,
            "producer_source": spec(out / "producer.py"),
            "pool": spec(POOL),
            "fit": spec(out / "fitted.json"),
            "report": spec(out / "report.json"),
        },
    }
    receipt = out / "run.research-screen.json"
    research_screen.write_receipt(receipt, body)
    claim = research_screen.project(research_screen.native_rows(receipt)[0])
    print("shared_grade", grade(claim))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "run"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    (prepare if args.phase == "prepare" else run)(args.output)
