from fastapi.testclient import TestClient
from backend.api import app
from backend.pep8_checker import check_pep8
import backend.db as db


def test_review_without_ai(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "reviews.sqlite3")
    with TestClient(app) as client:
        response = client.post("/api/review", json={
            "language": "javascript", "code": "const x = null; console.log(x.name);",
            "use_ai": False,
        })
        assert response.status_code == 200
        assert response.json()["language"] == "javascript"
        assert "style_findings" in response.json()
        assert response.json()["style_findings"] == []


def test_python_style_result_or_missing_dependency():
    findings, warnings = check_pep8("x=1\n")
    assert any("E225" in item["issue"] for item in findings) or warnings
