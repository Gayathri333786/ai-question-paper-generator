"""PDF rendering with reportlab: the question paper itself and a faculty blueprint page."""
from __future__ import annotations

import os
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from kl_engine.rules import LEVEL_NAMES, LEVELS
from . import paper as P

PAGE_W = A4[0] - 30 * mm   # 15 mm margins -> 180 mm usable
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
    "C:/Windows/Fonts/times.ttf",
    "/Library/Fonts/Times New Roman.ttf",
]


def _fonts(texts):
    """Times for normal text; a Unicode TTF only if some text has characters Times (cp1252) cannot show."""
    need_unicode = False
    for t in texts:
        try:
            t.encode("cp1252")
        except UnicodeEncodeError:
            need_unicode = True
            break
    if need_unicode:
        for path in _FONT_CANDIDATES:
            if os.path.exists(path):
                bold = path.replace("Serif.ttf", "Serif-Bold.ttf").replace("times.ttf", "timesbd.ttf")
                pdfmetrics.registerFont(TTFont("QPFont", path))
                pdfmetrics.registerFont(TTFont("QPFont-Bold", bold if os.path.exists(bold) else path))
                return "QPFont", "QPFont-Bold"
    return "Times-Roman", "Times-Bold"


def _all_texts(spec):
    out = [str(v) for v in spec["header"].values()]
    for part in spec["parts"]:
        for it in part["items"]:
            for opt in it["options"]:
                out += [p["text"] for p in opt["parts"]]
    return out


def _p(text, style):
    return Paragraph(escape(text or "").replace("\n", "<br/>"), style)


def _styles(fr, fb, size=10.5):
    return {
        "body": ParagraphStyle("body", fontName=fr, fontSize=size, leading=size * 1.3, alignment=TA_LEFT),
        "center": ParagraphStyle("center", fontName=fr, fontSize=size, leading=size * 1.3, alignment=TA_CENTER),
        "bold": ParagraphStyle("bold", fontName=fb, fontSize=size, leading=size * 1.3, alignment=TA_LEFT),
        "boldc": ParagraphStyle("boldc", fontName=fb, fontSize=size, leading=size * 1.3, alignment=TA_CENTER),
        "college": ParagraphStyle("college", fontName=fb, fontSize=14, leading=17, alignment=TA_CENTER),
        "aff": ParagraphStyle("aff", fontName=fr, fontSize=9.5, leading=12, alignment=TA_CENTER),
        "partt": ParagraphStyle("partt", fontName=fb, fontSize=11.5, leading=14, alignment=TA_CENTER),
        "instr": ParagraphStyle("instr", fontName=fr, fontSize=9.5, leading=12, alignment=TA_CENTER),
        "small": ParagraphStyle("small", fontName=fr, fontSize=8.5, leading=10.5, alignment=TA_LEFT),
    }


def _header_block(spec, S, fr, fb):
    h, t = spec["header"], spec["paper_type"]
    flow = []

    # Register number boxes (right) and QP code (left, semester papers)
    left = f"Question Paper Code: {h.get('qp_code', '')}" if t == "SEM" else ""
    box_w = 7 * mm
    reg = Table([[_p(left, S["bold"]), _p("Register Number", S["bold"])] + [""] * 12],
                colWidths=[PAGE_W - 38 * mm - 12 * box_w, 38 * mm] + [box_w] * 12, rowHeights=[8 * mm])
    reg.setStyle(TableStyle([("GRID", (1, 0), (-1, 0), 0.6, colors.black),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    flow += [reg, Spacer(1, 3 * mm), _p(h.get("college", ""), S["college"]), _p(h.get("affiliation", ""), S["aff"]),
             Spacer(1, 2 * mm)]

    if t == "SEM":
        title = f"{h.get('exam_title', 'Semester Examinations')} \u2013 {h.get('exam_year', '')}".strip(" \u2013")
        r0 = [_p(title, S["bold"]), "", _p(f"QP Code : {h.get('qp_code', '')}", S["body"]),
              _p(f"Regulations : {h.get('regulations', '')}", S["body"])]
    else:
        r0 = [_p(h.get("exam_title", ""), S["bold"]), "", _p(f"QP Set : {h.get('qp_set', '')}", S["body"]),
              _p(f"Regulations : {h.get('regulations', '')}", S["body"])]
    rows = [
        r0,
        [_p(f"Programme : {h.get('programme', '')}", S["body"]), _p(f"Semester : {h.get('semester', '')}", S["body"]),
         _p(f"Max. Marks : {h.get('max_marks', '')}", S["body"]), _p(f"Duration : {h.get('duration', '')}", S["body"])],
        [_p(f"Course Code & Title : {h.get('course', '')}", S["bold"]), "", "", ""],
        [_p(f"Class : {h.get('class_name', '')}", S["body"]), "", _p(f"Date : {h.get('date', '')}", S["body"]),
         _p(f"Time : {h.get('time', '')}", S["body"])],
    ]
    cw = [56 * mm, 28 * mm, 38 * mm, 58 * mm]
    tb = Table(rows, colWidths=cw)
    tb.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 2), (3, 2)), ("SPAN", (0, 3), (1, 3)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    legend = Table([[Paragraph("Knowledge Levels (KL)", S["bold"]),
                     Paragraph("K1 \u2013 Remembering<br/>K2 \u2013 Understanding", S["body"]),
                     Paragraph("K3 \u2013 Applying<br/>K4 \u2013 Analysing", S["body"]),
                     Paragraph("K5 \u2013 Evaluating<br/>K6 \u2013 Creating", S["body"])]],
                   colWidths=[42 * mm, 46 * mm, 46 * mm, 46 * mm])
    legend.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    flow += [tb, legend, Spacer(1, 4 * mm)]
    return flow


def _part_table(part, spec, S):
    either = part.get("either_or")
    if either:
        head = ["No.", "Question", "Marks", "CO", "KL"]
        cw = [16 * mm, 106 * mm, 16 * mm, 21 * mm, 21 * mm]
    else:
        head = ["No.", "Question", "CO", "KL"]
        cw = [12 * mm, 130 * mm, 19 * mm, 19 * mm]
    data = [[_p(h, S["boldc"]) for h in head]]
    spans, nosplit = [], []
    for it in part["items"]:
        first_row = len(data)
        for oi, opt in enumerate(it["options"]):
            if either and oi == 1:
                data.append([_p("(OR)", S["boldc"])] + [""] * (len(head) - 1))
                spans.append(("SPAN", (0, len(data) - 1), (-1, len(data) - 1)))
            for pi, p in enumerate(opt["parts"]):
                label = ""
                if pi == 0:
                    label = f"{it['no']}." + (f" ({opt['label']})" if opt["label"] else "")
                    if either and oi == 1:
                        label = "(b)"
                text = p["text"]
                if len(opt["parts"]) > 1:
                    text = f"({'i' * (pi + 1) if pi < 3 else pi + 1}) {text}"
                row = [_p(label, S["body"]), _p(text, S["body"])]
                if either:
                    row.append(_p(str(p["marks"]), S["center"]))
                row += [_p(it["co"] if pi == 0 else "", S["center"]), _p(p["kl"], S["center"])]
                data.append(row)
        nosplit.append(("NOSPLIT", (0, first_row), (-1, len(data) - 1)))
    tb = Table(data, colWidths=cw, repeatRows=1)
    style = [("GRID", (0, 0), (-1, -1), 0.6, colors.black),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)] + spans + nosplit
    tb.setStyle(TableStyle(style))
    return tb


def _footer(canvas, doc, label):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8.5)
    canvas.drawString(15 * mm, 9 * mm, label)
    canvas.drawRightString(A4[0] - 15 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_paper(spec: dict, path: str) -> str:
    fr, fb = _fonts(_all_texts(spec))
    S = _styles(fr, fb)
    h, t = spec["header"], spec["paper_type"]
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=16 * mm,
                            title=f"{h.get('exam_title', 'Question Paper')} - {h.get('course', '')}",
                            author=h.get("college", ""))
    flow = _header_block(spec, S, fr, fb)
    for part in spec["parts"]:
        flow += [_p(P.part_title(part, t), S["partt"]), _p(P.part_instruction(part), S["instr"]),
                 Spacer(1, 1.5 * mm), _part_table(part, spec, S), Spacer(1, 4 * mm)]
    flow.append(_p("\u2014\u2014\u2014 End of Question Paper \u2014\u2014\u2014", S["center"]))
    if h.get("hod_status") is not None:
        hod = Table([[_p("HoD Sign", S["bold"]), ""], [_p(h.get("hod_status", ""), S["small"]), ""]],
                    colWidths=[45 * mm, 45 * mm], rowHeights=[10 * mm, 6 * mm], hAlign="RIGHT")
        hod.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                                 ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1))]))
        flow += [Spacer(1, 6 * mm), hod]
    label = (f"QP Code: {h.get('qp_code', '')}" if t == "SEM" else f"QP Set: {h.get('qp_set', '')}") + \
            f"   |   {h.get('course', '')[:70]}"
    doc.build(flow, onFirstPage=lambda c, d: _footer(c, d, label), onLaterPages=lambda c, d: _footer(c, d, label))
    return path


def render_blueprint(spec: dict, path: str) -> str:
    """Faculty / HoD page: KL distribution, CO distribution, question-wise KL with confidence and review flags."""
    fr, fb = _fonts(_all_texts(spec))
    S = _styles(fr, fb, size=10)
    h = spec["header"]
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title="Blueprint")
    total = sum(pt["total_marks"] for pt in spec["parts"]) or 1
    flow = [_p("Question Paper Blueprint (faculty / HoD copy - not for students)", S["college"]),
            _p(f"{h.get('exam_title', '')} \u00b7 {h.get('course', '')} \u00b7 Max. Marks {total}", S["aff"]),
            Spacer(1, 4 * mm), _p("Knowledge-level distribution", S["bold"]), Spacer(1, 1.5 * mm)]

    kd = P.kl_distribution(spec)
    rows = [[_p(x, S["boldc"]) for x in ["Level", "Name", "Marks", "Percentage"]]]
    for k in LEVELS:
        rows.append([_p(k, S["center"]), _p(LEVEL_NAMES[k], S["body"]), _p(f"{kd[k]:g}", S["center"]),
                     _p(f"{100 * kd[k] / total:.0f}%", S["center"])])
    t1 = Table(rows, colWidths=[22 * mm, 60 * mm, 30 * mm, 30 * mm])
    t1.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED"))]))
    flow += [t1, _p("Either-or questions: each option counts half of the question's marks.", S["small"]),
             Spacer(1, 4 * mm), _p("Course-outcome distribution", S["bold"]), Spacer(1, 1.5 * mm)]

    cd = P.co_distribution(spec)
    rows = [[_p(x, S["boldc"]) for x in ["CO", "Marks", "Percentage"]]]
    for co, m in cd.items():
        rows.append([_p(co, S["center"]), _p(f"{m:g}", S["center"]), _p(f"{100 * m / total:.0f}%", S["center"])])
    t2 = Table(rows, colWidths=[30 * mm, 30 * mm, 30 * mm])
    t2.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED"))]))
    flow += [t2, Spacer(1, 4 * mm), _p("Question-wise Knowledge Level (suggested by the model unless marked staff)", S["bold"]),
             Spacer(1, 1.5 * mm)]

    rows = [[_p(x, S["boldc"]) for x in ["Q", "CO", "KL", "By", "Conf.", "Check this because"]]]
    review_n = 0
    for part in spec["parts"]:
        for it in part["items"]:
            for opt in it["options"]:
                for pi, p in enumerate(opt["parts"]):
                    if not p["text"]:
                        continue
                    q = f"{it['no']}" + (f"({opt['label']})" if opt["label"] else "")
                    conf = f"{p['confidence']:.0%}" if p["confidence"] is not None else "-"
                    why = "; ".join(p["review"])
                    review_n += 1 if why else 0
                    rows.append([_p(q, S["center"]), _p(it["co"], S["center"]), _p(p["kl"], S["center"]),
                                 _p(p["kl_source"] or "-", S["center"]), _p(conf, S["center"]),
                                 _p(why or "-", S["small"])])
    t3 = Table(rows, colWidths=[16 * mm, 16 * mm, 14 * mm, 16 * mm, 16 * mm, 102 * mm], repeatRows=1)
    t3.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED"))]))
    flow += [t3, Spacer(1, 3 * mm),
             _p(f"{review_n} question(s) are flagged for a second look. Predicted levels are suggestions: "
                "Bloom's level depends on the intended task, so staff should confirm or override them.", S["small"])]
    doc.build(flow)
    return path
