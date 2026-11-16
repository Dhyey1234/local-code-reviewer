# Local Code Reviewer MVP overlay

This is an **additive overlay** for your existing `local-code-reviewer` repository. It does not replace your `backend/static_analyzer.py`, `backend/review_engine.py`, `backend/review_validator.py`, existing tests, datasets, or LoRA adapters.

## Install

From project root with your Python 3.12 virtual environment activated:

```bash
python -m pip install -r backend/requirements-api.txt
cd frontend && npm install && cd ..
```

## Start (two terminals)

Terminal 1:
```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:
```bash
cd frontend
npm run dev
```

Open http://127.0.0.1:5173. The frontend proxies `/api` to the backend. The local MLX model is loaded on the first AI-enabled review and cached afterward; the first review can take longer.

## Tests

```bash
python -m pytest tests/ -v
cd frontend && npm run build
```

## API

- `GET /api/health`
- `POST /api/review` with `{"code":"...", "use_ai":true}`
- `POST /api/feedback` with `{"review_id":"...", "verdict":"correct|incorrect", "correction":"..."}`

Feedback is stored in `data/feedback.sqlite3`. It is **not** automatically used to train the model. Review the feedback, curate examples, and compare against a held-out evaluation set before retraining.

## Limitations

- Current API uses the existing `static_analyzer.py`, which is still limited in its understanding of function bodies, control flow, mutations, and aliasing.
- The optional `advanced_analyzer.py` is experimental and **not connected** to the API; do not treat it as a production analyzer.
- A model-generated review is not verified correct by formatting checks. The frontend displays warnings rather than claiming correctness.
- This MVP is local-only, with no authentication. Do not expose port 8000 to the internet.
- MLX model may need a first-time download if not already cached; normal inference uses local model weights, not a hosted AI API.
- The frontend stylesheet loads an optional Google Font over the internet; remove the `@import` line for a strictly offline UI (system fonts will be used).
- `evaluation/evaluate_mvp.py` is an exploratory static smoke test and assumes baseline JSONL records contain a `code` field; adapt if your dataset uses a different schema.
- `backend/api.py` runs inference synchronously; do not use for multiple concurrent users without queueing or worker isolation.

## Next milestones

1. Harden scope-aware static analysis and extend tests for branches, functions, and mutations.
2. Add structured review parsing and per-finding evidence, with confidence calibration.
3. Build curated feedback export, reproducible LoRA training, and independent held-out model comparison.
4. Add limits, observability, packaging, and security review before sharing publicly.
