"""
Predict the Knowledge Level (K1-K6) of questions.

    python predict_kl.py "Define data science."
    python predict_kl.py --file questions.txt            # one question per line
    python predict_kl.py --file questions.txt --csv out.csv
"""
import argparse
import csv

from kl_engine import LEVEL_NAMES, load_default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="*")
    ap.add_argument("--file")
    ap.add_argument("--csv")
    a = ap.parse_args()
    qs = [" ".join(a.question)] if a.question else []
    if a.file:
        qs += [l.strip() for l in open(a.file, encoding="utf-8") if l.strip()]
    if not qs:
        ap.error("give a question or --file")
    preds = load_default().predict_many(qs)
    for q, p in zip(qs, preds):
        flag = "  [REVIEW: " + "; ".join(p.reasons) + "]" if p.review else ""
        print(f"{p.level} ({LEVEL_NAMES[p.level]}, {p.confidence:.0%}){flag}\n    {q}")
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["question", "kl", "confidence", "review", "reasons"])
            for q, p in zip(qs, preds):
                w.writerow([q, p.level, f"{p.confidence:.3f}", p.review, "; ".join(p.reasons)])


if __name__ == "__main__":
    main()
