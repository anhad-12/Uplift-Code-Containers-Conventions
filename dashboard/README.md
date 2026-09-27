# Uplift Dashboard

Dash app that loads validated Uplift reports and draws the change-impact graph.

**Live URL:** `https://uplift-dashboard.onrender.com` *(placeholder — fill in after first deploy)*

---

## Setup

Python 3.11 or 3.12 required.

```
cd dashboard
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Run (local)

**Windows:**
```
cd dashboard
.venv\Scripts\python app.py
```

Open http://127.0.0.1:8050. The home page lists scenario cards; clicking one shows the
risk gauge, metric cards, the pipeline stepper, and a change-impact graph. Click a node to
see the detail panel. Use the upload zone or paste textarea to load your own report JSON.

**Linux / macOS (gunicorn):**
```
cd dashboard
gunicorn app:server
```

## Test

```
cd dashboard
.venv\Scripts\python -m pytest -q
```

All tests should pass (158 as of C8).

---

## Deploy to Render (primary)

`dashboard/render.yaml` is already committed. The exact click-by-click steps:

1. **Connect repo** — go to https://render.com → *New → Web Service* → connect your GitHub repo.
2. **Root directory** — set to `dashboard`.
3. **Build command** — `pip install -r requirements.txt` (pre-filled from render.yaml).
4. **Start command** — `gunicorn app:server` (pre-filled).
5. **Environment** — add env var `PYTHON_VERSION = 3.12.6` (pre-filled).
6. **Create Web Service** — Render builds and deploys; first deploy takes ~2 min.
7. **Live URL** — copy the `.onrender.com` URL, update the badge above, and paste into the
   lablab "Application URL" field.

> The app carries its own copy of `schema/report.schema.json` (`dashboard/schema/`) because
> Render deploys only the `dashboard/` root directory.

---

## Deploy to Hugging Face Spaces (backup)

Create a new Space (Docker SDK) and add the following `Dockerfile` at the repo root:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY dashboard/ .
EXPOSE 7860
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:server"]
```

Push to the Space repo. HF Spaces runs on port 7860 by default.

---

## Files that must be committed for the app to work

The dashboard is fully self-contained — no backend, no secrets, no database:

| File | Purpose |
|------|---------|
| `app.py` | Dash app + callbacks |
| `panels.py` | DataTable, gauge, summary strip |
| `graph.py` | Cytoscape element builder |
| `loader.py` | Report loader + validator |
| `comment.py` | PR comment renderer |
| `requirements.txt` | Python dependencies |
| `reports/*.json` | Built-in scenario reports |
| `schema/report.schema.json` | Validation schema |
| `assets/style.css` | Design system + CSS tokens |
| `assets/og.png` | 1200×630 OG share image |
| `render.yaml` | Render deploy config |
