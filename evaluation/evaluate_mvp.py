"""Run baseline static checks on the reserved evaluation set.
Usage: python -m evaluation.evaluate_mvp
This is a smoke test, NOT an accuracy estimate for AI reviews.
"""
import json
from pathlib import Path
from backend.static_analyzer import analyze_code

path = Path(__file__).resolve().parents[1] / "dataset/evaluation/baseline.jsonl"
for line in path.read_text().splitlines():
    if not line.strip():
        continue
    case = json.loads(line)
    print("Case:", case.get("id", "?"))
    print("Static findings:", analyze_code(case.get("code", "")))
