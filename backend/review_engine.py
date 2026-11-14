
import json
from mlx_lm import load, generate
from static_analyzer import analyze_code
from review_validator import validate_review
MODEL_NAME = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"


def review_code(code):
    # Step 1: Analyze code without executing it
    findings = analyze_code(code)

    # Step 2: Prepare evidence for the AI
    evidence = json.dumps(findings, indent=2)

    # Step 3: Load our local model
    model, tokenizer = load(MODEL_NAME)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Python code reviewer. "
                "Use static analysis findings as potential clues, "
                "not guaranteed bugs. "
                "Check the code carefully before reporting issues. "
                "Respond using Status, Issue, Impact, and Fix. "
                "Use BUG_FOUND or NO_BUG for Status."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Python code:\n{code}\n\n"
                f"Static analysis findings:\n{evidence}"
            ),
        },
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=300,
        verbose=False,
    )

    return findings, response


if __name__ == "__main__":
    sample_code = """
def first_item(items):
    return items[0]
"""

    findings, review = review_code(sample_code)

    print("\nSTATIC ANALYSIS:")
    print(json.dumps(findings, indent=2))

    print("\nAI REVIEW:")
    print(review)
print("\nVALIDATION:")
validation_issues = validate_review(review)

if validation_issues:
    for issue in validation_issues:
        print("WARNING:", issue)
else:
    print("Review format and status are consistent.")