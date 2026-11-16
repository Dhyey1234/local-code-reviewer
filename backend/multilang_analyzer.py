"""Conservative, dependency-free pattern checks for six languages.

These checks are NOT a compiler, type checker, or full control-flow analyzer.
Findings are potential bugs; they do not prove runtime failure.
"""
import re
from backend.static_analyzer import analyze_code as analyze_python

LANGUAGES = ('python', 'javascript', 'typescript', 'java', 'cpp', 'csharp')


def detect_language(code: str):
    """Return a language only when distinctive syntax provides a strong signal."""
    rules = [
        ('python', [r'(?m)^\s*(?:def|async def)\s+\w+\s*\(', r'(?m)^\s*(?:from\s+\w+\s+import|import\s+\w+)', r'(?m)^\s*class\s+\w+\s*:', r'(?m)^\s*if\s+.+:\s*$']),
        ('typescript', [r'\b(?:interface|type)\s+\w+\s*[={]', r'\b(?:const|let)\s+\w+\s*:\s*(?:number|string|boolean)', r'\bfunction\s+\w+\([^)]*:\s*(?:number|string|boolean)', r'\)\s*:\s*(?:number|string|boolean)\s*\{']),
        ('java', [r'\bpublic\s+(?:static\s+)?class\s+\w+', r'\bSystem\.out\.', r'\bpublic\s+static\s+void\s+main\s*\(']),
        ('cpp', [r'#include\s*[<"]', r'\bstd::', r'\busing\s+namespace\s+std\b', r'\b(?:cout|cin)\s*<<', r'\bvector\s*<']),
        ('csharp', [r'\busing\s+System\s*;', r'\bConsole\.Write(?:Line)?\s*\(', r'\bnamespace\s+\w+\s*\{', r'\bstatic\s+void\s+Main\s*\(']),
        ('javascript', [r'\b(?:const|let|var)\s+\w+\s*=', r'\bconsole\.log\s*\(', r'\bfunction\s+\w+\s*\(', r'=>\s*\{']),
    ]
    scores = {language: sum(bool(re.search(pattern, code)) for pattern in patterns) for language, patterns in rules}
    # Distinctive typed declarations outrank generic JS declarations.
    if scores['typescript'] and re.search(r'\b(?:const|let)\s+\w+\s*:\s*(?:number|string|boolean)', code):
        return 'typescript'
    highest = max(scores.values(), default=0)
    if highest == 0:
        return None
    winners = [language for language, score in scores.items() if score == highest]
    # A single shared marker (e.g. 'function') is not sufficient to infer a language.
    if len(winners) != 1 or (highest == 1 and winners[0] == 'javascript' and re.search(r'\bfunction\b', code)):
        return None
    return winners[0]


def analyze_code(code: str, language: str):
    if language not in LANGUAGES:
        raise ValueError(f'Unsupported language: {language}')
    if language == 'python':
        return analyze_python(code)

    findings = []
    lines = code.splitlines()
    null_vars = set()
    zero_vars = set()
    known_lengths = {}
    # Simple sequential tracking only. No cross-function or branch guarantees.
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('//') or stripped.startswith('*'):
            continue
        # Basic literal assignments, including typed declarations.
        match = re.match(r'^(?:(?:const|let|var|int|double|float|String|string|object|auto|var|[\w<>\[\],]+)\s+)?([A-Za-z_]\w*)(?:\s*:\s*[A-Za-z_]\w*)?\s*=\s*(null|nullptr|0)\s*;', stripped)
        if match:
            name, value = match.groups()
            if value == '0':
                zero_vars.add(name)
                null_vars.discard(name)
            else:
                null_vars.add(name)
                zero_vars.discard(name)
        # Only literal zero divisors and variables assigned literal zero.
        for m in re.finditer(r'(?<!/)/(?![/*=])\s*(0|[A-Za-z_]\w*)\b', line):
            divisor = m.group(1)
            if divisor == '0' or divisor in zero_vars:
                findings.append({'issue': 'Possible division by zero', 'line': number,
                                 'message': f'Divisor {divisor} is zero in the simple assignment pattern; check before dividing.'})
        for name in list(null_vars):
            if re.search(r'\b' + re.escape(name) + r'\s*(?:\.|->)\s*[A-Za-z_]\w*', line) and not re.search(r'\b' + re.escape(name) + r'\s*(?:\?\.|\?->)', line):
                # Skip obvious guards on the same line.
                if not re.search(r'\b' + re.escape(name) + r'\s*!=\s*null', line):
                    findings.append({'issue': 'Possible null dereference', 'line': number,
                                     'message': f'{name} was assigned null; member access may fail.'})
        # C++ vector initialization, JS/TS arrays, Java/C# arrays with initializer.
        array = re.search(r'\b([A-Za-z_]\w*)\s*=\s*(?:new\s+\w+\s*\[\]\s*)?\{([^{}]*)\}\s*;', line)
        js_array = re.search(r'\b([A-Za-z_]\w*)\s*=\s*\[([^\[\]]*)\]\s*;', line)
        cpp_vector = re.search(r'\b([A-Za-z_]\w*)\s*=\s*\{([^{}]*)\}\s*;', line)
        array = js_array if language in ('javascript', 'typescript') else (array or cpp_vector)
        if array:
            known_lengths[array.group(1)] = len([x for x in array.group(2).split(',') if x.strip()])
        for access in re.finditer(r'\b([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]', line):
            name, index = access.group(1), int(access.group(2))
            if name in known_lengths and index >= known_lengths[name]:
                findings.append({'issue': 'Out-of-bounds index', 'line': number,
                                 'message': f'{name} has {known_lengths[name]} literal elements, but index {index} is accessed.'})
    return findings
