"""
Question-paper model: normalise a spec, assign COs, predict KLs, validate, summarise.

Raw spec (what the app / JSON file holds):
{
  "paper_type": "CAT" | "SEM",
  "header": {...},                       # see presets.py
  "parts": [
    {"name": "A", "num_questions": 12, "marks_each": 2, "either_or": false,
     "co_plan": {"CO1": 6, "CO2": 6},    # faculty chooses COs and how many questions each, in sequence
     "questions": [ {"text": "..."}, ... ]},
    {"name": "B", "num_questions": 3, "marks_each": 12, "either_or": true,
     "co_plan": {"CO1": 1, "CO2": 1, "CO3": 1},   # one CO per question number; (a) and (b) share it
     "questions": [ {"a": {"text": "..."}, "b": {"parts": [{"text": "(i)..", "marks": 6}, {"text": "(ii)..", "marks": 6}]}} ]}
  ]
}
A question / option may carry "kl" (staff override) and "co" (item-level CO override).
"""
from __future__ import annotations

import copy
from collections import OrderedDict

from kl_engine.rules import LEVELS


def expand_co_plan(plan: dict, total: int) -> list[str]:
    """{'CO1': 5, 'CO2': 4, 'CO3': 3} -> ['CO1']*5 + ['CO2']*4 + ['CO3']*3  (sequence order)."""
    seq: list[str] = []
    for co, n in plan.items():
        seq += [co] * int(n)
    return seq[:total] + [""] * max(0, total - len(seq))


def _norm_option(raw: dict | None, marks_each: int) -> dict:
    raw = raw or {}
    if raw.get("parts"):
        parts = [{"text": (p.get("text") or "").strip(), "marks": int(p.get("marks", 0)),
                  "kl": (p.get("kl") or "").strip().upper()} for p in raw["parts"]]
    else:
        parts = [{"text": (raw.get("text") or "").strip(), "marks": int(raw.get("marks", marks_each)),
                  "kl": (raw.get("kl") or "").strip().upper()}]
    for p in parts:
        p["kl_source"] = "staff" if p["kl"] else ""
        p["confidence"] = None
        p["review"] = []
    return {"parts": parts}


def normalize_spec(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    s.setdefault("header", {})
    next_no = 1
    for part in s["parts"]:
        n, marks = int(part["num_questions"]), int(part["marks_each"])
        part["num_questions"], part["marks_each"] = n, marks
        cos = expand_co_plan(part.get("co_plan") or {}, n)
        raw_q = part.get("questions") or []
        items = []
        for i in range(n):
            rq = raw_q[i] if i < len(raw_q) else {}
            co = (rq.get("co") or cos[i]).strip()
            if part.get("either_or"):
                opts = [dict(_norm_option(rq.get("a"), marks), label="a"),
                        dict(_norm_option(rq.get("b"), marks), label="b")]
            else:
                opts = [dict(_norm_option(rq, marks), label=None)]
            items.append({"no": next_no + i, "co": co, "options": opts})
        part["items"] = items
        part["start_no"] = next_no
        part["total_marks"] = n * marks
        next_no += n
    return s


def apply_kl(spec: dict, predictor) -> dict:
    """Fill in KL for every part with text and no staff override (batch prediction)."""
    todo = []
    for part in spec["parts"]:
        for it in part["items"]:
            for opt in it["options"]:
                for p in opt["parts"]:
                    if p["text"] and not p["kl"]:
                        todo.append(p)
    if todo and predictor is not None:
        preds = predictor.predict_many([p["text"] for p in todo], [p["marks"] for p in todo])
        for p, pr in zip(todo, preds):
            p["kl"], p["kl_source"] = pr.level, "model"
            p["confidence"], p["review"] = round(pr.confidence, 3), pr.reasons
    return spec


def validate(spec: dict) -> list[str]:
    """Human-readable problems; empty list = good to print."""
    w = []
    total = 0
    for part in spec["parts"]:
        name = part["name"]
        total += part["total_marks"]
        plan_total = sum(int(v) for v in (part.get("co_plan") or {}).values())
        if plan_total != part["num_questions"]:
            w.append(f"Part {name}: CO plan covers {plan_total} questions but the part has {part['num_questions']}.")
        for it in part["items"]:
            for opt in it["options"]:
                lab = f"Q{it['no']}" + (f"({opt['label']})" if opt["label"] else "")
                if not any(p["text"] for p in opt["parts"]):
                    w.append(f"{lab}: question text is empty.")
                if len(opt["parts"]) > 1 and sum(p["marks"] for p in opt["parts"]) != part["marks_each"]:
                    w.append(f"{lab}: sub-part marks add up to {sum(p['marks'] for p in opt['parts'])}, expected {part['marks_each']}.")
    try:
        mm = int(str(spec["header"].get("max_marks", "")).strip())
        if mm != total:
            w.append(f"Max. marks in header is {mm} but the parts add up to {total}.")
    except ValueError:
        w.append("Max. marks in the header is not a number.")
    return w


def kl_distribution(spec: dict) -> "OrderedDict[str, float]":
    """Marks per KL. For either-or questions each option counts half of the marks (so the total is exact)."""
    d = OrderedDict((k, 0.0) for k in LEVELS)
    for part in spec["parts"]:
        for it in part["items"]:
            share = 0.5 if part.get("either_or") else 1.0
            for opt in it["options"]:
                for p in opt["parts"]:
                    if p["kl"] in d:
                        d[p["kl"]] += p["marks"] * share
    return d


def co_distribution(spec: dict) -> "OrderedDict[str, float]":
    d: OrderedDict[str, float] = OrderedDict()
    for part in spec["parts"]:
        for it in part["items"]:
            if it["co"]:
                d[it["co"]] = d.get(it["co"], 0.0) + part["marks_each"]
    return OrderedDict(sorted(d.items()))


def part_title(part: dict, paper_type: str) -> str:
    n, m, t = part["num_questions"], part["marks_each"], part["total_marks"]
    return f"Part {part['name']} – {n} × {m} = {t} Marks"


def part_instruction(part: dict) -> str:
    if part.get("either_or"):
        return "Answer ALL questions, choosing either (a) or (b) in each."
    return "Answer ALL questions."
