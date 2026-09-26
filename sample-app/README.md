# sample-app

A small FastAPI shop built on Pydantic v1. Used as a demo target.

## Requirements

- Python 3.11 or 3.12

## Create the virtual environment

```
python -m venv .venv
```

On macOS/Linux:

```
.venv/bin/python -m pip install -r requirements.txt
```

On Windows:

```
.venv\Scripts\python -m pip install -r requirements.txt
```

## Run the tests

macOS/Linux:

```
.venv/bin/python -m pytest -q
```

Windows:

```
.venv\Scripts\python -m pytest -q
```

Expected output: 46 passed.
