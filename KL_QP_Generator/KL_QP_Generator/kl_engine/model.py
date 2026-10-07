"""
Hybrid Knowledge-Level predictor: rules (rules.py) + a text classifier trained on labelled questions.

Why hybrid?  Keywords alone fail on questions like
    "Explain how to apply Dijkstra's algorithm"   (verb says K2, task is K3)
    "Compare two algorithms and evaluate ..."      (two verbs, two levels)
so the model also learns from the whole sentence, and every prediction carries a confidence
and a list of reasons to REVIEW. The staff always has the last word (override), and
overrides can be saved as new training data.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from . import rules
from .rules import LEVELS, LEVEL_INDEX

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TRAIN_FILES = ["seed_questions.csv", "user_labeled.csv", "feedback.csv"]  # holdout is never trained on


@dataclass
class Prediction:
    level: str
    confidence: float
    probabilities: dict
    rule_level: str | None
    ml_level: str
    review: bool
    reasons: list = field(default_factory=list)
    evidence: list = field(default_factory=list)

    def to_dict(self):
        return {
            "kl": self.level, "confidence": round(self.confidence, 3),
            "probabilities": {k: round(v, 3) for k, v in self.probabilities.items()},
            "rule_level": self.rule_level, "ml_level": self.ml_level,
            "review": self.review, "reasons": self.reasons, "evidence": self.evidence,
        }


def _augment(text: str) -> str:
    """Add synthetic tokens that stress the clause-leading verbs, so the model sees them clearly."""
    toks = []
    for clause in rules.split_clauses(text):
        words = clause.lower().split()
        if words:
            toks.append("cv_" + "".join(ch for ch in words[0] if ch.isalnum()))
    first = text.lower().split()[:2]
    toks += ["lead_" + "".join(ch for ch in w if ch.isalnum()) for w in first]
    return text + " " + " ".join(toks)


class KLPredictor:
    def __init__(self, use_rule_features: bool = True, rule_blend: float = 0.35, C: float = 8.0):
        self.use_rule_features = use_rule_features
        self.rule_blend = rule_blend
        self.C = C
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)
        self.clf = LogisticRegression(C=C, max_iter=3000, class_weight="balanced")
        self.fitted = False

    # ---------- training ----------
    def _matrix(self, questions, fit=False):
        texts = [_augment(q) for q in questions]
        X = self.vec.fit_transform(texts) if fit else self.vec.transform(texts)
        if self.use_rule_features:
            R = csr_matrix(np.array([rules.rule_features(q) for q in questions]) * 1.5)
            X = hstack([X, R]).tocsr()
        return X

    def fit(self, questions, labels):
        X = self._matrix(questions, fit=True)
        self.clf.fit(X, [LEVEL_INDEX[l] for l in labels])
        self.fitted = True
        return self

    # ---------- prediction ----------
    def _proba(self, questions):
        X = self._matrix(questions)
        P = np.zeros((len(questions), len(LEVELS)))
        P[:, self.clf.classes_] = self.clf.predict_proba(X)
        return P

    def predict(self, question: str, marks: int | None = None) -> Prediction:
        return self.predict_many([question], [marks])[0]

    def predict_many(self, questions, marks=None) -> list[Prediction]:
        marks = marks or [None] * len(questions)
        P_ml = self._proba(questions)
        out = []
        for q, p_ml, m in zip(questions, P_ml, marks):
            a = rules.analyse(q)
            p = p_ml.copy()
            if a["level"] and self.rule_blend > 0:
                p_rule = np.full(len(LEVELS), 0.06)
                p_rule[LEVEL_INDEX[a["level"]]] = 0.70
                p = (1 - self.rule_blend) * p_ml + self.rule_blend * p_rule
            p = p / p.sum()
            idx = int(np.argmax(p))
            level = LEVELS[idx]
            ml_level = LEVELS[int(np.argmax(p_ml))]
            conf = float(p[idx])

            reasons = []
            if conf < 0.55:
                reasons.append("low confidence")
            if a["level"] is None:
                reasons.append("no recognised action verb (decided by the model only)")
            elif a["level"] != level:
                reasons.append(f"rules say {a['level']} but the model says {ml_level}")
            if a["clause_levels"]:
                idxs = [LEVEL_INDEX[l] for l in a["clause_levels"]]
                if max(idxs) - min(idxs) >= 2:
                    reasons.append("question mixes verbs of very different levels")
            if m is not None and m >= 12 and level == "K1":
                reasons.append("K1 on a high-mark question")
            out.append(Prediction(level, conf, {k: float(v) for k, v in zip(LEVELS, p)},
                                  a["level"], ml_level, bool(reasons), reasons, a["evidence"]))
        return out


# ---------- data helpers ----------
def read_csv(path):
    qs, ls = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            q, k = (row.get("question") or "").strip(), (row.get("kl") or "").strip().upper()
            if q and k in LEVEL_INDEX:
                qs.append(q)
                ls.append(k)
    return qs, ls


def load_training_data(data_dir: str = DATA_DIR):
    qs, ls = [], []
    for name in TRAIN_FILES:
        p = os.path.join(data_dir, name)
        if os.path.exists(p):
            a, b = read_csv(p)
            qs += a
            ls += b
    return qs, ls


_DEFAULT = None


def load_default(force: bool = False) -> KLPredictor:
    """Train (takes about a second) on seed + user_labeled + feedback data, cached per process."""
    global _DEFAULT
    if _DEFAULT is None or force:
        qs, ls = load_training_data()
        _DEFAULT = KLPredictor().fit(qs, ls)
    return _DEFAULT


def append_feedback(question: str, kl: str, data_dir: str = DATA_DIR):
    """Save a staff correction so the next training run learns from it."""
    p = os.path.join(data_dir, "feedback.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        if new:
            w.writerow(["question", "kl"])
        w.writerow([question.strip(), kl])
