
import ast


def analyze_code(code):
    findings = []

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return [{
            "issue": "SyntaxError",
            "message": str(error)
        }]

    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            if isinstance(node.slice, ast.Constant):
                if isinstance(node.slice.value, int):
                    findings.append({
                        "issue": "Potential IndexError",
                        "line": node.lineno,
                        "message": (
                            "Direct indexing may fail if "
                            "the collection is empty or "
                            "the index is out of range."
                        )
                    })

    return findings


if __name__ == "__main__":
    code = """
def first_item(items):
    return items[0]
"""

    results = analyze_code(code)

    for result in results:
        print(result)
