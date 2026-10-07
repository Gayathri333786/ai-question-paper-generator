"""
Rule layer for Bloom's Knowledge Level (K1-K6) prediction.

This layer does NOT claim that a verb alone decides the level. It does three things:
  1. Splits the question into clauses and looks at the verb that *starts* each clause
     ("Define X and explain Y" -> K1 + K2; the highest level wins).
  2. Applies context patterns that override the plain verb
     ("Explain how to apply ..." -> K3, "Write a Python program ..." -> K3 even if it says "design").
  3. Adds weak floors from the whole sentence (numbers to calculate with -> at least K3, etc.).

Everything it used is returned as `evidence`, so a teacher can see WHY a level was suggested.
The ML model (model.py) learns from the full sentence and is blended with this layer.
"""
from __future__ import annotations

import re

LEVELS = ["K1", "K2", "K3", "K4", "K5", "K6"]
LEVEL_NAMES = {
    "K1": "Remembering", "K2": "Understanding", "K3": "Applying",
    "K4": "Analysing", "K5": "Evaluating", "K6": "Creating",
}
LEVEL_INDEX = {k: i for i, k in enumerate(LEVELS)}

# Verbs that, when they START a clause, signal a level.
VERBS = {
    "K1": ["define", "list", "state", "name", "identify", "recall", "mention", "enumerate",
           "label", "recogni[sz]e", "write down", "give the full form", "what (?:is|are|was|were)",
           "who", "when", "where", "how many", "tell", "write", "give the (?:definition|formula|syntax)"],
    "K2": ["explain", "describe", "discuss", "summari[sz]e", "differentiate", "distinguish",
           "illustrate", "interpret", "classify", "paraphrase", "outline", "elaborate",
           "give (?:an )?examples?", "why", "how (?:does|do|is|are|did)", "what (?:is|are) the (?:difference|need|purpose|role|significance)",
           "write (?:short )?notes?", "express", "convert", "extend", "represent", "relate"],
    "K3": ["calculate", "compute", "solve", "apply", "use", "using", "demonstrate", "implement",
           "find", "determine", "show", "execute", "simulate", "predict", "estimate", "perform",
           "trace", "plot", "construct", "draw", "evaluate the (?:expression|integral|function)",
           "obtain", "derive", "modify", "operate", "sketch", "complete", "run",
           "given", "consider", "how (?:would|can|could|will) you"],
    "K4": ["analy[sz]e", "compare", "contrast", "examine", "investigate", "inspect", "break down",
           "categori[sz]e", "infer", "differentiate between .* and analy[sz]e", "dissect",
           "diagnose", "deduce", "organi[sz]e", "attribute", "discriminate", "test"],
    "K5": ["evaluate", "justify", "critique", "critici[sz]e", "assess", "judge", "recommend",
           "defend", "appraise", "argue", "decide", "select the (?:best|most)", "prioriti[sz]e",
           "conclude", "validate", "support", "rate", "rank", "verify", "check whether", "measure"],
    "K6": ["design", "develop", "propose", "formulate", "create", "devise", "compose", "plan",
           "invent", "build", "generate", "synthesi[sz]e", "come up with", "construct a new",
           "suggest a new", "originate", "produce", "assemble", "hypothesi[sz]e", "predict a new"],
}

# Clause-level patterns: if a clause matches, its level is this, and the plain verb is ignored.
CLAUSE_PATTERNS = [
    # (regex, level, label)
    (r"\b(?:explain|describe|discuss|show|illustrate)\b.*\bhow (?:to|you|would you|can you|could you)\b.*\b(?:apply|use|solve|calculate|compute|find|implement|perform)\b",
     "K3", "'explain/describe how to apply/solve' is an application task"),
    (r"\b(?:outline|prepare|draft|draw up|sketch)\b.{0,10}\b(?:plan|strategy|proposal|roadmap)\b",
     "K6", "preparing a plan/strategy is a creating task"),
    (r"\b(?:write|develop|implement|create|build|code|design)\b.{0,30}\b(?:python |java |c\+\+ |c )?(?:program|function|code|script|query|snippet)\b",
     "K3", "writing a program/function/query is an application task"),
    (r"\bwhat is the (?:output|result|value)\b|\b(?:predict|find|trace|give|determine) the (?:output|result)\b",
     "K3", "tracing/predicting an output is an application task"),
    (r"\bwhat (?:is|are) the (?:difference|distinction)s?\b|\bdifference between\b",
     "K2", "'difference between' is an understanding task"),
    (r"\bwrite (?:short )?notes?\b|\bshort notes?\b",
     "K2", "'short notes' is an understanding task"),
    (r"\b(?:which|what) (?:\w+ ){0,3}(?:is|are) (?:best|better|most suitable|more suitable|best suited)\b|\bbest suited\b",
     "K5", "'which is best/better' needs a judgement"),
    (r"\bhow (?:can|could|would|do) you improve\b",
     "K5", "'how can you improve' needs a judgement"),
    (r"^(?:what|which) (?:is|are) (?:the )?(?:meaning|definition)\b",
     "K1", "asks for a definition"),
]

# Whole-sentence "floors": the level can never be LOWER than this when the signal is present.
GERUND_FLOORS = [
    (r"\b(?:by|through|after|and)\s+(?:analy[sz]ing|examining|comparing|contrasting|investigating)\b", "K4"),
    (r"\b(?:by|through|after|and)\s+(?:evaluating|justifying|assessing|critiquing|judging)\b", "K5"),
    (r"\b(?:by|through|after|and)\s+(?:designing|developing|proposing|formulating|creating)\b", "K6"),
]

_FILLER = re.compile(
    r"^(?:\s+|(?:please|kindly|briefly|also|then|next|finally|first|and|or|but|so|now|\w+ly)\b[\s,]*|"
    r"with the help of [^,]*,\s*|with reference to [^,]*,\s*|in (?:your own words|detail|brief)\b[\s,]*)+", re.I)
_NUMBERING = re.compile(r"^\s*(?:\(?[a-z0-9]{1,3}[\).:]\s+|q\.?\s*\d+[\).:]?\s*)+", re.I)
_CLAUSE_SPLIT = re.compile(r"[.?!;:]\s+|\s+and\s+|\s+then\s+|,\s+(?=[a-z])", re.I)
_NUMBER = re.compile(r"(?<![A-Za-z])-?\d+(?:\.\d+)?%?")


def _compile_verbs():
    out = []
    for lvl in LEVELS:
        for v in VERBS[lvl]:
            out.append((re.compile(r"^(?:" + v + r")\b", re.I), lvl, v))
    # longest pattern first so "what is the difference" beats "what is"
    out.sort(key=lambda t: -len(t[2]))
    return out


_VERB_RES = _compile_verbs()
_PATTERN_RES = [(re.compile(p, re.I), lvl, why) for p, lvl, why in CLAUSE_PATTERNS]
_GERUND_RES = [(re.compile(p, re.I), lvl) for p, lvl in GERUND_FLOORS]


def split_clauses(text: str) -> list[str]:
    text = _NUMBERING.sub("", text.strip())
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(text) if p and p.strip()]
    return parts or [text]


def _lead_verb(clause: str):
    c = _FILLER.sub("", clause.strip()).strip()
    for rx, lvl, name in _VERB_RES:
        m = rx.match(c)
        if m:
            return lvl, m.group(0).lower()
    return None, None


def analyse(question: str) -> dict:
    """Return {'level','scores','clause_levels','evidence','abstained'} for one question."""
    q = question.strip()
    scores = {k: 0.0 for k in LEVELS}
    evidence: list[str] = []
    clause_levels: list[str] = []

    # clause-level pass: patterns first (on the whole question for multi-word patterns)
    whole_hit = None
    for rx, lvl, why in _PATTERN_RES:
        if rx.search(q):
            whole_hit = (lvl, why)
            break

    handled_by_pattern = set()
    if whole_hit:
        lvl, why = whole_hit
        scores[lvl] += 2.0
        clause_levels.append(lvl)
        evidence.append(f"pattern -> {lvl}: {why}")

    for i, clause in enumerate(split_clauses(q)):
        # a clause that triggered a pattern should not also be judged by its raw verb
        if whole_hit and any(rx.search(clause) for rx, l, _ in _PATTERN_RES if l == whole_hit[0]):
            handled_by_pattern.add(i)
            continue
        lvl, verb = _lead_verb(clause)
        if lvl:
            weight = 1.0 if i == 0 else 0.8
            scores[lvl] += weight
            clause_levels.append(lvl)
            evidence.append(f"clause '{clause[:40]}' starts with '{verb}' -> {lvl}")

    # whole-sentence floors
    floor = None
    nums = _NUMBER.findall(q)
    if len(nums) >= 3:
        floor = "K3"
        scores["K3"] += 0.8
        evidence.append(f"{len(nums)} numbers in the question -> calculation, floor K3")
    for rx, lvl in _GERUND_RES:
        if rx.search(q):
            scores[lvl] += 0.8
            clause_levels.append(lvl)
            evidence.append(f"'by/and + gerund' signal -> {lvl}")
            if floor is None or LEVEL_INDEX[lvl] > LEVEL_INDEX[floor]:
                floor = lvl

    level = None
    if clause_levels or floor:
        cands = list(clause_levels) + ([floor] if floor else [])
        level = max(cands, key=lambda l: LEVEL_INDEX[l])   # highest level named in the question wins

    return {
        "level": level,
        "scores": scores,
        "clause_levels": clause_levels,
        "evidence": evidence,
        "abstained": level is None,
    }


def rule_features(question: str) -> list[float]:
    """13-dim feature vector for the ML model: 6 scores, 6 one-hot of rule level, 1 abstain flag."""
    a = analyse(question)
    s = [min(a["scores"][k], 2.0) / 2.0 for k in LEVELS]
    oh = [1.0 if a["level"] == k else 0.0 for k in LEVELS]
    return s + oh + [1.0 if a["abstained"] else 0.0]


def predict_level(question: str, fallback: str = "K2") -> str:
    """Rules-only prediction (used for baseline comparison)."""
    return analyse(question)["level"] or fallback
