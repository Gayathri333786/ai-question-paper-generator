"""
Local web app:   python app.py   ->  opens http://127.0.0.1:5000

Workflow (same as your handwritten algorithm):
 1. choose paper type (CAT / Semester)   2. fill the framework header
 3. choose parts, marks and COs (faculty)  4. paste questions -> KL is predicted automatically (staff can override)
 5. generate the question paper PDF (+ a faculty blueprint PDF)
"""
import io
import os
import webbrowser

from flask import Flask, jsonify, request, send_file, send_from_directory

from kl_engine import LEVEL_NAMES, append_feedback, load_default
from qp import paper, pdf_gen
from qp.presets import PRESETS

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(HERE, "static"))


def _prepare(raw_spec):
    spec = paper.normalize_spec(raw_spec)
    paper.apply_kl(spec, load_default())
    return spec


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/presets")
def presets():
    return jsonify(PRESETS)


@app.post("/api/predict")
def predict():
    data = request.get_json(force=True)
    qs = [q for q in data.get("questions", []) if q and q.strip()]
    preds = load_default().predict_many(qs)
    return jsonify([dict(question=q, name=LEVEL_NAMES[p.level], **p.to_dict()) for q, p in zip(qs, preds)])


@app.post("/api/build")
def build():
    spec = _prepare(request.get_json(force=True)["spec"])
    return jsonify({
        "spec": spec,
        "warnings": paper.validate(spec),
        "kl_distribution": paper.kl_distribution(spec),
        "co_distribution": paper.co_distribution(spec),
    })


@app.post("/api/pdf")
def pdf():
    data = request.get_json(force=True)
    spec = _prepare(data["spec"])
    kind = data.get("kind", "paper")
    buf = io.BytesIO()
    (pdf_gen.render_blueprint if kind == "blueprint" else pdf_gen.render_paper)(spec, buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", download_name=f"question_{kind}.pdf")


@app.post("/api/feedback")
def feedback():
    items = request.get_json(force=True).get("items", [])
    n = 0
    for it in items:
        if it.get("question", "").strip() and it.get("kl") in LEVEL_NAMES:
            append_feedback(it["question"], it["kl"])
            n += 1
    load_default(force=True)  # retrain right away so the corrections are used immediately
    return jsonify({"saved": n})


if __name__ == "__main__":
    load_default()
    url = "http://127.0.0.1:5000"
    print(f"Open {url}  (Ctrl+C to stop)")
    if os.environ.get("NO_BROWSER") != "1":
        webbrowser.open(url)
    app.run(host="127.0.0.1", port=5000, threaded=True)
