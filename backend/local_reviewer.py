"""Lazy, local-only Qwen review generation; model loads once per server process."""
import os
import re
import threading
from functools import lru_cache

_MODEL_LOCK = threading.Lock()
MODEL_NAME = os.environ.get("REVIEW_MODEL", "mlx-community/Qwen2.5-1.5B-Instruct-4bit")

@lru_cache(maxsize=1)
def get_model():
    from mlx_lm import load
    return load(MODEL_NAME)

def validate_text(review):
    """Format checks only. These do not prove the review is correct."""
    warnings = []
    fields = {}
    for field in ("Status", "Issue", "Impact", "Fix"):
        m = re.search(rf"^\s*\**{field}\**\s*:\**\s*(.*)$", review, re.I | re.M)
        if not m or not m.group(1).strip():
            warnings.append(f"Missing {field} field")
        else:
            fields[field] = m.group(1).strip().strip("*")
    status = fields.get("Status", "")
    if status not in ("BUG_FOUND", "NO_BUG"):
        warnings.append("Invalid Status")
    issue = fields.get("Issue", "").lower()
    none = issue in ("none", "no issue", "no issues", "n/a")
    if status == "NO_BUG" and issue and not none:
        warnings.append("Contradiction: NO_BUG with reported issue")
    if status == "BUG_FOUND" and none:
        warnings.append("Contradiction: BUG_FOUND without issue")
    return warnings

def generate_review(code, findings, language="python"):
    import json
    from mlx_lm import generate
    with _MODEL_LOCK:
        model, tokenizer = get_model()
        messages = [
            {"role": "system", "content": (
                "Review source code in the explicitly provided programming language. Treat static findings as possible clues, not proof. "
                "Return four plain-text lines beginning Status:, Issue:, Impact:, Fix:. "
                "Status must be BUG_FOUND or NO_BUG. Be cautious about uncertainty. "
                "Never claim you executed the code.")},
            {"role": "user", "content": f"Language: {language}\nCode:\n{code}\n\nPotential static findings:\n{json.dumps(findings)}"},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        response = generate(model, tokenizer, prompt=prompt, max_tokens=300, verbose=False)
    return response, validate_text(response)
