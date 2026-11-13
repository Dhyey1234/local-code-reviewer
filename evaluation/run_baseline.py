
import json
from pathlib import Path
from mlx_lm import load, generate

# Read our evaluation dataset
dataset = Path("dataset/evaluation/baseline.jsonl")

examples = [
    json.loads(line)
    for line in dataset.read_text().splitlines()
    if line.strip()
]

# Load the local AI model once
print("Loading local model...")
model, tokenizer = load("mlx-community/Qwen2.5-1.5B-Instruct-4bit")

# Review each example
for example in examples:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Python code reviewer. "
                "Identify genuine bugs and explain their impact. "
                "Name the correct Python exceptions. "
                "Suggest a fix when needed. "
                "Do not invent problems."
            ),
        },
        {
            "role": "user",
            "content": f"Review this Python code:\n{example['code']}",
        },
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    review = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=300,
        verbose=False,
    )

    print(f"\n{'=' * 50}")
    print(f"TEST {example['id']}")
    print(f"{'=' * 50}")
    print("AI REVIEW:")
    print(review)
    print("\nEXPECTED:")
    print(example["expected"])
