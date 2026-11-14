
import re


def extract_field(review, field):
    pattern = rf"^\s*\**{field}\**\s*:\**\s*(.+)$"

    match = re.search(
        pattern,
        review,
        re.MULTILINE | re.IGNORECASE,
    )

    return match.group(1).strip() if match else None


def validate_review(review):
    issues = []

    status = extract_field(review, "Status")
    issue = extract_field(review, "Issue")

    if status not in ("BUG_FOUND", "NO_BUG"):
        issues.append("Missing or invalid Status")

    if issue is None:
        issues.append("Missing Issue field")

    if issues:
        return issues

    no_issue_values = ("none", "no issue", "no issues")

    if status == "NO_BUG" and issue.lower() not in no_issue_values:
        issues.append(
            "Contradiction: NO_BUG status with a reported issue"
        )

    if status == "BUG_FOUND" and issue.lower() in no_issue_values:
        issues.append(
            "Contradiction: BUG_FOUND status without an issue"
        )

    return issues
