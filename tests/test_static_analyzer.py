
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "backend")
)

from static_analyzer import analyze_code


def test_potential_index_error():
    code = """
def first_item(items):
    return items[0]
"""
    findings = analyze_code(code)

    assert any(
        f["issue"] == "Potential IndexError"
        for f in findings
    )


def test_valid_addition():
    code = """
def add(a, b):
    return a + b
"""
    assert analyze_code(code) == []


def test_syntax_error():
    code = "def broken(:"

    findings = analyze_code(code)

    assert findings[0]["issue"] == "SyntaxError"


def test_direct_indexing():
    code = """
numbers = [10, 20, 30]
print(numbers[2])
"""
    findings = analyze_code(code)

    # Safe indexing should not produce a warning.
    assert findings == []

def test_out_of_range_index():
    code = """
numbers = [10, 20, 30]
print(numbers[5])
"""
    findings = analyze_code(code)

    assert any(
        f["issue"] == "Potential IndexError"
        for f in findings
    )

def test_reassigned_empty_list():
    code = """
numbers = [10, 20, 30]
numbers = []
print(numbers[2])
"""
    findings = analyze_code(code)

    assert any(
        f["issue"] == "Potential IndexError"
        for f in findings
    )

def test_index_before_reassignment():
    code = """
numbers = []
print(numbers[2])
numbers = [10, 20, 30]
"""
    findings = analyze_code(code)

    assert any(
        f["issue"] == "Potential IndexError"
        for f in findings
    )

