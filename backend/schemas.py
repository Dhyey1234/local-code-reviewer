"""Request schemas shared by the API routes."""
from typing import Literal
from pydantic import BaseModel, Field

Language = Literal["auto", "python", "javascript", "typescript", "java", "cpp", "csharp"]


class ReviewRequest(BaseModel):
    code: str = Field(min_length=1, max_length=30000)
    language: Language = "auto"
    use_ai: bool = True
    check_pep8: bool = True


class FeedbackRequest(BaseModel):
    review_id: str
    verdict: Literal["correct", "incorrect"]
    correction: str = Field(default="", max_length=10000)
