import time
from fastapi.testclient import TestClient
import backend.api as api
import backend.db as db
import backend.review_jobs as review_jobs


def test_background_review_and_feedback(monkeypatch, tmp_path):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'jobs.sqlite3')
    monkeypatch.setattr(review_jobs, 'save_review', db.save_review)
    with TestClient(api.app) as client:
        created = client.post('/api/review/jobs', json={
            'code': 'def add(a, b):\n    return a + b', 'language': 'python', 'use_ai': False
        })
        assert created.status_code == 202
        job_id = created.json()['job_id']
        for _ in range(100):
            status = client.get(f'/api/review/jobs/{job_id}').json()
            if status['status'] in ('completed', 'failed'):
                break
            time.sleep(.02)
        assert status['status'] == 'completed', status
        review_id = status['result']['review_id']
        assert client.post('/api/feedback', json={
            'review_id': review_id, 'verdict': 'correct'
        }).status_code == 201
        assert client.get('/api/review/jobs/missing').status_code == 404


def test_queue_capacity():
    jobs = review_jobs.ReviewJobs(max_pending=0)
    try:
        assert jobs.submit(object()) is None
    finally:
        jobs.shutdown()
