"""Code review orchestration, independent of HTTP and storage."""
from fastapi import HTTPException
from backend.multilang_analyzer import analyze_code, detect_language
from backend.local_reviewer import generate_review
from backend.pep8_checker import check_pep8


class ReviewService:
    """Coordinates language detection, static checks and local AI review."""

    def run(self, request):
        language = request.language
        if language == "auto":
            language = detect_language(request.code)
            if language is None:
                raise HTTPException(422, "Language is ambiguous. Please select it manually.")

        findings = analyze_code(request.code, language)
        style_findings, warnings = ([], [])
        if language == "python" and request.check_pep8:
            style_findings, warnings = check_pep8(request.code)

        ai_review = ""
        if request.use_ai:
            try:
                ai_review, model_warnings = generate_review(
                    request.code, findings, language=language,
                )
                warnings.extend(model_warnings)
            except Exception as exc:
                warnings.append(f"AI generation unavailable: {type(exc).__name__}: {exc}")
                ai_review = "AI review unavailable. Try again after checking the local model."

        return {
            "language": language,
            "findings": findings,
            "style_findings": style_findings,
            "ai_review": ai_review,
            "warnings": warnings,
        }
