
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "backend")
)

from review_validator import validate_review


def test_valid_bug_review():
    review = """Status: BUG_FOUND
Issue: Potential IndexError
Impact: Empty list causes an exception.
Fix: Check whether the list is empty."""

    assert validate_review(review) == []


def test_valid_no_bug_review():
    review = """Status: NO_BUG
Issue: None
Impact: None
Fix: None"""

    assert validate_review(review) == []


def test_contradictory_review():
    review = """**Status:** NO_BUG
**Issue:** Potential IndexError
**Fix:** Check whether the list is empty."""

    issues = validate_review(review)

    assert any("Contradiction" in issue for issue in issues)


def test_missing_status():
    review = """Issue: IndexError
Impact: Runtime exception.
Fix: Check the list."""

    issues = validate_review(review)

    assert "Missing or invalid Status" in issues
