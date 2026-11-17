"""Bounded, process-local review queue for the local MLX model."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import BoundedSemaphore, Lock
from uuid import uuid4

from backend.db import save_review
from backend.review_service import ReviewService


class ReviewJobs:
    def __init__(self, max_pending=12):
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="codelens-ai")
        self.capacity = BoundedSemaphore(max_pending)
        self.lock = Lock()
        self.jobs = {}
        self.service = ReviewService()

    def submit(self, request):
        if not self.capacity.acquire(blocking=False):
            return None
        job_id = str(uuid4())
        now = datetime.now(timezone.utc)
        with self.lock:
            self._prune(now)
            self.jobs[job_id] = {"status": "queued", "result": None, "error": None, "created_at": now}
        try:
            self.executor.submit(self._run, job_id, request)
        except Exception:
            with self.lock:
                self.jobs.pop(job_id, None)
            self.capacity.release()
            raise
        return job_id

    def _run(self, job_id, request):
        try:
            with self.lock:
                self.jobs[job_id]["status"] = "running"
            result = self.service.run(request)
            result["review_id"] = save_review(
                request.code, result["language"], result["findings"],
                result["ai_review"], result["warnings"],
            )
            with self.lock:
                self.jobs[job_id].update(status="completed", result=result)
        except Exception as exc:
            with self.lock:
                self.jobs[job_id].update(status="failed", error=str(exc))
        finally:
            with self.lock:
                self.jobs[job_id]["finished_at"] = datetime.now(timezone.utc)
            self.capacity.release()

    def get(self, job_id):
        with self.lock:
            self._prune(datetime.now(timezone.utc))
            job = self.jobs.get(job_id)
            if job is None:
                return None
            return {k: job[k] for k in ("status", "result", "error")}

    def _prune(self, now):
        expiry = now - timedelta(hours=1)
        for key, job in list(self.jobs.items()):
            if job.get("finished_at", now) < expiry:
                del self.jobs[key]

    def shutdown(self):
        self.executor.shutdown(wait=True, cancel_futures=False)
