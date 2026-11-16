"""Optional conservative AST checks, independent of the legacy analyzer.
Does not execute code. Avoids claiming safe index access across branches/loops.
"""
import ast

def analyze(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [{"issue": "SyntaxError", "line": exc.lineno, "message": str(exc)}]
    findings = []
    def visit_block(statements, env):
        env = dict(env)
        for stmt in statements:
            # Track only straightforward list assignments; unknown changes invalidate knowledge.
            for node in ast.walk(stmt):
                if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.slice, ast.Constant) and type(node.slice.value) is int:
                    name = node.value.id if isinstance(node.value, ast.Name) else None
                    length = env.get(name)
                    if length is None or not (-length <= node.slice.value < length):
                        findings.append({"issue": "Potential IndexError", "line": node.lineno, "message": "Index may be out of range"})
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit_block(stmt.body, {})
            elif isinstance(stmt, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                # Do not assume assignments within control flow are unconditional.
                for child in ast.iter_child_nodes(stmt):
                    if isinstance(child, ast.stmt):
                        visit_block([child], {})
                    elif isinstance(child, list):
                        visit_block(child, {})
                env.clear()
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        env[target.id] = len(stmt.value.elts) if isinstance(stmt.value, ast.List) else None
            elif isinstance(stmt, ast.AugAssign) and isinstance(stmt.target, ast.Name):
                env.pop(stmt.target.id, None)
        return env
    visit_block(tree.body, {})
    return findings
