"""Default frameworks for the two paper types. Everything here is editable in the app / JSON spec."""

COLLEGE = "VELALAR COLLEGE OF ENGINEERING AND TECHNOLOGY"
AFFILIATION = "(An Autonomous Institution, Affiliated to Anna University, Chennai)"

PRESETS = {
    # CAT: QP set, 60 marks, 2 hrs  (Part A 12 x 2 = 24, Part B 3 x 12 = 36, either-or)
    "CAT": {
        "paper_type": "CAT",
        "header": {
            "college": COLLEGE, "affiliation": AFFILIATION,
            "exam_title": "Continuous Assessment Test - I",
            "qp_set": "I", "regulations": "2022",
            "programme": "B.Tech - AI&DS", "semester": "3",
            "max_marks": "60", "duration": "2 Hrs",
            "course": "", "class_name": "", "date": "", "time": "",
            "hod_status": "Waiting for approval",
        },
        "parts": [
            {"name": "A", "num_questions": 12, "marks_each": 2, "either_or": False,
             "co_plan": {"CO1": 6, "CO2": 6}, "questions": []},
            {"name": "B", "num_questions": 3, "marks_each": 12, "either_or": True,
             "co_plan": {"CO1": 1, "CO2": 1, "CO3": 1}, "questions": []},
        ],
    },
    # Semester: QP code + exam year, 100 marks, 3 hrs (Anna University style A=10x2, B=5x13, C=1x15)
    "SEM": {
        "paper_type": "SEM",
        "header": {
            "college": COLLEGE, "affiliation": AFFILIATION,
            "exam_title": "Semester Examinations",
            "qp_code": "", "exam_year": "NOV/DEC 2026", "regulations": "2022",
            "programme": "B.Tech - AI&DS", "semester": "3",
            "max_marks": "100", "duration": "3 Hrs",
            "course": "", "class_name": "", "date": "", "time": "",
            "hod_status": "Waiting for approval",
        },
        "parts": [
            {"name": "A", "num_questions": 10, "marks_each": 2, "either_or": False,
             "co_plan": {"CO1": 2, "CO2": 2, "CO3": 2, "CO4": 2, "CO5": 2}, "questions": []},
            {"name": "B", "num_questions": 5, "marks_each": 13, "either_or": True,
             "co_plan": {"CO1": 1, "CO2": 1, "CO3": 1, "CO4": 1, "CO5": 1}, "questions": []},
            {"name": "C", "num_questions": 1, "marks_each": 15, "either_or": True,
             "co_plan": {"CO5": 1}, "questions": []},
        ],
    },
}
