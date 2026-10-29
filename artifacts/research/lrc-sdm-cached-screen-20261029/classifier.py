"""RoutingClassifier: Lightweight MLP for fast routing decisions.

A 2-layer MLP trained via Q-value weighted cross-entropy loss on distilled
episodic memory data. Pure numpy — no PyTorch dependency.

Architecture:
    Input(D) → Dense(128, ReLU) → Dense(64, ReLU) → Dense(N_actions, Softmax)
    ~200K parameters. Inference: <0.1ms (numpy matmul).

The classifier serves as a fast first-pass before full FAISS retrieval:
- If confidence >= threshold: skip retrieval, use classifier directly
- Otherwise: fall through to normal TwoPhaseRetriever pipeline

Training uses Q-value weighted cross-entropy:
    L = -sum(q_i * y_i * log(p_i)) / sum(q_i)
High Q-value memories contribute more — the classifier learns from
confident routing decisions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from scripts.graph_router.action_space import normalize_action

_REPO_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS_PATH = _REPO_ROOT / "orchestration/repl_memory/routing_classifier_weights.npz"


def _canonicalize_action_label(label: str) -> str:
    """Return the canonical live role for a loaded action label when known."""
    return normalize_action(label, include_seeded_frontdoor=True) or label


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0, x)


def _relu_grad(x: np.ndarray) -> np.ndarray:
    return (x > 0).astype(np.float32)


def _softmax(x: np.ndarray) -> np.ndarray:
    """Numerically stable softmax."""
    shifted = x - x.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


class RoutingClassifier:
    """2-layer MLP routing classifier with numpy-only inference and training."""

    def __init__(
        self,
        input_dim: int = 1031,
        hidden1: int = 128,
        hidden2: int = 64,
        n_actions: int = 6,
        label_map: Optional[Dict[int, str]] = None,
        class_thresholds: Optional[Dict[int, float]] = None,
    ):
        self.input_dim = input_dim
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        self.n_actions = n_actions
        self.label_map = label_map or {}
        # Per-class confidence thresholds (class_idx → threshold).
        # If set, predict_action returns (action, confidence) only when
        # confidence >= class threshold. Otherwise returns (None, confidence).
        self.class_thresholds: Dict[int, float] = class_thresholds or {}

        # Xavier initialization
        self._weights: Dict[str, np.ndarray] = {}
        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier uniform initialization."""
        rng = np.random.default_rng(42)

        def xavier(fan_in: int, fan_out: int) -> np.ndarray:
            limit = np.sqrt(6.0 / (fan_in + fan_out))
            return rng.uniform(-limit, limit, (fan_in, fan_out)).astype(np.float32)

        self._weights = {
            "W1": xavier(self.input_dim, self.hidden1),
            "b1": np.zeros(self.hidden1, dtype=np.float32),
            "W2": xavier(self.hidden1, self.hidden2),
            "b2": np.zeros(self.hidden2, dtype=np.float32),
            "W3": xavier(self.hidden2, self.n_actions),
            "b3": np.zeros(self.n_actions, dtype=np.float32),
        }

    @property
    def param_count(self) -> int:
        return sum(w.size for w in self._weights.values())

    def forward(self, X: np.ndarray) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Forward pass returning probabilities and intermediate activations.

        Args:
            X: (N, D) or (D,) input features.

        Returns:
            (probs, cache) where probs is (N, n_actions) and cache has intermediates.
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)

        z1 = X @ self._weights["W1"] + self._weights["b1"]
        a1 = _relu(z1)
        z2 = a1 @ self._weights["W2"] + self._weights["b2"]
        a2 = _relu(z2)
        z3 = a2 @ self._weights["W3"] + self._weights["b3"]
        probs = _softmax(z3)

        cache = {"X": X, "z1": z1, "a1": a1, "z2": z2, "a2": a2, "z3": z3}
        return probs, cache

    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """Predict action probability distribution.

        Args:
            features: (D,) feature vector.

        Returns:
            Dict mapping action name → probability.
        """
        probs, _ = self.forward(features)
        probs = probs[0]  # Remove batch dim
        return {
            self.label_map.get(i, f"action_{i}"): float(p)
            for i, p in enumerate(probs)
        }

    def predict_action(self, features: np.ndarray) -> Tuple[Optional[str], float]:
        """Predict best action and confidence.

        If per-class thresholds are set, returns (None, confidence) when
        the best class confidence is below its per-class threshold.
        This signals the caller to fall through to the next routing strategy.

        Args:
            features: (D,) feature vector.

        Returns:
            (action_name_or_None, confidence) tuple.
        """
        probs, _ = self.forward(features)
        probs = probs[0]  # Remove batch dim

        best_idx = int(np.argmax(probs))
        best_prob = float(probs[best_idx])
        best_action = self.label_map.get(best_idx, f"action_{best_idx}")

        # Per-class threshold check
        if self.class_thresholds:
            threshold = self.class_thresholds.get(best_idx, 0.95)  # conservative default
            if best_prob < threshold:
                return None, best_prob

        return best_action, best_prob

    def mc_predict(
        self,
        X: np.ndarray,
        p_drop: float = 0.1,
        n_samples: int = 10,
        seed: int = 0,
    ) -> np.ndarray:
        """MC-dropout-style forward pass with hidden-activation dropout.

        Returns per-sample probability tensors so callers can compute mean /
        variance / entropy as uncertainty signals. Classifier was NOT trained
        with dropout, so this is test-time activation-noise sensitivity, not
        canonical Bayesian MC-dropout — interpret variance as prediction
        stability, not posterior credible interval.

        Returns:
            probs: (n_samples, N, n_actions) probability tensor.
        """
        if X.ndim == 1:
            X = X.reshape(1, -1)
        rng = np.random.default_rng(seed)
        keep = 1.0 - p_drop
        out = []
        for _ in range(n_samples):
            z1 = X @ self._weights["W1"] + self._weights["b1"]
            a1 = _relu(z1)
            m1 = (rng.random(a1.shape) > p_drop).astype(np.float32) / keep
            a1 = a1 * m1
            z2 = a1 @ self._weights["W2"] + self._weights["b2"]
            a2 = _relu(z2)
            m2 = (rng.random(a2.shape) > p_drop).astype(np.float32) / keep
            a2 = a2 * m2
            z3 = a2 @ self._weights["W3"] + self._weights["b3"]
            out.append(_softmax(z3))
        return np.stack(out)

    def calibrate_thresholds(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray,
        target_precision: float = 0.9,
        min_samples: int = 10,
    ) -> Dict[int, float]:
        """Compute per-class confidence thresholds from validation data.

        For each class, finds the lowest softmax threshold where precision >= target.
        Classes with too few validation samples get a conservative default (0.95).

        Args:
            X_val: (N, D) validation feature matrix.
            y_val: (N,) validation integer labels.
            target_precision: Minimum precision to achieve per class.
            min_samples: Minimum predictions for a class to calibrate.

        Returns:
            Dict mapping class index → threshold.
        """
        probs, _ = self.forward(X_val)
        preds = np.argmax(probs, axis=1)
        max_probs = np.max(probs, axis=1)

        thresholds = {}
        for cls in range(self.n_actions):
            cls_mask = preds == cls
            n_predicted = int(cls_mask.sum())

            if n_predicted < min_samples:
                thresholds[cls] = 0.95
                continue

            # Sort predictions of this class by confidence descending
            cls_probs = max_probs[cls_mask]
            cls_correct = (y_val[cls_mask] == cls)
            sorted_idx = np.argsort(-cls_probs)

            # Walk from highest confidence down, find where precision drops below target
            cumul_correct = np.cumsum(cls_correct[sorted_idx])
            cumul_count = np.arange(1, len(sorted_idx) + 1)
            cumul_precision = cumul_correct / cumul_count

            # Find the last index where precision >= target
            valid = cumul_precision >= target_precision
            if valid.any():
                last_valid = np.where(valid)[0][-1]
                thresholds[cls] = float(cls_probs[sorted_idx[last_valid]])
            else:
                thresholds[cls] = 0.95

        self.class_thresholds = thresholds

        logger.info("Calibrated per-class thresholds (target_precision=%.2f):", target_precision)
        for cls, thr in sorted(thresholds.items()):
            name = self.label_map.get(cls, f"action_{cls}")
            logger.info("  [%d] %s: threshold=%.3f", cls, name, thr)

        return thresholds

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        q_weights: np.ndarray,
        epochs: int = 200,
        lr: float = 0.01,
        val_split: float = 0.2,
        patience: int = 30,
        batch_size: int = 64,
    ) -> Dict[str, List[float]]:
        """Train with mini-batch SGD and Q-value weighted cross-entropy.

        Args:
            X: (N, D) feature matrix.
            y: (N,) integer labels.
            q_weights: (N,) Q-value sample weights.
            epochs: Max training epochs.
            lr: Initial learning rate.
            val_split: Fraction for validation.
            patience: Early stopping patience.
            batch_size: Mini-batch size.

        Returns:
            Training history with train_loss, val_loss, val_acc lists.
        """
        N = X.shape[0]
        rng = np.random.default_rng(42)

        # Stratified train/val split
        indices = np.arange(N)
        rng.shuffle(indices)
        n_val = max(1, int(N * val_split))
        val_idx = indices[:n_val]
        train_idx = indices[n_val:]

        X_train, y_train, q_train = X[train_idx], y[train_idx], q_weights[train_idx]
        X_val, y_val, q_val = X[val_idx], y[val_idx], q_weights[val_idx]

        history = {"train_loss": [], "val_loss": [], "val_acc": []}
        best_val_loss = float("inf")
        best_weights = None
        no_improve = 0

        for epoch in range(epochs):
            # Shuffle training data
            perm = rng.permutation(len(X_train))
            X_train, y_train, q_train = X_train[perm], y_train[perm], q_train[perm]

            # Mini-batch SGD
            epoch_loss = 0.0
            n_batches = 0
            for start in range(0, len(X_train), batch_size):
                end = min(start + batch_size, len(X_train))
                X_b = X_train[start:end]
                y_b = y_train[start:end]
                q_b = q_train[start:end]

                # Forward
                probs, cache = self.forward(X_b)

                # Compute loss and gradients
                loss, grads = self._backward(probs, cache, y_b, q_b)
                epoch_loss += loss
                n_batches += 1

                # Cosine LR decay
                current_lr = lr * 0.5 * (1 + np.cos(np.pi * epoch / epochs))

                # Update weights
                for key in self._weights:
                    self._weights[key] -= current_lr * grads[key]

            train_loss = epoch_loss / max(n_batches, 1)

            # Validation
            val_probs, _ = self.forward(X_val)
            val_loss = self._compute_loss(val_probs, y_val, q_val)
            val_preds = np.argmax(val_probs, axis=1)
            val_acc = float((val_preds == y_val).mean())

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_acc)

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_weights = {k: v.copy() for k, v in self._weights.items()}
                no_improve = 0
            else:
                no_improve += 1

            if epoch % 20 == 0 or epoch == epochs - 1:
                logger.info(
                    "Epoch %3d/%d  train_loss=%.4f  val_loss=%.4f  val_acc=%.3f  lr=%.6f  patience=%d/%d",
                    epoch, epochs, train_loss, val_loss, val_acc, current_lr, no_improve, patience,
                )

            if no_improve >= patience:
                logger.info("Early stopping at epoch %d", epoch)
                break

        # Restore best weights
        if best_weights:
            self._weights = best_weights

        return history

    def _compute_loss(
        self,
        probs: np.ndarray,
        y: np.ndarray,
        q_weights: np.ndarray,
    ) -> float:
        """Q-value weighted cross-entropy loss.

        L = -sum(q_i * log(p_i[y_i])) / sum(q_i)
        """
        N = len(y)
        # Clip for numerical stability
        probs_clipped = np.clip(probs, 1e-7, 1.0)
        log_probs = np.log(probs_clipped[np.arange(N), y])
        return float(-np.sum(q_weights * log_probs) / np.sum(q_weights))

    def _backward(
        self,
        probs: np.ndarray,
        cache: Dict[str, np.ndarray],
        y: np.ndarray,
        q_weights: np.ndarray,
    ) -> Tuple[float, Dict[str, np.ndarray]]:
        """Backward pass computing loss and gradients.

        Returns:
            (loss, gradients_dict)
        """
        N = len(y)
        loss = self._compute_loss(probs, y, q_weights)

        # Softmax cross-entropy gradient: dL/dz3 = (p - one_hot(y)) * q_weight
        one_hot = np.zeros_like(probs)
        one_hot[np.arange(N), y] = 1.0
        q_norm = q_weights / np.sum(q_weights)
        dz3 = (probs - one_hot) * q_norm[:, None]  # (N, n_actions)

        # Layer 3 gradients
        grads = {}
        grads["W3"] = cache["a2"].T @ dz3  # (hidden2, n_actions)
        grads["b3"] = dz3.sum(axis=0)

        # Backprop through layer 2
        da2 = dz3 @ self._weights["W3"].T  # (N, hidden2)
        dz2 = da2 * _relu_grad(cache["z2"])
        grads["W2"] = cache["a1"].T @ dz2
        grads["b2"] = dz2.sum(axis=0)

        # Backprop through layer 1
        da1 = dz2 @ self._weights["W2"].T  # (N, hidden1)
        dz1 = da1 * _relu_grad(cache["z1"])
        grads["W1"] = cache["X"].T @ dz1
        grads["b1"] = dz1.sum(axis=0)

        return loss, grads

    def save(self, path: Path = DEFAULT_WEIGHTS_PATH) -> None:
        """Save weights, thresholds, and metadata to .npz file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        save_dict = dict(self._weights)
        save_dict["_label_map_keys"] = np.array(list(self.label_map.keys()), dtype=np.int64)
        save_dict["_label_map_vals"] = np.array(
            [
                _canonicalize_action_label(label)
                for label in self.label_map.values()
            ],
            dtype=object,
        )
        save_dict["_config"] = np.array([
            self.input_dim, self.hidden1, self.hidden2, self.n_actions,
        ], dtype=np.int64)

        # Per-class thresholds
        if self.class_thresholds:
            save_dict["_threshold_keys"] = np.array(
                list(self.class_thresholds.keys()), dtype=np.int64
            )
            save_dict["_threshold_vals"] = np.array(
                list(self.class_thresholds.values()), dtype=np.float32
            )

        np.savez_compressed(path, **save_dict)
        logger.info("Saved classifier weights to %s (%d params)", path, self.param_count)

    @classmethod
    def load(cls, path: Path = DEFAULT_WEIGHTS_PATH) -> Optional[RoutingClassifier]:
        """Load weights from .npz file.

        Returns None if file doesn't exist (e.g. after episodic memory reset).
        """
        path = Path(path)
        if not path.exists():
            logger.info("No classifier weights at %s — skipping", path)
            return None

        try:
            data = np.load(path, allow_pickle=True)
            config = data["_config"]
            input_dim, hidden1, hidden2, n_actions = int(config[0]), int(config[1]), int(config[2]), int(config[3])

            keys = data["_label_map_keys"]
            vals = data["_label_map_vals"]
            label_map = {
                int(k): _canonicalize_action_label(str(v))
                for k, v in zip(keys, vals)
            }

            clf = cls(
                input_dim=input_dim,
                hidden1=hidden1,
                hidden2=hidden2,
                n_actions=n_actions,
                label_map=label_map,
            )
            for key in ["W1", "b1", "W2", "b2", "W3", "b3"]:
                clf._weights[key] = data[key].astype(np.float32)

            # Load per-class thresholds if present
            if "_threshold_keys" in data and "_threshold_vals" in data:
                t_keys = data["_threshold_keys"]
                t_vals = data["_threshold_vals"]
                clf.class_thresholds = {int(k): float(v) for k, v in zip(t_keys, t_vals)}

            logger.info(
                "Loaded classifier: %d params, %d actions",
                clf.param_count, n_actions,
            )
            return clf
        except Exception as e:
            logger.warning("Failed to load classifier weights: %s", e)
            return None
