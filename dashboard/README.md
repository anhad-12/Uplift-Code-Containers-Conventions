# Uplift Dashboard

Dash app that loads validated Uplift reports and draws the change-impact graph.

## Setup

Python 3.11 or 3.12 required.

```
cd dashboard
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Run

```
cd dashboard
.venv\Scripts\python app.py
```

Open http://127.0.0.1:8050. The home page lists two scenario cards; clicking one shows the risk/metric cards, the stepper, and a graph with a star in the middle and coloured nodes on rings; clicking a node fills the right-hand panel.

## Test

```
cd dashboard
.venv\Scripts\python -m pytest -q
```

Expects 5 passed.

## Deploy

Deploy to Render (static site reading committed JSON — no backend required):

1. Connect the GitHub repo to Render.
2. Set the root directory to `dashboard/`.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:server`
5. Environment variable: `PYTHON_VERSION=3.12`

The dashboard carries its own copy of `schema/report.schema.json` (`dashboard/schema/`) because Render deploys only the `dashboard/` folder. (Filled in at C8 with live URL.)
