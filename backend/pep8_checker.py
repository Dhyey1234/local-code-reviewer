"""Optional PEP 8 checks for Python using pycodestyle."""

def check_pep8(code: str):
    """Return (style findings, warnings); never treat style as runtime bugs."""
    try:
        import pycodestyle
    except ImportError:
        return [], ["PEP 8 checks unavailable: install pycodestyle from backend/requirements-api.txt"]

    # Use a custom report to capture errors without printing them.
    class Collector(pycodestyle.BaseReport):
        def __init__(self, options):
            super().__init__(options)
            self.items = []

        def error(self, line_number, offset, text, check):
            code_id = super().error(line_number, offset, text, check)
            if code_id:
                self.items.append({
                    "issue": f"PEP 8: {code_id}",
                    "line": line_number,
                    "message": text,
                })
            return code_id

    guide = pycodestyle.StyleGuide(quiet=True)
    report = Collector(guide.options)
    checker = pycodestyle.Checker(
        filename="snippet.py", lines=code.splitlines(keepends=True),
        options=guide.options, report=report,
    )
    checker.check_all()
    return report.items, []
