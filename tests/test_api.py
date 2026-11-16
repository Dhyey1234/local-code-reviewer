import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import backend.api as api

def test_health():
    with TestClient(api.app) as client:
        assert client.get('/api/health').json()['status'] == 'ok'

def test_review_and_feedback(monkeypatch, tmp_path):
    monkeypatch.setattr(api, 'DB_PATH', tmp_path / 'feedback.sqlite3')
    with TestClient(api.app) as client:
        response = client.post('/api/review', json={'code':'def f(x):\n    return x[0]','use_ai':False})
        assert response.status_code == 200
        review_id = response.json()['review_id']
        assert review_id
        saved = client.post('/api/feedback', json={'review_id':review_id,'verdict':'incorrect','correction':'Check empty input'})
        assert saved.status_code == 201
        assert saved.json()['used_for_training'] is False
        assert client.post('/api/feedback', json={'review_id':'missing','verdict':'correct'}).status_code == 404
