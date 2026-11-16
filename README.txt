CodeLens frontend redesign

From ~/Projects/local-code-reviewer, back up existing files first:
  cp frontend/src/App.tsx frontend/src/App.tsx.bak
  cp frontend/src/style.css frontend/src/style.css.bak

Unzip this archive from the project root, overwriting only frontend/src/App.tsx and frontend/src/style.css:
  unzip -o ~/Downloads/codelens-frontend-redesign.zip

Then:
  cd frontend
  npm run build
  npm run dev

No backend changes. Existing API routes /api/review and /api/feedback are retained.
