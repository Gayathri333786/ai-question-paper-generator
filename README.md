# KL Question Paper Generator

Paste questions -> the system predicts the Bloom's Knowledge Level (K1-K6) -> generates the CAT / Semester question paper as PDF.

## Run (Python 3.10+)
```
pip install -r requirements.txt
python app.py              # opens http://127.0.0.1:5000
```
Command line alternatives:
```
python predict_kl.py "Explain how to apply Dijkstra's algorithm."      # KL only
python predict_kl.py --file questions.txt --csv result.csv
python make_pdf.py examples/sample_cat.json                           # JSON spec -> PDFs in outputs/
python evaluate.py                                                    # measure accuracy
python evaluate.py --test my_staff_labelled.csv                       # YOUR labelled questions (columns: question,kl)
python tests/test_core.py
```

## Workflow (algorithm )
1. Pick paper type: CAT (QP set) or Semester (QP code + exam year).
2. Fill the framework header (college, programme, semester, max marks, duration, regulation, course, date...).
3. Choose parts, marks and COs. Faculty gives COs and counts, e.g. CO1x5, CO2x4 -> Q1-5 CO1, Q6-9 CO2.
   Either-or parts (a)/(b) are supported, and marks can be split into (i)+(ii).
4. Paste questions. KL is predicted per question; staff can override from the drop-down.
5. Download the question paper PDF and the faculty blueprint PDF (KL/CO distribution, confidence, "check this" notes).

## How the KL prediction avoids "keywords only"
* Rule layer (`kl_engine/rules.py`): looks at the verb that starts each clause, takes the highest level when several
  verbs appear ("Compare ... and evaluate ..." -> K5), and applies context patterns
  ("Explain how to apply ..." -> K3, "Write a program to design ..." -> K3, numbers to calculate with -> at least K3).
* ML layer (`kl_engine/model.py`): TF-IDF + logistic regression over the whole sentence, plus the rule signals as features.
* Blend + confidence + review flags: low confidence, rules/model disagreement, mixed verb levels, or no recognised verb
  -> the question is marked "check". The PDF blueprint lists these.
* Staff always have the last word. "Save my KL overrides as training data" writes `data/feedback.csv`; it is used on the next start.

## Improve accuracy with your own data
Put staff-labelled questions in `data/user_labeled.csv` (columns `question,kl`; K1..K6). Training reads
`seed_questions.csv`, `user_labeled.csv` and `feedback.csv`. Hold-out files are never trained on.
Local conventions differ (e.g. your staff may label "Illustrate a data transformation for a simple example" K3; the
seed data says K2), so a few hundred of your own labelled questions will help more than any code change.

## Folder
```
app.py  static/index.html   web app          make_pdf.py / predict_kl.py / evaluate.py   command line
kl_engine/                  rules + ML        qp/                                          paper model + PDF
data/                       training + hold-out sets   examples/   sample specs   outputs/   sample PDFs   reports/evaluation.md
```
