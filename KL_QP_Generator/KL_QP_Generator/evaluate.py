"""
Evaluate the Knowledge-Level predictor.

    python evaluate.py                       # 5-fold CV on seed data + tricky hold-out set
    python evaluate.py --test my_file.csv    # your own staff-labelled file (columns: question,kl)

Three systems are compared:  rules only | ML text model only | hybrid (rules + ML, the one the app uses).
Metrics: exact accuracy, within-one-level accuracy (Bloom's boundaries are fuzzy), macro-F1,
confusion matrix, and how many of the WRONG predictions were flagged "review".
"""
import argparse
import os

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold

from kl_engine import rules
from kl_engine.model import DATA_DIR, KLPredictor, load_training_data, read_csv
from kl_engine.rules import LEVELS, LEVEL_INDEX


def make_systems():
    return {
        "rules only": None,
        "ML only": lambda: KLPredictor(use_rule_features=False, rule_blend=0.0),
        "hybrid": lambda: KLPredictor(),
    }


def predict_with(name, model, questions):
    """Return (pred_levels, review_flags)."""
    if name == "rules only":
        return [rules.predict_level(q) for q in questions], [rules.analyse(q)["abstained"] for q in questions]
    preds = model.predict_many(questions)
    return [p.level for p in preds], [p.review for p in preds]


def metrics(y_true, y_pred, flags):
    yt = np.array([LEVEL_INDEX[k] for k in y_true])
    yp = np.array([LEVEL_INDEX[k] for k in y_pred])
    flags = np.array(flags, dtype=bool)
    wrong = yt != yp
    cm = np.zeros((6, 6), dtype=int)
    for a, b in zip(yt, yp):
        cm[a, b] += 1
    unflagged = ~flags
    return {
        "n": len(yt),
        "acc": float((~wrong).mean()),
        "within1": float((np.abs(yt - yp) <= 1).mean()),
        "macro_f1": float(f1_score(yt, yp, average="macro", labels=list(range(6)), zero_division=0)),
        "wrong": int(wrong.sum()),
        "wrong_flagged": int((wrong & flags).sum()),
        "flag_rate": float(flags.mean()),
        "acc_unflagged": float((~wrong[unflagged]).mean()) if unflagged.any() else float("nan"),
        "cm": cm,
    }


def cross_validate(questions, labels, folds=5, seed=42):
    systems = make_systems()
    skf = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
    qs, ls = np.array(questions, dtype=object), np.array(labels)
    allp = {k: [None] * len(qs) for k in systems}
    allf = {k: [None] * len(qs) for k in systems}
    for tr, te in skf.split(qs, ls):
        for name, factory in systems.items():
            model = factory().fit(list(qs[tr]), list(ls[tr])) if factory else None
            p, f = predict_with(name, model, list(qs[te]))
            for i, pi, fi in zip(te, p, f):
                allp[name][i], allf[name][i] = pi, fi
    return {name: metrics(list(ls), allp[name], allf[name]) for name in systems}


def holdout(train_q, train_l, test_q, test_l):
    out = {}
    details = {}
    for name, factory in make_systems().items():
        model = factory().fit(train_q, train_l) if factory else None
        p, f = predict_with(name, model, test_q)
        out[name] = metrics(test_l, p, f)
        details[name] = (p, f)
    return out, details


def fmt_table(res):
    lines = ["| system | n | exact acc | within ±1 | macro-F1 | wrong | wrong but flagged | flagged % | acc on unflagged |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, m in res.items():
        lines.append(f"| {name} | {m['n']} | {m['acc']:.1%} | {m['within1']:.1%} | {m['macro_f1']:.3f} | "
                     f"{m['wrong']} | {m['wrong_flagged']} | {m['flag_rate']:.0%} | {m['acc_unflagged']:.1%} |")
    return "\n".join(lines)


def fmt_cm(cm):
    head = "| true \\ pred | " + " | ".join(LEVELS) + " |\n|---|" + "---|" * 6
    rows = [f"| **{LEVELS[i]}** | " + " | ".join(str(v) for v in cm[i]) + " |" for i in range(6)]
    return head + "\n" + "\n".join(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", help="CSV with columns question,kl (your own staff-labelled questions)")
    ap.add_argument("--report", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "evaluation.md"))
    args = ap.parse_args()

    tq, tl = load_training_data()
    md = ["# Knowledge-Level predictor - evaluation report", "",
          f"Training data: {len(tq)} labelled questions (seed + any user_labeled / feedback files).", ""]

    cv = cross_validate(tq, tl)
    md += ["## 1. 5-fold cross-validation on the training data", "", fmt_table(cv), "",
           "Hybrid confusion matrix (CV):", "", fmt_cm(cv["hybrid"]["cm"]), ""]

    sets = []
    if args.test:
        xq, xl = read_csv(args.test)
        sets.append((f"## 2. Your test file: {os.path.basename(args.test)}", xq, xl))
    else:
        sets.append(("## 2. Tricky hold-out set (never trained on, but written while the rules were being tuned - optimistic)",)
                    + read_csv(os.path.join(DATA_DIR, "holdout_tricky.csv")))
        sets.append(("## 3. Blind set (31 new questions on OS/DBMS/networks, written AFTER the rules were frozen)",)
                    + read_csv(os.path.join(DATA_DIR, "holdout_blind.csv")))
    for title, xq, xl in sets:
        res, det = holdout(tq, tl, xq, xl)
        md += [title, "", fmt_table(res), "", "Hybrid confusion matrix:", "", fmt_cm(res["hybrid"]["cm"]), ""]
        md += ["", "_Note: labels in the seed/hold-out files were written by the project author. "
           "Use `--test` with questions labelled by your own staff for a fair measurement._"]

    text = "\n".join(md)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    print(f"\n[report saved to {args.report}]")


if __name__ == "__main__":
    main()
