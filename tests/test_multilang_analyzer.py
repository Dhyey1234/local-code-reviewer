import pytest
from backend.multilang_analyzer import analyze_code, detect_language

@pytest.mark.parametrize('language,code,issue', [
    ('javascript', 'const user = null;\nconsole.log(user.name);', 'null'),
    ('typescript', 'const count: number = 0;\nconst result = 100 / count;', 'division'),
    ('java', 'String name = null;\nSystem.out.println(name.length());', 'null'),
    ('cpp', 'std::vector<int> numbers = {10,20,30};\nstd::cout << numbers[5];', 'index'),
    ('csharp', 'int count = 0;\nint avg = 100 / count;', 'division'),
    ('python', 'def first(items):\n    return items[0]', 'index'),
])
def test_language_checks(language, code, issue):
    findings = analyze_code(code, language)
    assert any(issue in f['issue'].lower() for f in findings), findings

@pytest.mark.parametrize('code,expected', [
    ('def first(items):\n    return items[0]', 'python'),
    ('console.log("hello");', 'javascript'),
    ('const count: number = 0;', 'typescript'),
    ('System.out.println("hello");', 'java'),
    ('#include <iostream>\nint main() {}', 'cpp'),
    ('using System;\nConsole.WriteLine("hello");', 'csharp'),
    ('x = 10', None),
])
def test_detection(code, expected):
    assert detect_language(code) == expected
