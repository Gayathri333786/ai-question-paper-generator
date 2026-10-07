"""Run:  python tests/test_core.py   (no pytest needed)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kl_engine import load_default
from qp import paper

m = load_default()
cases = {
    "Define data science.": "K1",
    "Explain how to apply Dijkstra's algorithm to the given graph.": "K3",
    "Compare two algorithms and evaluate their efficiency.": "K5",
    "Define overfitting and explain how it can be avoided.": "K2",
    "Write a Python program to design a simple calculator.": "K3",
    "Design a recommender system for an online bookstore.": "K6",
}
for q, k in cases.items():
    assert m.predict(q).level == k, (q, m.predict(q).level, k)

assert paper.expand_co_plan({"CO1": 2, "CO2": 1}, 4) == ["CO1", "CO1", "CO2", ""]
spec = paper.normalize_spec({"paper_type": "CAT", "header": {"max_marks": "60"}, "parts": [
    {"name": "A", "num_questions": 12, "marks_each": 2, "co_plan": {"CO1": 12}, "questions": []},
    {"name": "B", "num_questions": 3, "marks_each": 12, "either_or": True, "co_plan": {"CO1": 3}, "questions": []}]})
assert spec["parts"][1]["items"][0]["no"] == 13
assert sum(paper.kl_distribution(paper.apply_kl(spec, m)).values()) == 0
print("all tests passed")
