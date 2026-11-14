
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

    def analyze_block(statements, known_lists):
        for statement in statements:

            # Check indexing before updating assignments
            for node in ast.walk(statement):
                if not isinstance(node, ast.Subscript):
                    continue

                if not isinstance(node.slice, ast.Constant):
                    continue

                index = node.slice.value

                if type(index) is not int:
                    continue

                if isinstance(node.value, ast.Name):
                    name = node.value.id

                    if name in known_lists:
                        length = known_lists[name]

                        if -length <= index < length:
                            continue

                findings.append({
                    "issue": "Potential IndexError",
                    "line": node.lineno,
                    "message": (
                        "Direct indexing may fail if the collection "
                        "is empty or the index is out of range."
                    )
                })

            # Update list lengths after examining statement
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        if isinstance(statement.value, ast.List):
                            known_lists[target.id] = len(
                                statement.value.elts
                            )
                        else:
                            known_lists.pop(target.id, None)

    analyze_block(tree.body, {})

    return findings


if __name__ == "__main__":
    code = """
numbers = []
print(numbers[2])
numbers = [10, 20, 30]
"""

    print(analyze_code(code))
