#!/usr/bin/env python3
"""P4.5 Phase B step 2: KL-divergence soft-label training vs hard-label baseline.

Trains the production RoutingClassifier architecture two ways on the SAME
train/val split built from the journal soft-label dataset:

  - HARD arm: standard cross-entropy against argmax(soft_labels) — the
    winner-take-all role per question. This is the P4.5 baseline.
  - SOFT arm: KL divergence against the full soft label distribution
    (Fugu Stage 1 analog). For a softmax head the logit gradient is simply
    (probs - target), so swapping the one-hot for the soft target is the
    only change — same forward pass, same optimizer, same split.

Decision gate (P4.5): adopt soft labels if SOFT val "role-success accuracy"
beats HARD by >= 1 pp. Role-success accuracy = fraction of val questions
where the predicted role is one the question's history shows actually
succeeds (correctness > 0), which is the metric that matters for routing —
not whether we match the single argmax role.

Usage:
    python3 scripts/graph_router/train_routing_classifier_kl.py \
        [--data PATH] [--output PATH] [--epochs 300] [--tau 2.0]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("train_routing_classifier_kl")

DEFAULT_DATA = PROJECT_ROOT / "orchestration/reports/p45_soft_labels/soft_labels_embedded.npz"
DEFAULT_OUTPUT = PROJECT_ROOT / "orchestration/repl_memory/routing_classifier_weights_kl.npz"
DEFAULT_REPORT = PROJECT_ROOT / "orchestration/reports/p45_soft_labels/kl_ab_report.json"


def _train_arm(
    X_train, T_train, X_val, T_val,
    *,
    n_actions,
    label_map,
    epochs,
    lr,
    patience,
    batch_size,
    seed,
    arm_name,
    role_dropout_rate=0.0,
    role_dropout_min_roles=1,
    role_dropout_max_roles=2,
):
    """Train one arm against soft target matrix T (N, n_actions).

    Hard arm passes one-hot rows in T; soft arm passes the soft distribution.
    Loss is KL(T || p) up to the (constant in p) target-entropy term, i.e.
    cross-entropy H(T, p); the gradient at the logits is (p - T). With one-hot
    T this is exactly the standard CE used by the production trainer.
    """
    from orchestration.repl_memory.routing_classifier import RoutingClassifier

    clf = RoutingClassifier(
        input_dim=X_train.shape[1],
        n_actions=n_actions,
        label_map=label_map,
    )
    rng = np.random.default_rng(seed)

    def ce_loss(probs, T):
        p = np.clip(probs, 1e-7, 1.0)
        return float(-np.sum(T * np.log(p)) / T.shape[0])

    best_val = float("inf")
    best_weights = None
    no_improve = 0
    history = []

    for epoch in range(epochs):
        perm = rng.permutation(len(X_train))
        Xt, Tt = X_train[perm], T_train[perm]
        epoch_loss, n_batches = 0.0, 0

        for start in range(0, len(Xt), batch_size):
            end = min(start + batch_size, len(Xt))
            X_b, T_b = Xt[start:end], Tt[start:end]
            T_b = _apply_role_dropout_targets(
                T_b,
                rng=rng,
                rate=role_dropout_rate,
                min_roles=role_dropout_min_roles,
                max_roles=role_dropout_max_roles,
            )
            probs, cache = clf.forward(X_b)
            n = X_b.shape[0]

            # KL/CE gradient at logits: (p - T) / n
            dz3 = (probs - T_b) / n
            grads = {}
            grads["W3"] = cache["a2"].T @ dz3
            grads["b3"] = dz3.sum(axis=0)
            da2 = dz3 @ clf._weights["W3"].T
            dz2 = da2 * (cache["z2"] > 0)
            grads["W2"] = cache["a1"].T @ dz2
            grads["b2"] = dz2.sum(axis=0)
            da1 = dz2 @ clf._weights["W2"].T
            dz1 = da1 * (cache["z1"] > 0)
            grads["W1"] = cache["X"].T @ dz1
            grads["b1"] = dz1.sum(axis=0)

            current_lr = lr * 0.5 * (1 + np.cos(np.pi * epoch / epochs))
            for key in clf._weights:
                clf._weights[key] -= current_lr * grads[key]

            epoch_loss += ce_loss(probs, T_b)
            n_batches += 1

        val_probs, _ = clf.forward(X_val)
        val_loss = ce_loss(val_probs, T_val)
        history.append({"epoch": epoch, "train_loss": epoch_loss / max(n_batches, 1), "val_loss": val_loss})

        if val_loss < best_val:
            best_val = val_loss
            best_weights = {k: v.copy() for k, v in clf._weights.items()}
            no_improve = 0
        else:
            no_improve += 1
        if no_improve >= patience:
            logger.info("[%s] early stop at epoch %d", arm_name, epoch)
            break

    if best_weights:
        clf._weights = best_weights
    return clf, history


def _apply_role_dropout_targets(
    targets: np.ndarray,
    *,
    rng: np.random.Generator,
    rate: float,
    min_roles: int = 1,
    max_roles: int = 2,
) -> np.ndarray:
    """Drop secondary positive role mass from soft targets and renormalize.

    One-hot rows are left unchanged by construction because the argmax role is
    protected. This keeps the hard-label baseline equivalent while allowing
    P4.6 soft-label training to simulate missing alternate successful roles.
    """
    if not 0.0 <= rate <= 1.0:
        raise ValueError("role dropout rate must be between 0 and 1")
    if min_roles < 1:
        raise ValueError("role dropout min_roles must be >= 1")
    if max_roles < min_roles:
        raise ValueError("role dropout max_roles must be >= min_roles")
    if rate == 0.0:
        return targets

    dropped = targets.copy()
    for row in dropped:
        if rng.random() >= rate:
            continue
        positive = np.flatnonzero(row > 0.0)
        if positive.size <= 1:
            continue
        protected = int(np.argmax(row))
        eligible = positive[positive != protected]
        if eligible.size == 0:
            continue
        drop_count = int(rng.integers(min_roles, max_roles + 1))
        drop_count = min(drop_count, eligible.size)
        selected = rng.choice(eligible, size=drop_count, replace=False)
        row[selected] = 0.0
        total = float(row.sum())
        if total > 0.0:
            row /= total
    return dropped


def _role_success_acc(clf, X_val, correctness_val) -> float:
    """Fraction of val questions where the predicted role actually succeeds.

    correctness_val: (N, n_actions) — per-role correctness rate for each qid.
    A prediction counts as correct if the predicted role's historical
    correctness for that qid is > 0 (i.e. a role that can solve it).
    """
    probs, _ = clf.forward(X_val)
    preds = np.argmax(probs, axis=1)
    hits = correctness_val[np.arange(len(preds)), preds] > 0.0
    return float(hits.mean())


def _argmax_match_acc(clf, X_val, hard_val) -> float:
    probs, _ = clf.forward(X_val)
    preds = np.argmax(probs, axis=1)
    return float((preds == hard_val).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--patience", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--role-dropout-rate",
        type=float,
        default=0.0,
        help="P4.6 soft-arm-only probability of dropping secondary positive roles per training row.",
    )
    parser.add_argument("--role-dropout-min-roles", type=int, default=1)
    parser.add_argument("--role-dropout-max-roles", type=int, default=2)
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(f"Dataset not found: {args.data}. Run embed_soft_label_dataset.py first.")

    data = np.load(args.data, allow_pickle=True)
    X = data["X"].astype(np.float32)
    soft = data["soft_labels"].astype(np.float32)
    hard = data["hard_labels"].astype(np.int64)
    label_map_raw = data["label_map"]
    label_map = {int(row[0]): str(row[1]) for row in label_map_raw}
    n_actions = len(label_map)

    # Per-role correctness for the role-success metric: raw mean correctness
    # per role per qid (stored by the embed step). A role "can solve" a qid if
    # its historical correctness for that qid is > 0.
    correctness = data["correctness"].astype(np.float32)

    N = X.shape[0]
    rng = np.random.default_rng(args.seed)
    idx = rng.permutation(N)
    n_val = max(1, int(N * args.val_split))
    val_idx, train_idx = idx[:n_val], idx[n_val:]

    X_train, X_val = X[train_idx], X[val_idx]
    soft_train, soft_val = soft[train_idx], soft[val_idx]
    hard_train, hard_val = hard[train_idx], hard[val_idx]
    corr_val = correctness[val_idx]

    # HARD arm target: one-hot of argmax(soft)
    hard_onehot_train = np.zeros((len(train_idx), n_actions), dtype=np.float32)
    hard_onehot_train[np.arange(len(train_idx)), hard_train] = 1.0
    hard_onehot_val = np.zeros((len(val_idx), n_actions), dtype=np.float32)
    hard_onehot_val[np.arange(len(val_idx)), hard_val] = 1.0

    logger.info("Dataset: %d train, %d val, %d actions", len(train_idx), len(val_idx), n_actions)
    if args.role_dropout_rate:
        logger.info(
            "P4.6 role dropout enabled for SOFT arm: rate=%.3f roles=%d-%d",
            args.role_dropout_rate,
            args.role_dropout_min_roles,
            args.role_dropout_max_roles,
        )

    logger.info("=== Training HARD (cross-entropy) arm ===")
    clf_hard, _ = _train_arm(
        X_train, hard_onehot_train, X_val, hard_onehot_val,
        n_actions=n_actions, label_map=label_map, epochs=args.epochs,
        lr=args.lr, patience=args.patience, batch_size=args.batch_size,
        seed=args.seed, arm_name="hard",
    )

    logger.info("=== Training SOFT (KL divergence) arm ===")
    clf_soft, _ = _train_arm(
        X_train, soft_train, X_val, soft_val,
        n_actions=n_actions, label_map=label_map, epochs=args.epochs,
        lr=args.lr, patience=args.patience, batch_size=args.batch_size,
        seed=args.seed, arm_name="soft",
        role_dropout_rate=args.role_dropout_rate,
        role_dropout_min_roles=args.role_dropout_min_roles,
        role_dropout_max_roles=args.role_dropout_max_roles,
    )

    # Metrics
    hard_rsa = _role_success_acc(clf_hard, X_val, corr_val)
    soft_rsa = _role_success_acc(clf_soft, X_val, corr_val)
    hard_match = _argmax_match_acc(clf_hard, X_val, hard_val)
    soft_match = _argmax_match_acc(clf_soft, X_val, hard_val)

    delta_rsa = soft_rsa - hard_rsa
    adopt = delta_rsa >= 0.01  # >= 1 pp role-success-accuracy gate

    report = {
        "n_train": len(train_idx),
        "n_val": len(val_idx),
        "n_actions": n_actions,
        "hard_role_success_acc": round(hard_rsa, 4),
        "soft_role_success_acc": round(soft_rsa, 4),
        "delta_role_success_acc": round(delta_rsa, 4),
        "hard_argmax_match_acc": round(hard_match, 4),
        "soft_argmax_match_acc": round(soft_match, 4),
        "decision_gate": ">=+1pp role-success accuracy (soft over hard)",
        "adopt_soft_labels": bool(adopt),
        "label_map": label_map,
        "seed": args.seed,
        "role_dropout": {
            "applied_to": "soft" if args.role_dropout_rate > 0.0 else "disabled",
            "rate": args.role_dropout_rate,
            "min_roles": args.role_dropout_min_roles,
            "max_roles": args.role_dropout_max_roles,
        },
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w") as f:
        json.dump(report, f, indent=2)

    # Save the winning arm's weights (soft if adopted, else hard) as the
    # candidate — does NOT touch the production routing_classifier_weights.npz.
    winner = clf_soft if adopt else clf_hard
    winner.save(args.output)

    print("\n=== P4.5 KL A/B Report ===")
    print(f"  n_train={report['n_train']}  n_val={report['n_val']}")
    print(f"  HARD role-success acc: {hard_rsa:.1%}   (argmax-match {hard_match:.1%})")
    print(f"  SOFT role-success acc: {soft_rsa:.1%}   (argmax-match {soft_match:.1%})")
    print(f"  delta (soft - hard):   {delta_rsa:+.1%}")
    print(f"  DECISION: {'ADOPT soft labels' if adopt else 'KEEP hard labels'} (gate >=+1pp)")
    print(f"  Candidate weights → {args.output}")
    print(f"  Report → {args.report}")


if __name__ == "__main__":
    main()
