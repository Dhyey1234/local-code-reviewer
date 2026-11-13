
import json
from pathlib import Path

path = Path("dataset/train/train.jsonl")
seen = set()
valid = 0

for line_number, line in enumerate(path.read_text().splitlines(), 1):
    if not line.strip():
        continue

    example = json.loads(line)
    messages = example["messages"]

    assert [m["role"] for m in messages] == [
        "system", "user", "assistant"
    ], f"Invalid roles on line {line_number}"

    review = messages[-1]["content"]

    for field in ["Status:", "Issue:", "Impact:", "Fix:"]:
        assert field in review, (
            f"Missing {field} on line {line_number}"
        )

    status = review.splitlines()[0]
    assert status in [
        "Status: BUG_FOUND",
        "Status: NO_BUG"
    ], f"Invalid status on line {line_number}"

    code = messages[1]["content"]
    assert code not in seen, (
        f"Duplicate code on line {line_number}"
    )

    seen.add(code)
    valid += 1

print(f"Dataset validation passed: {valid} examples")
