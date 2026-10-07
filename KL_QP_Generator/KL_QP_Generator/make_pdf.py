"""
Build the question paper PDF (+ faculty blueprint PDF) from a JSON spec.

    python make_pdf.py examples/sample_cat.json            # -> outputs/<name>_paper.pdf, outputs/<name>_blueprint.pdf
    python make_pdf.py my_spec.json --out some_folder

Questions without a "kl" get one predicted automatically; a "kl" you write yourself is kept (staff override).
A spec with empty questions produces the blank framework.
"""
import argparse
import json
import os

from kl_engine import load_default
from qp import paper, pdf_gen


def build(spec_raw, out_dir, name):
    spec = paper.normalize_spec(spec_raw)
    paper.apply_kl(spec, load_default())
    os.makedirs(out_dir, exist_ok=True)
    p1 = pdf_gen.render_paper(spec, os.path.join(out_dir, f"{name}_paper.pdf"))
    p2 = pdf_gen.render_blueprint(spec, os.path.join(out_dir, f"{name}_blueprint.pdf"))
    return spec, p1, p2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default="outputs")
    a = ap.parse_args()
    raw = json.load(open(a.spec, encoding="utf-8"))
    name = os.path.splitext(os.path.basename(a.spec))[0]
    spec, p1, p2 = build(raw, a.out, name)
    for w in paper.validate(spec):
        print("WARNING:", w)
    print("Paper    :", p1)
    print("Blueprint:", p2)


if __name__ == "__main__":
    main()
